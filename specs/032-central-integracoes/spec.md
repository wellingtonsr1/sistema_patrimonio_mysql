# Feature Specification: Central de Integrações — Gerenciamento e Observabilidade

**Feature Branch**: `032-central-integracoes`

**Created**: 2026-09-23

**Status**: Draft

**Input**: Criar uma Central de Integrações no SisPatrimônio Pro, acessível somente a usuários autorizados, que permita visualizar, configurar, testar, monitorar e acompanhar o estado das integrações (E-mail, 1Doc, GLPI, Active Directory) em um único local. A Central é uma **camada de gerenciamento e observabilidade sobre o que já existe** — NÃO reimplementa as integrações existentes e NÃO inventa APIs/endpoints de serviços externos. Deve ser preparada para crescer sem alteração estrutural do sistema a cada nova integração. Princípio: "mudança mínima necessária, sem quebrar funcionalidades existentes".

---

## 1. Objetivo

Dar ao administrador do SisPatrimônio Pro **um único ponto** para responder, sem precisar navegar por vários menus ou consultar logs manualmente:

- Quais integrações o sistema possui e qual o estado real de cada uma?
- O e-mail está saindo? O 1Doc está recebendo as comunicações? O AD está alcançável?
- Qual integração está com problema, **desde quando**, quantas operações foram afetadas e qual foi o último erro?
- Existem operações pendentes que precisam de reprocessamento?
- A conexão com um serviço externo está funcionando **agora**?

Hoje essas respostas estão espalhadas entre três telas administrativas (Notificações, Integração 1Doc, Integração AD), a trilha de auditoria e o próprio banco. A Central as reúne, padroniza o vocabulário de status e cria a estrutura pela qual **futuras integrações** (GLPI e outras) aparecem automaticamente — mesmo quando ainda não implementadas, como "aguardando configuração/fornecedor".

**A Central não executa nada do negócio das integrações**: não envia e-mail, não fala com o 1Doc, não autentica no AD, não sincroniza com o GLPI. Ela **observa e administra** quem já faz isso.

## Clarifications

### Session 2026-09-23 (P-1..P-6 — ver também Seção 21)

> Integrada nas seções 9, 11, 15, FR-011, FR-013, Edge Cases e Pendências. Pendências de decisão restantes: apenas P-7 (nomes finais — detalhe de plan).

- Q: Como o histórico unificado de execuções da Central deve ser persistido? → A: Tabela unificada nova (aditiva), alimentada pelos pontos de execução já existentes (hooks 030/031 e testes da Central); o estado das integrações permanece nas tabelas atuais, sem duplicação de verdade (decisão P-1, 2026-09-23).
- Q: A Central de Integrações deve ter permissões próprias além das permissões existentes de cada integração? → A: Sim — criar `integracoes.visualizar` (painel, detalhes, histórico, propagação) e `integracoes.testar` (teste de conexão nas integrações sem guarda dedicada), ambas SEM concessão default, com Administrador recebendo via catálogo; as permissões/guardas existentes (`integracao1doc.reprocessar`, guarda do AD, `notificacoes.gerenciar`) continuam governando as ações específicas (decisão P-2, 2026-09-23).
- Q: Quem deve poder executar o "Testar conexão" em cada integração? → A: Cada integração mantém sua autorização vigente: AD usa a guarda existente da tela AD (`usuarios.editar` + `perfis.editar`); e-mail e 1Doc usam `integracoes.testar`; GLPI não oferece teste enquanto "Não configurada" (decisão P-3, 2026-09-23).
- Q: Como a contagem de "falhas recentes" exibida nos cards deve ser calculada e comunicada? → A: Janela fixa de 24 horas, explicitada na interface (ex.: "Falhas recentes (24h): 2"); o histórico completo continua consultável além da janela (decisão P-4, 2026-09-23).
- Q: O "Testar conexão" do e-mail deve enviar uma mensagem de teste de verdade, ou apenas verificar conexão e autenticação SMTP? → A: Apenas conexão e autenticação SMTP (handshake + login, sem envio de mensagem): mantém o teste 100% não destrutivo (FR-011); envio de mensagem de teste fica como evolução futura opcional (decisão P-6, 2026-09-23).

## 2. Princípio arquitetural

O SisPatrimônio Pro é o sistema central das informações patrimoniais. As integrações permanecem **independentes entre si** e acopladas apenas ao SisPatrimônio:

```
SisPatrimônio Pro
    |
    +---- E-mail          (feature 030 — existente)
    +---- 1Doc            (feature 031 — implementada, aguardando fornecedor)
    +---- GLPI            (prevista — não implementada)
    +---- Active Directory (existente)
    +---- futuras integrações
```

- **Nenhuma integração fala com outra**: 1Doc ↔ GLPI, GLPI ↔ AD, E-mail ↔ GLPI são proibidos. Quando uma integração precisar de informação patrimonial, recebe-a do SisPatrimônio.
- A Central é mais um "consumidor" do estado das integrações — não cria um caminho paralelo de execução nem um barramento novo.
- Nenhum código de aplicação pode ficar cheio de `if integracao == "glpi"`: a Central consome um **catálogo/registro de integrações** e cada integração se apresenta ao catálogo com seus próprios meios (status, teste, histórico, configuração). Cada integração implementa **apenas o que realmente suporta** — abstração simples, sem sobre-engenharia.

## 3. Estado atual da arquitetura (fatos verificados — análise somente leitura, 2026-09-23)

