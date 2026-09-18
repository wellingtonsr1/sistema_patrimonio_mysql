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


# ============================================================================
# FEATURE 019 — HELPERS (worker, drenagem, deadline, manutenção)
# ============================================================================

def _wait_for(predicate, timeout=10.0, interval=0.05):
    """Aguarda até predicate() ser verdadeiro (worker thread assíncrona)."""
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _wait_worker_finished(timeout=10.0):
    """Aguarda o slot da 017 liberar (worker concluiu, sucesso ou falha)."""
    from app.services import backup_service

    return _wait_for(
        lambda: not backup_service.restore_in_progress(), timeout=timeout
    )


def _patch_worker_sessions(monkeypatch):
    """Padrão 018/I7: sessões do worker apontam para a base de teste.

    O worker roda em thread própria e cria sessões via backup_service.SessionLocal —
    sem este patch ele conectaria no banco real do DATABASE_URL.

    IMPORTANTE: o conftest é carregado pelo pytest como módulo 'conftest'
    (sem tests/__init__.py); importar 'tests.conftest' criaria um SEGUNDO
    módulo com SEGUNDO engine :memory: — a thread veria uma base vazia.
    Resolvemos o módulo carregado via sys.modules (funciona nos dois casos).
    """
    import sys

    from app.services import backup_service

    mod = sys.modules.get("conftest") or sys.modules.get("tests.conftest")
    TestingSessionLocal = mod.TestingSessionLocal

    monkeypatch.setattr(backup_service, "SessionLocal", TestingSessionLocal)


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

def test_ciclo_completo_service_sucesso(db_session, monkeypatch):
    """019: ciclo completo agora é AGENDADO (worker) — mesmo contrato de eventos."""
    from app.services.audit_service import (
        ACTION_BACKUP_CREATED,
        ACTION_BACKUP_PRE_RESTORE,
        ACTION_BACKUP_RESTORE_STARTED,
        ACTION_BACKUP_RESTORE_SUCCESS,
        RESULT_SUCCESS,
    )

    _patch_worker_sessions(monkeypatch)

    name = _make_backup_file("backup_20260917_120000_001101.sql.gz")
    user = _make_user(db_session, "rstadmin", role_names=["Administrador"])

    result = BackupService.restore_backup(
        db_session,
        user,
        "127.0.0.1",
        name,
        import_executor=_fake_import,
    )

    # Retorno agendado (019): confirmação + URL de status
    assert result["agendado"] is True
    assert result["restaurado"] == name
    assert _wait_worker_finished()

    pre = _audit_entries(db_session, ACTION_BACKUP_PRE_RESTORE)
    security_name = _new_data(pre[0])["backup_seguranca"]

    # Backup de segurança listado e OK
    backups = {b["filename"]: b for b in BackupService.list_backups()}
    assert security_name.endswith(".sql.gz")
    assert security_name in backups
    assert backups[security_name]["integrity"] == "OK"

    # Eventos na ordem e com resultado SUCCESS
    started = _audit_entries(db_session, ACTION_BACKUP_RESTORE_STARTED)
    pre = _audit_entries(db_session, ACTION_BACKUP_PRE_RESTORE)
    success = _audit_entries(db_session, ACTION_BACKUP_RESTORE_SUCCESS)
    assert len(started) == 1 and len(pre) == 1 and len(success) == 1
    assert started[0].result == pre[0].result == success[0].result == RESULT_SUCCESS
    assert started[0].id < pre[0].id < success[0].id

    nd = _new_data(pre[0])
    assert nd["backup"] == name
    assert nd["backup_seguranca"] == security_name

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
    _patch_worker_sessions(monkeypatch)  # 019: o ciclo roda em worker thread

    resp = client.post(f"/admin/backups/{name}/restaurar", follow_redirects=False)
    assert resp.status_code == 303
    assert _wait_worker_finished()

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

