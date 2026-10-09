# Data Model — 066-preenchimento-automatico-localizacao

**Data**: 2026-10-09 | **DDL**: **ZERO** (Constitution VII) — nenhum campo, tabela, índice ou migração é criado/alterado.

## Entidades

### `Location` (tabela `locations`) — estrutura inalterada

| Campo | Tipo | Restrição | Papel nesta feature |
|---|---|---|---|
| `id` | Integer PK | — | Identificador interno (FKs de `assets` e `movements`) — intocado |
| `name` | String(100) | **NOT NULL, UNIQUE, index** | **Passa a ser gerado** no fluxo web como `TRIM(branch) + " - " + TRIM(department)`; continua chave natural de unicidade |
| `branch` | String(100) | NOT NULL | Fonte 1 da composição — comportamento de entrada inalterado |
| `department` | String(100) | NOT NULL | Fonte 2 da composição — comportamento de entrada inalterado |
| `building`, `floor`, `room` | String | opcionais | **Fora da composição** (P2/spec §4.1.6) — continuam independentes |
| `manager_name`, `description`, `created_at` | — | opcionais | Intocados |

Relacionamentos inalterados: `Asset.location_id` (FK), `Movement.origin/destination_location_id` (FK) + snapshots de texto (imutáveis).

### Sem entidades novas, sem transições de estado

A feature muda apenas **como o valor de `name` é produzido** na criação web. Nenhuma nova entidade, coluna, índice ou migração de estados.

## Regras de validação (derivadas da spec)

| # | Regra | Onde é aplicada | Origem |
|---|---|---|---|
| V1 | `name` composto = `TRIM(branch) + " - " + TRIM(department)` | Servidor (rota web, via helper do service) — autoridade | FR-003, AC05 (P1 aprovada) |
| V2 | `len(name) ≤ 100` após composição; excedeu → rejeição com mensagem (sem truncamento) | Servidor | FR-004, R5 |
| V3 | `branch` e `department` obrigatórios e não-vazios após `strip()` | HTML `required` + `Form(...)` da rota | FR-005, AC06 |
| V4 | Unicidade de `name` (case-insensitive do collation + `get_by_name`) | `LocationService.create` existente | FR-006, AC07 |
| V5 | Nome enviado pelo cliente no form web é **ignorado** (recebido como opcional e descartado) | Servidor | FR-003, AC05 |
| V6 | Registros existentes nunca são renomeados (nenhum UPDATE; API PUT usa `exclude_unset`) | — | FR-008, AC08/AC10/AC11 |

## Dados reais como referência (auditados 2026-10-09, somente leitura)

- 37 localizações — **37/37 já em V1**; soma máxima `branch+department+3` = 50 chars (V2 com folga de 50); 0 duplicados (V4); 0 pares `branch+department` repetidos.
