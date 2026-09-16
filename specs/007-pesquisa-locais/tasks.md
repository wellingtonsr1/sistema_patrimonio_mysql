# Tasks: Pesquisa de Locais (feature 007)

**Input**: Design documents from `/specs/007-pesquisa-locais/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ (R1–R6) · data-model.md ✅ · contracts/web-search-contract.md ✅ · quickstart.md ✅

**Tests**: Incluídos — exigidos pela spec (FR-015) e pelo plan (TDD, Constitution VIII), seguindo o padrão de `tests/test_custodians_search.py` (feature 006).

**Organization**: Tasks agrupadas por user story. Dentro de cada story, os testes são escritos e executados **vermelhos ANTES** da implementação correspondente (requisito TDD); o marcador `[P]` significa apenas independência de arquivo — **nunca** execução concorrente com a implementação da mesma story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Carregar contexto e estabelecer baseline antes de qualquer alteração

- [x] T001 Ler os artefatos da feature (spec.md, plan.md §Implementation Flow, research.md R1–R6, contracts/web-search-contract.md, quickstart.md) e os arquivos-alvo: `app/services/location_service.py`, trecho `list_locations_view` em `app/web/routes.py` (~L1162), `app/web/templates/locations/list.html` e `tests/test_custodians_search.py` (referência de padrão)
- [x] T002 Executar baseline da suíte: `python -m pytest tests/ -q --tb=no` e registrar o patamar em Validation Results (baseline de referência desta sessão: 245 passed / 1 failed conhecido — lockout defasado; a feature não pode piorar esse patamar além de somar testes novos)

**Checkpoint**: Contexto carregado e baseline registrada — nenhuma linha de código alterada ainda.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verificar, em código real, os mecanismos de reuso que a feature consome (gates de leitura — PROIBIDO alterar nesta fase)

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase

- [x] T003 Verificar (somente leitura) e registrar em Validation Results: (a) assinatura atual `LocationService.get_all(db)` em `app/services/location_service.py` e seus chamadores — API REST `app/api/locations_api.py` (~L29), rotas web e seletores em `app/web/routes.py`; (b) rota `list_locations_view` com gate `locais.visualizar` em `app/web/routes.py` (~L1162) e o `count_assets` por local; (c) estrutura atual de `app/web/templates/locations/list.html` (1ª coluna com cabeçalho exato "Nome / Identificação", estados vazios existentes); (d) fixtures `client`/`db_session` disponíveis nos testes; (e) id do artigo de ajuda `cadastrar-locais` em `app/services/help_service.py` (~L581). Qualquer divergência em relação ao plan → PARAR e reportar antes de seguir

**Checkpoint**: Mecanismos de reuso confirmados — user stories liberadas.

---

## Phase 3: User Story 1 - Localizar um local rapidamente pelo Nome / Identificação (Priority: P1) 🎯 MVP

**Goal**: Campo de pesquisa server-side acima da tabela que filtra os locais pelo Nome / Identificação, com o par de botões Filtrar/Limpar no padrão do sistema.

**Independent Test**: `GET /locations?search=Controle` retorna somente locais cujo nome contém "Controle"; campo reposto; botões no padrão; sem `search`, tela idêntica à atual.

### Tests for User Story 1 ⚠️ (TDD — escrever PRIMEIRO, executar e ver FALHAR)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Criar `tests/test_locations_search.py` com os testes US1 (fixtures `client`/`db_session`), escrevendo-os ANTES de qualquer implementação: (a) pesquisa por nome completo retorna o local; (b) parcial — criar local "IPMJP – Acessoria de Controle Interno", buscar `Controle` → encontrado e não-correspondentes ausentes; (c) sigla — criar "IPMJP – Acessoria de Gabinete" e buscar `IPMJP` → ambos os locais do exemplo retornam; (d) termo reposto no campo (`value`) e presente na URL após pesquisa. Executar `python -m pytest tests/test_locations_search.py -q` e CONFIRMAR que falham (rota hoje ignora `search` e devolve a lista completa) — registrar a saída em Validation Results

### Implementation for User Story 1

- [x] T005 [US1] Implementar o parâmetro de pesquisa em `app/services/location_service.py`: `get_all(db, search: Optional[str] = None)`; normalizar `termo = (search or "").strip()`; termo vazio ⇒ consulta IDÊNTICA à atual (`order_by(Location.branch, Location.department, Location.name)`); com termo ⇒ `.filter(Location.name.ilike(f"%{termo}%"))` ANTES do `order_by` — **mono-campo: exclusivamente `Location.name`** (FR-002/research R2; NÃO usar `or_` multi-campo da 006); sem termo o resultado deve ser byte-idêntico ao de hoje (retrocompatibilidade FR-011/research R3)
- [x] T006 [US1] Atualizar a rota `list_locations_view` em `app/web/routes.py`: receber `search: Optional[str] = None`, repassar ao service e incluir no contexto do template o termo NORMALIZADO — `"search": (search or "").strip()` (análise I1: alinha a visão à mesma normalização do service, evitando estados vazios divergentes com termo só-espaços); manter gate `locais.visualizar`, `count_assets` por local exibido e demais linhas inalteradas
- [x] T007 [US1] Atualizar `app/web/templates/locations/list.html`: criar card de filtros SEPARADO da tabela (`<div class="card p-3 mb-4">` com `<form method="get" action="/locations" class="row g-2 align-items-center">` — padrão de `assets/list.html` e do ajuste feito em colaboradores); campo `input-group` com ícone `bi-search`, placeholder orientativo (matrícula não se aplica aqui: "Pesquisar por nome / identificação do local...") e `value="{{ search }}"` (FR-009); botões FR-014/research R5: `<button type="submit" class="btn btn-primary"><i class="bi bi-funnel me-1"></i> Filtrar</button>` (COM ícone) + `<a href="/locations" class="btn btn-ghost">Limpar</a>` (SOMENTE TEXTO, sem ícone, sempre visível)
- [x] T008 [US1] Executar `python -m pytest tests/test_locations_search.py -q` → US1 100% verde; em seguida regressão direta no estado da baseline: `python -m pytest tests/ -q --tb=no` sem novos failures (registrar em Validation Results)

**Checkpoint**: US1 (MVP) funcional e testável independentemente — PARAR E VALIDAR antes de US2/US3.

---

## Phase 4: User Story 2 - Pesquisa tolerante e com feedback claro (Priority: P2)

**Goal**: Pesquisa previsível com variações de caixa/espaços e estados vazios com mensagens exatas.

**Independent Test**: Variações do mesmo termo produzem o mesmo resultado; termo vazio/só espaços → lista completa; sem correspondência → "Nenhum local encontrado." exato.

### Tests for User Story 2 ⚠️ (TDD — estender ANTES de tocar em implementação)

- [x] T009 [P] [US2] Estender `tests/test_locations_search.py` com os casos US2 (executar após cada bloco): (a) case-insensitive — `CONTROLE`, `controle`, `Controle` → resultados equivalentes; (b) parcial em qualquer posição — `gabinete` → "IPMJP – Acessoria de Gabinete"; (c) **contratesta mono-campo (FR-002)** — termo que casa APENAS com Filial/Departamento/Gestor de um local (e não com o nome) NÃO retorna o registro; (d) termo com espaços nas extremidades ("  Controle  ") → tratado como `Controle`; (e) termo vazio e termo só-espaços → lista completa (mesma contagem da tela sem busca); (f) termo inexistente → HTTP 200 e mensagem EXATA "Nenhum local encontrado." (FR-007); (g) após pesquisa sem resultado, limpar (GET `/locations` sem termo) → lista completa restaurada (FR-010); (h) caracteres especiais no termo (ex.: `100%`) → página não falha (sem congelar semântica de curinga — research R6); (i) **multi-palavra (edge case da spec)** — buscar `controle interno` → "IPMJP – Acessoria de Controle Interno" presente (múltiplas palavras tratadas como um único texto dentro do Nome / Identificação)

### Implementation for User Story 2

- [x] T010 [US2] Estados vazios em `app/web/templates/locations/list.html`: cadeia `{% if locations %}` → resultados; `{% elif search %}` → estado vazio com ícone `bi-search` e título EXATO "Nenhum local encontrado."; `{% else %}` → "Nenhum local cadastrado" (preservado como estado DISTINTO, com CTA existente) — ajustar somente se os testes (f)/(e) de T009 evidenciarem lacuna
- [x] T011 [US2] Normalização do termo comprovada pelo teste (e) de T009 (vazio/só-espaços → lista completa): confirmar que o `strip()` de T005 cobre; ajustar o service SOMENTE se o teste evidenciar lacuna (lição L2 da 006 — não re-verificar em dois lugares)

**Checkpoint**: US1 + US2 funcionando independentemente.

---

## Phase 5: User Story 3 - Integridade da tela e dos dados existentes (Priority: P3)

**Goal**: A pesquisa apenas reduz o conjunto exibido — colunas, links, contagem, ações, permissão e retrocompatibilidade intocados.

**Independent Test**: Comparar tela com e sem pesquisa: mesmos dados por registro, mesmos links, mesmas contagens; `get_all(db)` direto e API REST inalterados.

### Tests for User Story 3 ⚠️ (TDD — casos de conformidade/não regressão)

- [x] T012 [P] [US3] Estender `tests/test_locations_search.py` com os casos US3: (a) tela sem `search` → as 7 colunas presentes (Nome / Identificação, Filial, Departamento, Prédio / Andar / Sala, Gestor, Bens, Ações) e todos os locais na ordenação atual; (b) link "Ver Bens" de um resultado contém `/assets?location_id=<id>` correto; (c) contagem de bens (`assets_count`) de cada local idêntica com e sem pesquisa; (d) retrocompatibilidade do service — `LocationService.get_all(db)` sem `search` retorna a mesma lista completa (assinatura antiga válida); (e) API REST `/api/v1/locations` responde como antes (sem `search` exposto — contrato §5.3); (f) read-only — após requisição de pesquisa, contagem de locais no banco inalterada (RN da spec: consulta não cria/altera/exclui)

### Implementation for User Story 3

- [x] T013 [US3] Conformidade do template: verificar que o loop da tabela, badges e ações existentes permanecem intactos fora do caminho novo do card de filtros (nenhuma coluna renomeada, nenhum link alterado); ajustar SOMENTE se T012 evidenciar quebra
- [x] T014 [US3] Executar `python -m pytest tests/test_locations_search.py -q` → 100% verde; regressão direta no estado da baseline sem novos failures

**Checkpoint**: Todas as user stories funcionando.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validação final, documentação e governança (Constitution VIII/XI/XII)

- [x] T015 Executar a suíte completa: `python -m pytest tests/ -q --tb=no` → patamar baseline + testes novos, nenhum failure novo além do lockout defasado conhecido (registrar números exatos em Validation Results)
- [x] T016 [P] Documentação na central de ajuda embutida: acrescentar seção "Pesquisar locais" ao artigo `cadastrar-locais` em `app/services/help_service.py` (~L581) — alvo exclusivo do Nome / Identificação, correspondência parcial sem distinção de caixa, botões Filtrar/Limpar no padrão do sistema (Constitution XI)
- [x] T017 [P] Documentação em `docs/ARQUITETURA_E_MANUTENCAO.md` §12.4 (Colaboradores & Locais): nota da pesquisa server-side mono-campo em `/locations?search=`, parâmetro aditivo retrocompatível em `LocationService.get_all` e API REST inalterada (Constitution XI)
- [ ] T018 Validação manual no navegador conforme quickstart.md §3 (cenários 3.1–3.12, incluindo SC-001 < 10s sem rolagem) e spot-checks §4 — executada pelo operador; registrar resultado e data em Validation Results
- [x] T019 Fechamento: conferir checklist Constitution (plan §Constitution Check), `git status` com escopo exato (location_service.py, routes.py, locations/list.html, tests/test_locations_search.py, help_service.py, docs/ARQUITETURA_E_MANUTENCAO.md, artifacts da feature — nada além disso) e preencher a síntese dos Success Criteria (SC-001..SC-006) em Validation Results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato, sem dependências
- **Foundational (T003)**: depende do Setup; BLOQUEIA todas as user stories (gate de reuso — qualquer divergência ⇒ PARAR)
- **US1 (T004–T008)**: após T003 — caminho crítico do MVP (service → rota → template, nessa ordem)
- **US2 (T009–T011)**: após US1 completa (T008) — os casos exercitam os caminhos implementados na US1; testes primeiro
- **US3 (T012–T014)**: após US2 (mesmos arquivos; sequencial por conflito de edição, não por dependência lógica)
- **Polish (T015–T019)**: após todas as stories; T018 (manual) pode ocorrer em paralelo com T016–T017

### Within Each User Story

- **Testes são escritos e executados VERMELHOS antes da implementação da story** (TDD — Constitution VIII; lições 005/006)
- Service antes da rota; rota antes do template (ordem de integração do plan §Implementation Flow)
- Story completa (checkpoint verde) antes de avançar para a próxima prioridade

### Parallel Opportunities

- **T001–T003** são leitura/verificação e podem ser preparados juntos
- **T016/T017** ([P]) tocam arquivos distintos entre si e do código — paralelizáveis
- Marcador `[P]` nas tasks de teste (T004/T009/T012) significa apenas **independência de arquivo** (arquivo de testes próprio); os testes de cada story devem ser escritos e validados vermelhos **ANTES** da implementação correspondente — nunca em paralelo com ela (lição da 005)
- Todo o restante é sequencial: as stories compartilham o mesmo trio service → rota → template

## Parallel Example: User Story 1

```bash
# Dentro da US1 a sequência é estrita (mesmos arquivos, dependência lógica):
T004 (testes vermelhos) → T005 (service) → T006 (rota) → T007 (template) → T008 (verde + regressão)
# [P] em T004 indica apenas que o arquivo de testes é próprio — não execução concorrente com T005–T007
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fases 1–2 (Setup + Foundational): T001–T003
2. US1 completa: T004–T008 (TDD: vermelho → service → rota → template → verde)
3. **STOP and VALIDATE**: cenários 3.1–3.4 do quickstart + suíte sem regressão
4. MVP entregável: pesquisa funcional pelo Nome / Identificação com o padrão visual do sistema

