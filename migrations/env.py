"""env.py do Alembic — feature 052.

Lê a URL REAL do app (app.config.DATABASE_URL — fonte única) e usa
Base.metadata como target (para autogenerate de rascunho). Os enums
customizados são registrados antes de qualquer uso do metadata.

Override explícito: a variável de ambiente ALEMBIC_DATABASE_URL tem
precedência — usada APENAS por tooling/testes (ex.: teste condicional
da suíte contra banco dedicado). O boot do app NUNCA a define, então
produção usa sempre a URL do .env.
"""

from __future__ import annotations

import os

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import DATABASE_URL
from app.database import Base
from app.models.enums import _register_all_enums

_register_all_enums()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Fonte única de verdade: a mesma URL do app (FR-001), com override
# documentado apenas para tooling/testes
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("ALEMBIC_DATABASE_URL") or DATABASE_URL,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline (--sql): emite SQL sem conexão."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online: conexão real."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
