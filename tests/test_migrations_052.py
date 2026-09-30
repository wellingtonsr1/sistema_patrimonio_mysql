"""Migrações de Schema com Alembic — Feature 052.

Cobertura (Q4/FR-009):
- (a) Estrutural — roda SEMPRE, inclusive SQLite: cadeia de revisões
      (importáveis, encadeamento único, upgrade/downgrade definidos), env.py
      ligado ao app.config e database.py sem o mecanismo artesanal antigo.
- (b) Condicional — execução REAL contra MariaDB apenas quando
      MIGRATIONS_TEST_URL apontar para um banco de teste dedicado
      (upgrade head em banco vazio, idempotência, downgrade -1/upgrade +1).
      Em SQLite/suite padrão: skip explícito (Princípio VIII — zero DDL).
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"
DATABASE_PY = PROJECT_ROOT / "app" / "database.py"


# ---------------------------------------------------------------------------
# (a) Estrutural — sempre roda
# ---------------------------------------------------------------------------

def _script_directory():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return ScriptDirectory.from_config(cfg)


def test_infra_migrations_dir_completo():
    for nome in ("alembic.ini", "env.py", "script.py.mako", "versions"):
        assert (MIGRATIONS_DIR / nome).exists(), f"ausente em migrations/: {nome}"
    revisoes = sorted((MIGRATIONS_DIR / "versions").glob("*.py"))
    assert len(revisoes) >= 2, "esperado baseline + primeira revisão real"


def test_infra_cadeia_revisoes_encadeada_e_unica():
    sd = _script_directory()
    heads = tuple(sd.get_heads())
    assert heads == ("0002",), f"head inesperado: {heads}"
    base = sd.get_base()  # retorna str na API atual
    assert base == "0001"
    todas = list(sd.walk_revisions())
    assert len(todas) == 2, f"esperadas exatamente 2 revisões, há {len(todas)}"


def test_infra_revisoes_definem_upgrade_e_downgrade():
    sd = _script_directory()
    for rev in sd.walk_revisions():
        modulo = rev.module
        assert callable(getattr(modulo, "upgrade", None)), f"{rev.revision}: upgrade() ausente"
        assert callable(getattr(modulo, "downgrade", None)), f"{rev.revision}: downgrade() ausente"


def test_infra_env_py_ligado_ao_app_config():
    fonte = (MIGRATIONS_DIR / "env.py").read_text(encoding="utf-8")
    assert "from app.config import DATABASE_URL" in fonte
    assert "_register_all_enums" in fonte
    assert "target_metadata" in fonte and "Base.metadata" in fonte


def test_infra_baseline_e_no_op():
    sd = _script_directory()
    baseline = next(r for r in sd.walk_revisions() if r.revision == "0001")
    modulo = baseline.module
    # upgrade/downgrade do baseline não podem emitir DDL: fonte sem op.* de DDL
    fonte_upgrade = inspect.getsource(modulo.upgrade)
    assert "op." not in fonte_upgrade, "baseline deve ser no-op (decisão Q1)"


def test_infra_revisao_0002_porta_todos_os_alters_legados():
    fonte = (MIGRATIONS_DIR / "versions" / "0002_migracoes_legadas_idempotentes.py").read_text(
        encoding="utf-8"
    )
    for coluna in (
        "failed_login_attempts",
        "locked_until",
        "ad_object_guid",
        "ad_dn",
        "ad_last_sync",
        "assigned_by",
        "evidence_metadata",
    ):
        assert coluna in fonte, f"revisão 0002 sem a coluna legada {coluna}"
    for indice in (
        "ix_inv_off_coleta_inventory_status",
        "ix_inv_off_coleta_inventory_asset",
    ):
        assert indice in fonte, f"revisão 0002 sem o índice legado {indice}"
    assert fonte.count("IF NOT EXISTS") >= 8, "ALTERs devem ser idempotentes"


def test_database_sem_mecanismo_artesanal_e_com_estado_alembic():
    fonte = DATABASE_PY.read_text(encoding="utf-8")
    assert "_ensure_schema_migrations" not in fonte, (
        "mecanismo artesanal deve ser removido (FR-004)"
    )
    assert "def _ensure_alembic_state" in fonte
    assert "_ensure_alembic_state()" in fonte, "init_db deve chamar _ensure_alembic_state()"
    # Compatibilidade Python 3.10/3.12 (mínimo do install.sh): a anotação
    # `Path | None` avalia na importação — o import de Path tem de estar no
    # TOPO do módulo (bug real pego na validação T009). Com `from __future__
    # import annotations` a regra relaxaria, mas o arquivo não o usa.
    primeira_metade = fonte.split("def _ensure_alembic_state")[0]
    assert "from pathlib import Path" in primeira_metade, (
        "import de Path deve estar no topo (anotação avalia eager no py<3.14)"
    )


def test_sqlite_e_no_op_total(monkeypatch):
    """Guard por dialect (Princípio VIII/micro-remediação A1): em SQLite nada
    acontece — nem alembic_version é criada."""
    import app.database as db_mod

    engine_sqlite = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db_mod, "engine", engine_sqlite)
    db_mod._ensure_alembic_state()  # não pode lançar nem criar tabela
    from sqlalchemy import inspect as sa_inspect

    assert not sa_inspect(engine_sqlite).has_table("alembic_version")


def test_migrations_dir_ausente_faz_skip_com_warning(monkeypatch, caplog):
    """Ambiente sem migrations/ (ex.: deploy sem whitelist atualizada) NÃO
    pode derrubar o boot: warning com ação recomendada e segue."""
    import logging

    import app.database as db_mod

    engine_sqlite = create_engine("sqlite://")
    monkeypatch.setattr(db_mod, "engine", engine_sqlite)
    monkeypatch.setattr(db_mod.engine.dialect, "name", "mariadb", raising=False)
    with caplog.at_level(logging.WARNING, logger="app.database"):
        db_mod._ensure_alembic_state(migrations_dir=Path("Z:/definitely/not/here"))
    assert any("migrations" in r.message.lower() for r in caplog.records)


def test_condicional_upgrade_head_em_banco_mariadb():
    """(b) Condicional — executa só com MIGRATIONS_TEST_URL (MariaDB dedicado)."""
    url = os.getenv("MIGRATIONS_TEST_URL", "")
    if not url.startswith("mariadb"):
        pytest.skip("MIGRATIONS_TEST_URL não definida — validação real feita em T009/T015")

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(MIGRATIONS_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))

    # Override explícito de tooling (env.py lê app.config por padrão):
    # garante que o teste NUNCA toque o banco do .env por acidente.
    os.environ["ALEMBIC_DATABASE_URL"] = url

    command.upgrade(cfg, "head")
    engine = create_engine(url)
    with engine.connect() as conn:
        versao = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert versao == "0002"

    # Idempotência: segunda execução é no-op
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        versao2 = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert versao2 == "0002"

    # downgrade -1 → upgrade +1 (cadeia saudável)
    command.downgrade(cfg, "-1")
    with engine.connect() as conn:
        versao3 = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert versao3 == "0001"
    command.upgrade(cfg, "head")
    engine.dispose()
