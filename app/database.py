from sqlalchemy import create_engine, text
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

        conn.commit()


def init_db():
    """Inicializa as tabelas do banco de dados"""
    from app import models  # noqa: F401
    from app.models.enums import _register_all_enums  # noqa: F401
    _register_all_enums()
    Base.metadata.create_all(bind=engine)
    _ensure_schema_migrations()
