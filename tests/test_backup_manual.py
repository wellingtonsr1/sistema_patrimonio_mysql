"""Feature 015 — Backup Manual do SisPatrimônio Pro.

Cobertura (spec FR-012, quickstart §2):
  1. Geração (executor fake) → arquivo em data/backups/ + auditoria SUCCESS
  2. Falha de geração → auditoria FAILURE, nenhum artefato listado
  3. Listagem → ordenada desc, artefatos alheios ignorados
  4. Download → bytes íntegros + evento BACKUP_DOWNLOAD
  5. Download inexistente/fora do padrão → 404 sem tocar disco
  6. RBAC → 403 sem permissão nas 3 rotas; admin → 200
  7. Menu → item "Backups" apenas com can('backup.gerenciar')

O executor de dump é sempre FAKE na suíte (SQLite não roda mysqldump —
research R4); o dump real é validado manualmente (quickstart §3).
"""

import json
import re
from datetime import datetime, timedelta

import pytest

from app.services.audit_service import get_audit_logs
from app.services.backup_service import BackupService
from app.services.permission_service import (
    ensure_default_roles,
    get_role_by_name,
    get_role_permission_names,
)
from tests.test_rbac import PASSWORD, _login, _make_user

# Padrão estrito do nome (data-model §1; remediação I1: timestamp UTC)
_BACKUP_NAME_RE = re.compile(r"^backup_\d{8}_\d{6}_\d{6}\.sql$")

FAKE_DUMP_CONTENT = b"-- SisPatrimonio Pro fake dump\nSET autocommit=0;\n"


# ============================================================================
# HELPERS
# ============================================================================

def _fake_dump(path):
    """Executor fake: grava conteúdo determinístico no caminho recebido (R4)."""
    with open(path, "wb") as f:
        f.write(FAKE_DUMP_CONTENT)


def _failing_dump(path):
    """Executor fake que falha como um mysqldump com erro (exit != 0)."""
    raise RuntimeError("dump falhou (simulado)")


def _cleanup_backups():
    """Remove os backups gerados pelos testes (não toca em nada fora do padrão)."""
    from app.config import BACKUP_DIR

    if BACKUP_DIR.exists():
        for p in BACKUP_DIR.iterdir():
            if _BACKUP_NAME_RE.match(p.name):
                p.unlink()


@pytest.fixture(autouse=True)
def _clean_backup_dir():
    _cleanup_backups()
    yield
    _cleanup_backups()


def _audit_entries(db, action):
    return [log for log in get_audit_logs(db) if log.action == action]


def _new_data(log):
    """AuditLog.new_data é Text com JSON serializado (app/models/audit_log.py) — desserializa."""
    return json.loads(log.new_data) if log.new_data else {}


# ============================================================================
# FOUNDATIONAL — permissão/seed (T003) e núcleo do service (T004)
# ============================================================================

def test_seed_cria_permissao_backup_gerenciar(db_session):
    ensure_default_roles(db_session)
    from app.models.permission import Permission

    perm = (
        db_session.query(Permission)
        .filter(Permission.name == "backup.gerenciar")
        .first()
    )
    assert perm is not None
    assert perm.module == "Backup"

    admin = get_role_by_name(db_session, "Administrador")
    assert "backup.gerenciar" in get_role_permission_names(db_session, admin)


def test_seed_idempotente_nao_duplica(db_session):
    ensure_default_roles(db_session)
    ensure_default_roles(db_session)
    from app.models.permission import Permission

    perms = (
        db_session.query(Permission)
        .filter(Permission.name == "backup.gerenciar")
        .all()
    )
    assert len(perms) == 1


def test_list_backups_diretorio_vazio_ou_inexistente(db_session):
    assert BackupService.list_backups() == []


def test_list_backups_ignora_arquivos_fora_do_padrao(db_session):
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    (BACKUP_DIR / "nao-e-backup.txt").write_bytes(b"x")
    (BACKUP_DIR / "backup_20260917_120000_000123.sql").write_bytes(b"ok")

    backups = BackupService.list_backups()

    assert [b["filename"] for b in backups] == ["backup_20260917_120000_000123.sql"]


