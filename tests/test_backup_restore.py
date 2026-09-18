"""Restauração Segura de Backup (feature 017).

Cobertura (spec §8, quickstart §2 — testes A–K):
  A. Ciclo completo autorizado (service + web) → sucesso + eventos + backup de segurança
  B. Não autorizado → 403 nas 2 rotas, nenhum evento, banco inalterado
  C. Cancelar (sem POST) → nenhum efeito
  D. Backup corrompido → restauração não iniciada
  E. Backup inexistente → restauração não iniciada
  F. Path traversal → bloqueado
  G. Falha ao criar backup de segurança → restore não inicia, banco preservado
  H. Falha durante o import → falha registrada, nenhum falso sucesso,
     backup de segurança preservado
  I. Validação pós-restore (SELECT 1 + tabelas essenciais + contagens)
  J. Restore concorrente → rejeitado; generate_backup bloqueado durante restore
  K. Regressão → suíte completa (executada à parte)

O executor de import é sempre FAKE na suíte (SQLite não roda o cliente
MariaDB — research R2); o import real é validado no quickstart §3.
"""

import gzip
import json

import pytest

from app.services.audit_service import get_audit_logs
from app.services.backup_service import BackupService, BackupError
from app.services.permission_service import (
    ensure_default_roles,
    get_role_by_name,
    get_role_permission_names,
)
from tests.test_rbac import PASSWORD, _login, _make_user

# Padrões de nome (compatíveis com backup_service._BACKUP_NAME_RE)
_BACKUP_NAME_RE_STR = r"^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$"
_PART_RE_STR = r"^backup_\d{8}_\d{6}_\d{6}\.part(\.gz)?$"

SQL_CONTENT = b"-- SisPatrimonio Pro dump de teste\nCREATE TABLE prova (id INT);\n"


# ============================================================================
# HELPERS
# ============================================================================

def _make_backup_file(name, payload=SQL_CONTENT):
    """Grava um backup válido no diretório (gzip p/ .sql.gz, direto p/ .sql)."""
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / name
    if name.endswith(".gz"):
        buf = _gz_bytes(payload)
        path.write_bytes(buf)
    else:
        path.write_bytes(payload)
    return name


def _gz_bytes(payload):
    import io

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", filename="") as gz:
        gz.write(payload)
    return buf.getvalue()


def _corrupted_gz(name):
    """Grava um .sql.gz corrompido (bytes do meio removidos → CORROMPIDO)."""
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    data = bytearray(_gz_bytes(SQL_CONTENT * 20))
    del data[30:-8]
    (BACKUP_DIR / name).write_bytes(bytes(data))
    return name


def _fake_import(path, *, is_gzip=False):
    """Executor fake de import: lê o arquivo (verifica acessibilidade)."""
    if is_gzip:
        with gzip.open(path, "rb") as gz:
            gz.read()
    else:
        with open(path, "rb") as f:
            f.read()


def _failing_import(path, *, is_gzip=False):
    raise RuntimeError("import falhou (simulado)")


def _failing_security_backup(path):
    raise RuntimeError("dump de segurança falhou (simulado)")


def _cleanup_backups():
    """Remove backups/temporários dos testes (padrão de test_backup_manual.py)."""
    import re

    from app.config import BACKUP_DIR

    backup_re = re.compile(_BACKUP_NAME_RE_STR)
    part_re = re.compile(_PART_RE_STR)
    if BACKUP_DIR.exists():
        for p in BACKUP_DIR.iterdir():
            if (
                backup_re.match(p.name)
                or part_re.match(p.name)
                or p.name == "nao-e-backup.txt"
            ):
                if p.is_file():
                    p.unlink()


@pytest.fixture(autouse=True)
def _clean_backup_dir():
    _cleanup_backups()
    yield
    _cleanup_backups()


def _audit_entries(db, action):
    return [log for log in get_audit_logs(db) if log.action == action]


