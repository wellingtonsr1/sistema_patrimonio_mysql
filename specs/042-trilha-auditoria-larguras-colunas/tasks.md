---
description: "Task list for feature implementation"
---

# Tasks: Ajuste Responsivo da Tabela "Trilha de Auditoria & Fluxo" (042)

**Input**: Design documents from `/specs/042-trilha-auditoria-larguras-colunas/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ui-contract-tabela-trilha-auditoria.md, quickstart.md

**Tests**: NENHUM teste automatizado novo (seção 35 do pedido — sem testes artificiais; padrão 036–041). Suíte pytest existente como regressão (SC-006): baseline antes, focado durante, completo depois (`test_report_print_smoke.py` fixa a âncora `report-print`; `test_movements.py`/`test_help.py`/`test_rbac.py` exercitam a página/domínio/gate). Validação visual do quickstart (V0–V6, **com contagem de quebras e conferência de tooltips**) é o aceite, registrada em `validacao.md` (SC-008).

**Organization**: Tasks grouped by user story (US1 linha única/aproveitamento → US2 telas menores/zoom → US3 impressão/exportação inalteradas), seguida de polish/validação final. Sétima feature da família de ajustes de tabela — mecanismo validado nas 036–041 reusado (C-1/C-5). Especificidades da 042: **linha garantida nas textuais** (nowrap + ellipsis + tooltip Bootstrap — clarificações da spec, FR-005/007/008/010/011); **rolagem horizontal explicitamente permitida em telas pequenas** (C-4); **conjunto único de colunas em px** (lição da 041 — sem media query de colunas); neutralização de impressão **incluindo spans de ellipsis** (R10 — o C7 global só atinge `td/th`); rígidas em px com folga para a Plus Jakarta Sans (lições 039/041); comentários CSS não citam controles do header (lição `b75ba99`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: template Jinja2 em `app/web/templates/`, suíte pytest em `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmação do estado atual — nada de infraestrutura nova (stack intocável, Constitution).

- [x] T001 Ler/confirmar a tabela da trilha em `app/web/templates/reports/movements_report.html` e os elementos protegidos do contract §1 (container `card p-4 report-print` com a string exata fixada por `tests/test_report_print_smoke.py`, 10 colunas simétricas thead/tbody, `td.text-nowrap` da Data/Hora, `font-monospace fw-bold` do Tombamento, badge `badge-soft-primary` do Tipo, **estrutura condicional local + custodião de Origem/Destino** com `<br>` e cores atuais, pill `status-pill-*` do Status, Motivo com `truncate-2` + `max-width:200px` inline **sem tooltip**, `small text-muted` do Operador, link do Termo condicional a `{% if m.term_code %}` com target `_blank` e fallback "-") e o bloco `@media print` C1–C10 em `app/web/static/css/style.css` (compartilhado — NÃO editar) — sem alterar nada
- [x] T002 Rodar a suíte
  - Registro: baseline **728 passed**; V0 medido (`validar_local.py`, screen 1440px): tabela 1395,9px mas **soma das colunas 1065px** (~331px desperdiçados) — Origem 78,8px (5,6%) e Operador 75,5px (5,4%) espremidas; Motivo 106,8px truncado a 200px sem tooltip; referência de impressão V6 capturada (paper). como BASELINE verde: `python -m pytest tests/ -q` (SC-006; Windows: `.venv\Scripts\python -m pytest tests/ -q`) e capturar o baseline "antes" do quickstart V0 (screenshot desktop + medição das 10 colunas + **contagem de quebras de linha por célula** nas primeiras linhas) **e a referência de impressão do V6** (PDF da pré-visualização de `/reports/movements` em retrato e paisagem) para as comparações antes/depois

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhuma tarefa fundacional — feature de arquivo único (plan.md/Structure Decision); pré-requisitos são T001–T002.

**⚠️ CRITICAL**: T001–T002 concluídas antes de qualquer alteração (baseline + referência de impressão precisam existir para as comparações antes/depois).

**Checkpoint**: Estado confirmado, baseline e referência de impressão capturados — implementação pode começar.

---

