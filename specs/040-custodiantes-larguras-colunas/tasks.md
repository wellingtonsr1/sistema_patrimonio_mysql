---
description: "Task list for feature implementation"
---

# Tasks: Ajuste Responsivo da Tabela "Colaboradores & Custodiantes" (040)

**Input**: Design documents from `/specs/040-custodiantes-larguras-colunas/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ui-contract-tabela-custodiantes.md, quickstart.md

**Tests**: NENHUM teste automatizado novo (seções 22/27 do pedido — sem testes artificiais; padrão 036–039). Suíte pytest existente como regressão (SC-006): baseline antes, focado durante, completo depois. Validação visual do quickstart (V0–V5) é o aceite, registrada em `validacao.md` (SC-007).

**Organization**: Tasks grouped by user story (US1 desktop → US2 telas menores/zoom), seguida de polish/validação final. Quinta feature da família de ajustes de tabela — mecanismo validado nas 036–039 reusado por decisão das clarificações (C-1/C-5). Especificidades da 040: **texto completo nas textuais** (Nome/Cargo/Departamento/E-mail — sem clamp nem reticências, clarificação da spec, FR-004..007); **Ações com botão "Ver Bens" que tem texto** (coluna mais larga que nas telas anteriores); rígidas em **px com folga** para a Plus Jakarta Sans (lição da 039).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: template Jinja2 em `app/web/templates/`, suíte pytest em `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmação do estado atual — nada de infraestrutura nova (stack intocável, Constitution).

- [x] T001 Ler/confirmar a tabela de colaboradores em `app/web/templates/custodians/list.html` (linhas ~44–86) e os elementos protegidos do contract §1 (`tag-badge` da Matrícula + badge condicional "provisória" com `{% if is_provisional(c.registration_code) %}` e tooltip, link do Nome com `bi-person-circle` → `/custodians/{id}`, badge `badge-soft-gray` do Departamento, pill centralizado de Bens com `active_assets_count`, "Editar Colaborador" com `{% if can('colaboradores.editar') %}` e "Ver Bens" com texto, `text-center` de Bens, `text-end` + `d-flex gap-1 justify-content-end` de Ações, 2 estados vazios) — sem alterar nada
- [x] T002 Rodar a suíte como BASELINE verde: `python -m pytest tests/ -q` (SC-006; Windows: `.venv\Scripts\python -m pytest tests/ -q`) e capturar o baseline "antes" do quickstart V0 (screenshot desktop + medição das 7 colunas) para a comparação da seção 25 do pedido

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhuma tarefa fundacional — feature de arquivo único (plan.md/Structure Decision); pré-requisitos são T001–T002.

**⚠️ CRITICAL**: T001–T002 concluídas antes de qualquer alteração (baseline precisa existir para a comparação antes/depois).

**Checkpoint**: Estado confirmado e baseline capturado — implementação pode começar.

---

## Phase 3: User Story 1 - Aproveitamento horizontal na listagem de colaboradores (Priority: P1) 🎯 MVP

**Goal**: A tabela ocupa praticamente toda a largura útil do card; Nome, Cargo, Departamento e E-mail dominam exibindo o texto completo (sem clamp/ellipsis — clarificação); Matrícula proporcional; Bens e Ações compactas; alinhamento e funcionalidade preservados (quickstart V1–V3).

**Independent Test**: abrir `/custodians` em desktop e inspecionar/medir o aproveitamento e a proporção entre as 7 colunas (comparação com o baseline V0).

### Implementation for User Story 1

- [x] T003 [US1] Em `app/web/templates/custodians/list.html`: adicionar classe de escopo à tabela (ex.: `cust-lista-table`) e bloco `<style>` embutido no topo do `{% block content %}` com `table-layout: fixed; width: 100%; min-width: <medido>` e as larguras por classes `col.cN` no `<colgroup>` (mecanismo das 036–039 — research R2/R3; larguras de partida do data-model: Matrícula ~11 · Nome ~19 · Cargo ~15 · Departamento ~16 · E-mail ~19 · Bens ~8 · Ações ~12, a refinar por medição — C-1); rígidas (Matrícula/Bens/Ações) em px com folga para a Plus Jakarta Sans (lição da 039); nenhuma regra global (contract §4)
- [x] T004 [US1] Em `app/web/templates/custodians/list.html`: adicionar as proteções de quebra validadas nas 036–039 (research R4): `overflow-wrap: break-word` nas células; `white-space: nowrap` no `tag-badge` da Matrícula; **NENHUM clamp/ellipsis/nowrap nas textuais** (Nome/Cargo/Departamento/E-mail exibem texto completo — clarificação, FR-004..007); `white-space: normal` no badge do Departamento (texto completo pode ocupar 2+ linhas); preservar `text-center` de Bens, `text-end` de Ações e todos os IDs/classes funcionais (contract §1–§2)
- [x] T005 [US1] Validar em desktop os cenários V1 (aproveitamento ≥95% e textuais dominando — medição), V2 (conteúdos íntegros: matrícula + badge "provisória" íntegros, nome/cargo/departamento/e-mail completos sem corte, pill de Bens centralizado, 1–2 botões de Ação sem aperto) e V3 (alinhamento 7/7; links e botões funcionando com tooltips — "Editar Colaborador" respeitando `colaboradores.editar`; pesquisa/estados vazios intocados) do `quickstart.md` — refinar as larguras por medição se algum conteúdo estourar/quebrar (C-1), registrando os valores finais e o print antes/depois
- [x] T006 [US1] Rodar a suíte após a alteração (mínimo os arquivos que exercitam a página/domínio): `python -m pytest tests/test_help.py tests/test_custodians_search.py tests/test_custodian_provisional.py -q` e, na sequência, a suíte completa verde (SC-006)