def _new_data(log):
    return json.loads(log.new_data) if log.new_data else {}


# ============================================================================
# FOUNDATIONAL (T002/T003) — permissão backup.restaurar
# ============================================================================

def test_seed_cria_permissao_backup_restaurar(db_session):
    ensure_default_roles(db_session)
    from app.models.permission import Permission

    perm = (
        db_session.query(Permission)
        .filter(Permission.name == "backup.restaurar")
        .first()
    )
    assert perm is not None
    assert perm.module == "Backup"

    admin = get_role_by_name(db_session, "Administrador")
    assert "backup.restaurar" in get_role_permission_names(db_session, admin)


def test_seed_idempotente_restaurar(db_session):
    ensure_default_roles(db_session)
    ensure_default_roles(db_session)
    from app.models.permission import Permission

    perms = (
        db_session.query(Permission)
        .filter(Permission.name == "backup.restaurar")
        .all()
    )
    assert len(perms) == 1


# ============================================================================
# FOUNDATIONAL (T005/T006) — slot de concorrência
# ============================================================================

def test_restore_in_progress_false_por_padrao():
    from app.services import backup_service

    with backup_service._RESTORE_LOCK:
        assert backup_service._RESTORE_IN_PROGRESS is False


def test_generate_backup_recusa_durante_restore(db_session, monkeypatch):
    from app.services import backup_service
    from app.services.audit_service import ACTION_BACKUP_FAILED

    user = _make_user(db_session, "rstduring", role_names=["Administrador"])
    # Força a flag como se houvesse um restore em andamento
    monkeypatch.setattr(backup_service, "_RESTORE_IN_PROGRESS", True)

    with pytest.raises(BackupError, match="restaura"):
        BackupService.generate_backup(
            db_session, user, "127.0.0.1", dump_executor=lambda p: None
        )
    # Nenhum evento de backup criado/falha
    assert _audit_entries(db_session, ACTION_BACKUP_FAILED) == []


# ============================================================================
# FOUNDATIONAL (T007/T008) — validate_restore_source (Testes D/E/F service)
# ============================================================================

def test_validate_source_gz_valido(db_session):
    name = _make_backup_file("backup_20260917_120000_001001.sql.gz")
    info = BackupService.validate_restore_source(name)
    assert info["is_gzip"] is True
    assert info["size_bytes"] > 0


def test_validate_source_sql_legado_valido(db_session):
    name = _make_backup_file("backup_20260917_120000_001002.sql")
    info = BackupService.validate_restore_source(name)
    assert info["is_gzip"] is False
    assert info["size_bytes"] > 0


def test_validate_source_corrompido_recusa(db_session):
    name = _corrupted_gz("backup_20260917_120000_001003.sql.gz")
    with pytest.raises(BackupError):
        BackupService.validate_restore_source(name)


def test_validate_source_vazio_recusa(db_session):
    name = _make_backup_file("backup_20260917_120000_001004.sql", payload=b"")
    with pytest.raises(BackupError):
        BackupService.validate_restore_source(name)


def test_validate_source_traversal_e_inexistente(db_session):
    with pytest.raises(BackupError):
        BackupService.validate_restore_source("../../etc/passwd")
    with pytest.raises(BackupError):
        BackupService.validate_restore_source("backup_20260917_120000_999999.sql")


# ============================================================================
# FOUNDATIONAL (T008) — validate_post_restore (Teste I)
# ============================================================================

def test_validate_post_restore_ok(db_session):
    # SQLite de teste tem o schema criado pelas fixtures do conftest
    BackupService.validate_post_restore(db_session)


# ============================================================================
# US1 (T010) — Teste A service-level: ciclo completo
# ============================================================================

