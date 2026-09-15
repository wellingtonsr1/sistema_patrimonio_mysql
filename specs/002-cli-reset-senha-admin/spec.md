Claro. Abaixo está a **versão corrigida do `spec.md`**, mantendo o restante da especificação e alterando apenas os pontos necessários: **D-2**, **D-3** e **FR-011/auditoria**.

# Feature Specification: CLI de Reset Administrativo de Senha

**Feature Branch**: `002-cli-reset-senha-admin`

**Created**: 2026-09-15

**Status**: Draft — decisões D-1..D-4 registradas (2026-09-15); aguardando revisão final do responsável

**Input**: User description: "Implementar comando CLI para reset administrativo de senha. Permitir que um administrador do servidor redefina a senha de um usuário local do SisPatrimônio diretamente pelo terminal, usando a CLI Python existente. Não é 'Esqueci minha senha' self-service. A senha não pode aparecer na linha de comando, em argumentos do processo, em logs, em arquivos temporários, na auditoria ou em mensagens de erro. Entrada por prompt sem eco. Deve reutilizar o mecanismo existente de hash/serviço de senha, invalidar sessões conforme o comportamento atual, preservar roles/permissões, não alterar dados não relacionados, tratar erros sem exposição de informações sensíveis. Destinado à senha LOCAL — nunca alterar credenciais do Active Directory. Analisar o código existente antes de especificar; marcar pendências de decisão em vez de inventar soluções."

---

## 1. Contexto do Sistema Existente (análise obrigatória — verificada no código)

Esta feature **não é greenfield**. A análise do código confirmou que **todo o mecanismo necessário já existe** e deve ser reutilizado — nenhuma segunda implementação de hash, validação, armazenamento ou invalidação de sessão é permitida:

| Mecanismo existente                                                                                                 | Onde está                                                                                                                                                          | Evidência                                                                                                                                 | Papel nesta feature                                                         |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Redefinição administrativa de senha (política, hash, limpeza de bloqueio, invalidação de sessões, gravação atômica) | `app/services/auth_service.py` → `reset_password(db, user, new_password)`                                                                                          | Linha 176; já usada pela administração web (`admin_routes.py:360-384`)                                                                    | **Único caminho de escrita** do novo comando                                |
| Hash seguro de senha (PBKDF2-HMAC-SHA256, salt por senha, formato `pbkdf2_sha256$iter$salt$hash`)                   | `app/services/auth_service.py` → `hash_password` / `verify_password`                                                                                               | Linhas 60–83                                                                                                                              | Reutilizado indiretamente pelo serviço acima — proibido criar hash paralelo |
| Política de senha atual (mínimo 8 caracteres)                                                                       | `reset_password` / `create_user` no mesmo serviço                                                                                                                  | Levanta `ValueError("A nova senha deve ter no mínimo 8 caracteres.")`                                                                     | Mantida sem alteração; nenhuma política nova                                |
| Interação CLI com senha oculta + confirmação dupla                                                                  | `app/cli.py` → comando `create-user`                                                                                                                               | `import getpass`; `getpass.getpass("Senha: ")` + `getpass.getpass("Confirme a senha: ")`; erro "as senhas não conferem" com `sys.exit(1)` | Padrão de interface a seguir                                                |
| Padrão de subcomandos da CLI                                                                                        | `app/cli.py`                                                                                                                                                       | `argparse` + `subparsers` (`stats`, `list`, `show`, `move`, `create-user` — kebab-case, opções `--nome`)                                  | Novo subcomando segue exatamente este padrão                                |
| Trilha de auditoria de operações de senha                                                                           | `app/services/audit_service.py` → `write_audit`; constante `ACTION_PASSWORD_RESET = "RESET_SENHA"` (rótulo "Redefinição de Senha")                                 | Linhas 32, 72                                                                                                                             | Evento a registrar em cada execução (sucesso e falha), **sem a senha**      |
| Identificação de usuário local × AD                                                                                 | `app/models/user.py` → `auth_provider` (`local` | `ad`); provisionamento AD grava `password_hash="!ad-external"` (hash propositalmente inválido, provedor externo) | `app/services/ad_service.py:282-288`                                                                                                      | Critério de recusa para usuários AD                                         |
| Invalidação de sessões ao trocar/resetar senha                                                                      | `reset_password` exclui as sessões do usuário (`UserSession`) e grava em commit único                                                                              | Linhas 186–191                                                                                                                            | Comportamento preservado — o comando apenas o consome                       |
| Precedente de uso + auditoria do evento                                                                             | `app/web/admin_routes.py` → `admin_reset_password`                                                                                                                 | Registra `RESET_SENHA` com descrição "Redefinição de senha do usuário X (sessões invalidadas)"                                            | Modelo do registro de auditoria a reproduzir                                |

