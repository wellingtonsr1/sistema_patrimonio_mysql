# Implementation Plan: Ajuste Responsivo da Tabela "Trilha de Auditoria & Fluxo"

**Branch**: `042-trilha-auditoria-larguras-colunas` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/042-trilha-auditoria-larguras-colunas/spec.md`

## Summary

Redistribuir exclusivamente a largura das colunas da tabela da **Trilha de Auditoria & Fluxo** (`app/web/templates/reports/movements_report.html`, 10 colunas), com o objetivo visual principal de **manter os valores em uma única linha horizontal**: colunas textuais **Equipamento, Origem, Destino e Motivo** dominam — e, por clarificação, exibem **linha garantida** (`nowrap` + ellipsis + tooltip Bootstrap, corte controlado sem sobreposição, valor completo acessível — C-7); **Operador** intermediária (idem); **Data/Hora, Tombamento, Tipo, Status e Termo** compactas (nowrap; identificadores nunca quebram). Em telas pequenas, a **rolagem horizontal confinada é explicitamente permitida** (C-4 — diferença intencional das 036/037). Estratégia: **reusar o mecanismo comprovado das 036–041** (fixed + colgroup único em px calibrado para a Plus Jakarta Sans — lição da 041: um só conjunto, sem media query de colunas) **+ novidade da 042**: classe auxiliar de ellipsis com tooltip Bootstrap (auto-inicializado em `base.html`/`main.js`) e neutralização de impressão **incluindo os spans internos** (o C7 global só atinge `td/th`). Nenhuma mudança funcional; bloco C1–C10 intocado; âncora `report-print` preservada; comentários sem nomes de controles (lição `b75ba99`).

## Technical Context

**Language/Version**: Python 3.10+ (backend **intocado**); Jinja2 template; CSS3 (fixed + colgroup, nowrap/ellipsis escopados, regra de segurança de impressão) + atributos Bootstrap tooltip (sem JS novo)

**Primary Dependencies**: Bootstrap 5.3.3 (vendor local; Tooltip do bundle), `style.css` do projeto (**intocado**), Jinja2

**Storage**: N/A — nenhum model, tabela, migração, rota, payload ou registro de auditoria é alterado

**Testing**: pytest (suíte existente 100% verde — SC-006; run focado: `test_report_print_smoke.py`, `test_movements.py`, `test_help.py`, `test_rbac.py`); validação visual com medição real + screenshots V0–V6 **+ conferência dos tooltips no navegador + verificação de impressão antes/depois**, registrada em `validacao.md` (SC-008, formato das 036–041)

**Target Platform**: navegadores modernos desktop/notebook/tablet/celular; zoom 80%–200% (precedentes); diálogo de impressão do navegador (retrato/paisagem)

**Performance Goals**: nenhuma alteração de performance (mesmos assets; tooltips são inicialização existente; nenhuma dependência nova)

**Constraints**: mudança cirúrgica (Princípio I/FR-019); zero mudança funcional (FR-017); container/header/cabeçalho interno intocados (FR-014); **linha garantida nas textuais** com corte controlado + tooltip Bootstrap (clarificação, FR-005/007/008/010/011); identificadores/Data-Hora/Status/Termo nunca quebram (FR-003/004/006/009/012); rolagem confinada autorizada em telas pequenas (C-4/FR-015); bloco de impressão C1–C10 intocado + neutralização escopada **incluindo spans de ellipsis** (FR-016/R10); âncora `class="card p-4 report-print"` preservada (contract §1); estrutura local+custodião de Origem/Destino e fallbacks preservados (FR-018); telas da 036–041 intocadas (FR-019); tema claro/escuro preservado; sem nomes de controles do header em comentários (lição `b75ba99`); SC-001/SC-002 indicativos

**Scale/Scope**: 1 template (`reports/movements_report.html`) — classe de escopo na tabela + classe auxiliar de ellipsis + `<style>` embutido (incl. `@media print` escopado); nenhuma outra tela, rota, service ou asset

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Mudança cirúrgica: só o template do relatório; sem refatoração; sem troca de framework | ✅ PASS |
| II. Arquitetura em camadas | Nenhuma regra de negócio em template; services/models intocados | ✅ PASS |
| III. Regras nos services | Sem regras novas; dados e `MovementService` intocados | ✅ PASS |
| IV. Integridade patrimonial | Fluxo patrimonial e movimentações intocados (apenas apresentação) | ✅ PASS |
| V. Integridade do inventário | Inventários intocados (036/037 fora do escopo, FR-019) | ✅ PASS |
| VI. Segurança/RBAC | Nenhuma rota/permissão nova; gate `relatorios.exportar` preservado; comentários sem controles; tooltips carregam dados das linhas (não strings de controles) | ✅ PASS |
| VII. Banco de dados | Nenhuma alteração | ✅ PASS |
| VIII. Testes | Suíte existente permanece verde; sem testes de UI automatizados (padrão 036–041); validação visual + tooltips + impressão documentadas (SC-008) | ✅ PASS |
| IX. Auditoria | Nenhum registro de auditoria alterado (apenas como é exibido) | ✅ PASS |
| X. Interface consistente | É o objetivo: mesma linguagem visual (badges/pills/tooltips existentes), melhor aproveitamento horizontal | ✅ PASS |
| XI. Documentação fiel | README/ajuda descrevem a trilha sem detalhar larguras; nenhuma atualização necessária (constatado no pós-design; re-verificar na implementação) | ✅ PASS |
| XII. Validação | Quickstart V0–V6 + suíte verde + registro em `validacao.md` (SC-008) | ✅ PASS |

**GATE: PASS (12/12)** — reavaliação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/042-trilha-auditoria-larguras-colunas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-contract-tabela-trilha-auditoria.md
├── checklists/          # Created by /speckit-specify + clarified by /speckit-clarify
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
└── web/
    └── templates/reports/
        └── movements_report.html   # ÚNICO arquivo alterado: tabela da trilha (10 colunas)
                                     # + <style> escopado (fixed + colgroup + ellipsis
                                     # + @media print escopado — R10)

tests/                              # NENHUM arquivo alterado (suíte existente = regressão;
                                    # test_report_print_smoke.py fixa a âncora report-print)
```

**Structure Decision**: Projeto único (padrão do repositório). A alteração fica integralmente em `reports/movements_report.html`; CSS novo embutido com classe de escopo própria (ex.: `.movrep-table`, distinta de `.mov-lista-table` da 039) + classe auxiliar de ellipsis (ex.: `.movrep-ellip`), evitando o `style.css` global (versionado em 2 pontos acoplados — mesma decisão R1 das 036–041). A regra de segurança de impressão entra no mesmo `<style>` escopado (`@media print` restrito à 042), sem tocar o bloco compartilhado C1–C10.

## Complexity Tracking

> Nenhuma violação de Constitution a justificar.

**GATE pós-design: PASS (12/12)** — o design não introduz dependência, rota, asset ou JS novo (tooltips usam a inicialização existente do base.html/main.js); 1 arquivo de código; FR-019 permanece satisfeito; a proteção de impressão é aditiva e escopada (R10).
