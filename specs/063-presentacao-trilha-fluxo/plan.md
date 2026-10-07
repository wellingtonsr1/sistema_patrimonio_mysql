# Implementation Plan: Padronização da Apresentação de Origem e Destino na Trilha de Fluxo & Movimentações

**Branch**: `063-presentacao-trilha-fluxo` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/063-presentacao-trilha-fluxo/spec.md`

## Summary

Padronizar a apresentação de **Origem** e **Destino** na seção "Trilha de Fluxo & Movimentações" da janela do equipamento (`assets/detail.html`), adotando o mesmo padrão visual da seção "Custódia & Localização Atual": **Departamento/Setor como linha principal** e **`Localização • Unidade Administrativa` como contexto**, com deduplicação automática de nomes repetidos. A mudança é **somente de template**: o card `flow-card` passa a usar as relações `origin_location`/`destination_location` — que o service JÁ carrega via joinedload (`movement_service.py` L417–422) e o template hoje ignora — caindo para o snapshot de texto cru quando a relação não existe. **Zero backend, zero DDL, zero migração**; snapshot gravado, busca (Feature 049), termo e o dropdown da Feature 062 permanecem intocados, com prova por teste de não-mutação.

## Technical Context

**Language/Version**: Python 3.10+ (Jinja2 via FastAPI)

**Primary Dependencies**: FastAPI + Uvicorn, Jinja2 (macros e métodos de string nativos — `endswith`, `rsplit`, verificados na versão do projeto), Bootstrap 5 (classes `flow-*` existentes, sem CSS novo), SQLAlchemy 2 (somente leitura das relações já carregadas)

**Storage**: MariaDB/MySQL (produção); SQLite em memória nos testes. **Zero DDL** — nenhuma tabela/coluna/índice novo, nenhum dado migrado.

**Testing**: pytest (+ TestClient); fixtures `client`/`db_session` em `tests/conftest.py`; padrão da casa `tests/test_<tema>_<número>.py`. Suíte atual: **948 passed / 2 skipped / 0 failed** — nenhum teste trava o TEXTO renderizado na trilha do `assets/detail.html` (verificado); os testes que gravam movimentações travam o FORMATO do snapshot e permanecem verdes **sem edição**.

**Target Platform**: Servidor Linux (produção), navegadores desktop/mobile dos operadores

**Project Type**: Aplicação web monolítica em camadas (Web/API → Services → Models)

**Performance Goals**: idênticos aos atuais — nenhuma consulta nova (as relações já chegam carregadas na timeline); a formatação é computação de string desprezível na renderização

**Constraints**: zero DDL (Constitution VII); zero alteração de backend (spec FR-007); formato de snapshot preservado (FR-003/FR-004); dropdown 062 byte-a-byte (FR-005); seção "Custódia & Localização Atual" intocada (FR-006); nenhum teste existente enfraquecido (VIII); sem biblioteca nova (X); alteração restrita a 1 template + 1 arquivo de testes novo

**Scale/Scope**: 36 localizações (hoje), trilha com até ~50 itens de movimentação por página; 1 template alterado, 0 services/rotas/models alterados, 1 arquivo de testes novo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Avaliação pré-design | Pós-design (Phase 1) |
|---|---|---|---|
| I | Preservação / evolução incremental | ✅ Mudança de apresentação mínima em 1 bloco de 1 template | ✅ Confirmado: macro local no `assets/detail.html`; nenhum comportamento além do previsto na spec |
| II | Arquitetura em camadas | ✅ Nenhuma regra nova; formatação de exibição não é regra de negócio | ✅ Macro de apresentação no template (precedente 062: mecanismo nativo do template engine); nenhum service/rota alterado |
| III | Regras de negócio nos services | ✅ Nenhuma regra nova criada | ✅ Confirmado — a deduplicação de rótulos é apresentação, não validação/cálculo de domínio |
| IV | Integridade patrimonial | ✅ Motor de movimentações e snapshots intocados | ✅ ui-contract §4 + teste de não-mutação (US2) protegem gravação, histórico e busca |
| V | Integridade do inventário | ✅ Inventário não é tocado | ✅ Fora do escopo; nenhum arquivo de inventário alterado |
| VI | Segurança (auth, RBAC, AD) | ✅ Mesma rota e permissão (`patrimonio.visualizar`) | ✅ Confirmado — nenhuma rota nova |
| VII | Banco aditivo e dados preservados | ✅ **Zero DDL** — nenhum arquivo de model/database tocado | ✅ Confirmado em `data-model.md` (documento de não-mudança) |
| VIII | Testes como não-regressão | ✅ Suíte verde sem editar testes existentes; novos testes cobrem a apresentação | ✅ Estratégia em `quickstart.md` §1–2 |
| IX | Auditoria | ✅ Nada muda na trilha de auditoria | ✅ Confirmado — nenhum caminho de escrita alterado |
| X | Interface consistente | ✅ Mesmas classes `flow-*`/Bootstrap; padrão visual da própria página (referência "Custódia & Localização Atual") | ✅ Mockup antes/depois no `ui-contract.md` §3 |
| XI | Documentação fiel | ✅ Nenhum artigo de ajuda descreve o formato atual da trilha (verificado na spec) — nada a atualizar | ✅ Confirmado |
| XII | Especificação + validação | ✅ Fluxo Spec Kit em andamento | ✅ Quickstart define a validação (suíte + smoke visual) |

**GATE: PASS** (pré e pós-design: nenhuma violação; sem entradas em Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/063-presentacao-trilha-fluxo/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (R1–R7: regra de apresentação, macro Jinja2, fallbacks, testes, snapshot, telas fora de escopo)
├── data-model.md        # Phase 1 output (documento de não-mudança: zero DDL)
├── quickstart.md        # Phase 1 output (validação: suíte + smoke visual)
├── contracts/           # Phase 1 output
│   └── ui-contract.md   # contrato do card flow-card (estado protegido + novo estado + regra de deduplicação)
└── tasks.md             # Phase 2 output (gerado previamente com a spec; refinado para refletir as decisões do plan)
```

### Source Code (repository root)

```text
app/
├── services/            # NENHUM arquivo alterado (get_timeline_for_asset já entrega as relações carregadas)
├── models/              # NENHUM arquivo alterado (zero DDL)
├── web/
│   ├── routers/         # NENHUM arquivo alterado (view_asset_detail já passa timeline completa)
│   └── templates/
│       └── assets/detail.html   # ALTERADO — apenas o card flow-card (Origem/Destino) da seção Trilha
tests/
└── test_presentacao_trilha_063.py  # NOVO — renderização do detalhe + não-mutação
```

**Structure Decision**: estrutura existente do monolito em camadas preservada; o raio de alteração é um único bloco da camada de apresentação (o card `flow-card` em `app/web/templates/assets/detail.html`) e a suíte de testes (1 arquivo novo, padrão da casa `test_<tema>_<número>.py`).

## Complexity Tracking

> Vazio — nenhuma violação de Constitution a justificar.
