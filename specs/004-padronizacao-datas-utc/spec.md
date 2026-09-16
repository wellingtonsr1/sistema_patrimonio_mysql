# Feature Specification: Padronização de Data e Hora (UTC na persistência, America/Recife na apresentação)

**Feature Branch**: `004-padronizacao-datas-utc`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "Feature 004 — Padronização de Data e Hora do SisPatrimônio Pro. Estabelecer convenção única: todos os timestamps gerados pelo sistema e persistidos no banco representam UTC; na apresentação, os timestamps são convertidos de UTC para America/Recife. Preservar a semântica das datas de negócio. Base: análise técnica de 69 ocorrências de data/hora e 28 colunas DATETIME (docs/ANALISE_DATAS_HORARIOS.md, docs/ANALISE_TIMEZONE_INVENTARIO_AUDITORIA.md)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visualização de horários corretos nas telas (Priority: P1)

Um usuário do sistema (administrador, conferente de inventário ou auditor) consulta telas que exibem data e hora de registros — trilha de auditoria, telas de inventário (criação, início, conferência, re-conferência, encerramento), administração de usuários (último acesso, bloqueio temporário, última sincronização) e lista de manutenções — e vê o horário **no fuso de America/Recife**, igual ao relógio de parede do servidor/usuário local.

Hoje esses horários aparecem 3 horas adiantados porque a interface imprime o valor bruto armazenado (UTC). Após a feature, um registro feito às 19:30 locais aparece nas telas como 19:30.

**Why this priority**: É o sintoma visível que motivou a feature e afeta o valor comprobatório da auditoria e do inventário (documentos formais). Não depende da padronização da gravação: pode ser entregue e validada isoladamente sobre os dados já armazenados em UTC.

**Independent Test**: Registrar uma ação (ex.: conferência de item de inventário) em um horário local conhecido e verificar que a tela correspondente exibe o mesmo horário local (com tolerância de minutos de execução). Valor: telas confiáveis sem tocar na gravação.

**Acceptance Scenarios**:

1. **Given** um registro de auditoria gravado com instante UTC correspondente a 15/09/2026 19:30 em Recife, **When** o usuário abre a trilha de auditoria, **Then** a linha exibe "15/09/2026 19:30" (e segundos quando o formato atual os exibe).
2. **Given** um item de inventário conferido às 19:30 locais, **When** o usuário abre os detalhes do inventário, **Then** a conferência aparece com data/hora 19:30 e não 22:30.
3. **Given** um usuário bloqueado temporariamente até 20:00 locais, **When** o administrador abre a edição do usuário, **Then** o aviso de bloqueio mostra 20:00 (horário local), não 23:00.
4. **Given** uma manutenção iniciada às 21:30 locais, **When** o usuário lista manutenções (que exibem apenas a data), **Then** a data exibida é o dia 15/09 (local), e não o dia seguinte por causa do deslocamento de fuso.

---

### User Story 2 - Persistência padronizada em UTC (Priority: P2)

Todo timestamp **gerado pelo próprio sistema** e gravado no banco passa a representar UTC, em todos os módulos: movimentações (aquisição, alocação, transferência, manutenção, devolução, baixa, atualização de estado), importação (entrada de bens via CSV), patrimônio e demais entidades. Em uma mesma tabela não passam a coexistir padrões diferentes: hoje `movements.timestamp` grava hora local enquanto `movements.created_at` grava UTC na mesma linha; após a feature, ambos representam UTC.

**Why this priority**: É a base da convenção única e elimina a inconsistência raiz. Pode ser implementada e testada de forma independente da apresentação (verificando apenas o que é gravado), e é pré-requisito para confiabilidade de ordenação e filtros globais.

**Independent Test**: Executar uma movimentação em um horário local conhecido e verificar que o instante gravado corresponde ao UTC daquele momento (local + 3h no fuso de Recife). Valor: dados internamente consistentes e comparáveis.

**Acceptance Scenarios**:

1. **Given** um usuário registra uma movimentação às 19:30 locais (22:30 UTC), **When** o registro é gravado, **Then** o timestamp da movimentação armazenado representa 22:30 UTC — e não 19:30 rotulado como se fosse UTC.
2. **Given** uma importação CSV cria novos bens com movimentação de entrada, **When** os registros são gravados, **Then** os timestamps gerados pelo sistema (entrada, carimbo do bem) representam UTC, enquanto a data de compra vinda do arquivo permanece exatamente como informada.
3. **Given** uma movimentação altera o cadastro de um bem, **When** o registro de atualização do bem é gravado, **Then** ele também representa UTC (eliminando o caminho que hoje grava hora local).

