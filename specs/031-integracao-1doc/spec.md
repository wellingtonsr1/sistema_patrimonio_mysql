# Feature Specification: Integração 1Doc — Comunicação Automática de Movimentações

**Feature Branch**: `031-integracao-1doc`

**Created**: 2026-09-23

**Status**: Draft

**Input**: Integração SisPatrimônio Pro → 1Doc: a movimentação nasce e é concluída no SisPatrimônio; depois disso, o sistema registra a movimentação no processo 1Doc já existente, usando o modelo de mensagem/tabela que o setor de Patrimônio já utiliza. O e-mail ao setor (feature 030) é preservado integralmente.

---

## 1. Objetivo

Eliminar a redigitação manual das informações de movimentação no 1Doc: quando uma movimentação patrimonial for concluída no SisPatrimônio Pro, o sistema deve incluir automaticamente uma **nova comunicação no processo 1Doc já existente**, com o conteúdo no **modelo atualmente utilizado pelo setor de Patrimônio**:

> Bom dia! Seguem os dados acerca da movimentação do equipamento:
>
> | Descrição do Material | Tombamento | Origem | Destino |
> |---|---|---|---|
> | Monitor DELL | 0008 | Suporte | Desenvolvimento |

O formato acima é **referência funcional** da integração — não criar um novo modelo visual arbitrário.

O e-mail para o setor de Patrimônio **já está implementado (feature 030) e não deve ser removido, substituído ou duplicado**. Esta spec trata exclusivamente da integração com o 1Doc; as duas integrações são **independentes**.

## Clarifications

### Session 2026-09-23

- Q: Quais tipos de movimentação devem gerar comunicação no processo 1Doc? → A: Apenas cautela (alocação) e transferência de local; devolução ao estoque NÃO gera comunicação no 1Doc (decisão Q1, 2026-09-23 — difere do e-mail da 030, que cobre os 3 tipos).
- Q: Como o sistema deve tratar o número do processo 1Doc quando a API não puder confirmar sua existência? → A: Validar via API quando suportado (C-3) — processo inexistente impede a conclusão na tela; sem suporte de consulta, modo tolerante (aceitar e tratar no envio) (decisão Q2, 2026-09-23).
- Q: O que fazer quando a API retornar sucesso mas sem identificador da mensagem criada? → A: Registrar como enviada, com identificador desconhecido — a comunicação chegou; apenas a rastreabilidade do ID fica ausente (decisão Q3, 2026-09-23).
- Q: Quem pode reprocessar integrações 1Doc falhas? → A: Somente portadores de permissão dedicada nova (ex.: integracao1doc.reprocessar), SEM concessão default — admin concede explicitamente (padrão 030) (decisão Q4, 2026-09-23).
- Q: O campo de processo 1Doc aparece em quais telas de movimentação? → A: Somente nas telas dos tipos elegíveis (cautela e transferência de local); devolução e demais tipos nem veem o campo (decisão Q5, 2026-09-23).

## 2. Escopo

### Incluído

- Campo para informar o **processo 1Doc** no ato da movimentação (obrigatório quando a integração estiver ativa para o tipo de movimentação).
- Inclusão automática de **comunicação no processo 1Doc existente** após a conclusão da movimentação.
- Geração automática do conteúdo (mensagem + tabela) a partir dos **dados oficiais da movimentação** registrada.
- **Registro do estado da integração** (vínculo movimentação ↔ processo ↔ mensagem 1Doc), com histórico de tentativas.
- Tratamento de falhas: registro, **retry** para erros transitórios e **reprocessamento manual** por usuário autorizado.
- **Idempotência**: nenhuma comunicação duplicada para a mesma movimentação.
- Auditoria dos eventos de integração na trilha existente.
- Configuração segura (URL, credenciais, timeout, ativação) por variáveis de ambiente.

### Não incluído (fora de escopo nesta versão)