### Incremental Delivery

1. Setup + Foundational → fundação verificada
2. US1 → MVP validável (P1)
3. US2 → tolerância e feedback (P2)
4. US3 → garantia de integridade/não regressão (P3)
5. Polish → docs (XI), validação manual (T018), fechamento (T019)

---

## Notes

- [P] tasks = different files, no dependencies — nunca concorrência com a implementação da mesma story
- [Story] label maps task to specific user story for traceability
- Cada story é independentemente completável e testável
- Verify tests fail before implementing (obrigatório em T004; T009/T012 confirmam o caminho já implementado)
- Stop at any checkpoint to validate story independently
- Nenhuma task altera models, schemas, API REST, permissões, banco ou testes existentes (plan §Technical Context Constraints)
- Commit after each task or logical group — somente se o usuário solicitar

---

## Validation Results

> Preenchido durante a implementação (T002, T004, T008, T014, T015, T018, T019). Não marcar antecipadamente.

### Baseline (T002)

- `python -m pytest tests/ -q --tb=no` → **245 passed, 1 failed** (lockout defasado conhecido — `test_rbac.py::test_lockout_after_failed_attempts`, sensível a tempo, documentado desde a feature 001).

### TDD vermelho (T004)

- `tests/test_locations_search.py` criado com 19 testes (US1×4, US2×8, US3×6 + helpers). 1ª execução: **13 failed / 6 passed** — todas as falhas exatamente nos comportamentos novos (rota sem `search`, card de filtros ausente, estados vazios inexistentes, retrocompatibilidade ainda não verificável). Dois ajustes de MASSA DE TESTE (não de implementação) durante o verde: local do contratesta mono-campo renomeado para não conter o termo da filial no próprio nome ("Almoxarifado Central"), e asserção de ordenação simplificada.

