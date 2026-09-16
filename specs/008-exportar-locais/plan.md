# Implementation Plan: Exportação CSV de Locais

**Branch**: `008-exportar-locais` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-exportar-locais/spec.md`

## Summary

Adicionar botão **"Exportar CSV"** na tela de Locais (markup idêntico aos 3 botões existentes: `btn btn-ghost` + `bi-upload me-1`, gate `relatorios.exportar`) com **download direto** para um novo endpoint no `reports_api.py` (`GET /api/v1/reports/locations/csv`), gerado por novo método `generate_locations_csv` no `ReportService` existente (padrão exato de `generate_custodians_csv`: `csv.writer`, `;`, `QUOTE_MINIMAL`, cabeçalhos PT minúsculos, campos vazios como `""`), resposta `text/csv; charset=utf-8-sig` + `attachment; filename=locais.csv`. CSV contém **somente dados cadastrais** (nome, filial, departamento, prédio, andar, sala, gestor — decisão do responsável: sem "Ações" e sem "Bens"), todos os locais, na ordenação da listagem. Zero DDL, zero permissão nova, zero tela nova.

## Technical Context

**Language/Version**: Python 3.10+ (stack existente, Constitution §Restrições)

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2, Jinja2 + Bootstrap 5, `csv`/`io` stdlib (todos existentes — nenhuma dependência nova)

**Storage**: MariaDB/MySQL via `DATABASE_URL` (PyMySQL) — **zero DDL**; somente `SELECT`; SQLite restrito à suíte de testes (padrão existente)

**Testing**: pytest + TestClient (padrão existente); novo arquivo `tests/test_locations_export.py`

**Target Platform**: Servidor web local/Windows (existente), navegadores já suportados

**Project Type**: Aplicação web monolítica existente (FastAPI + Jinja2 server-side)

**Performance Goals**: Exportação completa com o volume atual de locais em < 2s (mesma ordem das exportações existentes)

**Constraints**:
- Reuso obrigatório: geração no `ReportService` (padrão `generate_custodians_csv`), resposta no padrão de `reports_api.py` — **nenhuma nova forma de gerar CSV** (FR-003).
- CSV **mono-dado**: `name;branch;department;building;floor;room;manager_name` — sem "Ações", sem "Bens" (FR-004, decisão do responsável registrada na spec).
- Exporta **todos** os locais (FR-006, precedente da tela gêmea) — o endpoint **não** recebe `search`.
- Gate do endpoint: `relatorios.exportar` (FR-007, padrão dos endpoints CSV); botão gated por `can('relatorios.exportar')`.
- Nenhuma tela nova, nenhuma dependência nova, nenhuma permissão nova, zero DDL (escopo da spec).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente | ✅ PASS | Extensão por adição (1 método em service existente, 1 endpoint em router existente, 1 âncora em template existente); nenhuma funcionalidade alterada ou removida; tela de Locais intacta fora do botão |
| II | Arquitetura em camadas | ✅ PASS | Geração no service (`ReportService`); rota API só autentica, delega e monta a resposta (padrão de `export_custodians_csv`) |
| III | Regras de negócio nos services | ✅ PASS | Regra das colunas/ordenação/campos vazios concentrada no `ReportService`; endpoint sem lógica de negócio |
| IV | Integridade patrimonial | ✅ PASS | Operação read-only; nenhum estado/localização/custódia alterado |
| V | Integridade do inventário | ✅ PASS | Nenhum fluxo de inventário tocado |
| VI | Segurança (auth, RBAC, AD) | ✅ PASS | Endpoint com `require_permission("relatorios.exportar")` + auth da API (herdada do `api_v1_router`); botão com `can('relatorios.exportar')`; sem credenciais envolvidas |
| VII | Banco MariaDB e proteção dos dados | ✅ PASS | Zero DDL, zero migração; somente `SELECT` |
| VIII | Testes como não regressão | ✅ PASS | TDD: testes novos em `tests/test_locations_export.py` **antes** da implementação; nenhum teste existente editado; suíte completa verde ao final |
| IX | Auditoria | ✅ PASS/N-A | Exportações existentes **não são auditadas** (`write_audit`: 0 em `reports_api.py`) — consulta read-only não se enquadra nas operações relevantes; coerência mantida |
| X | Interface consistente | ✅ PASS | Botão com markup idêntico aos 3 existentes (`bi-upload me-1`, `btn-ghost`, `page-header`, gate visual); ajuda embutida atualizada |
| XI | Documentação fiel | ✅ PASS | Atualização na mesma tarefa: artigo `cadastrar-locais` (seção "Exportar locais") + nota no §12.5 do `ARQUITETURA_E_MANUTENCAO.md` |
| XII | Spec-driven + validação | ✅ PASS | Fluxo Spec Kit em curso; validação final = suíte + quickstart (T-ui manual) |

**Post-design re-check**: sem violações — o desenho não introduz nova camada, novo padrão de geração, nova tela, nova permissão nem novo formato (Complexity Tracking vazio).

## Project Structure

### Documentation (this feature)

```text
specs/008-exportar-locais/
├── plan.md              # This file
├── research.md          # Phase 0 — decisões R1–R5
├── data-model.md        # Phase 1 — dados consultados (read-only)
├── contracts/
│   └── locations-csv-contract.md   # Phase 1 — contrato GET /api/v1/reports/locations/csv
├── quickstart.md        # Phase 1 — protocolo de validação
└── tasks.md             # Phase 2 (/speckit-tasks) — NÃO criado aqui
```

### Source Code (repository root)

```text
app/
├── services/
│   └── report_service.py          # ALTERAR: novo generate_locations_csv (junto aos generate_*_csv)
├── api/
│   └── reports_api.py             # ALTERAR: novo endpoint GET /locations/csv (junto aos export_*_csv)
└── web/
    └── templates/
        └── locations/
            └── list.html          # ALTERAR: botão "Exportar CSV" no page-header (gate relatorios.exportar)
