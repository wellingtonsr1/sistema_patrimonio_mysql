# Data Model: Inventário — Remover colaborador responsável do snapshot (feature 034)

**Fonte de verdade**: modelo atual de `inventario_itens` (snapshot do Inventário).
**Nenhuma migração é executada nesta feature** (decisão H-1 — Princípio VII).

## Entidade afetada: `InventarioItem` (`inventario_itens`)

| Coluna | Situação nesta feature |
|---|---|
| `expected_custodian_name` (String(150), nullable) | **Mantida no banco e no model (H-1)** para o histórico de inventários anteriores. A geração de NOVOS itens deixa de populá-la (fica `NULL`). Nenhuma coluna é adicionada, alterada ou removida. |
| `expected_location_id` / `expected_location_name` | Intocados — permanecem o núcleo do snapshot |
| `expected_custodian_id` | **Não existe** (fato do repositório) — nada a fazer |
| Demais colunas (status, found_*, checked_*, nao_previsto, observation) | Intocadas |

## Impacto por camada

| Camada | Componente | Mudança |
|---|---|---|
| Service | `InventarioService` (geração de itens) | Não passa mais `expected_custodian_name` na criação (fica `NULL`) |
| Service | `ReportService` (ata CSV/Excel/PDF) | Coluna "Responsável Esperado" presente **somente se** algum item do inventário tem o valor gravado (decisão D2/H-2); linha do valor "Estoque / Livre" mantida quando a coluna existe |
| Service | `InventarioOfflineService` (pacote, feature 033) | Chaves `expected_custodian_id`/`expected_custodian_name` removidas do payload para todo inventário (H-3/D4) |
| Template | `inventarios/detail.html` | Linha do colaborador esperado removida do card do item e do rodapé de local cadastrado |
| Template | `inventarios/conferir.html` | Rótulo "Colaborador esperado:" removido da conferência |
| Model | `app/models/inventario.py` | **Nenhuma mudança** (coluna permanece para histórico) |

## Invariantes preservados

- Snapshot **imutável** após a criação (Princípio V) — alterações no cadastro do bem
  (local ou custodiante) nunca refletem no item já criado.
- Inventário **nunca altera** o cadastro: local, custodiante e demais dados do bem
  permanecem intocados pela conferência (reafirmado; testes existentes continuam).
- Divergências possíveis continuam sendo exatamente: `LOCAL_DIFERENTE`,
  `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO` — o colaborador **não é** critério de
  conformidade (fato verificado no repositório; formalizado no FR-005 da spec).
- Dados históricos de inventários anteriores: preservados integralmente (H-1), com
  histórico acessível em consulta, conferência de itens pendentes, encerramento e ata
  (coluna presente quando houver histórico — D2).

## Relações intocadas

- `Asset.custodian` / cadastro de colaboradores (`Custodian`): usados por equipamentos,
  movimentações, alocação/cautela e relatórios de colaboradores — **nada muda**.
- `inventario_offline_coletas` (feature 033): o campo de custodiante **encontrado**
  (`found_custodian_id`) permanece — é dado da coleta, não do snapshot; o que sai é
  apenas o "esperado" do pacote.
