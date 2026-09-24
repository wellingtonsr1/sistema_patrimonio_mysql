---

description: "Task list for feature implementation"
---

# Tasks: Inventário — Remover colaborador responsável do snapshot (034)

**Input**: Design documents from `/specs/034-inventario-snapshot-sem-custodia/`

**Prerequisites**: plan.md (required), spec.md (required), research.md (D1–D5), data-model.md, contracts/inventario-ata-contract.md, quickstart.md

**Tests**: incluídos — Constitution VIII (TDD) e SC-005 exigem novos testes + suíte verde.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: `app/` em camadas (services → templates) + `tests/` na raiz.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmação de insumos — nenhuma infraestrutura nova (alteração cirúrgica, plan.md).

- [x] T001 Ler/confirmar os pontos exatos de alteração sem alterar nada: `app/services/inventario_service.py` (criação de itens ~L115-128), `app/services/report_service.py` (`_inventario_rows` ~L546 e headers das 3 atas ~L586/L673/L794), `app/services/inventario_offline_service.py` (~L130-140), `app/web/templates/inventarios/detail.html` (~L243 e ~L389), `app/web/templates/inventarios/conferir.html` (~L54), `tests/test_inventario.py` (asserts de `expected_custodian_name`)
- [x] T002 Confirmar `.specify/feature.json` apontando para `specs/034-inventario-snapshot-sem-custodia` (já gravado no specify — apenas verificar)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhuma fundação nova é necessária — sem migração (H-1), sem model novo, sem rota nova, sem permissão nova.

> Esta fase fica intencionalmente vazia: o plan.md (gate PASS) não exige infraestrutura.
> User stories podem iniciar imediatamente após o Setup.

---

## Phase 3: User Story 1 - Snapshot de novos inventários sem colaborador responsável (Priority: P1) 🎯 MVP

**Goal**: A geração de inventários novos não grava `expected_custodian_name` (fica `NULL`); criação funciona para bens com e sem custodiante; snapshot permanece imutável (D1).

**Independent Test**: criar inventário com bens com/sem custodiante e inspecionar os itens: tombamento + local esperado presentes, colaborador ausente; alterar o cadastro depois não muda o snapshot.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] [US1] Escrever testes primeiro em `tests/test_inventario.py`: (1) novo inventário gera itens com `expected_custodian_name is None` mesmo para bens COM custodiante; (2) bem sem custodiante entra normalmente no snapshot (com `expected_location_name` preenchido); (3) imutabilidade: alterar `asset.custodian_id`/local do bem após a criação não altera o item; (4) inventário não altera cadastro (local e custodiante do bem intactos após conferência — reafirmar teste existente). Rodar e confirmar FALHA do (1)

### Implementation for User Story 1

- [x] T004 [US1] Remover a atribuição `expected_custodian_name=asset.custodian.name if asset.custodian else None` na criação de itens em `app/services/inventario_service.py` (~L127, caminho `create_inventario`/adição de itens — D1); coluna permanece no model (H-1 — nenhuma mudança em `app/models/inventario.py`); verificar que não existe outro ponto de gravação do campo
- [x] T005 [US1] Ajustar em `tests/test_inventario.py` os asserts existentes que esperam `expected_custodian_name` preenchido na criação (comportamento alterado pela spec — exceção prevista no Princípio VIII): `test_create_inventario_generates_expected_items_with_snapshot` e quaisquer outros apontados por `grep expected_custodian tests/`; rodar `pytest tests/test_inventario.py -q` e deixar verde

**Checkpoint**: US1 funcional — novos inventários geram snapshot sem colaborador; suíte do inventário verde.

---

## Phase 4: User Story 2 - Conferência e ata sem "responsável esperado" (Priority: P1)

**Goal**: Tela de conferência e cards do inventário sem o dado; ata dos 3 formatos segue o critério D2 (coluna só quando houver histórico); conformidade continua por presença/local (D3/H-2).

**Independent Test**: conferir item de inventário novo (sem rótulo "Colaborador esperado"; ENCONTRADO mesmo com custodiante alterado) e exportar as 3 atas: novo sem a coluna; legado com a coluna e histórico.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T006 [P] [US2] Escrever testes primeiro em `tests/test_inventario.py`: (1) responsável diferente não gera divergência — criar inventário, gravar item com `expected_custodian_name="Maria"` diretamente (simula legado), alterar `asset.custodian` para "João", conferir ENCONTRADO no local esperado → status ENCONTRADO (não LOCAL_DIFERENTE/NAO_ENCONTRADO); (2) divergência de local continua: local encontrado ≠ esperado → FOUND_WRONG_LOCATION; (3) ata CSV de inventário novo: texto sem "Responsável Esperado" e com "Local Esperado"; (4) ata CSV de inventário legado (item com campo gravado direto no banco): texto COM "Responsável Esperado" e valor histórico na linha; (5) ata Excel novo sem a coluna / legado com a coluna (OpenPyXL workbook); (6) ata PDF novo sem a coluna / legado com a coluna (buffer ReportLab); (7) conteúdo dos templates: `detail.html` e `conferir.html` renderizados sem "Colaborador esperado" (via client do TestClient). Rodar e confirmar FALHAS de (3)–(7)

### Implementation for User Story 2

