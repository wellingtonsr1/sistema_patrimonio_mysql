---
description: "Task list for feature implementation"
---

# Tasks: Ajuste Responsivo da Tabela "Etiquetas de Patrimônio" (044)

**Input**: Design documents from `/specs/044-etiquetas-larguras-colunas/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ui-contract-tabela-etiquetas.md, quickstart.md

**Tests**: NENHUM teste automatizado novo (seção 29 do pedido — sem testes artificiais; padrão 036–043). Suíte pytest existente como regressão (SC-006): baseline antes, focado durante, completo depois — **baseline: nenhum teste dedicado à página de etiquetas** (constatado em `tests/`); run focado: `test_help.py` + `test_rbac.py`. Validação visual do quickstart (V0–V5, **com contagem de quebras, conferência de tooltips e da impressão de etiquetas**) é o aceite, registrada em `validacao.md` (SC-007).

**Organization**: Tasks grouped by user story (US1 linha única/aproveitamento → US2 telas menores/zoom), seguida de polish/validação final. Nona feature da família de ajustes de tabela — mecanismo validado nas 036–043 reusado (C-1/C-5). Especificidades da 044: **linha garantida em Equipamento (nome e marca/modelo), Setor e Localização** (nowrap + ellipsis + tooltip Bootstrap — clarificações da spec, FR-005/006/007/011); **Tombamento sem ellipsis novo** (regras globais do `.tag-badge` preservadas — clarificação); **coluna do checkbox estável** (FR-003); **sem badges** nesta tabela (a lição `white-space: normal` da 042/043 não se aplica); **conjunto único de colunas em px** (lição da 041); **sem bloco de impressão** (R10 — tela não-relatório) e **domínio da 013 protegido** (`#labels-print-area`/`.labels-sheet`/`.label-card`, `@media print` de etiquetas em `style.css` e JS de seleção em lote intocados — FR-013/FR-014); rígidas em px com folga para a Plus Jakarta Sans (lições 039/041); comentários CSS não citam controles do header/toolbar/filtros (lição `b75ba99`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: template Jinja2 em `app/web/templates/`, suíte pytest em `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmação do estado atual — nada de infraestrutura nova (stack intocável, Constitution).

- [x] T001 Ler/confirmar a tabela de seleção em `app/web/templates/assets/labels.html` e os elementos protegidos do contract §1 (5 colunas simétricas thead/tbody: `th` do checkbox com `width:36px` inline + `input.form-check-input.asset-check` por linha; Tombamento com `span.tag-badge`; Equipamento com `span.fw-semibold` + `div.text-muted` condicional `{% if a.brand or a.model %}`; Setor `td.small.text-muted` com fallback "—" condicional a `{% if a.location and a.location.department %}`; Localização `td.small.text-muted` com fallback "—" condicional a `{% if a.location %}`) e os domínios vizinhos intocáveis (folha `#labels-print-area` > `.label-card`; JS inline de QRCode e seleção em lote via `?selected=`; contraste de `.asset-check`/`#select-all-page` em `style.css:1595`; `.tag-badge` global em `style.css:491`/`1027`; `@media print` de etiquetas em `style.css:1605–1645`) — sem alterar nada
- [x] T002 Rodar a suíte como BASELINE verde: `python -m pytest tests/ -q` (SC-006; Windows: `.venv\Scripts\python -m pytest tests/ -q`) e capturar o baseline "antes" do quickstart V0 (screenshot desktop + medição das 5 colunas + **contagem de quebras de linha por célula**) para a comparação antes/depois

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhuma tarefa fundacional — feature de arquivo único (plan.md/Structure Decision); pré-requisitos são T001–T002.

**⚠️ CRITICAL**: T001–T002 concluídas antes de qualquer alteração (baseline precisa existir para a comparação antes/depois).

**Checkpoint**: Estado confirmado e baseline capturado — implementação pode começar.

---

## Phase 3: User Story 1 - Linha única e aproveitamento horizontal na seleção de etiquetas (Priority: P1) 🎯 MVP

**Goal**: A tabela ocupa praticamente toda a largura útil do card; Equipamento (nome e marca/modelo), Setor e Localização dominam com **linha garantida** (nowrap + ellipsis + tooltip Bootstrap); Tombamento compacto com o badge íntegro sem ellipsis novo; checkbox mínima e estável; alinhamento e funcionalidade preservados (quickstart V1–V3).

**Independent Test**: abrir `/assets/labels` em desktop e inspecionar/medir o aproveitamento, a linha única e os tooltips (comparação com o baseline V0).

### Implementation for User Story 1

