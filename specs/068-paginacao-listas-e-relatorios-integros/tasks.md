# Tasks: Paginação nas Listas Web e Integridade de Relatórios/Exportações

**Input**: Design documents from `/specs/068-paginacao-listas-e-relatorios-integros/`

**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (user stories + decisões P1–P5), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: **INCLUÍDAS** — AC01–AC15 (FR-019), TDD red→green no padrão da casa (063/064/066/067).

**Status**: **NÃO INICIADA** — **P1–P5 aprovadas** (P1–P3 em 2026-10-10; **P4 e P5 em 2026-10-11**, ver `spec.md` §14); T018 e T027 **liberadas**. Execução pelas fases abaixo.

**Organization**: Tarefas agrupadas por user story para implementação e teste independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos distintos)
- **[Story]**: US1, US2, US3 ou transversal (—)
- Caminhos exatos conforme plan.md §Source Code

## Path Conventions

Monolito existente: `app/` (web/services/models/utils), `tests/`, `docs/`. Conforme plan.md.

---

## Phase 1: Setup (Baseline e confirmações)

**Purpose**: registrar o patamar e confirmar os fatos da spec antes de mexer em algo (Constitution XII)

- [x] **T001** Executar `.venv/bin/python -m pytest -q` e registrar o patamar (esperado: 1005 passed / 2 skipped) em `specs/068-paginacao-listas-e-relatorios-integros/validacao.md` (criar no padrão da casa), **sem editar nenhum teste**
- [x] **T002** [P] Confirmar **somente leitura** os fatos da spec §1: (a) nenhum template com `pagination`/`page-item`; (b) `report_service.py:47` aplica `limit 10000`; (c) `view_inventory_report` usa `limit=1000` e o template não exibe `total`; (d) `get_audit_logs` já aceita `user_id`/`start_date`/`end_date`; (e) `CustodianService.get_all`/`LocationService.get_all` não têm `limit`; (f) `route_manifest.json` tem 142 rotas — **se qualquer item divergir, PARAR e reportar** — **verificação de baseline (Constitution XII) que sustenta FR-001, FR-003, FR-008, FR-010 e FR-014; não é tarefa de implementação**
- [x] **T003** Confirmar registrado em `spec.md` (Clarifications + §14) o conjunto de decisões **P1–P5**: **P1** aviso + exportação completa · **P2** todas as listas · **P3** `page_size` 200 (aprovadas 2026-10-10) · **P4** relatório web paginado · **P5** eliminar N+1 (**aprovadas 2026-10-11**) — **nenhuma decisão pendente; libera T018 e T027**

---

## Phase 2: Foundational (Prerequisito bloqueante)

**Purpose**: criar o alicerce compartilhado (helper + macro) — bloqueia todas as user stories

**⚠️ CRITICAL**: US1/US2/US3 não começam antes de T004/T005.

- [x] **T004** Criar `app/utils/pagination.py` com `parse_page(raw)`, `offset_for(page, page_size=200)`, `page_meta(total, page, page_size)` → `{page, page_size, pages, total, start, end, has_prev, has_next}` (vocabulário de `get_history`, research R2); testes unitários no arquivo novo (normalização de `abc`/`0`/`-1`/`>pages` — **FR-002**)
- [x] **T005** Criar `app/web/templates/macros/pagination.html` com `pager(...)` reutilizando o markup de `admin/integracoes/historico.html:86-95` (Anterior/Próxima + `{{ request.query_params }}`), **renderizando nada quando `pages <= 1`** (FR-006) e markup **responsivo** no padrão Bootstrap (360 px → desktop, FR-022/AC15) — research R3

**Checkpoint**: helper + macro prontos — todas as stories liberadas

---

## Phase 3: User Story 1 — Navegar até qualquer registro da lista (Priority: P1) 🎯 MVP

**Goal**: `/assets` e `/movements` (e em seguida as demais) paginam com 200 e mostram `Mostrando X–Y de Z`, preservando filtros

**Independent Test**: 250 bens → página 1 com 200 + total 250, **Próxima** mostra os 50 restantes (spec §5 US1)

### Tests for User Story 1 (TDD — escrever PRIMEIRO) ⚠️

- [x] **T006** [P] [US1] Criar `tests/test_paginacao_relatorios_068.py` com `test_assets_pagina1_mostra_200_e_total` (**AC01**), `test_assets_pagina2_mostra_restantes` (**AC02**: intervalo `201–250` com total) (seed de 250 bens; fixtures `client`/`db_session`) e `test_listas_403_sem_permissao_com_page` (**AC10**/**SC-012**: usuário sem a permissão da lista recebe 403 + trilha mesmo com `?page=2`, em ao menos 2 listas) — devem **FALHAR** contra o código atual (RED)
- [x] **T007** [P] [US1] Acrescentar em `tests/test_paginacao_relatorios_068.py`: `test_pagina_preserva_filtros` (**FR-007**: busca/situação sobrevivem à troca de página), `test_page_invalida_cai_em_pagina_valida` (**AC03**/**FR-002**: `abc`, `0`, `-1`, `99999` → 200), `test_lista_pequena_oculta_controle_de_pagina` (**AC04**), `test_pager_renderiza_nas_sete_listas` (**AC15**/FR-022: marcador presente nas 7 listas + relatório e omitido quando `pages <= 1`) e `test_api_custodians_e_assets_preservam_contrato` (**AC11**: `GET /api/v1/custodians` segue sem paginação; `GET /api/v1/assets` e `/movements` mantêm `skip`/`limit` inalterados)

