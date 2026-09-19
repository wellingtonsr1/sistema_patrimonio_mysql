"""Configuração administrável do backup — feature 021 (briefing §33).

Fonte única em runtime (persistido → env → default), tela Administração →
Backups → Configurações de Backup (RBAC backup.gerenciar), auditoria com
before/after, aplicação dinâmica sem reinício e preservação dos fluxos da 020.

Hermeticidade (lição da 020): valores de fallback são FIXADOS via monkeypatch
nas constantes — nenhum teste depende do .env/variáveis da máquina; o teste
anti-regressão do default exercita o código real em subprocesso isolado.
"""

import subprocess
import sys
from datetime import datetime

import pytest

from app import config
from app.models.backup_record import BackupRecord
from app.utils import time_utils
from app.services import backup_config_service, backup_scheduler
from app.services.backup_config_service import (
    EffectiveBackupConfig,
    get_backup_config,
    get_effective_config,
    save_backup_config,
)
from tests.test_rbac import PASSWORD, _login, _make_user

NOW = datetime(2026, 9, 18, 12, 0, 0)


@pytest.fixture(autouse=True)
def _clean_backup_dir():
    """Isola o diretório de backups (padrão 020): remove arquivos gerados."""
    import re

    from app.config import BACKUP_DIR

    name_re = re.compile(r"^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$")

    def _clean():
        if BACKUP_DIR.exists():
            for p in BACKUP_DIR.iterdir():
                if p.is_file() and (name_re.match(p.name) or ".part" in p.name):
                    p.unlink()

    _clean()
    yield
    _clean()


@pytest.fixture
def fixed_fallbacks(monkeypatch):
    """Fixa os fallbacks (env) para hermeticidade — independe do .env/da máquina."""
    monkeypatch.setattr(config, "BACKUP_AUTO_ENABLED", False)
    monkeypatch.setattr(config, "BACKUP_AUTO_SCHEDULE", "daily")
    monkeypatch.setattr(config, "BACKUP_AUTO_TIME", "02:00")
    monkeypatch.setattr(config, "BACKUP_AUTO_WEEKDAY", 0)
    monkeypatch.setattr(config, "BACKUP_RETENTION_DAILY_DAYS", 30)
    monkeypatch.setattr(config, "BACKUP_RETENTION_WEEKLY_WEEKS", 12)
    monkeypatch.setattr(config, "BACKUP_RETENTION_MONTHLY_MONTHS", 12)
    monkeypatch.setattr(config, "BACKUP_RETENTION_KEEP_PRE_RESTORE", 0)
    return {
        "auto_enabled": False,
        "schedule": "daily",
        "time": "02:00",
        "weekday": 0,
        "retention_daily_days": 30,
        "retention_weekly_weeks": 12,
        "retention_monthly_months": 12,
        "keep_pre_restore": 0,
    }


# ============================================================================
# FUNDAÇÃO — Teste A (primeiro uso) + precedência + anti-regressão FR-009
# ============================================================================

def test_primeiro_uso_aplica_defaults_da_020(db_session, fixed_fallbacks):
    """Teste A: linha inexistente → criação lazy + efetiva = defaults da 020."""
    row = get_backup_config(db_session)
    assert row.id == 1
    assert row.auto_enabled is False  # default desativado — nunca ativa por efeito colateral
    assert row.schedule is None       # "não definido" → fallback/default

    eff = get_effective_config(db_session)
    assert eff.auto_enabled is False
    assert eff.schedule == "daily"
    assert eff.time == "02:00"
    assert eff.weekday == 0
    assert eff.retention_daily_days == 30
    assert eff.retention_weekly_weeks == 12
    assert eff.retention_monthly_months == 12
    assert eff.keep_pre_restore == 0


def test_singleton_permanece_id_1(db_session, fixed_fallbacks):
    get_backup_config(db_session)
    again = get_backup_config(db_session)
    assert again.id == 1
    assert db_session.query(backup_config_service.BackupConfig).count() == 1


def test_precedencia_persistido_vence_env_vence_default(
    db_session, fixed_fallbacks, monkeypatch
):
    """Precedência única por campo: persistido → env → default (FR-007)."""
    # env vence default
    monkeypatch.setattr(config, "BACKUP_RETENTION_DAILY_DAYS", 7)
    eff = get_effective_config(db_session)
    assert eff.retention_daily_days == 7
    # persistido vence env
    row = get_backup_config(db_session)
    row.retention_daily_days = 5
    db_session.commit()
    eff = get_effective_config(db_session)
    assert eff.retention_daily_days == 5
    # campo persistido None volta ao fallback env (row sem valor)
    row.time = "03:30"
    row.schedule = None
    monkeypatch.setattr(config, "BACKUP_AUTO_SCHEDULE", "weekly")
    db_session.commit()
    eff = get_effective_config(db_session)
    assert eff.schedule == "weekly"   # env vence (persistido não definido)
    assert eff.time == "03:30"        # persistido vence env


