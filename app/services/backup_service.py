"""
Serviço de backup manual do SisPatrimônio Pro (feature 015).

Regras (contracts/service-contract.md, research R1–R8):
- Geração: dump consistente do banco via utilitário nativo do SGBD
  (mysqldump/mariadb-dump) em subprocesso; a senha vai EXCLUSIVAMENTE pelo
  ambiente do subprocesso (MYSQL_PWD) — nunca em argv, logs ou auditoria.
- Arquivo: data/backups/backup_YYYYMMDD_HHMMSS_micros.sql — timestamp UTC
  com microssegundos (unicidade em gerações repetidas; padrão do projeto de
  datas — feature 004). A regex estrita do nome é a âncora de reconhecimento
  e proteção contra path traversal.
- Listagem: derivada do repositório de arquivos (sem tabela; zero DDL) —
  considera apenas arquivos com o padrão de nome.
- Auditoria: todo resultado (sucesso/falha/download) registrado via
  write_audit, sem credenciais.
"""

import gzip
import hashlib
import logging
import os
import re
import subprocess
import threading
import time
import zlib
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse, unquote

import shutil

from app.config import BACKUP_DIR, DATABASE_URL, MYSQLDUMP_PATH
from app.models.user import User
from app.services.audit_service import (
    ACTION_BACKUP_CREATED,
    ACTION_BACKUP_DOWNLOAD,
    ACTION_BACKUP_FAILED,
    ACTION_BACKUP_PRE_RESTORE,
    ACTION_BACKUP_RESTORE_FAILED,
    ACTION_BACKUP_RESTORE_STARTED,
    ACTION_BACKUP_RESTORE_SUCCESS,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    write_audit,
)
from sqlalchemy.orm import Session

# Padrão estrito do nome de backup (data-model §1):
# backup_YYYYMMDD_HHMMSS_micros.sql — âncora de reconhecimento e de
# proteção contra path traversal (qualquer nome fora disso é rejeitado
# antes de tocar o disco).
# 016: aceita também o sufixo comprimido .sql.gz (compatibilidade BV-10;
# temporários .part/.part.gz ficam FORA do padrão — nunca listáveis).
_BACKUP_NAME_RE = re.compile(r"^backup_(\d{8})_(\d{6})_(\d{6})\.sql(\.gz)?$")

_DUMP_TIMEOUT_SECONDS = 600

# 018 (research R1): a senha vai EXCLUSIVAMENTE no ambiente do subprocesso
# (MYSQL_PWD); o ambiente é herdado do processo (nunca mais o PATH fixo Unix
# que impedia o Windows de resolver o executável).
_DUMP_TOOL_NAME = "mysqldump"
_IMPORT_TOOL_NAME = "mysql"


def _dump_env(password: str) -> Dict[str, str]:
    """Ambiente do subprocesso de dump/import: herda o processo + MYSQL_PWD (R1)."""
    env = os.environ.copy()
    env["MYSQL_PWD"] = password
    return env


def _resolve_tool_executable(tool_name: str) -> str:
    """Resolve o executável nativo do SGBD (R3/R6):

    1) MYSQLDUMP_PATH configurada (apontando o mysqldump; o cliente de import
       é derivado do mesmo bin — R4) — falha CLARA se o caminho não existe;
    2) fallback: shutil.which no PATH do processo (comportamento Linux atual);
    3) ausente → BackupError com mensagem distinta de 'não encontrado'
       (diagnosticável, sem segredos).
    """
    if tool_name == _DUMP_TOOL_NAME and MYSQLDUMP_PATH:
        configured = Path(MYSQLDUMP_PATH)
        if not configured.is_file():
            raise BackupError(
                "O utilitário de dump não foi encontrado no servidor: "
                "MYSQLDUMP_PATH aponta para um caminho inexistente. "
                "Verifique a configuração."
            )
        return str(configured)

    found = shutil.which(tool_name)
    if found:
        return found

    raise BackupError(
        f"O utilitário '{tool_name}' não foi encontrado no servidor. "
        "Instale-o ou configure o caminho correto (variável MYSQLDUMP_PATH)."
    )


