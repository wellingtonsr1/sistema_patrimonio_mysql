# Feature Specification: Backup Automático e Política de Retenção — SisPatrimônio Pro

**Feature Branch**: `020-backup-automatico-retencao`
**Título**: Backup automático agendado com política de retenção configurável no SisPatrimônio Pro
**Data**: 2026-09-18
**Input**: Briefing completo "Backup Automático e Política de Retenção" (seções 1–44), com regra central do operador: **o backup automático deve reutilizar o mecanismo de Backup Manual existente, e a retenção deve atuar somente sobre os backups que forem elegíveis**.

---

## 1. Contexto e análise obrigatória (somente leitura, realizada nesta especificação)

> O briefing exige (§3, §6, §44) que a implementação parta da análise do sistema real — nada presumido. Os fatos abaixo foram verificados no código em 2026-09-18 e ancoram cada requisito desta spec.

### 1.1 Mecanismo de backup existente (features 015/016/017/019, em produção)

| Aspecto | Realidade verificada | Relevância para esta feature |
|---|---|---|
| Serviço único de geração | `BackupService.generate_backup()` (`app/services/backup_service.py`): dump via `mysqldump`/`mariadb-dump` em subprocesso, compressão gzip streaming, validação (existe, > 0 bytes, gzip legível), SHA-256 streaming, rename atômico `.part.gz` → `.sql.gz` | **Ponto único de extensão** — o disparo automático DEVE chamar este serviço; é PROIBIDO um segundo mecanismo de dump |
| Executor injetável | `generate_backup(db, user, ip, *, dump_executor=None, _allow_during_restore=False)` | O disparo automático usa o executor padrão de produção; os testes injetam fakes (padrão já estabelecido pela suíte) |
| Identificação | Apenas o **nome do arquivo**: `backup_YYYYMMDD_HHMMSS_micros.sql(.gz)` — regex estrita `_BACKUP_NAME_RE` (âncora anti path-traversal). Não existe coluna/tabela de metadados de backup; **não existe campo de tipo** (manual × automático × pré-restore) | A distinção de tipo exigida pelo briefing (§13) precisa de **metadados novos e aditivos** (ver §1.3); o padrão de nome não pode ser quebrado (Restore e validações dependem dele) |
| Armazenamento | `data/backups/` (`BACKUP_DIR` em `app/config.py`), criado on-demand | Mesmo diretório para todos os tipos — a retenção NUNCA apaga fora dele |
| Integridade | `list_backups()` calcula `integrity` (OK / CORROMPIDO / —) e `sha256` por arquivo, on-demand | A retenção reutiliza essa mesma verificação — nunca remove um backup cuja integridade não pôde ser confirmada como OK |
| Auditoria | `audit_service.write_audit()` — trilha única imutável; eventos existentes: `BACKUP_CRIADO`, `BACKUP_DOWNLOAD`, `BACKUP_FALHA`, `BACKUP_PRE_RESTORE`, `BACKUP_RESTORE_STARTED/SUCCESS/FAILED` | Novos eventos são **aditivos** (§36 do briefing); o mecanismo é reutilizado, nunca duplicado |
| Log técnico | `logging.getLogger(__name__)` → handler rotativo `data/logs/app.log` (5 MB × 5) | Mesmo mecanismo; diagnóstico sem segredos (senha vai só no `MYSQL_PWD` do subprocesso) |
| Permissões RBAC | `backup.gerenciar` (015 — gerar/listar/baixar) e `backup.restaurar` (017 — restore); deny-by-default, seed idempotente concede ao Administrador | A configuração do automático/retenção reutiliza `backup.gerenciar` (§37) — não há permissão nova prevista |
| Credenciais | Senha do banco EXCLUSIVAMENTE no ambiente do subprocesso (`MYSQL_PWD`); stderr sanitizado (`_sanitize_stderr`) | Padrão obrigatório preservado — automático e retenção nunca logam segredos |
| Concorrência | `_RESTORE_LOCK` + `_RESTORE_IN_PROGRESS` (estado em memória do processo, uvicorn único): durante restore, novo restore e backup manual são rejeitados | O automático DEVE respeitar o mesmo guard: não dispara durante restore; e precisa de guarda própria contra sobreposição de duas execuções automáticas |
| Restore | `restore_backup()` (fluxo 019: validação → slot → worker → backup de segurança → drenagem do pool → import → validação pós) | Não deve ser modificado além do estritamente necessário (briefing §5); aceita qualquer arquivo do padrão existente — backups automáticos serão restauráveis por construção |

