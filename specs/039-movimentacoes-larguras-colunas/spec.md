# Feature Specification: Ajuste Responsivo da Tabela "Fluxo Global de Movimentações"

**Feature Branch**: `039-movimentacoes-larguras-colunas`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Ajustar exclusivamente o layout da tabela da tela **"Fluxo Global de Movimentações"** (`/movements`): aproveitar o máximo possível da largura horizontal disponível, redistribuindo o espaço entre as 9 colunas (Data / Hora, Tombamento, Equipamento, Tipo, Origem, Destino, Motivo, Operador, Ações). Colunas textuais **Equipamento**, **Origem**, **Destino**, **Motivo** e **Operador** recebem prioridade; **Data / Hora**, **Tombamento** e **Tipo** ficam proporcionais ao conteúdo; **Ações** permanece a mais compacta. Mesmo princípio das specs 036/037/038: redistribuição inteligente, análise antes de alterar, implementação cirúrgica — nenhuma funcionalidade, dado, rota ou regra de negócio é alterada.

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| Tela "Fluxo Global de Movimentações" = `app/web/templates/movements/list.html` (rota `/movements`, `movimentacao.visualizar`, limite 200 registros); tabela no bloco `{% if movements %}` (linhas ~47–104) | Superfície única a alterar |
| Colunas e conteúdo por célula: **Data / Hora** (`small text-muted text-nowrap` — `dd/mm/AAAA HH:MM` pré-formatado, 16 chars), **Tombamento** (link `tag-badge` → `/assets/{id}`), **Equipamento** (link `text-decoration-none` com `color:var(--c-text);font-weight:600` — nome do bem), **Tipo** (badge `badge-soft-primary` `.68rem` com `m.movement_type.label`), **Origem** (`small`, 2 linhas: ícone + local ou `-`, ícone + custodiante ou `-`), **Destino** (`small`, 2 linhas com `fw-semibold`/`color:var(--c-primary-text)`: ícone + local ou `-`, ícone + custodiante ou `-`), **Motivo** (`small truncate-2` com `max-width:220px` inline), **Operador** (`small text-muted` — nome do usuário), **Ações** (`text-end`, 1–2 botões-ícone `btn-ghost btn-icon` — "Imprimir Termo" se `m.term_code`, "Ver Bem" sempre) | Sem classes/colgroup de largura (exceto `max-width:220px` inline do Motivo); distribuição atual vem do layout automático. Nuances protegidas nos FRs: células multilinha de Origem/Destino (local + custodiante), `text-nowrap` funcional já existente (Data / Hora — **preservar**), `truncate-2` do Motivo (2 linhas — preservar comportamento), fallbacks `-`, botões condicionais por conteúdo |
| Tabela em `card` > `table-responsive` > `table align-middle`; container global `base.html` (`container-fluid ... max-width:90%`) | Container **não alterado** (FR-011); rolagem confinada ao `table-responsive` quando inevitável |
| Filtro único acima da tabela (card `form` com select de Tipo + Filtrar/Limpar) e contagem "Mostrando N registros de fluxo" | Fora do escopo — intocados (só a tabela) |
| Tipos de movimentação exibidos (rótulos reais de `enums.py`): "Entrada por Aquisição", "Alocação / Cautela", "Transferência de Local", "Envio para Manutenção", "Retorno de Manutenção", "Devolução ao Estoque", "Baixa / Descarte", "Atualização de Estado" — rótulo mais longo ~22 chars | A coluna Tipo deve dimensionar-se para os badges reais, sem espaço exagerado; tipos e regras intocados |
| `style.css` não define larguras para esta tabela; `.truncate-2` é utilitário global (L881); `style.css` versionado em 2 pontos acoplados (base.html + SW allowlist) | CSS embutido no template com classe de escopo (precedente 036/037/038), sem bump de cache global |
| `list.html` de movements não tem block de `head`; `<style>` entra no topo do `{% block content %}` | Mecanismo conhecido e validado nas 036/037/038 |
| Constitution I/X/XI/XII: escopo cirúrgico, interface consistente, docs fiéis, suíte verde | Restrições de implementação |