| # | Fato | Consequência para a Central |
|---|---|---|
| F1 | **E-mail (030)**: `notification_service` + `email_provider` (SMTP isolado atrás de protocolo próprio), singleton `email_config` (ativação + destinatários), credenciais SMTP **somente em ambiente** (`SMTP_*`), estados `PENDING/SENT/FAILED` com UNIQUE em `movement_id` | Estado e histórico do e-mail já existem e são a fonte da verdade; a Central apenas os reapresenta |
| F2 | **1Doc (031)**: `onedoc_service` + `onedoc_client` (protocolo próprio, `[PENDING C-1..C-4]` — **nenhum endpoint inventado**), modelo `OneDocIntegration` (PENDING/SENT/FAILED, tentativas, erro sanitizado), `ONEDOC_ENABLED=false` por padrão, tela admin mínima com reprocessamento (`integracao1doc.reprocessar`) | A 031 tem ciclo de vida completo (envio/falha/retry/reprocesso); a Central agrega seu estado e reaproveita o reprocessamento existente |
| F3 | **AD**: `ad_service` + `ad_ldap`, singleton `ad_settings` (conexão, provisionamento, `enabled`), fallback por ambiente (`AD_*`), senha **nunca persistida** (bind direto do usuário), tela `/admin/ad` com guarda própria (`usuarios.editar` + `perfis.editar`) e teste de conexão auditado (`TESTE_CONEXAO_AD`) | AD já possui diagnóstico e teste; a Central reapresenta e linka — não duplica a guarda nem a tela |
| F4 | **GLPI**: **não existe** no código (nenhum service, modelo ou configuração) | GLPI entra no catálogo como integração **prevista** ("Não configurada"); nada é inventado |
| F5 | **RBAC**: catálogo `PERMISSION_CATALOG` (padrão `modulo.acao`), deny by default, `require_permission`, `User.is_admin` como bypass auditado; permissões recentes seguem o padrão "sem concessão default" (`notificacoes.gerenciar`, `integracao1doc.reprocessar`) | Novas permissões da Central seguem o mesmo padrão; nenhuma autorização paralela é criada |
| F6 | **Auditoria**: trilha `audit_logs` imutável via `write_audit`/`write_change_audit`, constantes `ACTION_*` + rótulos, módulos por tema (`integracao_1doc`, eventos `NOTIFICACAO_*`, `*_AD_*`, `BACKUP_*`) | Ações da Central registram eventos `ACTION_*` novos (aditivos) na trilha existente, sempre sem credenciais |
| F7 | **Configuração**: padrão estabelecido = variáveis de ambiente (bootstrap) + singletons administráveis (`ad_settings`, `email_config`, `backup_config`) com precedência persistido → env → default | A Central **não duplica** configurações; aponta/reaproveita as estruturas existentes |
| F8 | **Movimentações**: `create_movement` é atômico e possui hook pós-commit best-effort (030: e-mail → 1Doc); falha externa **nunca** reverte a movimentação | A Central observa esse fluxo; não altera o motor de movimentações nem a regra de transação |
| F9 | **Idempotência estrutural**: UNIQUE `movement_id` em `notifications` e `onedoc_integrations` | Padrão obrigatório para futuras integrações; a Central não o altera |
| F10 | **Testes**: suíte pytest com fakes — nunca serviços externos reais (`test_onedoc.py`, `test_notificacoes.py`, `test_ad.py`, `test_rbac.py`) | Testes da Central usam fakes de integração; suíte existente deve permanecer verde |
| F11 | **UI**: Jinja2 + Bootstrap 5, tema claro/escuro, `active_tab="admin"`, menu conforme permissões, 403/404 amigáveis, fuso do operador (convenção 004) | Telas da Central seguem o padrão visual existente — nenhuma interface paralela |
| F12 | A tela 1Doc (031) é deliberadamente **mínima** ("veículo de execução do reprocessamento, não painel de monitoramento") | A Central é a camada de observabilidade que faltava — sem reescrever a tela mínima existente |

## 4. Escopo

### Incluído

- Área **Administração → Central de Integrações** com painel (cards) das integrações do catálogo: E-mail, 1Doc, GLPI, Active Directory.
- **Modelo de status padronizado** (Seção 7) derivado do estado real de cada integração.
- Página de **detalhe/diagnóstico** por integração (contadores, últimas execuções, último erro sanitizado, configuração relevante com segredos mascarados, ações disponíveis).
- Ação **"Testar conexão"** por integração que suporte, segura, não destrutiva, auditada.
- **Histórico de execuções** por integração com filtros (período, status, tipo de operação, usuário quando aplicável).
- **Classificação de erros** e apresentação amigável, sem exposição de segredos.
- **Visão de propagação por movimentação**: quais integrações receberam (ou pendem) os eventos de uma movimentação — somente leitura.
- **Reprocessamento** reaproveitando os mecanismos existentes (ex.: 1Doc) — nada de retry infinito.
- **Habilitar/desabilitar** somente pelos mecanismos já existentes de cada integração (a Central não cria um novo interruptor paralelo).
- **Auditoria** de todas as ações administrativas da Central.
- Catálogo de integrações **extensível**: adicionar uma nova integração não exige reestruturar a Central.
- Estrutura aditiva de persistência para o histórico unificado de execuções (decisão final no plan — P-1).

### Não incluído (fora de escopo nesta versão)

- **Reimplementar** qualquer integração existente (e-mail, AD, 1Doc) — nem parcialmente.
- **Inventar** endpoints, payloads ou campos da API do 1Doc ou do GLPI (Seção 18).
- **GLPI**: criação automática de equipamentos; sincronização efetiva (aguarda investigação da instalação real — Seção 18). Nesta etapa GLPI é apenas **representado** no catálogo.
- **Alertas automáticos** aos administradores ("GLPI indisponível há 30 min") — avaliado e **adiado** (P-5), com requisitos registrados para evolução futura.
- Alterar regras patrimoniais, o motor de movimentações, o comportamento do backup, as regras do AD ou do e-mail.
- Nova forma de autorização (a Central reusa o RBAC existente).
- Notificações externas adicionais (canais novos além do e-mail existente).
- Configuração nova de credenciais administrável pela Central nesta versão (credenciais permanecem em ambiente, padrão atual).

## 5. User Scenarios & Testing *(mandatory)*

### User Story 1 — Painel com o estado real das integrações (Priority: P1)

Um administrador abre **Administração → Central de Integrações** e vê um card por integração (E-mail, 1Doc, GLPI, Active Directory) com: status padronizado, última execução, último sucesso, falhas recentes e quantidade de operações pendentes. De relance ele sabe que o e-mail está ativo, que o 1Doc aguarda o fornecedor ("Pendente de configuração"), que o GLPI ainda não existe ("Não configurada") e que o AD está ativo.

**Why this priority**: é o valor central da Central — observabilidade em um único lugar, sem navegar por três telas e sem consultar o banco.

**Independent Test**: com as integrações em estados conhecidos (configurados por fixtures/fakes), a tela apresenta os status corretos para cada uma — testável isoladamente das demais histórias.

**Acceptance Scenarios**:

