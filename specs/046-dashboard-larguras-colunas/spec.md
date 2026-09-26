# Feature Specification: Ajuste Responsivo da Tabela "Visão Geral do Patrimônio"

**Feature Branch**: `046-dashboard-larguras-colunas`

**Created**: 2026-09-26

**Status**: Draft

**Input**: Ajustar exclusivamente o layout da tabela "Fluxo Recente de Movimentações" da tela **"Visão Geral do Patrimônio"** (`/`, dashboard): aproveitar o máximo possível da largura horizontal disponível e **manter os valores das colunas Data, Tombamento, Equipamento, Ação, Destino e Operador em uma única linha horizontal sempre que a largura permitir** (regra prioritária do pedido, seções 2/11/14), com colunas textuais (Equipamento, Destino, Operador) recebendo as maiores parcelas, coluna Ações compacta e responsividade preservada ou melhorada. Mesmo princípio das specs 036–044: análise antes de alterar, implementação cirúrgica — nenhuma funcionalidade de movimentação, patrimônio, dashboard, KPIs, banco, API ou regra de negócio é alterada. **Nenhuma outra tabela, card, seção ou componente do dashboard é tocado.**

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| Tela "Visão Geral do Patrimônio" = `app/web/templates/dashboard.html` (rota `/` em `app/web/routes.py:281`, `view_dashboard`, gate de autenticação global; render com `stats` de `DashboardService.get_stats`) | Superfície única a alterar (tabela "Fluxo Recente de Movimentações" apenas) |
| A tabela-alvo tem **7 colunas** (L242–291, dentro de `div.table-responsive` > `table.table.align-middle`, a ÚLTIMA seção do dashboard, header "Fluxo Recente de Movimentações"): **Data** (`td.text-muted.small.text-nowrap` — `%d/%m/%Y %H:%M`, nowrap já presente), **Tombamento** (`span.tag-badge` — monoespaçada bold .78rem, ellipsis/max-width:100% globais em `style.css:491`, `max-width:140px` ≤479.98px em `style.css:1027`), **Equipamento** (`a.fw-semibold` com nome do bem), **Ação** (`span.badge.badge-soft-primary` com `.68rem` inline — label PT do `MovementType`, ex.: "Entrada por Aquisição", "Alocação / Cautela", "Transferência de Local" — o mais longo ~25 caracteres), **Destino** (`td.small` — span com ícone `bi-person` + nome do colaborador **ou** `bi-geo-alt` + local/"Estoque" — textos com prefixo potencialmente longo), **Operador** (`td.text-muted.small` — nome), **Ações** (`th.text-end` / `td.text-end.text-nowrap` — botões `btn-ghost btn-icon` "Termo de Cautela" condicional ao `term_code` e "Ver Bem") | Nuances protegidas nos FRs: nowrap existente na Data, badge global do tombamento (nunca ellipsis novo), badge-soft da Ação, estrutura if/else do Destino (colaborador × local/"Estoque"), botão de Termo **condicional** (nem toda linha tem), `text-nowrap` existente nas Ações |
| Há **outra tabela** no mesmo template (L182–200: "Necessitam de atenção", 3 colunas Tag/Equipamento/Observação) + 4 `card-kpi` + 4 cards de distribuição (barras) + card "Integridade do Patrimônio" | **Escopo restrito**: só a tabela de movimentações; a tabela de observações e os demais cards permanecem idênticos (o dashboard inteiro é compartilhado por qualquer usuário autenticado) |
| Sem `<colgroup>` nem classes de largura próprias; distribuição atual vem do layout automático (`table-layout: auto` implícito do Bootstrap) | Sem regras pré-existentes para conflito; a 046 introduz classe de escopo própria (padrão da família 036–044) |
| `.table.align-middle` é a tabela de maior uso do sistema (036: conferência; 037: inventários; 038: equipamentos; 040: custodiantes; 044: etiquetas) — **qualquer regra global em `.table` mudaria todas essas telas** | Obriga classe de escopo própria, sem tocar `style.css` (padrão 042–044) |
| Conteúdo real típico: Data `26/09/2026 14:30` (16 caracteres), Tombamento `IMPJP1456`/`IMPJP679450` (7–13 caracteres), Equipamento "Computador Dell OptiPlex 7090" etc., Ação "Entrada por Aquisição"/"Alocação / Cautela"/"Transferência de Local" (badge), Destino "Nome Completo do Colaborador" (custódia) ou "IPMJP - Fundo Municipal de Previdência"/"Estoque" (local), Operador "wellington"/"admin" (nomes de usuário) | Maior variabilidade: **Destino** (nomes completos de colaboradores ou locais com prefixo "IPMJP - "), seguida de **Equipamento**; Operador tende a curto (username); Ação é badge com texto médio |
| Fonte real Plus Jakarta Sans ~20–30% mais larga que fallbacks (lição 036–043); padding real de `.5rem` (16px/coluna); conjunto único em px sem media query de colunas (lição 041); tooltips `data-bs-toggle="tooltip"` auto-inicializados em `base.html`/`main.js` (mecanismo das 042/043/044) | Premissas de dimensionamento e mecanismos validados |
| Testes existentes: `test_rbac.py` menciona dashboard (gates/strings de páginas) — **baseline: nenhum teste dedicado à tabela do dashboard** (varredura em `tests/`) | Suíte como regressão; run focado definido no plan |

