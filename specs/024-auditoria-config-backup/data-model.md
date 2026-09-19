# Data Model: Auditoria da Precedência da Configuração de Backup Automático

**Feature**: 024 | **Data**: 2026-09-19
**Natureza**: a feature **não cria nem altera nenhuma entidade de produção**. Este documento descreve: (1) o modelo de dados da configuração auditada (lido de `app/models/backup_config.py` — somente leitura) e (2) as entidades conceituais da própria auditoria (inventário de ocorrências, fluxos, relatório).

---

## 1. Entidade auditada: `BackupConfig` (tabela `backup_config` — código existente, intocado)

**Arquivo**: `app/models/backup_config.py` | **Padrão**: singleton `id=1` (precedente `ADSettings`)

| Campo | Tipo | Null | Default | Semântica |
|---|---|---|---|---|
| `id` | Integer PK | não | — | singleton: sempre 1 |
| `auto_enabled` | Boolean | não | `False` | backup automático ativado? (default desativado, FR-009/021) |
| `schedule` | String(10) | sim | — (`None` = não definido) | `daily` \| `weekly` |
| `time` | String(5) | sim | — (`None` = não definido) | `HH:MM` em America/Recife |
| `weekday` | Integer | sim | — (`None` = não definido) | 0=domingo … 6=sábado (usado se `weekly`) |
| `retention_daily_days` | Integer | sim | — | janela diária ≥ 1 |
| `retention_weekly_weeks` | Integer | sim | — | janela semanal ≥ 1 |
| `retention_monthly_months` | Integer | sim | — | janela mensal ≥ 1 |
| `keep_pre_restore` | Integer | sim | — | 0 = preservar todos; N>0 = N mais recentes |
| `updated_at` | DateTime | sim | `now_utc` (default/onupdate) | rastreio UTC |
| `updated_by` | String(100) | sim | — | username do operador |

**Regras do modelo** (model docstring + service docstring):
- Campos operacionais `None` = "não definido" → a efetiva resolve **por campo**: persistido → env (`app/config.py`) → default da Feature 020 (constantes `_DEFAULT_*` do service).
- Criação lazy: `get_backup_config(db)` cria a linha `id=1` se ausente (commit único); `create=False` = leitura pura sem efeito colateral (Feature 022).
- `auto_enabled` é **não-null** (bool sempre definido — estado sempre conhecido); os demais são nullable de propósito.
- Nenhum campo contém segredo (MYSQLDUMP_PATH/BACKUP_DIR/BACKUP_IMPORT_TIMEOUT/DATABASE_URL permanecem de ambiente — FR-005/021).

## 2. Entidade de entrega: `OccurrenceRecord` (inventário da varredura — conceitual)

Cada ocorrência das 8 constantes registrada no relatório como:

| Campo | Conteúdo |
|---|---|
| `constante` | `BACKUP_AUTO_*` / `BACKUP_RETENTION_*` |
| `arquivo:linha` | referência citável |
| `trecho` | linha(s) citada(s) |
| `classificação` | A–H (research R2) — exatamente uma |
| `papel funcional` | fallback / bootstrap / efetiva / apresentação / teste / doc |
| `justificativa` | por que a classificação |
| `config-efetiva?` | sim/não (sim = violação da precedência) |

**Regras de classificação** (research R2): A = definição (config L67–87); B = fallback por campo (`_first_defined(row.x, config.BACKUP_X)` — service L122/132/142/170–182); C = bootstrap/snapshot de boot (scheduler L31–39 + L117–124, caminho de exceção com faixa própria); D = configuração efetiva em runtime (**nenhuma ocorrência encontrada na varredura preliminar — a reconfirmar**); E = apresentação (nenhum template consome constantes — modal consome a efetiva); F = validação isolada (nenhum uso direto — validações consomem a efetiva); G = teste (monkeypatch hermético em `tests/test_backup_*.py`); H = outro (docs/specs, nomes semelhantes não-config — research R7: `ACTION_BACKUP_AUTO_*` são rótulos de auditoria, excluídos).