1. **Given** e-mail com SMTP configurado e notificações habilitadas, **When** o administrador abre a Central, **Then** o card E-mail exibe status ATIVA com data/hora da última execução e do último sucesso.
2. **Given** 1Doc com `ONEDOC_ENABLED=false` e contrato ainda não confirmado pelo fornecedor, **When** o administrador abre a Central, **Then** o card 1Doc exibe status PENDENTE ("aguardando informações do fornecedor") com última execução "—".
3. **Given** GLPI sem qualquer implementação, **When** o administrador abre a Central, **Then** o card GLPI exibe status NÃO CONFIGURADA e nenhuma ação de teste é oferecida.
4. **Given** AD habilitado com falha de comunicação registrada no teste mais recente, **When** o administrador abre a Central, **Then** o card AD exibe status COM ERRO ou INDISPONÍVEL com a data/hora da última falha.
5. **Given** qualquer integração com operações `PENDING` (ex.: comunicações 1Doc pendentes), **When** o administrador abre a Central, **Then** o card correspondente exibe a quantidade de operações pendentes.

---

### User Story 2 — Acesso restrito e segredos protegidos (Priority: P1)

Somente usuários com permissão administrativa apropriada acessam a Central e suas rotas; todos os demais recebem a negação padrão do sistema. Em **nenhum** ponto da interface, logs, auditoria ou mensagens de erro aparece uma credencial em texto puro — segredos são mascarados (ex.: `************ABCD` ou "Token configurado.").

**Why this priority**: a Central concentra informação sensível sobre todas as integrações; sem a garantia de acesso e de não-exposição ela não pode existir.

**Independent Test**: com um usuário sem permissão, todas as rotas da Central negam acesso; com um usuário autorizado, varre-se a renderização (e os eventos de auditoria) confirmando ausência de valores de credenciais — testável sem as demais histórias.

**Acceptance Scenarios**:

1. **Given** usuário autenticado sem permissão de visualizar integrações, **When** acessa qualquer rota da Central, **Then** recebe a negação padrão (403 amigável) e o acesso negado é auditado.
2. **Given** usuário autorizado e integração com token configurado, **When** visualiza o detalhe da integração, **Then** o token aparece mascarado/indicado como configurado, nunca o valor completo.
3. **Given** falha de autenticação com serviço externo, **When** a mensagem de erro é exibida ou auditada, **Then** aparece "Falha de autenticação na integração com o [serviço]" — sem token, senha, URL com credencial ou segredo do ambiente.
4. **Given** formulário de configuração que envolve segredo (via tela existente), **When** o administrador opta por manter o segredo atual, **Then** o valor existente é preservado sem nunca ser exibido.

---

### User Story 3 — Teste de conexão auditado e não destrutivo (Priority: P2)

O administrador executa "Testar conexão" em uma integração que suporte teste (ex.: AD — mecanismo existente; e-mail — verificação de disponibilidade/autenticação SMTP). O teste verifica disponibilidade e autenticação (e permissões mínimas quando possível), não cria/altera/exclui nada no sistema externo, apresenta resultado amigável e fica registrado no histórico e na auditoria.

**Why this priority**: é a ação administrativa mais frequente ao diagnosticar "o problema é aqui ou lá?" — mas depende do painel (US1) para fazer sentido operacionalmente.

**Independent Test**: com fakes de provedor (sucesso, timeout, erro de autenticação, indisponibilidade), o teste produz o resultado correto, registra histórico e auditoria — testável por integração, sem as demais histórias.

**Acceptance Scenarios**:

1. **Given** integração com serviço externo saudável (fake), **When** o administrador executa o teste, **Then** o resultado apresentado é positivo, com latência e data/hora, e o evento é registrado na auditoria.
2. **Given** serviço externo que rejeita a credencial (fake), **When** o teste é executado, **Then** o resultado classifica a falha como "autenticação" com mensagem amigável — sem segredo — e registra a falha.
3. **Given** serviço externo inalcançável (fake de timeout), **When** o teste é executado, **Then** o teste respeita um prazo máximo, classifica como indisponibilidade/temporário e registra o resultado.
4. **Given** qualquer teste, **When** o teste conclui (sucesso ou falha), **Then** nenhum dado foi criado, alterado ou excluído no sistema externo e nenhum dado patrimonial foi modificado.

---

### User Story 4 — Histórico de execuções e diagnóstico por integração (Priority: P2)

O administrador abre o detalhe de uma integração e consulta o histórico de execuções (data/hora, operação, resultado, duração, detalhes sanitizados) com filtros por período, status e tipo de operação — e vê contadores: operações realizadas, com erro, pendentes, última execução/sucesso/falha.

**Why this priority**: transforma "acho que o e-mail falhou ontem" em resposta verificável; sustenta a observabilidade contínua após o primeiro dia.

**Independent Test**: com execuções de teste semeadas (estados variados), os filtros e contadores retornam exatamente os registros esperados — testável isoladamente.

**Acceptance Scenarios**:

1. **Given** execuções de e-mail e 1Doc registradas, **When** o administrador filtra o histórico por integração e status "falha", **Then** somente as execuções com falha da integração escolhida são exibidas.
2. **Given** execução com erro técnico contendo credencial no texto original (fake), **When** o histórico é consultado, **Then** o detalhe exibe apenas o erro sanitizado/classificado.
3. **Given** integração sem nenhuma execução registrada, **When** o administrador abre o histórico, **Then** a lista vazia é apresentada de forma amigável ("—"), sem erro.
4. **Given** volume grande de execuções, **When** o administrador consulta o histórico, **Then** a consulta é paginada/limitada e permanece responsiva.

---

### User Story 5 — Acompanhamento da propagação de movimentações (Priority: P2)

Ao investigar a movimentação #1542, o administrador identifica em um só lugar: a movimentação foi concluída no SisPatrimônio; o e-mail foi enviado; a comunicação 1Doc está pendente; GLPI — não aplicável. Ele sabe exatamente **o que precisa de ação** (reprocessar o 1Doc pela via existente).

**Why this priority**: conecta a Central ao fluxo de negócio real (movimentações), respondendo "essa movimentação foi corretamente propagada aos sistemas externos?" — sem alterar a regra patrimonial.

**Independent Test**: com movimentações em estados conhecidos de e-mail/1Doc (fixtures), a visão exibe o estado correto por integração — testável isoladamente.

**Acceptance Scenarios**:

1. **Given** movimentação concluída com e-mail SENT e 1Doc PENDING, **When** o administrador consulta a propagação da movimentação, **Then** os estados por integração são exibidos (✓ enviado / ⚠ pendente / — não aplicável).
2. **Given** movimentação anterior à existência das integrações (sem registros), **When** consultada, **Then** as integrações aparecem como não aplicável/"—", sem erro.
3. **Given** movimentação com 1Doc FAILED, **When** o administrador aciona o reprocessamento pela via existente, **Then** o resultado atualiza o estado exibido e a movimentação em si permanece intocada.

