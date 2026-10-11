# Research — 068-paginacao-listas-e-relatorios-integros

> Decisões técnicas levantadas na leitura de código (somente leitura, 2026-10-10). Cada `R` responde a uma pergunta concreta de implementação e aponta para a evidência usada.

## R1 — Modelo de paginação: query string `page` + `page_size` fixo

- **Decisão**: parâmetro `page` (inteiro, default 1) na *query string*; `page_size = 200` constante da casa (P3 aprovada), sem seletor.
- **Cálculo**: `offset = (page - 1) * 200`, aplicado como `.offset(offset).limit(200)` **no service**.
- **Por que**: (a) todas as listas já usam `<form method="get">`, então filtros e página convivem na mesma URL; (b) sem rota nova → `tests/route_manifest.json` fica válido; (c) a API já usa `skip`/`limit` (`assets_api.py:46`, `movements_api.py:23`), então o vocabulário do sistema é esse.
- **Alternativa descartada**: *cursor/keyset* — melhor em páginas profundas, mas exige ordenação estritamente estável (`Movement.timestamp` não é único) e complica os filtros atuais; registrada como evolução futura (spec §9, alternativa H).

## R2 — Onde viverá a lógica de página

- **Decisão**: helper **`app/utils/pagination.py`** com funções puras:
  - `parse_page(raw: str | None) -> int` (normaliza `None`/`""`/`"abc"`/`0`/`-1` → `1`);
  - `offset_for(page: int, page_size: int = 200) -> int`;
  - `page_meta(total, page, page_size) -> dict` devolvendo `{page, page_size, pages, total, start, end, has_prev, has_next}`.
- **Por que**: 8 rotas precisam do mesmo comportamento; sem helper, a normalização de `page` seria copiada 8× (e divergiria). Padrão da casa para utilitários: `app/utils/time_utils.py`.
- **Vocabulário**: espelha `IntegrationCenterService.get_history` (`integration_center_service.py:859-897`), que já devolve `{rows, total, page, page_size, pages}` — manter nomes iguais facilita ler o código da casa.

## R3 — Apresentação: macro Jinja reaproveitando o markup existente

