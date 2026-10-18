# Feature Specification: Dropdown de Locais Cadastrados na Conferência Offline

**Feature Branch**: `074-dropdown-locais-conferencia-offline`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "Substituir o campo de digitação manual 'Local onde foi encontrado' da Conferência Offline por um dropdown com os locais cadastrados no SisPatrimônio Pro, reutilizando preferencialmente o mesmo mecanismo de armazenamento local já utilizado pelo inventário, mantendo seleção, persistência e sincronização funcionando sem regressões."

---

## Clarifications

### Session 2026-07-18

- Q: Quando o conferente marcar "Encontrado em local diferente" sem rede e sem nenhuma lista de locais armazenada no dispositivo, o que o sistema deve permitir fazer? → A: Bloquear o registro da coleta com mensagem clara orientando a reconectar e preparar os dados; nenhum texto livre é aceito.
- Q: Quais locais devem aparecer no dropdown da Conferência Offline? → A: Todos os locais cadastrados ativos — o mesmo conjunto que a Conferência Online já exibe hoje.
- Q: Qual estratégia para registros antigos de conferência offline que armazenam o local apenas como nome textual? → A: Mantê-los como estão, sem conversão; apenas os novos registros passam a gravar a referência estável do local.
- Q: Se o diagnóstico concluir que o mecanismo de armazenamento local do inventário não comporta a lista de locais nem com a menor extensão possível, o que deve acontecer? → A: Parar a implementação, apresentar o diagnóstico e reabrir a decisão antes de qualquer código.
- Q: A busca/filtragem dentro do dropdown deve entrar já na primeira versão ou depender do volume real de locais apurado na investigação? → A: Manter condicional: incluir apenas se a investigação apurar volume que comprometa a usabilidade.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Seleção do local por dropdown sem rede (Priority: P1)

Como conferente em campo, desejo **escolher o local onde o bem foi encontrado em uma lista de locais cadastrados** — em vez de digitar o nome manualmente — para registrar a divergência de local com grafia correta, mesmo estando sem conexão com o servidor.

**Why this priority**: é o valor central da funcionalidade. Elimina erro de grafia (causa atual de falhas de validação e de sincronização) e viabiliza o registro correto em campo. Sem esta história, as demais não têm objeto.

**Independent Test**: Com a lista de locais previamente armazenada no dispositivo e sem conexão, abrir a Conferência Offline, marcar "Encontrado em local diferente", escolher um local no dropdown e registrar a coleta — tudo sem qualquer requisição ao servidor e sem digitar texto livre.

**Acceptance Scenarios**:

1. **Given** existem locais cadastrados e armazenados localmente e o dispositivo está sem rede, **When** o conferente seleciona "Encontrado em local diferente", **Then** o campo "Local onde foi encontrado" é apresentado como dropdown com os locais disponíveis, sem campo de texto livre.
2. **Given** o dropdown aberto com locais disponíveis, **When** o conferente escolhe um local e registra a coleta, **Then** a seleção é gravada junto do registro da conferência e entra na fila de sincronização, sem consulta ao servidor.
3. **Given** o resultado da conferência não é "Encontrado em local diferente", **When** o registro é feito, **Then** o campo de local permanece oculto/irrelevante, exatamente como hoje.
4. **Given** o usuário selecionou um local, **When** a lista é exibida novamente, **Then** o local previamente escolhido continua marcado no dropdown.

---

### User Story 2 - Disponibilização e atualização da lista de locais (Priority: P2)

Como sistema, desejo **disponibilizar a lista de locais cadastrados no armazenamento local já usado pelo inventário** e mantê-la atualizada quando houver conexão, para que a Conferência Offline opere sem depender de um mecanismo paralelo.

**Why this priority**: sem a lista disponível localmente, a US1 não funciona offline. É a condição de habilitação, mas depende da US1 para gerar valor ao usuário.

**Independent Test**: Com conexão, preparar/usar o fluxo normal da aplicação; depois desligar a rede e confirmar que o dropdown apresenta os locais; derrubar a rede durante uma atualização e confirmar que a lista anterior continua disponível.

**Acceptance Scenarios**:

1. **Given** o dispositivo tem conexão e existem locais cadastrados, **When** os dados locais são preparados/atualizados conforme o fluxo da aplicação, **Then** os locais ficam disponíveis para uso offline pelo mecanismo de armazenamento local existente.
2. **Given** existe uma lista válida armazenada localmente, **When** uma tentativa de atualização falha por rede indisponível, **Then** a lista prévia permanece íntegra e utilizável.
3. **Given** o dispositivo nunca baixou a lista de locais e está sem conexão, **When** o conferente abre o campo de local na Conferência Offline, **Then** a aplicação exibe mensagem clara orientando que é preciso disponibilizar os dados antes de trabalhar offline — sem simular opções, sem selecionar local automaticamente e sem aceitar texto livre; o registro da coleta é bloqueado até que os dados estejam disponíveis.
4. **Given** houve conexão posteriormente, **When** a lista é atualizada, **Then** não ocorrem duplicações e os dados locais anteriores só são substituídos após a confirmação dos novos dados.
5. **Given** o mesmo cadastro de locais, **When** as opções do dropdown offline são comparadas com as opções oferecidas pela Conferência Online, **Then** o conjunto de locais é idêntico — nenhum local ativo ausente e nenhum local extra.

---

### User Story 3 - Persistência e sincronização da seleção (Priority: P3)

Como sistema, desejo que **a localização escolhida persista no registro da conferência offline e seja sincronizada com o servidor depois**, mantendo a associação correta entre local e conferência e preservando registros antigos pendentes.

**Why this priority**: é o que garante integridade patrimonial e aproveitamento do registro coletado; depende das US1 e US2, mas pode ser validada isoladamente sobre registros já coletados.

**Independent Test**: Registrar uma coleta com local selecionado, reabrir a tela/aplicação (a seleção permanece), reconectar e sincronizar; repetir com registros antigos que armazenam apenas o nome textual do local, confirmando que nenhum é descartado.

**Acceptance Scenarios**:

1. **Given** uma coleta com local selecionado ainda pendente, **When** a tela ou a aplicação é reaberta, **Then** a seleção é recuperada do armazenamento local da conferência.
2. **Given** uma coleta pendente com local selecionado, **When** a conexão é restabelecida e a sincronização roda, **Then** o registro é sincronizado uma única vez, com o local associado ao registro correto, e validado pelo servidor.
3. **Given** registros antigos de conferência offline armazenam o local em formato textual, **When** a nova implementação é aplicada, **Then** esses registros continuam sendo exibidos, tratados e sincronizáveis, sem conversão automática de formato — nenhum dado pendente é descartado silenciosamente.
4. **Given** uma sincronização falha, **When** a falha é tratada, **Then** os registros coletados permanecem preservados na fila para nova tentativa, sem perda e sem duplicação.
5. **Given** um bem com localização cadastral diferente do local encontrado, **When** o conferente registra o local encontrado, **Then** a localização cadastral do patrimônio **não** é alterada — as duas informações permanecem distintas.

---

### Edge Cases

