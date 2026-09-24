# Contract: API Offline de Inventário (`/api/v1/inventarios/{inventory_id}/offline/*`)

**Feature 033** · Autenticação: `require_api_auth` (cookie de sessão — decisão C-1) via
`include_router(..., dependencies=[Depends(require_api_auth)])`, padrão do `v1_router`.
Permissões: `inventario.visualizar` (ping/conflitos/leitura de coletas) e `inventario.conferir`
(pacote/sync/reconciliar) — decisão P-1, via mecanismo RBAC existente.

Erros seguem o padrão FastAPI existente (`{"detail": "..."}`): 401 não autenticado, 403 sem
permissão, 404 inventário/bem inexistente, 422 validação Pydantic. Nenhum payload inclui
credenciais; observações são sanitizadas (FR-031/FR-044).

---

## 1. `GET /api/v1/inventarios/{inventory_id}/offline/ping`

Verificação leve real de conectividade + estado do pacote (FR-042, indicador da UI).

**200**:
```json
{
  "ok": true,
  "inventory_id": 15,
  "inventory_status": "EM_ANDAMENTO",
  "server_time": "2026-09-24T14:32:11Z"
}
```
Sem efeito colateral; audita nada (é apenas connectivity check).

## 2. `POST /api/v1/inventarios/{inventory_id}/offline/package`

Gera o pacote on-demand (D9). Exige `inventario.conferir`.

**Request**: corpo vazio (estado e snapshot vêm do servidor).

**200**:
```json
{
  "inventory_id": 15,
  "inventory_code": "INV-2026-0007",
  "inventory_status": "EM_ANDAMENTO",
  "snapshot_version": "3f2a9c1d...",
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
      "qr_url": "https://sispat.example/assets/123"
    }
  ]
}
```

**409** `{"detail": "Este inventário está encerrado; não pode ser preparado para coleta offline."}` (C-2/P-2)
**422** inventário sem itens gerados.

Auditoria: `INVENTARIO_OFFLINE_PREPARADO` (inventário, contagem de itens, snapshot_version).

Regras (spec): pacote contém **somente** os campos do FR-003; preparação em PLANNED/IN_PROGRESS
não altera o estado do inventário (C-2); geração não escreve no cadastro (FR-005); limite de
1.000 itens validado (422 acima disso).

## 3. `POST /api/v1/inventarios/{inventory_id}/offline/sync`

Recebe lote de até 1.000 operações (D5). Exige `inventario.conferir`. **Servidor revalida tudo**
(FR-025): sessão, permissão, inventário aberto, snapshot_version, asset pertencente ao snapshot
(para `CHECK`), enum de resultado válido, local/responsável existentes quando informados,
integridade e duplicidade.

**Request**:
```json
{
  "device_id": "3f9d2a1e-...",
  "snapshot_version": "3f2a9c1d...",
  "operations": [
    {
      "client_operation_id": "b7c1-...",
      "operation": "CHECK",
      "asset_id": 123,
      "item_id": 456,
      "result": "ENCONTRADO",
      "found_location_id": 3,
      "found_location_name": "TI - Sala 2",
      "found_custodian_id": 8,
      "found_custodian_name": "João",
      "observation": "ok",
      "collected_at": "2026-09-24T09:12:00-03:00"
    },
    {
      "client_operation_id": "c8d2-...",
      "operation": "UNLISTED",
      "asset_id": 789,
      "found_location_id": 5,
      "found_location_name": "Almoxarifado",
      "observation": "bem não previsto no pacote",
      "collected_at": "2026-09-24T09:20:00-03:00"
    }
  ]
}
```

**200** (resultado estruturado por operação — FR-024):
```json
{
  "inventory_id": 15,
  "inventory_status": "EM_ANDAMENTO",
  "server_time": "2026-09-24T14:40:00Z",
  "accepted":   [{ "client_operation_id": "b7c1-...", "item_id": 456, "item_status": "ENCONTRADO" }],
  "duplicated": [{ "client_operation_id": "b7c1-...", "reason": "already_processed" }],
  "conflicts":  [{ "client_operation_id": "c8d2-...", "item_id": 456, "coleta_id": 88, "reason": "result_diverges" }],
  "rejected":   [{ "client_operation_id": "e9f3-...", "reason": "inventario_encerrado", "detail": "Inventário encerrado; coleta tardia não pode ser aplicada." }]
}
```

