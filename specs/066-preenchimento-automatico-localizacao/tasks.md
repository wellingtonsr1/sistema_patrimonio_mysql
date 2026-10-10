# Tasks: Preenchimento Automático do Campo Localização

**Input**: Design documents from `/specs/066-preenchimento-automatico-localizacao/`

**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (user stories), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: **INCLUÍDAS** — solicitadas explicitamente na spec (§12 Plano de testes, AC12, FR-010). TDD red→green no padrão da casa (063/064).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Monolito existente (raiz do repositório): `app/` (web/services/models), `tests/`, `docs/`. Conforme plan.md §Source Code.

---

## Phase 1: Setup (Baseline)

**Purpose**: Registrar o patamar atual antes de qualquer mudança (Constitution XII / padrão da casa)

- [x] T001 Executar a régua de baseline `python -m pytest` a partir da raiz e registrar o patamar (passed/failed/skipped) para comparação na validação final, sem editar nenhum teste, em `specs/066-preenchimento-automatico-localizacao/validacao.md` (criar o arquivo no padrão da casa)
- [x] T002 [P] Confirmar somente-leitura que `app/web/templates/locations/form.html` segue a situação da spec §1.1 (campos `name`/`branch`/`department` livres, sem `<script>`) e que `tests/conftest.py` expõe as fixtures `client`/`db_session` — se divergente da spec, PARAR e reportar antes de seguir

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: A regra de composição compartilhada — bloqueia US1 e US2

**⚠️ CRITICAL**: Nenhuma história de usuário pode começar até esta fase estar completa

- [x] T003 Implementar o helper puro `LocationService.compose_name(branch: str, department: str) -> str` em `app/services/location_service.py`, com a regra V1 verbatim de `data-model.md`: `f"{branch.strip()} - {department.strip()}"` (um único separador `" - "`, sem espaços excedentes, `None` tratado como string vazia) — **sem** alterar `create`, `update`, `get_by_name` ou `get_all` (research R1; FR-009)

**Checkpoint**: Fonte única da regra pronta — US1 e US2 podem seguir (em paralelo, se desejado)

---

## Phase 3: User Story 1 — Geração automática no formulário de cadastro (Priority: P1) 🎯 MVP

**Goal**: O campo "Localização" é preenchido em tempo real com `Unidade - Departamento` e exibido `readonly`

**Independent Test**: Abrir `/locations/new`, digitar branch e department e ver a composição sincronizada; o campo não é editável (AC01–AC04)

### Tests for User Story 1 (TDD — escrever PRIMEIRO, falhar contra o form atual) ⚠️

- [x] T004 [US1] Criar `tests/test_localizacao_automatica_066.py` com o teste `test_localizacao_gerada_no_template` (login com permissão `locais.criar`, GET `/locations/new`): campo `name` presente com `readonly`, `branch`/`department` com `required`, marcador de preenchimento automático no label/placeholder — deve FALHAR contra o template atual (RED); espelhar helpers das suítes `tests/test_fluxo_global_064.py`/`tests/test_presentacao_trilha_063.py`

### Implementation for User Story 1

- [x] T005 [US1] Alterar `app/web/templates/locations/form.html`: tornar o input `name` `readonly` (mantendo `name="name"` no form — research R3), atualizar o label para indicar preenchimento automático e ajustar o placeholder para o padrão `Unidade - Departamento` (P4 da spec §14)
- [x] T006 [US1] Adicionar em `app/web/templates/locations/form.html` o bloco `<script>` vanilla (padrão `DOMContentLoaded` dos templates da casa, sem CSP no projeto — research R2): listeners `input` em `[name=branch]` e `[name=department]`, composição `branch.strip() + " - " + department.strip()` **idêntica à regra V1**, campo vazio quando um dos dois estiver vazio (FR-001, FR-002, spec §4.2) — depende de T005
- [x] T007 [US1] Executar `python -m pytest tests/test_localizacao_automatica_066.py -v` e obter GREEN no teste de render (AC01–AC04)

**Checkpoint**: US1 funcional e testável de forma independente no navegador (quickstart §2.1–2.4)

