# Data Model: Pesquisa de Locais (feature 007)

**Natureza**: feature exclusivamente de **consulta** — nenhum modelo, schema, tabela ou coluna é criado ou alterado. Zero DDL (Constitution VII).

## Entidade consultada (somente leitura)

### `Location` (`app/models/location.py`)

| Campo | Papel nesta feature |
|---|---|
| `name` | **Alvo exclusivo da pesquisa** — exibido na interface como "Nome / Identificação" (1ª coluna); filtro `ilike %termo%` case-insensitive |
| `branch` | Coluna de exibição "Filial" — **não** é alvo de pesquisa |
| `department` | Coluna de exibição "Departamento" — **não** é alvo de pesquisa |
| `building` / `floor` / `room` | Coluna de exibição "Prédio / Andar / Sala" — **não** são alvo de pesquisa |
| `manager_name` | Coluna de exibição "Gestor" — **não** é alvo de pesquisa |
| `description` | Texto complementar exibido sob o nome na 1ª coluna — **não** é alvo de pesquisa (o input restringe ao Nome / Identificação exibido como título do registro) |
| `id` | Usado no link existente "Ver Bens" (`/assets?location_id={{ loc.id }}`) — inalterado |

## Regras de consulta (no service, não no modelo)

1. `LocationService.get_all(db, search: Optional[str] = None)` — parâmetro aditivo; default `None` preserva a chamada atual de todos os chamadores.
2. Normalização: `termo = (search or "").strip()` — vazio ⇒ sem filtro.
3. Com termo: `filter(Location.name.ilike(f"%{termo}%"))` — parcial em qualquer posição, case-insensitive (colation do banco).
4. Ordenação preservada com e sem filtro: `order_by(branch, department, name)` (Assumption 3 da spec).

## Dados derivados existentes (inalterados)

- `loc.assets_count` — calculado na rota via `LocationService.count_assets(db, loc.id)` para **cada local exibido**; com pesquisa, apenas o subconjunto filtrado é contado. Comportamento e valor por registro idênticos aos da listagem completa.

## Validações e transições de estado

Nenhuma — operação read-only; não há estados, mutações nem auditoria de mutação (Constitution IX não se aplica).
