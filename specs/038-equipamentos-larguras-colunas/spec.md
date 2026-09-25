# Feature Specification: Ajuste Responsivo da Tabela "Equipamentos"

**Feature Branch**: `038-equipamentos-larguras-colunas`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Ajustar exclusivamente o layout da tabela da tela **"Equipamentos"** (`/assets`): aproveitar o máximo possível da largura horizontal disponível, redistribuindo o espaço entre as 8 colunas (Tombamento, Equipamento/Modelo, Categoria, Status, Responsável, Localização, Valor, Ações). Colunas textuais **Equipamento/Modelo**, **Responsável** e **Localização** recebem prioridade; **Categoria** e **Tombamento** ficam proporcionais ao conteúdo; **Status**, **Valor** e **Ações** permanecem compactas. Mesmo princípio das specs 036/037: redistribuição inteligente, análise antes de alterar, implementação cirúrgica — nenhuma funcionalidade, dado, rota ou regra de negócio é alterada.

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| Tela "Equipamentos & Bens" = `app/web/templates/assets/list.html` (rota `/assets`); tabela no bloco `{% if assets %}` (linhas ~133–192) | Superfície única a alterar |
| Colunas e conteúdo por célula: **Tombamento** (link com `tag-badge`), **Equipamento/Modelo** (link `fw-semibold` com nome + linha auxiliar `.76rem` com marca/modelo e `S/N: <code>`), **Categoria** (badge `badge-soft-gray` `.68rem`), **Status** (`status-pill-{DISPONIVEL,EM_USO,EM_MANUTENCAO,EM_TRANSITO,BAIXADO}` com pseudo-elemento ::before — rótulos até "Em Manutenção"/"Em Transferência"), **Responsável** (link com ícone + nome + matrícula `.72rem`, ou "Estoque Livre"), **Localização** (texto `small text-muted` ou "Estoque Central"), **Valor** (`text-nowrap` pré-existente, font-monospace, formato R$ 1.250,00), **Ações** (`text-end text-nowrap`, 1–2 botões-ícone `btn-ghost btn-icon` — "Ver Detalhes" sempre; "Movimentar" se `movimentacao.criar`) | Sem classes/colgroup de largura; distribuição atual vem do layout automático. Nuances protegidas nos FRs: células multilinha (auxiliares), `text-nowrap` funcional já existente (Valor/Ações — **preservar**), status-pill com ::before (quebra de linha do rótulo desloca o ponto), botões condicionais por permissão |
| Tabela em `card` > `table-responsive` > `table align-middle`; container padrão do `base.html` | Container **não alterado** (FR-011); rolagem confinada ao `table-responsive` quando inevitável |
| Filtros extensos acima da tabela (formulário `assets-filters` com busca + múltiplos selects) | Fora do escopo — intocados (só a tabela) |
| `style.css` não define larguras para esta tabela; `style.css` versionado em 2 pontos acoplados (base.html + SW allowlist) | CSS embutido no template com classe de escopo (precedente 036/037), sem bump de cache global |
| `list.html` não tem block de `head`; `<style>` entra no topo do `{% block content %}` | Mecanismo conhecido e validado |
| Constitution I/X/XI/XII: escopo cirúrgico, interface consistente, docs fiéis, suíte verde | Restrições de implementação |

## Decisões registradas pelo solicitante (2026-09-25)

- **C-1**: **NÃO fixar percentuais na spec** — larguras determinadas pela implementação após análise do HTML/CSS/comportamento atual (padrão 037).
- **C-2**: prioridade de espaço: maior para **Equipamento/Modelo**, **Responsável** e **Localização**; intermediária para **Categoria** e **Tombamento**; compactas: **Status**, **Valor** e **Ações** (a mais compacta de todas).
- **C-3**: a tabela deve utilizar praticamente toda a largura útil disponível do container onde houver espaço, sem grandes vazios e sem colunas excessivamente largas.
- **C-4**: em telas menores, usar o mecanismo responsivo já adotado pelo projeto (incluída rolagem horizontal adequada para tabelas largas, quando inevitável); sem reduzir fonte excessivamente, esconder/cortar conteúdo ou tornar botões inacessíveis.
- **C-5** (implícita do pedido): `table-layout` (fixed vs auto) é decisão da implementação com base na análise — não aplicado automaticamente (seção 21).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aproveitamento horizontal na listagem de equipamentos (Priority: P1)

Um usuário abre "Equipamentos & Bens" e vê a tabela ocupando praticamente toda a largura útil do card, com Equipamento/Modelo, Responsável e Localização dominando o espaço para leitura confortável, Tombamento/Categoria proporcionais, Status/Valor/Ações compactas, cabeçalhos e valores alinhados e todos os links/botões funcionando como hoje.

