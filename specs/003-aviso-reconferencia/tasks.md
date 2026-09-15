# Tasks: Aviso de sobrescrita na re-conferência de inventário

**Input**: Design documents from `/specs/003-aviso-reconferencia/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ui-conferencia-contract.md ✅, quickstart.md ✅

**Tests**: INCLUÍDOS — exigidos pela Constitution (Princípio VIII) e definidos no plan.md
(`tests/test_inventario_reconferencia_ui.py`, 8 casos) e no quickstart.md. Escrever cada teste ANTES da
implementação correspondente e confirmar que ele FALHA.

**Organization**: Tarefas agrupadas por user story (US1 alerta nos modais, US2 confirmação no envio,
US3 página de conferência em campo). US1 e US2 alteram o **mesmo arquivo** (`detail.html`) — sequenciais;
US3 altera arquivo distinto (`conferir.html`) — paralelizável com US1/US2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Projeto monolítico existente (plan.md → Structure Decision): templates em `app/web/templates/`,
testes em `tests/`. Nenhum arquivo fora desses locais + README pode ser alterado (spec — fora de escopo).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar contexto e estabelecer baseline verde antes de qualquer alteração.

- [x] T001 Confirmar que o branch ativo é `003-aviso-reconferencia` e que os artefatos de design existem (`specs/003-aviso-reconferencia/plan.md`, `research.md`, `data-model.md`, `contracts/ui-conferencia-contract.md`, `quickstart.md`); revisar o contrato de UI em `contracts/ui-conferencia-contract.md` (textos canônicos) antes de tocar templates
- [x] T002 [P] Executar os testes existentes diretamente relacionados a inventário como **baseline funcional** (não é a suíte completa do projeto — esta será executada na T017): `pytest tests/test_inventario.py -v`. Se houver falha pré-existente, registrar e não corrigir nesta feature — reportar para decisão do responsável (não é escopo desta feature corrigir; Constitution VIII)

**Checkpoint**: Contexto confirmado e baseline verde — nenhum comportamento existente pode regredir.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Arquivo de testes compartilhado por todas as user stories (criado antes de qualquer caso de teste de story, seguindo os padrões de `tests/test_inventario.py` e `tests/conftest.py`).

- [x] T003 Criar `tests/test_inventario_reconferencia_ui.py` com cabeçalho de docstring (propósito: UI de re-conferência; nenhuma alteração de backend) e helpers compartilhados copiando os padrões existentes de `tests/test_inventario.py`: `_make_location(db, name, department)` (via `LocationService.create`), `_make_asset(db, tag, location, name)` (via `AssetService.create`), helper para criar inventário com escopo por local (via `POST /inventarios/new` com `client` autenticado como `testuser`/`teste@1234`, padrão `test_full_inventory_flow_via_web`) e helper para conferir um item (via `POST /inventarios/{inv_id}/conferir/{item_id}` com `data={"result": ..., "observation": ...}`). Nenhum caso de teste ainda — apenas helpers importáveis pela fase de cada story

**Checkpoint**: Infraestrutura de teste pronta — stories podem começar (US3 em paralelo com US1/US2).

---

## Phase 3: User Story 1 — Conferente vê a conferência anterior antes de preencher (Priority: P1) 🎯 MVP

**Goal**: Itens já conferidos exibem, nos modais de `detail.html`, um alerta com conferente anterior,
data/hora e resultado anterior + aviso de substituição; itens `PENDENTE` permanecem idênticos a hoje.

**Independent Test**: Abrir o modal de um item conferido → alerta presente com os dados disponíveis;
abrir o modal de um item pendente → sem alerta. (Cenários A, B e D do quickstart.md; CA-01, CA-02,
CA-03, CA-08.)

### Tests for User Story 1 ⚠️ (escrever primeiro; confirmar que FALHAM)

- [x] T004 [P] [US1] Teste "modal pendente sem alerta": com inventário aberto e item `PENDENTE`, `GET /inventarios/{inv_id}` deve conter `id="modalConferir{item.id}"` e **não** conter, dentro do modal, "Resultado anterior" nem "substituirá" (CA-01) — `tests/test_inventario_reconferencia_ui.py`
- [x] T005 [P] [US1] Teste "modal conferido com alerta": após conferir um item (ex.: `ENCONTRADO`), a página do inventário deve exibir, no modal do item, "Já conferido por testuser", a data no formato `%d/%m/%Y %H:%M`, "Resultado anterior: Encontrado" e "substituirá" (CA-02, CA-03) — `tests/test_inventario_reconferencia_ui.py`
- [x] T006 [P] [US1] Teste "alerta sem dados históricos": com item ≠ `PENDENTE` e `checked_by_name=None`/`checked_at=None` no banco (via `db_session` direto, simulando `SET NULL`), o modal **não** deve conter "Já conferido por" nem placeholders inventados, mantendo "Resultado anterior: …" e o aviso de substituição (CA-08) — `tests/test_inventario_reconferencia_ui.py`

### Implementation for User Story 1

- [x] T007 [US1] Em `app/web/templates/inventarios/detail.html`, dentro do bloco `modal-body` de `#modalConferir{{ item.id }}` (loop `{% for item in expected_itens %}`), inserir **acima** do bloco "Local cadastrado…" um `{% if item.status.value != 'PENDENTE' %}` com `alert alert-warning small` contendo, conforme `contracts/ui-conferencia-contract.md` §1.2: frase "Já conferido{% if item.checked_by_name %} por {{ item.checked_by_name }}{% endif %}{% if item.checked_at %} em {{ item.checked_at.strftime('%d/%m/%Y %H:%M') }}{% endif %}."; linha "Resultado anterior: {{ item.status.label }}."; aviso "Registrar um novo resultado **substituirá** o resultado anterior." — cada trecho com guard, nada inventado (FR-002..FR-005). Depende de T004–T006 (falhando) e do mesmo arquivo de T010
- [x] T008 [US1] Validar US1: `pytest tests/test_inventario_reconferencia_ui.py -v` verde + executar cenários A, B e D do `quickstart.md` §2 manualmente (ou registrar evidência de execução dos testes como substituto do manual)

