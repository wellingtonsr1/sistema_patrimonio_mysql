# Implementation Plan: Ajuste Responsivo da Tabela "Fluxo Global de Movimentações"

**Branch**: `039-movimentacoes-larguras-colunas` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/039-movimentacoes-larguras-colunas/spec.md`

## Summary

Redistribuir exclusivamente a largura das colunas da tabela de **Fluxo Global de Movimentações** (`app/web/templates/movements/list.html`, 9 colunas): a tabela aproveita praticamente toda a largura útil do card; colunas textuais **Equipamento**, **Origem**, **Destino**, **Motivo** e **Operador** dominam; **Data / Hora**, **Tombamento** e **Tipo** proporcionais; **Ações** compacta. Estratégia: **reusar o mecanismo comprovado das 036/037/038** (layout determinístico com larguras por classes escopadas + quebras locais + `min-width` com rolagem confinada), com as larguras desta tabela determinadas por medição na implementação (C-1) e a escolha de `table-layout` justificada pela análise (C-5). Especificidade da 039 (clarificação registrada): **remover o cap `max-width:220px` inline da coluna Motivo** mantendo o corte em 2 linhas (`truncate-2`). Zero mudança funcional; nenhum toque em `style.css`/Service Worker; container, filtro e contagem intocados.

## Technical Context

**Language/Version**: Python 3.10+ (backend **intocado**); Jinja2 template; CSS3 (layout de tabela, quebras locais, media query)

**Primary Dependencies**: Bootstrap 5.3.3 (vendor local), `style.css` do projeto (**intocado**), Jinja2

**Storage**: N/A — nenhum model, tabela, migração, rota ou payload é alterado

**Testing**: pytest (suíte existente 100% verde — SC-006; `test_movements.py` e demais testes de web/templating exercitam a página/domínio); validação visual com medição real + screenshots nos cenários do pedido e zoom 80%–200%, registrada em `validacao.md` (SC-007, formato das 036/037/038)

**Target Platform**: navegadores modernos desktop/notebook/tablet/celular; zoom 80%–200% (precedentes)

**Performance Goals**: nenhuma alteração de performance (mesmos assets; nenhuma dependência nova)

**Constraints**: mudança cirúrgica (Princípio I/FR-015); zero mudança funcional (FR-013); container/filtro/contagem intocados (FR-011); preservar `text-nowrap` funcional da Data / Hora, o corte em 2 linhas do Motivo (sem o cap de 220px, conforme clarificação) e as células de 2 linhas de Origem/Destino (FR-014); as tabelas da 036/037/038 e demais telas intocadas; tema claro/escuro preservado; SC-001/SC-002 indicativos

**Scale/Scope**: 1 template (`movements/list.html`) — classe de escopo na tabela + `<style>` embutido; nenhuma outra tela, rota, service ou asset

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Mudança cirúrgica: só o template de movements; sem refatoração; sem troca de framework | ✅ PASS |
| II. Arquitetura em camadas | Nenhuma regra de negócio em template; services/models intocados | ✅ PASS |
| III. Regras nos services | Sem regras novas | ✅ PASS |
| IV. Integridade patrimonial | Movimentações/patrimônio intocados (links/botões preservados, FR-013); trilha histórica apenas reexibida | ✅ PASS |
| V. Integridade do inventário | Inventários intocados (tabelas da 036/037 fora do escopo, FR-015) | ✅ PASS |
| VI. Segurança/RBAC | Nenhuma rota/permissão nova; botões "Imprimir Termo" (condicional a `m.term_code`) e "Ver Bem" preservados | ✅ PASS |
| VII. Banco de dados | Nenhuma alteração | ✅ PASS |
| VIII. Testes | Suíte existente permanece verde; sem testes de UI automatizados (padrão 036–038); validação visual documentada (SC-007) | ✅ PASS |
| IX. Auditoria | Nenhuma operação nova a auditar; dados auditáveis exibidos permanecem íntegros (FR-014) | ✅ PASS |
| X. Interface consistente | É o objetivo: mesma linguagem visual, melhor aproveitamento horizontal | ✅ PASS |
| XI. Documentação fiel | README/ajuda não descrevem larguras da listagem de movimentações; nenhuma atualização necessária (constatado no pós-design; re-verificar na implementação) | ✅ PASS |
| XII. Validação | Quickstart V0–V5 + suíte verde + registro em `validacao.md` (SC-007) | ✅ PASS |

**GATE: PASS (12/12)** — reavaliação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/039-movimentacoes-larguras-colunas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-contract-tabela-movimentacoes.md
├── checklists/          # Created by /speckit-specify
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
└── web/
    └── templates/movements/
        └── list.html    # ÚNICO arquivo alterado: tabela do fluxo global (linhas ~47–104)
                          # + <style> embutido escopado (precedente 036/037/038)

tests/                     # NENHUM arquivo alterado (suíte existente = regressão)
```

**Structure Decision**: Projeto único (padrão do repositório). A alteração fica integralmente em `movements/list.html`; CSS novo embutido com classe de escopo própria (ex.: `.mov-lista-table`), evitando o `style.css` global (versionado em 2 pontos acoplados — bump invalidaria cache de todo o sistema; mesma decisão R1 das 036/037/038).

## Complexity Tracking

> Nenhuma violação de Constitution a justificar.

**GATE pós-design: PASS (12/12)** — o design não introduz dependência, rota ou asset novo; 1 arquivo de código; FR-015 permanece satisfeito.
