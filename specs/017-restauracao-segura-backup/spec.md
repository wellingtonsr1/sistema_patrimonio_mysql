# Feature Specification: Restauração Segura de Backup — SisPatrimônio Pro

**Feature Branch**: `017-restauracao-segura-backup`
**Título**: Restauração segura de backup do SisPatrimônio Pro
**Data**: 2026-09-17
**Input**: Briefing completo "Feature 2 — Restauração Segura de Backup" (seções 1–40)

**Input**: Briefing completo "Feature 2 — Restauração Segura de Backup" (seções 1–40)

---

## 1. Contexto e análise obrigatória (somente leitura, realizada nesta especificação)

> O briefing exige (§3, §6, §7) que a implementação parta da análise do sistema real — nada presumido. Os fatos abaixo foram verificados no código em 2026-09-17 e ancoram cada requisito desta spec.

### 1.1 Mecanismo de backup existente (Feature 1 — features 015 e 016, em produção)

| Aspecto | Realidade verificada | Relevância para esta feature |
|---|---|---|
| Banco de dados | **MariaDB 10.6**, banco `sispatrimoniopro`, via `DATABASE_URL` (`.env`, parseado em `app/config.py`) — driver MySQL + SQLAlchemy | O restore usará o cliente **mysql/mariadb** nativo (presente em `/usr/bin/`), compatível com o dump gerado |
| Formato dos backups | `backup_YYYYMMDD_HHMMSS_micros.sql.gz` (gzip, feature 016) e `backup_YYYYMMDD_HHMMSS_micros.sql` (legado, feature 015) — regex estrita `^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$` | O restore deve aceitar **ambos** os formatos existentes (§35) e rejeitar qualquer nome fora do padrão |
| Listagem | `BackupService.list_backups()` — derivada dos arquivos em `data/backups/`, ordenada desc, com `integrity` (OK / — / CORROMPIDO) e `sha256` | A seleção do backup reutiliza exatamente essa listagem (§9) |
| Download/validação de nome | `BackupService.get_backup_path()` — rejeita path traversal e `.part*` com `FileNotFoundError` → 404 | A resolução do arquivo para restore reutiliza essa mesma função (§19) |
| Integridade | `integrity == "OK"` = gzip legível integralmente; `CORROMPIDO` = leitura falhou; `—` = `.sql` sem checksum | Backup com integridade `CORROMPIDO` **não** pode ser restaurado (§8); `—` é restaurável (formato válido, sem checksum) |
| Geração de backup | `BackupService.generate_backup()` com executor injetável; auditoria `BACKUP_CRIADO`/SUCCESS com `{arquivo, tamanho_bytes, sha256}` | O **backup de segurança pré-restore** reutiliza esse serviço (§14/§15) — sem segundo mecanismo |
| Permissão | `backup.gerenciar` (catálogo RBAC, seed idempotente concede ao Administrador; deny-by-default) | Nova permissão distinta para restore (§32) — restore é mais destrutivo que backup |
| Auditoria | `audit_service.write_audit()` — trilha única e imutável; constantes `BACKUP_CRIADO`, `BACKUP_DOWNLOAD`, `BACKUP_FALHA` | Novos eventos aditivos (§30), mesmo mecanismo |
| Log técnico | `logging.getLogger(__name__)` → handler rotativo `data/logs/app.log` (precedente em `backup_service.py`) | Diagnóstico sem segredos (§31) |
| Credenciais | Senha do banco vai **exclusivamente** no ambiente do subprocesso (`MYSQL_PWD`) — nunca em argv/logs/erros | Mesmo padrão obrigatório no subprocesso de restore (§34) |

### 1.2 Estado da aplicação, sessões e conexões (análise §21–§23)

