---

description: "Task list for feature implementation"
---

# Tasks: Conferência Offline — responsividade e padronização visual (035)

**Input**: Design documents from `/specs/035-conferencia-offline-layout/`

**Prerequisites**: plan.md (required), spec.md (required), research.md (D1–D7), data-model.md, contracts/ui-shell-offline-contract.md, quickstart.md

**Tests**: Nenhum teste automatizado novo ou alterado (decisões D6/D7 do research — validação visual por checklist + suíte pytest existente como rede de não-regressão). Constitution VIII é atendida pela suíte verde (FR-015/SC-005).

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: `app/web/templates/` + `app/web/static/` + `tests/` na raiz.

**Restrição estrutural**: praticamente todas as alterações de implementação acontecem em **um único arquivo** (`app/web/templates/inventarios/offline.html`) — tarefas de stories diferentes NÃO são paralelizáveis entre si e devem executar em ordem, com validação após cada fase (nota: edições de template às vezes não persistem — sempre revalidar com grep após cada edição).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmação de insumos — nenhuma infraestrutura nova (mudança de apresentação; plan.md gate 12/12).

- [x] T001 Ler/confirmar os pontos exatos de alteração sem alterar nada: `app/web/templates/inventarios/offline.html` (bloco `<style>` L43-141: `.offbar*`, media queries; `<header class="offbar">` L143-160; `<main>` L162; card de pesquisa/tabela L275-305) e o padrão de referência `app/web/static/css/style.css` (`.navbar-brand` L197-223 — marca empilhada, logo 32px); confirmar `app/web/static/js/sw.js` `CACHE_VERSION` atual (`inventario-offline-v24`)
- [x] T002 Confirmar `.specify/feature.json` apontando para `specs/035-conferencia-offline-layout` (já gravado no specify — apenas verificar)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhuma fundação nova é necessária — sem rota, sem model, sem banco, sem permissão, sem JS novo.

> Esta fase fica intencionalmente vazia: o plan.md (gate PASS 12/12) não exige infraestrutura.
> User stories podem iniciar imediatamente após o Setup.

---

## Phase 3: User Story 1 - Identificação da shell: nome abaixo da logo (Priority: P1) 🎯 MVP

**Goal**: Barra superior com marca empilhada (logo acima, "SisPatrimônio Pro" abaixo), espelhando `.navbar-brand` do `style.css`; cabeçalho em linha única ≥768px e com código+status na 2ª linha ≤767px (C-3/D4).

**Independent Test**: abrir a shell em desktop e em celular e observar a barra superior — logo empilhada com o nome abaixo, código e indicador íntegros em ambas as larguras. Não requer pacote nem coleta.

### Implementation for User Story 1

- [x] T003 [US1] Reorganizar o bloco de marca em `app/web/templates/inventarios/offline.html`: `.offbar-brand` passa a empilhar logo + "SisPatrimônio PRO" em coluna (`flex-direction: column`, `row-gap` ≈ `.3rem`, centralizados — espelhando `.navbar-brand` L197-223 do `style.css`, D1); logo mantém 32px (28px na media query ≤767.98px); mover o título para dentro do bloco de marca e deixar código (`{{ inv.code }}`) + indicador `#offlineModeIndicator` como bloco de informação ao lado (linha única ≥768px); revalidar com grep que `.offbar-brand`/`.offbar-title` foram persistidos
- [x] T004 [US1] Implementar o comportamento mobile do cabeçalho (C-3/D4) em `app/web/templates/inventarios/offline.html`: em ≤767.98px o código do inventário e o indicador de conexão quebram para uma segunda linha do próprio cabeçalho (flex-wrap com ordem explícita), sem esconder nenhum elemento; verificar em 320px que logo/nome não são cortados e `#darkToggle` permanece acessível; revalidar com grep

**Checkpoint**: US1 funcional — identidade visual da shell idêntica à navbar principal; validável com quickstart V1.

---

## Phase 4: User Story 2 - Largura e container padronizados (Priority: P1)

**Goal**: Área principal com o mesmo container/largura das demais páginas (90% centralizado ≥768px; 100% + padding reduzido ≤767px — C-1/D2); nenhum bloco com largura independente.

**Independent Test**: comparar a shell com a listagem de inventários na mesma janela — bordas de conteúdo coincidem; nenhum bloco ultrapassa o container.

### Implementation for User Story 2

