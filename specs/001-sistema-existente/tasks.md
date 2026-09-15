# Tasks: SisPatrimônio Pro — Baseline do Sistema Existente

**Input**: Design documents from `/specs/001-sistema-existente/`

**Prerequisites**: plan.md (✅ presente), spec.md (✅ presente), research.md (✅), data-model.md (✅), contracts/ (✅ 3 contratos), quickstart.md (✅)

**Tests**: **Nenhum teste novo é criado nesta feature** (plan §10, Constitution VIII). A suíte pytest existente (154 testes) é o instrumento de validação — as tarefas abaixo a **executam e classificam** o resultado esperado (153/154, com 1 falha defasada conhecida).

**Organization**: Tarefas agrupadas por user story da spec (US1 Custódia, US2 Inventário, US3 Acesso/Auditoria). Como esta feature **não implementa funcionalidade** (plan §Summary/R1), cada fase de story é um bloco de **validação de cobertura da baseline**: revisão dos artifacts contra o código real + execução dos testes que atestam aquele comportamento.

**Feature Branch**: `001-sistema-existente`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: User story da spec a que a tarefa pertence (US1, US2, US3)
- Todas as descrições incluem caminhos exatos de arquivo

## Path Conventions

- Projeto single-root: aplicação em `app/`, testes em `tests/`, artifacts desta feature exclusivamente em `specs/001-sistema-existente/` (plan §15/§16).

---

## Phase 1: Setup (Contexto da Baseline)

**Purpose**: Confirmar o contexto da feature e o estado limpo do repositório antes de qualquer validação

- [ ] T001 Verificar que `specs/001-sistema-existente/spec.md` e `specs/001-sistema-existente/plan.md` existem e registram a natureza documentacional da baseline (spec §12, plan §Summary)
- [ ] T002 [P] Confirmar via `git status --porcelain` que nenhum arquivo de `app/`, `tests/`, `docs/`, `requirements.txt`, `.env` está modificado e que nenhum commit foi feito (plan §16, quickstart §3)
- [ ] T003 [P] Confirmar que todos os artifacts de design existem em `specs/001-sistema-existente/`: `research.md`, `data-model.md`, `quickstart.md`, `contracts/api-contract.md`, `contracts/web-contract.md`, `contracts/cli-db-contract.md` e `checklists/requirements.md`

**Checkpoint**: Contexto confirmado — a validação por story pode começar; nenhum arquivo de aplicação será tocado daqui em diante.

---

## Phase 2: Foundational (Consistência da Baseline — Bloqueia as Stories)

**Purpose**: Garantir a integridade interna dos artifacts; sem isto, a validação por story seria contra uma baseline inconsistente

**⚠️ CRITICAL**: Nenhuma fase de user story pode começar antes desta fase

- [ ] T004 Cruzar a seção 7 (27 regras de negócio) com a seção 10 (P1–P24) de `specs/001-sistema-existente/spec.md` e confirmar cobertura total (critério SC-003 da spec) — registrar qualquer regra sem preservação correspondente
- [ ] T005 [P] Verificar ausência de placeholders, `[NEEDS CLARIFICATION]` ou texto de exemplo de template em todos os artifacts de `specs/001-sistema-existente/` (quickstart §2)
- [ ] T006 [P] Re-verificar o Constitution Check 12/12 PASS em `specs/001-sistema-existente/plan.md` contra os 12 princípios de `.specify/memory/constitution.md` (nenhuma violação introduzida pelos artifacts)

**Checkpoint**: Baseline internamente consistente — validação por user story pode começar em paralelo

---

## Phase 3: User Story 1 — Custódia rastreável do bem (Priority: P1) 🎯 MVP

**Goal**: Provar que a baseline documenta fielmente o fluxo de custódia (movimentações, termos, integridade patrimonial) e que o comportamento existente permanece verde na suíte

