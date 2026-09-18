# Service Contract — Backup Automático e Política de Retenção (feature 020)

> Contratos das superfícies tocadas. Padrão das specs 015–019: nomes finais podem variar minimamente na implementação, semântica não. Tudo confinado a `app/services/` (Constitution II/III); rotas delegam.

---

## §1. Configuração (env vars — `app/config.py`, após `load_dotenv()`)

| Variável | Default | Valores aceitos | Comportamento em valor inválido |
|---|---|---|---|
| `BACKUP_AUTO_ENABLED` | `"false"` | `true` → ativa; qualquer outro = desativado | desativado + log do valor desconhecido |
| `BACKUP_AUTO_SCHEDULE` | `"daily"` | `daily` \| `weekly` | cai em `daily` + log |
| `BACKUP_AUTO_TIME` | `"02:00"` | `HH:MM` 00:00–23:59 (America/Recife) | cai em default + log |
| `BACKUP_AUTO_WEEKDAY` | `"0"` | 0–6 (0=domingo); só usado se `weekly` | cai em default + log |
| `BACKUP_RETENTION_DAILY_DAYS` | `"30"` | inteiro ≥ 1 | cai em default + log |
| `BACKUP_RETENTION_WEEKLY_WEEKS` | `"12"` | inteiro ≥ 1 | cai em default + log |
| `BACKUP_RETENTION_MONTHLY_MONTHS` | `"12"` | inteiro ≥ 1 | cai em default + log |
| `BACKUP_RETENTION_KEEP_PRE_RESTORE` | `"0"` | 0 = preservar todos; N > 0 = preservar os N mais recentes | cai em default (0) + log |

Nota: defaults do 020 em `config.py` são os valores iniciais do briefing §21; a **regra** (GFS, guardas) vive no serviço — nada de política hardcoded.

## §2. `app/config.py` — API nova (aditiva)

```python
# Todos derivados das env vars acima; normalizados (int/bool) já em config.
BACKUP_AUTO_ENABLED: bool          # default False
BACKUP_AUTO_SCHEDULE: str          # "daily" | "weekly"
BACKUP_AUTO_TIME: str              # "HH:MM"
BACKUP_AUTO_WEEKDAY: int           # 0..6
BACKUP_RETENTION_DAILY_DAYS: int   # >= 1
BACKUP_RETENTION_WEEKLY_WEEKS: int # >= 1
BACKUP_RETENTION_MONTHLY_MONTHS: int  # >= 1
BACKUP_RETENTION_KEEP_PRE_RESTORE: int  # >= 0
```

## §3. `BackupService.generate_backup()` — extensão aditiva

```python
generate_backup(db, user, ip_address=None, *,
                dump_executor=None,
                _allow_during_restore=False,
                backup_type: str = "MANUAL") -> Dict
```

- `backup_type` ∈ {`MANUAL`, `AUTOMATICO`, `PRE_RESTAURACAO`}; outro valor → `ValueError` (falha rápida, sem dump);
- Comportamento existente **intocado**: dump → gzip → validação → sha256 → rename atômico → `BACKUP_CRIADO`/`BACKUP_FALHA`;
- **Novo (aditivo)**: grava `BackupRecord` com sessão própria e curta (sessão de request do chamador não é retida; escrita do registro em `try/finally` — erro de metadados NUNCA invalida o backup físico, só loga);
  - SUCCESS: `{filename, backup_type, timestamp, size_bytes, sha256}`;
  - FAILURE: `{filename={base}.sql.gz (nome FINAL projetado — casa com `_BACKUP_NAME_RE`), backup_type, status=FAILURE, error_description}` — arquivo parcial já removido pelo fluxo existente (BV-8); o filename de FAILURE NÃO indica arquivo disponível: listagem/elegibilidade sempre cruzam registro com arquivo presente;
- Retorno idêntico ao atual (campo `filename` inalterado) — chamadores existentes (rota manual, worker do restore) não mudam linha alguma.

## §4. `app/services/backup_scheduler.py` — contrato do agendador (novo módulo)

