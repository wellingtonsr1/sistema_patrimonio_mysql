"""baseline — stamp only (decisão Q1)

Revision ID: 0001
Revises:
Create Date: 2026-09-30

Feature 052 — revisão BASE, deliberadamente NO-OP.

DECISÃO Q1 (spec.md §3): baseline VAZIO (stamp), e não baseline completo
(autogenerate do schema inteiro). Bancos existentes são apenas MARCADOS
com esta revisão — zero DDL de colunas/tabelas no deploy de adoção
(regra máxima da spec). Instalações novas continuam criando o schema via
`Base.metadata.create_all` (init_db), que roda antes do Alembic no boot.

A evolução para um baseline completo do schema é dívida consciente
registrada (candidata a spec futura), com critério de evolução no Q1.
"""

from __future__ import annotations

# Identificadores da revisão
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op por design: a "migração" é apenas a marcação do banco
    # (a tabela alembic_version é criada pelo próprio Alembic no stamp).
    pass


def downgrade() -> None:
    # No-op: reverter o baseline significa apenas remover a marcação.
    # Nenhum objeto de schema foi criado por esta revisão.
    pass