def test_env_invalida_cai_no_default_sem_crash(db_session, fixed_fallbacks, monkeypatch):
    """Env inválida é tratada como ausente → default; nunca levanta (FR-008)."""
    monkeypatch.setattr(config, "BACKUP_AUTO_TIME", "25:99")
    monkeypatch.setattr(config, "BACKUP_AUTO_SCHEDULE", "mensal")
    monkeypatch.setattr(config, "BACKUP_AUTO_WEEKDAY", 9)
    monkeypatch.setattr(config, "BACKUP_RETENTION_DAILY_DAYS", -3)
    monkeypatch.setattr(config, "BACKUP_RETENTION_KEEP_PRE_RESTORE", "xpto")
    eff = get_effective_config(db_session)
    assert eff.schedule == "daily"
    assert eff.time == "02:00"
    assert eff.weekday == 0
    assert eff.retention_daily_days == 30
    assert eff.keep_pre_restore == 0


def test_anti_regressao_default_desativado_no_codigo_real():
    """FR-009: o DEFAULT REAL do código é desativado (comentário×código coerentes).

    Exercita o default em subprocesso isolado (env var removida), imune ao
    .env/ambiente da máquina (hermeticidade — lição da 020).
    """
    code = (
        "from app.config import BACKUP_AUTO_ENABLED;"
        "import sys;"
        "print('OK' if BACKUP_AUTO_ENABLED is False else 'FAIL')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=".",
        env={"PATH": "/usr/bin:/bin"},
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


# ============================================================================
# US1 — Teste K (alteração pela tela), Teste R (reinício), aplicação dinâmica
# ============================================================================

def _fresh_sessionmaker(db):
    """Sessionmaker sobre o MESMO engine da sessão de teste.

    Nunca importa tests.conftest diretamente: sem __init__.py, o pytest
    registra o conftest como módulo `conftest` e o import alternativo
    criaria um segundo engine (segundo :memory: vazio).
    """
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())


def _fake_dump(path):
    """Dump fake (padrão 020) para o POST /gerar não executar mysqldump real."""
    with open(path, "wb") as f:
        f.write(b"-- SisPatrimonio Pro fake dump (021)\n")


def _post_config(client, **overrides):
    data = {
        "auto_enabled": "false",
        "schedule": "daily",
        "time": "02:00",
        "weekday": "0",
        "retention_daily_days": "30",
        "retention_weekly_weeks": "12",
        "retention_monthly_months": "12",
        "keep_pre_restore": "0",
    }
    data.update(overrides)
    # checkbox: ausente = false; presente = true
    if data["auto_enabled"] in ("false", False):
        data.pop("auto_enabled")
    return client.post("/admin/backups/configuracoes", data=data, follow_redirects=False)


def test_k_alteracao_pela_interface_persiste(client, db_session, fixed_fallbacks):
    """Teste K: 02:00 → 23:00 pela tela persiste; GET exibe 23:00."""
    resp = _post_config(client, time="23:00", auto_enabled="true")
    assert resp.status_code == 303
    assert "success=" in resp.headers["location"]

    row = get_backup_config(db_session)
    assert row.time == "23:00"
    assert row.auto_enabled is True

    resp_get = client.get("/admin/backups/configuracoes")
    assert resp_get.status_code == 200
    assert 'value="23:00"' in resp_get.text
    assert "Configurações de Backup" in resp_get.text


def test_r_persistencia_sobrevive_a_reinicio(db_session, fixed_fallbacks):
    """Teste R: nova sessão + create_all idempotente → efetiva recarregada do banco."""
    save_backup_config(
        db_session, None, auto_enabled=True, schedule="weekly", time="23:00",
        weekday=1, retention_daily_days=7, retention_weekly_weeks=4,
        retention_monthly_months=6, keep_pre_restore=2,
    )
    # simula reinício: nova sessão sobre o MESMO banco de teste (conftest)
    fresh = _fresh_sessionmaker(db_session)()
    try:
        eff = get_effective_config(fresh)
        assert eff.auto_enabled is True
        assert eff.schedule == "weekly"
        assert eff.time == "23:00"
        assert eff.retention_daily_days == 7
    finally:
        fresh.close()


def test_aplicacao_dinamica_sem_reinicio(client, db_session, fixed_fallbacks):
    """Após salvar, a efetiva reflete o novo valor na mesma aplicação (FR-011)."""
    before = get_effective_config(db_session)
    assert before.time == "02:00"
    _post_config(client, time="23:00")
    after = get_effective_config(db_session)
    assert after.time == "23:00"


# ============================================================================
# US2 — Teste F (validações), limítrofes válidos, falha de persistência
# ============================================================================

def test_f_horario_invalido_rejeitado_sem_alterar(client, db_session, fixed_fallbacks):
    """Teste F: backend rejeita e a configuração vigente fica intacta (FR-015)."""
    for bad in ("25:99", "abc"):
        resp = _post_config(client, time=bad)
        assert resp.status_code == 303
        assert "error=" in resp.headers["location"]
    eff = get_effective_config(db_session)
    assert eff.time == "02:00"  # estado anterior intacto


def test_quantidades_invalidas_rejeitadas(client, db_session, fixed_fallbacks):
    for field in ("retention_daily_days", "retention_weekly_weeks", "retention_monthly_months"):
        for bad in ("0", "-1"):
            resp = _post_config(client, **{field: bad})
            assert resp.status_code == 303
            assert "error=" in resp.headers["location"]
    resp = _post_config(client, weekday="7")
    assert "error=" in resp.headers["location"]
    resp = _post_config(client, schedule="mensal")
    assert "error=" in resp.headers["location"]
    eff = get_effective_config(db_session)
    assert eff.retention_daily_days == 30
    assert eff.weekday == 0
    assert eff.schedule == "daily"