---

### User Story 6 — Administração: habilitar/desabilitar e acessar configurações (Priority: P3)

Do card/detalhe da integração, o administrador é conduzido à configuração existente de cada integração (Notificações → e-mail; Integração AD; Integração 1Doc) e pode habilitar/desabilitar a integração **quando existir mecanismo já previsto** (ex.: `enabled` do AD, ativação das notificações) — sempre pelas telas/mecanismos existentes, com auditoria.

**Why this priority**: conveniência administrativa; os mecanismos já existem — a Central apenas os organiza. O painel (US1) entrega valor mesmo sem esta história.

**Independent Test**: os atalhos respeitam as permissões específicas de cada tela de destino (ex.: guarda do AD) e as ações de habilitar/desabilitar são auditadas — testável isoladamente.

**Acceptance Scenarios**:

1. **Given** integração com mecanismo de habilitação existente, **When** o administrador com a permissão correspondente desabilita a integração, **Then** o status reflete DESABILITADA e a ação é auditada.
2. **Given** usuário sem a permissão específica da tela de configuração de destino, **When** tenta acessá-la a partir da Central, **Then** a negação da tela existente prevalece (nenhuma autorização paralela é criada).
3. **Given** integração sem mecanismo de habilitação pela interface (ex.: 1Doc via ambiente nesta versão), **When** o administrador visualiza o detalhe, **Then** a Central indica onde/como a ativação acontece, sem criar interruptor novo.

### Edge Cases

- **Integração recém-ativada sem execuções**: exibir "—" (sem erro, sem dado) — ausência de execução não é falha.
- **Falha do próprio mecanismo de coleta da Central**: o restante da administração continua funcionando; o card afetado mostra o último estado conhecido e mensagem interna sanitizada — sem estado novo no modelo de status.
- **Teste executado com integração desabilitada**: o teste permanece disponível para diagnóstico (resultado registra a condição), mas não reabilita nada sozinho.
- **Segredo alterado no ambiente** (fora da interface): a Central reflete a origem da configuração efetiva (ambiente/banco) sem revelar valor.
- **Movimentação antiga/sem integração**: coluna "—" na propagação; nada é retroagido.
- **Horários**: exibidos no fuso do operador (convenção 004), armazenados em UTC.
- **Concorrência de administração**: duas alterações simultâneas de configuração seguem o padrão existente (última gravação vence, ambas auditadas).
- **Contagem de "falhas recentes"**: janela fixa de **24 horas** (aprovado no clarify, P-4), explicitada na interface do card ("Falhas recentes (24h): N"); integrações de baixo volume sem execuções na janela exibem a última falha conhecida no detalhe — o histórico completo permanece consultável.

## 6. Requirements *(mandatory)*

### Functional Requirements

**Acesso e permissões**

- **FR-001**: O sistema MUST restringir todas as telas e ações da Central aos usuários autenticados que possuam as permissões apropriadas, pelo mecanismo de RBAC existente (deny by default) — nenhuma autorização paralela.
- **FR-002**: O menu Administração MUST exibir a entrada "Central de Integrações" somente para usuários autorizados, seguindo o padrão atual de menu por permissões.
- **FR-003**: O sistema MUST avaliar o catálogo de permissões existente antes de criar novas: as permissões específicas de cada integração (ex.: `notificacoes.gerenciar`, `integracao1doc.reprocessar`, guarda do AD) continuam governando as ações específicas — a Central não as duplica nem as contorna.

**Painel e catálogo**

- **FR-004**: O sistema MUST apresentar um card por integração do catálogo, contendo no mínimo: nome, status padronizado, última execução, último sucesso, falhas recentes e operações pendentes.
- **FR-005**: O sistema MUST manter um catálogo/registro de integrações extensível: adicionar uma nova integração ao painel não deve exigir alteração estrutural da Central (novos sistemas, contábeis, compras, contratos, APIs internas, webhooks).
- **FR-006**: O sistema MUST derivar o status exibido do **estado real** das integrações (configuração efetiva + registros existentes + verificações) — o status não é editável livremente nem uma verdade independente.
- **FR-007**: O painel MUST permitir identificar rapidamente (observabilidade): qual integração está com problema, desde quando, quantas operações foram afetadas, qual o último erro, se houve sucesso anterior, se existe operação pendente e quando ocorreu a última tentativa.

**Detalhe e diagnóstico**

- **FR-008**: A página de detalhe MUST apresentar: nome, descrição, finalidade, status atual, última execução, último sucesso, última falha, operações realizadas, com erro e pendentes, configuração relevante (quando aplicável) e ações disponíveis.
- **FR-009**: O diagnóstico MUST diferenciar, quando a integração permitir verificar: **configurada**, **disponível**, **autenticada** e **operacional** (ex.: "CONFIGURADA: Sim / DISPONIBILIDADE: Sim / AUTENTICAÇÃO: Falhou / STATUS: COM ERRO").
- **FR-010**: O resultado de verificação MUST ser padronizado (status, momento da verificação, latência, mensagem, detalhes) sem obrigar todas as integrações a implementarem o mesmo tipo de verificação — cada uma informa o que sua API/protocolo permite.

**Teste de conexão**

- **FR-011**: Cada integração que suportar teste MUST oferecer a ação "Testar conexão", que verifica disponibilidade e autenticação (e permissões mínimas quando possível), de forma **segura e não destrutiva** — nunca cria, altera ou exclui dados no sistema externo nem dados patrimoniais. No e-mail, o teste restringe-se a conexão e autenticação SMTP, **sem envio de mensagem** (decisão P-6); envio de e-mail de teste é evolução futura opcional.
- **FR-012**: Todo teste MUST registrar resultado no histórico e na auditoria, e apresentar mensagem amigável ao administrador.
- **FR-013**: O teste de cada integração MUST respeitar as regras de autorização vigentes dela (aprovado no clarify, P-3): teste do AD mantém a guarda existente da tela AD (`usuarios.editar` + `perfis.editar`); teste do e-mail e do 1Doc (interno, sem chamada externa enquanto o contrato não chega) exigem `integracoes.testar`; GLPI não oferece teste enquanto não configurada; reprocessamento 1Doc mantém `integracao1doc.reprocessar`.

**Configuração**