---

### User Story 3 - Datas de negócio preservadas (Priority: P2)

Datas que representam apenas uma data de negócio — data de compra, fim de garantia, datas digitadas pelo usuário em formulários e datas vindas de arquivos de importação — continuam significando **a data que foi informada**, sem ganhar nem perder um dia por causa de conversão de fuso. A convenção UTC vale para instantes no tempo (timestamps), não para datas puras.

**Why this priority**: Protege contra o erro mais provável e mais grave de uma padronização: converter indevidamente um campo que não é um instante, corrompendo o significado de dados cadastrais. Pode ser validada independentemente das outras histórias.

**Independent Test**: Cadastrar/importar um bem com data de compra "15/09/2026" e verificar que a data exibida e armazenada permanece 15/09/2026. Valor: integridade semântica dos dados de negócio.

**Acceptance Scenarios**:

1. **Given** um CSV com data de compra "15/09/2026", **When** a importação é executada, **Then** a data armazenada e a exibida continuam sendo 15/09/2026.
2. **Given** um usuário cadastra um bem com data de compra 15/09/2026 e garantia até 15/09/2028, **When** o detalhe do bem é exibido, **Then** as datas aparecem como informadas.
3. **Given** os filtros de relatório por período de data de compra, **When** o usuário filtra 01/09/2026 a 15/09/2026, **Then** o resultado permanece consistente com o comportamento atual (comparação por data de negócio).

---

### User Story 4 - Relatórios e documentos com horário correto (Priority: P3)

Os relatórios e documentos exportáveis — PDF, Excel, CSV e páginas HTML de relatório — apresentam datas/horas de dados do sistema no fuso de America/Recife, incluindo os dados de inventário (ata comprobatória), movimentações e o carimbo "Gerado em".

**Why this priority**: Mesma convenção da apresentação web, aplicada às saídas documentais; relevante para o valor comprobatório, mas depende dos mesmos mecanismos das histórias anteriores.

**Independent Test**: Gerar o PDF/CSV do inventário de um inventário conferido às 19:30 locais e verificar que "conferido em" aparece como 19:30. Valor: documentos comprobatórios com horário real.

**Acceptance Scenarios**:

1. **Given** um inventário com conferências registradas às 19:30 locais, **When** o usuário exporta o CSV/PDF do inventário, **Then** os horários impressos representam 19:30 (Recife).
2. **Given** um relatório gerado às 19:30 locais, **When** o documento é produzido, **Then** o carimbo "Gerado em" mostra o horário local 19:30 (mantendo o comportamento correto atual).

---

### User Story 5 - Filtros por período confiáveis (Priority: P3)

Quando um usuário informa um intervalo de data/hora em horário local (ex.: consultas com período inicial/final), o sistema interpreta o intervalo **em America/Recife** e o converte corretamente para UTC antes de comparar com os timestamps armazenados. O resultado inclui exatamente os registros que o usuário esperava ver naquele intervalo local.

**Why this priority**: Depende de a persistência estar em UTC (US2) para fazer sentido; é o último elo da convenção. Hoje os filtros existentes funcionam por coincidência de padrões misturados.

**Independent Test**: Consultar um intervalo conhecido (ex.: 15/09/2026 00:00 a 23:59 locais) após criar um registro às 19:00 locais e verificar que ele é retornado; criar um registro às 23:50 locais e verificar que um filtro que termina às 23:59 o inclui e um filtro de outro dia não o traz por deslocamento. Valor: filtros previsíveis.

**Acceptance Scenarios**:

1. **Given** um registro criado às 19:00 locais (22:00 UTC), **When** o usuário consulta o período local 15/09 00:00–23:59, **Then** o registro é retornado.
2. **Given** registros em dias consecutivos, **When** o usuário consulta o período de um dia local, **Then** nenhum registro é incluído/excluído indevidamente por deslocamento de fuso.

---

### Edge Cases

