# Feature Specification: Ajuste Responsivo das Larguras das Colunas na Tabela de Conferência de Inventário

**Feature Branch**: `036-conferencia-larguras-colunas`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Ajustar exclusivamente a apresentação da tabela da tela de conferência de inventário do SisPatrimônio Pro, redistribuindo o espaço horizontal entre as colunas: as colunas textuais **BEM** e **LOCAL ESPERADO** devem receber mais espaço; as colunas de conteúdo curto **RESULTADO** e **CONFERIR** devem ficar compactas. Alteração exclusivamente visual/layout — nenhuma regra de negócio, banco de dados, API ou fluxo de conferência é alterado.

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| A tabela-alvo está em `app/web/templates/inventarios/detail.html` (bloco "Bens esperados", `<table class="table align-middle">` dentro de `table-responsive`, linhas ~226–276) | Superfície única a alterar; as demais tabelas da mesma página (card "Conflitos offline" e card de coletas offline) têm estrutura própria e NÃO devem ser afetadas |
| Colunas atuais: `Tombamento` (link com `tag-badge`), `Bem` (`small`, `fw-semibold`), `Local esperado` (`small text-muted`), `Resultado` (badge + linhas auxiliares opcionais), `Conferir` (`text-end`, botão-ícone `btn-ghost btn-icon` que abre modal) | Sem classes de largura específicas por coluna; a distribuição atual vem do layout automático do navegador, que favorece células com mais conteúdo |
| A célula **Resultado** não contém apenas o badge curto: pode incluir **observação** (`<div>` com `font-size:.72rem`) e **metadados** de quem/when conferiu (`font-size:.68rem`) | Nuance do requisito FR-005: a coluna deve ficar compacta sem impedir a leitura dessas linhas auxiliares (que podem quebrar linha dentro da coluna) |
| O badge de `LOCAL_DIFERENTE` anexa o local encontrado (`⚠ Local diferente: {nome}`), podendo ficar longo | Edge case registrado: badge com conteúdo longo não pode forçar alargamento desproporcional da coluna |
| `style.css` não define larguras de coluna para esta tabela (busca por seletores de largura/coluna não encontrou regras específicas) | Não há duplicação a remover; a correção introduzirá o controle de largura (classes do framework já presentes ou CSS restrito à tela) |
| A página usa Bootstrap 5.3 + CSS do projeto (`style.css`), tema claro/escuro por variáveis | A implementação deve reutilizar o que existe; nada de nova dependência |
| Constitution I/X/XI/XII: escopo cirúrgico, interface consistente, documentação fiel, suíte verde | Restrições de implementação |

## Decisões registradas pelo solicitante (2026-09-25)

- **C-1**: a coluna **TOMBAMENTO** NÃO deve ser muito reduzida — já está relativamente compacta; dimensioná-la conforme o conteúdo.
- **C-2**: o ganho principal vem de **RESULTADO + CONFERIR**; o espaço liberado deve ir **principalmente para BEM + LOCAL ESPERADO**.
- **C-3**: prioridade de espaço em telas menores: 1º BEM, 2º LOCAL ESPERADO, 3º TOMBAMENTO, 4º RESULTADO, 5º CONFERIR.
- **C-4**: larguras NÃO iguais entre as colunas — distribuição proporcional à natureza do conteúdo de cada uma.

---

## Clarifications

### Session 2026-09-25

- Q: As proporções do SC-001 (Bem + Local esperado juntas ≥ 50% e Resultado + Conferir juntas < 25% da largura da tabela) devem ser tratadas como limites obrigatórios de aceitação ou apenas como referência indicativa sujeita a julgamento visual? → A: **Referência indicativa** — servem de guia de design; o julgamento visual prevalece desde que a intenção (colunas textuais dominando a largura, Resultado/Conferir compactas) seja claramente atendida.
- Q: A validação desta alteração visual deve exigir execução manual nos 4 cenários (desktop largo/médio, tablet, celular) com registro em `validacao.md`, ou basta a suíte automatizada existente mais verificação rápida em desktop? → A: **Completa como 033/035** — suíte pytest verde E validação manual nos 4 cenários registrada em `specs/036-conferencia-larguras-colunas/validacao.md`.
- Q: Qual faixa de zoom do navegador deve ser usada na validação de responsividade (FR-008/US2)? → A: **80% a 200%** — faixa típica de uso real (Chrome/Edge), cobrindo zoom-out e zoom-in moderados.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Proporção correta das colunas na conferência (Priority: P1)

