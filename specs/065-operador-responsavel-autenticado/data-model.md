# Data Model & Domain Rules: Operador Responsável Vinculado ao Usuário Autenticado

**Feature**: `065-operador-responsavel-autenticado`  
**Date**: 2026-10-09  

---

## Entidade Existente: `Movement` (`movements`)

A entidade `Movement` representa a gravação imutável de uma movimentação patrimonial.

### Atributos Relevantes

| Atributo | Tipo de Dados | Modificadores | Descrição |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Auto-increment | Identificador único da movimentação |
| `asset_id` | Integer | FK (`assets.id`), NOT NULL | Ativo patrimonial movimentado |
| `movement_type` | Enum | NOT NULL | Tipo da movimentação |
| `operator_name` | String(100) | NOT NULL, Default: "Sistema" | Identificação do operador responsável pelo registro |
| `created_at` | DateTime | Default: UTC | Data/hora de gravação da movimentação |

---

## Regras de Domínio e Validação

1. **Determinação da Identidade no Servidor**:
   - Para requisições autenticadas: `operator_name = (user.full_name or user.username)[:100]`
   - Para chamadas internas/automações sem sessão: mantém fallback seguro `"Sistema"` ou valor informado no serviço.
2. **Imutabilidade**:
   - Uma vez gravado o registro de `Movement`, o campo `operator_name` permanece inalterado para fins de histórico e auditoria imutável.
3. **Imunidade a Spoofing**:
   - Qualquer valor de `operator_name` enviado no corpo do formulário HTML ou payload JSON de requisição autenticada é desconsiderado e substituído pela identidade verificada no servidor.
