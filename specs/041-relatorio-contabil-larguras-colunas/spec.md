# Feature Specification: Ajuste Responsivo da Tabela "Relatório Contábil-Físico do Patrimônio"

**Feature Branch**: `041-relatorio-contabil-larguras-colunas`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Ajustar exclusivamente o layout da tabela da tela **"Relatório Contábil-Físico do Patrimônio"** (`/reports/inventory`): aproveitar o máximo possível da largura horizontal disponível, redistribuindo o espaço entre as 10 colunas (Tombamento, Descrição, Categoria, Status, Localização, Responsável, Data Compra, Valor Aquisição, Depreciação, Valor Atual). Colunas textuais **Descrição**, **Localização** e **Responsável** recebem prioridade; **Tombamento** e **Categoria** ficam intermediárias; **Status**, **Data Compra** e as 3 colunas monetárias permanecem compactas, com alinhamento consistente das monetárias. Mesmo princípio das specs 036–040: redistribuição inteligente, análise antes de alterar, implementação cirúrgica — nenhuma funcionalidade, dado, cálculo contábil, rota, exportação ou regra de negócio é alterada, e a impressão/PDF existente NÃO pode ser quebrada.

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| Tela "Relatório Contábil-Físico do Patrimônio" = `app/web/templates/reports/inventory.html` (rota `/reports/inventory` em `app/web/routes.py:1517`, gate `relatorios.visualizar`; template renderizado em routes.py:1558) | Superfície única a alterar |
| Tabela com exatamente as 10 colunas do pedido, em `thead`/`tbody` simétricos: **Tombamento** (`td.font-monospace.fw-bold`), **Descrição** (nome em `<strong>` + linha condicional `S/N` em `div` pequena quando há `serial_number`), **Categoria** (badge `badge-soft-gray`), **Status** (pill `status-pill-<valor>`), **Localização** (texto, fallback "Estoque Geral"), **Responsável** (texto, fallback "Livre"), **Data Compra** (`dd/mm/YYYY` ou "-"), **Valor Aquisição / Depreciação / Valor Atual** (`td.text-end small`, com `-XX%` vermelho na Depreciação e valor atual verde em negrito) | Nuances protegidas nos FRs: linha S/N condicional, fallbacks "Estoque Geral"/"Livre"/"-", cores semânticas e negrito da Valor Atual |
| Sem `<colgroup>`, sem classes de largura na tabela; container `card p-4 report-print` > `table-responsive` > `table table-bordered table-hover align-middle small mb-0` | Distribuição atual vem do layout automático (`table-layout: auto` do Bootstrap) — a tela deixa espaço sobrando em desktops largos porque o conteúdo dita a distribuição |
| Header com 2 controles ("Baixar CSV" condicional a `relatorios.exportar` + "Imprimir") em `page-header no-print`; cabeçalho interno do relatório (empresa + ano) e `border-bottom` acima da tabela | Fora do escopo — intocados (só a tabela) |
| Container global `base.html` (`container-fluid ... max-width:90%`) | Container **não alterado** (FR-012) |
| `style.css` não define larguras para esta tabela; bloco `@media print` de relatórios (C1–C10, L1650+) ancorado em `.report-print` é **compartilhado pelos 3 relatórios** (`movements_report.html`, `custodians_report.html`, `inventory.html`): `table-layout:auto!important`, `width:100%!important`, `white-space:normal!important`, `min-width:0` no `.table-responsive`, `font-size:8.5pt` | **CRÍTICO**: qualquer largura/min-width de tela para esta tabela MUST ser anulado ou neutralizado dentro de `@media print` para a 041 — sem editar regras compartilhadas nem bump de cache global (style.css versionado em base.html + SW allowlist) |
| `test_report_print_smoke.py` (L20: rota `/reports/inventory`), `test_help.py:109`, `test_rbac.py` (gate `relatorios.exportar` no CSV) e RBAC de template não devem ter strings novas introduzidas pelo `<style>` | Testes existentes executados como estão; nenhum nome de controle do header pode aparecer em comentários CSS/HTML (lição `b75ba99`) |
| Constitution I/X/XI/XII: escopo cirúrgico, interface consistente, docs fiéis, suíte verde | Restrições de implementação |

