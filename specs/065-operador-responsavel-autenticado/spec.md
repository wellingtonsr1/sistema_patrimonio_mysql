# Feature Specification: Operador Responsável Vinculado ao Usuário Autenticado

**Feature Branch**: `065-operador-responsavel-autenticado`  
**Created**: 2026-10-09  
**Status**: Draft  
**Input**: User description: "Fazer com que o campo Operador Responsável seja preenchido automaticamente com o usuário autenticado, sem comprometer auditoria, histórico de movimentações, autenticação LDAP/AD ou outras funcionalidades do SisPatrimônio Pro."

---

## Clarifications

### Session 2026-10-09

- Q: Como o campo "Operador Responsável" deve ser exibido visualmente no formulário HTML de movimentação patrimonial? → A: Option A - Campo de texto tradicional (`form-control`), marcado como `readonly`, exibindo a identidade do usuário logado e a indicação "(Preenchido automaticamente)".

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Preenchimento e Definição Automática do Operador (Priority: P1)

Como operador ou gestor do patrimônio devidamente autenticado no sistema,  
ao abrir o formulário de movimentação patrimonial,  
quero visualizar a minha identidade (Nome Completo ou Username) preenchida automaticamente no campo "Operador Responsável",  
para que eu não precise digitar ou apagar o texto genérico ("Operador do Patrimônio") e para que o registro seja gravado de forma precisa e auditável.

**Why this priority**: É o objetivo central da funcionalidade. Elimina o preenchimento manual/genérico e assegura a vinculação real do operador à movimentação.

**Independent Test**: Pode ser testado realizando o login com um usuário (local ou via Active Directory/LDAP) e abrindo a rota `/movements/new`. O campo "Operador Responsável" deve exibir o nome do usuário autenticado e a movimentação gravada no banco deve persistir exatamente essa identidade.

**Acceptance Scenarios**:
1. **Given** um usuário autenticado como "Carlos Silva" (`full_name="Carlos Silva"`, `username="csilva"`), **When** ele acede ao formulário `/movements/new`, **Then** o campo "Operador Responsável" exibe "Carlos Silva" (campo preenchido como `readonly`).
2. **Given** um usuário autenticado apenas com `username="admin"` (sem `full_name`), **When** ele acede ao formulário `/movements/new`, **Then** o campo "Operador Responsável" exibe "admin".
3. **Given** uma requisição POST de criação de movimentação enviada por um usuário autenticado, **When** a requisição é processada pelo servidor, **Then** o servidor determina o nome do operador a partir do `request.state.user` da sessão autenticada, gravando-o na tabela `movements`.

---

### User Story 2 — Proteção Contra Falsificação de Identidade (Priority: P2)

Como administrador do sistema e auditor de segurança,  
quero que o servidor determine a identidade do operador exclusivamente a partir da sessão autenticada (servidor), ignorando qualquer tentativa de alteração manual ou envio de dados manipulados via navegador,  
para que um usuário mal-intencionado não consiga registrar movimentações em nome de outro operador.

**Why this priority**: Garante a integridade da trilha de auditoria e impede que o navegador seja tratado como fonte confiável de identidade.

**Independent Test**: Pode ser testado simulando um formulário POST HTTP no qual o campo `operator_name` no corpo do form é alterado para "Outro Operador". O servidor deve ignorar o parâmetro manipulado e gravar o nome do usuário da sessão autenticada.

**Acceptance Scenarios**:
1. **Given** um usuário autenticado "João Souza" enviando uma requisição POST para `/movements/new`, **When** o corpo do formulário contém `operator_name="Maria Oliveira"`, **Then** o servidor ignora "Maria Oliveira" e registra "João Souza" como `operator_name` da movimentação.

---

### User Story 3 — Preservação de Histórico, Documentos e Rotas Alternativas (Priority: P3)

Como auditor e usuário do SisPatrimônio Pro,  
quero que todas as movimentações anteriores permaneçam inalteradas e que relatórios, termos de cautela, exportações e rotas automáticas continuem funcionando perfeitamente,  
para garantir zero regressão no sistema.

**Why this priority**: Garante retrocompatibilidade e integridade dos dados históricos existentes.

**Independent Test**: Consulta a movimentações antigas na interface, geração de relatórios de movimentação e verificação do funcionamento de rotas de importação CSV/automações.

**Acceptance Scenarios**:
1. **Given** movimentações gravadas antes da implementação (ex: com `operator_name="Operador do Patrimônio"` ou "Sistema"), **When** consultadas na tela `/movements` ou em relatórios/PDFs, **Then** os dados históricos exibem seus valores originais sem alterações.
2. **Given** o fluxo de importação em lote de bens (`/assets/import`), **When** executado por um usuário autenticado, **Then** as movimentações geradas continuam a utilizar a identidade do usuário autenticado (conforme regra da Feature 029).

---

### Edge Cases