- **Decisão**: **`app/web/templates/macros/pagination.html`** com `pager(page, pages, total, start, end)`, importada por `{% from "macros/pagination.html" import pager %}` e incluída ao pé de cada lista.
- **Evidência de precedente**: `admin/integracoes/historico.html:86-95` já renderiza "Página X de Y (N registros)" com botões **Anterior**/**Próxima** preservando `{{ request.query_params }}`; e `templates/macros/locations.html` já é a casa das macros compartilhadas.
- **Comportamento**: com `pages <= 1` a macro renderiza **nada** (FR-006 — sem ruído); o indicador `Mostrando X–Y de Z` fica no corpo do template (texto existente, agora padronizado).

## R4 — Services: parâmetros aditivos com default (Constitution I)

| Service | Hoje | Mudança |
|---|---|---|
| `AssetService.get_all` | já tem `skip=0`, `limit=100` e devolve `(lista, total)` | **nada** (só a rota passar `skip`) |
| `MovementService.get_all_movements` | já tem `skip`/`limit` e devolve `(lista, total)` | **nada** |
| `CustodianService.get_all` | **sem** `limit` (retorna tudo) | `skip: int = 0, limit: int = 0` — **`0` mantém "retorna tudo"** (chamadores atuais, incl. API, intactos) |
| `LocationService.get_all` | idem | idem |
| `InventarioService.get_all` | sem limit | idem |
| `audit_service.get_audit_logs` | `limit=200`, **sem offset** | `offset: int = 0` aditivo |
| `report_service.get_filtered_assets` | `limit=0 → 10000` | **remover o teto**: `limit=0` passa a significar "todos" (lotes), mantendo a assinatura |
| `InventarioService` (itens) | filtro em Python em `view_inventario` | novo método `get_itens(db, inventario_id, *, search, status, skip, limit) -> (itens, total)` |

- **Por que `limit=0` = sem teto** em `Custodian/Location/Inventario`: é o default atual (todos) — nenhum chamador muda de comportamento sem que a rota explicitamente passe `skip/limit`.

## R5 — Itens de inventário: filtro sair do Python

- **Hoje** (`inventario.py::view_inventario`): `itens = list(inv.itens)` + `filter`/`status_filter` aplicados em Python + `expected_itens`/`unlisted_itens` derivados disso.
- **Decisão**: mover a filtragem para `InventarioService` (SQL com join em `Asset` para busca por tombamento/nome) e paginar **sobre o filtro**; `expected_itens`/`unlisted_itens` continuam sendo a divisão da **página corrente**, enquanto os **contadores** (esperados, conferidas, restantes, divergências) vêm de `InventarioService.summary` (agregação no banco) e **não** mudam com a página (FR-005).
- **Risco coberto**: embaralhar a seção "não previstos" ou fazer os contadores reflitirem a página (spec §13).

## R6 — CSV sem teto: lotes + `StreamingResponse`

- **Decisão**: `ReportService.iter_inventory_csv_rows(...)` — gerador que varre o banco em **lotes de 1.000** (`offset/limit`) e rende linhas CSV; `generate_inventory_csv` (API atual) passa a ser `"".join(...)` do mesmo gerador, **preservando a assinatura** usada pelos testes e chamadores atuais.
- **Rota**: `export_inventory_csv` devolve `StreamingResponse(gen, media_type="text/csv; charset=utf-8-sig", headers={"Content-Disposition": ...})` — mesmos headers/status de hoje (`reports_api.py`).
- **Evidência**: hoje não existe `StreamingResponse` no projeto (grep = 0); a resposta é `Response(content=csv_content)` montada inteira.
- **Por que lotes**: memória constante e comportamento idêntico em MariaDB e SQLite; `query.count()` único para o total (já é assim).

## R7 — Excel sem teto: OpenPyXL *write-only*

- **Decisão**: `Workbook(write_only=True)` + `WriteOnlyWorksheet.append(row)` gerando linhas a partir do **mesmo** iterador de lotes do CSV.
- **Evidência**: `openpyxl==3.1.5` instalado (`requirements.txt` exige `>=3.1.0`) — `write_only` é suportado desde a série 2.x/3.x.
- **Cuidado**: em modo *write-only* não se lê células existentes; os estilos/cabeçalho precisam ser aplicados via `WriteOnlyCell` (a casa já monta cabeçalho manualmente nos CSVs).

## R8 — PDF: sem teto + aviso prévio

- **Decisão**: `generate_inventory_pdf` recebe o mesmo iterador completo (ReportLab monta o documento paginado em memória — não há como "streamar" PDF paginado sem gerar de uma vez).
- **Aviso**: a **tela** exibe alerta quando `total > 10.000` ("a geração pode demorar") antes do download; se por limite técnico um corte residual existir, ele é escrito **no próprio PDF** e repetido na tela (FR-013).
- **Por que não streaming**: ReportLab `SimpleDocTemplate.build` consome a lista inteira; trocar de biblioteca está fora do escopo (Constitution I) e nenhuma dependência nova é permitida.

## R9 — Tela de relatório: eliminar `limit=1000`

- **Hoje**: `view_inventory_report` chama `AssetService.get_all(..., limit=1000)` e o template **não exibe** `total` (verificado em `reports/inventory.html`). **`view_movements_report`** (`reports.py:86`) repete `limit=1000` e o template **exibe** `{{ total }} registros` (`movements_report.html:61`) **sem avisar o corte** — achado da T002, incluído pela **P6**.
- **`/reports/custodians`** (T002): não corta (`total = len(...)` coerente), mas faz **N+1** de contagens e carrega tudo → **fora do escopo** (Constitution I); dívida registrada em `docs/Melhorias_SisPatrimonio_Pro.md`.
- **Decisão (P4 — aprovada em 2026-10-11; estendida pela P6)**: mesma paginação das listas (`page`/200) + indicador de total + aviso prévio de PDF **nas duas telas**; os botões de exportação **continuam** mandando os filtros (não a página) para `/api/v1/reports/inventory/*`.

## R10 — Audit log: paginação + filtros já existentes

- **Hoje**: rota `admin_audit_log` com `limit: int = 200` e `min(limit, 1000)`, **sem offset**; `get_audit_logs` **já aceita** `user_id`, `start_date`, `end_date` (`audit_service.py:323-334`) — mas a rota não os expõe.
- **Decisão (P4/P5 do escopo)**: rota lê `page`, `start_date`, `end_date`, `user_id` da query string e os repassa **sem mudar o service** (além do `offset` aditivo). Filtros de `module`/`action`/`result` permanecem como estão.
- **Imutabilidade**: apenas leitura — nenhuma rota de escrita/exclusão é criada (Constitution IX).

## R11 — N+1 das listas (P5 — aprovada em 2026-10-11)

- **Hoje**: `custodians` faz `count_assigned_assets` **por linha**; `locations` faz `count_assets` **por linha**; `inventarios` faz `summary` (2 queries) **por inventário**.
- **Decisão**: substituir por agregações (`func.count` + `group_by(fk)`) executadas **uma vez** por página, alimentando um `dict` no contexto — mesmo resultado exibido, 1+3 consultas no lugar de 1+2N.
- **Validação**: teste de contagem de queries (SC-010/FR-020) comparando antes/depois com 200 linhas na página — obrigatório (T027).

## R12 — Estratégia de testes e regressão

- **Suíte nova**: `tests/test_paginacao_relatorios_068.py` com fixtures `client`/`db_session` de `tests/conftest.py` (SQLite in-memory, PBKDF2=1000), cobrindo AC01–AC15.
- **TDD**: testes de página/contador escritos primeiro (RED contra o template atual), depois rota/service (GREEN).
- **Regressão obrigatória**: `test_report_print_smoke.py`, `test_locations_export.py`, `test_datetime_flows.py`, `test_inventario.py`, `test_inventario_offline.py`, `test_movements_search.py`, `test_assets.py`, `test_api.py`, `test_rbac.py`, `test_route_inventory.py`, `test_central_integracoes.py`.
- **Manifesto**: nenhuma rota nova → `route_manifest.json` **não** é tocado; se alguma alteração de rota aparecer no diff, é **sinal de erro** de escopo e deve parar a implementação.
- **Medição**: reproduzir o harness da análise de 2026-10-10 (2.000 bens) para SC-011/SC-010 e registrar em `validacao.md` — harness temporário é removido ao final (padrão da 067).