## Decisões registradas pelo solicitante (2026-09-25)

- **C-1**: **NÃO fixar percentuais na spec** — larguras determinadas pela implementação após análise do HTML/CSS/comportamento atual (padrão 037/038).
- **C-2**: prioridade de espaço: maior para **Equipamento**, **Origem**, **Destino**, **Motivo** e **Operador**; intermediária para **Data / Hora**, **Tombamento** e **Tipo**; compacta: **Ações** (a mais compacta de todas).
- **C-3**: a tabela deve utilizar praticamente toda a largura útil disponível do container onde houver espaço, sem grandes vazios e sem colunas excessivamente largas.
- **C-4**: em telas menores, usar o mecanismo responsivo já adotado pelo projeto (incluída rolagem horizontal adequada para tabelas largas, quando inevitável — tabela de 9 colunas); sem reduzir fonte excessivamente, esconder/cortar conteúdo ou tornar botões inacessíveis.
- **C-5** (implícita do pedido): `table-layout` (fixed vs auto) é decisão da implementação com base na análise — não aplicado automaticamente (seção 22).

## Clarifications

### Session 2026-09-25

- Q: Como a coluna "Motivo" deve tratar o limite de largura atual (`max-width:220px` inline) quando a tabela passar a aproveitar mais espaço em telas largas? → A: Remover o cap de 220px e manter o corte em 2 linhas (`truncate-2`): o Motivo ocupa a largura disponível e o texto além de 2 linhas permanece oculto, como no restante do sistema (padrão 036/037/038).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aproveitamento horizontal na trilha de movimentações (Priority: P1)

Um usuário abre "Fluxo Global de Movimentações" e vê a tabela ocupando praticamente toda a largura útil do card, com Equipamento, Origem, Destino, Motivo e Operador dominando o espaço para leitura confortável, Data / Hora, Tombamento e Tipo proporcionais, Ações compacta, cabeçalhos e valores alinhados e todos os links/botões funcionando como hoje.

**Why this priority**: é o objetivo central do pedido — melhor distribuição do espaço horizontal na tela de auditoria do fluxo patrimonial.

**Independent Test**: abrir `/movements` em desktop e inspecionar/medir o aproveitamento da largura e a proporção entre as 9 colunas (comparação antes/depois).

**Acceptance Scenarios**:

1. **Given** movimentações listadas, **When** a tabela é exibida em desktop, **Then** ela ocupa praticamente toda a largura útil do card, com Equipamento, Origem, Destino, Motivo e Operador recebendo a maior parte do espaço.
2. **Given** movimentação com motivo descritivo longo, **When** a tabela é exibida com largura suficiente, **Then** o motivo permanece legível dentro do comportamento de 2 linhas já existente, com o mínimo de quebras necessário.
3. **Given** local institucional extenso e custodiante com nome completo longo em Origem/Destino, **When** a tabela é exibida, **Then** ambos aparecem sem truncamento prematuro, e a Data / Hora, o tombamento e os botões de Ação permanecem íntegros e clicáveis como hoje.

---

### User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

O usuário acessa a tela de notebook, tablet ou celular (e/ou zoom variado): a tabela de 9 colunas se adapta conforme o mecanismo do projeto, sem conteúdo cortado indevidamente, sem sobreposição, com os botões de ação acessíveis e qualquer rolagem horizontal confinada ao contêiner da tabela.

**Why this priority**: a trilha global de movimentações é consulta de auditoria usada em diversos dispositivos.

**Independent Test**: abrir `/movements` em larguras variadas (desktop, notebook, tablet, celular e zoom) e verificar adaptação, legibilidade e acessibilidade dos controles.

**Acceptance Scenarios**:

1. **Given** viewport de notebook/tablet, **When** a tabela é exibida, **Then** a distribuição permanece proporcional, sem sobreposição de cabeçalhos nem colunas colapsadas.
2. **Given** viewport de celular, **When** a tabela é exibida (9 colunas), **Then** o comportamento segue o padrão responsivo do projeto — rolagem horizontal confinada ao contêiner da tabela quando inevitável — com ações acessíveis e conteúdo legível.
3. **Given** zoom do navegador variado, **When** a tabela é exibida, **Then** os critérios de legibilidade e ausência de sobreposição se mantêm.