**Conclusão da análise**: o comando é **necessário** (não existe caminho de reset pela CLI — apenas `create-user` e os fluxos web) e é **viável sem criar mecanismo paralelo**: o novo subcomando é um invocador terminal do serviço existente, seguindo os padrões de interface já consolidados na própria CLI.

**Nome do comando (derivado do padrão existente, não inventado)**: os subcomandos atuais usam kebab-case em inglês (`create-user`), logo o comando proposto é:

```bash
python -m app.cli reset-password --username <usuario>
```

---

## 2. User Scenarios & Testing

### User Story 1 - Administrador redefine a senha de um usuário local pelo terminal (Priority: P1)

Um administrador com acesso ao servidor perdeu contato com as credenciais de um usuário local (ex.: responsável saiu de férias, senha esquecida, conta recém-criada precisa de senha inicial definida). Ele executa um comando na CLI, informa o nome do usuário, digita a nova senha duas vezes **sem que ela apareça na tela**, e recebe confirmação. O usuário alvo loga imediatamente com a nova senha; todas as sessões antigas dele deixam de valer; seus perfis, permissões e demais dados permanecem intocados.

**Why this priority**: é o valor central da feature — recuperação administrativa de acesso sem depender de acesso direto ao banco nem expor a senha em comando, log ou tela.

**Independent Test**: com um usuário local existente, executar o comando, fornecer a nova senha via prompt oculto e verificar: mensagem de sucesso; login só funciona com a nova senha; sessões anteriores do alvo invalidadas; perfis/permissões/demais atributos inalterados; nenhum rastro da senha em processo, logs ou tela.

**Acceptance Scenarios**:

1. **Given** um usuário local existente e ativo, **When** o administrador executa o comando informando o username e fornece nova senha (mínimo 8 caracteres) com confirmação coincidente, **Then** o comando reporta sucesso, o acesso com a senha antiga deixa de funcionar, o acesso com a nova funciona, todas as sessões ativas do usuário são invalidadas e perfis/permissões/demais atributos permanecem idênticos.

2. **Given** o mesmo comando em execução, **When** a senha é digitada, **Then** nenhum caractere aparece no terminal (entrada oculta) e a senha não consta nos argumentos do processo nem em qualquer saída do comando.

3. **Given** a confirmação digitada difere da primeira entrada, **When** o operador conclui a digitação, **Then** o comando aborta com mensagem clara ("as senhas não conferem"), nada é alterado no usuário e nenhuma sessão é invalidada.

---

### User Story 2 - Todo erro falha de forma segura, clara e sem alterar estado (Priority: P2)

Um operador de servidor comete erros: digita um username inexistente, tenta redefinir a senha de um usuário autenticado pelo Active Directory, digita uma senha curta demais, ou sofre uma falha de banco no meio da operação. Em todos os casos o comando recusa a operação, apresenta uma mensagem objetiva que orienta a correção **sem revelar informações sensíveis**, encerra com código de erro e deixa o sistema exatamente como estava.

**Why this priority**: a confiabilidade do comando administrativo depende de falhar sempre no mesmo padrão seguro — sem alteração parcial, sem semântica ambígua, sem vazamento de dados.

**Independent Test**: para cada caso de erro (inexistente, AD, política de senha, confirmação divergente, falha de gravação), executar o comando e verificar: código de saída com erro, mensagem clara não sensível, e o usuário alvo (quando existir) inalterado — nenhuma sessão invalidada pela tentativa malsucedida.

**Acceptance Scenarios**:

1. **Given** um username inexistente, **When** o comando é executado, **Then** mensagem de usuário não encontrado, encerramento com erro, nenhum usuário criado e nada alterado.

2. **Given** um usuário provisionado pelo Active Directory, **When** o comando é executado, **Then** recusa explícita informando que o comando redefine apenas senha local e não altera credenciais do AD; nada é alterado no usuário.

