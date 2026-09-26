# Contract de UI: Tabela da Trilha de Auditoria & Fluxo (042)

Contrato de apresentação da tabela em `app/web/templates/reports/movements_report.html` — define o que a mudança de larguras **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature.

## §1 Contrato DOM (Jinja/Bootstrap/template — identificadores e atributos funcionais intocados)

| Identificador | Função |
|---|---|
| `div.card.p-4.report-print` (container do relatório) | **Âncora de impressão** — a string exata `class="card p-4 report-print"` é fixada por `tests/test_report_print_smoke.py` (L19–21 incluem `/reports/movements`); a classe NÃO pode sair do container |
| `thead` > 10 `<th>` e `tbody` > 10 `<td>` por linha | Estrutura de colunas simétrica (10/10) |
| `td.text-nowrap` (Data / Hora) | Data/hora em linha única — classe global existente preservada |
| `td.font-monospace.fw-bold` (Tombamento) | Visual monoespaçado do código patrimonial (classes preservadas) |
| `<span class="badge badge-soft-primary">` (Tipo) | Badge do tipo de movimentação (classe/tamanho preservados) |
| Estrutura condicional de Origem: `{{ m.origin_location_name or '-' }}` + `{% if m.origin_custodian_name %}<br><span class="text-muted">(...)</span>{% endif %}` | Local + custodião em 2 linhas informativas (condições Jinja e classes preservadas) |
| Estrutura condicional de Destino: `<strong style="color:var(--c-primary-text);">` + `{% if m.destination_custodian_name %}<br><span style="color:var(--c-primary-text);">(...)</span>{% endif %}` | Local em destaque + custodião (cores/condições preservadas) |
| `<span class="status-pill status-pill-{{ m.new_status.value }}">` (Status) | Pill de status com valor dinâmico (classe/valor preservados) |
| `m.reason` (Motivo) | Conteúdo completo do motivo — o elemento que o exibe passa a ter tooltip com o valor integral (C-7); a classe global `truncate-2` e o `max-width:200px` inline saem desta célula |
| `td.small.text-muted` (Operador) | Operador (classes preservadas) |
| `<a href="/movements/{{ m.id }}/term" target="_blank">` condicional a `{% if m.term_code %}`, com fallback `-` (Termo) | Link do termo (rota, target, condição e fallback preservados) |
| `page-header.no-print` com controles do relatório | Header da tela fora do escopo (FR-014); **comentários CSS/HTML novos não citam os nomes dos controles** (lição `b75ba99`) |
| `.table-responsive` envolvendo a tabela | Contêiner de rolagem (rolagem confinada quando inevitável — C-4) |

## §2 Contrato de conteúdo (FR-018 — nada exibido é removido; C-7: nada oculto sem mecanismo de consulta)

Por linha da tabela, TODOS estes elementos permanecem renderizados como hoje:

1. Data/Hora completa `dd/mm/YYYY HH:MM`.
2. Tombamento mono/negrito íntegro.
3. Nome do equipamento.
4. Badge do tipo (`m.movement_type.label`).
5. Origem: local (ou "-") + custodião quando houver.
6. Destino: local (ou "-") + custodião quando houver, com destaque atual.
7. Pill de status (`m.new_status.label`).
8. Motivo completo — **acessível por tooltip** quando visualmente truncado (hoje: cortado em 200px sem mecanismo de consulta).
9. Operador.
10. Termo: link mono quando houver `term_code`; "-" caso contrário.

## §3 Contrato de comportamento responsivo (FR-015/C-4)