def test_falha_backup_seguranca_restore_nao_inicia(db_session, monkeypatch):
    """Teste G (019): falha do backup de segurança → FALHA auditada no worker,
    banco preservado, nenhum backup de segurança."""
    from app.services.audit_service import (
        ACTION_BACKUP_PRE_RESTORE,
        ACTION_BACKUP_RESTORE_FAILED,
        ACTION_BACKUP_RESTORE_STARTED,
    )

    _patch_worker_sessions(monkeypatch)

    name = _make_backup_file("backup_20260917_120000_001501.sql.gz")
    user = _make_user(db_session, "rstfail1", role_names=["Administrador"])

    from app.models.asset import Asset

    antes = db_session.query(Asset).count()

    result = BackupService.restore_backup(
        db_session,
        user,
        "127.0.0.1",
        name,
        import_executor=_fake_import,
        security_backup_executor=_failing_security_backup,
    )
    assert result["agendado"] is True
    assert _wait_worker_finished()

    failed = _audit_entries(db_session, ACTION_BACKUP_RESTORE_FAILED)
    assert len(failed) == 1
    assert _audit_entries(db_session, ACTION_BACKUP_PRE_RESTORE) == []
    # O evento INICIADO pode existir (a falha foi depois da validação da fonte)
    # mas o restore em si não rodou: nenhum import, banco intocado
    assert db_session.query(Asset).count() == antes
    # Nenhum arquivo novo de backup (o de segurança falhou; nenhum parcial)
    names = {b["filename"] for b in BackupService.list_backups()}
    assert names == {name}


def test_falha_no_import_sem_falso_sucesso(db_session, monkeypatch):
    """Teste H (019): import falha no worker → FALHA registrada, segurança preservado."""
    from app.services.audit_service import (
        ACTION_BACKUP_PRE_RESTORE,
        ACTION_BACKUP_RESTORE_FAILED,
        RESULT_FAILURE,
    )

    _patch_worker_sessions(monkeypatch)

    name = _make_backup_file("backup_20260917_120000_001502.sql.gz")
    user = _make_user(db_session, "rstfail2", role_names=["Administrador"])

    BackupService.restore_backup(
        db_session,
        user,
        "127.0.0.1",
        name,
        import_executor=_failing_import,
    )
    assert _wait_worker_finished()

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
    """BV-R3 (019): validação pós-restore falha no worker → SUCESSO nunca gravado."""
    from app.services.audit_service import (
        ACTION_BACKUP_RESTORE_FAILED,
        ACTION_BACKUP_RESTORE_SUCCESS,
    )
    from app.services import backup_service

    _patch_worker_sessions(monkeypatch)

    name = _make_backup_file("backup_20260917_120000_001601.sql.gz")
    user = _make_user(db_session, "rstfail4", role_names=["Administrador"])

    def _broken_post_restore(db):
        raise BackupError("validação pós-restore falhou (simulado)")

    monkeypatch.setattr(BackupService, "validate_post_restore", _broken_post_restore)

    BackupService.restore_backup(
        db_session,
        user,
        "127.0.0.1",
        name,
        import_executor=_fake_import,
    )
    assert _wait_worker_finished()

    assert _audit_entries(db_session, ACTION_BACKUP_RESTORE_SUCCESS) == []
    assert len(_audit_entries(db_session, ACTION_BACKUP_RESTORE_FAILED)) == 1


# ============================================================================
# FEATURE 019 — US1: fluxo agendado + worker + drenagem do pool
# ============================================================================


def test_019_drain_engineFechaOciosasEAguardaQuiescencia(db_session, monkeypatch):
    """T006 (contract §2): drain_engine retorna True, não altera DATABASE_URL."""
    from app.database import drain_engine

    assert drain_engine(timeout=5.0) is True
    from app.config import DATABASE_URL

    assert DATABASE_URL  # intocado (contract §2/FR-006)