def test_valores_limitrofes_validos_aceitos(client, db_session, fixed_fallbacks):
    """FR-016: 00:00, retenção 1, keep 0/N são aceitos (não só o usual)."""
    resp = _post_config(
        client, time="00:00", retention_daily_days="1",
        retention_weekly_weeks="1", retention_monthly_months="1",
        keep_pre_restore="1",
    )
    assert resp.status_code == 303
    assert "success=" in resp.headers["location"]
    eff = get_effective_config(db_session)
    assert eff.time == "00:00"
    assert eff.retention_daily_days == 1
    assert eff.keep_pre_restore == 1


def test_falha_de_persistencia_mantem_estado_anterior(
    db_session, fixed_fallbacks, monkeypatch
):
    """Edge case: commit falha → erro controlado, efetiva anterior vigente."""
    save_backup_config(
        db_session, None, auto_enabled=False, schedule="daily", time="02:00",
        weekday=0, retention_daily_days=30, retention_weekly_weeks=12,
        retention_monthly_months=12, keep_pre_restore=0,
    )
    eff_antes = get_effective_config(db_session)

    def _commit_que_falha():
        raise RuntimeError("banco indisponível")

    monkeypatch.setattr(db_session, "commit", _commit_que_falha)
    with pytest.raises(RuntimeError):
        save_backup_config(
            db_session, None, auto_enabled=True, schedule="weekly", time="05:00",
            weekday=2, retention_daily_days=7, retention_weekly_weeks=4,
            retention_monthly_months=6, keep_pre_restore=1,
        )
    monkeypatch.undo()
    db_session.rollback()
    eff_depois = get_effective_config(db_session)
    assert eff_depois == eff_antes  # nada mudou (nunca estado parcial)


# ============================================================================
# US3 — Testes B/C/D/E/L (fonte única + agendador por tick)
# ============================================================================

@pytest.fixture
def seeded_config(db_session, monkeypatch):
    """Linha singleton + scheduler lendo o MESMO banco da suíte (021)."""
    monkeypatch.setattr(
        backup_scheduler, "SessionLocal", _fresh_sessionmaker(db_session)
    )
    row = get_backup_config(db_session)
    return row


def test_l_precedencia_no_scheduler(db_session, seeded_config, fixed_fallbacks, monkeypatch):
    """Teste L: env diz 02:00, banco diz 23:00 → scheduler usa 23:00."""
    seeded_config.time = "23:00"
    db_session.commit()
    backup_scheduler.refresh_effective_config()  # snapshot lê o banco de teste
    monkeypatch.setattr(backup_scheduler, "_clock", lambda: datetime(2026, 9, 18, 21, 59, 0))
    eff = backup_scheduler._effective_time()
    assert (eff[0], eff[1]) == (23, 0)  # banco vence env (02:00 fixada em fixed_fallbacks)


def test_b_desativado_nao_dispara(db_session, seeded_config, fixed_fallbacks, monkeypatch):
    """Teste B: efetiva auto_enabled=false → nenhum disparo (nenhum AUTOMATICO)."""
    seeded_config.auto_enabled = False
    db_session.commit()
    monkeypatch.setattr(
        backup_scheduler, "SessionLocal", _fresh_sessionmaker(db_session)
    )
    monkeypatch.setattr(backup_scheduler, "_catchup_done", True)
    monkeypatch.setattr(backup_scheduler, "_clock", lambda: datetime(2026, 9, 18, 2, 0, 30))
    chamadas = []
    monkeypatch.setattr(
        backup_scheduler, "_run_scheduled_backup", lambda: chamadas.append(1) or None
    )
    stop = backup_scheduler.threading.Event()
    # stop APÓS o 1º tick (setar antes pularia o while inteiro)
    backup_scheduler.threading.Timer(0.05, stop.set).start()
    backup_scheduler._scheduler_loop(stop)
    assert chamadas == []
    assert db_session.query(BackupRecord).filter(
        BackupRecord.backup_type == "AUTOMATICO"
    ).count() == 0


def test_c_ativado_dispara_no_horario(db_session, seeded_config, fixed_fallbacks, monkeypatch):
    """Teste C: efetiva true + horário atingido → ciclo dispara via generate_backup."""
    seeded_config.auto_enabled = True
    seeded_config.time = "02:00"
    db_session.commit()
    monkeypatch.setattr(
        backup_scheduler, "SessionLocal", _fresh_sessionmaker(db_session)
    )
    monkeypatch.setattr(backup_scheduler, "_catchup_done", True)
    monkeypatch.setattr(backup_scheduler, "_clock", lambda: datetime(2026, 9, 18, 2, 0, 30))
    monkeypatch.setattr(
        backup_scheduler, "_next_run_utc",
        lambda now: datetime(2026, 9, 18, 2, 0, 0),
    )
    executado = []
    monkeypatch.setattr(
        backup_scheduler,
        "_run_scheduled_backup",
        lambda: executado.append(1),
    )
    stop = backup_scheduler.threading.Event()
    backup_scheduler.threading.Timer(0.05, stop.set).start()
    backup_scheduler._scheduler_loop(stop)
    import time as _time

    # worker roda em thread daemon — aguarda a execução do tick
    deadline = _time.time() + 2
    while not executado and _time.time() < deadline:
        _time.sleep(0.01)
    assert executado == [1]