## Phase 3: User Story 1 - Linha horizontal e aproveitamento máximo (Priority: P1) 🎯 MVP

**Goal**: A tabela ocupa praticamente toda a largura útil do card; Equipamento, Origem, Destino e Motivo dominam com **linha garantida** (nowrap + ellipsis + tooltip Bootstrap); Operador intermediária (idem); Data/Hora, Tombamento, Tipo, Status e Termo compactas sem quebra; alinhamento e funcionalidade preservados (quickstart V1–V3).

**Independent Test**: abrir `/reports/movements` em desktop e inspecionar/medir o aproveitamento, a linha única e os tooltips (comparação com o baseline V0).

### Implementation for User Story 1

- [x] T003 [US1] Em `app/web/templates/reports/movements_report.html`: adicionar classe de escopo à tabela (ex.: `movrep-table` — distinta de `.mov-lista-table` da 039) e bloco `<style>` embutido no topo do `{% block content %}` com comentário de rastreabilidade "Feature 042" (sem citar controles do header — lição `b75ba99`), `table-layout: fixed; width: 100%; min-width: <medido>` e as larguras por classes `col.cN` no `<colgroup>` (mecanismo das 036–041 — research R2/R3; larguras de partida do data-model: Data/Hora ~130 · Tombamento ~110 · Equipamento ~150 · Tipo ~150 · Origem ~145 · Destino ~145 · Status ~125 · Motivo ~170 · Operador ~130 · Termo ~110, a refinar por medição — C-1; **conjunto único, sem media query de colunas** — lição da 041); rígidas em px com folga para a Plus Jakarta Sans (×1,25–1,30 — lições 039/041); nenhuma regra global (contract §5)
- [x] T004 [US1] Em `app/web/templates/reports/movements_report.html`: implementar o mecanismo de **linha garantida** (research R4 — clarificações, FR-005/007/008/010/011): nowrap nas rígidas (Data/Hora já tem `text-nowrap`; Tombamento/Tipo/Status/Termo via classe escopada); classe auxiliar de ellipsis (ex.: `.movrep-ellip`: `nowrap + overflow:hidden + text-overflow:ellipsis + max-width:100%`) em Equipamento, Motivo e Operador com `data-bs-toggle="tooltip" data-bs-placement="top" title="{{ ... }}"` (tooltips auto-inicializados em `base.html:329–333`/`main.js`); em Origem/Destino, spans de ellipsis **por segmento** (local e custodião), preservando a estrutura condicional `<br>`, as cores e os fallbacks "-"; **Motivo: remover `truncate-2` e o `max-width:200px` inline** do `<td>` (FR-010); preservar todos os IDs/classes funcionais (contract §1–§2)
- [x] T005 [US1] Validar em desktop os cenários V1 (aproveitamento ≥95% e textuais dominando — medição), V2 (**tooltips Bootstrap** com o texto completo em cada valor truncado; Motivo sem os mecanismos antigos; fallbacks/cores/estrutura locais íntegros) e V3 (alinhamento 10/10; altura de linhas uniforme; distribuição estável entre massas) do `quickstart.md` — refinar as larguras por medição se algum conteúdo estourar ou o tooltip não corresponder ao valor (C-1), registrando os valores finais e o print antes/depois
- [x] T006 [US1] Rodar a suíte após a alteração (mínimo os arquivos que exercitam a página/domínio): `python -m pytest tests/test_report_print_smoke.py tests/test_movements.py tests/test_help.py tests/test_rbac.py -q` e, na sequência, a suíte completa verde (SC-006)

**Checkpoint**: US1 entregue — linha horizontal com corte controlado em desktop, tooltips acessíveis e zero regressão (MVP).

---

## Phase 4: User Story 2 - Responsividade com rolagem permitida (Priority: P2)

**Goal**: A tabela (10 colunas) mantém a leitura horizontal em notebook/tablet/celular e zoom 80%–200%, com rolagem confinada quando inevitável e todas as colunas acessíveis (quickstart V4).

**Independent Test**: abrir `/reports/movements` em larguras variadas e níveis de zoom e verificar adaptação, legibilidade, tooltips e acessibilidade das colunas.

