"""migrações legadas idempotentes (absorve _ensure_schema_migrations — Q2)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30

Feature 052 — primeira revisão REAL, idempotente por construção (Q2).

Porta EXATAMENTE os ALTERs que viviam em `app/database.py::
_ensure_schema_migrations` (removida nesta feature, FR-004):

- users: failed_login_attempts, locked_until (proteção força bruta),
  ad_object_guid, ad_dn, ad_last_sync (integração AD)
- user_roles: assigned_by (origem local|ad da atribuição)
- inventario_offline_coletas: evidence_metadata JSON (033 FR-017)
  + índices compostos ix_inv_off_coleta_inventory_status/_asset (033)

Idempotência: `ADD COLUMN IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`
(MariaDB 10.5+ — mesma pré-condição do mecanismo anterior; nenhum banco
que rodava a versão anterior pode regredir aqui). Bancos que já receberam
os ALTERs executam no-ops; bancos que nunca receberam convergem.
`downgrade()` é no-op PASSIVO (FR-007): as colunas/índices permanecem —
removê-los seria DDL destrutivo (Constituição VII) sem ganho algum.
"""

from __future__ import annotations

from alembic import op

# Identificadores da revisão
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    # No-op passivo (FR-007): manter colunas/índices é seguro e reversível;
    # DROP deles seria destrutivo sem necessidade (Constituição VII).
    pass
