---
description: "Task list for feature 012 implementation"
---

# Tasks: Seleção de Departamento/Setor no Cadastro de Colaborador

**Input**: Design documents from `/specs/012-selecao-departamento-colaborador/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md (REVISADO — fonte derivada de `Location.department`, zero DDL), data-model.md (RV-1..RV-7), contracts/ (service, ui, api), quickstart.md

**Tests**: Testes são requisito explícito da spec (Seção 8 — "Testes dos cenários desta spec"; SC-007). Cada user story inclui seus testes; escrevê-los ANTES da implementação correspondente (falham primeiro — TDD).

**Organization**: Tasks agrupadas por user story. **Decisão do plano que forma as tarefas**: fonte oficial = valores distintos de `Location.department` (R1 revista); integridade por validação de texto com marcador `department_source=official` (R2/R6/R7 revisadas); `CustodianService`, models, schemas e API **intocados**; **zero DDL**; regra de inativos (Q3/FR-015) inoperante — sem tarefas para ela.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Include exact file paths in descriptions

## Path Conventions

Projeto monolítico em `app/` (web/api/services/models) com suíte em `tests/` — conforme plan.md (Source Code).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Estabelecer a linha de base de regressão antes de qualquer alteração

- [x] T001 Executar a suíte baseline e registrar contagens verdes: `pytest -q` (nenhuma alteração de código nesta fase; base de comparação da Constitution VIII)
- [x] T002 [P] Criar o módulo de testes da feature `tests/test_department_selection.py` com docstring mapeando US1–US4/AC-01..AC-10 e helpers de massa (criar `Location`/`Custodian` via services, padrão de `tests/test_custodians_search.py`) — sem testes ainda

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `DepartmentService` — fonte oficial e validação usadas por TODAS as user stories

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase

- [x] T003 [P] Escrever testes FALHANDO de unidade para `DepartmentService` em `tests/test_department_selection.py` (RV-1/RV-2/RV-3/RV-4 de data-model.md): `list_official` retorna distintos de `locations.department` ordenados alfabético case-insensitive, sem nulos/vazios/trim vazio; `ensure_official` retorna forma canônica (case-insensitive: "SUPORTE" → valor oficial), vazio → `ValueError("Departamento/Setor é obrigatório")`, sem correspondência → `ValueError("Departamento/Setor inválido — selecione um registro da lista oficial")`, ambiguidade (dois oficiais diferindo só por caixa) → erro
- [x] T004 Implementar `list_official(db)` em `app/services/department_service.py` — `SELECT DISTINCT department FROM locations` filtrando nulos e trim vazio, ordenação alfabética case-insensitive (contract service §1.1; precedente `routes.py` linhas 342/406/1806) (depends: T003)
- [x] T005 Implementar `ensure_official(db, department)` em `app/services/department_service.py` — trim, vazio → erro obrigatório, casamento case-insensitive contra `list_official` retornando a forma canônica, sem correspondência/ambíguo → erro inválido (contract service §1.2) (depends: T004)
- [x] T006 Verificar checkpoint da fundação: `pytest tests/test_department_selection.py -q` (testes T003 verdes) e `pytest -q` (suíte existente permanece verde) (depends: T005)

**Checkpoint**: Fonte oficial e validação prontas — user stories podem começar

---

## Phase 3: User Story 1 — Cadastrar colaborador selecionando um Departamento/Setor oficial (Priority: P1) 🎯 MVP

**Goal**: O formulário de cadastro apresenta **campo de seleção (dropdown)** dos valores oficiais (derivados de locais) e o caminho de criação grava o valor canônico (AC-01, AC-02, AC-05; Cenários 1 e 4)

**Independent Test**: Abrir `/custodians/new` → campo é seleção dos oficiais (nada fixo no HTML); selecionar e salvar → colaborador gravado com o valor canônico; `pytest tests/test_department_selection.py -q`

### Tests for User Story 1 ⚠️ (escrever primeiro; devem FALHAR antes de T010–T012)

- [x] T007 [P] [US1] Teste FALHANDO de renderização em `tests/test_department_selection.py`: GET `/custodians/new` contém o marcador oculto `department_source` com valor `official`, o **campo de seleção (dropdown `<select>`)** e cada valor oficial vigente como `<option>`; NÃO contém lista fixa além das opções renderadas do contexto (AC-01/FR-001)
- [x] T008 [P] [US1] Testes FALHANDO de criação em `tests/test_department_selection.py`: POST `/custodians/new` com marcador + valor oficial (inclusive variação de caixa "SUPORTE") → 303 para `/custodians`, colaborador gravado com a forma **canônica** (AC-05/Cenário 1/RV-2); POST com valor oficial após cadastrar/editar local novo → novo valor disponível na lista (derivação ao vivo — RV-1)

### Implementation for User Story 1

- [x] T009 [US1] Atualizar `app/web/templates/custodians/form.html` **ramo de cadastro** (`is_edit` falso): substituir o `<input type="text" name="department">` por **campo de seleção (dropdown `<select class="form-select">`)** dos valores de `departments` (contexto) com opção vazia "— Selecione —", `required` e `<input type="hidden" name="department_source" value="official">` — **sem datalist/pesquisa** (decisão de UX 2026-09-17; R5 revista) (depends: T007)
- [x] T010 [US1] Atualizar `form_new_custodian` em `app/web/routes.py`: injetar `departments = DepartmentService.list_official(db)` no contexto do template (contract UI §4) (depends: T004, T009)
- [x] T011 [US1] Atualizar `create_custodian_form` em `app/web/routes.py`: adicionar `department_source: Optional[str] = Form(None)`; quando `department_source == "official"`, chamar `DepartmentService.ensure_official(db, department)` e usar o valor canônico em `CustodianCreate`; `ValueError` → redirect 303 `?error=` (padrão existente do handler); **sem o marcador, comportamento atual integral** (R6) (depends: T005, T008)
- [x] T012 [US1] Verificar checkpoint US1: `pytest tests/test_department_selection.py -q` (T007/T008 verdes) e `pytest -q` (sem regressão) (depends: T010, T011)

**Checkpoint**: Cadastro via seleção oficial funcional e testável de forma independente (MVP do formulário de criação)

---

## Phase 4: User Story 2 — Validação no backend (Priority: P1)

**Goal**: O servidor rejeita submissões inválidas do caminho do formulário (vazio, fora da lista) e o caminho legado permanece caracterizado (AC-02, AC-03, AC-04; Cenários 2 e 3; api-contract §3)

**Independent Test**: POST direto ao backend com marcador + valor vazio/inválido → redirect com erro e nada persistido; POST de API com texto livre → 201 (caracterização); `pytest tests/test_department_selection.py -q`

### Tests for User Story 2 ⚠️

- [x] T013 [P] [US2] Teste FALHANDO em `tests/test_department_selection.py`: POST `/custodians/new` com marcador e `department` vazio → redirect 303 com `error=` contendo "obrigatório"; NENHUM `Custodian` persistido (AC-03/Cenário 2/RV-4)
- [x] T014 [P] [US2] Teste FALHANDO em `tests/test_department_selection.py`: POST `/custodians/new` com marcador e valor fora da lista (ex.: "Setor Inexistente XYZ") → redirect 303 com `error=` contendo "inválido"; NENHUM `Custodian` persistido (AC-04/Cenário 3/RV-3)
- [x] T015 [P] [US2] Teste de CARACTERIZAÇÃO em `tests/test_department_selection.py` (deve PASSAR sem implementação nova — protege a não-mudança): POST `/api/v1/custodians` com `department` texto livre → 201; POST web **sem** marcador com texto livre → comportamento atual (RV-5/api-contract §3/R6)

### Implementation for User Story 2

- [x] T016 [US2] Garantir a rejeição server-side do vazio no caminho validado: verificar T013; se o vazio escapar de `ensure_official` e chegar a `CustodianService` (gravando ""), reforçar o guard em `create_custodian_form`/`update_custodian_form` em `app/web/routes.py` (chamada a `ensure_official` antes de montar o schema — sem alterar `CustodianService`) (depends: T011, T013)
- [x] T017 [US2] Verificar checkpoint US2: `pytest tests/test_department_selection.py -q` (T013–T015 verdes) e `pytest -q` (depends: T014, T015, T016)

**Checkpoint**: Cadastro validado no backend (obrigatório + lista oficial) com caminho legado preservado — **MVP completo (US1+US2)**

---

## Phase 5: User Story 3 — Editar colaborador usando a mesma lista oficial (Priority: P2)

**Goal**: O formulário de edição usa a mesma fonte oficial, com o valor vigente pré-preenchido, e o caminho de update grava o valor canônico (AC-06; Cenário 5)

**Independent Test**: Abrir `/custodians/{id}/edit` → valor vigente preenchido e lista oficial presente; trocar por outro oficial e salvar → atualizado canônico; `pytest tests/test_department_selection.py -q`

### Tests for User Story 3 ⚠️

- [x] T018 [P] [US3] Teste FALHANDO de renderização em `tests/test_department_selection.py`: GET `/custodians/{id}/edit` contém marcador `department_source=official`, o controle de seleção com `value="{{ custodian.department }}"` pré-preenchido e a lista oficial no contexto (AC-06)
- [x] T019 [P] [US3] Testes FALHANDO de edição em `tests/test_department_selection.py`: POST `/custodians/{id}/edit` com marcador + outro oficial → 303, valor atualizado canônico (Cenário 5); colaborador com valor vigente fora da lista atual (grafia herdada): POST com valor **idêntico ao vigente** → 303 e valor mantido sem re-normalização (FR-014 — remediação I2 opção b, contract UI §2), POST com valor **diferente** inválido → redirect com erro e colaborador inalterado — depende de T018/T019 escreverem os dois fluxos

### Implementation for User Story 3

- [x] T020 [US3] Atualizar `app/web/templates/custodians/form.html` **ramo de edição** (`is_edit` verdadeiro): mesmo controle da US1 com `value="{{ custodian.department }}"` pré-preenchido e o mesmo marcador oculto (contract UI §2) — **mesmo arquivo da T009, executar sequencialmente** (depends: T009, T018)
- [x] T021 [US3] Atualizar `form_edit_custodian` em `app/web/routes.py`: injetar `departments = DepartmentService.list_official(db)` no contexto (depends: T004, T020)
- [x] T022 [US3] Atualizar `update_custodian_form` em `app/web/routes.py`: adicionar `department_source: Optional[str] = Form(None)`; quando marcador presente, `ensure_official` antes de montar `CustodianUpdate` — **exceto** quando o valor submetido (trim) for idêntico ao valor vigente do colaborador, que passa sem re-normalização (remediação I2, opção b); `ValueError` → redirect `?error=`; sem marcador, comportamento atual (depends: T005, T019, padrão da T011)
- [x] T023 [US3] Verificar checkpoint US3: `pytest tests/test_department_selection.py -q` (T018/T019 verdes) e `pytest -q` (depends: T021, T022)

**Checkpoint**: Cadastro E edição com a mesma fonte oficial, validados no backend

---

## Phase 6: User Story 4 — Matrícula provisória e integridade do histórico (Priority: P2)

**Goal**: `PROV-*` usa o campo normalmente; alterar departamento não reescreve histórico; Localização e Cargo/Função intocados; colaboradores pré-existentes preservados (AC-07, AC-08, AC-09; Cenário 6; FR-011/FR-014)

**Independent Test**: Cadastrar `PROV-*` + seleção oficial → permitido; editar departamento de colaborador com movimentação → snapshots de `movements`/`audit_logs` byte-a-byte iguais; `pytest tests/test_department_selection.py -q`

### Tests for User Story 4 (somente testes — nenhuma implementação nesta story)

- [x] T024 [P] [US4] Teste em `tests/test_department_selection.py`: POST `/custodians/new` com `registration_code` vazio + marcador + oficial → 303, colaborador com `PROV-*` (regex `^PROV-\d{6}$`) **e** department canônico; nenhuma regra nova por tipo de matrícula (AC-07/Cenário 6/FR-007)
- [x] T025 [P] [US4] Teste em `tests/test_department_selection.py`: criar colaborador + movimentação (Alocação/Cautela via `MovementService`), capturar snapshots (`origin_custodian_name`/`destination_custodian_name`, `audit_logs`), editar departamento pelo formulário, e assegurar que movimentações/auditoria/termos anteriores permanecem **idênticos** (AC-08/FR-008/RV-6)
- [x] T026 [P] [US4] Teste em `tests/test_department_selection.py`: snapshot comparativo — `locations` (incl. `Location.department`) e `role` dos colaboradores inalterados após os fluxos da feature (AC-09/FR-009/FR-011); colaboradores pré-existentes sem edição permanecem com valores originais (Q2/FR-014)
- [x] T027 [US4] Verificar checkpoint US4: `pytest tests/test_department_selection.py -q` (T024–T026 verdes) e `pytest -q` (depends: T024, T025, T026)

**Checkpoint**: Todas as user stories funcionalmente completas e não-regressão comprovada

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentação fiel e validação final (Constitution XI/XII)

- [x] T028 [P] Atualizar documentação do comportamento visível: `README.md` (seção de colaboradores), `docs/` (arquivos que descrevem cadastro de colaborador) e central de ajuda embutida (`app/services/help_service.py`, quando houver conteúdo sobre colaboradores) — descrever: campo passa a ser seleção oficial derivada dos departamentos dos **locais**; novos valores oficiais surgem do fluxo de locais; obrigatoriedade validada no servidor (Princípio XI)
- [x] T029 Validar `specs/012-selecao-departamento-colaborador/quickstart.md` completo (Seções 1–3) e executar a suíte final `pytest -q` (Seção 4 — Definition of Done) (depends: T028)
- [x] T030 Re-verificar checklist da Constitution em `specs/012-selecao-departamento-colaborador/plan.md`: `git diff` confirma zero alterações em `app/models/`, `app/database.py`, `app/schemas/`, `app/api/`, `app/services/custodian_service.py`, `app/services/custodian_import_service.py`, `app/services/location_service.py` e nenhum teste existente editado (depends: T029)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: imediato — T001 (baseline) deve preceder qualquer alteração
- **Foundational (Phase 2)**: depende do Setup; **BLOQUEIA todas as user stories** (todas usam `DepartmentService`)
- **US1 (Phase 3)** → **US2 (Phase 4)** → **US3 (Phase 5)** → **US4 (Phase 6)**: sequencial por prioridade; US2 depende do wiring de criação (T011); US3 depende do padrão do template/handler da US1 (mesmo arquivo `form.html`); US4 é somente testes sobre o sistema já integrado
- **Polish (Phase 7)**: depende de todas as stories concluídas

### User Story Dependencies

- **US1 (P1)**: após Foundational — sem dependência de outras stories
- **US2 (P1)**: após US1 (o caminho validado precisa existir para ser rejeitado/testado)
- **US3 (P2)**: após US1 (mesmo template, padrão de handler) — independentemente testável
- **US4 (P2)**: após US2/US3 (exercita fluxos integrados) — apenas testes

### Within Each User Story

- Testes escritos primeiro e FALHANDO (exceto caracterização T015 — deve passar)
- Template/contexto (GET) antes do handler (POST) quando acoplados
- Checkpoint de suíte ao final de cada story

### Parallel Opportunities

- T002, T003 (fase 1/2 — arquivos distintos)
- T007 e T008; T013, T014 e T015; T018 e T019; T024, T025 e T026 (testes da mesma story, mesma convenção — podem ser escritos em lote)
- T028 (docs) em paralelo com as stories, desde que descreva comportamento já fixado nos contratos
- Atenção: T009 e T020 editam o **mesmo** `form.html` — sequenciais (fases distintas)

---

## Implementation Strategy

### MVP First (US1 + US2 — ambas P1)

1. Phase 1 (baseline) + Phase 2 (DepartmentService)
2. Phase 3 (US1: cadastro com seleção) → validar checkpoint
3. Phase 4 (US2: rejeições no backend + caracterização do legado) → **STOP and VALIDATE**: quickstart §3 passos 1–5
4. Deploy/demo se pronto

### Incremental Delivery

1. Setup + Foundational → fundação pronta
2. +US1 → cadastro padronizado (demo)
3. +US2 → validação server-side (MVP completo)
4. +US3 → edição com a mesma fonte
5. +US4 → garantias de integridade/compatibilidade comprovadas
6. Polish → documentação + validação final

### Parallel Team Strategy

Com mais de um executor: Foundational juntos; depois A = US1+US2 (P1), B = prepara testes US3/US4 (T018/T019/T024–T026 podem ser escritos antes); integração sequencial nos checkpoints (mesmo arquivo `form.html` é o único ponto de conflito).

---

## Notes

- **Sem tarefas para FR-015 (inativos)**: decisão da research R9 revista — fonte `Location.department` não possui conceito ativo/inativo; a spec tornou a regra condicional. Registrado no backlog.
- **Nenhuma tarefa altera**: `app/models/`, `app/database.py`, `app/schemas/`, `app/api/`, `app/services/custodian_service.py`, `app/services/custodian_import_service.py`, `app/services/location_service.py` ou qualquer teste existente (Constitution VIII; quickstart §1 é a prova).
- [P] = arquivos distintos, sem dependência pendente; [Story] mapeia à spec para rastreabilidade AC↔task.
- Commits após cada task ou grupo lógico; parar nos checkpoints para validar cada story independentemente.
