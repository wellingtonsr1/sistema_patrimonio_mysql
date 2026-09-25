---
description: "Task list for feature implementation"
---

# Tasks: Ajuste Responsivo da Tabela "Equipamentos" (038)

**Input**: Design documents from `/specs/038-equipamentos-larguras-colunas/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ui-contract-tabela-equipamentos.md, quickstart.md

**Tests**: NENHUM teste automatizado novo (seções 22/28 do pedido — sem testes artificiais; sem infra de teste de UI, D7 mantido das 035–037). Suíte pytest existente como regressão (SC-006): baseline antes, focado durante, completo depois. Validação visual do quickstart (V0–V5) é o aceite, registrada em `validacao.md` (SC-007).

**Organization**: Tasks grouped by user story (US1 desktop → US2 telas menores/zoom), seguida de polish/validação final. Terceira feature da família de ajustes de tabela — mecanismo validado nas 036/037 reusado por decisão das clarificações (C-1/C-5).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: template Jinja2 em `app/web/templates/`, suíte pytest em `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmação do estado atual — nada de infraestrutura nova (stack intocável, Constitution).

- [x] T001 Ler/confirmar a tabela de equipamentos em `app/web/templates/assets/list.html` (linhas ~133–192) e os elementos protegidos do contract §1 (3 links, `tag-badge`, `status-pill-*` com `::before`, `text-nowrap` de Valor/Ações, botões "Ver Detalhes"/"Movimentar" com tooltip e condição `movimentacao.criar`, fallbacks "Estoque Livre"/"Estoque Central") — sem alterar nada
- [x] T002 Rodar a suíte como BASELINE verde: `python -m pytest tests/ -q` (SC-006; Windows: `.venv\Scripts\python -m pytest tests/ -q`) e capturar o baseline "antes" do quickstart V0 (screenshot desktop + medição das 8 colunas) para a comparação da seção 27 do pedido

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhuma tarefa fundacional — feature de arquivo único (plan.md/Structure Decision); pré-requisitos são T001–T002.

**⚠️ CRITICAL**: T001–T002 concluídas antes de qualquer alteração (baseline precisa existir para a comparação antes/depois).

**Checkpoint**: Estado confirmado e baseline capturado — implementação pode começar.

---

## Phase 3: User Story 1 - Aproveitamento horizontal na listagem de equipamentos (Priority: P1) 🎯 MVP

**Goal**: A tabela ocupa praticamente toda a largura útil do card; Equipamento/Modelo, Responsável e Localização dominam; Tombamento/Categoria proporcionais; Status/Valor/Ações compactas; alinhamento e funcionalidade preservados (quickstart V1–V3).

**Independent Test**: abrir `/assets` em desktop e inspecionar/medir o aproveitamento e a proporção entre as 8 colunas (comparação com o baseline V0).

### Implementation for User Story 1

- [x] T003 [US1] Em `app/web/templates/assets/list.html`: adicionar classe de escopo à tabela (ex.: `assets-lista-table`) e bloco `<style>` embutido no topo do `{% block content %}` com `table-layout: fixed; width: 100%; min-width: <medido>` e as larguras por classes `col.cN` no `<colgroup>` (mechanismo das 036/037 — research R2/R3; larguras de partida do data-model: Tombamento ~11 · Equipamento/Modelo ~24 · Categoria ~9 · Status ~10 · Responsável ~15 · Localização ~19 · Valor ~7 · Ações ~5, a refinar por medição — C-1); nenhuma regra global (contract §4)
- [x] T004 [US1] Em `app/web/templates/assets/list.html`: adicionar as proteções de quebra validadas nas 036/037 (research R4): `overflow-wrap: break-word` nas células; `white-space: nowrap` no `tag-badge` do tombamento (FR-003); **preservar** os `text-nowrap` existentes de Valor e Ações; dimensionar a coluna Status para o rótulo mais longo ("Em Manutenção") caber em 1 linha com o `::before` alinhado (medição; lição da 037 — se impossível sem roubar das textuais, permitir quebra no pill e documentar o ajuste do alinhamento em `validacao.md`); preservar `text-end` de Ações e todos os IDs/classes funcionais (contract §1–§2)
- [x] T005 [US1] Validar em desktop os cenários V1 (aproveitamento ≥95% e textuais dominando — medição), V2 (conteúdos íntegros: tombamento sem truncamento, nome+S/N legíveis, status-pill íntegro, responsável+matrícula, localização longa, valor sem quebra, 1–2 botões de ação) e V3 (alinhamento; 3 links e botões funcionando com tooltips; fallbacks "Estoque Livre"/"Estoque Central"; filtros/contagem intocados) do `quickstart.md` — refinar as larguras por medição se algum conteúdo estourar/quebrar (C-1), registrando os valores finais e o print antes/depois
- [x] T006 [US1] Rodar a suíte após a alteração (mínimo os arquivos que exercitam a página/domínio): `python -m pytest tests/test_assets.py tests/test_movements.py tests/test_navbar.py -q` e, na sequência, a suíte completa verde (SC-006)

