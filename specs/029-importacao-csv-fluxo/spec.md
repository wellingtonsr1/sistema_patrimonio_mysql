# Feature Specification: Registrar no Fluxo as movimentações decorrentes da importação de equipamentos via CSV

**Feature Branch**: `029-importacao-csv-fluxo`

**Created**: 2026-09-21

**Status**: Draft

**Input**: Corrigir a integração entre a importação de equipamentos via CSV e o histórico de Fluxo/Movimentações patrimoniais do SisPatrimônio Pro: o CSV atualiza o estado do equipamento, mas não passa pela mesma lógica de movimentação/histórico patrimonial. A solução deve reutilizar integralmente a matriz de movimentações e a camada de serviço existentes, sem criar novos tipos de movimentação e sem duplicar regras de negócio.

---

## Análise do estado atual (fatos verificados no código, 2026-09-21)

Esta spec é de **correção em sistema existente**. A inconsistência foi localizada por leitura do código atual; a spec exige que o planejamento (`/speckit-plan`) e as tarefas (`/speckit-tasks`) partam destes fatos:

- **Importação não passa pelo motor de movimentações (causa estrutural)**: em `app/services/import_service.py`, `execute_import` cria o `Asset` **atribuindo `location_id` diretamente** no construtor e monta uma `Movement` de `ENTRADA_AQUISICAO` manualmente (via `db.add`), com snapshots fabricados: origem com `origin_location_name="Importação CSV"` e `origin_custodian_name="Sistema"`, termo fora do padrão do sistema (`TR-CSV-{ano}-{id}`) e campo `reason` com texto de linha do CSV. A movimentação gerada não representa uma alocação/cautela real e o estado de custódia nunca é derivado de uma operação de domínio.
- **O CSV de colaborador (custodiante) não é processado**: `COLUMN_ALIASES` de `import_service.py` não reconhece colunas de custodiante/colaborador. O arquivo real de carga `docs/doc_proviśorios/docs_para_testes/doc-final/equipamentos.csv` traz as colunas `Custodiante` (nome do colaborador) e `departamento`, que hoje são silenciosamente ignoradas. Consequentemente, um equipamento importado nunca fica vinculado a colaborador via CSV.
- **Reimportação não movimenta**: no ramo de atualização de equipamento existente (`skip_duplicates=False`), `execute_import` altera apenas campos cadastrais (nome, marca, modelo, série, nota, fornecedor, valor, data, condição, notas) e **nunca** localização/custódia — nem o estado (`Asset.location_id`), nem o histórico (`Movement`).
- **Fluxo lê de fonte única real**: `MovementService.get_timeline_for_asset` (usado pela tela de detalhe do bem e por `/api/v1/assets/{id}/timeline`) combina `Movement` + eventos de `AuditLog` (descartando `CRIACAO`, `MOVIMENTACAO` e `MANUTENCAO` para não duplicar o que já é movimentação). Logo, para aparecer no Fluxo o registro precisa existir na tabela de movimentações — a auditoria da importação não substitui a movimentação.
- **A matriz de movimentação existe e é a fonte das regras**: `MovementService.create_movement` (`app/services/movement_service.py`) resolve deterministicamente origem/destino e valida (VAL-002 a VAL-008): nenhuma alteração efetiva → erro; alocação exige custodiante; mudança só de local com mesmo responsável → `TRANSFERENCIA_LOCAL`; entrega a novo colaborador → `ALOCACAO_CAUTELA` (com termo); devolução redundante ao estoque → erro. `create_movement` grava o `Movement` e faz `commit` atômico por movimentação; o `operator_name` é o `MovementCreate.operator_name` (nome de exibição do operador).
- **Auditoria da importação existe e é independente**: as rotas web (`/assets/import/confirm`) e API (`/api/v1/assets/import/csv`) já emitem `write_audit(ACTION_IMPORT, module="Patrimônio", resource="Asset")` com contagem de importados/ignorados/erros, após `execute_import`. Essa auditoria é conceito distinto da movimentação patrimonial e deve continuar existindo.
- **Restrição temporal**: `Movement.timestamp` é UTC (`now_utc`); exibição converte para local (`America/Recife`). `write_audit` também persiste UTC.
- **Banco**: produção MariaDB/MySQL; testes em SQLite em memória (`db_session`); migrações aditivas via `init_db` + `_ensure_schema_migrations`. Nenhuma alteração de schema é necessária para esta correção.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Equipamento importado com colaborador e localização aparece corretamente no Fluxo (Priority: P1)