| Aspecto | Realidade verificada | Consequência para o design |
|---|---|---|
| Execução | `uvicorn.run("app.main:app", reload=False)` — **processo único**, sem workers múltiplos e sem jobs em background | O bloqueio de restore concorrente pode ser um estado **em memória do processo** (simples e suficiente); não há risco de outro processo competir |
| Sessões | **Server-side**: tabela `user_sessions` com hash SHA-256 do token; cookie guarda o token; `get_session_user` consulta o banco a cada requisição | Sessões vivem no **banco**: após restaurar um backup antigo, tokens de sessão posteriores ao backup deixam de existir → esses cookies invalidam-se naturalmente. Sessões que existiam no backup voltam a valer — comportamento coerente com "voltar no tempo", a documentar na UI |
| Pool de conexões | SQLAlchemy `QueuePool` (`pool_size=10`, `max_overflow=20`, `pool_recycle=1800`, `pool_pre_ping=True`) | Conexões do pool permanecem abertas ao mesmo servidor/banco — o cliente `mysql` atua no mesmo database; `pool_pre_ping` detecta conexões mortas. Nenhuma reconstrução de pool é necessária para restaurar tabelas; **dados já carregados em memória em requisições em andamento** podem ficar obsoletos — mitigado pelo bloqueio concorrente e pela natureza operacional (restore é ação rara e planejada) |
| Cache em memória | Nenhum cache de domínio identificado no código (consultas diretas por request) | Não há invalidação a fazer (§23) — documentar |
| Estado durante o restore | A operação de restore é síncrona e dura segundos (dump atual ≈ 200 KB comprimido) | Exigência mínima viável: flag em memória impede **segundo restore** e **geração de backup manual** durante o processo; demais operações seguem (são atômicas por requisição) |

### 1.3 O que está fora do escopo (§5 — reproduzido como limite da feature)

Backup automático/agendamento/cron/scheduler; retenção automática ou exclusão de backups; nuvem/replicação/sincronização; troca de SGBD/ORM/autenticação/RBAC/auditoria; qualquer módulo patrimonial (inventário, movimentações, manutenção, colaboradores, equipamentos).

**Especificamente NÃO implementado nesta feature** (§29/§28): exclusão automática do backup de segurança; segunda restauração automática de recuperação (rollback automático via backup de segurança) — se o restore falhar, o backup de segurança é preservado e listado para eventual **restauração manual** pelo operador.

---

## 2. Problema

A Feature 1 permite gerar, listar e baixar backups, mas a **recuperação de dados depende de procedimento manual fora do sistema** (acesso ao servidor, execução do import pelo administrador de banco). Isso:

1. **Atrasa a recuperação** em incidentes (o operador precisa de acesso shell/SSH e conhecimento do comando `mysql`);
2. **É propenso a erros** — não há validação, backup de segurança prévio nem trilha de auditoria do procedimento manual;
3. **Deixa rastro zero** — a restauração manual não é registrada na Auditoria do sistema;
4. **Não preserva o estado atual** — nada obriga a criar um backup de segurança antes de sobrescrever os dados.

---

## 3. Objetivo

Implementar no SisPatrimônio Pro uma **restauração segura de backup**, permitindo que um usuário autorizado:

1. visualize os backups disponíveis (mecanismo existente);
2. selecione um backup;
3. visualize informações do backup antes da confirmação;
4. confirme **explicitamente** a restauração (duas etapas);
5. tenha um **backup de segurança do estado atual** criado e validado automaticamente antes de qualquer alteração;
6. execute a restauração com a ferramenta compatível com o banco real;
7. tenha o resultado **validado** (não apenas "comando retornou 0");
8. tenha **todo o processo registrado na Auditoria existente**;
9. receba tratamento de falhas que **nunca apresente sucesso falso** e **sempre preserve o backup de segurança**;
10. não deixe o sistema em estado inconsistente (proteção contra restaurações concorrentes).

---

## 4. User Stories e Testes Independentes

### US1 — Restaurar um backup válido (P1) 🎯 MVP

**Como** administrador autorizado, **quero** selecionar um backup disponível e restaurá-lo após confirmação explícita e criação de backup de segurança, **para que** eu recupere o estado dos dados em incidente de forma controlada e auditável.

