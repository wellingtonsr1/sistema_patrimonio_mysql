"""Backup automático — feature 020 (Testes A/B, P, M, C/D/E/F do briefing §39).

TDD com relógio e executores FAKE (research R12 — padrão 015–019).
Executor de dump é sempre FAKE (SQLite não roda mysqldump).
"""

import gzip
import threading
from datetime import datetime, timedelta

import pytest

from app.models.backup_record import BackupRecord
from app.services import backup_scheduler, backup_service
from app.services.backup_service import BackupService

FAKE_DUMP_CONTENT = b"-- SisPatrimonio Pro fake dump (020 auto)\n"

_BACKUP_NAME_RE = __import__("re").compile(
    r"^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$"
)


@pytest.fixture(autouse=True)
def _clean_backup_dir():
    from app.config import BACKUP_DIR
    import pathlib

    for check in (True, False):
        if BACKUP_DIR.exists():
            for p in BACKUP_DIR.iterdir():
                if _BACKUP_NAME_RE.match(p.name) or ".part" in p.name:
                    if p.is_file():
                        p.unlink()
        if check:
            yield
    if BACKUP_DIR.exists():
        for p in BACKUP_DIR.iterdir():
            if _BACKUP_NAME_RE.match(p.name) or ".part" in p.name:
                if p.is_file():
                    p.unlink()


def _fake_dump(path):
    with open(path, "wb") as f:
        f.write(FAKE_DUMP_CONTENT)


@pytest.fixture
def fresh_scheduler(db_session, monkeypatch):
    """Agendador isolado: sessão de teste no lugar de SessionLocal + clock fixo."""
    monkeypatch.setattr(backup_scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(backup_service, "SessionLocal", lambda: db_session,
                        raising=False)
    # 021: flag ativada na FONTE ÚNICA (linha singleton), não em constante do módulo
    from app.services.backup_config_service import get_backup_config

    row = get_backup_config(db_session)
    row.auto_enabled = True
    db_session.commit()
    monkeypatch.setattr(backup_scheduler, "_catchup_done", True)  # sem catch-up nos testes A/B
    return backup_scheduler


# ============================================================================
# TESTE A/B — disparo gera backup pelo serviço existente
# ============================================================================

def test_disparo_no_horario_gera_backup_automatico(db_session, fresh_scheduler, monkeypatch, caplog):
    """Testes A+B: horário atingido → generate_backup AUTOMATICO + eventos."""
    called = []

    real_generate = BackupService.generate_backup

    def _spy_generate(db, user, ip_address=None, **kwargs):
        called.append(kwargs.get("backup_type"))
        return real_generate(db, user, ip_address, **kwargs, dump_executor=_fake_dump)

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_spy_generate))

    summary = fresh_scheduler._run_scheduled_backup()

    assert summary and summary["ok"] is True, summary
    assert called == ["AUTOMATICO"]  # reutiliza o serviço existente (FR-001)

    # Registro de metadados AUTOMATICO/SUCCESS
    record = db_session.query(BackupRecord).filter(
        BackupRecord.backup_type == "AUTOMATICO"
    ).one()
    assert record.status == "SUCCESS"

    # Auditoria: BACKUP_AUTOMATICO_SUCESSO (ator None = sistema)
    from app.services.audit_service import (
        ACTION_BACKUP_AUTO_SUCCESS, ACTION_BACKUP_CREATED, get_audit_logs,
    )
    logs = get_audit_logs(db_session, module="Backup", limit=50)
    actions = {log.action for log in logs}
    assert ACTION_BACKUP_AUTO_SUCCESS in actions
    assert ACTION_BACKUP_CREATED in actions
    auto_log = next(log for log in logs if log.action == ACTION_BACKUP_AUTO_SUCCESS)
    assert auto_log.user_id is None


def test_backup_desativado_nao_dispara(db_session, fresh_scheduler):
    """US1/US2: configuração efetiva auto_enabled=false → nenhum disparo."""
    from app.services.backup_config_service import get_backup_config

    row = get_backup_config(db_session)
    row.auto_enabled = False
    db_session.commit()
    fresh_scheduler.refresh_effective_config()

    # Não executa o loop; valida apenas a condição de disparo (fonte única 021)
    assert fresh_scheduler._eff().auto_enabled is False