## Decisões registradas pelo solicitante (2026-09-25)

- **C-1**: **NÃO fixar percentuais na spec** — larguras determinadas pela implementação após análise do HTML/CSS/comportamento atual (padrão 037–040).
- **C-2**: prioridade de espaço: maior para **Descrição**, **Localização** e **Responsável**; intermediária para **Tombamento** e **Categoria**; compactas: **Status**, **Data Compra**, **Valor Aquisição**, **Depreciação** e **Valor Atual** (monetárias sem espaço desnecessário).
- **C-3**: a tabela deve utilizar praticamente toda a largura útil disponível do container onde houver espaço, sem grandes vazios e sem colunas excessivamente largas.
- **C-4**: em telas menores, usar o mecanismo responsivo já adotado pelo projeto (incluída rolagem horizontal adequada quando inevitável, dado o volume de 10 colunas); sem reduzir fonte excessivamente, esconder/cortar conteúdo ou tornar controles inacessíveis.
- **C-5** (implícita do pedido): `table-layout` (fixed vs auto) é decisão da implementação com base na análise (seções 19/25 do pedido), considerando 10 colunas, conteúdo textual variável, valores monetários, datas e status — não aplicado automaticamente.
- **C-6** (específica do relatório): a melhoria de tela NÃO pode quebrar o layout de impressão/PDF existente; o CSS de impressão do relatório (bloco `report-print`) deve ser preservado (seção 36 do pedido).

## Clarifications

### Session 2026-09-25

- Q: Nas colunas textuais Descrição, Localização e Responsável, o que deve acontecer quando o texto for mais largo que a largura da coluna (viewport estreita)? → A: Exibir o texto completo, sem corte nenhum — a linha da tabela cresce para caber o conteúdo integral (padrão da 040/Custodiantes).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aproveitamento horizontal no Relatório Contábil-Físico (Priority: P1)

Um usuário abre "Relatório Contábil-Físico do Patrimônio" e vê a tabela ocupando praticamente toda a largura útil do card, com Descrição, Localização e Responsável dominando o espaço para leitura confortável, Tombamento e Categoria proporcionais, Status/Data Compra/monetárias compactas, monetárias com alinhamento consistente entre si, cabeçalhos e valores alinhados — e nada muda no papel: imprimir ou exportar gera exatamente o mesmo resultado de antes.

**Why this priority**: é o objetivo central do pedido — melhor distribuição do espaço horizontal no relatório contábil-físico, lista analítica de todos os bens.

**Independent Test**: abrir `/reports/inventory` em desktop e inspecionar/medir o aproveitamento da largura e a proporção entre as 10 colunas (comparação antes/depois), além de conferir que a impressão permanece idêntica.

**Acceptance Scenarios**:

1. **Given** bens listados, **When** a tabela é exibida em desktop, **Then** ela ocupa praticamente toda a largura útil do card, com Descrição, Localização e Responsável recebendo a maior parte do espaço.
2. **Given** descrição com nome + linha `S/N` condicional, **When** a tabela é exibida com largura suficiente, **Then** a Descrição aparece com o mínimo de quebras necessário, sem truncamento prematuro.
3. **Given** localização institucional longa e responsável com nome completo extenso, **When** a tabela é exibida, **Then** ambos aparecem sem truncamento prematuro e sem quebra em posições inadequadas.
4. **Given** as três colunas monetárias, **When** a tabela é exibida, **Then** as 3 colunas apresentam largura proporcional entre si e alinhamento consistente (o alinhamento à direita existente deve ser preservado), sem quebra dos valores.

---

### User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

O usuário acessa o relatório de notebook, tablet ou celular (e/ou zoom variado): a tabela se adapta conforme o mecanismo do projeto, sem conteúdo cortado indevidamente, sem sobreposição, com todas as 10 colunas acessíveis e qualquer rolagem horizontal confinada ao contêiner da tabela.