- Criar novos processos 1Doc (o processo é **criado previamente pelo setor de Patrimônio**; o SisPatrimônio apenas o utiliza).
- Substituir ou interferir no **fluxo de assinatura** do 1Doc — a assinatura continua sendo realizada no 1Doc pelo responsável.
- Link para consultar a movimentação no SisPatrimônio a partir do 1Doc (a arquitetura apenas reserva espaço para evolução futura — **sem gerar URL agora**).
- Alterar o e-mail existente (030), as regras patrimoniais, os tipos de movimentação, o RBAC das movimentações ou qualquer tela não relacionada.
- Qualquer mecanismo que simule ou falsifique assinatura.

## 3. Estado atual da arquitetura (fatos verificados — análise somente leitura, 2026-09-23)

| # | Fato | Consequência para a integração |
|---|---|---|
| F1 | `MovementService.create_movement` é **atômico** (valida → grava → commit) e já possui **hook pós-commit best-effort** (feature 030) no ponto de não-retorno | A integração 1Doc acopla-se no mesmo ponto, **após o commit**, com captura total de exceções — impossível reverter a movimentação por falha externa |
| F2 | `requests` já é dependência do projeto (`requirements.txt`) | Cliente HTTP disponível; nenhuma dependência nova é necessária (decisão final no plan) |
| F3 | Configuração por ambiente segue o padrão `SMTP_*` (`app/config.py` + `.env`) | Credenciais 1Doc seguem o mesmo padrão (variáveis `1DOC_*` — nomes finais no plan) |
| F4 | Precedente de configuração administrativa em banco (singleton 021/030) e de tela admin com permissão própria | Avaliado no plan; nesta versão a configuração é **somente por ambiente** (seção 13) |
| F5 | `write_audit` com padrão `ACTION_*` e eventos `NOTIFICACAO_*` (030) | Eventos de integração seguem o mesmo padrão |
| F6 | `create_movement` é **unitário** (1 movimentação = 1 bem); o lote da importação CSV cria N movimentações e passa `notify=False` | 1 comunicação por movimentação; lote CSV fora do alcance (mesma decisão Q2 da 030) |
| F7 | `Movement` contém origem/destino (local e custodiante, com nomes), operador, tipo, motivo e termo | Fonte exclusiva dos dados da tabela — nenhum dado redigitado |
| F8 | A suíte pytest (617 passed) cobre movimentações e notificações; testes usam fakes, nunca serviços externos reais | Testes da integração usarão fake de API 1Doc |

**Capacidades da API 1Doc: NENHUMA presumida.** Toda a superfície externa está marcada como **A CONFIRMAR COM O FORNECEDOR 1DOC** (seção 8) e a implementação é **bloqueada** pela Fase 1 de investigação.

## 4. User Scenarios & Testing *(mandatory)*

### User Story 1 — Comunicação automática no processo 1Doc (Priority: P1)

Um usuário realiza uma movimentação elegível (**cautela ou transferência de local** — decisão Q1; devolução NÃO gera comunicação) no SisPatrimônio. Com a integração ativa, ele informa o **número do processo 1Doc** no ato da movimentação. Após a movimentação ser concluída e persistida, o sistema inclui uma nova comunicação no processo informado, com a mensagem no modelo do setor e a tabela preenchida **automaticamente** com os dados oficiais (descrição do material, tombamento, origem, destino). O responsável assina no 1Doc pelo fluxo já existente do órgão.

**Why this priority**: é o valor central — elimina a redigitação manual e garante que o processo administrativo receba exatamente os dados do registro patrimonial oficial.

**Independent Test**: com credenciais e processo válidos, concluir uma movimentação elegível e verificar que o processo 1Doc passou a conter uma comunicação com a tabela preenchida fielmente (verificável no 1Doc e no registro de integração local).

**Acceptance Scenarios**:

1. **Given** integração ativa e processo 1Doc existente, **When** o usuário conclui uma movimentação elegível informando o processo, **Then** a movimentação é gravada normalmente e uma comunicação é incluída no processo com a tabela preenchida automaticamente.
2. **Given** integração ativa, **When** o usuário conclui uma movimentação elegível **sem** informar o processo, **Then** o sistema impede a conclusão, indicando que o processo 1Doc é obrigatório.
3. **Given** integração ativa e API com suporte a consulta de processo (C-3 confirmado), **When** o usuário informa um processo inexistente, **Then** o sistema impede a conclusão na tela, indicando que o processo não foi encontrado — sem gravar a movimentação.
4. **Given** integração ativa e API **sem** suporte a consulta de processo, **When** o usuário conclui a movimentação com um número em formato válido, **Then** a movimentação é gravada e a integração é processada; processo inexistente torna-se falha registrada, recuperável por reprocessamento (modo tolerante).
5. **Given** integração **desativada**, **When** qualquer movimentação é concluída, **Then** nenhuma interação com o 1Doc ocorre e o comportamento é idêntico ao atual.

### User Story 2 — Falha do 1Doc nunca afeta a movimentação (Priority: P1)

O 1Doc está indisponível, com credencial inválida, lento ou retorna erro. A movimentação já concluída **permanece válida**; o sistema registra o estado da integração (falha/pendente), o motivo técnico (sem segredos) e emite evento de auditoria. Nada é perguntado ao usuário além do necessário.

**Why this priority**: regra obrigatória de integridade patrimonial — nenhum serviço externo pode desfazer ou bloquear a operação patrimonial (mesmo princípio da RN-001 da feature 030).

**Independent Test**: simular indisponibilidade/erro da API 1Doc (fake) e concluir uma movimentação: ela deve persistir concluída, com registro de integração em falha e evento de auditoria correspondente.

**Acceptance Scenarios**:

1. **Given** API 1Doc indisponível, **When** uma movimentação elegível é concluída, **Then** a movimentação permanece concluída e válida, e a integração fica registrada como falha/pendente para tratamento posterior.
2. **Given** timeout da API 1Doc, **When** a chamada externa excede o tempo limite configurado, **Then** a chamada é interrompida, a falha é registrada e o usuário não fica preso à espera.
3. **Given** erro de autenticação/autorização (erro permanente), **When** a integração tenta enviar, **Then** a falha é registrada **sem** retries infinitos.
4. **Given** e-mail (030) e 1Doc configurados, **When** o 1Doc falha, **Then** o e-mail já enviado/pendente não é afetado — as integrações são independentes.

### User Story 3 — Ciência, reprocessamento e idempotência (Priority: P2)

O administrador consegue identificar quais movimentações tiveram a integração falha e **reprocessar** a inclusão no 1Doc. Reprocessar não duplica comunicações: se a movimentação já foi enviada, nova tentativa reconhece o envio anterior. Eventos de reprocessamento são auditados.

**Why this priority**: dá operacionalidade à integração (recuperação de falhas sem duplicidade), mas depende de US1/US2 existirem.

**Independent Test**: provocar falha, reprocessar por usuário autorizado e verificar recuperação com **uma única** comunicação no processo; tentar reprocessar uma integração já enviada e verificar que nada é reenviado.

**Acceptance Scenarios**:

1. **Given** integração em falha, **When** um usuário autorizado aciona o reprocessamento, **Then** a comunicação é enviada (se o 1Doc estiver ok), o estado é atualizado e o evento é auditado.
2. **Given** integração já enviada, **When** qualquer nova tentativa (retry automático, reprocessamento ou repetição de requisição) ocorre, **Then** nenhuma comunicação duplicada é criada no processo.
3. **Given** usuário sem a permissão dedicada de reprocessamento, **When** tenta reprocessar, **Then** o acesso é negado (403) — inclusive para administradores até que a permissão lhes seja concedida (padrão 030: nenhuma permissão nova é concedida automaticamente).

### Edge Cases

