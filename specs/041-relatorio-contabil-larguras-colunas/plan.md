# Implementation Plan: Ajuste Responsivo da Tabela "Relatório Contábil-Físico do Patrimônio"

**Branch**: `041-relatorio-contabil-larguras-colunas` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/041-relatorio-contabil-larguras-colunas/spec.md`

## Summary

Redistribuir exclusivamente a largura das colunas da tabela do **Relatório Contábil-Físico do Patrimônio** (`app/web/templates/reports/inventory.html`, 10 colunas): a tabela aproveita praticamente toda a largura útil do card; colunas textuais **Descrição**, **Localização** e **Responsável** dominam — e, por clarificação do solicitante, exibem o **texto completo, sem corte nenhum** (sem clamp nem reticências; linhas crescem conforme o conteúdo); **Tombamento** e **Categoria** ficam intermediárias; **Status**, **Data Compra** e as 3 monetárias permanecem compactas, com alinhamento consistente à direita. Estratégia: **reusar o mecanismo comprovado das 036–040** (layout determinístico com larguras por classes escopadas + `min-width` com rolagem confinada), com as larguras determinadas por medição na implementação (C-1) e a escolha de `table-layout` justificada pela análise (C-5). **Especificidade da 041**: preservação obrigatória da impressão/PDF (C-6/FR-013) — o bloco `@media print` C1–C10 é compartilhado pelos 3 relatórios e não é editado; regra de segurança escopada no `<style>` do template neutraliza em `@media print` qualquer largura/nowrap de tela (R10); âncora `report-print` fixada por `test_report_print_smoke.py`. Zero mudança funcional, contábil ou de exportações; nenhum toque em `style.css`/Service Worker; container, header e cabeçalho interno do relatório intocados; comentários CSS não citam controles do header (lição `b75ba99`).

## Technical Context

**Language/Version**: Python 3.10+ (backend **intocado**); Jinja2 template; CSS3 (layout de tabela, quebras locais, media query + regra de segurança de impressão escopada)

**Primary Dependencies**: Bootstrap 5.3.3 (vendor local), `style.css` do projeto (**intocado**), Jinja2

**Storage**: N/A — nenhum model, tabela, migração, rota, payload ou cálculo contábil é alterado

**Testing**: pytest (suíte existente 100% verde — SC-006; run focado: `test_report_print_smoke.py`, `test_rbac.py`, `test_help.py`); validação visual com medição real + screenshots nos cenários do pedido e zoom 80%–200% **+ verificação de impressão antes/depois (V6)**, registrada em `validacao.md` (SC-008, formato das 036–040)

**Target Platform**: navegadores modernos desktop/notebook/tablet/celular; zoom 80%–200% (precedentes); diálogo de impressão do navegador (retrato/paisagem)

**Performance Goals**: nenhuma alteração de performance (mesmos assets; nenhuma dependência nova)

**Constraints**: mudança cirúrgica (Princípio I/FR-016); zero mudança funcional/contábil (FR-014); container/header/cabeçalho interno intocados (FR-011); **texto completo em Descrição/Localização/Responsável** (sem clamp/ellipsis — clarificação, FR-004/007/008); bloco de impressão C1–C10 intocado + neutralização escopada em `@media print` (FR-013/R10); âncora `class="card p-4 report-print"` preservada (contract §1); fallbacks "Estoque Geral"/"Livre"/"-", `-XX%` vermelho e valor atual verde preservados (FR-015); tabelas da 036–040 e os outros 2 relatórios intocados (FR-016); tema claro/escuro preservado; sem nomes de controles do header em comentários (lição `b75ba99`); SC-001/SC-002 indicativos

**Scale/Scope**: 1 template (`reports/inventory.html`) — classe de escopo na tabela + `<style>` embutido (incl. `@media print` escopado); nenhuma outra tela, rota, service ou asset

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Mudança cirúrgica: só o template do relatório; sem refatoração; sem troca de framework | ✅ PASS |
| II. Arquitetura em camadas | Nenhuma regra de negócio em template; services/models intocados | ✅ PASS |
| III. Regras nos services | Sem regras novas; cálculos de depreciação intocados | ✅ PASS |
| IV. Integridade patrimonial | Nenhum dado/cálculo patrimonial alterado (apenas apresentação) | ✅ PASS |
| V. Integridade do inventário | Inventários intocados (tabelas da 036/037 fora do escopo, FR-016) | ✅ PASS |
| VI. Segurança/RBAC | Nenhuma rota/permissão nova; gate `relatorios.exportar` do header preservado; sem strings de controles em comentários | ✅ PASS |
| VII. Banco de dados | Nenhuma alteração | ✅ PASS |
| VIII. Testes | Suíte existente permanece verde; sem testes de UI automatizados (padrão 036–040); validação visual + impressão documentadas (SC-008) | ✅ PASS |
| IX. Auditoria | Nenhuma operação nova a auditar | ✅ PASS |
| X. Interface consistente | É o objetivo: mesma linguagem visual, melhor aproveitamento horizontal | ✅ PASS |
| XI. Documentação fiel | README/ajuda descrevem o relatório sem detalhar larguras de colunas; nenhuma atualização necessária (constatado no pós-design; re-verificar na implementação) | ✅ PASS |
| XII. Validação | Quickstart V0–V6 + suíte verde + registro em `validacao.md` (SC-008) | ✅ PASS |

**GATE: PASS (12/12)** — reavaliação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/041-relatorio-contabil-larguras-colunas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-contract-tabela-relatorio-contabil.md
├── checklists/          # Created by /speckit-specify + clarified by /speckit-clarify
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
└── web/
    └── templates/reports/
        └── inventory.html    # ÚNICO arquivo alterado: tabela do relatório (10 colunas)
                               # + <style> embutido escopado (incl. @media print escopado — R10)

tests/                         # NENHUM arquivo alterado (suíte existente = regressão;
                               # test_report_print_smoke.py fixa a âncora report-print)
```

**Structure Decision**: Projeto único (padrão do repositório). A alteração fica integralmente em `reports/inventory.html`; CSS novo embutido com classe de escopo própria (ex.: `.invrep-table`), evitando o `style.css` global (versionado em 2 pontos acoplados — bump invalidaria cache de todo o sistema; mesma decisão R1 das 036–040). A regra de segurança de impressão entra no mesmo `<style>` escopado (`@media print` restrito à classe da 041), sem tocar o bloco compartilhado C1–C10.

## Complexity Tracking

> Nenhuma violação de Constitution a justificar.

**GATE pós-design: PASS (12/12)** — o design não introduz dependência, rota ou asset novo; 1 arquivo de código; FR-016 permanece satisfeito; a proteção de impressão é aditiva e escopada (R10).
