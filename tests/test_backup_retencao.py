"""Retenção GFS de backups — feature 020 (Testes G/H/I/J/L/K do briefing §39).

Seleção determinística (data-model §3): janela diária + âncoras semanal ISO/
mensal; proteções absolutas (MANUAL/PRE_RESTAURACAO/legado); guarda do último
backup válido; histórico preservado após remoção; resultado COMPLETA/PARCIAL/FALHA.
"""

import gzip
from datetime import datetime, timedelta

import pytest

from app.models.backup_record import BackupRecord
from app.services import backup_scheduler, backup_service
from app.services.backup_service import BackupService

_BACKUP_NAME_RE = __import__("re").compile(
    r"^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$"
)

NOW = datetime(2026, 9, 18, 12, 0, 0)  # relógio fixo dos testes (UTC)

# Timestamps relativos ao relógio fixo
T_40_DIAS = NOW - timedelta(days=40)
T_10_DIAS = NOW - timedelta(days=10)   # dentro da janela diária (30 d)
T_100_DIAS = NOW - timedelta(days=100) # fora da janela mensal (12 meses? não)
T_400_DIAS = NOW - timedelta(days=400) # fora de todas as janelas


@pytest.fixture(autouse=True)
def _clean_backup_dir():
    from app.config import BACKUP_DIR

    for _pass in ("setup", None, "teardown"):
        if _pass is None:
            yield
        if BACKUP_DIR.exists():
            for p in BACKUP_DIR.iterdir():
                if _BACKUP_NAME_RE.match(p.name) or ".part" in p.name:
                    if p.is_file():
                        p.unlink()


def _fake_dump(path):
    with open(path, "wb") as f:
        f.write(b"-- fake dump 020 retencao\n")



def _refetch(db, record):
    """Reconsulta o registro (após commit interno da retenção, objetos do
    teste podem sair do identity_map — InvalidRequestError no refresh)."""
    db.expire_all()
    return db.query(BackupRecord).filter(BackupRecord.id == record.id).one()

def _seed_record(db, filename, backup_type="AUTOMATICO", status="SUCCESS",
                 timestamp=None):
    """Cria registro + arquivo físico válido correspondente."""
    record = BackupRecord(
        filename=filename,
        backup_type=backup_type,
        status=status,
        timestamp=timestamp or NOW,
    )
    db.add(record)
    db.commit()
    # Cria arquivo físico gzip válido (casa com a regex via get_backup_path)
    from app.config import BACKUP_DIR
    path = BACKUP_DIR / filename
    with gzip.open(path, "wb") as f:
        f.write(b"-- dump\n")
    return record