**Fluxo (§2, §10, §11)**: acessar a área de Backups → ver ação **Restaurar** (somente autorizados) → tela de informações do backup (arquivo, data/hora, tamanho, integridade + advertência clara) → **Continuar** → tela de confirmação explícita (**"SIM, RESTAURAR BACKUP"**) → sistema cria **backup de segurança pré-restore** → valida → executa restore → valida resultado → mensagem de sucesso com os dois arquivos (restaurado + segurança).

**Independent Test**: Usuário autorizado + backup válido + confirmação → backup de segurança existe e é OK → banco contém os dados do backup → validação pós-restore OK → eventos de auditoria registrados. (Teste A)

### US2 — Operação inacessível a não autorizados (P1)

**Como** usuário sem permissão de restauração, **quero** não ver nem conseguir executar a restauração por nenhuma via, **para que** a operação destrutiva fique restrita a quem foi explicitamente autorizado.

**Independent Test**: usuário sem permissão não vê a ação (UI), recebe acesso negado no endpoint (backend deny-by-default), não gera backup de segurança e não altera o banco. (Testes B, F)

### US3 — Cancelamento e validações que impedem o restore (P1)

**Como** administrador, **quero** poder cancelar a qualquer momento e quero que o sistema **se recuse a restaurar** backups inválidos, inexistentes ou corrompidos — e que nada aconteça com o banco nessas situações, **para que** a operação nunca comece em condições inseguras.

**Independent Test**: cancelar em qualquer etapa → nenhuma alteração, nenhum backup de segurança desnecessário; backup corrompido/inexistente/fora do padrão → restauração não iniciada, banco preservado, evento registrado quando apropriado. (Testes C, D, E, F)

### US4 — Falhas seguras e proteção de concorrência (P1)

**Como** administrador, **quero** que falhas no backup de segurança ou no restore **nunca sejam apresentadas como sucesso** e que o backup de segurança permaneça disponível; e que duas restaurações não possam ocorrer simultaneamente, **para que** o sistema nunca fique em estado inconsistente ou sem caminho de recuperação.

**Independent Test**: falha ao criar o backup de segurança → restore não inicia, banco intacto; falha no restore → falha registrada, nenhum falso sucesso, backup de segurança preservado e listado; segundo restore enquanto um está em andamento → rejeitado com mensagem clara. (Testes G, H, J)

### US5 — Confiança no resultado (P2)

**Como** administrador, **quero** que o sistema **valide o resultado após o restore** (conexão, tabelas essenciais, dados essenciais) antes de informar sucesso, **para que** eu possa confiar na mensagem "Restauração concluída".

**Independent Test**: após restore válido → verificação de conexão + tabelas principais + consultas somente-leitura de dados essenciais passam → sucesso informado com detalhes. (Teste I)

---

## 5. Requisitos Funcionais

### Reutilização da Feature 1 (§4, §15)

- **FR-01**: O fluxo de restore DEVE reutilizar o serviço de listagem de backups existente para apresentar os backups disponíveis — sem duplicar listagem, armazenamento ou cálculo de integridade.
- **FR-02**: O backup de segurança pré-restore DEVE ser gerado pelo serviço de backup existente (mesmo mecanismo, mesmo diretório, mesmo padrão de nome, integridade verificável), imediatamente antes do restore — sem criar um segundo mecanismo de backup.
- **FR-03**: A resolução do arquivo selecionado DEVE reutilizar a validação existente de nome/caminho (regex estrita + resolução no diretório autorizado), que já bloqueia `../`, `../../` e equivalentes — restauração de arquivo fora do padrão/diretório é impossível.

### Seleção, informação e confirmação (§9–§12)

