# Implementation Plan: Compatibilização da Importação Inteligente de Localizações com a Nova Nomenclatura (050)

**Branch**: `050-importacao-locais-nomenclatura` · **Spec**: [spec.md](spec.md) · **Created**: 2026-09-28

## Summary

A importação inteligente de locais (048) não reconhece o CSV oficial novo (`Localização;Unidade Administrativa;Departamento` — falha hoje com "filial é obrigatória", provado por execução). Este plan define a **extensão mínima**: aliases oficiais no parser, rótulos oficiais na camada inteligente e prévia, mensagem de validação oficial, cabeçalhos oficiais no export de locais (decisão clarify Q1) e correção dos testes defasados pelos textos já alterados em `62728fa` — preservando 100% da inteligência da 048, a API intocada (Q2) e a varredura confinada ao domínio de locais (Q3).

## Technical Context

**Language/Version**: Python 3.12 / FastAPI + SQLAlchemy 2 / Jinja2 / pytest
**Storage**: MariaDB (prod) / SQLite em memória (testes) — **nenhuma migração** (FR-016/017)
**Testing**: pytest com `DATABASE_URL_TEST="sqlite:///:memory:"`
**Target**: domínio de locais apenas — importação/exportação/rótulos

## Constitution Check (Pré-Design)

| Princípio | Status | Nota |
|---|---|---|
| I. Preservação e evolução incremental | PASS | Extensão de aliases/rótulos; nada recriado |
| II. Arquitetura em camadas | PASS | Mudanças em service (parser/labels) + template; rotas intocadas |
| III. Regras de negócio nos services | PASS | Validação continua no service; só o texto muda |
| IV. Integridade patrimonial | PASS | Movimentações/inventário intocados |
| V. Integridade do inventário | PASS | Fora do domínio |
| VI. Segurança RBAC | PASS | Permissões `locais.criar` preservadas |
| VII. Banco protegido | PASS | 0 migração; 0 schema change |
| VIII. Testes como não-regressão | PASS | +contrato oficial (FR-022); legados verdes |
| IX. Auditoria | PASS | `write_audit` intocado |
| X. Interface consistente | PASS | Rótulos oficiais reusando componentes existentes |
| XI. Documentação fiel | PASS | Docs de locais atualizadas na mesma task |
| XII. Especificações e validação | PASS | validacao.md no formato da família |

**GATE: PASS 12/12**

## Project Structure

```
app/services/location_import_service.py   # COLUMN_ALIASES + _validate_row (mensagens)
app/services/import_intelligence.py       # FIELD_LABELS["locations"] (rótulos)
app/services/report_service.py            # generate_locations_csv (cabeçalho)
app/web/templates/locations/import.html   # <th> da prévia tradicional + consistência
tests/test_importacao_inteligente.py      # contrato oficial + compatibilidade legada
tests/test_locations_export.py            # header do export + assertions defasados
tests/test_locations_search.py            # assertion defasado (header)
tests/test_location_nomenclatura_050.py   # NOVO: 12 cenários do contrato (FR-022)
docs/ARQUITETURA_E_MANUTENCAO.md          # trecho de locais (L715)
```

## Decisões técnicas (research)

