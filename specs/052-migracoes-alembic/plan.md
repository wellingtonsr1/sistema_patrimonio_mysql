# Implementation Plan: Migrações de Schema com Alembic (052)

**Branch**: `052-migracoes-alembic` · **Spec**: [spec.md](spec.md) · **Created**: 2026-09-28

## Summary

Introduzir Alembic com estratégia de **baseline vazio (stamp)**: bancos existentes são apenas marcados (zero DDL no deploy de adoção), `create_all` permanece o criador de tabelas novas, deltas futuros passam a ser revisões Alembic versionadas. A primeira revisão real absorve os ALTERs hoje em `_ensure_schema_migrations` de forma idempotente, que é então removida de `database.py`.

## Technical Context

**Language/Version**: Python 3.12 / SQLAlchemy 2 / Alembic (novo) / pytest
**Storage**: MariaDB (produção, `mariadb+pymysql://`) / SQLite em memória (suíte — migrações não executam DDL aí)
**Ponto de integração**: `app/database.py::init_db()` (chamada no lifespan de `app/main.py` e pelo instalador da 027)

## Constitution Check

| Princípio | Status | Nota |
|---|---|---|
| I. Evolução incremental | PASS | Nada recriado; mecanismo atual substituído por equivalente versionado |
| II. Arquitetura em camadas | PASS | Migrações vivem em `migrations/`; models/services intocados |
| III. Regras de negócio nos services | PASS | Zero regra de negócio tocada |
| IV/V. Integridade patrimonial/inventário | PASS | Sem alteração de dados; revisão 001 é idempotente e aditiva |
| VI. Segurança RBAC | PASS | Colunas de proteção (lockout/AD) preservadas pela revisão 001 |
| VII. Banco protegido | PASS | **Regra central desta spec**: zero DDL no deploy de adoção; revisões aditivas |
| VIII. Testes como não-regressão | PASS | Suíte SQLite verde; teste condicional MariaDB para a cadeia de revisões |
| IX. Auditoria | PASS | Intocada |
| XI. Documentação fiel | PASS | Workflow documentado (FR-006/SC-006) |
| XII. Especificações e validação | PASS | validacao.md com evidências SC-001..006 |

**GATE: PASS 10/10**

## Design técnico

### D1 — Layout

```
migrations/
├── alembic.ini          # script_location=migrations; logging padrão
├── env.py               # URL de app.config.DATABASE_URL; target_metadata=Base.metadata;
│                        # _register_all_enums() antes do autogenerate/upgrade
├── script.py.mako
└── versions/
    ├── 0001_baseline.py        # no-op — base; mensagem documenta decisão Q1
    └── 0002_migracoes_legadas_idempotentes.py
                              # absorve _ensure_schema_migrations (Q2):
                              # users (failed_login_attempts, locked_until,
                              #   ad_object_guid, ad_dn, ad_last_sync),
                              # user_roles.assigned_by,
                              # inventario_offline_coletas.evidence_metadata + 2 índices
                              # — todos via op.execute com IF NOT EXISTS
```

### D2 — Lógica de convergência em `init_db()` (substitui FR-003)

```python
# pseudo — implementar em app/database.py
_ensure_alembic_state():
    if "sqlite" in engine.dialect.name:      # suíte de testes (Princípio VIII):
        return                                # banco em memória já está no estado-alvo
                                              # via create_all; migrações são específicas
                                              # de MariaDB. Zero DDL na suíte.
    has_version_table = inspect(engine).has_table("alembic_version")
    if not has_version_table:
        # banco legado (instalado antes) OU instalação nova (create_all acabou de rodar):
        # nenhum schema pendente a aplicar — ambos estão no estado "head dos models",
        # pois create_all acabou de garantir as tabelas novas.
        stamp("0001")          # baseline no-op — ZERO DDL além da tabela de versão
    upgrade("head")            # aplica 0002 (idempotente) e futuras revisões
    # tolerância à corrida: OperationalError/conflito de lock DDL → 1 retry
    # (mesmo espírito do _create_all_tolerante_corrida, erro 1050 / 027)
```