### 1.2 Execução, agendamento e tempo

| Aspecto | Realidade verificada | Consequência para o design |
|---|---|---|
| Processo | `uvicorn.run("app.main:app", reload=False)` — **processo único**, sem workers múltiplos, sem Celery/Redis/APScheduler, sem jobs em background além do worker-thread do restore (019) | O agendamento DEVE ser interno ao processo (thread agendadora simples) — menor solução compatível; infraestrutura externa é proibida sem necessidade comprovada (briefing §7, Constitution I) |
| Persistência de configuração | Variáveis de ambiente via `app/config.py` (`.env`) — não há tabela de settings genérica | A configuração do automático/retenção segue o padrão existente: variáveis de ambiente com defaults seguros e documentados (briefing §8/§21: "não gravar números no código") |
| Fuso horário | Feature 004: **persistência em UTC naive** (`now_utc()`), **apresentação em America/Recife** (`utc_to_recife`, filtro `localtime`); `local_to_utc()` existe para converter entrada local → UTC | O horário de agendamento é informado/apresentado em **America/Recife** e convertido para a base de agendamento pela política existente — nenhuma segunda política de timezone (briefing §9) |
| Restart | Nada em memória sobrevive a restart; `maintenance_mode` da 019 é deliberadamente em memória (crash-safe por construção) | Após restart, o agendador recalcula a próxima execução a partir da configuração e do histórico persistido — comportamento previsível e documentado (briefing §10) |

### 1.3 Estado do histórico e do tipo de backup

- **Histórico atual**: a trilha `audit_logs` já registra geração (com `{arquivo, tamanho_bytes, sha256}`), download e falhas — mas não existe estrutura que responda "qual é o último backup automático válido" sem varredura de eventos, e não existe marcação de tipo.
- **Tipo de backup**: `BACKUP_MANUAL` e `BACKUP_PRE_RESTAURACAO` existem como conceitos operacionais (fluxo de restore gera backup de segurança com `_allow_during_restore=True`), mas **não há identificador persistido** que os distinga de um backup automático.
- **Consequência**: esta feature introduz a identificação determinística de tipo de forma **aditiva e idempotente** (alteração controlada de schema conforme Constitution VII — `init_db` + `_ensure_schema_migrations`), sem alterar o formato de arquivo, o padrão de nome nem o Restore (briefing §13/§14/§5). O mecanismo concreto (coluna/tabela) é decisão do `/speckit-plan`.

### 1.4 O que está fora do escopo (briefing §41 — limites da feature)

- Refatoração de módulos não relacionados; troca de framework/banco; segundo mecanismo de dump ou de restore;
- Monitoramento externo, e-mail, notificações, nuvem/replicação;
- Alterações em AD, autenticação, usuários, colaboradores, patrimônio, movimentações, inventário, relatórios;
- Alteração dos perfis RBAC existentes ou das permissões de backup já existentes;
- Remoção/renomeação de colunas ou tabelas existentes (apenas alterações aditivas idempotentes — Constitution VII);
- Backup de arquivos de log ou de artefatos do filesystem além do banco.

---

## 2. Problema

O sistema só gera backup quando uma pessoa clica no botão. Isso significa que:

1. **A proteção depende de disciplina humana** — um período movimentado ou a ausência do operador deixa o sistema sem cópias recentes;
2. **O diretório cresce indefinidamente** — não existe retenção: cada geração e cada backup de segurança pré-restore acumula para sempre, consumindo disco (a limpeza hoje é manual e feita "no dedo", sem trilha);
3. **Não há como saber, de relance**, quando foi o último backup válido ou se o backup está funcionando — só auditando eventos;
4. **Não há distinção persistida** entre um backup feito por pessoa, pelo sistema ou pelo fluxo de restore — impossível aplicar política de limpeza seletiva e segura.

---

## 3. Objetivo

