# Implementation Plan: Ajuste Responsivo da Tabela "Usuários do Sistema"

**Branch**: `043-usuarios-larguras-colunas` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/043-usuarios-larguras-colunas/spec.md`

## Summary

Redistribuir exclusivamente a largura das colunas da tabela de **Usuários do Sistema** (`app/web/templates/admin/users/list.html`, 7 colunas), com o objetivo prioritário de **manter os valores em uma única linha sempre que a largura permitir**: colunas textuais **E-mail, Usuário e Perfis** dominam — **E-mail e as duas linhas da coluna Usuário (username e full_name) com linha garantida** (nowrap + ellipsis + **tooltip Bootstrap** — clarificações; corte controlado sem sobreposição, valor completo acessível); **Perfis com badges íntegros sem ellipsis** (C-6, dado funcional), organizando-se entre si via flex-wrap; **Último Acesso** intermediária (nowrap existente); **Origem, Status e Ações** compactas (badges com quebra apenas entre palavras — lição da 042 sobre o nowrap embutido do `.badge`). Estratégia: **reusar o mecanismo comprovado das 036–042** (fixed + colgroup único em px calibrado para a Plus Jakarta Sans, sem media query de colunas — lição da 041). **Diferença das 041/042**: tela não-relatório — **sem bloco de impressão** (não participa do `@media print` dos relatórios; nada criado ou alterado). Zero mudança funcional (autenticação/RBAC/AD intocados); comentários sem nomes de controles (lição `b75ba99`; `test_rbac.py:213/221` valida strings desta página).

## Technical Context

**Language/Version**: Python 3.10+ (backend **intocado**); Jinja2 template; CSS3 (fixed + colgroup, nowrap/ellipsis escopados, `white-space: normal` escopado para badges) + atributos Bootstrap tooltip (sem JS novo)

**Primary Dependencies**: Bootstrap 5.3.3 (vendor local; Tooltip do bundle), `style.css` do projeto (**intocado**), Jinja2

**Storage**: N/A — nenhum model, tabela, migração, rota, payload ou regra de autenticação é alterado

**Testing**: pytest (suíte existente 100% verde — SC-006; run focado: `test_rbac.py`, `test_help.py` + testes do domínio admin/users identificados no baseline); validação visual com medição real V0–V5 **+ conferência dos tooltips no navegador**, registrada em `validacao.md` (SC-007, formato das anteriores)

**Target Platform**: navegadores modernos desktop/notebook/tablet/celular; zoom 80%–200% (precedentes)

**Performance Goals**: nenhuma alteração de performance (mesmos assets; tooltips usam a inicialização existente; nenhuma dependência nova)

**Constraints**: mudança cirúrgica (Princípio I/FR-015); zero mudança funcional (FR-013); container/header/filtro/estado vazio intocados (FR-010); **linha garantida em username, full_name e e-mail** com corte controlado + tooltip Bootstrap (clarificações, FR-003/004/011); **badges sem ellipsis** (Perfis/Origem/Status — C-6/FR-006/FR-005/FR-007), com `white-space: normal` escopado para quebra entre palavras; `text-nowrap` existentes preservados (FR-008/FR-009); conjunto único de colunas px (lição 041) com pisos ×1,25–1,30 (fonte real); sem `@media print` (R10); telas 036–042 intocadas (FR-015); tema claro/escuro preservado; sem nomes de controles em comentários (lição `b75ba99`); SC-001/SC-002 indicativos

**Scale/Scope**: 1 template (`admin/users/list.html`) — classe de escopo na tabela + classe auxiliar de ellipsis + `<style>` embutido; nenhuma outra tela, rota, service ou asset

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Mudança cirúrgica: só o template de usuários; sem refatoração; sem troca de framework | ✅ PASS |
| II. Arquitetura em camadas | Nenhuma regra de negócio em template; services/models intocados | ✅ PASS |
| III. Regras nos services | Sem regras novas; autenticação/AD intocados | ✅ PASS |
| IV. Integridade patrimonial | Nenhum dado patrimonial alterado (apenas apresentação do cadastro de usuários) | ✅ PASS |
| V. Integridade do inventário | Inventários intocados (036/037 fora do escopo, FR-015) | ✅ PASS |
| VI. Segurança/RBAC | Nenhuma rota/permissão nova; condições `usuarios.*` e `is_admin` preservadas; comentários sem controles; `test_rbac.py` valida esta página | ✅ PASS |
| VII. Banco de dados | Nenhuma alteração | ✅ PASS |
| VIII. Testes | Suíte existente permanece verde; sem testes de UI automatizados (padrão 036–042); validação visual + tooltips documentadas (SC-007) | ✅ PASS |
| IX. Auditoria | Nenhuma operação nova a auditar; último acesso apenas exibido | ✅ PASS |
| X. Interface consistente | É o objetivo: mesma linguagem visual (badges/tooltips existentes), melhor aproveitamento horizontal | ✅ PASS |
| XI. Documentação fiel | README/ajuda não descrevem larguras da listagem de usuários; nenhuma atualização necessária (constatado no pós-design; re-verificar na implementação) | ✅ PASS |
| XII. Validação | Quickstart V0–V5 + suíte verde + registro em `validacao.md` (SC-007) | ✅ PASS |

**GATE: PASS (12/12)** — reavaliação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/043-usuarios-larguras-colunas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-contract-tabela-usuarios.md
├── checklists/          # Created by /speckit-specify + clarified by /speckit-clarify
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
└── web/
    └── templates/admin/
        └── users/
            └── list.html    # ÚNICO arquivo alterado: tabela de usuários (7 colunas)
                              # + <style> escopado (fixed + colgroup + ellipsis);
                              # SEM @media print (R10 — tela não-relatório)

tests/                       # NENHUM arquivo alterado (suíte existente = regressão)
```

**Structure Decision**: Projeto único (padrão do repositório). A alteração fica integralmente em `admin/users/list.html`; CSS novo embutido com classe de escopo própria (ex.: `.usr-lista-table`) + classe auxiliar de ellipsis (ex.: `.usr-ellip`), evitando o `style.css` global (versionado em 2 pontos acoplados — mesma decisão R1 das anteriores). Diferença das 041/042: nenhum bloco de impressão é criado (tela não-relatório — R10).

## Complexity Tracking

> Nenhuma violação de Constitution a justificar.

**GATE pós-design: PASS (12/12)** — o design não introduz dependência, rota, asset ou JS novo; 1 arquivo de código; FR-015 permanece satisfeito; sem interação com o domínio de impressão.