- [x] T005 [US2] Alinhar o container e os espaçamentos em `app/web/templates/inventarios/offline.html`: `<main>` passa a `container-fluid py-4 px-lg-5 mx-auto` com `max-width: 90%` (idêntico ao `base.html` L314) nas regras ≥768px (remover a diferença 92%/`px-lg-4`); nas media queries ≤767.98px manter `max-width: 100%` + padding lateral `.75rem` (comportamento mobile atual — C-1); **FR-010**: padronizar os espaçamentos verticais/horizontais entre cabeçalho → pesquisa → tabela → conteúdo usando as classes Bootstrap já adotadas (`mb-4`/`mb-3`, `gap-2`, `py-4`), eliminando espaços excessivos ou elementos colados sem criar margens customizadas novas; revalidar com grep
- [x] T006 [US2] Auditar blocos com largura independente em `app/web/templates/inventarios/offline.html`: conferir que alerta, `#offlinePainel`, card de sincronização, card de pesquisa/tabela e `#qrVideo` (`max-width: 420px` — mantém, é dentro do container) herdam o container sem `width` fixo próprio; nenhuma largura nova específica da shell (FR-009); registrar exceções encontradas (se houver) no relatório de validação em vez de alterar arquivos fora do escopo

**Checkpoint**: US2 funcional — largura padronizada; validável com quickstart V2.

---

## Phase 5: User Story 3 - Pesquisa, "Ler QR" e tabela alinhados (Priority: P1)

**Goal**: Linha [pesquisa | Ler QR] e tabela ocupando a mesma largura do card; cabeçalhos alinhados aos dados; quebra de texto controlada (D3/C-2).

**Independent Test**: inspecionar as bordas do card de pesquisa+tabela — linha de pesquisa coincide com a largura da tabela; colunas alinham verticalmente.

### Implementation for User Story 3

- [x] T007 [US3] Ajustar a linha de pesquisa e a tabela em `app/web/templates/inventarios/offline.html`: manter `#buscaItem` com `flex: 1 1 auto; min-width: 0` e `#btnLerQR` com `flex-shrink-0` + estilo de contorno (`btn-outline-primary` — C-2, sem mudança de hierarquia); garantir que o bloco `d-flex` da pesquisa e o `table-responsive` ocupem 100% da largura útil do card (mesmas bordas); adicionar quebra controlada de texto nas células (ex.: `word-break`/`overflow-wrap` em descrição/local) sem posicionar colunas; `table-responsive` permanece como mecanismo de rolagem restrita; revalidar com grep

**Checkpoint**: US3 funcional — alinhamento fino pesquisa/tabela; validável com quickstart V3.

---

## Phase 6: User Story 4 - Responsividade em telas pequenas (Priority: P2)

**Goal**: Em 320–430px: nenhuma rolagem horizontal da página; rolagem restrita à tabela; "Ler QR" nunca cortado (reorganização vertical permitida).

**Independent Test**: abrir a shell em viewport 320px — página sem transbordo; tabela rola dentro do próprio bloco.

### Implementation for User Story 4

- [x] T008 [US4] Revisar/ajustar as media queries de telas estreitas em `app/web/templates/inventarios/offline.html`: preservar `body { overflow-x: hidden; }` e `table-responsive`; em ≤575.98px permitir que a linha pesquisa+"Ler QR" reorganize verticalmente (`flex-wrap: wrap` com o input ocupando a linha inteira quando necessário) garantindo o botão integralmente visível (FR-008); conferir contadores 2×2, modal (margem `.5rem`) e botões full-width existentes; nenhuma regra com `position: absolute`/largura fixa nova (FR-009); revalidar com grep

**Checkpoint**: US4 funcional — mobile íntegro; validável com quickstart V4 (320px primeiro).

---

## Phase 7: User Story 5 - Coerência de tema e funcionamento preservado (Priority: P2)

**Goal**: Claro/escuro funcionando por variáveis existentes; contrato DOM (§1 do contract) 100% intacto; nenhum comportamento funcional alterado.

**Independent Test**: alternar tema e executar o ciclo coletar → sincronizar: contraste correto nos dois temas e comportamento idêntico; suíte verde.

### Implementation for User Story 5

