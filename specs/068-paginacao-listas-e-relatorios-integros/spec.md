# Feature Specification: Paginação nas Listas Web e Integridade de Relatórios/Exportações

**Feature Branch**: `068-paginacao-listas-e-relatorios-integros`

**Created**: 2026-10-10

**Status**: **APROVADA (2026-10-11)** — decisões **P1–P5** todas aprovadas (P1–P3 em 2026-10-10; **P4 e P5 em 2026-10-11**, ver Clarifications e §14). Artefatos de planejamento completos (`plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`, `checklists/requirements.md`); pronta para implementação pelo `tasks.md`. **Nenhuma implementação até aqui.**

**Input**: User description: "Criar a spec para aplicar o que foi apontado na análise de 2026-10-10 (`docs/ANALISE_SEG_PERF_UX_2026-10-10.md`): **P1** paginação real nas listas web + **P2** aviso de corte e exportação completa nos relatórios + **U5** audit log paginado. Escopo aprovado: todas as listas (equipamentos, movimentações, audit log, colaboradores, locais, inventários lista e itens); relatórios com **aviso + exportação completa**; **page size fixo em 200**."

---

## Clarifications

### Session 2026-10-10 (escopo decidido pelo responsável)

- Q: O que a spec resolve nos relatórios/exportações (hoje há corte silencioso de 10.000 linhas)? → A: **Aviso + exportação completa.** Elimina o teto gerando em lotes/streaming (CSV/XLSX/PDF) **e** avisa o usuário sempre que um corte técnico residual existir. A alternativa "só o aviso" e a alternativa "deixar relatórios para outra spec" foram descartadas.
- Q: Quais listas web ganham paginação? → A: **Todas as selecionadas** — Equipamentos (`/assets`), Movimentações (`/movements`), Audit log (`/admin/audit`), Colaboradores (`/custodians`) e Locais (`/locations`), além de Inventários (`/inventarios`) e os itens da tela de conferência (`/inventarios/{id}`).
- Q: Qual tamanho de página? → A: **200 — manter o tamanho atual** (`page_size` fixo, sem seletor nesta feature). Visual próximo do atual, escopo menor.

### Session 2026-10-11 (aprovação de P4 e P5)

- Q: **P4** — a tela `/reports/inventory` passa a ser paginada, eliminando o corte silencioso de 1.000 linhas (hoje sem total exibido)? → A: **APROVADA.** Libera a tarefa **T018**; `FR-008`, `SC-006` e `AC05` deixam de ser condicionais.
- Q: **P5** — eliminar o N+1 das listas paginadas trocando as contagens por linha por uma agregação única (`GROUP BY`)? → A: **APROVADA.** Libera a tarefa **T027**; `SC-010` e `FR-020` deixam de ser condicionais.
- Q: **P6 (achado na T002, 2026-10-11)** — incluir **`/reports/movements`**, que também corta em 1.000 (`reports.py:86`) e exibe `{{ total }}` sem avisar o corte? → A: **APROVADA — incluir.** `RF04`/`FR-008`/`SC-006`/`AC05`/`T018` passam a cobrir **as duas telas**. **`/reports/custodians`** (sem corte, porém com N+1 e carga total) **fica fora do escopo** e vira dívida em `docs/Melhorias_SisPatrimonio_Pro.md` (Constitution I).

> Decisões finais: **P1–P6 aprovadas** — nenhuma pendência de escopo remanescente (`[NEEDS CLARIFICATION]` = 0).

---

## 1. Diagnóstico do comportamento atual (Fase 1 — somente leitura, verificado 2026-10-10)

Método: leitura do código real (`app/web/routers/`, `app/services/`, `app/api/`, `app/web/templates/`), dos testes e da análise `docs/ANALISE_SEG_PERF_UX_2026-10-10.md`. **Nenhum arquivo da aplicação foi alterado, nenhuma migração executada, nenhum commit feito.**

### 1.1 Listas web: o que existe hoje

| Rota | Permissão | Chamada de dados | **Corte atual** | **Contador exibido** | Onde |
|---|---|---|---|---|---|
| `/assets` | `patrimonio.visualizar` | `AssetService.get_all(..., limit=200)` — já aceita `skip` e devolve `total` | **200 fixo, sem `offset`** | ✅ "Mostrando **X** de **Y** equipamentos" | `app/web/templates/assets/list.html:164` |
| `/movements` | `movimentacao.visualizar` | `MovementService.get_all_movements(..., limit=200)` — já aceita `skip` e devolve `total` | **200 fixo, sem `offset`** | ⚠️ "Mostrando **X** registros de fluxo" — **`total` é recebido pela rota e não é exibido** | `app/web/templates/movements/list.html:85` |
| `/custodians` | `colaboradores.visualizar` | `CustodianService.get_all` — **sem `limit`** (carrega tudo) | **nenhum** (tudo em memória) | ❌ nenhum | `app/web/routers/custodians.py::list_custodians_view`, `app/services/custodian_service.py:135` |
| `/locations` | `locais.visualizar` | `LocationService.get_all` — **sem `limit`** | **nenhum** | ❌ nenhum | `app/web/routers/locations.py::list_locations_view`, `app/services/location_service.py:20` |
| `/inventarios` | `inventario.visualizar` | `InventarioService.get_all` + `summary` **por inventário** (N+1) | **nenhum** | ❌ nenhum | `app/web/routers/inventario.py::list_inventarios` |
| `/inventarios/{id}` | `inventario.visualizar` | `itens = list(inv.itens)` e **filtro feito em Python** (busca/status) | **nenhum** | ⚠️ "Bens esperados: `expected_itens\|length`" (do conjunto filtrado em memória) | `app/web/routers/inventario.py::view_inventario`, `app/web/templates/inventarios/detail.html:212` |
| `/admin/audit` | `auditoria.visualizar` | `get_audit_logs(..., limit=min(200,1000))` — **sem `offset`** | **200 default / teto 1000** | ⚠️ "Mostrando **X** registro(s)" — sem total | `app/web/admin_routes.py::admin_audit_log` (L546), `app/services/audit_service.py:323` |
| `/reports/inventory` | `relatorios.visualizar` | `AssetService.get_all(..., limit=1000)` | **1000 fixo** | ❌ **nenhum** — o `total` é calculado e não aparece no template | `app/web/routers/reports.py::view_inventory_report`, `app/web/templates/reports/inventory.html` |
| `/reports/movements` | `relatorios.visualizar` | `MovementService.get_all_movements(..., limit=1000)` | **1000 fixo** | ⚠️ exibe `{{ total }} registros` (`movements_report.html:61`) **sem avisar** que só 1.000 estão na tela | `app/web/routers/reports.py::view_movements_report` (L84-89) — **incluída pela P6 (2026-10-11)** |
| `/reports/custodians` | `relatorios.visualizar` | `CustodianService.get_all` **sem corte** + `count_assigned_assets` por linha (**N+1**) | nenhum | ✅ `total = len(...)` coerente | `app/web/routers/reports.py::view_custodians_report` — **fora do escopo** (dívida registrada) |