Um operador autenticado importa um CSV de equipamentos em que uma linha informa o colaborador responsável e a localização física. O equipamento é criado, fica vinculado ao colaborador e à localização informados, e o Fluxo do equipamento passa a registrar a atribuição com um **tipo de movimentação já existente**, emitida pelo mesmo serviço que processa as movimentações manuais — permitindo reconstruir que o bem chegou ao sistema já atribuído àquele colaborador/local, com o nome do operador que executou a importação e data/hora.

**Why this priority**: é a inconsistência central do problema — estado atual correto, histórico patrimonial ausente/incoerente. Sem ela, o Fluxo não é confiável para bens carregados em massa.

**Independent Test**: pode ser testado executando a importação de uma linha com colaborador + localização e consultando o Fluxo do equipamento criado — entrega valor mesmo sem os demais cenários.

**Acceptance Scenarios**:

1. **Given** um CSV com linha informando equipamento, colaborador cadastrado e localização cadastrada, **When** a importação é confirmada por um usuário autenticado, **Then** o equipamento é criado com status "Em Uso", vinculado ao colaborador e à localização informados.
2. **Given** o mesmo cenário, **When** o Fluxo do equipamento é consultado, **Then** existe uma movimentação correspondente à atribuição, com tipo `ALOCACAO_CAUTELA` (entrega a colaborador), origem representando a entrada do bem (estoque/entrada inicial) e destino apontando o colaborador e a localização informados.
3. **Given** o mesmo cenário, **When** os detalhes da movimentação são inspecionados, **Then** o campo de operador contém o nome de exibição do usuário autenticado que executou a importação (não "Sistema", não "Importação CSV" como operador, não o colaborador do CSV).
4. **Given** o mesmo cenário, **When** o Fluxo é aberto, **Then** a movimentação exibe equipamento, tipo, colaborador de destino, localização de destino, operador e data/hora — sem implementação paralela do Fluxo nem leitura dos dados do CSV pela tela.
5. **Given** o mesmo cenário, **When** o termo de responsabilidade é gerado, **Then** o código do termo segue o padrão sequencial existente do sistema (não o padrão "TR-CSV" atual).

---

### User Story 2 — Importação sem colaborador ou sem localização não inventa dados nem movimentações falsas (Priority: P1)

Um operador importa um CSV em que algumas linhas têm apenas localização (sem colaborador), outras apenas colaborador (sem localização) e outras nenhum dos dois. Cada equipamento é criado exatamente com os dados importados: nenhum colaborador é inventado, nenhuma localização é inventada, nenhuma alocação/transferência artificial é criada apenas para preencher a tela de Fluxo. A auditoria da importação continua sendo registrada normalmente.

**Why this priority**: protege a integridade patrimonial contra falsas alocações e falsas transferências — um fluxo falso é tão grave quanto um fluxo ausente.

**Independent Test**: pode ser testado importando linhas com ausências combinadas e verificando o estado do equipamento e a ausência de movimentações artificiais — independente da Story 1.

**Acceptance Scenarios**:

1. **Given** uma linha de CSV sem colaborador e sem localização, **When** a importação é executada, **Then** o equipamento é criado disponível, sem custodiante e sem localização, e nenhuma movimentação de alocação/transferência é criada para além da entrada registrada pelo próprio cadastro do bem.
2. **Given** uma linha com localização informada e válida, mas sem colaborador, **When** a importação é executada, **Then** o equipamento fica com a localização informada, sem custodiante; a representação histórica dessa situação não fabrica alocação a colaborador (sem `ALOCACAO_CAUTELA` com custodiante inventado); a localização efetiva é registrada pela operação de domínio que cria o bem (entrada/aquisição já existente) ou pela regra de movimentação aplicável, sem criar tipo novo.
3. **Given** uma linha com colaborador informado e cadastrado, mas sem localização, **When** a importação é executada, **Then** o equipamento fica vinculado ao colaborador, e a alocação correspondente aparece no Fluxo usando o tipo de movimentação e as validações já existentes (o bem sem localização anterior aloca sem exigir local de destino, conforme as regras atuais da matriz).
4. **Given** uma linha com localização que não existe no cadastro de locais, **When** a importação é executada, **Then** o comportamento atual de rejeitar a linha com erro (sem cadastrar o bem) é preservado, e a mensagem indica o local não encontrado.
5. **Given** qualquer linha importada com ou sem movimentação, **When** a operação termina, **Then** a auditoria da importação (`ACTION_IMPORT`) continua registrada com usuário autenticado, contagem de importados/ignorados/erros.

---

### User Story 3 — Reimportação idêntica não duplica movimentações (Priority: P1)

Um operador reimporta o mesmo CSV (ou linha) com exatamente o mesmo colaborador e a mesma localização. O sistema reconhece que não houve alteração efetiva de custódia/localização, não cria movimentação nova e preserva o histórico anterior intacto — sem erro indevido ao operador.

**Why this priority**: reimportação é operação normal de carga; duplicar histórico a cada reprocessamento corromperia a trilha patrimonial e destruiria a confiança no Fluxo.

**Independent Test**: pode ser testado importando a mesma linha duas vezes e contando as movimentações do equipamento — independente das demais stories.

**Acceptance Scenarios**:

1. **Given** um equipamento já importado com colaborador + localização, **When** a mesma linha é reimportada com os mesmos valores, **Then** nenhuma movimentação nova de alocação/transferência é criada.
2. **Given** a mesma reimportação, **When** o histórico anterior é consultado, **Then** permanece exatamente como estava (nada apagado, nada sobrescrito).
3. **Given** a mesma reimportação, **When** o resultado é exibido, **Then** a linha é tratada como processada/sem alteração (importada, ignorada ou reportada como sem alteração), sem crash e sem dupla contagem na auditoria da operação.

---

### User Story 4 — Reimportação com mudança real de colaborador/localização gera o histórico correto (Priority: P2)

Um operador reimporta um CSV em que um equipamento existente agora aparece com colaborador diferente, com localização diferente, ou ambos. O equipamento passa ao novo estado, e a alteração gera uma movimentação nova no Fluxo usando a matriz existente (entrega a novo colaborador → `ALOCACAO_CAUTELA`; só local com mesmo responsável → `TRANSFERENCIA_LOCAL`; local + custodiante novos → regra existente para entrega com termo), preservando todas as movimentações anteriores.

**Why this priority**: complementa o ciclo de vida; é o comportamento de movimentação comum aplicado à importação, com menor risco depois das P1.

**Independent Test**: pode ser testado importando uma linha, depois a mesma tombamento com outro colaborador/local e conferindo a sequência do histórico — independente das stories 1–3.

**Acceptance Scenarios**:

1. **Given** um equipamento existente alocado ao colaborador A, **When** o CSV o traz alocado ao colaborador B, **Then** o equipamento passa para B e uma movimentação `ALOCACAO_CAUTELA` é criada (entrega a novo colaborador, com termo), preservando a movimentação anterior no histórico.
2. **Given** um equipamento existente alocado ao colaborador A no local X, **When** o CSV traz o mesmo colaborador A no local Y, **Then** a localização é atualizada para Y e uma movimentação `TRANSFERENCIA_LOCAL` é criada, preservando o histórico.
3. **Given** um equipamento existente, **When** o CSV traz colaborador e localização novos, **Then** a movimentação resultante segue a matriz atual para entrega a novo colaborador (ALOCAÇÃO com termo), sem duplicar a lógica da matriz no importador.
4. **Given** qualquer mudança real, **When** a movimentação é criada, **Then** o operador registrado é o usuário autenticado que executou a reimportação.

