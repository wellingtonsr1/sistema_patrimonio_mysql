# Feature Specification: Correção da Impressão A4 dos Relatórios (Trilha de Auditoria, Colaboradores, Contábil-Físico)

**Feature Branch**: `013-impressao-relatorios`

**Created**: 2026-09-17

**Status**: Draft

**Input**: Corrigir exclusivamente o problema de impressão de três relatórios — Trilha de Auditoria & Fluxo, Relação de Colaboradores e Relatório Contábil-Físico — que hoje geram primeira página em branco, conteúdo iniciando na segunda página, truncamento e estouro da área imprimível A4. A impressão de Equipamentos → Etiquetas funciona corretamente e serve apenas de referência de boas práticas. Nenhuma lógica de negócio, consulta, permissão, filtro, dados exibidos ou o módulo de Etiquetas podem ser alterados.

---

## 1. Contexto e análise do sistema atual (somente leitura, verificada nesta especificação)

Fatos confirmados no código — nenhum nome abaixo é presumido:

| # | Ponto investigado | Realidade atual verificada |
|---|---|---|
| 1 | Templates dos 3 relatórios | `app/web/templates/reports/movements_report.html` (Trilha de Auditoria & Fluxo), `custodians_report.html` (Relação de Colaboradores), `inventory.html` (Contábil-Físico). Todos: `{% extends "base.html" %}` + `.page-header.no-print` com botão `window.print()` + conteúdo em `.card.p-4 > .table-responsive > table.table` |
| 2 | Referência funcional (Etiquetas) | `app/web/templates/assets/labels.html` + CSS dedicado `style.css` (~linhas 1490–1600): área de impressão isolada `#labels-print-area.labels-sheet`, ocultação seletiva de todo o resto via `body:has(#labels-print-area) > *:not(main)` etc., `@page` com margem, `break-inside: avoid` por etiqueta |
| 3 | CSS global | `app/web/static/css/style.css` (1617 linhas); `@media print` em 3 blocos: linhas 896–975 (PRINT geral, voltado ao Termo), 1476–1523 (paleta clara p/ tema escuro), 1588–1615 (exclusivo das Etiquetas) |
| 4 | Causa A — página inicial em branco (**revisada na fase de plano**) | Bloco PRINT global (style.css ~896–975): `html, body { padding: 0 !important }` **já neutraliza** o `padding-top: 90px` inline do `<body>` (regra com `!important` vence estilo inline sem `!important`) e `main { padding: 0 }` já anula o `py-4` — espaçamento NÃO é a causa. A causa real: `table { page-break-inside: avoid }` (mesmo bloco) torna a **tabela inteira inquebrável**; com o card contendo uma tabela maior que a página, o navegador empurra o bloco para a página 2 (a página 1 fica vazia — o cabeçalho é `.no-print`) e o excesso é cortado |
| 5 | Causa B — truncamento lateral | `table { table-layout: fixed !important }` (linha ~936) dentro de `.table-responsive` espreme 8–10 colunas na largura da folha; `.truncate-2` (linha 869: `-webkit-line-clamp:2; overflow:hidden`), `text-nowrap` e `max-width:200px` inline ocultam texto na impressão |
| 6 | Causa C — quebras degradadas/instabilidade | Ausência de `tr { break-inside: avoid }` (linhas inteiras podem ser divididas); ausência de `thead { display: table-header-group }` explícito; `@page { size: Auto }` — tamanho de papel não determinístico entre navegadores |
| 7 | Diferença-chave vs Etiquetas | Etiquetas imprime **apenas uma área dedicada** (oculta todo o resto da página), usa `@page` previsível e controla quebras por elemento. Os relatórios imprimem a página inteira, herdando estilos de tela (`padding-top:90px` inline, `py-4`, `max-width:90%`, cards sombreados, `.table-responsive`) sem neutralização completa |
| 8 | JS de impressão | Apenas `onclick="window.print()"` nos 3 relatórios e no botão de Etiquetas — nenhum usa manipulação temporária do DOM (hipótese descartada) |
| 9 | `position: fixed/absolute` | `.app-navbar` é `fixed-top` (oculta em print por `.no-print`); `.sidebar-overlay` (`position:fixed; inset:0`) e `.mobile-sidebar` (`position:fixed`) estão **fora do main** e não têm `no-print` — candidatos adicionais à página fantasma; o `:has()` usado nas Etiquetas não cobre as páginas de relatórios. Espaço fantasma por padding inline foi descartado como causa primária (revisão R1) |
| 10 | Testes existentes | Os 3 relatórios são exercitados em `tests/test_rbac.py`, `test_auth.py`, `test_datetime_flows.py` (render 200, dados, datas) — nenhum teste de layout de impressão existe (não é testável via pytest sem navegador) |