---

### Edge Cases

- **Movimentação sem local/custodiante de origem ou destino** (fallbacks `-`): renderizados como hoje, com ícones preservados.
- **Motivo longo**: cap de largura de 220px removido; comportamento de 2 linhas (`truncate-2`) preservado — texto além de 2 linhas permanece oculto como no restante do sistema; a coluna não pode ficar com largura mínima insuficiente.
- **Tipo com rótulo longo** ("Envio para Manutenção", "Atualização de Estado"): badge `badge-soft-primary` íntegro, sem quebra inadequada nem coluna excessivamente larga.
- **Movimentação com termo** (`m.term_code`): botão "Imprimir Termo" + "Ver Bem" (2 botões) acomodados sem aperto; sem termo, apenas 1 botão.
- **Data / Hora em `dd/mm/AAAA HH:MM`**: exibida integralmente em 1 linha (`text-nowrap` preservado), sem quebra entre data e hora.
- **Nome de equipamento longo**: link do bem legível, com mínimas quebras quando houver espaço.
- **Operador com nome longo**: legível sem truncamento prematuro.
- **Lista vazia / filtro sem resultado**: estado "Nenhuma movimentação encontrada" inalterado.
- **Tema claro/escuro**: nenhuma cor nova; contraste preservado.
- **Uma única linha na tabela**: distribuição estável por coluna (não por conteúdo da linha).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tabela MUST aproveitar praticamente toda a largura útil disponível do container onde houver espaço (C-3), sem grandes vazios e sem colunas excessivamente largas.
- **FR-002**: A distribuição de larguras MUST ser proporcional à natureza do conteúdo/função de cada coluna, seguindo C-2 (Equipamento, Origem, Destino, Motivo e Operador no topo; Data / Hora, Tombamento e Tipo intermediários; Ações compacta) — dimensionada pela implementação após análise (C-1), sem percentuais fixados por esta spec.
- **FR-003**: A coluna Data / Hora MUST exibir `dd/mm/AAAA HH:MM` integralmente em linha única (comportamento `text-nowrap` atual preservado), sem quebra entre data e hora, permanecendo compacta.
- **FR-004**: A coluna Tombamento MUST exibir os números patrimoniais integralmente, sem quebra desnecessária nem truncamento, permanecendo compacta e confortável para leitura.
- **FR-005**: A coluna Equipamento MUST receber espaço significativo: nome do bem legível, com mínimas quebras quando houver espaço e alinhamento com o cabeçalho.
- **FR-006**: A coluna Tipo MUST ter largura adequada ao conteúdo real (badges dos 8 tipos de movimentação existentes, rótulos até "Envio para Manutenção"/"Atualização de Estado"), sem espaço exagerado; o excedente beneficia as colunas textuais; tipos e rótulos intocados.
- **FR-007**: As colunas Origem e Destino MUST receber espaço significativo: local e custodiante legíveis (2 linhas por célula, com ícones e fallbacks `-` preservados), sem truncamento prematuro nem quebra excessiva.
- **FR-008**: A coluna Motivo MUST receber espaço adequado para textos descritivos maiores: o limite de largura atual (`max-width:220px` inline) MUST ser removido para que a coluna aproveite o espaço disponível em telas largas, preservando o corte em 2 linhas (`truncate-2`) como no restante do sistema; sem largura mínima insuficiente; prioridade sobre as colunas compactas.
- **FR-009**: A coluna Operador MUST possuir espaço suficiente para nomes de usuários/operadores legíveis, sem truncamento prematuro nem quebra desnecessária, sem espaço exagerado.
- **FR-010**: A coluna Ações MUST ser a mais compacta possível, acomodando 1 ou 2 botões-ícone (`btn-ghost btn-icon` — "Imprimir Termo" se houver termo, "Ver Bem" sempre) visíveis, clicáveis, alinhados à direita (comportamento atual preservado) e acessíveis.
- **FR-011**: Cabeçalho e corpo MUST compartilhar exatamente a mesma estrutura de colunas (sem deslocamento entre thead e tbody); o container da tela, o filtro e a contagem de registros NÃO podem ser alterados; a implementação MUST reutilizar a estrutura existente e, se necessário CSS novo, usar seletor específico desta tabela/tela, sem classes genéricas, sem duplicar estilos e sem bump de cache global.
- **FR-012**: A solução MUST manter ou melhorar a responsividade existente em desktop grande/médio, notebook, tablet, celular, larguras intermediárias e zoom (faixa 80%–200%, precedentes 036/037/038), sem overflow horizontal desnecessário onde a tabela puder se adaptar; em larguras mínimas, qualquer rolagem horizontal MUST ficar confinada ao contêiner da tabela, sem conteúdo cortado indevidamente, sobreposição, badges quebrados ou botões inacessíveis (C-4).
- **FR-013**: Nenhuma funcionalidade MAY ser alterada: criação/edição/exclusão/consulta de movimentações, filtros, pesquisa, ordenação, tipos de movimentação, regras de origem/destino, motivos, operadores, termo, patrimônio, inventário, QR Code, API, banco, modelos, schemas, permissões, autenticação e auditoria permanecem intocados.
- **FR-014**: Nenhum conteúdo exibido MAY ser removido ou alterado: data, hora, tombamento, equipamento, tipo, origem, destino, motivo, operador, ações, ícones, botões, links, tooltips e fallbacks permanecem presentes.
- **FR-015**: A alteração MUST ficar restrita aos arquivos estritamente necessários desta tela; as tabelas de equipamentos (038), inventários (037), conferência (036) e demais telas/componentes NÃO podem ser afetados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em desktop, a tabela ocupa ≥ 95% da largura útil do card/container (verificável por medição da renderização) — referência indicativa, sujeita ao julgamento visual.
- **SC-002**: As colunas Equipamento + Origem + Destino + Motivo + Operador ocupam juntas a maior parte da largura da tabela (referência indicativa: mais da metade), medida em desktop.
- **SC-003**: Zero desalinhamento entre cabeçalhos e valores em todas as larguras validadas.
- **SC-004**: Zero overflow horizontal da página em larguras a partir de notebook; em tablet/celular, qualquer rolagem fica restrita ao contêiner da tabela.
- **SC-005**: Zero sobreposição, zero truncamento indevido (tombamento, textos e datas) e zero quebras inadequadas de badges nas larguras validadas.
- **SC-006**: A suíte de testes existente permanece 100% verde (nenhuma regressão funcional).
- **SC-007**: Validação registrada em `specs/039-movimentacoes-larguras-colunas/validacao.md` no formato das 036/037/038: suíte pytest 100% verde E inspeção manual com medição nos cenários do pedido (desktop grande/médio, notebook, tablet, celular) e faixa de zoom 80%–200%, com resultado de cada cenário e comparação antes/depois.