---

### User Story 5 — Consistência transacional entre cadastro e histórico (Priority: P2)

Um operador importa um lote em que uma linha falha ao criar a movimentação correspondente. O sistema não deixa estado parcial: o equipamento da linha falha não permanece alocado sem movimentação (nem movimentação sem alocação); a linha é reportada como erro na importação e as demais linhas seguem o comportamento atual do lote.

**Why this priority**: evita divergência estrutural futura entre estado e histórico — a mesma classe de bug que esta feature corrige.

**Independent Test**: pode ser testado forçando falha na criação da movimentação e verificando que o equipamento não fica em estado inconsistente — independente das demais stories.

**Acceptance Scenarios**:

1. **Given** uma linha cuja criação de movimentação falha (ex.: validação da matriz), **When** a importação processa a linha, **Then** o equipamento não permanece com custódia/local alterados sem a movimentação correspondente (rollback da unidade da linha).
2. **Given** a falha da linha, **When** o resultado da importação é exibido, **Then** a linha aparece nos erros com mensagem clara, e as demais linhas do lote são processadas conforme o comportamento atual.
3. **Given** uma linha válida processada com sucesso, **When** o estado e o histórico são comparados, **Then** são derivados da mesma operação de domínio (cadastro/alteração e movimentação coerentes entre si).

---

### Edge Cases

- **Colaborador inexistente no cadastro (nome não encontrado / coluna vazia com espaços)**: não inventar colaborador. Se o CSV informar um nome e ele não corresponder a colaborador cadastrado, a linha deve ser reportada como erro (análogo ao tratamento atual de local inexistente), sem criar colaborador implicitamente e sem alocar a quem não existe. Nome vazio/branco trata-se como ausência de colaborador (cenário da Story 2).
- **CSV do mundo real**: colunas com acentos/caixa variável (`Custodiante`, `Número de série`, `departamento`, `Tipo`) continuam sendo reconhecidas pelos aliases existentes; a nova coluna de custodiante segue o mesmo mecanismo de aliases já usado pelo parser.
- **Equipamento em estoque/disponível**: linha sem colaborador importa como disponível (estoque), sem falsa alocação e sem devolução ao estoque artificial.
- **Bem baixado/descartado**: o CSV de equipamentos não reanima bem baixado; a regra existente do motor (não movimentar bem baixado, salvo entrada) permanece válida e erros resultantes são reportados na linha.
- **Duplicidade de tombamento dentro do mesmo CSV**: comportamento atual (segunda ocorrência tratada como duplicata conforme `skip_duplicates`) é preservado.
- **Falha de commit do lote**: preservar o comportamento atual de capturar erro de commit e reportá-lo no resultado da importação.
- **Fuso horário**: `timestamp` das movimentações continua em UTC conforme padrão da aplicação; exibição no Fluxo continua convertendo para horário local.

## Requirements *(mandatory)*

### Importação e Fluxo