**Consequências da análise** (refletidas nos requisitos): o problema é **exclusivamente de CSS/marcação de impressão** — nenhuma consulta, permissão, filtro ou dado é afetado. A correção segue a boa prática já consagrada no próprio sistema pelas Etiquetas: CSS de impressão dedicado, `@page` determinístico, neutralização completa dos espaçamentos herdados e controle explícito de quebras.

---

## 2. Problema e objetivo

### Problema

Ao clicar em "Imprimir" nos três relatórios:

- A primeira página sai completamente em branco; o conteúdo começa na segunda.
- Partes do conteúdo ficam truncadas nas páginas seguintes.
- Elementos ultrapassam os limites imprimíveis da folha A4.

### Objetivo

Imprimir qualquer um dos três relatórios em A4 de forma integral: sem página inicial em branco (a tabela volta a poder quebrar entre páginas, em vez de ser empurrada como bloco inquebrável), conteúdo iniciando na primeira página, nada cortado nas laterais ou verticalmente, tabelas longas continuando corretamente entre páginas com cabeçalho repetido, e linhas de tabela não divididas ao meio quando o navegador puder evitá-lo — preservando integralmente dados, filtros, permissões e lógica atual.

---

## 3. Princípio fundamental — impressão é apresentação, não funcionalidade

- **Zero alteração de lógica**: consultas, permissões (`relatorios.exportar`, RBAC), filtros, dados exibidos e geração dos relatórios permanecem byte-a-byte iguais.
- **Etiquetas é intocada**: o módulo de referência não recebe nenhuma modificação (nem em template, nem em CSS — as regras novas são adicionadas sem tocar as regras existentes do bloco de Etiquetas).
- **Boas práticas já existentes no sistema** (aprendidas de Etiquetas e do Termo) serão estendidas aos relatórios: `@page` determinístico, ocultação do que não é conteúdo, `break-inside: avoid` por unidade de conteúdo.

---

## 4. User Scenarios & Testing

### User Story 1 — Imprimir a Trilha de Auditoria & Fluxo sem página em branco nem cortes (Priority: P1) 🎯 MVP

Um gestor abre a Trilha de Auditoria & Fluxo, clica em "Imprimir" e obtém na pré-visualização um relatório A4 começando na primeira página, com a tabela completa, cabeçalho repetindo a cada página e nenhuma coluna truncada.

**Why this priority**: É o relatório com mais colunas (10) e maior volume de linhas — o mais crítico dos três e o que evidencia todos os sintomas.

**Independent Test**: Abrir o relatório, imprimir, navegar por todas as páginas da pré-visualização → primeira página com conteúdo, sem truncamento lateral/vertical, tabelas contínuas.

**Acceptance Scenarios**:

1. **Given** o relatório aberto, **When** o usuário clica em Imprimir, **Then** a pré-visualização inicia o conteúdo (cabeçalho do relatório com a empresa) na **primeira página** — nenhuma página em branco antes.
2. **When** o usuário navega por todas as páginas, **Then** nenhuma coluna/tabela está cortada nas laterais e nenhum texto é omitido por clamp/overflow.
3. **When** a tabela atravessa múltiplas páginas, **Then** o cabeçalho das colunas repete e as linhas continuam integralmente.

### User Story 2 — Imprimir a Relação de Colaboradores com o mesmo comportamento (Priority: P1)

**Independent Test**: Mesmo roteiro da US1 no relatório de Colaboradores (8 colunas, listagem longa).

**Acceptance Scenarios**:

1. Impressão inicia na primeira página, sem página em branco.
2. Todas as 8 colunas visíveis integralmente; nenhuma linha cortada ao meio quando evitável.
3. Dados exibidos idênticos aos atuais (mesmas colunas, mesmos valores).

### User Story 3 — Imprimir o Relatório Contábil-Físico com valores monetários íntegros (Priority: P1)

**Independent Test**: Mesmo roteiro da US1 no Relatório Contábil-Físico (10 colunas com valores R$ alinhados à direita).

**Acceptance Scenarios**:

1. Impressão inicia na primeira página, sem página em branco.
2. Valores monetários e percentuais de depreciação visíveis por completo (sem truncamento de colunas numéricas).
3. Tabela contínua entre páginas com cabeçalho repetido.

### User Story 4 — Não-regressão da impressão de Etiquetas e do Termo (Priority: P1)

**Independent Test**: Imprimir Etiquetas (lote selecionado) e o Termo de Responsabilidade → comportamento idêntico ao atual.

**Acceptance Scenarios**:

1. **Given** o módulo Etiquetas, **When** o usuário imprime etiquetas selecionadas, **Then** o resultado é idêntico ao atual (folha 3 colunas, quebras entre etiquetas, nenhuma alteração visual).
2. **Given** o Termo de Responsabilidade, **When** impresso, **Then** permanece funcional (nenhuma regra nova afeta `.term-paper`).
3. **Given** a suíte pytest existente, **When** executada, **Then** permanece verde sem edição de testes.

### Edge Cases

- **Tema escuro ativo**: a impressão já força paleta clara (bloco PRINT II); as regras novas não podem reverter isso.
- **Listas longas** (centenas de linhas): a quebra de página deve ocorrer entre linhas, com cabeçalho repetido, sem linhas órfãs cortadas ao meio.
- **Navegadores**: comportamento alvo é Chrome/Chromium e Firefox nas pré-visualizações de impressão, dentro das limitações normais de cada um (ex.: suporte a `:has()` — o CSS novo NÃO dependerá de `:has()`, ao contrário do bloco de Etiquetas).
- **Janela estreita/mobile**: a impressão é acionada a partir do desktop; nenhuma alteração de layout de tela é permitida.

---

## 5. Requirements

### Functional Requirements

- **FR-001**: Ao imprimir qualquer um dos três relatórios, a pré-visualização NÃO DEVE conter página inicial em branco; o conteúdo DEVE iniciar na primeira página (AC-01/AC-02).
- **FR-002**: O conteúdo impresso DEVE respeitar a área imprimível da folha A4; nenhum elemento pode ultrapassar os limites laterais ou verticais (AC-03).
- **FR-003**: Nenhum texto, coluna, valor monetário ou elemento relevante pode ser truncado/cortado na impressão (AC-04).
- **FR-004**: Tabelas extensas DEVEM continuar entre páginas, com o cabeçalho das colunas repetido em cada página (AC-05).
- **FR-005**: Uma linha de tabela NÃO DEVE ser dividida no meio entre páginas quando o navegador puder evitá-lo (AC-06).
- **FR-006**: Os dados, colunas, filtros, permissões e o comportamento de geração dos relatórios DEVEM permanecer exatamente como estão — a correção é restrita à apresentação de impressão (AC-07).
- **FR-007**: O módulo Equipamentos → Etiquetas e o Termo de Responsabilidade NÃO PODEM ter sua impressão alterada (AC-08).
- **FR-008**: Nenhum espaço ou bloco fantasma pode preceder o conteúdo do relatório na impressão: a tabela DEVE poder quebrar entre páginas (não pode permanecer como bloco inquebrável), eliminando o empurrão do conteúdo para a página seguinte (causa A).
- **FR-009**: Na impressão dos relatórios, o contêiner de rolagem de tabelas de tela DEVE se comportar como contêiner estático de largura integral, e a tabela DEVE distribuir suas colunas de forma legível dentro da folha (layout automático, sem o espremimento do layout fixo), sem cortes laterais (causa B).
- **FR-010**: Os mecanismos de corte de texto de tela (line-clamp/nowrap/max-width de célula) NÃO DEVEM ocultar conteúdo na impressão dos relatórios (causa B).
- **FR-011**: A quebra de página DEVE ser controlada por unidade de conteúdo (linha da tabela evita divisão; card não é mais forçado a caber inteiro), e o tamanho do papel DEVE ser determinístico (A4) para comportamento estável entre navegadores.
- **FR-012**: A correção DEVE ser implementada como CSS de impressão dedicado aos relatórios, sem alterar as regras `@media print` existentes do Termo nem as exclusivas de Etiquetas.

### Regras (síntese operacional)

- R1 — Impressão começa na página 1, sem espaço fantasma (FR-001/FR-008).
- R2 — Nada cortado: largura integral, sem clamp/nowrap oculto na impressão (FR-002/FR-003/FR-009/FR-010).
- R3 — Tabelas longas paginam com cabeçalho repetido e linhas íntegras (FR-004/FR-005/FR-011).
- R4 — Zero mudança funcional; Etiquetas/Termo intocados (FR-006/FR-007/FR-012).