3. **Given** uma nova senha com menos de 8 caracteres, **When** fornecida, **Then** o mecanismo existente recusa com a mensagem atual da política de senha; a senha antiga permanece válida; nada muda.

4. **Given** falha de banco durante a gravação, **When** ela ocorre, **Then** mensagem genérica de falha na atualização, encerramento com erro e nenhuma alteração parcial persistida.

---

### User Story 3 - Cada execução fica registrada na trilha de auditoria, sem segredos (Priority: P3)

O sistema já audita redefinições de senha feitas pela administração web. O novo caminho deve produzir rastreabilidade equivalente: **toda execução processada pelo comando deve tentar gerar exatamente um registro de auditoria**, seja sucesso ou falha, identificando a ação, o usuário alvo, o resultado e a origem (terminal), jamais contendo a senha ou qualquer segredo.

A autoria na aplicação permanece nula porque a CLI não autentica uma sessão do SisPatrimônio. Quando possível, a auditoria também deve registrar automaticamente o usuário do sistema operacional responsável pela execução, sem permitir que essa identidade seja informada manualmente como argumento.

**Why this priority**: redefinição de senha é operação sensível de administração de acesso; sem auditoria equivalente à web, a feature criaria um ponto cego na comprovação de segurança.

**Independent Test**: executar um reset bem-sucedido e duas tentativas que falham; verificar na trilha de auditoria os registros correspondentes do evento de redefinição de senha, com alvo, resultado, origem e identificação do operador do SO quando disponível, e conferir que nenhum registro contém a senha ou parte dela.

**Acceptance Scenarios**:

1. **Given** um reset bem-sucedido, **When** o comando conclui, **Then** a trilha registra o evento de redefinição de senha existente no catálogo, com usuário alvo, resultado de sucesso, origem CLI e descrição coerente com o precedente web — sem a senha.

2. **Given** uma tentativa que falha, **When** o comando encerra com erro, **Then** a trilha tenta registrar a tentativa com resultado de falha, identificando o alvo informado quando possível — sem a senha e sem detalhes internos do erro.

3. **Given** a execução ocorre diretamente ou através de `sudo`, **When** o ambiente fornece uma identidade do sistema operacional, **Then** a auditoria utiliza automaticamente `SUDO_USER` quando disponível e, como fallback, o usuário retornado por `getpass.getuser()`.

4. **Given** não seja possível identificar o usuário do sistema operacional, **When** o comando é executado, **Then** a operação não deve falhar exclusivamente por ausência dessa informação; o campo permanece nulo e a origem `CLI` continua sendo registrada.

---

## Edge Cases

* **Usuário local temporariamente bloqueado por tentativas falhas (lockout)**: o comando permite o reset; o mecanismo existente limpa o bloqueio e o contador de falhas como parte da redefinição (comportamento atual de `reset_password`, preservado).

* **Usuário local inativo (bloqueado administrativamente)**: o reset é **permitido sem reativar a conta**. A redefinição da senha **nunca altera o status de ativação** do usuário. A senha fica válida para quando o administrador reativar o acesso.

* **Username com espaços nas extremidades ou em caixa diferente**: o comando aplica a mesma normalização do login existente (remoção de espaços; comparação conforme o padrão atual).

* **Entrada vazia, encerramento de entrada (EOF) ou interrupção durante o prompt oculto**: o comando aborta com erro sem alterar nada (tratado como "nenhuma senha fornecida").

* **Falha de banco**: mensagem genérica ao operador; nenhuma alteração parcial persistida (a gravação do mecanismo existente é atômica — hash + sessões no mesmo commit).

* **Falha na auditoria**: o comportamento deve seguir o mecanismo de auditoria existente. O plano de implementação deverá determinar, a partir do código, se a auditoria é transacional/obrigatória ou best-effort. A falha de auditoria não poderá expor senha, segredo, SQL, stack trace ou detalhes internos ao operador.

* **Usuário local que possui vínculo com colaborador ou perfis múltiplos**: irrelevante para a senha; nada além do mecanismo de reset é tocado.

---

## Requirements

### Functional Requirements

* **FR-001**: O sistema DEVE oferecer um novo subcomando na CLI existente, seguindo o padrão atual de subcomandos (kebab-case, opções com `--nome`): `reset-password` com opção `--username`. *(D-4)*

