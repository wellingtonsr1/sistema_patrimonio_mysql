# Feature Specification: Contraste das Opções de Resultado da Conferência

**Feature Branch**: `011-contraste-conferencia`

**Created**: 2026-09-17

**Status**: Draft

**Input**: Corrigir o baixo contraste das bordas das opções de "Resultado da conferência" (Encontrado / Encontrado em local diferente / Não encontrado / Sem identificação) no modo claro, reutilizando o sistema de temas existente e preservando o modo escuro, sem alterar lógica, layout ou conteúdo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Contornos perceptíveis nos dois temas (Priority: P1)

Um conferente abre a tela de conferência de bem do inventário (página dedicada ou modal de detalhes do inventário) para registrar o resultado de um bem. Cada uma das quatro opções de resultado é apresentada como uma área selecionável delimitada por borda. No modo claro, as bordas atuais praticamente desaparecem contra o fundo: o usuário não percebe que cada opção é uma área independente e clicável, prejudicando a usabilidade. Esta story garante que os contornos sejam claramente perceptíveis no modo claro e continuem perceptíveis no modo escuro.

**Why this priority**: É o problema relatado — sem contorno visível, o usuário não identifica as opções como áreas selecionáveis no tema padrão (claro). Resolve o caso de uso principal de ponta a ponta.

**Independent Test**: Abrir a tela de conferência nos dois temas e verificar visualmente que cada uma das quatro opções apresenta contorno distinguível do fundo, sem tocar em nenhuma regra de negócio.

**Acceptance Scenarios**:

1. **Given** um inventário aberto com bens pendentes, **When** o conferente abre a tela de conferência (página dedicada) no modo claro, **Then** as quatro opções de resultado possuem bordas claramente perceptíveis contra o fundo claro.
2. **Given** um inventário aberto com bens pendentes, **When** o conferente abre o registro de resultado pelo modal de detalhes do inventário no modo claro, **Then** as quatro opções possuem bordas igualmente perceptíveis (mesmo tratamento nas duas telas).
3. **Given** a aplicação em modo escuro, **When** o conferente abre qualquer uma das duas telas de conferência, **Then** as bordas das quatro opções continuam claramente perceptíveis sobre o fundo escuro (sem regressão).

---

### User Story 2 - Estados de seleção, hover e foco preservados (Priority: P2)

Um conferente usa o campo após a correção: passa o mouse sobre as opções, seleciona uma delas (clique ou teclado) e navega pelo formulário com a tecla Tab. Os estados visuais existentes — seleção do rádio, hover com cursor de clique e foco acessível — devem continuar identificáveis; a correção de contraste não pode apagar essas diferenciações.

**Why this priority**: Protege a usabilidade já existente contra regressão introduzida pela mudança visual; é verificável logo após a US1, dependendo apenas dela.

**Independent Test**: Selecionar cada opção, pairar o mouse e navegar por teclado nos dois temas, confirmando que os estados permanecem visualmente distinguíveis.

**Acceptance Scenarios**:

1. **Given** a tela de conferência aberta, **When** o conferente seleciona uma das quatro opções, **Then** o estado selecionado permanece visualmente identificável (marcação do rádio e qualquer destaque existente).
2. **Given** o cursor sobre uma opção, **When** o usuário paira o mouse, **Then** o comportamento de hover existente (cursor de clique) continua funcionando.
3. **Given** navegação por teclado, **When** o foco chega ao grupo de opções, **Then** o estado de foco dos controles permanece perceptível.

---

### User Story 3 - Ausência de efeitos colaterais visuais (Priority: P3)

Qualquer usuário do sistema navega pelas demais telas após a correção. Como a mesma classe utilitária de borda pode ser usada em outros pontos da interface, a correção não pode alterar visualmente componentes fora do campo "Resultado da conferência".

**Why this priority**: Proteção de não-regressão da interface como um todo; não entrega valor novo por si só, mas evita danos.

**Independent Test**: Verificar as telas que utilizam as mesmas classes/estilos e confirmar que nada além das opções de resultado mudou de aparência.

**Acceptance Scenarios**:

1. **Given** a correção aplicada, **When** o usuário navega pelas demais telas do sistema nos dois temas, **Then** nenhum componente fora das opções de resultado apresenta alteração visual.
2. **Given** a mesma classe utilitária usada por outros elementos, **When** a correção é aplicada, **Then** o escopo do ajuste fica restrito ao componente de resultado da conferência (nas duas telas que o renderizam).

### Edge Cases

