# Data Model: Ajuste Responsivo da Tabela "Etiquetas de Patrimônio" (044)

**Sem entidades de dados novas ou alteradas.** Feature exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão ou payload muda (FR-013/FR-014/FR-015). Os dados exibidos (`Asset`: tag, name, brand, model, location.department, location.name) e a rota `/assets/labels` (`routes.py:381`, gate `patrimonio.visualizar`, render `routes.py:449`) permanecem intocados.

## Modelo de apresentação (única superfície afetada)

### Template `app/web/templates/assets/labels.html` — tabela de seleção (5 colunas)

Larguras de partida (C-1; soma ≈ 1230px, coerente com 042 (1380) e 043 (1330); a medir/refinar). Textuais = **linha garantida** (ellipsis + tooltip Bootstrap — clarificações); rígidas = nowrap com pisos de fonte real.

| Col | Coluna | Conteúdo atual | Largura de partida | Regras de layout previstas |
|---|---|---|---|---|
| c0 | (checkbox) | `input.form-check-input.asset-check` (cabeçalho vazio, `th` com `width:36px` inline hoje) | ~46px | mínima (FR-003): controle clicável íntegro, estável; `width` inline do `th` absorvido pelo colgroup |
| c1 | Tombamento | `span.tag-badge` (monoespaçada bold .78rem; ellipsis global embutido; `max-width:140px` ≤479.98px) | ~150px | rígida (FR-004): código completo em uma linha nas larguras alvo; **sem ellipsis novo** — regras globais preservadas |
| c2 | Equipamento / Modelo | `span.fw-semibold` (nome) + `div.text-muted` .76rem (marca/modelo, condicional) | ~420px | textual dominante (FR-005): **duas linhas cortáveis** — nome e marca/modelo cada uma com ellipsis + tooltip Bootstrap; estrutura de 2 linhas preservada (C-7) |
| c3 | Setor | `td.small.text-muted` — `a.location.department` ou "—" | ~280px | textual (FR-006): linha garantida — ellipsis + tooltip; fallback "—" fora do span cortável |
| c4 | Localização | `td.small.text-muted` — `a.location.name` ou "—" | ~334px | textual (FR-007): linha garantida — ellipsis + tooltip; **uma das maiores parcelas** (C-2); fallback "—" fora do span cortável |

Textuais (Equipamento+Setor+Localização) ≈ 1034px de partida (maior bloco — SC-002); rígidas com folga ×1,25–1,30 (Plus Jakarta Sans; padding `.5rem .5rem` = 16px/coluna).

### Estrutura técnica prevista (mecanismo reusado das 036–043)

- `<style>` embutido no topo do `{% block content %}` com comentário "Feature 044" (sem citar controles do header/toolbar/filtros — lição `b75ba99`) e classe de escopo própria (ex.: `.etiq-table`).
- `table-layout: fixed; width: 100%; min-width: ~1230px` (único conjunto, sem media query de colunas — lição da 041) + `<colgroup>` com `<col class="cN">` (incluindo a col c0 do checkbox).
- **Classe auxiliar de ellipsis** (ex.: `.etiq-ellip`): `display:inline-block; max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; vertical-align:bottom` + `data-bs-toggle="tooltip" data-bs-placement="top"` — aplicada no **nome do equipamento**, na **marca/modelo**, no **setor** e na **localização**.
- Fallbacks "—" (Setor/Localização) e conteúdo vazio (marca/modelo) **fora dos spans cortáveis**; sem tooltip em span vazio.
- `.tag-badge` do Tombamento: sem regra nova — regras globais de `style.css` preservadas (ellipsis embutido como fallback; `max-width:140px` ≤479.98px).
- **Sem badges** nesta tabela → a lição `white-space: normal` escopado (042/043) não se aplica; nada a fazer.
- `table-responsive`, card de listagem, contador e estado vazio preservados (FR-010); `page-header`, filtros e toolbar `no-print` intocados.
- **Sem bloco de impressão** (R10 — tela não-relatório; nenhum `@media print` criado ou alterado); **folha `#labels-print-area` e `@media print` de etiquetas em `style.css` intocados** (domínio da 013).

### O que NÃO é tocado (fronteira da superfície)

| Elemento da mesma página | Motivo |
|---|---|
| `page-header` ("no-print") | FR-010: fora do escopo (comentários novos não citam controles — lição `b75ba99`) |
| Card de filtros (search/status/categoria/marca/modelo/local/colaborador/setor) | FR-010: fora do escopo |
| Toolbar de seleção (`#select-all-page`, `#sel-count`, `#clear-selection`, `#print-selected`) | FR-010/FR-014: fora do escopo — controle funcional |
| Folha de etiquetas `#labels-print-area` > `.label-card` (QR + logo + tag) | **Domínio da feature 013** — intocado (FR-013) |
| JS inline (QRCode + seleção em lote via `?selected=`) | FR-014: intocado (classes `.asset-check`/`#select-all-page` preservadas) |
| Estado vazio "Nenhum equipamento encontrado" | FR-010: intocado |
| Container global `base.html` | FR-010: não alterado |
| Condições Jinja dos dados (`a.tag`, `a.name`, brand/model, department, location, selected_list) | FR-014/FR-015: lógica de dados intocada |
| `style.css` (inclui `@media print` de etiquetas 013 e contraste de checkboxes), `sw.js`, qualquer asset estático | FR-010/FR-013: sem bump de cache global; domínio de impressão protegido |
| Tabelas das specs 036–043 e demais telas | FR-016 |