- Lista de locais vazia (nenhum local cadastrado): o dropdown não oferece opções e a interface explica a situação; nenhum valor é atribuído automaticamente.
- Dados locais inexistem e não há rede: o registro da coleta com "local diferente" é bloqueado com mensagem clara de orientação (reconectar e disponibilizar os dados); sem texto livre, sem opções inventadas e preservando qualquer dado já coletado.
- Falha na atualização da lista (rede cai no meio): lista local prévia permanece disponível e utilizável.
- Local removido/desativado no servidor depois de armazenado localmente: a seleção não é descartada; o registro segue para sincronização e o servidor aplica suas regras de validação.
- Referência/identificador de local inexistente ou obsoleto em registro local: tratado pelas regras de validação/sincronização existentes, sem atribuição arbitrária de local.
- Locais com nomes iguais ou semelhantes: a apresentação usa as informações complementares já existentes no cadastro, quando disponíveis, para evitar escolha equivocada.
- Dados antigos que armazeniam apenas o nome do local: mantidos, exibidos e sincronizáveis conforme as regras de compatibilidade atuais.
- Falha durante a sincronização: registros permanecem preservados na fila (pendente/falha/conflito) até novo tratamento.
- Registros locais parcialmente preenchidos: não são invalidados nem apagados pela nova implementação.
- Perda de conexão no meio da seleção: a seleção é operada e gravada localmente sem depender de rede.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Na Conferência Offline, o sistema DEVE substituir a entrada manual de "Local onde foi encontrado" por um dropdown com os locais cadastrados no SisPatrimônio Pro; o usuário NÃO deverá precisar digitar o nome do local.
- **FR-002**: A implementação DEVE usar a Conferência Online como referência de consulta, apresentação e identificação dos locais, reutilizando componentes/regras existentes quando tecnicamente compatíveis; o comportamento da Conferência Online NÃO pode ser alterado. O conjunto de locais apresentado no dropdown offline DEVE ser idêntico ao conjunto que a Conferência Online exibe hoje (locais cadastrados ativos), sem filtros adicionais nem restrições novas.
- **FR-003**: Os locais DEVEM ser disponibilizados na Conferência Offline reutilizando o mecanismo de armazenamento local já empregado pelo inventário, desde que a investigação confirme sua adequação; é PROIBIDO criar um segundo sistema de persistência local, novo banco local ou nova rotina de sincronização — ampliações do mecanismo atual devem ser estritamente mínimas, sem alterar o funcionamento do inventário. Caso o diagnóstico conclua que o mecanismo não comporta a lista de locais nem com a menor extensão possível, a implementação DEVE ser interrompida, com o diagnóstico apresentado e a decisão reaberta antes de qualquer código — é PROIBIDO contornar a situação criando um mecanismo de persistência paralelo.
- **FR-004**: A lista de locais DEVE estar disponível sem conexão: carregada e armazenada enquanto houver conectividade, recuperada do dispositivo na Conferência Offline, utilizável sem consulta ao servidor, e não eliminada por indisponibilidade de rede; na ausência de dados locais, a interface DEVE informar a situação e orientar sobre a necessidade de disponibilizar os dados antes de trabalhar offline, **bloqueando o registro da coleta com "local diferente"** até que os dados estejam disponíveis — sem simular lista, sem selecionar local arbitrariamente e sem aceitar texto livre como recurso alternativo.
- **FR-005**: Quando houver conexão, os locais DEVEM ser atualizados preferencialmente pelo mesmo ciclo de atualização do inventário; a atualização DEVE preservar os dados locais válidos em caso de falha, evitar apagar lista antes de confirmar os novos dados, evitar duplicações, respeitar caches/sincronização existentes e não introduzir requisições excessivas ao servidor. Não implementar rotina periódica nova se a existente já atende.
- **FR-006**: O sistema DEVE identificar o local selecionado preferencialmente por identificador único e estável, quando existir no cadastro, preservando essa referência no armazenamento local e usando o nome apenas para apresentação; a decisão DEVE ser documentada no diagnóstico técnico. O modelo de dados e o contrato de sincronização NÃO devem ser alterados sem necessidade técnica comprovada.
- **FR-007**: A seleção do local DEVE ser persistida junto ao registro da conferência offline pelo mecanismo atual de armazenamento dessa conferência, permanecendo disponível após atualização de interface, reabertura de tela, reabertura da aplicação e períodos sem conexão, sem criar estrutura de persistência paralela.
- **FR-008**: Após o restabelecimento da conexão, o registro DEVE ser sincronizado pelo mecanismo existente, mantendo o local associado ao registro correto e submetido à validação do servidor; incompatibilidade de formato local × servidor só gera adaptação estritamente necessária, sem duplicação, perda de dados ou alteração indevida de equipamentos.
- **FR-009**: O sistema DEVE preservar a distinção entre o local cadastral do patrimônio e o "Local onde foi encontrado" na conferência; registrar o local encontrado NÃO pode alterar automaticamente a localização cadastral do bem, que continua sujeita às regras de negócio (movimentações) existentes.
- **FR-010**: O sistema DEVE tratar adequadamente: lista vazia, dados locais indisponíveis, falha de atualização, perda de conexão durante carregamento, local removido/desativado no servidor, identificador inexistente, nomes iguais/semelhantes, dados antigos com nome textual, falha de sincronização e registros parcialmente preenchidos — com mensagens claras ao usuário.
- **FR-011**: É PROIBIDO descartar registros coletados por falha de sincronização, selecionar automaticamente um local para evitar erro de validação ou apagar dados pendentes; os dados pendentes DEVEM ser preservados até tratamento pelas regras existentes.
- **FR-012**: A implementação DEVE ser compatível com registros de conferência offline existentes (inclusive pendentes de sincronização), sem descarte de dados antigos e sem migrações destrutivas. Registros antigos que armazenam o local como nome textual DEVEM ser mantidos como estão — **sem conversão automática de formato**; a referência estável do local passa a ser gravada apenas nos novos registros. O tratamento exibido dos antigos DEVE continuar resolvendo o nome conforme as regras atuais, e eles DEVEM permanecer sincronizáveis pelo contrato atual do servidor.
- **FR-013**: A investigação técnica (arquivos da Conferência Online/Offline, fonte de dados dos locais, mecanismo de armazenamento local do inventário, fluxo de sincronização, formato dos registros e testes existentes) DEVE ser produzida e apresentada como diagnóstico **antes** de qualquer alteração de código, fundamentada apenas na inspeção do código real.

### Non-Functional Requirements

