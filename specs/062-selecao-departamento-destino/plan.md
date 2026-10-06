# Implementation Plan: Seleção de Destino por Departamento/Setor na Movimentação (apresentação Departamento-primeiro)

**Branch**: `062-selecao-departamento-destino` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/062-selecao-departamento-destino/spec.md`

## Summary

Alterar a **apresentação** das opções de destino na movimentação patrimonial e no select de Localização do formulário de Equipamento: opções **agrupadas por Unidade Administrativa** (`optgroup` nativo) e rótulo iniciando pelo **Departamento/Setor** com a unidade como contexto — `Departamento (Unidade)` (ex.: `Divisão de Previdência (IPMJP - Sede)`), eliminando a redundância atual (`Sede - Divisão de Previdência (IPMJP - Sede - Divisão de Previdência)`). O identificador enviado permanece o **id da Localização** e **zero backend/banco/migração** é alterado: a fonte (`LocationService.get_all`, ordenada por `branch, department, name`) já entrega os dados agrupáveis; o agrupamento é feito no template com o filtro Jinja2 `groupby` (nativo, sem código novo em rota/service). O histórico é intocado por construção (snapshots imutáveis, Princípio IV) e a não-mutação da gravação é **comprovada por teste** (o formato atual já é travado por testes existentes — ex.: `test_import_asset_movements.py` L134).

## Technical Context

**Language/Version**: Python 3.10+ (Jinja2 via FastAPI)

**Primary Dependencies**: FastAPI + Uvicorn, Jinja2 (filtro `groupby` nativo), Bootstrap 5 (apresentação; `optgroup` é HTML nativo sem CSS novo), SQLAlchemy 2 (somente leitura da fonte existente)

**Storage**: MariaDB/MySQL (produção); SQLite em memória nos testes. **Zero DDL** — nenhuma tabela/coluna/índice novo, nenhum dado migrado.

**Testing**: pytest (+ TestClient); fixtures `client`/`db_session` em `tests/conftest.py`; padrão `tests/test_*.py`. Suíte atual: **923 passed / 1 skipped / 0 failed** — nenhum teste existente trava o TEXTO das opções afetadas (verificado); testes que gravam movimentações travam o FORMATO do snapshot e permanecem verdes **sem edição**.

**Target Platform**: Servidor Linux (produção), navegadores desktop/mobile dos operadores

**Project Type**: Aplicação web monolítica em camadas (Web/API → Services → Models)

**Performance Goals**: idênticos aos atuais — a fonte é a mesma consulta já executada hoje; `groupby` opera sobre a lista já carregada na renderização (custo desprezível); sem consulta ou endpoint novo

**Constraints**: zero DDL (Constitution VII); zero alteração de backend (escopo da spec — FR-009); formato de snapshot preservado (FR-006/FR-007); nenhum teste existente enfraquecido (VIII); nenhuma permissão nova (VI); sem biblioteca externa (X); alteração restrita a 2 templates + testes novos

**Scale/Scope**: 36 localizações (hoje), ~35 numa única unidade; 2 templates alterados, 0 services/rotas/models alterados, 1 arquivo de testes novo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Avaliação pré-design | Pós-design (Phase 1) |
|---|---|---|---|
| I | Preservação / evolução incremental | ✅ Alteração de apresentação mínima; nada reescrito | ✅ Confirmado: 2 templates; nenhum comportamento além do previsto na spec |
| II | Arquitetura em camadas | ✅ Nenhuma regra nova; nada de negócio em template | ✅ `groupby` é apresentação pura (ordenação/agrupamento visual), não regra de negócio |
| III | Regras de negócio nos services | ✅ Nenhuma regra nova criada | ✅ Confirmado — nenhum service alterado |
| IV | Integridade patrimonial | ✅ Motor de movimentações e snapshots intocados | ✅ Contract UI §5 + teste de não-mutação (US3) protegem o formato |
| V | Integridade do inventário | ✅ Inventário não é tocado | ✅ `inventarios/new.html` permanece fora do escopo (fora-de-escopo 4) |
| VI | Segurança (auth, RBAC, AD) | ✅ Mesmas rotas e permissões (`movimentacao.criar`, `patrimonio.criar`) | ✅ Confirmado em `ui-contract.md` §4 |
| VII | Banco aditivo e dados preservados | ✅ **Zero DDL** — nenhum arquivo de model/database tocado | ✅ Confirmado em `data-model.md` (documento de não-mudança) |
| VIII | Testes como não-regressão | ✅ Suíte verde sem editar testes existentes; novos testes cobrem a apresentação | ✅ Estratégia em `quickstart.md` §1–2 |
| IX | Auditoria | ✅ Nada muda na trilha (mesma rota, mesmo `write_change_audit`) | ✅ Confirmado |
| X | Interface consistente | ✅ `<optgroup>` nativo + padrão visual Bootstrap existente; sem biblioteca nova | ✅ Mockup no `ui-contract.md` §3 |
| XI | Documentação fiel | ✅ Nenhum artigo de ajuda menciona o formato atual das opções (verificado na spec) — nada a atualizar | ✅ Confirmado |
| XII | Especificação + validação | ✅ Fluxo Spec Kit em andamento | ✅ Quickstart define a validação (suíte + smoke visual) |

**GATE: PASS** (pré e pós-design: nenhuma violação; sem entradas em Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/062-selecao-departamento-destino/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (R1–R6: groupby, fonte, fora-de-escopo, testes, snapshot, UX)
├── data-model.md        # Phase 1 output (documento de não-mudança: zero DDL)
├── quickstart.md        # Phase 1 output (validação: suíte + smoke visual)
├── contracts/           # Phase 1 output
│   └── ui-contract.md   # contrato dos dois selects (estado protegido + novo estado)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── services/            # NENHUM arquivo alterado (LocationService.get_all permanece a fonte)
├── models/              # NENHUM arquivo alterado (zero DDL)
├── web/
│   ├── routers/         # NENHUM arquivo alterado (form_new_movement / form_new_asset já fornecem `locations`)
│   └── templates/
│       ├── movements/new.html   # ALTERADO — select de destino (optgroup + rótulo)
│       └── assets/form.html     # ALTERADO — select de Localização do bem (mesma apresentação)
tests/
└── test_departamento_destino_062.py  # NOVO — renderização dos 2 forms + não-mutação
```

**Structure Decision**: estrutura existente do monolito em camadas preservada; o raio de alteração é somente a camada de apresentação (2 templates Jinja2) e a suíte de testes (1 arquivo novo, padrão da casa `test_<tema>_<número>.py`).

## Complexity Tracking

> Vazio — nenhuma violação de Constitution a justificar.
