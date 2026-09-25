# Data Model: Ajuste Responsivo da Tabela "Relatório Contábil-Físico do Patrimônio" (041)

**Sem entidades de dados novas ou alteradas.** Feature exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão, cálculo contábil ou payload muda (FR-014/FR-015). Os dados exibidos (`Asset`, `Category`, `Location`, `Custodian`, `deprec_info`) e a rota `/reports/inventory` (`routes.py:1517`) permanecem intocados.

## Modelo de apresentação (única superfície afetada)

### Template `app/web/templates/reports/inventory.html` — tabela do relatório (10 colunas)

| Coluna | Conteúdo atual | Largura de partida (a medir/refinar — C-1) | Regras de layout previstas |
|---|---|---|---|
| **Tombamento** | `td.font-monospace.fw-bold` — código patrimonial | ~8% | intermediária (FR-003): código íntegro, sem quebra do código (nowrap na célula) |
| **Descrição** | `<strong>{{ a.name }}</strong>` + `div` condicional `S/N: {{ a.serial_number }}` (`.text-muted`, ~.72rem) quando houver `serial_number` | ~16% | maior prioridade (FR-004): **texto completo** (sem clamp — clarificação); estrutura de blocos do nome + S/N preservada |
| **Categoria** | `span.badge.badge-soft-gray` (~.68rem) — `a.category.label` | ~8% | intermediária (FR-005): badge íntegro; sem espaço excessivo |
| **Status** | `span.status-pill.status-pill-{{ a.status.value }}` — `a.status.label` | ~8% | compacta (FR-006): pill íntegro, comportamento visual atual |
| **Localização** | texto — `a.location.name` ou fallback **"Estoque Geral"** | ~12% | maior prioridade (FR-007): **texto completo** (clarificação) |
| **Responsável** | texto — `a.custodian.name` ou fallback **"Livre"** | ~11% | maior prioridade (FR-008): **texto completo** (clarificação) |
| **Data Compra** | `dd/mm/YYYY` (`a.purchase_date`) ou **"-"** | ~7% | compacta (FR-009): data sem quebra (nowrap na célula) |
| **Valor Aquisição** | `td.text-end.small` — `R$ {{ ... }}` formatado pt-BR | ~10% | compacta (FR-010): valor íntegro sem quebra; `text-end` preservado |
| **Depreciação** | `td.text-end.small` — `-{{ percent }}%` em `var(--red)` | ~9% | compacta (FR-010): formato `-XX%` e cor preservados |
| **Valor Atual** | `td.text-end.small.fw-bold` — `R$ {{ ... }}` em `var(--green)` | ~11% | compacta (FR-010): negrito e cor preservados |

Textuais (Descrição+Localização+Responsável) ≈ 39% de partida; as 5 compactas + intermediárias em px absorvem o resto no desktop real — a medição V0 calibra para as textuais dominarem o espaço variável (SC-002).

### Estrutura técnica prevista (mecanismo reusado das 036–040 — implementação mede e refina)

- `<style>` embutido no topo do `{% block content %}` com classe de escopo própria (ex.: `.invrep-table`) — nenhuma regra global, nenhuma outra tabela afetada.
- `table-layout: fixed; width: 100%; min-width: ~1480px` (a medir) + `<colgroup>` com `<col class="cN">` (larguras em classes para media query).
- Quebras: `break-word` nas células; **sem clamp/ellipsis nas textuais** (texto completo — clarificação); `nowrap` apenas nas células compactas (Tombamento/Data/monetárias).
- Compactas/intermediárias em **px com folga** para a Plus Jakarta Sans (lição da 039); textuais em % dividindo o restante.
- `table-responsive`, `card p-4 report-print` e cabeçalho interno do relatório **preservados** (FR-011; âncora de impressão fixada por `test_report_print_smoke.py`).
- Media query ≤768px com min-width reduzido, se a medição mostrar sobreposição (padrão 036–040).
- Regra de segurança de impressão escopada no mesmo `<style>` (`@media print` para a classe da 041) — R10: o papel nunca herda fixed/min-width/nowrap da tela.

### O que NÃO é tocado (fronteira da superfície)

| Elemento da mesma página | Motivo |
|---|---|
| `page-header no-print` com "Baixar CSV" (condicional a `relatorios.exportar`) e "Imprimir" | FR-011/FR-014: fora do escopo (comentários novos não citam esses nomes — lição `b75ba99`) |
| Cabeçalho interno do relatório (empresa + "Relatório de Inventário Físico e Contábil • ano") e `border-bottom` | FR-011: fora do escopo |
| Container global `base.html` (`container-fluid`, `max-width:90%`) | FR-011: não alterado |
| Bloco `@media print` C1–C10 em `style.css` (**compartilhado com os outros 2 relatórios**) | FR-013/R10: nenhuma regra editada |
| Exportações CSV/Excel/PDF (`/api/v1/reports/inventory/*`) | FR-014: intocadas |
| Tabelas da 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações), 040 (custodiantes) e demais telas | FR-016 |
