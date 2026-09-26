# Data Model: Ajuste Responsivo da Tabela "Visão Geral do Patrimônio" (046)

**Sem entidades de dados novas ou alteradas.** Feature exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão ou payload muda (FR-015/FR-016/FR-017). Os dados exibidos (`Movement` + `Asset` + `User` via `DashboardService.get_stats` → `recent_movements` limit 8: timestamp, asset.tag, asset.name, movement_type.label, destination_custodian_name/destination_location_name, operator_name, term_code) e a rota `/` (`routes.py:281`, `view_dashboard`) permanecem intocados.

## Modelo de apresentação (única superfície afetada)

### Template `app/web/templates/dashboard.html` — tabela "Fluxo Recente de Movimentações" (7 colunas)

Larguras de partida (C-1; soma ≈ 1370px, coerente com 042 (1380), 043 (1330) e 044 (1230); a medir/refinar). Textuais = **linha garantida** (ellipsis + tooltip Bootstrap — clarificação); rígidas = nowrap com pisos de fonte real.

| Col | Coluna | Conteúdo atual | Largura de partida | Regras de layout previstas |
|---|---|---|---|---|
| c0 | Data | `td.text-muted.small.text-nowrap` — `%d/%m/%Y %H:%M` | ~135px | rígida (FR-003): nowrap já existente preservado; data+hora em uma linha |
| c1 | Tombamento | `span.tag-badge` (monoespaçada bold .78rem; ellipsis global embutido; `max-width:140px` ≤479.98px) | ~150px | rígida (FR-004): código completo em uma linha nas larguras alvo; **sem ellipsis novo** — regras globais preservadas |
| c2 | Equipamento | `a.fw-semibold` (link para `/assets/{id}`, `style="color:var(--c-text)"` inline) | ~330px | textual dominante (FR-005): linha garantida — span interno cortável + tooltip Bootstrap; link e cor inline preservados |
| c3 | Ação | `span.badge.badge-soft-primary` (.68rem inline) — `movement_type.label` | ~200px | rígida pelo conteúdo real (FR-006): badge íntegro, rótulo mais longo ("Entrada por Aquisição") em uma linha; sem regra global de badge |
| c4 | Destino | `td.small` — if/else: span `bi-person` + colaborador **ou** span `bi-geo-alt` + local/"Estoque" | ~330px | textual dominante (FR-007): **uma das maiores parcelas** (C-2) — span interno cortável + tooltip em AMBOS os ramos; ícones e fallback "Estoque" fora do span cortável |
| c5 | Operador | `td.text-muted.small` — `m.operator_name` | ~130px | textual (FR-008): linha garantida — span interno cortável + tooltip; suficiente sem monopolizar espaço (C-2) |
| c6 | Ações | `td.text-end.text-nowrap` — `{% if m.term_code %}` botão Termo (impressora) **condicional** + botão Ver Bem (chevron) | ~95px | mínima estável (FR-009): dimensionada pelo PAR (pior caso com termo); `text-nowrap` e alinhamento à direita existentes preservados |

Textuais (Equipamento+Destino+Operador) ≈ 790px de partida (maior bloco — SC-002); rígidas com folga ×1,25–1,30 (Plus Jakarta Sans; padding `.5rem .5rem` = 16px/coluna).

### Estrutura técnica prevista (mecanismo reusado das 036–044)

- `<style>` embutido no topo do `{% block content %}` com comentário "Feature 046" (sem citar nomes de controles — lição `b75ba99`) e classe de escopo própria (ex.: `.dash-table`) **aplicada somente à tabela de movimentações**.
- `table-layout: fixed; width: 100%; min-width: ~1370px` (único conjunto, sem media query de colunas — lição da 041) + `<colgroup>` com `<col class="cN">`.
- **Classe auxiliar de ellipsis** (ex.: `.dash-ellip`): `display:inline-block; max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; vertical-align:bottom` + `data-bs-toggle="tooltip" data-bs-placement="top"` — aplicada em **Equipamento** (dentro do link), **Destino** (nos dois ramos) e **Operador**.
- Ícones (`bi-person`, `bi-geo-alt`), fallback "Estoque" e links **fora dos spans cortáveis**; sem tooltip em span vazio.
- `.tag-badge` do Tombamento e `.badge-soft-primary` da Ação: **sem regra nova** — regras globais/inline existentes preservadas (R4).
- **Sem bloco de impressão** (R10 da 043 — tela não-relatório; nenhum `@media print` criado ou alterado).
- `table-responsive`, card, header ("Fluxo Recente de Movimentações" + botão "Ver Tudo") e estado vazio preservados (FR-017).

### O que NÃO é tocado (fronteira da superfície — mesmo template!)

| Elemento da mesma página | Motivo |
|---|---|
| 4 `card-kpi` (L29–103) | FR-017: fora do escopo |
| 4 cards de distribuição (barras, L104–171) | FR-017: fora do escopo |
| Card "Integridade do Patrimônio" (L172–211) | FR-017: fora do escopo |
| Header do card + botão "Ver Tudo" (L214–236) | FR-017: fora do escopo |
| **Tabela "Necessitam de atenção"** (L182–200 — Tag/Equipamento/Observação, `.table.table-sm`) | FR-012/FR-017: **sem classe nova, sem regra nova** — o seletor escopado não a alcança; medição do script deve provar identidade antes/depois (R5) |
| Estado vazio "Nenhuma movimentação recente" (L294–298) | FR-017: fora do escopo |
| `page-header` da tela | FR-017: fora do escopo |

### O que NÃO é tocado (sistema)

| Elemento | Motivo |
|---|---|
| `app/web/routes.py` (`view_dashboard`) | Nenhuma rota/contexto muda (FR-015) |
| `app/services/dashboard_service.py` (`get_stats`, `recent_movements` limit 8) | Nenhuma regra de negócio muda (FR-015) |
| `app/web/static/css/style.css` | Global/cache — proibido (R1/FR-012) |
| `app/web/templates/base.html`, `main.js`, service worker | Intocados (R1) |
| Telas das specs 036–045 | FR-017: nenhuma é afetada |
| Banco, models, schemas, permissões | N/A (FR-015) |