def test_019_restoreAgendaEWorkerConcluiCiclo(db_session, monkeypatch):
    """US1 (T004 c/d/e): restore_backup agenda, retorna antes do import;
    worker executa segurança → drenagem → import → validação → SUCCESS."""
    from app.services import backup_service
    from app.services.audit_service import (
        ACTION_BACKUP_PRE_RESTORE,
        ACTION_BACKUP_RESTORE_STARTED,
        ACTION_BACKUP_RESTORE_SUCCESS,
    )

    _patch_worker_sessions(monkeypatch)

    ordem = []

    def _spy_import(path, *, is_gzip=False):
        ordem.append("import")

    original_drain = backup_service.drain_engine

    def _spy_drain(**kwargs):
        ordem.append("drain")
        return original_drain(**kwargs)

    monkeypatch.setattr(backup_service, "drain_engine", _spy_drain)

    name = _make_backup_file("backup_20260918_090000_001901.sql.gz")
    user = _make_user(db_session, "rst019a", role_names=["Administrador"])

    result = BackupService.restore_backup(
        db_session, user, "127.0.0.1", name, import_executor=_spy_import
    )
    # Fluxo agendado: retorna ANTES do import (nenhum SUCCESS ainda)
    assert result["agendado"] is True
    assert ordem == [] or "import" not in ordem
    assert _audit_entries(db_session, ACTION_BACKUP_RESTORE_SUCCESS) == []

    # Worker conclui em tempo finito com o ciclo completo na ordem correta
    assert _wait_worker_finished(), "worker não concluiu o ciclo"
    assert ordem == ["drain", "import"]  # drenagem ANTES do import (FR-003)
    started = _audit_entries(db_session, ACTION_BACKUP_RESTORE_STARTED)
    pre = _audit_entries(db_session, ACTION_BACKUP_PRE_RESTORE)
    success = _audit_entries(db_session, ACTION_BACKUP_RESTORE_SUCCESS)
    assert len(started) == 1 and len(pre) == 1 and len(success) == 1
    security_name = _new_data(pre[0])["backup_seguranca"]
    backups = {b["filename"]: b for b in BackupService.list_backups()}
    assert security_name in backups
    assert backups[security_name]["integrity"] == "OK"


def test_019_workerUsaSessoesPropriasNaoAsDoRequest(db_session, monkeypatch):
    """US1 (T004b/R5): eventos do worker NÃO passam pela sessão do request
    (a sessão recebida por restore_backup não é usada no ciclo destrutivo)."""
    from app.services import backup_service
    from app.services.audit_service import ACTION_BACKUP_RESTORE_SUCCESS

    _patch_worker_sessions(monkeypatch)

    sessoes_usadas = []

    real_write_audit = backup_service.write_audit

    def _spy_write_audit(db, **kwargs):
        sessoes_usadas.append(db)
        return real_write_audit(db, **kwargs)

    monkeypatch.setattr(backup_service, "write_audit", _spy_write_audit)

    name = _make_backup_file("backup_20260918_090000_001902.sql.gz")
    user = _make_user(db_session, "rst019b", role_names=["Administrador"])

    BackupService.restore_backup(
        db_session, user, "127.0.0.1", name, import_executor=_fake_import
    )
    assert _wait_worker_finished()
    # A sessão do request (db_session) não pode aparecer nos eventos do worker
    # (somente a do INICIADO, antes da thread, pode ser a do request)
    assert all(s is not db_session for s in sessoes_usadas[1:])
    assert len(_audit_entries(db_session, ACTION_BACKUP_RESTORE_SUCCESS)) == 1


def test_019_falhaDeQuiescenciaAbortaSemFalsoSucesso(db_session, monkeypatch):
    """US1 (T004f): drain_engine False → falha honesta, estado liberado,
    backup de segurança disponível."""
    from app.services import backup_service
    from app.services.audit_service import (
        ACTION_BACKUP_PRE_RESTORE,
        ACTION_BACKUP_RESTORE_FAILED,
        RESULT_FAILURE,
    )

    _patch_worker_sessions(monkeypatch)

    monkeypatch.setattr(backup_service, "drain_engine", lambda **k: False)

    name = _make_backup_file("backup_20260918_090000_001903.sql.gz")
    user = _make_user(db_session, "rst019c", role_names=["Administrador"])

    BackupService.restore_backup(
        db_session, user, "127.0.0.1", name, import_executor=_fake_import
    )
    assert _wait_worker_finished()

    failed = _audit_entries(db_session, ACTION_BACKUP_RESTORE_FAILED)
    assert len(failed) == 1 and failed[0].result == RESULT_FAILURE
    assert len(_audit_entries(db_session, ACTION_BACKUP_PRE_RESTORE)) == 1
    backups = {b["filename"] for b in BackupService.list_backups()}
    # Backup de segurança criado antes da falha permanece disponível (FR-005)
    assert any(".sql" in n for n in backups)
    with backup_service._RESTORE_LOCK:
        assert backup_service._RESTORE_IN_PROGRESS is False