## Assumptions

- Bootstrap 5.3 e `style.css` permanecem a base; nenhuma dependência nova.
- O mecanismo responsivo do projeto refere-se ao padrão validado nas 036/037/038 (layout determinístico com larguras por classe escopada + quebras locais + `min-width` com rolagem confinada ao `table-responsive`) — reuso esperado, com as larguras desta tabela determinadas pela implementação (C-1) e a escolha final de `table-layout` justificada pela análise (C-5).
- O filtro de tipo e a contagem de registros são intocados; a tabela exibe até 200 movimentações da página corrente.
- As larguras de Origem/Destino consideram as células de 2 linhas (local + custodiante), que não podem ser achatadas em layout de 1 linha.

## Fora de escopo

- Qualquer mudança funcional (CRUD, filtros, pesquisa, ordenação, paginação, tipos de movimentação, regras de origem/destino, motivos, operadores, termo, QR Code, permissões).
- Outras tabelas/telas (equipamentos — 038; inventários — 037; conferência — 037/036; colaboradores; locais; relatórios de movimentação) e o layout global/container/filtros da própria tela.
- Redesenho visual além da distribuição de larguras, quebras e alinhamentos.
- Novos testes automatizados de UI (seção 29 do pedido: apenas executar os existentes; sem testes artificiais).
