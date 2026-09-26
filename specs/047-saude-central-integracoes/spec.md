# Feature Specification: Central de Integrações — Saúde do Sistema e das Integrações

**Feature Branch**: `047-saude-central-integracoes`

**Created**: 2026-09-26

**Status**: Draft

**Input**: Criar uma evolução na área existente de Administração do SisPatrimônio Pro para disponibilizar uma **Central de Integrações com visão operacional da saúde do sistema e das integrações existentes** — painel operacional (não um sistema de monitoramento). O pedido estabelece prioridade máxima: **ANALISAR O QUE JÁ EXISTE, REUTILIZAR O QUE JÁ FUNCIONA E FAZER A MENOR ALTERAÇÃO POSSÍVEL** — proibido criar segundo health check, segundo mecanismo de teste, segundo scheduler, segunda auditoria, segundo backup, segundo cliente AD/SMTP/GLPI, segundo sistema de configuração/permissões ou segunda página de Administração com a mesma finalidade.

> **Relação com a feature 032 (verificada no código, 2026-09-26)**: a Central de Integrações **JÁ EXISTE e está implementada** (commit `6a3a0a5`, feature 032) — catálogo declarativo com E-mail, 1Doc, Active Directory e GLPI; painel `/admin/integracoes`; detalhe, histórico unificado (`IntegrationExecution`), propagação por movimentação e ação "Testar conexão" auditada; permissões próprias (`integracoes.visualizar`, `integracoes.testar`); mecanismo de máscara/sanitização de segredos (`mask_secret`, `_sanitize_detail`). Esta spec NÃO reimplementa a Central: **extende o catálogo existente** com os componentes de saúde que faltam (Aplicação, Banco de Dados, Armazenamento, Backup Local, Backup Externo, Agendador) e aprimora a apresentação do painel como **visão consolidada de saúde operacional** — exatamente o papel que a 032 já reserva para o catálogo ("adicionar uma nova integração não exige alteração estrutural da Central").

---

## 1. Objetivo

Dar ao administrador, em **Administração → Central de Integrações** (a própria página inicial da Central — sem subpágina "Visão geral"), resposta imediata e padronizada a:

- A aplicação está operacional? O banco de dados responde? O armazenamento está adequado?
- O Active Directory está acessível? O e-mail está configurado/operacional?
- O GLPI está acessível e funcionando (quando existir implementação)?
- O backup local está funcionando? O backup externo está acessível? O agendador está ativo?
- Quais integrações estão configuradas, não configuradas ou com falha?

A Central é um **painel operacional de leitura**: consulta estados já conhecidos/armazenados e só executa verificações ativas sob ação explícita do administrador. **Não** cria servidores, threads, conexões ou mecanismos paralelos de monitoramento.

## 2. Fatos verificados no código (fonte das reutilizações — análise somente leitura, 2026-09-26)

| # | Fato | Consequência para esta feature |
|---|---|---|
| F1 | **Central 032 implementada**: `integration_center_service.py` (catálogo `INTEGRATIONS`, vocabulário de status, `mask_secret`, `_sanitize_detail`, contadores do histórico), rotas `/admin/integracoes` (+ detalhe, histórico, `POST testar`, propagação por movimentação) com `integracoes.visualizar`/`integracoes.testar`, templates `admin/integracoes/{list,detail,historico,movimentacao}.html` | Toda a extensão acontece **dentro da estrutura existente**: novos itens no catálogo + apresentação; nenhuma área nova de Administração |
| F2 | **`/health` existente** (`app/main.py:153`): verifica aplicação, banco (`SELECT 1`) e AD (se configurado/habilitado, via `ad_ldap.test_connection`), retornando `healthy/degraded` com estados por componente | **Único health check do sistema** — a Central **consome** seus mecanismos/semântica (mesma sessão/configuração); proibido duplicar |
| F3 | **Banco**: conexão única via `DATABASE_URL` (`SessionLocal`); o health check já executa consulta simples com tratamento de erro | Verificação de banco reutiliza a sessão/config existente — nenhuma conexão nova |
| F4 | **AD**: `ad_service` + `ad_ldap.test_connection`, singleton `ad_settings`, tela `/admin/ad` com teste auditado; health check já verifica AD | Reutilização integral; sem bind real de usuário, sem senha em tela (senha AD nunca é persistida) |
| F5 | **E-mail**: `email_provider` + `email_config` + `SMTP_*` em ambiente; teste da Central já faz **conexão + autenticação SMTP sem envio** (P-6 da 032) | Card reapresenta o estado; teste manual reutiliza o mecanismo da 032 |
| F6 | **GLPI**: **não existe cliente/configuração no código** (apenas representação como integração prevista no catálogo da 032) | GLPI permanece **honesto**: "Não configurada" até que exista implementação; nada é inventado |
| F7 | **Backup local**: `backup_service` (BackupService, BackupRecord), histórico, retenção, `retention_monitoring_summary` (último backup, último válido, última falha, contagem de válidos no disco) | Card deriva o status dos dados já existentes — **não gera backup** para abrir a página |
| F8 | **Backup externo (045)**: `external_backup_service` com `get_external_config`, `test_destination` (arquivo temporário → grava → lê → remove, sem gerar backup completo) e modelo `BackupExternalRecord` com últimas cópias/falhas | "Testar destino" existente é **reutilizado** como teste ativo; estado deriva da config + registros; nenhuma cópia real ao abrir a página |
| F9 | **Agendador**: `backup_scheduler` com `scheduler_status()` (habilitado, agendamento, próximo run, último resultado, running) e `retention_monitoring_summary` | Card consulta o scheduler existente; **nenhum thread novo** |
| F10 | **RBAC**: catálogo `PERMISSION_CATALOG`, deny by default, `require_permission`; permissões da Central já existem (`integracoes.visualizar`, `integracoes.testar` — sem concessão default) | **Reutilizadas**; nenhuma permissão nova é necessária (a 032 já definiu o par correto para o painel e para testes) |
| F11 | **Auditoria**: trilha `audit_logs` + `record_execution` best-effort no histórico unificado da Central (eventos `ACTION_*` existentes: teste AD `TESTE_CONEXAO_AD`, testes da Central, BACKUP_*) | Testes manuais reutilizam os registros já previstos; nenhum evento por carregamento de página |
| F12 | **UI**: Jinja2 + Bootstrap 5, tema claro/escuro, componentes de cards/badges existentes, grid responsivo, central de ajuda | Painel segue o padrão visual vigente; nenhum CSS global novo; ajuda atualizada na mesma tarefa (Princípio XI) |
| F13 | **Armazenamento**: `shutil.disk_usage` já utilizado em `external_backup_service` (espaço livre do destino); diretórios de backup configuráveis (`backup_config`) | Verificação de armazenamento reutiliza o mecanismo padrão da plataforma (`shutil.disk_usage` + existência de diretórios); sem sistema de gerenciamento novo |
| F14 | **1Doc (031)**: integração implementada, aguardando fornecedor (`ONEDOC_ENABLED=false`, `[PENDING C-1..C-4]`); catálogo já a representa como PENDENTE | 1Doc reflete seu estado **real** (Pendente de Configuração) — nada inventado |

