# Feature Specification: Correção do Backup Manual no Windows

**Feature Branch**: `018-correcao-backup-windows`

**Created**: 2026-09-18

**Status**: Draft

**Input**: Corrigir a falha na geração do backup manual do SisPatrimônio Pro no Windows (erro atual: "Falha na geração do backup manual (erro de disco/subprocesso)." em `data/logs/app.error.log`), preservando o funcionamento no Linux. A causa NÃO deve ser presumida: deve ser identificada por análise do código e do comportamento real do ambiente. Menor alteração possível; mecanismo de backup existente (features 015–017) permanece o único.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backup manual funciona no Windows (Priority: P1)

Um administrador com permissão de gerenciar backups acessa a tela de backups no SisPatrimônio Pro executado no Windows (com MariaDB/XAMPP), solicita a geração do backup manual e a operação é concluída com sucesso: o arquivo é criado, validado, aparece na listagem com integridade OK e pode ser baixado. A auditoria registra o sucesso.

Hoje essa mesma operação falha com uma mensagem genérica que não permite identificar a causa.

**Why this priority**: É o problema central da feature — o backup manual é a proteção dos dados do sistema e está inoperante no ambiente Windows atual.

**Independent Test**: Teste real no Windows (não apenas unitário): iniciar a aplicação → gerar backup pela tela → arquivo criado e validado → backup listado com integridade OK → download funciona → auditoria registra sucesso.

**Acceptance Scenarios**:

1. **Given** o sistema executando no Windows com o utilitário nativo de dump do banco disponível no ambiente, **When** o administrador gera um backup manual, **Then** a operação é concluída com sucesso, o arquivo aparece na listagem com integridade OK e o download retorna o conteúdo íntegro.
2. **Given** qualquer geração de backup, **When** o resultado é apresentado como sucesso, **Then** todas as etapas de validação existentes foram concluídas (execução do utilitário, arquivo existente, conteúdo válido, validação existente) — nunca sucesso parcial.
3. **Given** o mesmo cenário do cenário 1, **When** a auditoria é consultada, **Then** o evento de sucesso é registrado conforme o mecanismo existente, sem credenciais.

---

### User Story 2 - Falhas de backup são diagnosticáveis sem expor segredos (Priority: P1)

Quando uma geração de backup falha, o log técnico registra informação suficiente para identificar a etapa e a causa da falha (tipo da exceção, mensagem, código de retorno, saída de erro do utilitário sanitizada e a etapa que falhou), sem nunca registrar credenciais. O usuário final continua recebendo apenas a mensagem amigável de falha.

Hoje o log registra somente a mensagem genérica "(erro de disco/subprocesso)", o que tornou o diagnóstico impossível sem alterar código.

**Why this priority**: É a condição para corrigir e manter o backup: sem diagnóstico técnico, qualquer falha futura volta a ser opaca. O briefing exige diagnóstico antes da implementação.

**Independent Test**: Provocar falhas controladas (executável inexistente, retorno de erro do utilitário, timeout) e verificar que o log técnico permite identificar cada causa sem reproduzir o erro — e que nenhuma credencial aparece.

**Acceptance Scenarios**:

1. **Given** uma falha na execução do utilitário de dump, **When** o log técnico é consultado, **Then** ele identifica a etapa que falhou e a causa (tipo/mensagem da exceção e, quando disponível, código de retorno e saída de erro sanitizada).
2. **Given** uma saída de erro do utilitário que contenha a senha do banco, **When** ela é registrada no log técnico, **Then** a senha aparece mascarada/ausente — nenhuma credencial é exposta.
3. **Given** uma falha de backup, **When** o usuário final visualiza a mensagem na tela, **Then** recebe uma mensagem clara de falha sem detalhes técnicos sensíveis (a mensagem amigável atual é preservada, ajustada somente se necessário para informar corretamente o resultado).

---

### User Story 3 - Robustez de falhas e preservação do Linux (Priority: P2)

Todos os cenários de falha são tratados sem falso sucesso: código de retorno diferente de zero é falha mesmo que um arquivo tenha sido criado; arquivo parcial nunca é listado ou disponibilizado como backup válido; falhas de executável ausente, diretório/permissão, espaço em disco, banco, subprocesso, timeout, compactação, validação e limpeza são distinguíveis quando possível, usando a estrutura existente. O comportamento no Linux permanece idêntico ao atual.

**Why this priority**: Protege contra regressão e contra backups "falsos" — um backup inválido apresentado como válido é pior que a falha explícita.

**Independent Test**: Suíte de testes (executores falsos) cobrindo os cenários A–H do briefing + validação real no Linux, quando o ambiente estiver disponível.

**Acceptance Scenarios**:

1. **Given** o utilitário de dump retorna código de erro, **When** a geração termina, **Then** o resultado é FALHA mesmo que um arquivo tenha sido gerado; o arquivo parcial não fica disponível como backup válido.
2. **Given** um arquivo parcial remanescente de uma falha, **When** a listagem de backups é consultada, **Then** o parcial não aparece (comportamento existente de temporários preservado); se a limpeza do parcial falhar, isso é registrado no log sem ocultar a falha original.
3. **Given** falhas distintas (executável ausente, permissão negada, espaço insuficiente, timeout, erro do banco, erro do subprocesso), **When** cada uma ocorre, **Then** o resultado é FALHA com diagnóstico técnico que permite distingui-las, sem criar hierarquia nova de exceções.
4. **Given** o sistema executando no Linux, **When** um backup manual é gerado, **Then** o comportamento é idêntico ao atual (mesmo fluxo, mesmos artefatos, mesma auditoria) — zero regressão.

---

### Edge Cases

- Utilitário de dump não encontrado no Windows (nome simples sem resolução de executável; PATH do ambiente do subprocesso).
- Ambiente do subprocesso com PATH fixado em diretórios que não existem no Windows (fato observado na análise inicial — a confirmar no diagnóstico; ver Assumptions).
- Diretório de backup inexistente, sem permissão de escrita, ou caminho inválido no Windows.
- Espaço em disco insuficiente durante o dump ou a compactação — distinguível de falha genérica do subprocesso.
- Timeout do utilitário de dump.
- Saída de erro do utilitário contendo a senha do banco — jamais pode vazar para logs, auditoria ou tela.
- Falha durante a limpeza do arquivo parcial — registrada sem ocultar a falha original.
- Tentativa de geração de backup durante uma restauração em andamento — guarda existente da feature 017 preservada.
- Diferenças de codificação/encoding de mensagens de erro no Windows (console e registro em log).

## Requirements *(mandatory)*

### Functional Requirements

**Diagnóstico (antes da implementação)**

- **FR-001**: A implementação DEVE ser precedida de diagnóstico conclusivo, registrado nos artefatos de planejamento, respondendo explicitamente: (a) qual é a causa real; (b) por que funciona no Linux; (c) por que falha no Windows; (d) qual trecho do código causa a diferença; (e) qual é a menor alteração necessária; (f) se essa alteração continua funcionando no Linux.
- **FR-002**: A causa NÃO pode ser presumida nem resolvida por tentativa específica de Windows sem comprovação do diagnóstico (não concluir antecipadamente que o problema é o banco, o utilitário de dump, caminho, permissão, subprocesso, espaço, extensão executável, separador de diretório, PATH ou XAMPP).

**Log técnico e segurança**

- **FR-003**: Em falha de geração, o log técnico DEVE registrar, quando disponível: tipo da exceção, mensagem da exceção, código de retorno do utilitário, saída de erro do utilitário (sanitizada) e a etapa que falhou — sem criar handlers novos, duplicar mensagens ou alterar globalmente o logging da aplicação.
- **FR-004**: É PROIBIDO registrar credenciais em logs, auditoria ou mensagens: senha do banco, URL de conexão com senha, tokens, chaves — inclusive em conteúdos derivados da saída de erro do utilitário e em qualquer composição de comando passada ao subprocesso.
- **FR-005**: A senha do banco NÃO deve ser passada ao utilitário por linha de comando/argv visível de processo — o mecanismo existente de passagem por ambiente do subprocesso deve ser preservado.
- **FR-006**: A mensagem amigável exibida ao usuário deve ser preservada, ajustando-a somente se necessário para informar corretamente o resultado da operação.

**Execução multiplataforma**

- **FR-007**: O utilitário nativo de dump deve ser localizado/executado corretamente no Windows e no Linux, sem caminho fixo hardcoded no código; se uma configuração explícita for comprovada como indispensável pelo diagnóstico, deve reutilizar a configuração existente do projeto ou criar somente a variável mínima necessária, documentada (exemplo de configuração sem senha real).
- **FR-008**: A execução do utilitário deve ser direta e segura (sem depender de shell, sem comandos de shell quando não necessários), multiplataforma.
- **FR-009**: O mecanismo de backup existente (features 015–017) permanece o único oficial: nenhuma duplicação completa por sistema operacional; diferenciação por SO somente quando tecnicamente indispensável.
- **FR-010**: A conexão principal do banco (DATABASE_URL) NÃO deve ser alterada para corrigir o backup; a conexão usada pelo mecanismo de backup permanece distinta da conexão da aplicação.

**Integridade do resultado**

- **FR-011**: O backup só pode ser considerado concluído quando: execução do utilitário bem-sucedida E arquivo existente E conteúdo válido E validação existente bem-sucedida. Qualquer etapa falha → BACKUP = FALHA.
- **FR-012**: Código de retorno do utilitário diferente de zero DEVE ser tratado como falha — nunca sucesso apenas porque o arquivo de saída foi criado.
- **FR-013**: Arquivo parcial gerado antes de uma falha: não classificado como backup válido, não disponibilizado para restauração, removido com limpeza segura quando possível; falha de limpeza registrada no log sem ocultar a falha original.
- **FR-014**: Quando possível, o tratamento deve distinguir: executável não encontrado, diretório inexistente/inacessível, permissão negada, espaço insuficiente, falha do banco, falha do subprocesso, timeout, falha de compactação, falha de validação e falha de limpeza — utilizando a estrutura de tratamento existente, sem hierarquia nova de exceções.
- **FR-015**: Erros de permissão de escrita no Windows (acesso negado) devem ser tratados como falha diagnosticável; é proibido contorná-los exigindo execução como administrador, reduzindo permissões ou desabilitando proteções do sistema operacional.

