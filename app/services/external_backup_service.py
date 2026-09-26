"""Destino externo para backups — SisPatrimônio Pro (feature 045).

Após cada backup local VÁLIDO (MANUAL/AUTOMATICO/PRE_RESTAURACAO), copia
atomicamente o arquivo para a pasta de rede/NAS configurada, valida a cópia
por existência + tamanho + SHA-256 idêntico ao local e grava o resultado em
`backup_external_records` (um único registro final por filename) + auditoria.

Regras do contrato (specs/045 contract §1):
- Gancho ÚNICO: `process_backup_after_success` é chamado apenas por
  `BackupService.generate_backup` (research R1) — manual, automático
  (scheduler) e pré-restauração são cobertos sem alterar chamadores.
- Falha externa NUNCA propaga exceção nem invalida o local (C-8/R5).
- Cópia ATÔMICA: streaming para `<dest>/.<filename>.tmp` (prefixo ponto —
  nunca parece backup válido), flush+fsync, validação de tamanho+sha256 e
  `os.replace` para o nome final (R3/C-7). Temporário é removido em
  qualquer erro; nome definitivo só existe com cópia completa validada.
- Retry IMEDIATO limitado (R4): tentativas com espera curta e orçamento
  total — constantes de módulo monkeypatcháveis nos testes.
- Idempotência: nome final já existente com hash igual → sucesso (sem
  duplicar); divergente → falha. `filename` UNIQUE garante um único
  registro final por backup (C-16/Teste H).
- Nenhuma rotina varre/exclui o destino (C-12 — sem retenção externa);
  nenhum `mkdir` automático (a pasta montada é infraestrutura); zero
  `shell=True`; zero segredos (não há campo para credencial — C-4).
"""