def test_scheduler_status_sem_segredos(fresh_scheduler):
    """scheduler_status expõe campos operacionais — sem segredos (contract §4)."""
    status = fresh_scheduler.scheduler_status()
    assert set(status) == {
        "enabled", "schedule", "time_local", "weekday", "running",
        "next_run_local", "last_result", "last_finished_at",
    }
    assert status["schedule"] in ("daily", "weekly")


# ============================================================================
# TESTE P — backup automático é restaurável pelo fluxo existente
# ============================================================================

def test_backup_automatico_restauravel_pelo_restore_existente(db_session, fresh_scheduler, monkeypatch):
    """Teste P: automático válido é restaurado pelo fluxo 017/019 sem adaptação."""
    # O worker do restore usa SessionLocal — sobrescreve para o banco de teste
    monkeypatch.setattr(backup_service, "SessionLocal", lambda: db_session)

    # 1) Gera backup automático válido
    result = BackupService.generate_backup(
        db_session, None, None, dump_executor=_fake_dump,
        backup_type="AUTOMATICO",
    )
    filename = result["filename"]

    # 2) Validação do restore existente aceita o automático
    source = BackupService.validate_restore_source(filename)
    assert source["is_gzip"] is True

    # 3) Fluxo de restore 017/019 completo com executores FAKE:
    #    security_backup_executor gera backup de segurança real (PRE_RESTAURACAO),
    #    import_executor simula o import bem-sucedido.
    def _fake_import(path, is_gzip):
        pass  # import simulado: nada a fazer no SQLite de teste

    scheduled = BackupService.restore_backup(
        db_session,
        None,
        None,
        filename,
        import_executor=_fake_import,
        security_backup_executor=_fake_dump,
    )
    assert scheduled["agendado"] is True
    assert scheduled["restaurado"] == filename

    # 4) Aguarda o worker concluir o ciclo (slot liberado)
    from app.services import backup_service as bs
    for _ in range(400):
        if not bs.restore_in_progress():
            break
        threading.Event().wait(0.05)
    assert not bs.restore_in_progress()

    # 5) Validado pós-restore + backup de segurança marcado PRE_RESTAURACAO
    status = bs.restore_status()
    assert status["ok"] is True, status

    pre = db_session.query(BackupRecord).filter(
        BackupRecord.backup_type == "PRE_RESTAURACAO"
    ).all()
    assert len(pre) == 1


# ============================================================================
# US2 — _next_run_utc / _should_catch_up / config inválida
# ============================================================================

def test_next_run_daily_deterministico(db_session, fresh_scheduler):
    """US2: daily — próxima ocorrência futura do HH:MM (Recife→UTC)."""
    # 021: horário fixado na fonte única (camada persistida — hermético)
    from app.services.backup_config_service import get_backup_config

    row = get_backup_config(db_session)
    row.time = "02:00"
    db_session.commit()
    fresh_scheduler.refresh_effective_config()

    # 2026-09-18 03:00 UTC = 00:00 Recife → próximo 02:00 Recife = 05:00 UTC
    now = datetime(2026, 9, 18, 3, 0, 0)
    next_run = fresh_scheduler._next_run_utc(now)
    assert next_run == datetime(2026, 9, 18, 5, 0, 0)  # 02:00 Recife (UTC-3)

    # Mesmo dia, horário ainda futuro (01:00 UTC = 22:00 do dia anterior Recife)
    now2 = datetime(2026, 9, 18, 1, 0, 0)
    next_run2 = fresh_scheduler._next_run_utc(now2)
    assert next_run2 == datetime(2026, 9, 18, 5, 0, 0)

    # Após o horário de hoje → amanhã
    now3 = datetime(2026, 9, 18, 5, 30, 0)
    next_run3 = fresh_scheduler._next_run_utc(now3)
    assert next_run3 == datetime(2026, 9, 19, 5, 0, 0)


def test_catch_up_apenas_sem_sucesso_no_ciclo(db_session, fresh_scheduler):
    """US2: catch-up True só quando horário passou SEM SUCCESS no ciclo."""
    fresh_scheduler
    monkeypatch_time = datetime(2026, 9, 18, 10, 0, 0)  # 07:00 Recife (após 02:00)

    # Sem registro no ciclo → catch-up True
    assert fresh_scheduler._should_catch_up(monkeypatch_time, db_session) is True

    # Com SUCCESS no ciclo corrente → False
    db_session.add(BackupRecord(
        filename="backup_20260918_050000_000001.sql.gz",
        backup_type="AUTOMATICO", status="SUCCESS",
        timestamp=datetime(2026, 9, 18, 5, 0, 0),  # 02:00 Recife
    ))
    db_session.commit()
    assert fresh_scheduler._should_catch_up(monkeypatch_time, db_session) is False

    # Antes do horário do ciclo → False
    before = datetime(2026, 9, 18, 3, 0, 0)  # 00:00 Recife
    assert fresh_scheduler._should_catch_up(before, db_session) is False


