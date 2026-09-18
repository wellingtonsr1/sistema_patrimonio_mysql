# Phase 0 Research: Correção do Deadlock da Restauração de Backup

**Feature**: 019-import-deadlock | **Date**: 2026-09-18

Todas as decisões abaixo partem de fatos verificados no código real e no ambiente da máquina do operador (Windows + XAMPP/MariaDB 10.4.32 — o mesmo ambiente onde o incidente ocorreu duas vezes). Nenhum [NEEDS CLARIFICATION] permanece.

## Diagnóstico conclusivo (FR-001) — evidências

| # | Fato | Método de verificação | Consequência |
|---|---|---|---|
| **D1** | O import é executado **pelo processo web**: `POST /admin/backups/{filename}/restaurar` chama `restore_backup()` sincronamente; `_run_mysql_import()` abre o subprocesso `mysql` e escreve o dump (descomprimido em memória) no stdin **a partir do processo web** | Leitura de `app/web/admin_routes.py` (L892–905) e `app/services/backup_service.py` (L276+) | FR-003 violado por construção hoje: o import disputa locks com o próprio processo que o dispara |
| **D2** | O timeout existente **não cobre** o write no pipe: `proc.wait(timeout=...)` só cronometra a espera final; o `proc.stdin.write(chunk)` do loop de streaming (após `Popen` L309) **bloqueia sem limite** se o servidor não consumir | Leitura de `_run_mysql_import` (L276–360+: Popen stdin=PIPE, loop de escrita, wait com timeout) | FR-007 exige deadline de relógio cobrindo **todas** as fases, monitorado por fora do subprocesso |
| **D3** | Quem segurava o metadata lock: conexão **do pool da aplicação** (`SHOW PROCESSLIST` no incidente: thread do `mysql.exe` esperando 933 s/852 s em `DROP TABLE audit_logs`; conexão Sleep do pool com a mesma idade do import) | `SHOW PROCESSLIST` executado durante as duas tentativas reais de restore (2026-09-18) | Causa raiz (nível verificado): o fluxo **síncrono** executa o ciclo inteiro com a sessão do request aberta — `get_db` (database.py L27–33) só fecha a sessão no fim do request, que só acontece depois do import. Qualquer transação aberta nessa sessão (o request começa com queries de auth/sessão; a auditoria comita e novos usos reabrem transação na mesma conexão) mantém seus metadata locks durante o import. Com o import no mesmo processo, o dump espera um lock do próprio processo web → auto-deadlock |
| **D4** | `write_audit()` **commita na sessão que recebe** (audit_service.py L186) — e o ciclo do restore lhe passa a sessão do request; a sessão do request permanece checked-out do pool até o fim do request (get_db) | Leitura de `audit_service.py` (L148–186) e da rota (`admin_routes.py` L894–905: `BackupService.restore_backup(db, actor, ...)`) | A drenagem tem de incluir o estado "rota síncrona com `db` aberto durante o import" — eliminado de raiz pelo fluxo 202: a rota devolve a sessão imediatamente e o worker usa **sessões próprias e curtas** (R5) |
| **D5** | Privilégios do banco: `GRANT ALL PRIVILEGES ON sispatrimoniopro.*` (sem privilégios globais); MariaDB **10.4.32** | `SHOW GRANTS` executado no ambiente real | `DROP/CREATE DATABASE` **inviável** com o usuário atual → reconstrução **por tabela** (o dump da 015 já contém `DROP/CREATE TABLE` por tabela) |

## Decisões (com alternativas rejeitadas)

### R1 — Abordagem anti-deadlock: **worker thread + drenagem do pool** (FR-003)

- **Escolha**: o ciclo destrutivo do restore roda numa **thread de worker** com **sessões próprias e curtas**; antes do import, a thread **drena o pool** da aplicação (`engine.dispose()` + quiescência: nenhuma conexão em uso; o middleware de manutenção garante que nenhuma requisição nova abra sessão durante o import). Conexões ociosas são fechadas pelo dispose; requisições em voo drenam (join com timeout curto). Sem conexões vivas do processo web, o `DROP/CREATE TABLE` do dump não encontra MDL → import flui.
- **Por que não subprocesso independente**: exigiria replicar autenticação de banco/sanitização/validação num segundo ponto de entrada, ou criar script CLI com as credenciais no argv/env de um novo processo — superfície nova de segurança (FR-006) e violação de menor-alteração para o mesmo ganho. A drenagem resolve **no mesmo processo**, sem novo binário, sem credenciais adicionais.
- **Por que não `DROP/CREATE DATABASE`**: inviável (D5 — sem privilégio global). Rejeitada também criar usuário com privilégio global: expansão de privilégio proibida pelo espírito do FR-014.
- **Por que thread e não processo/task queue**: sistema é uvicorn de processo único, sem Celery/RQ; introduzir broker viola escopo. Thread nativa é suficiente (a operação é I/O-bound) e mantém o estado de concorrência existente (017) utilizável com liberação garantida.