- **FR-04**: A ação de restauração DEVE aparecer apenas para usuários autorizados (condição de permissão na UI).
- **FR-05**: Antes da confirmação, o sistema DEVE apresentar: nome do arquivo, data/hora, tamanho, integridade — e advertência explícita de que os dados atuais serão substituídos e de que um backup de segurança será criado. Nenhuma restauração pode iniciar nesta etapa.
- **FR-06**: A confirmação DEVE ser explícita e em duas etapas (informações → confirmação final com botão inequívoco "SIM, RESTAURAR BACKUP"). A restauração NÃO pode ser disparada por: abrir página, selecionar arquivo, clique único, GET ou carregamento de página.
- **FR-07**: A confirmação DEVE incluir controle contra acidentes (modal/confirm com advertência, botão identificado e estado de processamento), compatível com o padrão visual existente.

### Endpoint e método (§13)

- **FR-08**: A restauração DEVE ser executada por operação de escrita (POST), seguindo o padrão de rotas administrativas existente — nunca por GET. Nenhum endpoint paralelo desnecessário.

### Validações pré-restore (§8, §16, §35)

- **FR-09**: Antes de qualquer alteração, o sistema DEVE validar o backup selecionado: arquivo existe, está dentro do diretório autorizado, formato reconhecido (`.sql.gz` ou `.sql` legado), tamanho válido, legível como dump e **não marcado como CORROMPIDO** pela listagem. Falha em qualquer item → **restauração não iniciada** e banco intocado.
- **FR-10**: O backup de segurança criado DEVE ser validado (existe, tamanho > 0, gzip legível/integridade OK) antes do restore iniciar. Qualquer falha → **restore cancelado**, banco atual intacto, falha registrada.

### Backup de segurança (§14, §15, §28)

- **FR-11**: O backup de segurança é **obrigatório e prévio**: se não puder ser criado, a restauração NÃO pode ser iniciada. Ele DEVE permanecer disponível após sucesso **ou** falha do restore (nunca excluído automaticamente) e não pode ser confundido com o backup restaurado.
- **FR-12**: O backup de segurança DEVE ser identificável como anterior a uma restauração para o operador (distinguível na listagem existente sem quebrar o padrão de nome da Feature 1 — p.ex. via metadado do evento de auditoria e/ou marcador não conflitante com a regex existente).

### Execução do restore (§17, §18, §19)

- **FR-13**: O restore DEVE importar o dump com a ferramenta nativa compatível com o banco real (cliente mysql/mariadb), configurada pelo ambiente autorizado (mesma `DATABASE_URL` do sistema, sem possibilidade de alteração via interface).
- **FR-14**: O processo de restore NÃO pode aceitar da interface: comandos SQL, comandos de shell, caminho/host/usuário/arquivo arbitrário — somente a seleção de um backup já listado pelo sistema.
- **FR-15**: A senha do banco DEVE ser passada exclusivamente pelo ambiente do subprocesso (`MYSQL_PWD`), nunca em argv, logs, erros ou auditoria — mesmo padrão da Feature 1.

### Concorrência e estado (§20, §21, §22, §23)

- **FR-16**: O sistema DEVE impedir restaurações concorrentes: enquanto um restore está em andamento, novas tentativas DEVEM ser rejeitadas com mensagem clara (mecanismo mínimo compatível com a execução em processo único).
- **FR-17**: Durante o restore, o sistema DEVE impedir também a geração de backup manual (evita dois subprocessos de dump/restauração simultâneos sobre o mesmo banco) — bloqueio mínimo, sem filas nem infraestrutura adicional.
- **FR-18**: Sessões: como são server-side no banco, o comportamento pós-restore (tokens posteriores ao backup deixam de existir; sessões contemporâneas ao backup voltam a valer) DEVE ser documentado na interface de confirmação — nenhuma invalidação arbitrária além do comportamento natural.
- **FR-19**: Nenhum novo mecanismo de cache: o sistema não possui cache de domínio em memória (verificado); nenhuma invalidação adicional é necessária — registrado como análise, não como requisito de código.

### Validação pós-restore (§24, §25)