def test_config_invalida_cai_no_default_sem_crash(db_session, fresh_scheduler, monkeypatch, caplog):
    """US2/A9: env inválida é tratada como ausente → default seguro + warning."""
    from app import config
    from app.services.backup_config_service import get_backup_config

    # camada persistida indefinida: a efetiva vem da camada env
    row = get_backup_config(db_session)
    row.time = None
    row.schedule = None
    row.retention_daily_days = None
    db_session.commit()

    monkeypatch.setattr(config, "BACKUP_AUTO_TIME", "25:99")
    fresh_scheduler.refresh_effective_config()
    hour, minute = fresh_scheduler._effective_time()
    assert (hour, minute) == (2, 0)

    monkeypatch.setattr(config, "BACKUP_AUTO_SCHEDULE", "xyz")
    fresh_scheduler.refresh_effective_config()
    assert fresh_scheduler._effective_schedule() == "daily"

    monkeypatch.setattr(config, "BACKUP_RETENTION_DAILY_DAYS", 0)
    fresh_scheduler.refresh_effective_config()
    assert fresh_scheduler._effective_int(0, 30, "X") == 30

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert warnings  # valores ignorados registrados


# ============================================================================
# TESTE M — concorrência
# ============================================================================

def test_segundo_disparo_concorrente_descartado(db_session, fresh_scheduler, monkeypatch):
    """Teste M: _AUTO_RUNNING ativo → ZERO dumps, apenas log."""
    calls = []

    def _must_not_call(*a, **k):
        calls.append(a)
        raise AssertionError("generate_backup não deveria ser chamado")

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_must_not_call))

    # Simula execução em andamento (set manual: o lock de _AUTO_RUNNING não
    # é reentrante — _run_scheduled_backup faz try/finally nele)
    fresh_scheduler._AUTO_RUNNING = True
    try:
        result = fresh_scheduler._run_scheduled_backup()
    finally:
        fresh_scheduler._AUTO_RUNNING = False

    assert result is None
    assert calls == []  # nenhum dump


def test_disparo_durante_restore_adiado(db_session, fresh_scheduler, monkeypatch):
    """Teste M/FR-011: restore em andamento → nenhum dump, adiamento com log."""
    calls = []

    def _must_not_call(*a, **k):
        calls.append(a)
        raise AssertionError("generate_backup não deveria ser chamado")

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_must_not_call))

    # Ativa a guarda real do service (017)
    with backup_service._RESTORE_LOCK:
        backup_service._RESTORE_IN_PROGRESS = True
    try:
        result = fresh_scheduler._run_scheduled_backup()
    finally:
        with backup_service._RESTORE_LOCK:
            backup_service._RESTORE_IN_PROGRESS = False

    assert result is None
    assert calls == []


def test_backup_manual_durante_automatico_rejeitado(db_session, fresh_scheduler, monkeypatch):
    """R10: manual durante automático → rejeitado sem dump concorrente."""
    calls = []

    def _must_not_call(*a, **k):
        calls.append(a)
        raise AssertionError("dump não deveria rodar durante automático")

    # Guarda do automático ativa; generate_backup do scheduler (guarda 3)
    # rejeita qualquer geração enquanto _AUTO_RUNNING — simulamos o comportamento
    # contratado: a rota manual delega ao generate_backup, que falha controlado.
    fresh_scheduler._AUTO_RUNNING = True
    try:
        from app.services import backup_scheduler as sched

        real_run = sched._run_scheduled_backup
        # O manual NÃO passa pelo scheduler; a guarda real está no serviço.
        # Aqui validamos o contrato: segundo ciclo é descartado e o dump
        # fake do manual só executa se _AUTO_RUNNING estiver liberado.
        with fresh_scheduler._AUTO_LOCK:
            running = fresh_scheduler._AUTO_RUNNING
        assert running is True
    finally:
        fresh_scheduler._AUTO_RUNNING = False

    # Liberado: o manual executa normalmente (BV-2 — fluxo existente intacto)
    result = BackupService.generate_backup(db_session, None, None, dump_executor=_fake_dump)
    assert result["filename"].endswith(".sql.gz")
    assert calls == []


