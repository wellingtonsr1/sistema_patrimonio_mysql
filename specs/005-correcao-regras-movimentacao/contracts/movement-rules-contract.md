# Contract: Regras e Validações de Movimentação Patrimonial

**Feature**: 005-correcao-regras-movimentacao | **Date**: 2026-09-15
**Camadas**: Service (`MovementService`), API REST (`/api/v1/movements`), Rota Web (`POST /movements/new`).

---

## 1. Contrato da Camada de Serviço (`MovementService.create_movement`)

### 1.1 Assinatura
```python
def create_movement(db: Session, data: MovementCreate) -> Movement:
    """Executa e grava de forma atômica uma nova movimentação patrimonial.
    
    Aplica as validações da matriz de movimentação (Origem x Destino: Local x Responsável).
    Lança ValueError em caso de violação de regra de negócio.
    """
```

### 1.2 Entradas (`MovementCreate`)
| Campo | Tipo | Obrigatório | Descrição |
|---|---|:---:|---|
| `asset_id` | `int` | Sim | ID do bem a ser movimentado. |
| `movement_type` | `MovementType` | Sim | Tipo da movimentação patrimonial. |
| `destination_location_id` | `Optional[int]` | Não | ID do local de destino (se omitido ou ≤ 0, resolve para o local atual do bem). |
| `destination_custodian_id` | `Optional[int]` | Não | ID do colaborador de destino. |
| `new_condition` | `Optional[AssetCondition]` | Não | Nova condição física do bem. |
| `reason` | `str` | Sim | Justificativa da movimentação (min 3 caracteres). |
| `operator_name` | `str` | Sim | Nome do operador que efetuou o registro. |
| `notes` | `Optional[str]` | Não | Observações complementares. |
| `generate_term` | `bool` | Não | Indicador de emissão de termo (padrão True). |

### 1.3 Tabela de Validações e Mensagens de Erro (`ValueError`)

| Código da Regra | Condição de Disparo | Mensagem Exata da Exceção (`ValueError`) |
|---|---|---|
| **VAL-001** | `asset.status == AssetStatus.WRITTEN_OFF and m_type != MovementType.ACQUISITION` | `"Não é possível movimentar um equipamento que já foi baixado/descartado."` |
| **VAL-002** | `is_location_same and is_custodian_same` em `ALLOCATION` ou `TRANSFER` | `"Nenhuma alteração efetiva detectada. O local e o colaborador de destino são idênticos aos atuais."` |
| **VAL-003** | `m_type == MovementType.ALLOCATION and not effective_dest_custodian_id` | `"Para alocação/cautela é obrigatório selecionar o colaborador de destino."` |
| **VAL-004** | `m_type == MovementType.ALLOCATION and not is_location_same and is_custodian_same` | `"O colaborador informado já é o responsável atual pelo equipamento. Para transferir o equipamento mantendo o mesmo responsável, utilize Transferência de Setor / Filial."` |
| **VAL-005** | `m_type == MovementType.TRANSFER and not data.destination_location_id` | `"Para transferência de setor é obrigatório selecionar o local de destino."` |
| **VAL-006** | `m_type == MovementType.TRANSFER and is_location_same` | `"Para transferência de setor/filial é obrigatório selecionar um local de destino diferente do atual. Para alterar apenas o colaborador responsável, utilize Alocação / Cautela."` |
| **VAL-007** | `m_type == MovementType.TRANSFER and not is_location_same and not is_custodian_same and effective_dest_custodian_id is not None` | `"A entrega do equipamento a um novo colaborador deve ser registrada como Alocação / Cautela para emissão do Termo de Responsabilidade."` |
| **VAL-008** | `m_type == MovementType.RETURN_STOCK and origin_custodian_id is None and is_location_same` | `"O equipamento já se encontra no estoque neste local."` |

---

## 2. Contrato da API REST (`POST /api/v1/movements`)

### 2.1 Requisição
- **Método**: `POST`
- **Path**: `/api/v1/movements`
- **Headers**:
  - `Content-Type: application/json`
  - Autenticação / Permissão: `movimentacao.criar`
- **Body**: Objeto JSON serializável em `MovementCreate`.

### 2.2 Respostas
#### 201 Created
Retorna o objeto `MovementRead` serializado com o registro de movimentação criado.
```json
{
  "id": 105,
  "movement_uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "asset_id": 12,
  "movement_type": "ALOCACAO_CAUTELA",
  "timestamp": "2026-09-15T22:30:00Z",
  "origin_location_id": 1,
  "origin_location_name": "Matriz - TI (Sala de Suporte)",
  "origin_custodian_id": null,
  "origin_custodian_name": "Nenhum / Estoque",
  "destination_location_id": 1,
  "destination_location_name": "Matriz - TI (Sala de Suporte)",
  "destination_custodian_id": 5,
  "destination_custodian_name": "Carlos Silva (MAT-1020)",
  "previous_status": "DISPONIVEL",
  "new_status": "EM_USO",
  "previous_condition": "BOM",
  "new_condition": "BOM",
  "reason": "Alocação para início de atividades",
  "operator_name": "Administrador",
  "term_code": "TR-2026-00015",
  "term_signed": false,
  "notes": null,
  "created_at": "2026-09-15T22:30:00Z"
}
```

#### 400 Bad Request
Retornado quando qualquer validação da matriz falha (`ValueError`).
```json
{
  "detail": "Nenhuma alteração efetiva detectada. O local e o colaborador de destino são idênticos aos atuais."
}
```

---

## 3. Contrato da Rota Web (`POST /movements/new`)

### 3.1 Requisição
- **Método**: `POST`
- **Path**: `/movements/new`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Campos**: `asset_id`, `movement_type`, `destination_location_id`, `destination_custodian_id`, `new_condition`, `reason`, `operator_name`, `notes`.

### 3.2 Comportamento em Sucesso
- Redirecionamento `303 See Other` para `/movements/{movement.id}/term` caso termo tenha sido gerado, ou para `/movements` com mensagem de sucesso.

### 3.3 Comportamento em Falha de Validação
- Redirecionamento `303 See Other` para `/movements/new?asset_id={asset_id}&error={quote(mensagem_do_erro)}`.
- O template `movements/new.html` renderiza o alerta em banner vermelho (`<div class="alert alert-danger">`) exibindo a mensagem exata recebida.