### R2 — Deadline de relógio (FR-007/FR-008): **vigilância na thread principal + limite configurável**- **Escolha**: a rota dispara o worker e **não espera** o import em bloco: responde **303** imediato (padrão de redirect do fluxo web) com a restauração em andamento (slot de concorrência existente da 017: `_RESTORE_LOCK`/`_RESTORE_IN_PROGRESS`/`_restore_slot` — sem mecanismo paralelo) e o **deadline de relógio** cobre a fase `importando` inteira — inclusive o feed: a escrita no stdin roda em **thread escritora dedicada** e o worker espera seu término com o limite `BACKUP_IMPORT_TIMEOUT` (nova variável, default 900 s). Se o write bloquear no pipe (o caso real do incidente) e o prazo estourar → `terminate()` no subprocesso (o pipe quebra, a thread escritora desbloqueia) → falha registrada (`BACKUP_RESTORE_FALHA`), estado liberado, backup de segurança mantido disponível. (Nota de plataforma: `select()` não funciona em pipes no Windows — por isso a vigilância é por thread + prazo no lado do worker, não por polling de descritor; mecanismo idêntico nos dois SO.)
- **Detalhe de segurança**: o `terminate()` é multiplataforma (sem `shell`); o kill definitivo usa `kill()` adicional no Windows (`terminate` já é hard-kill no Windows; no POSIX segue SIGTERM + SIGKILL de segurança).
- **Alternativa rejeitada**: confiar no `wait(timeout=)` existente — é exatamente o buraco que causou o incidente (D2).

### R3 — Modo de manutenção (FR-010..FR-013): **middleware em memória, servido sem banco**

- **Escolha**: flag **em memória** no módulo do service (`maintenance_mode = {"active": bool, "started_at": ..., "phase": ...}`), checada por **middleware** no `app/main.py` **antes** de qualquer dependência que toque o banco: quando ativa, **toda** rota (exceto as de polling de estado definidas no contrato) recebe a página de manutenção (`503.html`, HTTP 503, padrão visual do sistema). A flag vive em memória → crash/restart a limpa naturalmente (FR-011: "nunca persiste travado" por construção; FR-009: liberação garantida). A tela de manutenção não executa nenhuma query (D4 torna esse requisito verificável: zero imports de sessão no caminho da resposta).
- **Encerramento automático**: bloco `finally` do worker limpa a flag em sucesso, falha e exceção — inclusive crash da thread (contextmanager + `finally` cobre; reinício do servidor limpa por reinicialização do módulo).
- **Alternativa rejeitada**: tabela/flag no banco — exige acesso ao banco para dizer que o banco está indisponível (contradição, exatamente o risco F1 da revisão da spec).

### R4 — Feedback na tela de backups (FR-013): **estado na memória + polling leve**

- A tela de backups ganha um **indicador de estado** ("restauração em andamento — modo manutenção ativo") com polling leve (fetch a cada ~3 s enquanto ativa) nas rotas de estado já permitidas pelo middleware. Sem percentual (US3/FR-013 — estado, não progresso).

### R5 — Fluxo 202 + sessões próprias e curtas no worker (eliminação da D3/D4)

- **Escolha**: o POST de restore deixa de ser síncrono-destrutivo: `restore_backup` valida, audita o início e **agenda** o ciclo destrutivo; a rota responde **303 imediatamente** (padrão de redirect do fluxo web; polling pela tela de backups via fetch) e a sessão do request é devolvida ao pool no fim do POST (sem queries durante o ciclo). A worker thread usa **sessões próprias e curtas** (`SessionLocal()` aberto/fechado no ponto de uso — auditoria incluída, que comita na sessão recebida, audit_service L186) e drena o pool antes do import. Assim, no momento do import, **nenhuma transação do processo web está aberta** e o pool está sem conexões vivas → os `DROP/CREATE TABLE` do dump não encontram MDL.
- **Por que é a raiz e não paliativo**: mesmo com a drenagem, uma rota síncrona manteria a própria sessão do request checked-out durante o import (get_db só fecha no fim do request) — a drenagem nunca chegaria a zero. O fluxo 202 é o que permite fechar TODAS as conexões do processo durante o import.
- **Alternativa rejeitada**: manter o POST síncrono e apenas reordenar eventos — não resolve (a sessão do request continuaria aberta de qualquer forma) e a UI não teria como refletir o estado.

## Impacto no ciclo da 017 (preservação — Princípio I)

| Fase da 017 | Pós-019 |
|---|---|
| Validação do arquivo (gzip + conteúdo) | idêntica |
| Evento `BACKUP_RESTORE_INICIADO` | idêntico (sessão própria do worker) |
| Backup de segurança pré-restore | idêntico (worker) |
| **Import** | **mudou**: precedido de drenagem do pool; fed por watchdog com deadline; processo web sem transações abertas |
| Validação pós-restore real (`SELECT` por tabela essencial) | idêntica (sessão nova do worker, após o pool ser reaberto) |
| Evento `BACKUP_RESTORE_SUCCESS`/`BACKUP_RESTORE_FALHA` | idênticos |
| Liberação do estado de concorrência | idêntica (`finally`) |
| Fluxo HTTP | antes: POST síncrono esperava o ciclo inteiro; depois: **303 + polling** (necessário para o processo web não segurar sessão durante o ciclo) |

## Não-regressões travadas

- Backup manual da 018: intocado (o worker só existe no restore; `_run_mysqldump` não muda).
- Backup de segurança pré-restore: sempre executado antes do import; em falha, permanece listado e baixável.
- RBAC: `backup.restaurar` continua a única permissão; middleware de manutenção não abre exceção de acesso (páginas de estado exigem as mesmas permissões de antes — ver contract).
- AD/RBAC/config: zero alteração além de `BACKUP_IMPORT_TIMEOUT` (opcional).
- Sem DDL; sem bifurcação por SO; sem novas credenciais em disco.
