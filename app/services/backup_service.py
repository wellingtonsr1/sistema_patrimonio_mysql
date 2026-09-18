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

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse, unquote

from app.config import BACKUP_DIR, DATABASE_URL
from app.models.user import User
from app.services.audit_service import (
    ACTION_BACKUP_CREATED,
    ACTION_BACKUP_DOWNLOAD,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    write_audit,
)
from sqlalchemy.orm import Session

# Padrão estrito do nome de backup (data-model §1):
# backup_YYYYMMDD_HHMMSS_micros.sql — âncora de reconhecimento e de
# proteção contra path traversal (qualquer nome fora disso é rejeitado
# antes de tocar o disco).
_BACKUP_NAME_RE = re.compile(r"^backup_(\d{8})_(\d{6})_(\d{6})\.sql$")

_DUMP_TIMEOUT_SECONDS = 600


def _timestamp_suffix() -> str:
    """Sufixo do nome: UTC com microssegundos (remediação I1)."""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")


def _filename_to_datetime(filename: str) -> datetime:
    """Converte o timestamp do nome (UTC) em datetime para a listagem."""
    match = _BACKUP_NAME_RE.match(filename)
    if not match:
        raise ValueError(f"Nome de backup fora do padrão: {filename!r}")
    date_part, time_part, micro_part = match.groups()
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

        filename = f"backup_{_timestamp_suffix()}.sql"
        path = BACKUP_DIR / filename

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        try:
            executor(path)

            size_bytes = path.stat().st_size if path.exists() else 0
            if size_bytes <= 0:
                raise BackupError("O arquivo de backup gerado está vazio.")

            write_audit(
                db,
                user=user,
                action=ACTION_BACKUP_CREATED,
                module="Backup",
                resource="backup",
                resource_ref=filename,
                ip_address=ip_address,
                result=RESULT_SUCCESS,
                description="Backup manual gerado com sucesso.",
                new_data={"arquivo": filename, "tamanho_bytes": size_bytes},
            )
            return {
                "filename": filename,
                "timestamp": _filename_to_datetime(filename),
                "size_bytes": size_bytes,
            }
        except Exception as exc:
            # Remove artefato parcial (BV-4): apenas arquivos com o padrão de nome
            if path.exists():
                try:
                    path.unlink()
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
                action=ACTION_BACKUP_CREATED,
                module="Backup",
                resource="backup",
                resource_ref=filename,
                ip_address=ip_address,
                result=RESULT_FAILURE,
                description=description,
            )
            raise BackupError(description) from exc

    # =========================================================================
    # LISTAGEM (US2)
    # =========================================================================

    @staticmethod
    def list_backups() -> List[Dict]:
        """Lista os backups disponíveis (contract §1.3, research R7).

        Considera apenas arquivos com o padrão de nome; ordena do mais
        recente para o mais antigo. Diretório inexistente → [].
        """
        if not BACKUP_DIR.exists():
            return []

        backups: List[Dict] = []
        for entry in BACKUP_DIR.iterdir():
            if not entry.is_file() or not _BACKUP_NAME_RE.match(entry.name):
                continue  # artefatos alheios são ignorados
            backups.append(
                {
                    "filename": entry.name,
                    "timestamp": _filename_to_datetime(entry.name),
                    "size_bytes": entry.stat().st_size,
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
