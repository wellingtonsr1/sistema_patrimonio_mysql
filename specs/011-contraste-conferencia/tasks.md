---
description: "Task list for feature 011 implementation"
---

# Tasks: Contraste das Opções de Resultado da Conferência

**Input**: Design documents from `/specs/011-contraste-conferencia/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅ (decisões R1–R5), data-model.md ✅ (N/A — sem dados), contracts/visual-contract.md ✅, quickstart.md ✅

**Tests**: 1 teste de renderização (guarda leve, R4) — escrito ANTES da implementação (TDD); validação de contraste é visual/manual (quickstart §3), pois a suíte não tem navegador.

**Organization**: Tasks agrupadas por user story (spec.md: US1 P1 contornos nos dois temas · US2 P2 estados preservados · US3 P3 zero colateral).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: arquivo distinto, sem dependência com task incompleta (nunca execução concorrente com a implementação que testa — lição 005)
- **[Story]**: user story da spec (US1/US2/US3)
- Caminhos exatos em todas as tasks

## Path Conventions

Projeto existente (FastAPI + Jinja2): código em `app/`, testes em `tests/`. Esta feature toca SOMENTE: `app/web/static/css/style.css`, `app/web/templates/inventarios/conferir.html`, `app/web/templates/inventarios/detail.html`, 1 teste novo. **Zero Python de aplicação, zero banco, zero rota, zero permissão** (plan §Constitution Check 12/12).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Contexto carregado e baseline de não-regressão registrada

- [x] T001 Ler os artefatos da feature (spec §US/FR/SC, plan §Technical Approach + riscos, research R1–R5 + fatos F1–F14, contracts/visual-contract.md §4 garantias, quickstart §3) e os 3 arquivos-alvo no estado atual: `app/web/static/css/style.css` (região de componentes, ex. L498–508), `app/web/templates/inventarios/conferir.html` (bloco das 4 opções a partir de L70), `app/web/templates/inventarios/detail.html` (bloco do modal a partir de L315)
- [x] T002 Executar baseline da suíte: `python -m pytest tests/ -q --tb=no` → registrar números exatos em Validation Results (patamar esperado: 310 passed / 1 failed — lockout defasado conhecido)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verificação dos fatos que sustentam as decisões R1/R2 — BLOCKS user stories

**⚠️ CRITICAL**: Nenhuma user story começa antes desta verificação em código real

- [x] T003 Verificar em código os fatos do research antes de editar (gate): (a) `--bs-border-color` NÃO é sobrescrito em `style.css` (F5 — grep zero); (b) `style.css` é carregado DEPOIS de `bootstrap.min.css` em `app/web/templates/base.html` (F11 — ordem de estilos); (c) tokens `--c-border` existem e alternam por tema (claro L63→`#C8C2C0`; `[data-theme="dark"]` L1023+→`#3A3335` em F8); (d) re-confirmação F13: `grep -rn "d-block border rounded" app/web/templates/` retorna SOMENTE os 2 templates do inventário (garantia US3); (e) `data-bs-theme` sincronizado com `data-theme` em base.html (F6 — escuro funciona hoje). Registrar evidências em Validation Results. Se qualquer fato divergir, PARAR e reportar antes de prosseguir

**Checkpoint**: Fundamentos confirmados — user stories podem começar

---

## Phase 3: User Story 1 - Contornos perceptíveis nos dois temas (Priority: P1) 🎯 MVP

**Goal**: As 4 opções do "Resultado da conferência" ganham borda com contraste no modo claro (via token `--c-border`) mantendo o escuro — nas duas telas que renderizam o campo

**Independent Test**: Abrir a conferência (página e modal) nos 2 temas → contornos perceptíveis em todos os casos; suíte verde

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation** (a classe `result-option` ainda não existe no markup)