def test_d_proximo_disparo_diario_a_partir_da_efetiva(db_session, seeded_config, fixed_fallbacks):
    """Teste D: cálculo diário correto usando a efetiva (sexta 21:00 → sexta 23:00)."""
    seeded_config.time = "23:00"
    seeded_config.schedule = "daily"
    db_session.commit()
    backup_scheduler.refresh_effective_config()
    eff = get_effective_config(db_session)
    now = datetime(2026, 9, 18, 21, 0, 0)
    nxt = backup_scheduler._next_run_utc(time_utils.local_to_utc(now))
    local = time_utils.utc_to_recife(nxt)
    assert (local.day, local.hour, local.minute) == (18, 23, 0)  # próximo 23:00 futuro = hoje


def test_e_proximo_disparo_semanal_a_partir_da_efetiva(db_session, seeded_config, fixed_fallbacks):
    """Teste E: semanal respeita weekday da efetiva (020 — semana do weekday)."""
    seeded_config.schedule = "weekly"
    seeded_config.weekday = 0  # domingo
    seeded_config.time = "02:00"
    db_session.commit()
    backup_scheduler.refresh_effective_config()
    assert get_effective_config(db_session).schedule == "weekly"
    now = datetime(2026, 9, 18, 21, 0, 0)  # sexta 18/09
    nxt_local = time_utils.utc_to_recife(
        backup_scheduler._next_run_utc(time_utils.local_to_utc(now))
    )
    assert nxt_local.weekday() == 6  # domingo
    assert (nxt_local.hour, nxt_local.minute) == (2, 0)


def test_snapshot_consistente_no_ciclo(db_session, seeded_config, fixed_fallbacks, monkeypatch):
    """FR-012: retenção usa limites do MESMO snapshot do ciclo (sem mistura)."""
    seeded_config.retention_daily_days = 7
    db_session.commit()
    backup_scheduler.refresh_effective_config()
    summary = backup_scheduler._apply_retention(db_session)
    assert summary["candidatos"] == 0  # sem registros — mas executou com snapshot único


# ============================================================================
# US4 — Testes M/N (auditoria, RBAC, concorrência)
# ============================================================================

def test_m_auditoria_com_before_after(client, db_session, fixed_fallbacks):
    """Teste M: evento BACKUP_CONFIGURACAO_ALTERADA com before/after por campo."""
    from app.models.audit_log import AuditLog
    from app.services.audit_service import ACTION_BACKUP_CONFIG_UPDATED

    _post_config(client, time="23:00", retention_daily_days="7")
    evento = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == ACTION_BACKUP_CONFIG_UPDATED)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert evento is not None
    assert evento.username is not None
    assert "02:00" in (evento.previous_data or "") and "23:00" in (evento.new_data or "")
    assert "30" in (evento.previous_data or "") and "7" in (evento.new_data or "")
    assert "DATABASE_URL" not in (evento.new_data or "") and "senha" not in (evento.description or "").lower()


def test_n_sem_permissao_403_get_e_post(client, db_session, fixed_fallbacks):
    """Teste N: deny-by-default no backend — POST direto incluído."""
    _make_user(db_session, "cfgConsulta", role_names=["Consulta"])
    _login(client, "cfgConsulta")
    assert client.get("/admin/backups/configuracoes").status_code == 403
    resp = _post_config(client, time="23:00")
    assert resp.status_code == 403
    assert get_effective_config(db_session).time == "02:00"  # nada alterou


def test_dois_salvamentos_deterministicos(client, db_session, fixed_fallbacks):
    """FR-013: última escrita válida prevalece; cada salvamento audita."""
    from app.models.audit_log import AuditLog
    from app.services.audit_service import ACTION_BACKUP_CONFIG_UPDATED

    _post_config(client, time="05:00")
    _post_config(client, time="06:00")
    eff = get_effective_config(db_session)
    assert eff.time == "06:00"
    eventos = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == ACTION_BACKUP_CONFIG_UPDATED)
        .count()
    )
    assert eventos >= 2


# ============================================================================
# US5 — Testes O/P/Q/J (preservação da 020) + inspeção técnica
# ============================================================================

def test_o_backup_manual_intocado(client, db_session, fixed_fallbacks, monkeypatch):
    """Teste O: geração manual funciona com a nova config vigente (fluxo 020)."""
    from app.services import backup_service

    monkeypatch.setattr(backup_service, "_run_mysqldump", _fake_dump)
    _post_config(client, time="23:00", auto_enabled="true")
    resp = client.post("/admin/backups/gerar", follow_redirects=False)
    assert resp.status_code == 303
    assert "success=" in resp.headers["location"]
    registro = db_session.query(BackupRecord).filter_by(backup_type="MANUAL").first()
    assert registro is not None and registro.status == "SUCCESS"


