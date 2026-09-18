"""Metadados de backup (BackupRecord) — feature 020, fundação (T006).

Cobertura:
- Geração manual (executor fake — padrão 015) grava BackupRecord
  MANUAL/SUCCESS com size/sha256;
- Falha injetada grava FAILURE com error_description e SEM size/sha256,
  com filename = nome FINAL projetado `{base}.sql.gz` casando com
  `_BACKUP_NAME_RE` (C1);
- `backup_type` inválido → ValueError SEM executor chamado;
- Falha no cleanup de `.part*` (OSError simulado) → log técnico do leftover
  sem propagar exceção (F5);
- `init_db`/create_all cria `backup_records` sem tocar tabelas existentes (BV-1);
- filename UNIQUE impede registro duplicado (BV-4).

O executor de dump é sempre FAKE na suíte (SQLite não roda mysqldump — R4).
"""

import re

import pytest

from app.models.backup_record import BackupRecord
from app.services import backup_service
from app.services.backup_service import BackupService

_BACKUP_NAME_RE = re.compile(r"^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$")
FAKE_DUMP_CONTENT = b"-- SisPatrimonio Pro fake dump (020)\n"


@pytest.fixture(autouse=True)
def _clean_backup_dir():
    """Remove artefatos gerados pelos testes (mesmo padrão da 015/016)."""
    from app.config import BACKUP_DIR

    if BACKUP_DIR.exists():
        for p in BACKUP_DIR.iterdir():
            if _BACKUP_NAME_RE.match(p.name) or ".part" in p.name:
                if p.is_file():
                    p.unlink()
    yield
    if BACKUP_DIR.exists():
        for p in BACKUP_DIR.iterdir():
            if _BACKUP_NAME_RE.match(p.name) or ".part" in p.name:
                if p.is_file():
                    p.unlink()


def _fake_dump(path):
    with open(path, "wb") as f:
        f.write(FAKE_DUMP_CONTENT)


def _failing_dump(path):
    raise RuntimeError("dump falhou (simulado)")


# ============================================================================
# SUCCESS
# ============================================================================

def test_manual_backup_grava_registro_success(db_session):
    """Geração manual (fluxo existente) grava MANUAL/SUCCESS com size/sha256."""
    result = BackupService.generate_backup(db_session, None, None, dump_executor=_fake_dump)

    assert result["filename"].endswith(".sql.gz")
    assert _BACKUP_NAME_RE.match(result["filename"])

    record = (
        db_session.query(BackupRecord)
        .filter(BackupRecord.filename == result["filename"])
        .one()
    )
    assert record.backup_type == "MANUAL"
    assert record.status == "SUCCESS"
    assert record.size_bytes == result["size_bytes"]
    assert record.sha256 == result["sha256"]
    assert record.error_description is None
    assert record.removed_at is None  # só a retenção preenche
    assert record.timestamp is not None


# ============================================================================
# FAILURE (C1 — filename projetado casa com a regex)
# ============================================================================

def test_falha_grava_registro_failure_com_nome_final_projetado(db_session):
    """Falha injetada grava FAILURE: sem size/sha256, filename casa a regex (C1)."""
    with pytest.raises(backup_service.BackupError):
        BackupService.generate_backup(db_session, None, None, dump_executor=_failing_dump)

    records = db_session.query(BackupRecord).filter(BackupRecord.status == "FAILURE").all()
    assert len(records) == 1

    record = records[0]
    assert record.backup_type == "MANUAL"
    # C1: nome FINAL projetado — casa com a regex do serviço
    assert _BACKUP_NAME_RE.match(record.filename)
    assert record.filename.endswith(".sql.gz")
    assert record.size_bytes is None
    assert record.sha256 is None
    assert record.error_description  # descrição controlada, sem segredos
    assert "senha" not in (record.error_description or "").lower()


# ============================================================================
# VALIDAÇÃO DE TIPO (contract §3)
# ============================================================================