- [x] T004 [P] [US1] Criar teste de renderização `tests/test_conferencia_visual.py`: com fixtures `client`/`db_session` existentes, criar inventário + item (padrão de `tests/test_inventario.py`, ex. `test_asset_detail_offers_inventory_conference`) e renderizar a página de conferência (`GET /inventarios/{inv_id}/conferir/{asset_id}` — parâmetro real é o id do bem); asserir que o HTML contém **4 ocorrências** de `result-option` e os 4 valores intactos (`ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`); asserir também `cursor:pointer` preservado nos labels. **Obrigatório no mesmo arquivo**: asserção análoga para o modal de `app/web/templates/inventarios/detail.html` (GET `/inventarios/{id}` contém os 4 `result-option` — prova simétrica do FR-008). Executar e CONFIRMAR vermelho (classe ausente)

### Implementation for User Story 1

- [x] T005 [US1] Adicionar a classe do componente em `app/web/static/css/style.css` (região de componentes, junto a `.badge-soft-*`/`.tag-badge`): `.result-option { border: 1px solid var(--c-border) !important; }` com comentário "Feature 011 — opções de 'Resultado da conferência': borda com contraste nos dois temas via token existente; não altera a utilitária .border global" (R1/R2; `!important` necessário pois `.border` do Bootstrap também é `!important` — plan §Riscos). NADA além deste bloco no arquivo
- [x] T006 [P] [US1] Acrescentar `result-option` ao atributo `class` dos 4 `<label>` do bloco "Resultado da conferência" em `app/web/templates/inventarios/conferir.html` (L70+): `class="d-block border rounded p-2 result-option"` — nenhuma outra alteração no arquivo (R3)
- [x] T007 [P] [US1] Acrescentar `result-option` aos mesmos 4 `<label>` no modal em `app/web/templates/inventarios/detail.html` (L315+) — mesmo critério de T006 (FR-008: tratamento idêntico nas duas telas)
- [x] T008 [US1] Executar `python -m pytest tests/test_conferencia_visual.py -q` → verde; e `python -m pytest tests/test_inventario.py -q` → verde (nenhuma regressão nas regras de conferência)

**Checkpoint**: US1 completa — contornos corrigidos nas 2 telas; único toque de CSS do projeto

---

## Phase 4: User Story 2 - Estados de seleção, hover e foco preservados (Priority: P2)

**Goal**: Provar que a correção não afeta seleção, foco, hover nem a regra "borda não é o único indicador" (FR-005/FR-011)

**Independent Test**: Inspeção da regra adicionada + renderização — nenhum estado recebe/merece regra nova

- [x] T009 [US2] Revisar a regra de T005 e o HTML renderizado: (a) a classe `.result-option` define SOMENTE propriedades de borda — nenhuma regra sobre `input`, `:checked`, `:focus`, `:hover`, `cursor` ou `pointer-events` foi adicionada (estados intocados); (b) `cursor:pointer` inline dos labels continua no HTML renderizado (asserção do T004); (c) o `input.form-check-input` (indicador primário de seleção, FR-011) permanece inalterado no markup; (d) confirmar nos templates que nenhuma classe de estado foi removida (`git diff` dos templates mostra APENAS o acréscimo de `result-option` nas linhas de class). Registrar evidências em Validation Results

**Checkpoint**: US2 completa — estados comprovadamente intocados

---

## Phase 5: User Story 3 - Ausência de efeitos colaterais visuais (Priority: P3)

**Goal**: Provar que nenhum componente fora das 8 opções mudou (US3/SC-004)

**Independent Test**: git diff restrito ao bloco novo do CSS + varredura de templates + suíte verde

- [x] T010 [US3] Verificação de colaterais: (a) `git diff app/web/static/css/style.css` contém SOMENTE o bloco `.result-option` (nenhuma regra global `.border`, `--bs-border-color` ou outra alterada); (b) re-executar `grep -rn "d-block border rounded" app/web/templates/` → somente os 2 templates da feature (ambos corrigidos); (c) varredura rápida: nenhuma OUTRA regra de `style.css` referencia `result-option` (classe usada apenas pelo componente); (d) `git status --porcelain` sem arquivos fora do escopo. Registrar em Validation Results

