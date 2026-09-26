---
description: "Task list for feature implementation"
---

# Tasks: Ajuste Responsivo da Tabela "Visão Geral do Patrimônio" (046)

**Input**: Design documents from `/specs/046-dashboard-larguras-colunas/`

**Prerequisites**: plan.md (required), spec.md (required), research.md (R1–R10), data-model.md, contracts/ui-contract-tabela-dashboard.md, quickstart.md

**Tests**: **SEM testes novos de UI/pytest** (seção 29 do pedido — R9 do plan): suíte existente como regressão (SC-006) + **script automatizado de medição local** `specs/046-dashboard-larguras-colunas/validar_local.py` (clarificação 2026-09-26; padrão 039/042/044) + registro manual em `validacao.md` (SC-007). Superfície única: `app/web/templates/dashboard.html` — tabela "Fluxo Recente de Movimentações" (L242–291).

**Organization**: Tasks agrupadas por user story (US1 linha única/aproveitamento horizontal → US2 responsividade), precedidas de setup e seguidas de polish. Décima primeira feature da família de larguras — mecanismo reusado das 036–044 (R1/R2 do plan): classe de escopo própria + `table-layout: fixed` + `<colgroup>` único em px + spans ellipsis com tooltip Bootstrap. **Risco específico da 046**: o template contém DUAS tabelas — a tabela "Necessitam de atenção" (L182–200) não pode receber nenhuma regra nova (R5; comprovado pelo script).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: template em `app/web/templates/dashboard.html`; script de validação em `specs/046-dashboard-larguras-colunas/`; `style.css`, rotas, services e assets estáticos **intocados**.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar os fatos de integração e o estado verde de partida; medir o estado V0.

- [x] T001 Confirmar os fatos de integração em `app/web/templates/dashboard.html` — sem alterar nada: tabela-alvo "Fluxo Recente de Movimentações" (L242–291, 7 colunas, `table-responsive` > `table.table.align-middle`), `td` da Data com `text-nowrap` existente, `span.tag-badge` do Tombamento, link do Equipamento (`a.fw-semibold`, `style="color:var(--c-text);"`, `href="/assets/{{ m.asset_id }}"`), badge `.badge-soft-primary` da Ação (`.68rem` inline), if/else do Destino (colaborador com `bi-person` × local/"Estoque" com `bi-geo-alt`), `td.text-end.text-nowrap` das Ações com `{% if m.term_code %}` (par de botões vs. botão único) e a tabela "Necessitam de atenção" (L182–200) que NÃO pode ser afetada; rodar a suíte BASELINE: `python -m pytest tests/ -q` (748 passed esperado)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Baseline de medição V0 — bloqueia as stories (a comparação antes/depois é a evidência central).

**⚠️ CRITICAL**: O script de medição é ferramenta de VALIDAÇÃO (não entra na suíte pytest — R9/seção 29); deve funcionar contra o estado PRÉ-alteração para registrar o baseline.

- [x] T002 Criar `specs/046-dashboard-larguras-colunas/validar_local.py` no padrão das 039/042/044 (R6 — WeasyPrint + TestClient + seed, uso: `python specs/046-dashboard-larguras-colunas/validar_local.py [larguras...]`): renderiza a tela `/` (dois modos: V0 baseline e V1 pós-alteração), mede por coluna da tabela-alvo (largura renderizada em px, quebras de linha por célula, alinhamento thead/tbody, truncamento SEM tooltip, nowrap preservado em Data e Ações) nas larguras de referência (desktop grande ≥1400, desktop médio 768–1399, notebook 1024–1399, tablet 576–767, celular <576) e zoom 80%–200%, **nos temas claro E escuro** (R8); **seed de dados representativo** (`_seed_dados` no padrão da 039): movimentações COM e SEM `term_code` (par vs. botão único nas Ações), destinos por colaborador E por local/"Estoque" (os dois ramos do if/else) e equipamento com nome longo; **verifica a IDENTIDADE da tabela "Necessitam de atenção"** (larguras/quebras idênticas antes e depois — R5); emite relatório comparativo V0/V1 em `validacao_local.out.md` (padrão da família); executar e salvar o baseline V0

**Checkpoint**: Baseline V0 salvo — stories podem começar.

---

## Phase 3: User Story 1 - Linha única e aproveitamento horizontal no Fluxo Recente (Priority: P1) 🎯 MVP

