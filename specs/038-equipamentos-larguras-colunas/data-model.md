# Data Model: Ajuste Responsivo da Tabela "Equipamentos" (038)

**Sem entidades de dados novas ou alteradas.** Feature exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão ou payload muda (FR-013/FR-014).

## Modelo de apresentação (única superfície afetada)

### Template `app/web/templates/assets/list.html` — tabela de equipamentos (linhas ~133–192)

| Coluna | Conteúdo atual | Largura de partida (a medir/refinar — C-1) | Regras de layout previstas |
|---|---|---|---|
| **Tombamento** | link com `tag-badge` (número patrimonial) | ~11% | código integral sem quebra (FR-003); compacta |
| **Equipamento / Modelo** | link `fw-semibold` com nome + linha auxiliar `.76rem` (marca/modelo • `S/N: <code>`) | ~24% | maior prioridade (FR-004); nome+auxiliar legíveis, quebra graciosa |
| **Categoria** | badge `badge-soft-gray` (`.68rem`) | ~9% | adequada ao conteúdo (FR-005); excedente vai para textuais |
| **Status** | `status-pill-{DISPONIVEL,EM_USO,EM_MANUTENCAO,EM_TRANSITO,BAIXADO}` com `::before` | ~10% | compacta (FR-006); rótulo mais longo em 1 linha (medição; ver R4) |
| **Responsável** | link com ícone + nome + matrícula `.72rem`, ou "Estoque Livre" | ~15% | maior prioridade (FR-007); nome completo sem truncamento |
| **Localização** | texto `small text-muted` ou "Estoque Central" | ~19% | maior prioridade (FR-008); nomes institucionais longos |
| **Valor** | `small font-monospace fw-semibold text-nowrap` (R$ 1.250,00) | ~7% | sem quebra (nowrap funcional preservado — FR-009); compacta |
| **Ações** | `text-end text-nowrap`: 1–2 botões-ícone ("Ver Detalhes" sempre; "Movimentar" se `movimentacao.criar`) | ~5% | mínima (FR-010); 2 botões + gap cabem; alinhamento à direita preservado |

Textuais (Equipamento/Modelo + Responsável + Localização) ≈ 58% (SC-002 indicativo ✓).

### Estrutura técnica prevista (mecanismo reusado das 036/037 — implementação mede e refina)

- `<style>` embutido no topo do `{% block content %}` com classe de escopo própria (ex.: `.assets-lista-table`) — nenhuma regra global, nenhuma outra tabela afetada.
- `table-layout: fixed; width: 100%; min-width: ~1080px` (a medir) + `<colgroup>` com `<col class="cN">` (larguras em classes para media query).
- Quebras: `break-word` nas células; `nowrap` no badge do tombamento; `text-nowrap` de Valor/Ações **preservado**; status-pill dimensionado para 1 linha (medição; ver R4).
- `table-responsive` e `card` existentes **preservados** (FR-011); rolagem confinada em larguras mínimas.
- Media query ≤768px para header compacto, se a medição mostrar sobreposição (padrão 036/037).

### O que NÃO é tocado (fronteira da superfície)

| Elemento da mesma página | Motivo |
|---|---|
| Page header, dropdown de relatórios, formulário de filtros (`assets-filters`) | FR-011/FR-013: fora do escopo |
| Contagem "Mostrando X de Y" e estado vazio | Nada muda (edge case) |
| `style.css`, `sw.js`, qualquer asset estático | R1/R9: sem bump de cache global |
| Tabelas da 036 (conferência) e 037 (inventários) e demais telas | FR-015 |