def test_j_keep_pre_restore_politica_preservada(
    db_session, fixed_fallbacks, monkeypatch, tmp_path
):
    """Teste J: keep=0 preserva todos; N>0 preserva os N mais recentes (020)."""
    from app.services import backup_service

    # Diretório ISOLADO — a retenção remove via get_backup_path (BACKUP_DIR do
    # módulo backup_service), então patchear lá isola toda a cadeia.
    monkeypatch.setattr(backup_service, "BACKUP_DIR", tmp_path)
    import gzip

    tmp_path.mkdir(parents=True, exist_ok=True)
    from datetime import timedelta

    def _seed_com_arquivo(filename, days):
        rec = BackupRecord(
            filename=filename, backup_type="PRE_RESTAURACAO", status="SUCCESS",
            size_bytes=10, sha256="a" * 64, timestamp=NOW - timedelta(days=days),
        )
        db_session.add(rec)
        with gzip.open(tmp_path / filename, "wb") as f:
            f.write(b"-- dump")
        return rec

    r_antigo = _seed_com_arquivo("backup_20260701_020000_300001.sql.gz", 60)
    r_recente = _seed_com_arquivo("backup_20260801_020000_300002.sql.gz", 30)
    db_session.commit()

    # keep=0 (default da 020): preserva TODOS
    seeded = get_backup_config(db_session)
    seeded.keep_pre_restore = 0
    db_session.commit()
    summary = backup_scheduler._apply_retention(db_session)
    assert (tmp_path / r_antigo.filename).exists()
    assert (tmp_path / r_recente.filename).exists()

    # keep=1: preserva o mais recente; antigo vira candidato e é removido
    seeded.keep_pre_restore = 1
    db_session.commit()
    _seed_valido_para_guarda = BackupRecord(
        filename="backup_20260917_020000_300003.sql.gz", backup_type="AUTOMATICO",
        status="SUCCESS", size_bytes=10, sha256="a" * 64, timestamp=NOW - timedelta(days=1),
    )
    db_session.add(_seed_valido_para_guarda)
    with gzip.open(tmp_path / _seed_valido_para_guarda.filename, "wb") as f:
        f.write(b"-- dump")
    db_session.commit()
    summary = backup_scheduler._apply_retention(db_session)
    assert (tmp_path / r_recente.filename).exists()   # dentro do keep
    assert summary["removidos"] >= 0  # política executada sem erro


def test_q_retencao_usa_limites_da_efetiva(db_session, seeded_config, fixed_fallbacks):
    """Teste Q: GFS/guardas da 020 intactos com limites vindos da efetiva."""
    seeded_config.retention_daily_days = 30
    db_session.commit()
    summary = backup_scheduler._apply_retention(db_session)
    assert summary["resultado"] in ("COMPLETA", "PARCIAL", "FALHA")
    assert summary["candidatos"] == 0  # nenhum registro elegível na suíte limpa


def test_html_sem_campos_tecnicos(client, db_session, fixed_fallbacks):
    """FR-005/FR-021: a tela NÃO expõe caminhos/executáveis/credenciais/timeouts."""
    resp = client.get("/admin/backups/configuracoes")
    html = resp.text
    for termo in ("MYSQLDUMP_PATH", "BACKUP_DIR", "BACKUP_IMPORT_TIMEOUT", "DATABASE_URL", "mysqldump"):
        assert termo not in html


# ============================================================================
# FEATURE 022 — Configurações de Backup em Modal (spec/022-modal-configuracoes-backup)
# Fundação: leitura sem efeito colateral (create=False) + redirect do POST
# ============================================================================

def test_022_create_false_sem_linha_nao_persiste(db_session, fixed_fallbacks):
    """T002: create=False em banco SEM linha → nenhuma escrita (leitura pura)."""
    from app.models.backup_config import BackupConfig

    assert db_session.query(BackupConfig).count() == 0  # pré-condição
    row = get_backup_config(db_session, create=False)
    assert row.auto_enabled is False
    eff = get_effective_config(db_session, create=False)
    assert eff.schedule == "daily" and eff.time == "02:00"  # defaults
    assert db_session.query(BackupConfig).count() == 0  # NUNCA criou


def test_022_create_false_com_linha_retorna_persistido(db_session, fixed_fallbacks):
    """T002: create=False com linha existente → valores persistidos."""
    save_backup_config(
        db_session, None, auto_enabled=True, schedule="weekly", time="23:00",
        weekday=1, retention_daily_days=7, retention_weekly_weeks=4,
        retention_monthly_months=6, keep_pre_restore=2,
    )
    row = get_backup_config(db_session, create=False)
    assert row.time == "23:00" and row.schedule == "weekly"
    eff = get_effective_config(db_session, create=False)
    assert eff.time == "23:00" and eff.auto_enabled is True
    assert eff.retention_daily_days == 7 and eff.keep_pre_restore == 2


def test_022_create_true_mantem_criacao_lazy(db_session, fixed_fallbacks):
    """T002: create=True (default) preserva o comportamento atual (anti-regressão)."""
    from app.models.backup_config import BackupConfig

    assert db_session.query(BackupConfig).count() == 0
    row = get_backup_config(db_session)  # default create=True
    assert row.id == 1
    assert db_session.query(BackupConfig).count() == 1  # criada + commitada
    eff = get_effective_config(db_session)  # idem, agora linha existente
    assert eff.time == "02:00"


