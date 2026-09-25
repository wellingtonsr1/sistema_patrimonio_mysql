# Implementation Plan: Ajuste Responsivo da Tabela "Colaboradores & Custodiantes"

**Branch**: `040-custodiantes-larguras-colunas` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/040-custodiantes-larguras-colunas/spec.md`

## Summary

Redistribuir exclusivamente a largura das colunas da tabela de **Colaboradores & Custodiantes** (`app/web/templates/custodians/list.html`, 7 colunas): a tabela aproveita praticamente toda a largura útil do card; colunas textuais **Nome**, **Cargo**, **Departamento** e **E-mail** dominam — e, por clarificação do solicitante, exibem o **texto completo, sem corte nenhum** (sem clamp nem reticências; linhas crescem conforme o conteúdo); **Matrícula** proporcional (com o badge condicional "provisória"); **Bens** e **Ações** compactas. Estratégia: **reusar o mecanismo comprovado das 036–039** (layout determinístico com larguras por classes escopadas + `min-width` com rolagem confinada), com as larguras determinadas por medição na implementação (C-1) e a escolha de `table-layout` justificada pela análise (C-5). Especificidades da 040: coluna Ações contém botão com **texto** ("Ver Bens") além do ícone "Editar" — largura mínima maior que nas telas anteriores; fontes de medição locais são mais estreitas que a Plus Jakarta Sans (lição da 039: rígidas em px com folga). Zero mudança funcional; nenhum toque em `style.css`/Service Worker; container, filtro e estados vazios intocados.

## Technical Context

**Language/Version**: Python 3.10+ (backend **intocado**); Jinja2 template; CSS3 (layout de tabela, quebras locais, media query)

**Primary Dependencies**: Bootstrap 5.3.3 (vendor local), `style.css` do projeto (**intocado**), Jinja2

**Storage**: N/A — nenhum model, tabela, migração, rota ou payload é alterado

**Testing**: pytest (suíte existente 100% verde — SC-006; `test_rbac.py`, `test_help.py` e testes de custodians exercitam a página/domínio); validação visual com medição real + screenshots nos cenários do pedido e zoom 80%–200%, registrada em `validacao.md` (SC-007, formato das 036–039)

**Target Platform**: navegadores modernos desktop/notebook/tablet/celular; zoom 80%–200% (precedentes)

**Performance Goals**: nenhuma alteração de performance (mesmos assets; nenhuma dependência nova)

**Constraints**: mudança cirúrgica (Princípio I/FR-014); zero mudança funcional (FR-012); container/filtro/estados vazios intocados (FR-010); **texto completo em Nome/Cargo/Departamento/E-mail** (sem clamp/ellipsis — clarificação, FR-004..007); badge "provisória" e botão "Ver Bens" com texto preservados (FR-013); as tabelas da 036–039 e demais telas intocadas; tema claro/escuro preservado; SC-001/SC-002 indicativos

**Scale/Scope**: 1 template (`custodians/list.html`) — classe de escopo na tabela + `<style>` embutido; nenhuma outra tela, rota, service ou asset

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Mudança cirúrgica: só o template de custodians; sem refatoração; sem troca de framework | ✅ PASS |
| II. Arquitetura em camadas | Nenhuma regra de negócio em template; services/models intocados | ✅ PASS |
| III. Regras nos services | Sem regras novas | ✅ PASS |
| IV. Integridade patrimonial | Custódia/vínculo com bens intocados (links/botões preservados, FR-012) | ✅ PASS |
| V. Integridade do inventário | Inventários intocados (tabelas da 036/037 fora do escopo, FR-014) | ✅ PASS |
| VI. Segurança/RBAC | Nenhuma rota/permissão nova; "Editar Colaborador" permanece condicional a `colaboradores.editar` | ✅ PASS |
| VII. Banco de dados | Nenhuma alteração | ✅ PASS |
| VIII. Testes | Suíte existente permanece verde; sem testes de UI automatizados (padrão 036–039); validação visual documentada (SC-007) | ✅ PASS |
| IX. Auditoria | Nenhuma operação nova a auditar | ✅ PASS |
| X. Interface consistente | É o objetivo: mesma linguagem visual, melhor aproveitamento horizontal | ✅ PASS |
| XI. Documentação fiel | README/ajuda não descrevem larguras da listagem de colaboradores; nenhuma atualização necessária (constatado no pós-design; re-verificar na implementação) | ✅ PASS |
| XII. Validação | Quickstart V0–V5 + suíte verde + registro em `validacao.md` (SC-007) | ✅ PASS |

**GATE: PASS (12/12)** — reavaliação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/040-custodiantes-larguras-colunas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-contract-tabela-custodiantes.md
├── checklists/          # Created by /speckit-specify
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
└── web/
    └── templates/custodians/
        └── list.html    # ÚNICO arquivo alterado: tabela de colaboradores (linhas ~44–86)
                          # + <style> embutido escopado (precedente 036–039)

tests/                     # NENHUM arquivo alterado (suíte existente = regressão)
```

**Structure Decision**: Projeto único (padrão do repositório). A alteração fica integralmente em `custodians/list.html`; CSS novo embutido com classe de escopo própria (ex.: `.cust-lista-table`), evitando o `style.css` global (versionado em 2 pontos acoplados — bump invalidaria cache de todo o sistema; mesma decisão R1 das 036–039).

## Complexity Tracking

> Nenhuma violação de Constitution a justificar.

**GATE pós-design: PASS (12/12)** — o design não introduz dependência, rota ou asset novo; 1 arquivo de código; FR-014 permanece satisfeito.
