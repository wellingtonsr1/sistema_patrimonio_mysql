# Data Model: Exportação CSV de Locais (feature 008)

**Natureza**: feature exclusivamente de **consulta e serialização** — nenhum modelo, schema, tabela ou coluna é criado ou alterado. Zero DDL (Constitution VII).

## Dados consultados (somente leitura)

### `Location` (`app/models/location.py`)

| Campo | Papel nesta feature |
|---|---|
| `name` | Coluna **"nome"** do CSV — "Nome / Identificação" |
| `branch` | Coluna **"filial"** |
| `department` | Coluna **"departamento"** |
| `building` | Coluna **"predio"** (opcional → `""` quando nulo) |
| `floor` | Coluna **"andar"** (opcional → `""`) |
| `room` | Coluna **"sala"** (opcional → `""`) |
| `manager_name` | Coluna **"gestor"** (opcional → `""`) |
| `description` | **Não exportada** — não é coluna da tabela de exibição (decisão R2) |
| `id` | Não exportado — identificador interno sem correspondência na tela |

### Dados derivados deliberadamente fora do CSV

- Contagem de bens (`LocationService.count_assets`) — **coluna de interface**, excluída por decisão do responsável (spec FR-004/Assumption 2; precedente `generate_custodians_csv` não exporta contagens).
- Links de ação ("Ver Bens") — elemento de interface (FR-004).

## Fonte do conjunto exportado

`LocationService.get_all(db)` — **sem filtro** (FR-006/R5): todos os locais, na ordenação vigente `branch, department, name`. O CSV espelha a listagem completa, não o estado de pesquisa da tela.

## Formato de saída (serialização, não modelo)

| Propriedade | Valor | Precedente |
|---|---|---|
| Extensão / nome | `locais.csv` | `colaboradores.csv` (`reports_api.py` L226) |
| Content-Type | `text/csv; charset=utf-8-sig` (UTF-8 **com BOM** p/ Excel) | todos os endpoints CSV |
| Disposition | `attachment` (download) | todos os endpoints CSV |
| Delimitador | `;` | `csv.writer(delimiter=";")` |
| Quoting | `csv.QUOTE_MINIMAL` | idem |
| Cabeçalhos | PT minúsculos, sem acento (`nome`, `filial`, `predio`…) | `matricula;nome;email;...` de colaboradores |
| Campos vazios | `""` (em branco) | `c.cpf or ""` |
| Escapamento | nativo do `csv.writer` (`;`/aspas/quebras de linha) | idem |
| Última linha | linha de cabeçalho apenas (se zero locais) | padrão CSV |

## Validações e transições de estado

Nenhuma — operação read-only; não há estados, mutações nem auditoria de mutação (Constitution IX não se aplica; exportações existentes também não são auditadas).
