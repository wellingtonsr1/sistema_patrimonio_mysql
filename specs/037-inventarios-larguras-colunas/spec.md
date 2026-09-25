# Feature Specification: Ajuste Responsivo da Tabela "Inventário Patrimonial"

**Feature Branch**: `037-inventarios-larguras-colunas`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Ajustar exclusivamente o layout da tabela da tela **"Inventário Patrimonial"** (`/inventarios`): a tabela deve aproveitar o máximo possível da largura horizontal disponível, distribuindo o espaço de forma proporcional ao conteúdo e à função de cada coluna (Código, Inventário, Escopo, Progresso, Status, Ações). Colunas textuais **Inventário** e **Escopo** recebem prioridade de espaço; **Código**, **Progresso** e **Status** ficam adequadamente dimensionados; **Ações** permanece a mais compacta possível. Alteração exclusivamente visual/layout — nenhuma funcionalidade, dado, rota ou regra de negócio é alterada. Mesmo princípio da spec anterior de ajuste de tabela (036): redistribuição inteligente do espaço horizontal, análise antes de alterar e implementação cirúrgica.

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| Tela "Inventário Patrimonial" = `app/web/templates/inventarios/list.html`, rota `/inventarios`; tabela no bloco `<!-- Table -->` (linhas ~51–97) | Superfície única a alterar |
| Colunas atuais: `Código` (`tag-badge`), `Inventário` (link `fw-semibold` + linha auxiliar "Criado em … por …" `.74rem`), `Escopo` (`small text-muted`, `inv.scope_filters`), `Progresso` (até **4 badges empilhados** — verde ✓, âmbar ⚠, vermelho ✕, cinza "+N não previstos" — + linha auxiliar "X/Y conferidos" `.72rem`), `Status` (1 badge: Planejado/Em andamento/Concluído…), `Ações` (`text-end`, 1 botão-ícone `btn-ghost btn-icon` "Abrir") | Sem classes/colgroup de largura; distribuição vem do layout automático do navegador; nuance: células de Inventário e Progresso têm **conteúdo multilinha** (badges + auxiliar) que a compactação não pode prejudicar (mesmo padrão tratado na 036) |
| Tabela envolta em `card` > `table-responsive` > `table align-middle`; container/padding herdados do `base.html` (padrão das demais telas) | Container já padronizado: **não alterar** (seção 12 do pedido); qualquer rolagem em telas pequenas deve ficar confinada ao `table-responsive` |
| `style.css` global não define larguras para esta tabela (mesma conclusão da análise da 036); `style.css` é versionado em 2 pontos acoplados (`base.html` + allowlist do SW) | Preferir CSS embutido no template, escopado à tabela (precedente 036/`offline.html`), evitando bump de cache global |
| Célula Escopo renderiza `inv.scope_filters` (texto cru de filtros — pode ser longo) | Edge case: texto longo não pode transbordar nem truncar — deve quebrar dentro da coluna |
| `list.html` não tem block de `head` disponível; `<style>` entra no topo do `{% block content %}` (válido; precedente 036) | Mecanismo de implementação conhecido e já usado |
| Constitution I/X/XI/XII: escopo cirúrgico, interface consistente, docs fiéis, suíte verde | Restrições de implementação |

## Decisões registradas pelo solicitante (2026-09-25)

- **C-1**: **NÃO fixar percentuais de largura na spec** — a implementação analisa a tabela atual e determina a melhor distribuição (evita proporção boa só em uma resolução).
- **C-2**: prioridade de espaço: maior para **Inventário** e **Escopo**; intermediária para **Código**, **Progresso** e **Status**; menor para **Ações** (o espaço economizado vai principalmente para Inventário/Escopo).
- **C-3**: a tabela deve ocupar praticamente toda a largura útil do container onde houver espaço disponível (sem largura fixa inadequada, sem grandes vazios).
- **C-4**: em telas menores, adaptar conforme o mecanismo responsivo já adotado pelo projeto; sem conteúdo cortado, sobreposição ou botões inacessíveis; sem reduzir fontes excessivamente para eliminar overflow.

---

## Clarifications

### Session 2026-09-25

- Q: Qual faixa de zoom do navegador deve ser coberta na validação da responsividade da tabela da listagem? → A: **80% a 200%** — mesma faixa da 036, por consistência entre as validações das duas features (Chrome/Edge, uso real).
- Q: A implementação pode reutilizar diretamente o mecanismo comprovado da 036 (layout determinístico com larguras por classe + quebras locais, adaptado a esta tabela), ou o planning deve avaliar alternativas antes de escolher? → A: **Reusar padrão da 036** — análise antes, mesma família de solução já validada (layout determinístico com larguras por classe escopada + quebras locais), adaptada às particularidades desta tabela (6 colunas, Progresso com múltiplos badges).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aproveitamento horizontal na listagem (Priority: P1)