**Fato comprovado 1 — nenhum template tem paginação.** Varredura em `app/web/templates/` por `pagination`/`page-item`: **0 arquivos**. Não existe controle "Anterior/Próxima", número de página nem parâmetro `page` em nenhuma rota web.

**Fato comprovado 2 — três modelos diferentes de corte**: (a) corte fixo sem offset (assets, movements, audit, relatório web); (b) sem corte, tudo em memória (custodians, locais, inventários, itens de inventário); (c) corte com offset **só na API**. Nenhum dos três permite chegar ao registro 201 da listagem principal.

**Fato comprovado 3 — contadores inconsistentes**: só `/assets` mostra total; `/movements` e `/admin/audit` mostram apenas o tamanho da página; `/custodians`, `/locations` e `/inventarios` não mostram nada; a tela de relatório não mostra nem total nem corte.

### 1.2 Relatórios e exportações: de onde vem o corte

| Artefato | Gerador | Teto aplicado | Aviso de corte |
|---|---|---|---|
| Tela `/reports/inventory` | `AssetService.get_all(limit=1000)` | **1.000 linhas** | **Nenhum** (o `total` é calculado e descartado na apresentação) |
| Tela `/reports/movements` | `MovementService.get_all_movements(limit=1000)` | **1.000 linhas** | **Nenhum** — o rótulo `{{ total }} registros` mostra o total real sem indicar o corte (P6) |
| CSV/XLSX/PDF do patrimônio (`/api/v1/reports/inventory/*`) | `ReportService.generate_inventory_*` → `get_filtered_assets` | **10.000** — `limit_query = limit if limit > 0 else 10000` em `app/services/report_service.py:47` | **Nenhum** — o arquivo sai incompleto como se estivesse completo |
| CSV/XLSX/PDF de movimentações | `generate_movements_csv` carrega `db.query(Movement)...all()` (`report_service.py:488`) | sem teto, **tudo em memória** | Nenhum |
| CSV de colaboradores / locais | `generate_custodians_csv` / `generate_locations_csv` | sem teto, tudo em memória | Nenhum |
| Ata de inventário (CSV/XLSX/PDF) | `_inventario_rows` (`report_service.py:535`) — `for item in inv.itens` | sem teto, tudo em memória | Nenhum |

As respostas são montadas inteiras em memória (`Response(content=csv_content)`); não há `StreamingResponse` em todo o projeto (grep = 0 ocorrências).

**Fato comprovado 4 — o risco patrimonial**: com base acima de 10.000 bens, o CSV/Excel/PDF do patrimônio sai **faltando registros, sem indicação alguma**, dentro de um sistema cujo propósito é prova documental (ata, termo, trilha). O mesmo vale para a tela de relatório acima de 1.000.

### 1.3 API REST (contexto — não alterada nesta feature)

| Endpoint | Paginação |
|---|---|
| `GET /api/v1/assets` | ✅ `skip` (ge=0) + `limit` (1..500, default 100) — `app/api/assets_api.py:46-47` |
| `GET /api/v1/movements` | ✅ `skip` + `limit` (1..500, default 100) — `app/api/movements_api.py:23-24` |
| `GET /api/v1/custodians` | ❌ sem paginação (retorna tudo) |
| `GET /api/v1/locations` | ❌ sem paginação (retorna tudo) |

As listas web **não** consomem a API (renderização server-side com Jinja2); portanto a paginação web não depende de mudança de API.

### 1.4 Recursos equivalentes já implementados (reaproveitamento obrigatório)