## Clarifications

### Session 2026-09-26

- Q: Quando o card "Backup Local" deve mudar de OK para ATENÇÃO/FALHA por falta de backup recente? → A: Alinhado ao agendador existente — agendador ATIVO: atraso além do ciclo esperado (com folga de 1 ciclo) = ATENÇÃO e nenhum backup válido = FALHA; agendador desabilitado (regime manual): sem alerta por atualidade, espelhando a última falha registrada (decisão 2026-09-26).
- Q: Qual regra de alerta para o card "Armazenamento" (espaço livre nos diretórios verificados)? → A: Por capacidade de acomodar o próximo backup — ATENÇÃO quando o espaço livre fica abaixo do tamanho do último backup válido (não cabe mais um backup); FALHA apenas quando não há espaço para escrita; sem limite percentual (decisão 2026-09-26).
- Q: A consulta de saúde do Banco de Dados deve medir e exibir o tempo de resposta, ou apenas o estado de conexão? → A: Apenas estado (CONECTADO/FALHA) — sem medição nem exibição de tempo de resposta no painel (decisão 2026-09-26).

## 3. Escopo

### Incluído

- **Ampliação do catálogo** da Central com os componentes de saúde do sistema: **Aplicação**, **Banco de Dados**, **Armazenamento**, **Backup Local**, **Backup Externo**, **Agendador de Backup** (além dos existentes E-mail, 1Doc, AD, GLPI) — seguindo o mecanismo declarativo já vigente.
- **Painel `/admin/integracoes` como visão consolidada de saúde**: cada componente com status padronizado (§7) + resumo de uma linha (ex.: "Última verificação: 10:42", "Último backup válido: 24/09 02:00", "Próximo backup: 01/10 02:00"), em grid responsivo reutilizando os componentes existentes.
- **Consulta × Teste** (distinção obrigatória): abrir a página **consulta** estados já conhecidos (config, registros, `scheduler_status`, semântica do `/health`) — **sem I/O externo e sem operações caras**; verificações ativas acontecem **somente** na ação explícita "Testar" reutilizando os mecanismos existentes por componente.
- **Testes manuais** por componente que já os possui: AD, E-mail, GLPI (quando implementado), Backup Externo ("Testar destino" — sem gerar backup completo, sem deixar arquivos no destino).
- **Auditoria** dos testes manuais pelos mecanismos já existentes (trilha + histórico da Central); nenhum evento por carregamento de página.
- **Segurança**: reutilização de `integracoes.visualizar`/`integracoes.testar`; máscara/sanitização de segredos com os mecanismos existentes (`mask_secret`, `_sanitize_detail`); nenhum segredo em interface, logs ou auditoria.
- Detalhe de cada componente (página existente da Central, estendida) com as informações resumidas já disponíveis por componente; condução às telas de configuração existentes (sem páginas duplicadas).
- Modo claro e escuro; responsividade desktop → celular com o grid existente (3 colunas em telas grandes, 1 coluna em telas menores).
- Documentação (README/docs/central de ajuda) atualizada na mesma tarefa (Princípio XI).

### Não incluído (fora de escopo)

