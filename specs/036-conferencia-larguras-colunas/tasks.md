---
description: "Task list for feature implementation"
---

# Tasks: Ajuste Responsivo das Larguras das Colunas na Tabela de Conferência (036)

**Input**: Design documents from `/specs/036-conferencia-larguras-colunas/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ui-contract-tabela-conferencia.md, quickstart.md

**Tests**: NENHUM teste automatizado novo (research R9 — sem infra de teste de UI/D7; criar testes artificiais é proibido pela spec §15). A suíte pytest existente é a proteção de regressão (SC-005/SC-006) e roda em baseline e após a alteração. A validação visual do quickstart (V1–V5) é o aceite da feature, registrada em `validacao.md` (SC-007).

**Organization**: Tasks grouped by user story (US1 desktop → US2 telas menores), seguida de polish/validação final.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: template Jinja2 em `app/web/templates/`, suíte pytest em `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmação do estado atual — nada de infraestrutura nova (stack intocável, Constitution).

- [x] T001 Ler/confirmar a tabela de bens esperados em `app/web/templates/inventarios/detail.html` (linhas ~226–276) e os elementos protegidos do contract §1 (`formBuscar`, `#modalConferir{{ item.id }}`, `tag-badge`, `btn-ghost btn-icon`, condição Jinja do botão) — sem alterar nada (insumo para as tasks seguintes)
- [x] T002 Rodar a suíte de regressão como BASELINE verde antes de qualquer alteração: `python -m pytest tests/ -q` (SC-005; Windows: `.venv\Scripts\python -m pytest tests/ -q`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhuma tarefa fundacional necessária — feature de arquivo único (plan.md/Structure Decision); os pré-requisitos são as T001–T002.

**⚠️ CRITICAL**: T001–T002 concluídas antes de qualquer alteração no template (baseline de regressão precisa existir).

**Checkpoint**: Estado atual confirmado e suíte verde — a implementação pode começar.

---

## Phase 3: User Story 1 - Proporção correta das colunas na conferência (Priority: P1) 🎯 MVP

**Goal**: A tabela de bens esperados exibe Bem e Local esperado dominando a largura; Resultado e Conferir compactas; Tombamento proporcional (C-1/C-4); alinhamento preservado (quickstart V1–V3).

**Independent Test**: abrir `/inventarios/{id}` em desktop e inspecionar visualmente as proporções e alinhamentos (V1/V2/V3 do quickstart).

### Implementation for User Story 1

- [x] T003 [US1] Em `app/web/templates/inventarios/detail.html`: adicionar classe de escopo própria à tabela de bens esperados (ex.: `inv-esperados-table`) e bloco `<style>` embutido no topo do `{% block content %}` com `table-layout: fixed` restrito à classe (research R1/R2; nenhuma regra global — contract §4)
- [x] T004 [US1] Em `app/web/templates/inventarios/detail.html`: inserir `<colgroup>` com as 5 larguras de referência do data-model (Tombamento ~14%, Bem ~30%, Local esperado ~34%, Resultado ~15%, Conferir ~7% — SC-001 indicativo, clarificação Q1) mantendo `table-responsive`, `align-middle` e o `text-end` da coluna de ação (contract §1–§2)
- [x] T005 [US1] Em `app/web/templates/inventarios/detail.html`: adicionar proteções de quebra local na célula Resultado (`overflow-wrap: anywhere` nas linhas auxiliares de observação/metadados) e nos textos de Bem/Local esperado, para badge LOCAL_DIFERENTE com local anexado e textos longos quebrarem DENTRO da coluna sem transbordar (FR-005/research R3/R4)
- [x] T006 [US1] Validar em desktop os cenários V1 (proporção indicativa), V2 (conteúdos longos legíveis: local institucional 35–45 chars em linha única; badge longo não alarga a coluna) e V3 (alinhamento header/conteúdo; link do tombamento e modal de conferir funcionando; inventário encerrado sem espaço vazio desproporcional) do `quickstart.md` — ajustar percentuais finos se o julgamento visual indicar (clarificação Q1), registrando o valor final
- [x] T007 [US1] Rodar a suíte de regressão após a alteração: `python -m pytest tests/ -q` — 100% verde (SC-005/SC-006; `test_conferencia_visual.py` e `test_inventario*.py` exercitam esta página)

**Checkpoint**: US1 entregue — proporção correta em desktop com zero regressão funcional (MVP da feature).

---

## Phase 4: User Story 2 - Usabilidade em telas menores e zoom (Priority: P2)

**Goal**: A tabela se adapta a notebook/tablet/celular e zoom 80%–200% mantendo prioridade de espaço C-3, botão acessível e rolagem restrita ao contêiner (quickstart V4).

**Independent Test**: abrir a mesma tela em larguras menores e níveis de zoom e verificar adaptação/legibilidade (V4 do quickstart).

### Implementation for User Story 2

- [x] T008 [US2] Em `app/web/templates/inventarios/detail.html` (somente se a validação mostrar necessidade — research R2): ajuste responsivo pontual via media query DENTRO do `<style>` escopado (ex.: comportamento das colunas em ≤575px), preservando `table-responsive` como mecanismo primário e a prioridade C-3 (Bem > Local esperado > Tombamento > Resultado > Conferir)
- [x] T009 [US2] Validar o cenário V4 do `quickstart.md`: desktop médio (768–1399px), tablet (576–767px), celular (<576px) e zoom 80%–200% (clarificação Q3) — sem overflow da página, rolagem restrita ao contêiner da tabela, botão de conferir acessível, nada sobreposto/cortado; temas claro e escuro sem diferença de contraste (research R7)

**Checkpoint**: US1 + US2 funcionam independentemente — a alteração visual está completa.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Não-vazamento de escopo, registro formal e revisão final (Constitution I/XI/XII).

- [x] T010 Validar o cenário V5 do `quickstart.md` (contract §4–§5): tabelas dos cards "Conflitos offline" e de coletas offline visualmente idênticas ao estado anterior; outra tela com tabela inalterada; `git diff` contendo APENAS `app/web/templates/inventarios/detail.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`)
- [x] T011 Criar `specs/036-conferencia-larguras-colunas/validacao.md` registrando: baseline + suíte final verde, resultado de cada cenário V1–V5 (com resoluções testadas e nível de zoom), percentuais finais adotados (se ajustados em T006) e quaisquer decisões finas (ex.: truncamento com `title` no badge longo — research R3) (SC-007)
- [x] T012 Revisão final de documentação fiel (Princípio XI): confirmar que README/ajuda não descrevem proporções de coluna (plan Constitution Check XI) — se nada a atualizar, registrar a constatação em `validacao.md`; commit do grupo lógico (template + validação)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato; baseline obrigatório antes de tocar o template
- **US1 (T003–T007)**: depende do Setup; tasks sequenciais no MESMO arquivo (nenhuma [P] — mesma superfície)
- **US2 (T008–T009)**: depende da US1 concluída (refina o que ela produziu)
- **Polish (T010–T012)**: depende de US1+US2