- [x] T009 [US5] Verificação de tema e contrato DOM em `app/web/templates/inventarios/offline.html`: nenhuma cor literal nova introduzida (todas as cores continuam via variáveis `--color-primary`, `--c-text` etc. ou os rgba brancos já usados sobre fundo primário); conferir que TODOS os IDs/names/classes do contrato §1 (`contracts/ui-shell-offline-contract.md` — `buscaItem`, `btnLerQR`, `itensBody`, `avisoPacote`, `semPacoteDica`, `btnSincronizar`, `btnLimpar`, `pendenciasBadge`, `syncStatusLinha`, `cnt*`, `offlineModeIndicator`, `darkToggle`/`darkIcon`, `modalColetaOffline` e campos `m*`, `m_result`, `qrVideo`, classes `offbar-status st-*`, `badge-soft-*`, `tag-badge`, `result-option`, `painel-item`) existem com a mesma função; corrigir qualquer regressão introduzida por T003–T008

**Checkpoint**: US5 funcional — tema e DOM íntegros; validável com quickstart V4.3–V4.4 + V5.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Propagação do cache, não-regressão e validação final (Constitution XI/XII).

- [x] T010 Atualizar `CACHE_VERSION` em `app/web/static/js/sw.js` de `inventario-offline-v24` para `inventario-offline-v25` (D5 — única alteração do SW; `PRECACHE_URLS` e handlers intocados); se T006/T007 resultarem em alteração em `app/web/static/css/style.css` (não previsto), bump adicional da querystring `?v=` na referência do template
- [x] T011 Rodar a suíte completa `.venv/bin/python -m pytest tests/ -q` e deixar 100% verde (FR-015/SC-005; nenhum teste alterado)
- [x] T012 Rodar o quickstart.md completo (V1–V5 + roteiro visual 320→1920px, claro/escuro, retrato/paisagem) e registrar o resultado em `specs/035-conferencia-offline-layout/validacao.md` (padrão da 034 — Constitution XII)
- [x] T013 Verificação final de escopo: `git status` deve mostrar apenas `app/web/templates/inventarios/offline.html`, `app/web/static/js/sw.js` e os artefatos da spec (SC-006/FR-016); revisar README (seção 3.1 coleta offline) — nenhuma atualização esperada, pois comportamento/funcionalidade não mudam (Princípio XI; alterar apenas se alguma afirmação visual do README ficar imprecisa)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — inicia imediatamente
- **Foundational (Phase 2)**: vazia por design — user stories iniciam após Setup
- **User Stories (Phases 3–7)**: TODAS tocam o mesmo arquivo → executam **em ordem** (US1 → US2 → US3 → US4 → US5), cada checkpoint validando a anterior
- **Polish (Phase 8)**: depende de todas as stories completas (T010 só faz sentido após o template final)

### User Story Dependencies

- **US1 (P1)**: após Setup — sem dependência de outras stories
- **US2 (P1)**: independente de US1 no conteúdo, mas mesmo arquivo → sequencial
- **US3 (P1)**: usa o container corrigido por US2 como referência de largura
- **US4 (P2)**: ajusta media queries criadas/alteradas em US1–US3
- **US5 (P2)**: verificação transversal de tudo que veio antes (tema + contrato DOM)

### Parallel Opportunities

- T001 e T002 (Setup) podem executar em paralelo (arquivos distintos)
- T010 (sw.js) é arquivo distinto, mas **logicamente dependente** do template final — não paralelizar com as stories
- Dentro das stories não há paralelismo aproveitável (arquivo único)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: US1 (identidade visual — a correção que motivou a feature)
3. **STOP and VALIDATE**: quickstart V1 em desktop + 320px
4. Deploy/demo se pronto

### Incremental Delivery

1. Setup → US1 (header) → validar V1
2. US2 (container) + US3 (grid pesquisa/tabela) → validar V2–V3
3. US4 (telas pequenas) → validar V4 em 320px
4. US5 (tema/DOM) → validar V5 + ciclo de coleta
5. Polish: bump do SW, suíte verde, validação registrada, escopo

### Notes

- Validação após CADA edição de template com grep (histórico: edições de template podem não persistir)
- Decisões vinculantes: C-1 (90% ≥768px / 100% mobile), C-2 (Ler QR mantém contorno), C-3 (header quebra ≤767px); D1–D7 no research.md
- Contrato DOM §1 (`contracts/ui-shell-offline-contract.md`) é intocável — qualquer conflito entre layout e contrato resolve-se a favor do contrato
- Nenhuma regra de negócio, rota, permissão, banco ou JS funcional é alterado (FR-012/FR-013); único arquivo fora do template é `sw.js` (só versão de cache — T010)