def test_list_backups_ordenado_mais_recente_primeiro(db_session):
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    antigo = BACKUP_DIR / "backup_20260917_100000_000001.sql"
    novo = BACKUP_DIR / "backup_20260917_120000_000002.sql"
    antigo.write_bytes(b"a" * 10)
    novo.write_bytes(b"b" * 20)

    backups = BackupService.list_backups()

    assert [b["filename"] for b in backups] == [novo.name, antigo.name]
    assert backups[0]["size_bytes"] == 20
    assert isinstance(backups[0]["timestamp"], datetime)


def test_get_backup_path_valido_aponta_para_data_backups(db_session):
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    name = "backup_20260917_120000_000123.sql"
    (BACKUP_DIR / name).write_bytes(b"ok")

    path = BackupService.get_backup_path(name)

    assert path.parent == BACKUP_DIR
    assert path.name == name


def test_get_backup_path_rejeita_nome_fora_do_padrao(db_session):
    with pytest.raises(Exception):
        BackupService.get_backup_path("../../etc/passwd")


def test_get_backup_path_rejeita_inexistente(db_session):
    with pytest.raises(Exception):
        BackupService.get_backup_path("backup_20260917_120000_000999.sql")


# ============================================================================
# US1 — geração (T010) e rota web (T011)
# ============================================================================

def test_geracao_sucesso_cria_arquivo_e_audita(db_session):
    from app.services.audit_service import ACTION_BACKUP_CREATED, RESULT_SUCCESS

    user = _make_user(db_session, "bkpadmin", role_names=["Administrador"])

    result = BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_fake_dump
    )

    # Retorno com os 3 campos
    assert set(result.keys()) == {"filename", "timestamp", "size_bytes"}
    assert _BACKUP_NAME_RE.match(result["filename"])
    assert result["size_bytes"] == len(FAKE_DUMP_CONTENT)

    # Auditoria SUCCESS com new_data sem credenciais
    events = _audit_entries(db_session, ACTION_BACKUP_CREATED)
    assert len(events) == 1
    ev = events[0]
    assert ev.result == RESULT_SUCCESS
    nd = _new_data(ev)
    assert nd["arquivo"] == result["filename"]
    assert nd["tamanho_bytes"] == result["size_bytes"]


def test_geracao_falha_audita_failure_e_nao_deixa_artefato(db_session):
    from app.services.audit_service import ACTION_BACKUP_CREATED, RESULT_FAILURE

    user = _make_user(db_session, "bkpadmin2", role_names=["Administrador"])

    with pytest.raises(Exception):
        BackupService.generate_backup(
            db_session, user, "127.0.0.1", dump_executor=_failing_dump
        )

    events = _audit_entries(db_session, ACTION_BACKUP_CREATED)
    assert len(events) == 1
    assert events[0].result == RESULT_FAILURE
    # Sem comando/credenciais na descrição (Princípio VI)
    desc = (events[0].description or "")
    assert "mysqldump" not in desc and "PASSWORD" not in desc

    assert BackupService.list_backups() == []


def test_geracoes_repetidas_nomes_distintos(db_session):
    user = _make_user(db_session, "bkpadmin3", role_names=["Administrador"])

    r1 = BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_fake_dump
    )
    r2 = BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_fake_dump
    )

    assert r1["filename"] != r2["filename"]
    assert len(BackupService.list_backups()) == 2


