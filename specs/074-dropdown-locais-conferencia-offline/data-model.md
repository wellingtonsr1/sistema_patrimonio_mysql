# Data Model — 074 Dropdown de Locais na Conferência Offline

**Data**: 2026-10-18 | Base: inspeção de `app/models/location.py`, `app/services/inventario_offline_service.py`, `app/web/static/js/inventario_offline.js`

> **Zero mudança de esquema de banco.** Este documento descreve o modelo existente e os formatos de payload/registro envolvidos.

## 1. `Location` (servidor — intocado)

Tabela `locations` (SQLAlchemy `app/models/location.py`):

| Campo | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | **Identificador único e estável — usado como chave do dropdown (RF06/FR-006)** |
| `name` | String(100) | `unique=True, index=True` — **garante ausência de homônimos** (RNF-003 resolvido pelo modelo) |
| `branch` | String(100) | Unidade administrativa; parte do nome composto (`compose_location_name`) |
| `department` | String(100) | Setor; ordenação de exibição |
| `building`, `floor`, `room` | String, opcionais | — |
| `manager_name`, `description`, `created_at` | opcionais | — |

Não existe flag de ativo/inativo: "mesmo conjunto do online" (FR-002, decisão de clarify) = **todos os locais** de `LocationService.get_all` (ordenados `branch, department, name`).

## 2. Pacote offline — payload (campo novo, aditivo)

`InventarioOfflineService.generate_package` → `POST /api/v1/inventarios/{id}/offline/package`:

```jsonc
{
  "inventory_id": 12,
  "inventory_code": "INV-2026-001",
  "inventory_status": "EM_ANDAMENTO",
  "snapshot_version": "…",
  "generated_at": "…",
  "expires_when": "inventory_closed_or_reprepared",
  "items": [ { "asset_id", "item_id", "tag", "serial_number", "description",
               "expected_location_id", "expected_location_name", "qr_url" } ],
  "locations": [                       // ← NOVO (adição sem quebra)
    { "id": 3, "name": "Matriz SP - Tecnologia da Informação" },
    { "id": 7, "name": "Filial Campinas - Almoxarifado" }
  ]
}
```

Regras:
- `locations` contém **todos** os locais (mesma fonte/ordem do online), projeção mínima `id`+`name`.
- Campo aditivo: cliente antigo ignora; pacote antigo não o traz → tratado como "lista indisponível" (D5/D7).

## 3. Registro de pacote no dispositivo (IndexedDB `packages` — schema intocado)

`savePackage(pkg)` grava o payload completo como record (keyPath `inventory_id`), acrescido de campos gerenciados já existentes: `status` (`READY|EXPIRED`), `expired_reason`, `saved_at`, `device_id`. O campo `locations` trafega junto automaticamente — **`DB_VERSION` permanece 1**.

## 4. Coleta local (`coletas` — schema intocado)

Record já existente (`offline.html` → `idb.put("coletas", …)`); mudam apenas os **valores** em `LOCAL_DIFERENTE`:

| Campo | Antes | Depois |
|---|---|---|
| `found_location_id` | sempre `null` | **`Location.id` selecionado no dropdown** |
| `found_location_name` | texto digitado livre | nome exibido (snapshot de apresentação; opcional) |
| demais campos | inalterados | `client_operation_id`, `inventory_id`, `snapshot_version`, `item_id`, `asset_id`, `operation`, `result`, `observation`, `collected_at`, `device_id`, `sync_state` |

Estado de sincronização (fila `sync_queue`) — transições existentes, intocadas:

```text
PENDING → SYNCING → SYNCED
                   → FAILED (attempts < 5) → PENDING (retry manual)
                   → CONFLICT → reconciliação via web (023)
```

## 5. Sync — validação no servidor (intocada)

`process_sync` por operação (contrato §3 inalterado):
1. `found_location_id` presente → `db.get(Location, id)`; inexistente → rejeição estável `local_inexistente` (coleta preservada).
2. Sem id, com `found_location_name` (coletas antigas) → match exato único em `Location.name` (único por constraint); sem match → `local_nao_resolvido`.
3. `FOUND_WRONG_LOCATION` sem local resolvido → rejeição.
4. Gravação oficial única: `InventarioService.record_check(found_location_id=…)` → `item.found_location_id` + snapshot `item.found_location_name` (**não altera** a localização cadastral do bem — RF09/FR-009).

## 6. Regras de validação (resumo)

- Dropdown só exibido para resultado `LOCAL_DIFERENTE` (comportamento atual preservado).
- Seleção obrigatória para registrar `LOCAL_DIFERENTE` com dados disponíveis.
- Lista indisponível (pacote antigo/sem rede) ou vazia → registro **bloqueado** com orientação (FR-004, clarify Q1).
- Servidor é sempre a autoridade (RNF-005); cliente não decide validade.
