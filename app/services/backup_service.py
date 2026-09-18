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
from app.database import SessionLocal
from app.database import drain_engine
from app.models.backup_record import BackupRecord
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

# ============================================================================
# FEATURE 020 — tipos de backup (metadados determinísticos; spec FR-013)
# Vocabulário controlado persistido em backup_records.backup_type. Os rótulos
# conceituais do briefing (BACKUP_*) não são valores de banco.
# ============================================================================
BACKUP_TYPE_MANUAL = "MANUAL"
BACKUP_TYPE_AUTOMATICO = "AUTOMATICO"
BACKUP_TYPE_PRE_RESTAURACAO = "PRE_RESTAURACAO"
_VALID_BACKUP_TYPES = (
    BACKUP_TYPE_MANUAL,
    BACKUP_TYPE_AUTOMATICO,
    BACKUP_TYPE_PRE_RESTAURACAO,
)


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

# ============================================================================
# FEATURE 019 — deadline do import + modo de manutenção (R2/R3, contract §5)
# ============================================================================

# Deadline de relógio do import (segundos): cobre TODAS as fases do subprocesso,
# inclusive o feed no stdin (onde o incidente de 2026-09-18 bloqueou — D2).
# Configurável via .env; lida APÓS load_dotenv (guarda da 018).
def _default_import_timeout() -> float:
    try:
        from app.config import BACKUP_IMPORT_TIMEOUT

        return float(BACKUP_IMPORT_TIMEOUT)
    except Exception:  # pragma: no cover — config sempre define (default 900)
        return 900.0


BACKUP_IMPORT_TIMEOUT = _default_import_timeout()

# Modo de manutenção (FR-010..FR-013): flag EM MEMÓRIA (nunca persistida —
# crash/restart limpa por construção, R3). Gerida pelo ciclo do restore;
# consultada pelo middleware de app.main ANTES de qualquer dependência de banco.
maintenance_mode: Dict = {
    "active": False,
    "started_at": None,
    "phase": None,
    "target_file": None,
}


