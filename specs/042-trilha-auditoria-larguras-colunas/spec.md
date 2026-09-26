# Feature Specification: Ajuste Responsivo da Tabela "Trilha de Auditoria & Fluxo"

**Feature Branch**: `042-trilha-auditoria-larguras-colunas`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Ajustar exclusivamente o layout da tabela da tela **"Trilha de Auditoria & Fluxo"** (`/reports/movements`): aproveitar o máximo possível da largura horizontal disponível, com o objetivo visual principal de **manter os valores de cada coluna em uma única linha horizontal**, evitando que a tabela fique "espremida" e quebrada verticalmente. As 10 colunas (Data / Hora, Tombamento, Equipamento, Tipo, Origem, Destino, Status, Motivo, Operador, Termo) recebem prioridades distintas: textuais **Equipamento, Origem, Destino e Motivo** no topo; **Operador** intermediária; **Data / Hora, Tombamento, Tipo, Status e Termo** compactas. Em telas muito pequenas, a rolagem horizontal confinada é explicitamente permitida (diferença intencional das 036/037): em desktop maximizar a linha horizontal; em telas pequenas preservar a leitura e permitir rolagem quando necessário. Mesmo princípio das specs 036–041: análise antes de alterar, implementação cirúrgica — nenhuma funcionalidade, dado, registro de auditoria ou regra de negócio é alterada.

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| Tela "Trilha de Auditoria & Fluxo" = `app/web/templates/reports/movements_report.html` (rota `/reports/movements` em `app/web/routes.py:1578`, gate `relatorios.visualizar`, `MovementService.get_all_movements(db, limit=1000)`) | Superfície única a alterar — **distinta** da listagem de Movimentações (`movements/list.html`, ajustada na 039) |
| Tabela com exatamente as 10 colunas do pedido: **Data / Hora** (`td.text-nowrap` já existente, `dd/mm/YYYY HH:MM` via `localtime`), **Tombamento** (`font-monospace fw-bold`), **Equipamento** (texto puro, `m.asset.name`), **Tipo** (badge `badge-soft-primary` ~.68rem), **Origem** (local + quebra `<br>` condicional com custodião em `span.text-muted` abaixo — estrutura **proposital em 2 linhas**), **Destino** (idem, custodião em `var(--c-primary-text)`, local em `<strong>`), **Status** (pill `status-pill-{{ m.new_status.value }}`), **Motivo** (`td.truncate-2` com `max-width:200px` inline, **sem tooltip** — dado completo indisponível sem mecanismo de consulta), **Operador** (`small text-muted`), **Termo** (link `font-monospace` condicional a `m.term_code` → `/movements/{id}/term`, target `_blank`; fallback "-") | Nuances protegidas nos FRs: `text-nowrap` existente da Data/Hora, estrutura local+custodião de Origem/Destino, badge/pill, link do Termo com condição e fallback, `truncate-2` atual do Motivo |
| Sem `<colgroup>` nem classes de largura; container `card p-4 report-print` > `table-responsive` > `table table-bordered table-hover align-middle small mb-0` | Distribuição atual vem do layout automático — Motivo limitado a 200px inline; textuais competem por espaço sem priorização |
| Header com 2 controles ("Baixar CSV" condicional a `relatorios.exportar` + "Imprimir") em `page-header no-print`; cabeçalho interno do relatório (empresa + total de registros) | Fora do escopo — intocados (só a tabela); comentários novos não citam controles do header (lição `b75ba99`) |
| Bloco `@media print` C1–C10 em `style.css` (~L1650+) ancorado em `.report-print`, **compartilhado pelos 3 relatórios**: `table-layout:auto!important`, `white-space:normal!important` (revoga `text-nowrap` no papel), `truncate-2` liberado (C8), `min-width:0` no `.table-responsive`, `font-size:8.5pt` | **CRÍTICO**: qualquer largura/nowrap de tela introduzido MUST ser neutralizado em `@media print` para esta página (precedente da 041); nenhuma regra compartilhada editada; âncora `class="card p-4 report-print"` fixada por `test_report_print_smoke.py` (L19–21 incluem `/reports/movements`) |
| Lições incorporadas da família 036–041: fonte real (Plus Jakarta Sans, Google Fonts em base.html L23) ~20–30% mais larga que fallbacks de medição; padding real das células Bootstrap vendor `.5rem .5rem` (16px/coluna); comentários CSS/HTML não citam controles do header | Premissas de dimensionamento e de rastreabilidade |
| Testes existentes: `test_report_print_smoke.py` (renderiza a página), `test_help.py:109`, `test_rbac.py` (gate `relatorios.exportar` + RBAC de template), `test_movements.py`/`test_movements_report.py` (domínio) | Suíte como regressão (SC-006); run focado definido no plan |
| Constitution I/X/XI/XII: escopo cirúrgico, interface consistente, docs fiéis, suíte verde | Restrições de implementação |

