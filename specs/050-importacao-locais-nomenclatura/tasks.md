---
description: "Task list for Feature 050 — Compatibilização da Importação Inteligente de Localizações com a Nova Nomenclatura"
---

# Tasks: 050-importacao-locais-nomenclatura

**Input**: Design documents de `specs/050-importacao-locais-nomenclatura/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md, checklists/)

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ (R1–R10) · data-model.md ✅ · contracts/ui-contract-importacao-locais.md ✅ · quickstart.md ✅

**Tests**: Incluídos — a spec EXIGE cobertura do contrato (FR-022: 12 cenários; FR-023: suíte verde). TDD: escrever o cenário, ver falhar, implementar, ver passar.

**Organization**: Por user story (US1 contrato oficial · US2 compatibilidade · US3 interface/mensagens · US4 semântica/dados · US5 preservação 048 · US6 export). Alteração de domínio único — tasks sequenciais no mesmo conjunto de arquivos; [P] só onde não há conflito.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: user story da spec.md (US1–US6)
- Caminhos exatos em toda task

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar o estado real e o baseline antes de qualquer edição.

- [x] T001 Confirmar os elementos protegidos do contract §1 (parciais compartilhados `app/web/templates/imports/_mapping_step.html` e `_smart_preview.html` intocáveis; `execute_locations_import` e rotas `/locations/import*` inalterados; `FIELD_LABELS` de assets/custodians não tocados) — evidência grep/leitura registrada
- [x] T002 Rodar o baseline da suíte (plan R7): `DATABASE_URL_TEST="sqlite:///:memory:" .venv/Scripts/python -m pytest -q --no-header` — confirmar **842 passed / 5 failed** (3 do domínio de locais por `62728fa` defasado + 2 de `test_backup_externo.py` fora de escopo) e registrar os 5 FAILED nome a nome para comparação final

**Checkpoint**: elementos protegidos mapeados; baseline capturado — edição pode começar.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhum — feature de domínio único sem infraestrutura nova (padrão 036–038). O esqueleto de testes entra na US1 (TDD exige o cenário antes do alias).

---

## Phase 3: User Story 1 — Contrato oficial (P1) 🎯 MVP

**Goal**: O CSV oficial `Localização;Unidade Administrativa;Departamento` é reconhecido e importado ponta a ponta (hoje falha — problema 1 da spec).

**Independent Test**: `parse_locations_csv` com CSV oficial não devolve erro de "filial obrigatória"; fluxo web completo grava o local (cenário 1 do FR-022).

### Tests for User Story 1 ⚠️ (TDD — escrever primeiro, ver falhar)

- [x] T003 [US1] Criar `tests/test_location_nomenclatura_050.py` com helpers de login (padrão `POST /api/v1/auth/login` da suíte) e os CSVs inline (oficial `Localização;Unidade Administrativa;Departamento`, legado `Nome;Filial;Departamento`, misto) — cenários 1 e 2 do FR-022: oficial importa ponta a ponta (mapeamento sugerido correto + gravação + name/branch/department corretos) e ordem diferente/espaços/caixa-acento reconhecidos; **verificar que falham** (alias ausente)

### Implementation for User Story 1

- [x] T004 [US1] Adicionar aliases oficiais em `COLUMN_ALIASES` de `app/services/location_import_service.py` (R1): `"unidade_administrativa": "branch"` e `"nome_da_localizacao": "name"` — sem remover nenhum alias legado (FR-006); rodar T003 e ver passar
- [x] T005 [US1] Verificação anti-colisão R10 (obrigatória): executar `_normalize_column_name` sobre os termos oficial+legados do data-model §2.2 e conferir que a reversão alias→campo mantém `descricao` como única ambígua conhecida (nenhuma colisão nova introduzida — FR-009)

**Checkpoint**: US1 funcional — CSV oficial passa a importar; nada legado quebrado.

---

## Phase 4: User Story 2 — Compatibilidade controlada (P1)

**Goal**: Arquivos legados continuam importando; formas nunca reconhecidas permanecem "não utilizadas" (sem invenção).

**Independent Test**: CSV legado importa idêntico ao comportamento atual; `Matriz/Filial` aparece como coluna desconhecida (cenários 3–6 do FR-022).

- [x] T006 [US2] Adicionar em `tests/test_location_nomenclatura_050.py` os cenários 3–6 do FR-022: cabeçalhos legados (`nome;filial;departamento` e variações `unidade`/`sede`/`empresa`/`setor`) aceitos; cabeçalho desconhecido (`Matriz/Filial`) marcado "não utilizada" pela análise 048; coluna obrigatória ausente detectada; valores com espaços/caixa/acentos normalizados sem alterar valores gravados (FR-019 da 048) — alguns já passam (regressão de preservação, FR-006/008)

**Checkpoint**: compatibilidade comprovada por teste — zero regressão de arquivos antigos.

---

## Phase 5: User Story 3 — Nomenclatura oficial na interface e mensagens (P1)

**Goal**: Toda a superfície do fluxo de locais exibe Localização/Unidade Administrativa/Departamento.

**Independent Test**: prévia tradicional com `<th>` oficiais; mensagens de validação oficiais; mapeamento inteligente com rótulos oficiais; assertions defasados corrigidos (suíte do domínio verde).

- [x] T007 [US3] Mensagens oficiais na origem em `_validate_row` de `app/services/location_import_service.py` (R2): "Linha N: nome é obrigatório" → "Linha N: Localização é obrigatória"; "filial é obrigatória" → "Unidade Administrativa é obrigatória" (departamento permanece) — os dois fluxos (tradicional e inteligente, via `e.split(": ", 1)[-1]` em `_classify_location_row`) herdam; adicionar cenários 7–8 do FR-022 (obrigatória ausente com mensagem oficial; valores vazios)
- [x] T008 [US3] Rótulos oficiais em `FIELD_LABELS["locations"]` de `app/services/import_intelligence.py` (R3): `"name": "Localização"`, `"branch": "Unidade Administrativa"` — **somente a entrada locations**; conferir que `imports/_mapping_step.html` herda sem edição (contract §4) e que assets/custodians seguem intactos
- [x] T009 [US3] Prévia tradicional oficial em `app/web/templates/locations/import.html` (R5 + B1 do analyze): L182 `Nome / Identificação` → `Localização`; L183 `<th>Filial</th>` → `<th>Unidade Administrativa</th>`; badge do resumo `Duplicatas (nome existente)` → `Duplicatas (localização existente)` (FR-013 — texto de situação com termo legado); nenhuma outra linha do template
- [x] T010 [US3] Corrigir assertions defasados pelo `62728fa` (R6): `tests/test_locations_export.py` L157 (`"Nome / Identificação"` → `"Localização"`) e o header esperado em `test_screen_without_export_permission_search_and_table_intact`; `tests/test_locations_search.py::test_base_route_renders_current_table_structure` (header legado → `Localização`/`Unidade Administrativa`) — traz os 3 failures do domínio para verde

**Checkpoint**: interface e mensagens 100% oficiais; suíte do domínio de locais verde.

---

## Phase 6: User Story 4+5 — Semântica/dados e preservação da 048 (P1)

**Goal**: Provar que a mudança de rótulos não cria duplicidades, não altera dados e não degrada a inteligência da 048.

**Independent Test**: mesmo conteúdo em formato legado e oficial → mesmos registros, nada duplicado (SC-004); fluxo completo 048 funciona com o CSV oficial.

- [x] T011 [US4] Adicionar em `tests/test_location_nomenclatura_050.py` os cenários 9–12 do FR-022: localização existente → DUPLICADO sem novo registro; reanálise do mesmo arquivo → duplicados, nada duplicado (FR-018/SC-004); rollback da linha com erro preservado (gravação por linha da 029 intocada); dados pré-existentes intactos após a importação (FR-017) — consulta direta ao modelo para verificar name/branch/department
- [x] T012 [US5] Verificação de preservação da 048 (FR-019/020/021): cenário ponta a ponta do CSV oficial passando pelo passo de mapeamento dedicado (confirmação/alteração de coluna funciona), classificação por registro, confirmação explícita e auditoria `write_audit` registrada; grep provando rotas/URLs e `execute_locations_import` sem diff

**Checkpoint**: semântica preservada; inteligência 048 íntegra com o novo contrato.

---

## Phase 7: User Story 6 — Exportação coerente (P2)

**Goal**: O `locais.csv` exportado usa cabeçalhos oficiais e é reimportável sem ajustes (round-trip).

**Independent Test**: export tem header oficial; reimportar o arquivo baixado → duplicados corretos, nada criado (cenário cobre FR-026/027 + SC-004).

- [x] T013 [US6] Cabeçalho oficial em `generate_locations_csv` de `app/services/report_service.py` (R4): `["Localização", "Unidade Administrativa", "Departamento", "Prédio", "Andar", "Sala", "Gestor"]` (valores/colunas/ordem inalterados) + atualizar `LOCATION_CSV_HEADER` (L33) e assertions de header em `tests/test_locations_export.py` + teste de round-trip (exportar → reimportar → duplicados, nada novo) no arquivo de testes da 050

**Checkpoint**: round-trip exportar→importar 100% coerente com a nomenclatura oficial.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Regressão total, registro formal e fechamento.

- [x] T014 Suíte completa (FR-023/SC-005): `pytest -q` — régua comparativa contra o T002: **842 do baseline mantidos verdes + 3 failures do domínio corrigidos (passam a passar) + N novos testes do contrato verdes; somente os 2 de `test_backup_externo.py` falham** (baseline externo documentado — FR-021 proíbe tocá-los); nenhum teste que passava pode passar a falhar
- [x] T015 V5 não-vazamento (SC-006) + varredura de legados (C1 do analyze): `git diff --stat` confinado aos arquivos do contract §4 (location_import_service, import_intelligence—só FIELD_LABELS locations, report_service—só generate_locations_csv, locations/import.html, tests do domínio, docs de locais); parciais `imports/_*.html` sem diff; **grep de termos legados no domínio de locais** ("Filial", "Nome do local", "Nome / Identificação", "filial é obrigatória" em templates/services/JS de locations + `FIELD_LABELS` — 0 ocorrências como rótulo/mensagem; termos em valores de dados não contam, SC-003); escrever `specs/050-importacao-locais-nomenclatura/validacao.md` no formato da família (V1–V6 do quickstart, medições, baseline/final, evidências)
- [x] T016 Documentação (FR-024): atualizar `docs/ARQUITETURA_E_MANUTENCAO.md` L715 (header do export legado → oficial) e varrer trechos de locais (L680–716) para terminologia — sem tocar seções de outras funcionalidades; marcar tasks `[x]`; commits por grupo lógico (código+testes / artefatos spec)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato, sem dependências — bloqueia tudo (baseline é a régua do T014)
- **US1 (T003–T005)**: TDD — T003 (falhar) → T004 (implementar) → T005 (verificação)
- **US2 (T006)**: depende de T004 (aliases existentes para os legados serem testados)
- **US3 (T007–T010)**: T007 independente de T008/T009; T010 após T009 (textos oficiais definidos antes dos assertions)
- **US4+5 (T011–T012)**: após T004+T007 (contrato e mensagens prontos para o fluxo ponta a ponta)
- **US6 (T013)**: após T004 (round-trip depende dos aliases oficiais); conflito de arquivo com T010 (test_locations_export.py) — sequencial após US3
- **Polish (T014–T016)**: após todas as stories

### User Story Dependencies

US1 → US2 → US3 → US4/5 → US6 → Polish (sequencial por domínio compartilhado — Princípio I; sem paralelismo entre stories)

### Parallel Opportunities (limitadas, dentro das restrições)

- T008 (import_intelligence.py) e T009 (locations/import.html): arquivos diferentes, sem dependência mútua — únicos [P] seguros da execução
- T015 (validacao.md) pode ser redigido em paralelo ao T016 (docs) após T014
- Nenhuma outra: `test_locations_export.py` é tocado por T010 e T013 (conflito); parser/rótulos alimentam todos os testes

---

## Implementation Strategy

### MVP First (US1 apenas)

1. T001–T002 (setup/baseline) → 2. T003–T005 → **STOP**: CSV oficial já importa; demonstrável

### Incremental Delivery

US1 (contrato) → US2 (compatibilidade) → US3 (interface) → US4/5 (provas) → US6 (export) → Polish (regressão+validação+commit). Cada checkpoint é validável isoladamente pelo quickstart.md (V1–V6).

### Commit plan (grupo lógico)

1. `Feature 050: contrato oficial + compatibilidade no importador de locais` (T003–T006: parser + testes do contrato)
2. `Feature 050: nomenclatura oficial na interface, mensagens e export de locais` (T007–T013)
3. `Spec 050: artefatos spec-kit e registro de validação` (T015–T016)

---

## Notes

- [P] tasks = arquivos diferentes, sem dependência — apenas T008/T009 e T015/T016 qualificam
- T002 é a régua de regressão do T014: os 5 FAILED do baseline devem terminar exatamente como 3 FIXED + 2 externos
- Zero migração/schema/API (FR-016/017 + decisão clarify Q2) — qualquer diff em `models/`, `schemas/` ou `routes.py` é violação do contract §5
- Fontes: research R1–R10 · contract §1–§5 · data-model §2–§5 · quickstart V1–V6