**Why this priority**: o relatório é consultado em diversos dispositivos, inclusive em campo durante inventário.

**Independent Test**: abrir `/reports/inventory` em larguras variadas (desktop, notebook, tablet, celular e zoom) e verificar adaptação, legibilidade e acessibilidade.

**Acceptance Scenarios**:

1. **Given** viewport de notebook/tablet, **When** a tabela é exibida (10 colunas), **Then** a distribuição permanece proporcional, sem sobreposição de cabeçalhos nem colunas colapsadas.
2. **Given** viewport de celular, **When** a tabela é exibida, **Then** o comportamento segue o padrão responsivo do projeto — rolagem horizontal confinada ao contêiner da tabela quando inevitável — com todas as colunas acessíveis e conteúdo legível (sem sacrificar legibilidade para eliminar a rolagem).
3. **Given** zoom do navegador variado, **When** a tabela é exibida, **Then** os critérios de legibilidade e ausência de sobreposição se mantêm.

---

### User Story 3 - Impressão e exportação inalteradas (Priority: P2)

O usuário imprime o relatório ou baixa o CSV/Excel/PDF: o resultado é exatamente o mesmo de antes da alteração — mesmo layout de papel, mesmos dados, mesmas colunas e valores.

**Why this priority**: é um relatório contábil oficial; a alteração de `table-layout`, larguras ou CSS da tabela em tela poderia afetar o `@media print` e as exportações.

**Independent Test**: imprimir `/reports/inventory` (pré-visualização) e chamar as exportações antes/depois da alteração, comparando o resultado.

**Acceptance Scenarios**:

1. **Given** o bloco `@media print` do relatório (C1–C10) e a impressão funcionando hoje, **When** a alteração de tela é aplicada, **Then** a pré-visualização de impressão permanece idêntica ao comportamento atual (sem primeira página em branco, sem truncamento, cabeçalho repetido, valores íntegros).
2. **Given** exportações CSV/Excel/PDF do relatório, **When** qualquer exportação é executada, **Then** o resultado é idêntico ao de antes (mesmos dados, mesmos formatos).
3. **Given** usuário sem `relatorios.exportar`, **When** a página é renderizada, **Then** o HTML não introduz nenhuma string que viole os testes RBAC de template existentes.

---

### Edge Cases

