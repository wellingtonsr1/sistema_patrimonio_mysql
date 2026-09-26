"""Destino externo para backups — feature 045 (cenários A–L do quickstart).

Mecanismo (US1), operação pela tela (US2) e resiliência/preservações (US3):
- Destino externo de teste = diretório temporário (`tmp_path` — C-4: pasta
  montada comporta-se igual);
- Constantes de retry/espera/orçamento MONKEYPATCHÁVEIS (R4) — suíte rápida;
- Dump sempre FAKE (padrão 015–020; SQLite não roda mysqldump);
- Suíte existente permanece 100% verde (regressão §37).
"""

import re

import pytest

from app.models.audit_log import AuditLog
from app.models.backup_external_record import BackupExternalRecord
from app.models.backup_record import BackupRecord
from app.services import backup_scheduler, backup_service, external_backup_service
from app.services.backup_service import BackupService

FAKE_DUMP_CONTENT = b"-- SisPatrimonio Pro fake dump (045 externo)\n"

_BACKUP_NAME_RE = re.compile(r"^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$")

SECRET_PATTERNS = ("senha", "password", "token", "secret", "credential")


# ============================================================================
# Fixtures/helpers
# ============================================================================

def _fake_dump(path):
    with open(path, "wb") as f:
        f.write(FAKE_DUMP_CONTENT)


@pytest.fixture(autouse=True)
def _fast_retry(monkeypatch):
    """R4: retry/espera/orçamento encurtados — suíte rápida e determinística."""
    monkeypatch.setattr(external_backup_service, "EXTERNAL_COPY_ATTEMPTS", 1)
    monkeypatch.setattr(external_backup_service, "EXTERNAL_RETRY_WAIT_SECONDS", 0)
    monkeypatch.setattr(external_backup_service, "EXTERNAL_COPY_BUDGET_SECONDS", 5)


@pytest.fixture(autouse=True)
def _ext_session_isolation(db_session, monkeypatch):
    """O serviço 045 abre sessões PRÓPRIAS (padrão _worker_audit/020): nos
    testes, essas sessões apontam para o banco de teste (mesmo isolamento da
    fixture _scheduler_session_isolation do conftest — sessionmaker ligado ao
    MESMO bind do fixture; importar tests.conftest criaria um segundo módulo
    com um segundo engine :memory: vazio)."""
    from sqlalchemy.orm import sessionmaker as _sessionmaker

    ExtSM = _sessionmaker(
        autocommit=False, autoflush=False, bind=db_session.get_bind()
    )
    monkeypatch.setattr(external_backup_service, "SessionLocal", ExtSM)


@pytest.fixture(autouse=True)
def _clean_backup_dir():
    """Repositório local limpo por teste (padrão 020)."""
    from app.config import BACKUP_DIR

    def _clean():
        if BACKUP_DIR.exists():
            for p in BACKUP_DIR.iterdir():
                if p.is_file() and (_BACKUP_NAME_RE.match(p.name) or ".part" in p.name):
                    p.unlink()

    _clean()
    yield
    _clean()


@pytest.fixture
def dest(tmp_path):
    """Destino externo de teste: diretório temporário vazio."""
    d = tmp_path / "destino-externo"
    d.mkdir()
    return d


def _entries(dest):
    """Nomes de entradas do destino (para asserts de I/O e atomicidade)."""
    return sorted(p.name for p in dest.iterdir())


def _enable_external(db_session, dest_path):
    """Ativa o mecanismo apontando para o diretório de teste."""
    external_backup_service.save_external_config(
        db_session, enabled=True, dest_path=str(dest_path), updated_by="tester"
    )


def _disable_external(db_session):
    external_backup_service.save_external_config(
        db_session, enabled=False, dest_path=None, updated_by="tester"
    )


def _external_records(db_session):
    return (
        db_session.query(BackupExternalRecord)
        .order_by(BackupExternalRecord.id)
        .all()
    )


def _audit_actions(db_session):
    return {
        (log.action, log.result) for log in db_session.query(AuditLog).all()
    }


