---
description: "Task list for feature implementation"
---

# Tasks: Ajuste Responsivo da Tabela "Relatório Contábil-Físico do Patrimônio" (041)

**Input**: Design documents from `/specs/041-relatorio-contabil-larguras-colunas/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ui-contract-tabela-relatorio-contabil.md, quickstart.md

**Tests**: NENHUM teste automatizado novo (seção 33 do pedido — sem testes artificiais; padrão 036–040). Suíte pytest existente como regressão (SC-006): baseline antes, focado durante, completo depois (`test_report_print_smoke.py` fixa a âncora `report-print`; `test_rbac.py`/`test_help.py` exercitam a página/domínio). Validação visual do quickstart (V0–V6) é o aceite, registrada em `validacao.md` (SC-008).

**Organization**: Tasks grouped by user story (US1 desktop → US2 telas menores/zoom → US3 impressão/exportação inalteradas), seguida de polish/validação final. Sexta feature da família de ajustes de tabela — mecanismo validado nas 036–040 reusado por decisão das clarificações (C-1/C-5). Especificidades da 041: **texto completo nas textuais** (Descrição/Localização/Responsável — sem clamp nem reticências, clarificação da spec, FR-004/007/008); **preservação obrigatória da impressão** (C-6/FR-013: bloco C1–C10 compartilhado intocado + regra de segurança escopada em `@media print` — research R10); rígidas em **px com folga** para a Plus Jakarta Sans (lição da 039); **comentários CSS não citam controles do header** (lição `b75ba99`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: template Jinja2 em `app/web/templates/`, suíte pytest em `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmação do estado atual — nada de infraestrutura nova (stack intocável, Constitution).

- [x] T001 Ler/confirmar a tabela do relatório em `app/web/templates/reports/inventory.html` e os elementos protegidos do contract §1 (container `card p-4 report-print` com a string exata fixada por `tests/test_report_print_smoke.py`, 10 colunas simétricas thead/tbody, `font-monospace fw-bold` do Tombamento, `<strong>` + `div` S/N condicional na Descrição, badge `badge-soft-gray` da Categoria, pill `status-pill-*` do Status, fallbacks "Estoque Geral"/"Livre"/"-", `text-end small` + cores `var(--red)`/`var(--green)` + `fw-bold` das monetárias, formatação pt-BR inline) e o bloco `@media print` C1–C10 em `app/web/static/css/style.css` (compartilhado — NÃO editar) — sem alterar nada
- [x] T002 Rodar a suíte como BASELINE verde: `python -m pytest tests/ -q` (SC-006; Windows: `.venv\Scripts\python -m pytest tests/ -q`) e capturar o baseline "antes" do quickstart V0 (screenshot desktop + medição das 10 colunas) **e a referência de impressão do V6** (PDF da pré-visualização de `/reports/inventory` em retrato e paisagem) para as comparações antes/depois
  - Registro: baseline inicial 727/728 com 1 falha PRÉ-EXISTENTE (`test_rbac.py::test_web_action_buttons_hidden_without_permission` — comentário de `assets/list.html` citando controle do header, mesma classe do fix `b75ba99`; corrigido o comentário, fora do escopo da tabela) → re-execução completa: **728 passed**. V0 medido com `validar_local.py` (screen 1440: Descrição 7,8% / Localização 6,7% / Responsável 6,9% — textuais esmagadas pelo layout automático; print 1440: papel já 100% via C3).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhuma tarefa fundacional — feature de arquivo único (plan.md/Structure Decision); pré-requisitos são T001–T002.

**⚠️ CRITICAL**: T001–T002 concluídas antes de qualquer alteração (baseline + referência de impressão precisam existir para as comparações antes/depois).

**Checkpoint**: Estado confirmado, baseline e referência de impressão capturados — implementação pode começar.

---

## Phase 3: User Story 1 - Aproveitamento horizontal no Relatório Contábil-Físico (Priority: P1) 🎯 MVP

**Goal**: A tabela ocupa praticamente toda a largura útil do card; Descrição, Localização e Responsável dominam exibindo o texto completo (sem clamp/ellipsis — clarificação); Tombamento e Categoria proporcionais; Status/Data Compra/monetárias compactas com alinhamento à direita consistente; alinhamento e funcionalidade preservados (quickstart V1–V3).

**Independent Test**: abrir `/reports/inventory` em desktop e inspecionar/medir o aproveitamento e a proporção entre as 10 colunas (comparação com o baseline V0).

### Implementation for User Story 1