- **FR-001**: A importação CSV de equipamentos MUST processar a coluna de colaborador/custodiante (com reconhecimento pelos aliases de coluna já existentes do parser, ex.: "custodiante", "colaborador"), resolvendo o colaborador pelo cadastro existente (nome), sem criar colaboradores.
- **FR-002**: Quando colaborador e/ou localização forem informados e resolvidos, o estado do equipamento (custodiante, localização, status) e o histórico patrimonial MUST ser derivados da **mesma operação de domínio**, por meio do serviço de movimentação existente (`MovementService`) — a importação MUST NOT atribuir custodiante/localização por caminho que contorne o motor de movimentações quando houver movimentação real.
- **FR-003**: A importação MUST NOT criar novos tipos de movimentação; MUST utilizar exclusivamente os tipos existentes (`ENTRADA_AQUISICAO`, `ALOCACAO_CAUTELA`, `TRANSFERENCIA_LOCAL`, `DEVOLUCAO_ESTOQUE`, etc.) e a matriz de regras já implementada em `MovementService.create_movement`.
- **FR-004**: A lógica de decisão de qual movimentação aplicar (diferença de local/custodiante, tipos, validações VAL-002..VAL-008) MUST permanecer centralizada no serviço de movimentação; o importador CSV MUST NOT reimplementar ou duplicar a matriz.
- **FR-005**: A movimentação gerada pela importação MUST registrar como operador o usuário autenticado que executou a importação (nome de exibição do usuário logado, obtido das rotas web/API que já dispõem de `request.state.user`); é proibido usar usuário fictício, "Sistema" como operador da movimentação ou o colaborador do CSV como autor.
- **FR-006**: A movimentação gerada MUST persistir de forma real na tabela de movimentações existente, com origem → destino, motivo, operador e data/hora em UTC conforme padrão temporal da aplicação — de modo que seja recuperada pela consulta atual utilizada pelo Fluxo (`get_timeline_for_asset`), sem implementação paralela do Fluxo e sem o Fluxo ler dados do CSV.
- **FR-007**: O termo de responsabilidade gerado por alocação via importação MUST seguir o padrão sequencial existente do sistema, eliminando o código atual "TR-CSV-{ano}-{id}".
- **FR-008**: A movimentação de entrada do bem importado MUST representar a origem real do processo (entrada inicial/estoque), sem snapshots fabricados como operador "Sistema"/"Importação CSV" que caracterizem falsa atribuição de custódia ou operação.

### Sem inventar dados

- **FR-009**: Linha sem colaborador e sem localização MUST criar o equipamento conforme os dados importados (disponível, sem custodiante, sem localização) e MUST NOT criar movimentação artificial de alocação/transferência.
- **FR-010**: Linha somente com localização MUST registrar a localização atual do equipamento sem atribuir custodiante e sem fabricar alocação a colaborador; quando não houver operação de movimentação aplicável para a alteração de localização sem colaborador, o estado MUST ser preservado pelo cadastro (entrada/aquisição existente) sem inventar tipo de movimentação.
- **FR-011**: Linha somente com colaborador MUST alocar o equipamento usando a regra existente de alocação/cautela, respeitando as validações atuais da matriz (inclusive a exigência ou não de local de destino conforme o estado anterior do bem).
- **FR-012**: Colaborador informado e não encontrado no cadastro MUST resultar em erro reportado na linha (padrão análogo ao local inexistente), sem inventar colaborador e sem cadastrar o bem da linha.
- **FR-013**: Linha com localização inexistente MUST preservar o comportamento atual: erro na linha, sem cadastrar o bem.

### Reimportação e histórico

- **FR-014**: A especificação MUST distinguir criação de equipamento novo, atualização de equipamento existente e reimportação idêntica; os três caminhos conservam o mesmo comportamento de histórico descrito nestes requisitos.
- **FR-015**: Reimportação sem alteração efetiva de colaborador/localização MUST NOT criar movimentação nova; o histórico anterior MUST permanecer intacto (nada apagado ou sobrescrito).
- **FR-016**: Reimportação com mudança real de colaborador/localização MUST aplicar as regras normais de movimentação existentes (matriz) para produzir o novo registro histórico, preservando o histórico anterior.
- **FR-017**: Nenhuma movimentação histórica MAY ser apagada, editada ou sobrescrita pela importação.

### Auditoria e consistência

- **FR-018**: A auditoria da importação (`ACTION_IMPORT` via trilha existente) MUST continuar registrada nas rotas web e API, independente da movimentação patrimonial: auditoria não substitui movimentação e movimentação não substitui auditoria; quando ambos forem aplicáveis, ambos MUST existir.
- **FR-019**: Quando houver movimentação patrimonial necessária, a alteração do equipamento e a criação da movimentação MUST ser tratados de forma que não exista estado parcial (equipamento atribuído sem movimentação, ou movimentação sem estado correspondente), respeitando a arquitetura transacional atual (unidade da linha; erro na linha não deve deixar o bem da linha inconsistente).
- **FR-020**: Em caso de falha na criação da movimentação, a linha MUST ser reportada como erro no resultado da importação e o estado do bem da linha MUST permanecer consistente (sem alocação órfã).