## 3. Entidade de entrega: `FlowTrace` (fluxos de decisão documentados)

| Fluxo | Fonte real a registrar no relatório |
|---|---|
| Ativação | loop L796–800 → `refresh_effective_config()` por tick (L790/L799) → `get_effective_config(db)` → `row.auto_enabled` → env → default `False` (sem leitura direta de `config.BACKUP_AUTO_ENABLED` na decisão) |
| Frequência | `_effective_schedule()` sobre `eff.schedule` (efetiva validada) |
| Horário | `_effective_time()` sobre `eff.time` |
| Dia da semana | `eff.weekday` 0–6 (semântica 0=domingo…6=sábado) |
| Retenção | `_apply_retention` L625–627 lê `eff.retention_*`; `keep_pre_restore` idem |
| Tela (leitura) | `GET /admin/backups` → `get_effective_config(db, create=False)` (L840) |
| Tela (gravação) | `POST /admin/backups/configuracoes` → `save_backup_config` (validação prévia, commit único) → auditoria `BACKUP_CONFIGURACAO_ALTERADA` before/after (L925–963) → redirect 303 |

## 4. Entidade de entrega: `AuditReport` (relatório final — artefato da feature)

**Arquivo**: `specs/024-auditoria-config-backup/relatorio.md` (research R9). Estrutura = 12 seções do briefing §30 + tabela das 8 env vars (§18) + 7 respostas-chave com veredito (§28) + 14 critérios de conclusão marcados com evidência (§31) + achados rotulados OK/ATENÇÃO/INCONSISTÊNCIA/RISCO/BLOQUEADOR (§29).

**Regras de estado**:
- Estado inicial: inexistente; criado em `/speckit-implement`.
- Toda afirmação tem `arquivo:linha` + trecho citado (NFR-002).
- Nenhuma credencial/segredo citado (Constitution VI).
- Nenhuma alteração de produção associada (SC-001).

## 5. Precedência (o "relacionamento" central da auditoria)

```text
Tela (modal #modalBackupConfig)
  ↓ POST /admin/backups/configuracoes → save_backup_config (validação → commit único → auditoria)
backup_config (singleton id=1, campos None = "não definido")
  ↓
get_effective_config(db) — por campo: persistido → env (config.py) → default 020
  ↓ EffectiveBackupConfig (snapshot imutável por ciclo)
backup_scheduler (_current_effective renovado por tick — L790/L799)
  ├── decisão de disparo (enabled/schedule/time/weekday)
  └── _apply_retention (eff.retention_* / keep_pre_restore)
```

Env inválida é tratada como ausente (log técnico, cai no default) — nunca levanta (service L114–159). Env válida só vence o **default**, nunca o **persistido** (teste L, `test_backup_config.py`).

## 6. Defaults da Feature 020 (fonte final da precedência — research R6)

| Valor | Default (`_DEFAULT_*` no service L25–32) | Origem env (`config.py`) |
|---|---|---|
| `auto_enabled` | `False` | `os.getenv("BACKUP_AUTO_ENABLED", "false")` |
| `schedule` | `daily` | `os.getenv("BACKUP_AUTO_SCHEDULE", "daily")` |
| `time` | `02:00` | `os.getenv("BACKUP_AUTO_TIME", "02:00")` |
| `weekday` | `0` (domingo) | `os.getenv("BACKUP_AUTO_WEEKDAY", "0")` |
| `retention_daily_days` | `30` | `30` |
| `retention_weekly_weeks` | `12` | `12` |
| `retention_monthly_months` | **12** | `12` |
| `keep_pre_restore` | `0` (preservar todos) | `0` |

Duplicação intencional service × config (default ≠ env — sem import de `config` pelos defaults): se o service importasse as constantes, uma env inválida venceria o default e quebraria a precedência. Registro no relatório como achado de projeto, não problema (research R6).
