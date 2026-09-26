# Implementation Plan: Ajuste Responsivo da Tabela "Visão Geral do Patrimônio" (046)

**Branch**: `046-dashboard-larguras-colunas` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/046-dashboard-larguras-colunas/spec.md`

## Summary

Redistribuir exclusivamente a largura das colunas da tabela **"Fluxo Recente de Movimentações"** da tela **"Visão Geral do Patrimônio"** (`app/web/templates/dashboard.html`, 7 colunas), com o objetivo prioritário de **manter os valores em uma única linha sempre que a largura permitir** (C-4): **Data compacta** (nowrap já existente preservado), **Tombamento compacto** com o `.tag-badge` existente (regras globais preservadas — sem ellipsis novo), **Ação com badge íntegro** dimensionado pelos rótulos reais, **Equipamento, Destino e Operador amplos** com **linha garantida** (nowrap + ellipsis + **tooltip Bootstrap** — clarificação) e **Ações mínima** (dois botões-ícone, um deles condicional). Estratégia: **reusar o mecanismo comprovado das 036–044** (`table-layout: fixed` + `<colgroup>` único em px calibrado para a Plus Jakarta Sans, sem media query de colunas — lição da 041; classe de escopo própria; `<style>` embutido no template). **Tela não-relatório**: **sem `@media print`** (R10 da 043). **Outra tabela do mesmo template intocada** ("Necessitam de atenção", L182–200) — o escopo de CSS é restrito à classe da tabela de movimentações. Zero mudança funcional; comentários sem nomes de controles (lição `b75ba99`). Validação com **script automatizado de medição local** (`validar_local.py`, padrão 039/042/044 — clarificação) + `validacao.md`.

## Technical Context

**Language/Version**: Python 3.10+ / FastAPI / Jinja2 / Bootstrap 5.3 (nenhuma dependência nova — alteração de template/CSS embutido)

**Primary Dependencies**: Bootstrap 5.3.3 (vendor local; Tooltip do bundle), `style.css` do projeto (**intocado**), Jinja2

**Storage**: N/A (nenhum dado/modelo/rota muda; `DashboardService.get_stats` e `recent_movements` limit 8 permanecem)

**Testing**: pytest — suíte existente 100% verde (regressão; `test_rbac.py` menciona o dashboard) + script de medição local (`validar_local.py`); **sem testes novos de UI** (seção 29 do pedido)

**Target Platform**: servidor institucional (desktop/notebook/tablet/celular; zoom 80%–200% — precedentes 036–044)

**Project Type**: web app (projeto único — template único)

**Performance Goals**: nenhuma alteração de performance (mesma tabela, mesmos dados; CSS estático embutido)

**Constraints**: mudança cirúrgica (Princípio I/FR-017); zero mudança funcional (FR-015); tabela de movimentações é a única superfície (FR-012/FR-017) — **a outra tabela do dashboard (L182–200) e demais cards/seções são intocados**; **linha garantida em Data, Tombamento, Equipamento, Ação, Destino e Operador** com corte controlado + tooltip Bootstrap (clarificação, FR-003…FR-008/FR-013); **Tombamento sem ellipsis novo** (regras globais do `.tag-badge` preservadas); coluna Ações estável com par condicional de botões (FR-009); conjunto único de colunas px (lição 041) com pisos ×1,25–1,30 (fonte real); **sem `@media print`** (R10) e **sem tocar `style.css`** (FR-012); tela 046 não afeta 036–045 (FR-017); tema claro/escuro preservado (`color:var(--c-text)` inline do link do Equipamento intacto); sem nomes de controles em comentários (lição `b75ba99`); SC-001/SC-002 indicativos

**Scale/Scope**: 1 template (`dashboard.html`) — classe de escopo na tabela de movimentações + classe auxiliar de ellipsis + `<style>` embutido + 1 script de validação local (`specs/046-dashboard-larguras-colunas/validar_local.py`); nenhuma outra tela, rota, service, asset ou JS

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Extensão apenas de apresentação da tabela-alvo; nenhuma funcionalidade, rota ou dado alterado; alteração localizada em 1 template | ✅ PASS |
| II. Arquitetura em camadas | N/A — nenhuma lógica nova; template/CSS apenas | ✅ PASS |
| III. Regras nos services | N/A — nenhuma regra de negócio tocada (`DashboardService` intocado) | ✅ PASS |
| IV. Integridade patrimonial | Dados patrimoniais apenas exibidos; nenhum valor, link ou ação alterado | ✅ PASS |
| V. Integridade do inventário | N/A | ✅ PASS |
| VI. Segurança/RBAC | Nenhum gate novo; nenhuma permissão nova; dashboard segue atrás da autenticação global | ✅ PASS |
| VII. Banco MariaDB | N/A — zero DDL, zero model | ✅ PASS |
| VIII. Testes | Sem testes novos de UI (seção 29); suíte como regressão + script de medição local | ✅ PASS |
| IX. Auditoria | N/A | ✅ PASS |
| X. Interface consistente | Padrão visual das 036–044 reusado (fixed + colgroup + escopo próprio); Bootstrap intacto | ✅ PASS |
| XI. Documentação fiel | `docs/ARQUITETURA_E_MANUTENCAO.md` não descreve larguras de tabela — sem atualização necessária (padrão 036–044) | ✅ PASS |
| XII. Validação | Quickstart + `validacao.md` com script `validar_local.py` + inspeção manual (SC-007; clarificação) | ✅ PASS |

**GATE: PASS (12/12)** — reavaliação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/046-dashboard-larguras-colunas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-contract-tabela-dashboard.md
├── checklists/
│   └── requirements.md  # Created by /speckit-specify + clarified by /speckit-clarify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
└── web/
    └── templates/
        └── dashboard.html   # + classe de escopo na tabela de movimentações;
                              # + <style> escopado (fixed + colgroup + ellipsis);
                              # + spans internos cortáveis com tooltip Bootstrap
specs/046-dashboard-larguras-colunas/
└── validar_local.py         # NOVO (fase de tarefas): medição local antes/depois
                              # (padrão 039/042/044 — ferramenta de validação, não teste pytest)
```

**Structure Decision**: Projeto único (padrão do repositório). A alteração fica integralmente em `dashboard.html`; CSS novo embutido com classe de escopo própria (ex.: `.dash-table`) + classe auxiliar de ellipsis (ex.: `.dash-ellip`), evitando o `style.css` global — que é cache global versionado em 2 pontos acoplados (base.html + SW allowlist). A mesma decisão R1 das anteriores; nenhum asset estático é tocado. Tela não-relatório: nenhum bloco de impressão é criado (R10). A outra tabela do template (L182–200) e os demais cards não recebem nenhuma regra nova.

## Complexity Tracking

> Nenhuma violação de Constitution a justificar.

**GATE pós-design: PASS (12/12)** — 1 template alterado, mecanismo reusado das 036–044 (fixed + colgroup + escopo próprio + tooltips), zero mudança funcional, outra tabela do dashboard e telas 036–045 intocadas, validação com script local + manual.