**Preservação do sistema existente**

- **FR-016**: A auditoria existente de backup (eventos de sucesso e falha já utilizados pelo mecanismo atual) DEVE continuar funcionando sem alteração de formato; nenhum segundo sistema de auditoria.
- **FR-017**: Autenticação, autorização (RBAC), listagem e download existentes devem ser preservados; o diretório de backup não pode ficar exposto diretamente pela web nem permitir acesso arbitrário a arquivos do servidor.
- **FR-018**: A interface da tela de Backup Manual deve ser preservada (tela, navegação, tema, menus, permissões); somente a mensagem de erro pode ser ajustada conforme FR-006.
- **FR-019**: O comportamento no Linux deve permanecer idêntico ao atual: mesmo fluxo, mesmos artefatos gerados, mesma auditoria — zero regressão comprovada pela suíte de testes.
- **FR-020**: Fora do escopo (proibido nesta feature): restauração nova ou automática, agendamento, retenção/limpeza automática, monitoramento externo, backup em nuvem, replicação, novo sistema de backup, novo sistema de auditoria, nova arquitetura de banco, alteração de schema, alteração de RBAC/AD/usuários/colaboradores, alteração de módulos não relacionados.

### Key Entities *(include if feature involves data)*

- **Backup (arquivo)**: entidade existente, derivada do repositório de arquivos no diretório de backups configurado (sem tabela no banco). Nenhuma entidade nova; zero alteração de schema.
- **Registro de auditoria**: eventos existentes de backup (criado/falha/download e eventos de restauração) reutilizados como estão — sempre sem credenciais.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em um teste real no Windows com XAMPP/MariaDB, a geração manual produz arquivo listado com integridade OK, download íntegro e auditoria de sucesso — 100% das etapas do teste real concluídas (a aplicação inicia → backup gerado → arquivo validado → listado → download funciona → auditoria registrada).
- **SC-002**: No Linux, o backup manual permanece funcionando sem regressão: suíte de testes no patamar atual (com a única falha pré-existente conhecida) e, quando o ambiente estiver disponível, teste real confirmatório.
- **SC-003**: Cada cenário de falha simulado (executável ausente, diretório inválido, subprocesso com erro, arquivo parcial, auditoria, credenciais) resulta em FALHA registrada — zero falso sucesso — com log técnico suficiente para identificar a causa sem reproduzir o erro.
- **SC-004**: Zero ocorrências de credenciais (senha do banco, URL de conexão com senha, segredos) em logs, auditoria ou mensagens, em todos os cenários de sucesso e falha.
- **SC-005**: O diagnóstico (FR-001) está documentado e responde as seis perguntas antes de qualquer alteração de código; a menor alteração necessária é identificada e justificada.
- **SC-006**: Nenhum módulo não relacionado foi alterado (verificação do repositório ao final).

## Assumptions

- **Executor de dump em testes**: a suíte automatizada utiliza executor falso para o dump (padrão estabelecido pelas features 015–017, pois o banco de teste não executa o utilitário nativo); a prova real de funcionamento é manual — Windows (obrigatória quando o ambiente estiver disponível) e Linux (quando disponível). Testes unitários não são considerados prova de funcionamento no Windows.
- **Ambiente Windows atual**: o sistema está sendo executado no Windows com MariaDB/XAMPP; presume-se que o utilitário de dump necessário esteja disponível nesse ambiente (a confirmar no diagnóstico — se não estiver, o comportamento de falha diagnosticável se aplica).
- **Pontos de atenção confirmados na análise inicial (somente leitura) — fatos a confirmar no diagnóstico, NÃO conclusões de causa**:
  1. O ambiente repassado ao subprocesso do dump (e da importação) fixa a variável PATH com diretórios Unix — comportamento a verificar no Windows.
  2. O utilitário é invocado por nome simples, sem mecanismo de localização configurável no projeto (a configuração existente cobre apenas o diretório de backups e a URL do banco).
  3. O caminho do dump não registra diagnóstico técnico (diferente do caminho de importação, que registra saída de erro sanitizada) — por isso o log atual exibe apenas a mensagem genérica "(erro de disco/subprocesso)", correspondente ao tratamento de erro de disco/subprocesso existente.
- **Configuração**: nenhuma variável nova além da mínima indispensável comprovada pelo diagnóstico; se criada, documentada com exemplo sem senha real. Não criar configurações duplicadas das existentes.
- **Concorrência com restauração**: a guarda existente (não gerar backup durante restauração em andamento, feature 017) permanece inalterada.
- **Dependência**: o mecanismo de backup das features 015–017 (service, rotas, permissão, tela, auditoria) é reutilizado integralmente — esta feature não cria mecanismo paralelo.
