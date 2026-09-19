---
description: "Task list for feature 025 — documentation-only correction of backup config docs"
---

# Tasks: Correção da Documentação da Configuração de Backup

**Input**: Design documents from `/specs/025-documentacao-config-backup/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md (textos R1–R4), data-model.md (fatos de código), contracts/doc-edit-contract.md (edições E1–E4 fechadas), quickstart.md (validação)

**Tests**: Nenhum teste funcional é criado ou executado — feature exclusivamente documental (spec FR-001; briefing §27/§34). Validação = quickstart.md + verificação de preservação (§36).

**Organization**: Tasks por user story (US1–US5). **Regra transversal**: as únicas edições permitidas são E1–E4 do contrato (`contracts/doc-edit-contract.md` §1) — qualquer outra edição é proibida (§2); divergência código × auditoria 024 → briefing §37 (registrar, não corrigir código; funcional → interromper).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Feature documental: edições SOMENTE em `README.md`, `docs/GUIA_DE_MANUTENCAO.md`, `docs/ARQUITETURA_E_MANUTENCAO.md`; relatório em `specs/025-documentacao-config-backup/relatorio.md`; código (`app/`, `tests/`) apenas lido/verificado.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Estabelecer baseline e condições de verificação

- [x] T001 Registrar baseline: executar `git status --porcelain` e `git diff --stat` e anotar o estado inicial no rascunho do relatório (`specs/025-documentacao-config-backup/relatorio.md`) — condição esperada: limpo fora de `specs/025-…` e `.specify/feature.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Re-verificação do código atual (briefing §24) — BLOQUEIA todas as edições

**⚠️ CRITICAL**: Nenhuma edição de documentação antes deste phase — a doc deve refletir o código ATUAL, não a auditoria antiga

- [x] T002 [P] Re-verificar os fatos de código no estado atual (briefing §24.1–7) e registrar o resultado no relatório: precedência por campo (`app/services/backup_config_service.py:122–185`), `get_effective_config` centralizador (`:106`), fallback de boot + log "mantendo snapshot anterior" (`app/services/backup_scheduler.py:107–124`), tick 30 s (`:64`), renovação por tick (`:790,799`), `auto_enabled` não-nullable (`app/models/backup_config.py:23`) com leitura direta (`backup_config_service.py:155`), defaults `false/daily/02:00/0/30/12/12/0` (`app/config.py:67–87`), retenção via efetiva (`backup_scheduler.py:625–628`); SE qualquer fato divergiu → briefing §37: registrar no relatório, NÃO corrigir código, avaliar documental × funcional (funcional = interromper edições)
- [x] T003 [P] Reler as 4 passagens-alvo citadas no research (R1: `docs/GUIA_DE_MANUTENCAO.md` ~L113; R2: `README.md` ~L972–973; R3: `README.md` ~L994; R4: `docs/ARQUITETURA_E_MANUTENCAO.md` ~L1215) e confirmar que continuam idênticas às citações literais; se alguma mudou, ajustar APENAS a âncora de edição (o texto de correção do contrato permanece)

**Checkpoint**: Fatos confirmados no código atual — edições E1–E4 liberadas

---

## Phase 3: User Story 1 — Corrigir o papel das variáveis de ambiente (AT-1) (Priority: P1) 🎯 MVP

**Goal**: `docs/GUIA_DE_MANUTENCAO.md` deixa de afirmar "fallback da primeira inicialização" e passa a descrever fallback por campo dinâmico + bootstrap de boot (+ particularidade do `auto_enabled` — parte de AT-3 no mesmo trecho)

**Independent Test**: `rg -n "primeira inicialização" docs/GUIA_DE_MANUTENCAO.md` não retorna afirmação sobre `BACKUP_*`; o novo texto confere com `backup_config_service.py:122–185`

### Implementation for User Story 1

- [x] T004 [US1] Aplicar a edição E1 (contrato §1.1) em `docs/GUIA_DE_MANUTENCAO.md` (~L113, seção "Onde ficam as configurações?"): substituir a frase final "as env `BACKUP_*` são fallback da primeira inicialização (service: `backup_config_service.py`)" pelo texto de correção do research R1 — fallback **por campo** durante a resolução da efetiva + **bootstrap/fallback de boot** + particularidade do `auto_enabled` não-nulo; o restante do parágrafo e da seção permanece idêntico *(nota: E1 entrega também a menção da particularidade AT-3 no GUIA — parte do US3; ver contrato §1.1)*