* **FR-002**: O comando DEVE localizar o usuário pelo username informado, aplicando a mesma normalização do login existente; usuário inexistente DEVE produzir erro claro e encerramento com falha, sem criar nem alterar nada.

* **FR-003**: O comando DEVE recusar usuários cuja origem de autenticação é o Active Directory, com mensagem explícita de que o comando redefine apenas a senha local do SisPatrimônio e nunca altera credenciais do AD. Nenhum mecanismo de alteração de senha AD será criado.

* **FR-004**: A nova senha DEVE ser fornecida exclusivamente por prompt de terminal sem eco. É PROIBIDO aceitar a senha como argumento visível da linha de comando, variável de ambiente, arquivo ou qualquer canal que a exponha no processo.

* **FR-005**: A nova senha DEVE ser solicitada duas vezes (entrada + confirmação, ambas ocultas); se divergirem, o comando DEVE abortar sem alterar nada. *(D-1)*

* **FR-006**: A política de senha aplicável é a existente (mínimo 8 caracteres), validada pelo mecanismo atual; senha inválida DEVE produzir a mensagem atual da política, sem alteração de estado. Nenhuma política nova será introduzida.

* **FR-007**: A senha DEVE ser armazenada pelo mecanismo único de hash já utilizado pelo sistema. É PROIBIDO criar segunda implementação de hash, verificação ou armazenamento de senha.

* **FR-008**: A atualização DEVE ser realizada exclusivamente pela camada de serviço existente de redefinição administrativa de senha (a mesma usada pela administração web). O comando NÃO DEVE gravar diretamente no banco.

* **FR-009**: Todas as sessões ativas do usuário alvo DEVEM ser invalidadas como efeito da redefinição, exatamente conforme o comportamento atual de troca/reset de senha.

* **FR-010**: Perfis, permissões, situação de administrador, vínculos e quaisquer outros atributos do usuário DEVEM permanecer inalterados. O reset **não deve alterar o status de ativação**; somente o que o mecanismo de reset existente altera pode mudar (por exemplo, hash da senha, contador de falhas e bloqueio temporário).

* **FR-011**: Cada execução processada pelo comando DEVE tentar gerar exatamente um registro na trilha de auditoria, utilizando o evento de redefinição de senha já existente no catálogo de ações, com usuário alvo quando identificável, resultado (sucesso/falha), origem `CLI` e identificação automática do operador do sistema operacional quando disponível.

* **FR-012**: É PROIBIDO registrar a senha, qualquer parte dela ou qualquer segredo em auditoria, logs, mensagens de erro, mensagens de sucesso ou saídas do comando.

* **FR-013**: As mensagens do comando DEVEM ser mínimas e objetivas (padrão atual `Erro:`/`Sucesso:` da CLI), sem revelar informações sensíveis nem detalhes internos de falhas (ex.: exceções de banco, SQL, stack traces).

* **FR-014**: Em falha de gravação ou de banco, o comando DEVE exibir mensagem genérica de falha, encerrar com erro e não persistir alteração parcial.

* **FR-015**: A funcionalidade DEVE vir acompanhada de testes cobrindo: reset bem-sucedido (senha trocada, sessões invalidadas, atributos preservados), recusa de usuário AD, usuário inexistente, política de senha, confirmação divergente, usuário inativo, lockout e auditoria sem segredos; a suíte de autenticação existente DEVE continuar passando sem modificações.

---

## Key Entities

* **Usuário (User)**: conta de acesso do sistema — identidade (username único), origem de autenticação (local ou Active Directory), situação de ativação, contador/bloqueio temporário de tentativas falhas e hash de senha (armazenamento seguro, nunca texto puro). É a única entidade afetada pela feature — e apenas nos atributos que o mecanismo de reset existente já altera.

* **Sessão de usuário (UserSession)**: sessão ativa do usuário alvo; todas as sessões existentes do alvo deixam de valer após o reset (efeito do mecanismo existente).

* **Registro de auditoria (AuditLog)**: entrada imutável e somente-leitura da trilha, gerada como tentativa para cada execução do comando (evento de redefinição de senha do catálogo atual), sem segredos.

---

## Success Criteria

### Measurable Outcomes

