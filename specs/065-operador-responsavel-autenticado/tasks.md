# Tasks: Operador Responsável Vinculado ao Usuário Autenticado

**Input**: Design documents from `/specs/065-operador-responsavel-autenticado/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/movements-api-contract.md, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verificação inicial da infraestrutura da feature

- [x] T001 Verify specification and design documents in `specs/065-operador-responsavel-autenticado/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Validação prévia da suíte de testes existente

- [x] T002 Verify test environment execution via `.venv\Scripts\pytest.exe tests/test_movements.py`

---

## Phase 3: User Story 1 — Preenchimento e Definição Automática do Operador (Priority: P1) 🎯 MVP

**Goal**: Preencher automaticamente o campo "Operador Responsável" no HTML `/movements/new` com a identidade do usuário logado e gravar a movimentação no backend com a identidade autenticada.

**Independent Test**: Fazer login no sistema, acessar `/movements/new` e submeter uma movimentação, verificando que o operador exibe o nome do usuário logado e é persistido no banco com esse mesmo nome.

### Implementation for User Story 1

- [x] T003 [P] [US1] Update HTML template `app/web/templates/movements/new.html` line 125 to set input value to `{{ current_user.full_name or current_user.username if current_user else 'Operador do Patrimônio' }}` and add `readonly` attribute with help text "(Preenchido automaticamente)"
- [x] T004 [US1] Update Web router endpoint `create_movement_form` in `app/web/routers/movements.py` to extract authenticated user from `request.state.user` and override `operator_name` with `(user.full_name or user.username)[:100]`
- [x] T005 [P] [US1] Add unit test in `tests/test_movements.py` verifying that GET `/movements/new` renders the input as `readonly` with the authenticated user name
- [x] T006 [US1] Add unit test in `tests/test_movements.py` verifying that POST `/movements/new` creates a movement record with `operator_name` matching `request.state.user`

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 — Proteção Contra Falsificação de Identidade (Priority: P2)

**Goal**: Garantir imunidade contra falsificação de dados (anti-spoofing) no formulário web e na REST API.

**Independent Test**: Enviar requisições POST para `/movements/new` e `/api/v1/movements` contendo `operator_name="Nome Falso"` no corpo da requisição e verificar que o servidor ignora o valor manipulado, gravando a identidade real da sessão.

### Implementation for User Story 2

- [x] T007 [P] [US2] Update REST API endpoint `record_movement` in `app/api/movements_api.py` to extract authenticated user from `request.state.user` and override `data.operator_name` with `(user.full_name or user.username)[:100]`
- [x] T008 [US2] Add security test in `tests/test_movements.py` sending a POST to `/movements/new` with tampered `operator_name` form payload and asserting that `movement.operator_name` in DB matches `request.state.user`
- [x] T009 [P] [US2] Add security test in `tests/test_movements.py` sending a POST to `/api/v1/movements` with tampered `operator_name` JSON payload and asserting that `movement.operator_name` in DB matches `request.state.user`

**Checkpoint**: At this point, User Stories 1 AND 2 both work independently and securely.

---

## Phase 5: User Story 3 — Preservação de Histórico, Documentos e Rotas Alternativas (Priority: P3)

**Goal**: Assegurar zero regressão nos registros históricos, na geração de termos de responsabilidade e no fluxo de importação em lote (`/assets/import`).

**Independent Test**: Consultar movimentações antigas no histórico, gerar um termo de responsabilidade em PDF/HTML e executar uma importação em lote para verificar se tudo permanece 100% funcional.

### Implementation for User Story 3

- [x] T010 [P] [US3] Add regression test in `tests/test_movements.py` verifying that existing historical movements with `operator_name="Operador do Patrimônio"` remain readable and unaltered
- [x] T011 [P] [US3] Add integration test in `tests/test_movements.py` verifying that term of responsibility generation (`GET /movements/{id}/term`) works properly with the automatically set `operator_name`

**Checkpoint**: All user stories are now independently functional and regression-tested.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validação final de regressão da aplicação

- [x] T012 Run full test suite `.venv\Scripts\pytest.exe` to ensure 100% pass rate across all tests
- [x] T013 [P] Execute quickstart validation steps from `specs/065-operador-responsavel-autenticado/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - starts immediately.
- **Foundational (Phase 2)**: Depends on Setup completion.
- **User Story 1 (Phase 3 - MVP)**: Depends on Foundational completion.
- **User Story 2 (Phase 4)**: Depends on User Story 1 completion.
- **User Story 3 (Phase 5)**: Depends on User Story 1 & 2 completion.
- **Polish (Phase 6)**: Depends on all user stories completion.

### Parallel Opportunities

- T003 (`new.html`), T005 (test GET `/movements/new`) can be worked on in parallel.
- T007 (`movements_api.py`), T009 (REST API test) can be worked on in parallel.
- T010 (historical test), T011 (term test) can be worked on in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 & 2.
2. Complete Phase 3 (User Story 1 - T003 to T006).
3. **STOP & VALIDATE**: Test User Story 1.

### Incremental Delivery
1. Add User Story 2 (T007 to T009) → Validate Anti-Spoofing.
2. Add User Story 3 (T010 to T011) → Validate Regression.
3. Complete Phase 6 (T012 to T013) → Final green suite.
