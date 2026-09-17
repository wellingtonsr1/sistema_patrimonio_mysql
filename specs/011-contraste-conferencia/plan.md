# Implementation Plan: Contraste das Opções de Resultado da Conferência

**Branch**: `011-contraste-conferencia` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-contraste-conferencia/spec.md`

## Summary

Correção exclusivamente visual: as 4 opções do campo "Resultado da conferência" (renderizadas como `<label class="d-block border rounded p-2">` em `inventarios/conferir.html` e no modal de `inventarios/detail.html`) usam a classe utilitária `.border` do Bootstrap, cuja cor padrão (`--bs-border-color`, NÃO sobrescrita pelo projeto) é quase invisível sobre o fundo claro da aplicação. No escuro o próprio Bootstrap 5.3 ajusta o token via `data-bs-theme="dark"` (já sincronizado em `base.html`), por isso lá funciona.

Abordagem: criar uma **classe própria do componente** (`.result-option`) no único CSS do tema (`app/web/static/css/style.css`), colorindo a borda com o **token existente** `--c-border` — que já alterna automaticamente entre claro (`#C8C2C0`) e escuro (`#3A3335`) — e aplicar essa classe aos 8 `<label>` (4 em cada template). Zero mudança de estrutura HTML, conteúdo, layout, lógica ou dados.

## Technical Context

**Language/Version**: Python 3.10+ (backend intacto); front-end Jinja2 + Bootstrap 5.3.3 + CSS custom (`app/web/static/css/style.css`, 1.611 linhas, único arquivo de estilo do tema)

**Primary Dependencies**: Bootstrap 5.3.3 (CDN), Jinja2 templates, tema claro/escuro via `data-theme` (raiz) + `data-bs-theme` sincronizado (`base.html` L2/L13)

**Storage**: N/A — nenhuma alteração de dados, modelos ou persistência

**Testing**: pytest (+ TestClient) — suíte existente como guarda de não-regressão; validação do contraste é visual/manual (padrão da feature documental 009)

**Target Platform**: Navegadores já suportados pela aplicação (`:has()` já utilizado no `style.css` L1585 — seletores modernos fazem parte do padrão atual)

**Project Type**: web application existente (FastAPI + Jinja2)

**Performance Goals**: N/A (sem impacto — 1 classe CSS + atributo de classe em 8 elementos)

**Constraints**:
- A borda DEVE acompanhar o tema ativo (proibida cor fixa única para os dois temas — FR-004)
- A classe utilitária `.border` do Bootstrap NÃO pode ser modificada globalmente (FR-009/US3)
- Estados existentes (seleção, foco, hover/cursor) preservados (FR-005/FR-011)
- Zero mudança de estrutura HTML, texto, emojis, espaçamento ou responsividade (FR-006/FR-007)
- Suíte pytest permanece no patamar atual (SC-006)

**Scale/Scope**: 3 arquivos (1 CSS + 2 templates), 8 elementos HTML tocados (somente acréscimo de classe), 0 linhas de Python

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Notas |
|---|---|---|
| I. Preservação do sistema existente | ✅ PASS | Mudança incremental mínima; nenhuma funcionalidade removida ou alterada |
| II. Arquitetura em camadas | ✅ PASS | Nenhum código Python tocado; apresentação permanece em template/CSS |
| III. Regras de negócio nos services | ✅ PASS | Nenhuma regra de negócio envolvida |
| IV. Integridade patrimonial/movimentações | ✅ PASS | Nenhuma escrita de dados; conferência intocada |
| V. Integridade do inventário | ✅ PASS | Regras de status/validação intocadas; apenas apresentação do formulário |
| VI. Segurança (auth/RBAC/AD) | ✅ PASS | Nenhuma rota nova; permissões e guardas existentes intocados |
| VII. Banco MariaDB/proteção de dados | ✅ PASS | Zero DDL, zero query, zero migração |
| VIII. Testes como não-regressão | ✅ PASS | Suíte verde obrigatória; guarda leve de renderização prevista (R4) |
| IX. Auditoria | ✅ PASS | Nenhuma operação relevante nova (visual apenas) |
| X. Interface consistente e funcional | ✅ PASS | **É o objeto da feature**: corrige contraste mantendo padrões visuais |
| XI. Documentação fiel | ✅ PASS | Nenhum comportamento documentado muda (fluxos, endpoints, permissões intocados); não há atualização de docs — justificado no research R5 |
| XII. Fluxo por especificação | ✅ PASS | Spec aprovada → plan → tasks → implement |

**Pré-design: 12/12 PASS.** Pós-design: reavaliado ao final deste documento (sem violações — ver abaixo).

## Project Structure

### Documentation (this feature)

