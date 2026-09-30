# Registro de Validação — Feature 049 (Pesquisa no Fluxo Global de Movimentações)

**Data**: 2026-09-30 · **Feature**: campo de pesquisa textual em `/movements` (busca backend, cumulativa, read-only)
**Implementação**: commit **`65c0882`** (2026-09-27, dev) — código, testes e artefatos spec-kit no mesmo commit.
**Natureza deste registro**: regularização documental (Constituição XII) — a feature estava implementada e em produção, sem a validação formal da família. Todas as provas abaixo foram **re-executadas hoje** contra o código atual.

## Alteração implementada (commit 65c0882)

| Arquivo | Mudança |
|---|---|
| `app/schemas/movement.py` | `MovementFilter.search: Optional[str]` (F4 da spec) |
| `app/services/movement_service.py` | Busca aplicada na query do backend (L513+): tombamento, nome do equipamento, snapshots de local origem/destino, custodiantes origem/destino (nome e matrícula), rótulo/valor do tipo de movimentação — tudo `ilike` (case-insensitive, parcial), cumulativo com os demais filtros |
| `app/web/routers/movements.py` | Rota `GET /movements` recebe `search`, normaliza (trim; vazio → filtro desativado), mantém guarda `movimentacao.visualizar` e devolve o termo ao template |
| `app/web/templates/movements/list.html` | Campo no card de filtros existente: `input-group` com `bi-search`, `name="search"` via GET, repopulação do valor, link de limpeza e estado vazio dedicado |
| `tests/test_movements_search.py` (novo) | 14 testes cobrindo os FRs/SCs |

## Validação (V1–V6) — provas re-executadas em 2026-09-30

| # | Critério | Prova | Resultado |
|---|---|---|---|
| V1 | **FR-001/002/011** — campo presente, via GET, padrão visual | `movements/list.html:59-61` (`input-group` + `bi-search`, `name="search"`, form GET existente); repopulação `value="{{ search }}"` | ✅ |
| V2 | **FR-003/004/005** — cobertura dos dados, parcial e case-insensitive | 14/14 testes passed, incluindo `test_search_by_tag`, `test_search_by_equipment_name_partial_and_case_insensitive`, `test_search_by_custodian_name_and_matricula`, `test_search_by_location`, `test_search_by_operator_and_term_code`, `test_search_by_movement_type_label_or_enum` | ✅ |
| V3 | **FR-006/007/008** — cumulativo, vazio desativa, limpeza | `test_search_combined_with_movement_type`, `test_search_empty_or_whitespace_returns_all`, `test_search_web_clear_link_and_repopulation` passed | ✅ |
| V4 | **FR-009/010** — backend + estado vazio claro | busca na query SQL com `limit=200` (`test_search_respects_backend_limit`); mensagem "Nenhuma movimentação encontrada para a pesquisa informada" no template (L161) provada por `test_search_no_results_empty_state_feedback` | ✅ |
| V5 | **FR-012/013** — RBAC e read-only estrito | guarda `require_permission("movimentacao.visualizar")` na rota (L38); `test_search_requires_permission_rbac` e `test_search_is_strictly_read_only` passed | ✅ |
| V6 | **SC-005** — zero regressão | suíte completa re-executada hoje: **912 passed / 1 skipped (condicional MariaDB da 052, por design) / 0 failed** (64,2s) — inclui os 14 testes da 049 | ✅ |

## Observações

- **SC-001/SC-003** (UX < 5s; resposta < 500ms em 10k registros): busca é filtro na query com `ilike` indexável e limite 200 — perfil compatível; medição formal em base de 10k fica como smoke operacional (sem evidência de lentidão em uso real desde a entrega).
- **Produção**: a feature já está no snapshot do PRO (`b01f563`) — nada a deployar; este registro é documentação da dev.
- **Causa da lacuna**: o ciclo spec-kit da 049 (2026-09-27) antecedeu a formalização rígida do registro de validação por feature na prática da família; demais artefatos (plan/tasks/research/contracts/data-model/quickstart) foram entregues no mesmo commit e tasks.md já está 16/16 `[x]`.
