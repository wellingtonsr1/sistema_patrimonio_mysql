# Tasks: Identificador Provisório de Colaborador PROV-* (feature 010)

**Input**: Design documents from `/specs/010-matricula-provisoria/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ (R1–R6) · data-model.md ✅ · contracts/custodian-identifier-contract.md ✅ · quickstart.md ✅

**Tests**: Incluídos — exigidos pela spec (§13/SC-006) e pelo plan (TDD, Constitution VIII), em arquivo novo `tests/test_custodian_provisional.py`.

**Organization**: Tasks agrupadas por user story. Dentro de cada story, os testes são escritos e executados **vermelhos ANTES** da implementação correspondente (requisito TDD); o marcador `[P]` significa apenas independência de arquivo — **nunca** execução concorrente com a implementação da mesma story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Carregar contexto e estabelecer baseline antes de qualquer alteração

- [x] T001 Ler os artefatos da feature (spec.md, plan.md §Implementation Flow, research.md R1–R6, contracts/custodian-identifier-contract.md, quickstart.md) e os arquivos-alvo: `app/schemas/custodian.py`, `app/services/custodian_service.py`, `app/web/routes.py` (rotas `custodians/new` ~L885–930 e `custodians/{id}/edit` ~L933–990), `app/web/templates/custodians/form.html` (readonly L53-54), `tests/test_movements.py` (padrão de fixtures/massa `MAT-xxxx`) e `tests/conftest.py`
- [x] T002 Executar baseline da suíte: `python -m pytest tests/ -q --tb=no` e registrar o patamar em Validation Results (referência: **281 passed / 1 failed** — lockout defasado conhecido; a feature não pode piorar esse patamar além de somar testes novos)

**Checkpoint**: Contexto carregado e baseline registrada — nenhuma linha de código alterada ainda.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verificar, em código real, os mecanismos de reuso que a feature consome (gates de leitura — PROIBIDO alterar nesta fase)

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase

- [x] T003 Verificar (somente leitura) e registrar em Validation Results: (a) assinatura e validações atuais de `CustodianService.create/update` (erros "Matrícula já cadastrada"/"E-mail já cadastrado"; commit no service); (b) precedente de geração `InventarioService.next_code` (L32–43) — padrão max+1 a replicar; (c) constraint `UNIQUE`/`NOT NULL` de `Custodian.registration_code` e campo `String(50)` (comporta `PROV-999999`); (d) contrato atual da API (`POST/PUT /api/v1/custodians` — 400 via `ValueError`; auditoria `write_change_audit` no PUT) e da web (POST de edição hoje NÃO recebe matrícula; docstring do bloqueio); (e) como `MovementService` exige colaborador e grava snapshots (para os testes da US2); (f) padrão de fixtures `client`/`db_session`/`unauth_client` e massa de colaboradores `MAT-xxxx` nos testes. Qualquer divergência em relação ao plan → PARAR e reportar antes de seguir

**Checkpoint**: Mecanismos de reuso confirmados — user stories liberadas.

---

## Phase 3: User Story 1 - Cadastrar colaborador sem matrícula oficial (Priority: P1) 🎯 MVP

**Goal**: Cadastro (web e API) aceita matrícula não informada e gera `PROV-000001` sequencial automático, único, não escolhível, com marcação visual "provisória".

**Independent Test**: Cadastrar sem matrícula → colaborador criado com `PROV-*` único e marcado; aparece na pesquisa 006; cadastro com matrícula informada segue idêntico ao atual.

### Tests for User Story 1 ⚠️ (TDD — escrever PRIMEIRO, executar e ver FALHAR)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Criar `tests/test_custodian_provisional.py` com os testes US1 (fixtures `client`/`db_session`), ANTES de qualquer implementação: (a) `POST /api/v1/custodians` sem `registration_code` → 201 com `registration_code` em `PROV-000001` (primeiro); (b) segundo cadastro sem matrícula → `PROV-000002` (sequência); (c) web `POST /custodians/new` sem matrícula → colaborador criado com `PROV-*` (redirect de sucesso) e página/listagem exibindo a marcação "provisória"; (d) campo com espaços → tratado como não informado; (e) pesquisa por `PROV-000001` (GET `/custodians?search=`) encontra o colaborador (006); (f) não-regressão: cadastro COM matrícula `MAT-9001` (web e API) segue idêntico ao atual. Executar `python -m pytest tests/test_custodian_provisional.py -q` e CONFIRMAR que falham (não existe geração hoje) — registrar em Validation Results

### Implementation for User Story 1

- [x] T005 [US1] Alterar `app/schemas/custodian.py`: `CustodianCreate.registration_code: Optional[str] = None` (criação; `CustodianUpdate` já opcional — inalterado)
- [x] T006 [US1] Implementar em `app/services/custodian_service.py`: helper `is_provisional(code)` (`startswith("PROV-")`); geração `_next_provisional_code(db)` (padrão `InventarioService.next_code`: maior `PROV-%06d` + 1) integrada ao `create` quando o valor vem vazio/None após trim — com loop limitado de retentativa apoiado na `UNIQUE` (rollback → regenerar → inserir); validação anti-fabricação no `create` (valor informado casando com `PROV-` + 6 dígitos → `ValueError`); manter os erros atuais intactos
- [x] T007 [US1] Alterar `app/web/routes.py`: `create_custodian_form` com `registration_code: Optional[str] = Form(None)` (passando ao service; erros continuam via redirect `?error=`); expor `is_provisional` aos templates via `context_processors` existente (precedente: `can` em `app/web/routes.py` L110) — nenhuma mudança de contexto por rota; rotas delegam, sem regra nova em rota
- [x] T008 [US1] Alterar `app/web/templates/custodians/form.html` (campo opcional na criação com dica "Deixe em branco para gerar um identificador provisório"; em edição, mantém readonly — edição entra na US3) e `custodians/list.html` + `custodians/detail.html` (marcação "provisória" em badge do padrão visual atual junto ao código quando `is_provisional`)
- [x] T009 [US1] Executar `python -m pytest tests/test_custodian_provisional.py -q` → US1 100% verde; em seguida regressão direta: `python -m pytest tests/ -q --tb=no` sem novos failures (registrar em Validation Results)

**Checkpoint**: US1 (MVP) funcional e testável independentemente — PARAR E VALIDAR antes de US2/US3/US4.

---

## Phase 4: User Story 2 - Uso patrimonial normal do provisório (Priority: P1)

**Goal**: Colaborador `PROV-*` participa das operações patrimoniais existentes sem qualquer bloqueio novo (movimentações, termo, inventário, consultas).

**Independent Test**: Com colaborador `PROV-*` cadastrado, executar alocação/cautela via fluxo existente e emitir termo → tudo funciona como para qualquer colaborador; termo exibe a marcação de provisória.

### Tests for User Story 2 ⚠️ (TDD — estender ANTES de tocar em implementação)

- [x] T010 [P] [US2] Estender `tests/test_custodian_provisional.py` com os casos US2 (executar após cada bloco): (a) alocação/cautela de um bem ao colaborador `PROV-*` via `MovementService.create_movement` (padrão de `tests/test_movements.py`) → movimentação registrada, `asset.custodian_id` vinculado, status do bem atualizado — sem bloqueio por provisoriedade; (b) devolução ao estoque do mesmo bem → comportamento existente; (c) termo: movimentação com termo para o colaborador `PROV-*` → página `movements/term.html` 200 contendo o código `PROV-*` e a marcação "provisória"; (d) inventário (sanidade): criação de inventário não alterada (snapshot de nome) — teste leve de criação com custodiante provisório na lista esperada, se o fluxo existente permitir sem acoplamento; (e) consultas: detalhes do bem e listagens 200 com o colaborador provisório

### Implementation for User Story 2

- [x] T011 [US2] Confirmar que NENHUMA validação nova bloqueia operações (o service de movimentação não é alterado); ajustar apenas APRESENTAÇÃO onde a matrícula viva aparece: `app/web/templates/movements/new.html` (seletor/form, se exibir matrícula), `app/web/templates/assets/detail.html` + `assets/list.html` + `assets/form.html` (badge "provisória" junto ao custodiante `PROV-*`) e `app/web/templates/movements/term.html` (marcação no documento) — mudanças somente de apresentação, usando o helper `is_provisional` exposto globalmente via `context_processors` (I1); rodar os testes US2 até 100% verde e registrar

**Checkpoint**: US1 + US2 funcionando independentemente.

---

## Phase 5: User Story 3 - Substituição PROV-* pela matrícula oficial (Priority: P2)

**Goal**: Informar a matrícula oficial no lugar do `PROV-*` mantendo o mesmo colaborador (mesmo `id`), com bens/movimentações/histórico/auditoria preservados; oficiais seguem readonly na web e com validações atuais na API.

**Independent Test**: Cadastrar `PROV-*` com bem alocado → informar matrícula oficial → mesmo `id`, vínculo do bem preservado, snapshot antigo intacto, novo termo com a oficial, alteração auditada.

### Tests for User Story 3 ⚠️ (TDD — estender ANTES de tocar em implementação)

- [x] T012 [P] [US3] Estender `tests/test_custodian_provisional.py` com os casos US3: (a) web: colaborador `PROV-*` → formulário de edição exibe matrícula **editável**; POST `/custodians/{id}/edit` com nova matrícula oficial → mesmo `id`, `registration_code` oficial, sem marcação de provisória; (b) web: colaborador com matrícula oficial → campo permanece readonly e o POST não altera matrícula (comportamento atual); (c) API: `PUT /api/v1/custodians/{id}` com `registration_code` oficial sobre `PROV-*` → 200 com mesmo `id`; (d) preservação: bem alocado antes da substituição permanece vinculado (`asset.custodian_id` inalterado) e a movimentação anterior mantém o snapshot da época (texto com o `PROV-*` gravado); (e) auditoria: substituição via web/API registra `write_change_audit` com before (`PROV-*`) e after (oficial); (f) colisão: substituir por matrícula já usada → erro existente "Matrícula já cadastrada" e o `PROV-*` permanece; (g) API oficial→oficial → mantém o comportamento atual (documentado no contrato §4); (h) emissão futura (2ª metade do FR-011): após a substituição, novo termo/nova movimentação exibe a matrícula oficial e **sem** a marcação de provisória

### Implementation for User Story 3

- [x] T013 [US3] Implementar a substituição: `app/services/custodian_service.py` — no `update`, permitir mudança de `registration_code` quando a atual é `PROV-*` (mantendo anti-fabricação e unicidade atuais); `app/web/routes.py` — `update_custodian_form` ganha `registration_code: Optional[str] = Form(None)` aplicado SOMENTE quando `is_provisional(custodian.registration_code)` (caso contrário ignora o campo — readonly efetivo); `app/web/templates/custodians/form.html` — em edição, campo editável apenas quando provisório (readonly caso contrário); garantir auditoria before/after no caminho web (mecanismo `write_change_audit` existente) — rodar os testes US3 até 100% verde e registrar

**Checkpoint**: US1 + US2 + US3 funcionando.

---

## Phase 6: User Story 4 - Segurança e integridade da numeração (Priority: P2)

**Goal**: Numeração controlada pelo sistema: unicidade permanente, colisão concorrente tratada, fabricação manual rejeitada em todos os caminhos; `PROV-*` nunca é credencial.

**Independent Test**: Colisão com `PROV-000001` pré-existente → próximo número; `PROV-*` digitado em web/API (create e update) → rejeitado.

### Tests for User Story 4 ⚠️ (TDD — estender ANTES de tocar em implementação)

- [x] T014 [P] [US4] Estender `tests/test_custodian_provisional.py` com os casos US4: (a) colisão: pré-criar manualmente um colaborador com `registration_code="PROV-000001"` e cadastrar SEM matrícula → recebe `PROV-000002` (geração consulta o maior existente); (b) anti-fabricação web create: `PROV-000999` digitado → redirect com erro, nenhum colaborador gravado; (c) anti-fabricação API create: → 400; (d) anti-fabricação update (API e web): novo valor `PROV-*` → rejeitado; (e) unicidade permanente: nenhum par de colaboradores compartilha código (varre a massa); (f) não-credencial: cadastrar colaborador `PROV-*` não cria/altera usuário (`User` count inalterado) e `PROV-*` não aparece em nenhum mecanismo de autenticação (sanidade via estrutura existente)

### Implementation for User Story 4

- [x] T015 [US4] Conformidade da proteção: os casos (a)–(f) de T014 devem passar com a implementação de T006/T013; ajustar o service SOMENTE se algum caso evidenciar lacuna (ex.: regex da anti-fabricação, comportamento do loop de retentativa) — sem mecanismo novo de concorrência (research R5); rodar até 100% verde e registrar

**Checkpoint**: Todas as user stories funcionando.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validação final, documentação e governança (Constitution VIII/XI/XII)

- [x] T016 Executar a suíte completa: `python -m pytest tests/ -q --tb=no` → patamar baseline + testes novos, nenhum failure novo além do lockout defasado conhecido (registrar números exatos em Validation Results)
- [x] T017 [P] Documentação na central de ajuda embutida: artigo `cadastrar-colaboradores` em `app/services/help_service.py` — seção sobre o identificador provisório (quando é gerado: deixando a matrícula em branco; formato `PROV-*`; marcado como provisória; uso patrimonial normal; como informar a matrícula oficial depois preservando vínculos) (Constitution XI)
- [x] T018 [P] Documentação em `README.md`: seção de colaboradores menciona o identificador provisório `PROV-*` (geração automática, marcação, substituição pela oficial preservando vínculos e histórico) (Constitution XI)
- [ ] T019 Validação manual pelo operador conforme quickstart.md §3 (cenários 3.1–3.10: geração, sequência, anti-fabricação, pesquisa, alocação/termo, substituição com preservação, readonly de oficial, ajuda) e §4 (API opcional) — registrar resultado e data em Validation Results
- [x] T020 Fechamento: checklist Constitution (plan §Constitution Check), `git status --porcelain` com escopo exato (schemas/custodian.py, services/custodian_service.py, web/routes.py, templates listados no plan, tests/test_custodian_provisional.py novo, help_service.py, README.md, artifacts — nada além disso; ZERO models/migrations) e preencher a síntese dos Success Criteria (SC-001..SC-007) em Validation Results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato, sem dependências
- **Foundational (T003)**: depende do Setup; BLOQUEIA todas as user stories (gate de reuso — qualquer divergência ⇒ PARAR)
- **US1 (T004–T009)**: após T003 — caminho crítico do MVP (schema → service → rotas → templates, nessa ordem)
- **US2 (T010–T011)**: após US1 completa (T009) — exercita o colaborador provisório nas operações existentes
- **US3 (T012–T013)**: após US2 (mesmos arquivos de service/rotas/form)
- **US4 (T014–T015)**: após US3 (proteções fecham o conjunto)
- **Polish (T016–T020)**: após todas as stories; T019 (manual) pode ocorrer em paralelo com T017–T018

### Within Each User Story

- **Testes são escritos e executados VERMELHOS antes da implementação da story** (TDD — Constitution VIII; lições 005–009)
- Schema antes do service; service antes das rotas; rotas antes dos templates
- Story completa (checkpoint verde) antes de avançar para a próxima prioridade

### Parallel Opportunities

- **T017/T018** ([P]) tocam arquivos distintos entre si e do código — paralelizáveis
- Marcador `[P]` nas tasks de teste (T004/T010/T012/T014) significa apenas **independência de arquivo** (arquivo de testes próprio); os testes de cada story devem ser escritos e validados vermelhos **ANTES** da implementação correspondente — nunca em paralelo com ela (lição da 005)
- Todo o restante é sequencial: as stories compartilham schema/service/rotas/templates

## Parallel Example: User Story 1

```bash
# Dentro da US1 a sequência é estrita (mesmos arquivos, dependência lógica):
T004 (testes vermelhos) → T005 (schema) → T006 (service) → T007 (rotas) → T008 (templates) → T009 (verde + regressão)
# [P] em T004 indica apenas que o arquivo de testes é próprio — não execução concorrente com T005–T008
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fases 1–2 (Setup + Foundational): T001–T003
2. US1 completa: T004–T009 (TDD: vermelho → schema → service → rotas → templates → verde)
3. **STOP and VALIDATE**: cenários 3.1–3.4 do quickstart + suíte sem regressão
4. MVP entregável: cadastro sem matrícula gera `PROV-*` único e marcado