- **R1 — Aliases via extensão de `COLUMN_ALIASES`** (mesmo mecanismo, zero código novo): adicionar `unidade_administrativa` e `unidade administrativa` (normalizador gera a chave `unidade_administrativa`; caixa/espaços já tratados por `_normalize_column_name`) → `branch`; `nome_da_localizacao` → `name`. Sem remover aliases legados (FR-006). Verificação pós-edição: reversão alias→campo não pode criar colisão nova (a única conhecida é `descricao`, que permanece).
- **R2 — Mensagens de validação**: `_validate_row` troca "nome é obrigatório" → "Localização é obrigatória" e "filial é obrigatória" → "Unidade Administrativa é obrigatória" ("departamento é obrigatório" permanece). Os erros da camada inteligente derivam dessas mensagens (`_classify_location_row` faz `e.split(": ", 1)[-1]`) — corrigindo na origem, ambos os fluxos (tradicional e 048) ficam oficiais de uma vez.
- **R3 — `FIELD_LABELS["locations"]`**: `"name": "Localização"`, `"branch": "Unidade Administrativa"` (demais campos conferidos: `department: "Departamento"` ok). Consumidores (`routes.py` L631/1580/1638, `_mapping_step.html`) herdam automaticamente — **nenhum template do passo de mapeamento precisa edição**.
- **R4 — Export**: `writer.writerow` de `generate_locations_csv` → `["Localização", "Unidade Administrativa", "Departamento", "Prédio", "Andar", "Sala", "Gestor"]`. Valores/colunas/ordem inalterados. Round-trip garantido pelos aliases novos (R1): o cabeçalho exportado é reconhecido pelo importador (FR-027).
- **R5 — Prévia tradicional** (`locations/import.html` L183–184): `<th>Filial</th>` → `<th>Unidade Administrativa</th>`; `Nome / Identificação` → `Localização`. A prévia inteligente (`_smart_preview.html`) usa colunas genéricas (Linha/Identificador/Situação/Problema) — sem edição.
- **R6 — Testes defasados por `62728fa`**: `test_locations_export.py` L157 e `test_screen_without_export_permission_search_and_table_intact` + `test_locations_search.py::test_base_route_renders_current_table_structure` assertion `"Nome / Identificação"`/`"Filial"` — atualizar para os textos oficiais da listagem (`Localização`/`Unidade Administrativa`). São os 3 failures pré-existentes da suíte; a 050 os traz para verde (SC-005).
- **R7 — Baseline da suíte**: **842 passed / 5 failed** medido no plan (coletados 847). Os 5: 3 de assertions de header defasados (R6 — corrigidos pela 050) + 2 de `test_backup_externo.py` (feature 045, **fora do escopo** — falhas estáveis pré-existentes; registrar em validacao.md como baseline externo ao domínio).
- **R8 — Novo arquivo de teste** `tests/test_location_nomenclatura_050.py`: 12 cenários do FR-022 (oficial válido ponta a ponta via TestClient; ordem diferente; espaços/caixa/acentos; legado ainda aceito; desconhecida → não utilizada; obrigatória ausente com mensagem oficial; vazios; duplicado banco; reanálise sem duplicar; rollback por linha; dados preservados; round-trip export→import).
- **R9 — Docs**: `ARQUITETURA_E_MANUTENCAO.md` L715 menciona o header do export legado — atualizar para o oficial; conferir seções de locais (L687–714) para terminologia.

## Data Model (apresentação — sem banco)

Ver [data-model.md](data-model.md). Nenhuma tabela/coluna nova; mapeamento header→campo em memória apenas.

## Contrato de UI

Ver [contracts/ui-contract-importacao-locais.md](contracts/ui-contract-importacao-locais.md).

## Constitution Check (Pós-Design)

PASS 12/12 — mesmos princípios confirmados após decisões R1–R9: nenhum impacto em modelo/motor patrimonial/RBAC/auditoria; alterações confinadas a aliases, rótulos, mensagens, export de locais e testes. **GATE: PASS 12/12.**

## Risks

| Risco | Mitigação |
|---|---|
| Colisão de alias nova quebrar `analyze_columns` | R1: verificação de reversão após editar; teste do cenário 6 do FR-022 |
| Quebrar importadores de equipamentos/colaboradores | Rótulos alterados **somente** na entrada `locations`; suíte completa |
| Mensagem nova quebrar substring de testes 048 | R2: varrer `test_importacao_inteligente.py` por "filial" antes do commit; ajustar no mesmo grupo |
| Export quebrar consumidores do CSV atual | Decisão clarify Q1 do solicitante; cabeçalho é consumido pelo próprio importador (round-trip) |

## Complexity Tracking

Vazio — nenhuma violação justificada.

## Micro-remediações do /speckit-analyze (aplicadas 2026-09-28, antes do implement)

- **F1 (MEDIUM)**: SC-005 da spec atualizado do "789 passed, 100% verde" (número de specify) para a semântica do baseline medido R7 (842 mantidos + 3 do domínio corrigidos + 2 externos de backup documentados).
- **F2 (LOW)**: T014 reescrito como régua comparativa (842+N verdes, só os 2 de backup falham) — o número absoluto "845" ignorava os N testes novos do contrato.
- **C1 (LOW)**: T015 agora atribui explicitamente a varredura grep de termos legados no domínio de locais (SC-003) — antes só cobria o diff.
- **B1 (LOW)**: T009 inclui o badge `Duplicatas (nome existente)` → `(localização existente)` (FR-013) — único texto de situação legado restante na prévia tradicional.