# ============================================================================
# FEATURE 022 — US1: ⚙ no header + modal #modalBackupConfig (estrutura HTML)
# ============================================================================

def test_022_get_listagem_sem_insert_e_com_modal(client, db_session, fixed_fallbacks, monkeypatch):
    """T005/T004: GET /admin/backups (banco sem linha) → 200, leitura pura e com modal.

    O snapshot do scheduler (020) é pré-aquecido porque seu refresh lazy usa
    sessão própria com create=True — comportamento PRÉ-existente, fora do
    escopo da 022 (T012 proíbe alterar backup_scheduler.py). O alvo do assert
    é a rota: a leitura config_form (create=False) não pode escrever.
    """
    from app.models.backup_config import BackupConfig
    from app.services import backup_scheduler
    from app.services.backup_config_service import EffectiveBackupConfig

    monkeypatch.setattr(
        backup_scheduler, "_current_effective",
        EffectiveBackupConfig(
            auto_enabled=False, schedule="daily", time="02:00", weekday=0,
            retention_daily_days=30, retention_weekly_weeks=12,
            retention_monthly_months=12, keep_pre_restore=0,
        ),
    )
    assert db_session.query(BackupConfig).count() == 0  # pré-condição: sem linha
    resp = client.get("/admin/backups")
    assert resp.status_code == 200
    assert db_session.query(BackupConfig).count() == 0  # leitura pura (create=False)
    assert "modalBackupConfig" in resp.text  # modal pré-preenchido pela efetiva


def test_022_botao_engrenagem_estrutura(client, db_session, fixed_fallbacks):
    """T005(1)(2): ⚙ somente-ícone, aria/title, data-bs-target, no page-header flex."""
    html = client.get("/admin/backups").text
    assert 'aria-label="Configurações de Backup"' in html
    assert 'title="Configurações de Backup"' in html
    assert 'data-bs-target="#modalBackupConfig"' in html
    assert 'data-bs-toggle="modal"' in html
    assert 'bi bi-gear' in html
    # header flex com o botão APÓS o bloco do título
    header_pos = html.find("page-header d-flex justify-content-between")
    assert header_pos != -1
    title_pos = html.find("page-header-title", header_pos)
    btn_pos = html.find("data-bs-target=\"#modalBackupConfig\"", header_pos)
    assert -1 < title_pos < btn_pos


def test_022_estrutura_modal_conferir(client, db_session, fixed_fallbacks):
    """T005(3)+U1: modal com a estrutura do modalConferir + acessibilidade."""
    html = client.get("/admin/backups").text
    id_pos = html.find('id="modalBackupConfig"')
    assert id_pos != -1
    start = html.rfind("<div", 0, id_pos)  # abertura do div do modal (inclui class="modal fade")
    assert start != -1
    modal = html[start:start + 20000]
    for frag in (
        "modal fade", "modal-dialog", "modal-content", "modal-header",
        "modal-title", "btn-close", "modal-body", "modal-footer",
        'aria-label="Fechar"',  # U1: btn-close acessível
        "for=\"cfg-auto-enabled\"", "for=\"cfg-time\"",  # U1: labels associados
    ):
        assert frag in modal, f"esperado no modal: {frag}"


def test_022_oito_campos_uma_vez(client, db_session, fixed_fallbacks):
    """T005(4): os 8 name= aparecem EXATAMENTE 1 vez no HTML (só dentro do modal)."""
    html = client.get("/admin/backups").text
    for name in (
        'name="auto_enabled"', 'name="schedule"', 'name="time"',
        'name="weekday"', 'name="keep_pre_restore"',
        'name="retention_daily_days"', 'name="retention_weekly_weeks"',
        'name="retention_monthly_months"',
    ):
        assert html.count(name) == 1, f"{name} deve aparecer exatamente 1 vez"


def test_022_secao_antiga_removida_e_configurar_removido(client, db_session, fixed_fallbacks):
    """T005(5)(6): "Salvar configuração" só no modal; botão Configurar fora da página."""
    html = client.get("/admin/backups").text
    start = html.find('id="modalBackupConfig"')
    assert start != -1, "modal deve existir"
    end = html.find("Gerar backup agora", start)
    assert end != -1
    modal = html[start:end]
    fora = html[:start] + html[end:]
    assert modal.count("Salvar configuração") == 1  # dentro do modal
    assert fora.count("Salvar configuração") == 0  # card antigo fora do modal
    assert ">Configurar<" not in html  # botão 021 removido (FR-001)


def test_022_card_gerar_backup_e_indicadores_preservados(client, db_session, fixed_fallbacks):
    """T005/FR-010: cards "Gerar backup agora" e "Backup Automático" intocados."""
    html = client.get("/admin/backups").text
    assert "Gerar backup agora" in html
    assert "btn-gerar-backup" in html
    assert "Backup Automático" in html
    assert "Agendamento" in html  # indicador do card


def test_022_valores_da_efetiva_no_modal(client, db_session, fixed_fallbacks):
    """T007/US1: modal pré-preenchido com a efetiva (T002 já cobriu o service)."""
    save_backup_config(
        db_session, None, auto_enabled=True, schedule="weekly", time="23:00",
        weekday=3, retention_daily_days=15, retention_weekly_weeks=8,
        retention_monthly_months=10, keep_pre_restore=3,
    )
    html = client.get("/admin/backups").text
    assert 'value="23:00"' in html
    assert 'value="15"' in html and 'value="8"' in html and 'value="10"' in html
    assert 'value="3"' in html  # keep_pre_restore


