# Research & Decisions — Feature 050

**Data**: 2026-09-28 · Método: leitura do código real + execução do parser + suíte

## R1 — Mecanismo de aliases (decidir onde adicionar)

**Decisão**: estender `COLUMN_ALIASES` em `location_import_service.py` (L34–80).
**Evidência**: `_normalize_column_name('Unidade Administrativa')` → `unidade_administrativa` (sem alias → falha na validação, provado por execução nesta sessão). A chave normalizada é minúscula, espaços→`_`, acentos removidos — portanto basta a chave `unidade_administrativa` (e `nome_da_localizacao` → `name`).
**Contra-caso**: mapear no import_intelligence (`analyze_columns`) seria duplicar regra — os aliases vivem nos services e a camada inteligente os consome (`_KIND_ALIASES`); violaria III/A1 da 048.

## R2 — Mensagens de validação na origem (service)

**Decisão**: trocar os textos em `_validate_row` (L114–123): "nome é obrigatório" → "Localização é obrigatória"; "filial é obrigatória" → "Unidade Administrativa é obrigatória".
**Evidência**: `_classify_location_row` (import_intelligence L472) reaproveita as mensagens via `e.split(": ", 1)[-1]` — corrigindo na origem, o fluxo tradicional (parse) e o inteligente (048) ficam oficiais com uma única edição. Feito no template/rota exigiria duplicação.

## R3 — Rótulos da camada inteligente (`FIELD_LABELS["locations"]`)

**Decisão**: `"name": "Localização"`, `"branch": "Unidade Administrativa"` (import_intelligence L86–95); `department: "Departamento"` permanece.
**Evidência**: consumido por `routes.py` (L631/1580/1638) e renderizado em `imports/_mapping_step.html` (L59/63/69 usa `field_labels.get(...)`) — nenhum template editado; a mudança de rótulo propaga automaticamente para o passo de mapeamento das 3 entidades sem tocar as outras (a alteração é só na entrada `locations`).

## R4 — Export de locais oficial (decisão clarify Q1)

**Decisão**: cabeçalho de `generate_locations_csv` (report_service L459–467) → `Localização;Unidade Administrativa;Departamento;Prédio;Andar;Sala;Gestor`.
**Evidência**: hoje exporta `nome;filial;departamento;predio;andar;sala;gestor` (L460); `test_locations_export.py` L33 fixa o header legado (`LOCATION_CSV_HEADER`). Round-trip fechado por R1 (cabeçalho oficial reconhecido pelo importador — FR-027). Colunas/valores/ordem intocados.

## R5 — Prévia tradicional (template)

**Decisão**: em `templates/locations/import.html`: L183 `<th>Filial</th>` → `<th>Unidade Administrativa</th>`; L182 `Nome / Identificação` → `Localização` (e conferir L300–309 da ajuda, já oficial).
**Evidência**: a prévia inteligente (`imports/_smart_preview.html` L110–114) usa colunas genéricas (Linha/Identificador/Situação/Problema) — não exibe rótulos de campo; sem edição.

## R6 — Testes defasados pelo commit `62728fa` (falhas pré-existentes)

**Decisão**: atualizar assertions para os textos oficiais da listagem (que o commit aplicou):
- `test_locations_export.py` L157 (`"Nome / Identificação" in after.text`)
- `test_locations_export.py::test_screen_without_export_permission_search_and_table_intact` (mesmo header)
- `test_locations_search.py::test_base_route_renders_current_table_structure` (header `Nome / Identificação`/`Filial`)
**Evidência**: a listagem atual usa `<th>Localização</th>`/`<th>Unidade Administrativa</th>` (list.html L54–56) desde `62728fa`; os 3 testes falham na suíte atual (medido: 842 passed / 5 failed).

## R7 — Baseline da suíte e os 2 failures fora de escopo

**Medição (plan, 2026-09-28)**: 847 coletados; **842 passed / 5 failed** (116s).
- 3 failures = R6 (domínio de locais — corrigidos pela 050).
- 2 failures = `test_backup_externo.py::test_destino_sem_permissao` e `::test_zero_segredos_em_logs` (feature 045, falha estável pré-existente em ambiente Windows; **fora do escopo** — FR-021 proíbe tocar backup). Registrados como baseline externo em validacao.md; SC-005 interpreta "suíte verde" como: todos os testes verdes no baseline permanecem verdes + os 3 do domínio de locais passam a passar.

## R8 — Estratégia de teste do contrato (FR-022)

**Decisão**: novo `tests/test_location_nomenclatura_050.py` com os 12 cenários; ponta a ponta via TestClient autenticado (padrão `_login` da suíte — `POST /api/v1/auth/login`), parser direto para casos unitários de normalização. CSVs inline (padrão da 048 — `CSV_LOCALS_DESCRICAO` etc.). Compatibilidade legada: reutilizar `nome;filial;departamento` (já usado em L435/L644 de test_importacao_inteligente.py) como caso de regressão.
**Contra-caso**: estender `test_importacao_inteligente.py` misturaria escopos; arquivo próprio mantém o rastreio 050 (padrão da família de features).

## R9 — Documentação

**Decisão**: `docs/ARQUITETURA_E_MANUTENCAO.md` L715 (header do export legado) atualizado para o oficial; varredura dos trechos de locais (L680–716) para terminologia; ajuda da tela (`locations/import.html` L286–357) já oficial — não tocar (FR-014).

## R10 — Verificação anti-colisão pós-R1 (obrigatória no implement)

Após adicionar aliases, executar `_normalize_column_name` sobre todos os termos oficial+legados e confirmar que a reversão alias→campo mantém `descricao` como única ambígua conhecida (cenário 6 do FR-022). Evidência atual: `localização` → name já existe; os novos não colidem (unidade_administrativa/nome_da_localizacao não pertencem a nenhum outro campo).
