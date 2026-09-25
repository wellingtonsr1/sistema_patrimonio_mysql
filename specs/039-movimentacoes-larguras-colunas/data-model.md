# Data Model: Ajuste Responsivo da Tabela "Fluxo Global de Movimentações" (039)

**Sem entidades de dados novas ou alteradas.** Feature exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão ou payload muda (FR-013/FR-014).

## Modelo de apresentação (única superfície afetada)

### Template `app/web/templates/movements/list.html` — tabela do fluxo global (linhas ~47–104)

| Coluna | Conteúdo atual | Largura de partida (a medir/refinar — C-1) | Regras de layout previstas |
|---|---|---|---|
| **Data / Hora** | `small text-muted text-nowrap` — `dd/mm/AAAA HH:MM` (16 chars) | ~8% | integral em 1 linha (nowrap funcional preservado — FR-003); compacta |
| **Tombamento** | link com `tag-badge` (número patrimonial) | ~8% | código integral sem quebra (FR-004); compacta |
| **Equipamento** | link `text-decoration-none` com `color:var(--c-text);font-weight:600` (nome do bem) | ~15% | maior prioridade (FR-005); nome legível, quebra graciosa |
| **Tipo** | badge `badge-soft-primary` (`.68rem`) com `m.movement_type.label` | ~9% | adequada ao conteúdo real (FR-006); rótulo mais longo ~22 chars; excedente vai para textuais |
| **Origem** | `small`, 2 linhas: `bi-geo-alt` + local **ou** `-`; `bi-person` + custodiante **ou** `-` | ~15% | maior prioridade (FR-007); local e custodiante legíveis, 2 linhas empilhadas |
| **Destino** | `small`, 2 linhas: `bi-geo-alt-fill` + local (`fw-semibold`); `bi-person-fill` + custodiante | ~15% | maior prioridade (FR-007); ídem Origem, com ênfase visual atual preservada |
| **Motivo** | `small truncate-2` (**cap de 220px removido** — clarificação) | ~15% | maior prioridade (FR-008); corte em 2 linhas preservado; sem cap de largura |
| **Operador** | `small text-muted` (nome do usuário) | ~9% | prioridade intermediária/alta (FR-009); nome completo sem truncamento |
| **Ações** | `text-end`: 1–2 botões-ícone `btn-ghost btn-icon` ("Imprimir Termo" se `m.term_code`; "Ver Bem" sempre) em `d-flex gap-1 justify-content-end` | ~6% | mínima (FR-010); 2 botões + gap cabem; alinhamento à direita preservado |

Textuais (Equipamento + Origem + Destino + Motivo + Operador) ≈ 63% (SC-002 indicativo ✓).

### Estrutura técnica prevista (mecanismo reusado das 036/037/038 — implementação mede e refina)

- `<style>` embutido no topo do `{% block content %}` com classe de escopo própria (ex.: `.mov-lista-table`) — nenhuma regra global, nenhuma outra tabela afetada.
- `table-layout: fixed; width: 100%; min-width: ~1180px` (a medir) + `<colgroup>` com `<col class="cN">` (larguras em classes para media query).
- Quebras: `break-word` nas células; `nowrap` no badge do tombamento; `text-nowrap` da Data / Hora **preservado**; `truncate-2` do Motivo **preservado** (sem o cap inline); células de Origem/Destino com 2 `div`s empilhadas.
- `table-responsive` e `card` existentes **preservados** (FR-011); rolagem confinada em larguras mínimas.
- Media query ≤768px para header compacto, se a medição mostrar sobreposição (padrão 036/037/038).

### O que NÃO é tocado (fronteira da superfície)

| Elemento da mesma página | Motivo |
|---|---|
| Page header, botões "Exportar CSV"/"Nova Movimentação", formulário de filtro de tipo | FR-011/FR-013: fora do escopo |
| Contagem "Mostrando N registros de fluxo" e estado vazio | Nada muda (edge case) |
| `style.css`, `sw.js`, qualquer asset estático | R1/R9: sem bump de cache global |
| Tabelas da 036 (conferência), 037 (inventários), 038 (equipamentos) e demais telas | FR-015 |