def _resolve_import_executable() -> str:
    """Executável do cliente de import (R4, refinado pela suíte 017):

    Nunca falha antecipadamente (os fakes de Popen da suíte precisam ser
    alcançados em qualquer SO): (1) derivado do MYSQLDUMP_PATH (mesmo bin,
    sufixo preservado) quando existir; (2) shutil.which no PATH; (3) nome
    simples — a execução levantará FileNotFoundError, tratado com a
    mensagem distinta de 'não encontrado'."""
    if MYSQLDUMP_PATH:
        configured = Path(MYSQLDUMP_PATH)
        derived = configured.with_name(
            configured.name.replace(_DUMP_TOOL_NAME, _IMPORT_TOOL_NAME)
        )
        if derived.is_file():
            return str(derived)
    return shutil.which(_IMPORT_TOOL_NAME) or _IMPORT_TOOL_NAME

# Log técnico do módulo (feature 016, briefing §26): usa o handler rotativo
# existente; nunca registra credenciais, DATABASE_URL ou o comando completo.
logger = logging.getLogger(__name__)

# Compressão/leitura em blocos de 1 MB — memória constante (research R2/R4)
_CHUNK_SIZE = 1024 * 1024

# Restauração segura (feature 017, research R6): bloqueio de concorrência em
# memória do processo (uvicorn único — data-model BV-R2). Durante um restore:
# novo restore e geração de backup manual são rejeitados (FR-16/FR-17).
_RESTORE_LOCK = threading.Lock()
_RESTORE_IN_PROGRESS = False
_IMPORT_TIMEOUT_SECONDS = 900

# Tabelas essenciais para validação pós-restore (contract §4, remediação A1:
# nomes dos __tablename__ reais dos models)
_ESSENTIAL_TABLES = frozenset(
    {
        "users", "user_roles", "user_sessions", "roles", "role_permissions",
        "permissions", "custodians", "locations", "assets", "movements",
        "maintenances", "inventarios", "inventario_itens", "audit_logs",
        "ad_settings", "ad_group_roles", "setup_claims",
    }
)


def _timestamp_suffix() -> str:
    """Sufixo do nome: UTC com microssegundos (remediação I1)."""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")


def _filename_to_datetime(filename: str) -> datetime:
    """Converte o timestamp do nome (UTC) em datetime para a listagem."""
    match = _BACKUP_NAME_RE.match(filename)
    if not match:
        raise ValueError(f"Nome de backup fora do padrão: {filename!r}")
    date_part, time_part, micro_part = match.group(1), match.group(2), match.group(3)
    return datetime.strptime(f"{date_part}_{time_part}_{micro_part}", "%Y%m%d_%H%M%S_%f")