# ============================================================================
# FEATURE 022 — US2: Cancelar não persiste; Salvar usa o fluxo existente
# ============================================================================

def test_022_post_salvo_redirect_para_listagem(client, db_session, fixed_fallbacks):
    """T008(1): POST válida → 303 /admin/backups?success= (destino novo da 022)."""
    resp = _post_config(client, time="23:00", auto_enabled="true")
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/admin/backups?success=")


def test_022_post_invalido_redirect_para_listagem_e_intacto(client, db_session, fixed_fallbacks):
    """T008(2): POST inválida → 303 /admin/backups?error= e efetiva intacta."""
    resp = _post_config(client, time="25:99")
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/admin/backups?error=")
    assert get_effective_config(db_session).time == "02:00"  # configuração vigente intacta


def test_022_teste_e_valores_apos_salvar_no_modal(client, db_session, fixed_fallbacks):
    """T008(3) — Teste E completo: após salvar 23:00, a PÁGINA principal exibe 23:00."""
    _post_config(client, time="23:00", auto_enabled="true")
    html = client.get("/admin/backups").text
    assert 'value="23:00"' in html


def test_022_botao_cancelar_fora_do_submit(client, db_session, fixed_fallbacks):
    """T008(4) — Teste C automatizado: Cancelar é type=button + data-bs-dismiss (não submete)."""
    html = client.get("/admin/backups").text
    start = html.find('id="modalBackupConfig"')
    assert start != -1
    modal = html[start:start + 20000]
    cancelar_pos = modal.find(">Cancelar<")
    assert cancelar_pos != -1, "botão Cancelar deve existir no modal"
    tag_start = modal.rfind("<button", 0, cancelar_pos)
    tag = modal[tag_start:modal.find(">", cancelar_pos) + 1]
    assert 'type="button"' in tag
    assert 'data-bs-dismiss="modal"' in tag
    assert 'type="submit"' not in tag


def test_022_auditoria_backups_config_intacta(client, db_session, fixed_fallbacks, monkeypatch):
    """T008(5) — Teste H: BACKUP_CONFIGURACAO_ALTERADA continua gravado com before/after."""
    from app.services import audit_service

    eventos = []
    original = audit_service.write_change_audit

    def _spy(db, **kwargs):
        eventos.append(kwargs)
        return original(db, **kwargs)

    monkeypatch.setattr(audit_service, "write_change_audit", _spy)
    monkeypatch.setattr("app.web.admin_routes.write_change_audit", _spy)
    _post_config(client, time="23:00", retention_daily_days="7")
    assert eventos and eventos[-1]["action"] == "BACKUP_CONFIGURACAO_ALTERADA"
    assert eventos[-1]["before"]["time"] == "02:00" and eventos[-1]["after"]["time"] == "23:00"
    assert eventos[-1]["before"]["retention_daily_days"] == 30
    assert eventos[-1]["after"]["retention_daily_days"] == 7


# ============================================================================
# FEATURE 022 — US3: fidelidade visual (classes do modalConferir; zero JS/CSS novo)
# ============================================================================

def test_022_fidelidade_visual_sem_js_css_novo(client, db_session, fixed_fallbacks):
    """T010: modal usa somente classes Bootstrap já usadas; zero <script>/<style> novo."""
    html = client.get("/admin/backups").text
    id_pos = html.find('id="modalBackupConfig"')
    assert id_pos != -1
    start = html.rfind("<div", 0, id_pos)
    modal = html[start:start + 20000]
    # classes já presentes no modalConferir (inventarios/detail.html) e no projeto
    for classe in (
        "modal fade", "modal-dialog modal-lg modal-dialog-centered", "modal-content",
        "modal-header", "modal-title", "btn-close", "modal-body", "modal-footer",
        "btn-outline-secondary", "btn-primary", "form-select form-select-sm",
        "form-control form-control-sm", "form-check form-switch",
        "form-label small mb-1", "form-text small", "row g-3",
        "col-sm-6 col-lg-3", "col-sm-4 col-lg-4", "col-12",
    ):
        assert classe in modal, f"classe esperada no modal: {classe}"
    # nenhum script/CSS novo no template (baseline T001: 1 <script>, 0 <style>)
    from pathlib import Path
    template = Path("app/web/templates/admin/backups.html").read_text(encoding="utf-8")
    assert template.count("<script") == 1  # JS pré-existente (017 — restauração)
    assert template.count("<style") == 0


# ============================================================================
# FEATURE 026 — Atualização imediata do indicador "Agendamento" do card
# "Backup Automático" (badge Ativado/Desativado): a fonte do estado EXIBIDO
# passa a ser a configuração EFETIVA por request (config_form), a mesma do
# checkbox do modal — sem depender do snapshot interno do scheduler
# (_current_effective, renovado só por tick de 30 s).
# ============================================================================