## Decisões registradas pelo solicitante (2026-09-26)

- **C-1**: **NÃO fixar percentuais na spec** — larguras determinadas pela implementação após análise do HTML/CSS/comportamento atual (padrão 036–044).
- **C-2** (prioridade do pedido, seções 3/6/8/9): **Equipamento, Destino e Operador amplos** (colunas textuais de maior prioridade), com Destino e Equipamento entre as maiores parcelas (nomes de colaboradores/locais e descrições de bens são os textos mais longos); Operador amplo o suficiente para o nome em uma linha, sem monopolizar espaço. Proporções exatas decididas pela implementação pelo conteúdo real (seção 15).
- **C-3** (seções 2/14): a tabela deve ocupar praticamente toda a largura útil disponível, sem grandes vazios, sem colunas excessivamente comprimidas, sem larguras iguais para todas as colunas e sem tabela menor que o container quando há espaço.
- **C-4** (prioridade do pedido, seções 4–9/11): valores em **uma única linha** sempre que a largura permitir — Data (16 caracteres, nowrap já existente), Tombamento completo (badge íntegro), Equipamento, Ação (badge), Destino, Operador e títulos do cabeçalho; antes de permitir quebra, esgotar o espaço horizontal e reduzir espaços internos desnecessários (seções 11/14/16). A coluna Ações permanece compacta e estável (C-5).
- **C-5** (seção 10): **Ações compacta** — somente o espaço dos dois botões-ícone existentes; o economizado é redistribuído para Equipamento/Destino/Operador; sem aumento artificial.
- **C-6** (implícita do pedido, seção 23): `table-layout` (fixed vs auto) é decisão da implementação com base na análise — não aplicado automaticamente.
- **C-7** (seções 24/25/26): escopo exclusivamente visual/layout — movimentações, dashboard, KPIs, cards, filtros, banco, API e regras de negócio permanecem exatamente como estão; nenhum conteúdo removido; nenhuma outra tela ou seção do dashboard alterada.

## Clarifications

### Session 2026-09-26

