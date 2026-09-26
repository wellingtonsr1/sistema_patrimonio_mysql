"""Testes da Central de Integrações — Saúde do Sistema (feature 047).

Cobrem os cenários A–I/L do quickstart: catálogo ampliado (10 componentes),
derivação de status por fonte existente, regras do clarify (backup local por
ciclo do agendador; armazenamento por capacidade do último backup válido),
consulta ≠ teste (0 chamadas caras no GET), isolamento por card e RBAC.

Fakes/monkeypatch apenas — nenhum serviço externo real (F10/032).
"""
from datetime import timedelta
from pathlib import Path

from app import config
from app.models.backup_external_config import BackupExternalConfig
from app.models.backup_external_record import BackupExternalRecord
from app.models.backup_record import BackupRecord
from app.services import integration_center_service as ics
from app.services import backup_scheduler
from app.utils.time_utils import now_utc


# ---------------------------------------------------------------------------
# Helpers de seed
# ---------------------------------------------------------------------------

def _mk_backup_record(db, *, status="SUCCESS", size=None, age_min=30,
                      removed=False, backup_type="AUTOMATICO", filename=None):
    rec = BackupRecord(
        filename=filename or f"backup_20260926_{120000 + age_min:06d}_{abs(hash((status, age_min))) % 1000000:06d}.sql.gz",
        backup_type=backup_type,
        status=status,
        timestamp=now_utc() - timedelta(minutes=age_min),
        size_bytes=size,
        error_description=None if status == "SUCCESS" else "falha simulada",
        removed_at=(now_utc() if removed else None),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def _materialize_backup_file(filename: str) -> Path:
    """Cria o arquivo físico no BACKUP_DIR (padrão test_backup_monitoramento):
    o resumo da 020 só considera válidos backups presentes no disco."""
    import gzip
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / filename
    with gzip.open(path, "wb") as f:
        f.write(b"-- dump 047")
    return path


def _mk_external(db, *, enabled=True, dest="/tmp/dest-047", status="SUCCESS",
                 age_min=20, filename=None):
    cfg = db.query(BackupExternalConfig).filter(BackupExternalConfig.id == 1).first()
    if cfg is None:
        cfg = BackupExternalConfig(id=1)
        db.add(cfg)
    cfg.enabled = enabled
    cfg.dest_path = dest
    rec = None
    if status is not None:
        rec = BackupExternalRecord(
            filename=filename or f"ext_{status.lower()}_{age_min}.sql.gz",
            backup_type="AUTOMATICO",
            status=status,
            copied_at=now_utc() - timedelta(minutes=age_min),
            error_description=None if status == "SUCCESS" else "destino indisponivel",
        )
        db.add(rec)
    db.commit()
    return cfg, rec


# ---------------------------------------------------------------------------
# Cenário A — painel com 10 componentes (US1)
# ---------------------------------------------------------------------------

def test_painel_renderiza_10_cards_na_ordem(client):
    resp = client.get("/admin/integracoes")
    assert resp.status_code == 200
    body = resp.text
    ordem = ["Aplicação", "Banco de Dados", "Armazenamento", "Active Directory",
             "E-mail", "GLPI", "Backup Local", "Backup Externo",
             "Agendador de Backup", "1Doc"]
    pos = [body.find(n) for n in ordem]
    assert all(p >= 0 for p in pos), "card ausente no painel"
    assert pos == sorted(pos), "ordem dos cards difere do catálogo"


def test_catalogo_tem_10_chaves_e_labels():
    keys = [i["key"] for i in ics.INTEGRATIONS]
    assert keys == ["app", "database", "storage", "ad", "email", "glpi",
                    "backup_local", "backup_externo", "scheduler", "onedoc"]
    app_item = ics.get_integration("app")
    assert app_item["label_by_status"][ics.STATUS_ATIVA] == "Operacional"
    assert ics.get_integration("backup_externo")["test_label"] == "Testar destino"


# ---------------------------------------------------------------------------
# Cenário B — banco de dados (US1)
# ---------------------------------------------------------------------------

def test_database_status_conectado(db_session):
    r = ics._database_status_fn(db_session)
    assert r["status"] == ics.STATUS_ATIVA
    assert any(v and "OK" in str(v) for _, v in r["detail"].get("summary", []))


def test_database_status_falha(monkeypatch, db_session):
    from sqlalchemy.engine.base import Connection

    def boom(self, *a, **k):
        raise RuntimeError("db fora do ar")

    monkeypatch.setattr(Connection, "execute", boom)
    r = ics._database_status_fn(db_session)
    assert r["status"] == ics.STATUS_COM_ERRO


# ---------------------------------------------------------------------------
# Cenário C/D — GLPI e 1Doc honestos (US1)
# ---------------------------------------------------------------------------

def test_glpi_nao_configurada_e_onedoc_pendente(db_session):
    assert ics._glpi_status_fn(db_session)["status"] == ics.STATUS_NAO_CONFIGURADA
    r1d = ics._onedoc_status_fn(db_session)
    assert r1d["status"] in (ics.STATUS_PENDENTE, ics.STATUS_INATIVA)


# ---------------------------------------------------------------------------
# Cenário E/F — backup externo (US1)
# ---------------------------------------------------------------------------

def test_backup_externo_ok_com_copia_sucesso(db_session):
    _mk_external(db_session, enabled=True, status="SUCCESS")
    r = ics._backup_externo_status_fn(db_session)
    assert r["status"] == ics.STATUS_ATIVA


def test_backup_externo_com_erro_por_ultima_copia_falha(db_session):
    _mk_external(db_session, enabled=True, status="FAILURE")
    r = ics._backup_externo_status_fn(db_session)
    assert r["status"] == ics.STATUS_COM_ERRO


def test_backup_externo_desabilitado_e_nao_configurado(db_session):
    _mk_external(db_session, enabled=False, status=None)
    assert ics._backup_externo_status_fn(db_session)["status"] == ics.STATUS_DESABILITADA
    cfg = db_session.query(BackupExternalConfig).filter(BackupExternalConfig.id == 1).first()
    db_session.delete(cfg)
    db_session.commit()
    assert ics._backup_externo_status_fn(db_session)["status"] == ics.STATUS_NAO_CONFIGURADA


# ---------------------------------------------------------------------------
# Cenário I — agendador (US1)
# ---------------------------------------------------------------------------

def test_scheduler_ativo_e_desabilitado(db_session, monkeypatch):
    monkeypatch.setattr(backup_scheduler, "scheduler_status",
                        lambda: {"enabled": True, "schedule": "daily",
                                 "time_local": "02:00", "weekday": None,
                                 "running": False, "next_run_local": "amanhã 02:00",
                                 "last_result": None, "last_finished_at": None})
    r = ics._scheduler_status_fn(db_session)
    assert r["status"] == ics.STATUS_ATIVA
    monkeypatch.setattr(backup_scheduler, "scheduler_status",
                        lambda: {"enabled": False, "schedule": None,
                                 "time_local": None, "weekday": None,
                                 "running": False, "next_run_local": None,
                                 "last_result": None, "last_finished_at": None})
    assert ics._scheduler_status_fn(db_session)["status"] == ics.STATUS_DESABILITADA


def test_scheduler_com_ultimo_resultado_erro(db_session, monkeypatch):
    monkeypatch.setattr(backup_scheduler, "scheduler_status",
                        lambda: {"enabled": True, "schedule": "weekly",
                                 "time_local": "03:00", "weekday": 6,
                                 "running": False, "next_run_local": None,
                                 "last_result": {"result": "FAILURE",
                                                 "description": "erro simulado"},
                                 "last_finished_at": None})
    assert ics._scheduler_status_fn(db_session)["status"] == ics.STATUS_COM_ERRO


# ---------------------------------------------------------------------------
# Backup Local — regra do clarify (US1)
# ---------------------------------------------------------------------------

def test_backup_local_ok_com_valido_recente(db_session, monkeypatch):
    monkeypatch.setattr(backup_scheduler, "scheduler_status",
                        lambda: {"enabled": True, "schedule": "daily"})
    rec = _mk_backup_record(db_session, status="SUCCESS", size=1024, age_min=60)
    path = _materialize_backup_file(rec.filename)
    try:
        r = ics._backup_local_status_fn(db_session)
        assert r["status"] == ics.STATUS_ATIVA
    finally:
        path.unlink(missing_ok=True)


def test_backup_local_atencao_ciclo_perdido(db_session, monkeypatch):
    monkeypatch.setattr(backup_scheduler, "scheduler_status",
                        lambda: {"enabled": True, "schedule": "daily"})
    rec = _mk_backup_record(db_session, status="SUCCESS", size=1024, age_min=48 * 60)
    path = _materialize_backup_file(rec.filename)
    try:
        r = ics._backup_local_status_fn(db_session)
        assert r["status"] == ics.STATUS_ATENCAO
    finally:
        path.unlink(missing_ok=True)


def test_backup_local_falha_sem_valido_com_agendador_ativo(db_session, monkeypatch):
    monkeypatch.setattr(backup_scheduler, "scheduler_status",
                        lambda: {"enabled": True, "schedule": "daily"})
    _mk_backup_record(db_session, status="FAILURE", age_min=30)
    r = ics._backup_local_status_fn(db_session)
    assert r["status"] == ics.STATUS_COM_ERRO


def test_backup_local_manual_sem_alerta_por_atualidade(db_session, monkeypatch):
    monkeypatch.setattr(backup_scheduler, "scheduler_status",
                        lambda: {"enabled": False, "schedule": None})
    _mk_backup_record(db_session, status="SUCCESS", size=1024, age_min=90 * 24 * 60)
    assert ics._backup_local_status_fn(db_session)["status"] == ics.STATUS_ATIVA
    _mk_backup_record(db_session, status="FAILURE", age_min=10)
    assert ics._backup_local_status_fn(db_session)["status"] == ics.STATUS_COM_ERRO


# ---------------------------------------------------------------------------
# Armazenamento — regra do clarify (US1)
# ---------------------------------------------------------------------------

class _FakeUsage:
    def __init__(self, total, used, free):
        self.total = total
        self.used = used
        self.free = free


def test_storage_ok_quando_livre_maior_que_ultimo_backup(db_session, monkeypatch, tmp_path):
    import shutil as _shutil
    monkeypatch.setattr(config, "BACKUP_DIR", str(tmp_path), raising=False)
    _mk_backup_record(db_session, status="SUCCESS", size=100)
    monkeypatch.setattr(_shutil, "disk_usage", lambda p: _FakeUsage(10_000_000, 1_000, 9_000_000))
    r = ics._storage_status_fn(db_session)
    assert r["status"] == ics.STATUS_ATIVA


def test_storage_atencao_quando_livre_menor_que_ultimo_backup(db_session, monkeypatch, tmp_path):
    import shutil as _shutil
    monkeypatch.setattr(config, "BACKUP_DIR", str(tmp_path), raising=False)
    _mk_backup_record(db_session, status="SUCCESS", size=9_000_000)
    monkeypatch.setattr(_shutil, "disk_usage", lambda p: _FakeUsage(10_000_000, 5_000_000, 1_000_000))
    r = ics._storage_status_fn(db_session)
    assert r["status"] == ics.STATUS_ATENCAO


def test_storage_com_erro_diretorio_ausente(db_session, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_DIR", "/nao/existe/047", raising=False)
    _mk_backup_record(db_session, status="SUCCESS", size=100)
    assert ics._storage_status_fn(db_session)["status"] == ics.STATUS_COM_ERRO


def test_storage_ok_sem_backup_de_referencia(db_session, monkeypatch, tmp_path):
    import shutil as _shutil
    monkeypatch.setattr(config, "BACKUP_DIR", str(tmp_path), raising=False)
    monkeypatch.setattr(_shutil, "disk_usage", lambda p: _FakeUsage(10_000_000, 1_000, 9_000_000))
    r = ics._storage_status_fn(db_session)
    assert r["status"] == ics.STATUS_ATIVA


# ---------------------------------------------------------------------------
# Consulta ≠ Teste (SC-002) e isolamento (R6/SC-007)
# ---------------------------------------------------------------------------

def test_get_panel_nao_executa_testes_caros(client, monkeypatch):
    chamadas = {"backup": 0, "destino": 0, "smtp": 0, "ldap": 0}

    def _guard(name):
        def _fail(*a, **k):
            chamadas[name] += 1
            raise AssertionError(f"{name} não deveria rodar no GET do painel")
        return _fail

    monkeypatch.setattr("app.services.backup_service.BackupService.generate_backup",
                        _guard("backup"))
    monkeypatch.setattr("app.services.external_backup_service.test_destination",
                        _guard("destino"))
    monkeypatch.setattr("app.services.email_provider.check_connection",
                        _guard("smtp"))
    monkeypatch.setattr("app.services.ad_ldap.test_connection", _guard("ldap"))

    resp = client.get("/admin/integracoes")
    assert resp.status_code == 200
    assert all(v == 0 for v in chamadas.values())


def test_isolamento_um_card_nao_derruba_o_painel(client, monkeypatch):
    def boom(db):
        raise RuntimeError("coleta quebrada")

    # patch na ENTRADA do catálogo (a referência foi capturada no import)
    monkeypatch.setitem(ics.get_integration("storage"), "status_fn", boom)
    resp = client.get("/admin/integracoes")
    assert resp.status_code == 200
    body = resp.text
    assert "Banco de Dados" in body and "1Doc" in body
    assert "Não foi possível verificar" in body


# ---------------------------------------------------------------------------
# US2 — dispatcher backup_externo (teste de destino reutilizado)
# ---------------------------------------------------------------------------

def test_run_test_backup_externo_sucesso(db_session, tmp_path):
    _mk_external(db_session, enabled=True, dest=str(tmp_path), status=None)
    ok, msg = ics.run_test(db_session, "backup_externo", user="val047")
    assert ok is True
    # nenhum arquivo de teste deixado no destino
    assert list(Path(tmp_path).iterdir()) == []


def test_run_test_backup_externo_destino_invalido(db_session):
    _mk_external(db_session, enabled=True, dest="/nao/existe/dest-047", status=None)
    ok, msg = ics.run_test(db_session, "backup_externo", user="val047")
    assert ok is False
    assert msg  # mensagem amigável, sem segredo


def test_run_test_componentes_sem_mecanismo(db_session):
    for key in ("app", "database", "storage", "backup_local", "scheduler"):
        ok, msg = ics.run_test(db_session, key)
        assert ok is False
        assert "não suportado" in msg.lower()


# ---------------------------------------------------------------------------
# US3 — RBAC, segredos e auditoria
# ---------------------------------------------------------------------------

def _make_user(db, username, *, is_admin=False):
    """Usuário próprio do arquivo (padrão test_central_integracoes.py)."""
    from app.models.user import User
    from app.services.auth_service import hash_password

    user = db.query(User).filter(User.username == username).first()
    if user:
        return user
    user = User(
        username=username,
        full_name="Validador 047",
        email=f"{username}@test.local",
        is_active=True,
        is_admin=is_admin,
        password_hash=hash_password("SenhaForte!123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _grant(db, user, perm_name):
    """Concede permissão via RBAC (padrão test_central_integracoes.py)."""
    from app.models.permission import Permission
    from app.models.role import Role
    from app.models.role_permission import RolePermission
    from app.models.user_role import UserRole

    role = db.query(Role).filter(Role.name == "_central_saude_test").first()
    if not role:
        role = Role(name="_central_saude_test", description="perfil 047", is_system=False)
        db.add(role)
        db.commit()
        db.refresh(role)
    perm = db.query(Permission).filter(Permission.name == perm_name).first()
    if not perm:
        perm = Permission(name=perm_name, module="Integrações", label=perm_name)
        db.add(perm)
        db.commit()
        db.refresh(perm)
    if not db.query(RolePermission).filter_by(role_id=role.id, permission_id=perm.id).first():
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        db.commit()
    if not db.query(UserRole).filter_by(user_id=user.id, role_id=role.id).first():
        db.add(UserRole(user_id=user.id, role_id=role.id, assigned_by="local"))
        db.commit()


def _login(client, user):
    client.cookies.clear()
    resp = client.post("/api/v1/auth/login",
                       data={"username": user.username, "password": "SenhaForte!123"})
    assert resp.status_code == 200, resp.text


def test_painel_403_sem_permissao(client, db_session):
    user = _make_user(db_session, "val047sem", is_admin=False)
    _login(client, user)  # sem integracoes.visualizar
    assert client.get("/admin/integracoes").status_code == 403
    assert client.get("/admin/integracoes/app").status_code == 403


def test_painel_200_com_visualizar(client, db_session):
    user = _make_user(db_session, "val047vis", is_admin=False)
    _grant(db_session, user, "integracoes.visualizar")
    _login(client, user)
    assert client.get("/admin/integracoes").status_code == 200
    assert client.get("/admin/integracoes/app").status_code == 200


def test_painel_nao_exibe_segredos(client, monkeypatch):
    monkeypatch.setattr(config, "SMTP_PASSWORD", "SEGREDO-SMTP-047", raising=False)
    monkeypatch.setattr(config, "ONEDOC_API_TOKEN", "SEGREDO-1DOC-047", raising=False)
    monkeypatch.setattr(config, "AD_BIND_PASSWORD", "SEGREDO-AD-047", raising=False)
    body = client.get("/admin/integracoes").text
    for segredo in ("SEGREDO-SMTP-047", "SEGREDO-1DOC-047", "SEGREDO-AD-047"):
        assert segredo not in body


def test_get_nao_gera_eventos_de_auditoria(client, db_session):
    from app.models.integration_execution import IntegrationExecution
    from app.models.audit_log import AuditLog
    client.get("/admin/integracoes")
    client.get("/admin/integracoes")
    assert db_session.query(IntegrationExecution).count() == 0
    assert (db_session.query(AuditLog)
            .filter(AuditLog.module == "central_integracoes").count() == 0)
