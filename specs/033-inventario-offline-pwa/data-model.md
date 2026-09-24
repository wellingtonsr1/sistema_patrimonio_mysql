# Data Model: Conferência de Inventário Offline (feature 033)

**Fonte de verdade patrimonial**: permanece MariaDB via `inventarios` + `inventario_itens` (snapshot
`expected_*`). O modelo abaixo é **aditivo** — nenhuma tabela/coluna existente é alterada
(Princípios V e VII).

## Servidor — entidade nova: `InventarioOfflineColeta` (`inventario_offline_coletas`)

Registro de cada coleta offline recebida pelo servidor. É a âncora da **idempotência** (UNIQUE),
da **rastreabilidade** (dispositivo/usuário) e da **preservação de conflitos** (C-5).

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `inventory_id` | Integer, FK→`inventarios.id`, NOT NULL, index | inventário de origem |
| `client_operation_id` | String(64), NOT NULL | UUID gerado no dispositivo (FR-020) |
| `status` | Enum(`InventarioOfflineColetaStatus`), NOT NULL, index | ciclo abaixo |
| `asset_id` | Integer, FK→`assets.id`, index | bem conferido |
| `inventario_item_id` | Integer, FK→`inventario_itens.id`, nullable, index | null para operações de "bem não previsto" |
| `operation` | Enum: `CHECK`, `UNLISTED` | tipo de operação sincronizada |
| `result` | String(30), nullable | resultado declarado (`ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`) — snapshot textual, não FK de enum |
| `found_location_id` | Integer, FK→`locations.id`, nullable | local encontrado |
| `found_custodian_id` | Integer, FK→`employees.id`, nullable | responsável encontrado |
| `observation` | Text, nullable | observação do coletador (sanitizada — sem credenciais, FR-044) |
| `device_id` | String(64), NOT NULL, index | identificador local do dispositivo (FR-028) |
| `user_id` | Integer, FK→`users.id`, nullable | usuário da sessão no sync (oficial) |
| `username` | String(100), nullable | snapshot do username |
| `collected_at` | DateTime(timezone=True), NOT NULL | data/hora local declarada pelo dispositivo |
| `received_at` | DateTime(timezone=True), NOT NULL | momento do recebimento (referência oficial, FR-045) |
| `synced_at` | DateTime(timezone=True), nullable | momento da aceitação/gravação no item |
| `reconciled_at` | DateTime(timezone=True), nullable | momento da reconciliação (se conflito) |
| `reconciled_by` | Integer, FK→`users.id`, nullable | usuário que reconciliou |
| `reconcile_action` | String(20), nullable | `KEEP` ou `APPLY` (D8) |
| `client_payload` | Text, nullable | JSON do payload original — preservado em conflitos/rejeições (C-5/FR-019) |
| `reject_reason` | String(255), nullable | motivo da rejeição (quando `REJECTED`) |
| `evidence_metadata` | JSON, nullable | metadados de evidência associados à coleta (FR-017 — arquitetura prevista; sem sistema de fotos nesta feature) |

**UNIQUE** `(inventory_id, client_operation_id)` — idempotência (D5/FR-021).
**Índices**: `(inventory_id, status)`, `(inventory_id, asset_id)`, `device_id`.

### Enum novo (vocabulário controlado, aditivo): `InventarioOfflineColetaStatus`

Valores (em `app/models/enums.py`):

- `ACCEPTED` — gravada no item via `record_check`/`register_unlisted_asset` (único caminho, FR-026)
- `DUPLICATED` — reenvio ou resultado idêntico ao estado atual do item (C-5)
- `CONFLICT` — resultado divergente de coleta anterior/estado atual; preservada para reconciliação (C-5/P-3)
- `REJECTED` — falha de validação (inventário encerrado, asset fora do snapshot, integridade, payload inválido) com `reject_reason`
- `RECONCILED` — conflito resolvido por usuário autorizado (D8)

## Pacote offline (payload transitório — não é tabela)

Gerado **on-demand** pelo service a partir do snapshot `inventario_itens` (D9); o servidor não
persiste o pacote. Estrutura entregue ao dispositivo:

```json
{
  "inventory_id": 15,
  "inventory_code": "INV-2026-0007",
  "snapshot_version": "3f2a...",
  "generated_at": "2026-09-24T08:00:00Z",
  "expires_when": "inventory_closed_or_reprepared",
  "items": [
    {
      "asset_id": 123,
      "item_id": 456,
      "tag": "000123",
      "serial_number": "SN-9A2C",
      "description": "Notebook Dell Latitude 5440",
      "expected_location_id": 3,
      "expected_location_name": "TI - Sala 2",
      "expected_custodian_id": 8,
      "expected_custodian_name": "João",
      "qr_url": "https://sispat.../assets/123"
    }
  ]
}
```

- Campos = FR-003 (mínimo necessário); nada de usuários/permissões/administração (SC-008).
- `snapshot_version` = hash SHA-256 determinístico do conjunto `(asset_id, item_id, status)` ordenado (D9) — permite ao servidor reconhecer a base de coleta (FR-004) sem persistir o pacote.

## Dispositivo — IndexedDB `sispatrimonio_offline` (version 1)

| Store | keyPath | Campos principais |
|---|---|---|
| `packages` | `inventory_id` | inventory_id, code, snapshot_version, generated_at, status (`READY`/`EXPIRED`), items[] |
| `coletas` | `client_operation_id` | client_operation_id, inventory_id, item_id, asset_id, operation (`CHECK`/`UNLISTED`), result, found_location (texto+id), found_custodian, observation, collected_at, username, device_id, sync_state |
| `sync_queue` | `client_operation_id` | client_operation_id, state (`PENDING`/`SYNCING`/`SYNCED`/`FAILED`/`CONFLICT`), attempts, last_error, last_attempt_at |
| `device_info` | `key` | key (`device_id`), value (UUID persistente), created_at |

**Migração versionada** (`onupgradeneeded`): nunca apaga stores existentes; novas versões apenas
criam stores/índices e preservam registros (FR-038/SC-009). `localStorage`: somente
`sp_device_id` (UUID persistente, FR-028) e preferências de UI — nunca dados de coleta (FR-006).

### Estados da fila local (FR-018) e transições

```text
PENDING → SYNCING → SYNCED            (confirmação inequívoca do servidor)
PENDING → SYNCING → FAILED → PENDING  (erro de rede/retry com limite — FR-023)
PENDING → SYNCING → CONFLICT          (servidor detectou divergência — C-5)
CONFLICT → (reconciliação na tela do inventário) → limpo localmente após confirmação
```

Nunca apagar coleta local antes de confirmação inequívoca (FR-019); FAILED preserva payload e
motivo; SYNCED fica retido até a limpeza pós-confirmação (FR-040).

## Relações com entidades existentes (somente leitura exceto via services)

- `inventarios` — leitura (estado rege preparação/sync: C-2/P-2); escrita só pelo fluxo existente.
- `inventario_itens` — leitura (pacote) e escrita **exclusivamente** via
  `InventarioService.record_check`/`register_unlisted_asset` (FR-026).
- `assets`, `locations`, `employees`, `users` — leitura mínima para validar referências do payload.
- `audit_logs` — escrita apenas via `audit_service` (eventos `INVENTARIO_OFFLINE_*`, FR-044).
