# Implementation Plan: Conferência Offline — responsividade e padronização visual

**Branch**: `035-conferencia-offline-layout` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/035-conferencia-offline-layout/spec.md`

## Summary

Corrigir exclusivamente o **layout/apresentação** da shell de Conferência Offline (`app/web/templates/inventarios/offline.html` + CSS embutido): (1) marca empilhada — logo acima, "SisPatrimônio Pro" abaixo — espelhando o padrão `.navbar-brand` do `style.css` do sistema; (2) container/largura das páginas principais (`90%` centralizado a partir de 768px; 100% + padding reduzido em mobile — decisão C-1); (3) pesquisa + "Ler QR" + tabela no mesmo grid/largura do card, com cabeçalhos alinhados aos dados; (4) rolagem horizontal restrita à tabela em telas estreitas; (5) tema claro/escuro preservado. Nenhuma lógica funcional muda; o único toque no Service Worker é o bump do `CACHE_VERSION` (v24 → v25) para propagar os estáticos cacheados.

## Technical Context

**Language/Version**: Python 3.10+ (backend **intocado**); Jinja2 templates; CSS3 (media queries, flexbox)

**Primary Dependencies**: Bootstrap 5.3.3 (vendor local self-hosted), Bootstrap Icons 1.11.3, JS vanilla (`inventario_offline.js` — intocado), Service Worker (`sw.js` — só versão de cache)

**Storage**: N/A — nenhum dado, model, migração ou rota é alterado

**Testing**: pytest (suíte existente deve permanecer 100% verde — FR-015); validação visual por checklist do quickstart (o projeto não tem infraestrutura de teste de UI — decisão D7)

**Target Platform**: navegadores modernos em desktop/notebook/tablet/celular (coleta em campo: Chrome/Edge Android); shell PWA offline-first

**Performance Goals**: nenhuma alteração de performance esperada (mesmos assets; nenhuma dependência nova)

**Constraints**: mudança cirúrgica (Princípio I); zero mudança funcional/dados (FR-012/FR-013); shell continua autônoma (sem `base.html` — FR-030 da 033); funcionamento offline intocado

**Scale/Scope**: 1 template + seu CSS embutido (+ ajuste pontual em `style.css` se reuso exigir) + bump do SW; nenhuma tela, rota ou serviço novo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Mudança cirúrgica: template da shell + CSS + bump do SW; nenhuma refatoração não relacionada; sem troca de framework | ✅ PASS |
| II. Arquitetura em camadas | Nenhuma regra de negócio em template; nenhum service/model tocado | ✅ PASS |
| III. Regras nos services | Sem regras novas; JS e serviços intocados | ✅ PASS |
| IV. Integridade patrimonial | Movimentações/cadastro intocados | ✅ PASS |
| V. Integridade do inventário | Regras de conferência/snapshot intocadas (FR-012) | ✅ PASS |
| VI. Segurança/RBAC | Nenhuma rota/permissão nova; rota existente já protegida | ✅ PASS |
| VII. Banco de dados | Nenhuma alteração de banco (FR-013) | ✅ PASS |
| VIII. Testes | Suíte existente deve permanecer verde; sem testes a remover/enfraquecer; testes de layout automatizados não são exigidos (sem infra de UI test — D7); validação visual documentada cobre a verificação (Princípio XII) | ✅ PASS |
| IX. Auditoria | Nenhuma operação nova a auditar | ✅ PASS |
| X. Interface consistente | É o objetivo da feature: padronizar com o sistema; fluxo offline não pode quebrar (cenários de aceite garantem) | ✅ PASS |
| XI. Documentação fiel | Comportamento documentado no README (uso da coleta offline) não muda — nenhuma atualização necessária; constatado no pós-design | ✅ PASS |
| XII. Validação | Quickstart V1–V5 + suíte verde como definição de pronto | ✅ PASS |

**GATE: PASS (12/12)** — pós-design reavaliado ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/035-conferencia-offline-layout/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-shell-offline-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── web/
│   ├── templates/inventarios/
│   │   └── offline.html                     # TOQUE: marca empilhada (D1), container/largura (D2),
│   │                                        #   grid pesquisa+QR+tabela (D3), header mobile (D4),
│   │                                        #   media queries e espaçamentos — CSS embutido
│   ├── static/
│   │   ├── css/style.css                    # SOMENTE SE reuso de classes exigir (preferir CSS local do template)
│   │   └── js/sw.js                         # TOQUE: bump CACHE_VERSION v24 → v25 (D5) — nada mais
│   └── static/js/inventario_offline.js      # INTOCADO (contrato DOM preservado — contracts/)
tests/
└── test_inventario_offline.py               # INTOCADO: rota shell (200/401/403) já coberta; suíte verde é o gate

specs/035-conferencia-offline-layout/        # artefatos desta feature (plan/research/data-model/contracts/quickstart)
```

**Nota**: `tests/test_inventario_offline.py` renderiza a rota e valida RBAC — segue como rede de não-regressão; nenhum assert de layout existe (Assumptions da spec).

## Constitution Check (pós-design — reavaliação)

Após Phase 0/1 (research D1–D7, data-model, contrato de UI e quickstart), nenhum princípio foi afetado pelo desenho: as decisões D1–D5 operam exclusivamente sobre apresentação e versão de cache; D6/D7 formalizam a validação sem nova infraestrutura. O contrato de UI (§1) garante que o JS e a coleta offline não são afetados. **GATE pós-design: PASS (12/12).**
