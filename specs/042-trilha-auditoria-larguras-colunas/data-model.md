# Data Model: Ajuste Responsivo da Tabela "Trilha de Auditoria & Fluxo" (042)

**Sem entidades de dados novas ou alteradas.** Feature exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão, payload ou registro de auditoria muda (FR-017/FR-018). Os dados exibidos (`Movement` + `Asset` relacionados, `movement_type.label`, `new_status.label`, `localtime`) e a rota `/reports/movements` (`routes.py:1578`) permanecem intocados.

## Modelo de apresentação (única superfície afetada)

### Template `app/web/templates/reports/movements_report.html` — tabela da trilha (10 colunas)

Larguras de partida (C-1; soma ≈ 1340px, coerente com a 041; a medir/refinar). Textuais = **linha garantida** (nowrap + ellipsis + tooltip Bootstrap — clarificação); rígidas = nowrap com pisos de fonte real.

| Col | Coluna | Conteúdo atual | Largura de partida | Regras de layout previstas |
|---|---|---|---|---|
| c1 | Data / Hora | `td.text-nowrap` — `dd/mm/YYYY HH:MM` (localtime) | ~130px | compacta (FR-003): nowrap já existente preservado; "24/09/2026 12:20" ≈ 115–125px reais |
| c2 | Tombamento | `td.font-monospace.fw-bold` — `m.asset.tag` | ~110px | compacta (FR-004): nowrap escopado; código mono íntegro |
| c3 | Equipamento | texto puro — `m.asset.name` | ~150px | textual (FR-005): **linha garantida** — nowrap + hidden + ellipsis + tooltip Bootstrap |
| c4 | Tipo | `span.badge.badge-soft-primary` (~.68rem) — `m.movement_type.label` | ~150px | compacta (FR-006): badge íntegro ("Entrada por Aquisição" ≈ 135px reais); nowrap escopado |
| c5 | Origem | local + `<br>` condicional com custodião (`span.text-muted`) | ~145px | textual (FR-007): **cada segmento em linha garantida** (span ellipsis próprio + tooltip); estrutura de 2 linhas intencional preservada; fallback "-" |
| c6 | Destino | local `<strong>` (`var(--c-primary-text)`) + `<br>` condicional custodião | ~145px | textual (FR-008): idem Origem; cor/strong preservados |
| c7 | Status | `span.status-pill.status-pill-{{ m.new_status.value }}` | ~125px | compacta (FR-009): pill íntegro ("Em Manutenção" ≈ 97–126px reais); nowrap |
| c8 | Motivo | `td.truncate-2` com `max-width:200px` inline, **sem tooltip** | ~170px | textual (FR-010): **substituir truncate-2/200px** por linha garantida (nowrap + ellipsis + tooltip Bootstrap); maior textual |
| c9 | Operador | `td.small.text-muted` — `m.operator_name` | ~130px | textual/intermediária (FR-011): linha garantida (ellipsis + tooltip) |
| c10 | Termo | link `font-monospace` condicional a `m.term_code` → `/movements/{id}/term` (target `_blank`); fallback "-" | ~110px | compacta (FR-012): nowrap; link mono íntegro ("TR-2026-0439" ≈ 94px reais); text-center preservado |

Textuais (Equipamento+Origem+Destino+Motivo) ≈ 610px de partida (maior bloco); rígidas com folga ×1,25–1,30 (Plus Jakarta Sans; padding real `.5rem .5rem` = 16px/coluna).

### Estrutura técnica prevista (mecanismo reusado das 036–041 + novidades da 042)

- `<style>` embutido no topo do `{% block content %}` com comentário "Feature 042" (sem citar controles do header — lição `b75ba99`) e classe de escopo própria (ex.: `.movrep-table` — distinta de `.mov-lista-table` da 039).
- `table-layout: fixed; width: 100%; min-width: ~1340px` (único conjunto, sem media query de colunas — lição da 041) + `<colgroup>` com `<col class="cN">`.
- **Classe auxiliar de ellipsis** (ex.: `.movrep-ellip`): `white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;` — aplicada em elemento interno da célula (ou na própria `td`) com `title` + `data-bs-toggle="tooltip" data-bs-placement="top"` (tooltips auto-inicializados em `base.html:329–333` e `main.js`).
- `nowrap` direto nas células rígidas (Data/Hora já tem `text-nowrap` global; demais via classe escopada).
- **Motivo**: remover `truncate-2` + `max-width:200px` inline do `<td>` (FR-010).
- Regra de segurança de impressão escopada no mesmo `<style>` (R10): neutraliza fixed/min-width/nowrap/col **e os spans `.movrep-ellip`** no papel (o C7 global só atinge `td/th`).
- `table-responsive`, `card p-4 report-print` e cabeçalho interno do relatório preservados (FR-014; âncora fixada por `test_report_print_smoke.py`).

### O que NÃO é tocado (fronteira da superfície)

| Elemento da mesma página | Motivo |
|---|---|
| `page-header no-print` com "Baixar CSV" (condicional a `relatorios.exportar`) e "Imprimir" | FR-014/FR-017: fora do escopo (comentários novos não citam esses nomes — lição `b75ba99`) |
| Cabeçalho interno do relatório (empresa + "Trilha de Auditoria Patrimonial • N registros") | FR-014: fora do escopo |
| Container global `base.html` (`container-fluid`, `max-width:90%`) | FR-014: não alterado |
| Bloco `@media print` C1–C10 em `style.css` (**compartilhado com os outros 2 relatórios**) | FR-016/R10: nenhuma regra editada |
| Condições Jinja dos dados (`{% if m.origin_custodian_name %}`, `{% if m.term_code %}`, fallbacks "-") | FR-017/FR-018: lógica de dados intocada |
| Exportação CSV (`/api/v1/reports/movements/csv`) | FR-017: intocada |
| Listagem de Movimentações (`movements/list.html`, 039 — `.mov-lista-table`) e demais telas 036–041 | FR-019 |