| Viewport | Comportamento exigido |
|---|---|
| Desktop grande (≥1400px) | Tabela ocupa praticamente toda a largura útil do card; textuais (Equipamento/Origem/Destino/Motivo) dominam; valores predominantemente em linha única (com corte controlado + tooltip quando excedem) |
| Desktop médio (768–1399px) | Mesmas proporções relativas; sem sobreposição; linha garantida mantida com corte controlado |
| Notebook (1024–1399px) | Leitura confortável; Data/Hora/Tombamento/Status/Termo íntegros em 1 linha |
| Tablet (576–767px) | Rolagem horizontal (quando necessária) confinada ao `table-responsive`; todas as 10 colunas acessíveis |
| Celular (<576px) | Rolagem horizontal confinada (mecanismo do projeto, autorizado — C-4); sem fonte reduzida excessivamente; sem dados escondidos; colunas legíveis na rolagem |
| Zoom 80%–200% | Mesmos critérios de legibilidade, linha única e ausência de sobreposição (precedentes 036–041) |

## §4 Contrato de impressão (específico da 042 — FR-016/C-6)

- O bloco `@media print` dos relatórios (C1–C10 em `style.css`, ancorado em `.report-print`, **compartilhado** com os outros 2 relatórios) NÃO é editado — nenhuma linha alterada.
- Toda largura/min-width/nowrap/corte por ellipsis aplicado em tela fica **neutralizado dentro de `@media print`** por regra escopada no `<style>` do próprio template (precedente da 041) — incluindo os spans internos de ellipsis (`white-space: normal`, `overflow: visible`, `text-overflow: clip`), pois o C7 global só atinge `td/th`.
- No papel, o Motivo volta a quebrar/imprimir por completo como hoje (o C8 global deixa de ser necessário para esta tabela porque a classe `truncate-2` sai do template); tooltips não existem no papel (UI de hover) — o texto integral é impresso.
- A pré-visualização de impressão de `/reports/movements` permanece **idêntica ao comportamento atual**: sem primeira página em branco, cabeçalho das colunas repetido por página, linhas indivisíveis, `table-layout: auto` no papel, textos íntegros, escala `8.5pt`.
- `git diff` não contém `style.css` → nenhum bump de cache (`style.css?v=` em `base.html` e allowlist do Service Worker como estão).

## §5 Contrato de não-vazamento de escopo (FR-014/FR-019)

- CSS novo **escopado** à tabela da trilha (classe dedicada + `<style>` embutido): nenhuma outra tabela/página herda regra nova; nenhuma classe genérica (nome distinto de `.mov-lista-table` da 039).
- Container da tela (page header, cabeçalho interno do relatório, card) **inalterado**.
- Tabelas da 036 (inventarios/detail.html), 037 (inventarios/list.html), 038 (assets/list.html), 039 (`movements/list.html` — **não confundir**), 040 (custodians/list.html), 041 (`reports/inventory.html`), demais relatórios (`reports/custodians_report.html`) e demais telas intocadas.

## §6 Critérios de violação do contrato

O contrato é violado se, após a alteração:

1. A string `class="card p-4 report-print"` deixar de existir no HTML (`test_report_print_smoke.py` falha) ou a âncora mudar de elemento.
2. Algum item do §2 deixar de renderizar (incluídos fallbacks "-", custodiões condicionais, cores, link do termo).
3. Algum valor truncado visualmente ficar **sem tooltip** com o texto completo (C-7) — inclusive no Motivo.
4. Data/Hora, Tombamento ou Termo quebrarem no meio (identificadores).
5. Origem/Destino perderem a estrutura condicional local + custodião.
6. A pré-visualização de impressão mudar de layout em relação ao estado anterior (página em branco, sem repetição de cabeçalho, truncamento no papel, escala diferente).
7. Outra tabela/tela mudar de aparência (inclusive 036–041 e os outros 2 relatórios).
8. `style.css` ou `sw.js` forem modificados, ou o container/header/cabeçalho interno mudarem.
9. A exportação CSV mudar de conteúdo, nome de arquivo ou gate de permissão.
10. A página lançar erro de template (suíte pytest detecta via `test_report_print_smoke.py`/`test_movements.py`/`test_help.py`/`test_rbac.py`).
11. Um comentário CSS/HTML citar o nome de um controle do header e um teste RBAC de template falhar (lição `b75ba99`).