- **FR-014**: A Central MUST **não duplicar** configurações já existentes: antes de qualquer campo novo, a implementação deve localizar e reutilizar a estrutura onde a configuração já vive (ambiente, singletons); a Central referencia/conduz a elas.
- **FR-015**: Habilitar/desabilitar integração MUST ocorrer somente pelos mecanismos já previstos por integração, com auditoria; a Central não cria interruptor paralelo.
- **FR-016**: Ao tratar configuração sensível, o sistema MUST permitir manter o segredo existente sem exibi-lo, substituí-lo, e indicar apenas que existe credencial configurada.

**Segurança**

- **FR-017**: Nenhuma credencial MAY aparecer em texto puro na interface, logs, auditoria, mensagens de erro, código, URLs ou parâmetros de linha de comando — segredos são mascarados (ex.: `************ABCD`).
- **FR-018**: Os erros MUST ser classificados em categorias (autenticação, timeout, indisponibilidade, configuração inválida, permissão negada, recurso inexistente, validação, interno, temporário) e apresentados de forma compreensível ("Falha de autenticação na integração com o GLPI."), nunca com segredos.

**Histórico, retry e idempotência**

- **FR-019**: O sistema MUST manter histórico de execuções por integração (data/hora, operação, resultado, duração, detalhes sanitizados) com filtros por integração, período, status, tipo de operação e usuário quando aplicável — sem dados sensíveis nos detalhes.
- **FR-020**: O reprocessamento MUST reutilizar os mecanismos existentes por integração (ex.: reprocessamento 1Doc com limite de tentativas); retry com backoff e teto é padrão — **retry infinito é proibido**.
- **FR-021**: Uma integração indisponível MUST NOT bloquear permanentemente uma movimentação patrimonial: falha externa é falha da integração (PENDENTE/COM ERRO, reprocessável), nunca falha da operação patrimonial já confirmada.
- **FR-022**: Integrações que alteram sistemas externos MUST preservar a idempotência estrutural existente (um registro por movimentação por integração) — reenvio não pode duplicar mensagem; o mecanismo usa identificadores internos confiáveis, não comparação de texto.

**Movimentações**

- **FR-023**: A Central MUST oferecer visão somente leitura da propagação de cada movimentação pelas integrações (concluída no SisPatrimônio; enviado/pendente/falhado por integração), sem mover para a Central qualquer lógica patrimonial.
- **FR-024**: Nenhuma chamada externa MAY fazer parte da transação principal do banco de forma que possa causar rollback indevido da movimentação (padrão pós-commit best-effort existente).

**Especificidades por integração**

- **FR-025**: **E-mail**: implementação existente MUST ser preservada integralmente; a Central fornece apenas status, teste, diagnóstico, histórico e condução à configuração existente.
- **FR-026**: **1Doc**: a Central MUST representar fielmente os estados existentes (pendente/enviada/falhada + reprocessamento existente); enquanto o fornecedor não confirmar o contrato, o status agregado é "Pendente de configuração/aguardando fornecedor" — nada de endpoints ou payloads inventados.
- **FR-027**: **GLPI**: MUST ser representada como integração prevista ("Não configurada") até que a versão, API e autenticação da instalação real sejam confirmadas (Seção 18); quando implementada, prioriza atualização de equipamentos **já vinculados** — sem criação automática nesta etapa.
- **FR-028**: **AD**: implementação existente MUST ser preservada (autenticação, autorização, mapeamento de grupos, papéis internos inalterados); a Central funciona como painel de diagnóstico/condução — existir no AD não concede acesso ao SisPatrimônio.

**Geral**

- **FR-029**: A interface MUST seguir o padrão visual existente (tema claro/escuro, desktop e resoluções menores, contraste adequado, componentes existentes) — nenhuma interface paralela.
- **FR-030**: Nenhuma alteração MAY quebrar funcionalidades existentes: regras patrimoniais, movimentações, backup, AD, e-mail e as telas administrativas atuais permanecem intactas fora do previsto nesta spec; mudanças mínimas e cirúrgicas.
- **FR-031**: Alertas automáticos de integração crítica são **avaliados e adiados** (P-5): quando implementados no futuro, deverão ter controle de repetição (sem spam), auditoria e respeito às configurações existentes.

### Non-Functional Requirements

- **NFR-001**: Consultas da Central (painel, histórico, propagação) devem ser paginadas/limitadas e responsivas no volume típico do órgão (sem varreduras ilimitadas).
- **NFR-002**: Sanitização de segredos em profundidade: mesmo que um componente externo ecoe a credencial no texto do erro, a mensagem exibida/registrada não pode contê-la (precedente existente de sanitização).
- **NFR-003**: Datas/horas exibidas no fuso do operador (America/Recife) e armazenadas em UTC (convenção 004).
- **NFR-004**: Chamadas externas de verificação têm prazo máximo (timeout) e não são disparadas em cascata pelo painel — verificação em massa só sob ação explícita do administrador.
- **NFR-005**: Toda funcionalidade nova coberta por testes automatizados com fakes — nenhum serviço externo real na suíte.

### Key Entities *(include if feature involves data)*

- **Integração (catálogo)**: identidade de uma integração — nome, descrição, finalidade, capacidades suportadas (teste, habilitar/desabilitar, reprocessar), referências às configurações e às fontes de estado existentes. VIVE no registro/catálogo da Central, não é uma nova fonte de verdade.
- **Estado da integração**: derivado — status padronizado + dimensões de diagnóstico (configurada/disponível/autenticada/operacional) + momentos (última execução, último sucesso, última falha).
- **Execução/evento de integração**: ocorrência pontual (envio, envio tentado, teste, reprocessamento) com integração, operação, resultado, duração, ator (quando aplicável) e detalhe sanitizado. Origem: tabelas existentes e/ou estrutura aditiva unificada (P-1).
- **Propagação por movimentação**: leitura consolidada dos registros de integração vinculados a uma movimentação (existentes: notificação de e-mail, comunicação 1Doc; futuro: GLPI).

## 7. Modelo de status padronizado

Estados de **saúde da integração** (vocabulário único da Central):

| Status | Significado | Exemplos reais |
|---|---|---|
| NÃO CONFIGURADA | Faltam parâmetros mínimos ou a integração ainda não foi implementada | GLPI (sem implementação); e-mail sem SMTP configurado |
| PENDENTE | Aguardando algo externo/etapa necessária antes de operar | 1Doc aguardando confirmação do contrato pelo fornecedor |
| DESABILITADA | Implementada, mas explicitamente desligada pelo administrador | Notificações por e-mail desativadas; AD `enabled=false`; `ONEDOC_ENABLED=false` (após contrato confirmado) |
| ATIVA | Habilitada e operando (ou habilitada sem verificação recente) | E-mail com envios recentes; AD habilitado com teste bem-sucedido |
| COM ERRO | Última execução/verificação falhou, ou há falhas recentes | Falha de envio SMTP; comunicação 1Doc FAILED; teste de AD com credencial inválida |
| INDISPONÍVEL | Serviço externo não alcançável no momento (rede/timeout) | AD fora do ar; SMTP inacessível |
| INATIVA | Habilitada, porém sem atividade registrada (nunca executou/sem operações no período observado) | Integração habilitada recentemente, ainda sem execuções |

