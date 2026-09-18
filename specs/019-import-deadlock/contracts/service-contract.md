# Contract: Correção do Deadlock da Restauração (feature 019)

Contratos dos caminhos afetados. Tudo o que não está listado aqui permanece **byte-idêntico** ao comportamento atual.

## 1. Service — `app/services/backup_service.py`

### 1.1 `restore_backup(db, user, ip_address, filename, *, import_executor=None, security_backup_executor=None)` — assinatura preservada, fluxo dividido

| Aspecto | Contrato |
|---|---|
| Papel novo | **Valida, audita início e agenda**: valida o arquivo (`validate_restore_source`) e registra `BACKUP_RESTORE_INICIADO` como hoje (worker via sessão própria); cria o backup de segurança pré-restore (worker); então **retorna ANTES do import**, deixando o ciclo destrutivo (import + validação pós + eventos finais) para a worker thread |
| Retorno | `Dict` com estado "agendada/em andamento" (rota responde **303** — padrão de redirect do fluxo web — e a tela de backups faz polling). Em falha de validação: mesmas exceções/mensagens de hoje. Parametros de teste `import_executor`/`security_backup_executor` preservados (fakes da 017 continuam válidos) |
| Sessão | A sessão `db` recebida NÃO é usada no ciclo destrutivo (R5/D4): eventos do worker usam sessões próprias curtas; a rota devolve a sessão imediatamente (request encerra antes do import) |
| Estado | Ocupa o slot de concorrência EXISTENTE da 017 (`_RESTORE_LOCK`/`_RESTORE_IN_PROGRESS`/`_restore_slot` — sem mecanismo paralelo, FR-011) + `maintenance_mode` ativo ANTES da thread iniciar (nenhuma janela sem manutenção) |

### 1.2 Worker thread `_execute_restore_cycle(filename, security_backup_path)`

| Aspecto | Contrato |
|---|---|
| Sessões | Exclusivamente `SessionLocal()` próprias, abertas/fechadas no ponto de uso (auditoria incluída) — nenhuma sessão longa |
| Fases | `validando → seguranca → importando → verificando` expostas em `maintenance_mode["phase"]` |
| Drenagem | Antes do import: `drain_engine()` — `engine.dispose()` + aguardar quiescência de conexões em uso (join com timeout curto). Falha da quiescência → aborta com `BACKUP_RESTORE_FALHA`, estado liberado, backup de segurança disponível |
| Import | `_run_mysql_import(path, *, is_gzip)` com feed por chunks + **watchdog de relógio**: fase `importando` inteira sob `BACKUP_IMPORT_TIMEOUT` (default 900 s). Estouro → `terminate()` (+ kill de segurança) → falha com mensagem técnica sanitizável (etapa, tempo, exit code/stderr **sanitizado** padrão 018) |
| Pós-restore | Validação real por `SELECT` nas tabelas essenciais (017 preservada) com sessão nova (pool já reaberto) |
| Encerramento | `finally` SEMPRE: encerra manutenção, libera o slot (`_RESTORE_IN_PROGRESS` via mecanismo existente), grava `BACKUP_RESTORE_SUCCESS`/`BACKUP_RESTORE_FALHA`. Crash da thread ≠ manutenção eterna (contextmanager cobre exceções; restart do processo limpa por construção) |

### 1.3 `_run_mysql_import(path, *, is_gzip)` — mudanças pontuais

| Aspecto | Contrato |
|---|---|
| Execução | Continua sem shell (Popen direto, L309), cliente derivado do bin configurado (018), `MYSQL_PWD` só no ambiente — **nenhuma credencial em argv/logs** (FR-009); `stderr=subprocess.PIPE` capturado e nunca propagado |
| Feed | Escrita no stdin com controle de tempo por chunk (deadline total de relógio — D2) |
| Diagnóstico | Nas falhas: etapa ("feed no stdin" vs "aguardando término"), tempo decorrido, exit code, stderr **sanitizado** (senha mascarada) — paridade com o log técnico da 018 |
| Fakes de teste | `import_executor` injetado (assinatura `(Path, bool)`) continua sendo o caminho usado pelo worker — testes 017 não quebram |

## 2. Infraestrutura — `app/database.py`

| Símbolo | Contrato |
|---|---|
| `drain_engine()` | Novo helper: `engine.dispose()` (fecha ociosas do pool) + aguarda `checkedout() == 0` com timeout curto; retorna bool. Não toca em dados; não altera pool/URL/engine existentes |
| `SessionLocal`/`engine` | Intactos (mesmo pool reutilizável após dispose — SQLAlchemy recria conexões sob demanda) |

## 3. Middleware — `app/main.py`

| Aspecto | Contrato |
|---|---|
| Gatilho | `maintenance_mode["active"]` em memória; checado ANTES de qualquer dependência de banco (F1) |
| Resposta | HTTP 503 + `templates/admin/503.html` (padrão visual do sistema, sem query nenhuma) |
| Rotas isentas (whitelist mínima) | polling de estado do restore + login/health conforme contract de testes — definidas como constantes; nada além disso |
| RBAC | Middleware não concede acesso: rotas isentas mantêm suas permissões atuais; `503` não expõe dados (só texto de manutenção) |

## 4. Rotas — `app/web/admin_routes.py`

| Aspecto | Contrato |
|---|---|
| `POST /admin/backups/{filename}/restaurar` (`admin_backup_restore_exec` — caminho EXISTENTE em PT) | Permissão/dependências atuais intactas; chama `restore_backup` (que agora agenda) e responde **HTTP 303** imediato (padrão de redirect do sistema) para `/admin/backups`; falha de validação → fluxo de erro atual (`RedirectResponse error`). A sessão `db` do request é liberada no fim do POST — sem queries durante o ciclo |
| Polling `GET /admin/backups/restaurar/status` (novo, PT) | Mesma permissão de restore; JSON: `{active, phase, started_at, target_file, finished: bool, ok: bool, message}` — sem segredos; isenta do middleware (whitelist §3) |
| Tela `backups.html` | Indicador "restauração em andamento" + polling leve (~3 s enquanto ativa); botão desabilitado durante a restauração (defesa extra, o middleware já bloqueia tudo) |
| Formulário de confirmação (L859–893) | Intacto — continua sendo a tela informativa sem efeito (ui-contract 017) |

## 5. Config — `app/config.py`

| Variável | Contrato |
|---|---|
| `BACKUP_IMPORT_TIMEOUT` | Nova, opcional, default `900`; lida APÓS `load_dotenv()` (guarda da 018); nunca em logs com valor sensível (não é segredo) |

## 6. Não-regressão (garantias testáveis)

1. **Backup manual 018**: `_run_mysqldump` intocado — mesmo arquivo, mesmo log técnico.
2. **Ciclo seguro 017**: eventos, backup de segurança, validação pós-restore e liberação de estado preservados (ver §1.2).
3. **Falha honesta**: qualquer etapa falhando → `BACKUP_RESTORE_FALHA` + estado liberado + backup de segurança disponível (nunca falso sucesso).
4. **Segurança**: senha do banco exclusivamente no ambiente do subprocesso; stderr sanitizado antes de qualquer log.
5. **RBAC/AD**: zero alteração de permissões, roles, modelos ou AD.
6. **Multiplataforma**: drenagem é do pool SQLAlchemy; `terminate()` é POSIX/Windows; sem shell — comportamento idêntico em Linux e Windows.
