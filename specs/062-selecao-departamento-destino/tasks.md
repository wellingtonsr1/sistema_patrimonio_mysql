# Tasks: Seleção de Destino por Departamento/Setor (Feature 062)

**Input**: Design documents from `/specs/062-selecao-departamento-destino/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/ui-contract.md](./contracts/ui-contract.md), [quickstart.md](./quickstart.md)

**Tests**: INCLUÍDOS — TDD red→green solicitado pelo usuário e exigido pela Constitution VIII. Cada história começa pelos testes (RED comprovado) e só então altera o template (GREEN).

**Organization**: Tasks agrupadas por user story (US1 movimentação · US2 equipamento · US3 guarda de não-mutação). Raio total: 2 templates + 1 arquivo de testes novo — **nenhum arquivo de backend/banco é tocado** (FR-009).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Projeto monolítico: `app/` (código) e `tests/` na raiz. Alterações de produção limitadas a `app/web/templates/movements/new.html` e `app/web/templates/assets/form.html`.

---

## Phase 1: Setup

**Purpose**: Estabelecer a régua de partida (nada a inicializar — projeto existente).

- [ ] T001 Executar a suíte completa (`python -m pytest`) e registrar a régua de partida esperada **923 passed / 1 skipped / 0 failed** como baseline nas notas de validação (qualquer desvio deve ser resolvido ANTES de iniciar as histórias — Princípio VIII)

**Checkpoint**: Baseline verde documentado.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Nenhuma task nesta fase** — a feature não cria infraestrutura compartilhada: a fonte dos dados (`LocationService.get_all`) e os routers (`form_new_movement`, `form_new_asset`) já fornecem tudo (research R1/R2; plan §Technical Context). Passar direto para a Phase 3.

---

## Phase 3: User Story 1 — Escolher o destino pelo Departamento/Setor (Priority: P1) 🎯 MVP

**Goal**: O select "Novo Local / Departamento" em `/movements/new` apresenta opções agrupadas por Unidade Administrativa (`optgroup`) com rótulo `Departamento (Unidade)`, value = id do local, e a opção vazia `-- Manter Local Atual --` primeira e fora de grupo (ui-contract §1).

**Independent Test**: `GET /movements/new` com localizações de ≥2 unidades → grupos e rótulos conforme contrato; transferência submetida com opção da nova lista grava id + snapshot exatamente como hoje.

### Tests for User Story 1 (escritos ANTES da implementação — devem FALHAR) ⚠️

- [ ] T002 [P] [US1] Criar `tests/test_departamento_destino_062.py` (docstring referenciando a Feature 062 e o ui-contract §1) com o teste de renderização da movimentação: usar `LocationService.create(db_session, LocationCreate(...))` (helper `_criar_locais_062(db_session)` no próprio arquivo) para criar EXATAMENTE 3 locais: `(name="Sede - Divisão de Previdência", branch="IPMJP - Sede", department="Divisão de Previdência")`, `(name="Sede - Setor de Arquivo", branch="IPMJP - Sede", department="Setor de Arquivo")` e `(name="Clube da Pessoa Idosa", branch="Clube", department="Clube da Pessoa Idosa")`; `html = client.get("/movements/new").text`; ASSERTS obrigatórios: (a) `html.index("-- Manter Local Atual --") < html.index("<optgroup")` (opção vazia primeira e fora de grupo); (b) `'<optgroup label="Clube">'` e `'<optgroup label="IPMJP - Sede">'` presentes (grupos por unidade); (c) o trecho entre o `optgroup` de cada unidade e seu `</optgroup>` contém `f"{loc.department} ({loc.branch})"` e `f'<option value="{loc.id}">'` para cada local daquela unidade (rótulo `Departamento (Unidade)` com value correto DENTRO do grupo certo); (c2) ordem intra-grupo (FR-008): dentro do grupo `IPMJP - Sede`, o índice de `Divisão de Previdência (IPMJP - Sede)` é MENOR que o de `Setor de Arquivo (IPMJP - Sede)` (ordem da fonte: departamento → nome); (d) o texto antigo `f"{loc.name} ({loc.branch} - {loc.department})"` **NÃO** está presente (sem redundância); rodar e CONFIRMAR o RED (falha porque o template atual é plano)

### Implementation for User Story 1

- [ ] T003 [US1] Alterar APENAS o corpo do loop do select de destino em `app/web/templates/movements/new.html` (L102–106) conforme ui-contract §1: manter `<select name="destination_location_id" class="form-select">` e a option vazia byte-a-byte; substituir o `{% for loc in locations %}` plano por `{% for branch, locs in locations | groupby('branch') %}` → `<optgroup label="{{ branch }}">` → `<option value="{{ loc.id }}">{{ loc.department }} ({{ branch }})</option>` → `</optgroup>`; NÃO adicionar atributo `selected`, NÃO tocar em nenhum outro elemento do template (research R7)
- [ ] T004 [US1] Rodar `python -m pytest tests/test_departamento_destino_062.py -v` e CONFIRMAR o GREEN da US1; em seguida rodar o subconjunto de regressão `python -m pytest tests/test_movements.py tests/test_help.py` e confirmar que permanece 100% verde SEM edição de nenhum teste existente (research R4)

**Checkpoint**: US1 funcional e testável independentemente — o form de movimentação exibe a nova apresentação e grava como hoje.

---

## Phase 4: User Story 2 — Mesma apresentação no formulário de Equipamento (Priority: P2)

**Goal**: O select de Localização em `/assets/new` adota o mesmo padrão (ui-contract §2), preservando a option vazia `-- Estoque Central / Almoxarifado --` primeira e fora de grupo.

**Independent Test**: `GET /assets/new` → mesmas regras de grupos/rótulos/values da US1, com a opção vazia específica preservada.

### Tests for User Story 2 (escritos ANTES da implementação — devem FALHAR) ⚠️

- [ ] T005 [P] [US2] Adicionar a `tests/test_departamento_destino_062.py` o teste de renderização do equipamento (mesmos dados da T002 — reutilizar `_criar_locais_062` e criar também 1 colaborador no corpo do teste: `CustodianService.create(db_session, CustodianCreate(name="Colaborador 062", email="col062@test.local", role="Agente", department="Divisão de Previdência"))`, sem matrícula → gera `PROV-*`): `html = client.get("/assets/new").text`; ASSERTS obrigatórios: (a) `html.index("-- Estoque Central / Almoxarifado --") < html.index("<optgroup")`; (b) `'<optgroup label="Clube">'` e `'<optgroup label="IPMJP - Sede">'` presentes; (c) rótulo `f"{loc.department} ({loc.branch})"` + `f'<option value="{loc.id}">'` dentro do grupo correto para cada local; (d) NÃO deve haver dois selects alterados indevidamente: o select de COLABORADOR do mesmo form (L121) continua com o rótulo atual `Nome (Matrícula - Departamento)` — o HTML contém `Colaborador 062 (` seguido do department do colaborador no rótulo, imune à mudança; rodar e CONFIRMAR o RED

### Implementation for User Story 2

- [ ] T006 [US2] Alterar APENAS o corpo do loop do select de Localização em `app/web/templates/assets/form.html` (L109–111) conforme ui-contract §2: manter `<select name="location_id" class="form-select">` e a option vazia byte-a-byte; mesmo padrão `groupby('branch')` da T003; NÃO tocar no select de colaborador (L121) nem em nenhum outro campo do form
- [ ] T007 [US2] Rodar `python -m pytest tests/test_departamento_destino_062.py -v` e CONFIRMAR o GREEN da US2; rodar `python -m pytest tests/test_assets.py` e confirmar regressão verde sem edição

**Checkpoint**: US1 E US2 funcionando independentemente — os dois selects de localização exibem a mesma apresentação.

---

## Phase 5: User Story 3 — Integridade do histórico e não-mutação da gravação (Priority: P1)

**Goal**: Provar por teste que a mudança de apresentação NÃO altera gravação: destino = id + snapshot no formato atual; registros anteriores intocados; busca por snapshot funciona (spec US3; ui-contract §5; FR-006/FR-007).

**Independent Test**: Registrar `TRANSFERENCIA_LOCAL` escolhendo destino na nova lista → snapshot gravado no formato `"{branch} - {department} ({name})"` e movimentação anterior da mesma sessão intocada; busca por termo do snapshot encontra o registro.

### Tests for User Story 3 (teste de GUARDA — deve estar VERDE antes E depois da mudança de template)

> Diferente da US1/US2: este teste NÃO é red→green — é a prova de não-mutação. Deve passar ANTES das alterações de template (comportamento atual) e CONTINUAR passando depois.

- [ ] T008 [P] [US3] Adicionar a `tests/test_departamento_destino_062.py` o teste de não-mutação: criar `loc_a` (branch `Unidade A`, dept `Dept A`, name `Sala A`) e `loc_b` (branch `Unidade B`, dept `Dept B`, name `Sala B`) via `LocationService`, bem via `AssetService.create(..., initial_location_id=loc_a.id)` (gera ENTRADA_AQUISICAO com snapshot conhecido); guardar o snapshot da entrada ANTES; `client.post("/movements/new", data={"asset_id": str(asset.id), "movement_type": "TRANSFERENCIA_LOCAL", "destination_location_id": str(loc_b.id), "reason": "Teste 062 nao-mutacao", "operator_name": "Auditor 062"})` (status 303); ASSERTS obrigatórios: (a) a movimentação de transferência gravada tem `destination_location_id == loc_b.id` e `destination_location_name == "Unidade B - Dept B (Sala B)"` (FORMATO atual — FR-006); (b) o snapshot da ENTRADA_AQUISICAO permanece byte-a-byte idêntico ao de antes do POST (nada é regravado — FR-007); (c) `MovementService.get_all_movements` com `filters.search="Dept B"` encontra a transferência e com `filters.search="Dept A"` encontra a entrada (busca por snapshot intacta — US3/AS3); rodar e CONFIRMAR que está VERDE contra o código atual (guarda válida) — este teste roda novamente na T010 e na T012

**Checkpoint**: US3 provada — gravação, histórico e busca idênticos antes e depois da mudança de apresentação.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validação final e registro (padrão da casa).

- [ ] T009 Revisar o diff completo (`git diff app/`) e confirmar o escopo EXATO da 062: APENAS os corpos de loop de `app/web/templates/movements/new.html` e `app/web/templates/assets/form.html` + arquivo de testes novo; NENHUMA alteração em models/services/routers/schemas/API/migrations/static (FR-009; quickstart §4). ⚠️ A árvore de trabalho pode conter mudanças NÃO-commitadas de features anteriores (059/060: sw.js, base/login/setup.html, help_service.py, static/vendor/) — elas NÃO pertencem à 062: avaliar cada arquivo do diff quanto à sua origem (a 062 não as toca) e registrar a conclusão no `validacao.md`
- [ ] T010 Rodar a régua completa `python -m pytest` e registrar o resultado final esperado: **923 + N testes novos, 0 failed, 1 skipped** — NENHUM teste existente editado, enfraquecido ou pulado (Princípio VIII; SC-004)
- [ ] T011 Executar o smoke visual do quickstart §2 (subir a app local, `/movements/new` e `/assets/new`: grupos `Clube` → `IPMJP - Sede` → `Shoping` em ordem alfabética, rótulos `Departamento (Unidade)`, opções vazias preservadas) e anexar os prints antes/depois ao `validacao.md` (SC-005; AC-01/AC-02/AC-06)
- [ ] T012 [P] Escrever `specs/062-selecao-departamento-destino/validacao.md` no padrão da casa (V1–V5: suíte, testes novos red→green, smoke visual com prints, não-mutação, escopo do diff) referenciando spec/plan/quickstart
- [ ] T013 Verificação final da Constitution: percorrer o checklist do plan.md §Constitution Check (escopo, comportamento preservado, camadas, movimentações via motor, RBAC, sem credenciais, zero DDL, testes, documentação, validação) e marcar a execução no `validacao.md` (Princípio XII)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: imediato — baseline obrigatório antes de qualquer alteração.
- **Foundational**: vazia (justificado acima) — histórias podem iniciar após T001.
- **US1 (Phase 3)**: T002 (RED) → T003 (implementação) → T004 (GREEN). Primeira história a entrar.
- **US2 (Phase 4)**: T005 (RED) → T006 (implementação) → T007 (GREEN). Independente da US1 em arquivos distintos — pode rodar em paralelo com a US1 se houver executor separado (arquivos: `assets/form.html` × `movements/new.html` + funções de teste distintas no MESMO arquivo novo — se o mesmo executor fizer as duas, sequencial).
- **US3 (Phase 5)**: T008 é independente de template (testa o backend intocado) — pode ser escrita em paralelo com T002/T005; DEVE estar verde antes da T003 e re-executada na T004/T007/T010.
- **Polish (Phase 6)**: T009–T011 dependem de todas as histórias; T012 depende de T009–T011; T013 fecha a feature.

### User Story Dependencies

- **US1 (P1)**: sem dependência de outras histórias.
- **US2 (P2)**: sem dependência da US1 (arquivo distinto); compartilha apenas o arquivo de testes novo.
- **US3 (P1)**: sem dependência de outras histórias (guarda do comportamento atual).

### Within Each User Story

- Testes primeiro, comprovadamente vermelhos (US1/US2) ou verdes-guarda (US3) antes de tocar template.
- Implementação = somente o corpo do loop do template da história.
- GREEN + subconjunto de regressão da história antes do checkpoint.

### Parallel Opportunities

- T002 [US1], T005 [US2] e T008 [US3] podem ser escritos em paralelo (funções distintas no mesmo arquivo novo; nenhum conflito de conteúdo — apenas commit sequencial).
- T003 (US1) e T006 (US2) tocam arquivos distintos — paralelizáveis entre executores.
- T012 [P] é paralelizável com o smoke (T011) se os prints forem colados depois.

---

## Parallel Example: escrita dos testes (uma passada, antes das implementações)

```text
Task: "T002 [P] [US1] Teste de renderização da movimentação em tests/test_departamento_destino_062.py"
Task: "T005 [P] [US2] Teste de renderização do equipamento em tests/test_departamento_destino_062.py"
Task: "T008 [P] [US3] Teste de não-mutação em tests/test_departamento_destino_062.py"
# Depois: rodar a suíte nova — RED nas funções de US1/US2, VERDE na de US3
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 (baseline) → T002 (RED) → T003 (template da movimentação) → T004 (GREEN + regressão)
2. **STOP and VALIDATE**: `/movements/new` exibindo a nova apresentação; transferência real gravando como hoje (T008 verde)
3. MVP entregável — a dor relatada (destino por setor) já está resolvida

### Incremental Delivery

1. MVP (US1) → validar → (a apresentação já cobre o pedido central)
2. + US2 → consistência nos dois selects → validar
3. + US3 → guarda formal da não-mutação → validar
4. Polish (T009–T013) → validacao.md → feature pronta para commit/deploy pelo fluxo da casa

### Nota de escopo para o implementador

- É PROIBIDO alterar qualquer arquivo além de `app/web/templates/movements/new.html`, `app/web/templates/assets/form.html` e `tests/test_departamento_destino_062.py` (+ artefatos de spec/validacao). Qualquer problema encontrado no caminho (ex.: dados com typos) é registrado como observação, NUNCA corrigido nesta feature (Constitution I — regra permanente de escopo).
- É PROIBIDO alterar o formato dos snapshots (`movement_service.py` L136/L148 etc.) — o teste T008 é a sentinela (Constitution IV).

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- RED comprovado antes do template (US1/US2); US3 é guarda verde-verde
- Commit por grupo lógico ao final (padrão da casa — somente sob pedido do usuário)
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