- **Descrição com linha S/N condicional**: nome em `<strong>` + linha `S/N` pequena quando houver `serial_number`, íntegros, sem sobreposição entre as duas linhas.
- **Descrição/Localização/Responsável longos**: **texto completo sempre** — sem clamp nem reticências; alturas de linha podem variar entre linhas (clarificação).
- **Sem localização/responsável/data**: fallbacks "Estoque Geral", "Livre" e "-" exibidos como hoje.
- **Tombamento em fonte mono**: código patrimonial íntegro, sem quebra do código nem truncamento, permanecendo proporcional ao tamanho real dos códigos utilizados.
- **Status como pill**: pill `status-pill-<valor>` mantém comportamento visual atual, sem quebra inadequada.
- **Categoria como badge**: badge `badge-soft-gray` íntegro, com o espaço excedente beneficiando as colunas textuais.
- **Valores monetários altos** (ex.: R$ 120.000,00): legíveis, sem quebra, alinhamento consistente.
- **Percentual de depreciação**: sinal `-XX%` exibido como hoje (cor/negrito existentes preservados).
- **Lista vazia / sem bens**: estado do relatório inalterado.
- **Impressão do relatório**: qualquer largura/min-width aplicada em tela MUST ser neutralizada em `@media print` para esta página, sem editar o bloco compartilhado C1–C10.
- **Tema claro/escuro**: nenhuma cor nova; contraste preservado.
- **Uma única linha na tabela**: distribuição estável por coluna (não por conteúdo da linha).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tabela MUST aproveitar praticamente toda a largura útil disponível do container onde houver espaço (C-3), sem grandes vazios e sem colunas excessivamente largas.
- **FR-002**: A distribuição de larguras MUST ser proporcional à natureza do conteúdo/função de cada coluna, seguindo C-2 (Descrição, Localização e Responsável no topo; Tombamento e Categoria intermediárias; Status, Data Compra e as 3 monetárias compactas) — dimensionada pela implementação após análise (C-1), sem percentuais fixados por esta spec.
- **FR-003**: A coluna Tombamento MUST exibir os códigos patrimoniais integralmente, em fonte mono e negrito (como hoje), sem quebra do código nem truncamento, permanecendo proporcional ao tamanho real dos códigos utilizados.
- **FR-004**: A coluna Descrição MUST receber uma das maiores larguras da tabela: nome em `<strong>` e a linha condicional `S/N` exibidos **completamente** (sem clamp nem reticências — clarificação), com quebra somente quando o texto for mais largo que a coluna e sem reduzir a fonte.
- **FR-005**: A coluna Categoria MUST possuir espaço suficiente para os badges existentes, sem ocupar espaço excessivo; o excedente beneficia principalmente Descrição, Localização e Responsável.
- **FR-006**: A coluna Status MUST permanecer compacta: o pill `status-pill-<valor>` continua completamente visível, legível, sem quebra inadequada; os status e suas regras NÃO são alterados.
- **FR-007**: A coluna Localização MUST receber espaço horizontal significativo: nomes de locais longos exibidos **completamente** (sem clamp nem reticências — clarificação), quebrando somente quando necessário e preservando o fallback "Estoque Geral".
- **FR-008**: A coluna Responsável MUST receber espaço horizontal significativo: nomes completos exibidos **completamente** (sem clamp nem reticências — clarificação), quebrando somente quando necessário, preservando o fallback "Livre".
- **FR-009**: A coluna Data Compra MUST permanecer compacta: data `dd/mm/YYYY` (ou "-") sem quebra, sem largura reservada em excesso; o espaço economizado beneficia as colunas textuais.
- **FR-010**: As colunas Valor Aquisição, Depreciação e Valor Atual MUST permanecer compactas, com largura proporcional entre si, alinhamento consistente (preservando o `text-end` existente), valores legíveis sem quebra; a Depreciação mantém o formato `-XX%` com cor/negrito atuais e a Valor Atual mantém verde em negrito; formatação monetária, casas decimais e cálculos NÃO são alterados.
- **FR-011**: Cabeçalho e corpo MUST compartilhar exatamente a mesma estrutura de colunas (sem deslocamento entre thead e tbody, sem `width` aplicado somente ao `<td>`, sem redistribuição automática inesperada); o container da tela, o header (botões "Baixar CSV" e "Imprimir"), o cabeçalho interno do relatório e o `page-header` NÃO podem ser alterados; a implementação MUST reutilizar a estrutura existente e, se necessário CSS novo, usar seletor específico desta tabela/tela, sem classes genéricas, sem duplicar estilos e sem bump de cache global.
- **FR-012**: A solução MUST manter ou melhorar a responsividade existente em desktop grande/médio, notebook, tablet, celular, larguras intermediárias e zoom (faixa 80%–200%, precedentes 036–040), sem overflow horizontal desnecessário onde a tabela puder se adaptar; em larguras mínimas, qualquer rolagem horizontal MUST ficar confinada ao contêiner da tabela, sem conteúdo cortado indevidamente, sobreposição, badges/pills quebrados ou controles inacessíveis (C-4).
- **FR-013**: A alteração de tela MUST preservar integralmente a impressão: nenhuma regra do bloco `@media print` dos relatórios (C1–C10, ancorado em `.report-print` e **compartilhado** com os outros 2 relatórios) pode ser editada; se a 041 introduzir larguras/min-width de tela nesta tabela, elas MUST ser neutralizadas dentro de `@media print` para esta página, e a pré-visualização de impressão deve permanecer idêntica ao comportamento atual (C-6).
- **FR-014**: Nenhuma funcionalidade MAY ser alterada: geração do relatório, exportações (CSV/Excel/PDF), filtros, consultas, agregações, totais, arredondamentos, casas decimais, cálculo de depreciação, permissões, autenticação, auditoria, API, endpoints, banco, modelos e schemas permanecem intocados.
- **FR-015**: Nenhum conteúdo exibido MAY ser removido ou alterado: tombamento, descrição (com linha S/N condicional), categoria, status, localização, responsável, data de compra, valor de aquisição, depreciação, valor atual, fallbacks ("Estoque Geral", "Livre", "-"), ícones, botões e cores semânticas permanecem presentes.
- **FR-016**: A alteração MUST ficar restrita aos arquivos estritamente necessários desta tela; as telas de conferência (036), inventários (037), equipamentos (038), movimentações (039), custodiantes (040), os demais relatórios (Trilha de Auditoria, Relação de Colaboradores) e demais telas/componentes NÃO podem ser afetados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em desktop, a tabela ocupa ≥ 95% da largura útil do card/container (verificável por medição da renderização) — referência indicativa, sujeita ao julgamento visual.
- **SC-002**: As colunas textuais (Descrição + Localização + Responsável) ocupam juntas a maior parte da largura da tabela (referência indicativa: mais da metade), medida em desktop.
- **SC-003**: Zero desalinhamento entre cabeçalhos e valores em todas as larguras validadas.
- **SC-004**: Zero overflow horizontal da página em larguras a partir de notebook; em tablet/celular, qualquer rolagem fica restrita ao contêiner da tabela.
- **SC-005**: Zero sobreposição, zero truncamento indevido (tombamento, textos e valores monetários) e zero quebras inadequadas de badges/pills nas larguras validadas.
- **SC-006**: A suíte de testes existente permanece 100% verde (nenhuma regressão funcional), incluindo `test_report_print_smoke.py` e os testes RBAC do relatório.
- **SC-007**: A pré-visualização de impressão de `/reports/inventory` permanece idêntica ao comportamento atual (mesmas páginas, cabeçalho repetido, valores íntegros, sem página em branco inicial) — comparada antes/depois da alteração.
- **SC-008**: Validação registrada em `specs/041-relatorio-contabil-larguras-colunas/validacao.md` no formato das 036–040: suíte pytest 100% verde E inspeção manual com medição nos cenários do pedido (desktop grande/médio, notebook, tablet, celular) e faixa de zoom 80%–200%, com resultado de cada cenário, comparação antes/depois E verificação de impressão.

