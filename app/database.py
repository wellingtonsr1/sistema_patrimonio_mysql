import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

# MariaDB/MySQL: pool de conexões para múltiplos usuários simultâneos
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()


def drain_engine(timeout: float = 10.0) -> bool:
    """Drena o pool de conexões da aplicação (feature 019 — FR-003/R1/R5).

    Fecha as conexões OCIOSAS do pool (engine.dispose) e aguarda, até
    `timeout` segundos, que nenhuma conexão permaneça em uso (checkedout == 0).
    Não altera DATABASE_URL, nem os parâmetros do engine/pool (contract §2):
    o SQLAlchemy recria conexões sob demanda após o dispose.

    Retorna True se o pool chegou a zero conexões em uso no prazo;
    False caso contrário (o chamador deve abortar a operação destrutiva
    — no restore da 019 isso vira falha honesta auditada).
    """
    import time

    global engine

    engine.dispose()  # fecha conexões ociosas do pool

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if engine.pool.checkedout() == 0:
            return True
        time.sleep(0.1)
    return False


def get_db():
    """Dependency para obter sessão do banco de dados no FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_alembic_state(migrations_dir: Path | None = None) -> None:
    """Garante o estado Alembic do banco no boot (feature 052, plan D2).

    Estratégia de baseline VAZIO (decisão Q1 da spec):
    - **SQLite (suíte de testes, Princípio VIII)**: no-op TOTAL — o banco
      em memória já está no estado-alvo via create_all; migrações de
      MariaDB não são exercidas e a tabela alembic_version nem existe
      (micro-remediação A1 do /speckit-analyze).
    - **Banco sem alembic_version** (legado pré-052 OU instalação nova,
      cujo create_all acabou de rodar): `stamp 0001` — zero DDL além da
      própria tabela de versão (regra máxima da spec).
    - **Banco já versionado**: `upgrade head` — aplica revisões pendentes
      (idempotentes) e futuros deltas.
    - **migrations/ ausente no disco** (ex.: instalação cujo snapshot não
      incluía o diretório): warning com ação recomendada e boot segue —
      o mecanismo de migração nunca pode ser requisito de boot enquanto
      create_all continuar garantindo as tabelas novas.

    Tolerância à corrida: retry único espelhando
    `_create_all_tolerante_corrida` (crash-loop da 027); falha persistente
    é logada com ação recomendada e RELANÇADA (FR-005 — nunca engolida).
    """
    diretorio = Path(migrations_dir) if migrations_dir else Path(__file__).resolve().parent.parent / "migrations"
    logger = logging.getLogger(__name__)

    if "sqlite" in engine.dialect.name:  # suíte de testes: no-op total
        return

    if not (diretorio / "alembic.ini").is_file():
        logger.warning(
            "Alembic: diretório migrations/ não encontrado em %s — "
            "migrações ignoradas neste boot. Se esta é uma instalação de "
            "produção, atualize o deploy (migrations/ deve acompanhar o app). "
            "Deltas futuros de schema EXIGEM este diretório.",
            diretorio,
        )
        return

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect as sa_inspect

    cfg = Config(str(diretorio / "alembic.ini"))
    cfg.set_main_option("script_location", str(diretorio))

    try:
        if not sa_inspect(engine).has_table("alembic_version"):
            command.stamp(cfg, "0001")  # baseline no-op (zero DDL)
        command.upgrade(cfg, "head")
    except Exception as exc:  # noqa: BLE001 — relançada após retry (FR-005)
        logger.warning(
            "Alembic: falha no primeiro boot/convergência (%s: %s) — "
            "retentando uma vez (tolerância à corrida, espírito 027)...",
            type(exc).__name__,
            exc,
        )
        try:
            if not sa_inspect(engine).has_table("alembic_version"):
                command.stamp(cfg, "0001")
            command.upgrade(cfg, "head")
        except Exception:
            logger.error(
                "Alembic: falha PERSISTENTE ao convergir o schema (%s). "
                "Ação recomendada: verifique conexão/permissões do banco e "
                "rode manualmente `alembic upgrade head` com a URL do .env "
                "para ver o erro real; NÃO reverta código sem convergir.",
                diretorio,
            )
            raise


def init_db():
    """Inicializa as tabelas do banco de dados"""
    from app import models  # noqa: F401
    from app.models.enums import _register_all_enums  # noqa: F401
    _register_all_enums()
    # Feature 032: histórico unificado de execuções de integração (tabela NOVA,
    # aditiva — nada de tabelas/colunas existentes é alterado; data-model.md).
    from app.models.integration_execution import IntegrationExecution  # noqa: F401
    # Feature 033: coleta offline de inventário (tabela NOVA, aditiva —
    # idempotência/conflitos; nada de tabelas/colunas existentes é alterado).
    from app.models.inventario_offline import InventarioOfflineColeta  # noqa: F401
    _create_all_tolerante_corrida()
    # Feature 052: versionamento oficial de schema (baseline stamp + upgrade;
    # deltas futuros em migrations/versions/, nunca mais ALTER manual aqui).
    _ensure_alembic_state()


def _create_all_tolerante_corrida() -> None:
    """create_all tolerante à corrida entre processos no mesmo banco.

    Cenário real (feature 027): o instalador executa init_db() enquanto o
    serviço systemd de uma rodada anterior ainda está em crash-loop
    (Restart=on-failure, rodando init_db() a cada boot). Os dois processos
    avaliam "tabela não existe" ao mesmo tempo e o perdedor da corrida recebe
    OperationalError 1050 "Table ... already exists" ao emitir o CREATE TABLE.

    Nesse caso a tabela foi criada pelo outro processo — resultado idêntico
    ao do checkfirst. Basta repetir o create_all uma vez: os demais objetos
    pendentes são criados e o estado final é o mesmo. Repetição única evita
    mascarar erros persistentes (segunda falha 1050 = colisão real, relançada).
    """
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        if exc.orig is not None and getattr(exc.orig, "args", None) and exc.orig.args[0] == 1050:
            Base.metadata.create_all(bind=engine)
            return
        raise