### Preservação (não quebrar)

- **FR-021**: As funcionalidades existentes MUST permanecer inalteradas: importação de colaboradores, importação de locais, cadastro manual de equipamentos (incluindo alocação inicial e movimentação de entrada), movimentações manuais, manutenções, Fluxo existente, auditoria, permissões/RBAC/autenticação, inventário e exportações CSV/Excel/PDF.
- **FR-022**: A mudança MUST ser mínima e localizada, restrita aos arquivos responsáveis pela importação de equipamentos e pelo fluxo de chamada de movimentação; nenhuma refatoração fora do escopo.
- **FR-023**: Nenhuma alteração de banco de dados é esperada; se o planejamento concluir necessidade, MUST ser alteração aditiva idempotente compatível com MariaDB/MySQL e com o mecanismo atual de migrações, com motivo documentado. SQLite permanece restrito à suíte de testes.
- **FR-024**: Nenhuma credencial ou segredo MAY ser registrado em logs, auditoria ou movimentações como consequência desta correção.

### Key Entities

- **Equipamento/Asset** (existente): bem patrimonial com tombamento único, estado atual (status, condição, localização, custodiante) e movimentações associadas.
- **Movimentação/Movement** (existente): registro imutável do fluxo patrimonial do bem — tipo, timestamp UTC, snapshots de origem/destino (local e custodiante, id + nome), transição de status/condição, motivo, operador, termo. Fonte única do Fluxo.
- **Colaborador/Custodian** (existente): responsável/custodiante identificado por nome e matrícula; alvo da resolução da coluna do CSV.
- **Localização/Location** (existente): local físico já cadastrado, resolvido por nome (comportamento atual mantido).
- **Matriz de Movimentação** (existente, em `MovementService`): conjunto de regras/validações que determina o tipo de movimentação a partir das diferenças de local e custodiante (mesmo local + mesmo custodiante → nada; mesmo local + custodiante diferente → alocação/cautela; local diferente + mesmo custodiante → transferência de local; local diferente + custodiante diferente → entrega/cautela com termo; estoque → colaborador → alocação).
- **Operação de importação (auditoria)** (existente): registro `ACTION_IMPORT` na trilha de auditoria, distinto da movimentação patrimonial.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos equipamentos importados com colaborador e localização informados apresentam (a) cadastro atual correto e (b) movimentação correspondente no Fluxo, com tipo já existente, colaborador/local de destino, operador igual ao usuário autenticado da importação e data/hora (verificável pelos cenários da Story 1 e teste L).
- **SC-002**: 0 movimentações artificiais/duplicadas criadas nas importações sem mudança efetiva: linhas sem colaborador/local e reimportações idênticas não alteram o histórico (verificável pelas stories 2 e 3).
- **SC-003**: Reimportações com mudança real de colaborador/localização geram exatamente 1 movimentação nova por mudança, com tipo determinado pela matriz existente, preservando 100% do histórico anterior (story 4).
- **SC-004**: A movimentação persistida pela importação é recuperada pela consulta atual do Fluxo sem nenhum código novo na tela/consulta do Fluxo (teste de serviço/integração, teste L).
- **SC-005**: Falha na criação de movimentação não deixa equipamento em estado parcial: a linha é reportada como erro e o bem permanece consistente (story 5).
- **SC-006**: A suíte de testes existente completa permanece verde; novos testes cobrem os cenários A–L definidos na estratégia de testes.
- **SC-007**: Nenhuma alteração fora do escopo: importação de colaboradores/locais, cadastro manual, movimentações manuais, Fluxo, auditoria, RBAC e exportações permanecem intocados (exceto a passagem do operador já disponível nas rotas).

## Assumptions

