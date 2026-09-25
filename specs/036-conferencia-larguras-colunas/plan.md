# Implementation Plan: Ajuste Responsivo das Larguras das Colunas na Tabela de Conferência

**Branch**: `036-conferencia-larguras-colunas` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/036-conferencia-larguras-colunas/spec.md`

## Summary

Redistribuir exclusivamente a largura das colunas da tabela de **bens esperados** da tela de conferência de inventário (`app/web/templates/inventarios/detail.html`): colunas textuais **Bem** e **Local esperado** passam a dominar o espaço horizontal; **Resultado** e **Conferir** ficam compactas; **Tombamento** mantém tamanho proporcional ao conteúdo (C-1). Estratégia técnica: layout determinístico da tabela via `table-layout: fixed` + `<colgroup>` com percentuais de referência (SC-001, indicativos), com proteções de quebra para conteúdos longos, mantendo `table-responsive`, alinhamentos atuais e todos os IDs/classes funcionais. Zero mudança funcional, de dados ou de rota; nenhum toque em `style.css`/Service Worker (o CSS da tela entra embutido no template — sem bump de cache global).

## Technical Context

**Language/Version**: Python 3.10+ (backend **intocado**); Jinja2 template; CSS3 (`table-layout`, `colgroup`, `word-break`, media queries)

**Primary Dependencies**: Bootstrap 5.3.3 (vendor local), Bootstrap Icons 1.11.3, `style.css` do projeto (**intocado**), Jinja2

**Storage**: N/A — nenhum model, tabela, migração, rota ou payload é alterado

**Testing**: pytest (suíte existente 100% verde — SC-005/SC-006; `test_inventario.py`, `test_conferencia_visual.py`, `test_inventario_reconferencia_ui.py` exercitam esta página); validação visual manual pelos cenários do quickstart (sem infra de teste de UI — D7 da 035), registrada em `validacao.md` (SC-007)

**Target Platform**: navegadores modernos desktop/notebook/tablet/celular; faixa de zoom 80%–200% (decisão da clarificação)

**Performance Goals**: nenhuma alteração de performance (mesmos assets; nenhuma dependência nova)

**Constraints**: mudança cirúrgica (Princípio I/FR-012); zero mudança funcional/dados (FR-010/FR-011); não afetar as outras 2 tabelas da mesma página (card Conflitos offline e card de coletas — FR-012); tema claro/escuro preservado; proporções do SC-001 são **referência indicativa** (clarificação Q1)

**Scale/Scope**: 1 template (`detail.html`) — ajuste nas colunas da tabela-alvo + pequeno `<style>` embutido (precedente: `offline.html`); nenhuma outra tela, rota, service ou asset

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Mudança cirúrgica: só o template da tela; sem refatoração não relacionada; sem troca de framework | ✅ PASS |
| II. Arquitetura em camadas | Nenhuma regra de negócio em template; services/models intocados | ✅ PASS |
| III. Regras nos services | Sem regras novas | ✅ PASS |
| IV. Integridade patrimonial | Movimentações/cadastro intocados | ✅ PASS |
| V. Integridade do inventário | Regras de conferência/snapshot intocadas (FR-010) | ✅ PASS |
| VI. Segurança/RBAC | Nenhuma rota/permissão nova; página continua protegida como hoje | ✅ PASS |
| VII. Banco de dados | Nenhuma alteração | ✅ PASS |
| VIII. Testes | Suíte existente permanece verde; testes de layout automatizados não exigidos (sem infra de UI — D7 da 035); validação visual documentada (Princípio XII/SC-007) | ✅ PASS |
| IX. Auditoria | Nenhuma operação nova a auditar | ✅ PASS |
| X. Interface consistente | É o objetivo: redistribuição de larguras na mesma linguagem visual; fluxo de conferência não muda | ✅ PASS |
| XI. Documentação fiel | README/ajuda não descrevem proporções de coluna; nenhuma atualização necessária (constatado no pós-design) | ✅ PASS |
| XII. Validação | Quickstart V1–V5 + suíte verde + registro em `validacao.md` (SC-007) | ✅ PASS |

**GATE: PASS (12/12)** — reavaliação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/036-conferencia-larguras-colunas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-contract-tabela-conferencia.md
├── checklists/          # Created by /speckit-specify
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
└── web/
    └── templates/inventarios/
        └── detail.html   # ÚNICO arquivo alterado: colunas da tabela de bens esperados
                           # (linhas ~226–276) + <style> embutido restrito à tela

tests/                     # NENHUM arquivo alterado (suíte existente = regressão)
```

**Structure Decision**: Projeto único (padrão do repositório): template Jinja2 em `app/web/templates/`, CSS do projeto em `app/web/static/css/style.css` (**intocado** nesta feature) e suíte pytest em `tests/`. A alteração fica integralmente em `detail.html`; qualquer regra CSS nova é embutida no próprio template (precedente `offline.html`), evitando tocar o `style.css` global — que é versionado por querystring em dois pontos (base.html + allowlist do SW) e invalidaria cache de todas as páginas.

## Complexity Tracking

> Nenhuma violação de Constitution a justificar.

**GATE pós-design: PASS (12/12)** — o design Phase 0/1 não introduz dependência nova, tabela/rota nova, nem altera módulos fora do template; FR-012 (escopo) permanece satisfeito com 1 arquivo de código.