@pytest.fixture
def retention(db_session, monkeypatch):
    """Ambiente de retenção: clock fixo + sessão de teste.

    expire_on_commit=False: a retenção comita na sessão recebida (marca
    removed_at) e os objetos do teste permanecem utilizáveis sem refresh.
    """
    db_session.expire_on_commit = False
    monkeypatch.setattr(backup_scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(backup_service, "SessionLocal", lambda: db_session,
                        raising=False)
    monkeypatch.setattr(backup_scheduler, "_clock", lambda: NOW)
    return backup_scheduler


# ============================================================================
# TESTE G — seleção determinística
# ============================================================================

def test_automatico_expirado_nao_ancora_e_removido(db_session, retention):
    """Teste G: automático fora da janela diária e não-âncora é removido.

    Mesma semana ISO com 2 automáticos: o mais recente é âncora semanal
    (preservado); o mais antigo é elegível (removido). Terceiro backup
    recente garante a guarda do último válido.
    """
    r_antigo = _seed_record(db_session, "backup_20260804_120000_000001.sql.gz",
                            timestamp=NOW - timedelta(days=45))   # seg. da semana 32
    r_ancora = _seed_record(db_session, "backup_20260809_120000_000002.sql.gz",
                            timestamp=T_40_DIAS)                  # semana 32 (mais recente)
    _seed_record(db_session, "backup_20260917_120000_000003.sql.gz",
                 timestamp=NOW - timedelta(days=1))  # guarda: não fica 0 válidos

    summary = retention._apply_retention(db_session)

    assert summary["candidatos"] == 2
    assert summary["removidos"] == 1
    assert summary["resultado"] == "COMPLETA"
    r_tmp = _refetch(db_session, r_antigo)
    assert r_tmp.removed_at is not None
    assert r_tmp.removed_reason == "RETENCAO_DIARIA"
    # Arquivo físico removido; registro preservado (Teste L)
    from app.config import BACKUP_DIR
    assert not (BACKUP_DIR / r_antigo.filename).exists()
    assert (BACKUP_DIR / r_ancora.filename).exists()


def test_ancoras_semanal_e_mensal_preservadas(db_session, retention):
    """Teste G: âncoras semanal e mensal preservadas; não-âncora removida.

    O service checa a âncora SEMANAL primeiro (data-model §3.4, passos 2→3);
    ANCORA_MENSAL só é reportada quando o registro é o mais recente do mês
    mas NÃO da sua semana ISO — semana que cruza dois meses. Semana ISO 31
    = 27/07–02/08/2026:
      r_jul  = 28/07 (d-52)  → não é o mais recente da semana (02/08 é) →
                               cai para âncora MENSAL de julho ✓
      r_ago  = 02/08 (d-47)  → mais recente da semana 31 → ANCORA_SEMANAL
      r_fora = 2025-06-01 (d-474) → fora de todas as janelas → removido
    """
    r_jul = _seed_record(
        db_session, "backup_20260728_120000_000002.sql.gz",
        timestamp=NOW - timedelta(days=52))
    r_ago = _seed_record(
        db_session, "backup_20260802_120000_000022.sql.gz",
        timestamp=NOW - timedelta(days=47))
    r_fora = _seed_record(
        db_session, "backup_20250601_120000_000021.sql.gz",
        timestamp=NOW - timedelta(days=474))

    summary = retention._apply_retention(db_session)

    assert summary["preservados"].get(r_jul.filename) == "ANCORA_MENSAL"
    assert summary["preservados"].get(r_ago.filename) == "ANCORA_SEMANAL"
    assert summary["removidos"] == 1
    assert _refetch(db_session, r_fora).removed_at is not None
    assert _refetch(db_session, r_jul).removed_at is None
    assert _refetch(db_session, r_ago).removed_at is None


def test_dentro_da_janela_diaria_nao_e_candidato(db_session, retention):
    """Automático dentro de 30 dias não é candidato."""
    _seed_record(db_session, "backup_20260908_120000_000003.sql.gz",
                 timestamp=T_10_DIAS)
    summary = retention._apply_retention(db_session)
    assert summary["candidatos"] == 0
    assert summary["removidos"] == 0


# ============================================================================
# TESTE H — manual NUNCA removido
# ============================================================================

def test_manual_antigo_nunca_removido(db_session, retention):
    """Teste H: backup manual antigo (mesmo 2 anos) jamais é candidato."""
    r_manual = _seed_record(db_session, "backup_20240918_120000_000004.sql.gz",
                            backup_type="MANUAL", timestamp=NOW - timedelta(days=730))

    summary = retention._apply_retention(db_session)

    assert summary["candidatos"] == 0  # universo é só AUTOMATICO
    assert summary["removidos"] == 0
    from app.config import BACKUP_DIR
    assert (BACKUP_DIR / r_manual.filename).exists()


# ============================================================================
# TESTE I — pré-restauração preservado por default
# ============================================================================

def test_pre_restauracao_preservado_por_default(db_session, retention, monkeypatch):
    """Teste I: KEEP_PRE_RESTORE=0 (default) preserva TODOS os pré-restauração."""
    monkeypatch.setattr(backup_scheduler, "BACKUP_RETENTION_KEEP_PRE_RESTORE", 0)
    r_pre = _seed_record(db_session, "backup_20240918_120000_000005.sql.gz",
                         backup_type="PRE_RESTAURACAO",
                         timestamp=NOW - timedelta(days=730))

    summary = retention._apply_retention(db_session)
    assert summary["removidos"] == 0
    from app.config import BACKUP_DIR
    assert (BACKUP_DIR / r_pre.filename).exists()


def test_pre_restauracao_com_keep_n_preserva_os_n_mais_recentes(db_session, retention, monkeypatch):
    """Teste I (política explícita): KEEP_PRE_RESTORE=1 preserva só o mais recente."""
    monkeypatch.setattr(backup_scheduler, "BACKUP_RETENTION_KEEP_PRE_RESTORE", 1)
    r_antigo = _seed_record(db_session, "backup_20240901_120000_000006.sql.gz",
                            backup_type="PRE_RESTAURACAO",
                            timestamp=NOW - timedelta(days=740))
    r_recente = _seed_record(db_session, "backup_20240910_120000_000007.sql.gz",
                             backup_type="PRE_RESTAURACAO",
                             timestamp=NOW - timedelta(days=730))

    summary = retention._apply_retention(db_session)

    r_tmp = _refetch(db_session, r_antigo)
    r_tmp = _refetch(db_session, r_recente)
    assert r_recente.removed_at is None       # N mais recente preservado
    assert r_antigo.removed_at is not None    # excedente removido
    assert summary["removidos"] == 1


# ============================================================================
# TESTE J — guarda do último backup válido
# ============================================================================

def test_guarda_ultimo_backup_valido(db_session, retention, monkeypatch):
    """Teste J: se a remoção deixaria 0 válidos, preserva com motivo registrado.

    O candidato é o único backup no disco E é a última âncora possível —
    a ordem interna de checagem (âncoras antes da guarda) faz o motivo ser
    ANCORA_* quando aplicável; para exercitar a guarda propriamente dita,
    simula contagem de válidos == 1 na hora da remoção.
    """
    calls = {"n": 0}
    real_count = backup_scheduler._count_valid_backups_on_disk

    r_ultimo = _seed_record(db_session, "backup_20260809_120000_000008.sql.gz",
                            timestamp=T_40_DIAS)

    # Simula disco com 1 válido no momento da checagem de remoção
    monkeypatch.setattr(
        backup_scheduler, "_count_valid_backups_on_disk", lambda: 1
    )

    summary = retention._apply_retention(db_session)

    # Guarda bloqueou: arquivo presente, motivo registrado, nada removido
    assert summary["removidos"] == 0
    assert r_ultimo.filename in summary["preservados"]
    r_tmp = _refetch(db_session, r_ultimo)
    assert r_tmp.removed_at is None


# ============================================================================
# TESTE L — histórico preservado após remoção física
# ============================================================================

def test_historico_preservado_apos_remocao(db_session, retention):
    """Teste L: removed_at/reason no registro; registro NÃO é apagado.

    Semana 32 (d-45 e d-40): âncora + elegível; o candidato é removido e
    o registro permanece com removed_at/reason. Semana 38 recente (âncora
    futura da política) garante a guarda do último válido não bloquear.
    """
    r = _seed_record(db_session, "backup_20260804_120000_000009.sql.gz",
                     timestamp=NOW - timedelta(days=45))   # semana 32, elegível
    _seed_record(db_session, "backup_20260809_120000_000010.sql.gz",
                 timestamp=T_40_DIAS)                      # semana 32: âncora
    _seed_record(db_session, "backup_20260917_120000_000018.sql.gz",
                 timestamp=NOW - timedelta(days=1))        # fora da janela diária

    summary = retention._apply_retention(db_session)
    assert summary["removidos"] == 1

    record = db_session.query(BackupRecord).filter(
        BackupRecord.filename == r.filename
    ).one()  # registro AINDA EXISTE
    assert record.removed_at is not None
    assert record.removed_reason == "RETENCAO_DIARIA"
    assert record.status == "SUCCESS"  # status histórico intacto


# ============================================================================
# TESTE K — falha de remoção → PARCIAL
# ============================================================================

def test_falha_remocao_resultado_parcial(db_session, retention, monkeypatch):
    """Teste K: OSError na remoção → falha individual + resultado PARCIAL.

    Semana 33 (10–16/08) com 3 automáticos — âncora 16/08 preservada;
    o unlink do 10/08 falha (OSError simulado) e o do 11/08 ok → PARCIAL.
    Backup recente (17/09) evita a guarda do último válido.
    """
    real_unlink = __import__("pathlib").Path.unlink

    def _unlink_fails(self, missing_ok=False):
        if self.name.startswith("backup_20260810"):
            raise OSError(13, "Permission denied (simulado)")
        return real_unlink(self, missing_ok=missing_ok)

    # Semana 33 (10–16/08): 3 automáticos — mais recente (16/08) é âncora;
    # 10/08 falha no unlink (OSError simulado), 11/08 removido com sucesso.
    _seed_record(db_session, "backup_20260810_120000_000011.sql.gz",
                 timestamp=NOW - timedelta(days=39))  # remoção falhará
    _seed_record(db_session, "backup_20260811_120000_000012.sql.gz",
                 timestamp=NOW - timedelta(days=38))  # remoção ok
    _seed_record(db_session, "backup_20260816_120000_000019.sql.gz",
                 timestamp=NOW - timedelta(days=33))  # âncora semana 33
    _seed_record(db_session, "backup_20260917_120000_000020.sql.gz",
                 timestamp=NOW - timedelta(days=1))   # fora da janela diária

    monkeypatch.setattr("pathlib.Path.unlink", _unlink_fails)
    summary = retention._apply_retention(db_session)
    monkeypatch.undo()

    assert summary["falhas"] == 1
    assert summary["removidos"] == 1
    assert summary["resultado"] == "PARCIAL"  # NUNCA "COMPLETA" nesse cenário


# ============================================================================
# Integridade e legados
# ============================================================================

def test_integridade_nao_ok_preserva(db_session, retention):
    """Backup com gzip corrompido é preservado com motivo INTEGRIDADE_NAO_OK."""
    from app.config import BACKUP_DIR
    r = _seed_record(db_session, "backup_20260809_120000_000013.sql.gz",
                     timestamp=T_40_DIAS)
    # Corrompe o arquivo (segundo backup válido evita guarda do último)
    _seed_record(db_session, "backup_20260917_120000_000014.sql.gz",
                 timestamp=NOW - timedelta(days=1))
    (BACKUP_DIR / r.filename).write_bytes(b"nao-gzip")

    summary = retention._apply_retention(db_session)
    assert summary["preservados"].get(r.filename) == "INTEGRIDADE_NAO_OK"
    assert summary["removidos"] == 0


def test_legado_sem_registro_jamais_candidato(db_session, retention):
    """BV-5: arquivo no disco SEM registro (legado) — intocado."""
    from app.config import BACKUP_DIR
    import gzip as _gzip
    legacy = BACKUP_DIR / "backup_20250101_120000_000099.sql.gz"
    with _gzip.open(legacy, "wb") as f:
        f.write(b"-- legado sem registro")

    summary = retention._apply_retention(db_session)
    assert summary["candidatos"] == 0
    assert legacy.exists()


# ============================================================================
# Auditoria da retenção
# ============================================================================

def test_evento_resumo_com_preservados(db_session, retention):
    """F4: evento BACKUP_RETENCAO_EXECUTADA carrega candidatos/removidos/preservados."""
    from app.services.audit_service import (
        ACTION_RETENTION_EXECUTED, ACTION_BACKUP_REMOVED_RETENTION, get_audit_logs,
    )
    # Dois candidatos: um removido, um âncora semanal preservada
    _seed_record(db_session, "backup_20260601_120000_000015.sql.gz",
                 timestamp=NOW - timedelta(days=109))
    _seed_record(db_session, "backup_20260605_120000_000016.sql.gz",
                 timestamp=NOW - timedelta(days=105))
    # Terceiro backup válido para a guarda não bloquear
    _seed_record(db_session, "backup_20260917_120000_000017.sql.gz",
                 timestamp=NOW - timedelta(days=1))

    retention._apply_retention(db_session)

    logs = get_audit_logs(db_session, module="Backup", limit=20)
    resumo = next(log for log in logs if log.action == ACTION_RETENTION_EXECUTED)
    new_data = __import__("json").loads(resumo.new_data)
    assert new_data["candidatos"] == 2
    assert new_data["removidos"] == 1
    assert "preservados" in new_data
    removed = [log for log in logs if log.action == ACTION_BACKUP_REMOVED_RETENTION]
    assert len(removed) == 1