- Criar segundo health check, segundo mecanismo de teste de conexão, segundo serviço de monitoramento, segundo scheduler, segunda auditoria, segundo mecanismo de backup, segundo teste de destino externo, segundo cliente AD/SMTP/GLPI, segundo sistema de configuração, novo RBAC ou nova página "Visão geral".
- **Implementar a integração GLPI** (permanece prevista; quando implementada em spec própria, o card consome o cliente real).
- **Implementar a integração 1Doc** além do estado real atual (aguardando fornecedor).
- Enviar e-mail real, gerar backup real ou executar restore/inventário como efeito de abrir a página ou do teste.
- Persistir histórico novo de health checks ou criar tabela de estados derivados (§10 — tudo calculado dos componentes existentes).
- Alertas automáticos/proativos aos administradores (permanecem fora, conforme P-5 da 032).
- Alterar regras patrimoniais, movimentações, inventário, manutenção, relatórios, usuários, colaboradores, URLs existentes, endpoints não relacionados, banco de dados além do previsto e telas existentes fora da Central.

## 4. User Scenarios & Testing *(mandatory)*

### User Story 1 — Painel de saúde consolidado na Central (Priority: P1) 🎯

Um administrador abre **Administração → Central de Integrações** e vê, em uma única tela, o estado dos dez componentes (Aplicação, Banco de Dados, Armazenamento, Active Directory, E-mail, GLPI, 1Doc, Backup Local, Backup Externo, Agendador de Backup) — cada um com status padronizado e resumo de uma linha derivado dos dados já existentes (§9). De relance ele distingue o saudável, o não configurado e o com falha.

**Why this priority**: é o núcleo do pedido — visão operacional consolidada sem navegar por várias telas.

**Independent Test**: com os componentes em estados conhecidos (fakes/fixtures da suíte), o painel exibe o status e o resumo corretos para cada componente — testável isoladamente.

**Acceptance Scenarios**:

1. **Given** aplicação em execução com banco acessível, **When** o administrador abre a Central, **Then** os cards Aplicação ("Operacional") e Banco de Dados ("Conectado") exibem status verde.
2. **Given** banco indisponível (simulação controlada), **When** o painel é renderizado, **Then** o card Banco de Dados exibe status de falha **e a aplicação não quebra** (demais cards permanecem renderizados).
3. **Given** backup local com histórico existente, **When** o painel é aberto, **Then** o card Backup Local exibe último backup válido e contagem de backups válidos **sem gerar nenhum backup**.
4. **Given** backup externo habilitado com destino configurado, **When** o painel é aberto, **Then** o card Backup Externo exibe habilitado/destino/última cópia **sem executar o teste de destino nem gerar cópia**.
5. **Given** agendador ativo, **When** o painel é aberto, **Then** o card Agendador exibe ativo, agendamento e próximo backup a partir do `scheduler_status()` existente.
6. **Given** GLPI sem implementação e 1Doc aguardando fornecedor, **When** o painel é aberto, **Then** os cards exibem "Não Configurada" e "Pendente de Configuração" respectivamente — estados reais, sem invenção.

---

### User Story 2 — Testes manuais não destrutivos com reutilização integral (Priority: P1)

O administrador executa, sob ação explícita, o teste de um componente que já possui mecanismo: "Testar conexão" do AD (guarda e mecanismo existentes), "Testar conexão" do E-mail (conexão + autenticação SMTP **sem envio**), "Testar destino" do Backup Externo (arquivo temporário → grava → lê → valida → remove — **sem gerar backup completo e sem deixar arquivos no destino**), "Testar conexão" do GLPI (quando a integração existir). Cada teste registra resultado no histórico e na auditoria pelos mecanismos vigentes e apresenta mensagem amigável.

**Why this priority**: é a ação de diagnóstico essencial ("o problema é aqui ou lá?") e o pedido condiciona: nunca operações destrutivas, nunca backup real, nunca e-mail real.

**Independent Test**: com fakes de sucesso/timeout/erro de autenticação/indisponibilidade por componente, o teste produz o resultado correto e registra histórico + auditoria — testável por componente.

**Acceptance Scenarios**:

1. **Given** AD saudável (fake), **When** o administrador executa o teste, **Then** o resultado é positivo com data/hora, registrado no histórico e na auditoria via mecanismo existente.
2. **Given** destino externo acessível (fake de sistema de arquivos), **When** "Testar destino" é executado, **Then** o teste cria/valida/remove arquivo temporário e **não deixa arquivo no destino**; **nenhum backup é gerado**.
3. **Given** serviço externo inalcançável (fake de timeout), **When** qualquer teste é executado, **Then** o teste respeita prazo máximo, classifica a falha de forma amigável **e a aplicação não quebra**.
4. **Given** e-mail configurado, **When** o teste é executado, **Then** apenas conexão e autenticação SMTP são verificadas — **nenhuma mensagem é enviada**.
5. **Given** qualquer teste, **When** concluído, **Then** nenhum dado patrimonial, usuário ou configuração foi modificado.

---

### User Story 3 — Segurança, auditoria e acesso (Priority: P1)

Somente usuários com as permissões existentes da Central (`integracoes.visualizar` para o painel; `integracoes.testar` para testes; guardas próprias onde já existem — ex.: AD) acessam as informações; demais recebem a negação padrão. Em **nenhuma** superfície (interface, logs, auditoria, mensagens de erro) aparece credencial de AD, SMTP, GLPI ou qualquer segredo — máscara/sanitização pelos mecanismos já vigentes.

**Why this priority**: a Central concentra informação sensível de saúde e configuração; sem acesso controlado e não-exposição ela não pode existir.

**Independent Test**: usuário sem permissão recebe 403 em todas as rotas; com usuário autorizado, varre-se a renderização e os eventos confirmando ausência de segredos — testável isoladamente.