Um usuário conferindo um inventário abre a tela do inventário e visualiza a tabela de bens esperados. As colunas textuais (Bem, Local esperado) dominam a largura da tabela com seus conteúdos legíveis, enquanto Resultado e Conferir ocupam apenas o necessário para badge e botão. Cabeçalhos e conteúdos permanecem alinhados e nada muda de comportamento.

**Why this priority**: é o próprio objetivo do pedido — a distribuição atual desperdiça espaço nas colunas curtas e comprime as textuais.

**Independent Test**: abrir a tela do inventário em desktop e inspecionar visualmente as proporções (Bem e Local esperado dominando; Resultado e Conferir compactas; alinhamento cabeçalho/linhas).

**Acceptance Scenarios**:

1. **Given** inventário com bens esperados listados, **When** a tabela é exibida em desktop, **Then** Bem e Local esperado ocupam juntas a maior parte da largura, e Resultado/Conferir ocupam apenas o espaço de badge/botão.
2. **Given** local esperado com nome institucional longo (ex.: "IPMJP - Superintendência Adjunta"), **When** a tabela é exibida com largura suficiente, **Then** o nome aparece completo, em linha única, sem truncamento.
3. **Given** itens conferidos e pendentes misturados, **When** a tabela é exibida, **Then** os badges de resultado ficam legíveis sem quebra inadequada e o botão de conferir permanece visível, clicável e alinhado com sua coluna.

---

### User Story 2 - Usabilidade em telas menores e zoom (Priority: P2)

O conferidor usa notebook, tablet ou celular (e/ou zoom do navegador). A tabela se adapta: as colunas textuais preservam prioridade de espaço conforme C-3, RESULTADO e CONFERIR permanecem compactas, sem overflow horizontal desnecessário onde a tabela consegue se adaptar, e o botão de conferência continua acessível.

**Why this priority**: a tabela é usada em campo; a correção só está completa se funcionar além da resolução de desenvolvimento.

**Independent Test**: abrir a mesma tela em larguras variadas (desktop, tablet, celular e níveis de zoom) e verificar adaptação, legibilidade e acesso ao botão.

**Acceptance Scenarios**:

1. **Given** viewport de tablet ou notebook, **When** a tabela é exibida, **Then** nenhuma coluna fica cortada e não surge overflow horizontal desnecessário.
2. **Given** viewport de celular, **When** a tabela é exibida, **Then** o conteúdo permanece utilizável (legível, botão acessível), com rolagem horizontal apenas quando inevitável e restrita ao contêiner da tabela.
3. **Given** zoom do navegador entre 80% e 200%, **When** a tabela é exibida, **Then** os mesmos critérios de legibilidade e ausência de sobreposição se mantêm.

---

### Edge Cases