### Implementation for User Story 2

- [x] T007 [US2] Em `app/web/templates/reports/movements_report.html` (somente se a validação mostrar necessidade — research R6): ajuste responsivo pontual no `<style>` escopado — **sem media query de colunas** (conjunto único, lição da 041); eventual refinamento do `min-width` garantindo: rolagem horizontal confinada ao `table-responsive` quando a viewport for menor que o mínimo (comportamento autorizado — C-4/seções 20/21 do pedido), todas as 10 colunas acessíveis e legíveis na rolagem, sem sobreposição, sem reduzir fontes excessivamente (proibição da seção 20)
- [x] T008 [US2] Validar o cenário V4 do `quickstart.md`: desktop médio/notebook (768–1399px — linha garantida mantida com corte controlado), tablet (576–767px) e celular (<576px — rolagem confinada funcional, colunas acessíveis), zoom 80%–200% (precedentes 036–041) — além dos temas claro e escuro (nenhuma diferença de contraste)

**Checkpoint**: US1 + US2 funcionam — a alteração visual em tela está completa.

---

## Phase 5: User Story 3 - Impressão e exportação inalteradas (Priority: P2)

**Goal**: A pré-visualização de impressão de `/reports/movements` e as exportações permanecem idênticas ao comportamento anterior — textos impressos por completo, sem ellipsis no papel (quickstart V6; contract §4).

**Independent Test**: comparar a pré-visualização de impressão e as exportações antes/depois da alteração (referências do T002).

### Implementation for User Story 3

- [x] T009 [US3] Em `app/web/templates/reports/movements_report.html` (mesmo `<style>` escopado — research R10): adicionar o bloco de segurança `@media print` restrito às classes da 042 — `table-layout: auto !important; width: 100% !important; min-width: 0 !important` na tabela, `white-space: normal !important` nas células, `width: auto !important` nas `col` **e neutralização dos spans de ellipsis** (`white-space: normal !important; overflow: visible !important; text-overflow: clip !important` — o C7 global só atinge `td/th`), garantindo que nenhuma largura/nowrap/corte de tela alcance o papel; NÃO editar nenhuma regra do bloco C1–C10 em `style.css` (compartilhado com os outros 2 relatórios — FR-016); confirmar que a âncora `class="card p-4 report-print"` permanece intacta (`test_report_print_smoke.py` verde)
- [x] T010 [US3] Validar o cenário V6 do `quickstart.md`: pré-visualização de impressão depois da alteração idêntica à referência do T002 (mesmas páginas, sem página em branco, cabeçalho repetido, linhas indivisíveis, **textos completos no papel — sem ellipsis**), em retrato e paisagem; exportação CSV com conteúdo/nome de arquivo idênticos (gate `relatorios.exportar`); usuário sem a permissão vê o header sem o controle de exportação e a página íntegra

**Checkpoint**: US1 + US2 + US3 funcionam — tela com linha garantida e papel/dados intocados.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Não-vazamento de escopo, registro formal e revisão final (Constitution I/XI/XII).

- [x] T011 Validar o cenário V5 do `quickstart.md` (contract §4–§5): tabelas da 036 (conferência), 037 (listagem de inventários), 038 (equipamentos), **039 (listagem de Movimentações — `movements/list.html`, não confundir)**, 040 (custodiantes) e 041 (Relatório Contábil-Físico) e demais telas visualmente idênticas; os outros 2 relatórios (`/reports/inventory`, `/reports/custodians`) idênticos em tela e no papel; container da tela (page header, cabeçalho interno do relatório, card) inalterado; `git diff` contendo APENAS `app/web/templates/reports/movements_report.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`)
- [x] T012 Criar `specs/042-trilha-auditoria-larguras-colunas/validacao.md` no formato das 036–041: baseline + suíte final verde, comparação antes/depois (V0, **incluindo redução de quebras**), tabela de larguras finais adotadas (com ajustes e motivos), resultado de cada cenário V1–V6 (com medições, zoom, **verificação de tooltips e de impressão**), temas, observações preexistentes fora de escopo e decisões finas (SC-008)
- [x] T013 Revisão final de documentação fiel (Princípio XI): confirmar que README/ajuda não descrevem larguras da tabela da trilha — se nada a atualizar, registrar a constatação em `validacao.md`; marcar tasks concluídas e commit do grupo lógico (template + spec/validação) no padrão do repositório

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato; baseline + V0 + referência de impressão obrigatórios antes de tocar o template
- **US1 (T003–T006)**: depende do Setup; tasks sequenciais no MESMO arquivo (nenhuma [P])
- **US2 (T007–T008)**: depende da US1 concluída (refina o que ela produziu)
- **US3 (T009–T010)**: depende de US1+US2 concluídas (protege o CSS de tela final)
- **Polish (T011–T013)**: depende de US1+US2+US3