**Acceptance Scenarios**:

1. **Given** usuário autenticado sem `integracoes.visualizar`, **When** acessa a Central, **Then** recebe a negação padrão (403 amigável) e o acesso negado é auditado (padrão existente).
2. **Given** usuário com permissão e configuração com segredo, **When** visualiza qualquer detalhe, **Then** o segredo aparece mascarado ("Token configurado.", `************`) ou apenas indicado como configurado.
3. **Given** falha de conexão com serviço externo, **When** a mensagem é exibida/registrada, **Then** contém apenas classificação amigável (autenticação/timeout/indisponibilidade) — nunca credencial.
4. **Given** carregamento do painel, **When** a página é renderizada, **Then** nenhum evento de auditoria é criado apenas pela leitura.

---

### User Story 4 — Responsividade e consistência visual (Priority: P2)

A página da Central mantém o padrão visual do sistema em desktop grande (3 colunas), desktop médio/notebook, tablet e celular (1 coluna), nos temas claro e escuro, reutilizando os componentes existentes (cards, badges de status, grid, botões) — sem CSS global novo e sem novo design system.

**Why this priority**: conformidade com o padrão do sistema; o valor operacional já está entregue nas histórias P1.

**Independent Test**: renderização em larguras de referência (desktop grande/médio, notebook, tablet, celular) e nos dois temas, comparando consistência com as demais telas administrativas — testável isoladamente.

**Acceptance Scenarios**:

1. **Given** desktop grande (≥1400px), **When** o painel é aberto, **Then** os dez componentes apresentam-se em grid de 3 colunas equivalente ao pedido (§19 do pedido).
2. **Given** celular (<576px), **When** o painel é aberto, **Then** os componentes empilham em coluna única, sem sobreposição nem corte, com controles acessíveis.
3. **Given** tema escuro ativo, **When** qualquer estado é exibido, **Then** os status mantêm contraste e legibilidade (padrão de badges existente).
4. **Given** redimensionamento da janela, **When** a largura varia entre os breakpoints, **Then** o grid reorganiza-se sem quebrar o layout (comportamento Bootstrap existente).

### Edge Cases

- **Componente de saúde falha ao ser consultado** (ex.: erro ao calcular espaço em disco): o card afetado mostra estado de falha/desconhecido com mensagem sanitizada — **o restante do painel renderiza normalmente** (nenhum componente derruba a página).
- **Scheduler desabilitado**: card em estado distinto de falha ("Desabilitado"), com indicação de onde habilitar (tela de configuração existente de backup).
- **Backup externo desabilitado**: card indica "Desabilitado" com a configuração existente; teste de destino permanece disponível para diagnóstico quando o administrador o acionar.
- **Armazenamento sem regra de alerta existente**: ATENÇÃO quando o espaço livre do diretório fica abaixo do tamanho do último backup válido (não cabe mais um backup); FALHA apenas quando não há espaço para escrita — regra por capacidade real de backup, sem limite percentual (decisão 2026-09-26; detalhamento no plan).
- **Histórico vazio / integração recém-ativada sem execuções**: exibir "—" (ausência de execução não é falha — precedente da 032).
- **Falha do próprio mecanismo de coleta**: card com último estado conhecido/erro sanitizado; demais componentes normais.
- **Horários**: fuso do operador (America/Recife), armazenados em UTC (convenção 004).
- **GLPI em produção quando implementado**: a verificação não interrompe a aplicação (timeout e tratamento de erro próprios do mecanismo da 032).

## 5. Requirements *(mandatory)*

### Functional Requirements

**Painel e catálogo**

- **FR-001**: O sistema MUST apresentar, em `/admin/integracoes` (a própria página da Central — sem subpágina "Visão geral"), um card por componente do catálogo ampliado: Aplicação, Banco de Dados, Armazenamento, Active Directory, E-mail, GLPI, 1Doc, Backup Local, Backup Externo, Agendador de Backup.
- **FR-002**: O catálogo MUST permanecer o mecanismo declarativo existente da 032: novos itens entram como entradas do catálogo (key, nome, descrição, capacidades, status_fn), **sem alteração estrutural** da Central.
- **FR-003**: Cada card MUST exibir no mínimo: nome do componente, status padronizado (§7) e resumo de uma linha com a informação mais útil já disponível (§9); detalhes ficam no detalhe do componente e nas telas de configuração existentes.
- **FR-004**: O sistema MUST distinguir **Consulta** (estado já conhecido — ao abrir a página) de **Teste** (verificação ativa — somente sob ação explícita do administrador).
- **FR-005**: A renderização do painel MUST NOT executar: geração de backup, restore, teste de destino externo, teste SMTP, bind LDAP, chamadas externas ou operações potencialmente demoradas — apenas leitura de configuração, registros e estados já calculados.
- **FR-006**: O sistema MUST derivar o status exibido do **estado real** dos componentes (configuração efetiva + registros existentes + semântica do `/health` existente) — sem status inventado ou editável.

**Componentes de saúde (extensão do catálogo)**