### Incremental Delivery

1. Setup + Foundational → fundação verificada
2. US1 → cadastro provisório (P1)
3. US2 → uso patrimonial sem bloqueios (P1)
4. US3 → substituição pela oficial (P2)
5. US4 → segurança da numeração (P2)
6. Polish → docs (XI), validação manual (T019), fechamento (T020)

---

## Notes

- [P] tasks = different files, no dependencies — nunca concorrência com a implementação da mesma story
- [Story] label maps task to specific user story for traceability
- Cada story é independentemente completável e testável
- Verify tests fail before implementing (obrigatório em T004; T010/T012/T014 confirmam caminhos já implementados ou evidenciam lacunas)
- Zero DDL: nenhuma task altera models ou cria migration (SC-007); nenhuma task altera `movement_service.py`, `inventario_service.py`, `ad_service.py`, `custodian_import_service.py`, auth, RBAC ou permissões
- `PROV-*` nunca é usado como credencial nem derivado de dado pessoal (FR-004/FR-012)
- Stop at any checkpoint to validate story independently
- Commit after each task or logical group — somente se o usuário solicitar

---

## Validation Results

> Preenchido durante a implementação (T002, T003, T004, T009, T011, T013, T015, T016, T019, T020). Não marcar antecipadamente.

### Baseline (T002)