Um usuário abre "Inventário Patrimonial" e vê a tabela ocupando praticamente toda a largura útil do card, com Inventário e Escopo dominando o espaço para leitura confortável, Código/Progresso/Status dimensionados ao seu conteúdo e Ações compacta. Cabeçalhos e valores permanecem alinhados e nada funcional muda.

**Why this priority**: é o objetivo central do pedido — eliminar espaços desperdiçados e compressão indevida.

**Independent Test**: abrir `/inventarios` em desktop e inspecionar visualmente o aproveitamento da largura e a proporção entre colunas (comparação antes/depois).

**Acceptance Scenarios**:

1. **Given** inventários listados, **When** a tabela é exibida em desktop, **Then** ela ocupa praticamente toda a largura útil do container, sem grandes áreas vazias, com Inventário/Escopo recebendo a maior parte do espaço.
2. **Given** inventário com nome longo e escopo textual extenso, **When** a tabela é exibida com largura suficiente, **Then** os textos permanecem legíveis, com o mínimo de quebras necessárias, e o Código é exibido integralmente sem quebra inadequada.
3. **Given** linha com progresso contendo múltiplos badges, **When** a tabela é exibida, **Then** os badges e o texto "X/Y conferidos" permanecem legíveis e a coluna Ações mantém o botão visível, clicável e alinhado à direita como hoje.

---

### User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

O usuário acessa a listagem de notebook, tablet ou celular (e/ou zoom variado): a tabela se adapta conforme o padrão do projeto, sem conteúdo cortado indevidamente, sem sobreposição de cabeçalhos, com o botão de Ações acessível e qualquer rolagem horizontal confinada ao contêiner da tabela.

**Why this priority**: a listagem é usada em diversos dispositivos; a correção só está completa se manter/melhorar a responsividade existente.

**Independent Test**: abrir `/inventarios` em larguras variadas (notebook, tablet, celular e zoom) e verificar adaptação, legibilidade e acessibilidade dos controles.

**Acceptance Scenarios**:

1. **Given** viewport de notebook/tablet, **When** a tabela é exibida, **Then** a distribuição permanece proporcional, sem sobreposição de cabeçalhos nem colunas colapsadas.
2. **Given** viewport de celular, **When** a tabela é exibida, **Then** o comportamento segue o padrão responsivo do projeto (incluída rolagem horizontal confinada ao contêiner da tabela, quando inevitável), com ações acessíveis e conteúdo legível.
3. **Given** zoom do navegador entre 80% e 200% (decisão 2026-09-25), **When** a tabela é exibida, **Then** os critérios de legibilidade e ausência de sobreposição se mantêm.

---

### Edge Cases

