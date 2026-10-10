# Tasks: Consulta Detalhada e Edição Controlada de Bens Patrimoniais

**Input**: Design documents from `/specs/067-consulta-edicao-bens/`

**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (user stories), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: **INCLUÍDAS** — solicitadas explicitamente na spec (§12 plano de testes, AC01–AC15, FR-024). TDD red→green no padrão da casa (063/064/066).

**Status**: **CONCLUÍDA (2026-10-10)** — todas as tarefas **T001–T028** executadas: Setup, Foundational, US1 (MVP), US2, US3 e Polish. Suíte final **1005 passed / 2 skipped** (baseline 979; +26 testes novos, 0 regressão). Registro completo em [validacao.md](validacao.md) — inclui as duas limitações declaradas (cenários de navegador não executados; suíte em SQLite in-memory) e a decisão registrada de o histórico considerar apenas `ALTERACAO`. **Commit não criado** (aguarda pedido explícito).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Monolito existente (raiz do repositório): `app/` (web/services/models), `tests/`, `docs/`. Conforme plan.md §Source Code.

---

## Phase 1: Setup (Baseline e decisões)

**Purpose**: Registrar o patamar atual e destravar as pendências antes de mudar qualquer arquivo (Constitution XII / padrão da casa)

- [x] T001 Executar a régua de baseline `.venv/bin/python -m pytest` a partir da raiz e registrar o patamar (passed/failed/skipped) para comparação na validação final, **sem editar nenhum teste**, em `specs/067-consulta-edicao-bens/validacao.md` (criar o arquivo no padrão da casa)
- [x] T002 [P] Confirmar **somente leitura** os fatos da spec §1 que sustentam as decisões: (a) `AssetUpdate` **não** contém `tag`/`status`/`location_id`/`custodian_id`; (b) `AssetService.update` grava operador `"Sistema"` ao mudar `condition`; (c) `write_audit`/`write_change_audit` fazem `commit` interno; (d) `tests/test_route_inventory.py` compara as rotas com `tests/route_manifest.json`; (e) `assets/detail.html` não exibe `notes` nem `updated_at` — se qualquer item divergir da spec, **PARAR e reportar** antes de seguir
- [x] T003 Decisões **P1–P5 aprovadas e registradas** em `specs/067-consulta-edicao-bens/spec.md` (Clarifications + §14, 2026-10-10): P1 tombamento imutável · P2 condição editável na ficha com operador autenticado · P3 controle otimista por `updated_at` · P4 edição de bem `BAIXADO` bloqueada · P5 ata/exportações mantidas com leitura viva (dívida **M-003** em `docs/Melhorias_SisPatrimonio_Pro.md`). **Concluída — libera T005, T012, T016 e T024**

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Endurecimento da camada de serviço (validações, operador, conflito e transação) — base de US2 e US3

**⚠️ CRITICAL**: US2 e US3 não podem começar até T004/T005 estarem completos. US1 (apresentação de dados que já existem) pode começar em paralelo com esta fase.

- [x] T004 Adicionar o parâmetro **aditivo** `commit: bool = True` a `write_audit` e `write_change_audit` em `app/services/audit_service.py` (o `commit` só ocorre quando `True`), preservando **exatamente** o comportamento de todos os chamadores atuais (login, movimento, importação, usuários, AD) — research R5, FR-015
- [x] T005 Estender `AssetService.update` em `app/services/asset_service.py` (fonte única da regra — research R3/R4/R7/R8): assinatura `update(db, asset_id, data, *, operator_name=None, change_reason=None, commit=True, expected_updated_at=None)`; aplicar V1 (nome não vazio), V2 (limites 150/100/100/100/100/150), V3 (`purchase_value >= 0`), V9 ("nada mudou" → nada a gravar, com sinal explícito ao chamador), V10 (conflito por `updated_at`), V11 (bem `BAIXADO` recusado) e manter V4 (unicidade de `serial_number` ignorando o próprio `id`) e o `model_dump(exclude_unset=True)` existentes; na movimentação de `condition`, gravar `operator_name` informado (fallback preservado) e `change_reason`; **sem** tocar em `create`/`get_all`/`get_by_id`/`calculate_depreciation`

**Checkpoint**: Regra de edição centralizada e transacional — US2/US3 liberados

---

## Phase 3: User Story 1 — Consulta detalhada do bem (Priority: P1) 🎯 MVP

**Goal**: A tela `/assets/{id}` passa a exibir **todos** os dados cadastrais (incluindo observações e última atualização), com campos vazios marcados como não informados

**Independent Test**: Abrir o detalhe de um bem completo e de um bem mínimo e conferir todos os campos do §4.1 da spec (AC01/AC02)

### Tests for User Story 1 (TDD — escrever PRIMEIRO) ⚠️