- **FR-007**: **Aplicação**: componente operacional quando a aplicação responde (o carregamento da página já o comprova); pode reapresentar a semântica do `/health` existente sem duplicá-lo.
- **FR-008**: **Banco de Dados**: verificação pela conexão/configuração existente (consulta simples já usada pelo `/health`), exibindo apenas o estado (CONECTADO/FALHA — sem medição de tempo de resposta); NENHUMA conexão nova ou alteração de configuração.
- **FR-009**: **Armazenamento**: verificação de existência dos diretórios relevantes (backup e afins já configurados) e espaço disponível pelo mecanismo padrão da plataforma; teste de escrita somente quando tecnicamente necessário (preferência: não escrever ao abrir a página).
- **FR-010**: **Backup Local**: card derivado de `backup_records` e do resumo de monitoramento existente (último backup, último válido, contagem de válidos, última falha, retenção) — sem gerar backup e sem duplicar o monitoramento da área de Backups.
- **FR-011**: **Backup Externo**: card derivado da configuração existente (habilitado, destino) e dos registros de cópia já persistidos (última cópia, última cópia válida, última falha); teste ativo somente pela ação "Testar destino" existente (arquivo temporário → grava → lê → valida → remove), **sem gerar backup completo** e **sem deixar arquivos de teste no destino**.
- **FR-012**: **Agendador de Backup**: card a partir de `scheduler_status()` existente (ativo/inativo, agendamento, próximo backup, último resultado, última execução) — sem criar thread, scheduler ou mecanismo de agendamento novo.
- **FR-013**: **Active Directory**: reapresentação do estado existente (configurado/habilitado/último teste) com teste manual pelo mecanismo vigente (sem login real de usuário e sem solicitar senha na tela de saúde).
- **FR-014**: **E-mail**: reapresentação do estado (configurado/não configurado, último teste) com teste manual **sem envio de mensagem** (conexão + autenticação SMTP — mecanismo da 032).
- **FR-015**: **GLPI**: permanece fiel ao estado real do código; enquanto não houver implementação, "Não Configurada" e sem ação de teste; quando a integração existir (spec própria), o card consome o cliente real e o teste existente.
- **FR-016**: **1Doc**: reflete o estado real atual (implementada, aguardando fornecedor → "Pendente de Configuração") sem inventar status de funcionamento.

**Testes manuais, auditoria e segurança**

- **FR-017**: Cada componente com capacidade de teste MUST oferecer teste explícito reutilizando o mecanismo existente; componentes sem mecanismo próprio (Aplicação, Banco, Armazenamento, Backup Local, Agendador) não oferecem botão de teste (sua verificação é a consulta no painel) — nada de segundo mecanismo de teste.
- **AD/E-mail/GLPI/Backup Externo**: testes reutilizam integralmente os existentes (guarda do AD; teste SMTP sem envio; GLPI quando existir; "Testar destino" da 045).
- **FR-018**: Todo teste manual MUST registrar resultado no histórico unificado da Central e na trilha de auditoria existente (eventos `ACTION_*` vigentes; nenhum evento por carregamento de página).
- **FR-019**: Nenhuma credencial MAY aparecer em interface, logs, auditoria ou mensagens de erro — senhas, tokens, API keys, secrets, credenciais LDAP/SMTP/GLPI são mascaradas pelos mecanismos existentes (`mask_secret`, `_sanitize_detail`); URLs mascaradas quando necessário.
- **FR-020**: A Central MUST reutilizar o RBAC existente: `integracoes.visualizar` (painel/detalhes), `integracoes.testar` (testes sem guarda dedicada) e guardas próprias onde já existem (ex.: AD). **Nenhuma permissão nova** é criada (as existentes cobrem o escopo — F10).
- **FR-021**: Nenhuma operação de teste MAY ser destrutiva: não gerar backup real, não executar restore, não modificar patrimônio, usuários ou configurações, não enviar e-mail real, não deixar arquivos de teste no destino externo.

**Interface e layout**

- **FR-022**: A interface MUST seguir o padrão visual existente (Jinja2 + Bootstrap 5, tema claro/escuro, componentes de cards/badges/grid vigentes) — nenhum CSS global novo, nenhum segundo design system, nenhuma alteração de navbar/tema global.
- **FR-023**: Em telas grandes o painel MUST apresentar os componentes em grid de 3 colunas (linha 1: Aplicação, Banco, Armazenamento; linha 2: AD, E-mail, GLPI; linha 3: Backup Local, Backup Externo, Agendador; 1Doc e demais seguem o padrão do catálogo); em telas menores, coluna única (comportamento responsivo do grid existente).
- **FR-024**: Cada componente com configuração existente MUST conduzir à sua tela vigente pelo "Ver detalhes" (config_route do catálogo) — sem páginas duplicadas de configuração.
- **FR-025**: A ação "Atualizar" MUST reutilizar mecanismos existentes (recarregamento da página — consulta de estados já conhecidos); nenhuma verificação pesada automática em cascata.

**Geral**

- **FR-026**: Nenhuma alteração MAY quebrar funcionalidades existentes: integrações existentes (e-mail, 1Doc, AD), GLPI quando implementado, backup local/externo/automático, `/health`, telas administrativas e rotas vigentes permanecem intactos fora do previsto nesta spec.
- **FR-027**: O sistema MUST continuar iniciando normalmente e mantendo todas as rotas existentes funcionais após a alteração (verificado pela suíte).
- **FR-028**: A Central não MUST criar tabelas novas para estados derivados: toda informação de saúde é **calculada/consultada** dos componentes existentes (§9/§10); nenhuma migração é prevista nesta feature.
- **FR-029**: A central de ajuda/ documentação MUST ser atualizada na mesma tarefa (Princípio XI), refletindo o painel de saúde ampliado.
- **FR-030**: O sistema MUST documentar, por componente, a cadeia Componente → Fonte → Método → Status possível → Ação em caso de falha (§9), sem inventar status que não possam ser determinados de forma confiável.

