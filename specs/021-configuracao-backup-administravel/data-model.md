# Data Model: Configuração Administrável do Backup Automático e Política de Retenção

**Feature**: 021 | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

---

## 1. Entidade NOVA: `BackupConfig` (tabela `backup_config` — singleton)

Espelha o padrão de `ADSettings` (singleton `id=1`). Criada por `Base.metadata.create_all` — **aditiva, idempotente, zero `ALTER`, zero dado existente tocado** (Constitution VII; spec FR-024).

| Campo | Tipo | Nullable | Default | Semântica (idêntica à 020) |
|---|---|---|---|---|
| `id` | Integer PK | não | 1 | Singleton: sempre 1 |
| `auto_enabled` | Boolean | não | `False` | Backup automático ativado? (020: default desativado — FR-009) |
| `schedule` | String(10) | sim | `None` | "não definido" até 1º salvamento; valores: `daily` \| `weekly` |
| `time` | String(5) | sim | `None` | HH:MM em **America/Recife** (020: fuso da operação) |
| `weekday` | Integer | sim | `None` | 0=domingo … 6=sábado (usado quando `schedule=weekly`) |
| `retention_daily_days` | Integer | sim | `None` | Janela diária de retenção (dias) |
| `retention_weekly_weeks` | Integer | sim | `None` | Janela semanal (semanas ISO) |
| `retention_monthly_months` | Integer | sim | `None` | Janela mensal (meses-calendário) |
| `keep_pre_restore` | Integer | sim | `None` | 0 = preservar todos; N>0 = preservar os N mais recentes |
| `updated_at` | DateTime | não | `now_utc` (onupdate) | Rastreio (espelha ADSettings) |
| `updated_by` | String(100) | sim | `None` | Username do último administrador |

**Notas de design**:
- Campos `schedule`/`time`/`weekday`/`retention_*`/`keep_pre_restore` **nullable = "não definido"**: distingue "nunca configurado" (efetiva = env/default) de "configurado" (efetiva = salvo) — base da precedência R2/R3 e compatibilidade com deploys por env (FR-026);
- `auto_enabled` não-nullable com default `False`: o único campo booleano precisa de valor concreto desde a criação e o default seguro é desativado (nunca ativa backup por efeito colateral de instalação — FR-008/FR-009);
- Nenhum campo de caminho, executável, credencial ou timeout técnico (spec FR-005/§28/§29);
- Nomes de campo **sem** o prefixo `BACKUP_` (o contexto da tabela já é backup); nada do `backup_records` (020) é alterado.

## 2. Conceito derivado: Configuração Efetiva (não é tabela)

Resultado da função única `get_effective_config(db)` — o objeto consumido por scheduler, tela e retenção. Resolução **por campo**, idêntica para os 8 campos (R2):

```text
valor persistido (definido)  →  usa
valor persistido (None)      →  variável de ambiente (config.py)
env ausente/inválida         →  default da Feature 020
```

| Campo | Env (fallback) | Default final |
|---|---|---|
| `auto_enabled` | `BACKUP_AUTO_ENABLED` | `False` |
| `schedule` | `BACKUP_AUTO_SCHEDULE` | `daily` |
| `time` | `BACKUP_AUTO_TIME` | `02:00` |
| `weekday` | `BACKUP_AUTO_WEEKDAY` | `0` |
| `retention_daily_days` | `BACKUP_RETENTION_DAILY_DAYS` | `30` |
| `retention_weekly_weeks` | `BACKUP_RETENTION_WEEKLY_WEEKS` | `12` |
| `retention_monthly_months` | `BACKUP_RETENTION_MONTHLY_MONTHS` | `12` |
| `keep_pre_restore` | `BACKUP_RETENTION_KEEP_PRE_RESTORE` | `0` |

- É um **dataclass/objeto simples imutável em memória** (snapshot do ciclo — R5), não entidade persistida;
- Primeira inicialização (linha ausente): `get_backup_config` cria a linha vazia (padrão `get_ad_settings`) e a efetiva = defaults — scheduler nunca indefinido (FR-008);
- Env **inválida** (ex.: `BACKUP_AUTO_TIME=xpto`): tratada como ausente pela resolução (a validação de faixa existente do scheduler é preservada como segunda camada — R6); nunca derruba a aplicação.