- [x] T006 [P] [US1] Criar `tests/test_consulta_edicao_bens_067.py` com os testes `test_detalhe_exibe_dados_completos` (bem com marca/modelo/série/especificações/observações → todos presentes no HTML, incl. `notes` e `updated_at`) e `test_detalhe_omite_campos_vazios` (bem mínimo → nada de dado fictício) — devem **FALHAR** contra o template atual (RED); espelhar helpers de `tests/test_fluxo_global_064.py`/`tests/test_presentacao_trilha_063.py` (fixtures `client`/`db_session`)
- [x] T007 [P] [US1] Acrescentar em `tests/test_consulta_edicao_bens_067.py` os testes `test_detalhe_403_sem_permissao` (usuário sem `patrimonio.visualizar` → 403) e `test_detalhe_404_bem_inexistente` (id inexistente → 404) — guardas de AC07/AC03

### Implementation for User Story 1

- [x] T008 [US1] Alterar `app/web/templates/assets/detail.html`: exibir **Observações** (`asset.notes`) quando preenchidas e **Última atualização** (`asset.updated_at` com filtro `localtime`), organizando a ficha em seções legíveis e mantendo campos vazios como "não informado"/omitidos — **sem** redesenho fora do escopo e **sem** alterar os blocos existentes além do necessário (FR-001/FR-002)
- [x] T009 [US1] Executar `.venv/bin/python -m pytest tests/test_consulta_edicao_bens_067.py -v -k detalhe` e obter **GREEN** (AC01/AC02/AC03/AC07)

**Checkpoint**: Consulta detalhada completa e testável de forma independente — MVP entregue

---

## Phase 4: User Story 2 — Edição controlada dos dados cadastrais (Priority: P2)

**Goal**: Ação "Editar bem" conduz a `/assets/{id}/edit`, com autorização no backend, campos editáveis restritos, validações, auditoria atômica e sem criar bem novo

**Independent Test**: Como usuário com `patrimonio.editar`, editar nome/marca/modelo/série/especificações e conferir o **mesmo** bem atualizado, com 1 evento de auditoria; sem permissão → 403 e nada gravado

### Tests for User Story 2 (TDD — RED antes da implementação) ⚠️

- [x] T010 [US2] Acrescentar em `tests/test_consulta_edicao_bens_067.py` os testes (todos **RED** hoje): `test_editar_bem_sem_permissao_nega_e_audita` (GET e POST → 403 + `ACESSO_NEGADO` na trilha, sem gravação), `test_editar_bem_autorizado_atualiza_mesmo_registro` (mesmo `id`/`tag`, contagem de `assets` inalterada), `test_edicao_serial_duplicado_rejeitada`, `test_edicao_valida_limites_e_valor_negativo`, `test_edicao_ignora_campos_protegidos_manipulados` (POST com `tag`/`status`/`location_id`/`custodian_id` → inalterados, V5/V6), `test_edicao_grava_auditoria_com_before_after` (1 evento, autor = usuário autenticado, campos de/para), `test_edicao_sem_alteracao_nao_grava` (V9), `test_edicao_falha_nao_deixa_estado_parcial` (`monkeypatch` na trilha → rollback, AC11), `test_alteracao_de_condicao_gera_movimentacao_com_operador_autenticado` (V8, FR-012), `test_edicao_de_bem_baixado_recusada` (P4 aprovada), `test_edicao_conflito_de_versao_recusada` (P3 aprovada), `test_put_api_grava_operador_autenticado_na_condicao` (FR-012 no `PUT /api/v1/assets/{id}`)

### Implementation for User Story 2

