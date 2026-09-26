# Feature Specification: Ajuste Responsivo da Tabela "Usuários do Sistema"

**Feature Branch**: `043-usuarios-larguras-colunas`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Ajustar exclusivamente o layout da tabela da tela **"Usuários do Sistema"** (`/admin/users`): aproveitar o máximo possível da largura horizontal disponível e **manter os textos das colunas em uma única linha sempre que a largura permitir** (regra prioritária), com truncamento controlado + tooltip/title quando necessário e responsividade preservada. As 7 colunas (Usuário, E-mail, Origem, Perfis, Status, Último Acesso, Ações) recebem prioridades distintas: textuais **E-mail, Usuário e Perfis** no topo; **Último Acesso** intermediária; **Origem, Status e Ações** compactas. Mesmo princípio das specs 036–042: análise antes de alterar, implementação cirúrgica — nenhuma regra de autenticação, autorização, usuários, perfis, permissões, banco, API ou regra de negócio é alterada.

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| Tela "Usuários do Sistema" = `app/web/templates/admin/users/list.html` (rota `/admin/users` em `app/web/admin_routes.py:136`, gate `usuarios.visualizar`; renderizado em admin_routes.py:162) | Superfície única a alterar |
| 7 colunas: **Usuário** (username `fw-semibold` com ícone `bi-person-circle` + badge condicional "ADMIN" quando `u.is_admin`; segunda linha condicional `full_name` em `text-muted` pequena), **E-mail** (`small text-muted`, fallback "-"), **Origem** (badge `badge-soft-primary` com ícone `bi-hdd-network` "Active Directory" OU `badge-soft-gray` "Local"), **Perfis** (`d-flex flex-wrap gap-1` de badges `badge-soft-gray` por papel OU "Sem perfil" em `badge-soft-red`), **Status** (badge `bg-success-subtle text-success` "Ativo" OU `badge-soft-red` "Bloqueado"), **Último Acesso** (`small text-muted text-nowrap` — `dd/mm/YYYY HH:MM` ou "Nunca"), **Ações** (`text-end text-nowrap`: "Editar Usuário" `btn-icon` condicional a `usuarios.editar`) | Nuances protegidas nos FRs: badge ADMIN condicional, linha full_name, badge AD com ícone, flex-wrap de Perfis, badges de Status, `text-nowrap` existentes, condição do Editar |
| Sem `<colgroup>` nem classes de largura; container `card` > `table-responsive` > `table align-middle` (sem bordas/hover específicos desta tela) | Distribuição atual vem do layout automático |
| Header "Novo Usuário" condicional a `usuarios.criar`; card de busca/filtro (search + status_filter + Filtrar/Limpar); contador "Mostrando N usuário(s)"; estado vazio "Nenhum usuário encontrado" com CTA condicional | Fora do escopo — intocados (só a tabela); comentários novos não citam controles do header (lição `b75ba99`) |
| Badges Bootstrap têm `white-space: nowrap` embutido — badges curtos (Local/Ativo/Bloqueado/ADMIN) são seguros; labels longos ("Active Directory") precisam de largura suficiente ou quebra entre palavras (lição da 042) | Risco de estouro documentado; tratado nos FRs |
| Lições da família 036–042 incorporadas: fonte real (Plus Jakarta Sans) ~20–30% mais larga que fallbacks; padding real `.5rem .5rem` (16px/coluna); conjunto único em px sem media query de colunas; tooltips via `data-bs-toggle="tooltip"` (auto-inicializados em `base.html:329–333`/`main.js`) | Premissas de dimensionamento e mecanismos validados |
| Testes existentes: `test_help.py` (renderiza listagens), `test_rbac.py` (gates `usuarios.*`), testes de admin/users do domínio | Suíte como regressão (SC-006); run focado definido no plan |
| Constitution I/X/XI/XII: escopo cirúrgico, interface consistente, docs fiéis, suíte verde | Restrições de implementação |

## Decisões registradas pelo solicitante (2026-09-25)