### Key Entities

- **`app/web/templates/reports/*.html` (3 templates)**: nenhuma alteração estrutural de dados; alteração mínima **obrigatória** de marcação: classe de escopo de impressão (`report-print`) no container do relatório — âncora dos seletores do novo bloco (design R2 do plan; remediação /speckit-analyze I1).
- **`app/web/static/css/style.css`**: local da correção (novo bloco `@media print` dedicado aos relatórios, adicionado ao final, sem editar os blocos existentes).
- **`base.html`**: NÃO alterado — o bloco PRINT existente já neutraliza os paddings do body/main (regra com `!important` vence o estilo inline); a causa real (tabela inquebrável) é tratada por CSS no escopo dos relatórios.
- **`assets/labels.html` e regras CSS de Etiquetas**: intocados.

---

## 6. Critérios de Aceitação (rastreabilidade)

| AC | Enunciado | Coberto por |
|---|---|---|
| AC-01 | Pré-visualização inicia o conteúdo na primeira página (3 relatórios) | US1/AS1, US2/AS1, US3/AS1; FR-001 |
| AC-02 | Nenhuma página inicial em branco | US1/AS1; FR-001 |
| AC-03 | Conteúdo respeita os limites da folha A4 | US1/AS2; FR-002 |
| AC-04 | Nenhum conteúdo truncado (texto, coluna, valor) | US1/AS2, US2/AS2, US3/AS2; FR-003 |
| AC-05 | Tabelas extensas continuam entre páginas com cabeçalho repetido | US1/AS3; FR-004 |
| AC-06 | Linha de tabela não dividida ao meio quando evitável | US2/AS2; FR-005 |
| AC-07 | Dados/colunas/filtros/permissões idênticos aos atuais | US2/AS3; FR-006 |
| AC-08 | Etiquetas e Termo com impressão inalterada | US4/AS1–AS2; FR-007 |

### Cenários de validação do briefing (mapa)

| # | Passo do critério de aceitação do briefing | Onde |
|---|---|---|
| 1–2 | Abrir relatório e clicar em Imprimir | US1–US3 |
| 3–4 | Pré-visualização inicia na primeira página, sem página vazia | US1/AS1 (FR-001) |
| 5–6 | Navegar por todas as páginas; nada truncado | US1/AS2 (FR-002/FR-003) |
| 7 | Tabelas contínuas entre páginas | US1/AS3 (FR-004) |
| 8 | Dados e informações atuais preservados | US2/AS3 (FR-006) |

---

## 7. Success Criteria

- **SC-001**: Nos 3 relatórios, a primeira página da pré-visualização contém o cabeçalho do relatório e o início da tabela (100% dos casos testados).
- **SC-002**: Zero páginas em branco nas pré-visualizações dos 3 relatórios.
- **SC-003**: Zero truncamento lateral/vertical perceptível na pré-visualização (todas as colunas e valores visíveis por completo).
- **SC-004**: Tabelas com múltiplas páginas repetem o cabeçalho das colunas em todas elas.
- **SC-005**: Zero alteração de dados/consultas/permissões/filtros (verificado por `git diff` e suíte verde).
- **SC-006**: Etiquetas e Termo de Responsabilidade imprimem como antes (inspeção visual + zero diff em suas regras CSS/template).
- **SC-007**: Suíte pytest existente 100% verde, sem edição de testes.

---

## 8. Escopo

### Incluído

- Correção CSS de impressão para os 3 relatórios (novo bloco `@media print` dedicado em `style.css`);
- Classe de escopo de impressão (`report-print`) nos 3 templates de relatório — âncora **obrigatória** dos seletores do novo bloco: sem `:has()` (vetado por compatibilidade) e sem editar regras globais (vetado), não há outra forma de ancorar o CSS às páginas dos relatórios (design R2 do plan; remediação I1);
- Validação visual da impressão dos 3 relatórios e não-regressão de Etiquetas/Termo.

### Não incluído (limites de escopo)