**Independent Test**: Com os artifacts revisados contra `app/web/routes.py`, `app/api/*_api.py`, `app/models/` e os services, executar `pytest tests/test_movements.py tests/test_assets.py tests/test_api.py` — todos devem passar sem nenhuma alteração de código

### Revisão da cobertura da baseline para US1

- [ ] T007 [P] [US1] Revisar as rotas de bens e movimentações em `specs/001-sistema-existente/contracts/web-contract.md` contra `app/web/routes.py` (rotas `/assets*` com `patrimonio.*`, `/movements*` com `movimentacao.*`) e registrar divergência, se houver
- [ ] T008 [P] [US1] Revisar os endpoints de assets/movements/custodians em `specs/001-sistema-existente/contracts/api-contract.md` contra `app/api/assets_api.py`, `app/api/movements_api.py` e `app/api/custodians_api.py` (métodos, rotas, permissões e regras de não-regressão 1–4)
- [ ] T009 [P] [US1] Revisar `specs/001-sistema-existente/data-model.md` §2–§3 (Asset, Movement com 8 tipos e snapshots, Maintenance, Custodian, Location) contra `app/models/asset.py`, `app/models/movement.py`, `app/models/maintenance.py`, `app/models/custodian.py` e `app/models/location.py`
- [ ] T010 [US1] Verificar em `specs/001-sistema-existente/spec.md` §7 (regras 1–7 patrimoniais) e `specs/001-sistema-existente/research.md` R4 que o motor de movimentações está documentado como único caminho de mudança de estado/localização/custódia (`app/services/movement_service.py`), e executar `pytest tests/test_movements.py tests/test_assets.py tests/test_api.py` sem falhas

**Checkpoint**: US1 validada independentemente — baseline de custódia confirmada contra código e suíte

---

## Phase 4: User Story 2 — Inventário comprobatório (Priority: P2)

**Goal**: Provar que a baseline documenta fielmente o ciclo do inventário (snapshot, conferência, não previstos, encerramento, ata) e que o comportamento existente permanece verde

**Independent Test**: Com os artifacts revisados contra `app/models/inventario.py` e `app/services/inventario_service.py`, executar `pytest tests/test_inventario.py` — os 21 testes devem passar sem nenhuma alteração de código

### Revisão da cobertura da baseline para US2

- [ ] T011 [P] [US2] Revisar `specs/001-sistema-existente/data-model.md` §5 (Inventario com código INV-AAAA-NNNN, scope_filters; InventarioItem com snapshot de expectativa, 5 estados, nao_previsto, constraint única) contra `app/models/inventario.py` e `app/models/enums.py`
- [ ] T012 [P] [US2] Revisar as rotas de inventário em `specs/001-sistema-existente/contracts/web-contract.md` contra `app/web/routes.py` (buscar, iniciar, conferir GET/POST, nao-previsto, encerrar — permissões `inventario.*`) e a regra de ouro (inventário nunca altera cadastro) em `app/services/inventario_service.py`
- [ ] T013 [P] [US2] Revisar a ata de inventário em `specs/001-sistema-existente/contracts/api-contract.md` (`/api/v1/reports/inventarios/{id}/{csv,excel,pdf}` — permissão dupla) contra `app/api/reports_api.py`, preservando o comportamento P22 da spec
- [ ] T014 [US2] Verificar em `specs/001-sistema-existente/spec.md` §7 (regras 8–13 de inventário) e §6 (fluxo F5) que snapshot, LOCAL_DIFERENTE exigindo local diverso, não previsto sem duplicação e encerramento condicionado estão documentados, e executar `pytest tests/test_inventario.py` sem falhas

**Checkpoint**: US1 e US2 validadas independentemente — baseline comprobatória confirmada

---

## Phase 5: User Story 3 — Acesso controlado e auditável (Priority: P3)

**Goal**: Provar que a baseline documenta fielmente auth, RBAC deny-by-default, AD e auditoria, e que a suíte de segurança permanece verde (com a única falha conhecida e classificada)