- Processo 1Doc informado com espaços/formatos variados → normalização do identificador (trim; formato válido conforme convenção do órgão — definir no plan).
- API responde sucesso mas sem identificador de mensagem → registrar a integração como **enviada**, com identificador "desconhecido" (decisão Q3): a comunicação chegou ao processo; apenas o ID externo fica sem rastreio — nunca reenviar por causa de ID ausente (evitaria duplicidade).
- Múltiplas movimentações rápidas para o mesmo processo → cada movimentação gera sua comunicação; idempotência é por **movimentação**, não por processo.
- Movimentação elegível criada por caminhos sem interface (API/CLI) → mesmo comportamento de integração (o processo deve ser informável por todos os caminhos que criam movimentação elegível, quando a integração estiver ativa).
- Tipos não elegíveis (devolução, manutenções, baixa, ajustes, aquisição) → sem campo na interface e sem interação com o 1Doc, mesmo com a integração ativa (Q1/Q5).
- API do 1Doc alterada/atualizada pelo fornecedor → falhas passam a ser registradas; superfície externa isolada atrás de um único ponto de integração (sem espalhar chamadas pelo código).

## 5. Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir informar o **número do processo 1Doc** no ato da movimentação, em todos os caminhos que criam movimentação elegível (web e API), quando a integração estiver ativa. Na interface, o campo aparece **somente** nos formulários dos tipos elegíveis (cautela e transferência — decisão Q5); devolução e demais tipos não exibem o campo.
- **FR-002**: O processo 1Doc MUST ser **obrigatório** para movimentações elegíveis quando a integração estiver ativa; a ausência impede a conclusão, com mensagem clara (sem expor detalhes técnicos).
- **FR-003**: O sistema MUST solicitar a inclusão da comunicação **somente após** a movimentação estar concluída e persistida (pós-commit), **sem manter a transação patrimonial aberta** durante a chamada externa.
- **FR-004**: A comunicação MUST seguir o **modelo do setor de Patrimônio**: saudação seguida da tabela com as colunas **Descrição do Material, Tombamento, Origem, Destino**, preenchida exclusivamente com dados do registro patrimonial oficial (bem + movimentação).
- **FR-005**: O usuário MUST **não precisar redigitar** no 1Doc os dados da movimentação — todo o conteúdo é gerado pelo sistema.
- **FR-006**: A integração MUST alcançar **somente dois tipos de movimentação**: `ALOCACAO_CAUTELA` e `TRANSFERENCIA_LOCAL` (decisão Q1 — devolução ao estoque, manutenções, baixa, ajustes e aquisição NÃO geram comunicação no 1Doc). Tipos fora do alcance não geram nenhuma interação com o 1Doc.
- **FR-007**: Qualquer falha externa (indisponibilidade, timeout, erro HTTP, autenticação, rede) MUST **nunca desfazer, reverter ou alterar** a movimentação já concluída.
- **FR-008**: O sistema MUST manter **registro próprio do estado da integração** por movimentação: processo informado, estado (pendente/processando/enviado/falhou — nomes finais no padrão do projeto), tentativas, identificadores retornados pela API, data/hora de tentativa/erro/sucesso e erro técnico resumido (sem segredos).
- **FR-009**: O sistema MUST ser **idempotente**: no máximo **uma** comunicação por movimentação; retries e repetições MUST reconhecer envio anterior e não duplicar mensagens no processo.
- **FR-010**: O sistema MUST diferenciar **erros transitórios** (timeout, 5xx, conexão — permitem retry com limite) de **erros permanentes** (processo inexistente, credencial inválida, autorização, dados inválidos — não retentam); sem retries infinitos.
- **FR-011**: O sistema MUST permitir **reprocessamento manual** de integrações falhas por usuário portador de **permissão dedicada nova** (sem concessão default — administrador concede explicitamente; decisão Q4), com auditoria, idempotência e sem alterar a movimentação original.
- **FR-012**: O sistema MUST registrar em auditoria os eventos da integração (solicitada, enviada, falhou, reprocessada — nomes finais no padrão `ACTION_*` existente), permitindo responder: qual movimentação, para qual processo, quando, qual mensagem foi criada, se houve falha/reprocessamento — **nunca** registrando token, senha ou credenciais.
- **FR-013**: As chamadas ao 1Doc MUST possuir **timeout explícito** de conexão e leitura; o usuário não pode ficar preso indefinidamente à espera da API externa.
- **FR-014**: As credenciais e a URL da API MUST vir exclusivamente de **variáveis de ambiente** — nunca em código, templates, Git, logs, auditoria ou banco.
- **FR-015**: O e-mail da feature 030 MUST permanecer inalterado e **independente**: falha de uma integração não afeta a outra.
- **FR-016**: O sistema MUST **não criar** processos 1Doc e **não simular/falsificar** assinaturas; a assinatura permanece no fluxo próprio do 1Doc. Se a API permitir designar signatário/encaminhar para assinatura (A CONFIRMAR), a decisão é tomada no plan com o contrato real.
- **FR-017**: A arquitetura MUST permitir, futuramente, associar à comunicação uma **URL de consulta da movimentação** sem reestruturar a integração (espaço reservado no modelo; **sem gerar URL nesta versão**).
- **FR-018**: O sistema MUST registrar claramente o **resultado da integração** para ciência administrativa (estado consultável pela trilha de auditoria e por tela administrativa **mínima** de listagem — meio de execução do FR-011, não painel de monitoramento; alinhamento do analyze I1).
- **FR-019**: A validação da **existência do processo** segue decisão Q2: se a API suportar consulta (C-3 confirmado no plan), o sistema MUST validar **antes** de gravar a movimentação — processo inexistente impede a conclusão na tela; se a API NÃO suportar consulta, o sistema aceita o número informado (modo tolerante) e o resultado do envio é registrado — processo inexistente vira falha recuperável por reprocessamento.

