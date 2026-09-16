# Contract: `GET /api/v1/reports/locations/csv` (Exportação CSV de Locais)

**Feature**: 008-exportar-locais · **Tipo**: contrato de endpoint REST + âncora de UI · **Base**: `app/api/reports_api.py`, `app/services/report_service.py`, `app/web/templates/locations/list.html`

## 1. Requisição

```
GET /api/v1/reports/locations/csv
```

| Propriedade | Valor |
|---|---|
| Método / path | `GET` no router de reports existente (`/api/v1/reports`) |
| Parâmetros de query | **Nenhum** — o endpoint sempre exporta todos os locais (FR-006; parâmetros recebidos são simplesmente ignorados pelo FastAPI) |
| Autenticação | Obrigatória (herdada do `api_v1_router`) |
| Permissão | `relatorios.exportar` via `require_permission` — **nenhuma permissão nova** (FR-007) |

## 2. Resposta

| Propriedade | Valor | Precedente |
|---|---|---|
| Status | `200 OK` (com ou sem locais) | endpoints CSV existentes |
| Content-Type | `text/csv; charset=utf-8-sig` | `reports_api.py` L70 |
| Content-Disposition | `attachment; filename=locais.csv` | `colaboradores.csv` (L226) |
| Corpo | CSV gerado por `ReportService.generate_locations_csv` | — |

## 3. Formato do corpo (fixado)

- **Cabeçalho (linha 1, exata)**: `nome;filial;departamento;predio;andar;sala;gestor`
- **Delimitador `;`**, quoting mínimo, UTF-8 com BOM — padrão `ReportService`.
- **Uma linha por local** (todos; ordenação `filial, departamento, nome`): `name;branch;department;building;floor;room;manager_name`, campos nulos como `""`.
- **Ausências obrigatórias**: nenhuma coluna "Ações"; nenhuma coluna "Bens"/contagem; sem `descricao`, sem `id` (FR-004).
- Valores com `;`, aspas, vírgulas ou quebras de linha escapados pelo `csv.writer` nativo.

## 4. UI — botão na tela de Locais (âncora)

| Propriedade | Valor | Precedente |
|---|---|---|
| Texto | exato `Exportar CSV` | 3 botões existentes |
| Markup | `<a href="/api/v1/reports/locations/csv" class="btn btn-ghost"><i class="bi bi-upload me-1"></i> Exportar CSV</a>` | `custodians/list.html` L13-15 |
| Posição | `page-header` da tela, primeiro botão do grupo | idem |
| Gate visual | `{% if can('relatorios.exportar') %}` | idem |
| Comportamento | download direto do navegador (`Content-Disposition: attachment`) | download interno das páginas de relatório |

## 5. Regras de não regressão (verificáveis por teste)

1. `GET /locations` (tela) sem alteração fora do botão: pesquisa (007), tabela, colunas, contagem de bens, links e ações idênticos.
2. Exportações existentes intocadas: `/api/v1/reports/custodians/csv`, `/api/v1/reports/inventory/csv` (+`_filtrado`), ata de inventário — mesmas rotas, filtros e respostas.
3. `LocationService.get_all` inalterado (a exportação consome, não modifica).
4. Usuário autenticado sem `relatorios.exportar`: botão ausente no HTML da tela **e** endpoint com 403.
5. Chamada sem sessão: 401 pelo mecanismo da API.
6. Operação read-only: snapshot de `Location` antes/depois da exportação é idêntico.
7. Zero locais: `200` com apenas a linha de cabeçalho (sem 500).
8. Nenhum `write_audit` novo exigido — coerente com as exportações existentes (IX/N-A).

## 6. Fora do contrato

- Excel/XLSX, PDF, outros formatos; exportação filtrada/sufixo `_filtrado`; nova tela de relatório; paginação; autocomplete; alteração de permissões; alteração das demais exportações.