**Why this priority**: é o objetivo central do pedido — melhor distribuição do espaço horizontal na listagem principal do patrimônio.

**Independent Test**: abrir `/assets` em desktop e inspecionar/medir o aproveitamento da largura e a proporção entre as 8 colunas (comparação antes/depois).

**Acceptance Scenarios**:

1. **Given** equipamentos listados, **When** a tabela é exibida em desktop, **Then** ela ocupa praticamente toda a largura útil do card, com Equipamento/Modelo, Responsável e Localização recebendo a maior parte do espaço.
2. **Given** equipamento com descrição longa, marca/modelo e número de série, **When** a tabela é exibida com largura suficiente, **Then** nome e linha auxiliar (marca • S/N) permanecem legíveis, com o mínimo de quebras necessário.
3. **Given** colaborador com nome completo longo e local institucional extenso, **When** a tabela é exibida, **Then** ambos aparecem sem truncamento prematuro, e o Valor monetário e os botões de Ação permanecem íntegros e clicáveis como hoje.

---

### User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

O usuário acessa a listagem de notebook, tablet ou celular (e/ou zoom variado): a tabela se adapta conforme o mecanismo do projeto, sem conteúdo cortado indevidamente, sem sobreposição, com os botões de ação acessíveis e qualquer rolagem horizontal confinada ao contêiner da tabela.

**Why this priority**: a listagem é a principal ferramenta de consulta patrimonial, usada em diversos dispositivos.

**Independent Test**: abrir `/assets` em larguras variadas (desktop, notebook, tablet, celular e zoom) e verificar adaptação, legibilidade e acessibilidade dos controles.

**Acceptance Scenarios**:

1. **Given** viewport de notebook/tablet, **When** a tabela é exibida, **Then** a distribuição permanece proporcional, sem sobreposição de cabeçalhos nem colunas colapsadas.
2. **Given** viewport de celular, **When** a tabela é exibida (8 colunas), **Then** o comportamento segue o padrão responsivo do projeto — rolagem horizontal confinada ao contêiner da tabela quando inevitável — com ações acessíveis e conteúdo legível.
3. **Given** zoom do navegador variado, **When** a tabela é exibida, **Then** os critérios de legibilidade e ausência de sobreposição se mantêm.

---

### Edge Cases

