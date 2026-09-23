# Phase 1 Data Model: Notificação por E-mail de Movimentações

**Feature**: 030-notificacao-email-movimentacoes | **Date**: 2026-09-23

Alterações de schema: **1 tabela nova** (`notifications`) + **1 tabela nova de configuração** (`email_config`). Ambas criadas por `Base.metadata.create_all` no `init_db` — aditivo, idempotente, sem ALTER em tabela existente, `_ensure_schema_migrations` intocado (precedente `backup_records`/020; Constitution VII). Nenhum dado existente é tocado.

## Entity Relationship (apenas entidades novas)

```text
Movement (EXISTENTE — somente leitura para esta feature)
    │ 1:1 (movement_id UNIQUE)
    ▼
Notification (NOVA)          EmailConfig (NOVA, singleton id=1)
```

## 1. `EmailConfig` — configuração administrável (singleton)

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| `id` | Integer | PK, sempre `1` | Singleton (padrão BackupConfig/ADSettings) |
| `notifications_enabled` | Boolean | `default=False, nullable=False` | Ativação da notificação — **default desativado** (FR-006/RN-006) |
| `recipients` | Text | `nullable=True` | JSON array de e-mails válidos; `None`/vazio = não configurado |
| `updated_at` | DateTime | `default=now_utc, onupdate=now_utc` | UTC (padrão do projeto) |
| `updated_by` | String(100) | `nullable=True` | Username do admin que salvou |

**Validações (regra no `email_config_service`, não no model — Constitution III):**
- Salvar com `notifications_enabled=True` exige ≥ 1 destinatário com formato válido (rejeita lista vazia/inválida — spec Seção 13);
- Normalização: trim, lowercase do domínio, remoção de duplicatas; máx. 10 destinatários (cota conservadora);
- Nenhum campo contém segredo (senha SMTP só em ambiente — Constitution VI).

**Precedência da configuração efetiva** (precedente 021 — `email_config_service.get_effective_config`, dataclass congelada `EffectiveEmailConfig`):
- `enabled`: persistido → default `False` (sem fallback env de ativação — ativação é decisão da tela; nada em `.env` liga notificação);
- `recipients`: persistido → vazio (sem fallback env de destinatários — RN-004: destinatário é decisão administrativa oficial);
- SMTP (host/porta/usuário/senha/from/TLS/timeout): **exclusivamente ambiente** (`app/config.py`) — não faz parte do singleton.

Esclarecimento (analyze I1): o "fallback no ambiente para bootstrap" previsto na spec §9 refere-se **exclusivamente às variáveis `SMTP_*`** (dados de envio — linha anterior). A **ativação** e os **destinatários** não têm fallback de ambiente por decisão: são decisão administrativa persistida (RN-004/US3), e nada em `.env` liga a notificação.

## 2. `Notification` — registro de notificação (tabela `notifications`)

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | — |
| `movement_id` | Integer | **UNIQUE**, FK→`movements.id`, `nullable=False` | Vínculo 1:1 — garantia estrutural da idempotência (RN-007) |
| `status` | String(20) | `nullable=False, default="PENDING"` | `PENDING` / `SENT` / `FAILED` (valores literais — sem enum de banco) |
| `recipients` | Text | `nullable=True` | Destinatários efetivos do envio (JSON array; snapshot da config no momento) |
| `subject` | String(255) | `nullable=True` | Assunto enviado (RN-005) |
| `attempt_count` | Integer | `nullable=False, default=0` | Tentativas realizadas (FR-010; prepara retry futuro — P-1) |
| `last_attempt_at` | DateTime | `nullable=True` | UTC |
| `sent_at` | DateTime | `nullable=True` | UTC — preenchido quando `SENT` |
| `error_message` | Text | `nullable=True` | Erro técnico sanitizado (sem credenciais — Constitution VI) |
| `content_url` | String(500) | `nullable=True` | **Reservado, sempre NULL na v1** — link futuro (RN-008): preencher aqui + template = sem reestruturação |
| `created_at` | DateTime | `default=now_utc` | UTC |
| `updated_at` | DateTime | `default=now_utc, onupdate=now_utc` | UTC |

**Índices/constraints:**
- `UNIQUE (movement_id)` — idempotência estrutural (o banco rejeita uma 2ª linha para a mesma movimentação mesmo sob corrida);
- FK para `movements.id` (integridade referencial; sem ON DELETE — movimentação é imutável e permanente).

## 3. `Movement` (existente — nenhuma alteração)

Somente leitura como fonte dos dados do e-mail (F1): `asset_id` (→ `Asset.tag`, identificação), `movement_type` (`.label`), `origin/destination_location_name`, `origin/destination_custodian_name`, `operator_name`, `timestamp`, `reason`, `term_code`. **Nenhuma coluna nova, nenhuma alteração** (spec Seção 9).

## 4. Fluxo de estado da `Notification`

```text
         (movimentação elegível concluída — pós-commit)
                          │
                          ▼
                   [registro criado PENDING, attempt_count=0]
                          │  envio via provider (timeout SMTP_SEND_TIMEOUT)
              ┌───────────┴───────────┐
              ▼                       ▼
        [SENT]                   [FAILED]
     sent_at, attempt=1        error_message, attempt=1
     + auditoria ENVIADA       + auditoria FALHOU
              │                       │
              └─────── fim (v1) ──────┘
        (sem retry automático — P-1; estado guarda o necessário p/ futuro)
```

- Transição única por movimentação na v1 (sem fila, sem reprocesso): `PENDING → SENT` ou `PENDING → FAILED`;
- Nunca volta de `SENT` para `PENDING` (o e-mail foi emitido — nunca reenviar: RN-007);
- Registro criado **antes** do envio (commit próprio), estado atualizado **após** o resultado (commit próprio) — nenhuma das escritas participa da transação da movimentação (RN-001).

## 5. Enuns internos (módulo `notification_service`, não persistidos como enum de banco)

```python
STATUS_PENDING = "PENDING"
STATUS_SENT = "SENT"
STATUS_FAILED = "FAILED"
```

Constantes de elegibilidade (RN-002/Q1):
```python
NOTIFICABLE_TYPES = {MovementType.ALLOCATION, MovementType.TRANSFER, MovementType.RETURN_STOCK}
```

## 6. Validações resumo (fonte: spec)

| Regra | Onde |
|---|---|
| Ativado exige ≥1 destinatário válido | `email_config_service.save_config` (POST da tela) |
| Destinatários normalizados/deduplicados, máx. 10 | idem |
| No máx. 1 notificação por movimentação | UNIQUE(movement_id) + checagem prévia no service |
| Tipos notificados = só os 3 principais | `NOTIFICABLE_TYPES` (hook + service) |
| Sem envio quando desativado (default) | `get_effective_config().enabled` |
| Sem segredo em qualquer campo persistido | Constitution VI (revisão no implement) |
