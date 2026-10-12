# Implementation Plan: Legibilidade dos Eventos de Alteração Cadastral na Trilha de Fluxo & Movimentações (detalhe do Equipamento)

**Branch**: `070-legibilidade-trilha-auditoria` | **Date**: 2026-10-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/070-legibilidade-trilha-auditoria/spec.md`

## Summary

Transformar a apresentação dos eventos de **alteração cadastral** na "Trilha de Fluxo & Movimentações" do detalhe do Equipamento (`/assets/{id}`): resumo legível com título contextual, campos alterados com rótulo amigável e valor anterior → posterior (padrão visual já aceito do painel "Alterações cadastrais"), além de controle nativo **"Ver detalhes técnicos"** recolhido por padrão com o JSON original Antes/Depois. Técnica: **helper somente-leitura em `AssetService`** (padrão aprovado da Feature 067 — decisão PD-1 do clarify) chamado pela rota `view_asset_detail`, reutilizando `changed_fields` + `_ASSET_FIELD_LABELS` no lugar (PD-2); `MovementService.get_timeline_for_asset`, o payload de `GET /api/v1/assets/{id}/timeline`, a gravação de auditoria e o banco permanecem **intocados** (zero DDL, zero dependência nova).

## Technical Context

**Language/Version**: Python 3.10+ (Constitution — Restrições de Tecnologia)

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2, Pydantic v2, Jinja2 + Bootstrap 5 (BiIcons) — **nenhuma dependência nova**

**Storage**: MariaDB/MySQL (produção) via `audit_logs` — **somente leitura**; SQLite em memória apenas nos testes

**Testing**: pytest + TestClient do FastAPI; fixtures da casa (`client`, `db_session`); TDD red→green + guarda de não-mutação (padrão das Specs 063/064/067)

**Target Platform**: Servidor Linux/Windows; interface web server-rendered (PWA existente)

**Project Type**: Web service (camada de apresentação Jinja2 sobre services existentes)

**Performance Goals**: transformação desprezível — teto atual de 50 eventos de auditoria por bem (já aplicado por `get_timeline_for_asset`); diff por evento O(nº de campos do snapshot) (~17 campos)

**Constraints**: payload de `GET /api/v1/assets/{id}/timeline` byte-a-byte idêntico; nenhum `AuditLog` alterado; suíte existente 100% verde; mesma permissão atual (`patrimonio.visualizar`)

**Scale/Scope**: 1 template (ramo de auditoria) + 1 método novo em service + 1 chamada na rota + 1 arquivo de testes novo; tela única do módulo Equipamentos

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Veredito | Fundamentação |
|---|---|---|
| I — Preservação e evolução incremental | ✅ PASS | Mudança de apresentação sobre código existente; sem refatorações; alterações limitadas ao ramo `item.type == 'audit'` |
| II — Arquitetura em camadas | ✅ PASS | Dif­erencial calculado em **service** (`AssetService`); rota delega; template só apresenta (067 como precedente) |
| III — Regras nos services | ✅ PASS | Reutiliza `changed_fields`/`_ASSET_FIELD_LABELS` existentes; nenhuma regra duplicada em rota/template |
| IV — Integridade patrimonial e trilha imutável | ✅ PASS | Leitura pura; nenhum evento gravado/editado/excluído; motor de movimentações intocado |
| V — Integridade do inventário | ✅ N/A | Nenhum fluxo de inventário é tocado |
| VI — Segurança por padrão | ✅ PASS | Nenhuma rota nova; mesma permissão; autoescape preservado (AC10); nenhum segredo envolvido |
| VII — Banco de dados | ✅ PASS | **Zero DDL**; dados intocáveis |
| VIII — Testes como requisito | ✅ PASS | Arquivo de testes novo; nenhum teste existente modificado; régua de regressão 063/064/067/API |
| IX — Auditoria das operações | ✅ PASS | Nenhuma mudança de gravação; trilha imutável preservada |
| X — Interface consistente | ✅ PASS | Reaproveita padrão/estilos do painel "Alterações cadastrais"; `<details>` nativo (precedente `admin/audit/list.html`); sem CSS/JS novo obrigatório |
| XI — Documentação fiel | ✅ PASS | Nenhum artigo de ajuda descreve o formato atual dos cartões (verificação análoga da 063); reconfirmar na implementação |
| XII — Desenvolvimento orientado por especificação | ✅ PASS | Fluxo specify → clarify → plan executado; decisões PD-1…PD-4 fechadas no clarify 2026-10-12 |

**Re-check pós-design (Phase 1)**: ✅ **PASS** — nenhum artefato da fase de desenho introduz violação; **Complexity Tracking permanece vazio** (nenhuma violação a justificar).

## Project Structure

### Documentation (this feature)

```text
specs/070-legibilidade-trilha-auditoria/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Phase 0 — decisões R1…R10
├── data-model.md        # Phase 1 — estruturas de transformação (sem schema novo)
├── quickstart.md        # Phase 1 — guia de validação
├── contracts/           # Phase 1
│   ├── ui-contract.md          # Contrato de renderização do cartão de auditoria
│   └── preserved-contracts.md  # Contratos congelados que a feature não pode tocar
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado pelo /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── services/
│   └── asset_service.py          # ALTERADO — novo método somente-leitura de resumo de evento de auditoria (reutiliza changed_fields + _ASSET_FIELD_LABELS do próprio módulo)
└── web/
    ├── routers/
    │   └── assets.py             # ALTERADO — somente view_asset_detail: aplica o helper aos itens type='audit' do timeline (contexto do template)
    └── templates/
        └── assets/
            └── detail.html       # ALTERADO — somente o ramo item.type == 'audit' (título + resumo + <details>); cartões de movimentação e demais blocos intocados

tests/
└── test_legibilidade_trilha_070.py   # NOVO — renderização red→green + guardas de não-mutação/contrato

# INTOCADOS (regression-rail): app/services/movement_service.py, app/api/assets_api.py,
# app/services/audit_service.py, app/web/routers/templates_env.py, models/, migrations/,
# app/web/templates/admin/audit/list.html, demais templates e testes
```

**Structure Decision**: estrutura única do projeto web existente (FastAPI + Jinja2 monolítico por camadas) — a feature opera 100% dentro das camadas já estabelecidas (service → rota → template), sem novos diretórios nem módulos (Constitution I/II).

## Complexity Tracking

> **Preenchido APENAS quando o Constitution Check tem violações a justificar.**

*Nenhuma violação — seção vazia por decisão do gate.*
