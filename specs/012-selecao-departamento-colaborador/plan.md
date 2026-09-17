# Implementation Plan: Seleção de Departamento/Setor no Cadastro de Colaborador

**Branch**: `012-selecao-departamento-colaborador` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-selecao-departamento-colaborador/spec.md`

> **Revisão 2026-09-17 (pós-feedback do usuário, antes de /speckit-tasks)**: a decisão da fonte oficial foi revista para **reutilizar `Location.department`** (R1 revista), eliminando tabela/coluna novas e a FK `department_id`. Validação por texto no caminho do formulário (R2/R7 revisadas). Detalhes e trade-offs em [research.md](./research.md).

## Summary

Substituir o campo de texto livre "Departamento / Setor *" do cadastro e da edição de Colaborador por um **campo de seleção (dropdown/select nativo)** dos valores oficiais derivados ao vivo de `Location.department` (lista distinta já usada por filtros de bens e escopo de inventário — precedentes em `routes.py`), **sem lógica de pesquisa** (decisão de UX 2026-09-17, supersede a R5 original). **Zero DDL**: nenhuma tabela ou coluna nova; a coluna `Custodian.department` (texto) permanece como armazenamento único e todos os seus consumidores (pesquisa 006, relatórios, termo, CSV, AD) continuam intactos. A integridade é de **validação**: o formulário (novo marcador `department_source=official`) só oferece valores oficiais e o backend valida o valor recebido contra a lista oficial, gravando a forma canônica (elimina divergências de caixa). O campo continua obrigatório (backend), colaboradores `PROV-*` usam o campo normalmente, caminhos legados (API, importação CSV, service) preservam o comportamento atual — suíte existente verde sem edição. A regra de bloqueio por inativos (clarificação Q3) fica **inoperante** nesta fonte, conforme a condicional da própria spec. Colaboradores existentes não são alterados (clarificação Q2/FR-014).

## Technical Context

**Language/Version**: Python 3.10+ (executado com 3.10/3.13/3.14 na suíte local)

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2, Pydantic v2, Jinja2 + Bootstrap 5 (tema claro/escuro), MariaDB/MySQL via PyMySQL (produção)

**Storage**: MariaDB/MySQL (produção); SQLite em memória nos testes (`tests/conftest.py`). **Zero alteração de schema** (research R3 revista) — nenhuma tabela/coluna nova, nenhum `ALTER`, nenhum dado migrado.

**Testing**: pytest (+ TestClient); fixtures `client`/`db_session` em `tests/conftest.py`; suíte atual **116 arquivos de teste**, padrão `tests/test_*.py`. Caminho legado preservado garante suíte verde **sem edição** (R6 revista — 44 call sites verificados).

**Target Platform**: Servidor Linux (produção), navegador desktop (admin/operadores)

**Project Type**: Aplicação web monolítica em camadas (Web/API → Services → Models)

**Performance Goals**: lista derivada ao vivo (`SELECT DISTINCT department FROM locations`) com custo desprezível (consulta já praticada em 3 pontos de `routes.py`); formulário renderiza sem alteração perceptível de latência; sem endpoint de rede novo

**Constraints**: zero DDL e zero perda/alteração de dados existentes (Constitution VII); nenhum teste existente alterado (VIII); nenhuma permissão nova (VI); sem bibliotecas externas (X); `CustodianService` e API de colaboradores **intocados** (raio de alteração mínimo — R6/R7/R10)

**Scale/Scope**: dezenas a centenas de valores oficiais (distintos de `locations.department`); 1 template alterado, 1 service novo (leitura/validação), 4 handlers web alterados, ~1 arquivo de testes novo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Avaliação pré-design | Pós-design (Phase 1) |
|---|---|---|---|
| I | Preservação / evolução incremental | ✅ Extensão mínima: 1 service novo (leitura/validação) + alterações de formulário/rotas; nada reescrito | ✅ **Re-verificado**: raio ainda menor que o original — models/schemas/API/service do colaborador intocados |
| II | Arquitetura em camadas | ✅ Regra de validação em service; rota delega | ✅ `DepartmentService.ensure_official` (contract service §2); rotas apenas invocam |
| III | Regras de negócio nos services | ✅ Validação concentrada em service | ✅ Confirmado — validação NÃO fica no template nem inline na rota |
| IV | Integridade patrimonial | ✅ Motor de movimentações intocado; snapshots imutáveis (AC-08) | ✅ Nenhum toque em `movement_service`/`inventario_service` |
| V | Integridade do inventário | ✅ Inventário usa `Location.department` — agora com vocabulário coerente com o colaborador | ✅ Nenhuma alteração |
| VI | Segurança (auth, RBAC, AD) | ✅ Sem permissão/rota nova: lista server-side herdando `colaboradores.criar`/`editar` (R4) | ✅ Confirmado em `ui-contract.md` §4 |
| VII | Banco aditivo e dados preservados | ✅ **Zero DDL** (R3 revista) — grau máximo de aderência | ✅ Confirmado: nenhum arquivo de model/database é tocado |
| VIII | Testes como não-regressão | ✅ Caminho legado preservado (R6 revista — 44 call sites quantificados) | ✅ Estratégia em `quickstart.md` §1–2 |
| IX | Auditoria | ✅ Mecanismo `write_change_audit` intocado (texto continua o valor gravado) | ✅ Nenhuma alteração de snapshot necessária |
| X | Interface consistente | ✅ Campo de seleção (dropdown `<select>` nativo Bootstrap — decisão de UX 2026-09-17, R5 revista) | ✅ Confirmado em `ui-contract.md` |
| XI | Documentação fiel | ⚠️ Atualizar README/docs/ajuda na tarefa de implementação (comportamento visível muda) | ⚠️ Tarefa (pertence a tasks/implementação) |
| XII | Especificação + validação | ✅ Fluxo Spec Kit (spec → clarify → plan → tasks → implement) | ✅ Quickstart define a validação |

**GATE: PASS** (pós-design: nenhuma violação).

## Project Structure

### Documentation (this feature)

```text
specs/012-selecao-departamento-colaborador/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (REVISADO: R1–R3, R6–R9 em cascata da decisão do usuário)
├── data-model.md        # Phase 1 output (REVISADO: zero DDL; validação por texto)
├── quickstart.md        # Phase 1 output (REVISADO)
├── contracts/           # Phase 1 output (REVISADOS)
│   ├── service-contract.md
│   ├── ui-contract.md
│   └── api-contract.md  # contratos da API: inalterados (documento de não-mudança)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── services/
│   └── department_service.py    # NOVO: list_official() (DISTINCT de locations.department) + ensure_official() (validação/canonização)
├── web/
│   ├── routes.py                # 4 handlers: form_new/form_edit injetam a lista; create/update validam com marcador department_source
│   └── templates/custodians/form.html  # input texto → dropdown `<select>` + hidden department_source
└── (nenhum outro arquivo de app/ é alterado: models, database, schemas, api, custodian_service intocados)

tests/
└── test_department_selection.py  # NOVO: cenários US1–US4 / AC-01..AC-10 / caminho legado
```

**Structure Decision**: Estrutura monolítica existente preservada (Constitution I/II). Um arquivo novo em `app/services/`, um em `tests/`, e alterações pontuais em `routes.py` + `form.html` — o menor raio de alteração possível para o comportamento especificado (spec Seção 11 revista pela decisão da fonte).

## Complexity Tracking

> Sem violações de Constitution a justificar — tabela não utilizada.