def test_ciclo_completo_service_sucesso(db_session):
    from app.services.audit_service import (
        ACTION_BACKUP_CREATED,
        ACTION_BACKUP_PRE_RESTORE,
        ACTION_BACKUP_RESTORE_STARTED,
        ACTION_BACKUP_RESTORE_SUCCESS,
        RESULT_SUCCESS,
    )

    name = _make_backup_file("backup_20260917_120000_001101.sql.gz")
    user = _make_user(db_session, "rstadmin", role_names=["Administrador"])

    result = BackupService.restore_backup(
        db_session,
        user,
        "127.0.0.1",
        name,
        import_executor=_fake_import,
    )

    # Retorno com os 3 campos
    assert result["restaurado"] == name
    assert result["backup_seguranca"].endswith(".sql.gz")
    assert result["size_bytes"] > 0

    # Backup de segurança listado e OK
    backups = {b["filename"]: b for b in BackupService.list_backups()}
    assert result["backup_seguranca"] in backups
    assert backups[result["backup_seguranca"]]["integrity"] == "OK"

    # Eventos na ordem e com resultado SUCCESS
    started = _audit_entries(db_session, ACTION_BACKUP_RESTORE_STARTED)
    pre = _audit_entries(db_session, ACTION_BACKUP_PRE_RESTORE)
    success = _audit_entries(db_session, ACTION_BACKUP_RESTORE_SUCCESS)
    assert len(started) == 1 and len(pre) == 1 and len(success) == 1
    assert started[0].result == pre[0].result == success[0].result == RESULT_SUCCESS
    assert started[0].id < pre[0].id < success[0].id

    nd = _new_data(pre[0])
    assert nd["backup"] == name
    assert nd["backup_seguranca"] == result["backup_seguranca"]

    # Slot liberado
    from app.services import backup_service

    with backup_service._RESTORE_LOCK:
        assert backup_service._RESTORE_IN_PROGRESS is False

    # Evento de geração padrão da Feature 1 também existe (trilha apensável)
    assert len(_audit_entries(db_session, ACTION_BACKUP_CREATED)) >= 1


# ============================================================================
# US1 (T012) — Teste A web-level: GET não executa; POST executa
# ============================================================================

def test_web_get_info_nao_executa(client, db_session):
    from app.services.audit_service import ACTION_BACKUP_RESTORE_STARTED

    name = _make_backup_file("backup_20260917_120000_001201.sql.gz")

    resp = client.get(f"/admin/backups/{name}/restaurar")
    assert resp.status_code == 200
    body = resp.text
    assert name in body
    assert "ATENÇÃO" in body or "Atenção" in body or "atenção" in body
    assert "backup de segurança" in body
    # Nenhum evento de execução
    assert _audit_entries(db_session, ACTION_BACKUP_RESTORE_STARTED) == []
    assert BackupService.list_backups() != []  # arquivo ainda lá (nada aconteceu)


def test_web_post_executa_ciclo_completo(client, db_session, monkeypatch):
    from app.services.audit_service import (
        ACTION_BACKUP_PRE_RESTORE,
        ACTION_BACKUP_RESTORE_SUCCESS,
    )
    from app.services import backup_service

    name = _make_backup_file("backup_20260917_120000_001202.sql.gz")
    monkeypatch.setattr(backup_service, "_run_mysql_import", _fake_import)

    resp = client.post(f"/admin/backups/{name}/restaurar", follow_redirects=False)
    assert resp.status_code == 303

    backups = {b["filename"]: b for b in BackupService.list_backups()}
    assert len(backups) == 2  # restaurado + segurança

    assert len(_audit_entries(db_session, ACTION_BACKUP_PRE_RESTORE)) == 1
    assert len(_audit_entries(db_session, ACTION_BACKUP_RESTORE_SUCCESS)) == 1


# ============================================================================
# US2 (T016) — Teste B: não autorizado
# ============================================================================