- [x] T011 [US2] Criar `app/web/templates/assets/edit.html` espelhando `assets/form.html` (Bootstrap, tema claro/escuro, alerta de erro no topo no padrão `?error=`), com **apenas** os campos editáveis do §4.3 da spec, pré-preenchidos, e o campo oculto `expected_updated_at` (P3 aprovada) — **sem** expor `tag`/`status`/`location_id`/`custodian_id`
- [x] T012 [US2] Adicionar em `app/web/routers/assets.py` as rotas `GET /assets/{asset_id}/edit` (render do formulário; 404 se ausente; recusa para `BAIXADO` — P4 aprovada) e `POST /assets/{asset_id}/edit` — ambas com `require_permission("patrimonio.editar")` — orquestrando: carregar o bem → validar conflito/bem baixado → montar `AssetUpdate` → `AssetService.update(..., operator_name=user.full_name or user.username, commit=False)` → `write_change_audit(before=_asset_audit_snapshot(antes), after=_asset_audit_snapshot(depois), commit=False)` → `db.commit()` único com `rollback` em exceção; redirecionar `303` para `/assets/{asset_id}?updated=true` (sucesso), `?unchanged=true` (V9) ou `/assets/{asset_id}/edit?error=…` (validação/conflito) — contrato em `contracts/web-asset-edit-contract.md`; depende de T004/T005
- [x] T013 [US2] Acrescentar no `app/web/templates/assets/detail.html` a ação **"Editar bem"** visível somente com `can('patrimonio.editar')` e `asset.status.value != 'BAIXADO'` (P4 aprovada), no mesmo padrão dos botões existentes (FR-004) — depende de T012 apenas para a URL final
- [x] T014 [P] [US2] Estender `tests/test_assets.py` com a cobertura do service: operador autenticado e motivo na movimentação de condição, validações V1–V3 e `commit=False` não persistindo antes do `commit` do chamador (Constitution VIII — teste novo, nada existente alterado)
- [x] T027 [US2] Alterar `app/api/assets_api.py`: no `PUT /assets/{asset_id}`, passar `operator_name=(user.full_name or user.username)` (e o motivo da edição de condição) a `AssetService.update` — **sem** mudar os campos aceitos, a resposta `AssetRead` nem os códigos (research R4; FR-012 aplicada também à API; inserida pela análise de consistência de 2026-10-10) — depende de T005
- [x] T015 [US2] Executar `.venv/bin/python -m pytest tests/test_consulta_edicao_bens_067.py tests/test_assets.py -v` e obter **GREEN** (AC03–AC08, AC11, AC12)

**Checkpoint**: Edição controlada funcional e autorizada no backend — US1 + US2 entregues

---

## Phase 5: User Story 3 — Histórico de alterações cadastrais consultável (Priority: P3)

**Goal**: O detalhe apresenta o histórico cadastral (quem, quando, campo, de → para), separado das movimentações, com estado vazio claro

**Independent Test**: Alterar um campo (edição web ou API), abrir o detalhe e conferir o evento com campo/antes/depois/autor/data; bem sem alterações → estado vazio sem erro

### Tests for User Story 3 (TDD — RED) ⚠️

- [x] T016 [P] [US3] Acrescentar em `tests/test_consulta_edicao_bens_067.py` os testes `test_historico_cadastral_separado_de_movimentacoes` (após uma edição, o histórico cadastral mostra campo + valores anterior/novo + autor; a lista de movimentações não é misturada) e `test_historico_vazio_sem_erro` (bem sem alterações → mensagem de vazio, HTTP 200) — **RED**

### Implementation for User Story 3

- [x] T017 [US3] Implementar `AssetService.get_cadastral_history(db, asset_id, limit=50)` em `app/services/asset_service.py` como leitura **somente** da trilha existente (`AuditLog` com `resource == 'Asset' AND resource_id == asset_id`, ações cadastrais `ALTERACAO`/`CRIACAO`, desserializando `previous_data`/`new_data` no padrão já usado por `MovementService.get_timeline_for_asset`) — **sem** alterar `MovementService.get_timeline_for_asset` (contrato da API preservado, research R6) e **sem** criar tabela/mecanismo de auditoria paralelo
- [x] T018 [US3] Alterar `app/web/templates/assets/detail.html` para renderizar a seção/aba **"Alterações cadastrais"** (campo → valor anterior → valor novo, autor, data/hora com `localtime`) **separada** da trilha de movimentação (padrão visual 063), com estado vazio claro quando não houver eventos (FR-016/FR-017) — depende de T017
- [x] T019 [US3] Executar `.venv/bin/python -m pytest tests/test_consulta_edicao_bens_067.py -v` e obter **GREEN** em todos os testes da feature (AC01–AC15)