### User Story Dependencies

- **US1 (P1)**: independente — entrega o MVP sozinha (proporção em desktop)
- **US2 (P2)**: refina a US1 em telas menores; não faz sentido sem ela

### Parallel Opportunities

- Nenhuma tarefa marcada [P]: todas operam o mesmo arquivo (`detail.html`) ou dependem do seu estado (validações). O fluxo é estritamente sequencial por design (Princípio I — mudança cirúrgica).

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup (T001–T002, baseline verde)
2. US1 (T003–T007) → **STOP and VALIDATE**: quickstart V1–V3 em desktop + suíte verde
3. Só então US2 para telas menores

### Incremental Delivery

1. US1 → proporção correta no uso principal (desktop)
2. US2 → campo/tablet/celular/zoom
3. Polish → escopo confinado, validação registrada, docs fiéis

---

## Notes

- Mudança exclusivamente de apresentação: nenhuma regra, dado, rota, permissão ou asset estático muda (FR-010/FR-011/FR-012)
- NÃO bumpar versão de `style.css?v=` nem tocar o SW — `detail.html` é server-side, nunca cacheado (research R8)
- Percentuais do colgroup são referência indicativa (clarificação Q1); o aceite final é visual pelo quickstart
- Commit após cada grupo lógico (US1; US2; polish) — mensagens no padrão do repositório
- Evitar: regras CSS globais, alteração nas tabelas vizinhas da mesma página, refatoração não relacionada
