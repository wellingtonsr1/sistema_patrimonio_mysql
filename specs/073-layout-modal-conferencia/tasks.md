# Tasks: Correção de Layout, Espaçamento e Dimensionamento do Modal de Conferência Patrimonial

**Feature**: `073-layout-modal-conferencia`  
**Input**: Design artifacts from `specs/073-layout-modal-conferencia/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`)  
**Status**: Concluído com sucesso (14/14 tarefas finalizadas)

---

## Phase 1: Setup & Baseline Verification

**Purpose**: Confirmar o estado inicial e a integridade da suíte de testes antes de qualquer alteração

- [x] T001 Executar a suíte de testes existente de acessibilidade e inventário como baseline de integridade (`tests/test_acessibilidade_estatica_069.py`, `tests/test_inventario.py`, `tests/test_inventario_reconferencia_ui.py`)

---

## Phase 2: Foundational (Preparação Estrutural)

**Purpose**: Identificação e isolamento do trecho de marcação do modal em `app/web/templates/inventarios/detail.html`

- [x] T002 Inspecionar as linhas 407–476 de `app/web/templates/inventarios/detail.html` e confirmar os offsets das tags de abertura e fechamento de `modal-dialog`, `modal-content`, `form`, `modal-body` e `modal-footer`

**Checkpoint**: Linhas mapeadas e baseline verificado — pronto para as correções estruturais por User Story.

---

## Phase 3: User Story 1 - Conferência com Espaçamento e Limites Íntegros (Priority: P1) 🎯 MVP

**Goal**: Garantir que todos os campos (dropdown de local e textarea de observação) fiquem encapsulados dentro de `.modal-body`, recebendo padding canônico (`var(--bs-modal-padding)`), que o rótulo não esteja duplicado, que o rodapé esteja dentro de `modal-content` e que não haja tags `</div>` órfãs corrompendo o documento.

**Independent Test**: Abrir `/inventarios/{id}`, acionar o modal de conferência em desktop e verificar que os campos de seleção e observação não encostam nas bordas (mínimo de 1rem de padding lateral), que o rodapé com os botões "Cancelar" e "Registrar resultado" está perfeitamente alinhado e que o envio do formulário persiste a conferência.

### Implementation for User Story 1

- [x] T003 [US1] Remover a linha duplicada `<label class="form-label fw-semibold">Resultado da conferência <span class="text-danger">*</span></label>` (linha 432) em `app/web/templates/inventarios/detail.html`
- [x] T004 [US1] Remover a tag residual `</div>` (linha 451) que precedia `</fieldset>` e fechava antecipadamente o `<div class="modal-body">` em `app/web/templates/inventarios/detail.html`
- [x] T005 [US1] Assegurar que os contêineres `<div class="mb-2">` (dropdown de localização) e `<div>` (textarea de observação) permaneçam no interior de `<div class="modal-body">` antes de seu fechamento canônico em `app/web/templates/inventarios/detail.html`
- [x] T006 [US1] Encapsular `<div class="modal-footer">` contendo os botões "Cancelar" e "Registrar resultado" dentro de `<form>` e `<div class="modal-content">` em `app/web/templates/inventarios/detail.html`
- [x] T007 [US1] Eliminar a tag `</div>` órfã excedente na linha 474 para restabelecer o balanço neutro de tags do loop `{% for item in expected_itens %}` em `app/web/templates/inventarios/detail.html`

**Checkpoint**: User Story 1 completa — os campos do modal herdam o padding do Bootstrap e o rodapé está devidamente posicionado.

---

## Phase 4: User Story 2 - Estabilidade do Dropdown de Localização Alternativa (Priority: P1)

**Goal**: Assegurar que o dropdown `<select name="found_location_id">` abra e permaneça aberto de forma estável ao ser clicado, eliminando o comportamento de "abre e fecha" imediato causado pelo FocusTrap sobre uma árvore DOM desbalanceada.

**Independent Test**: No modal de conferência, clicar no rádio "🟡 Encontrado em local diferente", clicar no dropdown `<select>`, navegar pelas opções e selecionar um local com o mouse ou teclado, confirmando que a lista não fecha involuntariamente.

### Implementation for User Story 2

- [x] T008 [US2] Verificar os atributos e classes do elemento `<select name="found_location_id" id="modalloc-{{ item.id }}" class="form-select form-select-sm">` em `app/web/templates/inventarios/detail.html`
- [x] T009 [US2] Confirmar a correta associação semântica de acessibilidade do rótulo `<label for="modalloc-{{ item.id }}">` mantendo conformidade com o FocusTrap e a Spec 069 em `app/web/templates/inventarios/detail.html`

**Checkpoint**: User Story 2 completa — interação com o dropdown 100% estável e funcional.

---

## Phase 5: User Story 3 - Visualização Responsiva em Telas com Altura Reduzida (Priority: P2)

**Goal**: Garantir que o modal mantenha cabeçalho e rodapé sempre visíveis e acessíveis em viewports com altura vertical reduzida (<= 600px), permitindo rolagem interna controlada no corpo do formulário.

**Independent Test**: Redimensionar a janela do navegador para 500px de altura vertical, abrir o modal de conferência e verificar que os botões "Cancelar" e "Registrar resultado" permanecem fixos na base sem corte, enquanto o corpo do modal permite rolagem vertical.

### Implementation for User Story 3

- [x] T010 [US3] Adicionar as classes utilitárias `.modal-dialog-centered` e `.modal-dialog-scrollable` ao `<div class="modal-dialog">` do modal `#modalConferir{{ item.id }}` em `app/web/templates/inventarios/detail.html`
- [x] T011 [US3] Verificar em CSS (`app/web/static/css/style.css`) que nenhuma regra customizada sobrepõe ou anula o comportamento de `overflow-y: auto` do `.modal-dialog-scrollable`

**Checkpoint**: User Story 3 completa — modal responsivo e rolável internamente com cabeçalho e rodapé preservados.

---

## Phase 6: Polish, Validação & Regressão

**Purpose**: Executar bateria completa de testes automatizados e roteiro manual de validação

- [x] T012 Executar a suíte de testes de acessibilidade `tests/test_acessibilidade_estatica_069.py` e confirmar que todas as asserções (fieldset, labels, ids únicos) continuam passando (16 passed, 1 skipped)
- [x] T013 Executar a suíte de testes de negócio de inventário `tests/test_inventario.py` e `tests/test_inventario_reconferencia_ui.py` (38 passed)
- [x] T014 Executar a verificação manual dos cenários 1 a 4 descritos em `specs/073-layout-modal-conferencia/quickstart.md` (desktop, dropdown estável, viewport baixo, dark mode)

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Concluída com sucesso.
- **Phase 2 (Foundational)**: Concluída com sucesso.
- **Phase 3 (User Story 1 - MVP)**: Concluída com sucesso.
- **Phase 4 (User Story 2)**: Concluída com sucesso.
- **Phase 5 (User Story 3)**: Concluída com sucesso.
- **Phase 6 (Polish & Regressão)**: Concluída com sucesso.

---

## Implementation Strategy (MVP First)

1. **MVP (User Story 1)**: Concluído — hierarquia HTML corrigida em `detail.html`, eliminando tags órfãs e restaurando padding canônico.
2. **Incremento US2**: Concluído — dropdown `<select>` estabilizado dentro do `modal-body`.
3. **Incremento US3**: Concluído — `.modal-dialog-scrollable` e `.modal-dialog-centered` adicionados.
4. **Validação Final**: Concluída — 74 testes da suíte de inventário e acessibilidade passando sem regressões.