## Decisões registradas pelo solicitante (2026-09-25)

- **C-1**: **NÃO fixar percentuais na spec** — larguras determinadas pela implementação após análise do HTML/CSS/comportamento atual (padrão 037–041).
- **C-2**: prioridade de espaço: maior para **Equipamento, Origem, Destino e Motivo**; intermediária para **Operador**; compactas: **Data / Hora, Tombamento, Tipo, Status e Termo** — ajustada pela implementação após análise dos conteúdos reais (seção 28: "conceitual").
- **C-3**: a tabela deve ocupar praticamente toda a largura útil do container, sem grandes vazios, sem colunas excessivamente pequenas e sem larguras iguais para todas as colunas.
- **C-4 (diferença intencional das 036/037)**: objetivo visual principal é **manter os valores em uma única linha** sempre que possível (seção 14: quebra é o último recurso); em telas muito pequenas, com 10 colunas, a **rolagem horizontal confinada** é a solução responsiva adequada — não sacrificar legibilidade nem reduzir fonte excessivamente para "encaixar" (seções 20/21).
- **C-5** (implícita do pedido): `table-layout` (fixed vs auto) é decisão da implementação com base na análise (seção 26), considerando 10 colunas, conteúdo variável, necessidade de linha única e responsividade — não aplicado automaticamente.
- **C-6 (específica de relatório, herdada da 041)**: a melhoria de tela NÃO pode quebrar a impressão/PDF existente; o CSS de impressão do relatório (bloco `report-print` C1–C10) deve ser preservado integralmente.
- **C-7 (seção 31)**: nenhum dado removido, alterado, truncado permanentemente ou ocultado sem mecanismo de consulta — se houver truncamento visual com ellipsis, o valor completo deve permanecer acessível conforme o padrão do sistema (ex.: tooltip).

## Clarifications

### Session 2026-09-25

- Q: Nas colunas textuais Equipamento, Origem, Destino e Motivo, o que fazer quando o texto não couber em uma linha, mesmo com a coluna alargada? → A: Linha garantida — `nowrap` + ellipsis + tooltip; o corte é controlado (sem sobreposição) e o valor completo permanece acessível (C-7).
- Q: Como o valor completo deve ficar acessível no tooltip? → A: Tooltip Bootstrap (`data-bs-toggle="tooltip"`), padrão do projeto (já usado em badges/botões), com leitura confortável do texto completo.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Linha horizontal e aproveitamento máximo na Trilha de Auditoria (Priority: P1)

Um auditor abre "Trilha de Auditoria & Fluxo" e vê a tabela ocupando praticamente toda a largura útil do card, com cada valor predominando em **uma única linha**: data/hora completa, código íntegro, origem e destino legíveis sem espremimento, motivo com espaço adequado e termo clicável íntegro — análise rápida da trilha sem "escadinha" vertical.

**Why this priority**: é o objetivo central do pedido — leitura horizontal da trilha de auditoria, ferramenta de análise rápida de fluxo patrimonial.

**Independent Test**: abrir `/reports/movements` em desktop e inspecionar/medir o aproveitamento da largura e a quantidade de quebras por linha (comparação antes/depois).

**Acceptance Scenarios**:

1. **Given** movimentações listadas, **When** a tabela é exibida em desktop, **Then** ela ocupa praticamente toda a largura útil do card, com Equipamento, Origem, Destino e Motivo dominando o espaço.
2. **Given** qualquer linha da trilha, **When** exibida em largura suficiente, **Then** Data/Hora, Tombamento, Tipo, Status e Termo aparecem em uma única linha, sem quebra.
3. **Given** origem/destino institucionais longos e motivos extensos, **When** a tabela é exibida em desktop, **Then** cada valor permanece em uma única linha com corte controlado (ellipsis) e o texto completo acessível via tooltip Bootstrap (clarificação; C-7/seção 31 — hoje o Motivo fica truncado em 200px sem mecanismo de consulta).
4. **Given** o estado atual do Motivo (truncado em 200px **sem** tooltip), **When** a 042 é concluída, **Then** o valor completo fica acessível conforme o padrão do sistema (C-7/seção 31 — hoje o dado fica oculto sem mecanismo de consulta).

---

### User Story 2 - Responsividade com rolagem permitida em telas pequenas (Priority: P2)

