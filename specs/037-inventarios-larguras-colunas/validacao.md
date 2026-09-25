# Registro de Validação — Feature 037 (Constituição XII / SC-007 / T010)

**Data**: 2026-09-25 · **Feature**: Ajuste Responsivo da Tabela "Inventário Patrimonial"

**Método**: idêntico ao da 036 — suíte pytest (regressão) + inspeção visual com **medição real** da página renderizada via TestClient com o CSS real do app embutido, DevTools (getBoundingClientRect/Range) e screenshots nas larguras/temas indicados.

**Dados de teste**: 3 inventários em estados variados (Encerrado c/ 6/6; Planejado 0/0; Em Andamento 3/6 com todos os badges de progresso), nomes de tamanhos variados, escopos institucionais longos, criadores distintos.

## Comparação antes/depois (V0 — seção 25 do pedido)

| Métrica (1440px) | **Antes** (auto layout) | **Depois** (fixed + colgroup) |
|---|---|---|
| Código | 145px | **156px** (código integral, sem truncamento) |
| Inventário | 323px (27%) | **347px (29%)** — dominante |
| Escopo | 397px (33%) | **300px (25%)** — ainda textual, cede excesso |
| Progresso | 135px | **192px** — badges respiram |
| Status | 124px | **120px** — compacta, badge em 1 linha |
| Ações | 76px | **84px** — mínima p/ botão |
| Aproveitamento do card | 99.8% | **99.8%** |
| Inventário+Escopo | 60% (mal distribuído: Escopo > Inventário) | **53%** com prioridade correta (C-2) |

O problema real do "antes" não era a tabela não ocupar a largura (99.8%), e sim a **distribuição errada**: Escopo (texto secundário) maior que Inventário (texto primário), Progresso espremido com badges encostados. A 037 redistribuiu por prioridade de conteúdo/função (C-2).

## Larguras finais adotadas (T003, refinadas em T005/T007 por medição — C-1)

| Coluna | Partida (data-model) | **Final** | Ajuste e motivo |
|---|---|---|---|
| Código | ~11% | **13%** | badge do código truncava com "…" em 11% (FR-003) — medição V2 |
| Inventário | ~30% | **29%** | dominante; nomes longos quebram graciosamente |
| Escopo | ~26% | **24%** | texto completo quebrando em 2 linhas; cede 1pp ao Status |
| Progresso | ~17% | **16%** | badges empilhados íntegros |
| Status | ~9% | **11%** | "Em Andamento" quebrava em 9–10% (FR-007) |
| Ações | ~7% | **7%** | mínima (1 botão-ícone) |

Ajustes estruturais: `min-width: 1100px` (badge de Status precisa de célula ≥124px em qualquer largura; abaixo disso rola confinado) e `padding-left/right: 8px` na célula Status (badge 92px border-box + padding 16px = célula 108px disponível de ~118px).

## Suíte de regressão (T002 baseline / T006 final / SC-006)

| Momento | Comando | Resultado |
|---|---|---|
| Baseline (antes) | `pytest tests/ -q` | **728 passed** |
| Focado (inventário + navbar) | `pytest tests/test_inventario.py tests/test_navbar.py -q` | **37 passed** |
| Final (depois) | `pytest tests/ -q` | **728 passed** — zero regressão |

## V1 — Aproveitamento horizontal (US1/AC-01) — ✅ PASS

- Desktop 1440px: tabela ocupa **99.8%** da largura do card (SC-001 ≥95% ✓); Inventário+Escopo = **53%** dominando (SC-002 indicativo ✓ — "mais da metade"); Ações mínima (84px); sem grandes vazios (SC-003/SC-005 sem desalinhamento/sobreposição — medido).

## V2 — Conteúdos íntegros (AC-10/FR-003..007) — ✅ PASS

- Código `INV-2026-0003`: **1 linha, sem truncamento** (após 11%→13%; medido por Range com tops distintos).
- "Em Andamento": **1 linha** em todas as larguras testadas (após 11% + padding 8px; varredura: badge precisa de 92px border-box).
- Escopos institucionais longos: texto completo em 2 linhas, sem truncamento.
- Progresso com todos os badges (✓/⚠/✕) + "3/6 conferidos": legível, dentro da coluna.
- Linha "Criado em … por …" íntegra em todas as linhas.

## V3 — Alinhamento e funcionalidade (AC-08/AC-11/contract §1–§2) — ✅ PASS

- Headers alinhados aos valores; Ações à direita; zero sobreposição de headers (medido em todas as larguras).
- Link do nome e botão "Abrir" (com tooltip) presentes e funcionais; filtros (busca + status) intocados; colgroup garante thead=tbody.

## V4 — Responsividade e temas (US2/AC-09/contract §3) — ✅ PASS

| Viewport | Resultado |
|---|---|
| 1440px (desktop 100%) | tudo em 1 linha; sem rolagem; 99.8% |
| 1152px (zoom ~125%) | íntegro; sem overflow |
| 1024px (notebook) | íntegro; sem rolagem (min-width 1100 ainda < container útil) |
| 700px (tablet) | rolagem **confinada** ao `table-responsive` (scrollbar visível); headers/código/status íntegros; botão acessível (32px) |
| 375px (celular) | idem tablet; botão acessível ao final da rolagem; zero overflow da página |
| 2880px (zoom ~50%→larga) | íntegro |
| Zoom 80%–200% | coberto pelas larguras equivalentes (clarificação 2026-09-25) |
| Tema claro + escuro | screenshots nos dois temas: badges/contraste íntegros (nenhuma cor nova introduzida) |

## V5 — Não-vazamento de escopo (FR-011/FR-014/contract §4–§5) — ✅ PASS

- `git diff --stat` final: **apenas** `app/web/templates/inventarios/list.html` (+39 linhas) — nenhum asset estático, nenhum `style.css`, nenhum `sw.js`, nenhum bump de cache.
- Todas as regras CSS novas escopadas em `.inv-lista-table` (+ `nth-child(5)` restrito à tabela); nenhuma regra global.
- Container da tela (page header, filtros, card) e estado vazio intocados; outras telas não afetadas (CSS embutido só existe nesta página).

## Decisões finas registradas (research R4/R6)

1. `nowrap` no `tag-badge` do código (código nunca quebra — FR-003); `white-space: normal` nos badges (Progresso empilha; Status quebra em fronteira de palavra quando inevitável).
2. `min-width: 1100px`: garante coluna Status ≥121px em qualquer viewport; abaixo disso, rolagem confinada ao `table-responsive` (contrato §3) — sem reduzir fontes (proibição da seção 15).
3. Padding lateral 8px exclusivo na célula Status (5ª coluna) — equilibra o badge de rótulo mais longo sem roubar espaço das colunas textuais.
4. Media query ≤768px para header compacto (herdada do mecanismo da 036), mantida como proteção.

## Documentação (T011 / Princípio XI)

- README e central de ajuda não descrevem larguras da listagem (verificado por busca) — **nada a atualizar**.

## Resultado

- **Todos os cenários V0–V5 PASS** · suíte 728/728 verde antes e depois · diff confinado a 1 arquivo.
- Feature 037 **concluída** conforme spec/plan/tasks; pendência zero conhecida.