def _run_mysqldump(path: Path) -> None:
    """Executor padrão de produção (contract §1.2, research R1/R2).

    - Utilitário nativo do SGBD via subprocesso; stdout → arquivo.
    - Credenciais derivadas de DATABASE_URL em memória; a senha vai
      EXCLUSIVAMENTE no ambiente do subprocesso (MYSQL_PWD) — nunca em
      argv, logs, erros ou auditoria (Princípio VI).
    - Função de módulo: permite injeção nos testes web via monkeypatch
      (remediação U1).
    """
    parsed = urlparse(DATABASE_URL)
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    database = unquote((parsed.path or "").lstrip("/"))

    if not database:
        raise BackupError("DATABASE_URL não contém o nome do banco de dados.")

    # 018 (R1/R3): executável resolvido (config → PATH) e ambiente herdado;
    # a senha EXCLUSIVAMENTE no ambiente (nunca em argv — Princípio VI).
    executable = _resolve_tool_executable(_DUMP_TOOL_NAME)
    env = _dump_env(password)

    try:
        with open(path, "wb") as out:
            subprocess.run(
                [
                    executable,
                    "--single-transaction",
                    "--no-tablespaces",
                    f"--host={host}",
                    f"--port={port}",
                    f"--user={user}",
                    database,
                ],
                stdout=out,
                stderr=subprocess.PIPE,
                env=env,
                timeout=_DUMP_TIMEOUT_SECONDS,
                check=True,
            )
    except subprocess.CalledProcessError as exc:
        # Diagnóstico técnico no log (018 — R5, paridade com o import):
        # etapa, exit code e stderr SANITIZADO. stderr pode conter segredos —
        # NUNCA propagar ao usuário/auditoria (Princípio VI).
        stderr_text = ""
        if exc.stderr:
            stderr_text = exc.stderr.decode("utf-8", "replace")
        logger.error(
            "Dump falhou (etapa=dump, exit=%s). stderr do utilitário: %s",
            exc.returncode,
            _sanitize_stderr(stderr_text, password),
        )
        raise BackupError("O utilitário de dump retornou erro.")
    except subprocess.TimeoutExpired:
        logger.error("Dump falhou (etapa=dump): tempo limite de %ds excedido.", _DUMP_TIMEOUT_SECONDS)
        raise BackupError("O utilitário de dump excedeu o tempo limite.")
    except FileNotFoundError as exc:
        # Defesa em profundidade: executável sumiu entre a resolução e a
        # execução — mesmo tratamento diagnóstico (018)
        logger.error("Dump falhou (etapa=dump): executável indisponível (%s).", type(exc).__name__)
        raise BackupError(
            "O utilitário de dump não foi encontrado no servidor. "
            "Instale-o ou configure o caminho correto (variável MYSQLDUMP_PATH)."
        ) from exc


class BackupError(Exception):
    """Falha controlada de backup (mensagem segura para o usuário/auditoria)."""


def restore_in_progress() -> bool:
    """Indica se há uma restauração em andamento (contract §1)."""
    with _RESTORE_LOCK:
        return _RESTORE_IN_PROGRESS


class _restore_slot:
    """Context manager do slot de concorrência (BV-R2): marca o restore em
    andamento e libera em `finally` (sucesso ou falha)."""

    def __enter__(self):
        global _RESTORE_IN_PROGRESS
        with _RESTORE_LOCK:
            if _RESTORE_IN_PROGRESS:
                raise BackupError(
                    "Já existe uma restauração em andamento. Aguarde a conclusão antes de iniciar outra."
                )
            _RESTORE_IN_PROGRESS = True
        return self

    def __exit__(self, exc_type, exc, tb):
        global _RESTORE_IN_PROGRESS
        with _RESTORE_LOCK:
            _RESTORE_IN_PROGRESS = False
        return False


def _sanitize_stderr(stderr_text: str, password: str) -> str:
    """Sanitiza o stderr do cliente para o log técnico (Princípio VI).

    Remove a senha do banco (caso apareça em alguma mensagem) e limita o
    tamanho, preservando o diagnóstico (código de erro, sintaxe, linha).
    """
    if not stderr_text:
        return "(sem saída de erro)"
    text = stderr_text.strip()
    if password:
        text = text.replace(password, "***")
    if len(text) > 500:
        text = text[:500] + "…"
    return text