### Implementation for User Story 1

- [x] **T008** [US1] `app/web/routers/assets.py::list_assets`: ler `page`, calcular `skip`, passar ao `AssetService.get_all` (já aceita `skip`/`limit`), expor `total/page/pages/start/end` no contexto
- [x] **T009** [US1] `app/web/templates/assets/list.html`: padronizar o indicador (**FR-004**: `Mostrando X–Y de Z`, linha 164) e incluir a macro `pager`
- [x] **T010** [US1] `app/web/routers/movements.py::list_movements_view` + `movements/list.html`: idem, **passando a exibir o `total` que a rota já recebe** (linha 85 hoje mostra só o tamanho da página)
- [x] **T011** [US1] `app/web/routers/custodians.py` + `custodian_service.py` (param **aditivo** `skip=0, limit=0` — **FR-017**, research R4) + `custodians/list.html`: paginação com total **novo indicador** (**FR-004**)
- [x] **T012** [US1] Idem para `locations.py` + `location_service.py` + `locations/list.html`
- [x] **T013** [US1] Rodar regressão `test_assets.py`, `test_movements_search.py`, `test_api.py`, `test_rbac.py`, **`tests/test_route_inventory.py`** (manifesto **sem** mudança — **AC12**/**FR-003**) e **`tests/test_central_integracoes.py`** (precedente de paginação) — **sem editar teste existente** (**AC14**/**FR-019**)

**Checkpoint**: US1 entregue (MVP utilizável com as 4 primeiras listas)

---

## Phase 4: User Story 2 — Exportar o relatório completo, sem surpresa (Priority: P2)

**Goal**: elimina `limit 10000` e o `limit=1000` da tela; CSV/XLSX completos; PDF avisado; nenhum corte silencioso

**Independent Test**: exportação com >10.000 registros devolve exatamente o total (spec §5 US2 / AC06)

### Tests for User Story 2 (TDD — RED antes) ⚠️