**Checkpoint**: US1 entregue — aproveitamento horizontal correto em desktop com zero regressão (MVP).

---

## Phase 4: User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

**Goal**: A tabela (8 colunas) se adapta a notebook/tablet/celular e zoom 80%–200% mantendo proporções, controles acessíveis e rolagem confinada (quickstart V4).

**Independent Test**: abrir `/assets` em larguras variadas e níveis de zoom e verificar adaptação, legibilidade e acessibilidade dos controles.

### Implementation for User Story 2

- [x] T007 [US2] Em `app/web/templates/assets/list.html` (somente se a validação mostrar necessidade — research R6): ajuste responsivo pontual no `<style>` escopado — media query ≤768px para header compacto (padrão 036/037) e/ou refinamento do `min-width` — garantindo: sem cabeçalhos sobrepostos, pills/badges íntegros, valores e botões sem quebra, ações acessíveis, rolagem (quando inevitável) confinada ao `table-responsive`; sem reduzir fontes excessivamente (proibição da seção 17 do pedido)
- [x] T008 [US2] Validar o cenário V4 do `quickstart.md`: desktop médio/notebook (768–1399px), tablet (576–767px), celular (<576px) e zoom 80%–200% (precedentes 036/037) — além dos temas claro e escuro (nenhuma diferença de contraste) e dos casos de 1 botão (usuário sem `movimentacao.criar`, se testável)

**Checkpoint**: US1 + US2 funcionam — a alteração visual está completa.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Não-vazamento de escopo, registro formal e revisão final (Constitution I/XI/XII).

- [x] T009 Validar o cenário V5 do `quickstart.md` (contract §4–§5): tabelas da 036 (conferência) e 037 (listagem de inventários) e demais telas visualmente idênticas; container da tela (page header, filtros, card, contagem) inalterado; `git diff` contendo APENAS `app/web/templates/assets/list.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`)
- [x] T010 Criar `specs/038-equipamentos-larguras-colunas/validacao.md` no formato das 036/037: baseline + suíte final verde, comparação antes/depois (V0), tabela de larguras finais adotadas (com ajustes e motivos), resultado de cada cenário V1–V5 (com medições e nível de zoom), temas, observações preexistentes fora de escopo e decisões finas (ex.: tratamento do status-pill — research R4) (SC-007)
- [x] T011 Revisão final de documentação fiel (Princípio XI): confirmar que README/ajuda não descrevem larguras da listagem de equipamentos — se nada a atualizar, registrar a constatação em `validacao.md`; marcar tasks concluídas e commit do grupo lógico (template + spec/validação) no padrão do repositório

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato; baseline + V0 obrigatórios antes de tocar o template
- **US1 (T003–T006)**: depende do Setup; tasks sequenciais no MESMO arquivo (nenhuma [P])
- **US2 (T007–T008)**: depende da US1 concluída (refina o que ela produziu)
- **Polish (T009–T011)**: depende de US1+US2

### User Story Dependencies

- **US1 (P1)**: independente — entrega o MVP sozinha (aproveitamento horizontal em desktop)
- **US2 (P2)**: refina a US1 em telas menores/zoom; não faz sentido sem ela

### Parallel Opportunities

- Nenhuma tarefa marcada [P]: todas operam o mesmo arquivo (`assets/list.html`) ou dependem do seu estado (validações). Fluxo sequencial por design (Princípio I — mudança cirúrgica), como nas 036/037.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup (T001–T002, baseline + V0)
2. US1 (T003–T006) → **STOP and VALIDATE**: quickstart V1–V3 em desktop + suíte verde
3. Só então US2 para telas menores/zoom

### Incremental Delivery

1. US1 → aproveitamento horizontal correto no uso principal (desktop)
2. US2 → notebook/tablet/celular/zoom/temas
3. Polish → escopo confinado, validação registrada, docs fiéis, commit

---

## Notes

- Mudança exclusivamente de apresentação: nenhuma regra, dado, rota, permissão ou asset estático muda (FR-013/FR-014/FR-015)
- NÃO bumpar versão de `style.css?v=` nem tocar o SW — `assets/list.html` é server-side, nunca cacheado (research R1/R9)
- Larguras NÃO são fixadas pela spec (C-1): partida no data-model, refinamento por medição na implementação (V0 antes/depois)
- Escolha de `table-layout: fixed` justificada na análise (research R2 — C-5)
- Botão "Movimentar" permanece condicional a `movimentacao.criar` — a largura da coluna NÃO depende da permissão (coluna fixa por linhas; research R8)
- Commit após cada grupo lógico (US1; US2; polish) — mensagens no padrão do repositório
- Evitar: regras CSS globais, alteração em filtros/estado vazio/container, refatoração não relacionada