- [x] T003 [US1] Em `app/web/templates/assets/labels.html`: adicionar classe de escopo à tabela de seleção (ex.: `etiq-table`) e bloco `<style>` embutido no topo do `{% block content %}` com comentário de rastreabilidade "Feature 044" (sem citar controles do header/toolbar/filtros — lição `b75ba99`), `table-layout: fixed; width: 100%; min-width: <medido>` e as larguras por classes `col.cN` no `<colgroup>` (mecanismo das 036–043 — research R2/R3; larguras de partida do data-model: checkbox ~46 · Tombamento ~150 · Equipamento ~420 · Setor ~280 · Localização ~334, a refinar por medição — C-1; **conjunto único, sem media query de colunas** — lição da 041; o `width:36px` inline do `th` é absorvido pelo colgroup); rígidas em px com folga para a Plus Jakarta Sans (×1,25–1,30 — lições 039/041); nenhuma regra global em `.table`/`.tag-badge` (contract §5)
- [x] T004 [US1] Em `app/web/templates/assets/labels.html`: implementar o mecanismo de **linha garantida** (research R4 — clarificações, FR-005/006/007/008/011): classe auxiliar de ellipsis (ex.: `.etiq-ellip`: `display:inline-block; max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; vertical-align:bottom`) com `data-bs-toggle="tooltip" data-bs-placement="top" title="{{ ... }}"` no **nome do equipamento** (`span.fw-semibold`), na **linha auxiliar de marca/modelo** (`div.text-muted` — clarificação; sem tooltip em span vazio), no **setor** e na **localização** (fallbacks "—" fora dos spans cortáveis); Tombamento **sem ellipsis novo** — célula nowrap e `.tag-badge` com as regras globais preservadas (clarificação); preservar condições Jinja, classes funcionais (`.asset-check`), estrutura de 2 linhas (C-7), fallbacks e alinhamentos (contract §1–§2)
- [x] T005 [US1] Validar em desktop os cenários V1 (aproveitamento ≥95% e textuais dominando — medição), V2 (**tooltips Bootstrap** com o valor completo em nome/marca-modelo/setor/localização; tombamento completo e legível; fallbacks "—"; checkbox funcional atualizando contagem/folha/URL) e V3 (alinhamento 5/5 incluindo o cabeçalho vazio; altura de linhas uniforme; distribuição estável entre buscas) do `quickstart.md` — refinar as larguras por medição se algum conteúdo estourar/quebrar (C-1), registrando os valores finais e o print antes/depois
- [x] T006 [US1] Rodar a suíte após a alteração (mínimo o run focado): `python -m pytest tests/test_help.py tests/test_rbac.py -q` (baseline: nenhum teste dedicado a `/assets/labels`) e, na sequência, a suíte completa verde (SC-006)

**Checkpoint**: US1 entregue — linha garantida com corte controlado em desktop, tooltips acessíveis e zero regressão (MVP).

---

## Phase 4: User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

**Goal**: A tabela (5 colunas) mantém a leitura prioritariamente horizontal em notebook/tablet/celular e zoom 80%–200%, com rolagem confinada quando inevitável, valores truncados consultáveis e checkboxes acessíveis (quickstart V4).

**Independent Test**: abrir `/assets/labels` em larguras variadas e níveis de zoom e verificar adaptação, legibilidade, tooltips e acessibilidade dos controles.

### Implementation for User Story 2

- [x] T007 [US2] Em `app/web/templates/assets/labels.html` (somente se a validação mostrar necessidade — research R6): ajuste responsivo pontual no `<style>` escopado — **sem media query de colunas** (conjunto único, lição da 041); eventual refinamento do `min-width` garantindo: rolagem horizontal confinada ao `table-responsive` quando a viewport for menor que o mínimo, todas as 5 colunas acessíveis, valores truncados consultáveis via tooltip, sem sobreposição, sem reduzir fontes excessivamente (proibição da seção 23 do pedido); fallback global do `.tag-badge` (≤479.98px) aceitável em viewport muito estreita
- [x] T008 [US2] Validar o cenário V4 do `quickstart.md`: desktop médio/notebook (768–1399px — linha garantida mantida com corte controlado), tablet (576–767px) e celular (<576px — rolagem confinada funcional, checkboxes acessíveis), zoom 80%–200% (precedentes 036–043) — além dos temas claro e escuro (nenhuma diferença de contraste; contraste dos checkboxes intacto)

**Checkpoint**: US1 + US2 funcionam — a alteração visual está completa.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Não-vazamento de escopo, registro formal e revisão final (Constitution I/XI/XII).

