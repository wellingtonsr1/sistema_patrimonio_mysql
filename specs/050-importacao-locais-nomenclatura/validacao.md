# Registro de Validação — Feature 050 (Constituição XII / SC-007 / T015)

**Data**: 2026-09-28 · **Feature**: Compatibilização da Importação Inteligente de Localizações com a Nova Nomenclatura (048 → 050)
**Método**: TDD (testes do contrato escritos e vistos falhar antes da implementação) + suíte completa de regressão + fluxo web real via TestClient autenticado + varredura de legados por grep (C1 do analyze).

## Alteração aplicada (diff confinado — SC-006/contract §4)

**6 arquivos alterados** (27 inserções, 19 exclusões):

| Arquivo | Mudança |
|---|---|
| `app/services/location_import_service.py` | +2 aliases oficiais (`nome_da_localizacao`→name, `unidade_administrativa`→branch); mensagens de `_validate_row` oficiais ("Localização é obrigatória", "Unidade Administrativa é obrigatória") |
| `app/services/import_intelligence.py` | `FIELD_LABELS["locations"]`: "Nome do local"→"Localização", "Filial"→"Unidade Administrativa" (somente a entrada locations) |
| `app/services/report_service.py` | `generate_locations_csv`: cabeçalho oficial (round-trip com o importador) |
| `app/web/templates/locations/import.html` | Prévia tradicional: 2 `<th>` oficiais + badge "Duplicatas (localização existente)" (B1) |
| `tests/test_locations_export.py` | 3 assertions atualizados (2 defasados do `62728fa` + `LOCATION_CSV_HEADER`) |
| `tests/test_locations_search.py` | 1 assertion defasado atualizado (headers oficiais da listagem) |

**+1 arquivo novo**: `tests/test_location_nomenclatura_050.py` — 16 testes cobrindo os 12 cenários do FR-022 + preservação da 048 + round-trip.

**Zero alteração** em: models, schemas, rotas/URLs, `execute_locations_import`, parciais `imports/_*.html`, motor de movimentações, auditoria, permissões, `FIELD_LABELS` de assets/custodians, demais telas (FR-016/020/021 — verificado por `git diff --stat` e inspeção).

## V1 — Contrato oficial ponta a ponta (SC-001/FR-004) ✅

`test_cenario1_csv_oficial_importa_ponta_a_ponta`: CSV `Localização;Unidade Administrativa;Departamento` → passo de mapeamento com sugestão `auto` correta (prova: `analyze_columns` devolve `Unidade Administrativa → branch, confidence auto`) → confirmação → local gravado com name/branch/department corretos. **Antes da feature este fluxo falhava** ("filial é obrigatória" — provado por execução no specify).

## V2 — Compatibilidade legada (SC-002/FR-006/007/008) ✅

- `test_cenario3_*`: `Nome;Filial;Departamento` importa; variações `unidade`/`empresa`/`sede`/`setor`/`área`/`divisão` reconhecidas — nenhum alias legado removido.
- `test_cenario4`: `Matriz/Filial` permanece "não utilizada" (nenhuma invenção — FR-008).
- `test_cenario6`: valores originais preservados (normalização só para comparação — FR-019 da 048).

## V3 — Mensagens oficiais (FR-012) ✅

`test_cenario5`: CSV sem Unidade Administrativa → `Linha N: Unidade Administrativa é obrigatória` (antes: "filial é obrigatória"). Corrigido na origem (`_validate_row`) — fluxo tradicional e camada 048 herdam (R2). TDD: o teste foi escrito e falhou com a mensagem legada antes da correção.

## V4 — Export oficial + round-trip (FR-026/027) ✅

`test_export_locais_header_oficial_e_round_trip`: export → header `Localização;Unidade Administrativa;Departamento;Prédio;Andar;Sala;Gestor`; reimportar o arquivo exportado sem ajustes → duplicado identificado, **nada duplicado** (SC-004).

## V5 — Não-vazamento / varredura de legados (SC-003/SC-006) ✅

- `git diff --stat`: exatamente os 6 arquivos do escopo (+1 teste novo + specs). Parciais `imports/_*.html`: **sem diff**.
- **Grep de termos legados no domínio de locais** (C1 do analyze): "Nome do local", "Nome / Identificação", "Filial</th>", "filial é obrigatória" → **0 ocorrências como rótulo/mensagem** em templates/services/JS de locations e `FIELD_LABELS`. Os aliases legados em `COLUMN_ALIASES` (`"filial": "branch"` etc.) permanecem **intencionalmente** (compatibilidade FR-006 — não são rótulos); valores de dados em fixtures não contam (SC-003).
- Mapeamento de equipamentos/colaboradores intacto (`FIELD_LABELS` das outras entradas sem diff).

## V6 — Regressão (SC-005, régua comparativa F2 do analyze) ✅

| Baseline (T002, pré-implementação) | Final (T014) |
|---|---|
| 842 passed | **861 passed** = 842 mantidos + 3 do domínio corrigidos + 16 novos da 050 |
| 5 failed (3 locais defasados + 2 backup) | **2 failed** — somente `test_backup_externo.py` (feature 045, baseline externo documentado — FR-021 proíbe tocar backup) |

Os 3 failures do domínio de locais (`test_locations_export.py` ×2, `test_locations_search.py` ×1 — assertions defasados pelo `62728fa`) agora passam. Nenhum teste que passava passou a falhar.

## Cobertura de testes da 050 (16)

US1: 4 (ponta a ponta, ordem/espaços/caixa, normalização, parse) · US2: 5 (legados, variações, desconhecida, obrigatória ausente, valores preservados) · US4: 4 (duplicado, reanálise legado×oficial, rollback por linha, dados intactos) · US5: 2 (048 ponta a ponta + auditoria `IMPORT_*`, rotas/execute intocados) · US6: 1 (export + round-trip).

## Decisões registradas durante a implementação

- **D1**: o confirm da 048 exige `mapping` (JSON coluna→campo) junto do `csv_content` — os testes derivam o mapping de `analyze_columns` (fiel ao fluxo real; o servidor reclassifica server-side).
- **D2**: chave da sugestão é `column` (não `header`) no retorno de `analyze_columns`.
- **D3**: `AuditLog` vive em `app.models.audit_log` (não `app.models.audit`).
- **D4**: upload multipart no padrão da suíte (`files=` com `io.BytesIO`).

## Resultado

**V1–V6: PASS** — 28/28 FRs e 7/7 SCs satisfeitos (SC-005 pela régua comparativa acordada no analyze/F1).