- Q: Quando um valor textual (Equipamento ou Destino) não couber na largura da coluna, qual mecanismo de truncamento/consulta usar? → A: Corte controlado (ellipsis) + tooltip Bootstrap (`data-bs-toggle="tooltip"`), mesmo mecanismo das specs 042/043/044 — inicialização existente (base.html/main.js), zero JS novo; leitura confortável do valor completo (nomes completos consultáveis também na ficha do bem/movimentação). Nunca `overflow: hidden`/`ellipsis` sem acesso ao conteúdo (seção 13 do pedido).
- Q: O badge da coluna Ação ("Entrada por Aquisição", ~25 caracteres) pode quebrar em duas linhas em viewport intermediária? → A: A coluna recebe largura suficiente para os rótulos reais em uma linha nas larguras alvo; o badge mantém suas propriedades (`.badge-soft-primary`, fonte .68rem) — em viewport muito estreita, vale o comportamento responsivo geral (rolagem confinada ao `table-responsive`), sem regras globais de badge.
- Q: O link do Equipamento e o span do Operador usam classes globais (`fw-semibold`, `text-muted small`) — como tratar sem CSS global? → A: A classe de escopo própria da 046 (padrão da família) aplica as larguras pela célula (`td`/`th`) e o controle de linha/truncamento por span interno quando necessário; nenhuma classe global é alterada e `style.css` permanece intocado (padrão 042–044).
- Q: A validação da 046 deve incluir script automatizado de medição local (padrão `validar_local.py` das specs 039/042/044), além da inspeção manual em `validacao.md`? → A: Sim — script automatizado de medição local + inspeção manual: a evidência do SC-007 inclui medição reproduzível antes/depois (larguras por coluna, quebras de linha, alinhamento cabeçalho/corpo) gerada pelo script no padrão da família, complementada pela inspeção visual nos cenários do pedido; o script é ferramenta de validação pontual, não teste pytest da suíte.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Linha única e aproveitamento horizontal no Fluxo Recente (Priority: P1)

Um operador abre a página inicial "Visão Geral do Patrimônio" e vê a tabela "Fluxo Recente de Movimentações" ocupando praticamente toda a largura útil do card, com cada valor predominando em **uma única linha**: data/hora completa, tombamento íntegro, nome do equipamento sem quebra, rótulo da ação inteiro no badge, destino completo (colaborador ou local) e nome do operador sem quebra — leitura horizontal rápida das últimas movimentações do acervo.

**Why this priority**: é o objetivo central do pedido — leitura horizontal do feed de movimentações, a seção final e mais utilizada do dashboard.

**Independent Test**: abrir `/` em desktop e inspecionar/medir o aproveitamento da largura e a quantidade de quebras por linha (comparação antes/depois).

**Acceptance Scenarios**:

1. **Given** movimentações recentes registradas, **When** a tabela é exibida em desktop, **Then** ela ocupa praticamente toda a largura útil do card, com Equipamento, Destino e Operador dominando o espaço e Data/Tombamento/Ação/Ações compactos.
2. **Given** qualquer linha do feed, **When** exibida em largura suficiente, **Then** Data (data e hora juntas), Tombamento (badge íntegro), Equipamento, Ação (badge inteiro), Destino (colaborador **ou** local/"Estoque" completos) e Operador aparecem cada um em uma única linha, sem quebra (C-4).
3. **Given** um valor textual excepcionalmente longo (ex.: nome de colaborador ou local extenso), **When** a largura da coluna não bastar mesmo com a distribuição otimizada, **Then** o corte é controlado (ellipsis + tooltip com o valor completo), nunca uma quebra desorganizada nem conteúdo inacessível.

### User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

Um gestor consulta o dashboard de um notebook ou tablet (e com zoom do navegador) e a tabela continua utilizável: distribuição proporcional preservada, rolagem confinada ao contêiner da tabela quando necessário, ações acessíveis e nenhum conteúdo cortado sem consulta.

**Why this priority**: preservar a responsividade é requisito explícito (seções 17–19); o dashboard é acessado de vários dispositivos.

**Independent Test**: reduzir a viewport (e variar o zoom 80%–200%) e verificar comportamento, alinhamento e acessibilidade dos controles.

**Acceptance Scenarios**:

1. **Given** viewport de notebook/tablet, **When** a tabela é exibida, **Then** a distribuição permanece proporcional, sem sobreposição e com as ações acessíveis.
2. **Given** viewport de celular, **When** a tabela não couber, **Then** a rolagem horizontal fica confinada ao contêiner da tabela (comportamento responsivo existente), sem esconder colunas, sem fonte excessivamente reduzida e com todos os controles utilizáveis.
3. **Given** zoom do navegador na faixa 80%–200%, **When** a página é renderizada, **Then** o layout permanece íntegro (sem desalinhamento cabeçalho/corpo, sem overflow indevido da página).

### Edge Cases

- **Movimentação com Termo de Cautela**: a coluna Ações exibe DOIS botões-ícone (imprimir termo + ver bem) — a largura compacta deve acomodar os dois; movimentação sem termo exibe apenas "Ver Bem" (coluna não deve parecer desalinhada nem ocupar mais por causa de uma linha).
- **Destino "Estoque"** (fallback curto) ao lado de destinos longos ("IPMJP - Fundo Municipal de Previdência") na mesma tabela: coluna dimensionada para os casos reais, fallback curto não gera desperdício.
- **Nenhuma movimentação recente**: o estado vazio "Nenhuma movimentação recente" permanece idêntico (a tabela nem é renderizada) — intocado.
- **Nome de operador curto** (ex.: "admin") ao lado de equipamentos longos: operador recebe largura suficiente sem monopolizar espaço (C-2).
- **Uma única movimentação na tabela** (feed recém-iniciado): larguras estáveis independentemente da quantidade de linhas (até 8 linhas — limite do feed).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tabela "Fluxo Recente de Movimentações" MUST aproveitar praticamente toda a largura útil disponível do card onde houver espaço (C-3), sem grandes vazios, sem colunas excessivamente comprimidas, sem padding horizontal exagerado e sem larguras iguais para todas as colunas.
- **FR-002**: A distribuição de larguras MUST ser proporcional à natureza do conteúdo, seguindo C-2 (Equipamento, Destino e Operador amplos — Destino e Equipamento entre as maiores parcelas; Data, Tombamento e Ação compactos e suficientes; Ações mínima) — dimensionada pela implementação após análise (C-1), sem percentuais fixados por esta spec.
- **FR-003**: A coluna Data MUST manter a data/hora completa (`dd/mm/aaaa hh:mm`) em **uma única linha** nas larguras alvo (C-4), preservando o `text-nowrap` existente, sem quebra entre data e hora e sem ocupar espaço excessivo.
- **FR-004**: A coluna Tombamento MUST manter o código patrimonial completo e legível em **uma única linha** (C-4), com o badge existente íntegro (monoespaçada, borda, contraste e regras globais de `.tag-badge` preservadas — incluindo o fallback de ellipsis ≤479.98px), sem quebra interna do código e sem largura excessiva.
- **FR-005**: A coluna Equipamento MUST receber espaço horizontal significativo (C-2) e manter o nome do equipamento em **uma única linha** sempre que possível (C-4); quando não couber, corte controlado por **ellipsis + tooltip Bootstrap** — nunca quebra desorganizada, nunca conteúdo sem consulta (clarificação); o link para a ficha do bem e o peso visual (`fw-semibold`) permanecem.
- **FR-006**: A coluna Ação MUST manter o rótulo completo do tipo de movimentação (ex.: "Entrada por Aquisição", "Alocação / Cautela", "Transferência de Local") em **uma única linha** nas larguras alvo (C-4), com o badge existente (`.badge-soft-primary`, fonte .68rem) íntegro — sem regra global de badge e sem quebra do rótulo em viewport intermediária (clarificação); sem largura excessiva (seção 7).
- **FR-007**: A coluna Destino MUST receber uma das maiores parcelas da largura disponível (C-2) e manter o destino em **uma única linha** sempre que possível (C-4) — tanto o formato colaborador (ícone + nome) quanto o formato local/"Estoque" (ícone + nome); quando não couber, corte controlado por **ellipsis + tooltip Bootstrap**; fallback "Estoque" e ícones existentes preservados; sem compressão desnecessária (seção 8 do pedido).
- **FR-008**: A coluna Operador MUST receber espaço adequado para manter o nome do operador em **uma única linha** sempre que possível (C-2/C-4); quando não couber, corte controlado por **ellipsis + tooltip Bootstrap**; sem ficar excessivamente estreita enquanto houver espaço disponível (seção 9) e sem monopolizar espaço que pertença a Equipamento/Destino (C-2).
- **FR-009**: A coluna Ações MUST permanecer compacta (C-5): somente o espaço necessário para os botões-ícone existentes — **incluindo o par (Termo + Ver Bem)** das movimentações com termo — preservando o `text-nowrap` existente, visibilidade, clicabilidade, alinhamento à direita e acessibilidade; sem aumento artificial para preencher espaço (seção 10).
- **FR-010**: Nenhum truncamento/ocultação MAY ser aplicado sem mecanismo de consulta (seção 13): todo corte controlado usa tooltip Bootstrap (clarificação); badges de tombamento nunca recebem ellipsis novo além do global existente (lição da 042); sem truncamento em desktop quando há espaço suficiente.
- **FR-011**: Cabeçalho e corpo MUST compartilhar exatamente a mesma estrutura de colunas (sem deslocamento entre thead e tbody, sem `width` aplicado somente ao `<td>`); os sete títulos MUST permanecer legíveis e em linha única quando houver espaço (seção 20), sem hifenização, com alinhamento consistente entre cabeçalho, valores e controles (seção 21), preservando o alinhamento à direita do header de Ações.
- **FR-012**: A solução MUST usar estrutura/classes específicas desta tabela (padrão da família 036–044): **nenhuma regra global** em `.table`/`.tag-badge`/`.badge`/`.btn-ghost`/componentes compartilhados (a mesma combinação serve dezenas de telas — inclusive a OUTRA tabela deste mesmo template, L182–200), CSS novo apenas com seletor próprio desta tela/tabela, sem duplicar estilos e sem bump de cache global; `style.css` permanece intocado.
- **FR-013**: A regra geral (C-4/seções 11/14/16) MUST ser respeitada: primeiro evitar quebra, depois aproveitar o espaço horizontal, reduzir espaços internos excessivos, manter compactas as colunas curtas e usar o economizado nas textuais — quebra de texto apenas em último caso, quando a largura real não bastar; sem redução excessiva de fonte como solução principal (seção 19) e sem eliminação de espaçamento necessário à legibilidade/acessibilidade.
- **FR-014**: A solução MUST manter ou melhorar a responsividade em desktop grande/médio, notebook, tablet, celular, larguras intermediárias e zoom (faixa 80%–200%, precedentes 036–044), sem overflow indevido; em larguras mínimas, rolagem confinada ao contêiner da tabela (padrão `table-responsive` existente), sem sobreposição, sem esconder colunas, sem fonte excessivamente pequena, sem conteúdo cortado sem acesso ao valor completo e com os controles acessíveis (seções 17–19).
- **FR-015**: Nenhuma funcionalidade MAY ser alterada: movimentações, patrimônio, dashboard (KPIs, distribuições, inconsistências, integridade), links de termo e de bem, banco, API, endpoints, models, schemas, permissões, autenticação e auditoria permanecem intocados (seção 24 do pedido).
- **FR-016**: Nenhum conteúdo exibido MAY ser removido, escondido ou alterado: data/hora, tombamento, nome do equipamento, badge da ação, destino (colaborador/local/"Estoque"), operador, ícones e ambos os botões de ação permanecem presentes (seção 26).
- **FR-017**: A alteração MUST ficar restrita aos arquivos estritamente necessários desta tela/tabela; as telas das specs 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações), 040 (custodiantes), 041 (Relatório Contábil-Físico), 042 (Trilha de Auditoria), 043 (Usuários), 044 (Etiquetas), a **outra tabela do próprio dashboard** ("Necessitam de atenção", L182–200), os demais cards/seções do dashboard e quaisquer outras telas NÃO podem ser afetados (seção 25 do pedido). Sem `@media print` novo (R10 da 043 — o dashboard não é tela-relatório).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em desktop, a tabela ocupa ≥ 95% da largura útil do card/container (verificável por medição da renderização) — referência indicativa, sujeita ao julgamento visual.
- **SC-002**: As colunas textuais (Equipamento + Destino + Operador) ocupam juntas a maior parte da largura da tabela (referência indicativa: mais da metade), medida em desktop.
- **SC-003**: Zero desalinhamento entre cabeçalhos e valores em todas as larguras validadas; títulos em linha única quando há espaço.
- **SC-004**: Zero overflow horizontal da página em larguras a partir de notebook; em tablet/celular, qualquer rolagem fica restrita ao contêiner da tabela.
- **SC-005**: Zero sobreposição, zero truncamento sem tooltip e zero quebras inadequadas nas larguras validadas; data/hora, tombamento, equipamento, ação (badge), destino e operador sem quebra em desktop.
- **SC-006**: A suíte de testes existente permanece 100% verde (nenhuma regressão funcional).
- **SC-007**: Validação registrada em `specs/046-dashboard-larguras-colunas/validacao.md` no formato das 036–044: suíte pytest 100% verde E inspeção manual com medição nos cenários do pedido (desktop grande/médio, notebook, tablet, celular) e faixa de zoom 80%–200%, com resultado de cada cenário e comparação antes/depois **E script automatizado de medição local** (`validar_local.py`, padrão das 039/042/044) evidenciando larguras por coluna, quebras de linha e alinhamento cabeçalho/corpo antes/depois (clarificação 2026-09-26).