O usuário acessa a trilha de notebook, tablet ou celular (e/ou zoom variado): a tabela mantém a leitura horizontal com prioridade, e em larguras muito pequenas usa a rolagem horizontal confinada ao contêiner — todas as 10 colunas acessíveis, sem sobreposição, sem fonte minúscula, sem conteúdo cortado.

**Why this priority**: 10 colunas não cabem legíveis em um celular; a rolagem confinada é o mecanismo do projeto e foi explicitamente autorizada pelo solicitante (C-4).

**Independent Test**: abrir `/reports/movements` em larguras variadas (desktop, notebook, tablet, celular e zoom) e verificar adaptação, legibilidade, acessibilidade das colunas e comportamento da rolagem.

**Acceptance Scenarios**:

1. **Given** viewport de notebook/tablet, **When** a tabela é exibida, **Then** a distribuição maximiza a linha horizontal dentro do espaço, sem sobreposição nem colunas colapsadas.
2. **Given** viewport de celular, **When** a tabela é exibida, **Then** a rolagem horizontal confinada ao contêiner mantém todas as colunas acessíveis e legíveis (sem fonte reduzida excessivamente, sem dados escondidos).
3. **Given** zoom do navegador variado, **When** a tabela é exibida, **Then** os critérios de legibilidade, linha única e ausência de sobreposição se mantêm.

---

### User Story 3 - Impressão e exportação inalteradas (Priority: P2)

O usuário imprime a trilha ou baixa o CSV: o resultado é exatamente o mesmo de antes — no papel, as regras de impressão do relatório (C1–C10) continuam mandando (linhas podem quebrar no papel como hoje; o truncamento de tela é liberado pelo C8).

**Why this priority**: relatório oficial de auditoria; alterações de `table-layout`/larguras/nowrap em tela não podem vazar para o `@media print` (C-6).

**Independent Test**: imprimir `/reports/movements` (pré-visualização) e chamar as exportações antes/depois da alteração, comparando o resultado.

**Acceptance Scenarios**:

1. **Given** a impressão funcionando hoje, **When** a alteração de tela é aplicada, **Then** a pré-visualização permanece idêntica ao comportamento atual (sem página em branco, cabeçalho repetido, valores íntegros, `table-layout:auto` no papel).
2. **Given** a exportação CSV da trilha, **When** executada, **Then** o resultado é idêntico ao de antes (mesmos dados, mesmo nome de arquivo, mesmo gate `relatorios.exportar`).
3. **Given** usuário sem `relatorios.exportar`, **When** a página é renderizada, **Then** o HTML não introduz nenhuma string que viole os testes RBAC de template existentes.

---

### Edge Cases