1. **Precedente interno de paginação**: `IntegrationCenterService.get_history(..., page, page_size)` (`app/services/integration_center_service.py:859-897`) devolve `{rows, total, page, page_size, pages}` com `offset = (page-1)*page_size` e clamps (`page_size` 1..100, `page >= 1`).
2. **Precedente visual**: `app/web/templates/admin/integracoes/historico.html:86-95` — "Página X de Y (N registros)" + botões **Anterior**/**Próxima** preservando `{{ request.query_params }}`.
3. **Precedente de macro Jinja compartilhada**: `app/web/templates/macros/locations.html` importada por `{% from "macros/..." import ... %}` — lugar natural para uma macro de paginação.
4. **Serviços já pagináveis**: `AssetService.get_all(skip, limit)` e `MovementService.get_all_movements(skip, limit)` já retornam `(itens, total)`.
5. **Filtros de auditoria já existentes no service**: `get_audit_logs` aceita `user_id`, `start_date`, `end_date` (`audit_service.py:323-334`) — **a rota web não os expõe**.
6. **Filtros já na query string**: todas as listas usam `<form method="get">`, logo os filtros atuais já são compartilháveis por URL e sobrevivem à troca de página.

### 1.5 Testes e regressão existente

| Arquivo | Relação com esta feature |
|---|---|
| `tests/route_manifest.json` (142 rotas) + `tests/test_route_inventory.py` | **Não será alterado**: a paginação usa apenas *query string*, **nenhuma rota nova** |
| `tests/test_report_print_smoke.py`, `tests/test_locations_export.py`, `tests/test_datetime_flows.py` | Geradores de relatório/exportação (CSV/PDF/XLSX/ata) — regressão obrigatória do US2 |
| `tests/test_inventario.py`, `tests/test_inventario_offline.py` | Tela de conferência e contadores — regressão obrigatória do US3 |
| `tests/test_movements_search.py`, `tests/test_assets.py`, `tests/test_api.py`, `tests/test_rbac.py` | Listas, busca e permissões |
| `tests/test_central_integracoes.py` | Protege o precedente de paginação que será generalizado |
| Baseline medido em 2026-10-10 | `.venv/bin/python -m pytest -q` → **1005 passed, 2 skipped em 88,79 s** |

### 1.6 Specs anteriores relacionadas

| Spec | Relação |
|---|---|
| `001-sistema-existente` | Baseline do sistema |
| `007`/`049`/`050` | Busca e nomenclatura de locais |
| `051` | Manifesto de rotas (`route_manifest.json`) — será **intocado** por não haver rota nova |
| `067-consulta-edicao-bens` | Mesmo padrão de artefatos; `assets/list.html` foi tocado apenas na ação por linha (sem paginação) |
| `docs/ANALISE_SEG_PERF_UX_2026-10-10.md` §3 P1/P2/P3 e §4 U5 | **Origem deste trabalho** |

---

## 2. Problema e motivação

Hoje o usuário **não consegue alcançar** os registros além do corte da listagem (200 em assets/movements/audit, 1.000 na tela de relatório) e **não é informado** quando uma exportação sai incompleta (10.000). Isso se manifesta de três formas concretas:

1. **Perda funcional**: em uma base de 3.000 bens, 2.800 não têm como ser vistos sem inventar um filtro que reduza a lista a 200. O próprio contador denuncia o problema ("Mostrando 200 de 3000") sem oferecer navegação.
2. **Risco documental**: um CSV/Excel/PDF de patrimônio emitido com mais de 10.000 registros sai truncado **sem nenhum aviso** — em sistema cujo valor é a prova documental.
3. **Risco de desempenho/estabilidade**: as listas sem corte (colaboradores, locais, inventários, itens de inventário) carregam tudo em memória **e** fazem uma consulta por linha (N+1) para as contagens; a tela de um inventário grande renderiza todos os itens e filtra em Python.

Não é uma falha de arquitetura — é acabamento de borda, coerente com os achados P1/P2/U5 da análise de 2026-10-10.

---

## 3. Objetivo e escopo

**Objetivo**: toda listagem web navegável até o último registro, todo relatório/exportação íntegro ou explicitamente avisado, com **nenhum corte silencioso** em lugar algum do sistema.

### INCLUI

- **RF01** Paginação web (parâmetro `page`, `page_size` fixo 200) nas listas: `/assets`, `/movements`, `/custodians`, `/locations`, `/inventarios`, `/inventarios/{id}` (itens) e `/admin/audit`.
- **RF02** Contador honesto em todas as listas: **total** de registros do filtro × **intervalo** exibido na página corrente.
- **RF03** Filtros e busca existentes preservados na troca de página (mesma query string).
- **RF04** Telas de relatório `/reports/inventory` **e `/reports/movements`** paginadas e com total visível (elimina o corte de 1.000 — P6).
- **RF05** Exportações CSV e Excel **sem teto** (varredura em lotes/streaming) e PDF **sem teto**, com aviso prévio na tela para conjuntos grandes.
- **RF06** Qualquer corte técnico residual (inclusive de PDF) MUST ser **avisado** — na tela e dentro do próprio arquivo, com contagem "exibido X de Y". **Nunca corte silencioso.**
- **RF07** Audit log com paginação e com os filtros de período/usuário já suportados pelo service expostos na interface.
- **RF08** Nenhuma rota nova, nenhuma permissão nova, **zero DDL**, nenhuma dependência nova.

### NÃO INCLUI

- Seletor de tamanho de página, preferência persistida por usuário, ordenação por coluna (P3 aprovada: 200 fixo).
- Paginação/ordenação das **APIs** `custodians` e `locations` (registrada como dívida; ver §1.3).
- Busca full-text, índice novo, mudança de `ilike` (análise P6 — outra feature).
- Streaming de exportação **de terceiros/integrações** fora de `ReportService`.
- Alteração do conteúdo lido (snapshots × leitura viva — P5 da 067), dos modelos, das permissões ou do layout geral.
- Refatorações não relacionadas (Constitution I).

---

## 4. Comportamento funcional esperado

### 4.1 Paginação (RF01/RF03)

- Toda lista aceita `?page=N` (default 1) e aplica `offset = (page-1) * 200`, `limit = 200` no **serviço** (nunca em Python).
- `page` inválido (`abc`, `0`, negativo, vazio) → **página 1**, sem erro.
- `page` maior que o total de páginas → **última página** com conteúdo, sem tela em branco.
- Filtros atuais (`search`, `status`, `category`, `location_id`, `custodian_id`, `brand`, `model`, `department`, `maintenance_status`, `purchase_date_*`, `movement_type`, `asset_id`, `module`, `action`, `result`) são lidos da query string **na mesma página** que carrega `page`.
- Os filtros continuam no `<form method="get">`; o controle de página é link com a query string completa.

### 4.2 Contadores (RF02)

- Indicador obrigatório em toda lista: `Mostrando X–Y de Z` (Z = total do filtro; X/Y = primeiro/último da página corrente).
- Listas que hoje não mostram nada (colaboradores, locais, inventários) passam a mostrar o indicador.
- Contadores de resumo que **não** dependem da página permanecem globais: "Bens esperados: N", "Conferidas/Restantes/Divergências" do inventário, contadores de manutenção/etiqueta.
- Nenhum número pode ser apresentado como total quando for apenas o tamanho da página (hoje: "Mostrando X registros de fluxo" e "Mostrando X registro(s)").

### 4.3 Tela de relatório (RF04)

- `/reports/inventory` e `/reports/movements` deixam de cortar em 1.000: passam a paginar com `page`/200 e a exibir `total` (P6).
- Os filtros continuam idênticos; os botões **Exportar CSV / Excel / PDF** continuam recebendo os mesmos filtros e exportam o **conjunto completo** (§4.4), não apenas a página atual.

### 4.4 Exportações (RF05/RF06)

- **CSV e Excel**: varrem todos os registros do filtro em **lotes de 1.000 linhas por passo** (constante única em `ReportService`, idêntica à de `research.md` R6 e do contrato de exportação) — sem `limit 10000`. CSV em `StreamingResponse` (memória constante); XLSX em modo *write-only*.
- **PDF**: sem teto; a tela avisa previamente quando o total exceder 10.000 linhas ("a geração pode demorar").
- Se por motivo técnico um corte residual existir (inclusive em PDF), o sistema MUST: (a) avisar na tela, (b) gravar o aviso **dentro do arquivo** (primeira linha/rodapé do CSV; célula/aviso no XLSX; nota no PDF), com `exibido X de Y` — nunca entregar arquivo truncado como completo.
- Cabeçalhos, delimitador (`;`), encoding UTF-8 com BOM, nome de arquivo e permissões (`relatorios.exportar`) permanecem **os mesmos**.

### 4.5 Audit log (RF07)

- `/admin/audit` ganha paginação (200) com total exibido.
- Passam a ser expostos na interface os filtros de **período** (`start_date`/`end_date`) e **usuário** (`user_id`), já suportados por `get_audit_logs` — sem alterar o service.
- Permissão exclusiva `auditoria.visualizar` (inalterada); a trilha continua imutável (nenhuma escrita/exclusão).

### 4.6 Itens de inventário (RF01/RF02)

- A busca e o filtro de status dos itens passam a ser aplicados **no serviço** (hoje em Python) e paginados, para que a página corrente corresponda ao filtro.
- A conferência (`POST /inventarios/{id}/buscar`, QR, reconciliação offline) **não muda**: após conferir, o usuário segue na mesma página/filtro, com os contadores globais atualizados.

---

## 5. User Scenarios & Testing *(mandatory)*

### User Story 1 — Navegar até qualquer registro da lista (Priority: P1)

Como usuário com permissão de visualização, na tela de Equipamentos (ou Movimentações), quero avançar e voltar entre as páginas de resultados vendo **"Mostrando 201–400 de 3.142"**, para encontrar um registro que não está na primeira página sem ter que inventar um filtro.

**Why this priority**: é a lacuna P1 da análise — hoje o registro 201 é inalcançável; entregar só isto já resolve o problema funcional nas duas listas mais usadas.

**Independent Test**: com 250 bens cadastrados, abrir `/assets`, conferir 200 linhas e o total 250, clicar em **Próxima**, conferir as 50 restantes e o intervalo "201–250".

**Acceptance Scenarios**:
1. **Given** 250 bens, **When** `/assets` é aberta, **Then** a página 1 mostra 200 linhas e "Mostrando 1–200 de 250", com link **Próxima** ativo.
2. **Given** a página 1 com filtros (`search=notebook&status=EM_USO`), **When** o usuário avança de página, **Then** os filtros permanecem aplicados e o total reflete o filtro.
3. **Given** `page=abc` ou `page=0` ou `page=9999`, **When** acessada, **Then** o sistema responde com uma página válida (1ª ou última), **HTTP 200**, sem erro e sem lista vazia por engano.
4. **Given** total ≤ 200, **When** a lista é aberta, **Then** **não** é exibido controle de página (sem ruído) e o indicador mostra o intervalo e o total.
5. **Given** um usuário sem a permissão da lista, **When** ele acessa a rota (inclusive com `?page=2`), **Then** 403 registrado na trilha (comportamento inalterado).

### User Story 2 — Exportar o relatório completo, sem surpresa (Priority: P2)

Como patrimonheiro/gestor, quero baixar o CSV/Excel/PDF do patrimônio com **todos** os registros do filtro — ou, se algum limite técnico sobrar, ver um aviso claro dizendo "exibindo X de Y" — para poder confiar no documento emitido.

**Why this priority**: é o risco documental da análise (P2/P3): arquivo incompleto entregue como completo.

**Independent Test**: exportar CSV com um filtro que resulte em mais de 10.000 registros e conferir que o número de linhas de dados é igual ao total exibido na tela.

**Acceptance Scenarios**:
1. **Given** uma base de 12.000 bens, **When** o CSV do patrimônio é exportado, **Then** o arquivo contém **12.000** linhas de dados (mais o cabeçalho) — sem `limit 10000`.
2. **Given** o mesmo volume, **When** o Excel é exportado, **Then** o arquivo contém os 12.000 registros e é gerado sem estourar memória (modo *write-only*).
3. **Given** a tela de relatório com total > 1.000, **When** ela é aberta, **Then** os registros são paginados e o **total real** aparece (nada de "1.000 sem aviso").
4. **Given** um corte técnico residual em PDF, **When** o arquivo é gerado, **Then** ele contém o aviso "exibindo X de Y" **e** a tela repete o aviso.
5. **Given** um usuário sem `relatorios.exportar`, **When** ele tenta exportar, **Then** 403 + registro na trilha (inalterado).

### User Story 3 — Auditar e listar o restante do sistema sem limite (Priority: P3)

Como auditor, quero paginar a trilha de auditoria e filtrá-la por **período/usuário** (já suportados internamente), e quero o mesmo comportamento em Colaboradores, Locais e Inventários — inclusive nos itens da conferência — para conseguir varrer o histórico inteiro e as listas grandes sem perder registros.

**Why this priority**: fecha o escopo aprovado (todas as listas + U5); é independente das demais e pode ser entregue por lista.

**Independent Test**: com 300 eventos de auditoria, abrir `/admin/audit?page=3` e conferir os 100+ registros da terceira página e o total; repetir para `/custodians`, `/locations` e `/inventarios`.

**Acceptance Scenarios**:
1. **Given** 250 colaboradores, **When** `/custodians` é aberta, **Then** a lista pagina (200 + 50) e mostra o total — hoje carrega tudo sem indicador.
2. **Given** um inventário com 400 itens, **When** a tela de conferência é aberta, **Then** os itens paginam **no servidor** com filtro de busca/status preservado, e os contadores globais ("Bens esperados: 400", conferidas/restantes) continuam corretos.
3. **Given** audit log com 500 eventos, **When** o filtro de período é aplicado, **Then** apenas os eventos do período aparecem, paginados, com total coerente.
4. **Given** qualquer uma dessas telas, **When** a página é compartilhada por URL, **Then** o destinatário vê exatamente a mesma página e filtros.

### Edge Cases

- **`page` não numérico ou negativo**: normalizado para 1 (sem 400/500).
- **`page` além do fim**: última página com dados (nunca lista vazia sem explicação).
- **Total zero**: indicador "Nenhum registro encontrado" (estado vazio existente), sem controle de página.
- **Filtro que reduz o total para menos que a página atual**: cai para a última página válida.
- **Conferência de inventário na última página**: após o POST de conferência o usuário permanece com o item localizável (mesmo filtro/página ou retorno previsível); contadores globais atualizados.
- **Itens não previstos × esperados**: a separação atual (`expected_itens`/`unlisted_itens`) é preservada — a paginação não pode embaralhar essa divisão nem ocultar a seção de não previstos.
- **Exportação com zero resultados**: arquivo com cabeçalho e nenhum dado, sem erro.
- **Interrupção do download de CSV em streaming**: resposta parcial; nenhum dado é gravado no sistema (só leitura).
- **Base > 10.000 com PDF**: aviso prévio na tela; se ainda assim gerar, corte residual avisado dentro do arquivo (RF06).
- **Fuso/hora e conteúdo dos arquivos**: inalterados (colunas, delimitador, encoding, rodapé de comprovação).

---

## 6. Requirements *(mandatory)*

### Functional Requirements

| Requisito | FR | Descrição |
|---|---|---|
| RF01 | **FR-001** | As listas `/assets`, `/movements`, `/custodians`, `/locations`, `/inventarios`, `/inventarios/{id}` e `/admin/audit` MUST aceitar `page` na query string e aplicar `offset/limit` **no serviço** com `page_size = 200`. |
| RF01 | **FR-002** | `page` ausente, vazio, não numérico, `<= 0` ou além do fim MUST resultar em página válida (1ª ou última) com HTTP 200 — nunca em erro 4xx/5xx nem lista vazia sem aviso. |
| RF01 | **FR-003** | A paginação MUST NOT adicionar rota, endpoint nem parâmetro de path: apenas *query string* (`tests/route_manifest.json` permanece válido sem alteração). |
| RF02 | **FR-004** | Toda lista MUST exibir total do filtro e intervalo da página (`Mostrando X–Y de Z`); indicadores que hoje mostram apenas o tamanho da página MUST passar a mostrar o total. |
| RF02 | **FR-005** | Contadores de resumo não paginados (bens esperados, conferidas/restantes/divergências, resumo de inventários, etiquetas) MUST permanecer **globais**, independente da página exibida. |
| RF02 | **FR-006** | Quando o total couber em uma única página, o controle de página MUST ser omitido (sem ruído visual). |
| RF03 | **FR-007** | Filtros e busca existentes MUST ser preservados na navegação entre páginas e na URL compartilhada; o comportamento de busca (campos, operadores, case-insensitive) MUST permanecer idêntico ao atual. |
| RF04 | **FR-008** | As telas `/reports/inventory` e `/reports/movements` MUST remover o corte de 1.000: paginar com `page`/200 e exibir o total real (filtro). **P4 aprovada em 2026-10-11, estendida pela P6** (§14). |
| RF04 | **FR-009** | Os botões de exportação da tela de relatório MUST continuar exportando o **conjunto completo filtrado** (não a página exibida), com os mesmos parâmetros de hoje. |
| RF05 | **FR-010** | CSV e Excel do patrimônio MUST conter **todos** os registros do filtro, sem `limit 10000`, varrendo o banco em lotes; o CSV MUST ser emitido em *streaming* e o XLSX em modo *write-only*. |
| RF05 | **FR-011** | O PDF MUST ser gerado sem teto de registros; quando o total exceder 10.000 linhas, a tela MUST avisar previamente que a geração pode demorar. |
| RF05 | **FR-012** | Permissões, encoding (UTF-8 BOM), delimitador (`;`), cabeçalhos, colunas, nome do arquivo e códigos HTTP das exportações MUST permanecer idênticos aos atuais. |
| RF06 | **FR-013** | Nenhum artefato MUST ser entregue truncado silenciosamente: se houver corte técnico residual, a tela MUST mostrar `exibido X de Y` e o próprio arquivo MUST carregar a mesma indicação. |
| RF07 | **FR-014** | `/admin/audit` MUST paginar (200) com total exibido e MUST expor os filtros de período (`start_date`/`end_date`) e usuário já suportados por `get_audit_logs`, sem alterar o service nem a imutabilidade da trilha. |
| RF08 | **FR-015** | A implementação MUST exigir as mesmas permissões atuais (`patrimonio.visualizar`, `movimentacao.visualizar`, `colaboradores.visualizar`, `locais.visualizar`, `inventario.visualizar`, `auditoria.visualizar`, `relatorios.visualizar`, `relatorios.exportar`) — **nenhuma permissão nova**. |
| RF08 | **FR-016** | **Zero DDL**: nenhuma tabela, coluna, índice ou migração nova; nenhuma dependência nova em `requirements.txt`. |
| RF08 | **FR-017** | Filtros e paginação MUST viver nos **services** (parâmetros aditivos com default que preservam todos os chamadores atuais, incluindo a API) — sem regra de negócio no router nem no template (Constitution II/III). |
| RF08 | **FR-018** | A alteração MUST ser incremental e cirúrgica (Constitution I): routers, services de listagem/relatório, templates de lista, macro de paginação, testes e documentação — sem refatorações não relacionadas. |
| — | **FR-019** | A suíte pytest existente MUST permanecer verde (nenhum teste removido, enfraquecido ou pulado) e novos testes MUST cobrir AC01–AC15 (Constitution VIII). |
| — | **FR-020** | A paginação MUST reduzir o custo por página (chamadas por linha convertidas em agregação) **apenas** nas listas desta feature, sem alterar o resultado exibido. |
| — | **FR-021** | `docs/ARQUITETURA_E_MANUTENCAO.md` e a central de ajuda (`/ajuda`) MUST registrar a paginação e a integridade das exportações (Constitution XI). |
| — | **FR-022** | O indicador e os controles de paginação MUST seguir o padrão visual existente (Bootstrap 5, tema claro/escuro, macros/componentes já usados, 403/404 amigáveis) e permanecer utilizáveis de **360 px** a desktop, sem sobreposição nem quebra de fluxo existente (Constitution X). |

### Key Entities

- **Nenhuma entidade nova.** A feature não cria tabela nem coluna.
- **Parâmetros de página** (`page`, `page_size`): efêmeros, só na URL; `page_size` fixo 200.
- **`Asset` / `Movement` / `Custodian` / `Location` / `Inventario` / `InventarioItem`**: apenas consultados com `offset/limit` e agregações; conteúdo inalterado.
- **`AuditLog`**: consultado com `offset/limit` e filtros já existentes; **somente leitura** (Constitution IX).
- **Relatórios** (`ReportService`): geradores de CSV/XLSX/PDF que deixam de aplicar `limit 10000` e passam a varrer em lotes.
- **Autorização**: permissões já existentes citadas em FR-015 (nenhuma nova).

---

## 7. Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em qualquer lista paginada, o **último registro** do filtro é alcançável pela interface (verificado com 250 registros: página 1 com 200, página 2 com 50).
- **SC-002**: 100% das listas do escopo exibem total do filtro e intervalo da página; 0 indicadores que apresentem apenas o tamanho da página como se fossem o total.
- **SC-003**: 100% dos testes de `page` inválido (vazio, `abc`, `0`, `-1`, `99999`) respondem HTTP 200 com página válida.
- **SC-004**: Exportação CSV/XLSX com 12.000 registros de teste contém **12.000** linhas/registros (igualdade com o total exibido) — corte de 10.000 eliminado.
- **SC-005**: 0 exportações entregues sem a indicação de total quando houver corte residual; a indicação existe **tela + arquivo** (teste automatizado de PDF).
- **SC-006**: As telas de relatório (`/reports/inventory` e `/reports/movements`) exibem o total real e nunca mais do que 200 linhas por página (corte de 1.000 eliminado). **P4 aprovada em 2026-10-11 (§14), estendida pela P6**.
- **SC-007**: Os contadores globais do inventário (esperados/conferidas/restantes/divergências) permanecem **idênticos** em qualquer página exibida.
- **SC-008**: Suíte pytest completa verde, com os novos testes da feature passando e nenhum teste existente alterado (baseline 2026-10-10: 1005 passed / 2 skipped).
- **SC-009**: `tests/route_manifest.json` **inalterado** e `tests/test_route_inventory.py` verde (prova de que nenhuma rota nova foi criada).
- **SC-010**: Nenhuma consulta SQL nova por linha nas listas paginadas (as contagens por linha viram agregação) — medido com contagem de queries antes/depois em lista de 200 itens. **P5 aprovada em 2026-10-11 (§14)**: a agregação faz parte do escopo (T027).
- **SC-011**: A página 1 de cada lista responde em tempo **não pior que o baseline medido** — critério objetivo: mediana **≤ baseline + 10%**, medido no harness da análise (SQLite in-memory + `TestClient`, 2.000 bens; `/assets` ≈ 33 ms e `/` ≈ 24 ms em 2026-10-10) — e a paginação não introduz N+1.
- **SC-012**: Nenhum acesso sem permissão é concedido: 100% das tentativas de paginação por usuário sem a permissão da lista respondem 403 com registro na trilha.

---

## 8. Compatibilidade

- **API REST**: **inalterada**. `GET /api/v1/assets` e `/movements` seguem com `skip/limit`; os services ganham parâmetros **aditivos com default** que preservam exatamente os chamadores atuais (inclusive `/api/v1/custodians` e `/api/v1/locations`, que continuam sem paginação — dívida registrada).
- **Autorização**: nenhuma permissão nova, nenhum perfil novo, mesmo `require_permission` nas mesmas rotas (Constitution VI).
- **Banco**: **zero DDL, zero migração** (Constitution VII). `skip/limit` e `GROUP BY` são portáveis entre MariaDB/MySQL e SQLite da suíte.
- **Rotas**: nenhuma rota nova → `tests/route_manifest.json` intocado (feature 051).
- **Exportações**: mesmo formato de saída; muda apenas a **completude** (sem teto) e o aviso de corte residual.
- **Inventário**: fluxo de conferência, reconciliação offline, encerramento e ata **inalterados**; apenas a apresentação da lista de itens pagina (Constitution V).
- **Documentação**: `docs/ARQUITETURA_E_MANUTENCAO.md` + central de ajuda atualizados na mesma implementação (Constitution XI).
- **Multiplataforma**: sem SQL específico, sem dependência nova; compatível com os ambientes Windows/Linux do projeto.

---

## 9. Alternativas avaliadas

| Alternativa | Descrição | Veredito |
|---|---|---|
| **A — Paginação por query string + services aditivos + macro de paginação reutilizando o precedente da 061/`historico.html`, com exports em lotes/streaming** | Resolve P1/P2/U5 com o menor diff, sem rota nova, sem DDL, sem permissão nova | ✅ **ESCOLHIDA** |
| B — Paginação client-side (carregar tudo e fatiar no navegador) | Reproduz o problema de memória das listas sem corte e não resolve exportação | ❌ Descartada |
| C — Apenas aumentar os cortes (200 → 10.000; 10.000 → 1.000.000) | Troca um corte silencioso por outro e mantém o risco documental | ❌ Descartada |
| D — Só o aviso de corte, sem eliminar o teto | Não resolve: usuário recebe arquivo incompleto que sabe incompleto | ❌ Descartada (decisão P1: aviso **+** exportação completa) |
| E — Grid/paginação com JavaScript (datatable, biblioteca nova) | Dependência nova, quebra o PWA offline e a regra de assets locais | ❌ Descartada (nenhuma dependência nova) |
| F — Paginar tudo na **API** e consumir via `fetch` nas telas | Reescreveria as listas Jinja inteiras, duplicaria autorização/estado vazio | ❌ Descartada (escopo desproporcional) |
| G — Ordenação por coluna + tamanho de página configurável | P3 aprovada: **200 fixo** nesta feature (evita escopo e teste extra) | ❌ Descartada nesta feature |
| H — Cursor/keyset pagination em vez de offset | Melhor em páginas muito profundas, mas exige ordenação estável e complica filtros; auditoria ordena por `timestamp` (não único) | ⚠️ Registrada como evolução futura; offset é suficiente para o volume atual |

---

## 10. Critérios de aceitação

- **AC01 — Navegação completa**: nas 7 listas do escopo, com mais de 200 registros, é possível chegar ao último registro pelos controles de página, com filtros preservados.
- **AC02 — Contadores honestos**: toda lista exibe `Mostrando X–Y de Z` (ou estado vazio); nenhum indicador apresenta só o tamanho da página como total.
- **AC03 — Parâmetros normalizados**: `page` inválido/fora do intervalo resulta em página válida HTTP 200.
- **AC04 — Sem ruído**: com total ≤ 200, não há controle de página e o indicador mostra o intervalo correto.
- **AC05 — Relatórios sem corte de 1.000 (P4/P6)**: as telas `/reports/inventory` e `/reports/movements` paginam e exibem o total real do filtro.
- **AC06 — CSV/Excel completos**: exportação com > 10.000 registros devolve exatamente o total de registros do filtro.
- **AC07 — PDF avisado**: PDF sem teto; total > 10.000 gera aviso prévio; qualquer corte residual aparece na tela **e** no arquivo com `exibido X de Y`.
- **AC08 — Auditoria paginada e filtrável**: `/admin/audit` pagina com total e filtra por período/usuário, sem alterar a trilha.
- **AC09 — Inventário preservado**: contadores globais e fluxo de conferência inalterados em qualquer página; itens filtrados no serviço, não em Python.
- **AC10 — Autorização intacta**: mesmo 403 + trilha para quem não tem a permissão da lista/exportação, com ou sem `page`.
- **AC11 — Contrato de API intacto**: `GET /api/v1/*` segue respondendo o mesmo (campos, códigos, `skip/limit`).
- **AC12 — Zero rota/DDL/permissão nova**: `route_manifest.json` inalterado, nenhuma migração, `requirements.txt` inalterado.
- **AC13 — Desempenho**: página 1 não fica mais lenta que o baseline medido; nenhum N+1 novo (SC-010/SC-011).
- **AC14 — Não regressão**: suíte completa verde sem editar teste existente (baseline 1005 passed / 2 skipped).
- **AC15 — UI consistente e responsiva (FR-022)**: indicador `X–Y de Z` e controles de paginação presentes nas 7 listas + tela de relatório, no padrão Bootstrap existente, renderizando **nada** quando há uma única página e permanecendo utilizáveis de **360 px** a desktop (marcador verificado por teste; 360 px verificado no `quickstart.md` §2).

---

## 11. Arquivos provavelmente envolvidos

| Arquivo | Alteração prevista (implementação futura) |
|---|---|
| `app/utils/pagination.py` | **NOVO**: helper de normalização/`offset`/`pages` no vocabulário de `get_history` (research R3) |
| `app/web/templates/macros/pagination.html` | **NOVO**: macro `pager(page, pages, total, ...)` reaproveitando o markup de `admin/integracoes/historico.html:86-95` |
| `app/web/routers/assets.py`, `movements.py`, `custodians.py`, `locations.py`, `inventario.py` | **ALTERAR**: ler `page`, passar `skip`, expor `total`/`page`/`pages` no contexto |
| `app/web/admin_routes.py` | **ALTERAR** (`admin_audit_log`): paginação + filtros de período/usuário |
| `app/web/routers/reports.py` | **ALTERAR** (`view_inventory_report` **e** `view_movements_report`): remover `limit=1000`, paginar, exibir total e aviso prévio de PDF |
| `app/services/audit_service.py` | **ALTERAR (aditivo)**: parâmetro `offset` com default, preservando o `limit` e todos os chamadores atuais |
| `app/services/asset_service.py`, `app/services/movement_service.py` | **INTOCADOS**: já aceitam `skip`/`limit` e devolvem `(lista, total)` — só a rota passa `skip` (research R4) |
| `app/services/custodian_service.py`, `location_service.py`, `inventario_service.py` | **ALTERAR (aditivo)**: aceitar `skip`/`limit`/`offset` com default que mantém "retorna tudo" para os chamadores atuais |
| `app/services/report_service.py` | **ALTERAR**: eliminar `limit 10000` (`get_filtered_assets`), gerar CSV em lotes/*streaming*, XLSX *write-only*, PDF sem teto + aviso; wrappers existentes preservados como API |
| `app/api/reports_api.py`, `app/web/routers/reports.py` (exports) | **ALTERAR (mínimo)**: devolver `StreamingResponse` no CSV mantendo headers/status |
| `app/web/templates/assets/list.html`, `movements/list.html`, `custodians/list.html`, `locations/list.html`, `inventarios/list.html`, `inventarios/detail.html`, `admin/audit/list.html`, `reports/inventory.html`, `reports/movements_report.html` | **ALTERAR**: indicador `X–Y de Z` + `{% include/import %}` da macro de paginação |
| `tests/test_paginacao_relatorios_068.py` | **NOVO**: AC01–AC15 |
| `tests/route_manifest.json` | **INTOCADO** (nenhuma rota nova) |
| `docs/ARQUITETURA_E_MANUTENCAO.md`, `app/services/help_service.py` | **ALTERAR**: documentação e central de ajuda (FR-021) |
| `app/models/*`, `app/services/permission_service.py`, `app/api/deps.py`, `requirements.txt` | **INTOCADOS** (zero DDL, zero permissão nova, zero dependência) |

---

## 12. Plano mínimo de testes

**Regressão obrigatória (sem alterar asserções existentes)**: `test_report_print_smoke.py`, `test_locations_export.py`, `test_datetime_flows.py` (ata), `test_inventario.py`, `test_inventario_offline.py`, `test_movements_search.py`, `test_assets.py`, `test_api.py`, `test_rbac.py`, `test_route_inventory.py` (manifesto **sem** mudança), `test_central_integracoes.py` (precedente de paginação), + régua completa `python -m pytest`.

**Novos testes** (`tests/test_paginacao_relatorios_068.py`, fixtures `client`/`db_session`, SQLite in-memory):

> **Fonte única**: o **`tasks.md`** (T006, T007, T014, T021, T027) manda **quando e onde** cada teste é escrito — a tabela abaixo é apenas o **mapa teste ↔ critério**; em qualquer divergência de nomenclatura ou de cobertura, prevalece o `tasks.md`.

| Teste | Protege |
|---|---|
| `test_assets_pagina1_mostra_200_e_total` / `test_assets_pagina2_mostra_restantes` | AC01/AC02 (intervalo e total) |
| `test_pagina_preserva_filtros` | AC01 (busca/status sobrevivem à troca de página) |
| `test_page_invalida_cai_em_pagina_valida` (`abc`, `0`, `-1`, `99999`) | AC03 |
| `test_lista_pequena_oculta_controle_de_pagina` | AC04 |
| `test_colaboradores_e_locais_paginam_com_total` | AC01/AC02 (hoje sem corte e sem contador) |
| `test_relatorio_web_sem_corte_de_1000` | AC05 (total real + página — **as duas telas**: inventory e movements) |
| `test_export_csv_completo_acima_de_10000` (monkeypatch do teto/geração em lote) | AC06 (FR-010) |
| `test_export_xlsx_completo` | AC06 |
| `test_pdf_aviso_previo_e_corte_residual_avisado` | AC07 (tela + arquivo) |
| `test_audit_pagina_com_total_e_filtros_periodo_usuario` | AC08 |
| `test_audit_sem_permissao_retorna_403_com_page` | AC10 |
| `test_inventario_contadores_globais_invariantes_por_pagina` / `test_inventario_itens_filtrados_no_servico` | AC09 |
| `test_api_custodians_e_assets_preservam_contrato` | AC11 |
| `tests/test_route_inventory.py` (suíte **existente**: compara rotas × `route_manifest.json`) | AC12 |
| `test_listas_sem_n1_de_contagem` (contagem de queries) | AC13/SC-010 |
| `test_export_ignora_page_e_devolve_filtro_completo` | AC06/**FR-009** (exportação não herda a página exibida) |
| `test_listas_403_sem_permissao_com_page` | AC10/**SC-012** (403 + trilha em qualquer lista, com ou sem `page`) |
| `test_pager_renderiza_nas_sete_listas` | **AC15**/FR-022 (marcador em todas as listas + relatório; omitido quando `pages <= 1`) |