@pytest.fixture
def fresh_scheduler(db_session, monkeypatch):
    """Agendador isolado (padrão 020/021): sessão de teste + catch-up off."""
    monkeypatch.setattr(backup_scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(backup_service, "SessionLocal", lambda: db_session,
                        raising=False)
    from app.services.backup_config_service import get_backup_config

    row = get_backup_config(db_session)
    row.auto_enabled = True
    db_session.commit()
    monkeypatch.setattr(backup_scheduler, "_catchup_done", True)
    return backup_scheduler


def _spy_generate_with_fake_dump(monkeypatch):
    """generate_backup com dump FAKE injetado (mantém o gancho 045 real)."""
    real_generate = BackupService.generate_backup

    def _spy(db, user, ip_address=None, **kwargs):
        kwargs.setdefault("dump_executor", _fake_dump)
        return real_generate(db, user, ip_address, **kwargs)

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_spy))


# ============================================================================
# Cenários A/B/L — desabilitado: somente local, zero I/O no destino
# ============================================================================

def test_externo_desabilitado_manual_somente_local(db_session, dest):
    """A — manual sem externo: comportamento atual preservado; zero I/O."""
    _disable_external(db_session)
    before = _entries(dest)

    result = BackupService.generate_backup(db_session, None, None,
                                           dump_executor=_fake_dump)

    assert result["filename"].endswith(".sql.gz")
    assert result["external"] is None  # no-op: sem status externo
    assert _entries(dest) == before  # ZERO I/O no destino
    assert _external_records(db_session) == []
    # Zero eventos externos
    actions = _audit_actions(db_session)
    assert ("BACKUP_EXTERNO_SUCESSO", "SUCCESS") not in actions
    assert ("BACKUP_EXTERNO_FALHA", "FAILURE") not in actions


def test_externo_desabilitado_automatico_somente_local(db_session, fresh_scheduler,
                                                       dest, monkeypatch):
    """B — automático sem externo: idem no ciclo do scheduler."""
    _disable_external(db_session)
    before = _entries(dest)
    _spy_generate_with_fake_dump(monkeypatch)

    summary = fresh_scheduler._run_scheduled_backup()

    assert summary and summary["ok"] is True
    assert _entries(dest) == before  # ZERO I/O no destino
    assert _external_records(db_session) == []


def test_desativado_volta_somente_local(db_session, dest):
    """L — desativado novamente: manual/auto voltam a somente local."""
    # 1) com externo: cópia acontece
    _enable_external(db_session, dest)
    result = BackupService.generate_backup(db_session, None, None,
                                           dump_executor=_fake_dump)
    assert _entries(dest) == [result["filename"]]

    # 2) desativado: novo backup NÃO é copiado
    _disable_external(db_session)
    before = _entries(dest)
    result2 = BackupService.generate_backup(db_session, None, None,
                                            dump_executor=_fake_dump)
    assert result2["external"] is None
    assert _entries(dest) == before  # nada novo no destino


# ============================================================================
# Cenários C/D — cópia validada (mecanismo completo)
# ============================================================================

def test_manual_com_externo_copia_validada(db_session, dest):
    """C — manual com externo: local OK → externo OK; mesmo nome; sha256 igual;
    registro único + auditoria."""
    import hashlib

    _enable_external(db_session, dest)

    result = BackupService.generate_backup(db_session, None, None,
                                           dump_executor=_fake_dump)

    # mesmo nome e conteúdo idêntico (sha256 igual ao local)
    assert result["external"] == {"external_status": "SUCCESS",
                                  "external_reason": None}
    copied = dest / result["filename"]
    assert copied.is_file()
    assert copied.stat().st_size == result["size_bytes"]
    assert hashlib.sha256(copied.read_bytes()).hexdigest() == result["sha256"]

    # registro final único
    records = _external_records(db_session)
    assert len(records) == 1
    rec = records[0]
    assert rec.filename == result["filename"]
    assert rec.backup_type == "MANUAL"
    assert rec.status == "SUCCESS"
    assert rec.size_bytes == result["size_bytes"]
    assert rec.sha256 == result["sha256"]
    assert rec.error_description is None

    # auditoria
    assert ("BACKUP_EXTERNO_SUCESSO", "SUCCESS") in _audit_actions(db_session)


def test_automatico_com_externo_copia_validada(db_session, fresh_scheduler, dest,
                                               monkeypatch):
    """D — automático com externo: ciclo do scheduler copia (dump único)."""
    import hashlib

    _enable_external(db_session, dest)
    _spy_generate_with_fake_dump(monkeypatch)

    summary = fresh_scheduler._run_scheduled_backup()

    assert summary and summary["ok"] is True
    filename = summary["filename"]
    copied = dest / filename
    assert copied.is_file()

    # registro com o tipo ORIGINAL (AUTOMATICO)
    rec = (
        db_session.query(BackupExternalRecord)
        .filter(BackupExternalRecord.filename == filename)
        .one()
    )
    assert rec.backup_type == "AUTOMATICO"
    assert rec.status == "SUCCESS"

    local = None
    from app.config import BACKUP_DIR
    local_path = BACKUP_DIR / filename
    assert hashlib.sha256(copied.read_bytes()).hexdigest() == (
        hashlib.sha256(local_path.read_bytes()).hexdigest()
    )
    del local


