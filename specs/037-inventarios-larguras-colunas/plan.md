# Implementation Plan: Ajuste Responsivo da Tabela "Inventário Patrimonial"

**Branch**: `037-inventarios-larguras-colunas` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/037-inventarios-larguras-colunas/spec.md`

## Summary

Redistribuir exclusivamente a largura das colunas da tabela de listagem da tela **"Inventário Patrimonial"** (`app/web/templates/inventarios/list.html`): a tabela passa a aproveitar praticamente toda a largura útil do card; colunas textuais **Inventário** e **Escopo** dominam o espaço; **Código**, **Progresso** e **Status** ficam dimensionados ao conteúdo; **Ações** permanece mínima. Estratégia: **reusar o mecanismo comprovado da 036** (clarificação 2026-09-25) — `table-layout: fixed` + larguras por classes escopadas + quebras locais — com as larguras específicas desta tabela determinadas pela implementação após análise (C-1: sem percentuais fixados pela spec). Zero mudança funcional, de dados ou de rota; nenhum toque em `style.css`/Service Worker (CSS embutido no template).

## Technical Context

**Language/Version**: Python 3.10+ (backend **intocado**); Jinja2 template; CSS3 (`table-layout`, classes de coluna, `overflow-wrap`, media query)

**Primary Dependencies**: Bootstrap 5.3.3 (vendor local), `style.css` do projeto (**intocado**), Jinja2

**Storage**: N/A — nenhum model, tabela, migração, rota ou payload é alterado

**Testing**: pytest (suíte existente 100% verde — SC-006; `test_inventario.py` e `test_navbar.py` exercitam rotas da página); validação visual com medição real + screenshots nos cenários do pedido e faixa de zoom 80%–200%, registrada em `validacao.md` (SC-007, mesmo formato da 036)

**Target Platform**: navegadores modernos desktop/notebook/tablet/celular; zoom 80%–200% (clarificação)

**Performance Goals**: nenhuma alteração de performance (mesmos assets; nenhuma dependência nova)

**Constraints**: mudança cirúrgica (Princípio I/FR-014); zero mudança funcional (FR-012); container da tela **não alterado** (FR-011); as demais tabelas/páginas intocadas; tema claro/escuro preservado (nenhuma cor nova); SC-001/SC-002 são referências indicativas

**Scale/Scope**: 1 template (`list.html`) — classe de escopo na tabela + `<style>` embutido; nenhuma outra tela, rota, service ou asset

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Mudança cirúrgica: só o template da listagem; sem refatoração; sem troca de framework | ✅ PASS |
| II. Arquitetura em camadas | Nenhuma regra de negócio em template; services/models intocados | ✅ PASS |
| III. Regras nos services | Sem regras novas | ✅ PASS |
| IV. Integridade patrimonial | Movimentações/cadastro intocados | ✅ PASS |
| V. Integridade do inventário | CRUD/conferência/encerramento intocados (FR-012) | ✅ PASS |
| VI. Segurança/RBAC | Nenhuma rota/permissão nova; filtros e paginação intocados | ✅ PASS |
| VII. Banco de dados | Nenhuma alteração | ✅ PASS |
| VIII. Testes | Suíte existente permanece verde; sem testes de UI automatizados (mesmo D7 da 035/036); validação visual documentada (SC-007) | ✅ PASS |
| IX. Auditoria | Nenhuma operação nova a auditar | ✅ PASS |
| X. Interface consistente | É o objetivo: melhor aproveitamento horizontal na mesma linguagem visual | ✅ PASS |
| XI. Documentação fiel | README/ajuda não descrevem larguras da listagem; nenhuma atualização necessária (constatado no pós-design; re-verificar na implementação) | ✅ PASS |
| XII. Validação | Quickstart V1–V5 + suíte verde + registro em `validacao.md` (SC-007) | ✅ PASS |

**GATE: PASS (12/12)** — reavaliação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/037-inventarios-larguras-colunas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-contract-tabela-listagem.md
├── checklists/          # Created by /speckit-specify
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
└── web/
    └── templates/inventarios/
        └── list.html    # ÚNICO arquivo alterado: tabela de listagem (linhas ~51–97)
                          # + <style> embutido escopado (precedente 036)

tests/                     # NENHUM arquivo alterado (suíte existente = regressão)
```

**Structure Decision**: Projeto único (padrão do repositório). A alteração fica integralmente em `list.html`; o CSS novo é embutido no template com seletor de escopo próprio (ex.: `.inv-lista-table`), evitando o `style.css` global — versionado em 2 pontos acoplados (base.html + allowlist do SW), cujo bump invalidaria cache de todo o sistema (mesma decisão R1 da 036).

## Complexity Tracking

> Nenhuma violação de Constitution a justificar.

**GATE pós-design: PASS (12/12)** — o design não introduz dependência, rota ou asset novo; 1 arquivo de código; FR-014 permanece satisfeito.