- [x] T003 [US1] Em `app/web/templates/reports/inventory.html`: adicionar classe de escopo à tabela (ex.: `invrep-table`) e bloco `<style>` embutido no topo do `{% block content %}` com comentário de rastreabilidade "Feature 041" (sem citar controles do header — lição `b75ba99`), `table-layout: fixed; width: 100%; min-width: <medido>` e as larguras por classes `col.cN` no `<colgroup>` (mecanismo das 036–040 — research R2/R3; larguras de partida do data-model: Tombamento ~8 · Descrição ~16 · Categoria ~8 · Status ~8 · Localização ~12 · Responsável ~11 · Data Compra ~7 · Valor Aquisição ~10 · Depreciação ~9 · Valor Atual ~11, a refinar por medição — C-1); compactas/intermediárias em px com folga para a Plus Jakarta Sans (lição da 039); nenhuma regra global (contract §5)
- [x] T004 [US1] Em `app/web/templates/reports/inventory.html`: adicionar as proteções de quebra validadas nas 036–040 (research R4): `overflow-wrap: break-word` nas células; `white-space: nowrap` **apenas nas células compactas** (Tombamento, Data Compra, monetárias — conteúdos curtos conhecidos); **NENHUM clamp/ellipsis/nowrap nas textuais** (Descrição/Localização/Responsável exibem texto completo — clarificação, FR-004/007/008); preservar a estrutura de blocos `<strong>` + `div` S/N da Descrição, badge/pill, `text-end` das monetárias, cores semânticas, fallbacks e todos os IDs/classes funcionais (contract §1–§2)
- [x] T005 [US1] Validar em desktop os cenários V1 (aproveitamento ≥95% e textuais dominando — medição), V2 (conteúdos íntegros: tombamento sem quebra, descrição/S/N completos, badge/pill íntegros, localização/responsável completos, data sem quebra, monetárias íntegras alinhadas à direita com `-XX%` vermelho e valor atual verde em negrito) e V3 (alinhamento 10/10; distribuição estável entre filtros e com 1 linha) do `quickstart.md` — refinar as larguras por medição se algum conteúdo estourar/quebrar (C-1), registrando os valores finais e o print antes/depois
- [x] T006 [US1] Rodar a suíte após a alteração (mínimo os arquivos que exercitam a página/domínio): `python -m pytest tests/test_report_print_smoke.py tests/test_rbac.py tests/test_help.py -q` e, na sequência, a suíte completa verde (SC-006)

**Checkpoint**: US1 entregue — aproveitamento horizontal correto em desktop com zero regressão (MVP).

---

## Phase 4: User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

**Goal**: A tabela (10 colunas) se adapta a notebook/tablet/celular e zoom 80%–200% mantendo proporções, todas as colunas acessíveis e rolagem confinada (quickstart V4).

**Independent Test**: abrir `/reports/inventory` em larguras variadas e níveis de zoom e verificar adaptação, legibilidade e acessibilidade.

### Implementation for User Story 2

- [x] T007 [US2] Em `app/web/templates/reports/inventory.html` (somente se a validação mostrar necessidade — research R6): ajuste responsivo pontual no `<style>` escopado — media query ≤768px com min-width reduzido e/ou refinamento do `min-width` desktop — garantindo: sem cabeçalhos sobrepostos, badge/pill íntegros, valores monetários íntegros, todas as 10 colunas acessíveis, rolagem (quando inevitável) confinada ao `table-responsive`, sem sacrificar legibilidade para eliminar a rolagem (seções 20/21 do pedido); sem reduzir fontes excessivamente (proibição da seção 19)
- [x] T008 [US2] Validar o cenário V4 do `quickstart.md`: desktop médio/notebook (768–1399px), tablet (576–767px), celular (<576px) e zoom 80%–200% (precedentes 036–040) — além dos temas claro e escuro (nenhuma diferença de contraste)

**Checkpoint**: US1 + US2 funcionam — a alteração visual em tela está completa.

---

## Phase 5: User Story 3 - Impressão e exportação inalteradas (Priority: P2)

**Goal**: A pré-visualização de impressão de `/reports/inventory` e as exportações permanecem idênticas ao comportamento anterior (quickstart V6; contract §4).

**Independent Test**: comparar a pré-visualização de impressão e as exportações antes/depois da alteração (referências do T002).

### Implementation for User Story 3

- [x] T009 [US3] Em `app/web/templates/reports/inventory.html` (mesmo `<style>` escopado — research R10): adicionar o bloco de segurança `@media print` restrito à classe da 041 — `table-layout: auto !important; width: 100% !important` na tabela, `white-space: normal !important` nas células, `width: auto !important` nas `col` — garantindo que nenhuma largura/nowrap de tela alcance o papel mesmo se o C3/C6/C7 mudar no futuro; NÃO editar nenhuma regra do bloco C1–C10 em `style.css` (compartilhado com os outros 2 relatórios — FR-013); confirmar que a âncora `class="card p-4 report-print"` permanece intacta (`test_report_print_smoke.py` verde)
- [x] T010 [US3] Validar o cenário V6 do `quickstart.md`: pré-visualização de impressão depois da alteração idêntica à referência do T002 (mesmas páginas, sem página em branco, cabeçalho repetido, linhas indivisíveis, valores íntegros, escala compacta atual) em retrato e paisagem; exportação CSV com conteúdo/nome de arquivo idênticos (gate `relatorios.exportar`; Excel/PDF idem, se exercitados); usuário sem a permissão vê o header sem o controle de exportação e a página íntegra