Implementar no SisPatrimônio Pro, de forma incremental sobre o mecanismo existente:

1. **Backup automático**: disparo agendado que reutiliza integralmente `BackupService.generate_backup()` (mesmo dump, mesma compressão, mesma validação, mesmo diretório, mesmo padrão de nome);
2. **Agendamento** configurável (ativado/desativado, frequência, horário) com fuso respeitando a política UTC/America-Recife da feature 004;
3. **Identificação determinística** do tipo de cada backup gerado (manual, automático, pré-restauração) — aditiva, sem quebrar o formato atual;
4. **Política de retenção** configurável que atua **somente sobre backups elegíveis** (automáticos), com proteção explícita de manuais e pré-restauração;
5. **Limpeza segura** que nunca deixa o sistema sem nenhum backup válido e registra cada operação;
6. **Histórico** preservado independentemente do arquivo físico;
7. **Tratamento de falhas** que nunca apresenta falso sucesso;
8. **Monitoramento** administrativo (indicadores na área de Backups existente) e **auditoria** pelos mecanismos existentes.

---

## 4. User Stories e Testes Independentes

### US1 — Backup automático dispara e reutiliza o mecanismo existente (P1) 🎯 MVP

**Como** administrador do sistema, **quero** que o sistema gere backup automaticamente na frequência e horário configurados, **para que** eu tenha cópias de segurança recentes sem depender de ação manual.

**Fluxo (briefing §6)**: agendamento interno dispara → chama o **mesmo** `BackupService.generate_backup()` existente (dump → compressão → validação → SHA-256) → arquivo criado no mesmo diretório e padrão de nome, identificado como automático → registrado no histórico e na Auditoria → retenção aplicada ao final.

**Independent Test**: com o agendamento ativado e o relógio simulado no horário configurado, um arquivo de backup válido (gzip íntegro, padrão existente) é gerado, identificado como `BACKUP_AUTOMATICO`, e os eventos de auditoria correspondentes são registrados — sem que o botão manual seja usado. (Testes A, B, P do briefing)

**Acceptance Scenarios**:

1. **Given** backup automático ativado com horário configurado, **When** o horário chega, **Then** um backup válido é gerado pelo serviço existente e registrado como automático no histórico e na Auditoria.
2. **Given** backup automático ativado, **When** a geração conclui com validação OK, **Then** o backup aparece na listagem existente de Backups, restaurável pelo mecanismo de restore atual (Teste P — nenhum formato novo).
3. **Given** backup automático desativado, **When** o horário configurado chega, **Then** nenhum backup é gerado.

### US2 — Agendamento configurável e previsível após restart (P1)

**Como** administrador, **quero** configurar se o backup automático está ativado, sua frequência e horário — e saber o que acontece quando o servidor reinicia — **para que** o comportamento seja controlado por mim e previsível.

**Independent Test**: alterar a configuração (via variáveis de ambiente) e reiniciar a aplicação → o agendador reflete a nova configuração; após restart com backup ativado, a próxima execução é recalculada de forma determinística e documentada. (Testes N, O)

**Acceptance Scenarios**:

1. **Given** frequência diária e horário 02:00 (America/Recife) configurados, **When** a aplicação inicia, **Then** a próxima execução corresponde ao próximo 02:00 local e a interface de monitoramento a exibe.
2. **Given** o processo reiniciado após o horário configurado do dia, **When** o agendador recalcula, **Then** o comportamento (executar imediatamente ou aguardar o próximo ciclo) segue a regra documentada na especificação/plan — sem ambiguidade.
3. **Given** configuração inválida (ex.: horário malformado), **When** a aplicação inicia, **Then** o sistema adota o default seguro documentado, registra em log técnico o valor inválido ignorado, e não falha o start.

### US3 — Sem execuções simultâneas nem conflito com restore (P1)

**Como** administrador, **quero** que duas execuções de backup automático não se sobreponham e que o automático não dispute recursos com uma restauração em andamento, **para que** o sistema nunca fique em estado inconsistente.

**Independent Test**: simular um disparo enquanto outro backup automático ainda executa → o segundo é ignorado/adia com registro em log; simular horário do automático durante um restore → o disparo não inicia backup. (Teste M)

**Acceptance Scenarios**:

1. **Given** um backup automático em execução, **When** um novo disparo agendado ocorre, **Then** apenas um backup executa; o segundo disparo é descartado e o fato registrado em log técnico.
2. **Given** uma restauração em andamento (guarda 017/019 ativa), **When** o horário do backup automático chega, **Then** o disparo não gera backup durante o restore e segue a regra documentada (adiar para o próximo ciclo).
3. **Given** backup automático em execução, **When** um usuário tenta gerar backup manual pela tela existente, **Then** o comportamento existente de guarda de concorrência é preservado (o manual pode ser rejeitado com mensagem clara, sem impacto no automático).

### US4 — Identificação determinística do tipo de backup (P1)

**Como** administrador, **quero** que o sistema distinga backup manual, automático e pré-restauração de forma determinística, **para que** a retenção possa selecionar com segurança quem é elegível à limpeza.

**Independent Test**: gerar um backup de cada tipo (manual pela tela, automático pelo agendador, pré-restauração pelo fluxo de restore) → cada um apresenta seu tipo de forma confiável na listagem/histórico, sem depender exclusivamente do nome do arquivo. (Base dos Testes G–I)

**Acceptance Scenarios**:

1. **Given** um backup gerado pelo botão manual existente, **When** consultado o histórico/listagem, **Then** seu tipo é `BACKUP_MANUAL`.
2. **Given** um backup gerado pelo disparo automático, **When** consultado o histórico/listagem, **Then** seu tipo é `BACKUP_AUTOMATICO`.
3. **Given** um backup de segurança gerado pelo fluxo de restauração existente, **When** consultado o histórico/listagem, **Then** seu tipo é `BACKUP_PRE_RESTAURACAO`.
4. **Given** backups gerados antes desta feature (arquivos pré-existentes sem tipo persistido), **When** consultados, **Then** recebem tratamento documentado (ex.: classificados como manuais/legados — i.e., **não elegíveis** à limpeza por padrão).

### US5 — Retenção conservadora que só apaga elegíveis (P1)

**Como** administrador, **quero** que a limpeza automática remova apenas backups automáticos expirados conforme a política configurada, preservando manuais, pré-restauração e o último backup válido, **para que** o sistema nunca perca sua única cópia de recuperação.

**Independent Test**: criar conjunto de backups (automáticos dentro/fora do prazo, manual antigo, pré-restauração, corrompido) → executar retenção → somente automáticos elegíveis e íntegros são removidos; manuais e pré-restauração permanecem; se a remoção deixaria 0 backups válidos, nada é removido e o motivo é registrado. (Testes G, H, I, J)

**Acceptance Scenarios**:

1. **Given** um backup automático mais antigo que o prazo configurado, **When** a retenção executa, **Then** ele é removido e o registro histórico correspondente é preservado, marcado como removido pela retenção (Teste L).
2. **Given** um backup manual antigo, **When** a retenção executa, **Then** ele NÃO é removido (briefing §25 — por padrão manuais não participam da limpeza).
3. **Given** um backup pré-restauração, **When** a retenção executa, **Then** ele NÃO é removido indiscriminadamente — segue a política específica definida para ele (ver FR-021).
4. **Given** uma limpeza que deixaria o diretório com 0 backups válidos, **When** a retenção executa, **Then** a exclusão não ocorre e o motivo é registrado (briefing §28).
5. **Given** um backup cujo arquivo não pôde ser removido (permissão/uso), **When** a retenção executa, **Then** o resultado é "falha" para aquele arquivo, a limpeza prossegue com os demais elegíveis e o resultado final é reportado como **parcial** — nunca "concluída" (briefing §32).

### US6 — Falhas honestas e diagnósticáveis (P1)

**Como** administrador, **quero** que toda falha do backup automático ou da retenção seja registrada como falha — sem falso sucesso — com diagnóstico técnico no log, **para que** eu possa confiar no status exibido e descobrir a causa.

**Independent Test**: forçar falhas (executável inexistente, subprocesso com erro, timeout, arquivo parcial, falta de espaço/permissão simulada) → o backup é marcado como FALHA no histórico, evento de auditoria de falha gravado, log técnico contém etapa/código/erro sanitizado, e nenhum arquivo parcial é tratado como backup válido. (Testes C, D, E, F, K)