---

## Phase 4: User Story 2 — Validação autoritativa no servidor (Priority: P2)

**Goal**: Requisição manipulada não persiste nome divergente; limite de 100 chars respeitado; incompletos nunca criam registro

**Independent Test**: POST a `/locations/new` com `name` adulterado grava a composição; POST com composição >100 chars é rejeitado sem gravação (AC05, AC06, FR-003/FR-004/FR-005)

### Tests for User Story 2 (TDD — RED contra a rota atual) ⚠️

- [x] T008 [US2] Acrescentar em `tests/test_localizacao_automatica_066.py` os testes: (a) `test_post_web_recompoe_nome_ignorando_cliente` — POST com `name="HACK"`, branch/department válidos persiste `compose_name(...)` (AC05); (b) `test_campos_incompletos_nao_criam_registro` — branch ou department vazio não cria registro e a contagem de locais não muda (AC06/V3, cota verbatim de `data-model.md`); (c) `test_nome_composto_acima_de_100_chars_rejeitado` — composição com `len > 100` (limite da coluna `locations.name`) redireciona com `error` e **não** grava truncado (FR-004/V2); (d) `test_duplicidade_por_nome_composto` — 1º POST cria `UNID X - SETOR X`, 2º POST idêntico redireciona com a mensagem existente "Já existe um local cadastrado com este nome" e a contagem de locais não muda (FR-006/AC07, reaproveitando o `ValueError` de `LocationService.create`) — todos devem FALHAR hoje (RED)

### Implementation for User Story 2

- [x] T009 [US2] Alterar `create_location_form` em `app/web/routers/locations.py`: receber `name: Optional[str] = Form(None)` e **ignorar** o valor do cliente; montar `LocationCreate(name=LocationService.compose_name(branch, department), ...)` (research R4, P1 aprovada — só este fluxo web); se `len(name) > 100` → redirect `303` para `/locations/new?error=` com a mensagem exata `Localização gerada excede o limite de 100 caracteres` (via `quote()`, padrão `?error=`) e **sem persistir** — nunca truncamento silencioso (research R5, FR-004); preservar `write_change_audit`, permissão `locais.criar` e redirecionamentos existentes — depende de T003
- [x] T010 [US2] Executar `python -m pytest tests/test_localizacao_automatica_066.py -v` e obter GREEN em todos os testes de servidor (AC05, AC06 e AC07 — item (d) de T008 — reaproveitando o `ValueError` existente de `LocationService.create`)

**Checkpoint**: AC01–AC07 cobertos — servidor é a autoridade (contracts §2)

---

## Phase 5: User Story 3 — Compatibilidade com fluxos existentes (Priority: P3)

**Goal**: API, importações, snapshots e dados históricos permanecem intocados

**Independent Test**: Guardas verdes + réguas de regressão executadas sem edição (AC08–AC12)

### Tests for User Story 3 (guardas) ⚠️

- [x] T011 [US3] Acrescentar em `tests/test_localizacao_automatica_066.py` o teste `test_dados_existentes_intocados_e_regressao`: (a) `PUT /api/v1/locations/{id}` com payload parcial (sem `name`) **não renomeia** o local (AC08/exclude_unset); (b) `POST /api/v1/locations` com `name` explícito fora do padrão é aceito como antes — contrato preservado (P1/FR-007); (c) após um cadastro web, nenhum local pré-existente mudou de nome (contagem e nomes idênticos — AC10/AC11) — RED antes da T009

### Regression (executar sem editar testes)

- [x] T012 [US3] Executar as réguas `python -m pytest tests/test_locations_search.py tests/test_movements.py tests/test_department_selection.py tests/test_import_asset_location.py tests/test_import_asset_movements.py tests/test_departamento_destino_062.py tests/test_presentacao_trilha_063.py tests/test_fluxo_global_064.py -v` e confirmar **0 falhas novas em relação ao baseline registrado em T001** (AC09/AC12 — a casa tem 4 failures ambientais pré-existentes de subprocesso `dotenv`/`alembic`, documentados em `specs/063/validacao.md`); qualquer falha nova deve ser investigada e corrigida **na causa**, nunca por edição ou enfraquecimento de teste existente (Constitution VIII)

