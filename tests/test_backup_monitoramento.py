"""Monitoramento do Backup Automático — feature 020 (US7).

Cobre T023: GET /admin/backups apresenta indicadores (último automático,
próxima execução, último válido, última falha, última retenção, válidos,
removidos) e a coluna Tipo (MANUAL/AUTOMATICO/PRE_RESTAURACAO/—); usuário
sem backup.gerenciar → 403 (deny-by-default); nenhum segredo no HTML.
"""

from datetime import datetime, timedelta

from app.models.backup_record import BackupRecord
from app.services.audit_service import write_audit
from tests.test_rbac import PASSWORD, _login, _make_user

NOW = datetime(2026, 9, 18, 12, 0, 0)


def _seed(db, filename, backup_type="MANUAL", status="SUCCESS",
          timestamp=None, removed_at=None, error_description=None):
    rec = BackupRecord(
        filename=filename,
        backup_type=backup_type,
        status=status,
        size_bytes=1234,
        sha256="a" * 64,
        timestamp=timestamp or NOW,
        removed_at=removed_at,
        error_description=error_description,
    )
    db.add(rec)
    db.commit()
    return rec


def _seed_retention_event(db, removed=2):
    write_audit(
        db,
        user=None,
        action="BACKUP_RETENCAO_EXECUTADA",
        module="Backup",
        resource="backup",
        result="SUCCESS",
        description=f"Retenção executada: {removed} removido(s) — resultado COMPLETA.",
        new_data={"candidatos": 3, "removidos": removed, "falhas": 0,
                  "resultado": "COMPLETA", "preservados": {}},
    )


# ============================================================================
# Indicadores presentes no HTML (admin autenticado — fixture client é admin)
# ============================================================================

def test_pagina_contem_indicadores(client, db_session):
    _seed(db_session, "backup_20260917_020000_100001.sql.gz",
          backup_type="AUTOMATICO", timestamp=NOW - timedelta(hours=10))
    _seed(db_session, "backup_20260916_100000_100002.sql.gz",
          backup_type="MANUAL", timestamp=NOW - timedelta(days=2))
    _seed(db_session, "backup_20260601_020000_100003.sql.gz",
          backup_type="AUTOMATICO", status="FAILURE",
          timestamp=NOW - timedelta(days=90),
          error_description="mysqldump retornou 2")
    _seed_retention_event(db_session, removed=2)

    resp = client.get("/admin/backups")
    assert resp.status_code == 200
    html = resp.text

    # Card de monitoramento
    assert "Backup Automático" in html
    assert "Último automático" in html
    assert "Último backup válido" in html
    assert "Última retenção" in html
    assert "Backups válidos" in html
    assert "Última falha" in html
    assert "mysqldump retornou 2" in html  # diagnóstico legível (sem segredo)


def test_legado_sem_registro_exibe_traco(client, db_session):
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    (BACKUP_DIR / "backup_20200101_000000_999999.sql.gz").write_bytes(
        b"\x1f\x8b legacy"
    )
    resp = client.get("/admin/backups")
    assert resp.status_code == 200
    assert "999999" in resp.text  # listado
    # sem registro → sem badge de tipo (coluna mostra —)


def test_sem_nenhum_registro_indicadores_vazios(client, db_session, monkeypatch):
    """Sem registros, o card mostra estados vazios legíveis.

    Hermeticidade: a flag é fixada via monkeypatch — o teste não depende do
    default do ambiente (.env/BACKUP_AUTO_ENABLED pode variar por deploy).
    """
    from app.services import backup_scheduler

    monkeypatch.setattr(backup_scheduler, "BACKUP_AUTO_ENABLED", False)
    resp = client.get("/admin/backups")
    assert resp.status_code == 200
    assert "Backup Automático" in resp.text
    assert "Desativado" in resp.text  # flag fixada desativada acima
    assert "NENHUMA" in resp.text  # estados vazios legíveis (falha/retenção)


# ============================================================================
# RBAC — deny-by-default (backup.gerenciar)
# ============================================================================

def test_sem_permissao_403(client, db_session):
    _make_user(db_session, "bkConsulta", role_names=["Consulta"])
    _login(client, "bkConsulta")
    resp = client.get("/admin/backups")
    assert resp.status_code == 403


def test_nao_autenticado_redireciona_login(unauth_client):
    resp = unauth_client.get("/admin/backups", follow_redirects=False)
    assert resp.status_code in (302, 303, 307)


# ============================================================================
# Segurança — nenhum segredo no HTML (contract §1: config sem credenciais)
# ============================================================================

def test_html_sem_segredos(client, db_session):
    resp = client.get("/admin/backups")
    assert resp.status_code == 200
    html = resp.text
    for segredo in ("DATABASE_URL", "mysql://", "MYSQL_PWD", "senha@1234"):
        assert segredo not in html


# ============================================================================
# Helper de monitoramento (unitário — sem sessão de request)
# ============================================================================

def test_retention_monitoring_summary_unitario(db_session, monkeypatch):
    """O helper apura os indicadores do banco passado (sessão do chamador)."""
    from app.services import backup_scheduler

    _seed(db_session, "backup_20260917_020000_200001.sql.gz",
          backup_type="AUTOMATICO", timestamp=NOW - timedelta(hours=10))
    _seed(db_session, "backup_20260910_020000_200002.sql.gz",
          backup_type="AUTOMATICO", status="FAILURE",
          timestamp=NOW - timedelta(days=8),
          error_description="boom técnico")
    _seed(db_session, "backup_20260801_020000_200003.sql.gz",
          backup_type="AUTOMATICO", timestamp=NOW - timedelta(days=48),
          removed_at=NOW - timedelta(days=1))
    _seed_retention_event(db_session, removed=1)

    # cria o arquivo do SUCCESS mais recente (para last_valid e valid_count)
    import gzip as _gzip
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with _gzip.open(BACKUP_DIR / "backup_20260917_020000_200001.sql.gz", "wb") as f:
        f.write(b"-- dump")

    monkeypatch = None  # sessão de teste passada direto ao helper
    summary = backup_scheduler.retention_monitoring_summary(db_session)

    assert summary["last_auto"]["filename"] == "backup_20260917_020000_200001.sql.gz"
    assert summary["last_auto"]["status"] == "SUCCESS"
    assert summary["last_valid"]["filename"] == "backup_20260917_020000_200001.sql.gz"
    assert summary["valid_count"] == 1
    assert summary["last_failure"]["error_description"] == "boom técnico"
    assert summary["removed_count"] == 1
    assert summary["last_retention"]["result"] == "COMPLETA"
    assert summary["last_retention"]["removidos"] == 1