**Acceptance Scenarios**:

1. **Given** o utilitário de dump indisponível, **When** o disparo automático executa, **Then** o resultado é FALHA, registrado no histórico e na Auditoria, com diagnóstico no log técnico — e nenhum falso sucesso.
2. **Given** a geração que produziu arquivo parcial, **When** a execução falha, **Then** o artefato parcial não é classificado como backup válido, é removido de forma segura (a falha de remoção também é registrada) e não aparece como ponto de restauração.
3. **Given** uma falha de limpeza de arquivo elegível, **When** a retenção executa, **Then** o evento registra resultado de falha para aquele arquivo, preservando os backups válidos existentes (briefing §29 — falha de backup não dispara limpeza agressiva).

### US7 — Monitoramento e auditoria na área existente (P2)

**Como** administrador, **quero** ver na área de Backups existente os indicadores do backup automático e da retenção, **para que** eu acompanhe a saúde das cópias sem ferramentas externas.

**Independent Test**: acessar a tela de Backups com permissão adequada → indicadores exibidos: último backup automático (data/hora e status), último backup válido, última falha, última execução de retenção/limpeza, quantidade de backups válidos e removidos — usando os componentes visuais existentes. (Briefing §34/§35)

**Acceptance Scenarios**:

1. **Given** backups automáticos já executados, **When** o administrador abre a área de Backups, **Then** os indicadores do §34 são exibidos com dados do histórico.
2. **Given** eventos de backup automático e retenção, **When** consultada a Auditoria existente, **Then** os eventos novos aparecem com data/hora, resultado, tipo, arquivo/identificador e motivo — sem segredos.

---

## 5. Requisitos Funcionais

### Reutilização do mecanismo existente (briefing §2/§4/§6/§44)

- **FR-001**: O backup automático DEVE reutilizar `BackupService.generate_backup()` (mesmo dump via utilitário nativo, mesma compressão gzip, mesmas validações, mesmo SHA-256, mesmo diretório `data/backups/`, mesmo padrão de nome de arquivo) — é PROIBIDO criar um segundo mecanismo de geração de backup.
- **FR-002**: O formato dos arquivos e o padrão de nomenclatura existentes NÃO DEVEM ser alterados; a identificação do tipo NÃO DEVE depender exclusivamente do nome do arquivo.
- **FR-003**: O mecanismo de Restauração existente NÃO DEVE ser modificado além do estritamente necessário para esta feature; backups automáticos válidos DEVEM ser restauráveis pelo fluxo atual sem adaptação.
- **FR-004**: O botão, o fluxo, as permissões e o comportamento do Backup Manual existentes DEVEM permanecer inalterados.

### Agendamento e disparo (briefing §7/§8/§10/§11/§12)

- **FR-005**: O sistema DEVE executar backup automaticamente conforme configuração de: ativado/desativado, frequência (mínimo: diário) e horário (HH:MM) — com valores padrão seguros e documentados (default: **desativado**).
- **FR-006**: A configuração NÃO DEVE ter valores de política gravados hardcoded; os parâmetros devem ser configuráveis por variáveis de ambiente (padrão do projeto, `app/config.py` + `.env`), documentados no README.
- **FR-007**: O agendamento DEVE respeitar a política de tempo da feature 004: horário configurado e exibido em **America/Recife**, operação interna coerente com a persistência UTC — sem criar segunda política de timezone.
- **FR-008**: O agendamento DEVE ser interno ao processo da aplicação (menor solução compatível); nenhuma infraestrutura externa (Celery, Redis, RQ, servidor extra, banco extra) pode ser adicionada sem necessidade comprovada nesta spec.
- **FR-009**: Após reinicialização da aplicação/processo/servidor, o comportamento DEVE ser determinístico e documentado: o agendador recalcula a próxima execução a partir da configuração vigente; a regra para execução imediata (catch-up) versus aguardo do próximo ciclo DEVE estar definida no plano e refletida no monitoramento.
- **FR-010**: Nenhuma execução simultânea: se um backup automático já está em execução, o novo disparo DEVE ser descartado (com registro em log técnico); o sistema DEVE reutilizar/prever guardas simples compatíveis com a arquitetura de processo único.
- **FR-011**: O disparo automático NÃO DEVE gerar backup durante uma restauração em andamento (guarda existente da 017/019); nesse caso, a execução é adiada para o próximo ciclo, com registro.
- **FR-012**: A solução DEVE funcionar de forma idêntica em Linux e Windows, reutilizando a correção multiplataforma da feature 018 (resolução de executável via `MYSQLDUMP_PATH`/PATH, ambiente herdado + `MYSQL_PWD`) — sem mecanismo específico por SO.