def test_019_webPostRestaurarResponde303Imediato(client, db_session, monkeypatch):
    """US1 (T005a/I3): POST /restaurar responde 303 imediato (fluxo web) sem
    bloquear o request até o fim do import; polling conclui depois."""
    import threading

    from app.services import backup_service

    _patch_worker_sessions(monkeypatch)

    solta = threading.Event()

    def _slow_import(path, *, is_gzip=False):
        solta.wait(timeout=10)

    monkeypatch.setattr(backup_service, "_run_mysql_import", _slow_import)

    name = _make_backup_file("backup_20260918_090000_001904.sql.gz")

    resp = client.post(f"/admin/backups/{name}/restaurar", follow_redirects=False)
    assert resp.status_code == 303  # imediato — request NÃO esperou o import

    status = client.get("/admin/backups/restaurar/status")
    assert status.status_code == 200
    dados = status.json()
    assert dados["active"] is True

    solta.set()
    assert _wait_worker_finished()

    dados = client.get("/admin/backups/restaurar/status").json()
    assert dados["finished"] is True and dados["ok"] is True
    assert "senha" not in status.text.lower() or "password" not in status.text.lower()


def test_019_statusExigePermissaoRestaurar(client, db_session, monkeypatch):
    """US1 (T005b/FR-014): rota de status exige backup.restaurar (403 sem ela)."""
    from tests.test_rbac import _login

    _make_user(db_session, "rst019d", role_names=["Consulta"])
    _login(client, "rstConsulta") if False else _login(client, "rst019d")

    resp = client.get("/admin/backups/restaurar/status")
    assert resp.status_code == 403


def test_019_guardaExternaDeGeracaoDuranteRestore(client, db_session, monkeypatch):
    """US1 (T005e/FR-015): generate_backup SEM _allow_during_restore continua
    bloqueado durante a restauração em andamento (guarda 017 preservada)."""
    import threading

    from app.services import backup_service

    _patch_worker_sessions(monkeypatch)

    solta = threading.Event()

    def _slow_import(path, *, is_gzip=False):
        solta.wait(timeout=10)

    monkeypatch.setattr(backup_service, "_run_mysql_import", _slow_import)

    name = _make_backup_file("backup_20260918_090000_001905.sql.gz")

    resp = client.post(f"/admin/backups/{name}/restaurar", follow_redirects=False)
    assert resp.status_code == 303
    try:
        from app.services.audit_service import ACTION_BACKUP_CREATED

        antes = len(_audit_entries(db_session, ACTION_BACKUP_CREATED))
        with pytest.raises(BackupError):
            BackupService.generate_backup(db_session, user=None)
        depois = len(_audit_entries(db_session, ACTION_BACKUP_CREATED))
        assert depois == antes  # nenhum backup criado
    finally:
        solta.set()
        assert _wait_worker_finished()


# ============================================================================
# FEATURE 019 — US2: deadline real, diagnóstico sanitizado, liberação
# ============================================================================