**Checkpoint**: US1 completa — única afirmação factualmente incorreta eliminada (MVP)

---

## Phase 4: User Story 2 — Documentar o fallback de boot do scheduler (AT-2) (Priority: P1)

**Goal**: A precedência documentada no README e no registro técnico do ARQUITETURA passa a incluir o caminho de exceção: falha → mantém snapshot anterior → sem snapshot → bootstrap env/default (como mecanismo de segurança, nunca como 4º nível normal)

**Independent Test**: "fallback de boot" presente em `README.md` e `docs/ARQUITETURA_E_MANUTENCAO.md` com a ordem/condição corretas, conferindo com `backup_scheduler.py:107–124`

### Implementation for User Story 2

- [x] T005 [P] [US2] Aplicar a edição E2 (contrato §1.2) em `README.md` (~L972–973): substituir o parágrafo introdutório da precedência pelo texto do research R2 — fallback por campo (elimina a imprecisão AT-1 do README) + precedência atribuída explicitamente a `get_effective_config()` + parágrafo do **fallback de boot** como exceção de segurança; a tabela das 8 variáveis seguinte permanece IDÊNTICA
- [x] T006 [P] [US2] Aplicar a edição E4 (contrato §1.3) em `docs/ARQUITETURA_E_MANUTENCAO.md` (~L1215): estender o registro do fluxo de configuração com a cláusula do research R4 ("**fallback de boot**: em falha de leitura o scheduler mantém o snapshot anterior ou usa env/default se ainda não houver snapshot"); nada mais na linha/seção é alterado

**Checkpoint**: US2 completa — AT-2 documentado nos dois pontos (README + ARQUITETURA)

---

## Phase 5: User Story 3 — Documentar a particularidade de BACKUP_AUTO_ENABLED (AT-3) (Priority: P1)

**Goal**: A nota da particularidade (campo `auto_enabled` não nulo → env não reconsultada dinamicamente; vale na instalação nova e no fallback de boot) está presente no README, sem propor alteração de modelo ou lógica

**Independent Test**: `rg -n "não nulo" README.md` retorna a nota; o texto confere com `models/backup_config.py:23` + `backup_config_service.py:155`

### Implementation for User Story 3

- [x] T007 [US3] Aplicar a edição E3 (contrato §1.2) em `README.md`: inserir, logo após "Valores inválidos não derrubam o sistema: caem no default seguro com registro no log técnico." (~L994), a nota do research R3 (particularidade de `BACKUP_AUTO_ENABLED` — campo não nulo, instalação nova `false`, fallback de boot); sequencial após T005 (mesmo arquivo) (nota: a parte do AT-3 no GUIA já foi entregue pela E1/T004)

**Checkpoint**: US3 completa — AT-3 documentado no ponto de maior visibilidade

---

## Phase 6: User Story 4 — Consolidar o fluxo completo na documentação (Priority: P1)

**Goal**: As 8 respostas do briefing §38 (onde configuro / onde fica salvo / quem resolve / quem usa / para que serve config.py / dupla fonte? / reiniciar? / quanto tempo? / e se o banco falhar?) estão todas respondíveis apenas com a documentação — sem criar seções novas

**Independent Test**: para cada pergunta do §38, existe local citável na doc editada que responde conforme o código (data-model §2)

### Implementation for User Story 4

- [x] T008 [US4] Mapear as 8 perguntas do briefing §38 → local na documentação editada (leitura de `README.md`, `docs/GUIA_DE_MANUTENCAO.md`, `docs/ARQUITETURA_E_MANUTENCAO.md` — NENHUMA seção nova; as edições E1–E4 devem fechá-las) e registrar o mapa no relatório; se alguma resposta permanecer ausente, NÃO criar edição fora do contrato E1–E4 — registrar como pendência para feature futura (briefing §40); confirmar que nenhuma frase sugere fonte concorrente ou reinício obrigatório

