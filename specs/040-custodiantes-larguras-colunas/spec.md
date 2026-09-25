# Feature Specification: Ajuste Responsivo da Tabela "Colaboradores & Custodiantes"

**Feature Branch**: `040-custodiantes-larguras-colunas`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Ajustar exclusivamente o layout da tabela da tela **"Colaboradores & Custodiantes"** (`/custodians`): aproveitar o máximo possível da largura horizontal disponível, redistribuindo o espaço entre as 7 colunas (Matrícula, Nome, Cargo, Departamento, E-mail, Bens, Ações). Colunas textuais **Nome**, **Cargo**, **Departamento** e **E-mail** recebem prioridade; **Matrícula** fica proporcional ao conteúdo; **Bens** e **Ações** permanecem compactas. Mesmo princípio das specs 036/037/038/039: redistribuição inteligente, análise antes de alterar, implementação cirúrgica — nenhuma funcionalidade, dado, rota ou regra de negócio é alterada.

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| Tela "Colaboradores & Custodiantes" = `app/web/templates/custodians/list.html` (rota `/custodians`, `colaboradores.visualizar`); tabela no bloco `{% if custodians %}` (linhas ~44–86) | Superfície única a alterar |
| Colunas e conteúdo por célula: **Matrícula** (`tag-badge` + badge condicional "provisória" quando `is_provisional(c.registration_code)`), **Nome** (link `fw-semibold` com ícone `bi-person-circle` → `/custodians/{id}`), **Cargo** (`small`, texto livre — ex.: "Analista Administrativo", "Técnico de Informática"), **Departamento** (badge `badge-soft-gray`), **E-mail** (`small text-muted`), **Bens** (badge pill centralizado `text-center` com `active_assets_count`), **Ações** (`text-end`: "Editar Colaborador" condicional a `colaboradores.editar` + "Ver Bens" sempre) | Sem classes/colgroup de largura; distribuição atual vem do layout automático. Nuances protegidas nos FRs: badge "provisória" condicional na Matrícula, link do Nome com ícone, badge do Departamento, pill do Bens com `text-center`, botão "Ver Bens" com texto (não é só ícone — coluna Ações mais larga que nas telas 036–039) |
| Tabela em `card` > `table-responsive` > `table align-middle`; container global `base.html` (`container-fluid ... max-width:90%`) | Container **não alterado** (FR-011); rolagem confinada ao `table-responsive` quando inevitável |
| Filtro de pesquisa acima da tabela (`input[name="search"]` + Filtrar/Limpar) e botões do header ("Exportar CSV", "Importar CSV", "Cadastrar Colaborador") | Fora do escopo — intocados (só a tabela) |
| Dois estados vazios distintos ("Nenhum colaborador encontrado" com busca; "Nenhum colaborador cadastrado" com CTA) | Edge cases intocados |
| `style.css` não define larguras para esta tabela; `tag-badge` global com `max-width:140px` em ≤479px (L1027); `style.css` versionado em 2 pontos acoplados (base.html + SW allowlist) | CSS embutido no template com classe de escopo (precedente 036/037/038/039), sem bump de cache global |
| `list.html` de custodians não tem block de `head`; `<style>` entra no topo do `{% block content %}` | Mecanismo conhecido e validado nas 036–039 |
| Constitution I/X/XI/XII: escopo cirúrgico, interface consistente, docs fiéis, suíte verde | Restrições de implementação |

## Decisões registradas pelo solicitante (2026-09-25)

- **C-1**: **NÃO fixar percentuais na spec** — larguras determinadas pela implementação após análise do HTML/CSS/comportamento atual (padrão 037–039).
- **C-2**: prioridade de espaço: maior para **Nome**, **Cargo**, **Departamento** e **E-mail**; intermediária para **Matrícula**; compactas: **Bens** e **Ações** (Ações a mais compacta possível).
- **C-3**: a tabela deve utilizar praticamente toda a largura útil disponível do container onde houver espaço, sem grandes vazios e sem colunas excessivamente largas.
- **C-4**: em telas menores, usar o mecanismo responsivo já adotado pelo projeto (incluída rolagem horizontal adequada quando inevitável); sem reduzir fonte excessivamente, esconder/cortar conteúdo ou tornar ações inacessíveis.
- **C-5** (implícita do pedido): `table-layout` (fixed vs auto) é decisão da implementação com base na análise — não aplicado automaticamente (seção 20).

## Clarifications

### Session 2026-09-25

- Q: Na coluna "Departamento" (badge), como o texto longo deve ser tratado quando não couber na largura da coluna? → A: Exibir o texto completo, sem corte nenhum — a linha da tabela cresce para caber o conteúdo integral.
- Q: Para as demais colunas textuais (Nome, Cargo, E-mail), qual comportamento quando o texto for mais largo que a coluna? → A: Texto completo sempre — sem corte vertical (clamp) nem reticências; as linhas podem crescer conforme o conteúdo.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aproveitamento horizontal na listagem de colaboradores (Priority: P1)