- **Origem/Destino com custodião**: estrutura de 2 linhas (local + custodião em `<br>` condicional) é **intencional do template** e preservada; cada linha (local e custodião) em linha única com corte controlado + tooltip (clarificação); sem custodião, exibe apenas o local (ou "-").
- **Destino sem local**: fallback "-" exibido como hoje; custodião do destino em `var(--c-primary-text)` preservado.
- **Motivo longo** (texto extenso): **linha garantida** — ellipsis + tooltip Bootstrap com o texto completo (clarificação/C-7); nunca ocultar o dado sem mecanismo de consulta.
- **Equipamento/Operador longos**: linha única com corte controlado + tooltip quando excederem a largura da coluna (clarificação).
- **Termo ausente**: fallback "-" preservado; com `term_code`, link mono íntegro em uma linha (identificador não quebra).
- **Tipo com label longo** (ex.: "Entrada por Aquisição", "Envio para Manutenção"): badge íntegro, podendo quebrar entre palavras quando inevitável — sem quebra no meio da palavra.
- **Status como pill**: pill `status-pill-<valor>` íntegro, sem quebra, comportamento visual atual.
- **Data/Hora**: `dd/mm/YYYY HH:MM` em uma linha (o `text-nowrap` existente permanece).
- **Tombamento mono**: código íntegro, sem quebra no meio (ex.: "PMJP679450").
- **Operador com nome extenso**: nome completo em linha única com corte controlado + tooltip quando exceder a largura da coluna (clarificação).
- **Lista vazia / sem registros**: estado do relatório inalterado.
- **Impressão da trilha**: qualquer largura/nowrap de tela neutralizada em `@media print` para esta página, sem editar o bloco compartilhado C1–C10.
- **Tema claro/escuro**: nenhuma cor nova; contraste preservado.
- **Uma única linha na tabela**: distribuição estável por coluna (não por conteúdo da linha).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tabela MUST aproveitar praticamente toda a largura útil disponível do container onde houver espaço (C-3), sem grandes vazios, sem colunas excessivamente pequenas e sem larguras iguais para todas as colunas.
- **FR-002**: A distribuição de larguras MUST ser proporcional à natureza do conteúdo, seguindo C-2 (Equipamento, Origem, Destino e Motivo no topo; Operador intermediária; Data/Hora, Tombamento, Tipo, Status e Termo compactas) — dimensionada pela implementação após análise (C-1), sem percentuais fixados por esta spec.
- **FR-003**: A coluna Data / Hora MUST exibir `dd/mm/YYYY HH:MM` completo em uma única linha (preservando o `text-nowrap` existente), sem quebra em nenhuma parte da data ou da hora.
- **FR-004**: A coluna Tombamento MUST exibir o código patrimonial completo em uma única linha, em fonte mono e negrito (como hoje), sem quebra do código no meio.
- **FR-005**: A coluna Equipamento MUST manter a descrição/nome do equipamento em **uma única linha** (clarificação): quando o texto exceder a largura da coluna, corte controlado com ellipsis + tooltip Bootstrap — sem quebra e sem sobreposição.
- **FR-006**: A coluna Tipo MUST permanecer compacta, com os badges existentes íntegros e em linha única sempre que possível (quebra apenas entre palavras quando inevitável), sem largura exagerada.
- **FR-007**: A coluna Origem MUST receber espaço significativo: o nome do local/setor em **uma única linha** (clarificação), com corte controlado por ellipsis + tooltip quando exceder a largura; a estrutura condicional do custodião (2ª linha informativa intencional) é preservada, também em linha única com corte controlado quando necessário; fallback "-" preservado.
- **FR-008**: A coluna Destino MUST seguir a mesma lógica da Origem (linha única com corte controlado + tooltip no local e no custodião), com espaço proporcional ao conteúdo, preservando o local em `<strong>` com a cor atual e o custodião condicional.
- **FR-009**: A coluna Status MUST permanecer compacta: o pill `status-pill-<valor>` continua íntegro, legível, sem quebra e alinhado verticalmente; os status e suas regras NÃO são alterados.
- **FR-010**: A coluna Motivo MUST receber espaço adequado (maior que Tipo/Status/Termo) e manter o texto em **uma única linha** (clarificação), substituindo o `truncate-2` atual (2 linhas, 200px, sem tooltip) por corte controlado com ellipsis + tooltip Bootstrap — o valor completo permanece acessível (C-7).
- **FR-011**: A coluna Operador MUST possuir largura suficiente para o nome/identificação do operador em **uma única linha** (clarificação), com corte controlado por ellipsis + tooltip Bootstrap quando exceder a largura da coluna.
- **FR-012**: A coluna Termo MUST permanecer compacta: o link mono do termo (condicional a `m.term_code`, target `_blank`) permanece íntegro em uma linha, sem quebra de identificadores; o fallback "-" é preservado.
- **FR-013**: A regra geral de quebra (seção 14) MUST ser respeitada: primeiro linha única, depois uso do espaço horizontal, redistribuição entre colunas e compactação das curtas — quebra de texto somente quando realmente necessária; `white-space: nowrap` nas células onde quebra não faz sentido (Data/Hora, Tombamento, Tipo, Status, Termo, identificadores) e nas textuais conforme clarificação (Equipamento, Origem, Destino, Motivo — sempre com ellipsis + tooltip), garantindo corte controlado sem sobreposição (seção 15).
- **FR-014**: Cabeçalho e corpo MUST compartilhar exatamente a mesma estrutura de colunas (sem deslocamento entre thead e tbody, sem `width` aplicado somente ao `<td>`, sem redistribuição automática inesperada); o container da tela, o header (controles do relatório), o cabeçalho interno e o `page-header` NÃO podem ser alterados; a implementação MUST reutilizar a estrutura existente e, se necessário CSS novo, usar seletor específico desta tabela/tela, sem classes genéricas, sem duplicar estilos e sem bump de cache global.
- **FR-015**: A solução MUST manter ou melhorar a responsividade em desktop grande/médio, notebook, tablet, celular, larguras intermediárias e zoom (faixa 80%–200%, precedentes 036–041), priorizando a linha horizontal dentro do espaço disponível; em larguras mínimas a rolagem horizontal confinada ao contêiner da tabela é a solução adequada (C-4), sem conteúdo cortado indevidamente, sobreposição, badges/pills quebrados, fonte reduzida excessivamente ou colunas inacessíveis.
- **FR-016**: A alteração de tela MUST preservar integralmente a impressão: nenhuma regra do bloco `@media print` dos relatórios (C1–C10, ancorado em `.report-print` e compartilhado com os outros 2 relatórios) pode ser editada; qualquer largura/nowrap/corte por ellipsis de tela introduzido MUST ser neutralizado dentro de `@media print` para esta página (precedente da 041), e a pré-visualização de impressão deve permanecer idêntica ao comportamento atual (C-6).
- **FR-017**: Nenhuma funcionalidade MAY ser alterada: registros de auditoria, movimentações, regras de negócio, filtros, pesquisa, ordenação, paginação, exportações, impressão, relatórios, API, endpoints, banco, modelos, schemas, permissões, autenticação, auditoria e fluxo patrimonial permanecem intocados.
- **FR-018**: Nenhum conteúdo exibido MAY ser removido, alterado, truncado permanentemente ou ocultado sem mecanismo de consulta (C-7): data/hora, tombamento, equipamento, tipo, origem, destino, status, motivo, operador, termo, fallbacks ("-", sem custodião), badges, pills, link do termo e cores semânticas permanecem presentes.
- **FR-019**: A alteração MUST ficar restrita aos arquivos estritamente necessários desta tela; as telas da 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (listagem de Movimentações), 040 (custodiantes), 041 (Relatório Contábil-Físico) e demais telas/componentes NÃO podem ser afetados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em desktop, a tabela ocupa ≥ 95% da largura útil do card/container (verificável por medição da renderização) — referência indicativa, sujeita ao julgamento visual.
- **SC-002**: Em desktop, a maioria dos valores das colunas compactas (Data/Hora, Tombamento, Tipo, Status, Termo) aparece em uma única linha, e as textuais (Equipamento, Origem, Destino, Motivo) ocupam as maiores larguras da tabela (referência indicativa: mais da metade somadas), medida em desktop.
- **SC-003**: Zero desalinhamento entre cabeçalhos e valores em todas as larguras validadas.
- **SC-004**: Em desktop/notebook, zero overflow horizontal da página; em tablet/celular, qualquer rolagem fica restrita ao contêiner da tabela com todas as 10 colunas acessíveis.
- **SC-005**: Zero sobreposição, zero truncamento indevido (códigos, identificadores, data/hora) e zero quebras inadequadas de badges/pills nas larguras validadas; nenhum dado oculto sem mecanismo de consulta (C-7).
- **SC-006**: A suíte de testes existente permanece 100% verde (nenhuma regressão funcional), incluindo `test_report_print_smoke.py` e os testes RBAC do relatório.
- **SC-007**: A pré-visualização de impressão de `/reports/movements` permanece idêntica ao comportamento atual — comparada antes/depois da alteração.
- **SC-008**: Validação registrada em `specs/042-trilha-auditoria-larguras-colunas/validacao.md` no formato das 036–041: suíte pytest 100% verde E inspeção manual com medição nos cenários do pedido (desktop grande/médio, notebook, tablet, celular) e faixa de zoom 80%–200%, com resultado de cada cenário, comparação antes/depois E verificação de impressão.