**Checkpoint**: US4 completa — fluxo consolidado sem duplicação

---

## Phase 7: User Story 5 — Validação e relatório final (Priority: P2)

**Goal**: Validação completa (quickstart + preservação §36) e relatório final com os 13 itens do briefing §39

**Independent Test**: executar os comandos do quickstart e conferir o relatório contra o diff real

### Implementation for User Story 5

- [x] T009 [US5] Executar a validação do `specs/025-documentacao-config-backup/quickstart.md` (Passos 1–6: escopo do diff; resquícios AT-1 via `rg -n "primeira inicialização" README.md docs/`; presença AT-2/AT-3 via `rg`; conferência factual dos 5 itens contra o código; preservações; consistência interna entre os 3 docs) e registrar o resultado
- [x] T010 [US5] Verificação de preservação final (briefing §36): `git status`, `git diff --stat`, `git diff` — confirmar alteração SOMENTE em `README.md`, `docs/GUIA_DE_MANUTENCAO.md`, `docs/ARQUITETURA_E_MANUTENCAO.md` (+ specs da feature); qualquer caminho em `app/`, `tests/`, `data/`, `.env` → investigar imediatamente e reverter; confirmar explicitamente que `app/config.py` está ausente do diff — as 8 constantes permanecem preservadas (FR-003)
- [x] T011 [US5] Consolidar o relatório final `specs/025-documentacao-config-backup/relatorio.md` com os 13 itens do briefing §39 (arquivos alterados; correção por arquivo; AT-1/AT-2/AT-3; confirmações: config.py intocado funcionalmente, 8 constantes preservadas, scheduler/service/banco/testes intocados; verificações realizadas; divergências deixadas para feature futura)

**Checkpoint**: US5 completa — entrega validada e documentada

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — inicia imediatamente
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as edições (re-verificação §24 obrigatória)
- **US1 (Phase 3)**: depende da Foundational — E1 em arquivo próprio (GUIA)
- **US2 (Phase 4)**: depende da Foundational — T005 (README) e T006 (ARQUITETURA) paralelizáveis entre si
- **US3 (Phase 5)**: depende de T005 (mesmo arquivo README — sequencial)
- **US4 (Phase 6)**: depende de T004+T005+T006+T007 (mapeia o estado pós-edições)
- **US5 (Phase 7)**: depende de US4 — validação final e relatório

### User Story Dependencies

- **US1 (P1)**: independente (arquivo exclusivo)
- **US2 (P1)**: independente de US1; T005 e T006 em paralelo
- **US3 (P1)**: depende de T005 (mesmo arquivo)
- **US4 (P1)**: consolidação — requer todas as edições prontas
- **US5 (P2)**: última — validação + relatório

### Parallel Opportunities

- T002 + T003 (Foundational) em paralelo
- T005 (README) + T006 (ARQUITETURA) em paralelo (US2)
- T004 (GUIA) poderia paralelizar com T005/T006 se desejado (arquivos distintos), mantida sequencial no MVP por simplicidade de validação

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline)
2. Complete Phase 2: Foundational (re-verificação §24)
3. Complete Phase 3: US1 (E1 — elimina a única afirmação incorreta)
4. **STOP and VALIDATE**: `rg -n "primeira inicialização" docs/GUIA_DE_MANUTENCAO.md` sem afirmação sobre `BACKUP_*`

### Incremental Delivery

1. MVP (US1) → AT-1 corrigido no GUIA
2. +US2 → AT-2 documentado no README e ARQUITETURA
3. +US3 → AT-3 documentado no README
4. +US4 → mapa das 8 respostas do §38 confirmado
5. +US5 → validação completa + relatório final (§39)

### Notes

- **Universo fechado de edições**: apenas E1–E4 (contrato §1); as proibições do contrato §2 prevalecem sobre qualquer melhoria "óbvia" identificada durante a edição
- Textos de correção prontos no research R1–R4 — adaptar no máximo a pontuação/âncora, nunca o conteúdo factual
- A tabela das 8 variáveis do README e as seções de comportamento/catch-up/retenção são INVARIANTES (contrato §1.2)
- Nenhuma execução de aplicação, suíte, migration ou acesso a banco; nenhum commit implícito (decisão do usuário)