- 2026-09-17: **281 passed / 1 failed** (lockout defasado pré-existente) — patamar registrado, zero regressão esperada.

### Fatos verificados (T003)

- `AssetService.create` (não `create_asset`) — testes corrigidos para a API real.
- Suíte existente usa `follow_redirects=False` ao assertar 303 (TestClient segue redirects por padrão) — testes novos alinhados.
- `AuditLog`: colunas `previous_data`/`new_data`; `ACTION_UPDATE = "ALTERACAO"` (audit_service L28) — usadas nas asserções.
- Rota web de criação redireciona 303 → `/custodians`; edição 303 → própria página.
- Helper `can` precedentado em `_inject_current_user` (context_processors) — `is_provisional` injetado ao lado.

### TDD vermelho (T004)

- 2026-09-17: **24 failed / 2 passed** na 1ª execução (comportamentos novos inexistentes) — vermelho confirmado.

### Execuções por story (T009/T011/T013/T015)

- US1 (T009): verde após implementação (service + schema + rotas + templates). Correção de execução: removida **duplicata do `create()`** no service (resto de edição que sombreava a nova lógica e gravava `registration_code=None`).
- US2 (T011): badge nos templates (`list.html`, `detail.html`, `term.html` via `is_provisional`); helper inline com `len(code)==10` estava errado (PROV-000001 tem 11 chars) — **delegado a `CustodianService.is_provisional`** (fonte única).
- US3 (T013): guard de substituição web OK; correção de **bug if/elif** no `update()` (matrícula informada era ignorada quando igual-check inicial falhava); auditoria testada pelo caminho web real (mecanismo existente `write_change_audit`, I2).
- US4 (T015): anti-fabricação nos 4 caminhos; colisão pré-existente criada direto no modelo (o serviço rejeita PROV-* digitado — prova do FR-005).