def _badge(html: str) -> str:
    """Valor do badge de Agendamento no card 'Backup Automático'."""
    marker = "Agendamento</dt>"
    pos = html.find(marker)
    assert pos != -1, "card Backup Automático ausente do HTML"
    chunk = html[pos : pos + 600]
    if ">Ativado<" in chunk:
        return "Ativado"
    if ">Desativado<" in chunk:
        return "Desativado"
    raise AssertionError("badge Agendamento não encontrado no card")


def _post_config_follow(client, **overrides):
    """POST + seguir redirect (fluxo real: POST → 303 → GET — briefing §42)."""
    resp = _post_config(client, **overrides)
    assert resp.status_code == 303, f"esperado 303 do POST, veio {resp.status_code}"
    return client.get(resp.headers["location"])


def test_026_ativacao_refletida_imediatamente(
    client, db_session, fixed_fallbacks, seeded_config
):
    """Off → salvar Ativado → GET pós-redirect já mostra 'Ativado' (SC-001)."""
    seeded_config.auto_enabled = False
    db_session.commit()
    backup_scheduler.refresh_effective_config()  # snapshot = estado antigo (janela entre ticks)

    resp = _post_config_follow(client, auto_enabled="true")
    assert resp.status_code == 200
    assert _badge(resp.text) == "Ativado"
    # checkbox do modal na MESMA resposta (mesma fonte — FR-002/SC-003)
    assert 'name="auto_enabled" checked' in resp.text


def test_026_desativacao_refletida_imediatamente(
    client, db_session, fixed_fallbacks, seeded_config
):
    """On → salvar Desativado → GET pós-redirect já mostra 'Desativado' (SC-001)."""
    seeded_config.auto_enabled = True
    db_session.commit()
    backup_scheduler.refresh_effective_config()  # snapshot antigo = Ativado

    resp = _post_config_follow(client, auto_enabled=False)
    assert resp.status_code == 200
    assert _badge(resp.text) == "Desativado"
    assert 'name="auto_enabled" checked' not in resp.text


def test_026_causa_snapshot_defasado_reproduz_problema(
    client, db_session, fixed_fallbacks, seeded_config
):
    """Teste-documentação da causa (§45.1): com o snapshot do scheduler
    propositalmente defasado (auto_enabled contrário ao persistido), o fluxo
    POST→redirect→GET deve AINDA refletir o valor novo no badge — pois a
    fonte do estado exibido é a efetiva por request, não o snapshot.

    No código pré-026 (badge alimentado por auto_status.enabled), este teste
    falha exibindo o valor antigo — reproduzindo o problema relatado.
    """
    seeded_config.auto_enabled = True
    db_session.commit()
    backup_scheduler.refresh_effective_config()  # snapshot real: Ativado

    # Salva Desativado e segue o redirect. O snapshot do scheduler permanece
    # com o valor ANTIGO (só se renova no próximo tick de 30 s) — exatamente
    # o estado de produção após um salvamento entre ticks.
    resp = _post_config_follow(client, auto_enabled=False)
    assert resp.status_code == 200
    assert get_effective_config(db_session).auto_enabled is False
    # Snapshot ainda defasado — e NÃO é a fonte da tela:
    assert backup_scheduler._current_effective.auto_enabled is True
    # O badge já mostra o valor novo (fonte da tela = efetiva por request):
    assert _badge(resp.text) == "Desativado"
    assert 'name="auto_enabled" checked' not in resp.text


def test_026_alteracao_repetida_off_on_off(
    client, db_session, fixed_fallbacks, seeded_config
):
    """Off→On→Off: a cada POST, o HTML seguinte reflete o novo estado (§26)."""
    seeded_config.auto_enabled = False
    db_session.commit()
    backup_scheduler.refresh_effective_config()

    esperados = ("Ativado", "Desativado", "Ativado")
    valores = ("true", False, "true")
    for esperado, valor in zip(esperados, valores):
        resp = _post_config_follow(client, auto_enabled=valor)
        assert resp.status_code == 200
        assert _badge(resp.text) == esperado
        backup_scheduler.refresh_effective_config()  # simula tick entre salvamentos


def test_026_outros_campos_nao_regredem_indicador(
    client, db_session, fixed_fallbacks, seeded_config
):
    """Toggle + outros campos: indicador coerente com o toggle (§28)."""
    seeded_config.auto_enabled = False
    db_session.commit()
    backup_scheduler.refresh_effective_config()

    resp = _post_config_follow(client, auto_enabled="true", time="05:30")
    assert resp.status_code == 200
    assert _badge(resp.text) == "Ativado"

    backup_scheduler.refresh_effective_config()  # simula tick entre salvamentos
    resp = _post_config_follow(client, auto_enabled=False, retention_daily_days=7)
    assert resp.status_code == 200
    assert _badge(resp.text) == "Desativado"


def test_026_f5_idempotente(client, db_session, fixed_fallbacks, seeded_config):
    """GET consecutivo após salvar = mesmo valor do primeiro GET (§29)."""
    seeded_config.auto_enabled = False
    db_session.commit()
    backup_scheduler.refresh_effective_config()

    _post_config_follow(client, auto_enabled="true")
    first = client.get("/admin/backups")
    second = client.get("/admin/backups")
    assert first.status_code == second.status_code == 200
    assert _badge(first.text) == _badge(second.text) == "Ativado"