### Key Entities *(include if feature involves data)*

- **Componente de saúde (catálogo)**: entrada declarativa do catálogo existente da Central — key, nome, descrição, finalidade, capacidades (suporta teste? conduz a qual configuração?), função de derivação de status. Nenhuma tabela nova.
- **Estado do componente**: derivado em tempo de consulta — status padronizado (§7) + resumo de uma linha (§9) + momentos relevantes (último backup, próximo backup, última verificação) obtidos das fontes existentes.
- **Execução de teste**: ocorrência já suportada pela estrutura existente (`IntegrationExecution` + trilha de auditoria) — integração, operação, resultado, duração, ator, detalhe sanitizado. Nenhuma estrutura nova.

## 6. Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos dez componentes visíveis com status padronizado em uma única tela (`/admin/integracoes`), sem subpágina "Visão geral".
- **SC-002**: 0 operações caras ao abrir a página: 0 gerações de backup, 0 testes SMTP/LDAP/destino externo, 0 threads novos — verificado por testes que contam chamadas aos mecanismos existentes.
- **SC-003**: 0 ocorrências de credenciais/segredos em interface, logs, auditoria e mensagens de erro da Central (varredura na suíte, padrão da 032).
- **SC-004**: 100% das rotas da Central negam acesso a usuário sem permissão (negação padrão, auditada) — verificado por testes.
- **SC-005**: Todo teste manual conclui com resultado apresentado dentro de prazo máximo (≤ 10 s) e 100% dos testes registrados em histórico + auditoria.
- **SC-006**: 0 alterações de comportamento fora do previsto: suíte existente permanece 100% verde (baseline atual: 748 passed).
- **SC-007**: Backup externo inacessível ou GLPI indisponível (simulação controlada) NÃO quebra a aplicação: painel renderiza os demais componentes normalmente (falha isolada no card).
- **SC-008**: Painel responsivo nas larguras de referência (desktop grande/médio, notebook, tablet, celular) e nos temas claro/escuro, reutilizando componentes existentes (0 CSS global novo).
- **SC-009**: 0 tabelas novas e 0 migrações: toda a saúde é derivada das fontes existentes (§9).
- **SC-010**: Documentação e central de ajuda atualizadas na mesma tarefa, fiéis ao comportamento implementado.

## 7. Modelo de status padronizado (reutilizado da 032 — §7 da spec 032)

Vocabulário único da Central (já implementado em `integration_center_service.py`), com as cores do sistema visual existente:

| Cor | Status | Significado |
|---|---|---|
| Verde | OPERACIONAL / CONECTADO / OK / ATIVO | Componente saudável (Aplicação, Banco, Armazenamento, Backup Local/Externo, Agendador) ou integração operando |
| Amarelo | ATENÇÃO / CONFIGURADO MAS NÃO TESTADO / DEGRADADO | Configurado com ressalva; dependência parcialmente degradada |
| Vermelho | FALHA / INDISPONÍVEL / ERRO DE CONEXÃO | Falha comprovada pelo estado real (última execução/verificação/cópia) |
| Cinza | NÃO CONFIGURADO / DESABILITADO / NÃO APLICÁVEL | Ausente, desligado ou sem aplicabilidade |

Regras: sem cores arbitrárias por integração (badges existentes do sistema); precedência de derivação conforme a 032 (COM ERRO/INDISPONÍVEL refletem o evento mais recente; NÃO CONFIGURADO/DESABILITADO refletem a configuração efetiva; estados positivos são residuais); não inventar status que não possam ser determinados de forma confiável.

## 8. Consulta × Teste (fluxo obrigatório)

1. **Abrir a página = Consulta**: o painel deriva os estados das fontes existentes (configuração efetiva, `backup_records`, `scheduler_status()`, `retention_monitoring_summary()`, semântica do `/health`, registros da Central) — **zero I/O externo, zero operações caras** (NFR-004 da 032 mantido).
2. **"Testar" = ação explícita**: apenas nos componentes com mecanismo existente (AD, E-mail, GLPI quando implementado, Backup Externo) — delegação integral aos mecanismos vigentes, com timeout, resultado amigável, histórico e auditoria.
3. **"Atualizar" = recarregar a consulta**: nenhum endpoint novo de verificação em massa é criado; se algum componente precisar de teste ativo sob demanda, usa a ação de teste existente dele.
4. **Nova integração futura**: entra pelo catálogo (mecanismo da 032) — a Central não muda de estrutura.

## 9. Fonte de cada status (cadeia Componente → Fonte → Método → Status → Ação)