**Procedimento**: suíte em SQLite in-memory (padrão da casa); nenhuma escrita em banco real; validação manual opcional via `quickstart.md`. Medição de desempenho (SC-011) reproduz o harness da análise de 2026-10-10 (2.000 bens) e registra tempo/queries antes e depois em `validacao.md`.

---

## 13. Riscos e medidas de mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Exportação incompleta ser usada como prova documental | **Alto** (patrimonial) | RF05/RF06 + AC06/AC07: sem `limit 10000` + aviso tela/arquivo |
| CSV gigante em streaming quebrar clientes/expectativa de header | Médio | Mesmo encoding/delimitador/cabeçalho (FR-012) + teste de conteúdo igual ao total |
| XLSX/PDF estourar memória em base muito grande | Médio | XLSX *write-only*; PDF com aviso prévio >10.000 (FR-011) e corte residual avisado (FR-013) |
| Testes existentes quebrarem por passarem a ver só 200 linhas | Médio | `page_size=200` == corte atual de assets/movements; listas sem corte hoje têm volume pequeno nos testes; regressão completa em T-setup |
| Filtros de inventário em Python migrarem para o service e mudarem resultado | Médio | Casos de teste de busca/status com itens "não previstos" e acentuação (AC09) |
| Contadores globais do inventário passarem a refletir a página | Alto (prova de conferência) | FR-005 + teste de invariância por página (AC09) |
| Regressão de desempenho (paginação piorar a página 1) | Médio | `offset/limit` no serviço + SC-011 medido antes/depois; agregação de contagens (FR-020) |
| Escopo inflar (ordenar colunas, tamanho configurável, API de locais) | Médio | §3 "NÃO INCLUI" + tabela §11 fechada no diff final |
| `route_manifest` / `test_route_inventory` quebrarem | Baixo | Nenhuma rota nova é permitida (FR-003/AC12) |
| Streaming + dependência de geração síncrona no mesmo request | Baixo | CSV *streaming* é leitura pura; XLSX/PDF seguem síncronos como hoje |