**Goal**: A tabela "Fluxo Recente de Movimentações" ocupa praticamente toda a largura útil do card, com Data, Tombamento, Equipamento, Ação, Destino e Operador em linha única (corte controlado + tooltip quando excedem), Ações compacta e Equipamento/Destino/Operador dominando o espaço (quickstart C-1; FR-001…FR-011).

**Independent Test**: abrir `/` em desktop e medir/inspecionar: aproveitamento da largura (SC-001 ≥95%), quebras por célula (SC-005), tooltips nos valores cortados — comparação com o baseline V0.

### Implementation for User Story 1

- [x] T003 [US1] Em `app/web/templates/dashboard.html`: adicionar classe de escopo própria (ex.: `.dash-table`) **apenas** na tabela de movimentações (L243) e bloco `<style>` embutido no topo do `{% block content %}` com comentário "Feature 046" (sem citar nomes de controles — lição `b75ba99`): `table-layout: fixed; width: 100%; min-width: ~1370px` (conjunto único em px, sem media query de colunas — lição 041) + `<colgroup>` com 7 `<col>` nas larguras de partida do data-model (Data ~135px, Tombamento ~150px, Equipamento ~330px, Ação ~200px, Destino ~330px, Operador ~130px, Ações ~95px — a medir/refinar, C-1); a tabela "Necessitam de atenção" (L182–200) NÃO recebe classe nem regra (R5)
- [x] T004 [US1] Em `app/web/templates/dashboard.html` (colunas rígidas — FR-003/FR-004/FR-006/FR-009): preservar `text-nowrap` da Data e das Ações; garantir nowrap da célula do Tombamento (o `.tag-badge` mantém as regras globais de `style.css` — **sem ellipsis novo**); dimensionar a coluna Ação pelo rótulo real mais longo ("Entrada por Aquisição") com o badge `.badge-soft-primary` íntegro (sem regra global de badge); dimensionar Ações pelo PAR de botões (pior caso com termo), preservando `text-end`, `text-nowrap` e a estrutura condicional `{% if m.term_code %}`
- [x] T005 [US1] Em `app/web/templates/dashboard.html` (colunas textuais com linha garantida — FR-005/FR-007/FR-008): criar classe auxiliar de ellipsis (ex.: `.dash-ellip`: `display:inline-block; max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; vertical-align:bottom`) e aplicar span interno cortável com `data-bs-toggle="tooltip" data-bs-placement="top" title="{{ ... }}"` em: **Equipamento** (span dentro do link existente, preservando `fw-semibold`, `href` e o `style="color:var(--c-text);"`); **Destino** (span interno nos DOIS ramos do if/else — colaborador e local/"Estoque" — com os ícones `bi-person`/`bi-geo-alt` e o fallback "Estoque" FORA do span cortável); **Operador** (span interno na `td.text-muted.small`); sem tooltip em span vazio (R4; mecanismo das 042/043/044 — zero JS novo)
- [x] T006 [US1] Executar `specs/046-dashboard-larguras-colunas/validar_local.py` (V1 — uso: `python specs/046-dashboard-larguras-colunas/validar_local.py [larguras...]`) e refinar as larguras do `<colgroup>` pelo conteúdo real até: tabela ≥95% da largura do card (SC-001), textuais dominando (SC-002), zero quebras indevidas/truncamento sem tooltip/sobreposição em desktop (SC-005), alinhamento thead/tbody íntegro (SC-003) e a tabela "Necessitam de atenção" IDÊNTICA ao baseline (R5); rodar `python -m pytest tests/ -q` (SC-006)

**Checkpoint**: MVP — US1 completa: linha única + aproveitamento horizontal comprovados pelo script; suíte verde; outra tabela intocada.

---

## Phase 4: User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

**Goal**: A tabela continua utilizável em notebook/tablet/celular e zoom 80%–200%: distribuição proporcional, rolagem confinada ao `table-responsive`, controles acessíveis, nenhum conteúdo cortado sem consulta (quickstart C-2; FR-012/FR-014).

**Independent Test**: reduzir a viewport (e variar zoom) e verificar comportamento, alinhamento e acessibilidade dos controles — comparado ao baseline V0 nas mesmas larguras.

### Implementation for User Story 2