- **RNF-001**: O dropdown DEVE seguir o padrão visual e de interação já adotado pela aplicação, mantendo consistência com os demais campos de seleção e responsividade em desktop e dispositivos móveis.
- **RNF-002**: Havendo grande quantidade de locais, a interface DEVE avaliar pesquisa/filtragem dentro do dropdown, filtrando apenas locais existentes (sem permitir cadastro de locais por texto livre) e sem introduzir biblioteca adicional sem necessidade comprovada. **Decisão (Clarifications 2026-07-18): regra mantida como condicional** — a busca/filtragem será incluída somente se a investigação apurar volume de locais que comprometa a usabilidade; a primeira versão pode dispensá-la.
- **RNF-003**: Os locais DEVEM ser apresentados de forma a evitar escolhas equivocadas, usando informações complementares já existentes no cadastro quando houver homonímia — sem inventar informações.
- **RNF-004**: A associação rótulo↔campo, a navegação por teclado e os recursos de acessibilidade já adotados no sistema DEVEM ser preservados, sem regressões.
- **RNF-005**: O servidor DEVE continuar validando a existência e a validade do local recebido; o dropdown NÃO substitui a validação server-side.
- **RNF-006**: Os dados locais DEVEM respeitar os mecanismos de persistência, permissões e proteção já usados pelo inventário, sem armazenar informações desnecessárias nem enfraquecer controles existentes.
- **RNF-007**: A seleção DEVE manter sua associação com o registro correto da conferência, nunca sendo aplicada acidentalmente a outro registro.

### Key Entities

- **Local (cadastro de locais)**: unidade física/de espaço do SisPatrimônio Pro; possui identificador estável (a confirmar na investigação) e nome de apresentação; é a fonte das opções do dropdown.
- **Registro de conferência offline (coleta)**: evento coletado no dispositivo contendo bem/inventário, resultado da conferência, local encontrado (referência ao Local), observação, identificador único de operação e estado de sincronização (pendente/sincronizado/falha/conflito).
- **Dados locais do inventário (lista de locais incluída)**: conjunto de dados mantido no dispositivo pelo mecanismo de armazenamento local existente, que passa a incluir — pela menor extensão possível — a lista de locais para uso offline.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com a lista previamente armazenada e sem conexão, 100% das seleções de local na Conferência Offline são concluídas sem nenhuma requisição ao servidor.
- **SC-002**: 100% dos registros de "local diferente" na Conferência Offline passam a ser feitos por seleção em lista — 0 casos de digitação manual de nome de local e 0 registros com nome fora do cadastro.
- **SC-003**: 100% das seleções persistem após reabertura da tela e da aplicação, conforme o ciclo de persistência existente.
- **SC-004**: Em cenários de teste de sincronização, 100% dos registros coletados chegam ao servidor sem perda e sem duplicação, com o local associado ao registro correto.
- **SC-005**: Em falha de atualização da lista, 100% das listas locais previamente válidas permanecem disponíveis (nenhuma lista perdida por falha temporária).
- **SC-006**: Quando não há dados locais e não há rede, 100% dos casos exibem mensagem de orientação clara e bloqueiam o registro da coleta — 0 opções de local inventadas, 0 seleções automáticas, 0 registros concluídos com texto livre.
- **SC-007**: Registros antigos de conferência offline (com nome textual) continuam 100% tratáveis e sincronizáveis — 0 descartes silenciosos.
- **SC-008**: A suíte de testes existente permanece 100% verde, com 0 regressões na Conferência Online, no inventário, na persistência local e na sincronização.
- **SC-009**: O número de arquivos alterados é restrito ao estritamente necessário — 0 alterações fora do escopo (conforme auditoria final do diff).

---

## Assumptions

- A investigação técnica obrigatória (FR-013) antecede qualquer alteração de código; a implementação só começa depois de identificado o mecanismo real de armazenamento local do inventário e demonstrada a forma de reutilizá-lo. Esta SPEC descreve o quê/porquê; o como será detalhado na fase de planejamento (`/speckit-plan`).
- O cadastro de locais possui identificador único e estável, usado hoje pela Conferência Online para identificar o local; caso a investigação contrarie isso, prevalece a menor alteração compatível com a arquitetura (FR-006).
- A quantidade atual de locais cadastrados é tratada como moderada; busca/filtro dentro do dropdown só será especificado se a investigação indicar volume que comprometa a usabilidade (RNF-002).
- Registros de conferência offline existentes armazenam o local em formato textual (nome); a compatibilidade com esse formato é obrigatória e a decisão registrada nas Clarifications (2026-07-18) é **não converter** dados antigos — a referência estável vale só para novos registros (FR-006/FR-012).
- A Conferência Online, o inventário, as regras de movimentação/permissões e o contrato de sincronização permanecem inalterados, salvo adaptação estritamente indispensável comprovada na investigação.
- Nenhuma dependência nova de biblioteca será introduzida sem necessidade comprovada.
- Fora do escopo: alterações de banco de produção, migrações destrutivas, mudanças de autenticação/permissões/infraestrutura e alterações na localização cadastral dos bens.