- **Valor ausente**: campos de data/hora vazios (ex.: inventário não iniciado, `closed_at` vazio, item nunca conferido) continuam exibindo o estado atual ("—", "Nunca", texto condicional) sem erro.
- **Virada de dia**: um instante UTC que corresponde ao dia anterior em Recife (ex.: UTC 16/09 02:30 = Recife 15/09 23:30) deve exibir a data local correta, com o dia de Recife.
- **Segundos**: a conversão não pode perder minutos/segundos onde o formato atual os exibe (ex.: auditoria exibe HH:MM:SS).
- **Dupla conversão**: um valor já convertido para apresentação não pode sofrer nova conversão (diferença de 6h) em nenhum caminho.
- **Deslocamento fixo proibido**: a conversão deve usar o fuso nomeado de America/Recife (com regras oficiais de fuso), não uma subtração fixa de 3 horas.
- **Dados antigos em transição**: registros de teste existentes gravados em hora local (movimentações) poderão parecer com horário incorreto nas telas após a mudança de apresentação/gravação; são dados de teste a serem descartados, e não devem receber migração automática.
- **Dúvida de semântica**: se durante a implementação um campo não for claramente classificável como timestamp ou data de negócio, aquele ponto deve ser interrompido e a dúvida registrada, não assumida.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE gerar todo timestamp persistido que represente "o agora" a partir de um mecanismo centralizado único, que produza o instante atual em UTC.
- **FR-002**: O sistema DEVE evitar que novos códigos criem timestamps persistidos por meio de relógios locais espalhados (o gerador central é o caminho estabelecido para todo service que gravar "agora").
- **FR-003**: O sistema DEVE fornecer um mecanismo centralizado para converter timestamps persistidos como UTC para America/Recife na apresentação, reutilizável por templates, relatórios e demais saídas que exibam timestamps.
- **FR-004**: A conversão central DEVE aceitar o formato de valor atualmente armazenado (instante sem indicação de fuso que semanticamente representa UTC) e DEVE tratar valor ausente sem erro, retornando apresentação vazia/condicional como hoje.
- **FR-005**: O mecanismo de apresentação DEVE definir claramente que seus valores de entrada representam timestamps persistidos em UTC e DEVE ser aplicado uma única vez em cada fluxo de apresentação. O código não deve converter novamente um valor que já tenha sido convertido para America/Recife. NÃO DEVE usar deslocamento fixo de horas.
- **FR-006**: Todas as telas que exibem timestamps armazenados em UTC (auditoria; inventário: criação, início, conferência/re-conferência, encerramento; usuários: último acesso, bloqueio temporário, última sincronização AD; manutenções) DEVEM exibir o horário convertido para America/Recife, sem lógica de fuso duplicada em cada tela.
- **FR-007**: Os timestamps gerados pelo sistema nos fluxos de movimentação (todos os tipos) DEVEM ser gravados representando UTC, incluindo o carimbo de atualização do bem quando alterado por movimentação.
- **FR-008**: Na importação, os timestamps gerados pelo sistema DEVEM ser gravados em UTC; as datas provenientes do arquivo DEVEM continuar sendo tratadas como datas de negócio, sem conversão de fuso, e o formato de entrada não deve ser alterado.
- **FR-009**: Os relatórios e exportações (PDF, Excel, CSV, páginas HTML de relatório) DEVEM apresentar em America/Recife os horários de dados armazenados em UTC (inventário, auditoria, movimentações), mantendo o carimbo "Gerado em" em horário local.
- **FR-010**: Os filtros de período informados pelo usuário em data/hora local DEVEM ser convertidos de America/Recife para UTC antes da comparação com timestamps armazenados em UTC; os filtros que comparam apenas datas de negócio DEVEM preservar o comportamento atual.
- **FR-011**: O sistema NÃO DEVE alterar tipos/estrutura das colunas de data existentes nem introduzir mecanismo de fuso no banco; a convenção UTC é mantida pela aplicação.
- **FR-012**: O sistema NÃO DEVE migrar nem converter registros históricos existentes (dados atuais são de teste e serão descartados); apenas registros criados após a feature seguem o padrão. Se for descoberta base de produção não descartável, a implementação DEVE parar e registrar o risco, sem conversão automática.
- **FR-013**: A lógica funcional de autenticação, bloqueio de usuários, sessões e integração AD (que já opera em UTC) NÃO DEVE ser alterada; quando um timestamp desses for exibido ao usuário, aplica-se apenas a conversão de apresentação.
- **FR-014**: Campos de data de negócio (data de compra, fim de garantia e equivalentes) NÃO DEVEM receber conversão UTC→Recife; sua semântica atual deve ser preservada campo a campo.
- **FR-015**: Testes DEVEAM cobrir: conversão UTC→Recife, virada de dia (UTC que corresponde ao dia anterior em Recife), preservação de segundos, tratamento de valor ausente, ausência de dupla conversão, apresentação de Inventário e Auditoria, gravação em UTC nas Movimentações/Importação e conversão local→UTC nos filtros de período.
- **FR-016**: Testes existentes que validam comportamento legítimo DEVEM ser preservados; somente testes diretamente dependentes do padrão antigo de horário local podem ser atualizados como consequência direta desta convenção, sem enfraquecer coberturas.
- **FR-017**: Todo componente de data/hora modificado DEVE ser classificado explicitamente como "timestamp" (instante) ou "data de negócio" (data pura); componentes de autenticação/sessões/AD não têm seu comportamento alterado, apenas a apresentação quando exibida.