* **SC-001**: Um administrador conclui um reset de senha completo (comando + entrada oculta + confirmação) em menos de 2 minutos, sem consultar documentação além da ajuda do próprio comando.

* **SC-002**: 100% das execuções processadas pelo comando realizam uma tentativa de registro de auditoria com ator da aplicação nulo, alvo, resultado, origem `CLI` e operador do SO quando disponível.

* **SC-003**: Zero ocorrências da senha em argumentos do processo, logs, trilha de auditoria, mensagens e saídas do comando — verificável por inspeção e testes.

* **SC-004**: 100% dos casos de erro identificados produzem mensagem clara e não sensível, com encerramento com falha e estado do usuário alvo inalterado.

* **SC-005**: Após um reset, 100% das sessões anteriores do alvo deixam de funcionar e o próximo acesso exige a nova senha.

* **SC-006**: A suíte de testes existente relacionada à autenticação permanece 100% aprovada e o novo comportamento está coberto por testes novos aprovados.

---

## Assumptions

* O operador do comando já possui acesso ao servidor (shell) e ao ambiente da aplicação; a barreira de entrada é o acesso ao terminal do servidor — a CLI não possui login de usuário nem verificação RBAC da aplicação.

* A autoria da aplicação permanece nula (`user=None` ou equivalente), porque não existe sessão autenticada do SisPatrimônio na CLI.

* Quando disponível, a identificação do operador do sistema operacional deve ser obtida automaticamente, priorizando `SUDO_USER` e utilizando `getpass.getuser()` como fallback. O operador não poderá informar manualmente sua identidade através de argumento do comando.

* O nome do subcomando segue o padrão existente de subcomandos em kebab-case inglês (`create-user` → `reset-password`).

* A interação de entrada segue o padrão do `create-user` atual: senha oculta com confirmação dupla via prompt sem eco.

* A normalização/comparação do username é a mesma do login existente.

* Usuário local temporariamente bloqueado (lockout) pode ter a senha redefinida; o mecanismo existente limpa o bloqueio como parte do reset (comportamento atual, preservado).

* Usuário local inativo pode ter a senha redefinida, mas o reset **não altera seu status de ativação**.

* Nenhuma alteração de schema de banco, configuração, catálogo de permissões (RBAC) ou integração AD é necessária — confirmado pela análise (a funcionalidade é um invocador do serviço existente).

* Documentação (README/central de ajuda) será atualizada na mesma tarefa de implementação, conforme regra do projeto.

---

## Decisões Registradas (responsável, 2026-09-15)

Decisões que o código existente **não determinava por completo** foram submetidas ao responsável e **aprovadas com os defaults propostos**:

* **D-1 — Confirmação da nova senha**: ✅ **Sim** — dupla entrada oculta (espelha o `create-user` atual; reduz erro de digitação em operação sem visualização da senha).

* **D-2 — Autoria no registro de auditoria**: ✅ **Captura automática do usuário do sistema operacional + origem CLI** — o registro mantém o ator da aplicação nulo, pois a CLI não autentica uma sessão do SisPatrimônio. A origem deve ser identificada como `CLI`. Quando disponível, o operador do sistema operacional deve ser capturado automaticamente, priorizando `SUDO_USER` e utilizando `getpass.getuser()` como fallback. Não será permitido informar manualmente o operador como argumento.

* **D-3 — Reset para usuário local inativo**: ✅ **Permitir, sem reativar a conta** — o reset de senha é permitido para usuário local inativo, mas a operação jamais altera o status de ativação. A senha fica válida para quando o administrador reativar o acesso.

* **D-4 — Nome do comando**: ✅ **`reset-password`** — mantém o padrão kebab-case inglês da CLI (`create-user`, `stats`, `list`, `show`, `move`).

---

## Out of Scope (não serão tratados nesta feature)

* Recuperação de senha por e-mail; tela web de "Esqueci minha senha".
* Alteração de senha no Active Directory ou qualquer mecanismo de modificação de credenciais AD.
* Criação de novo sistema de autenticação ou mecanismo paralelo de gerenciamento de senha.
* Alteração de RBAC, do modelo de usuário, do schema do banco ou da configuração.
* Refatoração geral da CLI ou alterações não relacionadas à funcionalidade.
* Reset de senha via API REST ou interface web adicional (o caminho web já existe).