- **Badge com local anexado** (`Local diferente: {nome do local}`): conteúdo potencialmente longo dentro da coluna compacta — deve quebrar dentro da coluna (ou truncar com recurso de título), nunca alargar a coluna desproporcionalmente nem sobrepor vizinhos.
- **Observação longa** registrada em um item: as linhas auxiliares da célula Resultado devem quebrar linha dentro da coluna compacta, permanecendo legíveis.
- **Nome de bem muito longo**: deve quebrar em linha seguinte quando a viewport não permitir linha única, sem estourar a célula nem provocar overflow da tabela.
- **Tombamento com formato longo** (padrões atuais do sistema): a coluna Tombamento dimensionada por conteúdo deve acomodá-lo sem quebra inadequada.
- **Inventário encerrado**: sem botão de conferir (estado atual), a coluna Conferir não deve reservar espaço vazio desproporcional.
- **Tema escuro/claro**: a alteração é de largura/alinhamento — nenhum contraste ou cor pode ser afetado em nenhum dos temas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tabela de bens esperados da conferência MUST distribuir as larguras das colunas de forma proporcional à natureza do conteúdo: colunas textuais (Bem, Local esperado) com as maiores larguras; Resultado e Conferir compactas; larguras NÃO iguais (C-4).
- **FR-002**: A coluna Tombamento MUST ser dimensionada conforme o conteúdo típico do tombamento (badge/chip completo legível) sem ocupar espaço excessivo — e NÃO deve ser significativamente reduzida em relação ao estado atual (C-1).
- **FR-003**: A coluna Bem MUST receber mais espaço horizontal do que recebe atualmente; quando a largura permitir, o conteúdo MUST permanecer em linha única, com quebra graciosa (sem overflow/corte) quando não permitir.
- **FR-004**: A coluna Local esperado MUST estar entre as colunas de maior largura da tabela; nomes institucionais longos MUST permanecer legíveis, em linha única quando houver espaço suficiente.
- **FR-005**: A coluna Resultado MUST ter largura reduzida ao necessário para o badge legível; as linhas auxiliares existentes (observação e metadados de conferência) MUST permanecer legíveis quebrando linha dentro da coluna, sem impedir a compactação.
- **FR-006**: A coluna Conferir MUST ter largura mínima suficiente para o botão/ícone de ação (visível, clicável, alinhado com o cabeçalho, acessível em telas menores).
- **FR-007**: Cabeçalho e conteúdo de cada coluna MUST permanecer alinhados (incluídos os alinhamentos atuais distintos, ex.: coluna de ação à direita), sem desalinhamento entre cabeçalhos, linhas e controles.
- **FR-008**: A tabela MUST permanecer responsiva em desktop, notebook, tablet, celular e níveis de zoom do navegador dentro da faixa 80%–200% (decisão 2026-09-25), sem overflow horizontal desnecessário onde for possível adaptar; em larguras menores, a prioridade de espaço segue C-3 (Bem > Local esperado > Tombamento > Resultado > Conferir).
- **FR-009**: A implementação MUST reutilizar a estrutura e classes existentes do projeto (incluídos os recursos do framework CSS já presentes), podendo acrescentar CSS restrito à tabela/tela de conferência; é PROIBIDO duplicar estilos, criar segunda implementação equivalente ou afetar outras tabelas/páginas.
- **FR-010**: Nenhuma regra funcional MAY ser alterada por esta feature: regras de inventário/conferência, status, API, banco, modelos, schemas, permissões, autenticação, auditoria, movimentações, QR Code, filtros, pesquisa, paginação e ações da tabela permanecem intocadas.
- **FR-011**: Nenhum dado exibido atualmente MAY ser removido ou alterado: links, badges, observações, metadados e modais de conferência continuam presentes e funcionando exatamente como antes.
- **FR-012**: A alteração MUST ser restrita aos arquivos estritamente necessários da tela de conferência; as demais tabelas da mesma página (Conflitos offline, coletas offline) e qualquer outra tela NÃO podem ser afetadas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em desktop, as colunas Bem + Local esperado ocupam juntas mais da metade da largura da tabela, e Resultado + Conferir juntas ocupam menos de um quarto da largura total — **referência indicativa** (decisão 2026-09-25): serve de guia de design e verificação por inspeção/medição; a aceitação final é visual, desde que a intenção (textuais dominando, curtas compactas) seja claramente atendida.
- **SC-002**: Nomes de locais com 35–45 caracteres (padrão institucional atual) exibem-se completos, sem truncamento, em desktop.
- **SC-003**: Zero desalinhamento entre cabeçalhos e conteúdos, verificado visualmente nas larguras testadas (desktop largo, desktop médio, tablet, celular).
- **SC-004**: Zero overflow horizontal da página em larguras a partir de tablet; em celular, qualquer rolagem horizontal fica restrita ao contêiner da tabela.
- **SC-005**: A suíte de testes existente permanece 100% verde após a alteração (nenhuma regressão funcional — a mudança é de apresentação).
- **SC-006**: Nenhum comportamento funcional alterado: abertura dos modais de conferência, filtros, pesquisa e paginação operam identicamente (comprovado pelos testes existentes de conferência/visual).
- **SC-007**: Validação registrada em `specs/036-conferencia-larguras-colunas/validacao.md` contendo: suíte pytest 100% verde E inspeção manual executada nos 4 cenários do pedido (desktop largo, desktop médio, tablet, celular) e na faixa de zoom 80%–200% do navegador, com resultado de cada cenário.

## Assumptions

- Bootstrap 5.3 e o `style.css` do projeto permanecem a base estilística; nenhuma nova dependência é introduzida.
- O print da tela fornecido pelo solicitante é a referência visual do problema (colunas Resultado/Conferir largas demais; Bem/Local esperado comprimidas).
- A tela continua exigindo as permissões atuais para exibir a tabela e o botão de conferir; nada de acesso muda.
- Alteração exclusivamente de apresentação: pode incluir classes de utilitário do framework já carregado e/ou CSS específico restrito à tela; não altera templates além do necessário.

## Fora de escopo

- Redesenho visual da tela (cores, tipografia, componentes) além da distribuição de larguras e alinhamentos das colunas.
- Alterações nas outras tabelas da mesma página (Conflitos offline, coletas offline) ou em qualquer outra tela/tabela do sistema.
- Qualquer mudança de regra de negócio, dados, API, permissões, auditoria ou fluxo de conferência.
- Mudanças de tema claro/escuro (apenas garantir que nada nelas seja afetado).