Ordem dentro de `init_db()`: `_register_all_enums()` → `create_all` → `_ensure_alembic_state()`.
Justificativa da ordem: `create_all` primeiro garante que tabelas novas de models recentes existam mesmo sem revisão; o Alembic só passa a ser **obrigatório** para mudanças em tabelas existentes.

### D3 — Edge cases cobertos

| Caso | Comportamento |
|---|---|
| Instalação nova | create_all cria tudo → stamp 0001 → upgrade aplica 0002 (no-ops, pois colunas já existem via create_all) |
| Banco legado 1ª vez pós-adoção | create_all (no-op) → stamp 0001 → upgrade aplica 0002 (colunas ausentes são criadas — mesmo DDL de hoje) |
| Banco já com 0002 aplicado (restart) | upgrade head = no-op |
| Crash no meio do upgrade | MariaDB DDL não transacional: revisão 001 é idempotente por construção → re-executar convergi; tolerância à corrida cobre dois processos simultâneos |
| Restore de dump pré-Alembic (017/019) | idem banco legado: convergi no boot |
| Restore de dump pós-Alembic antigo | alembic_version presente com revisão antiga → upgrade head aplica os deltas |

### D4 — Por que não autogenerate/baseline completo

Enums customizados registrados dinamicamente (`_register_all_enums`) + types específicos de MariaDB tornam o autogenerate propenso a diffs falsos; provar fidelidade do baseline completo é o risco que esta adoção existe para evitar. Documentado como dívida consciente (Q1).

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Alembic travar boot de produção (falha persistente) | FR-005: erro logado com ação recomendada; revisão base é no-op, revisão 001 idempotente — única fonte real de falha é infra (conexão/permissão), que já travaria o create_all |
| Dois processos em boot concorrente (crash-loop 027) | Retry único espelhando `_create_all_tolerante_corrida`; lock de DDL do MariaDB serializa ALTERs |
| Desenvolvedor esquece de criar revisão (muda só o model) | Workflow documentado + revisão de PR com checklist "mudou model? tem revisão?"; guardrail futuro (spec candidata): teste que roda autogenerate em modo comparação e falha se houver diff |
| SQLite da suíte divergir de MariaDB | Já é a realidade atual (ALTERs hoje só rodam em MariaDB); teste condicional SC-004 cobre a cadeia quando ambiente existe; no-op do D2 garante suíte 100% inalterada |
| Revisão futura quebrada impede boot de TODAS as instalações (inclusive quem não precisa dela) | Risco aceito e padrão do Alembic; mitigado por revisão obrigatória com `downgrade()`, teste condicional (T010) e validação em MariaDB antes do merge (T009) |

## Complexity Tracking

Nenhuma violação justificada. Dívida consciente assumida (dupla fonte models+migrations até baseline completo futuro) está registrada em Q1 com critério de evolução.

## Micro-remediações do /speckit-analyze (aplicadas 2026-09-28, antes do implement)

- **A1 (HIGH — gap real)**: a spec exigia suíte verde inalterada (SC-003/Princípio VIII), mas FR-003 mandava rodar `stamp`/`upgrade` em todo boot — em SQLite in-memory isso falha (o DDL de criação da `alembic_version` + stamp em conexão recém-aberta não persiste entre sessões e os testes exercitariam caminhos de MariaDB). Corrigido: guard explícito por dialect em D2 (no-op em SQLite), refletido em FR-003/FR-005/T007 — suíte permanece 100% intocada.
- **A2 (MEDIUM)**: Q4 prometia "validação de encadeamento" apenas no teste condicional — em CI sem MariaDB a cadeia ficaria sem nenhuma verificação. Corrigido: parte estrutural roda sempre (FR-009/T010a).
- **B1 (LOW)**: risco ausente na matriz: revisão futura quebrada bloqueia boot de todas as instalações. Adicionado com mitigação (downgrade() obrigatório, T009/T010).
- **C1 (INFO)**: constituição VII menciona `init_db` + `_ensure_schema_migrations` como "mecanismo existente" — após a 052 o mecanismo passa a ser Alembic; a doc da constitution não é emendada por spec de feature (governança própria), mas FR-006/T012 do plan já determinam documentar o novo mecanismo em ARQUITETURA_E_MANUTENCAO.md; emenda da constitution fica registrada como follow-up para o responsável.