def test_backup_type_invalido_value_error_sem_executor(db_session):
    """Valor fora do vocabulário → ValueError ANTES de qualquer dump."""
    calls = []

    def _spy_dump(path):
        calls.append(path)

    with pytest.raises(ValueError, match="Tipo de backup inválido"):
        BackupService.generate_backup(
            db_session,
            None,
            None,
            dump_executor=_spy_dump,
            backup_type="TIPO_MALUCO",
        )

    assert calls == []  # executor NUNCA chamado
    assert db_session.query(BackupRecord).count() == 0


def test_tipos_validos_aceitos(db_session):
    """Os 3 valores do vocabulário são aceitos na assinatura."""
    for tipo in ("MANUAL", "AUTOMATICO", "PRE_RESTAURACAO"):
        result = BackupService.generate_backup(
            db_session, None, None, dump_executor=_fake_dump, backup_type=tipo
        )
        record = (
            db_session.query(BackupRecord)
            .filter(BackupRecord.filename == result["filename"])
            .one()
        )
        assert record.backup_type == tipo


def test_default_e_manual_retrocompativel(db_session):
    """Chamadores existentes (sem backup_type) continuam gravando MANUAL (BV-2)."""
    result = BackupService.generate_backup(db_session, None, None, dump_executor=_fake_dump)
    record = (
        db_session.query(BackupRecord)
        .filter(BackupRecord.filename == result["filename"])
        .one()
    )
    assert record.backup_type == "MANUAL"


# ============================================================================
# F5 — cleanup de .part* com OSError é registrado, não propagado
# ============================================================================

def test_falha_cleanup_part_registrada_no_log(db_session, monkeypatch, caplog):
    """OSError no unlink do .part → log técnico, sem propagar (F5)."""
    real_unlink = __import__("pathlib").Path.unlink

    def _unlink_fails(self, missing_ok=False):
        if ".part" in str(self):
            raise OSError(13, "Permission denied (simulado)")
        return real_unlink(self, missing_ok=missing_ok)

    def _dump_cria_part_e_falha(path):
        """Simula mysqldump interrompido: cria o .part e depois falha."""
        with open(path, "wb") as f:
            f.write(b"-- dump parcial\n")
        raise RuntimeError("dump interrompido (simulado)")

    monkeypatch.setattr("pathlib.Path.unlink", _unlink_fails)

    with pytest.raises(backup_service.BackupError):
        BackupService.generate_backup(
            db_session, None, None, dump_executor=_dump_cria_part_e_falha
        )

    leftover_logs = [r for r in caplog.records if "artefato parcial" in r.getMessage()]
    assert leftover_logs, "Falha de remoção do .part deveria ser registrada (F5)"


# ============================================================================
# BV-1 — create_all cria a tabela nova sem tocar as existentes
# ============================================================================

def test_backup_records_criada_sem_tocar_tabelas_existentes(db_session):
    """BV-1: tabela existe (criada pelo create_all do conftest) e as demais seguem intactas."""
    from sqlalchemy import inspect

    inspector = inspect(db_session.bind)
    tables = set(inspector.get_table_names())
    assert "backup_records" in tables
    # Tabelas essenciais da aplicação continuam presentes
    for essential in ("users", "audit_logs", "assets", "locations"):
        assert essential in tables


# ============================================================================
# BV-4 — UNIQUE de filename impede registro duplicado
# ============================================================================

def test_filename_unique_impede_duplicado(db_session):
    db_session.add(
        BackupRecord(
            filename="backup_20260918_000000_000001.sql.gz",
            backup_type="MANUAL",
            status="SUCCESS",
        )
    )
    db_session.commit()
    db_session.add(
        BackupRecord(
            filename="backup_20260918_000000_000001.sql.gz",
            backup_type="MANUAL",
            status="SUCCESS",
        )
    )
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()
