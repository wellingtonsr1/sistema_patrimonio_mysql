# Data Model — Configurações de Backup em Modal (feature 022)

> **Nenhuma entidade, tabela, coluna ou registro é criado ou alterado.** Este documento registra a forma dos dados que fluem para a interface e a única mudança de assinatura (aditiva) no service.

## 1. Entidades existentes (referência — intocadas)

| Entidade | Papel nesta feature |
|---|---|
| `BackupConfig` (tabela `backup_config`, singleton `id=1` — 021) | Fonte dos valores exibidos no modal; campos `auto_enabled`, `schedule`, `time`, `weekday`, `keep_pre_restore`, `retention_daily_days`, `retention_weekly_weeks`, `retention_monthly_months` (+ `updated_at`/`updated_by`) |
| `EffectiveBackupConfig` (dataclass do `backup_config_service`) | Snapshot resolvido (persistido → env → default) que vira `config_form` no template |

## 2. Única mudança de assinatura (aditiva e compatível)

```python
def get_backup_config(db: Session, create: bool = True) -> BackupConfig
def get_effective_config(db: Session, create: bool = True) -> EffectiveBackupConfig
```

- `create=True` (default): comportamento **atual preservado** — cria a linha singleton se ausente (add + commit) e prossegue. Todos os chamadores existentes (rota da config, POST, scheduler) não mudam.
- `create=False`: **leitura pura** — consulta a linha; se ausente, constrói `BackupConfig(id=1, auto_enabled=False)` **não persistido** (campos operacionais `None`) e resolve a efetiva normalmente (None → env → default). **Nunca** `add`/`commit`/`flush`.

### Invariantes de `create=False`

1. Nenhuma escrita no banco (nenhum INSERT, nenhum commit) — um `GET` permanece apenas-leitura;
2. O objeto retornado é **não-persistido** quando a linha não existe (`id` setado para satisfazer o template; `db.object_session` nula) — atributos simples (`str`/`bool`/`int`/`None`) não disparam lazy-load, seguro para render;
3. O valor efetivo exibido é **idêntico** ao que uma primeira abertura da tela de config mostraria (defaults da 020/fallback env) — sem estado indefinido.

## 3. Contexto do template (`backups.html`)

| Variável | Rota | Valor | Mudança |
|---|---|---|---|
| `config_form` (`EffectiveBackupConfig`) | `GET /admin/backups` | `get_effective_config(db, create=False)` | **Novo** nesta rota (pré-preenche o modal) |
| `config_form` | `GET /admin/backups/configuracoes` | `get_effective_config(db)` (com criação — comportamento atual) | Inalterado |
| `config_row` | (ambas) | Linha singleton quando existir | Inalterado onde já existe |
| demais variáveis (`backups`, `auto_status`, `retention_summary`, `success`, `error`…) | idem | idem | Inalteradas |

**Observação**: com `create=False` na listagem, `config_row` não é necessário (o modal usa só a efetiva); a rota dedicada continua passando ambos.

## 4. Fluxo de salvamento (inalterado — referência)

```text
modal (form POST /admin/backups/configuracoes)
  → admin_backup_config_save (valida → persiste → audita BACKUP_CONFIGURACAO_ALTERADA)
  → 303 /admin/backups?success=…|error=…
  → página principal com alerta do topo + modal fechado (server-rendered)
```

Nenhum dado novo trafega; nenhum campo é adicionado/removido.
