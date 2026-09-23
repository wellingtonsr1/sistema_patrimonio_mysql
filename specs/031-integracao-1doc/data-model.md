# Data Model: Integração 1Doc (feature 031)

**N/A para DDL destrutivo.** 1 tabela nova via `create_all` (precedentes `backup_records`/020 e `notifications`/030). Nenhuma tabela/coluna existente é alterada.

## Entidade nova: `OneDocIntegration` (`onedoc_integrations`)

Vínculo **um-para-um** entre movimentação e integração 1Doc (UNIQUE em `movement_id` — idempotência estrutural, espelha `uq_notifications_movement_id` da 030).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | — |
| `movement_id` | Integer FK→`movements.id`, **UNIQUE**, NOT NULL | Uma integração por movimentação (D1) |
| `process_number` | String(60), NOT NULL | Número do processo 1Doc informado pelo operador (normalizado: trim) |
| `status` | String(20), NOT NULL, default `PENDING` | `PENDING` / `SENT` / `FAILED` (padrão 030; nomes no padrão do projeto) |
| `message_id` | String(100), NULL | Identificador da comunicação retornado pela API; **NULL = desconhecido** (Q3 — sucesso sem ID continua `SENT`) |
| `attempt_count` | Integer, NOT NULL, default 0 | Tentativas de envio (FR-008) |
| `last_attempt_at` | DateTime, NULL | Última tentativa (UTC — `now_utc`) |
| `sent_at` | DateTime, NULL | Sucesso (UTC) |
| `last_error_at` | DateTime, NULL | Última falha (UTC) |
| `last_error` | Text, NULL | Erro técnico **sanitizado** (sem token — Constitution VI), máx. 2000 chars |
| `content_url` | String(500), NULL | **Reservado** para link futuro da movimentação (FR-017) — permanece NULL nesta versão |

### Transições de estado

```text
        (hook pós-commit, integração ativa, tipo elegível)
                          │ cria PENDING (commit próprio)
                          ▼
                      [PENDING] ── envio OK ─────────────► [SENT]      (terminal; idempotência)
                          │
                          └── falha (transitória ou permanente) ► [FAILED] ── reprocessar (permissão dedicada) ──► [SENT]
                                                                       │ falha de novo ──► [FAILED] (attempt_count+1)
```

- `SENT` é terminal: reprocessamento de uma integração `SENT` **não reenvia** (Q3/D8 — return silencioso).
- Reprocessamento mantém o **mesmo** registro (nunca cria outro — UNIQUE) e incrementa `attempt_count`.
- `PENDING` órfão (crash entre insert e envio) é recuperável por reprocessamento.

## Entidades existentes (somente leitura)

| Entidade | Uso na 031 | Campos lidos |
|---|---|---|
| `Movement` | Fonte exclusiva do conteúdo e da elegibilidade | `id`, `movement_type`, `origin_location_name`, `destination_location_name`, `operator_name`, `asset_id` |
| `Asset` (via relação) | Descrição do Material + Tombamento | `name`, `tag` |
| `SystemUser`/auth | Operador do reprocessamento (auditoria com user real) | `request.state.user` |

## Configuração (ambiente — nada em banco nesta versão)

| Variável | Default | Papel |
|---|---|---|
| `ONEDOC_ENABLED` | `false` | **Integração nasce desativada** (D2/D4 — produção só após C-1..C-4) |
| `ONEDOC_API_URL` | vazio | Base URL da API (sem rota inventada) |
| `ONEDOC_API_TOKEN` | vazio | **SEGREDO** — somente ambiente; sanitizado em erros |
| `ONEDOC_CONNECT_TIMEOUT` | `3` | Timeout de conexão (FR-013) |
| `ONEDOC_READ_TIMEOUT` | `10` | Timeout de leitura (FR-013; SC-004) |
| `ONEDOC_MAX_ATTEMPTS` | `3` | Teto documentado para a evolução worker (P-5) |

## Regras de integridade

1. **UNIQUE** `movement_id` = no máximo 1 integração por movimentação (SC-003);
2. Nenhuma escrita em `movements`/`assets` pela integração (Constitution IV — a movimentação já foi concluída pelo motor oficial);
3. `process_number` só existe no registro de integração — o modelo patrimonial não conhece 1Doc (D1/D2);
4. Auditoria via `write_audit` — a trilha `audit_logs` não recebe novas colunas;
5. `content_url` NULL permanente na v1 (nenhuma URL gerada — FR-017).