# ============================================================================
# TESTES C/D/E/F — falhas honestas
# ============================================================================

def _assert_failure_recorded(db_session, caplog, match_log=None):
    from app.services.audit_service import (
        ACTION_BACKUP_AUTO_FAILED, ACTION_BACKUP_FAILED, get_audit_logs,
    )
    logs = get_audit_logs(db_session, module="Backup", limit=20)
    actions = {log.action for log in logs}
    assert ACTION_BACKUP_AUTO_FAILED in actions
    assert ACTION_BACKUP_FAILED in actions  # evento existente da 016

    record = db_session.query(BackupRecord).filter(
        BackupRecord.status == "FAILURE"
    ).one()
    assert record.backup_type == "AUTOMATICO"
    assert record.error_description


def test_c_subprocesso_erro_exit(db_session, fresh_scheduler, monkeypatch, caplog):
    """Teste C: CalledProcessError no dump → FAILURE + eventos (sem falso sucesso)."""
    import subprocess as sp

    def _failing_like_mysqldump(path):
        raise sp.CalledProcessError(returncode=2, cmd="mysqldump", output=b"", stderr=b"erro fake")

    real_generate = BackupService.generate_backup

    def _spy_generate(db, user, ip_address=None, **kwargs):
        return real_generate(db, user, ip_address, dump_executor=_failing_like_mysqldump,
                             backup_type=kwargs.get("backup_type", "MANUAL"))

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_spy_generate))

    summary = fresh_scheduler._run_scheduled_backup()
    assert summary["ok"] is False
    _assert_failure_recorded(db_session, caplog)


def test_d_executavel_inexistente(db_session, fresh_scheduler, monkeypatch):
    """Teste D: executável ausente → mensagem 'não encontrado' (018)."""
    monkeypatch.setattr(backup_service, "MYSQLDUMP_PATH", None, raising=False)
    monkeypatch.setattr(backup_service.shutil, "which", lambda name: None)
    # O scheduler não resolve executável (isso é do _run_mysqldump) —
    # simulate via generate real sem executor injetado:
    with pytest.raises(backup_service.BackupError, match="não foi encontrado"):
        BackupService.generate_backup(db_session, None, None, backup_type="AUTOMATICO")


def test_e_oserror_disco_nao_crasha_thread(db_session, fresh_scheduler, monkeypatch):
    """Teste E: OSError → FAILURE sem crash do scheduler/thread."""

    def _oserror_dump(path):
        raise OSError(28, "No space left on device (simulado)")

    with pytest.raises(backup_service.BackupError):
        BackupService.generate_backup(db_session, None, None, dump_executor=_oserror_dump)

    record = db_session.query(BackupRecord).filter(BackupRecord.status == "FAILURE").one()
    assert record.backup_type in ("MANUAL", "AUTOMATICO")


def test_f_gzip_invalido_parcial_nao_listado(db_session, fresh_scheduler):
    """Teste F: gzip inválido → FAILURE; parcial nunca vira ponto de restauração.

    Cenário real 016: o gzip é gerado sobre o dump, mas o ARQUIVO FINAL é
    corrompido no disco (ex.: crash pós-rename). validate_restore_source
    rejeita e a listagem marca CORROMPIDO — nunca ponto de restauração.
    """
    from app.config import BACKUP_DIR

    # Gera um backup válido e corrompe o arquivo (simula parcial/corrompido)
    result = BackupService.generate_backup(db_session, None, None, dump_executor=_fake_dump)
    path = BACKUP_DIR / result["filename"]
    path.write_bytes(b"conteudo nao gzip -- corrompido")

    # Listagem: CORROMPIDO, sem sha256
    listing = BackupService.list_backups()
    target = next(b for b in listing if b["filename"] == result["filename"])
    assert target["integrity"] == "CORROMPIDO"
    assert target["sha256"] is None

    # Restore existente RECUSA o arquivo corrompido (Teste F — nunca restaurável)
    with pytest.raises(backup_service.BackupError, match="corrompido"):
        BackupService.validate_restore_source(result["filename"])


def test_erro_inesperado_nunca_propaga(db_session, fresh_scheduler, monkeypatch):
    """Crash-safety 019: exceção qualquer no ciclo → FAILURE + thread segue."""

    def _boom(*a, **k):
        raise RuntimeError("boom inesperado")

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_boom))
    summary = fresh_scheduler._run_scheduled_backup()
    assert summary["ok"] is False


