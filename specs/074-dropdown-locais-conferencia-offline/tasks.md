# Tasks: Dropdown de Locais Cadastrados na Conferência Offline

**Input**: Design documents from `/specs/074-dropdown-locais-conferencia-offline/`

**Prerequisites**: plan.md, spec.md, research.md (diagnóstico FR-013 + decisões D1–D8), data-model.md, contracts/offline-package-locations-contract.md, quickstart.md

**Tests**: **Incluídos** — exigidos pela Constitution VIII (Princípio VIII) e pelo quickstart.md (Cenários A–J). Convencção: escrever o teste primeiro e confirmar que falha antes da implementação.

**Organization**: Tarefas organizadas por user story (spec.md). **Dependência especial**: US1 (dropdown) e US2 (atualização) consomem a extensão `locations` do pacote (Foundational, Phase 2) — por isso ela bloqueia todas as stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizável (arquivos diferentes, sem dependências entre tarefas incompletas)
- **[Story]**: US1/US2/US3 conforme spec.md

## Path Conventions

Projeto único web app (ver plan.md §Project Structure): `app/` e `tests/` na raiz do repositório.

---

## Phase 1: Setup

**Purpose**: Baseline de regressão antes de qualquer alteração (Constitution VIII)

- [X] T001 Executar a suíte completa `pytest -q` na raiz do repositório e registrar o resultado como baseline verde obrigatório (nenhuma falha aceitável pré-existente)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extensão aditiva do pacote offline com o catálogo de locais — bloqueia TODAS as user stories (é a fonte de dados do dropdown e do ciclo de atualização)

**⚠️ CRITICAL**: Nenhuma tarefa de story pode começar antes desta fase

- [X] T002 [P] Teste de contrato do pacote em `tests/test_dropdown_locais_offline_074.py`: `POST /api/v1/inventarios/{id}/offline/package` (permissão `inventario.conferir`) devolve campo `locations` como `Array<{id: int, name: string}>` contendo **todos** os locais cadastrados, ordenados por `branch, department, name` (mesma ordem de `LocationService.get_all`), sem campos além de `id`/`name` (contrato §1) — confirmar que FALHA antes de T003
- [X] T003 Estender `InventarioOfflineService.generate_package` em `app/services/inventario_offline_service.py` para incluir `"locations"` no payload, obtido via `LocationService.get_all(db)` com projeção mínima `{"id": loc.id, "name": loc.name}` (adição sem quebra; nenhum outro método alterado)
- [X] T004 [P] Teste de retrocompatibilidade do cliente em `tests/test_dropdown_locais_offline_074.py`: payload de pacote **antigo** (JSON sem `locations`) é aceito pelo fluxo de persistência e classificado como "lista indisponível" (contrato §2). Implementar como **teste estático** do template/JS (precedente: `tests/test_sw_service_worker.py` e `tests/test_acessibilidade_estatica_069.py`): o template de `app/web/templates/inventarios/offline.html` contém o branch que trata `pkg.locations` ausente, com mensagem de reconectar/re-preparar e sem opções inventadas — confirmar que FALHA antes das tarefas de UI

**Checkpoint**: Pacote carrega o catálogo — stories podem iniciar

---

## Phase 3: User Story 1 - Seleção do local por dropdown sem rede (Priority: P1) 🎯 MVP

**Goal**: O conferente escolhe o local em `<select>` (padrão `form-select` do online), 100% offline, sem texto livre

**Independent Test**: Com pacote preparado e dispositivo sem rede, abrir `/inventarios/{id}/offline`, marcar 🟡 e concluir a seleção sem nenhuma requisição de rede (DevTools Network vazio)

### Tests for User Story 1

- [X] T005 [P] [US1] Teste estático do template em `tests/test_dropdown_locais_offline_074.py`: em `app/web/templates/inventarios/offline.html`, o modal de coleta possui `<select id="mFoundLocationId" class="form-select form-select-sm">` com `<label for="mFoundLocationId">` associado e **não possui** mais `<input type="text" id="mFoundLocationName">` (FR-001/RNF-004, regressão 069) — confirmar que FALHA antes de T007
- [X] T006 [P] [US1] Teste dos estados de lista em `tests/test_dropdown_locais_offline_074.py`: quando `pkg.locations` está ausente → mensagem de "reconecte e prepare a coleta offline"; quando presente e vazio → "nenhum local cadastrado"; em ambos, o registro `LOCAL_DIFERENTE` fica bloqueado (FR-004/FR-010/SC-006, D7) — confirmar que FALHA antes de T008

