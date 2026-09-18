# Phase 0 — Research: Backup Automático e Política de Retenção

> Todas as incógnitas do Technical Context foram resolvidas contra o código real (2026-09-18). Formato: Decisão → Rationale → Alternativas consideradas/rejeitadas.

---

## R1 — Tecnologia de agendamento: thread interna ao processo

**Decisão**: agendador próprio em **thread daemon do processo** (novo `app/services/backup_scheduler.py`), iniciado/parado no `lifespan` do FastAPI (`app/main.py`). Loop de verificação com intervalo curto (~30 s) calculando a próxima execução; disparo delegado ao `BackupService.generate_backup()`.

**Rationale**:
- O processo é **uvicorn único** (verificado na 017/019 — spec.md §1.2), sem múltiplos workers: uma thread em memória é suficiente e é a "menor solução compatível com a arquitetura" (briefing §7, Constitution I);
- Precisão de minutos é o requisito (horário HH:MM, não segundos): um despertar a cada 30 s garante disparo no minuto configurado com folga;
- Zero dependências novas (Princípio de stack da Constitution — Celery/Redis/RQ são vedados sem necessidade comprovada);
- Precedente do projeto: worker-thread com sessões próprias já existe no restore (019, `restore-worker-019`).

**Alternativas rejeitadas**:
- *Celery/Redis/RQ + broker*: infraestrutura externa nova (servidor + banco de broker) para uma tarefa de 1 execução/dia — proibida pelo briefing §7 e injustificada para processo único;
- *APScheduler*: dependência nova que reimplementa o que ~60 linhas resolvem; adicionalmente introduz mascaramento de job store que não usaremos;
- *cron do SO / Task Scheduler do Windows*: duplicaria a configuração em dois lugares (SO + sistema), não funcionaria identicamente nos dois SO (briefing §12 exige mecanismo único), e ficaria invisível ao monitoramento/auditoria do sistema;
- *BackgroundTasks do FastAPI*: acoplado ao ciclo request/response; não é um scheduler (não sobrevive sem request e não recalcula ciclos).

## R2 — Configuração: variáveis de ambiente (padrão do projeto)

**Decisão**: configuração exclusivamente por env vars em `app/config.py` (lidas APÓS `load_dotenv()`, guarda da 018):

| Variável | Default | Validação (no serviço) |
|---|---|---|
| `BACKUP_AUTO_ENABLED` | `"false"` | `"true"` ativa; qualquer outro valor = desativado (log registra valor desconhecido) |
| `BACKUP_AUTO_SCHEDULE` | `"daily"` | `daily` \| `weekly`; inválido → `daily` + log |
| `BACKUP_AUTO_TIME` | `"02:00"` | `HH:MM` (00:00–23:59); inválido → default + log |
| `BACKUP_AUTO_WEEKDAY` | `"0"` (domingo) | 0–6; usado só se `weekly`; inválido → default + log |
| `BACKUP_RETENTION_DAILY_DAYS` | `"30"` | inteiro ≥ 1 |
| `BACKUP_RETENTION_WEEKLY_WEEKS` | `"12"` | inteiro ≥ 1 |
| `BACKUP_RETENTION_MONTHLY_MONTHS` | `"12"` | inteiro ≥ 1 |
| `BACKUP_RETENTION_KEEP_PRE_RESTORE` | `"0"` | 0 = preservar todos os pré-restauração (default conservador); N > 0 = preservar os N mais recentes |

**Rationale**:
- Padrão vigente do projeto: **toda** configuração vive em `app/config.py` + `.env` (AD_*, AUTH_*, MYSQLDUMP_PATH, BACKUP_IMPORT_TIMEOUT) — não existe tabela de settings genérica; criar uma seria "nova arquitetura de banco" (vedado no briefing §41);
- "Não gravar números no código" (briefing §21) = a **regra** não é hardcoded; os valores são defaults seguros **documentados** e substituíveis por ambiente (briefing §8: "os valores padrão deverão ser documentados");
- Valores inválidos caem no default seguro com log (briefing §38 — não permitir configuração que provoque exclusão indiscriminada; FR-035/A9).