## Assumptions

- Bootstrap 5.3 e `style.css` permanecem a base; nenhuma dependência nova.
- O mecanismo responsivo do projeto refere-se ao padrão validado nas 036–044 (layout determinístico com larguras por classe escopada + `min-width` com rolagem confinada ao `table-responsive`); conjunto único em px sem media query de colunas (lição da 041), com pisos calibrados para a Plus Jakarta Sans (×1,25–1,30).
- Tooltips: `data-bs-toggle="tooltip"` (decisão do solicitante na clarificação — mesmo mecanismo das 042/043/044; auto-inicializado em `base.html`/`main.js`).
- `.tag-badge` já traz `overflow: hidden; text-overflow: ellipsis; max-width: 100%` globais (e `max-width:140px` ≤479.98px): não recebem ellipsis novo; a coluna dimensionada pela implementação cobre os códigos reais nas larguras alvo.
- A tabela exibe as **últimas 8 movimentações** (`DashboardService.get_stats` → `recent_movements` limit 8); larguras dimensionadas pelo conteúdo real dessas linhas.
- Os rótulos da coluna Ação são os labels PT do `MovementType` ("Entrada por Aquisição", "Alocação / Cautela", "Transferência de Local", "Envio para Manutenção", "Retorno de Manutenção", "Devolução ao Estoque", "Baixa / Descarte", "Atualização de Estado") — o mais longo define o piso da coluna.
- O destino exibe colaborador (custódia) OU local/"Estoque"; os dois formatos convivem na mesma coluna (estrutura if/else do template preservada).
- Header, KPIs, cards de distribuição, card de integridade, tabela "Necessitam de atenção", botão "Ver Tudo" e estado vazio são intocados; a tabela exibe o feed corrente do serviço.

## Fora de escopo

- Qualquer mudança funcional (movimentações, patrimônio, dashboard, CRUD, auditoria, permissões, restauração de dados).
- Outras tabelas/telas (036–044 e demais), a tabela "Necessitam de atenção" do próprio dashboard, KPIs, cards, menu, header e estado vazio.
- O layout global/container da página (seção 16: se o container já estiver adequado, modificar somente a distribuição da tabela).
- Redesenho visual além da distribuição de larguras, quebras, truncamentos controlados e alinhamentos.
- Novos testes automatizados de UI (seção 29 do pedido: apenas executar os existentes; sem testes artificiais).