**Avaliação de PROCESSANDO**: descartado como status de saúde da integração — a Central não mantém execuções de longa duração próprias; "em andamento" existe apenas no nível de **operações individuais** (`PENDING` nas tabelas existentes), que a Central exibe como contagem de pendentes. Não criar estados desnecessários.

**Precedência de derivação** (diretriz; detalhes finais no plan): COM ERRO e INDISPONÍVEL refletem o evento/verificação mais recente; DESABILITADA e NÃO CONFIGURADA refletem a configuração efetiva; PENDENTE reflete bloqueio externo conhecido; ATIVA/INATIVA são os estados residuais positivos.

**Dimensões de diagnóstico** (FR-009), quando verificáveis: CONFIGURADA (parâmetros mínimos presentes) → DISPONIBILIDADE (alcançável) → AUTENTICAÇÃO (credencial aceita) → OPERACIONAL (permissões/fluxo mínimos funcionam). A Central diferencia explicitamente esses níveis — exibindo onde a cadeia quebrou.

## 8. Fluxo da Central (como a camada observa as integrações)

1. **Catálogo**: a Central conhece as integrações por um registro declarativo (cada integração se descreve: nome, finalidade, capacidades, fontes de estado). Nenhuma integração é "descoberta" por varredura de código.
2. **Coleta de estado**: o painel deriva o estado de cada integração a partir das fontes existentes (configuração efetiva, tabelas de integração, eventos de auditoria) — **sem chamadas externas** durante a renderização do painel.
3. **Verificação sob demanda**: chamadas externas acontecem somente na ação explícita "Testar conexão" (com timeout e auditoria) — NFR-004.
4. **Ações**: reprocessar/habilitar/desabilitar delegam aos mecanismos existentes de cada integração; a Central nunca reexecuta a lógica alheia por conta própria.
5. **Nova integração**: implementar o provedor/service (fora da Central) → registrar no catálogo → aparece no painel. A Central não muda de estrutura.

## 9. Modelo de dados (diretrizes; decisão final no plan)

**Reutilizar (fontes existentes — não duplicar):**

| Informação | Fonte atual |
|---|---|
| Ativação/destinatários do e-mail | singleton `email_config` + `SMTP_*` (ambiente) |
| Estado de envios de e-mail por movimentação | `notifications` (PENDING/SENT/FAILED, tentativas, erro sanitizado) |
| Configuração de conexão AD | singleton `ad_settings` + `AD_*` (ambiente) |
| Estado de comunicações 1Doc por movimentação | `onedoc_integrations` (PENDING/SENT/FAILED, tentativas, erro sanitizado) |
| Ações administrativas e eventos | trilha `audit_logs` (`ACTION_*`) |
| Credenciais (sempre) | variáveis de ambiente — nunca banco, nunca a Central |

**Novas estruturas (aditivas, controladas — mecanismo existente de migração idempotente):**

- **Histórico unificado de execuções** (decidido P-1): tabela aditiva nova com integração, tipo de operação, resultado, duração, ator (quando aplicável), momento e detalhe sanitizado — alimentada pelos pontos de execução já existentes (hooks 030/031 e testes da Central). O estado das integrações permanece nas tabelas atuais (`notifications`, `onedoc_integrations`): a tabela unificada registra ocorrências, não substitui a fonte de verdade do estado.
- Nenhuma tabela duplica informação que já existe; nenhum segredo é persistido.
- Relacionamentos com operações internas por referência (ex.: movimentação), preservando as garantias estruturais existentes (UNIQUE por movimentação por integração).

## 10. Segurança de credenciais

Nenhuma credencial deve: aparecer na interface em texto puro; aparecer em logs; aparecer na auditoria; aparecer em mensagens de erro; ser armazenada em código; ser incluída em URLs; ser incluída em parâmetros de linha de comando.

Ao lidar com configuração sensível: manter o segredo existente sem exibi-lo; permitir substituição; indicar apenas que existe credencial configurada (ex.: `Token: ************ABCD` ou "Token configurado."). Padrão já vigente no sistema (senha AD nunca persistida; credenciais SMTP/1Doc somente em ambiente) — a Central o estende a toda a nova superfície, com sanitização em profundidade (NFR-002).

## 11. Teste de conexão e verificação de saúde

- Teste = verificação **somente-leitura** sobre o serviço externo: disponibilidade → autenticação → permissões mínimas (quando a API permitir). Nenhuma criação/alteração/exclusão de dados externos para "testar". No e-mail, o teste limita-se a conexão + autenticação SMTP — nenhuma mensagem é enviada (P-6).
- Resultado padronizado: status, momento da verificação, latência, mensagem amigável, detalhes (sem segredos).
- Nem toda integração precisa verificar o mesmo nível: a Central exibe o que a integração consegue informar (FR-010) e diferencia configurada/disponível/autenticada/operacional (FR-009).
- Testes existentes são reaproveitados (ex.: teste de conexão do AD já auditado como `TESTE_CONEXAO_AD`).

## 12. Histórico, erros, retry e reprocessamento

- **Histórico**: por integração, com filtros (integração, período, status, tipo de operação, usuário quando aplicável) e paginação (NFR-001). Detalhes nunca contêm dados sensíveis.
- **Classificação de erros** (FR-018): autenticação; timeout; indisponibilidade; configuração inválida; permissão negada; recurso inexistente; validação; interno; temporário. A interface apresenta a categoria + mensagem amigável; o detalhe técnico permanece sanitizado. Reaproveita as classificações já existentes (erros transitórios × permanentes do 1Doc; classes de erro do AD).
- **Retry/reprocessamento**: tentativa inicial → retry com backoff → limite de tentativas → estado pendente/falhado → reprocessamento manual (quando previsto). Sem retry infinito (FR-020). A Central reapresenta os mecanismos existentes — não cria um novo motor de retry.

## 13. Idempotência