- O usuário autenticado que executa a importação está disponível nas rotas web e API atuais (`request.state.user`) e pode ser repassado à camada de importação como dado do contexto da operação (nome de exibição, conforme padrão já usado em `operator_name` nas movimentações manuais).
- O CSV real de carga (`docs/doc_proviśorios/docs_para_testes/doc-final/equipamentos.csv`) traz a coluna `Custodiante` com o **nome** do colaborador; a resolução é pelo cadastro existente de colaboradores. Colaboradores ausentes no cadastro geram erro de linha (não criação implícita).
- "Equipamento em estoque" corresponde ao estado atual do sistema: disponível (`AVAILABLE`), sem custodiante, com ou sem localização — a representação de estoque já existente não é alterada.
- A movimentação de entrada do bem importado (quando criada) permanece do tipo entrada/aquisição existente; o que esta feature corrige é a representação correta de origem/operador/termo e a geração da movimentação de custódia (alocação/transferência) quando aplicável.
- A coluna "departamento" do CSV de carga não é tratada como localização nesta feature (a localização continua resolvida pelas colunas de localização já suportadas); eventuais novas colunas suportadas ficam fora do escopo.
- Nenhuma alteração de schema de banco é necessária: os campos de snapshot da movimentação (origem/destino, custodiante, local, operador) já suportam o histórico descrito.
- A suíte de testes atual cobre importação de localização (`tests/test_import_asset_location.py`) e movimentações (`tests/test_movements.py`, `tests/test_api.py`); os novos testes seguirão os mesmos padrões (fixtures `db_session`, TestClient).

## Estratégia de Testes (cenários obrigatórios)

Os testes automatizados devem cobrir, no mínimo (serviço/integração, seguindo os padrões existentes da suíte):

- **A. Novo equipamento importado com colaborador + localização**: equipamento criado; colaborador associado; localização associada; movimentação criada com tipo já existente (alocação/cautela); operador = usuário autenticado; movimentação recuperável pelo Fluxo (timeline).
- **B. Novo equipamento sem colaborador**: nenhum colaborador inventado; nenhuma falsa alocação; comportamento da localização conforme regra definida (FR-010).
- **C. Novo equipamento sem localização**: nenhuma localização inventada; nenhuma falsa transferência; alocação por colaborador quando informado segue a matriz.
- **D. Novo equipamento sem colaborador e sem localização**: nenhuma movimentação artificial; auditoria da importação continua funcionando.
- **E. Reimportação sem alteração**: nenhuma movimentação duplicada; histórico anterior intacto.
- **F. Reimportação com mudança de colaborador**: equipamento passa ao novo colaborador; movimentação correta criada; movimentação anterior permanece; sem duplicação indevida.
- **G. Reimportação com mudança de localização**: localização atualizada; movimentação correspondente criada; histórico anterior permanece.
- **H. Mudança de colaborador e localização simultânea**: aplicação correta da matriz existente (entrega/cautela com termo).
- **I. Equipamento em estoque**: importado como disponível, sem colaborador indevido.
- **J. Usuário autenticado**: a movimentação utiliza como operador o usuário que realizou a importação (não "Sistema", não o colaborador do CSV).
- **K. Falha transacional**: simulada falha na criação da movimentação; equipamento não fica parcialmente atualizado; linha reportada como erro.
- **L. Fluxo**: a movimentação persistida pela importação é recuperada pela consulta utilizada pelo Fluxo (`get_timeline_for_asset` / timeline da API), sem alteração na consulta.

## Casos de erro

- **Colaborador informado não cadastrado**: erro na linha ("colaborador 'X' não encontrado no cadastro de colaboradores"), bem não cadastrado, sem movimentação.
- **Localização informada não cadastrada**: erro na linha (comportamento atual preservado), bem não cadastrado.
- **Reimportação sem alteração efetiva**: linha processada sem nova movimentação; reportada como processada/sem alteração (não deve aparecer como erro falso ao operador quando a importação é válida; erros de validação da matriz, quando ocorrerem por dado inconsistente, são reportados na linha).
- **Bem baixado/descartado em reimportação**: erro de linha reportado conforme a regra do motor de movimentações; sem reativação implícita.
- **Falha transacional na movimentação**: linha reportada como erro; sem estado parcial; demais linhas seguem o comportamento atual do lote.
- **Commit do lote falha**: comportamento atual preservado (erro reportado no resultado da importação).

