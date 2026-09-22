# Implementation Plan: Registrar no Fluxo as movimentações da importação CSV de equipamentos

**Branch**: `029-importacao-csv-fluxo` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/029-importacao-csv-fluxo/spec.md`

## Summary

Correção cirúrgica da causa estrutural "o CSV atualiza o estado do equipamento, mas não passa pela lógica de movimentação/histórico": o importador de equipamentos (`import_service.py`) passa a derivar **estado e histórico da mesma operação de domínio** — a entrada do bem segue o padrão do cadastro manual (`ENTRADA_AQUISICAO` com snapshots reais) e a custódia informada no CSV (coluna de custodiante, hoje ignorada pelo parser) é aplicada **exclusivamente via `MovementService.create_movement`** (matriz VAL-002..VAL-008, tipos existentes, termo sequencial padrão, operador = usuário autenticado). Reimportação só movimenta quando há mudança efetiva de local/custodiante, com a **decisão de tipo centralizada** em um novo método puro de `MovementService` (nada de matriz duplicada no importador). Zero DDL, zero novo tipo de movimentação, Fluxo/consulta intactos, auditoria `ACTION_IMPORT` das rotas preservada.

## Technical Context

**Language/Version**: Python 3.10+ (stack da Constitution)

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2, Pydantic v2, Jinja2 + Bootstrap 5 — todos existentes, nenhuma dependência nova.

**Storage**: MariaDB/MySQL via `DATABASE_URL` (produção); SQLite apenas na suíte de testes (`db_session`) — padrão do projeto. **Nenhuma alteração de schema** (FR-023).

**Testing**: pytest + TestClient (padrão do projeto).

**Target Platform**: Windows e Linux (deploy de processo único).

**Performance Goals**: N/A (nenhuma rota nova; volume de movimentações passa a ser 1–2 por equipamento importado — sem otimização fora do escopo).

**Constraints**:
- **Baseline medida nesta sessão (2026-09-21): 565 passed / 0 failed** (`python -m pytest tests/ -q`, 58 s). Observação de ambiente: foi necessário `pip install httpx2` **no venv do projeto** para o TestClient do starlette funcionar — dependência faltante do ambiente, não do projeto.
- Patamar pós-029 = 565 + novos testes verdes (cenários A–L da spec).
- Mudança mínima: 4 arquivos de produção alterados (2 services + 2 rotas) e 1 arquivo de teste novo; nenhuma alteração de templates, banco, permissões ou Fluxo.
- Compatibilidade de assinatura: `execute_import` ganha parâmetro opcional `operator_name` (chamadas existentes de teste continuam válidas); as rotas passam sempre o usuário autenticado (FR-005).
- `MovementService.create_movement` faz `commit` por movimentação (fato D4): a unidade transacional da linha é garantida por esse commit + commit de linha no importador (R3); o `write_audit` das rotas (que comita a sessão) permanece FORA do `execute_import` (R9).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| 1 | I — Preservação do sistema existente | ✓ PASS | Correção localizada em `import_service` + 1 método novo puro em `MovementService`; nenhuma refatoração; `create_movement` e `AssetService.create` intocados em semântica |
| 2 | II — Arquitetura em camadas | ✓ PASS | Toda a lógica fica nos services; rotas web/API apenas repassam o operador autenticado (dados que já possuem) |
| 3 | III — Regras nos services | ✓ PASS | Decisão de tipo de movimentação centralizada em `MovementService.resolve_movement_type`; o importador NÃO implementa matriz própria (FR-004) |
| 4 | IV — Integridade patrimonial | ✓ PASS | Estado/localização/custódia passam a ser alterados SOMENTE pelo motor de movimentações (elimina o caminho que contornava o motor); nenhum tipo novo; histórico imutável preservado |
| 5 | V — Integridade do inventário | ✓ PASS | Não toca `inventario_service` (inventário continua não alterando cadastro) |
| 6 | VI — Segurança/RBAC/AD | ✓ PASS | Nenhuma rota nova; permissões existentes (`patrimonio.criar`) mantidas; operador autenticado registrado na movimentação; zero credenciais em logs/auditoria |
| 7 | VII — Banco MariaDB/aditivo | ✓ PASS | Zero DDL (data-model documenta N/A); nenhuma tabela/coluna nova |
| 8 | VIII — Testes de não regressão | ✓ PASS | Baseline 565/0 preservada; testes A–L novos; testes existentes de importação (`test_import_asset_location.py`) verificados um a um no research (D10) — nenhum enfraquecido |
| 9 | IX — Auditoria | ✓ PASS | Nenhum evento novo e nenhum removido: `ACTION_IMPORT` das rotas permanece (audit não substitui movimentação e vice-versa — FR-018); movimentação registra operador; sem segredos |
| 10 | X — Interface consistente | ✓ PASS | Nenhuma alteração de templates/telas; Fluxo e termo usam telas existentes |
| 11 | XI — Documentação fiel | ✓ PENDENTE-T | README/docs atualizados na mesma tarefa de implementação (item de tasks) |
| 12 | XII — Spec-driven + validação | ✓ PASS | Fluxo Spec Kit seguido; validação via quickstart |

### Post-Design Re-check (após Phase 1)

| # | Princípio | Status | Evidência |
|---|---|---|---|
| 1–12 | Revalidação integral | ✓ PASS 11/12 + 1 tarefa | Sem DDL (data-model N/A); sem nova dependência; escopo de arquivos fechado (Project Structure); contratos garantem matriz como fonte única (C3) e preservação da consulta do Fluxo (C2.6); quickstart valida cenários A–L ponta a ponta. Princípio XI (documentação) é ação da fase de implementação (tasks), não do design. Nota R2/R3: política "CSV sem custodiante em reimportação = manter custódia atual" e commit por linha estão documentados nos contratos. |

## Project Structure

### Documentation (this feature)

```text
specs/029-importacao-csv-fluxo/
├── plan.md              # This file
├── research.md          # Phase 0 output — fatos D1–D10 + decisões R1–R10
├── data-model.md        # Phase 1 output — zero DDL; uso das entidades existentes + transições
├── contracts/           # Phase 1 output — contrato por caminho afetado
│   └── service-contract.md
└── quickstart.md        # Phase 1 output — validação ponta a ponta (suíte + manual)
```

### Source Code (repository root)

```text
app/
├── services/
│   ├── import_service.py        # parse: alias da coluna de custodiante; execute_import:
│   │                            #   entrada padrão cadastro manual + custódia via
│   │                            #   MovementService (decisão por resolve_movement_type);
│   │                            #   commit por linha; operator_name
│   └── movement_service.py      # + resolve_movement_type (estático, puro, sem DB);
│                                #   create_movement INTOCADO
├── web/routes.py                # confirm_import_assets: operator_name=request.state.user
└── api/assets_api.py            # import_csv_api: operator_name=request.state.user
tests/
└── test_import_asset_movements.py   # NOVO: cenários A–L da spec (serviço/integração)
```

**Structure Decision**: projeto único existente (FastAPI). Nenhum módulo novo de produção; nenhuma alteração em templates, banco, permissões, Fluxo, inventário ou demais importações.

## Complexity Tracking

> Vazio — nenhuma violação da Constitution a justificar.
