# Data Model: Ajuste Responsivo da Tabela "Colaboradores & Custodiantes" (040)

**Sem entidades de dados novas ou alteradas.** Feature exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão ou payload muda (FR-012/FR-013).

## Modelo de apresentação (única superfície afetada)

### Template `app/web/templates/custodians/list.html` — tabela de colaboradores (linhas ~44–86)

| Coluna | Conteúdo atual | Largura de partida (a medir/refinar — C-1) | Regras de layout previstas |
|---|---|---|---|
| **Matrícula** | `tag-badge` monoespaçada + badge condicional "provisória" (`is_provisional`) | ~11% | código integral sem quebra no badge (FR-003); "provisória" ao lado, quebra só entre elementos |
| **Nome** | link `fw-semibold` com ícone `bi-person-circle` → `/custodians/{id}` | ~19% | maior prioridade (FR-004); **texto completo** (sem clamp — clarificação); quebra em fronteira de palavra |
| **Cargo** | `small`, texto livre | ~15% | maior prioridade (FR-005); **texto completo** (clarificação) |
| **Departamento** | badge `badge-soft-gray` | ~16% | maior prioridade (FR-006); **texto completo** no badge, `white-space: normal` (clarificação) |
| **E-mail** | `small text-muted` | ~19% | maior prioridade (FR-007); **texto completo** (clarificação); quebra natural apenas quando inevitável |
| **Bens** | badge pill centralizado (`active_assets_count`) | ~8% | compacta (FR-008); `text-center` preservado |
| **Ações** | `text-end`: "Editar Colaborador" (ícone, condicional a `colaboradores.editar`) + "Ver Bens" (ícone + **texto**) | ~12% | mínima (FR-009); dimensionada para 2 controles com texto |

Textuais (Nome+Cargo+Departamento+E-mail) ≈ 69% (SC-002 indicativo ✓).

### Estrutura técnica prevista (mecanismo reusado das 036–039 — implementação mede e refina)

- `<style>` embutido no topo do `{% block content %}` com classe de escopo própria (ex.: `.cust-lista-table`) — nenhuma regra global, nenhuma outra tabela afetada.
- `table-layout: fixed; width: 100%; min-width: ~1150px` (a medir) + `<colgroup>` com `<col class="cN">` (larguras em classes para media query).
- Quebras: `break-word` nas células; **sem clamp/ellipsis nas textuais** (texto completo — clarificação); `nowrap` no badge da Matrícula; `white-space: normal` no badge do Departamento.
- Rígidas (Matrícula/Bens/Ações) em **px com folga** para a Plus Jakarta Sans (lição da 039); textuais em % dividindo o restante.
- `table-responsive` e `card` existentes **preservados** (FR-010); rolagem confinada em larguras mínimas.
- Media query ≤768px para header compacto, se a medição mostrar sobreposição (padrão 036–039).

### O que NÃO é tocado (fronteira da superfície)

| Elemento da mesma página | Motivo |
|---|---|
| Page header, botões "Exportar CSV"/"Importar CSV"/"Cadastrar Colaborador", formulário de pesquisa | FR-010/FR-012: fora do escopo |
| Ambos os estados vazios ("com busca" e "sem cadastro" com CTA) | Nada muda (edge case) |
| `style.css`, `sw.js`, qualquer asset estático | R1/R9: sem bump de cache global |
| Tabelas da 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações) e demais telas | FR-014 |