**Checkpoint**: Todas as histórias funcionando de forma independente; compatibilidade comprovada

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T013 [P] Atualizar `docs/ARQUITETURA_E_MANUTENCAO.md` (§12.4 Locais) com a nota de que o cadastro web gera o nome automaticamente no padrão `Unidade - Departamento`, mantendo API/importação com `name` explícito (Constitution XI)
- [x] T017 [P] Atualizar o artigo `cadastrar-locais` da central de ajuda em `app/services/help_service.py` para descrever o preenchimento automático do campo Localização (P4 opção A, Constitution XI — depende de T005; mesmo formato de nota do T013)
- [x] T014 [P] Executar o `quickstart.md` §1 (suite nova + réguas + régua completa `python -m pytest`) e §3 (verificação read-only de dados no MariaDB: total e `fora do padrao = 0`) e registrar os resultados em `specs/066-preenchimento-automatico-localizacao/validacao.md`
- [x] T015 Conferir `git diff --stat` limitado aos arquivos da spec §11 (`app/web/templates/locations/form.html`, `app/web/routers/locations.py`, `app/services/location_service.py`, `docs/ARQUITETURA_E_MANUTENCAO.md`, `tests/test_localizacao_automatica_066.py`) — **zero** DDL, zero migração, zero UPDATE, nenhum arquivo fora de escopo alterado
- [x] T016 Fechar `specs/066-preenchimento-automatico-localizacao/validacao.md` no padrão da casa: régua final vs baseline T001, checklist Constitution (escopo/comportamento/serviços/banco/testes/docs), e status das pendências P3/P4 (P1/P2 já aprovadas na spec §14)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: Depende do Setup — **BLOQUEIA US1 e US2** (helper da regra)
- **US1 (Phase 3)**: Depende de Phase 2; independente de US2/US3
- **US2 (Phase 4)**: Depende de Phase 2 (T003); T008–T010 independentes de US1 (a rota não depende do JS)
- **US3 (Phase 5)**: Depende de US2 (T009) para testar o comportamento pós-mudança; réguas (T012) podem rodar após qualquer fase
- **Polish (Phase 6)**: Depende das histórias desejadas estarem completas (T013 paralelo; T014–T016 ao final)

### Within Each User Story

- Testes escritos e FALHANDO antes da implementação (red→green)
- T005 antes de T006 (mesmo arquivo, ordem sequencial)
- T003 antes de T009 (service antes da rota que o consome)

### Parallel Opportunities

- T001 ∥ T002 (Setup)
- T004 ∥ T003 (baseline + helper, arquivos diferentes)
- Após T003: **US1 (T005–T007) ∥ US2 (T008–T009)** — arquivos distintos (`form.html` × `locations.py`)
- T013 ∥ T014 (docs × execução de validação)

---

## Parallel Example: User Story 1

```bash
# Unir em paralelo (arquivos distintos):
Task: "Escrever teste de render em tests/test_localizacao_automatica_066.py (RED)"
Task: "Implementar helper compose_name em app/services/location_service.py (Foundational)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup (baseline)
2. Phase 2: Foundational (CRITICAL — bloqueia tudo)
3. Phase 3: US1 → testar no navegador de forma independente
4. **PARAR e VALIDAR**: quickstart §2.1–2.4
5. Demo/entrega do MVP de preenchimento automático

### Incremental Delivery

1. Setup + Foundational → regra pronta
2. US1 → validação independente (MVP!)
3. US2 → anti-falsificação + limite de tamanho (AC05/AC06 verdes)
4. US3 → guardas + réguas (compatibilidade comprovada)
5. Polish → docs, validacao.md, escopo de diff

### Notas

- Nenhum teste existente pode ser editado, removido ou enfraquecido (Constitution VIII)
- Nenhuma tarefa cria migração, coluna ou tabela (Constitution VII — zero DDL)
- Commit apenas sob pedido explícito do usuário
- Parar em qualquer checkpoint para validar a história de forma independente
