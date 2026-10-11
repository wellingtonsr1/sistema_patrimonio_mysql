# Implementation Plan: Paginação nas Listas Web e Integridade de Relatórios/Exportações

**Branch**: `068-paginacao-listas-e-relatorios-integros` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/068-paginacao-listas-e-relatorios-integros/spec.md`

## Summary

Duas lacunas abertas pela análise de 2026-10-10 (`docs/ANALISE_SEG_PERF_UX_2026-10-10.md`, achados P1/P2/U5):

1. **Nenhuma listagem web é navegável além do primeiro bloco** — `/assets` e `/movements` cortam em 200 sem `offset`, `/admin/audit` em 200 (teto 1.000), `/reports/inventory` em 1.000; `/custodians`, `/locations` e `/inventarios` carregam tudo em memória sem indicador algum. Nenhum template tem controle de página (grep `pagination`/`page-item` = 0).
2. **Exportações cortam em silêncio** — `ReportService.get_filtered_assets` aplica `limit 10000` (`report_service.py:47`) e as respostas são montadas inteiras em memória; arquivo incompleto sai como se estivesse completo.

Abordagem técnica (incremental, sem DDL, sem rota nova, sem permissão nova, sem dependência nova):

1. **Helper único de paginação** em `app/utils/pagination.py` + **macro Jinja** `templates/macros/pagination.html`, generalizando o precedente interno já existente (`IntegrationCenterService.get_history` + `admin/integracoes/historico.html:86-95`) — mesmo vocabulário `{page, pages, total}`, mesmos botões Anterior/Próxima preservando `request.query_params`.
2. **Parâmetros aditivos com default** nos services de listagem (`skip`/`offset`/`limit`), de modo que **todos os chamadores atuais — inclusive a API — continuem idênticos** (Constitution I). `AssetService.get_all` e `MovementService.get_all_movements` já paginam; `CustodianService`, `LocationService`, `InventarioService` e `get_audit_logs` ganham o parâmetro.
3. **Filtro dos itens de inventário sai do Python e vai para o serviço** (hoje `list(inv.itens)` + filtro em memória), para que página e filtro concordem.
4. **Relatório web sem corte**: `view_inventory_report` deixa de passar `limit=1000`, pagina com 200 e exibe o total real.
5. **Exportações sem teto**: `get_filtered_assets` deixa de aplicar `limit 10000`; CSV em **lotes + `StreamingResponse`**, XLSX em modo **write-only**, PDF **sem teto** com aviso prévio na tela >10.000 linhas; qualquer corte residual avisado na tela **e** dentro do arquivo (FR-013). Headers, encoding, delimitador, colunas e permissões inalterados.
6. **Audit log paginado + filtros de período/usuário** expostos (já existentes em `get_audit_logs`, só falta a rota).

**Decisões**: **todas aprovadas** — **P1** aviso **+** exportação completa · **P2** todas as listas do escopo · **P3** `page_size` fixo 200 (2026-10-10); **P4** relatório web paginado · **P5** eliminar N+1 das listas (2026-10-11).

## Technical Context

**Language/Version**: Python 3.10+ | Jinja2 + Bootstrap 5 (sem JS novo)

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Jinja2, OpenPyXL 3.1.5 (já instalado, suporta `write_only`), ReportLab (já instalado) — **nenhuma dependência nova**

**Storage**: MariaDB/MySQL em produção (`DATABASE_URL`); SQLite in-memory na suíte (`tests/conftest.py`) — **zero DDL, zero migração, zero backfill**

**Testing**: pytest + `TestClient`; baseline medido em 2026-10-10 = **1005 passed / 2 skipped (88,79 s)**; `tests/route_manifest.json` **inalterado** (nenhuma rota nova)

**Target Platform**: aplicação web (Linux/Windows); desktop e mobile já cobertos pelo PWA

**Project Type**: monolito em camadas Web/API → Services → Models (Constitution II)

**Performance Goals**: página 1 não mais lenta que o baseline medido (`/assets` ≈ 33 ms medianos com 2.000 bens, análise 2026-10-10); **zero N+1 de contagem** por página; exportação de 12.000 linhas em CSV com memória constante (streaming)

**Constraints**: preservar contratos de API (`skip/limit`, códigos, campos), formato dos arquivos exportados (encoding `utf-8-sig`, `;`, cabeçalhos, nome), permissões, fluxo de conferência do inventário e imutabilidade da trilha; nenhum teste existente editado

**Scale/Scope**: 7 telas de listagem + 1 tela de relatório + 1 audit log + 6 geradores de exportação; ~10 arquivos de produção alterados, 2 arquivos novos (helper + macro), 1 arquivo de teste novo, 1 template de página parcial; dados de referência 2.000 bens (medição) / base auditada 313 bens e 352 movimentações (specs 066/067)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Veredito | Justificativa |
|---|---|---|
| I — Preservação/evolução incremental | ✅ PASS | Só adições: parâmetros **aditivos com default** (`skip`/`offset`/`limit`), 1 helper, 1 macro; nenhum módulo reescrito; wrappers de exportação preservados como API pública |
| II — Arquitetura em camadas | ✅ PASS | Router lê `page` e delega; `offset/limit`, filtros e agregações vivem no **service**; template só apresenta |
| III — Regras nos services | ✅ PASS | Filtro/paginação dos itens de inventário migrado **de** `view_inventario` **para** `InventarioService` (primeira vez no servidor certo); nada de regra nova em template |
| IV — Integridade patrimonial e movimentações | ✅ PASS | Nenhuma escrita em `Asset`/`Movement`; movimentações e custódia intocadas; exportações mudam apenas **completude** |
| V — Integridade do inventário | ✅ PASS | Itens, resultados, listas esperadas e conferência **inalterados**; paginação é só apresentação; contadores globais preservados (FR-005) |
| VI — Segurança por padrão | ✅ PASS | Mesmas permissões em cada rota; `page` não concede nada; auditoria segue somente-leitura; nenhuma permissão/perfil novo |
| VII — Banco de dados (MariaDB) | ✅ PASS | **Zero DDL**; `offset/limit` e `GROUP BY` portáveis (MariaDB e SQLite da suíte) |
| VIII — Testes como não regressão | ✅ PASS | Nenhum teste editado/enfraquecido; suíte nova `tests/test_paginacao_relatorios_068.py` cobrindo AC01–AC15; manifesto de rotas **sem** mudança |
| IX — Auditoria das operações relevantes | ✅ PASS | Apenas **leitura** da trilha (paginação + filtros); nenhuma escrita/edição/exclusão |
| X — Interface consistente e funcional | ✅ PASS | Macro de paginação no padrão visual já usado em `historico.html`; contadores no texto existente; responsivo (Botão Anterior/Próxima) — exigido por **FR-022/AC15** (360 px → desktop) |
| XI — Documentação fiel | ✅ PASS | `docs/ARQUITETURA_E_MANUTENCAO.md` + central de ajuda atualizados na mesma implementação |
| XII — Spec → implementação → validação | ✅ PASS | Spec 068 com AC01–AC15 e `quickstart.md`; implementação pelo `tasks.md`; registro em `validacao.md` |

**Resultado do gate**: **PASS** — nenhuma violação a justificar (Complexity Tracking vazio). Todas as mudanças de assinatura são **aditivas com default**, portanto retrocompatíveis.

## Project Structure

### Documentation (this feature)

```text
specs/068-paginacao-listas-e-relatorios-integros/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Phase 0 — decisões técnicas R1–R12
├── data-model.md        # Phase 1 — sem entidades novas; parâmetros, invariantes e matrizes
├── quickstart.md        # Phase 1 — validação executável
├── contracts/
│   ├── web-list-pagination-contract.md    # Contrato das 7 listas + relatório web
│   └── export-completeness-contract.md    # Contrato de CSV/XLSX/PDF e avisos
├── checklists/
│   └── requirements.md  # Checklist de qualidade da spec
├── spec.md              # Especificação (P1–P5 aprovadas — §14)
└── tasks.md             # Phase 2 — /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── utils/
│   └── pagination.py                # NOVO: normalização de page/offset/pages (vocabulário de get_history)
├── web/
│   ├── routers/
│   │   ├── assets.py                # ALTERAR: page/total em list_assets (e labels se necessário)
│   │   ├── movements.py             # ALTERAR: page + exibir total
│   │   ├── custodians.py            # ALTERAR: skip/limit + total
│   │   ├── locations.py             # ALTERAR: skip/limit + total
│   │   ├── inventario.py            # ALTERAR: paginação na lista e nos itens (filtro via service)
│   │   └── reports.py               # ALTERAR: relatório web sem limit=1000 (P4) + aviso prévio de PDF
│   ├── admin_routes.py              # ALTERAR: /admin/audit paginado + filtros de período/usuário
│   └── templates/
│       ├── macros/pagination.html   # NOVO: macro pager (reaproveita markup de historico.html)
│       ├── assets/list.html         # ALTERAR: "Mostrando X–Y de Z" + macro
│       ├── movements/list.html      # ALTERAR: total + macro
│       ├── custodians/list.html     # ALTERAR: indicador + macro
│       ├── locations/list.html      # ALTERAR: indicador + macro
│       ├── inventarios/list.html    # ALTERAR: indicador + macro
│       ├── inventarios/detail.html  # ALTERAR: itens paginados; contadores globais intactos
│       ├── admin/audit/list.html    # ALTERAR: total + macro + filtros período/usuário
│       └── reports/inventory.html   # ALTERAR: total real + paginação + aviso prévio
├── services/
│   ├── asset_service.py             # INTOCADO — já aceita skip/limit e devolve (lista, total); só a rota passa skip (research R4)
│   ├── movement_service.py          # INTOCADO — get_all_movements já aceita skip/limit e devolve total; só a rota passa skip
│   ├── audit_service.py             # ALTERAR (aditivo): offset/limit com default
│   ├── custodian_service.py         # ALTERAR (aditivo): skip/limit com default (hoje: tudo)
│   ├── location_service.py          # ALTERAR (aditivo): skip/limit com default (hoje: tudo)
│   ├── inventario_service.py        # ALTERAR: filtragem/paginação de itens + contagem agregada
│   └── report_service.py            # ALTERAR: sem limit 10000; CSV em lotes/streaming; XLSX write-only; PDF sem teto + aviso
└── api/
    └── reports_api.py               # ALTERAR (mínimo): StreamingResponse no CSV, mesmos headers/status

docs/
├── ARQUITETURA_E_MANUTENCAO.md      # ALTERAR: listagens paginadas + integridade de exportações (XI)
└── Melhorias_SisPatrimonio_Pro.md   # ALTERAR: dívidas remanescentes (ex.: API de custodians/locais sem paginação)

app/services/help_service.py         # ALTERAR: artigo da ajuda sobre paginação/exportação completa

tests/
├── test_paginacao_relatorios_068.py  # NOVO: AC01–AC15
├── route_manifest.json               # INTOCADO (nenhuma rota nova — feature 051)
└── (demais)                          # INTOCADOS: só regressão executada
```

**Structure Decision**: monolito existente em camadas (opção única do projeto). A feature **não** cria diretório de regra novo, tabela, permissão ou dependência: cria **2 arquivos** (`app/utils/pagination.py`, `app/web/templates/macros/pagination.html`) e altera routers, services de listagem/relatório, templates de lista, um arquivo de teste e a documentação — exatamente como delimita a spec §11.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(nenhuma)_ | — | — |