def _maintenance_set(active: bool, phase: Optional[str] = None) -> None:
    """Liga/desliga o modo de manutenção (chamado apenas pelo ciclo do restore)."""
    maintenance_mode["active"] = active
    if active:
        # Carimbo do início REAL: só na transição inativo→ativo (trocas de
        # fase — seguranca/importando/verificando — não resetam o horário).
        if not maintenance_mode.get("active"):
            maintenance_mode["started_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        maintenance_mode["phase"] = phase
    else:
        maintenance_mode["started_at"] = None
        maintenance_mode["phase"] = None
        maintenance_mode["target_file"] = None
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


def restore_status() -> Dict:
    """Estado da restauração para a rota de polling (019, contract §4).

    Sem segredos: apenas flags/fases/timestamps do ciclo.
    """
    with _RESTORE_LOCK:
        active = _RESTORE_IN_PROGRESS
    return {
        "active": active,
        "phase": maintenance_mode.get("phase"),
        "started_at": maintenance_mode.get("started_at"),
        "target_file": maintenance_mode.get("target_file"),
        "finished": not active and maintenance_mode.get("last_ok") is not None,
        "ok": bool(maintenance_mode.get("last_ok")),
        "message": maintenance_mode.get("last_message"),
    }


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


# ============================================================================
# FEATURE 020 — gravação de metadados (BackupRecord)
#
# Estratégia de sessão (data-model/contract §3): os helpers aceitam a SESSÃO
# DO FLUXO quando ela existe (request manual, ciclo do restore, worker do
# scheduler) — abertura/fechamento no ponto de uso sem reter conexão extra;
# quando nenhuma sessão é passada (fluxos sem sessão), abrem uma PRÓPRIA E
# CURTA (padrão _worker_audit da 019). Erro de metadados NUNCA invalida o
# backup físico (só loga — data-model §1).
# ============================================================================

def _write_backup_record(db: Optional[Session], record: BackupRecord) -> None:
    """Persiste o registro usando a sessão fornecida ou uma própria e curta."""
    own_session = db is None
    session = SessionLocal() if own_session else db
    try:
        session.add(record)
        session.commit()
    finally:
        if own_session:
            session.close()


def _record_backup_success(
    filename: str, backup_type: str, size_bytes: int, sha256: str, db: Optional[Session] = None
) -> None:
    """Registra tentativa bem-sucedida em backup_records (contract §3)."""
    try:
        if not _BACKUP_NAME_RE.match(filename):
            logger.error(
                "Registro de backup ignorado: filename fora do padrão (%s).", filename
            )
            return
        _write_backup_record(
            db,
            BackupRecord(
                filename=filename,
                backup_type=backup_type,
                status="SUCCESS",
                timestamp=_filename_to_datetime(filename),
                size_bytes=size_bytes,
                sha256=sha256,
            ),
        )
    except Exception as exc:  # metadados nunca invalidam o backup físico
        logger.error(
            "Falha ao gravar BackupRecord de sucesso para %s (tipo=%s): %s",
            filename,
            type(exc).__name__,
            exc,
        )


def _record_backup_failure(
    filename: str, backup_type: str, error_description: str, db: Optional[Session] = None
) -> None:
    """Registra tentativa FALHA em backup_records (contract §3; sem segredos)."""
    try:
        if not _BACKUP_NAME_RE.match(filename):
            logger.error(
                "Registro de falha de backup ignorado: filename fora do padrão (%s).",
                filename,
            )
            return
        _write_backup_record(
            db,
            BackupRecord(
                filename=filename,
                backup_type=backup_type,
                status="FAILURE",
                error_description=(error_description or "")[:255],
            ),
        )
    except Exception as exc:  # idem — loga e segue
        logger.error(
            "Falha ao gravar BackupRecord de falha para %s (tipo=%s): %s",
            filename,
            type(exc).__name__,
            exc,
        )


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
        # 019 (R2/D2): deadline de relógio cobrindo TODAS as fases — o feed no
        # stdin roda em THREAD ESCRITORA dedicada (select() não funciona em
        # pipes no Windows); o worker espera o término com o prazo configurável.
        _import_with_deadline(
            proc,
            lambda: _iter_dump_chunks(path, is_gzip),
            password=password,
            timeout=BACKUP_IMPORT_TIMEOUT,
        )
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


def _import_with_deadline(
    proc: "subprocess.Popen",
    chunks_factory: Callable[[], object],
    *,
    password: str,
    timeout: Optional[float] = None,
) -> None:
    """Feed do dump com DEADLINE DE RELÓGIO (019 — FR-007/R2, Teste B/D).

    O write no stdin roda em thread escritora dedicada; o worker espera o
    término com o prazo `timeout`. Bloqueou no pipe (caso real do incidente,
    D2) e estourou o prazo → terminate() no subprocesso: o pipe quebra, a
    thread escritora desbloqueia (BrokenPipeError é esperado e ignorado).
    Diagnóstico técnico no log: etapa, tempo decorrido e exit code — stderr
    NUNCA contém credenciais (sanitizado antes de qualquer log, Princípio VI).

    `proc` é injetável (testes usam fake com terminate/write/wait).
    """
    if timeout is None:
        timeout = BACKUP_IMPORT_TIMEOUT
    inicio = time.monotonic()
    erro_feed: list = []
    concluido = threading.Event()

    def _feeder():
        try:
            stdin = getattr(proc, "stdin", None)
            if stdin is None:
                # Sem stdin=PIPE não há feed — é falha de configuração do
                # subprocesso (nunca sucesso silencioso; FR-009).
                raise BackupError("O processo de importação não possui stdin configurado.")
            for chunk in chunks_factory():
                stdin.write(chunk)
            stdin.close()
        except BrokenPipeError:
            # terminate() do deadline quebra o pipe — desbloqueio esperado.
            pass
        except Exception as exc:  # qualquer outro erro do feed é registrado
            erro_feed.append(exc)
        finally:
            concluido.set()

    feeder = threading.Thread(target=_feeder, name="import-feeder-019", daemon=True)
    feeder.start()

    if not concluido.wait(timeout=timeout):
        decorrido = time.monotonic() - inicio
        # Estouro do prazo: encerra o subprocesso (hard-kill de segurança)
        try:
            proc.terminate()
            kill = getattr(proc, "kill", None)
            if callable(kill):
                kill()
        except Exception:  # pragma: no cover — processo já pode ter morrido
            pass
        concluido.wait(timeout=5.0)
        logger.error(
            "Importação excedeu o deadline (etapa=feed no stdin, limite=%ss, "
            "decorrido=%.1fs, exit=%s) — subprocesso encerrado.",
            timeout,
            decorrido,
            getattr(proc, "returncode", None),
        )
        raise BackupError(
            "A importação do dump excedeu o tempo limite configurado "
            "(BACKUP_IMPORT_TIMEOUT) e foi interrompida. "
            "Verifique o log técnico do servidor."
        )

    if erro_feed:
        logger.error(
            "Importação falhou na escrita do dump (etapa=feed no stdin): %s",
            type(erro_feed[0]).__name__,
        )
        raise BackupError(
            "Falha na escrita dos dados para o utilitário de importação."
        ) from erro_feed[0]

    # Feed concluído: espera o processo terminar dentro do MESMO prazo global
    restante = max(1.0, timeout - (time.monotonic() - inicio))
    try:
        proc.wait(timeout=restante)
    except subprocess.TimeoutExpired:
        decorrido = time.monotonic() - inicio
        try:
            proc.terminate()
            kill = getattr(proc, "kill", None)
            if callable(kill):
                kill()
        except Exception:  # pragma: no cover
            pass
        proc.wait(timeout=5.0)
        logger.error(
            "Importação excedeu o deadline (etapa=aguardando término, limite=%ss, "
            "decorrido=%.1fs, exit=%s) — subprocesso encerrado.",
            timeout,
            decorrido,
            getattr(proc, "returncode", None),
        )
        raise BackupError(
            "A importação do dump excedeu o tempo limite configurado "
            "(BACKUP_IMPORT_TIMEOUT) e foi interrompida. "
            "Verifique o log técnico do servidor."
        )


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
        backup_type: str = BACKUP_TYPE_MANUAL,
    ) -> Dict:
        """Gera um backup do estado atual do sistema (contract §1.1).

        - `dump_executor` permite injeção para testes (research R4);
          em produção usa `_run_mysqldump`.
        - Em sucesso: grava ACTION_BACKUP_CREATED/SUCCESS e retorna
          {filename, timestamp, size_bytes}.
        - Em falha: remove artefato parcial (BV-4), grava ACTION_BACKUP_CREATED/
          FAILURE com descrição controlada e propaga BackupError.

        Feature 020 (contract §3, aditivo):
        - `backup_type` ∈ {MANUAL, AUTOMATICO, PRE_RESTAURACAO} (default MANUAL
          — retrocompatível com todos os chamadores existentes); valor inválido
          → ValueError ANTES de qualquer dump;
        - Grava `BackupRecord` (sucesso e falha) com SESSÃO PRÓPRIA E CURTA;
          erro de metadados NUNCA invalida o backup físico (só loga — data-model);
        - Arquivo parcial: o cleanup de `.part*` no except registra no log
          técnico qualquer falha de remoção (F5), sem propagar.
        """
        # 020 (contract §3): validação do tipo ANTES de qualquer dump/disco
        if backup_type not in _VALID_BACKUP_TYPES:
            raise ValueError(
                f"Tipo de backup inválido: {backup_type!r}. "
                f"Esperado um de: {', '.join(_VALID_BACKUP_TYPES)}."
            )

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
            # 020 (contract §3): metadados determinísticos do backup gerado.
            # Sessão PRÓPRIA e curta (padrão _worker_audit da 019) — a sessão
            # do chamador não é retida; erro de metadados NUNCA invalida o
            # arquivo físico válido (data-model: registro é aditivo).
            _record_backup_success(final_path.name, backup_type, size_bytes, digest, db=db)
            return {
                "filename": final_path.name,
                "timestamp": _filename_to_datetime(final_path.name),
                "size_bytes": size_bytes,
                "sha256": digest,
            }
        except Exception as exc:
            # Remove temporários .part* (BV-8): parcial nunca fica disponível.
            # 020 (F5): falha de remoção é REGISTRADA no log técnico (a exceção
            # não propaga — o fluxo de falha original continua).
            for leftover in (part_path, part_gz_path):
                try:
                    if leftover.exists():
                        leftover.unlink()
                except OSError as cleanup_exc:
                    logger.error(
                        "Falha ao remover artefato parcial %s após erro de "
                        "geração (tipo=%s): %s",
                        leftover.name,
                        type(cleanup_exc).__name__,
                        cleanup_exc,
                    )

            description = "Falha na geração do backup manual."
            if isinstance(exc, BackupError):
                description = f"Falha na geração do backup manual: {exc}"
            elif isinstance(exc, (OSError, subprocess.SubprocessError)):
                description = "Falha na geração do backup manual (erro de disco/subprocesso)."

            # 020 (contract §3): metadados da tentativa FALHA — filename é o
            # nome FINAL projetado (casa com a regex; NÃO indica arquivo
            # disponível — data-model §1/BV-4).
            _record_backup_failure(f"{base}.sql.gz", backup_type, description, db=db)
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
        """Agenda a restauração com o ciclo seguro (feature 019 — contract §1.1).

        Fluxo 303/R5: valida a fonte, ocupa o slot de concorrência, marca o
        modo de manutenção e retorna ANTES do import. O ciclo destrutivo
        (segurança → drenagem do pool → import → validação pós → eventos)
        roda em WORKER THREAD com sessões próprias e curtas — no momento do
        import nenhuma transação do processo web está aberta e o pool está
        sem conexões vivas (elimina o auto-deadlock de metadata lock).

        Falha de validação/concorrência → fluxo de hoje (audit + BackupError).
        Ordem invariável do worker (BV-R1..R4 da 017 preservada — FR-004).
        """
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

        # Slot de concorrência da 017 + manutenção: marcados ANTES da thread
        # (nenhuma janela sem manutenção — contract §1.1/FR-011).
        global _RESTORE_IN_PROGRESS
        with _RESTORE_LOCK:
            if _RESTORE_IN_PROGRESS:
                raise BackupError(
                    "Já existe uma restauração em andamento. Aguarde a conclusão antes de iniciar outra."
                )
            _RESTORE_IN_PROGRESS = True

        _maintenance_set(True, phase="validando")
        maintenance_mode["target_file"] = filename
        maintenance_mode.pop("last_ok", None)
        maintenance_mode.pop("last_message", None)

        worker = threading.Thread(
            target=_execute_restore_cycle,
            kwargs={
                "filename": filename,
                "ip_address": ip_address,
                "source": source,
                "user_id": getattr(user, "id", None),
                "import_executor": import_executor,
                "security_backup_executor": security_backup_executor,
            },
            name="restore-worker-019",
            daemon=False,
        )
        worker.start()
        return {
            "agendado": True,
            "restaurado": filename,
            "status_url": "/admin/backups/restaurar/status",
        }