- **Seleção com resultado já registrado**: quando o item já possui resultado anterior (aviso de re-conferência exibido), as opções continuam visíveis e com os mesmos contornos — o aviso não é afetado.
- **Formulário bloqueado (inventário encerrado)**: quando o formulário não é renderizado, nada muda — a correção não afeta estados de leitura.
- **Preferência de tema por usuário**: a troca de tema em tempo de execução (claro ↔ escuro) atualiza os contornos imediatamente, sem recarregar a página de forma diferente do comportamento atual de troca de tema.
- **Zoom e responsividade**: em larguras reduzidas (empilhamento das opções) e níveis típicos de zoom, os contornos permanecem perceptíveis sem alterar espaçamentos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada uma das quatro opções do campo "Resultado da conferência" (Encontrado, Encontrado em local diferente, Não encontrado, Sem identificação) DEVE apresentar borda/contorno claramente distinguível do fundo no modo claro.
- **FR-002**: As mesmas opções DEVEM manter bordas claramente distinguíveis do fundo no modo escuro (sem regressão).
- **FR-003**: A correção DEVE reutilizar as variáveis/tokens de tema já existentes da aplicação sempre que houver variável adequada; a criação de nova variável só é aceitável se nenhuma existente for apropriada, e nesse caso restrita ao sistema de tokens existente.
- **FR-004**: A correção NÃO DEVE depender de cor de borda fixa única aplicada igualmente aos dois temas (a cor deve acompanhar o tema ativo).
- **FR-005**: Os estados existentes — não selecionado, selecionado, foco e hover — DEVEM permanecer visualmente distinguíveis após a correção.
- **FR-006**: O texto, os indicadores visuais (emojis) e a semântica dos controles de formulário das opções DEVEM permanecer inalterados.
- **FR-007**: Layout, tamanho, espaçamento, posicionamento e responsividade do formulário NÃO DEVEM ser alterados pela correção.
- **FR-008**: O tratamento visual DEVE ser aplicado de forma consistente nas duas telas que renderizam o campo (página de conferência dedicada e modal de detalhes do inventário).
- **FR-009**: Nenhum componente fora das opções do "Resultado da conferência" DEVE ter sua aparência alterada (a mesma classe utilitária de borda usada por outros pontos da interface não pode ser modificada globalmente de forma que os afete).
- **FR-010**: Nenhuma regra de negócio, lógica de conferência, persistência, API, permissão ou auditoria DEVE ser alterada — a feature é exclusivamente visual.
- **FR-011**: A borda NÃO DEVE ser o único meio de comunicar o estado selecionado (a marcação do controle de seleção permanece como indicador primário).

### Key Entities *(include if feature involves data)*

- Não há entidades de dados envolvidas: a feature é exclusivamente de apresentação visual, sem alteração de modelos, banco ou persistência. As opções de resultado e seus valores permanecem exatamente como estão.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No modo claro, 100% das quatro opções de resultado apresentam contorno perceptível contra o fundo (verificação visual nos dois temas das duas telas).
- **SC-002**: No modo escuro, as quatro opções continuam com contorno perceptível (zero regressão visual).
- **SC-003**: Seleção, hover e foco continuam 100% identificáveis após a correção (cenários da US2 aprovados nos dois temas).
- **SC-004**: Nenhuma alteração visual em telas/componentes fora do campo de resultado (varredura das telas nos dois temas sem diferenças indevidas).
- **SC-005**: Conteúdo, valores das opções e comportamento do formulário idênticos ao atual (registro de conferência funciona sem qualquer mudança funcional).
- **SC-006**: A suíte de testes existente permanece no patamar atual (nenhuma regressão funcional).

## Assumptions

- O sistema já possui arquitetura de temas claro/escuro baseada em atributo de tema no elemento raiz e conjunto de variáveis de cor (incluindo tokens de borda para os dois temas) — a correção deve partir desse mecanismo, sem criar nova arquitetura de temas.
- A mesma classe utilitária de borda utilizada pelas opções pode existir em outros pontos da interface; por isso a correção deve preferir escopo restrito ao componente (via variável de tema aplicada ao componente ou classe específica), evitando efeitos globais indevidos.
- Os emojis indicadores (🟢 🟡 🔴 ⚠️) permanecem como diferenciadores de conteúdo; a correção é apenas do contorno.
- A validação desta feature é essencialmente visual/manual (nos dois temas, nas duas telas); não há comportamento novo a cobrir com testes funcionais automatizados — a suíte existente serve como guarda de não-regressão.
- Navegadores alvo: os já suportados pela aplicação.

## Impacto esperado

Componentes confirmados pela análise do código (análise somente leitura, Seção 1):

| Componente | Papel |
|---|---|
| Folha de estilo global da aplicação (arquivo CSS único do tema) | Onde vivem os tokens de borda dos dois temas e onde a regra visual da correção será definida (preferencialmente via variável existente, ex. tokens de borda já presentes para claro e escuro) |
| Template da página de conferência dedicada (`inventarios/conferir.html`) | Renderiza as 4 opções como `<label>` com classe utilitária de borda + estilo inline de cursor |
| Template de detalhes do inventário (`inventarios/detail.html`) | Renderiza o mesmo campo no modal — mesmo markup, mesmo tratamento |

Nenhum outro arquivo precisa ser alterado: modelos, serviços, rotas, API, permissões e banco permanecem intocados.
