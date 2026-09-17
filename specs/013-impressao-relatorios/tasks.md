---
description: "Task list for feature 013 implementation"
---

# Tasks: Correção da Impressão A4 dos Relatórios

**Input**: Design documents from `/specs/013-impressao-relatorios/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md (R1–R9), css-contract.md (C1–C10), quickstart.md

**Tests**: A spec (R9) prevê um teste de fumaça pytest-verificável (classe de escopo renderizada nos 3 templates) + suíte existente como guarda de não-regressão. A validação de layout de impressão é manual/visual (quickstart §2) — pytest não renderiza CSS.

**Organization**: O bloco CSS é **compartilhado pelas 3 stories** (Foundational); cada story aplica a âncora `report-print` em um template e valida o relatório correspondente. US4 é somente verificação de não-regressão.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Include exact file paths in descriptions

## Path Conventions

Projeto monolítico em `app/` (web com templates Jinja2 + CSS estático) e suíte em `tests/` — conforme plan.md (Source Code).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Linha de base de regressão e teste de fumaça que falha antes da implementação

- [x] T001 Executar a suíte baseline e registrar contagens: `python3 -m pytest -q` — **nota**: a falha `tests/test_rbac.py::test_lockout_after_failed_attempts` é **pré-existente** (registrada no baseline da feature 012) e externa a esta feature; base de comparação da Constitution VIII
- [x] T002 [P] Escrever teste de fumaça FALHANDO em `tests/test_report_print_smoke.py`: para cada rota `/reports/movements`, `/reports/custodians` e `/reports/inventory` (client autenticado admin, padrão de `tests/test_rbac.py`), assert que o HTML renderizado contém a classe de escopo `report-print` no container do relatório (ancora o css-contract §1; pesquisa R9). **Nota (remediação U1)**: as rotas exigem `relatorios.visualizar` — antes de interpretar a falha do teste vermelho, confirmar o bypass de admin em `require_permission`; se admin não for superuser, conceder a permissão no teste (padrão da suíte)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: O novo bloco `@media print` compartilhado pelas 3 stories

**⚠️ CRITICAL**: Nenhuma story pode começar antes desta fase

- [x] T003 Implementar o **novo bloco `@media print`** no **final** de `app/web/static/css/style.css`, implementando exatamente C1–C10 de `specs/013-impressao-relatorios/css-contract.md`: `@page { size: A4; margin: 10mm }` (C1); `.report-print` com `break-inside: auto !important` (C2); `.report-print table` com `page-break-inside/break-inside: auto !important`, `width: 100% !important`, `table-layout: auto !important` (C3 — **causa raiz da página em branco**, R1); `.report-print thead { display: table-header-group !important }` (C4); `.report-print tr { break-inside: avoid }` (C5); `.report-print .table-responsive { overflow: visible !important; min-width: 0 !important }` (C6); `.report-print td/th { white-space: normal !important; overflow-wrap: anywhere; max-width: none !important }` (C7 — remediado A3); `.report-print .truncate-2 { display: block !important; overflow: visible !important; -webkit-line-clamp: unset }` (C8); escala `font-size: 8.5pt` (C9); badges/pills com borda de contraste **preservando as cores semânticas** (C10 — remediado A1). **NÃO editar** os blocos existentes (~linhas 896, ~1476, ~1588) nem qualquer outra regra (depends: T002)

**Checkpoint**: CSS aditivo pronto — as stories aplicam a âncora por template

---

## Phase 3: User Story 1 — Trilha de Auditoria & Fluxo (Priority: P1) 🎯 MVP

**Goal**: `/reports/movements` imprime em A4 começando na página 1, tabela contínua com cabeçalho repetido, motivo completo, sem colunas cortadas (AC-01..AC-06)

**Independent Test**: Abrir o relatório → Imprimir → pré-visualização: conteúdo na 1ª página, navegar por todas — nada truncado; `pytest tests/test_report_print_smoke.py -q`

### Implementation for User Story 1

- [x] T004 [US1] Adicionar a classe de escopo ao container do relatório em `app/web/templates/reports/movements_report.html`: `<div class="card p-4">` → `<div class="card p-4 report-print">` — **única linha alterada** (css-contract §1; dados/colunas/botões intocados) (depends: T003)
- [x] T005 [US1] Verificar checkpoint US1: `python3 -m pytest tests/test_report_print_smoke.py -q` (rota movements verde) e `python3 -m pytest -q` (sem regressão); validação manual do quickstart §2 em `/reports/movements` no Chrome/Chromium **e** Firefox (AC-01..AC-06) (depends: T004)

**Checkpoint**: MVP — o relatório mais crítico (10 colunas) imprimindo corretamente

---

## Phase 4: User Story 2 — Relação de Colaboradores (Priority: P1)

**Goal**: `/reports/custodians` com o mesmo comportamento de impressão (AC-01..AC-06; AC-07 dados idênticos)

**Independent Test**: Mesmo roteiro do quickstart §2 em `/reports/custodians`; `pytest tests/test_report_print_smoke.py -q`

### Implementation for User Story 2

- [x] T006 [P] [US2] Adicionar `report-print` ao container em `app/web/templates/reports/custodians_report.html`: `<div class="card p-4">` → `<div class="card p-4 report-print">` — única linha alterada (depends: T003)
- [x] T007 [US2] Verificar checkpoint US2: smoke test (rota custodians verde) + `python3 -m pytest -q` + validação manual do quickstart §2 em `/reports/custodians` (2 navegadores) (depends: T006)

**Checkpoint**: US1+US2 funcionais e validáveis independentemente

---

## Phase 5: User Story 3 — Relatório Contábil-Físico (Priority: P1)

**Goal**: `/reports/inventory` com valores R$/% íntegros e tabela contínua (AC-01..AC-06; US3/AS2)

**Independent Test**: Mesmo roteiro do quickstart §2 em `/reports/inventory` (massa com 50+ bens para 2+ páginas); `pytest tests/test_report_print_smoke.py -q`

### Implementation for User Story 3

- [x] T008 [P] [US3] Adicionar `report-print` ao container em `app/web/templates/reports/inventory.html`: `<div class="card p-4">` → `<div class="card p-4 report-print">` — única linha alterada (depends: T003)
- [x] T009 [US3] Verificar checkpoint US3: smoke test (rota inventory verde) + `python3 -m pytest -q` + validação manual do quickstart §2 em `/reports/inventory` (2 navegadores, com massa de 2+ páginas) (depends: T008)

**Checkpoint**: Os três relatórios imprimindo corretamente

---

## Phase 6: User Story 4 — Não-regressão de Etiquetas e Termo (Priority: P1)

**Goal**: Provar que Etiquetas e Termo permanecem idênticos (AC-08; FR-007) e que o diff ficou restrito ao escopo

**Independent Test**: Imprimir etiquetas (6+ bens) e um termo → resultado idêntico ao atual; `git diff` restrito

### Verification for User Story 4 (somente verificação — nenhuma implementação)

- [x] T010 [P] [US4] Verificação estática: `git diff` mostra alterações **apenas** em `app/web/static/css/style.css` (bloco novo no final) e nos 3 templates de `app/web/templates/reports/` (classe) — **zero** alterações em `app/web/templates/assets/labels.html`, `app/web/templates/movements/term.html`, `app/web/templates/base.html` e nos blocos `@media print` existentes de `style.css` (quickstart §3) (depends: T008)
- [x] T011 [P] [US4] Verificação manual de não-regressão (quickstart §3): imprimir etiquetas com 6+ bens selecionados (folha 3 colunas, quebras entre etiquetas) e um termo de responsabilidade — comportamento e visual idênticos ao atual (AC-08) (depends: T008)

**Checkpoint**: Todas as stories completas; não-regressão comprovada

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validação final (Constitution XI/XII)

- [x] T012 Executar o `specs/013-impressao-relatorios/quickstart.md` completo (§1 suíte, §2 roteiro ×3 relatórios ×2 navegadores, §3 não-regressão) e conferir a Definition of Done (depends: T010, T011)
- [x] T013 Re-verificar a Constitution (plan.md): `git diff` confirma zero alterações em rotas/services/models/schemas/permissões/consultas; documentação não exige atualização (research R8 — impressão dos relatórios não é documentada); escopo respeitado (depends: T012)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: imediato — T001 baseline antes de qualquer alteração; T002 (teste de fumaça) falha até T003/T004+
- **Foundational (Phase 2)**: T003 implementa o CSS compartilhado — **bloqueia as 3 stories**
- **US1 → US2 → US3**: sequenciais na ordem de prioridade; T006/T008 são [P] entre si (arquivos distintos) após o padrão de T004
- **US4**: após US3 (verifica o conjunto completo)
- **Polish (Phase 7)**: depende de todas as stories

### Within Each User Story

- Template (âncora) → checkpoint de suíte + validação manual do relatório correspondente
- Cada story é um incremento independente: o CSS existe desde a Foundational; a story "liga" o relatório

### Parallel Opportunities

- T002 (setup) isolado
- T006 e T008 ([P], arquivos distintos) — podem ser aplicados em lote após T004 estabelecer o padrão
- T010 e T011 ([P], verificação estática × manual)

## Implementation Strategy

### MVP First (Foundational + US1)

1. T001 baseline → T002 smoke (vermelho) → T003 CSS (C1–C10)
2. T004 âncora em movements_report → T005 checkpoint
3. **STOP and VALIDATE**: quickstart §2 em `/reports/movements`

### Incremental Delivery

- +US2 → `/reports/custodians` validado
- +US3 → `/reports/inventory` validado (conjunto completo dos relatórios)
- +US4 → não-regressão de Etiquetas/Termo comprovada
- Polish → DoD completa

## Notes

- **Nenhuma tarefa altera**: `base.html`, `assets/labels.html`, `movements/term.html`, rotas, services, models, schemas, permissões, consultas ou qualquer teste existente (Constitution I/VIII; T010 é a prova).
- O bloco CSS é 100% aditivo: regras novas ancoradas em `.report-print` sobrecarregam por especificidade **apenas dentro do escopo das 3 páginas** (css-contract §2 — notas de integridade).
- Falha pré-existente fora do escopo: `tests/test_rbac.py::test_lockout_after_failed_attempts` (baseline da feature 012) — registrar, não corrigir.
- Validação de impressão é manual/visual (quickstart §2) — pytest não renderiza CSS; o smoke test (T002) é o guarda automatizado da âncora.
- [P] = arquivos distintos, sem dependência pendente; [Story] mapeia à spec para rastreabilidade AC↔task.