## 3. Ciclo de vida e transições

```text
Instalação/1º início          Administrador salva              Reinício
─────────────────────        ────────────────────────         ─────────────
linha inexistente             GET  → form com efetiva          linha existe
  ↓ criação lazy (id=1)       POST → valida (R6)               ↓ create_all idempotente
campos None                   ↓ commit único + auditoria       ↓ get_effective_config
efetiva = defaults 020        efetiva = valores salvos         efetiva = valores salvos
(backup desativado)           (scheduler aplica por tick)      (persistência comprovada — Teste R)
```

- **Estados da configuração**: NUNCA_CONFIGURADA (campos None) → CONFIGURADA (campos definidos). Não há volta para "não configurada" (limpar campo no form equivale a salvar o valor anterior — campos são obrigatórios no POST);
- **Falha de persistência**: commit abortado → estado vigente intacto + mensagem de erro (spec Edge case);
- **Concorrência**: commit único atômico; última escrita válida prevalece (R5).

## 4. Consultas derivadas

| Uso | Consulta/consumo |
|---|---|
| Tela de configuração (form) | `get_backup_config(db)` + `get_effective_config(db)` (campos não definidos mostram o efetivo como placeholder) |
| Scheduler (por tick) | `get_effective_config(db)` — snapshot por ciclo (R4/R5) |
| Retenção (por ciclo) | limites do snapshot do ciclo (mesma leitura) |
| Card de monitoramento existente | `scheduler_status()` passa a reportar a partir da efetiva (mesma fonte) |
| Auditoria | eventos `BACKUP_CONFIGURACAO_ALTERADA` (before/after por campo — §5 do contract) |

## 5. Validações (regras de dados — R6)

| Campo | Regra | Rejeição |
|---|---|---|
| `schedule` | ∈ {`daily`, `weekly`} | mensagem clara, nada persiste |
| `time` | HH:MM válido (00:00–23:59) | idem |
| `weekday` | inteiro 0–6 | idem |
| `retention_daily_days` | ≥ 1 | idem |
| `retention_weekly_weeks` | ≥ 1 | idem |
| `retention_monthly_months` | ≥ 1 | idem |
| `keep_pre_restore` | ≥ 0 | idem |
| `auto_enabled` | booleano (checkbox) | coerção padrão de Form |

Valores limítrofes **válidos** (00:00; retenção 1; keep 0) são aceitos (FR-016). A validação do backend é obrigatória e a do serviço/scheduler permanece como defesa em profundidade (FR-014/FR-015).

## 6. Entidades existentes — apenas consumo (zero alteração)

| Entidade | Uso nesta feature |
|---|---|
| `AuditLog` | recebe a ação nova `BACKUP_CONFIGURACAO_ALTERADA` (before/after JSON); schema intocado |
| `BackupRecord` (020) | intocada — retenção continua operando sobre ela com os limites do snapshot |
| `ADSettings` | **não é tocada** — é apenas o padrão de referência (singleton + efetiva + tela) |
| `User` | ator da alteração (`updated_by` + evento de auditoria) |

## 7. Cenários de borda modelados

- **Env divergente do banco**: precedência única resolve — mesmo valor em toda leitura (FR-006/007; Teste L);
- **Env inválida**: tratada como ausente; defaults governam (R2);
- **Scheduler rodando durante salvamento**: tick lê snapshot consistente; combinação parcial impossível (R5);
- **Dois admins salvando**: commits atômicos sequenciais; ambos auditados (FR-013);
- **Banco indisponível no POST**: erro controlado, configuração anterior vigente (Edge case da spec);
- **Reinício**: linha persiste; `create_all` idempotente; efetiva recarregada (Teste R);
- **Instalação nova nunca configurada**: efetiva = defaults; backup desativado (FR-008; Teste A/B).