def _worker_audit(*, action: str, ip_address: Optional[str], result: str,
                  description: str, resource_ref: Optional[str] = None,
                  new_data: Optional[Dict] = None,
                  user_id: Optional[int] = None) -> None:
    """Evento de auditoria do worker com SESSÃO PRÓPRIA E CURTA (R5/D4).

    O write_audit comita na sessão recebida (audit_service L186) — com sessão
    própria, a transação abre e fecha no ponto de uso: nenhuma conexão do
    worker permanece checked-out durante o import. O ator é recarregado por
    id na sessão do evento (trilha preserva o operador — FR-017).
    """
    db = SessionLocal()
    try:
        actor: Optional[User] = None
        if user_id is not None:
            actor = db.query(User).filter(User.id == user_id).first()
        write_audit(
            db,
            user=actor,
            action=action,
            module="Backup",
            resource="backup",
            resource_ref=resource_ref,
            ip_address=ip_address,
            result=result,
            description=description,
            new_data=new_data,
        )
    finally:
        db.close()


def _execute_restore_cycle(
    filename: str,
    ip_address: Optional[str],
    source: Dict,
    *,
    user_id: Optional[int] = None,
    import_executor: Optional[Callable[[Path, bool], None]] = None,
    security_backup_executor: Optional[Callable[[Path], None]] = None,
) -> None:
    """Worker thread do ciclo destrutivo (019 — contract §1.2).

    Sessões SEMPRE próprias e curtas (nunca a do request). Ordem 017:
    INICIADO → backup de segurança → valida segurança → PRE_RESTORE →
    DRENAGEM DO POOL (FR-003) → import (deadline — US2) → validação pós
    (sessão nova) → SUCCESS/FAILURE. finally SEMPRE libera slot + manutenção
    (FR-009/FR-011/FR-012 — crash-safety).
    """
    global _RESTORE_IN_PROGRESS
    do_import = import_executor or _run_mysql_import
    security_name: Optional[str] = None
    try:
        _worker_audit(
            action=ACTION_BACKUP_RESTORE_STARTED,
            ip_address=ip_address,
            result=RESULT_SUCCESS,
            description="Restauração de backup iniciada.",
            resource_ref=filename,
            new_data={"backup": filename},
            user_id=user_id,
        )

        # Backup de segurança OBRIGATÓRIO (FR-11 017/FR-005) — worker usa
        # sessão própria e bypass da guarda (chamada interna ao ciclo).
        _maintenance_set(True, phase="seguranca")
        db = SessionLocal()
        try:
            actor = (
                db.query(User).filter(User.id == user_id).first()
                if user_id is not None
                else None
            )
            security = BackupService.generate_backup(
                db,
                actor,
                ip_address,
                dump_executor=security_backup_executor,
                _allow_during_restore=True,
                backup_type=BACKUP_TYPE_PRE_RESTAURACAO,  # 020 (BV-3): marca o tipo
            )
        finally:
            db.close()

        security_name = security["filename"]
        BackupService.validate_restore_source(security_name)

        _worker_audit(
            action=ACTION_BACKUP_PRE_RESTORE,
            ip_address=ip_address,
            result=RESULT_SUCCESS,
            description="Backup de segurança pré-restauração criado.",
            resource_ref=security_name,
            new_data={"backup": filename, "backup_seguranca": security_name},
            user_id=user_id,
        )

        # DRENAGEM DO POOL (FR-003/R1): sem conexões vivas do processo web,
        # os DROP/CREATE do dump não encontram metadata lock da própria app.
        _maintenance_set(True, phase="importando")

        if not drain_engine(timeout=30.0):
            raise BackupError(
                "Restauração não concluída: não foi possível drenar as conexões "
                "do sistema para executar a importação com segurança. "
                "O backup de segurança permanece disponível para restauração manual."
            )

        # Import com deadline de relógio (US2 — cobre o write no stdin, D2)
        do_import(source["path"], is_gzip=source["is_gzip"])

        # Validação pós-restore real (017): sessão nova (pool reaberto)
        _maintenance_set(True, phase="verificando")
        db = SessionLocal()
        try:
            BackupService.validate_post_restore(db)
        finally:
            db.close()

        _worker_audit(
            action=ACTION_BACKUP_RESTORE_SUCCESS,
            ip_address=ip_address,
            result=RESULT_SUCCESS,
            description="Backup restaurado com sucesso.",
            resource_ref=filename,
            new_data={"backup": filename, "backup_seguranca": security_name},
            user_id=user_id,
        )
        maintenance_mode["last_ok"] = True
        maintenance_mode["last_message"] = (
            f"Restauração concluída com sucesso. Backup de segurança: {security_name}."
        )
        logger.info("Restauração do backup %s concluída (worker 019).", filename)
    except BackupError as exc:
        description = (
            f"{exc} O backup de segurança permanece disponível para "
            "restauração manual."
            if "backup de segurança" not in str(exc)
            else str(exc)
        )
        _worker_audit(
            action=ACTION_BACKUP_RESTORE_FAILED,
            ip_address=ip_address,
            result=RESULT_FAILURE,
            description=description,
            resource_ref=filename,
            user_id=user_id,
        )
        logger.error("%s", description)
        maintenance_mode["last_ok"] = False
        maintenance_mode["last_message"] = description
    except Exception as exc:  # crash-safety: nenhuma exceção escapa do worker
        description = "Restauração não concluída por erro inesperado."
        logger.exception("Falha inesperada no worker de restauração: %s", exc)
        try:
            _worker_audit(
                action=ACTION_BACKUP_RESTORE_FAILED,
                ip_address=ip_address,
                result=RESULT_FAILURE,
                description=description,
                resource_ref=filename,
                user_id=user_id,
            )
        except Exception:  # pragma: no cover — auditoria nunca quebra o finally
            logger.exception("Falha ao auditar o erro inesperado do restore.")
        maintenance_mode["last_ok"] = False
        maintenance_mode["last_message"] = description
    finally:
        # Liberação GARANTIDA (FR-009/FR-011/FR-012): slot + manutenção
        _maintenance_set(False)
        with _RESTORE_LOCK:
            _RESTORE_IN_PROGRESS = False


# ==========================================================================
# DOWNLOAD (US3 da 015) — valida nome/existência para rota e serviço
# ==========================================================================


def get_backup_path(filename: str) -> Path:
    """Valida o nome e retorna o caminho do backup (contract 015 §1.4).

    Levanta FileNotFoundError (→ 404 na rota) se o nome está fora do
    padrão (path traversal impossível — R8) ou se o arquivo não existe.
    """
    if not _BACKUP_NAME_RE.match(filename):
        raise FileNotFoundError(f"Nome de backup inválido: {filename!r}")

    path = BACKUP_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Backup não encontrado: {filename}")

    return path


BackupService.get_backup_path = staticmethod(get_backup_path)  # API da classe preservada (015/016/017)
