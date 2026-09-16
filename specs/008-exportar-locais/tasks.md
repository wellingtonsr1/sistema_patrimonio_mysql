# Tasks: Exportação CSV de Locais (feature 008)

**Input**: Design documents from `/specs/008-exportar-locais/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ (R1–R5) · data-model.md ✅ · contracts/locations-csv-contract.md ✅ · quickstart.md ✅

**Tests**: Incluídos — exigidos pela spec (FR-010) e pelo plan (TDD, Constitution VIII), em arquivo novo `tests/test_locations_export.py`.

**Organization**: Tasks agrupadas por user story. Dentro de cada story, os testes são escritos e executados **vermelhos ANTES** da implementação correspondente (requisito TDD); o marcador `[P]` significa apenas independência de arquivo — **nunca** execução concorrente com a implementação da mesma story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Carregar contexto e estabelecer baseline antes de qualquer alteração

- [ ] T001 Ler os artefatos da feature (spec.md, plan.md §Implementation Flow, research.md R1–R5, contracts/locations-csv-contract.md, quickstart.md) e os arquivos-alvo: `app/services/report_service.py` (métodos `generate_*_csv`, em especial `generate_custodians_csv` ~L410), `app/api/reports_api.py` (endpoint `export_custodians_csv` ~L219), `app/web/templates/locations/list.html` (page-header) e `tests/test_rbac.py` L100-170 (padrão do teste de permissão de export)
- [ ] T002 Executar baseline da suíte: `python -m pytest tests/ -q --tb=no` e registrar o patamar em Validation Results (baseline de referência desta sessão: 264 passed / 1 failed conhecido — lockout defasado; a feature não pode piorar esse patamar além de somar testes novos)

**Checkpoint**: Contexto carregado e baseline registrada — nenhuma linha de código alterada ainda.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verificar, em código real, os mecanismos de reuso que a feature consome (gates de leitura — PROIBIDO alterar nesta fase)

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase

- [ ] T003 Verificar (somente leitura) e registrar em Validation Results: (a) padrão exato de `generate_custodians_csv` em `app/services/report_service.py` (assinatura com lista opcional, `io.StringIO`, `csv.writer(delimiter=";", quoting=csv.QUOTE_MINIMAL)`, cabeçalhos PT minúsculos, campos `or ""`); (b) padrão de resposta de `export_custodians_csv` em `app/api/reports_api.py` (`require_permission("relatorios.exportar")`, `Response(media_type="text/csv; charset=utf-8-sig", headers={"Content-Disposition": "attachment; filename=..."})`); (c) estrutura atual do page-header de `app/web/templates/locations/list.html` (grupo de botões gated por `locais.criar`, padrão `btn btn-ghost` + `bi-upload me-1` nos 3 botões existentes do sistema); (d) fixtures `client`/`unauth_client`/`db_session` em `tests/conftest.py` e padrão de 403 por perfil sem `relatorios.exportar` em `tests/test_rbac.py`; (e) id do artigo de ajuda `cadastrar-locais` e a §12.5 de `docs/ARQUITETURA_E_MANUTENCAO.md`. Qualquer divergência em relação ao plan → PARAR e reportar antes de seguir

**Checkpoint**: Mecanismos de reuso confirmados — user stories liberadas.

---

## Phase 3: User Story 1 - Exportar os locais em CSV a partir da tela (Priority: P1) 🎯 MVP

**Goal**: Botão "Exportar CSV" na tela de Locais que baixa `locais.csv` com todos os locais, no padrão de exportação do sistema.

**Independent Test**: Autenticado com `relatorios.exportar`: botão visível; clique (ou GET direto ao endpoint) devolve 200 com download CSV contendo todos os locais; tela continua funcionando.

### Tests for User Story 1 ⚠️ (TDD — escrever PRIMEIRO, executar e ver FALHAR)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T004 [P] [US1] Criar `tests/test_locations_export.py` com os testes US1 (fixtures `client`/`db_session`), ANTES de qualquer implementação: (a) botão "Exportar CSV" presente no HTML de `GET /locations` com `href="/api/v1/reports/locations/csv"` e gate correto; (b) `GET /api/v1/reports/locations/csv` → 200 com `text/csv; charset=utf-8-sig` no content-type e `attachment; filename=locais.csv` no Content-Disposition; (c) corpo contém o nome de todos os locais criados na massa (e somente eles); (d) após a exportação, `GET /locations` segue 200 com a tabela íntegra (tela não afetada). Executar `python -m pytest tests/test_locations_export.py -q` e CONFIRMAR que falham (endpoint e botão não existem) — registrar a saída em Validation Results

### Implementation for User Story 1

- [ ] T005 [US1] Implementar `generate_locations_csv(db, locations: Optional[List[Location]] = None) -> str` em `app/services/report_service.py` (junto aos demais `generate_*_csv`): se `locations is None` → `LocationService.get_all(db)` (todos, ordenação vigente `branch, department, name`); `io.StringIO` + `csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)`; cabeçalho `nome;filial;departamento;predio;andar;sala;gestor`; uma linha por local com `name, branch, department, building or "", floor or "", room or "", manager_name or ""` — SEM colunas "Ações" e "Bens" (FR-004/research R2); importar `LocationService` seguindo o padrão de import existente no arquivo
- [ ] T006 [US1] Implementar `GET /locations/csv` em `app/api/reports_api.py` (junto aos demais `export_*_csv`): `dependencies=[Depends(require_permission("relatorios.exportar"))]`; corpo idêntico a `export_custodians_csv` — chamar `ReportService.generate_locations_csv(db)` e responder `Response(content=csv_content, media_type="text/csv; charset=utf-8-sig", headers={"Content-Disposition": "attachment; filename=locais.csv"})`; SEM parâmetros de query (FR-006/research R5)
- [ ] T007 [US1] Adicionar o botão no page-header de `app/web/templates/locations/list.html`: `{% if can('relatorios.exportar') %}<a href="/api/v1/reports/locations/csv" class="btn btn-ghost"><i class="bi bi-upload me-1"></i> Exportar CSV</a>{% endif %}` como primeiro botão do grupo (precedente de colaboradores), fora do bloco `locais.criar`; markup byte-idêntico aos 3 botões existentes (contrato §4)
- [ ] T008 [US1] Executar `python -m pytest tests/test_locations_export.py -q` → US1 100% verde; em seguida regressão direta no estado da baseline: `python -m pytest tests/ -q --tb=no` sem novos failures (registrar em Validation Results)

**Checkpoint**: US1 (MVP) funcional e testável independentemente — PARAR E VALIDAR antes de US2/US3.

---

## Phase 4: User Story 2 - Conteúdo fiel e no padrão do sistema (Priority: P2)

**Goal**: CSV com formato fixado no contrato: cabeçalho exato, escapamento correto, vazios como `""`, ordenação da listagem, sem colunas de interface.

**Independent Test**: Inspecionar o corpo do CSV: 1ª linha exata; linha por local na ordem `filial, departamento, nome`; valores com `;`/aspas/acentos escapados; nulos em branco; sem "Ações"/"Bens".

### Tests for User Story 2 ⚠️ (TDD — estender ANTES de tocar em implementação)

- [ ] T009 [P] [US2] Estender `tests/test_locations_export.py` com os casos US2 (executar após cada bloco): (a) primeira linha EXATAMENTE `nome;filial;departamento;predio;andar;sala;gestor` (contrato §3); (b) uma linha por local, na ordenação filial→departamento→nome (massa com filiais/departamentos fora de ordem de inserção); (c) escapamento — local com `;` no nome e local com aspas/acentos: linhas íntegras, célula única ao re-parsear com `csv.reader(delimiter=";")`; (d) campos opcionais nulos → vazios (`""`), não `"None"`; (e) ausência das colunas de interface — sem "Ações"/"Ver Bens" e sem contagem de bens no corpo; (f) `ReportService.generate_locations_csv(db)` direto (sem argumento) = mesmo conteúdo do endpoint (reuso R1)

### Implementation for User Story 2

- [ ] T010 [US2] Conformidade do formato: os casos (a)–(f) de T009 devem passar com a implementação da T005; ajustar o service SOMENTE se algum caso evidenciar lacuna (ex.: escaping ou default de lista) — sem reescrever o mecanismo padrão (research R1)

**Checkpoint**: US1 + US2 funcionando independentemente.

---

## Phase 5: User Story 3 - Proteção e preservação (Priority: P3)

**Goal**: Exportação protegida por RBAC e read-only, sem qualquer regressão na tela ou nas exportações existentes.

**Independent Test**: Sem `relatorios.exportar`: botão ausente + endpoint 403; 401 sem sessão; dados intactos após exportar; exports existentes (custodians/inventory) inalterados.

### Tests for User Story 3 ⚠️ (TDD — casos de proteção/não regressão)

- [ ] T012 [P] [US3] Estender `tests/test_locations_export.py` com os casos US3: (a) usuário autenticado SEM `relatorios.exportar` (padrão de perfil do `test_rbac.py`) → botão AUSENTE no HTML de `/locations` e endpoint com **403**; (b) `unauth_client` no endpoint → 401 (mecanismo da API); (c) read-only — snapshot de `Location` (contagem + campos) antes/depois de exportações repetidas é idêntico; (d) zero locais → 200 com APENAS a linha de cabeçalho (sem 500); (e) não-regressão das exportações existentes — `/api/v1/reports/custodians/csv` continua 200 com `filename=colaboradores.csv` e `/api/v1/reports/inventory/csv` continua 200 (mesmo gate e resposta de antes); (f) tela sem o gate de exportação para usuário sem permissão: pesquisa (007) e tabela seguem íntegras
- [ ] T011 [US3] Executar `python -m pytest tests/test_locations_export.py -q` → 100% verde; regressão direta no estado da baseline sem novos failures (nota: T011 executa a validação da story — os testes T012 são escritos primeiro; ordem de escrita: T012 → correções mínimas se houver lacuna → T011 verde)

**Checkpoint**: Todas as user stories funcionando.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validação final, documentação e governança (Constitution VIII/XI/XII)

- [ ] T013 Executar a suíte completa: `python -m pytest tests/ -q --tb=no` → patamar baseline + testes novos, nenhum failure novo além do lockout defasado conhecido (registrar números exatos em Validation Results)
- [ ] T014 [P] Documentação na central de ajuda embutida: acrescentar seção "Exportar locais" ao artigo `cadastrar-locais` em `app/services/help_service.py` — o que exporta (todos os locais, dados cadastrais da tabela, sem colunas de interface), formato CSV padrão do sistema (Excel-friendly), botão no cabeçalho e permissão necessária (Constitution XI)
- [ ] T015 [P] Documentação em `docs/ARQUITETURA_E_MANUTENCAO.md` §12.5 (Relatórios & Exportações): nova exportação `GET /api/v1/reports/locations/csv` (`locais.csv`), geração via `ReportService.generate_locations_csv`, gate `relatorios.exportar`, decisão "todos os locais, sem colunas de interface" (Constitution XI)
- [ ] T016 Validação manual no navegador conforme quickstart.md §3 (cenários 3.1–3.11, incluindo abertura no Excel — SC-002) e spot-checks §4 — executada pelo operador; registrar resultado e data em Validation Results
- [ ] T017 Fechamento: conferir checklist Constitution (plan §Constitution Check), `git status` com escopo exato (report_service.py, reports_api.py, locations/list.html, tests/test_locations_export.py, help_service.py, docs/ARQUITETURA_E_MANUTENCAO.md, artifacts da feature — nada além disso) e preencher a síntese dos Success Criteria (SC-001..SC-006) em Validation Results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato, sem dependências
- **Foundational (T003)**: depende do Setup; BLOQUEIA todas as user stories (gate de reuso — qualquer divergência ⇒ PARAR)
- **US1 (T004–T008)**: após T003 — caminho crítico do MVP (service → endpoint → template, nessa ordem)
- **US2 (T009–T010)**: após US1 completa (T008) — os casos exercitam o formato já implementado; testes primeiro
- **US3 (T011–T012)**: após US2 (mesmos arquivos; T012 escrito antes, T011 fecha a story em verde)
- **Polish (T013–T017)**: após todas as stories; T016 (manual) pode ocorrer em paralelo com T014–T015

### Within Each User Story

- **Testes são escritos e executados VERMELHOS antes da implementação da story** (TDD — Constitution VIII; lições 005/006/007)
- Service antes do endpoint; endpoint antes do template (ordem de integração do plan §Implementation Flow)
- Story completa (checkpoint verde) antes de avançar para a próxima prioridade

### Parallel Opportunities

- **T001–T003** são leitura/verificação e podem ser preparados juntos
- **T014/T015** ([P]) tocam arquivos distintos entre si e do código — paralelizáveis
- Marcador `[P]` nas tasks de teste (T004/T009/T012) significa apenas **independência de arquivo** (arquivo de testes próprio); os testes de cada story devem ser escritos e validados vermelhos **ANTES** da implementação correspondente — nunca em paralelo com ela (lição da 005)
- Todo o restante é sequencial: as stories compartilham service + endpoint + template

## Parallel Example: User Story 1

```bash
# Dentro da US1 a sequência é estrita (mesmos arquivos, dependência lógica):
T004 (testes vermelhos) → T005 (service) → T006 (endpoint) → T007 (template) → T008 (verde + regressão)
# [P] em T004 indica apenas que o arquivo de testes é próprio — não execução concorrente com T005–T007
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fases 1–2 (Setup + Foundational): T001–T003
2. US1 completa: T004–T008 (TDD: vermelho → service → endpoint → template → verde)
3. **STOP and VALIDATE**: cenários 3.1–3.4 do quickstart + suíte sem regressão
4. MVP entregável: exportação funcional a partir da tela, no padrão do sistema