**Checkpoint**: US1 funcional e testável isoladamente — alerta visível, pendentes intocados. `detail.html` ainda sem confirmação (US2).

---

## Phase 4: User Story 2 — Sobrescrita exige confirmação explícita no envio (Priority: P1)

**Goal**: O envio do formulário de um item já conferido, nos modais de `detail.html`, passa pelo diálogo
de confirmação; Cancelar = 0 requisições; Continuar = POST normal pela rota existente.

**Independent Test**: Submeter o modal de um item conferido → diálogo com o texto canônico; Cancelar
(nada enviada); Continuar (gravação normal). (Cenário C do quickstart.md; CA-04, CA-05, CA-06; CA-01
para a ausência em pendentes.)

### Tests for User Story 2 ⚠️ (escrever primeiro; confirmar que FALHAM)

- [x] T009 [P] [US2] Teste "onsubmit condicional": no HTML da página do inventário, o `<form` do modal de item conferido deve conter `onsubmit="return confirm('Este item já foi conferido. Registrar um novo resultado vai substituir o anterior. Continuar?')"` (texto exato do contrato §1.4) e o `<form` do modal de item `PENDENTE` **não** deve conter `onsubmit` (CA-01, CA-04) — `tests/test_inventario_reconferencia_ui.py`
- [x] T010 [P] [US2] Teste "re-conferência continua gravando": `POST /inventarios/{inv_id}/conferir/{item_id}` de um item já conferido responde 303 e o item recebe o novo resultado (regressão do CA-06; espelha `test_full_inventory_flow_via_web`) — `tests/test_inventario_reconferencia_ui.py`

### Implementation for User Story 2

- [x] T011 [US2] Em `app/web/templates/inventarios/detail.html`, tornar o atributo `onsubmit` do `<form>` do modal **condicional server-side**: para `item.status.value != 'PENDENTE'` emitir `onsubmit="return confirm('Este item já foi conferido. Registrar um novo resultado vai substituir o anterior. Continuar?')"`; para `PENDENTE` emitir o `<form>` sem o atributo, preservando o comportamento funcional atual. Mecanismo e rationale: research.md R2. Depende de T009–T010 (falhando) e de T007 (mesmo bloco de modal)
- [x] T012 [US2] Validar US2: testes verdes + executar cenário C do `quickstart.md` §2 (confirmar → 303; cancelar → 0 requisições na aba Network, formulário preservado)

**Checkpoint**: US1 + US2 completos — sobrescrita nos modais é visível e deliberada. MVP do briefing atingido.

---

## Phase 5: User Story 3 — Página de conferência em campo informa quem conferiu antes (Priority: P2)

**Goal**: O alerta existente de `conferir.html` é complementado com conferente anterior, data/hora e
resultado anterior (quando disponíveis); sem refatoração e sem confirmação no envio (research.md R1).

**Independent Test**: Abrir `GET /inventarios/{inv_id}/conferir/{asset_id}` de um item conferido →
alerta existente + complemento; item pendente → apresentação atual. (Cenário E do quickstart.md; US3.)

### Tests for User Story 3 ⚠️ (escrever primeiro; confirmar que FALHAM)

- [x] T013 [P] [US3] Teste "página de conferência complementada": para item conferido, `GET /inventarios/{inv_id}/conferir/{asset_id}` deve manter o alerta existente ("Resultado já registrado:" e "pode ser atualizado abaixo") e conter "Conferido por testuser" + data `%d/%m/%Y %H:%M`; para item `PENDENTE`, a página contém "Pendente de conferência" e **não** contém "Resultado já registrado" (CA-08 também se aplica: omitir trechos ausentes) — `tests/test_inventario_reconferencia_ui.py`

### Implementation for User Story 3

