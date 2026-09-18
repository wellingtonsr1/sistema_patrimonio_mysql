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
import re
import subprocess
import time
import zlib
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse, unquote

from app.config import BACKUP_DIR, DATABASE_URL
from app.models.user import User
from app.services.audit_service import (
    ACTION_BACKUP_CREATED,
    ACTION_BACKUP_DOWNLOAD,
    ACTION_BACKUP_FAILED,
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

# Log técnico do módulo (feature 016, briefing §26): usa o handler rotativo
# existente; nunca registra credenciais, DATABASE_URL ou o comando completo.
logger = logging.getLogger(__name__)

# Compressão/leitura em blocos de 1 MB — memória constante (research R2/R4)
_CHUNK_SIZE = 1024 * 1024


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

    env = {"MYSQL_PWD": password, "PATH": "/usr/local/bin:/usr/bin:/bin"}

    try:
        with open(path, "wb") as out:
            subprocess.run(
                [
                    "mysqldump",
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
    except subprocess.CalledProcessError:
        # stderr pode conter o comando — NUNCA propagar (Princípio VI)
        raise BackupError("O utilitário de dump retornou erro.")
    except subprocess.TimeoutExpired:
        raise BackupError("O utilitário de dump excedeu o tempo limite.")


class BackupError(Exception):
    """Falha controlada de backup (mensagem segura para o usuário/auditoria)."""


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