# ============================================================================
# Atomicidade (C-7) — tmp oculto nunca permanece; final só validado
# ============================================================================

def test_atomicidade_tmp_oculto_nao_permanece(db_session, dest, monkeypatch):
    """Tmp oculto não permanece; nome final só aparece validado."""
    _enable_external(db_session, dest)

    # Durante a cópia válida: nenhum rastro de tmp ao final
    result = BackupService.generate_backup(db_session, None, None,
                                           dump_executor=_fake_dump)
    assert _entries(dest) == [result["filename"]]  # só o nome final

    # Em falha (destino some após config): tmp (se houve) é removido
    # e NENHUM nome final aparece.
    monkeypatch.setattr(
        external_backup_service, "copy_backup_to_external",
        lambda *a, **k: {"ok": False, "reason": "tempo limite da cópia"},
    )
    result2 = BackupService.generate_backup(db_session, None, None,
                                            dump_executor=_fake_dump)
    assert result2["external"]["external_status"] == "FAILURE"
    assert _entries(dest) == [result["filename"]]  # nada novo publicado


# ============================================================================
# Cenário G — integridade: hash divergente → cópia inválida + falha
# ============================================================================

def test_hash_divergente_copia_invalida(db_session, dest, monkeypatch):
    """G — hash divergente no destino → FAILURE com motivo de integridade;
    nenhum nome final publicado; local preservado."""
    real_sha = external_backup_service._sha256_of

    def _sha_poisoned(path, *, deadline=None):
        digest = real_sha(path, deadline=deadline)
        # Sabotagem apenas na validação do temporário (não toca o local)
        if getattr(path, "name", "").endswith(".tmp"):
            return "f" * 64
        return digest

    monkeypatch.setattr(external_backup_service, "_sha256_of", _sha_poisoned)
    _enable_external(db_session, dest)

    result = BackupService.generate_backup(db_session, None, None,
                                           dump_executor=_fake_dump)

    assert result["external"] == {
        "external_status": "FAILURE",
        "external_reason": "falha de integridade (sha256 divergente)",
    }
    assert _entries(dest) == []  # nada publicado (tmp removido)
    rec = _external_records(db_session)[0]
    assert rec.status == "FAILURE"
    assert rec.error_description == "falha de integridade (sha256 divergente)"
    # Local íntegro
    from app.config import BACKUP_DIR
    assert (BACKUP_DIR / result["filename"]).is_file()


# ============================================================================
# Cenário H — duplicidade: retry/reprocesso não duplica registro nem cópia
# ============================================================================

def test_sem_duplicidade_de_registro_e_copia(db_session, dest):
    """H — processamento repetido com o mesmo filename: um registro, uma cópia."""
    _enable_external(db_session, dest)

    result = BackupService.generate_backup(db_session, None, None,
                                           dump_executor=_fake_dump)
    assert _entries(dest) == [result["filename"]]

    # Segunda execução do gancho com o MESMO filename (nome final já existe
    # com hash igual → sucesso idempotente; registro continua único)
    out = external_backup_service.process_backup_after_success(
        {"filename": result["filename"],
         "size_bytes": result["size_bytes"],
         "sha256": result["sha256"]},
        "MANUAL",
    )
    assert out["external_status"] == "SUCCESS"
    assert _entries(dest) == [result["filename"]]  # sem segunda cópia
    records = _external_records(db_session)
    assert len(records) == 1  # filename UNIQUE — retry não duplica


# ============================================================================
# Cenários E/F — falha externa nunca afeta o local nem a aplicação
# ============================================================================

def test_destino_indisponivel_local_preservado(db_session, dest):
    """E — destino inexistente: local SUCCESS íntegro; falha registrada+
    auditada com motivo; app responde."""
    _enable_external(db_session, dest)
    import shutil
    shutil.rmtree(dest)  # destino some (NAS desmontado)

    result = BackupService.generate_backup(db_session, None, None,
                                           dump_executor=_fake_dump)

    # local preservado
    assert result["filename"].endswith(".sql.gz")
    assert result["external"]["external_status"] == "FAILURE"
    assert result["external"]["external_reason"] == "destino indisponível"

    from app.config import BACKUP_DIR
    assert (BACKUP_DIR / result["filename"]).is_file()

    rec = _external_records(db_session)[0]
    assert rec.status == "FAILURE"
    assert rec.error_description == "destino indisponível"
    assert ("BACKUP_EXTERNO_FALHA", "FAILURE") in _audit_actions(db_session)