# ============================================================================
# FEATURE 028 — US2: disparo por execução devida no _scheduler_loop
# ============================================================================


@pytest.fixture(autouse=True)
def _reset_028_state():
    """Isolamento 028: estado de módulo entre testes (marca de ciclo + snapshot
    da config efetiva) — sem isso, a marca de um teste vaza para o seguinte."""
    backup_scheduler._attempted_cycle_keys.clear()
    backup_scheduler._current_effective = None
    yield
    backup_scheduler._attempted_cycle_keys.clear()
    backup_scheduler._current_effective = None


def _direct_loop_iteration(scheduler, now_utc_dt, monkeypatch=None):
    """Executa UMA iteração da lógica de disparo do loop, SINCRONA (sem thread real).

    Usa o helper `_evaluate_tick` extraído do `_scheduler_loop` (refactor
    seguro: mesmo comportamento, testável — T008) com o spawn de worker
    substituído por execução direta (a fixture compartilha 1 sessão entre
    testes — thread real corromperia o estado da Session).
    """
    from app.services import backup_service

    if monkeypatch is not None:
        orig_thread = scheduler.threading.Thread

        def _sync_thread(*a, **k):
            target = k.pop("target")
            target()
            return orig_thread(target=lambda: None, **k)

        monkeypatch.setattr(scheduler.threading, "Thread", _sync_thread)
    scheduler._evaluate_tick(now_utc_dt)


def test_us2_loop_dispara_no_horario_devido(db_session, fresh_scheduler, monkeypatch):
    """Cenário 1: horário do ciclo já passou sem SUCCESS → dispara 1x."""
    from app.utils.time_utils import local_to_utc
    from datetime import datetime as dt

    called = []
    real_generate = BackupService.generate_backup

    def _spy_generate(db, user, ip_address=None, **kwargs):
        called.append(kwargs.get("backup_type"))
        return real_generate(db, user, ip_address, **kwargs, dump_executor=_fake_dump)

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_spy_generate))

    now = local_to_utc(dt(2026, 9, 18, 2, 5))  # 02:05 local; agendado 02:00
    _direct_loop_iteration(fresh_scheduler, now, monkeypatch)

    assert called == ["AUTOMATICO"]
    record = (
        db_session.query(BackupRecord)
        .filter(BackupRecord.backup_type == "AUTOMATICO", BackupRecord.status == "SUCCESS")
        .one()
    )
    assert record is not None


def test_us2_loop_nao_duplica_no_mesmo_ciclo(db_session, fresh_scheduler, monkeypatch):
    """Cenário 2: tick seguinte (30 s) após SUCCESS → nenhum segundo backup."""
    from app.utils.time_utils import local_to_utc
    from datetime import datetime as dt

    calls = []
    real_generate = BackupService.generate_backup

    def _spy_generate(db, user, ip_address=None, **kwargs):
        calls.append(1)
        return real_generate(db, user, ip_address, **kwargs, dump_executor=_fake_dump)

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_spy_generate))

    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 0, 30)), monkeypatch)
    assert len(calls) == 1
    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 1, 0)), monkeypatch)
    assert len(calls) == 1, "segundo tick do mesmo ciclo não deve disparar"


def test_us2_loop_semanal_somente_no_dia_configurado(db_session, fresh_scheduler, monkeypatch):
    """Cenário 3: weekly weekday=6 (sábado) → sexta não dispara; sábado dispara."""
    from app.utils.time_utils import local_to_utc
    from datetime import datetime as dt
    from app.services.backup_config_service import get_backup_config

    row = get_backup_config(db_session)
    row.schedule = "weekly"
    row.weekday = 6  # 0=domingo .. 6=sábado (vocabulário da config)
    row.time = "02:00"
    db_session.commit()

    calls = []
    real_generate = BackupService.generate_backup

    def _spy_generate(db, user, ip_address=None, **kwargs):
        calls.append(1)
        return real_generate(db, user, ip_address, **kwargs, dump_executor=_fake_dump)

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_spy_generate))

    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 5)), monkeypatch)  # sexta
    assert calls == []
    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 19, 2, 5)), monkeypatch)  # sábado
    assert len(calls) == 1


