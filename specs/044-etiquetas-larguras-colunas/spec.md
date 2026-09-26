# Feature Specification: Ajuste Responsivo da Tabela "Etiquetas de Patrimônio"

**Feature Branch**: `044-etiquetas-larguras-colunas`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Ajustar exclusivamente o layout da tabela de seleção da tela **"Etiquetas de Patrimônio"** (`/assets/labels`): aproveitar o máximo possível da largura horizontal disponível e **manter os valores das colunas Tombamento, Equipamento / Modelo, Setor e Localização em uma única linha horizontal sempre que a largura permitir** (regra prioritária do pedido, seções 3/9/14/16), com truncamento controlado + tooltip quando necessário e responsividade preservada ou melhorada. Mesmo princípio das specs 036–043: análise antes de alterar, implementação cirúrgica — nenhuma regra de geração/impressão de etiquetas, seleção, filtros, QR Code, tombamento, equipamento, setor, localização, banco, API ou regra de negócio é alterada. **A área de impressão de etiquetas (`#labels-print-area`) e seu comportamento de impressão são intocados.**

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| Tela "Etiquetas de Patrimônio" = `app/web/templates/assets/labels.html` (rota `/assets/labels` em `app/web/routes.py:381`, gate `patrimonio.visualizar`, render `routes.py:449`) | Superfície única a alterar (tabela de seleção apenas) |
| Tabela de seleção tem **5 colunas**: **checkbox** (`th` com `style="width:36px;"`; `input.form-check-input.asset-check` por linha), **Tombamento** (`span.tag-badge` — monoespaçada bold, `.78rem`, `inline-block`, `max-width:100%`, ellipsis já embutidos em `style.css:491`; no tema claro reduz a `max-width:140px` ≤479.98px em `style.css:1027`), **Equipamento / Modelo** (duas linhas: `span.fw-semibold` com nome + `div.text-muted` de `.76rem` com marca/modelo — `div` força a segunda linha por estrutura, não por largura), **Setor** (`td.small.text-muted` — `a.location.department` ou "—" quando ausente), **Localização** (`td.small.text-muted` — `a.location.name` ou "—" quando ausente) | Nuances protegidas nos FRs: coluna do checkbox, badge de tombamento com regras globais próprias, estrutura de 2 linhas no Equipamento, fallbacks "—" |
| Sem `<colgroup>` nem classes de largura; container `card no-print` > `card-header-clean` (contador) > `table-responsive` > `table align-middle` | Distribuição atual vem do layout automático do Bootstrap; `table-responsive` já confina rolagem |
| `table.align-middle` de `table-responsive` é a tabela de maior uso do sistema (036: conferência; 037: inventários; 038: equipamentos; 040: custodiantes) — **qualquer regra global em `.table` mudaria todas essas telas** | Obriga classe de escopo própria (padrão da família) |
| Filtros (mesmos da listagem de equipamentos), toolbar de seleção (`#select-all-page`, `#sel-count`, `#clear-selection`, `#print-selected`), contador "Mostrando N de M" e estado vazio "Nenhum equipamento encontrado" são `no-print` | Intocados; comentários novos não citam nomes de controles do header/toolbar (lição `b75ba99`) |
| Folha de etiquetas `#labels-print-area` > `.label-card` (QR `data-label-qr` + `.label-info` logo/tombamento) + JS inline de seleção em lote (estado via URL `?selected=`, atualização ao vivo da folha) | **DOMÍNIO PROTEGIDO da feature 013**: não tocar |
| `style.css:1605–1645` tem `@media print` exclusivo de etiquetas (`body:has(#labels-print-area) ...`) e comentário C1–C10 dos relatórios que cita explicitamente etiquetas/Termo como fora dos seletores | A tela NÃO é tela-relatório → **sem `@media print` novo** (R10 da 043); `style.css` intocado |
| `style.css:1595` (contraste de `.asset-check`/`#select-all-page` no tema claro) e o JS inline referenciam essas classes | Classes/id existentes preservados — a 044 só adiciona regras escopadas de largura |
| Conteúdo real típico: Tombamento ~`IMPJP1456`/`IMPJP679450` (7–13 caracteres monoespaçados), Equipamento "Computador Dell OptiPlex 7090" + "Dell OptiPlex" na segunda linha, Setor "Setor de Contabilidade"/"Gabinete da Superintendência", Localização "IPMJP - Fundo Municipal de Previdência"/"IPMJP - Setor de Análise de Benefícios" | Localização tende a ser o texto mais longo (prefixo "IPMJP - " sempre presente quando há local) |
| Lições da família 036–043 incorporadas: fonte real (Plus Jakarta Sans) ~20–30% mais larga que fallbacks; padding real `.5rem .5rem` (16px/coluna); conjunto único em px sem media query de colunas; tooltips via `data-bs-toggle="tooltip"` (auto-inicializados em `base.html:329–333`/`main.js`); spans internos de ellipsis (`display:inline-block; max-width:100%; vertical-align:bottom`) nas 042/043; badges nunca recebem ellipsis | Premissas de dimensionamento e mecanismos validados |
| Testes existentes: `test_help.py` (renderiza listagens), `test_rbac.py` (gates e strings de páginas) — **baseline: nenhum teste dedicado à página de etiquetas** (varredura em `tests/`) | Suíte como regressão (SC-006); run focado definido no plan |