**Alternativas rejeitadas**:
- *Tabela de configurações + UI de edição*: mudança arquitetural de dados maior, exigiria CRUD/validação/auditoria próprios — não é a menor alteração; registrada como evolução futura candidata;
- *Arquivo YAML/JSON próprio*: terceiro mecanismo de configuração no projeto (já há env vars); confunde operação.

## R3 — Identificação de tipo: tabela nova `backup_records` (metadados), nome de arquivo intocado

**Decisão**: nova tabela `backup_records` (model `BackupRecord`, criada por `Base.metadata.create_all` — tabela nova não precisa de `ALTER`, mecanismo `_ensure_schema_migrations` fica intocado). O `generate_backup()` ganha parâmetro **aditivo** `backup_type: str = "MANUAL"` e grava o registro (sucesso **e** falha) na mesma transação da auditoria existente.

**Rationale**:
- Briefing §13: identificação **determinística**, "não depender somente do nome do arquivo se já existirem metadados adequados" — hoje **não existem** metadados; a única fonte é o nome, que não distingue tipo;
- O padrão de nome `backup_YYYYMMDD_HHMMSS_micros.sql(.gz)` é a âncora de segurança do Restore (regex estrita + path traversal): alterá-lo para embutir tipo (ex.: `backup_auto_...`) obrigaria a **mudar o Restore e toda a validação existente** — contraria o briefing §14 ("não alterar o formato atual sem necessidade") e o §5 (não modificar o Restore);
- Arquivos legados (pré-feature, sem registro): resolvidos por FR-014/A5 — tratados como **não elegíveis** à limpeza (conservador);
- Tipo é `VARCHAR(20)` com valores controlados no serviço (`MANUAL`/`AUTOMATICO`/`PRE_RESTAURACAO`) — vocabulário aditivo, sem enum de banco rígido (paridade com `assigned_by` de `user_roles`).

**Alternativas rejeitadas**:
- *Sufixo no nome do arquivo (`backup_auto_*`)*: quebra a regex/âncora atual, exige alterar Restore/listagem/validações — maior risco e contra §14; e o briefing pede explicitamente não depender só do nome;
- *Coluna em tabela existente*: não existe tabela de backups (listagem é derivada de arquivos) — não há onde adicionar;
- *JSON sidecar por arquivo*: metadados separados do histórico de auditoria, mais frágil (arquivo extra a sincronizar) e sem consulta SQL.

## R4 — Ciclo da execução automática: worker com sessões próprias + guardas em camadas

**Decisão**: o disparo do scheduler roda em **worker thread dedicada** (paridade `restore-worker-019`) com **sessões próprias e curtas** (`SessionLocal()`, abrir-fechar no ponto de uso). Guardas, em ordem:

1. `_AUTO_RUNNING` flag + `threading.Lock` em memória (paridade `_RESTORE_IN_PROGRESS`): segunda execução automática simultânea é **descartada com log** (FR-010/Teste M);
2. `restore_in_progress()` (guarda existente da 017): durante restore, o disparo **não executa** e é adiado para o próximo ciclo, com log (FR-011);
3. `generate_backup(..., _allow_during_restore=False)` — guarda existente reutilizada como defesa em profundidade.

Após a geração (sucesso **ou** falha), o worker executa a **retenção** (fluxo do briefing §6) e registra eventos de auditoria com ator `None` (sistema) — a auditoria do worker usa sessão própria (padrão `_worker_audit` da 019).

**Rationale**: para o import/dump não competir com transações abertas, a lição da 019 é: sessões curtas e nunca a sessão de request. Backup automático é de fundo, não há request — mesmo padrão aplicado preventivamente. Guardas em memória bastam (processo único).

**Alternativas rejeitadas**:
- *Disparo síncrono no thread do loop*: um dump de banco demorado atrasaria as verificações de agendamento e retém conexão por mais tempo;
- *Fila persistente de jobs*: infraestrutura nova sem necessidade (mesma rationale de R1).

## R5 — Próxima execução e catch-up: determinístico, sem cascata