- **FR-20**: Após a importação, o sistema DEVE validar: conexão ativa, consulta simples executável, existência das tabelas essenciais do sistema e acesso somente-leitura aos dados essenciais (usuários/colaboradores/equipamentos, conforme estrutura real). **Sucesso não pode ser declarado apenas porque o comando retornou código 0.**
- **FR-21**: Toda validação pós-restore DEVE ser somente leitura — nenhum dado modificado durante a verificação.

### Falhas (§26, §27)

- **FR-22**: Em falha de qualquer etapa (validação do backup, backup de segurança, importação, validação pós-restore): nenhuma mensagem de sucesso; falha registrada na Auditoria com motivo **seguro** (sem credenciais/conteúdo do dump); usuário informado de forma controlada.
- **FR-23**: Se o restore falhar no meio da importação (possibilidade de estado parcial), o sistema DEVE: registrar explicitamente a falha, preservar o backup de segurança e orientar o operador à restauração manual do backup de segurança — **sem implementar rollback automático** nesta feature (decisão documentada).

### Auditoria e log (§30, §31)

- **FR-24**: Toda a operação DEVE ser registrada exclusivamente na Auditoria existente, com eventos aditivos: `BACKUP_RESTORE_INICIADO` (solicitada), `BACKUP_PRE_RESTORE_CRIADO` (backup de segurança), `BACKUP_RESTORE_SUCESSO`, `BACKUP_RESTORE_FALHA` — sem segundo mecanismo de auditoria.
- **FR-25**: Auditoria e log técnico NÃO podem conter: senha, token, credencial, `DATABASE_URL` com senha, segredo ou conteúdo integral do dump.

### RBAC (§32, §33)

- **FR-26**: A restauração DEVE exigir permissão própria (p.ex. `backup.restaurar`), distinta da permissão de backup — criar/gerenciar backups não implica autorizar sobrescrever todos os dados. Padrão RBAC existente (catálogo + seed idempotente concedendo ao Administrador; deny-by-default).
- **FR-27**: Usuário não autorizado: não vê a ação (UI), recebe acesso negado no endpoint (backend), não inicia backup de segurança, não altera o banco — e a tentativa é auditada conforme o mecanismo existente para acessos negados.

### Compatibilidade (§35)

- **FR-28**: Backups válidos existentes da Feature 1 (`.sql` e `.sql.gz`) DEVEM continuar reconhecidos e restauráveis; a solução NÃO pode invalidar backups existentes. Incompatibilidade detectável (p.ex. arquivo ilegível) → rejeição segura com mensagem clara — extensão correta não é garantia de restaurabilidade.

---

## 6. Regras

1. **Regra principal (§2)**: nunca substituir os dados atuais sem confirmação explícita **e** sem backup de segurança prévio validado.
2. **Ordem invariável (§40)**: validar backup → confirmar → criar backup de segurança → validar backup de segurança → restaurar → validar resultado → auditar. Nunca "selecionou → restaurou".
3. **Menor alteração (§38)**: somente arquivos diretamente necessários; nenhuma refatoração; nenhuma substituição de mecanismos existentes (backup, auditoria, autenticação, RBAC).
4. **Fluxo de falha (§26/§28)**: preservar o backup de segurança sempre; nunca apresentar sucesso sem validação pós-restore aprovada.
5. **Preservação (§3/§37)**: backups existentes, permissão de backup, tela e fluxos da Feature 1 permanecem funcionando inalterados.

---

## 7. Critérios de Aceitação

