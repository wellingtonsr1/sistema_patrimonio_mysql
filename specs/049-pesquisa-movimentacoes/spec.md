# Feature Specification: Adicionar Campo de Pesquisa no Fluxo Global de Movimentações

**Feature Branch**: `049-pesquisa-movimentacoes`  
**Created**: 2026-09-27  
**Status**: Draft  

**Input**: Adicionar um campo de pesquisa na página "Fluxo Global de Movimentações", integrado aos filtros existentes, permitindo localizar rapidamente movimentações existentes por tombamento, equipamento, colaborador, matrícula, local de origem/destino, tipo, operador ou termo, com correspondência parcial, sem diferenciar maiúsculas/minúsculas, respeitando paginação/limites e permissões RBAC, com alteração mínima e cirúrgica sem modificar regras de movimentação.

---

## 1. Contexto do Sistema Existente (Fatos verificados no código)

Esta especificação é aditiva e cirúrgica sobre a arquitetura existente do SisPatrimônio Pro. O levantamento prévio no código identificou os seguintes componentes:

| # | Item verificado | Onde está no código | Implicação para a especificação |
|---|---|---|---|
| F1 | **Rota responsável** | `app/web/routes.py` (`list_movements_view`, rota `GET /movements`) | A rota já recebe `movement_type` e `asset_id`; deve receber o parâmetro `search` via query string mantendo a guarda RBAC `movimentacao.visualizar`. |
| F2 | **Template de visualização** | `app/web/templates/movements/list.html` | A tela já possui um card de filtros com `<form method="get" action="/movements">`, dropdown de `movement_type` e botões "Filtrar" e "Limpar". O campo de pesquisa deve ser integrado organicamente a este formulário existente. |
| F3 | **Serviço de consulta** | `app/services/movement_service.py` (`MovementService.get_all_movements`) | O método centraliza a query de listagem recebendo `filters: Optional[MovementFilter]` e limites. A pesquisa deve ser aplicada na query do backend, evitando carregamento indiscriminado no navegador. |
| F4 | **Filtros estruturados** | `app/schemas/movement.py` (`MovementFilter`) | O schema Pydantic já define os filtros de movimentação. Pode ser estendido com o campo opcional `search: Optional[str] = None` sem quebrar compatibilidade. |
| F5 | **Modelos e relacionamentos** | `Movement` (`app/models/movement.py`), `Asset` (`app/models/asset.py`), `Custodian` (`app/models/custodian.py`), `Location` (`app/models/location.py`) | A tabela `movements` possui campos diretos (`reason`, `operator_name`, `term_code`, `movement_type`), colunas de snapshot (`origin_location_name`, `destination_location_name`, `origin_custodian_name`, `destination_custodian_name`) e relacionamentos carregados (`asset`, `origin_custodian`, `destination_custodian`, `origin_location`, `destination_location`). A pesquisa textual atua sobre essas entidades e dados já existentes. |
| F6 | **Padrão de busca do sistema** | `assets/list.html`, `custodians/list.html`, `locations/list.html`, `admin/audit/list.html` | O sistema adota o padrão visual com `input-group`, ícone Bootstrap `<i class="bi bi-search"></i>`, campo de texto `name="search"`, placeholder orientativo, botão de filtrar e link/botão "Limpar" que restaura a listagem. |
| F7 | **Paginação / Limite** | `MovementService.get_all_movements` com `limit=200` | A query aplica filtragem e ordenação decrescente por data (`timestamp`) antes de fatiar o resultado, retornando a lista e o total real encontrado. |
| F8 | **Regras de movimentação intocadas** | `MovementService.create_movement`, tipos de movimentação, transições e auditoria | Nenhuma regra de negócio de criação, alteração ou validação de movimentação é tocada. A funcionalidade é estritamente de consulta/filtragem. |

---

## 2. User Scenarios & Testing *(mandatory)*

### User Story 1 - Localizar movimentações por texto simples e parcial (Priority: P1) 🎯

Como operador ou gestor patrimonial que visualiza o histórico de movimentações, desejo digitar um termo no campo de pesquisa (número do tombamento, nome do equipamento, nome ou matrícula do colaborador, local de origem ou destino, tipo de movimentação, operador ou número do termo) para localizar rapidamente as movimentações correspondentes, sem precisar navegar manualmente por várias páginas de registros.

