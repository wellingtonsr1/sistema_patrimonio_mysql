# Contract de UI: Tabela do Relatório Contábil-Físico do Patrimônio (041)

Contrato de apresentação da tabela em `app/web/templates/reports/inventory.html` — define o que a mudança de larguras **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature.

## §1 Contrato DOM (Jinja/Bootstrap/template — identificadores e atributos funcionais intocados)

| Identificador | Função |
|---|---|
| `div.card.p-4.report-print` (container do relatório) | **Âncora de impressão** — a string exata `class="card p-4 report-print"` é fixada por `tests/test_report_print_smoke.py` (assert de conteúdo HTML); a classe NÃO pode sair do container |
| `thead` > 10 `<th>` e `tbody` > 10 `<td>` por linha | Estrutura de colunas simétrica (10/10) |
| `td.font-monospace.fw-bold` (Tombamento) | Visual monoespaçado do código patrimonial (classes preservadas) |
| `<strong>{{ a.name }}</strong>` + `div.text-muted` "S/N: ..." condicional a `a.serial_number` (Descrição) | Nome destacado + linha de serial como blocos distintos (estrutura preservada — evita sobreposição) |
| `span.badge.badge-soft-gray` (Categoria) | Visual da categoria (classe preservada) |
| `span.status-pill.status-pill-{{ a.status.value }}` (Status) | Pill de status com valor dinâmico (classe/valor preservados) |
| fallbacks Jinja: `a.location.name if a.location else 'Estoque Geral'`, `a.custodian.name if a.custodian else 'Livre'`, `a.purchase_date.strftime('%d/%m/%Y') if a.purchase_date else '-'` | Fallbacks "Estoque Geral"/"Livre"/"-" preservados |
| `td.text-end.small` (Valor Aquisição) · `td.text-end.small` com `style="color:var(--red);"` e prefixo `-` (Depreciação) · `td.text-end.small.fw-bold` com `style="color:var(--green);"` (Valor Atual) | Alinhamento à direita e cores semânticas das monetárias (preservados) |
| formatação pt-BR inline (`"{:,.2f}".format(...).replace(...)`) | Formato monetário e casas decimais (intocados — FR-014) |
| `page-header.no-print` com controles do relatório | Header da tela fora do escopo (FR-011); **comentários CSS/HTML novos não citam os nomes dos controles** (lição `b75ba99` — vazamento detectado por testes RBAC) |
| `.table-responsive` envolvendo a tabela | Contêiner de rolagem (rolagem confinada quando inevitável) |

## §2 Contrato de conteúdo (FR-015 — nada exibido é removido)

Por linha da tabela, TODOS estes elementos permanecem renderizados como hoje:

1. Tombamento (`font-monospace fw-bold`).
2. Descrição: nome em `<strong>` + linha "S/N: ..." quando houver `serial_number`.
3. Categoria como badge `badge-soft-gray`.
4. Status como pill `status-pill-<valor>` com o label do status.
5. Localização (ou "Estoque Geral").
6. Responsável (ou "Livre").
7. Data Compra `dd/mm/YYYY` (ou "-").
8. Valor Aquisição formatado pt-BR.
9. Depreciação como `-XX%` em vermelho.
10. Valor Atual formatado pt-BR em verde, negrito.

## §3 Contrato de comportamento responsivo (FR-012/C-4)

| Viewport | Comportamento exigido |
|---|---|
| Desktop grande (≥1400px) | Tabela ocupa praticamente toda a largura útil do card; textuais (Descrição/Localização/Responsável) dominam o espaço variável; sem grandes vazios |
| Desktop médio (768–1399px) | Mesmas proporções relativas; sem sobreposição; textos longos quebram em fronteira de palavra |
| Notebook (1024–1399px) | Leitura confortável; cabeçalhos alinhados; valores monetários íntegros |
| Tablet (576–767px) | Adaptação correta; rolagem horizontal (se inevitável) confinada ao `table-responsive`; todas as 10 colunas acessíveis |
| Celular (<576px) | Padrão responsivo do projeto (rolagem confinada); sem conteúdo cortado indevidamente; sem sacrificar legibilidade para eliminar a rolagem |
| Zoom 80%–200% | Mesmos critérios de legibilidade e ausência de sobreposição (precedentes 036–040) |

## §4 Contrato de impressão (específico da 041 — FR-013/C-6)

- O bloco `@media print` dos relatórios (C1–C10 em `style.css`, ancorado em `.report-print`, **compartilhado** com os outros 2 relatórios) NÃO é editado — nenhuma linha alterada.
- Toda largura/min-width/nowrap/table-layout aplicado em tela à tabela da 041 fica **neutralizado dentro de `@media print`** por regra escopada no `<style>` do próprio template (R10: defesa em profundidade sobre o C3/C6/C7 existentes).
- A pré-visualização de impressão de `/reports/inventory` permanece **idêntica ao comportamento atual**: sem primeira página em branco, cabeçalho das colunas repetido por página (`thead` header-group), linhas indivisíveis, `table-layout: auto` no papel, textos íntegros (`white-space: normal`), escala `8.5pt`, bordas de contraste em badges/pills (C10).
- `git diff` não contém `style.css` → nenhum bump de cache (`style.css?v=` em `base.html` e allowlist do Service Worker como estão).

## §5 Contrato de não-vazamento de escopo (FR-011/FR-016)

- CSS novo **escopado** à tabela do relatório (classe dedicada + `<style>` embutido): nenhuma outra tabela/página herda regra nova; nenhuma classe genérica.
- Container da tela (page header, cabeçalho interno do relatório, card) **inalterado**.
- Tabelas da 036 (inventarios/detail.html), 037 (inventarios/list.html), 038 (assets/list.html), 039 (movements/list.html), 040 (custodians/list.html), demais relatórios (`movements_report.html`, `custodians_report.html`) e demais telas intocadas.

## §6 Critérios de violação do contrato

O contrato é violado se, após a alteração:

1. A string `class="card p-4 report-print"` deixar de existir no HTML (`test_report_print_smoke.py` falha) ou a âncora mudar de elemento.
2. Algum item do §2 deixar de renderizar (incluídos linha S/N, fallbacks, cores semânticas, negrito do Valor Atual).
3. Descrição/Localização/Responsável forem truncados com clamp/ellipsis (contraria a clarificação de texto completo).
4. Tombamento, datas ou valores monetários quebrarem de forma indevida (ex.: `R$ 1.250,00` dividido entre linhas).
5. A pré-visualização de impressão mudar de layout em relação ao estado anterior (página em branco, sem repetição de cabeçalho, truncamento no papel, escala diferente).
6. Outra tabela/tela mudar de aparência (inclusive 036–040 e os outros 2 relatórios).
7. `style.css` ou `sw.js` forem modificados, ou o container/header/cabeçalho interno mudarem.
8. Exportações CSV/Excel/PDF mudarem de conteúdo, nome de arquivo ou gate de permissão.
9. A página lançar erro de template (suíte pytest detecta via `test_report_print_smoke.py`/`test_help.py`/`test_rbac.py`).
10. Um comentário CSS/HTML citar o nome de um controle do header e um teste RBAC de template falhar (lição `b75ba99`).