- **Escopo com texto muito longo** (filtros descritivos): quebra dentro da coluna, sem truncamento prematuro e sem transbordar.
- **Nome de inventário longo**: quebra graciosa; a linha auxiliar "Criado em … por …" permanece legível.
- **Progresso com todos os badges** (incluído "+N não previstos"): os badges empilham/quebram dentro da coluna compacta sem transbordar nem alargar desproporcionalmente.
- **Status com rótulo mais longo** (valores atuais do sistema): badge íntegro, sem quebra inadequada.
- **Lista vazia**: estado "Nenhum inventário encontrado" inalterado.
- **Tema claro/escuro**: nenhuma cor nova introduzida; contraste preservado nos dois temas.
- **Uma única linha na tabela**: distribuição não pode "inflar" colunas curtas (o dimensionamento é por coluna, não por conteúdo da linha).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tabela da listagem MUST aproveitar praticamente toda a largura útil disponível do container onde houver espaço (C-3), sem largura fixa inadequada e sem grandes áreas vazias.
- **FR-002**: A distribuição de larguras MUST ser proporcional à natureza do conteúdo/função de cada coluna, seguindo a prioridade C-2 (Inventário e Escopo no topo; Código/Progresso/Status intermediários; Ações mínima) — dimensionada pela implementação após análise (C-1), sem percentuais fixados por esta spec.
- **FR-003**: A coluna Código MUST exibir os códigos integralmente, sem quebra inadequada e sem largura excessiva.
- **FR-004**: A coluna Inventário MUST receber espaço significativo, com leitura confortável, mínimas quebras de linha quando houver espaço e alinhamento consistente com o cabeçalho.
- **FR-005**: A coluna Escopo MUST receber espaço significativo para textos longos, sem truncamento prematuro nem quebra excessiva.
- **FR-006**: A coluna Progresso MUST ter largura proporcional ao seu conteúdo visual (badges + indicador "X/Y conferidos"), sem espaço exagerado; os elementos internos MUST permanecer legíveis quebrando dentro da coluna quando necessário.
- **FR-007**: A coluna Status MUST ser compacta e suficiente para os badges/rótulos atuais, sem compressão ou quebra inadequada.
- **FR-008**: A coluna Ações MUST ser a mais compacta possível, com o botão visível, clicável, alinhado (alinhamento à direita atual preservado) e acessível.
- **FR-009**: Cabeçalho e corpo MUST compartilhar exatamente a mesma estrutura de colunas (sem deslocamento entre thead e tbody).
- **FR-010**: A solução MUST manter ou melhorar a responsividade existente em desktop grande/médio, notebook, tablet, celular, larguras intermediárias e zoom do navegador dentro da faixa 80%–200% (decisão 2026-09-25), sem overflow horizontal desnecessário onde a tabela puder se adaptar; em larguras mínimas, qualquer rolagem horizontal MUST ficar confinada ao contêiner da tabela, sem conteúdo cortado indevidamente, sobreposição, badges quebrados ou texto ilegível (C-4).
- **FR-011**: A implementação MUST reutilizar a estrutura existente (Bootstrap/CSS do projeto) e, se necessário CSS novo, MUST usar seletor específico desta tabela/tela, sem classes genéricas, sem duplicar estilos e sem alterar o container global (seção 12); o container atual da tela NÃO pode ser alterado para "consertar" a tabela.
- **FR-012**: Nenhuma funcionalidade MAY ser alterada: criação, edição, exclusão, abertura, encerramento, conferência, progresso, status, escopo, regras de negócio, API, banco, modelos, schemas, permissões, autenticação e auditoria permanecem intocados.
- **FR-013**: Nenhum conteúdo exibido MAY ser removido ou alterado: códigos, nomes, escopos, indicadores de progresso, status, ações, ícones, botões, links, tooltips e linhas auxiliares permanecem presentes.
- **FR-014**: A alteração MUST ficar restrita aos arquivos estritamente necessários desta tela; outras tabelas, páginas, menu, cabeçalho global e layout global NÃO podem ser afetados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em desktop, a tabela ocupa ≥ 95% da largura útil do card/container (verificável por medição da renderização) — referência indicativa, sujeita ao julgamento visual.
- **SC-002**: As colunas Inventário + Escopo ocupam juntas a maior parte da largura da tabela (referência indicativa: mais da metade), medida em desktop.
- **SC-003**: Zero desalinhamento entre cabeçalhos e valores em todas as larguras validadas.
- **SC-004**: Zero overflow horizontal da página em larguras a partir de tablet; em celular, qualquer rolagem fica restrita ao contêiner da tabela.
- **SC-005**: Zero sobreposição de cabeçalhos/badges e zero quebras inadequadas (código e status integrais) nas larguras validadas.
- **SC-006**: A suíte de testes existente permanece 100% verde (nenhuma regressão funcional).
- **SC-007**: Validação registrada em `specs/037-inventarios-larguras-colunas/validacao.md` contendo: suíte pytest 100% verde E inspeção manual nos cenários do pedido (desktop grande/médio, notebook, tablet, celular) e na faixa de zoom 80%–200%, com resultado de cada cenário — mesmo formato da validação da 036.

## Assumptions

- Bootstrap 5.3 e `style.css` permanecem a base; nenhuma dependência nova.
- O mecanismo responsivo "já adotado pelo projeto" refere-se ao padrão atual: `table-responsive` + o padrão de layout/escopo comprovado na 036 (layout determinístico com larguras por classe + quebras locais) — reuso decidido na clarificação de 2026-09-25, com as larguras específicas desta tabela determinadas pela implementação (C-1).
- A lista usa paginação/filtros existentes — intocados.
- A alteração pode incluir classes de escopo na tabela e `<style>` embutido no template (precedente 036), sem tocar `style.css` global.

## Fora de escopo

- Qualquer mudança funcional (CRUD, conferência, progresso, status, escopo, filtros, paginação, permissões).
- Outras tabelas/telas (incluída a tabela de bens esperados da tela de detalhe — já tratada pela 036) e o layout global/container.
- Redesenho visual além da distribuição de larguras, quebras e alinhamentos.
- Novos testes automatizados de UI (seguir seção 26 do pedido: apenas executar os existentes; sem testes artificiais).