- Garantia estrutural já vigente: **um registro por movimentação por integração** (UNIQUE em `movement_id`). Reprocessar uma comunicação 1Doc nunca cria uma segunda mensagem; um e-mail nunca é duplicado.
- O mecanismo usa identificadores internos confiáveis (id da movimentação/registro de integração) — nunca comparação de texto de conteúdo.
- Toda integração futura que alterar sistemas externos DEVE seguir o mesmo padrão (requisito de catálogo).

## 14. Auditoria

Ações administrativas da Central registradas na trilha existente (eventos `ACTION_*` novos, aditivos), sempre com: usuário, data/hora, integração, ação, resultado e contexto não sensível — **nunca credenciais**:

- integração configurada (via telas existentes — eventos já vigentes); integração habilitada/desabilitada; teste executado (bem-sucedido/falhou); configuração alterada; operação reprocessada; operação cancelada (quando aplicável).
- Eventos de execução automática (envios, falhas) seguem o padrão já estabelecido pelas features 030/031 (ator = serviço, quando não houver usuário).

## 15. Permissões e acesso

Avaliação do modelo atual (F5) concluída no clarify (P-2, 2026-09-23): **criar permissões próprias da Central**, seguindo o padrão "sem concessão default" das features 030/031:

| Permissão proposta | Cobertura | Observação |
|---|---|---|
| `integracoes.visualizar` | Painel, detalhes, histórico, propagação | **Nova (aprovada P-2)**; sem concessão default (padrão 030/031); Administrador recebe via catálogo |
| `integracoes.testar` | Executar "Testar conexão" nas integrações sem guarda dedicada (e-mail) | **Nova (aprovada P-2)**; sem concessão default |
| `integracao1doc.reprocessar` (existente) | Reprocessamento 1Doc | **Reutilizada** — não duplicar |
| Guarda do AD (existente: `usuarios.editar` + `perfis.editar`) | Tela AD e teste de conexão AD | **Reutilizada** — não duplicar |
| `notificacoes.gerenciar` (existente) | Tela de notificações (e-mail) | **Reutilizada** — não duplicar |

Regras: deny by default; validação sempre no backend; menu/botões apenas apresentação; nenhuma autorização nova paralela; a Central jamais concede permissão que a tela de destino não concederia.

## 16. Relação com movimentações e regra de transação

- A Central **acompanha** eventos originados de movimentações (propagação por movimentação — FR-023) e **não modifica** a regra de negócio da movimentação; nenhuma lógica patrimonial migra para a Central.
- Regra fundamental (FR-024, F8): movimentação concluída + falha de integração ⇒ movimentação **permanece registrada**; a integração fica PENDENTE/COM ERRO e pode ser reprocessada. Aplicável a 1Doc, GLPI (futuro) e e-mail. Chamadas externas permanecem fora da transação principal (pós-commit best-effort).

## 17. Interface

- Padrão visual existente (Jinja2 + Bootstrap 5), tema claro/escuro, desktop e resoluções menores, contraste adequado, componentes existentes, `403/404` amigáveis, ajuda central atualizada na mesma tarefa (Princípio XI da Constitution).
- Navegação: Administração → Central de Integrações → card → detalhe → (histórico / propagação / configuração existente).
- Nenhuma interface paralela; nenhuma remoção de acesso existente.

## 18. Dependências externas / informações pendentes — A CONFIRMAR

> **Nada desta seção pode ser presumido ou inventado.** As implementações do 1Doc e do GLPI ficam condicionadas às confirmações abaixo; até lá, a Central apenas **representa** os estados ("Pendente de configuração", "Não configurada").

### 1Doc (integração implementada, bloqueada ao fornecedor — continuar de `specs/031-integracao-1doc`)

Pendências C-1..C-8 já registradas na 031 e solicitação formal em `docs/SOLICITACAO_API_1DOC.md`. A confirmar com o suporte do 1Doc antes de qualquer evolução:

- API disponível na instalação do IPMJP e documentação oficial (referência/Swagger, se houver);
- método de **autenticação** (API key, Bearer, OAuth2), validade e renovação de credencial, escopos leitura × escrita;
- **endpoints** reais (consulta de processo, validação de existência, inclusão de comunicação);
- **permissões** da credencial concedida;
- **criação de mensagens**: formatos aceitos (texto, HTML, tabela), anexos, retorno de identificador;
- **inclusão de tabela** no corpo da comunicação;
- **assinatura**: capacidades (a assinatura segue fluxo normal do 1Doc — não falsificar);
- **identificadores**: convenção real do número de processo no ambiente do IPMJP; id de mensagem;
- **limites**: rate limits, tamanho de mensagem;
- **erros**: códigos comuns e semântica (para refinar a classificação da Seção 12);
- existência de ambiente de homologação e mecanismo nativo de idempotência.

### GLPI (integração prevista — investigar antes de implementar)

Antes de qualquer implementação, investigar a **instalação real** e confirmar:

- versão efetivamente utilizada do GLPI;
- API disponível nessa versão e mecanismo de autenticação (app token, user token, sessão);
- como os **equipamentos** são identificados (tipo de item, critério de vínculo com o tombamento);
- como **usuário/responsável** é representado;
- como **localização** é representada;
- permissões da conta da API a ser utilizada;
- existência de ambiente de teste e política de alteração (a prioridade inicial é **atualizar equipamentos já vinculados** — sem criação automática de equipamentos nesta etapa).

### Active Directory e E-mail

Nenhuma pendência externa nova: implementações existentes preservadas; a Central apenas as observa (F1, F3).

## 19. Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das integrações do catálogo visíveis com status padronizado em uma única tela, sem navegar por outros menus.
- **SC-002**: 100% das rotas da Central negam acesso a usuário sem permissão (negação padrão, auditada) — verificado por testes.
- **SC-003**: 0 ocorrências de credenciais/segredos em interface, logs, auditoria e mensagens de erro da Central (varredura automatizada na suíte + revisão).
- **SC-004**: Todo "Testar conexão" conclui com resultado apresentado dentro do prazo máximo da integração (ex.: ≤ 10 s) e 100% das execuções ficam registradas em histórico + auditoria.
- **SC-005**: A partir do painel + detalhe, identificar integração com problema, desde quando, último erro e operações afetadas **sem sair da Central** (0 consultas manuais ao banco).
- **SC-006**: 0 alterações de comportamento em funcionalidades existentes fora do previsto: suíte existente permanece verde (Princípio VIII da Constitution).
- **SC-007**: Adicionar uma integração nova (demonstrado em teste com integração fictícia/stub) não exige alteração estrutural da Central — apenas registro no catálogo.
- **SC-008**: 0 registros duplicados em reprocessamentos/testes (idempotência verificada por testes).
- **SC-009**: O histórico consulta execuções com filtros funcionais (integração, período, status, tipo, usuário) e paginação — resposta dentro do padrão de desempenho da aplicação (NFR-001).
- **SC-010**: 0 endpoints/payloads inventados para 1Doc e GLPI: as seções de pendências (18) permanecem a única fonte dos itens a confirmar, e o status das duas integrações reflete o bloqueio real.