def _run_mysql_import(path: Path, *, is_gzip: bool) -> None:
    """Importa o dump com o cliente nativo do SGBD (contract §3, research R1).

    Função de MÓDULO com implementação real (remediação I1) — fake apenas nos
    testes via monkeypatch (research R2).

    - O Python abre o dump (gzip streaming ou direto) e alimenta o stdin do
      subprocesso — sem pipelines de shell (briefing §18).
    - Credenciais derivadas de DATABASE_URL em memória; a senha vai
      EXCLUSIVAMENTE no ambiente do subprocesso (MYSQL_PWD) — nunca em
      argv, logs, erros ou auditoria (Princípio VI).
    - stderr capturado e NUNCA propagado (pode conter host/credenciais).
    """
    parsed = urlparse(DATABASE_URL)
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    database = unquote((parsed.path or "").lstrip("/"))

    if not database:
        raise BackupError("DATABASE_URL não contém o nome do banco de dados.")

    # 018 (R1/R4): mesma correção do dump — ambiente herdado + MYSQL_PWD e
    # executável derivado do MYSQLDUMP_PATH (mesmo bin) com fallback PATH.
    executable = _resolve_import_executable()
    env = _dump_env(password)

    try:
        # Streaming: o Python alimenta o stdin do cliente bloco a bloco
        # (memória constante; sem pipelines de shell — briefing §18).
        # stderr é capturado para diagnóstico no log técnico (sanitizado —
        # §31: nunca credenciais) e NUNCA vai ao usuário/auditoria.
        proc = subprocess.Popen(
            [
                executable,
                f"--host={host}",
                f"--port={port}",
                f"--user={user}",
                database,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=env,
        )
        try:
            for chunk in _iter_dump_chunks(path, is_gzip):
                proc.stdin.write(chunk)
            proc.stdin.close()
            proc.wait(timeout=_IMPORT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise BackupError("O utilitário de importação excedeu o tempo limite.")
        stderr_text = ""
        if proc.stderr is not None:
            stderr_text = proc.stderr.read().decode("utf-8", "replace")
            proc.stderr.close()
        if proc.returncode != 0:
            # Diagnóstico técnico no log (sanitizado); usuário/auditoria
            # recebem apenas a mensagem controlada (§26/§31)
            logger.error(
                "Importação de dump falhou (exit=%s). stderr do cliente: %s",
                proc.returncode,
                _sanitize_stderr(stderr_text, password),
            )
            raise subprocess.CalledProcessError(proc.returncode, proc.args)
    except subprocess.CalledProcessError:
        # stderr pode conter host/comando — NUNCA propagar (Princípio VI)
        raise BackupError("O utilitário de importação retornou erro.")
    except subprocess.TimeoutExpired:
        raise BackupError("O utilitário de importação excedeu o tempo limite.")
    except FileNotFoundError as exc:
        # 018: executável ausente no PATH/config — falha clara e
        # diagnosticável (mesma mensagem-padrão da resolução do dump)
        logger.error(
            "Importação falhou (etapa=import): executável indisponível (%s).",
            type(exc).__name__,
        )
        raise BackupError(
            "O utilitário 'mysql' não foi encontrado no servidor. "
            "Instale-o ou configure o caminho correto (variável MYSQLDUMP_PATH)."
        ) from exc


def _iter_dump_chunks(path: Path, is_gzip: bool):
    """Gera o conteúdo do dump em blocos (gzip streaming ou direto — R1)."""
    opener = gzip.open if is_gzip else open
    with opener(path, "rb") as src:
        while True:
            chunk = src.read(_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk


class BackupService:
    # =========================================================================
    # GERAÇÃO (US1)
    # =========================================================================

    @staticmethod
    def generate_backup(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
        *,
        dump_executor: Optional[Callable[[Path], None]] = None,
        _allow_during_restore: bool = False,
    ) -> Dict:
        """Gera um backup do estado atual do sistema (contract §1.1).

        - `dump_executor` permite injeção para testes (research R4);
          em produção usa `_run_mysqldump`.
        - Em sucesso: grava ACTION_BACKUP_CREATED/SUCCESS e retorna
          {filename, timestamp, size_bytes}.
        - Em falha: remove artefato parcial (BV-4), grava ACTION_BACKUP_CREATED/
          FAILURE com descrição controlada e propaga BackupError.
        """
        executor: Callable[[Path], None] = dump_executor or _run_mysqldump

        # 017 (FR-17, BV-R2): durante uma restauração, geração de backup é
        # rejeitada — evita subprocessos de dump/import simultâneos no banco.
        # O próprio restore_backup gera o backup de segurança com a flag
        # `_allow_during_restore` (chamada interna, dentro do slot).
        if not _allow_during_restore and restore_in_progress():
            raise BackupError(
                "Não é possível gerar backup durante uma restauração em andamento."
            )

        base = f"backup_{_timestamp_suffix()}"
        part_path = BACKUP_DIR / f"{base}.part"
        part_gz_path = BACKUP_DIR / f"{base}.part.gz"
        final_path = BACKUP_DIR / f"{base}.sql.gz"

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        started = time.monotonic()
        logger.info("Início da geração de backup manual (%s).", base)

        try:
            # Nunca sobrescreve nome final existente (BV-3 da 015, mantida)
            if final_path.exists():
                raise BackupError("Conflito de nome de backup; tente novamente.")

            # 1) Dump no temporário .part (nunca casa o regex final — BV-8)
            executor(part_path)

            # 2) Compressão streaming .part → .part.gz (blocos de 1 MB, stdlib).
            #    filename="" evita embutir o nome do temporário no cabeçalho
            #    gzip (FNAME) — a extração externa produz `backup_....sql`,
            #    não `backup_....part`.
            with open(part_path, "rb") as src, open(
                part_gz_path, "wb"
            ) as raw_dst, gzip.GzipFile(
                fileobj=raw_dst, mode="wb", filename=""
            ) as dst:
                while True:
                    chunk = src.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    dst.write(chunk)
            part_path.unlink(missing_ok=True)

            # 3) Validação: existe, tamanho > 0 e gzip legível (briefing §16)
            if not part_gz_path.is_file() or part_gz_path.stat().st_size <= 0:
                raise BackupError("O arquivo de backup gerado está vazio.")
            try:
                with gzip.open(part_gz_path, "rb") as gz:
                    while gz.read(_CHUNK_SIZE):
                        pass
            except (OSError, EOFError, zlib.error) as gz_exc:
                raise BackupError("O arquivo de backup gerado é inválido.") from gz_exc

            # 4) SHA-256 streaming sobre o arquivo comprimido (briefing §16)
            sha256 = hashlib.sha256()
            with open(part_gz_path, "rb") as f:
                while True:
                    chunk = f.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    sha256.update(chunk)
            digest = sha256.hexdigest()

            # 5) Renomear para o nome final — atômico no mesmo filesystem (§27)
            part_gz_path.rename(final_path)

            size_bytes = final_path.stat().st_size
            duration = time.monotonic() - started

            write_audit(
                db,
                user=user,
                action=ACTION_BACKUP_CREATED,
                module="Backup",
                resource="backup",
                resource_ref=final_path.name,
                ip_address=ip_address,
                result=RESULT_SUCCESS,
                description="Backup manual gerado com sucesso.",
                new_data={
                    "arquivo": final_path.name,
                    "tamanho_bytes": size_bytes,
                    "sha256": digest,
                },
            )
            logger.info(
                "Backup concluído: %s (%d bytes, sha256=%s) em %.2fs.",
                final_path.name,
                size_bytes,
                digest,
                duration,
            )
            return {
                "filename": final_path.name,
                "timestamp": _filename_to_datetime(final_path.name),
                "size_bytes": size_bytes,
                "sha256": digest,
            }
        except Exception as exc:
            # Remove temporários .part* (BV-8): parcial nunca fica disponível
            for leftover in (part_path, part_gz_path):
                try:
                    if leftover.exists():
                        leftover.unlink()
                except OSError:
                    pass

            description = "Falha na geração do backup manual."
            if isinstance(exc, BackupError):
                description = f"Falha na geração do backup manual: {exc}"
            elif isinstance(exc, (OSError, subprocess.SubprocessError)):
                description = "Falha na geração do backup manual (erro de disco/subprocesso)."

            write_audit(
                db,
                user=user,
                action=ACTION_BACKUP_FAILED,
                module="Backup",
                resource="backup",
                resource_ref=base,
                ip_address=ip_address,
                result=RESULT_FAILURE,
                description=description,
            )
            # Log de erro com a descrição controlada — sem segredos (§26)
            logger.error("%s", description)
            raise BackupError(description) from exc

    # =========================================================================
    # LISTAGEM (US2)
    # =========================================================================

    @staticmethod
    def _gzip_read_status(path: Path):
        """Valida o gzip e calcula o SHA-256 do ARQUIVO (bytes em disco).

        Retorna (ok, sha256_hex | None) (contract §3; quickstart §3.4: o hash
        exibido é o `sha256sum` do próprio arquivo, comparável ao download).

        - ok=True → gzip legível até o fim (trailer válido); sha256 = hash
          streaming dos bytes do arquivo (mesmo cálculo de generate_backup).
        - OSError/EOFError → corrompido; sha256 é omitido (None) para não
          exibir um hash de um conteúdo que não pôde ser integralmente lido.
        """
        try:
            with gzip.open(path, "rb") as gz:
                while gz.read(_CHUNK_SIZE):
                    pass
        except (OSError, EOFError, zlib.error):
            return False, None

        digest = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(_CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
        return True, digest.hexdigest()

    @staticmethod
    def list_backups() -> List[Dict]:
        """Lista os backups disponíveis (contract §3 — v2 com Integridade).

        Considera apenas arquivos com o padrão de nome; ordena do mais
        recente para o mais antigo. Diretório inexistente → [].

        Campos aditivos v2: `sha256` (streaming on-demand; None para .sql
        antigos — BV-10) e `integrity` (OK | CORROMPIDO | —).
        """
        if not BACKUP_DIR.exists():
            return []

        backups: List[Dict] = []
        for entry in BACKUP_DIR.iterdir():
            if not entry.is_file() or not _BACKUP_NAME_RE.match(entry.name):
                continue  # artefatos alheios e temporários .part são ignorados

            sha256: Optional[str] = None
            integrity = "—"
            if entry.name.endswith(".gz"):
                readable, gz_sha = BackupService._gzip_read_status(entry)
                if readable:
                    integrity = "OK"
                    sha256 = gz_sha
                else:
                    integrity = "CORROMPIDO"

            backups.append(
                {
                    "filename": entry.name,
                    "timestamp": _filename_to_datetime(entry.name),
                    "size_bytes": entry.stat().st_size,
                    "sha256": sha256,
                    "integrity": integrity,
                }
            )

        backups.sort(key=lambda b: b["filename"], reverse=True)
        return backups

    # =========================================================================
    # RESTAURAÇÃO SEGURA (feature 017)
    # =========================================================================

    @staticmethod
    def validate_restore_source(filename: str) -> Dict:
        """Valida o backup selecionado antes de restaurar (contract §2, FR-09).

        Reusa `get_backup_path` (regex/existência/path traversal) + integridade
        da listagem (CORROMPIDO rejeita) + leitura de teste. Falha → BackupError
        com motivo seguro; restauração não inicia (Testes D/E/F).
        """
        try:
            path = BackupService.get_backup_path(filename)
        except FileNotFoundError as exc:
            raise BackupError("Backup não encontrado ou fora do padrão.") from exc

        size_bytes = path.stat().st_size
        if size_bytes <= 0:
            raise BackupError("O arquivo de backup está vazio.")

        is_gzip = filename.endswith(".gz")
        if is_gzip:
            # Integridade já calculada pela 016 (gzip legível integralmente)
            integrity = next(
                (
                    b["integrity"]
                    for b in BackupService.list_backups()
                    if b["filename"] == filename
                ),
                None,
            )
            if integrity == "CORROMPIDO":
                raise BackupError(
                    "O arquivo de backup está corrompido e não pode ser restaurado."
                )
            if integrity not in ("OK", "—", None):
                raise BackupError("Integridade do backup não pôde ser verificada.")
            # Leitura de teste adicional (defesa em profundidade)
            readable, _ = BackupService._gzip_read_status(path)
            if not readable:
                raise BackupError(
                    "O arquivo de backup está corrompido e não pode ser restaurado."
                )
        else:
            # .sql legado (sem checksum — Assumption 4): valida conteúdo não vazio
            with open(path, "rb") as f:
                if not f.read(1024):
                    raise BackupError("O arquivo de backup está vazio.")

        return {"path": path, "is_gzip": is_gzip, "size_bytes": size_bytes}

    @staticmethod
    def validate_post_restore(db: Session) -> None:
        """Validação pós-restore real (contract §4, FR-20/FR-21 — somente leitura).

        1) SELECT 1 executável; 2) presença das 17 tabelas essenciais
        (remediação A1); 3) contagens somente-leitura executáveis.
        Qualquer falha → BackupError com motivo seguro (nunca sucesso
        apenas porque o import retornou 0 — briefing §24).
        """
        from sqlalchemy import inspect, text

        try:
            db.execute(text("SELECT 1"))
        except Exception as exc:
            raise BackupError("Falha ao conectar ao banco após a restauração.") from exc

        try:
            inspector = inspect(db.bind)
            present = set(inspector.get_table_names())
        except Exception as exc:
            raise BackupError(
                "Falha ao inspecionar o banco após a restauração."
            ) from exc

        missing = sorted(_ESSENTIAL_TABLES - present)
        if missing:
            raise BackupError(
                "Tabelas essenciais ausentes após a restauração: " + ", ".join(missing)
            )

        try:
            for table in ("users", "assets", "custodians"):
                db.execute(text(f"SELECT COUNT(*) FROM {table}"))
        except Exception as exc:
            raise BackupError(
                "Dados essenciais inacessíveis após a restauração."
            ) from exc

    @staticmethod
    def restore_backup(
        db: Session,
        user: User,
        ip_address: Optional[str],
        filename: str,
        *,
        import_executor: Optional[Callable[[Path, bool], None]] = None,
        security_backup_executor: Optional[Callable[[Path], None]] = None,
    ) -> Dict:
        """Restaura um backup com o ciclo seguro completo (contract §5).

        Ordem invariável (BV-R1..R4): valida fonte → INICIADO → backup de
        segurança (generate_backup, com security_backup_executor delegado
        como dump_executor — remediação U1) → valida segurança →
        PRE_RESTORE_CRIADO → import → validação pós-restore → SUCCESS.

        Falha em qualquer etapa → BACKUP_RESTORE_FALHA com motivo seguro +
        BackupError (nunca falso sucesso; backup de segurança preservado).
        Slot de concorrência ocupado durante todo o ciclo, liberado em finally.
        """
        do_import = import_executor or _run_mysql_import

        try:
            source = BackupService.validate_restore_source(filename)
        except BackupError as exc:
            write_audit(
                db,
                user=user,
                action=ACTION_BACKUP_RESTORE_FAILED,
                module="Backup",
                resource="backup",
                resource_ref=filename,
                ip_address=ip_address,
                result=RESULT_FAILURE,
                description=f"Restauração não iniciada: {exc}",
            )
            raise

        try:
            with _restore_slot():
                write_audit(
                    db,
                    user=user,
                    action=ACTION_BACKUP_RESTORE_STARTED,
                    module="Backup",
                    resource="backup",
                    resource_ref=filename,
                    ip_address=ip_address,
                    result=RESULT_SUCCESS,
                    description="Restauração de backup iniciada.",
                    new_data={"backup": filename},
                )

                # Backup de segurança OBRIGATÓRIO (FR-11) — mecanismo da Feature 1.
                # Chamada interna dentro do slot: bypass da guarda de concorrência.
                try:
                    security = BackupService.generate_backup(
                        db,
                        user,
                        ip_address,
                        dump_executor=security_backup_executor,
                        _allow_during_restore=True,
                    )
                except Exception as exc:
                    description = (
                        "Restauração não iniciada: falha ao criar o backup de segurança."
                    )
                    write_audit(
                        db,
                        user=user,
                        action=ACTION_BACKUP_RESTORE_FAILED,
                        module="Backup",
                        resource="backup",
                        resource_ref=filename,
                        ip_address=ip_address,
                        result=RESULT_FAILURE,
                        description=description,
                    )
                    logger.error("%s", description)
                    raise BackupError(
                        "Não foi possível criar o backup de segurança; a restauração não foi iniciada."
                    ) from exc

                security_name = security["filename"]
                try:
                    sec_info = BackupService.validate_restore_source(security_name)
                except BackupError as exc:
                    description = (
                        "Restauração não iniciada: backup de segurança inválido."
                    )
                    write_audit(
                        db,
                        user=user,
                        action=ACTION_BACKUP_RESTORE_FAILED,
                        module="Backup",
                        resource="backup",
                        resource_ref=filename,
                        ip_address=ip_address,
                        result=RESULT_FAILURE,
                        description=description,
                    )
                    logger.error("%s", description)
                    raise BackupError(description) from exc

                write_audit(
                    db,
                    user=user,
                    action=ACTION_BACKUP_PRE_RESTORE,
                    module="Backup",
                    resource="backup",
                    resource_ref=security_name,
                    ip_address=ip_address,
                    result=RESULT_SUCCESS,
                    description="Backup de segurança pré-restauração criado.",
                    new_data={"backup": filename, "backup_seguranca": security_name},
                )

                # Import (cliente nativo em produção; fake nos testes)
                try:
                    do_import(source["path"], is_gzip=source["is_gzip"])
                except Exception as exc:
                    description = (
                        "Restauração não concluída: falha na importação do dump. "
                        "O backup de segurança permanece disponível para restauração manual."
                    )
                    write_audit(
                        db,
                        user=user,
                        action=ACTION_BACKUP_RESTORE_FAILED,
                        module="Backup",
                        resource="backup",
                        resource_ref=filename,
                        ip_address=ip_address,
                        result=RESULT_FAILURE,
                        description=description,
                    )
                    logger.error("%s", description)
                    raise BackupError(description) from exc

                # Validação pós-restore real (nunca sucesso só por retorno 0)
                try:
                    BackupService.validate_post_restore(db)
                except BackupError as exc:
                    description = (
                        f"Restauração não concluída: {exc} "
                        "O backup de segurança permanece disponível para restauração manual."
                    )
                    write_audit(
                        db,
                        user=user,
                        action=ACTION_BACKUP_RESTORE_FAILED,
                        module="Backup",
                        resource="backup",
                        resource_ref=filename,
                        ip_address=ip_address,
                        result=RESULT_FAILURE,
                        description=description,
                    )
                    logger.error("%s", description)
                    raise BackupError(description) from exc

                write_audit(
                    db,
                    user=user,
                    action=ACTION_BACKUP_RESTORE_SUCCESS,
                    module="Backup",
                    resource="backup",
                    resource_ref=filename,
                    ip_address=ip_address,
                    result=RESULT_SUCCESS,
                    description="Backup restaurado com sucesso.",
                    new_data={
                        "backup": filename,
                        "backup_seguranca": security_name,
                    },
                )
                return {
                    "restaurado": filename,
                    "backup_seguranca": security_name,
                    "size_bytes": sec_info["size_bytes"],
                }
        except BackupError:
            raise
        except Exception as exc:
            description = "Restauração não concluída por erro inesperado."
            write_audit(
                db,
                user=user,
                action=ACTION_BACKUP_RESTORE_FAILED,
                module="Backup",
                resource="backup",
                resource_ref=filename,
                ip_address=ip_address,
                result=RESULT_FAILURE,
                description=description,
            )
            logger.error("%s", description)
            raise BackupError(description) from exc

    # =========================================================================
    # DOWNLOAD (US3)
    # =========================================================================

    @staticmethod
    def get_backup_path(filename: str) -> Path:
        """Valida o nome e retorna o caminho do backup (contract §1.4).

        Levanta FileNotFoundError (→ 404 na rota) se o nome está fora do
        padrão (path traversal impossível — R8) ou se o arquivo não existe.
        """
        if not _BACKUP_NAME_RE.match(filename):
            raise FileNotFoundError(f"Nome de backup inválido: {filename!r}")

        path = BACKUP_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(f"Backup não encontrado: {filename}")

        return path