**Decisão** (resolve FR-009/A4): regra **conservadora e determinística**:
- No start, o scheduler calcula `next_run` = próxima ocorrência do horário configurado (Recife → UTC, via `local_to_utc` da política da 004) estritamente **futuro**;
- **Catch-up**: se o horário do ciclo corrente já passou e **não existe** backup automático bem-sucedido registrado para aquele ciclo (`backup_records`, tipo `AUTOMATICO`, status sucesso, janela do ciclo), executa **uma única** execução de recuperação ~60 s após o start; se já existe registro de sucesso para o ciclo corrente, **não** re-executa;
- Nunca mais de 1 catch-up por start (sem cascata/compensação de ciclos perdidos múltiplos);
- A regra fica visível no monitoramento (campo "próxima execução").

**Rationale**: protege contra servidor desligado no momento do backup (janela perdida) sem criar rajada de dumps ao religar; determinístico (mesma entrada → mesma decisão, exigência do briefing §22–§24 para seleção e §10 para restart). 60 s de espera evita disparar dump durante o boot (init_db/pool aquecendo).

**Janela do ciclo corrente — definição precisa** (resolve F3):
- **Schedule `daily`**: o ciclo corrente é o **dia calendário em America/Recife** do relógio atual (`now_utc()` convertido para Recife). Horário do ciclo já passou = hora local atual ≥ `BACKUP_AUTO_TIME` (comparação HH:MM local). "Sucesso no ciclo" = existe `BackupRecord(AUTOMATICO/SUCCESS)` cujo timestamp (UTC) cai dentro desse dia-calendário local ( convertido: `[início do dia local 00:00, agora]`);
- **Schedule `weekly`**: o ciclo corrente é a **semana de agendamento iniciando às 00:00 local do `BACKUP_AUTO_WEEKDAY`** configurado — não é a semana ISO. Horário do ciclo já passou = dia local atual é o `WEEKDAY` configurado (ou posterior, dentro da mesma semana) e hora local ≥ `BACKUP_AUTO_TIME`. "Sucesso no ciclo" = registro SUCCESS com timestamp dentro dessa janela semanal local;
- Comparação e consulta sempre em UTC (conversão das bordas da janela com `local_to_utc`), sem criar nova política de fuso;
- Catch-up é avaliado UMA vez por start (flag em memória); nunca reavaliado a cada tick — sem cascata por definição.

**Alternativas rejeitadas**:
- *Nunca compensar (só próximo ciclo)*: até 24 h sem backup após um fim de semana com queda — conservador demais para proteção de dados;
- *Compensar todos os ciclos perdidos*: rajada de dumps inútil ao religar (só o último importa) — anti-padrão.

## R6 — Política de retenção: GFS determinístico ancorado em dias/semanas/meses

**Decisão**: retenção **GFS (Grandfather-Father-Son)** aplicada **somente** a registros `AUTOMATICO` com arquivo existente e integridade OK (verificada por `_gzip_read_status` da 016), usando o **timestamp persistido em `backup_records`** (UTC):

1. **Son (diário)**: todo automático mais antigo que `DAILY_DAYS` é elegível, **exceto** âncoras semanais/mensais preservadas;
2. **Father (semanal)**: por semana ISO (semana de segunda-feira), preserva o automático **mais recente** da semana enquanto a semana estiver dentro de `WEEKLY_WEEKS`... (determinístico: âncora = mais recente por bucket semanal);
3. **Grandfather (mensal)**: por mês-calendário, preserva o automático **mais recente** do mês enquanto o mês estiver dentro de `MONTHLY_MONTHS`.

Elegibilidade final exige, cumulativamente (briefing §30): tipo = AUTOMATICO → integridade OK → não protegido (nunca MANUAL, PRE_RESTAURACAO ou legado sem registro) → fora da janela/âncora → **não ser o último backup válido do sistema** (guarda do §28: se a remoção deixaria 0 válidos — considerando manuais e pré-restauração presentes — o arquivo é preservado e o motivo registrado).

Execução: **após cada execução automática** (briefing §6, A8) e a cada start (após catch-up decision). Cada remoção: 1 evento `BACKUP_REMOVIDO_RETENCAO`; resultado consolidado: `COMPLETA` (todos candidatos removidos) / `PARCIAL` (≥1 falha de remoção — nunca reportada como "concluída", §32) / `FALHA`. Falha por arquivo não interrompe os demais (§32: "10 candidatos, 8 removidos, 2 falharam → PARCIAL").