- [x] T009 Validar o cenário V5 do `quickstart.md` (contract §5–§6): tabelas das specs 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações), 040 (custodiantes), 041 (Relatório Contábil-Físico), 042 (Trilha de Auditoria) e 043 (Usuários) e demais telas visualmente idênticas; container da tela (page header, filtros, toolbar, contador, estado vazio) inalterado; **impressão de etiquetas idêntica à atual** (selecionar → imprimir: apenas `#labels-print-area`, A4 8mm, etiquetas íntegras — domínio da 013 intocado; tela não-relatório — R10, sem `@media print` novo); JS de seleção em lote funcional; `git diff` contendo APENAS `app/web/templates/assets/labels.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`)
- [x] T010 Criar `specs/044-etiquetas-larguras-colunas/validacao.md` no formato das 036–043: baseline + suíte final verde, comparação antes/depois (V0, **incluindo redução de quebras**), tabela de larguras finais adotadas (com ajustes e motivos), resultado de cada cenário V1–V5 (com medições, zoom, **verificação de tooltips** e **conferência da impressão de etiquetas**), temas, observações preexistentes fora de escopo e decisões finas (SC-007)
- [x] T011 Revisão final de documentação fiel (Princípio XI): confirmar que README/ajuda não descrevem larguras da tabela de etiquetas — se nada a atualizar, registrar a constatação em `validacao.md`; marcar tasks concluídas e commit do grupo lógico (template + spec/validação) no padrão do repositório (subject "Feature 044: ..." sem acentos, corpo com causas, footer Codebuff)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato; baseline + V0 obrigatórios antes de tocar o template
- **US1 (T003–T006)**: depende do Setup; tasks sequenciais no MESMO arquivo (nenhuma [P])
- **US2 (T007–T008)**: depende da US1 concluída (refina o que ela produziu)
- **Polish (T009–T011)**: depende de US1+US2

### User Story Dependencies

- **US1 (P1)**: independente — entrega o MVP sozinha (linha garantida + aproveitamento em desktop)
- **US2 (P2)**: refina a US1 em telas menores/zoom; não faz sentido sem ela

### Parallel Opportunities

- Nenhuma tarefa marcada [P]: todas operam o mesmo arquivo (`assets/labels.html`) ou dependem do seu estado (validações). Fluxo sequencial por design (Princípio I — mudança cirúrgica), como nas 036–043.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup (T001–T002, baseline + V0)
2. US1 (T003–T006) → **STOP and VALIDATE**: quickstart V1–V3 em desktop (linha única + tooltips) + suíte verde
3. Só então US2 para telas menores/zoom

### Incremental Delivery

1. US1 → linha garantida com corte controlado + tooltips no uso principal (desktop)
2. US2 → notebook/tablet/celular/zoom/temas (rolagem confinada)
3. Polish → escopo confinado (impressão da 013 intacta), validação registrada, docs fiéis, commit

---

## Notes

- Mudança exclusivamente de apresentação: nenhuma regra de seleção/filtros/QR/impressão, dado, rota, permissão ou asset estático muda (FR-014/FR-015)
- NÃO bumpar versão de `style.css?v=` nem tocar o SW — `assets/labels.html` é server-side, nunca cacheado (research R1)
- **Sem `@media print`** (R10) e **domínio da 013 protegido**: `#labels-print-area`/`.labels-sheet`/`.label-card`, o `@media print` de etiquetas em `style.css` e o JS de seleção permanecem intocados
- Larguras NÃO são fixadas pela spec (C-1): partida no data-model, refinamento por medição na implementação (V0 antes/depois)
- Escolha de `table-layout: fixed` justificada na análise (research R2 — C-5): torna o corte previsível (linha garantida) e absorve o `width:36px` inline do `th`
- **Linha garantida** (clarificações): nome, marca/modelo, setor e localização com nowrap + ellipsis + tooltip Bootstrap — nunca ellipsis sem tooltip (C-4); fallbacks "—" e conteúdo vazio fora dos spans cortáveis
- **Tombamento sem ellipsis novo** (clarificação): `.tag-badge` com regras globais preservadas — fallback ≤479.98px aceitável
- **Sem badges nesta tabela**: a lição `white-space: normal` escopado (042/043) não se aplica — nada a fazer
- **Conjunto único de colunas px** (lição da 041): sem media query de colunas; pisos ×1,25–1,30 da fonte real; rolagem confinada é o plano B
- Tooltips: `data-bs-toggle="tooltip" data-bs-placement="top" title="..."` — inicialização existente em `base.html`/`main.js` (sem JS novo); carregam dados das linhas, não strings de controles
- Comentários CSS/HTML NÃO citam nomes de controles do header/toolbar/filtros (lição `b75ba99`)
- Commit após cada grupo lógico (US1; US2; polish) — mensagens no padrão do repositório
- Evitar: regras CSS globais, alteração em header/filtros/toolbar/estado vazio/container/folha de etiquetas, refatoração não relacionada