## Assumptions

- Bootstrap 5.3 e `style.css` permanecem a base; nenhuma dependência nova.
- O mecanismo responsivo do projeto refere-se ao padrão validado nas 036–041 (layout determinístico com larguras por classe escopada + `min-width` com rolagem confinada ao `table-responsive`), com a nuance de que a **linha única tem prioridade** nesta spec e a rolagem é o plano B aceito em telas pequenas (C-4).
- Fonte real do app (Plus Jakarta Sans) é ~20–30% mais larga que fontes de fallback — medições de largura MUST incluir folga para isso (lições 039/041), inclusive nos headers ("Valor Aquisição" e "Data Compra" já demonstraram o risco).
- O bloco `@media print` C1–C10 é compartilhado por 3 templates; qualquer exceção de impressão necessária entra como regra nova e escopada no template, nunca editando as regras existentes (padrão da 041).
- A listagem de Movimentações (`movements/list.html`, 039) e os outros 2 relatórios não são afetados — classe de escopo própria para esta tabela.

## Fora de escopo

- Qualquer mudança funcional (registros de auditoria, movimentações, filtros, exportações CSV/Excel/PDF, permissões, fluxo patrimonial).
- Impressão/PDF em si: o comportamento de impressão permanece idêntico (nenhuma regra de impressão editada).
- Outras tabelas/telas (036–041, Relação de Colaboradores, demais telas) e o layout global/container/header/cabeçalho interno da própria tela.
- Redesenho visual além da distribuição de larguras, quebras, truncamentos controlados e alinhamentos.
- Novos testes automatizados de UI (seção 35 do pedido: apenas executar os existentes; sem testes artificiais).