### Identificação, histórico e validação (briefing §13/§14/§15/§19/§20/§33)

- **FR-013**: O sistema DEVE identificar deterministicamente cada backup gerado com um tipo: `BACKUP_MANUAL`, `BACKUP_AUTOMATICO` ou `BACKUP_PRE_RESTAURACAO` — por metadados persistidos (estrutura nova, aditiva e idempotente, conforme Constitution VII), não apenas pelo nome do arquivo. *(Equivalência de vocabulário: os rótulos `BACKUP_*` do briefing são os identificadores conceituais; os valores persistidos no metadado são `MANUAL`, `AUTOMATICO` e `PRE_RESTAURACAO` — sem prefixo —, conforme definido no design; a listagem/UI exibem o conceito correspondente.)*
- **FR-014**: Backups pré-existentes à feature (sem tipo persistido) DEVEM receber classificação documentada e conservadora: tratados como não elegíveis à limpeza automática (equivalente a manual/legado).
- **FR-015**: Todo backup automático DEVE ser registrado no histórico com, quando disponível: data/hora, tipo, status (sucesso/falha), arquivo, tamanho, integridade e motivo da falha — reutilizando a Auditoria existente e/ou os metadados da FR-013 (o plano decide a fonte de cada campo; proibido duplicar mecanismos).
- **FR-016**: Um backup automático só pode ser considerado CONCLUÍDO quando: processo de geração retornou sucesso **e** o arquivo existe **e** possui conteúdo **e** a validação de integridade retorna OK — caso contrário, o status é FALHA (nunca falso sucesso).
- **FR-017**: A remoção de um arquivo pela retenção NÃO DEVE remover seu registro histórico; o registro deve indicar que o arquivo foi removido pela política de retenção.

### Falhas e arquivos parciais (briefing §16/§17/§18/§29)

- **FR-018**: As falhas do backup automático DEVEM ser tratadas (executável inexistente, erro de subprocesso, código de retorno ≠ 0, erro do SGBD, falta de espaço, permissão negada, diretório inexistente, erro de compactação, timeout, arquivo inválido, falha de validação), sem mascarar a exceção original no log técnico.
- **FR-019**: O log técnico DEVE registrar, quando disponível: tipo da exceção, mensagem técnica, etapa que falhou, código de retorno e stderr sanitizado — e NUNCA registrar senha, `DATABASE_URL` com senha, token, credencial ou segredo (padrão `_sanitize_stderr`/`MYSQL_PWD` da 018).
- **FR-020**: Arquivo parcial de execução falha: não pode ser classificado como backup válido, deve ser removido com segurança (a falha de remoção também é registrada) e nunca disponibilizado como ponto de restauração.
- **FR-021**: Em caso de falha do backup automático, a retenção NÃO DEVE executar limpeza que reduza as cópias válidas existentes; os backups válidos são preservados.

### Política de retenção e limpeza segura (briefing §21–§32)

