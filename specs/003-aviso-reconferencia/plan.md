# Implementation Plan: Aviso de sobrescrita na re-conferência de inventário

**Branch**: `003-aviso-reconferencia` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-aviso-reconferencia/spec.md`

## Summary

Adicionar, **apenas na camada de templates/JavaScript**, o aviso de sobrescrita e a confirmação explícita
na re-conferência de itens de inventário. Nos modais de `detail.html`, itens ≠ `PENDENTE` passam a exibir
um alerta (conferente anterior, data/hora, resultado anterior + aviso de substituição) e exigir confirmação
no envio; itens `PENDENTE` permanecem idênticos a hoje. Na página `conferir.html`, o alerta existente é
complementado com conferente/data (dados já presentes no contexto). **Zero alteração de backend**: mesma
rota `POST /inventarios/{id}/conferir/{item_id}`, mesmo `InventarioService.record_check`, mesmo modelo
`InventarioItem` (campos `status`, `checked_by_name`, `checked_at` já disponíveis no contexto dos dois
templates — verificado), mesmo RBAC, mesma auditoria. Mecanismo de confirmação: `confirm()` nativo via
`onsubmit`, padrão já consolidado no sistema (4 ocorrências em templates de administração).

## Technical Context

**Language/Version**: Python 3.10+ com Jinja2 templates + JavaScript inline (stack existente, inalterada).

**Primary Dependencies**: Nenhuma nova. Reutiliza: Jinja2, Bootstrap 5 (componente `alert alert-warning`),
Bootstrap Icons, JavaScript nativo do navegador (`confirm()`). FastAPI/SQLAlchemy/Pydantic não são tocados.

**Storage**: MariaDB (produção) / SQLite em memória (testes). **Zero alteração de schema** — nenhum campo
novo, nenhuma tabela nova; a feature apenas exibe dados já persistidos (`status`, `checked_by_name`,
`checked_at` de `inventario_itens`).

**Testing**: pytest ≥8 (padrão existente). Novo arquivo `tests/test_inventario_reconferencia_ui.py` com
TestClient (padrão `client`/`db_session` de `tests/conftest.py`), seguindo o estilo de asserção de HTML
já usado (`assert "..." in response.text` — precedentes em `test_movements.py:176`,
`test_custodian_import.py:171-186`). Suíte existente intacta — `tests/test_inventario.py` continua verde.

**Target Platform**: Navegador (interface web desktop, Bootstrap 5, tema claro/escuro) sobre Uvicorn/Linux.

**Project Type**: Extensão de UI de um sistema web monolítico em camadas (Jinja2 server-rendered).

**Performance Goals**: Não aplicável (renderização server-side de bloco condicional por item; custo
desprezível — dezenas de nós Jinja por modal).

**Constraints**: Re-conferência não pode ser impedida nem dificultada (spec FR-012); nada de dados
inventados quando `checked_by_name`/`checked_at` ausentes (FR-005); inventário `ENCERRADO` permanece
intocado (FR-010); nenhum arquivo fora dos templates e testes de UI (spec, fora de escopo).

**Scale/Scope**: 2 templates alterados (detail.html, conferir.html) e 1 arquivo de testes novo (~8 casos). Nenhum outro arquivo será alterado.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio (Constitution v1.0.0) | Status | Observação |
|---|---|---|
| I. Preservação / evolução incremental | ✅ PASS | Extensão aditiva e condicional: o comportamento funcional de itens PENDENTE e de inventário encerrado permanece inalterado. Alteração restrita ao que a spec prevê |
| II. Arquitetura em camadas | ✅ PASS | Nenhuma regra de negócio nova em qualquer camada; a UI apenas apresenta dados existentes do item |
| III. Regras de negócio nos services | ✅ PASS | `record_check` permanece a única fonte de verdade da gravação; nenhuma regra duplicada na UI |
| IV. Integridade patrimonial / movimentações | ✅ PASS | Não toca bens, movimentações ou custódia |
| V. Integridade do inventário | ✅ PASS | Regra de re-conferência e travamento no encerramento preservados; a feature só os torna visíveis |
| VI. Segurança por padrão | ✅ PASS | Nenhuma permissão/rota nova; `confirm()` é apenas barreira de UX client-side — a garantia real continua no backend (service + RBAC), como hoje |
| VII. MariaDB / proteção de dados | ✅ PASS | Zero DDL, zero migração; apenas leitura de colunas existentes |
| VIII. Testes como não-regressão | ✅ PASS | Novos testes de UI + suíte existente intacta (`test_inventario.py` sem modificações) |
| IX. Auditoria | ✅ PASS | Trilha intocada; sobrescritas continuam registrando antes/depois como hoje |
| X. Interface consistente | ✅ PASS | Alerta `alert-warning` no padrão visual existente; `confirm()` em pt-BR segue o padrão dos 4 precedentes (`admin/roles/list.html`, `admin/users/edit.html` ×2, `admin/ad/settings.html`) |
| XI. Documentação fiel | ✅ PASS | A implementação não altera documentação existente; o comportamento implementado permanece fiel à spec. |
| XII. Especificação + validação | ✅ PASS | Spec aprovada; validação executável definida em `quickstart.md` |

**Resultado: 12/12 PASS — sem violações.** Re-check pós-Phase 1: mantém-se 12/12 (o design não adiciona
nenhuma camada, dependência ou mecanismo novo).

## Project Structure

### Documentation (this feature)

```text
specs/003-aviso-reconferencia/
├── plan.md                          # This file
├── research.md                      # Phase 0 — decisões R1..R4 verificadas no código
├── data-model.md                    # Phase 1 — entidades somente-leitura (nenhum schema novo)
├── quickstart.md                    # Phase 1 — protocolo de validação executável
├── contracts/
│   └── ui-conferencia-contract.md   # Phase 1 — contrato de comportamento da UI
├── checklists/
│   └── requirements.md              # (da etapa /speckit-specify)
└── tasks.md                         # Phase 2 output (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
app/web/templates/inventarios/
├── detail.html
│   # ALTERADO: alerta nos modais de conferência + confirmação
│   # explícita para itens já conferidos
│
└── conferir.html
    # ALTERADO: complemento do alerta existente

tests/
└── test_inventario_reconferencia_ui.py
    # NOVO: testes da interface de re-conferência

# Intactos (proibidos por spec):
# rotas, services, models, banco, migrations,
# permissões, autenticação, AD, auditoria e demais templates

# Intactos (proibidos por spec): rotas, services, models, banco, migrations,
# permissões, autenticação, AD, auditoria, demais templates

### Arquivos permitidos para alteração

A implementação desta feature poderá alterar/criar somente:

1. app/web/templates/inventarios/detail.html
2. app/web/templates/inventarios/conferir.html
3. tests/test_inventario_reconferencia_ui.py

Nenhum outro arquivo do projeto poderá ser alterado.

Não modificar rotas, services, models, banco de dados, migrations,
permissões, autenticação, AD, auditoria ou templates não relacionados.
```

**Structure Decision**: nenhuma mudança estrutural — projeto monolítico em camadas preservado
(`app/web/templates/` para UI; `tests/` para pytest). Os únicos arquivos tocados são os dois templates do
módulo de inventário e um novo arquivo de testes.

## Complexity Tracking

> Sem violações de Constitution — tabela não utilizada.