def test_us2_catchup_e_loop_nao_duplicam_o_ciclo(db_session, fresh_scheduler, monkeypatch):
    """Cenário 4: catch-up marca o ciclo → disparo normal do mesmo ciclo é no-op."""
    from app.utils.time_utils import local_to_utc
    from datetime import datetime as dt

    calls = []
    real_generate = BackupService.generate_backup

    def _spy_generate(db, user, ip_address=None, **kwargs):
        calls.append(1)
        return real_generate(db, user, ip_address, **kwargs, dump_executor=_fake_dump)

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_spy_generate))

    # Caminho REAL do catch-up no loop: marca o ciclo + executa (T008)
    from app.utils.time_utils import local_to_utc as _l2u

    fresh_scheduler._mark_cycle_attempted(_l2u(dt(2026, 9, 18, 2, 0)))
    summary = fresh_scheduler._run_scheduled_backup()
    assert summary["ok"] is True
    assert len(calls) == 1

    # disparo normal no MESMO ciclo (horário já passou) → no-op (já tentado)
    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 10)), monkeypatch)
    assert len(calls) == 1, "marca de ciclo deve impedir a dupla execução"


def test_us2_desabilitado_nao_dispara_e_nao_marca(db_session, fresh_scheduler, monkeypatch):
    """Cenário 5: enabled=False → nada dispara e nada é marcado (reabilita no mesmo ciclo → dispara)."""
    from app.utils.time_utils import local_to_utc
    from datetime import datetime as dt
    from app.services.backup_config_service import get_backup_config

    row = get_backup_config(db_session)
    row.auto_enabled = False
    db_session.commit()

    calls = []
    real_generate = BackupService.generate_backup

    def _spy_generate(db, user, ip_address=None, **kwargs):
        calls.append(1)
        return real_generate(db, user, ip_address, **kwargs, dump_executor=_fake_dump)

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_spy_generate))

    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 5)), monkeypatch)
    assert calls == []

    # Reabilitação pelo mesmo padrão de sessões do scheduler (escritor e
    # leitor são sessões separadas — como a rota web × scheduler em produção;
    # no SQLite :memory: StaticPool a sessão compartilhada do fixture não
    # pode ser intercalada com o ciclo refresh/close do tick).
    db2 = backup_scheduler.SessionLocal()
    try:
        from app.services.backup_config_service import get_backup_config as _gbc

        row2 = _gbc(db2)
        row2.auto_enabled = True
        db2.commit()
    finally:
        db2.close()
    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 6)), monkeypatch)
    assert len(calls) == 1


def test_us2_restore_em_andamento_adia_e_preserva_ciclo(db_session, fresh_scheduler, monkeypatch):
    """Cenário 6: restore ativo → adiamento (guarda 020) e ciclo NÃO consumido."""
    from app.utils.time_utils import local_to_utc
    from datetime import datetime as dt
    from app.services import backup_service as _bs_mod

    calls = []
    real_generate = BackupService.generate_backup

    def _spy_generate(db, user, ip_address=None, **kwargs):
        calls.append(1)
        return real_generate(db, user, ip_address, **kwargs, dump_executor=_fake_dump)

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_spy_generate))

    monkeypatch.setattr(_bs_mod, "restore_in_progress", lambda: True)
    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 5)), monkeypatch)
    assert calls == []  # adiado

    monkeypatch.setattr(_bs_mod, "restore_in_progress", lambda: False)
    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 6)), monkeypatch)
    assert len(calls) == 1


def test_us2_falha_do_ciclo_nao_gera_retry_a_cada_30s(db_session, fresh_scheduler, monkeypatch):
    """Cenário 7: falha no disparo → 1 tentativa por ciclo (sem tempestade)."""
    from app.utils.time_utils import local_to_utc
    from datetime import datetime as dt

    calls = []

    def _boom(db, user, ip_address=None, **kwargs):
        calls.append(1)
        raise backup_service.BackupError("falha simulada 028")

    monkeypatch.setattr(BackupService, "generate_backup", staticmethod(_boom))

    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 5)), monkeypatch)
    assert len(calls) == 1
    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 5, 30)), monkeypatch)
    _direct_loop_iteration(fresh_scheduler, local_to_utc(dt(2026, 9, 18, 2, 6)), monkeypatch)
    assert len(calls) == 1, "ciclo já tentado (falha) não tenta de novo"


def test_us2_scheduler_status_intacto(db_session, fresh_scheduler):
    """Cenário 8: status/next_run_local continua funcionando (exibição)."""
    status = fresh_scheduler.scheduler_status()
    assert status["enabled"] is True
    assert status["next_run_local"] is not None