import hashlib
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.backup_external_config import BackupExternalConfig
from app.models.backup_external_record import BackupExternalRecord
from app.utils.time_utils import now_utc
from app.services.audit_service import (
    ACTION_BACKUP_DESTINO_EXTERNO_CONFIGURADO,
    ACTION_BACKUP_EXTERNO_FALHA,
    ACTION_BACKUP_EXTERNO_SUCESSO,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    write_audit,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Constantes de retry/orçamento (R4) — MÓDULO, monkeypatcháveis nos testes
# ============================================================================

EXTERNAL_COPY_ATTEMPTS = 3          # tentativas por backup
EXTERNAL_RETRY_WAIT_SECONDS = 2     # espera entre tentativas
EXTERNAL_COPY_BUDGET_SECONDS = 120  # orçamento TOTAL (todas as tentativas)

# Tamanho do bloco da cópia/hash streaming (memória constante)
_COPY_CHUNK_SIZE = 1024 * 1024

# Motivos controlados (data-model 045 — nunca segredos)
REASON_DESTINO_INDISPONIVEL = "destino indisponível"
REASON_SEM_PERMISSAO = "sem permissão de escrita"
REASON_SEM_ESPACO = "espaço insuficiente no destino"
REASON_INTEGRIDADE = "falha de integridade (sha256 divergente)"
REASON_TIMEOUT = "tempo limite da cópia"


def _validate_dest_path(dest_path: str) -> Optional[str]:
    """Valida o caminho configurado (R3.1): retorna motivo ou None se ok.

    - Não vazio; absoluta (caminho relativo não é destino confiável);
    - sem caracteres de controle (defesa contra lixo/segredos de terminal);
    - sem execução de shell (a cópia é 100% stdlib/pathlib — C-4/C-14).
    """
    if not dest_path or not dest_path.strip():
        return REASON_DESTINO_INDISPONIVEL
    candidate = Path(dest_path.strip())
    if not candidate.is_absolute():
        return REASON_DESTINO_INDISPONIVEL
    if any(ord(ch) < 32 for ch in dest_path):
        return REASON_DESTINO_INDISPONIVEL
    return None


def _sha256_of(path: Path, *, deadline: Optional[float] = None) -> str:
    """SHA-256 streaming do arquivo (exceção de orçamento propaga ao chamador)."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(_COPY_CHUNK_SIZE)
            if not chunk:
                break
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError()
            digest.update(chunk)
    return digest.hexdigest()


def copy_backup_to_external(
    filename: str,
    sha256_local: str,
    size_local: int,
    dest_path: str,
) -> Dict:
    """Copia e valida UM arquivo para o destino (R3 — contract §1).

    Fluxo: validar caminho → espaço (quando verificável) → destino existente →
    idempotência (nome final existente) → tmp oculto + fsync → validar
    tamanho+sha256 → `os.replace` → limpar tmp em qualquer erro.

    Levanta exceções controladas internamente e as traduz em
    `{"ok": bool, "reason": str|None}` — o chamador decide registro/auditoria.
    O orçamento total (`EXTERNAL_COPY_BUDGET_SECONDS`) cobre a tentativa.
    """
    started = time.monotonic()
    deadline = started + EXTERNAL_COPY_BUDGET_SECONDS

    # 1) Caminho validado (absoluto, sem controle, sem shell)
    invalid_reason = _validate_dest_path(dest_path)
    if invalid_reason:
        return {"ok": False, "reason": invalid_reason}
    dest = Path(dest_path.strip())

    # 2) Destino precisa EXISTIR como diretório — nunca mkdir automático
    if not dest.is_dir():
        return {"ok": False, "reason": REASON_DESTINO_INDISPONIVEL}

    # 3) Espaço quando tecnicamente verificável (§31)
    try:
        free = shutil.disk_usage(dest).free
        if size_local is not None and size_local > 0 and free < size_local:
            return {"ok": False, "reason": REASON_SEM_ESPACO}
    except OSError:
        pass  # verificação indisponível → segue (validação real é a cópia)

    local_path = None
    final_path = dest / filename
    tmp_path = dest / f".{filename}.tmp"

    try:
        # 4) Idempotência: nome final já existe → hash decide (sem duplicar)
        if final_path.exists():
            try:
                existing_sha = _sha256_of(final_path, deadline=deadline)
            except TimeoutError:
                return {"ok": False, "reason": REASON_TIMEOUT}
            if existing_sha == sha256_local:
                return {"ok": True, "reason": None}
            return {"ok": False, "reason": REASON_INTEGRIDADE}

        # 5) Arquivo local válido é pré-condição do gancho (só SUCCESS local)
        from app.config import BACKUP_DIR
        from app.services.backup_service import get_backup_path

        local_path = get_backup_path(filename)  # valida padrão + existência
        if local_path.parent != BACKUP_DIR:  # pragma: no cover — defensivo
            return {"ok": False, "reason": REASON_DESTINO_INDISPONIVEL}

        # 6) Cópia streaming para o temporário OCULTO + flush + fsync
        try:
            with open(local_path, "rb") as src, open(tmp_path, "wb") as dst:
                while True:
                    chunk = src.read(_COPY_CHUNK_SIZE)
                    if not chunk:
                        break
                    if time.monotonic() > deadline:
                        raise TimeoutError()
                    dst.write(chunk)
                dst.flush()
                os.fsync(dst.fileno())
        except PermissionError:
            return {"ok": False, "reason": REASON_SEM_PERMISSAO}
        except TimeoutError:
            return {"ok": False, "reason": REASON_TIMEOUT}

        # 7) Validação do temporário: tamanho + sha256 idênticos ao local
        try:
            copied_size = tmp_path.stat().st_size
        except OSError:
            return {"ok": False, "reason": REASON_DESTINO_INDISPONIVEL}
        if size_local is not None and copied_size != size_local:
            return {"ok": False, "reason": REASON_INTEGRIDADE}
        try:
            copied_sha = _sha256_of(tmp_path, deadline=deadline)
        except TimeoutError:
            return {"ok": False, "reason": REASON_TIMEOUT}
        if copied_sha != sha256_local:
            return {"ok": False, "reason": REASON_INTEGRIDADE}

        # 8) Publicação atômica no mesmo filesystem
        try:
            os.replace(tmp_path, final_path)
        except PermissionError:
            return {"ok": False, "reason": REASON_SEM_PERMISSAO}
        except OSError:
            return {"ok": False, "reason": REASON_DESTINO_INDISPONIVEL}

        return {"ok": True, "reason": None}
    finally:
        # 9) Temporário NUNCA permanece (nenhum parcial visível — C-7)
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            logger.error(
                "Falha ao remover temporário de cópia externa %s.", tmp_path.name
            )


def get_external_config(db: Session) -> BackupExternalConfig:
    """Retorna a linha singleton id=1, criando-a (lazy) se ausente.

    Default: `enabled=False` (FR-004/SC-001 — comportamento atual
    preservado). Segue o padrão `get_backup_config` da 021.
    """
    settings = (
        db.query(BackupExternalConfig)
        .filter(BackupExternalConfig.id == 1)
        .first()
    )
    if settings is None:
        settings = BackupExternalConfig(
            id=1, enabled=False, dest_type="PASTA_REDE", dest_path=None
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def save_external_config(
    db: Session,
    *,
    enabled: bool,
    dest_path: Optional[str],
    updated_by: Optional[str],
) -> BackupExternalConfig:
    """Persiste a configuração do destino externo (singleton id=1).

    Audita `BACKUP_DESTINO_EXTERNO_CONFIGURADO` quando a configuração é
    alterada (contract §3). Nenhum campo contém segredo (C-4).
    """
    row = get_external_config(db)
    before = {"enabled": bool(row.enabled), "dest_path": row.dest_path}
    after = {
        "enabled": bool(enabled),
        "dest_path": (dest_path or "").strip() or None,
    }
    row.enabled = after["enabled"]
    row.dest_path = after["dest_path"]
    row.dest_type = "PASTA_REDE"
    row.updated_by = updated_by
    db.commit()
    db.refresh(row)

    if before != after:
        try:
            write_audit(
                db,
                user=None,
                username=updated_by,
                action=ACTION_BACKUP_DESTINO_EXTERNO_CONFIGURADO,
                module="Backup",
                resource="backup_external_config",
                resource_ref="1",
                result=RESULT_SUCCESS,
                description="Configuração do destino externo de backup salva.",
                new_data={
                    "enabled": after["enabled"],
                    "dest_path": after["dest_path"],
                    "updated_by": updated_by,
                },
            )
        except Exception:  # auditoria nunca quebra a configuração
            logger.exception("Falha ao auditar configuração do destino externo.")
    return row


def test_destination(path: str) -> tuple:
    """Testa o destino informado SEM gerar backup (§24/R8).

    Passos: configurado/não vazio → existe e é diretório → cria arquivo
    temporário oculto → escreve → lê de volta → remove. Retorna
    `(ok, mensagem_controlada)`; a mensagem nunca contém segredo.
    """
    invalid_reason = _validate_dest_path(path)
    if invalid_reason:
        return False, "Informe um caminho absoluto válido para o destino."

    dest = Path(path.strip())
    if not dest.is_dir():
        return False, "O destino informado não existe ou não é um diretório."

    probe = dest / ".backup_externo_teste.tmp"
    payload = b"teste-destino-externo-045"
    try:
        with open(probe, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        with open(probe, "rb") as f:
            if f.read() != payload:
                return False, "O destino não devolveu o conteúdo gravado."
        return True, "Destino acessível: escrita, leitura e remoção OK."
    except PermissionError:
        return False, "Sem permissão de escrita no destino."
    except OSError:
        return False, "O destino não aceitou a operação de teste."
    finally:
        try:
            if probe.exists():
                probe.unlink()
        except OSError:
            logger.error("Falha ao remover arquivo de teste do destino.")


def process_backup_after_success(result: Dict, backup_type: str) -> Optional[Dict]:
    """Gancho ÚNICO pós-`_record_backup_success` (R1 — contract §1).

    - Config desabilitada ou sem `dest_path` → None (no-op, ZERO I/O externo
      e ZERO eventos — Testes A/B/L);
    - Habilitada → cópia com retry/espera/orçamento (R4), **um único**
      `BackupExternalRecord` final por filename (sessão própria e curta —
      padrão `_worker_audit`/020) + evento `BACKUP_EXTERNO_SUCESSO|FALHA`;
    - **NUNCA propaga exceção** (C-8): qualquer erro inesperado vira falha
      externa registrada (e log técnico);
    - Retorna `{"external_status": "SUCCESS"|"FAILURE", "external_reason": ...}`
      para composição do flash da tela.
    """
    filename = None
    try:
        filename = (result or {}).get("filename")
        sha256_local = (result or {}).get("sha256")
        size_local = (result or {}).get("size_bytes")
        if not filename:
            return None

        # Leitura da configuração em sessão própria e curta
        db = SessionLocal()
        try:
            config = get_external_config(db)
            enabled = bool(config.enabled)
            dest_path = config.dest_path
        finally:
            db.close()

        if not enabled or not (dest_path and dest_path.strip()):
            return None  # no-op: zero I/O no destino, zero eventos

        # Retry imediato limitado (R4): tentativas com espera curta e
        # orçamento TOTAL verificado dentro da cópia (por chunk/hash).
        process_started = time.monotonic()
        attempts = max(1, int(EXTERNAL_COPY_ATTEMPTS))
        copied: Optional[Dict] = None
        for attempt in range(1, attempts + 1):
            try:
                copied = copy_backup_to_external(
                    filename, sha256_local, size_local, dest_path
                )
            except Exception as exc:  # qualquer erro é falha externa (C-8)
                logger.error(
                    "Cópia externa de %s falhou (tentativa %d/%d, tipo=%s): %s",
                    filename,
                    attempt,
                    attempts,
                    backup_type,
                    type(exc).__name__,
                )
                copied = {"ok": False, "reason": REASON_DESTINO_INDISPONIVEL}
            if copied and copied.get("ok"):
                break
            if (
                attempt < attempts
                and (time.monotonic() - process_started)
                < EXTERNAL_COPY_BUDGET_SECONDS
            ):
                time.sleep(EXTERNAL_RETRY_WAIT_SECONDS)

        ok = bool(copied and copied.get("ok"))
        reason = None if ok else (copied or {}).get("reason") or REASON_DESTINO_INDISPONIVEL

        # Registro FINAL único (filename UNIQUE) + auditoria — sessão própria
        db = SessionLocal()
        try:
            record = (
                db.query(BackupExternalRecord)
                .filter(BackupExternalRecord.filename == filename)
                .first()
            )
            if record is None:
                record = BackupExternalRecord(filename=filename)
                db.add(record)
            # Uma única escrita ao fim do ciclo: resultado final (C-16).
            # copied_at é regenerado a cada nova tentativa de ciclo — o
            # registro SEMPRE reflete o último resultado.
            record.backup_type = backup_type
            record.status = "SUCCESS" if ok else "FAILURE"
            record.size_bytes = size_local if ok else None
            record.sha256 = sha256_local if ok else None
            record.error_description = reason
            record.copied_at = now_utc()
            db.commit()

            try:
                write_audit(
                    db,
                    user=None,  # ator sistema (cópia é pós-fluxo do backup)
                    action=ACTION_BACKUP_EXTERNO_SUCESSO if ok else ACTION_BACKUP_EXTERNO_FALHA,
                    module="Backup",
                    resource="backup_externo",
                    resource_ref=filename,
                    result=RESULT_SUCCESS if ok else RESULT_FAILURE,
                    description=(
                        f"Cópia externa validada ({backup_type})."
                        if ok
                        else f"Cópia externa falhou ({backup_type}): {reason}."
                    ),
                    new_data={
                        "arquivo": filename,
                        "backup_type": backup_type,
                        "destino": dest_path,
                        **(
                            {}
                            if ok
                            else {"motivo": reason}
                        ),
                    },
                )
            except Exception:  # auditoria nunca quebra o fluxo
                logger.exception("Falha ao auditar resultado externo de %s.", filename)
        finally:
            db.close()

        return {"external_status": "SUCCESS" if ok else "FAILURE",
                "external_reason": reason}
    except Exception:  # à prova de exceção (C-8) — nunca afeta o local
        logger.exception(
            "Processamento pós-sucesso do destino externo falhou para %s.",
            filename,
        )
        return {"external_status": "FAILURE", "external_reason": REASON_DESTINO_INDISPONIVEL}