**Checkpoint**: US3 completa — escopo visual provado

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Suíte final, validação manual e fechamento

- [x] T011 Executar a suíte completa: `python -m pytest tests/ -q --tb=no` → patamar baseline + 1 (novo teste), nenhum failure novo além do lockout conhecido (registrar números exatos em Validation Results)
- [ ] T012 Validação manual pelo operador conforme quickstart.md §3 (cenários 3.1–3.10: contornos no claro/escuro nas 2 telas, troca de tema em runtime, seleção/hover/foco, item já conferido, varredura de colaterais, registro real de conferência) — registrar resultado e data em Validation Results
- [x] T013 Fechamento: Constitution checklist do plan (12/12) confirmado; `git status --porcelain` com escopo exato (`style.css`, `conferir.html`, `detail.html`, `tests/test_conferencia_visual.py`, artefatos `specs/011.../` — nada além; ZERO Python/banco); síntese SC-001..SC-006 em Validation Results. Nota: **sem atualização de documentação** (R5 — nenhum comportamento documentado muda)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: sem dependências — imediato
- **Foundational (T003)**: depende do Setup — BLOCKS todas as stories (gate de fatos)
- **US1 (T004–T008)**: depende de T003; T004 (teste vermelho) ANTES de T005–T007 (implementação); T005 (CSS) antes de T006/T007 fazem sentido lógico, porém ambos os templates independem do CSS para receber a classe — a ordem estrita é T004 → T005 → T006/T007 → T008
- **US2 (T009)**: depende de T008 (revisa o que a US1 produziu)
- **US3 (T010)**: depende de T008 (verifica o diff consolidado); independente de T009 no conteúdo, mas executa após
- **Polish (T011–T013)**: dependem de todas as stories; T012 (manual) após T011

### User Story Dependencies

- **US1 (P1)**: start após Foundational — nenhuma dependência de outra story
- **US2 (P2)**: inspeção sobre o resultado da US1 (mesma mudança de código; validação distinta)
- **US3 (P3)**: verificação sobre o mesmo diff — não altera código

### Within Each User Story

- Testes escritos e validados vermelhos ANTES da implementação correspondente (nunca em paralelo com ela — lição da 005)
- CSS antes dos templates (a classe precisa existir para o efeito; os templates só referenciam)

### Parallel Opportunities

- `[P]` indica apenas **independência de arquivo** — NUNCA execução concorrente entre um teste e a implementação que ele valida (T004 é vermelho antes de T005–T007)
- T006 e T007 são arquivos distintos e independentes entre si (após T005)
- Nenhuma outra task é paralelizável: todas as stories tocam o mesmo par CSS/templates e o fluxo é de verificação encadeada

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003 — gate de fatos)
3. Complete Phase 3: US1 (T004–T008)
4. **STOP and VALIDATE**: contornos visíveis nos 2 temas (quickstart 3.1–3.3) + suíte verde
5. As stories 2 e 3 são verificações — concluí-las na mesma passada é barato

### Incremental Delivery

- US1 entrega o valor (problema relatado resolvido nas 2 telas)
- US2/US3 são garantias de não-regressão (inspeção + varredura) — concluídas imediatamente após US1

---

## Notes

- Feature exclusivamente visual: **nenhum arquivo Python da aplicação é alterado** (contrato §4.1)
- Zero DDL, zero rota, zero permissão, zero docs (R5)
- A validação do contraste é manual (quickstart §3) — a suíte guarda a não-regressão (T004/T008/T011)
- Commit após cada grupo lógico, se desejado; parar nos checkpoints

---

## Validation Results

> Preenchido durante a implementação (T002, T003, T004, T008, T009, T010, T011, T012, T013). Não marcar antecipadamente.