## Assumptions

- Bootstrap 5.3 e `style.css` permanecem a base; nenhuma dependência nova.
- O mecanismo responsivo do projeto refere-se ao padrão validado nas 036–040 (layout determinístico com larguras por classe escopada + quebras locais + `min-width` com rolagem confinada ao `table-responsive`) — reuso esperado, com as larguras desta tabela determinadas pela implementação (C-1) e a escolha final de `table-layout` justificada pela análise (C-5).
- Header (botões do `page-header no-print`) e cabeçalho interno do relatório (empresa/ano) são intocados; a tabela exibe o resultado corrente dos filtros.
- Fonte real do app (Plus Jakarta Sans) é ~20–30% mais larga que fontes de fallback — medições de largura MUST incluir folga para isso (lição da 039), inclusive nos headers das colunas ("Valor Aquisição" é o título mais largo).
- O bloco `@media print` C1–C10 é compartilhado por 3 templates; qualquer exceção de impressão necessária entra como regra nova e escopada, nunca editando as regras existentes.

## Fora de escopo

- Qualquer mudança funcional (geração, filtros, exportações CSV/Excel/PDF, cálculos contábeis, depreciação, permissões).
- Impressão/PDF/Excel em si: o comportamento de impressão e o conteúdo das exportações permanecem idênticos (a alteração é de tela; nenhuma regra de impressão editada).
- Outras tabelas/telas (conferência — 036; inventários — 037; equipamentos — 038; movimentações — 039; custodiantes — 040; demais relatórios e locais) e o layout global/container/filtros/header da própria tela.
- Redesenho visual além da distribuição de larguras, quebras e alinhamentos.
- Novos testes automatizados de UI (seção 33 do pedido: apenas executar os existentes; sem testes artificiais).