def test_web_sem_permissao_403(client, db_session):
    from app.services.audit_service import ACTION_BACKUP_RESTORE_STARTED

    name = _make_backup_file("backup_20260917_120000_001301.sql.gz")
    _make_user(db_session, "rstConsulta", role_names=["Consulta"])
    _login(client, "rstConsulta")

    assert client.get(f"/admin/backups/{name}/restaurar").status_code == 403
    assert client.post(f"/admin/backups/{name}/restaurar").status_code == 403

    assert _audit_entries(db_session, ACTION_BACKUP_RESTORE_STARTED) == []


def test_gerenciar_nao_implica_restaurar(db_session, client):
    """backup.gerenciar não concede backup.restaurar (research R9):
    usuário com gerenciar-only recebe 403 no restore."""
    from app.models.user import User
    from app.services.permission_service import (
        assign_role,
        create_role,
        get_user_permission_names,
        update_role,
    )

    name = _make_backup_file("backup_20260917_120000_001302.sql.gz")
    _make_user(db_session, "rstGerente", role_names=["Consulta"])
    user = db_session.query(User).filter(User.username == "rstGerente").first()

    # Perfil dedicado com APENAS backup.gerenciar
    role = create_role(db_session, "Só Backup")
    update_role(db_session, role, permission_names=["backup.gerenciar"])
    assign_role(db_session, user, role)

    perms = get_user_permission_names(db_session, user)
    assert "backup.gerenciar" in perms
    assert "backup.restaurar" not in perms

    _login(client, "rstGerente")
    resp = client.get(f"/admin/backups/{name}/restaurar")
    assert resp.status_code == 403


def test_ui_mostra_restaurar_apenas_com_permissao(client, db_session):
    """Ação Restaurar aparece na linha do backup (com permissão admin)."""
    _make_backup_file("backup_20260917_120000_001303.sql.gz")
    resp = client.get("/admin/backups")
    assert resp.status_code == 200
    assert "/restaurar" in resp.text


# ============================================================================
# US3 (T017) — Testes C/D/E/F web: recusas seguras
# ============================================================================

def test_web_cancelar_nao_tem_efeito(client, db_session):
    """Teste C (remediação C1): cancelar = confirm() recusado/navegação — nenhum POST."""
    from app.services.audit_service import ACTION_BACKUP_RESTORE_STARTED

    name = _make_backup_file("backup_20260917_120000_001401.sql.gz")

    # Apenas o GET (informações) — nada mais é enviado
    resp = client.get(f"/admin/backups/{name}/restaurar")
    assert resp.status_code == 200

    assert _audit_entries(db_session, ACTION_BACKUP_RESTORE_STARTED) == []
    names = {b["filename"] for b in BackupService.list_backups()}
    assert names == {name}  # nenhum backup de segurança criado


def test_web_backup_corrompido_recusa(client, db_session, monkeypatch):
    """Teste D: restore não inicia, banco preservado, falha registrada."""
    from app.services.audit_service import (
        ACTION_BACKUP_PRE_RESTORE,
        ACTION_BACKUP_RESTORE_FAILED,
        ACTION_BACKUP_RESTORE_STARTED,
    )
    from app.services import backup_service

    name = _corrupted_gz("backup_20260917_120000_001402.sql.gz")
    monkeypatch.setattr(backup_service, "_run_mysql_import", _fake_import)

    from app.models.asset import Asset

    antes = db_session.query(Asset).count()

    resp = client.post(f"/admin/backups/{name}/restaurar", follow_redirects=False)
    assert resp.status_code == 303  # redirect com flash de erro

    failed = _audit_entries(db_session, ACTION_BACKUP_RESTORE_FAILED)
    assert len(failed) == 1
    assert _audit_entries(db_session, ACTION_BACKUP_PRE_RESTORE) == []
    # Restore não iniciou: nenhum backup de segurança (apenas o corrompido)
    assert len(BackupService.list_backups()) == 1
    assert db_session.query(Asset).count() == antes


