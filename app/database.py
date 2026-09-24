from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool
from app.config import DATABASE_URL

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


def _ensure_schema_migrations():
    """
    Migrações leves e idempotentes para tabelas já existentes.

    `Base.metadata.create_all` cria apenas tabelas novas; para adicionar
    colunas em tabelas existentes (ex: `users` com dados reais) usamos
    `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (MariaDB 10.5+).
    Nenhum dado existente é alterado ou removido.
    """
    with engine.connect() as conn:
        # Colunas de proteção contra força bruta em `users`
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts "
            "INTEGER DEFAULT 0 NOT NULL"
        ))
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until DATETIME"
        ))

        # Integração Active Directory: colunas adicionais em `users`
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ad_object_guid VARCHAR(64)"
        ))
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ad_dn VARCHAR(400)"
        ))
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ad_last_sync DATETIME"
        ))

        # Origem da atribuição de perfil em `user_roles` ('local' | 'ad')
        conn.execute(text(
            "ALTER TABLE user_roles ADD COLUMN IF NOT EXISTS assigned_by "
            "VARCHAR(20) DEFAULT 'local' NOT NULL"
        ))

        # Feature 033: metadados de evidência (FR-017) acrescentados ao model
        # APÓS a primeira criação da tabela em bancos já existentes — o
        # create_all não altera tabelas previamente criadas, então a coluna
        # nova exige migração aditiva idempotente (MariaDB 10.5+, mesmo
        # mecanismo das colunas acima; nulo, sem dado default).
        conn.execute(text(
            "ALTER TABLE inventario_offline_coletas ADD COLUMN IF NOT EXISTS "
            "evidence_metadata JSON NULL"
        ))

        # Feature 033: índices compostos do data-model.md — mesmo caso da
        # coluna acima (tabela criada em rodada anterior sem eles). Idempotente.
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_inv_off_coleta_inventory_status "
            "ON inventario_offline_coletas (inventory_id, status)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_inv_off_coleta_inventory_asset "
            "ON inventario_offline_coletas (inventory_id, asset_id)"
        ))

        conn.commit()


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
    _ensure_schema_migrations()