```python
start_scheduler() -> None            # idempotente; chamado no lifespan (após init_db)
stop_scheduler() -> None             # chamado no shutdown; sinaliza e aguarda saída
scheduler_status() -> Dict           # sem segredos: {enabled, schedule, time_local, weekday,
                                     #   next_run_local, last_result, last_finished_at, running}

# Internos (testáveis):
_run_scheduled_backup() -> Dict      # ciclo completo: guardas → generate_backup(backup_type="AUTOMATICO")
                                     #   → evento auditoria → retenção → retorna resumo
_apply_retention(db) -> Dict         # {candidatos, removidos, falhas, resultado: COMPLETA|PARCIAL|FALHA}
_next_run_utc(now_utc) -> datetime   # determinística: próxima ocorrência futura do horário (local_to_utc)
_should_catch_up(now_utc) -> bool    # True só se ciclo corrente sem SUCCESS e horário já passou (R5):
                                     #   daily = dia calendário local (Recife) corrente; weekly = semana
                                     #   iniciando 00:00 local no BACKUP_AUTO_WEEKDAY (não é semana ISO);
                                     #   "sucesso no ciclo" = SUCCESS com timestamp UTC dentro da janela
```

**Ciclo `_run_scheduled_backup` (ordem invariável):**

1. Guarda 1: `_AUTO_RUNNING` (lock) já ativo → **descartar** (log técnico, sem evento de auditoria — não é falha de backup);
2. Guarda 2: `restore_in_progress()` → **adiar** (log; próxima execução recálculada; sem evento);
3. Marcar `_AUTO_RUNNING`; worker thread executa:
   a. `generate_backup(db, None, None, backup_type="AUTOMATICO")` (sessão própria);
   b. Auditoria: `BACKUP_AUTOMATICO_SUCESSO` ou `BACKUP_AUTOMATICO_FALHA` (ator None + "sistema");
   c. `_apply_retention(db)` — somente após (a), com resultado auditado (ver §5);
   d. Atualizar `last_result`/`last_finished_at` em memória;
4. `finally`: liberar `_AUTO_RUNNING`.

**Relógio/loop**: verificação a cada 30 s (`stop_event.wait(30)`); comparação sempre em UTC via `now_utc()`; conversão Recife↔UTC só com `app/utils.time_utils` (R11).

## §5. Retenção (`_apply_retention`) — algoritmo contratado

**Entrada**: registros `AUTOMATICO`/`SUCCESS` com `removed_at IS NULL` + arquivo presente; config §1.

**Seleção (determinística — data-model §3)**: candidata-se o automático que satisfaz **todas**:
1. `timestamp < now_utc() − DAILY_DAYS` (janela diária);
2. NÃO é âncora semanal (mais recente da semana ISO dentro de `WEEKLY_WEEKS`);
3. NÃO é âncora mensal (mais recente do mês dentro de `MONTHLY_MONTHS`);
4. Integridade do arquivo OK (`_gzip_read_status` da 016);
5. Guarda do último válido: conjunto de backups válidos remanescentes (todos os tipos, no disco) > 0 após a remoção; senão preserva com motivo `ULTIMO_BACKUP_VALIDO`;
6. Pré-restauração/legado/manual: **fora do universo** desta seleção (nunca candidatos; `KEEP_PRE_RESTORE>0` trata os pré-restauração separadamente, preservando os N mais recentes).

**Execução por candidato (ordem: mais antigo primeiro)**:
- Remover arquivo via `get_backup_path()` validado (regex + diretório oficial — §31; path traversal estruturalmente impossível);
- Sucesso: `removed_at`/`removed_reason` no registro + evento `BACKUP_REMOVIDO_RETENCAO` (SUCCESS, `{motivo, faixa}`);
- Falha de remoção (OSError): **não interrompe** — evento FAILURE para o arquivo, continua nos demais (§32);
- Resultado consolidado: `COMPLETA` (0 falhas) | `PARCIAL` (≥1 falha — **nunca** reportado como "concluída") | `FALHA` (nenhum removido e ≥1 falha);
- **Motivos de não-exclusão** (F4): cada candidato preservado entra no resumo com seu motivo — `new_data` do evento `BACKUP_RETENCAO_EXECUTADA` carrega `preservados: {filename: motivo}` com motivo ∈ {`ULTIMO_BACKUP_VALIDO`, `ANCORA_SEMANAL`, `ANCORA_MENSAL`, `INTEGRIDADE_NAO_OK`}; o mesmo mapa vai ao log técnico — rastreabilidade completa sem novo mecanismo;