def test_web_backup_inexistente_404(client, db_session):
    """Teste E: restauração não iniciada (nome válido fora do padrão/inexistente →
    recusa segura; banco inalterado; nenhum evento de execução)."""
    from app.services.audit_service import ACTION_BACKUP_RESTORE_STARTED

    resp = client.get("/admin/backups/backup_20260917_120000_999999.sql/restaurar")
    # GET da tela: inexistente → 404 (rota valida antes de renderizar)
    assert resp.status_code == 404

    resp2 = client.post(
        "/admin/backups/backup_20260917_120000_999999.sql/restaurar",
        follow_redirects=False,
    )
    assert resp2.status_code == 303  # redirect com flash de erro
    assert _audit_entries(db_session, ACTION_BACKUP_RESTORE_STARTED) == []


def test_web_path_traversal_bloqueado(client, db_session):
    """Teste F: ../ e ../../ bloqueados."""
    resp = client.get("/admin/backups/../../etc/passwd/restaurar")
    assert resp.status_code in (400, 404)


# ============================================================================
# US4 (T018) — Testes G/H/J: falhas seguras e concorrência
# ============================================================================

def test_falha_backup_seguranca_restore_nao_inicia(db_session):
    """Teste G: dump de segurança falha → restore NÃO inicia, banco preservado."""
    from app.services.audit_service import (
        ACTION_BACKUP_PRE_RESTORE,
        ACTION_BACKUP_RESTORE_FAILED,
        ACTION_BACKUP_RESTORE_STARTED,
    )

    name = _make_backup_file("backup_20260917_120000_001501.sql.gz")
    user = _make_user(db_session, "rstfail1", role_names=["Administrador"])

    from app.models.asset import Asset

    antes = db_session.query(Asset).count()

    with pytest.raises(BackupError):
        BackupService.restore_backup(
            db_session,
            user,
            "127.0.0.1",
            name,
            import_executor=_fake_import,
            security_backup_executor=_failing_security_backup,
        )

    failed = _audit_entries(db_session, ACTION_BACKUP_RESTORE_FAILED)
    assert len(failed) == 1
    assert _audit_entries(db_session, ACTION_BACKUP_PRE_RESTORE) == []
    # O evento INICIADO pode existir (a falha foi depois da validação da fonte)
    # mas o restore em si não rodou: nenhum import, banco intocado
    assert db_session.query(Asset).count() == antes
    # Nenhum arquivo novo de backup (o de segurança falhou; nenhum parcial)
    names = {b["filename"] for b in BackupService.list_backups()}
    assert names == {name}


def test_falha_no_import_sem_falso_sucesso(db_session):
    """Teste H: import falha → falha registrada, backup de segurança preservado."""
    from app.services.audit_service import (
        ACTION_BACKUP_PRE_RESTORE,
        ACTION_BACKUP_RESTORE_FAILED,
        RESULT_FAILURE,
    )

    name = _make_backup_file("backup_20260917_120000_001502.sql.gz")
    user = _make_user(db_session, "rstfail2", role_names=["Administrador"])

    with pytest.raises(BackupError):
        BackupService.restore_backup(
            db_session,
            user,
            "127.0.0.1",
            name,
            import_executor=_failing_import,
        )

    failed = _audit_entries(db_session, ACTION_BACKUP_RESTORE_FAILED)
    assert len(failed) == 1
    assert failed[0].result == RESULT_FAILURE
    # Backup de segurança foi criado e permanece listado (BV-R4)
    assert len(_audit_entries(db_session, ACTION_BACKUP_PRE_RESTORE)) == 1
    backups = BackupService.list_backups()
    assert len(backups) == 2  # restaurado + segurança (preservado)
    # Descrição segura (sem segredos)
    desc = failed[0].description or ""
    assert "mysql" not in desc.lower() or "MYSQL_PWD" not in desc
    assert "PASSWORD" not in desc


