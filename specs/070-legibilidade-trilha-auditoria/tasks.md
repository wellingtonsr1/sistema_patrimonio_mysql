# Tasks: Legibilidade dos Eventos de Alteração Cadastral na Trilha de Fluxo & Movimentações (detalhe do Equipamento) — Feature 070

**Input**: Design documents from `/specs/070-legibilidade-trilha-auditoria/`

**Prerequisites**: plan.md, spec.md (US1/US2/US3 + Clarifications 2026-10-12), research.md (R1–R11), data-model.md, contracts/ (ui-contract.md, preserved-contracts.md), quickstart.md

**Tests**: **SOLICITADOS** — spec FR-010 + research R9 + Constitution VIII exigem testes novos (red→green + guardas). Testes existentes NUNCA são editados.

**Organization**: Tarefas agrupadas por user story para implementação e validação independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizável (arquivos distintos, sem dependência de tarefa incompleta)
- **[Story]**: US1/US2/US3 conforme spec.md
- Caminhos exatos em todas as descrições

## Escopo de arquivos permitido (contrato — `contracts/preserved-contracts.md`)

```text
ALTERAR: app/services/asset_service.py · app/web/routers/assets.py · app/web/templates/assets/detail.html
NOVO:    tests/test_legibilidade_trilha_070.py
PROIBIDO: qualquer outro arquivo (regressão C1–C10 falha a feature)
```

---

## Phase 1: Setup

**Purpose**: Registrar o baseline antes de qualquer mudança (Constitution VIII — comparabilidade).

- [X] T001 Registrar baseline da suíte completa executando `python -m pytest tests/ -q` da raiz do repositório e anotar contagem de aprovados/falhas no topo de `specs/070-legibilidade-trilha-auditoria/validacao.md` (criar o arquivo com cabeçalho da feature, padrão das Specs 063/064) — nenhuma alteração de código

---

## Phase 2: Foundational (Bloqueia todas as user stories)

**Purpose**: Infraestrutura de teste compartilhada — fixtures da casa (SQLite em memória, `client`, `db_session`) que US1/US2/US3 consomem.

**⚠️ CRITICAL**: Nenhum trabalho de user story começa antes desta fase.

- [X] T002 Criar `tests/test_legibilidade_trilha_070.py` com a estrutura do arquivo (docstring de escopo, imports e fixtures de apoio espelhando `tests/test_presentacao_trilha_063.py` e o `_form` de `tests/test_consulta_edicao_bens_067.py`): helpers `_make_asset(...)` (tag `PAT-070xx`, `AssetService.create`), fixture `asset_com_edicao` que (a) cria bem via `AssetService.create(db_session, ...)`, (b) edita via `client.post("/assets/{id}/edit", data=_form(name=...))` com permissões `patrimonio.visualizar`+`patrimonio.editar` no padrão da suíte, e (c) retorna `(asset, evento_audit)` — sem nenhum assert de render ainda

**Checkpoint**: fixtures prontas — histórias podem começar.

---

## Phase 3: User Story 1 - Cartão de alteração cadastral legível na trilha (Priority: P1) 🎯 MVP

**Goal**: O cartão do evento exibe título contextual + resumo `rótulo: ~~anterior~~ → **posterior**` com apenas os campos alterados; JSON completo não é o conteúdo principal.

**Independent Test**: editar um campo em `/assets/{id}/edit`, abrir `/assets/{id}` e verificar título `Alteração cadastral — Nome do bem`, linha do resumo no padrão do painel e ausência do JSON como conteúdo principal.

### Tests for User Story 1 (RED — devem FALHAR antes da implementação) ⚠️