### Baseline (T002)

- 2026-09-17: **310 passed / 1 failed** (lockout defasado pré-existente). Escopo do repositório limpo antes de editar (só artefatos da 011).

### Fatos verificados (T003)

- (a) `--bs-border-*`: **0 ocorrências** em `style.css` (F5 ✓ — token do Bootstrap não sobrescrito).
- (b) Ordem de carregamento em `base.html`: `bootstrap.min.css` L24 → `style.css` L28 (F11 ✓ — CSS do projeto vence empates).
- (c) Tokens: `--c-border: var(--color-border)` L63 → `#C8C2C0` (L31); dark L1086 → `--dark-border: #3A3335` (L1037) (F8 ✓). **Descoberta registrada**: existe override de `--c-border: #E3DEDC` em `@media print` (L1481) — afeta apenas impressão, irrelevante para a validação em tela.
- (d) F13 ✓: `d-block border rounded` existe **somente** nos 2 templates do inventário.
- (e) F6 ✓: `data-theme` + `data-bs-theme` sincronizados no `<html>` (base.html L2/L13).

### TDD vermelho (T004)

- 2026-09-17: **2 failed** (`test_conference_page_renders_result_option`, `test_inventory_detail_modal_renders_result_option`) — classe ausente no markup, vermelho confirmado antes da implementação.

### Execução US1 (T008)

- 2026-09-17: `test_conferencia_visual.py` 2/2 + `test_inventario.py` 21/21 verdes — página dedicada e modal com 4× `result-option`, valores e cursor intactos.

### Estados preservados (T009)

- (a) `.result-option` define **somente** `border` (L518) — nenhuma regra sobre input/:checked/:focus/:hover/cursor.
- (b) `cursor:pointer` inline: 4 por template (8 no total) preservados.
- (c) `form-check-input` radios: 4 por template intactos (indicador primário de seleção — FR-011).
- (d) `git diff` dos 2 templates: cada linha alterada é par `-label class="d-block border rounded p-2"` → `+... p-2 result-option"` (4 pares em cada) — nenhuma classe de estado removida.

### Colaterais (T010)

- (a) `git diff style.css`: **apenas o bloco comentado + a regra `.result-option`** — nenhuma regra global `.border`/`--bs-border-color` tocada.
- (b) Padrão de classes segue restrito aos 2 templates da feature.
- (c) `result-option` referenciado só em: style.css, conferir.html, detail.html, teste novo.
- (d) `git status --porcelain`: exatamente os 3 arquivos de código do escopo + teste novo + artefatos da spec.

### Suíte completa (T011)

- 2026-09-17: **312 passed / 1 failed** (310 baseline + 2 novos; mesma falha pré-existente de lockout). Zero regressão.

### Validação manual (T012)

- (pendente — a executar pelo operador conforme quickstart §3; cenários 3.1–3.10; servidor precisa de restart para o CSS novo se houver cache — versão em base.html `?v=` não foi alterada de propósito: o token resolve no mesmo arquivo)

### Fechamento (T013)

- 2026-09-17. Constitution Check 12/12 ✓ (plan). Escopo por `git status`: `app/web/static/css/style.css`, `app/web/templates/inventarios/conferir.html`, `app/web/templates/inventarios/detail.html`, `tests/test_conferencia_visual.py` (novo), artefatos `specs/011.../` — **zero Python de aplicação, zero banco, zero rota, zero permissão** ✓.
- SC-001 contornos no claro ✓ (implementado, validação visual T012) · SC-002 escuro sem regressão ✓ (token dark intacto; T012) · SC-003 seleção/hover/foco preservados ✓ (T009) · SC-004 zero colateral ✓ (T010) · SC-005 conteúdo/valores intactos ✓ (T004/T008) · SC-006 suíte no patamar ✓ (T011).
- R5: sem atualização de documentação (nenhum comportamento documentado muda).