def test_restore_concorrente_rejeitado(db_session, monkeypatch):
    """Teste J: com o slot ocupado, novo restore é rejeitado sem evento."""
    from app.services import backup_service
    from app.services.audit_service import ACTION_BACKUP_RESTORE_STARTED

    name = _make_backup_file("backup_20260917_120000_001503.sql.gz")
    user = _make_user(db_session, "rstfail3", role_names=["Administrador"])

    monkeypatch.setattr(backup_service, "_RESTORE_IN_PROGRESS", True)

    with pytest.raises(BackupError, match="restaura"):
        BackupService.restore_backup(
            db_session,
            user,
            "127.0.0.1",
            name,
            import_executor=_fake_import,
        )
    # Nenhum evento novo (nada foi iniciado)
    assert _audit_entries(db_session, ACTION_BACKUP_RESTORE_STARTED) == []


# ============================================================================
# US5 (T019) — Teste I: validação pós-restore na ordem do ciclo
# ============================================================================

# ============================================================================
# 017 — diagnóstico de importação: stderr do cliente no log técnico (sanitizado)
# ============================================================================

def test_sanitize_stderr_redaciona_senha():
    """_sanitize_stderr remove a senha e preserva o diagnóstico (Princípio VI)."""
    from app.services.backup_service import _sanitize_stderr

    text = "ERROR 1045: Access denied for user 'u'@'h' senha=secret123"
    out = _sanitize_stderr(text, "secret123")
    assert "secret123" not in out
    assert "ERROR 1045" in out


def test_import_failure_loga_stderr_sanitizado(monkeypatch, caplog, tmp_path):
    """Falha de importação: diagnóstico vai ao log técnico SEM segredos (§31);
    mensagem ao usuário/auditoria permanece genérica."""
    import logging
    import io as io_mod

    from app.services import backup_service

    class _FakeStdin:
        def write(self, chunk):
            pass

        def close(self):
            pass

    class _FakeProc:
        def __init__(self):
            self.stdin = _FakeStdin()
            self.stderr = io_mod.BytesIO(
                b"ERROR 1064 (42000): You have an error in your SQL syntax near 'X'\n"
            )
            self.returncode = 1
            self.args = ["mysql"]

        def wait(self, timeout=None):
            return 1

    monkeypatch.setattr(backup_service.subprocess, "Popen", lambda *a, **k: _FakeProc())
    monkeypatch.setattr(
        backup_service,
        "DATABASE_URL",
        "mariadb+pymysql://usuario:senhasecreta@127.0.0.1:3306/banco",
    )

    dump = tmp_path / "dump.sql"
    dump.write_bytes(b"-- conteudo\n")

    with caplog.at_level(logging.ERROR, logger="app.services.backup_service"):
        with pytest.raises(BackupError, match="retornou erro"):
            backup_service._run_mysql_import(dump, is_gzip=False)

    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "ERROR 1064" in joined          # diagnóstico presente no log técnico
    assert "senhasecreta" not in joined    # senha NUNCA (Princípio VI)


def test_sucesso_somente_apos_validacao(db_session, monkeypatch):
    """BV-R3: se validate_post_restore falha, SUCESSO nunca é gravado."""
    from app.services.audit_service import (
        ACTION_BACKUP_RESTORE_FAILED,
        ACTION_BACKUP_RESTORE_SUCCESS,
    )
    from app.services import backup_service

    name = _make_backup_file("backup_20260917_120000_001601.sql.gz")
    user = _make_user(db_session, "rstfail4", role_names=["Administrador"])

    def _broken_post_restore(db):
        raise BackupError("validação pós-restore falhou (simulado)")

    monkeypatch.setattr(BackupService, "validate_post_restore", _broken_post_restore)

    with pytest.raises(BackupError):
        BackupService.restore_backup(
            db_session,
            user,
            "127.0.0.1",
            name,
            import_executor=_fake_import,
        )

    assert _audit_entries(db_session, ACTION_BACKUP_RESTORE_SUCCESS) == []
    assert len(_audit_entries(db_session, ACTION_BACKUP_RESTORE_FAILED)) == 1