## Decisões registradas pelo solicitante (2026-09-25)

- **C-1**: **NÃO fixar percentuais na spec** — larguras determinadas pela implementação após análise do HTML/CSS/comportamento atual (padrão 036–043).
- **C-2**: prioridade de espaço: **Tombamento compacto, mas suficiente** para o código completo em uma linha; **Equipamento / Modelo, Setor e Localização amplos**, com Localização entre as maiores parcelas (prefixo "IPMJP - " torna seus valores os mais longos). Proporções exatas decididas pela implementação pelo conteúdo real (seção 8).
- **C-3**: a tabela deve ocupar praticamente toda a largura útil disponível, sem grandes vazios, sem colunas excessivamente estreitas, sem padding horizontal exagerado e sem larguras iguais para todas as colunas.
- **C-4 (regra prioritária da spec, seções 3/9/14/16)**: valores em **uma única linha** sempre que a largura permitir — combinando nowrap/estratégia equivalente, largura flexível, **truncamento controlado com tooltip quando necessário** (nunca texto que desapareça sem consulta — seção 11) e comportamento responsivo em telas pequenas; antes de permitir quebra, esgotar o espaço horizontal e remover espaços internos desnecessários (seções 14/16).
- **C-5** (implícita do pedido, seção 21): `table-layout` (fixed vs auto) é decisão da implementação com base na análise — não aplicado automaticamente.
- **C-6 (seções 24/25/26)**: escopo exclusivamente visual/layout — seleção em lote, filtros, geração e impressão de etiquetas, QR Code e demais funcionalidades permanecem exatamente como estão; nenhum conteúdo removido; nenhuma outra tela alterada.
- **C-7 (interpretação da seção 5 vs. análise do template)**: a segunda linha de Equipamento / Modelo (marca/modelo em fonte pequena) é **estrutural** (`div` própria), não quebra de linha do valor principal — preservada como está; a exigência de linha única aplica-se ao **nome do equipamento** e às demais colunas textuais.

## Clarifications

### Session 2026-09-25

- Q: Quando um valor textual (Equipamento, Setor ou Localização) não couber na largura da coluna, qual mecanismo de truncamento/consulta usar? → A: Corte controlado (ellipsis) + tooltip Bootstrap (`data-bs-toggle="tooltip"`), mesmo mecanismo das specs 042/043 — inicialização existente (base.html/main.js), zero JS novo; leitura confortável do valor completo. Nunca `overflow: hidden`/`ellipsis` sem acesso ao conteúdo (seção 11 do pedido).
- Q: O Tombamento usa `.tag-badge` com `max-width:140px` global até 479.98px (style.css:1027) e ellipsis embutido — como tratar? → A: A coluna recebe largura suficiente para o código completo em uma linha nas larguras alvo; o comportamento global do badge não é alterado; em viewport muito estreita, o ellipsis existente do badge é o fallback aceitável (código completo consultável na ficha do bem).
- Q: Na linha auxiliar de marca/modelo da coluna Equipamento / Modelo, como tratar estouro de largura? → A: Ellipsis + tooltip Bootstrap, mesmo tratamento do nome — corte controlado com consulta, coerente com C-4 (nenhum texto desaparece sem mecanismo de consulta; padrão da 043 para o full_name).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Linha única e aproveitamento horizontal na seleção de etiquetas (Priority: P1)

Um operador abre "Etiquetas de Patrimônio" e vê a tabela de seleção ocupando praticamente toda a largura útil do card, com cada valor predominando em **uma única linha**: tombamento completo e legível, nome do equipamento sem quebra (com marca/modelo na linha auxiliar), setor completo e localização completa — leitura horizontal rápida para escolher os bens que receberão etiquetas.