| ID | Critério | Origem |
|---|---|---|
| AC-01 | Usuário autorizado consegue selecionar um backup listado pelo mecanismo existente | §37; Teste A |
| AC-02 | O backup selecionado é validado (existência, diretório, formato, tamanho, legibilidade, não-corrompido) antes da restauração | §8/FR-09; Teste D/E |
| AC-03 | A restauração exige confirmação explícita em duas etapas e não é executável por GET | §11/§13/FR-06/FR-08; Teste C |
| AC-04 | Backup de segurança do estado atual é criado automaticamente antes de qualquer alteração, pelo mecanismo existente | §14/§15/FR-02/FR-11; Teste A |
| AC-05 | O backup de segurança é validado antes do restore; se falhar, o restore não começa e o banco fica intacto | §16/FR-10; Teste G |
| AC-06 | O restore usa a ferramenta nativa compatível com o banco real (MariaDB) e a configuração autorizada do ambiente | §6/§17/FR-13 |
| AC-07 | Arquivos fora do diretório autorizado e path traversal são bloqueados | §19/FR-03; Teste F |
| AC-08 | Usuários não autorizados não executam restore por nenhuma via (UI + backend), sem alterar o banco | §33/FR-26/FR-27; Teste B |
| AC-09 | Restaurações concorrentes são rejeitadas (uma por vez); backup manual também bloqueado durante o restore | §20/FR-16/FR-17; Teste J |
| AC-10 | O resultado do restore é validado (conexão, tabelas, dados essenciais) antes de informar sucesso — nunca sucesso só por retorno 0 | §24/§25/FR-20; Teste I |
| AC-11 | Falhas nunca são apresentadas como sucesso; motivo seguro registrado | §26/FR-22; Teste H |
| AC-12 | O backup de segurança permanece disponível (sucesso ou falha), nunca excluído automaticamente | §28/FR-11 |
| AC-13 | Auditoria existente registra os 4 eventos do ciclo; sem segredos | §30/§31/FR-24/FR-25 |
| AC-14 | Logs técnicos não contêm segredos | §31/FR-25 |
| AC-15 | Backups existentes da Feature 1 continuam funcionando (listagem/download/geração inalterados) | §35/FR-28; Teste K |
| AC-16 | O sistema permanece operacional após restauração válida | §24/FR-20 |
| AC-17 | Nenhuma funcionalidade não relacionada é alterada | §37/§38 |

---

## 8. Cenários de Validação (Testes Obrigatórios §36)

| Teste | Cenário | Esperado |
|---|---|---|
| A | Autorizado + backup válido + confirmação + backup de segurança criado + restore + validação | SUCESSO; backup de segurança listado; dados do backup vigentes; auditoria completa |
| B | Usuário não autorizado tenta restore | ACESSO NEGADO (backend); banco inalterado; sem backup de segurança; tentativa auditada |
| C | Selecionar backup e cancelar a confirmação | Nenhuma restauração; nenhum backup de segurança desnecessário; banco inalterado |
| D | Backup corrompido/inválido selecionado | Restore NÃO iniciado; banco preservado; auditoria registrada |
| E | Backup inexistente | Restore NÃO iniciado |
| F | Path traversal (`../`, `../../`) | Acesso negado/bloqueado; nada restaurado |
| G | Falha ao criar o backup de segurança | Restore NÃO iniciado; banco atual preservado; falha registrada |
| H | Falha durante o restore (simulada) | Falha registrada; NENHUM falso sucesso; backup de segurança preservado e listado |
| I | Validação pós-restore após restore válido | SELECT simples + tabelas essenciais + dados essenciais → OK |
| J | Duas restaurações simultâneas | Somente uma executa; outra rejeitada com mensagem clara |
| K | Regressão completa do projeto | Login, RBAC, usuários, colaboradores, equipamentos, locais, movimentações, inventário, manutenção, relatórios, auditoria, AD, **backup manual** e demais módulos continuam passando |

---

## 9. Assumptions (decisões documentadas — informed guesses)