- [X] T003 [P] [US1] Teste RED de campo único em `tests/test_legibilidade_trilha_070.py`: edição de `name` → no HTML da trilha existem `Alteração cadastral — Nome do bem`, o rótulo `Nome do bem`, o valor anterior e o posterior; o objeto JSON completo (todas as chaves do snapshot numa linha) NÃO aparece como conteúdo principal do cartão (fora de `<details>`); executar `python -m pytest tests/test_legibilidade_trilha_070.py -q` e confirmar FALHA
- [X] T004 [P] [US1] Teste RED de vários campos em `tests/test_legibilidade_trilha_070.py`: edição de `name`+`brand`+`supplier` numa única ação → título `Alteração cadastral — Dados do equipamento` e os três rótulos com antes/depois presentes; rótulo de campo NÃO alterado (ex.: `Categoria`) ausente do resumo; confirmar FALHA
- [X] T005 [P] [US1] Teste RED de fallback e campo desconhecido em `tests/test_legibilidade_trilha_070.py`: (a) evento `AuditLog` gravado manualmente com `previous_data`/`new_data` contendo chave fora de `_ASSET_FIELD_LABELS` (ex.: `campo_futuro`) → exibida pelo nome técnico, página 200; (b) evento sem `previous_data`/`new_data` → linha `Descrição:` atual preservada e nenhuma lista de resumo; (c) evento com resumo → a linha `Descrição: Campos alterados` NÃO aparece junto do resumo (M4); confirmar FALHA

### Implementation for User Story 1

- [X] T006 [US1] Implementar em `app/services/asset_service.py` o método somente-leitura `AssetService.get_audit_summary(prev_data, new_data)` conforme `data-model.md` §2/§3 e research R1/R2/R6/R7: usa `changed_fields` (importado, já presente) e `_ASSET_FIELD_LABELS` (reutilizado no lugar); retorna `{"titulo", "mudancas"[], "detalhes"}` com `titulo` = `"Alteração cadastral — <label>"` (1 campo) ou `"Alteração cadastral — Dados do equipamento"` (≥2), `mudancas` ordenadas por rótulo, `label = _ASSET_FIELD_LABELS.get(field, field)`, e as regras: diff vazio → `titulo=None, mudancas=[]`; exatamente um dict → sem resumo (apenas `detalhes=True`); nenhum dict → `None` (sem chave no item)
- [X] T007 [US1] Em `app/web/routers/assets.py`, função `view_asset_detail` (~L478–519): após `timeline = MovementService.get_timeline_for_asset(db, asset_id)` (NÃO modificado), aplicar `AssetService.get_audit_summary` aos itens com `item.get('type') == 'audit'`, gravando o resultado em `item['audit_summary']` apenas quando o helper retornar valor — sem tocar nos itens de movimentação nem em nenhuma outra variável de contexto
- [X] T008 [US1] Em `app/web/templates/assets/detail.html`, dentro do ramo `{% if item.type == 'audit' %}` (L285–321, único ponto editado — M9): adicionar o bloco de título (`item.audit_summary.titulo` quando existir) e a lista de resumo no padrão visual do painel 067 (L238–248: `text-decoration-line-through` + `bi-arrow-right` + `strong`, `—` para `none` — M1–M3, M8); condicionar a linha atual `<strong>Descrição:</strong>` ao caminho sem resumo (M4); executar `python -m pytest tests/test_legibilidade_trilha_070.py -q` → **GREEN** nos testes de US1

**Checkpoint**: US1 funcional e testada de forma independente (MVP entregável — a feature já resolve o problema central).

---

## Phase 4: User Story 2 - Detalhes técnicos expansíveis (Priority: P2)

**Goal**: Controle discreto "Ver detalhes técnicos" recolhido por padrão com o JSON original Antes/Depois, renderização segura e sem quebra de layout.

**Independent Test**: no cartão exibido, `<details>` sem `open`; ao expandir, JSON completo dos dois estados distinguíveis; recolher volta ao tamanho normal.

### Tests for User Story 2 (RED) ⚠️