**Independent Test**: Executar `pytest tests/test_rbac.py tests/test_ad.py tests/test_auth.py` — único resultado aceitável: 1 falha conhecida (`test_rbac.py::test_lockout_after_failed_attempts`, espera 5 tentativas × config 10); nenhuma outra falha

### Revisão da cobertura da baseline para US3

- [ ] T015 [P] [US3] Revisar as rotas de administração e permissões em `specs/001-sistema-existente/contracts/web-contract.md` (seção administração, `/admin/*`, `/profile/password`) contra `app/web/admin_routes.py`
- [ ] T016 [P] [US3] Revisar o mecanismo RBAC documentado em `specs/001-sistema-existente/research.md` (R4/R6: `require_permission`, deny-by-default, 29 permissões) contra `app/api/deps.py` e `app/services/permission_service.py`
- [ ] T017 [P] [US3] Revisar `specs/001-sistema-existente/data-model.md` §4 (User, UserSession, RBAC, AuditLog somente-leitura com before/after, ADSettings/ADGroupRole) contra `app/models/user.py`, `app/models/session.py`, `app/models/audit_log.py`, `app/models/ad.py` e `app/services/audit_service.py`
- [ ] T018 [US3] Executar `pytest tests/test_rbac.py` e classificar a falha conhecida `test_lockout_after_failed_attempts` conforme plan §10/quickstart §1 (esperada: teste espera 5, `AUTH_MAX_FAILED_ATTEMPTS` = 10; defasagem pré-existente, fora do escopo) — nenhuma outra falha é aceitável
- [ ] T019 [P] [US3] Executar `pytest tests/test_ad.py tests/test_auth.py` — todas as 49 verificações (32 AD + 17 auth) devem passar
- [ ] T020 [US3] Verificar em `specs/001-sistema-existente/spec.md` §7 (regras 14–27 de acesso/auditoria) e §10 (P1–P9, P17–P24) que lockout, sessão server-side, AD sem autorizar, credenciais nunca logadas e auditoria somente-leitura estão cobertos pelos artifacts revisados em T017–T019

**Checkpoint**: Todas as user stories validadas independentemente

---

## Phase 6: Polish & Cross-Cutting (Validação Final da Baseline)

**Purpose**: Executar o protocolo de validação completo e publicar a baseline como referência

- [ ] T021 Executar o protocolo completo de `specs/001-sistema-existente/quickstart.md` §1: `pytest -v` na raiz — resultado esperado **153 aprovados, 1 falha conhecida**; qualquer falha diferente indica regressão real e bloqueia a entrega
- [ ] T022 [P] Completar o checklist de conformidade da Constitution em `specs/001-sistema-existente/quickstart.md` §4 (escopo, comportamento preservado, sem credenciais, sem DDL, documentação fiel)
- [ ] T023 [P] Verificar os critérios de sucesso SC-001..SC-005 de `specs/001-sistema-existente/spec.md` §8 conforme quickstart §5 (17 módulos, sem invenção, 24 preservações cobrindo 27 regras, suíte verde, baseline como referência)
- [ ] T024 [P] Re-executar `git status --porcelain` e confirmar que apenas `specs/001-sistema-existente/*` e `.specify/feature.json` foram adicionados/alterados desde o início (quickstart §3)
- [ ] T025 Registrar o resultado consolidado da validação (execução da suíte, classificação da falha conhecida, divergências artifact↔código encontradas em T007–T020, critérios SC) na seção "Validation Results" ao final deste `specs/001-sistema-existente/tasks.md`

**Checkpoint**: Baseline validada e publicada — referência obrigatória para toda feature futura (SC-E da spec)

---

## Validation Results

> Preenchido pela tarefa T025. Nada executado ainda — a baseline está aguardando validação.