- [x] T014 [US3] Em `app/web/templates/inventarios/conferir.html`, dentro do `{% else %}` do alerta `alert alert-info` existente ("Resultado já registrado: …"), acrescentar linha condicional "Conferido por {% if item.checked_by_name %}{{ item.checked_by_name }}{% endif %}{% if item.checked_at %} em {{ item.checked_at.strftime('%d/%m/%Y %H:%M') }}{% endif %}." com guards por campo; **não alterar** mais nada da página (sem `confirm()` — R1; sem refatoração — FR-009). Depende de T013 (falhando)
- [x] T015 [US3] Validar US3: testes verdes + executar cenário E do `quickstart.md` §2

**Checkpoint**: Todos os caminhos de conferência informam a conferência anterior.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentação, regressão total e verificação de escopo.

- [x] T016 [P] Atualizar `README.md` (seção "3. 📋 Inventário Patrimonial", linha da conferência em campo): acrescentar menção fiel ao comportamento — itens já conferidos exibem quem conferiu antes e exigem confirmação antes de sobrescrever, enquanto o inventário estiver aberto (Constitution XI; texto curto, sem inventar comportamento)
- [x] T017 Executar o protocolo completo do `quickstart.md` §2 (cenários A–F, incluindo F — inventário `ENCERRADO` intocado) e §3 (suíte nova + `pytest tests/test_inventario.py -v` + suíte completa `pytest`)
- [x] T018 Verificação final de escopo e conformidade: `git diff` contém **apenas** `app/web/templates/inventarios/detail.html`, `app/web/templates/inventarios/conferir.html`, `tests/test_inventario_reconferencia_ui.py` e `README.md`; zero alteração de rotas/services/models/banco/permissões/auditoria (CA-09); preencher mentalmente o checklist de conformidade da Constitution — resultado registrado no relatório da tarefa. **Se `git diff` ou `git status` identificar qualquer alteração fora dos quatro arquivos permitidos, PARAR e não corrigir/remover automaticamente essa alteração** (proibido usar `git restore`, `git checkout`, `git reset`, `git clean` ou equivalentes): a alteração pode ser legítima, feita pelo responsável em outra máquina — reportá-la para decisão do responsável

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: imediato, sem dependências
- **Foundational (Phase 2)**: depende do baseline verde (T002); cria o arquivo de testes compartilhado (T003) — BLOQUEIA todas as stories
- **US1 (Phase 3)** → **US2 (Phase 4)**: sequenciais — **mesmo arquivo** (`detail.html`), mesmo bloco de modal
- **US3 (Phase 5)**: independente de US1/US2 (arquivo distinto, `conferir.html`) — pode rodar em paralelo após Phase 2
- **Polish (Phase 6)**: depende de US1+US2+US3 completos

### User Story Dependencies

- **US1 (P1)**: após T003; não depende de outras stories
- **US2 (P1)**: os testes (T009–T010) podem ser escritos antecipadamente após T003, mas a implementação (T011) somente começa após T007/T008 (implementação/validação da US1 concluídas), pois US1 e US2 alteram o mesmo bloco de `detail.html`
- **US3 (P2)**: após T003; pode rodar em paralelo com US1/US2 (arquivo distinto)

### Within Each User Story

- Testes primeiro (T004–T006 / T009–T010 / T013), confirmar FALHA
- Implementação (T007 / T011 / T014)
- Validação da story (T008 / T012 / T015) antes de avançar

### Parallel Opportunities

- T002 pode rodar em paralelo com T001
- T004, T005, T006 (US1, mesmos casos de teste em arquivo único — escrever juntos)
- **US3 inteira em paralelo com US1→US2** (arquivos distintos)
- T016 em paralelo com qualquer story (arquivo distinto), desde que o comportamento final já esteja decidido (é)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (T001–T002) → Phase 2 (T003)
2. Phase 3: US1 (T004–T008)
3. **STOP and VALIDATE**: cenários A, B, D do quickstart — o risco de sobrescrita silenciosa já está eliminado na percepção do usuário (alerta), mesmo antes da confirmação
4. US2 completa a barreira deliberada; US3 fecha a consistência entre os dois caminhos

### Incremental Delivery

1. Setup + Foundational → base de testes pronta
2. US1 → validar → alerta visível (MVP)
3. US2 → validar → confirmação no envio (comportamento final dos modais)
4. US3 → validar → consistência da página em campo
5. Polish → README + validação total + verificação de escopo

### Notes

- [P] tasks = diferentes arquivos, sem dependências
- [Story] label mapeia para as US da spec (rastreabilidade com CA-01..CA-09 via tabela da spec)
- `confirm()` é client-side: o TestClient valida a **presença e o texto exato** do atributo; o comportamento de cancelamento (0 requisições) é validado no cenário manual C
- Nenhuma tarefa altera backend — se uma implementação "precisar" tocar rota/service/model, a spec foi mal compreendida: PARAR e re-ler research.md R3
- Commit após cada story validada (mensagem no padrão do repositório)