tests/
└── test_locations_export.py       # CRIAR: suíte TDD da feature
app/services/help_service.py      # ALTERAR (docs XI): seção "Exportar locais" no artigo
docs/ARQUITETURA_E_MANUTENCAO.md  # ALTERAR (docs XI): nota na §12.5
```

**Structure Decision**: Estrutura monolítica existente mantida; alterações restritas ao trio service → API endpoint → template (mesmo desenho da exportação de colaboradores), testes em arquivo novo.

## Implementation Flow (ordem de integração)

1. **Service** (`report_service.py`): novo `generate_locations_csv(db, locations: Optional[List[Location]] = None) -> str` — análogo direto de `generate_custodians_csv`:
   - Se `locations is None` → `LocationService.get_all(db)` (**todos**, ordenação `branch, department, name` — FR-006).
   - `io.StringIO` + `csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)`.
   - Cabeçalho PT minúsculo: `nome;filial;departamento;predio;andar;sala;gestor`.
   - Uma linha por local: `c.name, c.branch, c.department, c.building or "", c.floor or "", c.room or "", c.manager_name or ""` (padrão `c.cpf or ""` do gêmeo) — **sem "Ações", sem "Bens"** (FR-004).
2. **Endpoint** (`reports_api.py`): `GET /locations/csv` com `dependencies=[Depends(require_permission("relatorios.exportar"))]` — corpo idêntico ao de `export_custodians_csv`: chama o service, responde `Response(content=csv_content, media_type="text/csv; charset=utf-8-sig", headers={"Content-Disposition": "attachment; filename=locais.csv"})`. **Sem parâmetro `search`** (FR-006). Router já registrado em `app/main.py` → publicação automática.
3. **Template** (`locations/list.html`): no `page-header`, adicionar o link com markup idêntico ao de `custodians/list.html` L13-15: `{% if can('relatorios.exportar') %}<a href="/api/v1/reports/locations/csv" class="btn btn-ghost"><i class="bi bi-upload me-1"></i> Exportar CSV</a>{% endif %}` — posicionado como primeiro botão do grupo (precedente de colaboradores), convivendo com "Importar CSV"/"Cadastrar Novo Local" (gated por `locais.criar`) existentes.
4. **Testes** (`tests/test_locations_export.py`, TDD — vermelho antes do verde):
   - US1: botão visível com permissão (`client`); download 200 com headers padrão e `filename=locais.csv`; conteúdo com todos os locais; tela continua funcionando.
   - US2: cabeçalho exato; linha por local com valores esperados; escapamento de `;`/aspas/acentos no nome; vazios como `""`; **sem "Ações"/"Bens"**; ordenação da listagem.
   - US3: oculto sem `relatorios.exportar`; endpoint 403 sem a permissão (padrão de `test_rbac.py` L137-138: usuário "Técnico" via `unauth_client` para 401 e usuário sem permissão quando aplicável); read-only (snapshot antes/depois); `generate_locations_csv(db)` direto = todos.
5. **Documentação** (Constitution XI, mesma tarefa): seção "Exportar locais" no artigo `cadastrar-locais` da ajuda; nota no §12.5 (Relatórios) do doc de arquitetura registrando o novo CSV e a decisão "todos, sem colunas de interface".

## Error Handling

| Cenário | Comportamento |
|---|---|
| Nenhum local cadastrado | Download entregue com apenas a linha de cabeçalho (padrão CSV; sem erro) |
| Nome/valores com `;`, aspas, acentos, quebra de linha | Escapamento pelo `csv.writer` padrão (mesmo mecanismo das exportações existentes) |
| Chamada sem autenticação | 401 pelo mecanismo da API (padrão `/api/v1/reports/*`) |
| Chamada autenticada sem `relatorios.exportar` | 403 por `require_permission` (padrão de `export_inventory_csv`, provado em `test_rbac.py`) |
| Falha de banco | Comportamento existente (exceção propagada pelo handler global) — nenhum tratamento novo inventado |

## Security & Permissions

- **Nenhuma permissão nova**: reuso de `relatorios.exportar` (FR-007) — a mesma que já protege todos os endpoints CSV; usuário precisa também ter acesso à tela (`locais.visualizar`) para ver o botão, mas o endpoint valida apenas o gate de exportação (padrão idêntico ao de colaboradores: botão na tela gated, endpoint gated por `relatorios.exportar`).
- Sem credenciais nem dados sensíveis no CSV (dados cadastrais de locais — mesmos dados visíveis na tela para quem tem `locais.visualizar`).
- Operação read-only; trilha de auditoria não se aplica (IX) — coerente com as exportações existentes.

## Testing Strategy

- **Arquivo novo** `tests/test_locations_export.py` (fixtures `client`/`unauth_client`/`db_session` existentes).
- **TDD** (lições 005/006/007): testes escritos e executados **vermelhos** antes da implementação; `[P]` = independência de arquivo, nunca concorrência com a implementação.
- **Caso de 403 sem permissão**: seguir o padrão do `test_rbac.py` (usuário de perfil sem `relatorios.exportar`, ex. "Técnico"); 401 via `unauth_client`.
- **Regressão**: suíte completa verde (baseline atual: 264 passed / 1 failed conhecido — lockout defasado; a feature soma testes sem alterar esse patamar).
- **Retrocompatibilidade comprovada**: botões/exports existentes (custodians/inventory/movements) intocados — nenhum teste existente editado.

## Risks & Mitigations

| Risco | Mitigação |
|---|---|
| Duplicar lógica de CSV fora do `ReportService` | Endpoint delega 100% ao service (Constitution III); teste compara o padrão de saída |
| Divergência de formato vs demais CSVs | Cabeçalho/delimitador/quoting/codificação copiados de `generate_custodians_csv`; contrato §3 fixa o formato |
| Quebrar a tela de Locais (recém-ajustada na 007) | Único ponto de contato é o `page-header`; suíte da 007 continua verde (T015 da 007 já cobre a tela) |
| Expectativa de exportar filtrado | FR-006 decide **todos** por precedente; registrado na ajuda para o usuário |

## Complexity Tracking

> Sem violações de Constitution — tabela vazia por design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