### Key Entities

- **Registro de Integração 1Doc** (novo): vínculo **movimentação ↔ processo 1Doc**; estado da integração; número do processo; identificadores retornados pela API (ex.: id da mensagem criada); contagem de tentativas; datas de tentativa/último erro/sucesso; erro técnico resumido; espaço reservado para URL futura. Uma movimentação elegível possui **no máximo um** registro (idempotência estrutural).
- **Movimentação** (existente): fonte oficial e exclusiva dos dados (bem, tombamento, origem, destino, operador, tipo, motivo, termo). **Nenhum campo novo obrigatório na movimentação** — o processo 1Doc vive no registro de integração (decisão final de modelagem no plan).
- **Configuração 1Doc** (nova, por ambiente): URL da API, credencial/token, timeout de conexão/leitura, ativação da integração, tipos elegíveis e limites de retry — nomes finais no padrão do projeto (plan).

## 6. Ordem das operações (fluxo obrigatório)

```text
1. Usuário inicia movimentação no SisPatrimônio
2. Regras patrimoniais existentes são validadas (inalteradas)
3. Movimentação gravada
4. Transação patrimonial CONFIRMADA (ponto de não-retorno)
5. E-mail existente (030) processado (best-effort, inalterado)
6. Integração 1Doc processada (best-effort, independente)
7. Resultado da integração registrado (estado + auditoria)
8. Responsável assina no 1Doc pelo fluxo já existente do órgão
```

**PROIBIDO**: chamar a API 1Doc dentro da transação principal (`BEGIN → grava → chama API → COMMIT`). A chamada externa ocorre sempre **após** o commit patrimonial.

## 7. Responsabilidades de cada sistema

| Sistema | Responsabilidades |
|---|---|
| **SisPatrimônio Pro** | Selecionar o patrimônio; identificar origem/destino/responsável; validar regras patrimoniais; executar e persistir a movimentação; manter histórico e auditoria; disparar o e-mail existente; solicitar a inclusão da comunicação no processo 1Doc; registrar o resultado da integração |
| **1Doc** | Manter o processo criado pelo Patrimônio; receber a nova comunicação; manter a informação no processo; executar o fluxo de assinatura/aprovação já utilizado pelo órgão |

O SisPatrimônio **não substitui** o processo administrativo do 1Doc — apenas o alimenta com a comunicação da movimentação.

## 8. Investigação obrigatória da API 1Doc — FASE 1 BLOQUEANTE

**Nenhum endpoint, método ou formato de payload pode ser inventado.** Antes de qualquer implementação, a Fase 1 (no `/speckit-plan` → `research.md`) deve documentar o contrato **real** disponibilizado ao IPMJP, obtido junto ao fornecedor/administrador do 1Doc. Cada item abaixo permanece **A CONFIRMAR COM O FORNECEDOR 1DOC** até evidenciado:

| # | Capacidade | O que documentar (Operação · Endpoint · Método · Autenticação · Request · Response · Erros) |
|---|---|---|
| C-1 | **Autenticação** | método (token/API key/OAuth), validade, renovação, armazenamento seguro |
| C-2 | **Processos** | localizar/consultar/validar processo pelo identificador; obter id interno |
| C-3 | **Validação de processo** | a API permite confirmar existência antes do envio? |
| C-4 | **Comunicações/mensagens** | adicionar comunicação ao processo; formatos aceitos (texto/HTML/tabela/modelos); anexos; id da mensagem criada |
| C-5 | **Assinatura** | solicitar assinatura / designar signatário / consultar status — se não suportado, permanece manual no 1Doc (documentar a limitação) |
| C-6 | **Idempotência da API** | mecanismo nativo de chave de idempotência, se houver |
| C-7 | **Erros e limites** | códigos de erro, rate limits, comportamento em duplicidade |
| C-8 | **Ambiente** | URL/credenciais de homologação ou produção; restrições de rede do IPMJP |

**Regra**: a implementação (Fase 3) só avança com os itens C-1 a C-4 confirmados; C-5/C-6 são desejáveis e condicionam decisões do plan. Se a documentação não estiver disponível publicamente, prever obtenção junto ao fornecedor **antes** do `/speckit-tasks`.

## 9. Modelo da comunicação (conteúdo no 1Doc)

Conteúdo gerado **exclusivamente** dos dados oficiais da movimentação:

- **Saudação** — conforme horário do envio (Bom dia!/Boa tarde!/Boa noite!) — ver P-2.
- **Tabela** (modelo do setor, colunas fixas):

| Coluna | Fonte no SisPatrimônio |
|---|---|
| Descrição do Material | nome/identificação do bem |
| Tombamento | tag do bem |
| Origem | local de origem da movimentação |
| Destino | local de destino da movimentação |

- Formato de renderização (texto/HTML/tabela) conforme o que a API do 1Doc aceitar (C-4) — fiel ao modelo visual do setor.
- **Sem link** para o SisPatrimônio nesta versão (FR-017).
- Informações adicionais (custodiante, termo, motivo) **não entram** no modelo padrão — eventuais acréscimos são decisão do setor (ver P-1).

## 10. Tratamento de falhas, retry e reprocessamento

- **Falha → registro** (FR-008) + auditoria (FR-012); movimentação intocada (FR-007).
- **Transitórios** → retry com limite configurável e intervalo mínimo; nunca em loop infinito; o processamento pós-commit desta versão é single-shot com registro — o retry automático efetivo entra conforme decisão do plan (ver P-5), garantido o reprocessamento **manual** (FR-011) como caminho de recuperação.
- **Permanentes** → estado final de falha, sem novas tentativas automáticas; correção depende de ação administrativa (ex.: processo corrigido) + reprocessamento manual.
- **Reprocessamento manual** → RBAC próprio, auditado, idempotente (FR-009/FR-011).

## 11. Auditoria

Eventos no padrão existente (nomes finais no plan), por exemplo: `INTEGRACAO_1DOC_SOLICITADA`, `INTEGRACAO_1DOC_ENVIADA`, `INTEGRACAO_1DOC_FALHOU`, `INTEGRACAO_1DOC_REPROCESSADA`. A trilha responde: qual movimentação, para qual processo, quando, qual mensagem foi criada, se houve falha/reprocessamento — **sem** token, senha, API key ou conteúdo sensível. Ator dos eventos automáticos = serviço (`user=None`, precedente 020/030); reprocessamento manual identifica o usuário.

## 12. Segurança

