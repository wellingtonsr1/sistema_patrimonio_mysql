# Implementation Plan: SisPatrimônio Pro — Baseline do Sistema Existente

**Branch**: `001-sistema-existente` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-sistema-existente/spec.md`

## Summary

Esta feature **não implementa funcionalidade nova**: estabelece a baseline técnica e
funcional do SisPatrimônio Pro (sistema existente em produção) para governar sua evolução
via Spec Kit. A abordagem técnica é **documentacional e de verificação**: consolidar o
mapa dos componentes reais (Web/API → Services → Models → MariaDB), os 27 comportamentos
e regras a preservar, e o protocolo de validação de não-regressão (suíte pytest de 154
testes + checklist da Constitution). Nenhuma alteração de código, schema, dependência ou
configuração é necessária para atendê-la; o plano restringe-se a artifacts de design e a
um guia de validação executável.

## Technical Context

**Language/Version**: Python 3.10+ (confirmado em README e requirements.txt)

**Primary Dependencies**: FastAPI ≥0.110, Uvicorn[standard] ≥0.28, SQLAlchemy 2 ≥2.0,
Pydantic v2 ≥2.6, Jinja2 ≥3.1, python-multipart, ldap3 ≥2.9.1, PyMySQL ≥1.1 (driver
MariaDB), OpenPyXL ≥3.1, ReportLab ≥4.0, python-dotenv — todas já presentes em
`requirements.txt` (nenhuma nova dependência).

**Storage**: MariaDB/MySQL via SQLAlchemy (`DATABASE_URL`, dialecto
`mariadb+pymysql://`); SQLite em memória exclusivamente na suíte de testes
(`tests/conftest.py`, `DATABASE_URL_TEST`).

**Testing**: pytest ≥8 + TestClient do FastAPI; 154 testes em 12 arquivos
(`tests/`), banco isolado por teste (`create_all`/`drop_all` no fixture).

**Target Platform**: Servidor Linux (Uvicorn, `python run.py`); acesso por navegador
(Bootstrap 5 via CDN) e API REST `/api/v1`.

**Project Type**: Aplicação web full-stack monolítica em camadas (backend + templates
server-side + JS estático) com CLI administrativa.

**Performance Goals**: Não aplicável a esta feature (nenhum código alterado). Metas do
sistema permanecem as atuais.

**Constraints**: Não alterar comportamento existente (Constitution I); não alterar
schema (nenhuma necessidade aqui); suíte de 154 testes deve permanecer aprovada
(exceto 1 teste já defasado conhecido — ver Riscos).

**Scale/Scope**: 17 módulos funcionais; 4 artefatos de documentação a gerar neste
feature directory; zero arquivos de aplicação modificados.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio (Constitution v1.0.0) | Status | Observação |
|---|---|---|
| I. Preservação do sistema / evolução incremental | ✅ PASS | Plano não altera código; escopo = artifacts de design em `specs/001-sistema-existente/` |
| II. Arquitetura em camadas (Web/API → Services → Models) | ✅ PASS | Documentada como está; nenhuma mudança proposta |
| III. Regras de negócio nos Services | ✅ PASS | Mapa de services registra a responsabilidade real |
| IV. Integridade patrimonial / movimentações | ✅ PASS | Comportamentos P7–P9/P13–P15 preservados por documento |
| V. Integridade do inventário | ✅ PASS | P10–P12 preservados por documento |
| VI. Segurança por padrão (auth, RBAC, AD, credenciais) | ✅ PASS | Nenhuma mudança de segurança; segredos não examinados nem reproduzidos |
| VII. MariaDB / proteção de dados / DDL aditivo | ✅ PASS | **Nenhuma alteração de schema** (registrado explicitamente) |
| VIII. Testes como não-regressão | ✅ PASS | quickstart.md executa a suíte existente como validação |
| IX. Auditoria das operações relevantes | ✅ PASS | Trilha mapeada; nenhuma mudança |
| X. Interface consistente | ✅ PASS | Nenhuma mudança de UI |
| XI. Documentação fiel ao comportamento real | ✅ PASS | Todos os artifacts citam arquivos/linhas reais; não-confirmados marcados |
| XII. Especificação + validação | ✅ PASS | Este plano é a especificação técnica da baseline; validação definida em quickstart.md |