- [X] T009 [P] [US2] Testes RED de detalhes em `tests/test_legibilidade_trilha_070.py`: (a) cartão com diff contém `<details` SEM atributo `open` e `<summary>` com "Ver detalhes técnicos" (M5); (b) expandindo-se o HTML, `Antes:` e `Depois:` com o JSON completo (`tojson`) de cada estado estão dentro do `<details>` (M6); (c) `<pre` com `white-space:pre-wrap` presente (M7); (d) payload hostil: evento com `<script>alert(1)</script>` em `notes` → literal escapado no HTML, sem `<script>` executável vindo do dado; (e) evento com apenas um estado → `<details>` presente mostrando o estado disponível e SEM resumo de diff (R6.2); confirmar FALHA

### Implementation for User Story 2

- [X] T010 [US2] Em `app/web/templates/assets/detail.html` (ramo de auditoria) + ajuste mínimo em `app/services/asset_service.py`/`app/web/routers/assets.py` se a flag `detalhes` ainda não estiver saindo do helper: implementar o bloco `<details>` do `contracts/ui-contract.md` §1 (`<summary>Ver detalhes técnicos</summary>` + `<pre style="white-space:pre-wrap;word-break:break-word">` com `item.prev_data | tojson(indent=2)` e `item.new_data | tojson(indent=2)` rotulados "Antes:"/"Depois:", presentes apenas quando forem dict); manter autoescape (nunca `|safe` — M6); executar `python -m pytest tests/test_legibilidade_trilha_070.py -q` → **GREEN** em US1+US2

**Checkpoint**: US1 e US2 funcionais de forma independente.

---

## Phase 5: User Story 3 - Preservação integral: demais eventos, painel cadastral e histórico (Priority: P1 — guarda)

**Goal**: Provar que nada além da apresentação mudou: registros byte-a-byte, payload da API idêntico, cartões de movimentação e painel 067 intactos.

**Independent Test**: rodar as guardas e a régua de regressão — tudo verde sem editar nenhum teste existente.

### Guardas (verde-verde: passam ANTES e CONTINUAM passando depois) 

- [X] T011 [P] [US3] Guardas de contrato em `tests/test_legibilidade_trilha_070.py`: (a) não-mutação: snapshot de todos os `AuditLog` do bem antes e depois de `client.get(f"/assets/{id}")` → idênticos byte-a-byte (AC07/C4); (b) payload: `GET /api/v1/assets/{id}/timeline` entrega as mesmas chaves/valores de `MovementService.get_timeline_for_asset` sem enriquecimento (AC16/C2 — `audit_summary` NUNCA presente na API); (c) cartão de movimentação com transferência → Origem/Destino no padrão 063 intacto no HTML (AC11/C6); (d) painel `id="historico-cadastral"` com seus `mudanca.label` 067 intacto (AC11/C5); (e) evento de auditoria sem dados → cartão com `Descrição:` e `Registrado por` como hoje (fallback R6.3)
- [X] T012 [US3] Executar a régua de regressão sem editar arquivos: `python -m pytest tests/test_api.py tests/test_movements.py tests/test_datetime_flows.py tests/test_presentacao_trilha_063.py tests/test_fluxo_global_064.py tests/test_consulta_edicao_bens_067.py -q` → 100% passed (C1/C2/C5/C6/C8); registrar o resultado em `specs/070-legibilidade-trilha-auditoria/validacao.md`
- [X] T013 [US3] Verificação de escopo: `git status --porcelain` deve listar apenas `app/services/asset_service.py`, `app/web/routers/assets.py`, `app/web/templates/assets/detail.html`, `tests/test_legibilidade_trilha_070.py` e `specs/070-legibilidade-trilha-auditoria/`; nenhum arquivo de `migrations/`, `app/models/`, `app/services/movement_service.py`, `app/services/audit_service.py` ou `app/api/` alterado (C9/C10 + spec FR-008) — registrar em `validacao.md`

