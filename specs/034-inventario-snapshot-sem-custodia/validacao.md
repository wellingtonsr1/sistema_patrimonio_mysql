# Validação — Feature 034 (Inventário — snapshot sem colaborador responsável)

**Data**: 2026-09-24 · **Suíte**: `.venv/bin/python -m pytest tests/ -q` → **727 passed** (baseline 715 + 12 novos testes 034) — SC-005 ✓

## Cenários do quickstart (V1–V4)

| Cenário | Como foi validado | Resultado |
|---|---|---|
| V1 — Snapshot sem colaborador (US1) | `test_new_inventory_snapshot_has_no_expected_custodian` (bem COM custodiante → item sem `expected_custodian_name`, com tombamento + local esperado); `test_asset_without_custodian_enters_snapshot_normally`; `test_snapshot_immutable_after_registration_changes` (mudança de custodiante/local depois não altera o snapshot) | ✅ PASS |
| V2 — Conferência/ata (US2) | `test_conference_ignores_custodian_difference` (legado "Maria", cadastro "João" → ENCONTRADO); `test_location_divergence_still_detected`; atas CSV/Excel/PDF: novo sem coluna (`test_ata_*_new_*`), legado com coluna e histórico (`test_ata_*_legacy_*`); templates sem "Colaborador esperado" (`test_templates_do_not_render_expected_custodian`, cobre também item legado) | ✅ PASS |
| V3 — Ata legado com histórico (H-2/D2) | `test_ata_csv_legacy_inventory_keeps_custodian_column` (coluna + "Maria Legado" + "Estoque / Livre"); Excel e PDF idem; `test_legacy_inventory_consultable_with_history` (summary íntegro + ata com histórico) | ✅ PASS |
| V4 — Legado íntegro + pacote (US3) | `test_pacote_sem_chaves_de_custodiante_mesmo_legado` + dev DB real: coluna `expected_custodian_name varchar(150) NULL` preservada com **50 registros históricos** (H-1 — nenhuma migração); `generate_package` de inventário legado real (id 1, 52 itens) → chaves do item sem `expected_custodian_id/name` (H-3) | ✅ PASS |

## TDD (Constitution VIII)

- Testes escritos primeiro e confirmados **vermelhos** antes da implementação:
  - US1: `test_new_inventory_snapshot_has_no_expected_custodian` falhou com `'Maria Custodia' is None` (gravação ainda ativa) — T003.
  - US2: 4 falhas nas atas (CSV/Excel/PDF novo com coluna) e nos templates — T006.
  - US3: `test_pacote_com_campos_minimos_apenas` e novo teste do pacote legado falharam antes de T012 — T011.
- Verde após implementação: `tests/test_inventario.py` 31 passed; `tests/test_inventario_offline.py` 34 passed; suíte completa 727 passed.

## Escopo das alterações (FR-012 / Princípio I)

`git status` na validação: apenas os arquivos previstos — `app/services/inventario_service.py`, `report_service.py`, `inventario_offline_service.py`, templates `inventarios/detail.html` e `conferir.html`, `README.md`, `tests/test_inventario.py`, `tests/test_inventario_offline.py`, artefatos das specs 033/034.

**Nota**: `app/web/templates/inventarios/offline.html` aparece modificado na árvore de trabalho — ajuste cosmético de navbar da feature 033 (resto de trabalho anterior não comitado; último commit `87024ad`), **não** faz parte da 034 e não foi alterado nesta execução.

## Observações

- **SW**: nenhum arquivo da allowlist do `sw.js` mudou (só estáticos) → sem bump do `CACHE_VERSION`.
- Coluna `inventario_itens.expected_custodian_name` mantida no model e no banco (H-1); único ponto de gravação removido (`InventarioService.generate_items`), verificado por grep (T005).
- Artefatos da 033 atualizados com nota de superação (H-3) em `spec.md` (FR-003), `data-model.md` e `contracts/inventario-offline-contract.md`.
- Nenhum módulo de movimentação/alocação/cadastro tocado; nenhuma permissão nova; nenhuma migração.