**Checkpoint**: As três histórias funcionam de forma independente e rastreável

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T020 Atualizar `tests/route_manifest.json` com as rotas novas (`GET`/`POST /assets/{asset_id}/edit`, com os nomes de endpoint reais gerados pelo FastAPI) e executar `.venv/bin/python -m pytest tests/test_route_inventory.py -v` → **GREEN** (AC15; exigência da feature 051 — research R9)
- [x] T021 [P] Atualizar `docs/ARQUITETURA_E_MANUTENCAO.md` (seção de bens/listagem) com: consulta detalhada completa, ação "Editar bem" (`patrimonio.editar`), campos protegidos (tombamento/situação/local/custódia) e histórico cadastral na trilha (Constitution XI)
- [x] T022 [P] Atualizar o artigo de bens da central de ajuda em `app/services/help_service.py` descrevendo como consultar os dados completos e como editar o cadastro (Constitution XI)
- [x] T023 [P] (polimento aprovado) Acrescentar a ação "Editar" também na listagem `app/web/templates/assets/list.html` (ação de linha, visível só com `can('patrimonio.editar')` e oculta para bem `BAIXADO` — P4 aprovada), sem alterar filtros/busca/paginação
- [x] T024 Executar o `quickstart.md` §1 (suíte nova + manifesto + réguas + **réguas de relatórios/exportações/documentos** — `test_locations_export.py`, `test_report_print_smoke.py`, `test_inventario.py`, `test_datetime_flows.py`, AC13 — + régua completa) e §2–§4 (cenários manuais, verificação somente leitura de contagens e de auditoria, contrato da API) e registrar os resultados, incluindo a ressalva da **P5 aprovada** (leitura viva; dívida M-003), em `specs/067-consulta-edicao-bens/validacao.md`
- [x] T025 Conferir `git diff --stat` limitado aos arquivos da spec §11 (`app/web/routers/assets.py`, `app/api/assets_api.py`, `app/web/templates/assets/detail.html`, `app/web/templates/assets/edit.html`, `app/web/templates/assets/list.html`, `app/services/asset_service.py`, `app/services/audit_service.py`, `app/services/help_service.py`, `docs/ARQUITETURA_E_MANUTENCAO.md`, `tests/route_manifest.json`, `tests/test_consulta_edicao_bens_067.py`, `tests/test_assets.py`) — **zero** DDL, zero migração, zero dependência nova, nenhum arquivo fora de escopo
- [x] T026 Fechar `specs/067-consulta-edicao-bens/validacao.md` no padrão da casa: régua final vs baseline T001, checklist da Constitution (escopo/comportamento/serviços/movimentações/banco/testes/docs) e status das decisões **P1–P5 aprovadas em 2026-10-10** (registradas em T003)
- [x] T028 [P] Verificar **FR-020/SC-009/SC-010** (AC14): conferir as classes responsivas (`col-12 col-md-*`) nos templates alterados, executar o cenário `quickstart §2.18` em **360 px** e desktop e conferir a ausência de N+1 novo no detalhe, registrando o resultado em `validacao.md` (alimenta T024; inserida pela análise de consistência de 2026-10-10)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T003)**: T001/T002 sem dependências; **T003 (P1–P5) CONCLUÍDA em 2026-10-10** — T005, T012, T016 e T024 estão liberados
- **Foundational (T004–T005)**: depende de T003; **BLOQUEIA US2 e US3** (US1 pode rodar em paralelo — apenas apresenta dados já existentes)
- **US1 (T006–T009)**: depende do Setup; independente de US2/US3
- **US2 (T010–T015, T027)**: depende de T004/T005; T011 ∥ T010 (template × testes); **T027** (operador autenticado na API) depois de T005 — ID fora da sequência numérica por ter sido incorporada pela análise de consistência de 2026-10-10
- **US3 (T016–T019)**: depende de T005 (validação de conflito não é necessária aqui) e de T017 para T018
- **Polish (T020–T026, T028)**: T020 após T012 (rotas existentes); T021/T022/T023/T028 ∥; T024–T026 por último (T028 alimenta T024)

### Within Each User Story

- Testes escritos e **FALHANDO** antes da implementação (red→green, padrão da casa)
- T004 antes de T005 (a transação depende do `commit` aditivo da auditoria)
- T005 antes de T012 e de T027 (service antes das rotas web e API)
- T017 antes de T018 (leitura antes da renderização)

### Parallel Opportunities

- T001 ∥ T002 ∥ T003 (Setup)
- T004 ∥ T006/T007 (audit_service × testes de detalhe — arquivos diferentes)
- Após T005: **US2 (T010/T011) ∥ US3 (T016/T017)**; T014 ∥ T011
- T021 ∥ T022 ∥ T023 ∥ T028 (docs × ajuda × listagem × verificação de responsividade)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup (baseline + confirmação read-only; decisões P1–P5 **já aprovadas** e registradas)
2. US1: testes RED → template do detalhe → GREEN
3. **PARAR e VALIDAR**: quickstart §2 (cenários 1–5) — "consulta detalhada" já entrega valor sozinha
4. Demo/entrega do MVP de consulta

### Incremental Delivery

1. Setup + Foundational → serviço endurecido (validações/operador/transação)
2. US1 → consulta completa (MVP!)
3. US2 → edição controlada com auditoria atômica e autorização
4. US3 → histórico cadastral separado e legível
5. Polish → manifesto de rotas, documentação, ajuda, `validacao.md` e checagem de escopo do diff

### Notas

- Nenhum teste existente pode ser editado, removido ou enfraquecido (Constitution VIII)
- Nenhuma tarefa cria tabela, coluna, índice, migração, permissão, perfil ou dependência (Constitution VI/VII)
- `tag`/`status`/`location_id`/`custodian_id` nunca entram no schema de edição (Constitution IV)
- Commit apenas sob pedido explícito do usuário