- **C-1**: **NÃO fixar percentuais na spec** — larguras determinadas pela implementação após análise do HTML/CSS/comportamento atual (padrão 037–042).
- **C-2**: prioridade de espaço: maior para **E-mail, Usuário e Perfis**; intermediária para **Último Acesso**; menor para **Origem, Status e Ações** — orientação a ajustar pela análise do conteúdo real (seção 12).
- **C-3**: a tabela deve ocupar praticamente toda a largura útil disponível, sem grandes vazios, sem colunas excessivamente estreitas e sem larguras iguais para todas as colunas.
- **C-4 (regra prioritária da spec, seções 4/17/31)**: valores em **uma única linha** sempre que a largura permitir — combinando nowrap/estratégia equivalente, largura flexível, **truncamento controlado com tooltip/title quando necessário** (nunca texto que desapareça sem consulta) e comportamento responsivo em telas pequenas; nowrap nunca de modo a tornar a tabela inutilizável.
- **C-5** (implícita do pedido): `table-layout` (fixed vs auto) é decisão da implementação com base na análise (seção 22) — não aplicado automaticamente.
- **C-6 (seção 8)**: a forma funcional como os perfis são exibidos (badges) não muda — apenas o layout; os badges individuais nunca quebram no meio, mas os elementos podem se organizar responsivamente quando a largura realmente não bastar.

## Clarifications

### Session 2026-09-25

- Q: Quando um valor precisar ser truncado (ex.: e-mail longo em viewport estreita), qual mecanismo de tooltip usar? → A: Tooltip Bootstrap (`data-bs-toggle="tooltip"`), mesmo mecanismo da 042, inicialização existente (base.html/main.js), leitura confortável do valor completo.
- Q: Na coluna Usuário, como tratar username e full_name quando excederem a largura da coluna? → A: Ambos com linha garantida — corte controlado (ellipsis) + tooltip Bootstrap; visual uniforme nas duas linhas.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Linha única e aproveitamento horizontal em Usuários (Priority: P1)

Um administrador abre "Usuários do Sistema" e vê a tabela ocupando praticamente toda a largura útil do card, com cada valor predominando em **uma única linha**: usuário com seu badge ADMIN íntegro, e-mail completo sem quebra, perfis legíveis, status compacto, último acesso em linha e ações à direita — leitura horizontal rápida do cadastro.

**Why this priority**: é o objetivo central do pedido — leitura horizontal da gestão de usuários.

**Independent Test**: abrir `/admin/users` em desktop e inspecionar/medir o aproveitamento da largura e a quantidade de quebras por linha (comparação antes/depois).

**Acceptance Scenarios**:

1. **Given** usuários listados, **When** a tabela é exibida em desktop, **Then** ela ocupa praticamente toda a largura útil do card, com E-mail, Usuário e Perfis dominando o espaço.
2. **Given** qualquer linha do cadastro, **When** exibida em largura suficiente, **Then** Usuário (com ADMIN quando aplicável), E-mail, Origem, Status e Último Acesso aparecem em uma única linha, sem quebra.
3. **Given** um e-mail longo (ex.: `wellington@ipmjp.pb.gov.br`), **When** a tabela é exibida em desktop, **Then** o endereço aparece completo em uma linha (sem quebra desorganizada); se não couber em viewport menor, corte controlado com tooltip — nunca oculto sem mecanismo de consulta.
4. **Given** múltiplos perfis em um usuário, **When** a linha é exibida, **Then** os badges permanecem íntegros (cada um em uma linha própria, sem quebra interna), organizando-se entre si quando necessário (C-6).

---

### User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

O administrador acessa a listagem de notebook, tablet ou celular (e/ou zoom variado): a tabela mantém a leitura prioritariamente horizontal e, quando a largura realmente não bastar, usa o comportamento responsivo adequado (rolagem confinada, truncamento com tooltip) — sem sobreposição, sem fonte minúscula, sem conteúdo inacessível, com controles utilizáveis.

**Why this priority**: a gestão de usuários é administrada em diversos dispositivos; a tabela não pode depender de uma única resolução.

**Independent Test**: abrir `/admin/users` em larguras variadas (desktop, notebook, tablet, celular e zoom) e verificar adaptação, legibilidade, acessibilidade dos controles e consulta aos valores truncados.

**Acceptance Scenarios**:

1. **Given** viewport de notebook/tablet, **When** a tabela é exibida, **Then** a distribuição permanece proporcional com o máximo em linha única, sem sobreposição nem colunas colapsadas.
2. **Given** viewport de celular, **When** a tabela é exibida (7 colunas), **Then** o comportamento responsivo do projeto se aplica (rolagem confinada ao contêiner quando inevitável), com ações acessíveis e valores truncados consultáveis via tooltip.
3. **Given** zoom do navegador variado, **When** a tabela é exibida, **Then** os critérios de legibilidade, linha única e ausência de sobreposição se mantêm.

---

### Edge Cases