**Vedado**: apagar por extensão/glob; apagar fora de `BACKUP_DIR`; apagar sem registro/evento; remover quando resultaria 0 válidos.

## §6. Auditoria (`app/services/audit_service.py`) — aditivo

```python
ACTION_BACKUP_AUTO_SUCCESS      = "BACKUP_AUTOMATICO_SUCESSO"
ACTION_BACKUP_AUTO_FAILED       = "BACKUP_AUTOMATICO_FALHA"
ACTION_RETENTION_EXECUTED       = "BACKUP_RETENCAO_EXECUTADA"
ACTION_BACKUP_REMOVED_RETENTION = "BACKUP_REMOVIDO_RETENCAO"
ACTION_RETENTION_FAILED         = "BACKUP_RETENCAO_FALHA"
```

+ rótulos em `ACTION_LABELS`. Eventos existentes (`BACKUP_CRIADO`, `BACKUP_FALHA`, `BACKUP_PRE_RESTORE_CRIADO`, ...) intocados e continuam gravados. Ator: usuário real (manual/restore); `None` + description "sistema" (automático/retenção). Nunca credenciais.

## §7. UI (`admin/backups.html` + `admin_backups`) — aditivo

- Rota `GET /admin/backups` (permissão `backup.gerenciar` — reuso, **sem permissão nova**): contexto ganha `auto_status` (`scheduler_status()`) e `retention_summary` (consultas ao service);
- Template: **card novo** "Backup Automático" acima da listagem (componentes existentes: `card`, `badge`, `dd/dt`): ativado/desativado, frequência/horário (local), próxima execução, último automático + status, último válido, última falha, última retenção (resultado + removidos), válidos/removidos;
- Listagem existente: coluna "Tipo" aditiva (`MANUAL`/`AUTOMATICO`/`PRE_RESTAURACAO`/`—` para legados);
- Botão/fluxo manual: **linha a linha intocados**.

## §8. `app/main.py` (lifespan) — aditivo

```python
# Após init_db/ensure_admin/seed:
from app.services.backup_scheduler import start_scheduler, stop_scheduler
...
start_scheduler()   # só inicia thread se BACKUP_AUTO_ENABLED ou retenção aplicável
yield
stop_scheduler()    # shutdown limpo
```

Middleware de manutenção (019), whitelist, rotas e exception handlers: **intocados**.

## §9. Matriz de erros (FR-016/FR-018/§16–§18)

| Falha | Comportamento contratado |
|---|---|
| Executável inexistente (`MYSQLDUMP_PATH`/PATH) | `BackupError` (mensagem distinta "não encontrado") → registro FAILURE + `BACKUP_AUTOMATICO_FALHA` + log com etapa |
| Subprocesso exit ≠ 0 / erro SGBD | `BackupError` ("retornou erro") → idem; stderr **sanitizado** no log |
| Timeout do dump | `BackupError` ("tempo limite") → idem |
| Falha de compactação/validação (gzip inválido, vazio) | `BackupError` → FAILURE; `.part*` removidos (fluxo existente) |
| Disco cheio / permissão (OSError) | `BackupError` ("erro de disco/subprocesso") → FAILURE; log registra `type(exc).__name__` |
| Colisão de nome final | `BackupError` ("Conflito de nome") → FAILURE (BV-3 015) |
| Remoção na retenção falha (OSError) | arquivo NÃO removido; evento individual FAILURE; ciclo segue; resultado PARCIAL |
| Disparo durante restore / sobreposto | descartado/adiado com log — sem evento de falha, sem dump |
| Config inválida | default seguro + log no start (nunca crash do lifespan) |

**Nenhum caminho apresenta sucesso falso**: status SUCCESS só com arquivo válido + integridade OK (FR-016).