```text
Aplicação
 ↓
A própria aplicação responde (renderização da página); semântica do /health existente
 ↓
Leitura do estado da aplicação (sem verificação ativa adicional)
 ↓
OPERACIONAL / (indisponível = página não carrega, não é estado do painel)
 ↓
Falha: não interrompe a aplicação

Banco de Dados
 ↓
Conexão/config existente (mesma sessão do app; consulta simples já usada pelo /health)
 ↓
Consulta simples com tratamento de erro; exibição apenas do estado (sem tempo de resposta — decisão 2026-09-26)
 ↓
CONECTADO / FALHA
 ↓
Falha: card em erro; aplicação continua (padrão do /health: aplicação "degraded", não derrubada)

Armazenamento
 ↓
Diretórios de backup configurados (backup_config) + mecanismo padrão da plataforma (shutil.disk_usage)
 ↓
Existência dos diretórios + espaço livre calculado no momento da consulta; referência = tamanho do último backup válido
 ↓
OK / ATENÇÃO (espaço livre < tamanho do último backup válido) / FALHA (sem espaço para escrita ou diretório ausente)
 ↓
Falha: card em atenção/falha; nada é criado ou movido

Active Directory
 ↓
ad_settings + ad_ldap (teste de conexão existente, auditado) + semântica do /health
 ↓
Consulta: estado persistido (configurado/habilitado/último teste); Teste: ação explícita
 ↓
CONECTADO / FALHA / NÃO CONFIGURADO / DESABILITADO
 ↓
Falha: conduz à tela AD existente; autenticação de usuários permanece inalterada

E-mail
 ↓
email_config + SMTP_* (ambiente) + notificações existentes
 ↓
Consulta: configurado ou não; Teste: conexão + autenticação SMTP sem envio (mecanismo da 032)
 ↓
CONECTADO / NÃO CONFIGURADO / DESABILITADO / FALHA
 ↓
Falha: conduz à tela Notificações existente; nenhum e-mail real no teste

GLPI
 ↓
Catálogo da 032 (integração prevista — sem cliente no código)
 ↓
Representação honesta; teste somente quando a implementação existir (spec própria)
 ↓
NÃO CONFIGURADO (hoje) / CONECTADO / FALHA (futuro, com cliente real)
 ↓
Falha: não interrompe a aplicação (timeout/tratamento do mecanismo vigente)

1Doc
 ↓
onedoc_service + ONEDOC_* (implementada, aguardando fornecedor)
 ↓
Estado real: ONEDOC_ENABLED + registros existentes
 ↓
PENDENTE DE CONFIGURAÇÃO (hoje) / estados da 031 quando operacional
 ↓
Falha: reprocessamento pela via existente (fora do escopo desta feature)

Backup Local
 ↓
backup_records + retention_monitoring_summary (monitoramento existente da área de Backups)
 ↓
Leitura do resumo (último backup, último válido, válidos no disco, última falha, retenção)
 ↓
Agendador ATIVO: ATENÇÃO quando o ciclo esperado passa sem backup novo (folga de 1 ciclo); FALHA quando não há nenhum backup válido. Agendador DESABILITADO (regime manual): sem alerta por atualidade — espelha a última falha registrada; OK quando o estado existente é positivo
 ↓
Falha: conduz à área Administração → Backups (monitoramento completo já existente)

Backup Externo
 ↓
BackupExternalConfig + BackupExternalRecord (045) + test_destination existente
 ↓
Consulta: habilitado/destino/última cópia/última falha; Teste: "Testar destino" explícito
 ↓
OK / DESABILITADO / NÃO CONFIGURADO / FALHA (última cópia falhou / destino inacessível)
 ↓
Falha: conduz à configuração do destino externo existente; cópias futuras seguem o mecanismo da 045

Agendador de Backup
 ↓
backup_scheduler.scheduler_status() existente
 ↓
Leitura direta do estado (habilitado, agendamento, próximo run, último resultado, running)
 ↓
ATIVO / DESABILITADO / FALHA (último resultado com erro)
 ↓
Falha: conduz à configuração de backup automático existente; scheduler inalterado
```

## 10. Persistência e migração (§23 do pedido)

- **Nenhuma tabela nova, nenhuma coluna nova, nenhuma migração**: os estados de saúde são **calculados** das fontes existentes a cada consulta (configuração efetiva, registros de backup, `scheduler_status`, registros da Central). Não há histórico permanente de health checks nem tabela de estados derivados — nada aqui justifica persistência (a Central já mantém histórico **de execuções** nos mecanismos da 032, reutilizado para os testes manuais).
- Registros de testes manuais continuam seguindo o mecanismo vigente (`IntegrationExecution` + trilha de auditoria) — nenhuma estrutura nova.

## 11. Desempenho (§18 do pedido)

- A página não gera backup, não executa restore, não executa inventário, não faz consultas pesadas, não executa múltiplos testes demorados automaticamente, não abre conexões desnecessárias e não cria threads novos.
- Verificações ativas apenas por ação explícita de teste, respeitando os prazos dos mecanismos existentes (SC-005).
- Consultas de painel limitadas aos resumos já calculados pelos services existentes (sem varreduras ilimitadas).

## 12. Testes obrigatórios (§25 do pedido — mapeamento para a suíte)

Cenários do pedido (A–M) mapeados para a estratégia da suíte (fakes, nunca serviços externos reais):