def test_destino_sem_permissao(db_session, dest):
    """F — sem permissão de escrita: local OK; externo FALHA (motivo)."""
    import os
    import stat

    _enable_external(db_session, dest)
    os.chmod(dest, stat.S_IRUSR | stat.S_IXUSR)  # r-x: leitura sem escrita
    try:
        result = BackupService.generate_backup(db_session, None, None,
                                               dump_executor=_fake_dump)
        assert result["external"]["external_status"] == "FAILURE"
        assert result["external"]["external_reason"] == "sem permissão de escrita"
        rec = _external_records(db_session)[0]
        assert rec.status == "FAILURE"
        assert rec.error_description == "sem permissão de escrita"
        # local íntegro
        from app.config import BACKUP_DIR
        assert (BACKUP_DIR / result["filename"]).is_file()
    finally:
        os.chmod(dest, 0o755)  # restaura para o cleanup do tmp_path


# ============================================================================
# Cenário I — restauração e pré-restauração intocados
# ============================================================================

def test_restore_e_pre_restauracao_intactos(db_session, dest, monkeypatch):
    """I — restore existente funciona; o pré-restauração é copiado (gancho)."""
    import threading

    _enable_external(db_session, dest)
    _spy_generate_with_fake_dump(monkeypatch)
    monkeypatch.setattr(backup_service, "SessionLocal", lambda: db_session)

    # Backup automático válido para restaurar
    result = BackupService.generate_backup(db_session, None, None,
                                           dump_executor=_fake_dump,
                                           backup_type="AUTOMATICO")
    filename = result["filename"]
    assert result["external"]["external_status"] == "SUCCESS"

    def _fake_import(path, is_gzip):
        pass

    scheduled = BackupService.restore_backup(
        db_session, None, None, filename,
        import_executor=_fake_import,
        security_backup_executor=_fake_dump,
    )
    assert scheduled["agendado"] is True

    for _ in range(400):
        if not backup_service.restore_in_progress():
            break
        threading.Event().wait(0.05)
    assert not backup_service.restore_in_progress()
    assert backup_service.restore_status()["ok"] is True

    # Pré-restauração criado e COPIADO pelo mesmo gancho (clarificação)
    pre = (
        db_session.query(BackupRecord)
        .filter(BackupRecord.backup_type == "PRE_RESTAURACAO")
        .all()
    )
    assert len(pre) == 1
    pre_ext = (
        db_session.query(BackupExternalRecord)
        .filter(BackupExternalRecord.filename == pre[0].filename)
        .one()
    )
    assert pre_ext.backup_type == "PRE_RESTAURACAO"
    assert pre_ext.status == "SUCCESS"
    assert (dest / pre[0].filename).is_file()

    # O arquivo restaurado em si não passa pelo gancho (não é geração)
    assert (
        db_session.query(BackupExternalRecord)
        .filter(BackupExternalRecord.filename == filename)
        .count()
        == 1
    )


# ============================================================================
# Cenário J — retenção não toca o destino
# ============================================================================

def test_retencao_nao_toca_destino(db_session, fresh_scheduler, dest, monkeypatch):
    """J — ciclo com retenção não altera o diretório externo."""
    _enable_external(db_session, dest)
    _spy_generate_with_fake_dump(monkeypatch)

    summary = fresh_scheduler._run_scheduled_backup()  # inclui _apply_retention
    assert summary["ok"] is True
    before = _entries(dest)

    # Segundo ciclo (retenção roda de novo) — destino permanece intacto
    summary2 = fresh_scheduler._run_scheduled_backup()
    assert summary2["ok"] is True
    assert _entries(dest) == before + [summary2["filename"]]  # só a nova cópia
    # Nenhuma cópia antiga foi removida (sem retenção externa — C-12)


# ============================================================================
# Cenário K — configuração persiste após reinicialização
# ============================================================================