def test_rota_gerar_com_admin_cria_e_audita(client, db_session, monkeypatch):
    from app.services import backup_service

    monkeypatch.setattr(backup_service, "_run_mysqldump", _fake_dump)

    resp = client.post("/admin/backups/gerar", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/admin/backups")
    assert len(BackupService.list_backups()) == 1


def test_rota_gerar_sem_permissao_negada(client, db_session):
    _make_user(db_session, "semperm", role_names=["Consulta"])
    _login(client, "semperm")

    resp = client.post("/admin/backups/gerar", follow_redirects=False)

    assert resp.status_code == 403
    assert BackupService.list_backups() == []


# ============================================================================
# US2 — tela de listagem e menu (T015)
# ============================================================================

def test_tela_backups_com_admin_lista_ordenado(client, db_session):
    from app.config import BACKUP_DIR

    ensure_default_roles(db_session)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    (BACKUP_DIR / "backup_20260917_100000_000001.sql").write_bytes(b"a" * 10)
    (BACKUP_DIR / "backup_20260917_120000_000002.sql").write_bytes(b"b" * 20)

    resp = client.get("/admin/backups")

    assert resp.status_code == 200
    body = resp.text
    assert "backup_20260917_120000_000002.sql" in body
    assert body.index("backup_20260917_120000_000002.sql") < body.index(
        "backup_20260917_100000_000001.sql"
    )


def test_tela_backups_vazia_estado_amigavel(client, db_session):
    resp = client.get("/admin/backups")

    assert resp.status_code == 200
    assert "Nenhum backup" in resp.text


def test_tela_backups_sem_permissao_negada(client, db_session):
    _make_user(db_session, "semperm2", role_names=["Consulta"])
    _login(client, "semperm2")

    resp = client.get("/admin/backups")

    assert resp.status_code == 403


def test_menu_contem_item_backups_com_permissao(client, db_session):
    resp = client.get("/")

    assert resp.status_code == 200
    assert "/admin/backups" in resp.text
    assert "Backups" in resp.text


# ============================================================================
# US3 — download (T018)
# ============================================================================

def test_download_serve_bytes_e_audita(client, db_session):
    from app.config import BACKUP_DIR
    from app.services.audit_service import ACTION_BACKUP_DOWNLOAD, RESULT_SUCCESS

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    name = "backup_20260917_120000_000123.sql"
    (BACKUP_DIR / name).write_bytes(FAKE_DUMP_CONTENT)

    resp = client.get(f"/admin/backups/{name}/download")

    assert resp.status_code == 200
    assert resp.content == FAKE_DUMP_CONTENT  # SC-003 integridade
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert name in resp.headers.get("content-disposition", "")

    events = _audit_entries(db_session, ACTION_BACKUP_DOWNLOAD)
    assert len(events) == 1
    assert events[0].result == RESULT_SUCCESS
    assert _new_data(events[0])["arquivo"] == name


def test_download_sem_permissao_negado(client, db_session):
    _make_user(db_session, "semperm3", role_names=["Consulta"])
    _login(client, "semperm3")

    name = "backup_20260917_120000_000123.sql"
    resp = client.get(f"/admin/backups/{name}/download")

    assert resp.status_code == 403


def test_download_nome_fora_do_padrao_404_sem_evento(client, db_session):
    from app.services.audit_service import ACTION_BACKUP_DOWNLOAD

    resp = client.get("/admin/backups/../../etc/passwd/download")

    assert resp.status_code in (400, 404)

    assert _audit_entries(db_session, ACTION_BACKUP_DOWNLOAD) == []


def test_download_inexistente_404_sem_evento(client, db_session):
    from app.services.audit_service import ACTION_BACKUP_DOWNLOAD

    name = "backup_20260917_120000_000999.sql"
    resp = client.get(f"/admin/backups/{name}/download")

    assert resp.status_code == 404
    assert _audit_entries(db_session, ACTION_BACKUP_DOWNLOAD) == []


# ============================================================================
# US4 — matriz de segurança (T021)
# ============================================================================

def test_matriz_sem_permissao_403_nas_tres_rotas(client, db_session):
    _make_user(db_session, "matriz", role_names=["Consulta"])
    _login(client, "matriz")

    assert client.get("/admin/backups").status_code == 403
    assert client.post("/admin/backups/gerar", follow_redirects=False).status_code == 403
    name = "backup_20260917_120000_000123.sql"
    assert client.get(f"/admin/backups/{name}/download").status_code == 403

    # Nenhum evento de backup criado por esses acessos negados
    from app.services.audit_service import ACTION_BACKUP_CREATED

    assert _audit_entries(db_session, ACTION_BACKUP_CREATED) == []


def test_eventos_nao_contem_credenciais_nem_comando(db_session):
    from app.services.audit_service import ACTION_BACKUP_CREATED

    user = _make_user(db_session, "bkpaudit", role_names=["Administrador"])
    BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_fake_dump
    )

    ev = _audit_entries(db_session, ACTION_BACKUP_CREATED)[0]
    new_data = _new_data(ev)
    assert set(new_data.keys()) <= {"arquivo", "tamanho_bytes"}