- **Usuário admin**: badge "ADMIN" condicional ao lado do username, íntegro, sem quebra inadequada.
- **Usuário com `full_name`**: segunda linha informativa (menor, muted) preservada — **ambas as linhas (username e full_name) com linha garantida** (corte controlado + tooltip — clarificação); sem `full_name`, apenas o username.
- **Origem Active Directory**: badge com ícone `bi-hdd-network` + texto "Active Directory" íntegro (label longo — largura suficiente ou quebra entre palavras, nunca no meio); "Local" compacto.
- **Usuário sem perfis**: badge "Sem perfil" (`badge-soft-red`) preservado.
- **Múltiplos perfis**: badges do loop com `flex-wrap gap-1` — organização entre badges permitida (C-6), cada badge íntegro.
- **Status**: "Ativo" (`bg-success-subtle`) ou "Bloqueado" (`badge-soft-red`) íntegros, compactos.
- **Último acesso "Nunca"**: fallback preservado; data/hora completa em uma linha (text-nowrap existente).
- **Usuário sem permissão de edição**: vê apenas o header sem "Novo Usuário" e a coluna Ações com o Editar ausente (condição `usuarios.editar` preservada) — coluna estável.
- **Lista vazia (com e sem busca)**: estado "Nenhum usuário encontrado" + CTA inalterados.
- **Tema claro/escuro**: nenhuma cor nova; contraste preservado.
- **Uma única linha na tabela**: distribuição estável por coluna (não por conteúdo da linha).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tabela MUST aproveitar praticamente toda a largura útil disponível do container onde houver espaço (C-3), sem grandes vazios, sem colunas excessivamente estreitas e sem larguras iguais para todas as colunas.
- **FR-002**: A distribuição de larguras MUST ser proporcional à natureza do conteúdo, seguindo C-2 (E-mail, Usuário e Perfis no topo; Último Acesso intermediária; Origem, Status e Ações compactas) — dimensionada pela implementação após análise (C-1), sem percentuais fixados por esta spec.
- **FR-003**: A coluna Usuário MUST manter o username em **uma única linha** (com o ícone e o badge "ADMIN" condicional íntegros) e a linha condicional de `full_name` também em linha garantida — **ambas com corte controlado (ellipsis) + tooltip Bootstrap** quando excederem a largura (clarificação); largura proporcional aos nomes reais.
- **FR-004**: A coluna E-mail MUST receber espaço horizontal significativo e manter o endereço em **uma única linha**; quando não couber, corte controlado por **ellipsis + tooltip Bootstrap** — nunca quebra desorganizada do e-mail em várias linhas, nunca conteúdo sem consulta (C-4/clarificação).
- **FR-005**: A coluna Origem MUST permanecer compacta, com o badge ("Local" ou "Active Directory" com ícone) íntegro e em linha única — label longo pode quebrar apenas entre palavras quando inevitável (lição da 042: `.badge` Bootstrap é nowrap por padrão), nunca no meio.
- **FR-006**: A coluna Perfis MUST exibir os badges de forma legível: cada badge íntegro (sem quebra interna), com a organização responsiva entre badges permitida quando a largura não bastar (C-6); o fallback "Sem perfil" é preservado; a forma funcional de exibição não muda.
- **FR-007**: A coluna Status MUST permanecer compacta, com o badge ("Ativo"/"Bloqueado") íntegro e em linha única, sem ser comprimido a ponto de prejudicar a leitura.
- **FR-008**: A coluna Último Acesso MUST manter data/hora (`dd/mm/YYYY HH:MM`) ou "Nunca" em **uma única linha** (preservando o `text-nowrap` existente), sem quebra de data ou hora e sem redução excessiva de fonte.
- **FR-009**: A coluna Ações MUST ser compacta, ocupando somente o espaço dos controles existentes ("Editar Usuário" `btn-icon` condicional a `usuarios.editar`), visíveis, clicáveis, alinhados à direita e centralizados verticalmente (`text-end text-nowrap` preservados) — sem ocupar espaço das colunas textuais.
- **FR-010**: Cabeçalho e corpo MUST compartilhar exatamente a mesma estrutura de colunas (sem deslocamento entre thead e tbody, sem `width` aplicado somente ao `<td>`, sem redistribuição automática inesperada); os títulos MUST permanecer legíveis e em linha única quando houver espaço; o container da tela, o header, o filtro e o estado vazio NÃO podem ser alterados; a implementação MUST reutilizar a estrutura existente e, se necessário CSS novo, usar seletor específico desta tabela/tela, sem classes genéricas, sem duplicar estilos e sem bump de cache global.
- **FR-011**: A regra geral (C-4/seção 17) MUST ser respeitada: primeiro evitar quebra, depois aproveitar o espaço horizontal, reduzir espaços internos excessivos, manter curtas compactas e usar o economizado nas textuais — adaptar o conteúdo para telas muito pequenas apenas em último caso; truncamento (quando necessário) SEMPRE com tooltip Bootstrap (clarificação), principalmente em Usuário, E-mail, Perfis e Último Acesso; sem truncamento em desktop quando há espaço suficiente.
- **FR-012**: A solução MUST manter ou melhorar a responsividade em desktop grande/médio, notebook, tablet, celular, larguras intermediárias e zoom (faixa 80%–200%, precedentes 036–042), sem overflow indevido; em larguras mínimas, rolagem confinada ao contêiner da tabela, sem sobreposição, sem fonte excessivamente pequena, sem conteúdo cortado sem acesso ao valor completo e com botões acessíveis.
- **FR-013**: Nenhuma funcionalidade MAY ser alterada: autenticação, login/logout, criação/edição/exclusão de usuários, ativação/desativação, perfis, permissões, RBAC, Active Directory, origem, último acesso, auditoria, API, endpoints, banco, modelos e schemas permanecem intocados.
- **FR-014**: Nenhum conteúdo exibido MAY ser removido, escondido ou alterado: usuário, badge ADMIN, full_name, e-mail, origem, perfis, status, último acesso, ações, ícones, badges, links e tooltips permanecem presentes.
- **FR-015**: A alteração MUST ficar restrita aos arquivos estritamente necessários desta tela; as telas das specs 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações), 040 (custodiantes), 041 (Relatório Contábil-Físico), 042 (Trilha de Auditoria) e demais telas/componentes NÃO podem ser afetados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em desktop, a tabela ocupa ≥ 95% da largura útil do card/container (verificável por medição da renderização) — referência indicativa, sujeita ao julgamento visual.
- **SC-002**: As colunas textuais (E-mail + Usuário + Perfis) ocupam juntas a maior parte da largura da tabela (referência indicativa: mais da metade), medida em desktop.
- **SC-003**: Zero desalinhamento entre cabeçalhos e valores em todas as larguras validadas; títulos em linha única quando há espaço.
- **SC-004**: Zero overflow horizontal da página em larguras a partir de notebook; em tablet/celular, qualquer rolagem fica restrita ao contêiner da tabela.
- **SC-005**: Zero sobreposição, zero truncamento sem tooltip e zero quebras inadequadas de badges nas larguras validadas; e-mails/nomes/datas sem quebra em desktop.
- **SC-006**: A suíte de testes existente permanece 100% verde (nenhuma regressão funcional).
- **SC-007**: Validação registrada em `specs/043-usuarios-larguras-colunas/validacao.md` no formato das 036–042: suíte pytest 100% verde E inspeção manual com medição nos cenários do pedido (desktop grande/médio, notebook, tablet, celular) e faixa de zoom 80%–200%, com resultado de cada cenário e comparação antes/depois.

