---
description: "Task list for Feature 052 — Migrações de Schema com Alembic"
---

# Tasks: 052-migracoes-alembic

**Input**: plan.md + spec.md de `specs/052-migracoes-alembic/`

**Prerequisites**: ambiente MariaDB disponível para validação (SC-001/SC-004); backup pré-upgrade do banco de validação (regra da casa 017/019).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo
- **[Story]**: US1 (infra), US2 (workflow dev), US3 (compat restore/testes)

---

## Phase 1: Setup

- [x] T001 [P] Adicionar `alembic>=1.13` a `requirements.txt`; instalar no venv
- [x] T002 Capturar dump de schema do banco de validação ANTES (referência para SC-001: `mysqldump --no-data`) e registrar em `specs/052-migracoes-alembic/validacao.md`
- [x] T003 [P] Rodar suíte completa e registrar baseline (registrado: 912 passed/0 failed após a 055/058; baseline anterior 903/0)

---

## Phase 2: US1 — Infraestrutura Alembic

- [x] T004 [US1] Criar `migrations/` (alembic.ini, env.py, script.py.mako, versions/) conforme plan D1: env.py lendo `app.config.DATABASE_URL`, `target_metadata=Base.metadata`, `_register_all_enums()` no topo
- [x] T005 [US1] Criar revisão base `0001_baseline` no-op com mensagem documentando a decisão Q1 (FR-002)
- [x] T006 [US1] Criar revisão `0002_migracoes_legadas_idempotentes`: portar TODOS os ALTERs de `_ensure_schema_migrations` via `op.execute` com `IF NOT EXISTS` (users ×5 colunas, user_roles ×1, inventario_offline_coletas ×1 + 2 índices), `downgrade()` documentado como no-op passivo (colunas permanecem — FR-007)
- [x] T007 [US1] Implementar `_ensure_alembic_state()` em `app/database.py` (plan D2): **no-op total em SQLite** (suíte inalterada — FR-003); sem `alembic_version` → `stamp 0001`; com → `upgrade head`; retry único em conflito; chamar após `create_all` no `init_db()`
- [x] T008 [US1] Remover `_ensure_schema_migrations` de `database.py` e suas chamadas (FR-004); conferir que nenhum outro módulo a importa (grep)
- [x] T009 [US1] Validação manual em MariaDB (SC-001/SC-002): banco legado → boot → diff de schema mostra APENAS `alembic_version`; instalação nova em banco vazio → funcional; segundo boot → no-op. Registrar em validacao.md

---

## Phase 3: US3 — Compatibilidade e testes

- [x] T010 [US3] Criar `tests/test_migrations_052.py` conforme Q4: (a) validação estrutural das revisões (importáveis, encadeamento `down_revision` único, `upgrade()`/`downgrade()` definidos) — roda SEMPRE, inclusive SQLite; (b) teste condicional de execução real contra MariaDB quando `MIGRATIONS_TEST_URL` apontar para MariaDB dedicado (upgrade head em banco vazio, idempotência na 2ª execução, `downgrade -1` + `upgrade +1`), com skip explícito em SQLite
- [x] T011 [US3] Documentar/cobrir o cenário de restore (FR-008): simular banco sem `alembic_version` (drop da tabela) → boot → convergência; registrar evidência em validacao.md

---

## Phase 4: US2 — Workflow e documentação

- [x] T012 [P] [US2] Atualizar `docs/ARQUITETURA_E_MANUTENCAO.md`: seção "Migrações de schema" — como criar revisão (`alembic revision -m "0XX-descricao"`), regras (escrita à mão, downgrade(), proibição de DDL destrutivo, autogenerate só como rascunho), integração com boot (D2) e a dívida consciente do Q1
- [x] T013 [P] [US2] Adicionar checklist "mudou model? → criou revisão?" ao guia de contribuição/PR do projeto (README)

---

## Phase 5: Finalização

- [x] T014 Suíte completa final vs. baseline T003 (SC-003); `alembic history` mostrando `0001 → 0002` encadeadas (SC-005); atualizar validacao.md com todas as evidências SC-001..006
- [x] T015 Simulação de regressão do fluxo completo: schema pré-Alembic carregado em banco dedicado → boot → convergência automática (SC-004/FR-008 ponta a ponta)