- [x] T007 [US2] Implementar critério D2 em `app/services/report_service.py`: `_inventario_rows` continua devolvendo `responsavel_esperado`; nas 3 exportações (CSV ~L586, Excel ~L794, PDF ~L673) incluir a coluna "Responsável Esperado" **somente** se `any(item.expected_custodian_name for item in itens)`; ordem das demais colunas inalterada; valor "Estoque / Livre" mantido quando a coluna existe (contrato §1)
- [x] T008 [P] [US2] Remover em `app/web/templates/inventarios/detail.html` a linha do colaborador esperado no card do item (~L243-245) e o acréscimo no rodapé "Local cadastrado" (~L389) — D3
- [x] T009 [P] [US2] Remover em `app/web/templates/inventarios/conferir.html` o rótulo "Colaborador esperado:" (~L54-55) — D3
- [x] T010 [US2] Rodar `pytest tests/test_inventario.py -q` e deixar verde (depende de T007–T009)

**Checkpoint**: US2 funcional — conferência/ata alinhadas ao novo escopo; legados preservam histórico na ata.

---

## Phase 5: User Story 3 - Inventários históricos íntegros + pacote offline (Priority: P2)

**Goal**: Histórico preservado (H-1) e consultável; pacote offline (033) sem o campo para todo inventário (H-3/D4); documentação/contrato da 033 ajustados.

**Independent Test**: abrir/exportar inventário anterior à mudança (íntegro, ata com coluna); gerar pacote offline de inventário legado → payload sem as chaves de custodiante esperado.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T011 [P] [US3] Escrever testes primeiro: (1) em `tests/test_inventario.py`: inventário legado (item com `expected_custodian_name` gravado direto) permanece consultável via `InventarioService.summary` e ata CSV com histórico (complementa T006); (2) em `tests/test_inventario_offline.py`: pacote de inventário com item legado (valor gravado direto) NÃO contém as chaves `expected_custodian_id`/`expected_custodian_name` no payload; ajustar o teste da 033 que asserta o campo na lista de campos do FR-003 (`test_pacote_com_campos_minimos_apenas`). Rodar e confirmar FALHA do pacote

### Implementation for User Story 3

- [x] T012 [US3] Remover as chaves `expected_custodian_id`/`expected_custodian_name` do payload em `app/services/inventario_offline_service.py` (~L130-140, D4/H-3); verificar que o client `app/web/static/js/inventario_offline.js` não referencia o campo (verificado no research)
- [x] T013 [US3] Atualizar os artefatos da 033 no mesmo escopo: `specs/033-inventario-offline-pwa/data-model.md` (remover `expected_custodian_id`/`expected_custodian_name` do exemplo do pacote e nota do fato do repositório) e `specs/033-inventario-offline-pwa/contracts/inventario-offline-contract.md` (remover as chaves do exemplo §2); rodar `pytest tests/test_inventario_offline.py -q` e deixar verde

**Checkpoint**: US3 funcional — histórico íntegro; pacote offline coerente com o novo snapshot.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentação fiel e validação final (Constitution XI/XII).

- [x] T014 [P] Atualizar `README.md` (seção 3 Inventário Patrimonial): snapshot = tombamento + local esperado (sem colaborador); nota de que responsabilidade é tratada pelos fluxos próprios (movimentação/alocação); nenhum outro trecho alterado
- [x] T015 Verificar não-regressão global: `.venv/bin/python -m pytest tests/ -q` 100% verde (SC-005); nenhum módulo não relacionado alterado (Princípio I — conferir `git status`)
- [x] T016 Rodar o quickstart.md completo (V1–V4) e registrar o resultado da validação em `specs/034-inventario-snapshot-sem-custodia/` (Constitution XII)
- [x] T017 Revisão final de documentação fiel: README compatível com o comportamento implementado (Princípio XI)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — inicia imediatamente
- **Foundational (Phase 2)**: vazia por design — user stories iniciam após Setup
- **User Stories (Phases 3–5)**: US1 → US2 → US3 (a critério D2 da ata assume que novos inventários não gravam o campo; legados são simulados por gravação direta nos testes, então as fases são tecnicamente independentes mas executam na ordem de prioridade)
- **Polish (Phase 6)**: depende de todas as stories completas

### User Story Dependencies

- **US1 (P1)**: após Setup — sem dependência de outras stories
- **US2 (P1)**: usa US1 (inventários novos sem campo) para o cenário "ata novo sem coluna"; legado simulado independe
- **US3 (P2)**: complementa US2 (ata legado) e ajusta a 033; depende de US1 para o assert "pacote sem campo"

### Within Each User Story

- Tests before implementation (TDD — Constitution VIII)
- Service antes de template (US2)
- Story completa antes da próxima prioridade

### Parallel Opportunities

- T003 (US1 tests) e T006 (US2 tests) podem ser escritos em paralelo (mesmo arquivo — consolidar num único commit de testes se houver conflito)
- T008 e T009 são [P] (arquivos distintos)
- T011 (US3 tests) em paralelo com T008/T009
- T014 [P] no Polish

---

## Parallel Example: User Story 2

```bash
# Launch all US2 tasks that are marked [P] together:
Task: "Remover linha do card em app/web/templates/inventarios/detail.html" (T008)
Task: "Remover rótulo em app/web/templates/inventarios/conferir.html" (T009)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: US1
3. **STOP and VALIDATE**: criar inventário e inspecionar o snapshot (Independent Test)
4. Deploy/demo se pronto

### Incremental Delivery

1. Setup → fundação (nenhuma nova) → US1 (snapshot) → validar
2. US2 (conferência + ata D2) → validar com inventário novo e legado
3. US3 (histórico + offline H-3) → validar pacote
4. Polish: README, suíte completa, quickstart

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing (TDD — Constitution VIII)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Decisões vinculantes: H-1 (nenhuma migração), H-2 (ata legado preserva histórico — critério D2), H-3 (pacote sem o campo para todo inventário); detalhes em research.md D1–D5
- Nenhuma regra de movimentação/alocação/cadastro é alterada (FR-012/Princípio I); nenhuma permissão nova; nenhum arquivo novo de produção