def test_config_persiste_apos_reinicializacao(db_session, fresh_scheduler, dest):
    """K — nova sessão reabre o singleton; scheduler status íntegro."""
    _enable_external(db_session, dest)

    # "Reinicialização": sessão nova sobre o mesmo banco (create_all idempotente)
    from sqlalchemy.orm import sessionmaker as _sessionmaker

    RestartSM = _sessionmaker(
        autocommit=False, autoflush=False, bind=db_session.get_bind()
    )
    RestartSM().close()  # sanity: sessão disponível
    db2 = RestartSM()
    try:
        row = external_backup_service.get_external_config(db2)
        assert row.id == 1
        assert row.enabled is True
        assert row.dest_path == str(dest)
    finally:
        db2.close()

    # Scheduler segue íntegro (status sem segredos)
    status = fresh_scheduler.scheduler_status()
    assert status["enabled"] is True


# ============================================================================
# US2 — tela/rotas: RBAC, "Testar destino", persistência no modal
# ============================================================================

from tests.test_rbac import _login, _make_user  # noqa: E402


def test_rbac_403_sem_backup_gerenciar(client, db_session, tmp_path):
    """Sem `backup.gerenciar` → 403 em configurar e testar (C-13)."""
    _make_user(db_session, "bkExterno", role_names=["Consulta"])
    _login(client, "bkExterno")

    resp_cfg = client.post(
        "/admin/backups/configuracoes",
        data={
            "schedule": "daily", "time": "02:00", "weekday": "0",
            "retention_daily_days": "30", "retention_weekly_weeks": "12",
            "retention_monthly_months": "12", "keep_pre_restore": "0",
            "externo_dest_path": str(tmp_path),
        },
    )
    assert resp_cfg.status_code == 403

    resp_test = client.post(
        "/admin/backups/externo/testar",
        data={"dest_path": str(tmp_path)},
    )
    assert resp_test.status_code == 403


def test_testar_destino_valido_e_invalido(client, db_session, tmp_path):
    """§24: teste do destino cria/lê/remove temporário — sem backup."""
    # Válido
    resp_ok = client.post(
        "/admin/backups/externo/testar",
        data={"dest_path": str(tmp_path)},
        follow_redirects=False,
    )
    assert resp_ok.status_code == 303
    assert "success=" in resp_ok.headers["location"]

    # Inválido (caminho inexistente)
    resp_bad = client.post(
        "/admin/backups/externo/testar",
        data={"dest_path": str(tmp_path / "nao-existe")},
        follow_redirects=False,
    )
    assert resp_bad.status_code == 303
    assert "error=" in resp_bad.headers["location"]

    # Auditado como TESTADO (sucesso e falha)
    from app.services.audit_service import ACTION_BACKUP_DESTINO_EXTERNO_TESTADO

    logs = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == ACTION_BACKUP_DESTINO_EXTERNO_TESTADO)
        .all()
    )
    assert {log.result for log in logs} == {"SUCCESS", "FAILURE"}


