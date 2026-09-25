# Data Model: Ajuste Responsivo da Tabela "Inventário Patrimonial" (037)

**Sem entidades de dados novas ou alteradas.** Feature exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão ou payload muda (FR-012/FR-013).

## Modelo de apresentação (única superfície afetada)

### Template `app/web/templates/inventarios/list.html` — tabela de listagem (linhas ~51–97)

| Coluna | Conteúdo atual | Largura de partida (a medir/refinar na implementação — C-1) | Regras de layout previstas |
|---|---|---|---|
| **Código** | `tag-badge` com `INV-YYYY-NNNN` (12 chars) | ~11% | código integral sem quebra (FR-003); compacta (AC-04) |
| **Inventário** | link `fw-semibold` com nome + linha auxiliar "Criado em dd/mm/aaaa HH:MM por …" (`.74rem`) | ~30% | maior prioridade (FR-004); nome com quebra graciosa; linha auxiliar legível |
| **Escopo** | `inv.scope_filters` (`small text-muted`; até 255 chars) | ~26% | maior prioridade (FR-005); quebra dentro da coluna, sem truncamento |
| **Progresso** | até 4 badges empilhados (✓/⚠/✕/“+N não previstos”) + "X/Y conferidos" (`.72rem`) | ~17% | proporcional (FR-006); badges podem quebrar/empilhar dentro da coluna |
| **Status** | 1 badge (Planejado/Em andamento/Concluído…) | ~9% | compacta (FR-007); badge íntegro, sem quebra inadequada |
| **Ações** | `text-end` + 1 botão-ícone `btn-ghost btn-icon` (Abrir) | ~7% | mínima (FR-008); alinhamento à direita preservado |

Inventário+Escopo ≈ 56% (SC-002 indicativo ✓). **Valores de partida**: a implementação mede a renderização real e refina (print antes/depois para comparação — seção 25 do pedido).

### Estrutura técnica prevista (mecanismo reusado da 036 — clarificação 2026-09-25)

- `<style>` embutido no topo do `{% block content %}` com classe de escopo própria na `<table>` (ex.: `.inv-lista-table`) — nenhuma regra global, nenhuma outra tabela afetada.
- `table-layout: fixed; width: 100%; min-width: ~860px` (valor medido) + `<colgroup>` com `<col class="cN">` (larguras em classes para permitir media query).
- Quebras: `break-word` nas células; `nowrap` no badge do código; `white-space: normal` nos badges de status/progresso (Bootstrap é nowrap).
- `table-responsive` e `card` existentes **preservados** (container intocado — FR-011); rolagem confinada em larguras mínimas.
- Media query ≤768px para header compacto, se a medição mostrar sobreposição (padrão 036).

### O que NÃO é tocado (fronteira da superfície)

| Elemento da mesma página | Motivo |
|---|---|
| Page header, botão "Novo Inventário", formulário de filtros (`search`, `status_filter`) | FR-014: fora do escopo (só a tabela) |
| Estado vazio ("Nenhum inventário encontrado") | Nada muda (edge case) |
| `style.css`, `sw.js`, qualquer asset estático | R1/R8: sem bump de cache global |
| Outras telas (detalhe do inventário — tabela da 036 —, dashboard etc.) | FR-014 |
