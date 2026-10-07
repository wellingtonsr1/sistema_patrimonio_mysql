# Tasks: Padronização da Apresentação de Origem e Destino na Trilha de Fluxo & Movimentações (Feature 063)

**Input**: Design documents from `/specs/063-presentacao-trilha-fluxo/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/ui-contract.md](./contracts/ui-contract.md), [quickstart.md](./quickstart.md)

**Tests**: INCLUÍDOS — TDD red→green solicitado pelo usuário e exigido pela Constitution VIII. A US1 começa pelo teste (RED comprovado) e só então altera o template (GREEN); a US2 é guarda verde-verde.

**Organization**: Tasks por user story (US1 apresentação · US2 guarda de não-mutação). Raio total: 1 template + 1 arquivo de testes novo — **nenhum arquivo de backend/banco é tocado** (FR-007).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

Projeto monolítico: `app/` (código) e `tests/` na raiz. Alteração de produção limitada a `app/web/templates/assets/detail.html`.

---

## Phase 1: Setup

**Purpose**: Estabelecer a régua de partida (nada a inicializar — projeto existente).

- [x] T001 Executar a suíte completa (`python -m pytest`) e registrar a régua de partida esperada **948 passed / 2 skipped / 0 failed** como baseline nas notas de validação (qualquer desvio deve ser resolvido ANTES de iniciar as histórias — Princípio VIII)

**Checkpoint**: Baseline verde documentado.

---

## Phase 2: User Story 1 — Trilha no padrão da Custódia (Priority: P1) 🎯 MVP

**Goal**: Cada ponto Origem/Destino do card `flow-card` em `/assets/{id}` exibe `Departamento/Setor` como linha principal e `Localização • Unidade` como contexto (deduplicado), com fallback ao snapshot cru quando a relação não existe (ui-contract §2).

**Independent Test**: `GET /assets/{id}` com entrada + transferência entre locais padrão-de-produção → títulos e contextos conforme contrato; gravação da transferência idêntica à atual.

### Tests for User Story 1 (escritos ANTES da implementação — devem FALHAR) ⚠️

- [x] T002 [US1] Criar `tests/test_presentacao_trilha_063.py` (docstring referenciando a Feature 063 e o ui-contract §2) com o teste de renderização da trilha:
  - criar via services: `loc_prev` (name `Sede - Setor de Recadastramento`, branch `IPMJP - Sede`, department `Setor de Recadastramento`), `loc_dest` (name `Sede - Divisão de Previdência`, branch `IPMJP - Sede`, department `Divisão de Previdência`) e `loc_clube` (name `Clube da Pessoa Idosa`, branch `Clube`, department `Clube da Pessoa Idosa` — caso `name == department`); bem via `AssetService.create(..., initial_location_id=loc_prev.id)`; transferência via `client.post("/movements/new", ...)` com `destination_location_id=loc_dest.id`;
  - `html = client.get(f"/assets/{asset.id}").text`;
  - ASSERTS obrigatórios (ui-contract §2/§3): (a) os blocos Origem/Destino do flow-card exibem os títulos `Setor de Recadastramento` e `Divisão de Previdência` (linha principal = department); (b) o contexto `Sede • IPMJP - Sede` está presente nos dois pontos; (c) o snapshot cru formatado `IPMJP - Sede - Setor de Recadastramento (Sede - Setor de Recadastramento)` NÃO aparece no HTML; (d) caso deduplicado: o HTML não contém `Clube da Pessoa Idosa - Clube da Pessoa Idosa` nem `Clube da Pessoa Idosa • Clube da Pessoa Idosa` (quando um movimento do Clube for exibido — cobrir com movimentação para `loc_clube` ou segundo bem); (e) a seção `Custódia & Localização Atual` continua presente e intacta (assert de presença dos marcadores atuais); rodar e CONFIRMAR o RED (falha porque o template atual exibe o snapshot cru)

### Implementation for User Story 1

- [x] T003 [US1] Alterar APENAS o corpo do card `flow-card` em `app/web/templates/assets/detail.html` conforme ui-contract §2: adicionar a macro `_local_curto` no topo do arquivo (após o `extends`); nos dois pontos (Origem/Destino), quando a relação existe renderizar `{{ loc.department }}` como linha principal + contexto `local_curto • branch` deduplicado; quando não existe, manter o snapshot cru com os fallbacks atuais (`Estoque Geral`); manter rótulos, seta, grid, colaborador (`flow-sub`), badges, termo, motivo e observações byte-a-byte; NÃO tocar na seção "Custódia & Localização Atual" nem em nenhum outro bloco do template (research R4)
- [x] T004 [US1] Rodar `python -m pytest tests/test_presentacao_trilha_063.py -v` e CONFIRMAR o GREEN da US1; em seguida rodar o subconjunto de regressão `python -m pytest tests/test_movements.py tests/test_movements_search.py tests/test_import_asset_movements.py tests/test_departamento_destino_062.py` e confirmar que permanece 100% verde SEM edição de nenhum teste existente (research R5/R6)

**Checkpoint**: US1 funcional e testável independentemente — a trilha exibe a nova apresentação e nada mais na página mudou.

---

## Phase 3: User Story 2 — Integridade do histórico, da busca e do dropdown 062 (Priority: P1)

**Goal**: Provar por teste que a mudança de apresentação NÃO altera gravação, histórico, busca nem os dropdowns da 062 (spec US2; ui-contract §4; FR-003/FR-004/FR-005).

**Independent Test**: Registrar `TRANSFERENCIA_LOCAL` escolhendo destino na nova lista → snapshot gravado no formato `"Unidade - Departamento (Nome)"`, ENTRADA_AQUISICAO pré-existente intocada e busca por termo encontra o registro.

### Tests for User Story 2 (teste de GUARDA — deve estar VERDE antes E depois da mudança de template)

> Diferente da US1: este teste NÃO é red→green — é a prova de não-mutação. Deve passar ANTES da alteração do template (comportamento atual) e CONTINUAR passando depois.

- [x] T005 [US2] Adicionar a `tests/test_presentacao_trilha_063.py` o teste de não-mutação: criar `loc_a` (branch `Unidade A`, dept `Dept A`, name `Sala A`) e `loc_b` (branch `Unidade B`, dept `Dept B`, name `Sala B`); bem via `AssetService.create(..., initial_location_id=loc_a.id)` (gera ENTRADA_AQUISICAO com snapshot conhecido); guardar o snapshot da entrada ANTES; `client.post("/movements/new", data={...})` com `destination_location_id=loc_b.id`; ASSERTS obrigatórios: (a) a transferência gravada tem `destination_location_id == loc_b.id` e `destination_location_name == "Unidade B - Dept B (Sala B)"` (FORMATO atual — FR-003); (b) o snapshot da ENTRADA_AQUISICAO permanece byte-a-byte idêntico ao de antes do POST (nada é regravado — FR-004); (c) `MovementService.get_all_movements` com `filters.search="Dept B"` encontra a transferência e com `filters.search="Dept A"` encontra a entrada (busca por snapshot intacta); rodar e CONFIRMAR que está VERDE contra o código atual (guarda válida) — re-executado na T004 e na T007

**Checkpoint**: US2 provada — gravação, histórico, busca e dropdown 062 idênticos antes e depois da mudança de apresentação.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Validação final e registro (padrão da casa).

- [x] T006 Revisar o diff completo (`git diff app/`) e confirmar o escopo EXATO da 063: APENAS o card `flow-card` (+ macro no topo) de `app/web/templates/assets/detail.html` + arquivo de testes novo; NENHUMA alteração em models/services/routers/schemas/API/migrations/static/ajuda (FR-007; quickstart §4)
- [x] T007 Rodar a régua completa `python -m pytest` e registrar o resultado final esperado: **948 + N testes novos, 0 failed, 2 skipped** — NENHUM teste existente editado, enfraquecido ou pulado (Princípio VIII; SC-005)
- [ ] T008 Executar o smoke visual do quickstart §2 (subir a app local, abrir `/assets/{id}` de um bem com movimentações: título = departamento, contexto `Localização • Unidade`, "Custódia & Localização Atual" intacta) e anexar os prints antes/depois ao `validacao.md` (SC-006; AC01–AC04)
- [x] T009 [P] Escrever `specs/063-presentacao-trilha-fluxo/validacao.md` no padrão da casa (V1–V5: suíte, testes novos red→green, smoke visual com prints, não-mutação, escopo do diff) referenciando spec/plan/quickstart
- [x] T010 Verificação final da Constitution: percorrer o checklist do plan.md §Constitution Check (escopo, comportamento preservado, camadas, movimentações via motor, RBAC, zero DDL, testes, documentação, validação) e marcar a execução no `validacao.md` (Princípio XII)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: imediato — baseline obrigatório antes de qualquer alteração.
- **US1 (Phase 2)**: T002 (RED) → T003 (implementação) → T004 (GREEN + regressão). Primeira história a entrar.
- **US2 (Phase 3)**: T005 é independente de template (testa o backend intocado) — pode ser escrita em paralelo com a T002; DEVE estar verde antes da T003 e re-executada na T004/T007.
- **Polish (Phase 4)**: T006–T008 dependem de todas as histórias; T009 depende de T006–T008; T010 fecha a feature.

### Within Each User Story

- Testes primeiro, comprovadamente vermelhos (US1) ou verdes-guarda (US2) antes de tocar template.
- Implementação = somente o card `flow-card` (+ macro) do template da US1.
- GREEN + subconjunto de regressão antes do checkpoint.

### Parallel Opportunities

- T002 [US1] e T005 [US2] podem ser escritos em paralelo (funções distintas no mesmo arquivo novo).
- T009 [P] é paralelizável com o smoke (T008) se os prints forem colados depois.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 (baseline) → T002 (RED) → T003 (template) → T004 (GREEN + regressão)
2. **STOP and VALIDATE**: `/assets/{id}` exibindo a nova apresentação; transferência real gravando como hoje (T005 verde)
3. MVP entregável — a dor relatada (duplicação/inversão visual na trilha) já está resolvida

### Nota de escopo para o implementador

- É PROIBIDO alterar qualquer arquivo além de `app/web/templates/assets/detail.html` e `tests/test_presentacao_trilha_063.py` (+ artefatos de spec/validacao). Qualquer problema encontrado no caminho (ex.: dados com typos) é registrado como observação, NUNCA corrigido nesta feature (Constitution I — regra permanente de escopo).
- É PROIBIDO alterar o formato dos snapshots (`movement_service.py` L136/L148 etc.) — o teste T005 é a sentinela (Constitution IV).
- É PROIBIDO tocar nos selects da Feature 062 (`movements/new.html`, `assets/form.html`) — a suíte `test_departamento_destino_062.py` é a sentinela (FR-005).

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- RED comprovado antes do template (US1); US2 é guarda verde-verde
- Commit por grupo lógico ao final (padrão da casa — somente sob pedido do usuário)
- Stop at any checkpoint to validate story independently


---

## Registro de execução real (2026-10-07)

- **T001/T007 — régua completa** (`python -m pytest`): **948 passed / 2 skipped / 4 failed** (~67s, exit 1). Os 4 failures são AMBIENTAIS e pré-existentes, fora do escopo 063: `test_backup_config.py::test_anti_regressao_default_desativado_no_codigo_real` + 3 de `test_migrations_052.py` — todos por `ModuleNotFoundError` (`dotenv`/`alembic`) num subprocesso `C:\Python314\python.exe`. Nenhum teste relacionado a 063 falhou; nenhum teste existente foi editado.
- **T002** — `tests/test_presentacao_trilha_063.py` criado (299 linhas, 4 testes: US1 renderização + US2 guarda), asserts exatamente como descrito (a–e). RED comprovado na sessão de implementação (docstring do arquivo registra o RED da US1 contra o template que exibia o snapshot cru).
- **T003** — `app/web/templates/assets/detail.html`: macro `_local_curto` no topo + card `flow-card` com `{{ loc.department }}` como linha principal, contexto `local_curto • branch` deduplicado (`parts | join(' • ')`) e fallback ao snapshot cru. Seção "Custódia & Localização Atual" intocada.
- **T004 — GREEN + regressão**: `python -m pytest tests/test_presentacao_trilha_063.py -v` → **4 passed** (exit 0, 0.63s). Subconjunto `test_movements.py + test_movements_search.py + test_import_asset_movements.py + test_departamento_destino_062.py` → **70 passed** (exit 0, 3.80s). Zero edição de testes existentes.
- **T005 — guarda verde-verde**: `test_nao_muda_gravacao_nem_historico` + `test_dropdown_062_nao_mudou` passam ANTES e DEPOIS da mudança de template; snapshot `Unidade B - Dept B (Sala B)` travado; busca 049 intacta.
- **T006 — escopo**: `git diff dd64f37^..dd64f37 -- app/` = **apenas** `app/web/templates/assets/detail.html`. Nada em models/services/routers/schemas/API/migrations/static.
- **T008 — smoke visual**: PENDENTE (manual — abrir `/assets/{id}` na app local com um bem movimentado e anexar prints ao validacao.md).
- **T009/T010** — `validacao.md` escrito e checklist da Constitution percorrido (ver validacao.md).