- **FR-022**: A política de retenção DEVE ser configurável por variáveis de ambiente, com valores iniciais: diária **30 dias**, semanal **12 semanas**, mensal **12 meses** (parâmetros iniciais, não hardcoded).
- **FR-023**: A retenção DEVE atuar **somente sobre backups automáticos elegíveis** (tipo `BACKUP_AUTOMATICO` com integridade OK e fora do prazo configurado).
- **FR-024**: Backups `BACKUP_MANUAL` NÃO PODEM ser removidos pela limpeza automática por padrão, mesmo antigos.
- **FR-025**: Backups `BACKUP_PRE_RESTAURACAO` NÃO PODEM ser removidos indiscriminadamente: a política específica para eles (ex.: preservação total por padrão) DEVE ser definida no plano e documentada — conservadora por padrão.
- **FR-026**: Antes de excluir qualquer arquivo, o sistema DEVE verificar: tipo elegível, integridade OK, não estar protegido (manual/pré-restauração/associado a operação), e regras de retenção aplicáveis — arquivos protegidos são preservados.
- **FR-027**: A limpeza NUNCA DEVE deixar o sistema com 0 backups válidos: se a exclusão resultaria em nenhum backup válido restante, a exclusão não ocorre e o motivo é registrado.
- **FR-028**: A limpeza DEVE ser segura e determinística: localizar somente arquivos do armazenamento oficial (regex estrita existente), identificar tipo, verificar status/integridade/proteção/retenção, excluir somente elegíveis e registrar cada operação; é PROIBIDO apagar por padrão de extensão ou o conteúdo do diretório.
- **FR-029**: A limpeza DEVE impedir path traversal: nenhum valor fornecido por usuário pode determinar livremente qual arquivo excluir — somente arquivos reconhecidos dentro do diretório oficial são candidatos.
- **FR-030**: Falha na remoção de um arquivo: resultado individual = FALHA, registro na Auditoria, prosseguimento com os demais candidatos quando seguro; resultado geral reportado como LIMPEZA PARCIAL (nunca "concluída" nesse cenário).
- **FR-031**: A seleção dos pontos preservados por faixa (diária/semanal/mensal) DEVE ser determinística — nenhum sorteio aleatório; a regra exata de classificação por faixa DEVE estar definida no plano.

### Monitoramento, auditoria e RBAC (briefing §34–§37)

- **FR-032**: A área administrativa de Backups existente DEVE apresentar indicadores de monitoramento, reutilizando componentes visuais existentes: último backup automático (data/hora/status), último backup válido, último backup com falha, última execução de retenção e limpeza, quantidade de backups válidos e removidos, falhas recentes.
- **FR-033**: A Auditoria existente DEVE registrar os eventos novos de forma aditiva, reutilizando eventos equivalentes quando existirem: sucesso/falha de backup automático, retenção executada, backup removido por retenção, falha de retenção — com data/hora, resultado, tipo, arquivo/identificador, motivo e quantidade afetada quando aplicável; nunca segredos.
- **FR-034**: A configuração do backup automático e da retenção DEVE respeitar o RBAC existente (deny-by-default); deve-se reutilizar permissão adequada existente (`backup.gerenciar`) e somente criar permissão nova se indispensável — nada de alterar perfis sem necessidade.
- **FR-035**: A interface de configuração/monitoramento NÃO PODE permitir valores que provoquem exclusão indiscriminada (validação de faixas/valores configuráveis, com defaults conservadores).
- **FR-036**: Toda a feature DEVE operar identicamente nos dois ambientes suportados (Linux e Windows), herdando o comportamento multiplataforma do serviço de backup existente.

---

## 6. Critérios de Sucesso

### Measurable Outcomes

- **SC-001**: Com o backup automático ativado no padrão diário, um backup válido é gerado no horário configurado **sem nenhuma ação manual** — verificado em ao menos 2 ciclos simulados e 1 execução real em Linux e 1 em Windows (Testes N/O).
- **SC-002**: 100% dos backups gerados (manual, automático, pré-restauração) apresentam tipo determinístico consultável — nenhum backup sem classificação.
- **SC-003**: Após a retenção executar sobre um conjunto misto de backups, **0 backups manuais e 0 pré-restauração são removidos** e **0 arquivos fora do padrão/diretório são tocados** — verificação por teste automatizado.
- **SC-004**: Em nenhum cenário de teste a limpeza deixa o sistema com menos de 1 backup válido (guarda do último válido confirmada em teste).
- **SC-005**: Toda execução automática (sucesso ou falha) gera registro no histórico e evento de auditoria correspondente — 100% das execuções dos testes auditadas.
- **SC-006**: Nenhuma mensagem de log/auditoria contém senha, `DATABASE_URL` com senha, token ou segredo — verificado nos testes de segurança (Teste Q).
- **SC-007**: A suíte pytest existente permanece verde (Constitution VIII) e os novos comportamentos possuem cobertura automatizada (Testes A–M, P, Q; N e O executados nos ambientes reais).
- **SC-008**: O administrador visualiza os indicadores do §34 na área de Backups existente sem navegar para outra ferramenta.

