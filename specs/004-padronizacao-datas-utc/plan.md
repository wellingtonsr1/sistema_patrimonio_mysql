# Implementation Plan: Padronização de Data e Hora (UTC na persistência, America/Recife na apresentação)

**Branch**: `004-padronizacao-datas-utc` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-padronizacao-datas-utc/spec.md`

## Summary

Estabelecer a convenção única de data/hora do SisPatrimônio Pro: **todo timestamp gerado pelo sistema
é persistido representando UTC** (contrato aplicacional sobre as colunas `DATETIME` existentes, sem
mudança de schema), e **toda apresentação converte UTC → `America/Recife`** num mecanismo central
reaproveitado por templates, relatórios (PDF/Excel/CSV/HTML) e documentos. Datas de negócio
(`purchase_date`, `warranty_expiry`, datas de CSV/formulários) permanecem intocadas. Caminhos hoje em
hora local (Movimentações, Importação, `assets.updated_at` via movimentação) migram para o gerador
central de UTC; filtros de período sobre timestamps passam a interpretar o intervalo local informado e
convertê-lo para UTC antes de comparar. Fuso nomeado via `zoneinfo.ZoneInfo("America/Recife")`
(stdlib, zero dependência nova). **Zero migração de dados, zero DDL** — dados atuais são de teste e
serão descartados (FR-012).

## Technical Context

**Language/Version**: Python 3.10+ (timezone via `zoneinfo` da stdlib — disponível e testado no
ambiente conforme `docs/ANALISE_DATAS_HORARIOS.md` seção F; `tzdata` presente).

**Primary Dependencies**: Nenhuma nova. Reutiliza: FastAPI, SQLAlchemy 2, Jinja2 (filtro global
`templates.env.filters`), OpenPyXL/ReportLab (já usados pelo `report_service`). `pytz`/`dateutil`
estão instaladas mas **não** serão usadas — decisão é `zoneinfo` (stdlib, sem dependência).

**Storage**: MariaDB (produção) / SQLite em memória (testes). **Zero alteração de schema** (FR-011):
as 28 colunas `DATETIME` permanecem como estão; a convenção UTC é contrato da aplicação
(FR-018: naive `datetime` lido do banco é tratado como UTC).

**Testing**: pytest ≥8 (padrão existente, TestClient + `db_session` de `tests/conftest.py`). Novos
testes em `tests/test_datetime_convention.py` (mecanismos centrais + edge cases da FR-015) e
`tests/test_datetime_flows.py` (gravação UTC em Movimentações/Importação, filtros de período,
apresentação de Inventário/Auditoria). Suíte existente permanece verde (FR-016).

**Target Platform**: Navegador (UI server-rendered Jinja2/Bootstrap 5) + documentos exportáveis
(PDF/Excel/CSV) sobre Uvicorn/Linux, fuso do processo herdado do SO (UTC-3) — irrelevante após a
padronização, pois toda geração é UTC e toda apresentação usa fuso nomeado.

**Project Type**: Extensão transversal de convenção temporal em sistema web monolítico em camadas
(Web/API → Services → Models), server-rendered.

**Performance Goals**: Não aplicável (conversão `ZoneInfo` é O(µs) por valor; filtro aplicado só nos
pontos de exibição já mapeados — ~12 pontos de template + bloco do `report_service`).

**Constraints**: Proibido deslocamento fixo de −3h (SC-008); proibida dupla conversão (edge case);
proibido tocar auth/sessões/AD além da apresentação (FR-013); proibido migrar dados (FR-012);
proibido alterar formato visual existente (dd/mm/aaaa hh:mm e hh:mm:ss); `INV-YYYY`/`TR-YYYY` e
depreciação fora do escopo. Classificação de campo dúbia interrompe e registra (edge case da spec).

**Scale/Scope**: 1 módulo novo (`app/utils/time_utils.py`), 1 arquivo de rotas tocado para registro
do filtro Jinja (`app/web/routes.py`), 3 services de movimentação/importação, 1 bloco do
`report_service`, ~12 pontos de template, 2 arquivos de API para filtros de período, 2 arquivos de
teste novos + ajustes cirúrgicos em 2 testes existentes de UI (FR-016).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio (Constitution v1.0.0) | Status | Observação |
|---|---|---|
| I. Preservação / evolução incremental | ✅ PASS | Mudança aditiva e prevista explicitamente na spec aprovada; nenhuma funcionalidade removida. Comportamentos alterados (gravação de `Movement.timestamp`/`assets.updated_at` de local → UTC; apresentação +3h → Recife) são exatamente o objeto da especificação |
| II. Arquitetura em camadas | ✅ PASS | Mecanismos centrais vivem em módulo utilitário (`app/utils/time_utils.py`) e são consumidos por services/rotas/templates; nenhuma regra de negócio nova em rota ou template |
| III. Regras de negócio nos services | ✅ PASS | Conversão de gravação (local→UTC) ocorre nos services (`movement_service`, `asset_service`, `import_service`); filtro Jinja é apenas apresentação |
| IV. Integridade patrimonial / movimentações | ✅ PASS | Motor `MovementService.create_movement` intacto — só muda o relógio que carimba `timestamp`/`updated_at`; trilha histórica permanece imutável e apensável |
| V. Integridade do inventário | ✅ PASS | Regras de inventário intocadas; apenas a exibição de `checked_at`/`started_at`/`closed_at` passa pelo filtro de conversão |
| VI. Segurança por padrão | ✅ PASS | Nenhuma rota/permissão nova; auth/sessões/AD não têm lógica alterada (FR-013) — apenas a exibição de seus timestamps passa pela conversão |
| VII. MariaDB / proteção de dados | ✅ PASS | Zero DDL, zero migração, zero `UPDATE` de dados (FR-011/FR-012/SC-007); convenção aplicada apenas na aplicação |
| VIII. Testes como não-regressão | ✅ PASS | Suíte existente preservada; 2 testes de UI que validam `strftime` de valor recém-gravado serão atualizados como consequência direta da convenção (comparando a apresentação convertida) — cobertura mantida/fortalecida (FR-016) |
| IX. Auditoria | ✅ PASS | Trilha intocada na escrita; apenas a exibição do `audit_logs.timestamp` passa pela conversão de apresentação |
| X. Interface consistente | ✅ PASS | Formatos visuais preservados (dd/mm/aaaa hh:mm, hh:mm:ss); muda só o valor do fuso exibido; nenhuma mudança de fluxo de tela |
| XI. Documentação fiel | ✅ PASS | A convenção implementada será documentada (README/docs de manutenção) na implementação, mantendo docs fiéis ao comportamento real |
| XII. Especificação + validação | ✅ PASS | Spec aprovada; validação executável definida em `quickstart.md` |

**Resultado: 12/12 PASS — sem violações.** Re-check pós-Phase 1: mantém-se 12/12 — o design não
adiciona dependência (`zoneinfo` é stdlib), camada ou mecanismo estrutural novo; mecanismos centrais
são utilitário + filtro Jinja consumidos dentro das camadas existentes. Nota: o helper morto
`_now_utc()` em `ad_ldap.py` fica intocado (fora de escopo).

## Project Structure

### Documentation (this feature)

```text
specs/004-padronizacao-datas-utc/
├── plan.md                          # This file
├── research.md                      # Phase 0 — decisões R1..R7 verificadas no código
├── data-model.md                    # Phase 1 — classificação campo a campo (28 colunas)
├── quickstart.md                    # Phase 1 — protocolo de validação executável
├── contracts/
│   ├── time-utils-contract.md       # Phase 1 — contrato do mecanismo central (now_utc, converters)
│   └── presentation-contract.md     # Phase 1 — contrato de apresentação (filtro Jinja + exports)
├── checklists/
│   └── requirements.md              # (da etapa /speckit-specify)
└── tasks.md                         # Phase 2 output (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
app/
├── utils/
│   └── time_utils.py                # NOVO: now_utc(), to_utc_persist(), utc_to_recife(),
│                                    #       local_to_utc(), format_local() — mecanismo central
├── web/
│   ├── routes.py                    # ALTERADO: registra filtro/global Jinja "localtime"
│   │                                #   (e chamadas de conversão nos filtros de período de
│   │                                #   movimentação, se houver, conforme tasks)
│   └── templates/
│       ├── admin/audit/list.html        # ALTERADO: log.timestamp → localtime
│       ├── inventarios/detail.html      # ALTERADO: 7 pontos (closed_at/checked_at/created_at/started_at)
│       ├── inventarios/list.html        # ALTERADO: inv.created_at
│       ├── inventarios/conferir.html    # ALTERADO: item.checked_at
│       ├── admin/users/list.html        # ALTERADO: u.last_login
│       ├── admin/users/edit.html        # ALTERADO: last_login, ad_last_sync, locked_until
│       ├── maintenances/list.html       # ALTERADO: m.start_date (início da OS = instante)
│       ├── movements/list.html          # ALTERADO: m.timestamp (passa a ser UTC gravado)
│       ├── dashboard.html               # ALTERADO: m.timestamp
│       ├── reports/movements_report.html# ALTERADO: m.timestamp
│       └── assets/detail.html           # ALTERADO: item.timestamp (2 pontos)
├── services/
│   ├── movement_service.py          # ALTERADO: timestamp/updated_at via now_utc(); term.date (302)
│   │                                #   e get_term_details via apresentação central
│   ├── asset_service.py             # ALTERADO: Movement.timestamp (178, 224) via now_utc()
│   ├── import_service.py            # ALTERADO: Movement.timestamp (506) via now_utc()
│   └── report_service.py            # ALTERADO: timestamps de inventário/auditoria/movimentações
│                                    #   convertidos antes do strftime (bloco 334+, 509–534, 609–618, 725–730)
├── api/
│   └── movements_api.py             # ALTERADO: start_date/end_date locais → UTC antes de filtrar
└── (models/ — NENHUMA alteração: defaults utcnow já conformes)

tests/
├── test_datetime_convention.py      # NOVO: mecanismo central + edge cases (FR-015)
├── test_datetime_flows.py           # NOVO: gravação UTC, filtros de período, apresentação
├── test_inventario_reconferencia_ui.py  # AJUSTE cirúrgico: 2 asserções de strftime passam a
│                                        #   comparar o horário convertido (FR-016)
└── (demais testes intactos)

# Intactos (proibidos por spec/constitution):
# banco (DDL/migração), models, auth_service, session_service, ad_service, ad_ldap,
# permission/RBAC, cálculo de depreciação, códigos sequenciais INV-/TR-, parser CSV,
# seed_demo.py, JavaScript/navegador
```

**Structure Decision**: nenhuma mudança estrutural — projeto monolítico em camadas preservado. O
mecanismo central vive em `app/utils/time_utils.py` (novo módulo utilitário, coerente com a camada de
services), o registro do filtro Jinja ocorre onde os globals já são registrados
(`app/web/routes.py:120–125`), e os services continuam sendo o único ponto de gravação de timestamps.

## Complexity Tracking

> Sem violações de Constitution — tabela não utilizada.