Semântica por operação (C-5/D5):
- `CHECK` válida + inventário aberto → grava via `record_check` → `accepted` (com novo status do item).
- `UNLISTED` válida → grava via `register_unlisted_asset` → `accepted`.
- `(inventory_id, client_operation_id)` já registrado → `duplicated` (sem regravar).
- Resultado **igual** ao estado atual do item → `duplicated` (`already_processed`).
- Resultado **diferente** de coleta anterior/estado atual para o mesmo snapshot → coleta
  `CONFLICT` preservada (payload íntegro) → resposta em `conflicts`; **nunca** sobrescreve (C-5/P-3).
- Falha de validação → `REJECTED` com `reason` estável e `detail` compreensível; nada gravado no item.
- Inventário encerrado → todas as operações do lote são `REJECTED` com motivo claro (C-2).

Auditoria: `INVENTARIO_OFFLINE_SYNC` (contagens por resultado, device_id); `INVENTARIO_OFFLINE_CONFLITO`
por conflito; `INVENTARIO_OFFLINE_REJEITADO` por rejeição — sempre sem credenciais (FR-044).

**Parcialidade** (FR-022/SC-005): o processamento é por operação; falha de rede no meio do lote
não regrava aceitas — o cliente reenvia apenas o que permaneceu `PENDING` (fila local).

## 4. `GET /api/v1/inventarios/{inventory_id}/offline/coletas?status=&device_id=`

Consulta das coletas registradas (rastreabilidade — US4). Exige `inventario.visualizar`.

**200**:
```json
{
  "inventory_id": 15,
  "total": 2,
  "coletas": [
    {
      "id": 87,
      "client_operation_id": "b7c1-...",
      "operation": "CHECK",
      "status": "ACCEPTED",
      "asset_id": 123,
      "device_id": "3f9d2a1e-...",
      "username": "maria",
      "collected_at": "2026-09-24T09:12:00-03:00",
      "received_at": "2026-09-24T14:40:01Z",
      "reject_reason": null,
      "reconcile_action": null
    }
  ]
}
```
Filtros opcionais: `status` (enum), `device_id`. Sem credenciais no retorno (FR-044).

## 5. `POST /api/v1/inventarios/{inventory_id}/offline/coletas/{coleta_id}/reconcile`

Reconciliação de conflito (D8). Exige `inventario.conferir`.

**Request**:
```json
{ "action": "APPLY" }
```
`action`: `KEEP` (mantém estado atual do item; coleta → `RECONCILED`) ou `APPLY` (grava a coleta
offline via `record_check` — inventário ainda aberto; coleta → `RECONCILED`).

**200**:
```json
{ "coleta_id": 88, "status": "RECONCILED", "action": "APPLY", "item_id": 456, "item_status": "LOCAL_DIFERENTE" }
```

**409** coleta não está em `CONFLICT`; **409** inventário encerrado (para `APPLY`).

Auditoria: `INVENTARIO_OFFLINE_RECONCILED` (coleta, ação, usuário).

---

## Notas de contrato

- **Sem endpoints de escrita patrimonial além do sync/reconcile** — toda gravação em
  `inventario_itens` passa por `InventarioService` (FR-026/Princípios III e V).
- **`snapshot_version`** (FR-004): hash determinístico do conjunto de itens do snapshot (D9);
  divergência entre o `snapshot_version` do cliente e o atual do servidor → operações `REJECTED`
  com motivo `snapshot_mismatch` (coleta foi feita sobre base diferente).
- **Datas** (FR-045): cliente envia `collected_at` (ISO 8601 com offset); servidor registra
  `received_at` (UTC, padrão do sistema) como referência oficial.
- **Idempotência** garantida por UNIQUE `(inventory_id, client_operation_id)` no banco
  (data-model) + verificação de igualdade de resultado (C-5).
- **SW/PWA**: nenhuma resposta deste contrato é cacheada pelo Service Worker (FR-036) —
  as rotas `/api/*` são network-only.