```text
specs/011-contraste-conferencia/
├── plan.md              # This file
├── research.md          # Phase 0 output (decisões R1–R5)
├── data-model.md        # Phase 1 output (N/A documentado — feature sem dados)
├── quickstart.md        # Phase 1 output (validação visual nos 2 temas × 2 telas)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
app/
├── web/
│   ├── static/css/
│   │   └── style.css                    # + classe .result-option (borda via --c-border)
│   └── templates/inventarios/
│       ├── conferir.html                # 4 <label>: + classe result-option
│       └── detail.html                  # 4 <label> (modal): + classe result-option
tests/
└── test_inventario.py (ou novo test_render_011.py)  # guarda leve de renderização (R4)
```

**Structure Decision**: feature de apresentação — nenhum service, model, rota ou schema é tocado. A única fonte de estilo é `style.css` (padrão do projeto: classes de componente próprias convivendo com utilitários Bootstrap, ex. `.badge-soft-primary`, `.tag-badge`).

## Technical Approach

### Fluxo de implementação (8 passos)

1. **Baseline** — `python -m pytest tests/ -q --tb=no` → patamar atual registrado (310 passed / 1 failed conhecida de lockout).
2. **CSS (R1/R2)** — em `style.css`, criar a classe do componente na região de componentes existentes:
   ```css
   /* Feature 011 — opções de "Resultado da conferência": borda com contraste
      nos dois temas via token existente (não altera a utilitária .border global). */
   .result-option {
     border: 1px solid var(--c-border) !important;
   }
   ```
   - `var(--c-border)` já resolve claro (`#C8C2C0`) e escuro (`#3A3335`) — FR-003/FR-004.
   - `!important` é necessário porque a utilitária `.border` do Bootstrap define `border: var(--bs-border-width) var(--bs-border-style) var(--bs-border-color)!important` (mesma especificidade; a do Bootstrap também é important — a nossa precisa vencer sem tocar nela).
3. **Templates (R3)** — acrescentar `result-option` à lista de classes dos 8 `<label>` (4 em `conferir.html`, 4 em `detail.html`), ex.: `class="d-block border rounded p-2 result-option"`. Nenhuma outra alteração no markup.
4. **Guarda de renderização (R4)** — 1 teste leve (pytest/TestClient, padrão da suíte): renderizar a página de conferência de um item e verificar a presença de `result-option` nas 4 opções e a integridade dos valores `ENCONTRADO`/`LOCAL_DIFERENTE`/`NAO_ENCONTRADO`/`SEM_IDENTIFICACAO`. Opcionalmente o mesmo para o modal em `detail.html`. Sem asserção de cor (não testável sem navegador) — a validação visual fica no quickstart.
5. **Suíte completa** — patamar baseline + novo teste, zero failure novo.
6. **Validação visual manual (quickstart)** — 2 temas × 2 telas + cenários de seleção/hover/foco + varredura de outras telas (US3).
7. **Fechamento** — `git status --porcelain` restrito aos 3 arquivos + artefatos; Constitution checklist.
8. **Sem atualização de documentação** (R5) — nenhum comportamento documentado (fluxo, endpoint, permissão) muda; ajuda/README não descrevem estilos de borda.

### Tratamento dos estados existentes (FR-005/FR-011)

| Estado | Mecanismo atual | Impacto da correção |
|---|---|---|
| Selecionado | marcação do `input[type=radio]` (Bootstrap `form-check-input`) | Intocado — borda não é o único indicador (FR-011) |
| Foco | outline de foco do Bootstrap no rádio | Intocado |
| Hover | `cursor:pointer` inline no `<label>` | Intocado |
| Não selecionado | sem destaque além da borda | **Único ponto alterado**: borda ganha contraste |

### Riscos e mitigação

| Risco | Mitigação |
|---|---|
| `.border` do Bootstrap usa `!important` — regra nova pode não vencer | A própria utilitária é `!important`; a classe do componente com `!important` e maior especificidade de posição (carregada depois, `style.css` vem após o bootstrap.min.css em `base.html`) vence — verificado na validação |
| Alguma outra tela use `<label class="d-block border rounded p-2">` | Varredura por grep confirmou: **somente** os 2 templates do inventário (US3/FR-009) — re-verificar no implement |
| Regressão no escuro ao trocar a borda | O token `--c-border` no escuro (`#3A3335`) é o mesmo usado por cards/tabelas do tema escuro — contraste equivalente ao atual (cenário 2 do quickstart) |
| Estilo inline `cursor:pointer` conflitar | Não conflita — propriedade distinta (`cursor` vs `border`) |

## Complexity Tracking

> Sem violações da Constitution — seção vazia por design.
