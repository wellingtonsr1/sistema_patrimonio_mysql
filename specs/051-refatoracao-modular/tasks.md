---
description: "Task list for Feature 051 — Refatoração Modular: Rotas Web e Backup Service"
---

# Tasks: 051-refatoracao-modular

**Input**: plan.md + spec.md de `specs/051-refatoracao-modular/`

**Prerequisites**: baseline da suíte capturado antes da F1 (T001).

**Regra de ouro**: MOVER, NÃO REESCREVER. Cada fase termina com a suíte verde antes da próxima começar.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (sem dependência pendente)
- **[Story]**: US1 (routes), US2 (backup), US3 (guardrails/docs)

---

## Phase 1: Setup

- [x] T001 Capturar baseline: rodar suíte completa e registrar contagem/nome dos failures pré-existentes (esperado: 2 de `test_backup_externo.py`) em `specs/051-refatoracao-modular/validacao.md` — **863 passed / 0 failed** (as 2 falhas previstas não existem no repo atual)
- [x] T002 [P] [US1] Criar `tests/test_route_inventory.py`: helper que captura inventário `(path, methods, endpoint_name)` de todas as rotas do app FastAPI e compara contra manifesto JSON versionado (`tests/route_manifest.json`); gerar o manifesto a partir do código PRÉ-refatoração e commitar ambos — o teste deve passar antes de qualquer movimentação — **140 rotas; walker recursivo para `_IncludedRouter` lazy do FastAPI**

**Checkpoint**: manifesto de rotas congelado; baseline documentado.

---

## Phase 2: US1 — Decomposição de routes.py

- [x] T003 [F1] Criar `app/web/routers/__init__.py` (agregador vazio) e mover helpers compartilhados (L31–154: `_confirm_payload_rows`, `_apply_mapping_to_rows`) para `app/web/routers/shared.py`; `routes.py` importa de lá. Suíte verde.
- [x] T004 [F1] Converter configuração Jinja2 + injeção global de templates (L157–213) no núcleo do facade `routes.py`; manter export de `templates`. Suíte verde. — **ajuste do implement: config Jinja2 movida para `routers/templates_env.py` (import circular facade↔domínios; FR-004 preservado — configuração única)**
- [x] T005 [F2] Extrair AUTENTICAÇÃO (L215–354) → `routers/auth.py` e PRIMEIRO ACESSO (L1979–2167) → `routers/setup.py`; registrar no facade na ordem original. `_claim_first_access` re-exportado do facade (consumido por teste). Suíte verde.
- [x] T006 [F3] [P-dependente de T005] Extrair DASHBOARD (L356–367) → `routers/dashboard.py` e RELATÓRIOS (L1884–1977) → `routers/reports.py`. Suíte verde.
- [x] T007 [F4] Extrair MOVIMENTAÇÃO (L923–1071) → `routers/movements.py`. Suíte verde.
- [x] T008 [F5] Extrair COLABORADORES (L1073–1422) → `routers/custodians.py`. Suíte verde.
- [x] T009 [F6] Extrair LOCAIS (L1424–1778) → `routers/locations.py`. Suíte verde.
- [x] T010 [F7] Extrair MANUTENÇÕES (L1780–1882) → `routers/maintenances.py`. Suíte verde.
- [x] T011 [F8] Extrair INVENTÁRIO (L2169–2668) → `routers/inventario.py`. Suíte verde.
- [x] T012 [F9] Extrair BENS/EQUIPAMENTOS (L369–921) → `routers/assets.py` (maior seção — por último). Suíte verde.
- [x] T013 [US1] Verificar FR-002: `routes.py` ≤ 200 linhas; `git diff` prova que `main.py`, `admin_routes.py`, `help_routes.py` não foram editados (SC-004); rodar `tests/test_rbac.py` completo como verificação adicional de que decorators de permissão sobreviveram intactos à movimentação (FR-006). — **routes.py = 86 linhas; 3 consumidores 0 diffs; RBAC 30 passed**

**Checkpoint US1**: inventário de rotas idêntico (T002 verde), suíte verde, facade enxuto.

---

## Phase 3: US2 — Decomposição de backup_service.py

- [x] T014 [B1] ~~Criar pacote `app/services/backup/`~~ **AMENDMENT A1 (spec)**: evidência de 42 pontos de monkeypatch no namespace `backup_service` (injeção de `SessionLocal`, `DATABASE_URL`, `_run_mysqldump`, etc.) inviabiliza o split físico sem quebrar NR-002/FR-009 — módulo único preservado, mapa de navegação por seções no docstring.
- [x] T015 [B1] ~~Transformar `backup_service.py` em facade~~ **A1**: desnecessário — arquivo permanece módulo único; superfície de monkeypatch integralmente preservada (42/42).
- [x] T016 [US2] Exercitar ciclo de restore via TestClient em ambiente de testes (fluxo 019) — **`test_backup_restore.py` 46 passed; suíte de backup completa verde (SC-005)**

**Checkpoint US2**: facade ≤ 60 linhas; scheduler/backup/restore 100% verdes.

---

## Phase 4: US3 — Guardrails e documentação

- [x] T017 [P] [US3] Atualizar `docs/ARQUITETURA_E_MANUTENCAO.md`: novo mapa de módulos (`app/web/routers/*`), diagrama de camadas e tabela de autenticação. — **(A1: sem mudança em backup; mapa de seções documentado no docstring do próprio módulo)**
- [x] T018 [US3] Conferir FR-011: nenhum arquivo novo > ~800 linhas; registrar medidas em validacao.md. — **maior: inventario.py 529 linhas**

---

## Phase 5: Finalização

- [x] T019 Rodar suíte completa final; comparar com baseline T001 (mesmos passed + 2 failures pré-existentes, nenhum teste editado — NR-002); atualizar `validacao.md` com evidências (diff stat, contagens, linhas por arquivo, resultado do `test_rbac.py`). — **879 passed / 0 failed (863 baseline + 16 novos); 1 assertion de import da 050 ajustada (documentado)**
- [x] T020 [P] [US1] Criar `tests/test_routers_structure.py`: importa cada módulo de `app/web/routers/` e `app/services/backup/` isoladamente — canário de imports circulares que roda em segundos antes da suíte completa (complementa SC-005). — **A1: lista cobre `backup_service` como módulo único**
- [x] T021 Varredura final: `grep -rn "from app.web.routes import"` e `"from app.services.backup_service import"` — todos resolvem via facade; nenhum consumidor quebrado. — **3 consumidores web + 7 de backup intocados e verdes**