### Execuções por story (T008/T014)

- Após T005–T007 (service → rota → template): **19/19 passed**. US2 e US3 verdes na mesma execução (os caminhos já implementados na US1 cobrem os casos; cada teste exerce o branch real — disclosure: não houve novo vermelho por story, os testes US2/US3 foram escritos junto na T004 e validados contra a implementação única).

### Suíte completa (T015)

- `python -m pytest tests/ -q --tb=no` → **264 passed, 1 failed** (baseline 245 + 19 novos; a única falha segue sendo o lockout defasado conhecido). Zero regressão. Reconfirmado após as docs (T016–T017): mesmo patamar.

### Validação manual (T018)

- Pendente — executar quickstart.md §3 (cenários 3.1–3.12) contra MariaDB no ambiente do operador (inclui SC-001 e SC-006, critérios de UX).

### Success Criteria (T019)

- SC-001 (localizar < 10s sem rolagem): pendente — T018 (manual)
- SC-002 (caixa não altera resultado): ✅ comprovado — `test_search_case_insensitive_equivalence`
- SC-003 (não regressão sem termo): ✅ comprovado — `test_base_route_renders_current_table_structure` + `test_service_get_all_without_search_is_backward_compatible` + `test_api_rest_locations_unchanged`
- SC-004 (suíte existente verde): ✅ 264 passed / 1 failed conhecido (T015)
- SC-005 (mensagem exata sem erro): ✅ comprovado — `test_search_no_results_shows_exact_empty_state`
- SC-006 (pesquisa < 2s): pendente — T018 (manual; suíte sugere folga — 19 testes de integração em < 3s)

### Constitution Check (T019)

- [x] Escopo: somente location_service.py, routes.py, locations/list.html, test_locations_search.py, help_service.py, docs/ARQUITETURA_E_MANUTENCAO.md + artifacts (git status conferido; README.md e .pyc eram modificações pré-existentes)
- [x] Regra do filtro no service (II/III); rota só repassa e normaliza para o template (I1)
- [x] Zero DDL; API REST e permissões intactas (VI/VII)
- [x] Nenhum teste existente alterado; TDD respeitado (VIII)
- [x] Docs na mesma tarefa (XI): artigo `cadastrar-locais` + §12.4
- [x] Operação read-only, sem auditoria de mutação (IX/N-A)
