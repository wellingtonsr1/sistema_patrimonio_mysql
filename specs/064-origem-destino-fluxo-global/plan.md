# Implementation Plan: Padronização da Apresentação de Origem e Destino no Fluxo Global de Movimentações

**Branch**: `064-origem-destino-fluxo-global` | **Date**: 2026-10-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/064-origem-destino-fluxo-global/spec.md` (inclui Clarifications 2026-10-07: cadastro atual exibido; duas linhas por célula; guarda CSV byte-a-byte)

## Summary

Padronizar a apresentação das colunas **Origem** e **Destino** na tabela do "Fluxo Global de Movimentações" (`movements/list.html`), replicando o padrão visual aprovado na Feature 063 para a trilha: **Departamento/Setor como linha principal** e **`Localização (curta) • Unidade Administrativa` como contexto em `.mov-sec`** (duas linhas por ponto, layout fixo da Feature 039 preservado — nenhuma largura de coluna muda), com deduplicação automática e fallback ao snapshot cru quando a relação não existe. Quando a relação existe, exibe o **cadastro atual** (decisão confirmada na spec); o snapshot fiel permanece no banco, CSV e termo. **Zero backend, zero DDL, zero migração**; snapshot gravado, busca (Feature 004/049), CSV (`generate_movements_csv` — guarda byte-a-byte), termo, dashboard, relatório, dropdown 062 e a trilha 063 permanecem intocados, com prova por teste de não-mutação.

## Technical Context

**Language/Version**: Python 3.10+ (Jinja2 via FastAPI)

**Primary Dependencies**: FastAPI + Uvicorn, Jinja2 (macro e métodos de string nativos — `endswith`, `rsplit`, precedentes 062/063 na mesma versão), Bootstrap 5 (classes `mov-fluxo`/`mov-sec` existentes, sem CSS novo), SQLAlchemy 2 (somente leitura das relações já carregadas por `joinedload` em `get_all_movements`, `movement_service.py` L479–485)

**Storage**: MariaDB/MySQL (produção); SQLite em memória nos testes. **Zero DDL** — nenhuma tabela/coluna/índice novo, nenhum dado migrado.

**Testing**: pytest (+ TestClient); fixtures `client`/`db_session` em `tests/conftest.py`; padrão da casa `tests/test_<tema>_<número>.py`. Suíte atual: **948 passed / 2 skipped / 4 failed** — os 4 failures são AMBIENTAIS e pré-existentes (`test_backup_config.py` ×1 e `test_migrations_052.py` ×3, `ModuleNotFoundError` de `dotenv`/`alembic` num subprocesso `C:\Python314\python.exe`; ver `063/validacao.md` V1); nenhum teste trava o TEXTO renderizado nas células do `movements/list.html` (verificado); os testes que gravam movimentações travam o FORMATO do snapshot e permanecem verdes **sem edição**.

**Target Platform**: Servidor Linux (produção), navegadores desktop/mobile dos operadores

**Project Type**: Aplicação web monolítica em camadas (Web/API → Services → Models)

**Performance Goals**: idênticos aos atuais — nenhuma consulta nova (as relações já chegam carregadas no `get_all_movements`); a formatação é computação de string desprezível na renderização de até 200 linhas

**Constraints**: zero DDL (Constitution VII); zero alteração de backend (spec §16); formato de snapshot preservado (FR-003/FR-004 da 063, herejados); CSV byte-a-byte (AC11 + guarda por teste); layout fixo da Feature 039 preservado (§19 spec); dropdown 062 byte-a-byte (AC12); trilha 063 intocada (AC13); nenhum teste existente enfraquecido (VIII); sem biblioteca nova (X); alteração restrita a 1 template + 1 arquivo de testes novo

**Scale/Scope**: 36 localizações (hoje), listagem com limite fixo de 200 registros (sem paginação — nada a preservar além do comportamento atual); 1 template alterado, 0 services/rotas/models alterados, 1 arquivo de testes novo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Avaliação pré-design | Pós-design (Phase 1) |
|---|---|---|---|
| I | Preservação / evolução incremental | ✅ Mudança de apresentação mínima em 2 células de 1 template | ✅ Confirmado: macro local no `movements/list.html`; nenhum comportamento além do previsto na spec |
| II | Arquitetura em camadas | ✅ Nenhuma regra nova; formatação de exibição não é regra de negócio | ✅ Macro de apresentação no template (precedentes 062/063: mecanismo nativo do template engine); nenhum service/rota alterado |
| III | Regras de negócio nos services | ✅ Nenhuma regra nova criada | ✅ Confirmado — a deduplicação de rótulos é apresentação, não validação/cálculo de domínio |
| IV | Integridade patrimonial | ✅ Motor de movimentações e snapshots intocados | ✅ ui-contract §4 + teste de não-mutação (US2) protegem gravação, histórico, busca e CSV |
| V | Integridade do inventário | ✅ Inventário não é tocado | ✅ Fora do escopo; nenhum arquivo de inventário alterado |
| VI | Segurança (auth, RBAC, AD) | ✅ Mesma rota e permissão (`movimentacao.visualizar`) | ✅ Confirmado — nenhuma rota nova |
| VII | Banco aditivo e dados preservados | ✅ **Zero DDL** — nenhum arquivo de model/database tocado | ✅ Confirmado em `data-model.md` (documento de não-mudança) |
| VIII | Testes como não-regressão | ✅ Suíte verde sem editar testes existentes; novos testes cobrem a apresentação e a guarda do CSV | ✅ Estratégia em `quickstart.md` §1–2 (inclui guarda CSV byte-a-byte) |
| IX | Auditoria | ✅ Nada muda na trilha de auditoria | ✅ Confirmado — nenhum caminho de escrita alterado |
| X | Interface consistente | ✅ Mesmas classes `mov-*`/Bootstrap; padrão visual já aprovado na 063; layout fixo da 039 preservado | ✅ Mockup antes/depois no `ui-contract.md` §3 |
| XI | Documentação fiel | ✅ Nenhum artigo de ajuda descreve o formato atual das colunas Origem/Destino do Fluxo Global (verificado na spec §1 item 12 da 063 e confirmado) | ✅ Confirmado — nada a atualizar |
| XII | Especificação + validação | ✅ Fluxo Spec Kit em andamento (spec clarificada: 3 decisões registradas) | ✅ Quickstart define a validação (suíte + smoke visual) |

**GATE: PASS** (pré e pós-design: nenhuma violação; sem entradas em Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/064-origem-destino-fluxo-global/
├── spec.md              # Especificação clarificada (Clarifications 2026-10-07)
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (R1–R7)
├── data-model.md        # Phase 1 output (documento de não-mudança: zero DDL)
├── quickstart.md        # Phase 1 output (validação: suíte + guarda CSV + smoke visual)
├── contracts/           # Phase 1 output
│   └── ui-contract.md   # contrato das células Origem/Destino (estado protegido + novo estado + regra de deduplicação)
└── tasks.md             # Phase 2 output (gerado por /speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── services/            # NENHUM arquivo alterado (get_all_movements já entrega as relações carregadas; generate_movements_csv intocado)
├── models/              # NENHUM arquivo alterado (zero DDL)
├── api/                 # NENHUM arquivo alterado (/api/reports/movements/csv byte-a-byte)
├── web/
│   ├── routers/         # NENHUM arquivo alterado (list_movements_view já passa movements com relações)
│   └── templates/
│       └── movements/list.html  # ALTERADO — macro _local_curto no topo + corpo das 2 células Origem/Destino (linhas 128–137); <style> e layout da Feature 039 intocados
tests/
└── test_fluxo_global_064.py     # NOVO — renderização da tabela + não-mutação (gravação/busca/CSV)
```

**Structure Decision**: estrutura existente do monolito em camadas preservada; o raio de alteração é um único bloco da camada de apresentação (as 2 células Origem/Destino + macro em `app/web/templates/movements/list.html`) e a suíte de testes (1 arquivo novo, padrão da casa `test_<tema>_<número>.py`). A duplicação consciente da macro `_local_curto` (também presente em `assets/detail.html` da 063) está registrada na spec §11 como dívida, resolvível por macro compartilhada em feature futura — extrair agora violaria o escopo mínimo (Constitution I).

## Complexity Tracking

> Vazio — nenhuma violação de Constitution a justificar.