def test_config_salva_persiste_e_tela_reflete(client, db_session, tmp_path):
    """Salvar config → singleton persiste; recarregar a página reflete."""
    resp = client.post(
        "/admin/backups/configuracoes",
        data={
            "schedule": "daily", "time": "02:00", "weekday": "0",
            "retention_daily_days": "30", "retention_weekly_weeks": "12",
            "retention_monthly_months": "12", "keep_pre_restore": "0",
            "externo_enabled": "on",
            "externo_dest_path": str(tmp_path),
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    row = external_backup_service.get_external_config(db_session)
    assert row.enabled is True
    assert row.dest_path == str(tmp_path)
    assert row.updated_by == "testuser"

    # Página reflete o singleton (fieldset + card Destino externo)
    page = client.get("/admin/backups")
    assert page.status_code == 200
    assert "Backup externo" in page.text
    assert "Destino externo" in page.text
    assert str(tmp_path) in page.text

    # Auditoria de configuração (quando alterada)
    from app.services.audit_service import ACTION_BACKUP_DESTINO_EXTERNO_CONFIGURADO

    assert (
        db_session.query(AuditLog)
        .filter(AuditLog.action == ACTION_BACKUP_DESTINO_EXTERNO_CONFIGURADO)
        .count()
        >= 1
    )


def test_flash_gerar_composto_local_e_externo(db_session, client, dest, monkeypatch):
    """§15: flash compõe \"Backup local: SUCESSO / Backup externo: ...\"."""
    _enable_external(db_session, dest)
    monkeypatch.setattr(backup_service, "SessionLocal", lambda: db_session,
                        raising=False)
    monkeypatch.setattr(backup_service, "_run_mysqldump", _fake_dump)

    resp = client.post("/admin/backups/gerar", follow_redirects=False)
    assert resp.status_code == 303
    from urllib.parse import unquote
    location = unquote(resp.headers["location"])
    assert "Backup local: SUCESSO" in location
    assert "Backup externo: SUCESSO" in location


def test_flash_gerar_composto_com_falha_externa(db_session, client, dest, monkeypatch):
    """§15: falha externa aparece no flash sem alterar o sucesso local."""
    import shutil

    _enable_external(db_session, dest)
    monkeypatch.setattr(backup_service, "SessionLocal", lambda: db_session,
                        raising=False)
    monkeypatch.setattr(backup_service, "_run_mysqldump", _fake_dump)
    shutil.rmtree(dest)  # destino indisponível

    resp = client.post("/admin/backups/gerar", follow_redirects=False)
    assert resp.status_code == 303
    from urllib.parse import unquote
    location = unquote(resp.headers["location"])
    assert "Backup local: SUCESSO" in location
    assert "Backup externo: FALHA" in location
    assert "destino indisponível" in location  # motivo controlado


def test_coluna_externo_no_historico(db_session, client, dest):
    """§4.2: coluna Externo com ✓/✗(motivo no title)/—."""
    from app.config import BACKUP_DIR

    # Backup externo OK
    _enable_external(db_session, dest)
    result = BackupService.generate_backup(db_session, None, None,
                                           dump_executor=_fake_dump)

    # Registro externo de falha SEM backup local correspondente (histórico puro)
    db_session.add(BackupExternalRecord(
        filename="backup_20260901_020000_999001.sql.gz",
        backup_type="AUTOMATICO", status="FAILURE",
        error_description="destino indisponível",
    ))
    db_session.commit()

    page = client.get("/admin/backups")
    assert page.status_code == 200
    assert "Externo" in page.text
    assert "✓" in page.text  # cópia validada
    assert 'title="destino indisponível"' in page.text  # motivo no title


# ============================================================================
# SC-007 — zero segredos em logs e auditoria (evidência automatizada)
# ============================================================================

def test_zero_segredos_em_logs(db_session, dest, monkeypatch, caplog):
    """A2/SC-007: nos cenários de falha E/F/G, nenhum log ou descrição de
    auditoria contém padrões de senha/credencial/token/segredo."""
    import logging
    import os
    import shutil
    import stat

    caplog.set_level(logging.DEBUG)

    # E — destino indisponível (some do SO)
    _enable_external(db_session, dest)
    shutil.rmtree(dest)
    result = BackupService.generate_backup(db_session, None, None,
                                           dump_executor=_fake_dump)
    assert result["external"]["external_status"] == "FAILURE"

    # F — sem permissão
    dest2 = dest.parent / "destino-sem-permissao"
    dest2.mkdir()
    _enable_external(db_session, dest2)
    os.chmod(dest2, stat.S_IRUSR | stat.S_IXUSR)
    try:
        result2 = BackupService.generate_backup(db_session, None, None,
                                                dump_executor=_fake_dump)
        assert result2["external"]["external_status"] == "FAILURE"
    finally:
        os.chmod(dest2, 0o755)
    shutil.rmtree(dest2)

    # G — hash divergente (novo destino vazio)
    dest3 = dest.parent / "destino-hash"
    dest3.mkdir()
    _enable_external(db_session, dest3)
    real_sha = external_backup_service._sha256_of

    def _sha_poisoned(path, *, deadline=None):
        digest = real_sha(path, deadline=deadline)
        if getattr(path, "name", "").endswith(".tmp"):
            return "f" * 64
        return digest

    monkeypatch.setattr(external_backup_service, "_sha256_of", _sha_poisoned)
    _enable_external(db_session, dest)
    result3 = BackupService.generate_backup(db_session, None, None,
                                            dump_executor=_fake_dump)
    assert result3["external"]["external_status"] == "FAILURE"

    # Nenhum padrão de segredo nos logs capturados
    for pattern in SECRET_PATTERNS:
        assert pattern.lower() not in caplog.text.lower()

    # Nenhum padrão de segredo nas descrições/audit data gravadas
    logs = db_session.query(AuditLog).all()
    for log in logs:
        blob = f"{log.description or ''} {log.new_data or ''}".lower()
        for pattern in SECRET_PATTERNS:
            assert pattern not in blob, f"padrão {pattern!r} vazou em auditoria"
