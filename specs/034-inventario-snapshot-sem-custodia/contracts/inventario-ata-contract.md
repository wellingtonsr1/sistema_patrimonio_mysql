# Contract: Ata de Inventário (CSV/Excel/PDF) + Pacote Offline — feature 034

**Feature 034** · Contrato das superfícies afetadas pela remoção do colaborador
responsável do snapshot. Endpoints/rotas existentes não mudam de assinatura nem de
permissão — apenas o conteúdo das saídas abaixo.

---

## 1. Ata de inventário — CSV (`/api/v1/reports/inventarios/{id}/csv`), Excel (`.../excel`) e PDF (`.../pdf`)

Permissão: `relatorios.exportar` (inalterada).

**Critério da coluna "Responsável Esperado" (decisão D2/H-2)**: presente **se e
somente se** algum item do inventário tiver `expected_custodian_name` gravado.

| Caso | Coluna na ata |
|---|---|
| Inventário criado APÓS a feature (nenhum item com o valor) | **Ausente** nas 3 exportações (ordem das demais colunas inalterada) |
| Inventário criado ANTES da feature (≥1 item com o valor) | **Presente**, com o histórico gravado por item ("Estoque / Livre" quando o item legado não tinha custodiante — valor existente mantido) |

Demais colunas e blocos (cabeçalho formal de comprovação, consolidação, totais)
permanecem como estão. Nenhuma ata já emitida é reeditada.

## 2. Pacote offline — `POST /api/v1/inventarios/{inventory_id}/offline/package` (feature 033)

Permissão: `inventario.conferir` (inalterada).

**Item do pacote APÓS esta feature** (decisão H-3 — vale para todo inventário):

```json
{
  "asset_id": 123,
  "item_id": 456,
  "tag": "000123",
  "serial_number": "SN-9A2C",
  "description": "Notebook Dell Latitude 5440",
  "expected_location_id": 3,
  "expected_location_name": "TI - Sala 2",
  "qr_url": "https://sispat.example/assets/123"
}
```

Removidos vs. contrato da 033: `expected_custodian_id` e `expected_custodian_name`.
O client da 033 não consome o campo (verificado); nenhum endpoint do pacote muda de
assinatura. O campo `found_custodian_id` da coleta (`inventario_offline_coletas`)
**permanece** — é dado encontrado em campo, não snapshot.

## 3. Telas (web) — contrato de conteúdo

- `GET /inventarios/{id}` (detail): cards dos itens não exibem mais a linha do
  colaborador esperado; rodapé "Local cadastrado" sem o acréscimo do colaborador.
- `GET /inventarios/{id}/conferir/{asset_id}` (conferir): sem o rótulo
  "Colaborador esperado:" no bloco de contexto do item.
- Nenhuma tela de outro módulo muda.

## 4. Compatibilidade

- Inventários anteriores: consulta, conferência de itens pendentes, encerramento e
  ata continuam funcionando; dados históricos preservados (H-1).
- Nenhum contrato de movimentação, alocação/cautela, colaboradores ou equipamentos
  é alterado.
