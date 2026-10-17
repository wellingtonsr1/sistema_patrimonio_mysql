"""COR-01 (SEC-005) — permissão dedicada de baixa de patrimônio (dados)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16

Feature COR-01 da spec de correção (SEC-005, score 7.1): a baixa definitiva
(WRITE_OFF = BAIXA_DESCARTE) passa a exigir a permissão dedicada
`movimentacao.baixar` (antes: qualquer portador de `movimentacao.criar`
executava baixa — guarda única sem filtro de tipo).

Revisão de DADOS (nenhum DDL; nada de enum alterado — Constituição):

1. Insere a linha em `permissions` (idempotente: só se `name` não existir),
   espelhando o catálogo (`app/services/permission_service.py`).
2. Corrige a descrição de `movimentacao.criar`, que definia a própria
   confusão do achado (remove "…e dar baixa" — o efeito permanente sai da
   operação rotineira).
3. Concessão padrão: APENAS o perfil `Administrador` recebe
   `movimentacao.baixar` (decisão registrada da spec de correção: perfis
   institucionais que executem descarte recebem a concessão pela gestão de
   perfis — deny by default, regra de ouro do RBAC). Idempotente: insere o
   vínculo só se não existir.

Idempotência por construção (mesmo padrão da 0002): INSERTS condicionais à
existência prévia; UPDATE com guarda `description <> <novo>`. Bancos novos
(próprios do seed) e bancos legados convergem para o mesmo estado final.

`downgrade()` é no-op PASSIVO (mesma disciplina da 0002/FR-007): remover a
permissão de um banco em produção faria `require_permission` negar TUDO que
a referencia (as rotas HTTP checam `movimentacao.baixar` após 0003) e
destruiria o histórico de `role_permissions` sem ganho inverso.
"""

from __future__ import annotations

from sqlalchemy import text

from alembic import op

# Identificadores da revisão
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# Espelho exato do catálogo (fonte única de verdade já atualizada)
BAIXA_NAME = "movimentacao.baixar"
BAIXA_MODULE = "Movimentação"
BAIXA_LABEL = "Registrar baixa de patrimônio"
BAIXA_DESC = "Executar baixa definitiva de bens (descarte) — operação de efeito permanente."
CRIAR_NAME = "movimentacao.criar"
CRIAR_DESC_NOVO = "Alocar, transferir, devolver e enviar/retornar de manutenção."


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Permissão nova (idempotente)
    perm_id = conn.execute(
        text("SELECT id FROM permissions WHERE name = :n"), {"n": BAIXA_NAME}
    ).scalar()
    if perm_id is None:
        conn.execute(
            text(
                "INSERT INTO permissions (name, module, label, description, created_at) "
                "VALUES (:n, :m, :l, :d, CURRENT_TIMESTAMP)"
            ),
            {"n": BAIXA_NAME, "m": BAIXA_MODULE, "l": BAIXA_LABEL, "d": BAIXA_DESC},
        )
        perm_id = conn.execute(
            text("SELECT id FROM permissions WHERE name = :n"), {"n": BAIXA_NAME}
        ).scalar()

    # 2) Descrição de movimentacao.criar corrigida (idempotente)
    conn.execute(
        text(
            "UPDATE permissions SET description = :d "
            "WHERE name = :n AND (description IS NULL OR description <> :d)"
        ),
        {"d": CRIAR_DESC_NOVO, "n": CRIAR_NAME},
    )

    # 3) Concessão padrão: apenas Administrador (idempotente)
    if perm_id is not None:
        admin_id = conn.execute(
            text("SELECT id FROM roles WHERE name = 'Administrador'")
        ).scalar()
        if admin_id is not None:
            link = conn.execute(
                text(
                    "SELECT id FROM role_permissions "
                    "WHERE role_id = :r AND permission_id = :p"
                ),
                {"r": admin_id, "p": perm_id},
            ).scalar()
            if link is None:
                conn.execute(
                    text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
                    {"r": admin_id, "p": perm_id},
                )


def downgrade() -> None:
    """No-op passivo (mesma disciplina da 0002): DML destrutivo de
    permissão/concessão em produção negaria operações legítimas de quem já
    usa a permissão dedicada e apagaria histórico de concessão."""
