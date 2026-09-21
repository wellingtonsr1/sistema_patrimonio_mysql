# Contract: Correção do Ciclo de Backup, Restauração e Agendamento (028)

Contratos dos caminhos afetados. Tudo o que não está listado aqui permanece **byte-idêntico** ao comportamento atual.

## 1. Service — `app/services/backup_service.py` (US1 — reconciliação)

### 1.1 `BackupService.generate_backup` — intocado

Nenhuma mudança de assinatura, fluxo, auditoria ou criação de registros.

### 1.2 `_execute_restore_cycle(...)` — assinatura preservada, dois pontos de aplicação

| Aspecto | Contrato |
|---|---|
| Assinatura | Preservada integralmente (worker 019): `(filename, ip_address, source, *, user_id=None, import_executor=None, security_backup_executor=None)` — fakes dos testes 017/019 continuam válidos |
| Captura (novo) | Entre a auditoria `BACKUP_PRE_RESTORE` e a troca de fase `importando`: snapshot em memória `filename → {backup_type, status, timestamp, size_bytes, sha256}` de `BackupRecord` com `removed_at IS NULL`, lido em sessão própria e curta (padrão do worker) — inclui o registro do próprio pré-restauração criado nesta janela |
| Reconciliação (novo) | Após `validate_post_restore` (sucesso) E no caminho que segue após falha de validação (o banco foi substituído nos dois casos), SEMPRE antes do `finally` liberar slot/manutenção: para cada item do snapshot cujo arquivo ainda existe no disco (via `get_backup_path`) — registro existente → UPDATE apenas dos campos divergentes (`backup_type`, e demais campos do snapshot); registro inexistente → INSERT com os dados capturados; commit na sessão própria |
| Semântica | Best-effort: exceção de reconciliação é logada e NUNCA altera o resultado do ciclo, a auditoria (SUCCESS/FAILURE já emitidos permanecem) nem a liberação da manutenção; nunca levanta |
| Proibições | Nenhum fallback para MANUAL; nenhuma inferência por nome de arquivo; nenhum registro para arquivo inexistente; nunca tocar `removed_at/removed_reason`; nunca criar registro duplicado (respeita UNIQUE de `filename`) |
| Auditoria | Nenhum evento novo (R6 — backlog registrado); eventos existentes do ciclo intactos |

## 2. Service — `app/services/backup_scheduler.py` (US2 — disparo)

| Aspecto | Contrato |
|---|---|
| `_scheduler_loop` (bloco de disparo) | Substituição da condição `next_run = _next_run_utc(_clock()); if _clock() >= next_run` pela avaliação de execução devida: sessão própria e curta por tick → `_should_catch_up(now, db)` (mesmo critério do catch-up: horário do ciclo corrente já passou E ciclo sem SUCCESS) — se devido E ciclo ainda não tentado (`_attempted_cycle_keys`) → worker thread `backup-auto-worker-028` |
| `_attempted_cycle_keys` (novo) | `set` em memória de chaves de ciclo (início UTC da janela via `_cycle_window_utc`); registro da tentativa ao disparar — pelo caminho normal E pelo catch-up (anti-dupla-execução FR-013); anti-crescimento: só guarda o ciclo corrente (chaves antigas removidas por tick); crash/restart limpa por construção |
| `start_scheduler`/`stop_scheduler`/catch-up existente | Intactos (mesmo atraso de 60 s, mesma thread daemon única, mesmo `_CATCHUP_DELAY_SECONDS`) — o catch-up passa também a marcar o ciclo como tentado |
| `scheduler_status()` | Intacto (`next_run_local` continua para exibição) |
| Guardas preservadas | `_AUTO_RUNNING` (sobreposição descartada), `restore_in_progress()` (adiamento), guarda interna do `generate_backup` — ordem invariável |
| TYPE_CHECKING (R5) | `from typing import TYPE_CHECKING; if TYPE_CHECKING: from app.services.backup_config_service import EffectiveBackupConfig` — `refresh_effective_config` e `_eff()` intactos |
| Catch-up em loop desabilitado | Com `enabled=False`, nada dispara (não marca ciclo — Cenário 5 da US2) |

## 3. `app/main.py` — gate de manutenção (US3)

| Aspecto | Contrato |
|---|---|
| Whitelist de prefixos | `"/admin/backups"` NÃO entra na tupla `_MAINTENANCE_WHITELIST_PREFIXES` (prefixo isentaria POSTs — research D6) |
| Caso especial (novo, comentado) | Dentro do middleware, após o teste de prefixos: se `maintenance active` E `request.url.path == "/admin/backups"` E método ∈ {GET, HEAD} → `call_next` (isenção somente-leitura e específica; dependency `require_permission("backup.gerenciar")` da rota continua valendo — o middleware não concede acesso) |
| Todo o resto | Intacto: outros métodos/caminhos seguem recebendo 503 com `admin/503.html` (FR-022) |

## 4. Rota + template — `admin_routes.py` / `backups.html` (US3 — modo degradado)

| Aspecto | Contrato |
|---|---|
| `admin_backups` (GET) | Se `backup_service.restore_status()["active"]`: contexto degradado SEM queries de banco — `types_by_filename={}`, `retention_summary={}`, `config_form=None`, `backups=[]`; mantém `restore_status` e `auto_status` (`scheduler_status()` nunca lança — research D7). Caso contrário: contexto atual inalterado |
| `backups.html` | Estado vazio da tabela quando `backups` vazio durante manutenção (mensagem "listagem indisponível durante a restauração"); **nenhum guarda novo**: os usos de `config_form` (visão rápida L103, modal L155), `retention_summary` e `types_by_filename` JÁ são guardados no template; banner/polling/botões desabilitados da 019 reutilizados sem alteração |
| Rotas POST de backups | Intocadas e continuam bloqueadas durante manutenção (nenhum POST está isento — FR-018) |

## 5. Não-regressões (6 garantias)

1. Backup manual: arquivo + `BackupRecord(MANUAL)` + auditoria — inalterados.
2. Pré-restauração: criação, tipo e arquivo preservados; nenhum apagado durante o ciclo.
3. Catch-up de inicialização: no máximo 1 execução por start (agora sem coexistir com disparo normal no mesmo ciclo).
4. Retenção GFS: universos, âncoras, guarda do último válido, eventos — intocados (reconciliação nunca grava `removed_at/removed_reason`).
5. Auditoria: eventos existentes intactos; nenhum segredo novo em logs/auditoria.
6. 503 legítimo: todos os endpoints não-isentos continuam bloqueados durante manutenção.

## 6. Config — nenhuma

Zero variável nova (nenhuma necessária). `.env.example` não é tocado.