**Checkpoint**: US1 + US2 + US3 funcionam — tela melhorada e papel/comércio de dados intocados.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Não-vazamento de escopo, registro formal e revisão final (Constitution I/XI/XII).

- [x] T011 Validar o cenário V5 do `quickstart.md` (contract §4–§5): tabelas da 036 (conferência), 037 (listagem de inventários), 038 (equipamentos), 039 (movimentações) e 040 (custodiantes) e demais telas visualmente idênticas; os outros 2 relatórios (`/reports/movements`, `/reports/custodians`) idênticos em tela e no papel; container da tela (page header, cabeçalho interno do relatório, card) inalterado; `git diff` contendo APENAS `app/web/templates/reports/inventory.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`)
- [x] T012 Criar `specs/041-relatorio-contabil-larguras-colunas/validacao.md` no formato das 036–040: baseline + suíte final verde, comparação antes/depois (V0), tabela de larguras finais adotadas (com ajustes e motivos), resultado de cada cenário V1–V6 (com medições e nível de zoom), temas, **verificação de impressão (V6)**, observações preexistentes fora de escopo e decisões finas (SC-008)
- [x] T013 Revisão final de documentação fiel (Princípio XI): confirmar que README/ajuda não descrevem larguras da tabela do relatório — se nada a atualizar, registrar a constatação em `validacao.md`; marcar tasks concluídas e commit do grupo lógico (template + spec/validação) no padrão do repositório

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato; baseline + V0 + referência de impressão obrigatórios antes de tocar o template
- **US1 (T003–T006)**: depende do Setup; tasks sequenciais no MESMO arquivo (nenhuma [P])
- **US2 (T007–T008)**: depende da US1 concluída (refina o que ela produziu)
- **US3 (T009–T010)**: depende de US1+US2 concluídas (protege o CSS de tela final)
- **Polish (T011–T013)**: depende de US1+US2+US3

### User Story Dependencies

- **US1 (P1)**: independente — entrega o MVP sozinha (aproveitamento horizontal em desktop)
- **US2 (P2)**: refina a US1 em telas menores/zoom; não faz sentido sem ela
- **US3 (P2)**: valida a preservação da impressão sobre o resultado final de US1+US2; é o diferencial de risco da 041 (relatório contábil)

### Parallel Opportunities

- Nenhuma tarefa marcada [P]: todas operam o mesmo arquivo (`reports/inventory.html`) ou dependem do seu estado (validações). Fluxo sequencial por design (Princípio I — mudança cirúrgica), como nas 036–040.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup (T001–T002, baseline + V0 + referência de impressão)
2. US1 (T003–T006) → **STOP and VALIDATE**: quickstart V1–V3 em desktop + suíte verde
3. Só então US2 para telas menores/zoom

### Incremental Delivery

1. US1 → aproveitamento horizontal correto no uso principal (desktop)
2. US2 → notebook/tablet/celular/zoom/temas
3. US3 → impressão/exportação comprovadamente inalteradas
4. Polish → escopo confinado, validação registrada, docs fiéis, commit

---

## Notes

- Mudança exclusivamente de apresentação: nenhuma regra contábil, dado, rota, permissão, exportação ou asset estático muda (FR-014/FR-015)
- NÃO bumpar versão de `style.css?v=` nem tocar o SW — `reports/inventory.html` é server-side, nunca cacheado (research R1/R9)
- NÃO editar o bloco `@media print` C1–C10 (compartilhado) — a proteção da 041 é a regra escopada dentro do próprio template (R10/contract §4)
- A âncora `class="card p-4 report-print"` é fixada por `test_report_print_smoke.py` — não renomear classes do container
- Larguras NÃO são fixadas pela spec (C-1): partida no data-model, refinamento por medição na implementação (V0 antes/depois)
- Escolha de `table-layout: fixed` justificada na análise (research R2 — C-5); o papel usa `auto` (C3) e não herda o fixed
- **Texto completo nas textuais** (específico da 041): Descrição/Localização/Responsável SEM clamp, sem ellipsis, sem nowrap — linhas crescem conforme o conteúdo (clarificação da spec); o `fixed` não trunca aqui porque não há nowrap nas textuais
- `nowrap` apenas nas células compactas (Tombamento/Data Compra/monetárias) — seguras por terem px com folga (Plus Jakarta Sans, lição da 039)
- Comentários CSS/HTML NÃO citam nomes de controles do header (lição `b75ba99` — vazamento detectado por testes RBAC)
- Commit após cada grupo lógico (US1; US2; US3; polish) — mensagens no padrão do repositório
- Evitar: regras CSS globais, alteração em header/cabeçalho interno/container, refatoração não relacionada