**Checkpoint**: todas as user stories funcionais e as garantias de integridade provadas.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T014 Executar a suíte completa `python -m pytest tests/ -q` e comparar com o baseline do T001 (quickstart §1): 100% passed, sem teste existente modificado; registrar em `specs/070-legibilidade-trilha-auditoria/validacao.md`
- [X] T015 [P] Smoke visual conforme `quickstart.md` §2 com dados reais (edição de 1 campo, edição de vários, expansão dos detalhes): capturar prints antes/depois da trilha em `specs/070-legibilidade-trilha-auditoria/smoke/` (padrão 062/063) e validar SC-009 (identificação em segundos sem comparar JSON)
- [X] T016 [P] Reconfirmar a central de ajuda (Constitution XI, research R11): busca por "trilha"/"auditoria" em `app/services/` e `app/web/templates/ajuda/` — se algum artigo descrever o formato antigo dos cartões, atualizá-lo; se nenhum (esperado), registrar "não requerida" em `validacao.md`
- [X] T017 Revisão final de escopo e checklist da Constitution: conferir diff restrito aos arquivos permitidos, `localtime` mantido no cartão (C8), nenhum `|safe`, `<details>` sem `open`, rótulos sem duplicação de `_ASSET_FIELD_LABELS`; fechar `validacao.md` com o checklist de conformidade (Escopo/Comportamento/Camadas/Testes/Documentação)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — começa imediatamente
- **Foundational (Phase 2)**: depende do Setup (baseline) — **bloqueia todas as user stories**
- **US1 (Phase 3)**: depende da Foundational; MVP
- **US2 (Phase 4)**: depende da Foundational; integra com US1 no mesmo ramo de template mas é testavelmente independente (controle de expansão)
- **US3 (Phase 5)**: guardas verde-verde podem ser escritas a qualquer momento após a Foundational; T012/T013 só fazem sentido com US1+US2 implementadas (comparam antes/depois)
- **Polish (Phase 6)**: depende das desejadas US1–US3

### Within Each User Story

- Testes RED escritos e **falhando** antes da implementação (T003–T005 → T006–T008; T009 → T010)
- Service (T006) → rota (T007) → template (T008): ordem imposta pelo fluxo de dados (data-model §2)
- História concluída antes de passar à próxima prioridade

### Parallel Opportunities

- T003, T004 e T005 [P] (mesmo arquivo, mas blocos de teste independentes — merge no mesmo arquivo; executar em sequência rápida ou dividir por classes `TestUS1*`)
- T009 [P] em relação às tarefas de implementação de US1 concluídas
- T011 [P] em relação ao restante da Phase 5
- T015 e T016 [P] (smoke × verificação de ajuda)

---

## Parallel Example: User Story 1

```bash
# Juntos (classes independentes no mesmo arquivo novo):
Task: "T003 — teste RED campo único em tests/test_legibilidade_trilha_070.py"
Task: "T004 — teste RED vários campos em tests/test_legibilidade_trilha_070.py"
Task: "T005 — teste RED fallback/desconhecido em tests/test_legibilidade_trilha_070.py"

# Depois, em sequência (cadeia de dados):
Task: "T006 — helper em app/services/asset_service.py"
Task: "T007 — rota em app/web/routers/assets.py"
Task: "T008 — template em app/web/templates/assets/detail.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 + Phase 2 (baseline + fixtures)
2. Phase 3: testes RED → helper → rota → template → GREEN
3. **PARAR E VALIDAR**: editar um bem, conferir o cartão na trilha e rodar as guardas de US3 escritas até aqui — o problema central (legibilidade) já está resolvido

### Incremental Delivery

1. Setup + Foundational → fundação pronta
2. US1 → testada → entregue (MVP — resolve o prompt original)
3. US2 → testada → entregue (detalhes técnicos sob demanda)
4. US3 → guardas + régua → prova de não-regressão
5. Polish → suíte completa, smoke, docs, fechamento

### Escopo mínimo garantido (spec §13)

Zero dependências novas · zero DDL · zero mudança de gravação · zero mudança em `get_timeline_for_asset`/API · zero teste existente editado · diff de template restrito ao ramo `item.type == 'audit'`.
