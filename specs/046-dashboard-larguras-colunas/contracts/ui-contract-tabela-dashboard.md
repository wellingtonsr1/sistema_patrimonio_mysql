# Contract de UI: Tabela "Fluxo Recente de Movimentações" (046)

Contrato de apresentação da tabela em `app/web/templates/dashboard.html` (seção "Fluxo Recente de Movimentações" da tela "Visão Geral do Patrimônio") — define o que a mudança de larguras **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature.

## §1 Contrato DOM (Jinja/Bootstrap/template — identificadores e atributos funcionais intocados)

| Identificador | Função |
|---|---|
| `div.card` > `div.card-header-clean` (título "Fluxo Recente de Movimentações" + subtítulo) com `{% if can('movimentacao.visualizar') %}` + botão "Ver Tudo" | Header do card intocado; gate do botão preservado |
| `div.table-responsive` envolvendo a tabela | Contêiner de rolagem (rolagem confinada quando inevitável) |
| `table.table.align-middle` (recebe a classe de escopo da 046) | Superfície da alteração (apenas classe ADICIONADA) |
| `th` Data / Tombamento / Equipamento / Ação / Destino / Operador / `th.text-end` Ações | Cabeçalhos com textos e alinhamentos preservados |
| `td.text-muted.small.text-nowrap` (Data) com `(m.timestamp \| localtime).strftime('%d/%m/%Y %H:%M')` | Rígida: nowrap e formato existentes preservados |
| `span.tag-badge` (Tombamento) com `{{ m.asset.tag }}` | Badge global existente (monoespaçada, borda); regras de `style.css` preservadas — sem ellipsis novo |
| `a.fw-semibold.text-decoration-none` (Equipamento, `href="/assets/{{ m.asset_id }}"`, `style="color:var(--c-text);"`) | Link funcional e cor inline preservados (span interno cortável + tooltip dentro do link) |
| `span.badge.badge-soft-primary` (Ação, `style="font-size:.68rem;"`) com `{{ m.movement_type.label }}` | Badge íntegro — estilos inline e vocabulário de labels preservados |
| `td.small` (Destino) com if/else: `span.fw-medium` + `i.bi-person` + `{{ m.destination_custodian_name }}` **ou** `span.text-muted` + `i.bi-geo-alt` + `{{ m.destination_location_name or 'Estoque' }}` | Estrutura condicional, ícones e fallback "Estoque" preservados (spans internos cortáveis + tooltip nos dois ramos) |
| `td.text-muted.small` (Operador) com `{{ m.operator_name }}` | Valor preservado (span interno cortável + tooltip) |
| `td.text-end.text-nowrap` (Ações) com `{% if m.term_code %}` `a.btn-ghost.btn-icon` (impressora, title="Termo de Cautela", target="") + `a.btn-ghost.btn-icon` (chevron, title="Ver Bem") | Botões, títulos, hrefs e estrutura condicional preservados |
| Estado vazio `div.empty-state` ("Nenhuma movimentação recente") | Intocado (renderiza quando `stats.recent_movements` vazio) |
| **Tabela "Necessitam de atenção"** (L182–200, Tag/Equipamento/Observação) | **Sem classe nova, sem regra nova** — o seletor escopado não a alcança (R5) |
| KPIs, cards de distribuição, card "Integridade do Patrimônio", `page-header` | Fora do escopo — intocados; **comentários CSS/HTML novos não citam nomes de controles** (lição `b75ba99`) |

## §2 Contrato de conteúdo (FR-016 — nada exibido é removido; C-4: nada oculto sem consulta)

Por linha da tabela, TODOS estes elementos permanecem renderizados como hoje:

1. Data/hora completa (`dd/mm/aaaa hh:mm`).
2. Tombamento completo e legível (badge íntegro).
3. Nome do equipamento como **link** para a ficha — **acessível por tooltip** quando visualmente truncado.
4. Rótulo da ação (`movement_type.label`) — badge íntegro.
5. Destino: colaborador (ícone + nome) **ou** local/"Estoque" (ícone + nome) — **acessível por tooltip** quando truncado.
6. Nome do operador — **acessível por tooltip** quando truncado.
7. Botão "Termo de Cautela" quando `term_code` existir + botão "Ver Bem" sempre.

## §3 Contrato de comportamento responsivo (FR-014/C-4)

| Viewport | Comportamento exigido |
|---|---|
| Desktop grande (≥1400px) | Tabela ocupa praticamente toda a largura útil do card; textuais (Equipamento/Destino/Operador) dominam; valores predominantemente em linha única (com corte controlado + tooltip quando excedem) |
| Desktop médio (768–1399px) | Mesmas proporções relativas; sem sobreposição; linha garantida mantida com corte controlado |
| Notebook (1024–1399px) | Leitura confortável; equipamentos/destinos/operadores íntegros ou com tooltip |
| Tablet (576–767px) | Rolagem horizontal (quando necessária) confinada ao `table-responsive`; todas as 7 colunas acessíveis |
| Celular (<576px) | Rolagem confinada (mecanismo do projeto); sem fonte reduzida excessivamente; sem conteúdo cortado sem consulta; controles acessíveis |
| Zoom 80%–200% | Mesmos critérios de legibilidade, linha única e ausência de sobreposição (precedentes 036–044) |

## §4 Contrato de tooltips e badges (específico da 046 — clarificações)

- Tooltip Bootstrap (`data-bs-toggle="tooltip" data-bs-placement="top" title="..."`) em **Equipamento, Destino (dois ramos) e Operador** — sempre com o valor completo; sem JS novo (inicialização existente em `base.html:329–333`/`main.js`); sem tooltip em span vazio.
- **Tombamento sem ellipsis novo**: o `.tag-badge` mantém as regras globais de `style.css` (ellipsis embutido como fallback; `max-width:140px` ≤479.98px) — dado funcional íntegro; código completo consultável na ficha do bem.
- **Badge da Ação sem regra nova**: dimensionado pelos rótulos reais (`movement_type.label` — "Entrada por Aquisição" é o mais longo) em uma linha nas larguras alvo; nenhum seletor global de `.badge` é criado.
- **Nenhum `@media print` novo** (R10 da 043 — o dashboard não é tela-relatório).

## §5 Contrato de não-vazamento de escopo (FR-012/FR-017)

- CSS novo **escopado** à tabela de movimentações (classe dedicada + `<style>` embutido): nenhuma outra tabela/página herda regra nova; nenhuma classe genérica; **nenhuma regra global em `.table`/`.tag-badge`/`.badge`/`.btn-ghost`** (a combinação serve dezenas de telas).
- **A outra tabela do mesmo template ("Necessitam de atenção") NÃO recebe classe, regra ou alteração alguma** — comprovada idêntica na medição antes/depois (R5/R6).
- `style.css`, `base.html`, `main.js`, service worker e telas 036–045: **zero linhas alteradas**.
- Comentários novos (HTML/CSS) não citam nomes de controles ou IDs funcionais (lição `b75ba99`).