**Rationale**: GFS é o padrão de mercado para "30 diários, 12 semanais, 12 mensais" (briefing §21); âncora "mais recente por bucket" é determinística e reprodutível (briefing §23/§24 — "não selecionar aleatoriamente"); timestamp do registro (persistido) em vez do nome do arquivo atende §13 (metadados > nome); o nome só é usado para localizar o arquivo físico (via `get_backup_path`, que mantém a proteção anti-path-traversal — §31).

**Alternativas rejeitadas**:
- *Idade simples (delete tudo > X dias)*: viola §24 ("não apagar simplesmente todos os backups antigos ignorando a retenção semanal/mensal");
- *Últimos N arquivos*: não preserva pontos mensais/semanais definidos; sensível a ordem de execução;
- *Política separada por hora*: briefing não pede; escopo maior.

## R7 — Monitoramento: indicadores na tela existente (sem rota nova)

**Decisão**: a rota `GET /admin/backups` (existente, `backup.gerenciar`) recebe no contexto os indicadores: último automático (data/hora + status), próximo agendamento, último backup válido, última falha, última execução de retenção (resultado + removidos), quantidade de backups válidos, removidos pela retenção (total), falhas recentes. Fonte: `backup_records` (consultas no service) + `restore_status()`/estado do scheduler (memória). Template `admin/backups.html` ganha card **aditivo** com os componentes visuais atuais (badge/dd/small — paridade do card de restauração). A listagem existente ganha coluna "Tipo" aditiva (registro via metadados; legados exibem `—`).

**Rationale**: briefing §35 ("utilizar componentes visuais existentes; não redesenhar"); reuso de `backup.gerenciar` evita permissão nova (§37); indicadores derivados de dados persistidos sobrevivem a restart (§34).

**Alternativas rejeitadas**: *dashboard novo/rota separada*: mais superfície, quebra o padrão de consolidar na área de Backups; *endpoint JSON de métricas*: não foi pedido; monitoramento externo está fora de escopo (§34).

## R8 — Auditoria: 5 eventos novos aditivos

**Decisão**: constantes em `audit_service.py` (mecanismo `write_audit` existente, trilha imutável):

| Constante | Valor | Resultado típico |
|---|---|---|
| `ACTION_BACKUP_AUTO_SUCCESS` | `BACKUP_AUTOMATICO_SUCESSO` | SUCCESS |
| `ACTION_BACKUP_AUTO_FAILED` | `BACKUP_AUTOMATICO_FALHA` | FAILURE |
| `ACTION_RETENTION_EXECUTED` | `BACKUP_RETENCAO_EXECUTADA` | SUCCESS (com `{candidatos, removidos, falhas, resultado}`) |
| `ACTION_BACKUP_REMOVED_RETENTION` | `BACKUP_REMOVIDO_RETENCAO` | SUCCESS por arquivo (com `{motivo: expirado, faixa}`) ou FAILURE (falha de remoção) |
| `ACTION_RETENTION_FAILED` | `BACKUP_RETENCAO_FALHA` | FAILURE (erro inesperado do ciclo de retenção) |

Eventos equivalentes reutilizados: geração do dump continua gravando `BACKUP_CRIADO`/`BACKUP_FALHA` existentes (o automático adiciona o evento específico de tipo — sem duplicar o mecanismo, §36). Ator: usuário real no manual; `None`+description "sistema" no automático/retenção. **Nunca** segredos (Princípio VI).

**Rationale**: o briefing §36 lista exatamente esses cinco nomes; rótulos em `ACTION_LABELS` para a UI (padrão vigente).

**Alternativas rejeitadas**: *reusar `BACKUP_CRIADO` para tudo*: o briefing pede eventos próprios do automático (§36) e o monitoramento precisa filtrá-los; *nova tabela de eventos*: proibido — trilha única imutável (Princípio IX).

## R9 — Log técnico e tratamento de falhas: paridade com a 018

**Decisão**: o ciclo automático loga via `logging.getLogger(__name__)` → handler rotativo existente: etapa, exceção/exit code, stderr **sanitizado** (`_sanitize_stderr` existente — remove senha, limita 500 chars), tempo decorrido. Senha segue EXCLUSIVAMENTE no `MYSQL_PWD` do subprocesso (herdado da 018 — nada novo aqui, o automático simplesmente reusa o executor). Arquivo parcial: o mecanismo existente do `generate_backup` já remove `.part*` em `except` (BV-8 da 015) e audita falha — o automático registra o mesmo comportamento no `BackupRecord` (status FALHA, motivo). Falha de remoção na retenção: log + evento FAILURE individual (§32), sem mascarar a exceção original (FR-018).