- [x] T007 [US2] Em `app/web/templates/dashboard.html`: validar/refinar o comportamento responsivo do `<style>` escopado — `min-width` da tabela com rolagem confinada ao `table-responsive` existente em tablet/celular (sem esconder colunas, sem reduzir fonte, sem comprimir botões — seção 19 do pedido); verificar que os 7 `<col>` mantêm proporções relativas em desktop médio/notebook (sem media query de colunas — lição 041); conferir tooltips funcionando nos valores truncados em todas as larguras e o estado vazio/estrutura condicional de Ações íntegros (FR-009/FR-014)
- [x] T008 [US2] Executar `specs/046-dashboard-larguras-colunas/validar_local.py` nas larguras de tablet/celular e zoom 80%–200% (V1 — uso: `python specs/046-dashboard-larguras-colunas/validar_local.py [larguras...]`) e refinar se necessário: zero overflow da PÁGINA (qualquer rolagem confinada ao contêiner da tabela — SC-004), zero sobreposição/desalinhamento (SC-003), controles clicáveis e acessíveis (AC-13); rodar `python -m pytest tests/ -q` (SC-006)

**Checkpoint**: US1+US2 — tabela responsiva e validada nas larguras do pedido.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Regressão completa, validação formal e commit.

- [x] T009 Rodar a suíte completa: `python -m pytest tests/ -q` — 100% verde (SC-006) e `git diff` coerente com o plan: **somente `app/web/templates/dashboard.html` alterado** (+ arquivos da spec); nenhuma alteração em `style.css`, `routes.py`, `dashboard_service.py`, `base.html`, outras telas (036–045) ou na tabela "Necessitam de atenção"
- [x] T010 Criar `specs/046-dashboard-larguras-colunas/validacao.md` (SC-007): resultado de cada cenário do §28 (desktop grande/médio, notebook, tablet, celular, zoom 80%–200%), comparação antes/depois do script (relatório `validacao_local.out.md` anexado/referenciado), verificação de integridade da tabela "Necessitam de atenção" e das fronteiras de escopo (FR-017) — não inventar resultados
- [x] T011 Marcar tasks concluídas e commit do grupo lógico no padrão do repositório (subject "Feature 046: ..." sem acentos, footer Codebuff)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: imediato; baseline da suíte
- **Foundational (T002)**: bloqueia as stories (baseline V0 é a referência da comparação)
- **US1 (T003–T006)**: depende do Foundational; T003→T004→T005 no template, T006 valida e refina
- **US2 (T007–T008)**: depende da US1 (refina o mesmo `<style>`); valida responsividade
- **Polish (T009–T011)**: depende de tudo

### User Story Dependencies

- **US1 (P1)**: independente após Foundational — entrega a tabela com linha única e largura aproveitada (MVP)
- **US2 (P2)**: complementa a US1 no mesmo arquivo/`<style>`; não faz sentido sem ela

### Parallel Opportunities

- Nenhuma task paralelizável: todas operam sequencialmente no MESMO arquivo (`dashboard.html`) ou dependem do seu estado — coerente com a alteração localizada (C-7); apenas T001 (leitura) e T002 (script novo, arquivo próprio) poderiam ser paralelas entre si

## Implementation Strategy

### MVP First (US1)

1. Setup + Foundational (T001 baseline da suíte, T002 baseline V0)
2. US1 (T003–T006) → **STOP and VALIDATE**: script V1 confirma linha única + largura + escopo; suíte verde
3. Só então US2 (responsividade) e Polish

### Incremental Delivery

1. US1 → tabela desktop com linha única e colgroup estável
2. US2 → comportamento tablet/celular/zoom validado
3. Polish → regressão total, validacao.md com antes/depois, commit

## Notes

- **Uma única superfície**: toda a alteração vive em `dashboard.html` (template) — `style.css`, rotas, services e assets estáticos intocados (R1/FR-012)
- **Duas tabelas no mesmo template**: o seletor do CSS embutido deve ancorar na classe de escopo; a tabela "Necessitam de atenção" deve ficar IDÊNTICA na medição (R5 — risco específico da 046)
- **Linha garantida**: primeiro evitar quebra, depois aproveitar o espaço horizontal; corte controlado SEMPRE com tooltip Bootstrap (clarificação) — nunca texto que desapareça sem consulta (seção 13)
- **Badges intocados**: `.tag-badge` (regras globais de style.css preservadas) e `.badge-soft-primary` (sem regra global nova — dimensionamento pelo rótulo real)
- **Sem `@media print`** (R10 da 043 — tela não-relatório) e **sem nomes de controles em comentários** (lição `b75ba99`)
- **Sem testes pytest novos** (seção 29/R9): suíte como regressão + script de medição local (ferramenta de validação) + registro manual
- Commit após o grupo lógico (US1+US2+polish) — mensagem no padrão do repositório
- Evitar: refatoração de template, alteração de rotas/services/models, regras globais de CSS, media query de colunas, `@media print`, mudança em outras telas