## 20. Assumptions

- A Central é camada de gerenciamento/observabilidade; nenhuma lógica de negócio das integrações ou das movimentações migra para ela.
- Configurações existentes (ambiente + singletons) permanecem a **fonte única de verdade**; a Central não passa a armazenar configuração própria de credenciais nesta versão.
- GLPI e a ativação efetiva do 1Doc dependem de confirmação externa (Seção 18); a Central nasce representando esses bloqueios de forma honesta.
- As novas permissões `integracoes.visualizar` e `integracoes.testar` (aprovadas no clarify, P-2) não têm concessão default; o administrador concede explicitamente (padrão vigente).
- O ambiente de testes não possui serviços externos reais: todos os testes usam fakes (padrão da suíte).
- Documentação (README/docs/ajuda central) é atualizada na mesma tarefa (Princípio XI).
- Aderência integral à Constitution v1.0.0 (Princípios I–XII), em especial I (evolução incremental), VI (segurança/credenciais), VII (banco aditivo), VIII (testes), IX (auditoria) e XII (validação).

## 21. Pendências de decisão (com defaults propostos — decidir no plan)

- **P-1 — RESOLVIDA no clarify (2026-09-23)**: histórico unificado em tabela aditiva nova, alimentada pelos pontos de execução existentes; sem duplicação da fonte de verdade do estado. Ver `## Clarifications`.
- **P-2 — RESOLVIDA no clarify (2026-09-23)**: criar `integracoes.visualizar` e `integracoes.testar`, sem concessão default, reutilizando as permissões/guardas existentes por integração. Seção 15 atualizada.
- **P-3 — RESOLVIDA no clarify (2026-09-23)**: autorização do teste por integração = guarda existente (AD) + `integracoes.testar` (e-mail, 1Doc); FR-013 atualizado.
- **P-4 — RESOLVIDA no clarify (2026-09-23)**: janela fixa de 24 horas para "falhas recentes", explicitada na interface.
- **P-5 — Fechada no clarify (2026-09-23)**: mantida fora do escopo desta versão (sem pergunta necessária — decisão já registrada na spec); requisitos para futuro: gatilho por transição de status, controle de repetição (sem spam), auditoria, respeito às configurações existentes.
- **P-7 — Nomes finais** (service/rotas/eventos de auditoria/entidade de histórico): não é ambiguidade de spec — é detalhe de plan. **Mantida para decisão no `/speckit-plan`**, seguindo o padrão do projeto (precedente 031 P-6).
- **P-6 — RESOLVIDA no clarify (2026-09-23)**: teste SMTP = conexão + autenticação, sem envio de mensagem; envio de teste como evolução futura opcional.


## 22. Estratégia de testes

Cenários obrigatórios (todos com fakes; cada integração testada individualmente, sem exigir serviços externos reais):

- acesso autorizado × acesso não autorizado (todas as rotas da Central);
- listagem de integrações e status correto para cada estado do modelo (Seção 7);
- configuração: condução às telas existentes; alteração de configuração auditada (vias existentes);
- **segredo não exposto** em nenhuma superfície (interface, auditoria, erro, log);
- teste de conexão: sucesso, timeout, erro de autenticação, integração indisponível — cada classificação e o registro (histórico + auditoria);
- histórico: filtros, paginação, lista vazia, detalhes sanitizados;
- auditoria dos eventos administrativos da Central;
- reprocessamento: reuso do mecanismo existente, limite de tentativas, sem retry infinito;
- idempotência: reprocesso/teste não duplica registros;
- movimentação sem rollback por falha externa (regressão do contrato 030/031);
- propagação por movimentação: estados corretos, incluindo movimentação sem registros;
- não-regressão: suíte existente 100% verde.

## 23. Riscos

| Risco | Mitigação |
|---|---|
| Acoplamento acidental: Central passa a executar lógica das integrações | Contrato claro (Seção 8): Central observa/delega; revisão de conformidade da Constitution |
| Duplicação de verdade de configuração/estado | FR-014/F9 + análise obrigatória "onde isso já vive?" antes de qualquer campo novo |
| Exposição acidental de segredos em nova superfície | Sanitização em profundidade (NFR-002), mascaramento por padrão, SC-003 com varredura |
| Custo/abuso de verificações externas (health check em massa) | Verificação apenas sob ação explícita, com timeout (NFR-004) |
| Degradação do painel com volume de histórico | Paginação/limites (NFR-001) e agregações limitadas |
| Regressão nas integrações existentes (030/031/AD) | Princípio I + FR-030 + suíte existente verde (SC-006) |
| Expectativa indevida de GLPI/1Doc antes do fornecedor | Seção 18 bloqueante; status honestos (PENDENTE/NÃO CONFIGURADA); SC-010 |

## 24. Arquivos/módulos potencialmente afetados (preliminar — confirmar no plan)

- `app/services/` — **novo** service da Central (catálogo, derivação de status, orquestração de testes); **somente leitura** de `notification_service`, `onedoc_service`, `ad_service`, `email_config_service`, `audit_service` (instrumentação de eventos do histórico se P-1 for tabela unificada).
- `app/services/permission_service.py` — novas permissões no catálogo (se P-2 confirmado).
- `app/services/audit_service.py` — novos eventos `ACTION_*` (aditivos) + rótulos.
- `app/web/admin_routes.py` — rotas da Central (painel, detalhe, histórico, teste) com `require_permission`.
- `app/web/templates/admin/` — novos templates no padrão existente; `base.html` apenas para entrada de menu (padrão vigente).
- `app/models/` + `app/database.py` — estrutura aditiva de histórico (se P-1), via mecanismo idempotente existente.
- `docs/`, central de ajuda — atualização na mesma tarefa.
- `tests/` — novo arquivo de testes da Central + fakes.
- **Intocáveis**: `movement_service` (motor e hooks pós-commit), `backup_*`, regras de `ad_service`/`ad_ldap`, `email_provider`, `onedoc_client` (`[PENDING C-*]` permanece), telas administrativas existentes fora das adições previstas.