- **Suíte pytest**: ☐ executada · ☐ 153/154 confirmado · ☐ falha conhecida classificada (lockout 5×10)
- **Divergências artifact ↔ código**: ☐ nenhuma · ☐ encontradas (listar abaixo)
- **Constitution checklist**: ☐ completo
- **SC-001..SC-005**: ☐ verificados
- **Observações**:

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — começa imediatamente
- **Foundational (Phase 2)**: depende da Phase 1 — BLOQUEIA todas as stories (a validação por story só faz sentido contra uma baseline consistente)
- **User Stories (Phases 3–5)**: dependem da Phase 2; entre si são **independentes** e podem rodar em paralelo ou em ordem de prioridade (P1 → P2 → P3)
- **Polish (Phase 6)**: depende da conclusão de todas as stories desejadas (T021 consome o resultado de T010/T014/T018/T019)

### User Story Dependencies

- **User Story 1 (P1)**: pode começar após a Phase 2 — sem dependência das demais
- **User Story 2 (P2)**: pode começar após a Phase 2 — sem dependência das demais (executável de forma independente, como a própria spec define)
- **User Story 3 (P3)**: pode começar após a Phase 2 — sem dependência das demais; sustenta o valor comprobatório de US1/US2 (na spec, não na execução destas tarefas)

### Within Each User Story

- Revisão dos contratos ([P], paralela) → revisão do data-model ([P]) → verificação das regras + execução dos testes do story (tarefa final, consolida o story)
- Cada story termina com seu **Checkpoint** e é um incremento completo e testável

### Parallel Opportunities

- T002/T003 (Setup) em paralelo
- T004–T006 (Foundational) em paralelo
- Todas as tarefas [P] dentro de cada story (revisões de arquivos diferentes) em paralelo
- As três stories inteiras (Phases 3–5) em paralelo, se houver capacidade — não compartilham arquivos
- T022–T024 (Polish) em paralelo, antes de T025 consolidar

---

## Parallel Example: User Story 2

```bash
# Lançar em paralelo as três revisões independentes:
Task: "Revisar data-model.md §5 contra app/models/inventario.py e app/models/enums.py"     # T011
Task: "Revisar rotas de inventário do web-contract.md contra app/web/routes.py"            # T012
Task: "Revisar ata de inventário do api-contract.md contra app/api/reports_api.py"         # T013

# Depois, sequencialmente, fechar o story:
Task: "Verificar regras 8–13 da spec e executar pytest tests/test_inventario.py"           # T014
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup (contexto e repositório limpo)
2. Completar Phase 2: Foundational (baseline consistente — CRITICAL)
3. Completar Phase 3: US1 (custódia — o coração do sistema)
4. **STOP and VALIDATE**: revisões sem divergência + `pytest tests/test_movements.py tests/test_assets.py tests/test_api.py` verde
5. A baseline de custódia já está utilizável como referência

### Incremental Delivery

1. Setup + Foundational → baseline consistente
2. US1 → validada → referência de custódia publicável
3. US2 → validada → referência comprobatória (inventário) somada
4. US3 → validada → referência de segurança/auditoria completa
5. Phase 6 → protocolo quickstart completo → baseline integral publicada (SC-E)

### Validation Strategy (substitui "Parallel Team Strategy")

- Como não há implementação, a "estratégia de equipe" traduz-se em divisão de revisão: um revisor por story (artifacts vs. código), com as execuções de pytest consolidadas por quem roda a Phase 6
- Nenhuma edição de código, teste, template, banco ou configuração em qualquer fase (plan §16)

---

## Notes

- [P] = arquivos diferentes, sem dependências
- [Story] mapeia a tarefa à user story da spec para rastreabilidade
- **Nenhum teste novo é escrito**; a suíte existente é executada, nunca editada (plan §10, quickstart §1)
- A falha esperada `test_rbac.py::test_lockout_after_failed_attempts` é **conhecida e documentada** (plan §13); sua "correção" é tarefa própria futura (spec §11.4) e não pode ser feita aqui (Constitution I — escopo)
- Divergências encontradas nas revisões são **registradas** (T025), nunca corrigidas nesta feature
- Evitar: tarefas vagas, revisões sem caminho de arquivo, alterar arquivos fora de `specs/001-sistema-existente/`
