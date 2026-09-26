# Implementation Plan: Ajuste Responsivo da Tabela "Etiquetas de Patrimônio"

**Branch**: `044-etiquetas-larguras-colunas` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/044-etiquetas-larguras-colunas/spec.md`

## Summary

Redistribuir exclusivamente a largura das colunas da **tabela de seleção** da tela **Etiquetas de Patrimônio** (`app/web/templates/assets/labels.html`, 5 colunas), com o objetivo prioritário de **manter os valores em uma única linha sempre que a largura permitir** (C-4): **Tombamento compacto** com o `.tag-badge` existente (regras globais preservadas — sem ellipsis novo), **Equipamento / Modelo, Setor e Localização amplos** com **linha garantida** (nowrap + ellipsis + **tooltip Bootstrap** — clarificações; valor completo acessível), incluindo a **linha auxiliar de marca/modelo** (clarificação). Estratégia: **reusar o mecanismo comprovado das 036–043** (fixed + colgroup único em px calibrado para a Plus Jakarta Sans, sem media query de colunas — lição da 041). **Tela não-relatório**: **sem `@media print`** (R10 da 043). **Domínio de impressão de etiquetas intocado**: `#labels-print-area`/`.labels-sheet`/`.label-card`, o `@media print` de etiquetas em `style.css` (feature 013) e o JS inline de seleção não são tocados. Zero mudança funcional; comentários sem nomes de controles (lição `b75ba99`).

## Technical Context

**Language/Version**: Python 3.10+ (backend **intocado**); Jinja2 template; CSS3 (fixed + colgroup, nowrap/ellipsis escopados) + atributos Bootstrap tooltip (sem JS novo)

**Primary Dependencies**: Bootstrap 5.3.3 (vendor local; Tooltip do bundle), `style.css` do projeto (**intocado** — inclui o domínio de impressão de etiquetas da 013), Jinja2

**Storage**: N/A — nenhum model, tabela, migração, rota, payload ou regra de seleção/filtro é alterado

**Testing**: pytest (suíte existente 100% verde — SC-006; run focado: `test_help.py` + `test_rbac.py` — **sem testes dedicados à página de etiquetas, constatado no baseline**); validação visual com medição real V0–V5 **+ conferência dos tooltips e da impressão de etiquetas no navegador**, registrada em `validacao.md` (SC-007, formato das anteriores)

**Target Platform**: navegadores modernos desktop/notebook/tablet/celular; zoom 80%–200% (precedentes)

**Performance Goals**: nenhuma alteração de performance (mesmos assets; tooltips usam a inicialização existente; nenhuma dependência nova)

**Constraints**: mudança cirúrgica (Princípio I/FR-016); zero mudança funcional (FR-014); tabela de seleção é a única superfície (FR-010/FR-016); **linha garantida em Equipamento (nome e marca/modelo), Setor e Localização** com corte controlado + tooltip Bootstrap (clarificações, FR-005/006/007/008/011); **Tombamento sem ellipsis novo** (regras globais do `.tag-badge` preservadas — fallback aceitável ≤479.98px, clarificação); coluna do checkbox estável (FR-003); conjunto único de colunas px (lição 041) com pisos ×1,25–1,30 (fonte real); **sem `@media print`** (R10) e **sem tocar `style.css`** (FR-013/FR-010); telas 036–043 intocadas (FR-016); tema claro/escuro preservado (contraste dos checkboxes em `style.css:1595` intacto); sem nomes de controles em comentários (lição `b75ba99`); SC-001/SC-002 indicativos

**Scale/Scope**: 1 template (`assets/labels.html`) — classe de escopo na tabela de seleção + classe auxiliar de ellipsis + `<style>` embutido; nenhuma outra tela, rota, service, asset ou JS

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Mudança cirúrgica: só o template de etiquetas (tabela de seleção); sem refatoração; sem troca de framework | ✅ PASS |
| II. Arquitetura em camadas | Nenhuma regra de negócio em template; services/models intocados | ✅ PASS |
| III. Regras nos services | Sem regras novas; geração de etiquetas intocada | ✅ PASS |
| IV. Integridade patrimonial | Nenhum dado patrimonial alterado (apenas apresentação da seleção); tombamentos intactos | ✅ PASS |
| V. Integridade do inventário | Inventários intocados (036/037 fora do escopo, FR-016) | ✅ PASS |
| VI. Segurança/RBAC | Nenhuma rota/permissão nova; gate `patrimonio.visualizar` preservado; comentários sem controles (lição `b75ba99`) | ✅ PASS |
| VII. Banco de dados | Nenhuma alteração | ✅ PASS |
| VIII. Testes | Suíte existente permanece verde; sem testes de UI automatizados (padrão da família); validação visual + tooltips + impressão documentadas (SC-007) | ✅ PASS |
| IX. Auditoria | Nenhuma operação nova a auditar; seleção continua via URL (somente leitura) | ✅ PASS |
| X. Interface consistente | É o objetivo: mesma linguagem visual (badge/tooltips/checkbox existentes), melhor aproveitamento horizontal | ✅ PASS |
| XI. Documentação fiel | README/ajuda não descrevem larguras da tabela de etiquetas; nenhuma atualização necessária (constatado no pós-design; re-verificar na implementação) | ✅ PASS |
| XII. Validação | Quickstart V0–V5 + suíte verde + registro em `validacao.md` (SC-007) | ✅ PASS |

**GATE: PASS (12/12)** — reavaliação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/044-etiquetas-larguras-colunas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-contract-tabela-etiquetas.md
├── checklists/          # Created by /speckit-specify + clarified by /speckit-clarify
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
└── web/
    └── templates/assets/
        └── labels.html  # ÚNICO arquivo alterado: tabela de seleção (5 colunas)
                          # + <style> escopado (fixed + colgroup + ellipsis);
                          # SEM @media print (R10 — tela não-relatório);
                          # folha de etiquetas e JS de seleção INTOCADOS
                          # (a parte modificada NÃO contém nomes de controles)

tests/                    # NENHUM arquivo alterado (suíte existente = regressão)
```

**Structure Decision**: Projeto único (padrão do repositório). A alteração fica integralmente em `assets/labels.html`; CSS novo embutido com classe de escopo própria (ex.: `.etiq-table`) + classe auxiliar de ellipsis (ex.: `.etiq-ellip`), evitando o `style.css` global — que aqui é ainda mais sensível: contém o `@media print` de etiquetas da feature 013 (`style.css:1605–1645`), o contraste dos checkboxes (`style.css:1595`) e as regras globais do `.tag-badge` (`style.css:491`/`1027`). Mesma decisão R1 das anteriores: nenhum asset estático é tocado. Tela não-relatório: nenhum bloco de impressão é criado (R10).

## Complexity Tracking

> Nenhuma violação de Constitution a justificar.

**GATE pós-design: PASS (12/12)** — o design não introduz dependência, rota, asset, JS ou regra de impressão nova; 1 arquivo de código; FR-016 permanece satisfeito; o domínio de impressão de etiquetas (013) e o JS de seleção em lote permanecem intocados.