### User Story Dependencies

- **US1 (P1)**: independente — entrega o MVP sozinha (linha garantida + aproveitamento em desktop)
- **US2 (P2)**: refina a US1 em telas menores/zoom; não faz sentido sem ela
- **US3 (P2)**: valida a preservação da impressão sobre o resultado final de US1+US2; crítica porque a 042 introduz cortes por ellipsis que NÃO podem vazar para o papel (R10)

### Parallel Opportunities

- Nenhuma tarefa marcada [P]: todas operam o mesmo arquivo (`reports/movements_report.html`) ou dependem do seu estado (validações). Fluxo sequencial por design (Princípio I — mudança cirúrgica), como nas 036–041.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup (T001–T002, baseline + V0 + referência de impressão)
2. US1 (T003–T006) → **STOP and VALIDATE**: quickstart V1–V3 em desktop (linha única + tooltips) + suíte verde
3. Só então US2 para telas menores/zoom

### Incremental Delivery

1. US1 → linha garantida com corte controlado + tooltips no uso principal (desktop)
2. US2 → notebook/tablet/celular/zoom/temas (rolagem confinada autorizada)
3. US3 → impressão/exportação comprovadamente inalteradas (spans neutralizados no papel)
4. Polish → escopo confinado, validação registrada, docs fiéis, commit

---

## Notes

- Mudança exclusivamente de apresentação: nenhuma regra, dado, registro de auditoria, rota, permissão, exportação ou asset estático muda (FR-017/FR-018)
- NÃO bumpar versão de `style.css?v=` nem tocar o SW — `reports/movements_report.html` é server-side, nunca cacheado (research R1/R9)
- NÃO editar o bloco `@media print` C1–C10 (compartilhado) — a proteção da 042 é o bloco escopado no próprio template (R10/contract §4), **incluindo os spans de ellipsis**
- A âncora `class="card p-4 report-print"` é fixada por `test_report_print_smoke.py` — não renomear classes do container
- Larguras NÃO são fixadas pela spec (C-1): partida no data-model, refinamento por medição na implementação (V0 antes/depois)
- Escolha de `table-layout: fixed` justificada na análise (research R2 — C-5): é o que torna o corte previsível (sem redistribuição por conteúdo); o papel usa `auto` (C3) e não herda o fixed
- **Linha garantida** (clarificação): Equipamento/Motivo/Operador e cada segmento de Origem/Destino com nowrap + ellipsis + tooltip Bootstrap — nunca ellipsis sem tooltip (C-7); nunca quebra nas rígidas (identificadores)
- **Conjunto único de colunas px** (lição da 041): sem media query de colunas; pisos ×1,25–1,30 da fonte real; rolagem confinada é o plano B autorizado (C-4)
- Tooltips: atributos `data-bs-toggle="tooltip" data-bs-placement="top" title="..."` — inicialização existente em `base.html`/`main.js` (sem JS novo); carregam dados das linhas, não strings de controles
- Comentários CSS/HTML NÃO citam nomes de controles do header (lição `b75ba99` — vazamento detectado por testes RBAC)
- Commit após cada grupo lógico (US1; US2; US3; polish) — mensagens no padrão do repositório
- Evitar: regras CSS globais, alteração em header/cabeçalho interno/container, refatoração não relacionada, tocar em `movements/list.html` (039)