**Why this priority**: é o objetivo central do pedido — leitura horizontal da seleção de etiquetas.

**Independent Test**: abrir `/assets/labels` em desktop e inspecionar/medir o aproveitamento da largura e a quantidade de quebras por linha (comparação antes/depois).

**Acceptance Scenarios**:

1. **Given** equipamentos listados, **When** a tabela é exibida em desktop, **Then** ela ocupa praticamente toda a largura útil do card, com Equipamento, Setor e Localização dominando o espaço e Tombamento compacto.
2. **Given** qualquer linha da listagem, **When** exibida em largura suficiente, **Then** Tombamento (badge íntegro), Equipamento (nome completo em uma linha), Setor e Localização aparecem cada um em uma única linha, sem quebra (C-4).
3. **Given** uma localização longa (ex.: "IPMJP - Setor de Análise de Benefícios"), **When** a tabela é exibida em desktop, **Then** o valor aparece completo em uma linha (sem quebra desorganizada); se não couber em viewport menor, corte controlado com tooltip — nunca oculto sem mecanismo de consulta (seção 11).
4. **Given** um equipamento com marca e modelo, **When** a linha é exibida, **Then** o nome permanece em uma linha e a linha auxiliar (marca/modelo) permanece em sua estrutura própria (C-7), sem layout quebrado.

---

### User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

O operador acessa a seleção de etiquetas de notebook, tablet ou celular (e/ou zoom variado): a tabela mantém a leitura prioritariamente horizontal e, quando a largura realmente não bastar, usa o comportamento responsivo adequado (rolagem confinada, truncamento com tooltip) — sem sobreposição, sem fonte minúscula, sem conteúdo inacessível, com checkboxes e controles de seleção utilizáveis.

**Why this priority**: a seleção de etiquetas é feita em diversos dispositivos; a tabela não pode depender de uma única resolução (seções 12/15/16 do pedido).

**Independent Test**: abrir `/assets/labels` em larguras variadas (desktop, notebook, tablet, celular e zoom) e verificar adaptação, legibilidade, acessibilidade dos controles e consulta aos valores truncados.

**Acceptance Scenarios**:

1. **Given** viewport de notebook/tablet, **When** a tabela é exibida, **Then** a distribuição permanece proporcional com o máximo em linha única, sem sobreposição nem colunas colapsadas; antes de quebrar texto, espaços internos desnecessários são reduzidos (seções 14/16).
2. **Given** viewport de celular, **When** a tabela é exibida (5 colunas), **Then** o comportamento responsivo do projeto se aplica (rolagem confinada ao contêiner quando inevitável), com checkboxes acessíveis e valores truncados consultáveis via tooltip.
3. **Given** zoom do navegador variado, **When** a tabela é exibida, **Then** os critérios de legibilidade, linha única e ausência de sobreposição se mantêm.

---

### Edge Cases