def test_019_timeoutDoImportAbortaNoPrazo(db_session, monkeypatch):
    """US2 (T009a/SC-002): write bloqueante + BACKUP_IMPORT_TIMEOUT baixo →
    aborta dentro do prazo, FALHA auditada, slot liberado."""
    import threading
    import time

    from app.services import backup_service
    from app.services.audit_service import (
        ACTION_BACKUP_RESTORE_FAILED,
        RESULT_FAILURE,
    )

    _patch_worker_sessions(monkeypatch)

    solta = threading.Event()

    class _ProcBloqueante:
        def __init__(self):
            self.returncode = None
            self.stderr = None
            self.terminated = False
            self.stdin = self  # write bloqueante é o próprio stdin (fake)

        def write(self, chunk):
            solta.wait(timeout=30)  # simula o bloqueio real do incidente (D2)
            return len(chunk)

        def close(self):
            pass

        def wait(self, timeout=None):
            return 0

        def terminate(self):
            self.terminated = True
            solta.set()

        kill = terminate

    proc = _ProcBloqueante()

    def _bloqueante(path, *, is_gzip=False):
        backup_service._import_with_deadline(
            proc, lambda: iter([b"chunk"]), password="senha_falsa"
        )

    monkeypatch.setattr(backup_service, "BACKUP_IMPORT_TIMEOUT", 1.5)
    monkeypatch.setattr(backup_service, "_run_mysql_import", _bloqueante)

    name = _make_backup_file("backup_20260918_090000_001906.sql.gz")
    user = _make_user(db_session, "rst019e", role_names=["Administrador"])

    inicio = time.monotonic()
    BackupService.restore_backup(
        db_session, user, "127.0.0.1", name, import_executor=_bloqueante
    )
    assert _wait_worker_finished(timeout=15)
    decorrido = time.monotonic() - inicio

    assert decorrido < 10, "deadline não abortou em tempo finito"
    assert proc.terminated, "subprocesso não foi terminado no estouro"
    failed = _audit_entries(db_session, ACTION_BACKUP_RESTORE_FAILED)
    assert len(failed) == 1 and failed[0].result == RESULT_FAILURE
    with backup_service._RESTORE_LOCK:
        assert backup_service._RESTORE_IN_PROGRESS is False


def test_019_diagnosticoDoTimeoutSemCredenciais(db_session, monkeypatch, caplog):
    """US2 (T009b/H): log técnico do deadline traz etapa/tempo e NUNCA a senha."""
    import logging
    import threading

    from app.services import backup_service

    _patch_worker_sessions(monkeypatch)

    solta = threading.Event()

    class _ProcBloqueante:
        returncode = None
        stderr = None
        stdin = None  # definido no __init__ (write bloqueante é o próprio stdin)

        def __init__(self):
            self.stdin = self

        def write(self, chunk):
            solta.wait(timeout=30)
            return len(chunk)

        def close(self):
            pass

        def wait(self, timeout=None):
            return 0

        def terminate(self):
            solta.set()

        kill = terminate

    def _bloqueante(path, *, is_gzip=False):
        with caplog.at_level(logging.ERROR, logger="app.services.backup_service"):
            backup_service._import_with_deadline(
                _ProcBloqueante(), lambda: iter([b"chunk"]), password="senha_falsa"
            )

    monkeypatch.setattr(backup_service, "BACKUP_IMPORT_TIMEOUT", 1.0)
    monkeypatch.setattr(backup_service, "_run_mysql_import", _bloqueante)

    name = _make_backup_file("backup_20260918_090000_001907.sql.gz")
    user = _make_user(db_session, "rst019f", role_names=["Administrador"])

    BackupService.restore_backup(
        db_session, user, "127.0.0.1", name, import_executor=_bloqueante
    )
    assert _wait_worker_finished(timeout=15)
    solta.set()

    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "etapa" in joined.lower()
    assert "senha_falsa" not in joined  # Princípio VI


def test_019_returncodeErroMantemFalhaHonestaeEstadoLivre(db_session, monkeypatch):
    """US2 (T009c/d): fluxo assíncrono preserva a falha honesta da 017."""
    from app.services import backup_service
    from app.services.audit_service import ACTION_BACKUP_RESTORE_FAILED

    _patch_worker_sessions(monkeypatch)

    name = _make_backup_file("backup_20260918_090000_001908.sql.gz")
    user = _make_user(db_session, "rst019g", role_names=["Administrador"])

    BackupService.restore_backup(
        db_session, user, "127.0.0.1", name, import_executor=_failing_import
    )
    assert _wait_worker_finished()

    failed = _audit_entries(db_session, ACTION_BACKUP_RESTORE_FAILED)
    assert len(failed) == 1
    backups = {b["filename"] for b in BackupService.list_backups()}
    assert len(backups) >= 1  # backup de segurança disponível (FR-005)
    with backup_service._RESTORE_LOCK:
        assert backup_service._RESTORE_IN_PROGRESS is False


