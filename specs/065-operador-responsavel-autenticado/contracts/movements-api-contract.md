# Interface Contracts: Operador Responsável Vinculado ao Usuário Autenticado

**Feature**: `065-operador-responsavel-autenticado`  
**Date**: 2026-10-09  

---

## 1. Web Form Interface: `POST /movements/new`

- **Método**: `POST`
- **URL**: `/movements/new`
- **Autenticação**: Cookie de Sessão + Permissão `movimentacao.criar`
- **Content-Type**: `application/x-www-form-urlencoded`

### Campos do Formulário
- `asset_id`: int (obrigatório)
- `movement_type`: string (obrigatório)
- `reason`: string (obrigatório)
- `operator_name`: string (enviado pelo cliente HTML `readonly`, **ignorado pelo servidor se autenticado**)
- `destination_location_id`: int (opcional)
- `destination_custodian_id`: int (opcional)
- `new_condition`: string (opcional)
- `notes`: string (opcional)

### Comportamento do Servidor
O servidor extrai o usuário de `request.state.user`.  
Define `operator_name = (user.full_name or user.username)[:100]`.  
Persiste a movimentação no banco de dados com essa identidade.

---

## 2. REST API Endpoint: `POST /api/v1/movements`

- **Método**: `POST`
- **URL**: `/api/v1/movements`
- **Autenticação**: API Session / Bearer Token + Permissão `movimentacao.criar`
- **Content-Type**: `application/json`

### Payload de Entrada (JSON)
```json
{
  "asset_id": 123,
  "movement_type": "TRANSFERENCIA_LOCAL",
  "reason": "Reorganização de setor",
  "operator_name": "Qualquer Texto Enviado"
}
```

### Comportamento do Servidor
O servidor intercepta a requisição via `require_permission("movimentacao.criar")`.  
Obtém `user = request.state.user`.  
Substitui `operator_name` no objeto de transferência por `(user.full_name or user.username)[:100]`.  
Retorna a movimentação criada com HTTP 201 Created.