### Implementation for User Story 1

- [X] T007 [US1] Trocar o input de texto por `<select>` em `app/web/templates/inventarios/offline.html`: popular as options a partir de `pkg.locations` (value=`id`, texto=`name`), opção vazia "Selecione o local…", mantendo a exibição do campo **apenas** quando o resultado é `LOCAL_DIFERENTE` (comportamento atual) e o padrão visual Bootstrap 5 do online (`detail.html` → `modalloc-*`)
- [X] T008 [US1] Implementar os estados D7 em `app/web/templates/inventarios/offline.html`: `locations` ausente/pacote inexistente → orientação "reconecte e re-prepare a coleta offline"; `locations: []` → "nenhum local cadastrado no sistema"; em ambos o submit de `LOCAL_DIFERENTE` é bloqueado com alerta claro — **sem texto livre, sem opções inventadas, sem seleção automática**. **Escopo delimitado (anti-duplicação com T013)**: aqui apenas os estados de **ausência** de lista; a exigência de escolha no dropdown quando a lista **está disponível** é T013

**Checkpoint**: US1 funcional e testável offline de ponta a ponta (MVP)

---

## Phase 4: User Story 2 - Disponibilização e atualização da lista de locais (Priority: P2)

**Goal**: A lista segue o ciclo existente do inventário (preparar/re-preparar), preservada em falha de rede, sem duplicações e sem rotina nova

**Independent Test**: Re-preparar o pacote online e confirmar que `locations` no IndexedDB reflete o cadastro atual; bloquear a rede durante o re-preparo e confirmar que o pacote anterior permanece utilizável

### Tests for User Story 2

- [X] T009 [P] [US2] Testes de atualização em `tests/test_dropdown_locais_offline_074.py`: (a) re-preparo gera novo payload com `locations` consistente com o cadastro (substituição atômica, contrato §1); (b) `InventarioOfflineService.generate_package` é somente-leitura sobre o cadastro (nenhum write em `locations` — FR-005/FR-003); (c) fluxo cliente `prepareFromDetail` em `app/web/static/js/inventario_offline.js` persiste via `savePackage` **somente** após resposta OK do fetch (falha de rede preserva o pacote anterior — SC-005) — teste estático do arquivo JS

**Checkpoint**: US2 comprovada — ciclo de atualização e preservação em falha verificados

---

## Phase 5: User Story 3 - Persistência e sincronização da seleção (Priority: P3)

**Goal**: A seleção grava `found_location_id` no registro da conferência offline e sincroniza pelo mecanismo existente, com validação no servidor e compatibilidade com registros antigos

**Independent Test**: Registrar coleta `LOCAL_DIFERENTE` com local selecionado, reabrir a tela (seleção refletida no painel de coletas), reconectar e sincronizar — item aceito com o local correto no servidor

### Tests for User Story 3

- [X] T010 [P] [US3] Teste de sync com id em `tests/test_dropdown_locais_offline_074.py`: `POST /api/v1/inventarios/{id}/offline/sync` com operação `CHECK`/`LOCAL_DIFERENTE` e `found_location_id` válido é **aceita** e o `InventarioItem` resultante tem `found_location_id` correto e `found_location_name` snapshot (usa padrões de `tests/test_inventario_offline.py`). **Incluir asserção de FR-009 (Constitution IV)**: após o sync aceito, o `Asset` correspondente permanece com o `location_id` **cadastral inalterado** e nenhuma movimentação é criada — a divergência é apenas registrada — confirmar que FALHA antes de T013
- [X] T011 [P] [US3] Testes de integridade/retrocompat em `tests/test_dropdown_locais_offline_074.py`: (a) `found_location_id` inexistente → rejeição estável `local_inexistente` **preservando** a coleta; (b) coleta antiga só com `found_location_name` (nome único) continua aceita pelo servidor (FR-012/SC-007); (c) `LOCAL_DIFERENTE` sem local resolvido → rejeição `local_nao_resolvido` sem descarte

### Implementation for User Story 3

- [X] T012 [US3] Gravar a seleção na coleta em `app/web/templates/inventarios/offline.html`: ao registrar `LOCAL_DIFERENTE`, enviar `found_location_id` (value do `<select>`) e `found_location_name` (nome exibido, snapshot de apresentação) via `InventarioOffline.registrarColeta` — sem alterar `app/web/static/js/inventario_offline.js` (já persiste e já envia os dois campos)
- [X] T013 [US3] Confirmar/ajustar o bloqueio de submissão sem seleção em `app/web/templates/inventarios/offline.html` quando `LOCAL_DIFERENTE` e lista disponível: exigir escolha no dropdown (nada de valor arbitrário), integrando com o estado vazio de T008