Um usuário abre "Colaboradores & Custodiantes" e vê a tabela ocupando praticamente toda a largura útil do card, com Nome, Cargo, Departamento e E-mail dominando o espaço para leitura confortável, Matrícula proporcional, Bens e Ações compactas, cabeçalhos e valores alinhados e todos os links/botões funcionando como hoje.

**Why this priority**: é o objetivo central do pedido — melhor distribuição do espaço horizontal na listagem de colaboradores, ferramenta central de custódia.

**Independent Test**: abrir `/custodians` em desktop e inspecionar/medir o aproveitamento da largura e a proporção entre as 7 colunas (comparação antes/depois).

**Acceptance Scenarios**:

1. **Given** colaboradores listados, **When** a tabela é exibida em desktop, **Then** ela ocupa praticamente toda a largura útil do card, com Nome, Cargo, Departamento e E-mail recebendo a maior parte do espaço.
2. **Given** colaborador com nome completo longo e cargo extenso ("Analista Administrativo", "Diretor Administrativo"), **When** a tabela é exibida com largura suficiente, **Then** ambos aparecem com o mínimo de quebras necessário.
3. **Given** departamento institucional extenso e e-mail longo, **When** a tabela é exibida, **Then** ambos aparecem sem truncamento prematuro e sem quebra em posições inadequadas, e o badge "provisória" da Matrícula permanece íntegro.

---

### User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

O usuário acessa a listagem de notebook, tablet ou celular (e/ou zoom variado): a tabela se adapta conforme o mecanismo do projeto, sem conteúdo cortado indevidamente, sem sobreposição, com as ações acessíveis e qualquer rolagem horizontal confinada ao contêiner da tabela.

**Why this priority**: a listagem de colaboradores é consultada em diversos dispositivos, inclusive em campo durante inventário.

**Independent Test**: abrir `/custodians` em larguras variadas (desktop, notebook, tablet, celular e zoom) e verificar adaptação, legibilidade e acessibilidade dos controles.

**Acceptance Scenarios**:

1. **Given** viewport de notebook/tablet, **When** a tabela é exibida, **Then** a distribuição permanece proporcional, sem sobreposição de cabeçalhos nem colunas colapsadas.
2. **Given** viewport de celular, **When** a tabela é exibida (7 colunas), **Then** o comportamento segue o padrão responsivo do projeto — rolagem horizontal confinada ao contêiner da tabela quando inevitável — com ações acessíveis e conteúdo legível.
3. **Given** zoom do navegador variado, **When** a tabela é exibida, **Then** os critérios de legibilidade e ausência de sobreposição se mantêm.

---

### Edge Cases