**Checkpoint**: US1 entregue — aproveitamento horizontal correto em desktop com zero regressão (MVP).

---

## Phase 4: User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

**Goal**: A tabela (7 colunas) se adapta a notebook/tablet/celular e zoom 80%–200% mantendo proporções, controles acessíveis e rolagem confinada (quickstart V4).

**Independent Test**: abrir `/custodians` em larguras variadas e níveis de zoom e verificar adaptação, legibilidade e acessibilidade dos controles.

### Implementation for User Story 2

- [x] T007 [US2] Em `app/web/templates/custodians/list.html` (somente se a validação mostrar necessidade — research R6): ajuste responsivo pontual no `<style>` escopado — media query ≤768px para header compacto (padrão 036–039) e/ou refinamento do `min-width` — garantindo: sem cabeçalhos sobrepostos, badges íntegros, "Ver Bens" íntegro, ações acessíveis, rolagem (quando inevitável) confinada ao `table-responsive`; sem reduzir fontes excessivamente (proibição da seção 15 do pedido)
- [x] T008 [US2] Validar o cenário V4 do `quickstart.md`: desktop médio/notebook (768–1399px), tablet (576–767px), celular (<576px) e zoom 80%–200% (precedentes 036–039) — além dos temas claro e escuro (nenhuma diferença de contraste) e dos casos de 1 botão (usuário sem `colaboradores.editar`, se testável)

**Checkpoint**: US1 + US2 funcionam — a alteração visual está completa.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Não-vazamento de escopo, registro formal e revisão final (Constitution I/XI/XII).

- [x] T009 Validar o cenário V5 do `quickstart.md` (contract §4–§5): tabelas da 036 (conferência), 037 (listagem de inventários), 038 (equipamentos) e 039 (movimentações) e demais telas visualmente idênticas; container da tela (page header, botões "Exportar CSV"/"Importar CSV"/"Cadastrar Colaborador", pesquisa, card) inalterado; `git diff` contendo APENAS `app/web/templates/custodians/list.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`)
- [x] T010 Criar `specs/040-custodiantes-larguras-colunas/validacao.md` no formato das 036–039: baseline + suíte final verde, comparação antes/depois (V0), tabela de larguras finais adotadas (com ajustes e motivos), resultado de cada cenário V1–V5 (com medições e nível de zoom), temas, observações preexistentes fora de escopo — incluindo o `max-width:140px` global do `tag-badge` em ≤479px (F3 do analyze: comportamento preexistente, não confundir com regressão) — e decisões finas (ex.: quebra do badge do Departamento) (SC-007)
- [x] T011 Revisão final de documentação fiel (Princípio XI): confirmar que README/ajuda não descrevem larguras da listagem de colaboradores — se nada a atualizar, registrar a constatação em `validacao.md`; marcar tasks concluídas e commit do grupo lógico (template + spec/validação) no padrão do repositório

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

- Nenhuma tarefa marcada [P]: todas operam o mesmo arquivo (`custodians/list.html`) ou dependem do seu estado (validações). Fluxo sequencial por design (Princípio I — mudança cirúrgica), como nas 036–039.

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

- Mudança exclusivamente de apresentação: nenhuma regra, dado, rota, permissão ou asset estático muda (FR-012/FR-013/FR-014)
- NÃO bumpar versão de `style.css?v=` nem tocar o SW — `custodians/list.html` é server-side, nunca cacheado (research R1/R9)
- Larguras NÃO são fixadas pela spec (C-1): partida no data-model, refinamento por medição na implementação (V0 antes/depois)
- Escolha de `table-layout: fixed` justificada na análise (research R2 — C-5)
- **Texto completo nas textuais** (específico da 040): Nome/Cargo/Departamento/E-mail SEM clamp, sem ellipsis, sem nowrap — linhas crescem conforme o conteúdo (clarificação da spec); o `fixed` não trunca aqui porque não há nowrap nas textuais
- Badge "provisória" permanece condicional a `is_provisional` e ao lado da `tag-badge`; "Editar Colaborador" permanece condicional a `colaboradores.editar` — a largura da coluna Ações NÃO depende da permissão (coluna fixa por linhas; research R8)
- Commit após cada grupo lógico (US1; US2; polish) — mensagens no padrão do repositório
- Evitar: regras CSS globais, alteração em pesquisa/estados vazios/container, refatoração não relacionada