## Riscos

- **Regressão em importações existentes**: a alteração do `execute_import` pode afetar os testes atuais de localização e os fluxos web/API de importação; mitigado por manter os contratos atuais (`parse_csv`, `preview_import`, `execute_import`, contagens do resultado, mensagens de erro) e pela suíte existente.
- **Duplicação acidental da matriz no importador**: risco central de design; mitigado pelo requisito FR-004 e pela revisão de conformidade da Constitution (Princípios III e IV).
- **Inconsistência transacional parcial no lote**: a unidade transacional por linha deve ser definida no planejamento respeitando o comportamento atual por linha (linhas falhas reportadas, lote segue); risco mitigado pelos testes K e D.
- **Colaborador com nome duplicado no cadastro**: a resolução por nome pode ser ambígua; o planejamento deve definir critério determinístico (ex.: erro de linha pedindo desambiguação, ou primeira correspondência documentada) sem inventar dados.
- **Volume de lote**: importações grandes geram mais movimentações do que hoje (uma por atribuição); custo aceitável e sem alteração de schema; nenhuma otimização fora do escopo.
- **Termo de responsabilidade em massa**: alocações via CSV geram códigos de termo sequenciais; a numeração deve permanecer consistente com o contador existente de termos.

## Critérios de aceite (consolidados)

1. Equipamento importado com colaborador e localização apresenta essas informações no cadastro atual **e** o histórico patrimonial correspondente.
2. A movimentação criada pela importação aparece no Fluxo do equipamento (fonte de dados atual, sem implementação paralela).
3. O histórico permite identificar: equipamento; tipo de movimentação; colaborador envolvido (quando aplicável); localização envolvida (quando aplicável); usuário que realizou a operação; data/hora.
4. Nenhum novo tipo de movimentação é criado.
5. A matriz de movimentações existente continua sendo a única fonte das regras.
6. Reimportações idênticas não geram movimentações duplicadas.
7. Alterações reais de colaborador/localização geram o histórico correspondente.
8. A auditoria da importação continua funcionando independentemente da movimentação patrimonial.
9. O histórico anterior nunca é apagado ou sobrescrito.
10. A implementação utiliza os serviços/camadas de domínio existentes.
11. Não há lógica duplicada da matriz de movimentação dentro do importador CSV.
12. Todos os testes existentes continuam passando.
13. Testes específicos dos cenários A–L são adicionados.
14. Funcionalidades não relacionadas não são alteradas.

## Lista explícita do que NÃO deve ser alterado

- Importação de colaboradores (`custodian_import_service`) e importação de locais (`location_import_service`) — inclusive seus parsers e rotas.
- Cadastro manual de equipamentos (`AssetService.create/update`) e seus registros de entrada.
- Movimentações manuais (tela/API de Fluxo) e `MovementService.create_movement` como contrato de regras — apenas reutilizado, não alterado em sua semântica.
- A consulta do Fluxo (`get_timeline_for_asset`) e as telas/API do Fluxo (nenhuma mudança de fonte de dados).
- Trilha de auditoria (`audit_service`) e os eventos `ACTION_IMPORT` existentes nas rotas de importação.
- Permissões, RBAC, autenticação e sessões.
- Inventário (`inventario_service`) — incluindo o princípio de que o inventário nunca altera o cadastro.
- Exportações CSV/Excel/PDF e relatórios.
- Banco de dados (schema, tipos, tabelas) — nenhuma alteração é esperada; migrações aditivas somente se comprovadamente necessárias (FR-023).
- Parser do CSV de equipamentos nos demais aspectos: aliases existentes, detecção de delimitador, validações de campos obrigatórios e normalizações atuais (exceto o acréscimo do reconhecimento da coluna de custodiante, FR-001).
- Estratégia de banco de produção (MariaDB/MySQL); nenhuma reintrodução de SQLite fora dos testes.