# ============================================================================
# FEATURE 019 — US3: modo de manutenção sem banco
# ============================================================================


def test_019_manutencaoResponde503SemBanco(client, db_session, monkeypatch):
    """US3 (T012a/FR-010/F1): middleware ativo → 503 amigável mesmo com get_db
    quebrado (a página de manutenção NÃO depende do banco)."""
    from app.services import backup_service

    def _broken_get_db():
        raise RuntimeError("banco indisponível (simulado)")
        yield  # pragma: no cover

    monkeypatch.setattr(backup_service, "maintenance_mode", {"active": True})
    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = _broken_get_db
    try:
        resp = client.get("/admin/users")
        assert resp.status_code == 503
        assert "restaura" in resp.text.lower()  # informa a restauração
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_019_manutencaoWhitelistMinima(client, db_session, monkeypatch):
    """US3 (T012b): status do restore e login/health acessíveis; demais 503."""
    from app.services import backup_service

    monkeypatch.setattr(backup_service, "maintenance_mode", {"active": True})

    assert client.get("/admin/backups/restaurar/status").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/admin/users").status_code == 503
    assert client.get("/assets").status_code == 503


def test_019_manutencaoEncerraAutomaticamente(db_session, monkeypatch):
    """US3 (T012d/FR-012): worker limpa a manutenção em sucesso e falha."""
    from app.services import backup_service

    _patch_worker_sessions(monkeypatch)

    name = _make_backup_file("backup_20260918_090000_001909.sql.gz")
    user = _make_user(db_session, "rst019h", role_names=["Administrador"])

    BackupService.restore_backup(
        db_session, user, "127.0.0.1", name, import_executor=_fake_import
    )
    assert _wait_worker_finished()
    assert backup_service.maintenance_mode["active"] is False

    # Falha: manutenção também é encerrada
    name2 = _make_backup_file("backup_20260918_090000_001910.sql.gz")
    BackupService.restore_backup(
        db_session, user, "127.0.0.1", name2, import_executor=_failing_import
    )
    assert _wait_worker_finished()
    assert backup_service.maintenance_mode["active"] is False


def test_019_crashDaThreadNaoDeixaManutencaoEterna(db_session, monkeypatch):
    """US3 (T012e/FR-011/FR-009): exceção no worker → manutenção encerrada,
    slot liberado, falha auditada (crash-safety)."""
    from app.services import backup_service
    from app.services.audit_service import ACTION_BACKUP_RESTORE_FAILED

    _patch_worker_sessions(monkeypatch)

    name = _make_backup_file("backup_20260918_090000_001911.sql.gz")
    user = _make_user(db_session, "rst019i", role_names=["Administrador"])

    def _explode_security(path):
        raise RuntimeError("boom (crash simulado)")

    BackupService.restore_backup(
        db_session,
        user,
        "127.0.0.1",
        name,
        security_backup_executor=_explode_security,
    )
    assert _wait_worker_finished()

    assert backup_service.maintenance_mode["active"] is False
    with backup_service._RESTORE_LOCK:
        assert backup_service._RESTORE_IN_PROGRESS is False
    assert len(_audit_entries(db_session, ACTION_BACKUP_RESTORE_FAILED)) == 1


def test_019_estadoNaoPersisteEntreProcessos(db_session, monkeypatch):
    """US3 (T012f/R3): flag de manutenção é em memória — novo import do módulo
    começa limpo (restart do processo limpa a manutenção)."""
    import importlib

    from app.services import backup_service

    backup_service.maintenance_mode["active"] = True
    importlib.reload(backup_service)
    try:
        assert backup_service.maintenance_mode["active"] is False
        assert backup_service.restore_in_progress() is False
    finally:
        # reload substituiu símbolos; restaura estado limpo para os próximos testes
        backup_service.maintenance_mode["active"] = False