**Resultado: 12/12 PASS — sem violações.** Re-check pós-Phase 1: mantém-se 12/12
(artifacts gerados não introduzem complexidade nem alteram design do sistema).

## Project Structure

### Documentation (this feature)

```text
specs/001-sistema-existente/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
├── checklists/          # requirements.md (da etapa /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

Estrutura existente do repositório (nada será criado ou movido fora de
`specs/001-sistema-existente/`):

```text
app/
├── api/                  # Endpoints REST /api/v1 + deps de auth/RBAC
├── models/               # 17 modelos SQLAlchemy + enums
├── schemas/              # Schemas Pydantic v2
├── services/             # 17 módulos de regras de negócio
├── web/                  # Rotas Jinja2 (routes, admin_routes, help_routes),
│   ├── templates/        #   templates HTML
│   └── static/           #   css/style.css, js/main.js
├── config.py             # Configuração única via env (DATABASE_URL obrigatória)
├── database.py           # engine/SessionLocal/Base/get_db/init_db/_ensure_schema_migrations
├── main.py               # FastAPI: lifespan, handlers 403/404, /health
└── cli.py                # CLI administrativa

tests/                    # Suíte pytest (12 arquivos, 154 testes)
docs/                     # Documentação técnica existente
data/                     # Logs (data/logs/) — não versionar dados sensíveis
run.py · seed_demo.py · requirements.txt
```

**Structure Decision**: estrutura single-project existente mantida integralmente. Esta
feature produz **apenas** artifacts de documentação dentro de
`specs/001-sistema-existente/`; nenhum diretório de código é criado ou alterado.

## Complexity Tracking

> Sem violações de Constitution — tabela não aplicável (vazia por design).

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

---

# Plano Técnico Detalhado (conforme solicitação)

## 1. Resumo da Implementação

Entregar a baseline governada: **(a)** `plan.md` (este documento) fixando o contexto
técnico e os limites; **(b)** `research.md` consolidando decisões e verificando no código
cada afirmação da spec; **(c)** `data-model.md` mapeando as 15 entidades reais e seus
relacionamentos; **(d)** `contracts/` documentando os contratos existentes de interface
(rotas web protegidas, API REST `/api/v1`, CLI) como referência de não-regressão;
**(e)** `quickstart.md` com o protocolo de validação executável (suíte de regressão +
checagens de integridade). **Nenhum arquivo de aplicação, teste, template, CSS/JS, banco
ou configuração é modificado.** O "código entregue" desta feature é o próprio conjunto de
artifacts, e a validação é a execução da suíte existente.

## 2. Arquitetura Existente Relevante

Verificada no código e documentada em `SPEC-KIT-SISTEMA-ATUAL.md` (raiz) e
`docs/ARQUITETURA_E_MANUTENCAO.md`:

```text
Browser / cliente HTTP
   ↓