- Qualquer alteração em `assets/labels.html` ou nas regras CSS de Etiquetas;
- Qualquer alteração na lógica dos relatórios, consultas, services, permissões, filtros, rotas ou dados;
- Refatoração geral de CSS, reestruturação dos templates `base.html` ou dos relatórios;
- Novos relatórios, exportações ou formatos de papel adicionais;
- Testes automatizados de **renderização de layout de impressão** (ex.: comparação de PDF, navegador headless — infraestrutura fora do stack; a validação de impressão é manual/visual, com a suíte pytest como guarda de não-regressão). **Exceção prevista**: smoke test de marcação (presença da classe de escopo no HTML renderizado) é permitido e faz parte do plano (research R9, tasks T002 — remediação A2).

---

## 9. Casos de erro (comportamento definido)

| Situação | Comportamento |
|---|---|
| Tabela maior que a área útil mesmo com ajustes | Última coluna mantém legibilidade; quebra de página entre linhas — nunca corte lateral |
| Navegador sem suporte a seletor moderno usado na correção | O CSS novo NÃO depende de `:has()`; degrada para comportamento padrão de impressão sem quebrar |
| Tema escuro ativo na impressão | Paleta clara do bloco PRINT II existente permanece; regras novas não a anulam |
| Relatório vazio (0 registros) | Impressão exibe apenas o cabeçalho do relatório — sem página em branco |

---

## 10. Premissas e dependências

- A validação de impressão é **manual/visual** (pré-visualização do navegador), pois pytest não renderiza layout; a suíte existente serve como guarda de não-regressão funcional.
- O padrão A4 (210×297mm) é o alvo; margens definidas no `@page` do novo bloco.
- As limitações normais de cada navegador são aceitas (o que se exige é o comportamento dentro do razoável em Chrome/Chromium e Firefox).

---

## 11. Impacto esperado (componentes confirmados pela análise — nada inventado)

| Arquivo | Alteração esperada |
|---|---|
| `app/web/static/css/style.css` | **Novo bloco `@media print` dedicado aos relatórios** (final do arquivo, sem editar blocos existentes): `@page { size: A4 }` determinístico, habilitar quebra de tabela (`page-break-inside: auto` no escopo — revoga o `avoid` herdado que causa a página em branco), `thead { display: table-header-group }`, `tr { break-inside: avoid }`, `table-layout: auto` + quebra de texto (`overflow-wrap`) (revoga o `fixed` espremido), `.table-responsive` estático de largura integral, `.truncate-2`/`text-nowrap`/`max-width` liberados na impressão, escala tipográfica compacta |
| `app/web/templates/reports/movements_report.html` | Classe de escopo de impressão no container do relatório (âncora dos seletores do novo bloco) — sem tocar dados/colunas |
| `app/web/templates/reports/custodians_report.html` | Idem |
| `app/web/templates/reports/inventory.html` | Idem |
| `app/web/templates/base.html` | **NÃO alterado** (neutralização via CSS) |
| `app/web/templates/assets/labels.html` | **NÃO alterado** |
| Regras CSS existentes (Termo/Etiquetas) | **NÃO alteradas** |

**Causas responsáveis (resumo — revisado na fase de plano)**: (A) `table { page-break-inside: avoid }` do bloco PRINT global torna a tabela inteira inquebrável → bloco maior que a página é empurrado para a página 2 (vazia, pois o cabeçalho é `.no-print`) e cortado; (B) `table-layout: fixed !important` + 8–10 colunas + `.truncate-2`/`text-nowrap`/`max-width` inline → truncamento lateral; (C) ausência de `thead: table-header-group`/`tr { break-inside: avoid }` + `@page { size: Auto }` → quebras degradadas e tamanho de papel instável. Os paddings de `html/body/main` já são neutralizados pelo bloco existente (o `!important` vence o inline do `<body>`), e `base.html` permanece intocado.

---

## 12. Premissas registradas

- O volume de registros dos relatórios é variável (dezenas a centenas) — a solução deve paginar corretamente em qualquer volume.
- Não há necessidade de cabeçalho/rodapé de impressão repetidos por página além do cabeçalho das tabelas (requisito do briefing menciona apenas "cabeçalhos/identificação consistentes").

---

*Esta especificação documenta a análise somente-leitura exigida pela REGRA DE SEGURANÇA do briefing (arquivos envolvidos, causas, regras responsáveis, solução proposta e arquivos a alterar). Nada foi implementado nesta etapa; a implementação ocorrerá no fluxo seguinte (/speckit-plan → /speckit-tasks → /speckit-implement), restrita aos arquivos listados na Seção 11.*