- **A — Central acessível**: usuário autorizado abre `/admin/integracoes` e a página renderiza com os dez componentes (novo teste).
- **B — Banco**: banco disponível → status CONECTADO/OK (novo teste da status_fn).
- **C — GLPI**: GLPI disponível → CONECTADO — **condicionado à existência da integração**; hoje o teste equivale a "GLPI não configurado → NÃO CONFIGURADO" (teste da status_fn).
- **D — GLPI indisponível**: simulação controlada → falha sem quebrar a aplicação — aplicável quando o cliente GLPI existir; hoje: ausência de cliente não quebra o painel.
- **E — Backup externo disponível**: destino OK → status correto (teste da status_fn com config/registros semeados).
- **F — Backup externo indisponível**: última cópia com falha → status de falha; sistema não quebra (teste da status_fn).
- **G — AD**: disponível → status correto (reutiliza/estende os testes da 032).
- **H — E-mail**: configuração existente → status correto (reutiliza os testes da 032).
- **I — Agendador**: `scheduler_status` com estados variados → apresentação correta (novo teste da status_fn).
- **J — Responsividade** e **K — Dark mode**: verificação manual/medição nas larguras e temas de referência (registro em validação).
- **L — RBAC**: usuário sem permissão não acessa informações administrativas (reutiliza o padrão de testes RBAC vigente).
- **M — Regressão**: suíte completa verde (748 passed como baseline; SC-006).

## 13. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Duplicar mecanismos existentes (health, testes, scheduler) | §2/§9 obrigatórios no plan: cada verificação aponta o mecanismo reutilizado; revisão de conformidade |
| Painel executar I/O caro ao abrir (anti-padrão) | FR-005 + SC-002: testes contam chamadas aos mecanismos de teste — 0 ao renderizar |
| Componente de saúde quebrado derruba o painel | Edge case §4: isolamento por componente (try/except na derivação; card em erro, página de pé) |
| Exposição de segredos em nova superfície | FR-019 + SC-003: reutilização de mask/sanitize; varredura na suíte |
| Expectativa indevida de GLPI/1Doc funcionais | FR-015/FR-016: estados honestos; SC sobre representação fiel |
| Regressão no fluxo de backup/scheduler | FR-026 + SC-006: suíte verde; alteração limitada à leitura de estados |

## 14. Assumptions

- As permissões `integracoes.visualizar`/`integracoes.testar` (032) cobrem o escopo da Central de saúde — nenhuma permissão nova é criada (F10/FR-020).
- A verificação de armazenamento usa o mecanismo padrão da plataforma para espaço em disco; a regra de alerta (limites de atenção/falha) é definida no plan com justificativa simples (nenhuma regra equivalente existe hoje).
- "Tempo de resposta do GLPI" é exibido somente quando trivialmente obtível pelo mecanismo existente; para o Banco de Dados a decisão foi **apenas estado** (sem latência — clarify 2026-09-26); nenhum instrumento de medição novo é criado.
- O ambiente de testes não possui serviços externos reais: todos os testes usam fakes (padrão da suíte — F10/032).
- Aderência integral à Constitution v1.0.0: I (evolução incremental, menor alteração possível), II/III (camadas/services), VI (segurança/credenciais), VII (banco aditivo — aqui, nenhuma migração), VIII (testes), IX (auditoria), X (UI consistente), XI (documentação), XII (validação).

## 15. Pendências de decisão (decidir no `/speckit-plan`, estilo P-7 da 032)

- **P-1**: nomes finais das keys do catálogo para os novos componentes (ex.: `app`, `database`, `storage`, `backup_local`, `backup_externo`, `scheduler`) — detalhe de plan, seguindo o padrão existente (email/onedoc/ad/glpi).
- **P-2**: detalhamento da regra do Armazenamento decidida no clarify (ATENÇÃO = espaço livre abaixo do tamanho do último backup válido; FALHA = sem espaço para escrita) — fonte do "tamanho do último backup válido" e comportamento sem backup válido registrado: detalhes no plan.
- **P-3**: apresentação final do grid (ordem exata dos cards e agrupamento visual) — seguindo o mock do pedido (§19) e os componentes existentes.

## 16. Arquivos/módulos potencialmente afetados (preliminar — confirmar no plan)

- `app/services/integration_center_service.py` — **extensão do catálogo** (novas status_fn para os componentes de saúde, leitura das fontes existentes); nada das integrações existentes muda.
- `app/web/admin_routes.py` — ajustes pontuais no painel existente se necessário (ex.: passagem de resumos por componente); rotas novas **não** são esperadas.
- `app/web/templates/admin/integracoes/list.html` (+ `detail.html` quando aplicável) — apresentação da visão consolidada; nenhum template global alterado.
- `docs/` e central de ajuda — atualização na mesma tarefa.
- `tests/` — novo arquivo de testes da Central de saúde (status_fn dos componentes, RBAC, não-execução de operações caras ao renderizar) + fakes.
- **Intocáveis**: `app/main.py` (health check), `backup_service`, `backup_scheduler`, `external_backup_service`, `ad_service`/`ad_ldap`, `email_provider`/`notification_service`, `onedoc_*`, `permission_service` (nenhuma permissão nova), motor de movimentações, telas administrativas existentes fora da Central.

## 17. Relatório final esperado (§27 do pedido)

A implementação deverá encerrar com relatório informando: arquivos alterados e o porquê de cada alteração; componentes existentes reutilizados; verificações implementadas por componente (GLPI, backup externo, backup local, agendador, AD, e-mail, banco, armazenamento, aplicação); como os estados são determinados (cadeia §9); permissões reutilizadas; eventos de auditoria reutilizados/criados; testes executados e resultados; arquivos NÃO alterados e por quê; limitações encontradas — **sem inventar arquivos, testes ou funcionalidade não verificada**.