---

## 7. Key Entities

- **Backup (arquivo)**: dump comprimido do banco em `data/backups/`, padrão de nome existente `backup_YYYYMMDD_HHMMSS_micros.sql(.gz)`; atributos observáveis: timestamp, tamanho, integridade (OK/CORROMPIDO/—), SHA-256.
- **Tipo de backup (novo metadado)**: classificação determinística do backup — conceitos `BACKUP_MANUAL`, `BACKUP_AUTOMATICO`, `BACKUP_PRE_RESTAURACAO` (valores persistidos: `MANUAL`, `AUTOMATICO`, `PRE_RESTAURACAO` — ver FR-013); persistido de forma aditiva (Constitution VII); backups anteriores à feature são classificados como não elegíveis.
- **Configuração de backup automático**: ativado/desativado, frequência, horário (America/Recife), parâmetros de retenção (dias/semanas/meses por faixa) — fornecida por variáveis de ambiente com defaults documentados.
- **Execução de backup automático (registro)**: ocorrência histórica de um disparo — data/hora, tipo, status (sucesso/falha), arquivo gerado (quando houver), tamanho, integridade, motivo da falha; preservada mesmo após a remoção física do arquivo.
- **Execução de retenção (registro)**: ocorrência de limpeza — data/hora, resultado (concluída/parcial/falha), quantidade de candidatos, removidos e falhas, motivo das não-exclusões (proteção/último válido).

---

## 8. Assumptions

- **Assumption 1 — Agendador interno**: dado processo único uvicorn sem jobs externos (verificado), um agendador por thread interna é suficiente e é a menor solução compatível (briefing §7); infraestrutura externa fica explicitamente fora.
- **Assumption 2 — Configuração por ambiente**: a configuração do automático/retenção segue o padrão do projeto (variáveis de ambiente em `app/config.py`/`.env`), pois não existe tabela de configurações genérica; alterar isso para "configuração em banco via UI" implicaria nova arquitetura de dados, fora da menor alteração necessária (briefing §41 — reportado como possível evolução futura).
- **Assumption 3 — Frequência mínima viável**: o briefing admite "Diário/Semanal/etc."; a spec exige diário como frequência obrigatória da primeira entrega; semanal/mensal (e a separação de faixas de retenção diária/semanal/mensal) são configuráveis conforme o plano — os três prazos de retenção do §21 são parâmetros padrão da política.
- **Assumption 4 — Catch-up após restart**: sem histórico de "último disparo automático bem-sucedido do ciclo corrente", a regra conservadora é aguardar o próximo ciclo configurado (nunca disparar em cascata ao ligar o servidor); a definição final e o ajuste fino ficam no `/speckit-plan`, documentados e visíveis no monitoramento.
- **Assumption 5 — Backups legados**: arquivos pré-existentes à feature não têm tipo persistido; por conservadorismo são tratados como não elegíveis à limpeza (Assumption/FR-014), alinhado à proteção de manuais (§25).
- **Assumption 6 — Backup de segurança pré-restore**: continua sendo gerado pelo mesmo serviço (017/019) e passa a ser identificado como `BACKUP_PRE_RESTAURACAO` pelos novos metadados — sem mudança de fluxo do restore além da marcação.
- **Assumption 7 — Permissão reutilizada**: a área de configuração/monitoramento reutiliza `backup.gerenciar` (briefing §37 prioriza reuso); nova permissão só se o plano evidenciar indispensabilidade (reportaria na revisão da spec).
- **Assumption 8 — Retenção executada ao final do backup automático** (fluxo do briefing §6): a limpeza roda após uma execução automática concluída (e pode ser executada junto do ciclo; execução manual sob demanda é opcional e decidida no plano).
- **Assumption 9 — Horário e frequência validados**: valores fora das faixas aceitáveis (ex.: frequência desconhecida, HH:MM inválido, retenção 0/negativa que provocaria exclusão imediata) caem no default seguro documentado, com registro em log (briefing §38 — validação e defaults conservadores).