FastAPI (app/main.py) — lifespan: init_db → ensure_admin_user → ensure_default_roles
   ├── Rotas web (Jinja2): app/web/routes.py · admin_routes.py · help_routes.py
   └── API REST: app/api/v1_router.py (prefixo /api/v1) → auth_api, assets_api,
       movements_api, custodians_api, locations_api, reports_api
   ↓ Dependências (app/api/deps.py): require_web_auth · require_api_auth ·
     require_permission (RBAC deny-by-default, auditado)
   ↓ Provedores (app/services/auth_provider.py): local (PBKDF2) | AD (LDAP bind direto)
   ↓ Services (app/services/*.py — 17 módulos, regras de negócio)
   ↓ Models (app/models/*.py — SQLAlchemy 2)
   ↓ MariaDB (DATABASE_URL, PyMySQL) — sem fallback SQLite na aplicação
```

Pontos de integração relevantes à baseline: motor de movimentações
(`movement_service.create_movement` — único caminho legítimo de mudança de
estado/localização/custódia), inventário (`inventario_service` — nunca altera cadastro),
trilha de auditoria (`audit_service` — somente-leitura), RBAC (`permission_service` +
`require_permission`).

## 3. Stack Tecnológica

A stack atual é mantida integralmente (Constitution: restrição de tecnologia). Nenhuma
tecnologia é substituída, adicionada ou removida. Referência confirmada em
`requirements.txt`: Python 3.10+, FastAPI, Uvicorn, SQLAlchemy 2, Pydantic v2, Jinja2,
ldap3, PyMySQL, OpenPyXL, ReportLab, pytest. Frontend: Jinja2 + Bootstrap 5.3.3 +
Bootstrap Icons + Chart.js + QRCode.js (todos via CDN) + `static/css/style.css` +
`static/js/main.js`. **Nova dependência: nenhuma.**

## 4. Componentes Afetados

Análise técnica obrigatória — componentes que a **baseline** toca (todos como objeto de
**documentação/leitura**, não de modificação):

| Componente | Tipo | Por que é afetado |
|---|---|---|
| `app/services/*.py` (17 módulos) | Service | Objeto central do mapeamento em `data-model.md`/`research.md` (onde cada regra vive) — apenas lidos |
| `app/models/*.py` (17 arquivos) | Model | Entidades e relacionamentos documentados em `data-model.md` — apenas lidos |
| `app/api/*.py` + `app/web/*.py` | Rotas | Contratos existentes documentados em `contracts/` — apenas lidos |
| `app/web/templates/**`, `static/**` | UI | Referenciados nos contratos de fluxo de tela — apenas listados |
| `app/config.py`, `database.py` | Config/DB | Parâmetros de ambiente e mecanismo de migração leve documentados — apenas lidos |
| `tests/**` (12 arquivos) | Testes | Base de regressão referenciada no quickstart — apenas lidos/executados |
| `specs/001-sistema-existente/*` | Docs | **Únicos arquivos criados/atualizados** por esta feature |

Módulos/rotas/services/models/templates/JS-CSS/tabelas/relacionamentos/permissões/
auditoria/testes/integrações: todos mapeados com justificativa nos artifacts
(`data-model.md` §por entidade; `contracts/` §por rota; quickstart §testes). Nenhum
impacto indireto em runtime: a baseline não altera comportamento — impactos indiretos
posíveis limitam-se a **documentação defasada** caso o sistema evolua sem atualizar
estes artifacts (mitigação: regra XI da Constitution + seção 10 da spec).

## 5. Modelo de Dados

**Nenhuma alteração de schema é necessária** — registrado explicitamente conforme
requisito. As 15 entidades existentes (assets, movements, maintenances, custodians,
locations, users, user_sessions, roles, permissions, user_roles, role_permissions,
audit_logs, ad_settings, ad_group_roles, inventarios, inventario_itens, setup_claims —
17 tabelas no total) são documentadas em detalhe (campos, chaves, constraints,
índices, relacionamentos) em `data-model.md`. Mecanismo de evolução futura de schema
permanece o existente: `init_db` (`create_all`) + `_ensure_schema_migrations`
(`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, idempotente, aditivo — MariaDB 10.5+).

## 6. Fluxo da Funcionalidade

Fluxo desta feature (de documentação):

```text
/spec.planeja baseline
  ↓ (esta etapa) plan.md + research.md + data-model.md + contracts/ + quickstart.md
  ↓ /speckit.tasks → tasks.md (tarefas de revisão/validação dos artifacts)
  ↓ Validação: pytest (suíte existente) + checklist Constitution + revisão dos artifacts
  ↓ Baseline publicada no repositório → referência para TODAS as features futuras
```

Fluxos de negócio do sistema (F1–F8 da spec) não são alterados; permanecem documentados
na spec §6 e nos contratos.

## 7. Segurança e Autorização

**Nenhuma alteração de segurança.** Avaliação de impacto:

- **Autenticação**: intocada (local PBKDF2 + AD/LDAP híbridos, lockout, sessão
  server-side) — protegida por spec P1–P3 e FR-001.
- **Autorização/RBAC**: intocada — deny-by-default, 29 permissões, 7 perfis; protegido
  por P4–P5 e FR-002.
- **Sessões**: intocadas (hash SHA-256 no banco, expiração/revogação no servidor) — P2.
- **Auditoria**: intocada; permanece somente-leitura — P6, FR-007.
- **Exposição de dados**: nenhuma nova superfície; artifacts não incluem segredos
  (`.env` não lido; credenciais omitidas por política).
- **Permissões por funcionalidade**: mapeadas por rota em `contracts/` como referência
  de que toda rota nova futura deve seguir o padrão `require_permission`.

## 8. Auditoria

A trilha `audit_logs` permanece intocada. Este plano registra que **qualquer evolução
futura** deve: (a) manter os eventos atuais (20 gerais + 13 AD); (b) registrar eventos
para operações novas via `write_audit`/`write_change_audit`; (c) nunca escrever
credenciais; (d) preservar registros históricos (sem exclusão/edição). A baseline em si
não gera eventos (não executa operações no sistema).

## 9. Interface

Nenhuma alteração visual ou funcional de UI. As telas existentes (login, dashboard,
assets, movements, custodians, locations, maintenances, inventarios, reports, admin,
ajuda, perfil, 403/404) permanecem intocadas e são listadas nos contratos como
referência. Consistência visual/funcional segue protegida por P21 e Princípio X.

## 10. Testes

Prioridade absoluta: **regressão**. A suíte existente é a definição executável de
"comportamento preservado".

| Ação | Testes | Motivo |
|---|---|---|
| **Manter/Executar** | Todos os 154 (`pytest`) — `test_rbac.py` (30), `test_ad.py` (32), `test_inventario.py` (21), `test_auth.py` (17), `test_custodian_import.py` (13), `test_import_asset_location.py` (12), `test_help.py` (9), `test_api.py` (7), `test_movements.py` (5), `test_navbar.py` (4), `test_setup_first_access.py` (3), `test_assets.py` (1) | Base de não-regressão exigida pela spec (SC-D) |
| **Ampliar** | Nenhum nesta feature (nada de código é alterado) | Sem necessidade |
| **Criar** | Nenhum nesta feature | Sem necessidade; features futuras criarão testes por FR-016 |
| Conhecido | `test_rbac.py::test_lockout_after_failed_attempts` falha hoje (espera 5 tentativas; config = 10) | Defasagem pré-existente, fora do escopo; registrada como risco (§13) |

Protocolo completo em `quickstart.md`.

## 11. Estratégia de Migração

**Não aplicável** — nenhuma migração de banco, de configuração ou de código é necessária.
Registrado para clareza: o plano proíbe execução de migrações nesta feature; o mecanismo
existente (`_ensure_schema_migrations`) permanece como padrão para features futuras que
comprovadamente exijam DDL.

## 12. Compatibilidade

- **Comportamental**: 100% — nenhum comportamento muda (objetivo da baseline).
- **De dados**: 100% — nenhuma escrita em banco por esta feature.
- **De API/UI/CLI**: 100% — contratos documentados em `contracts/` permanecem válidos.
- **De processos**: features futuras passam a consumir a baseline (spec + plan +
  contracts + data-model) como referência obrigatória, citando os itens de
  preservação (P1–P24) afetados — sem custo de runtime.

## 13. Riscos

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Artefatos de baseline ficarem defasados conforme o sistema evolui | Média | Médio | Regra XI da Constitution (docs na mesma tarefa) + SC-E (toda feature cita a baseline) |
| Teste defasado conhecido (lockout 5×10) mascarar regressão real | Baixa | Médio | Registrado; correção é tarefa própria (spec §11.4); suíte permanece monitorada |
| Divergência entre spec/documentos e código em pontos não confirmados (assinatura de termo, permissões reservadas, edição via UI) | Média | Baixo | Marcados como não-confirmados (spec §11); nenhum tratado como requisito |
| Interpretação errada da baseline como "tarefa de implementação" | Baixa | Alto | Este plano: zero modificações de código; validação = suíte verde + checklist |

Problemas existentes **fora do escopo** (registrados, não corrigidos): os listados em
`SPEC-KIT-SISTEMA-ATUAL.md` §25 (term_signed nunca setado, numeração de termo sem
unique/lock, next_code sem lock, ORM inline em rotas, `datetime.now` vs `utcnow`, etc.).

## 14. Decisões Técnicas

| # | Decisão | Justificativa | Alternativas descartadas |
|---|---|---|---|
| D1 | Feature de baseline **sem alteração de código** | Spec exige descrição fiel + preservação; Constitution I/XII | Incluir correções conhecidas — rejeitado: ampliaria escopo e violaria a regra de escopo |
| D2 | Contratos documentados como estão (não "melhorados") | Não-regressão exige referência fiel ao real | Redesenhar contratos — rejeitado: reescrita proibida |
| D3 | `data-model.md` espelha os models SQLAlchemy reais | Fonte única verificável das 17 tabelas | Modelo idealizado — rejeitado: inventaria comportamento inexistente |
| D4 | Validação = suíte pytest existente + checklist | quickstart executável sem novos recursos | Criar suite nova de smoke — rejeitado: desnecessário sem mudança de código |
| D5 | Artifacts em português, no padrão dos docs do projeto | Consistência com README/docs existentes (P21/XI) | Inglês — rejeitado: quebraria convenção do projeto |
| D6 | Nenhuma alteração de schema | Nenhum requisito da spec exige DDL | Migração "preventiva" — rejeitado: viola regra 11 do briefing |

## 15. Arquivos que Deverão Ser Modificados (criados)

Somente estes (todos novos, dentro do feature directory):

1. `specs/001-sistema-existente/plan.md` — este plano (criado por setup + preenchido).
2. `specs/001-sistema-existente/research.md` — decisões e verificação no código (Phase 0).
3. `specs/001-sistema-existente/data-model.md` — 17 entidades/relacionamentos (Phase 1).
4. `specs/001-sistema-existente/contracts/*.md` — contratos web/API/CLI/DB (Phase 1).
5. `specs/001-sistema-existente/quickstart.md` — protocolo de validação (Phase 1).

*(Já existentes no feature directory, sem alteração: `spec.md`,
`checklists/requirements.md`, `.specify/feature.json`.)*

## 16. Arquivos que NÃO Devem Ser Modificados

Lista explícita de exclusão (nenhum motivo de escopo justifica tocá-los nesta feature):

- `app/**` — todo o código da aplicação (api, models, schemas, services, web, templates, static, config, database, main, cli, logging_config)
- `tests/**` — suíte de testes (executar, não editar)
- `docs/**` — documentação existente
- `.env`, `.env.un~` — segredos/configuração (nem lidos)
- `requirements.txt` — nenhuma dependência nova
- `run.py`, `seed_demo.py`
- `data/**` — logs e dados locais
- `.specify/**` (exceto artifacts padrão desta feature), `.github/**`, `TASKS/**`
- `SPEC-KIT-SISTEMA-ATUAL.md` — análise técnica existente (referenciada, não editada)
- Banco de dados — nenhuma conexão de escrita, nenhuma migração

## 17. Estratégia de Implementação Incremental

Aplicável à entrega dos artifacts (e ao padrão para features futuras):

1. **Fase única, aditiva**: criar os artifacts listados em §15 dentro de
   `specs/001-sistema-existente/` — nada existente é alterado (conforme regra 1/2/4
   do briefing e Constitution I).
2. **Ordem de produção**: plan → research → data-model → contracts → quickstart
   (cada artifact consome o anterior; contracts e data-model derivam do código real,
   lido — nunca de memória).
3. **Verificação a cada artifact**: cada afirmação citada de arquivo/rota/regra deve
   ser verificável no código citado; não-confirmados ficam marcados.
4. **Validação final** (quickstart): `pytest` (153/154 esperados, com 1 falha
   conhecida defasada) + checklist da Constitution + revisão cruzada spec ↔ artifacts.
5. **Padrão para features futuras** (relevância da baseline): cada próxima feature
   partirá daqui, identificará os P1–P24 afetados, aplicará o fluxo
   Web/API → Services → Models, DDL aditivo se imprescindível, testes novos + suíte
   verde, docs atualizados — exatamente os critérios de sucesso SC-A..E da spec.