## Assumptions

- Bootstrap 5.3 e `style.css` permanecem a base; nenhuma dependência nova.
- O mecanismo responsivo do projeto refere-se ao padrão validado nas 036–042 (layout determinístico com larguras por classe escopada + `min-width` com rolagem confinada ao `table-responsive`); conjunto único em px sem media query de colunas (lição da 041), com pisos calibrados para a Plus Jakarta Sans (×1,25–1,30).
- Tooltips: `data-bs-toggle="tooltip"` (decisão do solicitante na clarificação — mesmo mecanismo da 042; auto-inicializado em `base.html`/`main.js`).
- Badges Bootstrap são nowrap por padrão (lição da 042): badges curtos desta tabela são seguros; o badge "Active Directory" exige largura suficiente ou `white-space: normal` escopado (quebra entre palavras).
- Header, filtro e estado vazio são intocados; a tabela exibe o resultado corrente da busca/filtro.

## Fora de escopo

- Qualquer mudança funcional (autenticação, RBAC, AD, CRUD de usuários, perfis, permissões, auditoria).
- Outras tabelas/telas (036–042 e demais) e o layout global/container/filtro/header da própria tela.
- Redesenho visual além da distribuição de larguras, quebras, truncamentos controlados e alinhamentos.
- Novos testes automatizados de UI (seção 28 do pedido: apenas executar os existentes; sem testes artificiais).
