# Implementation Plan: Inventário — Remover o colaborador responsável do snapshot de bens esperados

**Branch**: `034-inventario-snapshot-sem-custodia` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/034-inventario-snapshot-sem-custodia/spec.md`

## Summary

Remover o colaborador responsável do snapshot de bens esperados do Inventário e de todas as superfícies que o apresentam como dado de conferência. Decisões H-1/H-2/H-3 da spec (clarify 2026-09-24): **H-1** — a coluna e os dados históricos já gravados permanecem no banco (sem migração destrutiva; Princípio VII); **H-2** — a ata de inventário legado preserva a coluna "Responsável Esperado" com o histórico gravado (valor comprobatório), enquanto a ata de inventário novo não contém a coluna; **H-3** — o pacote offline (033) deixa de incluir o campo para TODO inventário (payload técnico transitório). A conferência já não compara responsável (fato verificado) — nada muda na lógica de conformidade. Alteração cirúrgica: nenhum módulo de movimentação/alocação/cadastro é tocado.

## Technical Context

**Language/Version**: Python 3.10+ (backend); Jinja2 + Bootstrap 5 (templates); sem build step

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Pydantic v2 (stack existente — Constitution); ReportLab/OpenPyXL (ata PDF/Excel); CSV UTF-8 BOM

**Storage**: MariaDB — **nenhuma migração** (decisão H-1: a coluna `expected_custodian_name` de `inventario_itens` permanece para o histórico de inventários anteriores; novos registros não a alimentam)

**Testing**: pytest + TestClient (padrão existente); novos testes em `tests/test_inventario.py` (comportamento do snapshot/ata) + ajuste dos testes existentes que assertam o campo

**Target Platform**: Linux server (Uvicorn) — inalterado

**Project Type**: web-application monolítica existente — alteração pontual em 6 arquivos + testes

**Performance Goals**: n/a (remoção de dado; nenhum caminho novo de processamento)

**Constraints**: nenhuma migração destrutiva (H-1/Princípio VII); nenhum módulo fora do Inventário alterado (FR-012/Princípio I); ata legado preserva histórico (H-2); pacote offline sem o campo para todo inventário (H-3)

**Scale/Scope**: ~6 arquivos alterados (1 service de geração, 1 service de relatório, 1 service offline, 2 templates, 1 data-model doc) + testes; nenhum arquivo novo de produção

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente / evolução incremental | ✅ PASS | Remoção pontual de campo do snapshot e de exibições; nenhum módulo reescrito; movimentação/alocação intocados (FR-012) |
| II | Arquitetura em camadas | ✅ PASS | Mudanças concentradas em services (geração, relatório, offline) e templates; nenhuma regra em rota |
| III | Regras de negócio nos services | ✅ PASS | Comportamento do snapshot e da ata definidos em `InventarioService`/`ReportService`/`InventarioOfflineService` |
| IV | Integridade patrimonial/movimentações | ✅ PASS | Nenhuma regra de movimentação tocada; o Inventário continua sem alterar cadastro (Princípio V) |
| V | Integridade do Inventário | ✅ PASS | Snapshot continua imutável (reafirmado); encerramento/ata travados; somente o campo de custódia sai do snapshot novo |
| VI | Segurança (auth, RBAC, AD) | ✅ PASS | Nenhuma permissão nova ou alterada; nenhuma rota nova |
| VII | MariaDB / alterações aditivas | ✅ PASS | **Zero migração**: coluna permanece (H-1); nenhum dado apagado |
| VIII | Testes como não regressão | ✅ PASS | Novos testes para as 7 exigências do input; testes existentes que assertam o campo são AJUSTADOS (comportamento especificamente alterado pela spec — exceção prevista no Princípio VIII) |
| IX | Auditoria | ✅ PASS | Nenhuma alteração; eventos existentes continuam |
| X | Interface consistente | ✅ PASS | Telas apenas REMOVEM a linha de colaborador esperado; nenhum layout novo |
| XI | Documentação fiel | ✅ PASS | README (seção Inventário) e docs atualizados no que muda |
| XII | Fluxo por especificação | ✅ PASS | specify → clarify (H-1..H-3) → plan → tasks → implement |

**Gate: PASS** — sem violações; nada a registrar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/034-inventario-snapshot-sem-custodia/
├── plan.md              # Este arquivo
├── research.md          # Phase 0: decisões D1–D5
├── data-model.md        # Phase 1: impacto no modelo (nenhuma migração)
├── contracts/           # Phase 1: contrato da ata (CSV/Excel/PDF) + pacote offline
│   └── inventario-ata-contract.md
├── quickstart.md        # Phase 1: validação ponta a ponta
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── services/
│   ├── inventario_service.py            # TOQUE: geração não grava expected_custodian_name
│   ├── report_service.py                # TOQUE: coluna "Responsável Esperado" só quando houver histórico (H-2)
│   └── inventario_offline_service.py    # TOQUE: pacote sem o campo (H-3)
└── web/templates/inventarios/
    ├── detail.html                      # TOQUE: remove exibição do colaborador esperado nos cards
    └── conferir.html                    # TOQUE: remove "Colaborador esperado:" da conferência

tests/
└── test_inventario.py                   # TOQUE: novos testes + ajustes dos asserts do campo
```

**Structure Decision**: nenhum arquivo novo de produção; alterações pontuais nos services existentes (Princípios II/III) e nos dois templates. Documentação (README) atualizada na implementação (Princípio XI).

## Complexity Tracking

> Sem violações de Constitution — seção vazia por decisão de gate PASS.
