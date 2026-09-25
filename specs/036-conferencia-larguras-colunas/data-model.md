# Data Model: Ajuste Responsivo das Larguras das Colunas na Tabela de Conferência (036)

**Sem entidades de dados novas ou alteradas.** A feature é exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão ou payload muda (FR-010/FR-011 da spec).

## Modelo de apresentação (única superfície afetada)

### Template `app/web/templates/inventarios/detail.html` — tabela de bens esperados (linhas ~226–276)

| Coluna | Conteúdo atual | Classe/célula atual | Largura de referência (colgroup) | Regras de layout previstas |
|---|---|---|---|---|
| **Tombamento** | link com `tag-badge` (`item.asset.tag`) | sem classe de largura | **~14%** | dimensão por conteúdo (C-1); badge completo legível; `nowrap` opcional no badge (tombamento não tem espaços) |
| **Bem** | `item.asset.name` (`small`, `fw-semibold`) | `small` | **~30%** | linha única quando houver espaço; quebra graciosa (`overflow-wrap`) em larguras pequenas |
| **Local esperado** | `item.expected_location_name or 'Estoque Central'` (`small text-muted`) | `small text-muted` | **~34%** | entre as maiores larguras (FR-004); nomes institucionais de 35–45 chars em linha única em desktop; quebra responsiva em mobile |
| **Resultado** | badge de status (+ observação `.72rem` e metadados `.68rem` quando existirem) | sem classe de largura | **~15%** | compacta (FR-005); linhas auxiliares quebram dentro da coluna (`overflow-wrap: anywhere` local); badge LOCAL_DIFERENTE com local anexado quebra/trunca sem alargar a coluna |
| **Conferir** | botão-ícone `btn-ghost btn-icon` (abre modal) | `text-end` | **~7%** | mínima para botão+padding (FR-006); `text-end` preservado; estado encerrado mantém largura (R6) |

### Estrutura técnica prevista (nível de mecanismo — implementação decide detalhes finos)

- `<style>` embutido no topo do `{% block content %}` com **seletor de escopo** restrito à tabela de bens esperados (classe própria, ex.: `.inv-esperados-table`, adicionada à `<table>` — sem colidir com as outras 2 tabelas da página).
- `table-layout: fixed` + `<colgroup>` com 5 `<col style="width:X%">` conforme tabela acima.
- `table-responsive` (wrapper existente) **preservado** — garante rolagem restrita à tabela em larguras mínimas.
- Alinhamentos existentes preservados (`text-end` na coluna de ação).
- **IDs/classes funcionais intocados**: `formBuscar`, `modalConferir{{ item.id }}`, `tag-badge`, `btn-ghost btn-icon`, badges `badge-soft-*`.

### O que NÃO é tocado (fronteira da superfície)

| Elemento da mesma página | Motivo |
|---|---|
| Card "Conflitos offline" (tabela própria, L~107) | FR-012: fora do escopo |
| Card de coletas offline (tabela própria, L~150) | FR-012: fora do escopo |
| Formulário de busca `#formBuscar`, modais `#modalConferir*`, `#modalEncerrar`, botões "Iniciar/Preparar coleta offline" | Nada funcional muda (FR-010/FR-011) |
| `style.css` global, `sw.js`, `manifest`, qualquer asset estático | R1/R8: sem bump de cache global |