### Incremental Delivery

1. Setup + Foundational → fundação verificada
2. US1 → MVP validável (P1)
3. US2 → formato fiel ao contrato (P2)
4. US3 → proteção RBAC e preservação (P3)
5. Polish → docs (XI), validação manual (T016), fechamento (T017)

---

## Notes

- [P] tasks = different files, no dependencies — nunca concorrência com a implementação da mesma story
- [Story] label maps task to specific user story for traceability
- Cada story é independentemente completável e testável
- Verify tests fail before implementing (obrigatório em T004; T009/T012 confirmam caminhos já implementados ou evidenciam lacunas)
- Stop at any checkpoint to validate story independently
- Nenhuma task altera models, schemas, permissões, banco, tela de Locais fora do page-header, ou as exportações existentes (plan §Technical Context Constraints)
- Commit after each task or logical group — somente se o usuário solicitar

---

## Validation Results

> Preenchido durante a implementação (T002, T004, T008, T011, T013, T016, T017). Não marcar antecipadamente.

### Baseline (T002)

- (a preencher)

### TDD vermelho (T004)

- (a preencher)

### Execuções por story (T008/T011)

- (a preencher)

### Suíte completa (T013)

- (a preencher)

### Validação manual (T016)

- (a preencher — operador)

### Success Criteria (T017)

- SC-001 (download em 1 clique com `relatorios.exportar`): (a preencher — T004/T016)
- SC-002 (abre no Excel com padrão do sistema): (a preencher — T016)
- SC-003 (100% dos locais, sem colunas de interface): (a preencher — T004c/T009e)
- SC-004 (100% das tentativas sem permissão negadas): (a preencher — T012a/T012b)
- SC-005 (zero alterações de dados): (a preencher — T012c)
- SC-006 (suíte verde, sem regressão): (a preencher — T013)