- **Linha do checkbox**: coluna estreita estável (36px atuais), área clicável preservada, alinhada com o cabeçalho; o checkbox permanece o controle funcional de seleção.
- **Tombamento longo** (ex.: `IMPJP679450`): código completo em uma linha nas larguras alvo; badge `.tag-badge` íntegro (regras globais preservadas, incluindo `max-width:140px` ≤479.98px com ellipsis como fallback).
- **Equipamento sem marca/modelo**: segunda linha auxiliar renderiza vazia — estrutura preservada, sem buraco visual novo.
- **Marca/modelo longa**: linha auxiliar segue o mesmo tratamento do nome — corte controlado + tooltip (clarificação), nunca texto sem consulta.
- **Setor ausente**: fallback "—" preservado (small muted).
- **Localização ausente**: fallback "—" preservado (small muted).
- **Localização longa** ("IPMJP - Fundo Municipal de Previdência"): maior parcela de espaço entre as textuais; tooltip quando não couber.
- **Estado vazio / filtros**: "Nenhum equipamento encontrado" + texto de ajuste inalterados.
- **Impressão de etiquetas**: `#labels-print-area`/`.labels-sheet`/`.label-card` e o `@media print` de etiquetas em `style.css` permanecem intocados — a tabela de seleção não recebe regras de impressão novas; seleção em lote (`?selected=`, contadores, folha ao vivo) idem.
- **Tema claro/escuro**: nenhuma cor nova; contraste dos checkboxes (incluindo regra do tema claro) preservado.
- **Uma única linha na tabela**: distribuição estável por coluna (não por conteúdo da linha).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tabela MUST aproveitar praticamente toda a largura útil disponível do container onde houver espaço (C-3), sem grandes vazios, sem colunas excessivamente estreitas, sem padding horizontal exagerado e sem larguras iguais para todas as colunas.
- **FR-002**: A distribuição de larguras MUST ser proporcional à natureza do conteúdo, seguindo C-2 (Tombamento compacto mas suficiente; Equipamento, Setor e Localização amplos, com Localização entre as maiores parcelas) — dimensionada pela implementação após análise (C-1), sem percentuais fixados por esta spec.
- **FR-003**: A coluna do checkbox MUST permanecer estreita e estável (largura mínima para o controle clicável), sem herdar espaço das colunas de conteúdo e com o cabeçalho vazio alinhado às células.
- **FR-004**: A coluna Tombamento MUST manter o código patrimonial completo e legível em **uma única linha** nas larguras alvo (C-2), com o badge existente íntegro (monoespaçada, borda, contraste e regras globais de `.tag-badge` preservadas — incluindo o fallback de ellipsis ≤479.98px), sem quebra interna do código e sem ocupar espaço excessivo.
- **FR-005**: A coluna Equipamento / Modelo MUST receber espaço horizontal significativo e manter o **nome do equipamento em uma única linha** sempre que possível (C-4); quando não couber, corte controlado por **ellipsis + tooltip Bootstrap** — nunca quebra desorganizada, nunca conteúdo sem consulta (clarificação). A linha auxiliar de marca/modelo (fonte pequena) MUST permanecer em sua estrutura própria e, quando exceder a largura, também usa corte controlado por **ellipsis + tooltip Bootstrap** — mesmo tratamento do nome (clarificação; C-7).
- **FR-006**: A coluna Setor MUST receber espaço suficiente para manter os nomes dos setores em **uma única linha** sempre que a viewport permitir (C-4); quando não couber, corte controlado por **ellipsis + tooltip Bootstrap**; sem largura excessivamente pequena apenas para economizar espaço (seção 6); fallback "—" preservado.
- **FR-007**: A coluna Localização MUST receber uma das maiores parcelas da largura disponível (C-2) e manter os nomes dos locais em **uma única linha** sempre que possível (C-4); quando não couber, corte controlado por **ellipsis + tooltip Bootstrap**; sem compressão desnecessária (seção 7); fallback "—" preservado.
- **FR-008**: Nenhum truncamento/ocultação MAY ser aplicado sem mecanismo de consulta (seção 11): todo corte controlado usa tooltip Bootstrap (clarificação); badges de tombamento nunca recebem ellipsis novo além do global existente (lição da 042: dado funcional íntegro); sem truncamento em desktop quando há espaço suficiente.
- **FR-009**: Cabeçalho e corpo MUST compartilhar exatamente a mesma estrutura de colunas (sem deslocamento entre thead e tbody, sem `width` aplicado somente ao `<td>` — o `style="width:36px"` atual do `th` é absorvido pela nova estrutura sem perda de alinhamento); os títulos MUST permanecer legíveis e em linha única quando houver espaço; alinhamento consistente entre cabeçalho, valores e checkbox (seção 19), sem centralizações artificiais.
- **FR-010**: A solução MUST usar estrutura/classes específicas desta tabela (padrão da família 036–043): **nenhuma regra global** em `.table`/`.tag-badge`/`.badge`/componentes compartilhados (a mesma combinação serve dezenas de telas), CSS novo apenas com seletor próprio desta tela, sem duplicar estilos e sem bump de cache global; `style.css` permanece intocado.
- **FR-011**: A regra geral (C-4/seções 14/16) MUST ser respeitada: primeiro evitar quebra, depois aproveitar o espaço horizontal, reduzir espaços internos excessivos, manter compactas as colunas curtas e usar o economizado nas textuais — quebra de texto apenas em último caso, quando a largura real não bastar; sem redução excessiva de fonte como solução principal (seção 23) e sem eliminação de espaçamento necessário à legibilidade/acessibilidade (seção 22).
- **FR-012**: A solução MUST manter ou melhorar a responsividade em desktop grande/médio, notebook, tablet, celular, larguras intermediárias e zoom (faixa 80%–200%, precedentes 036–043), sem overflow indevido; em larguras mínimas, rolagem confinada ao contêiner da tabela (padrão `table-responsive` existente), sem sobreposição, sem fonte excessivamente pequena, sem conteúdo cortado sem acesso ao valor completo e com checkboxes/controles acessíveis (seções 15/16).
- **FR-013**: A tela não é tela-relatório e não recebe novas regras de impressão: **nenhum `@media print` novo** (R10 da 043); a folha `#labels-print-area`, as classes `.labels-sheet`/`.label-card`, o `@media print` de etiquetas em `style.css` e o comportamento de impressão da 013 permanecem intocados; a tabela de seleção e a toolbar são `no-print` e seguem como estão.
- **FR-014**: Nenhuma funcionalidade MAY ser alterada: seleção em lote (checkboxes, `?selected=`, seleção total, limpeza, contagem), filtros, busca, geração e impressão de etiquetas, QR Code, tombamento, equipamento, setor, localização, API, endpoints, banco, models, schemas, permissões, autenticação e auditoria permanecem intocados (seção 24 do pedido).
- **FR-015**: Nenhum conteúdo exibido MAY ser removido, escondido ou alterado: checkbox, tombamento, nome do equipamento, marca/modelo, setor, localização, fallbacks "—" e ícones permanecem presentes (seção 26).
- **FR-016**: A alteração MUST ficar restrita aos arquivos estritamente necessários desta tela; as telas das specs 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações), 040 (custodiantes), 041 (Relatório Contábil-Físico), 042 (Trilha de Auditoria), 043 (Usuários) e demais telas/componentes NÃO podem ser afetados (seção 25 do pedido).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em desktop, a tabela ocupa ≥ 95% da largura útil do card/container (verificável por medição da renderização) — referência indicativa, sujeita ao julgamento visual.
- **SC-002**: As colunas textuais (Equipamento + Setor + Localização) ocupam juntas a maior parte da largura da tabela (referência indicativa: mais da metade), medida em desktop.
- **SC-003**: Zero desalinhamento entre cabeçalhos e valores em todas as larguras validadas; títulos em linha única quando há espaço.
- **SC-004**: Zero overflow horizontal da página em larguras a partir de notebook; em tablet/celular, qualquer rolagem fica restrita ao contêiner da tabela.
- **SC-005**: Zero sobreposição, zero truncamento sem tooltip e zero quebras inadequadas nas larguras validadas; tombamento, nomes de equipamentos, setores e localizações sem quebra em desktop.
- **SC-006**: A suíte de testes existente permanece 100% verde (nenhuma regressão funcional).
- **SC-007**: Validação registrada em `specs/044-etiquetas-larguras-colunas/validacao.md` no formato das 036–043: suíte pytest 100% verde E inspeção manual com medição nos cenários do pedido (desktop grande/médio, notebook, tablet, celular) e faixa de zoom 80%–200%, com resultado de cada cenário e comparação antes/depois.