### Suíte completa (T016)

- 2026-09-17: **307 passed / 1 failed** (281 baseline + 26 novos; mesma falha de lockout pré-existente). `test_help.py` 9/9.

### Validação manual (T019)

- (em andamento — a completar pelo operador conforme quickstart §3; cenários 3.1–3.10)
- **Achado 1 (2026-09-17, operador)**: na edição de um provisório, digitar `PROV-0000` (malformado, 4 dígitos) era **aceito** — o anti-fabricação só cobria o formato estrito `PROV-\d{6}` — e o registro ficava num estado inválido: sem badge (regex não casa) e com matrícula aparentemente "oficial" disfarçada. **Corrigido**: anti-fabricação agora rejeita QUALQUER valor iniciado por `PROV-` (case-insensitive, todos os caminhos de escrita); `is_provisional` passa a verificar o PREFIXO (malformado continua provisório — com badge e substituível pela oficial, recuperando registros envenenados); `_next_provisional_code` ignora malformados na contagem. 3 testes de regressão novos (g/h/i) — suíte: **310 passed / 1 failed** (mesma falha pré-existente de lockout).

### Fechamento (T020)

- 2026-09-17. Constitution Check: I–XII ✓ (zero DDL/migrations — `git status` sem models; trilha imutável preservada — snapshots não reescritos, testado em T012d; regras novas só no service; nenhuma permissão nova; TDD vermelho por story; docs XI ✓ T017/T018; auditoria mecanismo existente).
- Escopo por `git status --porcelain`: `README.md`, `app/schemas/custodian.py`, `app/services/custodian_service.py`, `app/services/help_service.py`, `app/web/routes.py`, 4 templates (`custodians/list|detail|form.html`, `movements/term.html`), `tests/test_custodian_provisional.py` (novo), `specs/010.../` (artefatos) — nada além. ZERO alterações em models/migrations ✓.
- SC-001 geração automática ✓ (T004a–d) · SC-002 sequência/unicidade ✓ (T004b, T014a/e) · SC-003 marcação visual ✓ (T004c, T008, T011) · SC-004 uso patrimonial sem bloqueios ✓ (T010a–e) · SC-005 substituição preservando vínculos/histórico ✓ (T012a–h) · SC-006 não-regressão ✓ (T004f, T012b/g + suíte 307/1) · SC-007 zero DDL ✓ (gate deste fechamento).
- A1/A2 (analyze) registrados: anti-fabricação reiterada deliberadamente; teste de concorrência prova o caminho determinístico — `UNIQUE` é a garantia final (R5).