**Rationale**: não criar segundo mecanismo de logging (§17); precedentes 015/016/018 já provaram o padrão (trilha imutável + stderr sanitizado).

**Alternativas rejeitadas**: *arquivo de log próprio do scheduler*: segundo mecanismo, vedado; *alertas e-mail/webhook*: fora de escopo (§34).

## R10 — Concorrência com backup manual e restore: comportamento definido

**Decisão**:
- Automático ↔ automático: segunda execução descartada (flag em memória, log técnico) — FR-010;
- Automático durante restore: adiamento para o próximo ciclo (guarda `restore_in_progress()`), log — FR-011;
- Manual durante automático: o manual **pode falhar** com `BackupError` de concorrência (mensagem clara, evento `BACKUP_FALHA` existente) — o comportamento de guarda existente é estendido à flag do automático; nenhuma fila é criada;
- Restore durante automático: possível tecnicamente, mas o restore ocupa o slot e bloqueia **novo** backup; o automático em curso termina antes (o restore já rejeita backup manual durante restore — paridade estendida).

**Rationale**: guardas simples em memória bastam no processo único (BV-R2 da 017); FR-010 exige evitar sobreposição "com mecanismo simples".

## R11 — Fuso horário: horário local para o operador, UTC para a máquina

**Decisão**: `BACKUP_AUTO_TIME` é informado/exibido em **America/Recife** (fuso da apresentação da 004); o scheduler converte para a base UTC com `local_to_utc()` (`app/utils/time_utils.py` — mecanismo central existente) e compara `now_utc()`. `backup_records.timestamp` persiste **UTC naive** (padrão dos models); a UI converte com filtro `localtime` existente.

**Rationale**: briefing §9 — "preservar a arquitetura UTC/America-Recife; não criar segunda política de timezone". Reuso do mecanismo central elimina qualquer conversão ad-hoc.

## R12 — Testabilidade: relógio e executores injetáveis

**Decisão**: `backup_scheduler` recebe dependências por parâmetro (padrão 015–019): `clock: Callable[[], datetime]` (default `now_utc`), `dump_executor` (delegado ao `generate_backup`), `sleep_fn`/`stop_event` para o loop. Testes controlam tempo sem `time.sleep` real. Suíte: `tests/test_backup_automatico.py` com SQLite em memória (restrição da Constitution — SQLite só em testes).

**Rationale**: a suíte atual testa backups com executor fake (R4 da 015); estender o mesmo padrão ao scheduler mantém os Testes A–M executáveis em CI determinístico.

---

## Incógnitas resolvidas do briefing

| Item do briefing | Resolução |
|---|---|
| §7 tecnologia de agendamento | R1 (thread interna) |
| §8/§21 configuração e valores | R2 (env vars, defaults seguros) |
| §13/§14 identificação e nomenclatura | R3 (`backup_records`; nome intocado) |
| §10/§FR-009 comportamento pós-restart | R5 (catch-up único determinístico) |
| §22–§24 seleção por faixas | R6 (GFS determinístico) |
| §25/§26 proteção de manuais/pré-restauração | R6 + `BACKUP_RETENTION_KEEP_PRE_RESTORE` (default 0 = preservar todos) |
| §28 último backup válido | R6 (guarda antes de cada remoção) |
| §29 falha de backup × limpeza | R4 (retenção roda após ciclo; se FALHA, guarda do §28 e conservadorismo prevalecem — remoções continuam vedadas para 0 válidos e manuais; FR-021 preservado) |
| §32 limpeza parcial | R6 (resultado PARCIAL com falhas individuais auditadas) |
| §34–§35 monitoramento | R7 (card aditivo na tela existente) |
| §36 auditoria | R8 (5 eventos) |
| §37 RBAC | R7 (reuso `backup.gerenciar`; nenhuma permissão nova) |
| §12 Windows/Linux | R1/R4 (thread + executor herdam 018; quickstart cobre os 2 SO) |
| §9 fuso | R11 (local_to_utc + localtime) |