## Assumptions

- Bootstrap 5.3 e `style.css` permanecem a base; nenhuma dependência nova.
- O mecanismo responsivo do projeto refere-se ao padrão validado nas 036–043 (layout determinístico com larguras por classe escopada + `min-width` com rolagem confinada ao `table-responsive`); conjunto único em px sem media query de colunas (lição da 041), com pisos calibrados para a Plus Jakarta Sans (×1,25–1,30).
- Tooltips: `data-bs-toggle="tooltip"` (decisão do solicitante na clarificação — mesmo mecanismo das 042/043; auto-inicializado em `base.html`/`main.js`).
- `.tag-badge` já traz `overflow: hidden; text-overflow: ellipsis; max-width: 100%` globais (e `max-width:140px` ≤479.98px): não recebem ellipsis novo; a coluna dimensionada pela implementação cobre os códigos reais nas larguras alvo.
- A segunda linha de marca/modelo no Equipamento é estrutura de template (não quebra por largura) e permanece (C-7).
- Header, filtros, toolbar de seleção, folha de etiquetas e estado vazio são intocados; a tabela exibe o resultado corrente da busca/filtro.

## Fora de escopo

- Qualquer mudança funcional (seleção em lote, filtros, geração/impressão de etiquetas, QR Code, CRUD de patrimônio, auditoria, permissões).
- A folha de etiquetas (`#labels-print-area`), suas classes e o `@media print` de etiquetas em `style.css` — domínio da feature 013, intocados.
- Outras tabelas/telas (036–043 e demais), o layout global/container, filtros, toolbar, menu e estado vazio da própria tela.
- Redesenho visual além da distribuição de larguras, quebras, truncamentos controlados e alinhamentos.
- Novos testes automatizados de UI (seção 29 do pedido: apenas executar os existentes; sem testes artificiais).
