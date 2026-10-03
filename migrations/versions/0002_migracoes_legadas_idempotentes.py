"""migrações legadas idempotentes (absorve _ensure_schema_migrations — Q2)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30

Feature 052 — primeira revisão REAL, idempotente por construção (Q2).
Feature 061 (M-1) — paridade MariaDB × MySQL (CS-1 do diagnóstico): MySQL
(Oracle) NÃO suporta `ADD COLUMN IF NOT EXISTS`/`CREATE INDEX IF NOT
EXISTS` (sintaxe exclusiva de MariaDB 10.5+; rodar aqui quebraria o
init_db no Windows+MySQL). O dialecto é detectado pela versão REAL do
servidor (`SELECT VERSION()`); em MySQL os MESMOS ALTERs são emitidos
condicionalmente via information_schema (coluna/índice existe?) — a
idempotência é preservada nos DOIS bancos (matriz do diagnóstico §9).

Porta EXATAMENTE os ALTERs que viviam em `app/database.py::
_ensure_schema_migrations` (removida nesta feature, FR-004):

- users: failed_login_attempts, locked_until (proteção força bruta),
  ad_object_guid, ad_dn, ad_last_sync (integração AD)
- user_roles: assigned_by (origem local|ad da atribuição)
- inventario_offline_coletas: evidence_metadata JSON (033 FR-017)
  + índices compostos ix_inv_off_coleta_inventory_status/_asset (033)

Idempotência:
- MariaDB 10.5+: `ADD COLUMN IF NOT EXISTS` / `CREATE INDEX IF NOT
  EXISTS` — mesma pré-condição do mecanismo anterior; nenhum banco que
  rodava a versão anterior pode regredir aqui.
- MySQL 8.0+: cada DDL é emitido SOMENTE se o objeto não existir
  (information_schema.COLUMNS / information_schema.STATISTICS de
  DATABASE()) — mesmo esquema lógico, mesmo resultado final.

Bancos que já receberam os ALTERs executam no-ops; bancos que nunca
receberam convergem. `downgrade()` é no-op PASSIVO (FR-007): as
colunas/índices permanecem — removê-los seria DDL destrutivo
(Constituição VII) sem ganho algum.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

# Identificadores da revisão
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# (tabela, coluna, DDL) — MESMA definição lógica nos dois bancos.
# Identificadores vêm destas constantes (nunca de entrada externa — sem
# risco de injeção); os literais de DDL são aceitos por MariaDB e MySQL.
_COLUNAS = (
    ("users", "failed_login_attempts", "INTEGER DEFAULT 0 NOT NULL"),
    ("users", "locked_until", "DATETIME"),
    ("users", "ad_object_guid", "VARCHAR(64)"),
    ("users", "ad_dn", "VARCHAR(400)"),
    ("users", "ad_last_sync", "DATETIME"),
    ("user_roles", "assigned_by", "VARCHAR(20) DEFAULT 'local' NOT NULL"),
    ("inventario_offline_coletas", "evidence_metadata", "JSON NULL"),
)

# (tabela, índice, colunas) — mesmos índices compostos do data-model (033).
_INDICES = (
    (
        "inventario_offline_coletas",
        "ix_inv_off_coleta_inventory_status",
        "(inventory_id, status)",
    ),
    (
        "inventario_offline_coletas",
        "ix_inv_off_coleta_inventory_asset",
        "(inventory_id, asset_id)",
    ),
)


def _eh_mariadb(bind) -> bool:
    """True = MariaDB (suporta IF NOT EXISTS em DDL); False = MySQL (Oracle)."""
    dialecto = bind.dialect.name
    if dialecto not in ("mysql", "mariadb"):
        # Nem SQLite nem outro SGBD emitem estes ALTERs — erro claro cedo
        # (antes a falha seria um erro de sintaxe do próprio DDL).
        raise RuntimeError(
            "revisão 0002 executa apenas em MariaDB/MySQL; "
            f"dialecto recebido: {dialecto}"
        )
    try:
        versao = bind.execute(text("SELECT VERSION()")).scalar()
    except Exception:  # pragma: no cover — driver sem SELECT VERSION()
        # Fallback raro: usa o que o dialecto já negociou na conexão
        # (server_version_info do PyMySQL contém 'MariaDB' quando for MariaDB).
        versao = " ".join(str(v) for v in (bind.dialect.server_version_info or ()))
    return "MariaDB" in str(versao)


def _coluna_existe(bind, tabela: str, coluna: str) -> bool:
    return bool(
        bind.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = :tabela AND COLUMN_NAME = :coluna"
            ),
            {"tabela": tabela, "coluna": coluna},
        ).scalar()
    )


def _indice_existe(bind, tabela: str, indice: str) -> bool:
    return bool(
        bind.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = :tabela AND INDEX_NAME = :indice"
            ),
            {"tabela": tabela, "indice": indice},
        ).scalar()
    )


def _upgrade_mysql(bind) -> None:
    """MySQL (Oracle): condicional via information_schema (mesma
    idempotência da sintaxe MariaDB — segunda execução é no-op)."""
    for tabela, coluna, ddl in _COLUNAS:
        if _coluna_existe(bind, tabela, coluna):
            continue
        op.execute(f"ALTER TABLE `{tabela}` ADD COLUMN `{coluna}` {ddl}")
    for tabela, indice, colunas in _INDICES:
        if _indice_existe(bind, tabela, indice):
            continue
        op.execute(f"CREATE INDEX `{indice}` ON `{tabela}` {colunas}")


def upgrade() -> None:
    bind = op.get_bind()
    if _eh_mariadb(bind):
        # MariaDB 10.5+: sintaxe original (idempotente por construção).

        # Colunas de proteção contra força bruta em `users`
        op.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts "
            "INTEGER DEFAULT 0 NOT NULL"
        )
        op.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until DATETIME"
        )

        # Integração Active Directory: colunas adicionais em `users`
        op.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ad_object_guid VARCHAR(64)"
        )
        op.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ad_dn VARCHAR(400)"
        )
        op.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ad_last_sync DATETIME"
        )

        # Origem da atribuição de perfil em `user_roles` ('local' | 'ad')
        op.execute(
            "ALTER TABLE user_roles ADD COLUMN IF NOT EXISTS assigned_by "
            "VARCHAR(20) DEFAULT 'local' NOT NULL"
        )

        # Feature 033: metadados de evidência (FR-017)
        op.execute(
            "ALTER TABLE inventario_offline_coletas ADD COLUMN IF NOT EXISTS "
            "evidence_metadata JSON NULL"
        )

        # Feature 033: índices compostos do data-model.md
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_inv_off_coleta_inventory_status "
            "ON inventario_offline_coletas (inventory_id, status)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_inv_off_coleta_inventory_asset "
            "ON inventario_offline_coletas (inventory_id, asset_id)"
        )
        return

    _upgrade_mysql(bind)


def downgrade() -> None:
    # No-op passivo (FR-007): manter colunas/índices é seguro e reversível;
    # DROP deles seria destrutivo sem necessidade (Constituição VII).
    pass