1. **Permissão distinta para restore** (`backup.restaurar`): o briefing deixa em aberto reutilizar `backup.gerenciar` ou criar permissão nova ("Analisar se já existe uma permissão adequada... Caso seja necessária uma nova"). Decisão: permissão própria, pois restaurar sobrescreve todos os dados (inclusive usuários e permissões) — impacto maior que gerar backup. O Administrador recebe automaticamente via seed idempotente.
2. **Bloqueio em memória do processo**: suficiente pela execução em uvicorn de processo único (`reload=False`, sem workers extras) — verificado. Se no futuro houver múltiplos workers, o mecanismo terá de ser revisto (documentado como limitação).
3. **Sessões**: invalidação natural (server-side no banco) aceita como comportamento correto e documentado na confirmação — sem mecanismo adicional de revogação.
4. **`-` (sem checksum) é restaurável**: backups `.sql` legados não têm checksum, mas são dumps válidos; a validação de legibilidade substitui a verificação de checksum nesse caso.
5. **Sem rollback automático** (§27): a ferramenta de import do MariaDB não provê rollback transacional cross-statement de forma segura para este caso; a mitigação é o backup de segurança preservado + orientação ao operador (requisito FR-23), alinhada ao briefing.
6. **Duração síncrona**: dumps atuais (~200 KB comprimido) permitem restore síncrono em segundos; a UI precisa apenas de estado de processamento e o bloqueio concorrente cobre a janela de execução.

---

## 10. Key Entities

- **Backup** (existente, Feature 1): arquivo em `data/backups/` com padrão estrito de nome, timestamp UTC, tamanho, integridade (OK/—/CORROMPIDO), sha256 quando aplicável — consumido como está.
- **Backup de segurança pré-restore** (novo papel, mesmo artefato): backup gerado pelo mecanismo existente imediatamente antes do restore, identificável para o operador (FR-12), nunca excluído automaticamente.
- **Operação de restauração** (novo conceito efêmero, sem tabela): ciclo validar → confirmar → segurança → restaurar → validar, com estado "em andamento" em memória para proteção de concorrência (FR-16) — persistência zero (zero DDL).
- **Permissão `backup.restaurar`** (nova): catálogo RBAC, módulo Backup, seed idempotente ao Administrador.
- **Eventos de auditoria** (novos, aditivos): `BACKUP_RESTORE_INICIADO`, `BACKUP_PRE_RESTORE_CRIADO`, `BACKUP_RESTORE_SUCESSO`, `BACKUP_RESTORE_FALHA`.

---

## 11. Impacto esperado

> Somente componentes confirmados pela análise do código (Seção 1) — nada inventado.

**NOVO**: módulo de testes da restauração (`tests/test_backup_restore.py`).

**Aditivo (arquivos existentes)**:
- `app/services/backup_service.py` — funções de restore (validação, import via cliente nativo, validação pós-restore, flag de operação em andamento), reutilizando `_BACKUP_NAME_RE`, `get_backup_path`, `list_backups`, `generate_backup` e o padrão de credenciais `MYSQL_PWD`;
- `app/web/admin_routes.py` — rotas de confirmação/POST do restore com a nova permissão (padrão existente);
- `app/web/templates/admin/backups.html` — ação Restaurar (condicionada à permissão), telas de informações/confirmação, estado de processamento e notas de sessão;
- `app/web/templates/base.html` — nenhum item novo de menu (restaurar vive dentro de Administração → Backups); alteração eventualmente desnecessária;
- `app/services/permission_service.py` — +1 permissão `backup.restaurar` no catálogo (seed idempotente);
- `app/services/audit_service.py` — +4 constantes/rótulos de eventos;
- `app/services/help_service.py` + `README.md` — documentação do restore, do backup de segurança e do comportamento de sessões.

**Intocado**: rota e fluxo de geração/listagem/download da Feature 1 (além das funções reutilizadas), models, migrations, demais módulos.

---

## 12. Restrições verificadas

- **Zero DDL**: nenhuma tabela nova; estado do restore em memória; backup de segurança é artefato de arquivo (padrão da Feature 1).
- **Zero novos eventos destrutivos fora da Auditoria existente.**
- **Prioridade máxima (§40)**: preservar o sistema existente e proteger os dados atuais — qualquer alteração não indispensável para o restore seguro NÃO será feita.