**Why this priority**: É o objetivo primário da funcionalidade. Elimina a busca visual exaustiva e traz agilidade imediata à auditoria e acompanhamento de bens.

**Independent Test**: Pode ser testado de forma independente acessando `/movements?search=termo` com termos correspondentes a cada um dos campos suportados, verificando que apenas as movimentações compatíveis são retornadas.

**Acceptance Scenarios**:

1. **Given** movimentações registradas com equipamentos diversos, **When** o usuário pesquisa pelo número exato do tombamento (ex.: `12345`), **Then** o sistema exibe apenas as movimentações referentes àquele tombamento.
2. **Given** movimentações envolvendo equipamentos como "Notebook Dell Latitude" e "Monitor Dell 24", **When** o usuário pesquisa por `Dell` ou `notebook`, **Then** todas as movimentações dos equipamentos compatíveis são listadas (correspondência parcial insensível a maiúsculas/minúsculas).
3. **Given** movimentações com colaboradores de origem ou destino "João Silva" e matrícula "MAT-1234", **When** o usuário pesquisa `joao` ou `MAT-1234`, **Then** as movimentações associadas a esse colaborador são retornadas.
4. **Given** movimentações envolvendo os locais "Almoxarifado Central" e "TI Suporte", **When** o usuário pesquisa `almoxarifado`, **Then** as movimentações onde a origem ou o destino contenha o termo são exibidas.
5. **Given** movimentações com operadores específicos (ex.: "Carlos Operador"), **When** o usuário pesquisa pelo nome do operador, **Then** as movimentações geradas por aquele operador são listadas.
6. **Given** movimentações que possuem código de termo (ex.: `TR-2026-00042`), **When** o usuário pesquisa `TR-2026`, **Then** os registros com termos correspondentes são retornados.

---

### User Story 2 - Integração da pesquisa com os filtros existentes e limpeza (Priority: P2)

Como usuário do sistema, desejo utilizar o campo de pesquisa em conjunto com o filtro de tipo de movimentação existente, e ser capaz de limpar a pesquisa a qualquer momento retornando ao estado padrão.

**Why this priority**: A pesquisa não deve anular ou sobrepor os critérios de filtragem já disponíveis na interface; filtros combinados são essenciais para refinar a busca operacional.

**Independent Test**: Selecionar um tipo de movimentação no dropdown (ex.: "Transferência") e simultaneamente informar um termo de busca (ex.: "Notebook"), verificando que a interseção dos critérios é apresentada. Em seguida, clicar em "Limpar" e verificar que a listagem é redefinida.

**Acceptance Scenarios**:

1. **Given** que existem movimentações de "Transferência" e "Alocação" para equipamentos "Notebook", **When** o usuário pesquisa `Notebook` e seleciona o tipo `Transferência`, **Then** o sistema exibe apenas as movimentações que atendem a ambos os critérios cumulativamente.
2. **Given** uma pesquisa aplicada na página, **When** o usuário aciona a ação "Limpar", **Then** o campo de pesquisa é esvaziado, a URL é limpa e a listagem exibe novamente os registros gerais do fluxo.
3. **Given** que o usuário envia o campo de pesquisa vazio ou contendo apenas espaços em branco, **When** o filtro é submetido, **Then** a pesquisa é tratada como inativa e os registros são exibidos normalmente respeitando eventuais filtros adicionais.

---

### User Story 3 - Feedback de estado vazio, responsividade e preservação de segurança (Priority: P3)

Como usuário, desejo visualizar uma mensagem clara e contextualizada quando nenhum registro atender aos critérios pesquisados, e ter a garantia de que a pesquisa funciona confortavelmente em qualquer dispositivo e não expõe dados além das minhas permissões.

**Why this priority**: Garante a consistência da experiência do usuário (UX), a integridade do controle de acesso (RBAC) e a adaptabilidade visual aos temas e tamanhos de tela da organização.

**Independent Test**: Realizar busca por termo inexistente e verificar mensagem na tela; testar redimensionamento responsivo de tela; verificar que usuários sem permissão `movimentacao.visualizar` continuam com acesso negado.

**Acceptance Scenarios**:

1. **Given** que o usuário pesquisa um termo inexistente (ex.: `TERMO_INEXISTENTE_999`), **When** a consulta é executada, **Then** o sistema apresenta a mensagem amigável: "Nenhuma movimentação encontrada para a pesquisa informada.", orientando o usuário a ajustar ou limpar os filtros.
2. **Given** um dispositivo móvel ou tablet, **When** a página do Fluxo Global é carregada, **Then** o campo de pesquisa e os filtros se acomodam sem quebra de layout, truncamentos indesejados ou overflow horizontal desalinhado.
3. **Given** um usuário sem a permissão `movimentacao.visualizar`, **When** ele tenta acessar a página ou a consulta de movimentações com parâmetro de pesquisa, **Then** a requisição é bloqueada conforme as regras vigentes do RBAC.

---

### Edge Cases

- **Termo com espaços no início ou fim**: Espaços em branco excedentes nas extremidades do termo devem ser desconsiderados (`strip()`), pesquisando apenas a parte significativa.
- **Caracteres especiais ou pontuação**: Caracteres comuns em identificadores (hifens em `MAT-1234` ou `TR-2026-0001`, barras, pontos) devem ser aceitos normalmente sem causar erros de consulta.
- **Movimentações sem colaboradores ou locais**: Registros de movimentações antigas ou com dados parciais legítimos (onde origem ou destino seja nulo) não devem quebrar a consulta ao aplicar os filtros textuais.
- **Volume expressivo de dados**: A consulta deve aplicar o filtro diretamente no banco de dados com limite de paginação preservado, impedindo a sobrecarga de memória do servidor ou do navegador.

---

## 3. Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST disponibilizar um campo de pesquisa textual na área de filtros da página "Fluxo Global de Movimentações" (`/movements`).
- **FR-002**: O campo de pesquisa MUST receber o valor via parâmetro HTTP GET (convenção `search`) para permitir atualização de página, navegação e compartilhamento de URL.
- **FR-003**: A pesquisa textual MUST operar sobre os seguintes dados existentes da movimentação:
  - Número de tombamento / Tag do bem (`Asset.tag`);
  - Nome / Descrição do equipamento (`Asset.name`);
  - Nome do colaborador/responsável de origem ou destino (`origin_custodian_name`, `destination_custodian_name` e nomes vinculados);
  - Matrícula do colaborador (`registration_code`);
  - Nome do local de origem ou destino (`origin_location_name`, `destination_location_name` e locais vinculados);
  - Descrição ou rótulo do tipo de movimentação (`movement_type`);
  - Nome do operador responsável pelo registro da movimentação (`operator_name`);
  - Código identificador do Termo de Responsabilidade (`term_code`).
- **FR-004**: A busca MUST realizar correspondência textual parcial (subconjunto de caracteres contido no valor).
- **FR-005**: A busca MUST ser insensível a maiúsculas e minúsculas (*case-insensitive*).
- **FR-006**: A busca MUST operar cumulativamente com o filtro de Tipo de Movimentação (`movement_type`) e qualquer outro filtro presente na requisição.
- **FR-007**: Quando o campo de pesquisa estiver vazio ou com apenas espaços, o filtro textual MUST ser desativado, retornando os registros regulares.
- **FR-008**: O sistema MUST fornecer um mecanismo direto para limpar a pesquisa e redefinir a listagem.
- **FR-009**: A filtragem MUST ocorrer no backend / banco de dados por meio da composição da query SQL, respeitando o limite de registros estabelecido (`limit=200`).
- **FR-010**: Quando a pesquisa não retornar nenhuma movimentação compatível, a interface MUST apresentar um estado vazio claro com a mensagem "Nenhuma movimentação encontrada para a pesquisa informada.", informando que os critérios podem ser ajustados.
- **FR-011**: O campo de pesquisa MUST adotar o padrão visual do SisPatrimônio Pro (ícone de busca, classes de formulário Bootstrap, suporte a tema claro e escuro).
- **FR-012**: O acesso à funcionalidade de pesquisa MUST ser restrito exclusivamente a usuários autenticados que possuam a permissão `movimentacao.visualizar`.
- **FR-013**: A funcionalidade de pesquisa MUST ser puramente de consulta, sendo ESTRITAMENTE PROIBIDO alterar qualquer regra de negócio de movimentação, criação, atualização, auditoria ou integridade cadastral.

---

### Key Entities

