# Implementation Plan: Preenchimento Automático do Campo Localização

**Branch**: `066-preenchimento-automatico-localizacao` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/066-preenchimento-automatico-localizacao/spec.md`

## Summary

Tornar o campo "Localização" do formulário `/locations/new` preenchido automaticamente a partir de `Unidade Administrativa` + `Departamento / Setor`, no formato `TRIM(branch) + " - " + TRIM(department)`, com a autoridade da regra no servidor (a rota ignora o valor enviado pelo navegador e recompoõe). Abordagem técnica: helper puro de composição em `LocationService` (fonte única — Constitution III), JS vanilla embutido no template para sincronização em tempo real (padrão dos templates da casa, sem CSP restritiva — verificado), campo `name` tornado `readonly` e opcional no POST, validação de tamanho (100 chars) e preservação integral de API REST, importações, snapshots e banco (zero DDL, zero migração). Aprovada em 2026-10-09 com as pendências P1 (validação só no fluxo web) e P2 (`readonly` confirmado).

## Technical Context

**Language/Version**: Python 3.10+ (executado em 3.14 no ambiente), Jinja2 + JavaScript ES6 do lado do navegador

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Pydantic v2, Jinja2 + Bootstrap 5 (sem novas dependências)

**Storage**: MariaDB/MySQL via `DATABASE_URL` (produção); SQLite in-memory na suíte de testes — **zero DDL, zero migração**

**Testing**: pytest + TestClient do FastAPI (fixtures `client`/`db_session` de `tests/conftest.py`)

**Target Platform**: Servidor web + navegadores modernos (desktop/PWA já suportado)

**Project Type**: Web application (FastAPI + Jinja2) — monolito em camadas Web/API → Services → Models

**Performance Goals**: sem impacto perceptível — composição é O(1) no cliente e no servidor (nenhuma query adicional)

**Constraints**: nome composto ≤ 100 caracteres (coluna `locations.name`); regra aplicada **somente** no fluxo web `/locations/new` (P1 aprovada); API `POST/PUT /api/v1/locations` e importação CSV de locais/bens com contratos intactos

**Scale/Scope**: 37 localizações reais, 313 bens, 352 movimentações; escopo fechado em ~5 arquivos (spec §11)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Veredito | Justificativa |
|---|---|---|
| I — Preservação/evolução incremental | ✅ PASS | Extensão pontual em 1 template + 1 rota + helper; nenhum módulo substituído; escopo fechado na spec §11 |
| II — Arquitetura em camadas | ✅ PASS | Regra (composição) vive no service; a rota apenas delega; template só apresenta/sincroniza |
| III — Regras nos services | ✅ PASS | Helper `compose_name` em `LocationService` é a fonte única; JS replica apenas para UX (servidor é autoridade — FR-003) |
| IV — Integridade de movimentações | ✅ PASS | Nenhuma alteração em `MovementService`, snapshots ou motor de movimentações |
| V — Integridade de inventário | ✅ PASS | Inventário intocado; nomes novos seguem o mesmo padrão dos existentes (37/37) |
| VI — Segurança por padrão | ✅ PASS | Rotas existentes mantêm `require_permission("locais.criar")`; servidor ignora valor do cliente (anti-spoofing) |
| VII — Banco de dados | ✅ PASS | **Zero DDL, zero migração, zero UPDATE** — apenas criação de novos registros com nome composto |
| VIII — Testes como regressão | ✅ PASS | Suíte existente intacta; novo arquivo `tests/test_localizacao_automatica_066.py` cobre AC01–AC06 + regressão |
| IX — Auditoria | ✅ PASS | `write_change_audit` do `create_location_form` permanece inalterado (continua gravando `after={"name", "branch", "department"}`) |
| X — Interface consistente | ✅ PASS | Mesmo layout Bootstrap do form; `readonly` com indicador visual no padrão da casa (precedente: campo Operador da 065) |
| XI — Documentação fiel | ✅ PASS | Nota em `docs/ARQUITETURA_E_MANUTENCAO.md` §12.4 (Locais) na mesma tarefa |
| XII — Spec → implementação → validação | ✅ PASS | Spec aprovada 2026-10-09; plano → tasks → implementação com suíte verde |

**Resultado do gate**: **PASS** — nenhuma violação a justificar (Complexity Tracking vazio).

## Project Structure

### Documentation (this feature)

```text
specs/066-preenchimento-automatico-localizacao/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Phase 0 — decisões técnicas (R1–R7)
├── data-model.md        # Phase 1 — entidades e regras de validação
├── quickstart.md        # Phase 1 — guia de validação executável
├── contracts/           # Phase 1 — contrato do formulário web + limites preservados
│   └── web-location-form-contract.md
├── checklists/
│   └── requirements.md  # Checklist de qualidade da spec
├── spec.md              # Especificação aprovada
└── tasks.md             # Phase 2 — /speckit-tasks (NÃO criado por /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── web/
│   ├── routers/
│   │   └── locations.py        # ALTERADO: create_location_form compõe o nome no servidor
│   └── templates/
│       └── locations/
│           └── form.html       # ALTERADO: name readonly + JS de sincronização + placeholder
├── services/
│   └── location_service.py     # ALTERADO: helper puro de composição (create/update/get_all intactos)
└── (demais camadas)            # INTOCADAS: models, schemas, api/locations_api.py, importações

docs/
└── ARQUITETURA_E_MANUTENCAO.md # ALTERADO: nota sobre composição automática (§12.4)

tests/
└── test_localizacao_automatica_066.py  # NOVO: cobertura de AC01–AC06 + regressão
```

**Structure Decision**: monolito existente em camadas (opção única do projeto) — a feature não cria diretórios nem módulos novos; altera 3 arquivos de produção, 1 doc e cria 1 arquivo de teste, exatamente como delimita a spec §11.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Nenhuma violação — tabela vazia por design.