- **Usuário sem `full_name` definido**: O sistema deve utilizar `username` como fallback seguro (`user.full_name or user.username`).
- **Autenticação via Active Directory / LDAP**: Como o login via AD sincroniza/preenche `user.full_name` com o `display_name` do AD e `user.username` com o sAMAccountName, a lógica `(user.full_name or user.username)` funciona de forma idêntica e transparente.
- **Requisição sem sessão autenticada**: O middleware de autenticação (`require_web_auth` / `require_permission`) já redireciona requisições web para `/login` (303) e rejeita requisições de API com 401. Nenhuma movimentação é criada sem autenticação.
- **Nomes longos**: Caso o nome completo do usuário ultrapasse 100 caracteres (limite da coluna `movements.operator_name`), o servidor trunca o valor para 100 caracteres antes de gravar, evitando erro de banco de dados.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O formulário web de movimentação (`/movements/new`) MUST apresentar o campo "Operador Responsável" preenchido automaticamente com o nome do usuário autenticado na sessão (`current_user.full_name or current_user.username`).
- **FR-002**: O campo "Operador Responsável" na interface web MUST ser mantido como elemento de formulário de texto padrão (`form-control`), configurado como `readonly` (somente leitura) com a indicação "(Preenchido automaticamente)", impedindo edições no navegador.
- **FR-003**: O endpoint do servidor web (`POST /movements/new`) MUST extrair a identidade do operador diretamente do contexto de autenticação validado (`request.state.user`), ignorando o valor enviado pelo formulário cliente para fins de persistência.
- **FR-004**: O endpoint da API REST (`POST /api/v1/movements`) MUST sobrescrever o atributo `operator_name` com a identidade do usuário autenticado obtido via token de sessão/API (`request.state.user`), garantindo imunidade contra falsificação de identidade (spoofing).
- **FR-005**: O sistema MUST suportar perfeitamente usuários autenticados via base local e usuários autenticados via Active Directory / LDAP, utilizando `(user.full_name or user.username)` como regra uniforme de identificação.
- **FR-006**: A persistência MUST limitar o valor de `operator_name` a no máximo 100 caracteres (capacidade da coluna `movements.operator_name`), aplicando truncamento seguro caso o nome do usuário exceda essa extensão.
- **FR-007**: As movimentações existentes no banco de dados MUST permanecer inalteradas. Nenhuma alteração retroativa pode ser realizada nos registros históricos.
- **FR-008**: A geração de termos de responsabilidade (PDF/HTML), comprovantes, relatórios e a trilha de auditoria MUST continuar funcionando sem qualquer alteração nas assinaturas ou contratos de serviços.
- **FR-009**: Todos os fluxos operacionais de movimentação (alocação a colaborador, transferência entre locais/setores, devolução ao estoque, envio/retorno de manutenção e baixa definitiva) MUST continuar operantes e utilizar a mesma regra de atribuição do operador.
- **FR-010**: A implementação MUST ser cirúrgica, modificando estritamente os arquivos necessários e mantendo a suíte de testes 100% verde.

---

### Security & Audit Requirements

- **SEC-001**: O servidor é a única autoridade para identificação do operador. O valor enviado pelo cliente HTTP NUNCA deve ser aceito como fonte primária quando houver um usuário autenticado na requisição.
- **SEC-002**: O registro de auditoria (`write_change_audit`) MUST continuar registrando o usuário da sessão em `user=request.state.user`, mantendo consistência total entre o campo `operator_name` da movimentação e o log de auditoria global do sistema.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das novas movimentações criadas via interface web são gravadas com a identidade do usuário autenticado, sem nenhum registro com o valor genérico "Operador do Patrimônio".
- **SC-002**: 100% das tentativas de falsificação de identidade (envio de `operator_name` manipulado via POST) são neutralizadas pelo servidor, gravando o usuário real da sessão.
- **SC-003**: 0% de regressão nos registros históricos e 100% de aprovação na suíte de testes automatizados (`pytest`).
- **SC-004**: O tempo de abertura do formulário e de gravação da movimentação permanece inalterado (0 overhead perceptível).

---

## Acceptance Criteria

- **AC01 — Preenchimento automático**: O formulário apresenta a identificação do usuário autenticado (`current_user.full_name or current_user.username`), em vez do texto genérico "Operador do Patrimônio".
- **AC02 — Persistência correta**: A movimentação registra no banco de dados o operador autenticado na sessão atual.
- **AC03 — Proteção contra falsificação**: Uma requisição HTTP manipulada que tente informar outro operador não altera a identidade efetivamente registrada no servidor.
- **AC04 — Autenticação obrigatória**: Nenhuma movimentação é criada sem autenticação válida; a tentativa é bloqueada com redirecionamento/401 pelos middlewares existentes.
- **AC05 — Compatibilidade com autenticação**: O comportamento funciona de forma idêntica tanto para contas locais quanto para contas sincronizadas via Active Directory / LDAP.
- **AC06 — Histórico preservado**: Os registros antigos permanecem intactos no banco de dados e continuam consultáveis em telas e relatórios.
- **AC07 — Documentos e relatórios**: Termos de responsabilidade, relatórios, consultas e exportações continuam funcionando normalmente e exibindo o operador registrado.
- **AC08 — Regressão**: Os fluxos de alocação a colaborador, transferência de setor/filial, devolução ao estoque e baixa definitiva continuam funcionando perfeitamente.
- **AC09 — Cobertura de Testes**: Testes automatizados cobrem o preenchimento, a persistência no servidor, a tentativa de falsificação de identidade e a retrocompatibilidade.
- **AC10 — Escopo Mínimo**: A implementação modifica apenas os arquivos estritamente necessários (`movements/new.html`, `app/web/routers/movements.py`, `app/api/movements_api.py`, e testes), sem alterações de banco de dados ou refatorações desnecessárias.

---

## Assumptions

- **Premissa 1**: O modelo SQLAlchemy `Movement` e a coluna `movements.operator_name` (VARCHAR 100) possuem estrutura adequada e não requerem alteração no esquema do banco de dados (Alembic/MySQL).
- **Premissa 2**: O objeto `User` exposto em `request.state.user` pelo middleware de autenticação possui os campos `full_name` e `username` devidamente populados tanto para login local quanto para Active Directory.
- **Premissa 3**: O context processor de templates Jinja2 (`_inject_current_user`) disponibiliza a variável `current_user` para a página `/movements/new`.