- **Movimentação (`Movement`)**: Registro histórico e imutável de fluxo de equipamentos. Contém referências para ativo, locais, custodiantes, tipo, justificativa, operador e código de termo.
- **Equipamento/Bem (`Asset`)**: Objeto patrimonial movimentado, identificado principalmente por `tag` (tombamento), `name` (descrição/nome), marca e modelo.
- **Colaborador/Custodiante (`Custodian`)**: Agente envolvido no fluxo como origem ou destino da custódia, identificado por `name` (nome) e `registration_code` (matrícula).
- **Localização (`Location`)**: Ponto geográfico ou setor envolvido no fluxo (origem ou destino), identificado por `name`.

---

## 4. Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário localiza uma movimentação específica por tombamento ou colaborador em menos de 5 segundos, sem necessidade de percorrer visualmente a tabela.
- **SC-002**: 100% das buscas combinadas (pesquisa textual + tipo de movimentação) retornam apenas os registros que satisfazem todos os filtros aplicados conjuntamente.
- **SC-003**: O tempo de resposta da listagem com filtro textual permanece inferior a 500ms em bases com até 10.000 movimentações.
- **SC-004**: Em caso de busca sem correspondências, 100% das ocorrências exibem mensagem de estado vazio compreensível, sem telas em branco, tabelas vazias silenciosas ou erros de sistema.
- **SC-005**: 100% dos testes existentes da suíte de movimentações e permissões continuam passando sem regressão.

---

## 5. Assumptions

- **Arquitetura de dados existente**: Os dados de movimentação já armazenam snapshots textuais dos nomes de locais e custodiantes (`origin_location_name`, `destination_location_name`, `origin_custodian_name`, `destination_custodian_name`), além das chaves estrangeiras com relacionamentos ativos. A busca textual pode examinar tanto os snapshots quanto as tabelas relacionadas (como a matrícula do colaborador e o tombamento do bem).
- **Volume e Paginação**: O sistema atualmente trabalha com visualização dos 200 registros mais recentes no fluxo geral (`limit=200`). A pesquisa atua dentro desse mesmo mecanismo de corte do backend, garantindo desempenho e previsibilidade de memória.
- **Padrão de Interface**: A interface do SisPatrimônio Pro adota Bootstrap 5 com temas gerenciados por variáveis CSS (`--c-border`, `--c-surface`, `--c-text`), garantindo compatibilidade imediata em modo claro e escuro.
- **Permissões**: O acesso à rota `/movements` continua unificado sob a permissão `movimentacao.visualizar`. Não há necessidade de criar uma nova permissão exclusiva para a busca.

---

## 6. Matriz de Testes Obrigatórios

A implementação deve ser validada pelos seguintes testes automatizados:

| Teste | Descrição | Entrada | Resultado Esperado |
|---|---|---|---|
| **Teste A** | Pesquisa por tombamento | `search = "PAT-99001"` | Apenas movimentações do bem com tombamento `PAT-99001` retornadas. |
| **Teste B** | Pesquisa parcial por equipamento | `search = "Latitude"` | Movimentações de "Dell Latitude 5440" encontradas com sucesso. |
| **Teste C** | Pesquisa por colaborador | `search = "Rodrigo"` ou `search = "MAT-5001"` | Movimentações cujo colaborador de origem ou destino corresponda ao termo. |
| **Teste D** | Pesquisa por local | `search = "TI Central"` | Movimentações com origem ou destino no local especificado. |
| **Teste E** | Pesquisa combinada com tipo | `search = "Dell"` + `movement_type = "TRANSFERENCIA_LOCAL"` | Somente transferências de equipamentos Dell retornadas. |
| **Teste F** | Pesquisa sem resultados | `search = "TERMO_INEXISTENTE"` | Lista vazia, exibição de mensagem clara de estado vazio. |
| **Teste G** | Pesquisa vazia ou nula | `search = ""` | Comportamento padrão de listagem preservado integralmente. |
| **Teste H** | Paginação e limite | Consulta com mais de 200 itens | Limite de registros do backend respeitado sem erro. |
| **Teste I** | Permissão RBAC | Usuário sem `movimentacao.visualizar` | Acesso negado com código HTTP 403. |
| **Teste J** | Regressão da suíte | Execução de `pytest tests/test_movements.py` | 100% dos testes existentes aprovados. |