---

## 14. Decisões P1–P5

- **P1 — Relatórios/exportações**: ✅ **APROVADA (2026-10-10): aviso + exportação completa.** Elimina o teto de 10.000 varrendo em lotes/streaming e avisa sempre que sobrar corte técnico. Alternativas "só aviso" e "deixar para outra spec" descartadas (ver Clarifications).
- **P2 — Escopo das listas**: ✅ **APROVADA (2026-10-10): todas** — `/assets`, `/movements`, `/admin/audit`, `/custodians`, `/locations`, `/inventarios` e itens de `/inventarios/{id}`.
- **P3 — Tamanho de página**: ✅ **APROVADA (2026-10-10): 200 fixo**, sem seletor de tamanho e sem preferência de usuário nesta feature. Alternativas 50/100/dinâmico descartadas.
- **P4 — Tela de relatório paginada (eliminar o corte de 1.000)**: ✅ **APROVADA (2026-10-11)** — `/reports/inventory` pagina com `page`/200 e exibe o total real; **estendida em 2026-10-11 pela P6** para `/reports/movements`; libera **T018**. (`FR-008`, `SC-006`, `AC05` deixam de ser condicionais.)
- **P6 — Escopo dos relatórios (achado na T002)**: ✅ **APROVADA (2026-10-11): incluir `/reports/movements`** (mesma paginação/indicador); **`/reports/custodians` fora do escopo** → dívida (N+1 + carga total) em `docs/Melhorias_SisPatrimonio_Pro.md`.
- **P5 — Eliminar N+1 das listas paginadas (agregação de contagens em colaboradores/locais/inventários)**: ✅ **APROVADA (2026-10-11)** — contagens por linha viram agregação única (`GROUP BY`), com teste de contagem de queries; libera **T027** e mantém `SC-010`/`FR-020` no escopo de aceitação.

**Limitações desta execução**: somente leitura — nenhum arquivo funcional alterado, nenhuma migração, nenhum teste executado que escreva fora do escopo, nenhum commit. Esta spec **não** cria rota, tabela, coluna, permissão nem dependência: ela delimita o que será feito na implementação, com **P1–P5 todas aprovadas** (§14).

---

**Próximo passo**: implementar pelo `tasks.md` (Setup → Foundational → US1 → US2 → US3 → Polish), dentro do escopo §11 e conforme as decisões **P1–P5 aprovadas** (P1–P3 em 2026-10-10, P4–P5 em 2026-10-11).