- Credenciais **somente** em variáveis de ambiente (padrão `1DOC_*` — nomes finais no plan); proibidas em código, templates, Git, logs, auditoria, banco.
- Sanitização de erros da API: mensagens nunca ecoam credenciais (precedente `_sanitize_error_message` da 030).
- Usuário comum não altera URL/credenciais/configurações da integração (RBAC existente; movimentação continua obedecendo às permissões atuais — nenhum RBAC novo além do acesso ao reprocessamento).
- O processo informado nunca vem de fonte não confiável: é digitado pelo operador autenticado no ato da movimentação e validado conforme Q2/C-3.
- Reprocessamento exige permissão dedicada nova, sem concessão default (Q4) — coerente com deny by default (Constitution VI).

## 13. Configuração (decisão da versão)

Configuração **somente por variáveis de ambiente** nesta versão (ativação, URL, credencial, timeout, tipos elegíveis, limites de retry) — alternativa mais simples e segura, coerente com o padrão `SMTP_*` da 030 e com "alterar somente o necessário". Tela administrativa própria fica como evolução futura (P-4); nada de configuração duplicada entre `.env`, banco e código.

## 14. Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das movimentações elegíveis com processo informado geram registro de integração com resultado determinado (enviado ou falha registrada) — nenhuma fica sem estado.
- **SC-002**: **0** movimentações revertidas, alteradas ou bloqueadas por falha do 1Doc (verificável por testes e auditoria).
- **SC-003**: **0** comunicações duplicadas para a mesma movimentação (verificável por testes de idempotência).
- **SC-004**: A resposta da movimentação ao usuário não é atrasada além do timeout configurado (verificável por teste com fake lento).
- **SC-005**: **0** ocorrências de credenciais/segredos em logs, auditoria, respostas e repositório (verificação automatizada no padrão T024 da 030).
- **SC-006**: 100% de fidelidade entre os dados da tabela enviada e o registro patrimonial (verificação por teste comparando conteúdo gerado × movimentação).
- **SC-007**: Suíte de regressão existente permanece verde; novos testes cobrem os cenários da seção 4.
- **SC-008**: O setor de Patrimônio reconhece o conteúdo recebido no 1Doc como equivalente ao modelo manual atual (validação com a tabela do setor em ambiente controlado).

## 15. Assumptions

- O processo 1Doc **já existe** e é criado/mantido pelo setor de Patrimônio; o sistema apenas referencia e o alimenta.
- As credenciais e a URL da API do 1Doc serão fornecidas ao projeto **antes** da implementação (Fase 1 — C-1/C-8); sem elas, a feature não sai da fase de investigação.
- Um movimento = um bem (arquitetura atual) → **uma comunicação por movimentação**, tabela com uma linha (P-3 consolida o cenário de múltiplos equipamentos).
- O lote da importação CSV **não** gera comunicação individual (ciência dada pelo relatório da importação — coerente com decisão Q2 da 030).
- Tipos elegíveis = **cautela e transferência de local** (decisão Q1 — conjunto MENOR que o do e-mail da 030).
- Processamento **pós-commit síncrono com timeout curto** nesta versão (padrão da 030); evolução para worker/fila é prevista pela arquitetura de estados sem redesenho (P-5).
- A assinatura continua manual no 1Doc, salvo se C-5 confirmar designação de signatário e o plan decidir usá-la.

## 16. Pendências de decisão

**A confirmar com o fornecedor 1Doc (externas — Fase 1 bloqueante)**: C-1 a C-8 (seção 8).

**Decisões com default proposto (resolvíveis no `/speckit-clarify`)**:

| # | Pendência | Default proposto |
|---|---|---|
| P-1 | Colunas adicionais na tabela (ex.: custodiante) | Manter o modelo exato de 4 colunas do setor |
| P-2 | Saudação | Conforme horário do envio |
| P-3 | Tipos elegíveis e múltiplos equipamentos | **RESOLVIDA (Q1)**: cautela + transferência de local; 1 comunicação por movimentação (uma linha); lote CSV fora |
| P-4 | Configuração por ambiente vs tela admin | Somente ambiente nesta versão |
| P-5 | Execução: pós-commit síncrono vs worker/fila | Pós-commit síncrono com timeout curto (padrão 030); retry automático efetivo e worker como evolução |
| P-6 | Nome final do registro/entidade e eventos de auditoria | Padrão do projeto, definido no plan |