### Classification of system date/time fields (Key Entities)

**Timestamps (instante; regem a convenção UTC + apresentação em Recife)**: `audit_log.timestamp`; `Inventario.created_at`, `started_at`, `closed_at`; `InventarioItem.created_at`, `checked_at`; `Movement.timestamp`, `Movement.created_at`; `Asset.created_at`, `updated_at`; `Maintenance.start_date`, `end_date`, `created_at`; `User.created_at`, `last_login`, `locked_until`, `ad_last_sync`; `UserSession.created_at`, `expires_at`; `Role.created_at`, `Permission.created_at`, `Location.created_at`, `Custodian.created_at`, `ADGroupRole.created_at`, `ADSettings.updated_at`, `SetupClaim.claimed_at`.

**Datas de negócio (preservadas, sem conversão)**: `Asset.purchase_date`, `Asset.warranty_expiry`, datas interpretadas de arquivos de importação, datas digitadas em formulários/filtros que representam apenas data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das telas listadas em FR-006 exibem o horário de America/Recife correto: um evento ocorrido às 19:30 locais aparece como 19:30 (hoje aparece 22:30) — verificado por inspeção em cada tela.
- **SC-002**: 100% dos novos registros de timestamp gerados pelo sistema, em todos os módulos, representam UTC — verificado comparando o valor gravado com o instante UTC do momento da ação (tolerância de segundos de execução).
- **SC-003**: Dentro de uma mesma linha/entidade não existe mais divergência de padrão: os carimbos da movimentação e do bem alterado representam o mesmo instante de referência (UTC), eliminando a divergência atual de 3h entre colunas da mesma tabela.
- **SC-004**: 100% das datas de negócio informadas (cadastro e importação) permanecem idênticas no armazenamento e na exibição — zero casos de data deslocada por conversão indevida.
- **SC-005**: Consultas por período retornam exatamente os registros do intervalo local informado (precisão de minuto), sem inclusões/exclusões por deslocamento de fuso.
- **SC-006**: A suíte de testes existente permanece verde e os novos testes da convenção (conversão, virada de dia, segundos, valor ausente, dupla conversão, módulos) passam — cobrindo todos os cenários de FR-015.
- **SC-007**: Zero alterações estruturais no banco de dados e zero migrações de dados executadas como parte desta feature.
- **SC-008**: Nenhuma ocorrência de deslocamento fixo de "-3 horas" e nenhum caminho de dupla conversão no código entregue — verificado por revisão do diff e pelos testes específicos.

## Assumptions

- O ambiente atual é de desenvolvimento/teste e seus dados (~202 registros de movimentação em hora local e demais registros) são descartáveis; não há base de produção a preservar nesta feature (confirmado pelo requisito 9 da descrição).
- O fuso de apresentação é America/Recife (UTC-3, sem horário de verão vigente); a conversão usa o fuso nomeado com regras oficiais, o que absorve eventuais mudanças futuras de legislação.
- Os relatórios técnicos já produzidos (`docs/ANALISE_DATAS_HORARIOS.md`, `docs/ANALISE_TIMEZONE_INVENTARIO_AUDITORIA.md`) refletem fielmente o código atual e servem de mapa inicial; cada ponto deve ser re-verificado no código antes de alteração.
- A apresentação continua renderizada no servidor (sem conversão no navegador), como hoje — o navegador não participa da conversão.
- Formatos visuais de data/hora existentes (dd/mm/aaaa hh:mm e hh:mm:ss) são preservados; a feature muda o valor do fuso exibido, não o formato.
- Os códigos sequenciais por ano (`INV-YYYY`, `TR-YYYY`) e o cálculo de depreciação permanecem com a lógica atual (fora do escopo), mesmo que internamente usem relógios diferentes.
- Mudanças em arquivos ou componentes não previstos exigem justificativa explícita antes da alteração (regra "Importante" da descrição).