- **Equipamento com S/N longo** (`<code>` na linha auxiliar): quebra/legibilidade preservada dentro da coluna.
- **"Estoque Livre" / "Estoque Central"** (fallbacks de Responsável/Localização): renderizados como hoje.
- **Responsável com matrícula longa**: linha auxiliar íntegra.
- **Status "Em Manutenção"/"Em Transferência"** (rótulos mais longos): status-pill íntegro, sem quebra inadequada do ::before.
- **Valor alto** (R$ 120.000,00): cabe sem quebra (`text-nowrap` preservado).
- **2 botões de Ação** (usuário com `movimentacao.criar`): coluna acomoda ambos sem aperto.
- **Lista vazia / filtros sem resultado**: estado "Nenhum equipamento encontrado" inalterado.
- **Tema claro/escuro**: nenhuma cor nova; contraste preservado.
- **Uma única linha na tabela**: distribuição estável por coluna (não por conteúdo da linha).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tabela MUST aproveitar praticamente toda a largura útil disponível do container onde houver espaço (C-3), sem grandes vazios e sem colunas excessivamente largas.
- **FR-002**: A distribuição de larguras MUST ser proporcional à natureza do conteúdo/função de cada coluna, seguindo C-2 (Equipamento/Modelo, Responsável e Localização no topo; Categoria e Tombamento intermediários; Status, Valor e Ações compactas) — dimensionada pela implementação após análise (C-1), sem percentuais fixados por esta spec.
- **FR-003**: A coluna Tombamento MUST exibir os números patrimoniais integralmente, sem quebra desnecessária nem truncamento, permanecendo compacta.
- **FR-004**: A coluna Equipamento/Modelo MUST receber espaço significativo: nome e linha auxiliar (marca/modelo • S/N) legíveis, com mínimas quebras quando houver espaço e alinhamento com o cabeçalho.
- **FR-005**: A coluna Categoria MUST ter largura adequada ao conteúdo real (badges das categorias), sem espaço exagerado; o excedente beneficia as colunas textuais.
- **FR-006**: A coluna Status MUST ser compacta e suficiente para os status-pill existentes (incluídos os rótulos "Em Manutenção"/"Em Transferência"), sem quebra inadequada nem espaço exagerado.
- **FR-007**: A coluna Responsável MUST receber espaço significativo: nome completo legível (link) + matrícula, sem truncamento prematuro; fallback "Estoque Livre" preservado.
- **FR-008**: A coluna Localização MUST receber espaço significativo: nomes de locais longos legíveis, sem quebra excessiva; fallback "Estoque Central" preservado.
- **FR-009**: A coluna Valor MUST ter largura suficiente para os valores monetários sem quebra (comportamento `text-nowrap` atual preservado), sem espaço exagerado.
- **FR-010**: A coluna Ações MUST ser a mais compacta possível, acomodando 1 ou 2 botões-ícone conforme a permissão do usuário, visíveis, clicáveis, alinhados à direita (comportamento atual preservado) e acessíveis.
- **FR-011**: Cabeçalho e corpo MUST compartilhar exatamente a mesma estrutura de colunas (sem deslocamento entre thead e tbody); o container da tela e os filtros NÃO podem ser alterados; a implementação MUST reutilizar a estrutura existente e, se necessário CSS novo, usar seletor específico desta tabela/tela, sem classes genéricas, sem duplicar estilos e sem bump de cache global.
- **FR-012**: A solução MUST manter ou melhorar a responsividade existente em desktop grande/médio, notebook, tablet, celular, larguras intermediárias e zoom (faixa 80%–200%, precedentes 036/037), sem overflow horizontal desnecessário onde a tabela puder se adaptar; em larguras mínimas, qualquer rolagem horizontal MUST ficar confinada ao contêiner da tabela, sem conteúdo cortado indevidamente, sobreposição, badges quebrados ou botões inacessíveis (C-4).
- **FR-013**: Nenhuma funcionalidade MAY ser alterada: cadastro, edição, exclusão, consulta, filtros, pesquisa, paginação, QR Code, movimentações, responsáveis, localização, valores, status, API, banco, modelos, schemas, permissões, autenticação e auditoria permanecem intocados.
- **FR-014**: Nenhum conteúdo exibido MAY ser removido ou alterado: tombamento, equipamento, modelo, categoria, status, responsável, localização, valor, ações, ícones, botões, links, tooltips e linhas auxiliares permanecem presentes.
- **FR-015**: A alteração MUST ficar restrita aos arquivos estritamente necessários desta tela; as tabelas de inventários (037), conferência (036) e demais telas/componentes NÃO podem ser afetados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em desktop, a tabela ocupa ≥ 95% da largura útil do card/container (verificável por medição da renderização) — referência indicativa, sujeita ao julgamento visual.
- **SC-002**: As colunas Equipamento/Modelo + Responsável + Localização ocupam juntas a maior parte da largura da tabela (referência indicativa: mais da metade), medida em desktop.
- **SC-003**: Zero desalinhamento entre cabeçalhos e valores em todas as larguras validadas.
- **SC-004**: Zero overflow horizontal da página em larguras a partir de notebook; em tablet/celular, qualquer rolagem fica restrita ao contêiner da tabela.
- **SC-005**: Zero sobreposição, zero truncamento indevido (tombamento e textos) e zero quebras inadequadas de badges/status nas larguras validadas.
- **SC-006**: A suíte de testes existente permanece 100% verde (nenhuma regressão funcional).
- **SC-007**: Validação registrada em `specs/038-equipamentos-larguras-colunas/validacao.md` no formato das 036/037: suíte pytest 100% verde E inspeção manual com medição nos cenários do pedido (desktop grande/médio, notebook, tablet, celular) e faixa de zoom 80%–200%, com resultado de cada cenário e comparação antes/depois.

## Assumptions

- Bootstrap 5.3 e `style.css` permanecem a base; nenhuma dependência nova.
- O mecanismo responsivo do projeto refere-se ao padrão validado nas 036/037 (layout determinístico com larguras por classe escopada + quebras locais + `min-width` com rolagem confinada ao `table-responsive`) — reuso esperado, com as larguras desta tabela determinadas pela implementação (C-1) e a escolha final de `table-layout` justificada pela análise (C-5).
- Paginação/filtros existentes são intocados; a tabela exibe a página corrente.

## Fora de escopo

- Qualquer mudança funcional (CRUD, filtros, pesquisa, paginação, QR Code, movimentações, permissões).
- Outras tabelas/telas (listagem de inventários — 037; conferência — 036; colaboradores; locais; movimentações) e o layout global/container/filtros da própria tela.
- Redesenho visual além da distribuição de larguras, quebras e alinhamentos.
- Novos testes automatizados de UI (seção 28 do pedido: apenas executar os existentes; sem testes artificiais).