- **Matrícula provisória** (`is_provisional`): `tag-badge` + badge "provisória" lado a lado na mesma célula, íntegros, sem quebra inadequada.
- **Cargo longo** ("Analista Administrativo", "Assessor Técnico"): legível, com mínimas quebras quando houver espaço.
- **Departamento extenso** (badge): **texto completo exibido, sem corte** — a linha cresce conforme o conteúdo (clarificação).
- **Nome/Cargo/E-mail longos**: **texto completo sempre** — sem clamp nem reticências; alturas de linha podem variar entre linhas (clarificação).
- **"Ver Bens" (botão com texto + ícone) + "Editar" (ícone)**: ambos acomodados sem aperto; usuário sem `colaboradores.editar` vê apenas "Ver Bens" e a coluna permanece estável.
- **Pill de Bens com contagem alta**: íntegro e centralizado.
- **Lista vazia (com e sem busca)**: ambos os estados vazios inalterados.
- **Tema claro/escuro**: nenhuma cor nova; contraste preservado.
- **Uma única linha na tabela**: distribuição estável por coluna (não por conteúdo da linha).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tabela MUST aproveitar praticamente toda a largura útil disponível do container onde houver espaço (C-3), sem grandes vazios e sem colunas excessivamente largas.
- **FR-002**: A distribuição de larguras MUST ser proporcional à natureza do conteúdo/função de cada coluna, seguindo C-2 (Nome, Cargo, Departamento e E-mail no topo; Matrícula intermediária; Bens e Ações compactas) — dimensionada pela implementação após análise (C-1), sem percentuais fixados por esta spec.
- **FR-003**: A coluna Matrícula MUST exibir os códigos integralmente (incluído o badge "provisória" condicional), sem quebra desnecessária nem truncamento, permanecendo proporcional ao conteúdo real.
- **FR-004**: A coluna Nome MUST receber espaço significativo: nome do colaborador exibido **completamente** (sem clamp nem reticências — clarificação), com o link e o ícone preservados e alinhamento com o cabeçalho.
- **FR-005**: A coluna Cargo MUST receber espaço adequado para cargos maiores ("Analista Administrativo", "Diretor Administrativo", "Assessor Técnico"), exibindo o texto **completamente** (clarificação).
- **FR-006**: A coluna Departamento MUST exibir o **texto completo** do departamento no badge, sem corte algum — a linha da tabela cresce conforme o conteúdo (clarificação).
- **FR-007**: A coluna E-mail MUST exibir o endereço **completamente** (clarificação), sem quebra em posições inadequadas nem reticências.
- **FR-008**: A coluna Bens MUST permanecer compacta, suficiente para o pill de contagem (centralizado), sem espaço exagerado; o excedente beneficia as textuais.
- **FR-009**: A coluna Ações MUST ser a mais compacta possível, acomodando "Editar Colaborador" (condicional a `colaboradores.editar`) e "Ver Bens" (com texto) visíveis, clicáveis, alinhados à direita e acessíveis — dimensionada para o caso de 2 controles.
- **FR-010**: Cabeçalho e corpo MUST compartilhar exatamente a mesma estrutura de colunas (sem deslocamento entre thead e tbody); o container da tela, o filtro de pesquisa e os botões do header NÃO podem ser alterados; a implementação MUST reutilizar a estrutura existente e, se necessário CSS novo, usar seletor específico desta tabela/tela, sem classes genéricas, sem duplicar estilos e sem bump de cache global.
- **FR-011**: A solução MUST manter ou melhorar a responsividade existente em desktop grande/médio, notebook, tablet, celular, larguras intermediárias e zoom (faixa 80%–200%, precedentes 036–039), sem overflow horizontal desnecessário onde a tabela puder se adaptar; em larguras mínimas, qualquer rolagem horizontal MUST ficar confinada ao contêiner da tabela, sem conteúdo cortado indevidamente, sobreposição, badges quebrados ou botões inacessíveis (C-4).
- **FR-012**: Nenhuma funcionalidade MAY ser alterada: cadastro/edição/exclusão de colaboradores, pesquisa, filtros, importação CSV, vínculo com bens, custódia, matrícula, departamento, cargo, e-mail, permissões, autenticação, auditoria, API, banco, modelos e schemas permanecem intocados.
- **FR-013**: Nenhum conteúdo exibido MAY ser removido ou alterado: matrícula, badge "provisória", nome, cargo, departamento, e-mail, contagem de bens, ações, ícones, botões, links e tooltips permanecem presentes.
- **FR-014**: A alteração MUST ficar restrita aos arquivos estritamente necessários desta tela; as tabelas de conferência (036), inventários (037), equipamentos (038), movimentações (039) e demais telas/componentes NÃO podem ser afetados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em desktop, a tabela ocupa ≥ 95% da largura útil do card/container (verificável por medição da renderização) — referência indicativa, sujeita ao julgamento visual.
- **SC-002**: As colunas Nome + Cargo + Departamento + E-mail ocupam juntas a maior parte da largura da tabela (referência indicativa: mais da metade), medida em desktop.
- **SC-003**: Zero desalinhamento entre cabeçalhos e valores em todas as larguras validadas.
- **SC-004**: Zero overflow horizontal da página em larguras a partir de notebook; em tablet/celular, qualquer rolagem fica restrita ao contêiner da tabela.
- **SC-005**: Zero sobreposição, zero truncamento indevido (matrícula, textos e e-mails) e zero quebras inadequadas de badges nas larguras validadas.
- **SC-006**: A suíte de testes existente permanece 100% verde (nenhuma regressão funcional).
- **SC-007**: Validação registrada em `specs/040-custodiantes-larguras-colunas/validacao.md` no formato das 036–039: suíte pytest 100% verde E inspeção manual com medição nos cenários do pedido (desktop grande/médio, notebook, tablet, celular) e faixa de zoom 80%–200%, com resultado de cada cenário e comparação antes/depois.

## Assumptions

- Bootstrap 5.3 e `style.css` permanecem a base; nenhuma dependência nova.
- O mecanismo responsivo do projeto refere-se ao padrão validado nas 036–039 (layout determinístico com larguras por classe escopada + quebras locais + `min-width` com rolagem confinada ao `table-responsive`) — reuso esperado, com as larguras desta tabela determinadas pela implementação (C-1) e a escolha final de `table-layout` justificada pela análise (C-5).
- O filtro de pesquisa e os botões do header são intocados; a tabela exibe a página corrente.
- Fonte real do app (Plus Jakarta Sans) é ~20–30% mais larga que fontes de fallback — medições de largura MUST incluir folga para isso (lição da 039).

## Fora de escopo

- Qualquer mudança funcional (CRUD, pesquisa, importação CSV, custódia, permissões).
- Outras tabelas/telas (conferência — 036; inventários — 037; equipamentos — 038; movimentações — 039; locais) e o layout global/container/filtros da própria tela.
- Redesenho visual além da distribuição de larguras, quebras e alinhamentos.
- Novos testes automatizados de UI (seção 27 do pedido: apenas executar os existentes; sem testes artificiais).