**Checkpoint**: Todas as stories funcionais e sincronizando

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Propagação do cache, documentação fiel, acessibilidade e validação final

- [X] T014 [P] Atualizar `app/web/static/js/sw.js`: `CACHE_VERSION` de `inventario-offline-v34` para `inventario-offline-v35` (shell offline e `inventario_offline.js` são servidos cache-first e precisam propagar a atualização aos dispositivos)
- [X] T015 [P] Atualizar a central de ajuda em `app/services/help_service.py` (texto da conferência, ≈ L709): "informe o Local onde foi encontrado" → linguagem de seleção em lista/dropdown (Constitution XI)
- [X] T016 [P] Regressão de acessibilidade: executar `pytest -q tests/test_acessibilidade_estatica_069.py` e garantir que a nova página offline (`/offline`) continua sem controles sem nome (label/for + id únicos)
- [X] T017 Executar a suíte completa `pytest -q` (0 falhas — SC-008) e os Cenários A–J do `quickstart.md`; conferir `git diff --stat` contendo apenas os 5 arquivos previstos em plan.md (SC-009)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — baseline imediato
- **Foundational (Phase 2)**: depende do Phase 1 — **bloqueia todas as stories**
- **US1 (Phase 3)**: depende do Foundational; **também depende do contrato `locations`** (T002–T003)
- **US2 (Phase 4)**: depende do Foundational; independente das demais stories
- **US3 (Phase 5)**: depende do Foundational; a gravação do id (T012) usa o `<select>` da US1 (T007) — se implementada sem US1, cai no caminho legado de nome
- **Polish (Phase 6)**: depende das stories desejadas; T014–T016 paralelizáveis

### User Story Dependencies

- **US1 (P1)**: após Foundational — sem dependência de outras stories para o contrato (T002–T003)
- **US2 (P2)**: após Foundational — independente
- **US3 (P3)**: após Foundational; integra com o `<select>` da US1 quando presente (T013 depende de T007)

### Within Each User Story

- Testes escritos e **falhando** antes da implementação (T002→T003; T005/T006→T007/T008; T010/T011→T012/T013)
- Template antes da lógica de submit; bloqueio antes da gravação
- Story completa antes de migrar para a próxima prioridade

### Parallel Opportunities

- T002 e T004 (arquivos de teste distintos por contexto) + T001
- T005 e T006 (mesmo arquivo de teste, blocos distintos)
- T010 e T011 (blocos distintos do mesmo arquivo de teste)
- T014, T015 e T016 (arquivos distintos)
- Stories paralelas em equipe: US1 × US2 após Foundational

---

## Parallel Example: User Story 1

```bash
# Lançar juntos os testes da US1 (arquivo tests/test_dropdown_locais_offline_074.py, blocos distintos):
Task: "T005 Teste estático do <select> e label associado"
Task: "T006 Teste dos estados lista indisponível/vazia"

# Depois, a implementação (mesmo template, sequencial):
Task: "T007 Trocar input por <select> populado de pkg.locations"
Task: "T008 Estados D7 + bloqueio de registro"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: baseline verde (T001)
2. Phase 2: `locations` no pacote (T002–T004) — **CRÍTICO**
3. Phase 3: dropdown offline (T005–T008)
4. **PARAR E VALIDAR**: Cenários A/B/E/F do quickstart + `pytest -q`

### Incremental Delivery

1. Setup + Foundational → fundação pronta
2. + US1 → validação independente → **MVP entregável** (valor real: fim da digitação manual)
3. + US2 → prova de atualização/preservação (Cenários E/J)
4. + US3 → persistência e sync de ponta a ponta (Cenários C/D/G/H/I)
5. Polish → cache v35, ajuda, acessibilidade, suíte 100% (SC-008/SC-009)

---

## Notes

- Cada tarefa é executável por um LLM/agente sem contexto adicional: arquivo exato, formato verbatim (`{"id", "name"}`), constraint citada (`name` unique → sem homônimos) e critério de falha prévia dos testes.
- Nenhum teste existente pode ser removido/enfraquecido (Constitution VIII); alterações pontuais de asserção só se justificarem por mudança prevista na spec — caso contrário, registrar em relatório.
- Nenhuma task toca: `app/models/*`, `migrations/*`, `app/api/inventario_offline_api.py`, `app/services/inventario_service.py`, `app/web/routers/inventario.py`, templates da Conferência Online (SC-009).
