# Data Model — Feature 062: Seleção de Destino por Departamento/Setor

**Natureza**: documento de **não-mudança**. A spec (FR-009) e o plano estabelecem **zero DDL**: nenhuma tabela, coluna, índice, FK, enum ou dado é criado, alterado ou migrado. Este registro torna explícito o que permanece intocado e como a apresentação se alimenta do modelo atual.

## Entidades envolvidas (todas existentes, todas intocadas)

### `Location` (tabela `locations`) — fonte de leitura

| Campo | Tipo atual | Papel nesta feature |
|---|---|---|
| `id` | Integer PK | **value do option** (permanece o único identificador enviado) |
| `branch` | String(100) NOT NULL | **cabeçalho do optgroup** (Unidade Administrativa) e contexto do rótulo |
| `department` | String(100) NOT NULL | **início do rótulo** (`Departamento (Unidade)`) |
| `name` | String(100) UNIQUE NOT NULL | continua no banco e nas demais telas; sai do rótulo da opção (Q3) |

Sem alteração de tipo, constraint, índice ou valor. `LocationService.get_all(db)` permanece a única fonte (ordenação atual `branch, department, name` — `location_service.py` L22).

### `Movement` (tabela `movements`) — intocada

- `destination_location_id` (FK): continua recebendo o id escolhido no form — nenhum caminho de escrita é alterado.
- `destination_location_name` / `origin_location_name` (snapshots): **formato preservado** `"{branch} - {department} ({name})"` (FR-006; research R5). Registros existentes não são regravados (FR-007).

### `Asset` (tabela `assets`) — intocada

- `location_id` (FK): continua sendo o vínculo do bem; o form de Equipamento envia o id como hoje.

## Validações e regras (nenhuma nova)

- Nenhuma validação de negócio é criada ou movida (Princípio III). O backend continua validando o destino como hoje (matriz da Feature 005: VAL-002/003/004/005) — regras intocadas.
- A obrigatoriedade de `department`/`branch` já é garantida no cadastro de Localização (`location` schemas/rotas) — a apresentação não adiciona regra sobre os dados.

## Transições de estado

Nenhuma. Nenhum estado de bem, movimentação, inventário ou localização é alterado por esta feature.

## Diagrama do fluxo (inalterado no que grava; alterado só no que exibe)

```
Cadastro de Localizações (locations: id, name, branch, department)   ← intocado
        │
        │ LocationService.get_all(db)  ← intocado (ordenada branch, department, name)
        ▼
Template (movements/new.html | assets/form.html)                     ← ÚNICA MUDANÇA
        │  groupby('branch') → optgroup por unidade
        │  rótulo: "Departamento (Unidade)" · value: loc.id
        ▼
POST (destination_location_id | location_id)  ← intocado (mesmo campo, mesmo id)
        ▼
MovementService.create_movement / AssetService.create ← intocado
        │  snapshot gravado no formato atual "branch - department (name)"
        ▼
movements (FK + snapshot imutável) ← intocado (formato preservado; nada regravado)
```