- [ ] **T014** [P] [US2] Testes `test_export_csv_completo_acima_de_10000` (monkeypatch de volume/lote + contagem de linhas == total), `test_export_xlsx_completo`, `test_pdf_aviso_previo_e_corte_residual_avisado` (**AC07**/**FR-011**: tela **e** arquivo), `test_relatorio_web_sem_corte_de_1000` (**AC05** — cobre `/reports/inventory` **e** `/reports/movements`, P6) e `test_export_ignora_page_e_devolve_filtro_completo` (**FR-009**: a exportação usa o filtro inteiro, nunca a página exibida) — RED contra o código atual

### Implementation for User Story 2

- [ ] **T015** [US2] `app/services/report_service.py::get_filtered_assets`: **remover** `limit_query = ... else 10000` (linha 47); `limit=0` passa a significar "todos"
- [ ] **T016** [US2] Novo iterador em lotes de 1.000 (`iter_inventory_csv_rows`/`iter_inventory_rows`) e `generate_inventory_csv`/`generate_inventory_excel`/`generate_inventory_pdf` reescritos **por cima** dele, preservando assinaturas, cabeçalhos, colunas e nome de arquivo (**FR-012**; research R6/R7/R8)
- [ ] **T017** [US2] `app/api/reports_api.py::export_inventory_csv`: `StreamingResponse` com os mesmos `media_type`/`Content-Disposition`; XLSX em *write-only*
- [ ] **T018** [US2] **(P4 — aprovada em 2026-10-11; estendida pela P6)** `app/web/routers/reports.py::view_inventory_report` **e `view_movements_report`**: trocar `limit=1000` por paginação `page`/200 + total; `reports/inventory.html` e `reports/movements_report.html` com indicador, pager e **aviso prévio de PDF quando total > 10.000** (**FR-011**)
- [ ] **T019** [US2] Aplicar a mesma garantia de aviso (FR-013) aos geradores de movimentações/colaboradores/locais e à ata de inventário (`_inventario_rows`)
- [ ] **T020** [US2] Rodar regressão de exportações: `test_report_print_smoke.py`, `test_locations_export.py`, `test_datetime_flows.py`, `test_inventario.py` — **sem editar teste existente**

**Checkpoint**: US2 entregue — nenhum arquivo sai truncado em silêncio

---

## Phase 5: User Story 3 — Auditar e listar o restante do sistema sem limite (Priority: P3)

**Goal**: audit log paginado com filtros de período/usuário; inventários e itens paginados com contadores globais intactos

**Independent Test**: 500 eventos → `/admin/audit?page=3` com total e filtros; 400 itens de inventário → contadores inalterados em qualquer página (spec §5 US3)

### Tests for User Story 3 (TDD — RED) ⚠️

- [ ] **T021** [P] [US3] `test_audit_pagina_com_total_e_filtros_periodo_usuario` (**AC08**), `test_audit_sem_permissao_retorna_403_com_page` (**AC10**/**FR-015**), `test_inventario_contadores_globais_invariantes_por_pagina` e `test_inventario_itens_filtrados_no_servico` (**AC09**), `test_colaboradores_e_locais_paginam_com_total` (**AC01**/**AC02**)

### Implementation for User Story 3

- [ ] **T022** [US3] `audit_service.get_audit_logs`: parâmetro aditivo `offset=0` (research R4); `admin_routes.py::admin_audit_log`: `page` + total + exposição de `start_date`/`end_date`/`user_id` (já suportados)
- [ ] **T023** [US3] `admin/audit/list.html`: indicador com total + pager + novos campos de filtro (mesmo padrão visual dos filtros atuais)
- [ ] **T024** [US3] `inventario_service.py`: novo método de itens com filtro (busca por tombamento/nome + status) **em SQL** e `skip/limit`, retornando `(itens, total)`; `inventario.py::view_inventario` delega (research R5)
- [ ] **T025** [US3] `inventarios/list.html` e `inventarios/detail.html`: pager nos itens + indicador, **preservando** `expected_itens`/`unlisted_itens`, contadores globais (`summary` — **FR-005**) e o fluxo de conferência (`POST buscar`, QR, reconciliação offline)
- [ ] **T026** [US3] Rodar regressão `test_inventario.py`, `test_inventario_offline.py`, `test_rbac.py`

**Checkpoint**: US3 entregue — 7 listas + relatório + audit paginados

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] **T027** [P] **(P5 — aprovada em 2026-10-11)** Eliminar N+1 das listas paginadas: contagens de colaboradores/locais e resumo de inventários por **agregação única** (`GROUP BY`), alimentando dict no contexto; teste `test_listas_sem_n1_de_contagem` (**AC13**/SC-010/FR-020) — escopo **obrigatório**, sem alternativa de recusa nesta execução
- [ ] **T028** [P] Documentação: `docs/ARQUITETURA_E_MANUTENCAO.md` (listagens paginadas + integridade de exportações) e artigo da central de ajuda em `app/services/help_service.py` (FR-021)
- [ ] **T029** [P] Medição de desempenho (**AC13**/SC-010/SC-011) com o harness da análise 2026-10-10 — **critério de SC-011: mediana da página 1 ≤ baseline + 10%** (mesmo banco/harness: SQLite in-memory + `TestClient`, 2.000 bens) — registrar antes/depois em `validacao.md` e **remover** o harness
- [ ] **T030** Verificar `git diff`: `tests/route_manifest.json`, `requirements.txt`, `app/models/`, `migrations/` **sem alteração** (**FR-016**/**FR-018**); executar `tests/test_route_inventory.py` e registrar em `validacao.md` que **nenhuma rota nova** foi criada (**AC12** — a cobertura automatizada de AC12 é essa suíte existente); nenhum teste existente modificado (**AC14**)
- [ ] **T031** Régua completa `.venv/bin/python -m pytest -q` + validação manual do `quickstart.md` §2 (incl. 360 px) + registro final em `validacao.md`
- [ ] **T032** Confirmar em `spec.md` §14 e `checklists/requirements.md` que **P1–P5** constam como aprovadas (2026-10-10 / 2026-10-11); **commit apenas sob pedido explícito**

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) → Phase 2 (helper + macro) → Phase 3 (US1) ─┐
                                        └─────────────────→ Phase 4 (US2)
                                        └─────────────────→ Phase 5 (US3)
Phase 3/4/5 → Phase 6 (Polish)
```

- **T004/T005** bloqueiam tudo.
- **T018 (P4)** e **T027 (P5)** **liberados** — decisões aprovadas em 2026-10-11 (nenhuma pendência de aprovação).
- US2 e US3 são independentes entre si e de US1 após a Phase 2.

### Within Each User Story

Sempre **testes primeiro (RED)** → implementação (GREEN) → regressão do domínio tocado.

### Parallel Opportunities

- T006/T007, T014, T021 (testes) são paralelizáveis entre si.
- T011 (custodians) ∥ T012 (locations) — arquivos distintos.
- T022/T023 (audit) ∥ T024/T025 (inventário).
- T028 ∥ T029 ∥ T030.

## Implementation Strategy

### MVP First (User Story 1 only)

Phase 1 + 2 + 3 já entregam valor real: navegação e total nas listas mais usadas.

### Incremental Delivery

1. `helper + macro` · 2. `assets/movements` · 3. `custodians/locations` · 4. `relatório + exports (US2)` · 5. `audit + inventários (US3)` · 6. `polish/medição`.

### Notas

- Toda mudança de assinatura é **aditiva com default** (Constitution I) — nenhum chamador muda sem a rota pedir.
- Se aparecer diff em `route_manifest.json`, é **erro de escopo**: parar (FR-003/AC12).
- Nenhum teste existente pode ser editado; falha de regressão é investigada como bug da feature, não ajustada no teste (Constitution VIII).
