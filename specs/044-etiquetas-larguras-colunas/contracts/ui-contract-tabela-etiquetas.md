# Contract de UI: Tabela de Seleção de Etiquetas (044)

Contrato de apresentação da tabela de seleção em `app/web/templates/assets/labels.html` — define o que a mudança de larguras **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature.

## §1 Contrato DOM (Jinja/Bootstrap/template — identificadores e atributos funcionais intocados)

| Identificador | Função |
|---|---|
| `th` do checkbox (cabeçalho vazio) + `input.form-check-input.asset-check` por linha (`value="{{ a.id }}"`, `checked` quando `a.id|string in selected_list`) | Controle funcional de seleção; classe/valor/condição preservados |
| `span.tag-badge` (Tombamento) com `{{ a.tag }}` | Badge global existente (monoespaçada, borda); regras de `style.css` preservadas — sem ellipsis novo |
| `span.fw-semibold` (Equipamento, 1ª linha) | Nome do equipamento (span interno cortável + tooltip) |
| `div.text-muted` condicional (`{% if a.brand or a.model %}`, .76rem) | Linha auxiliar de marca/modelo (span interno cortável + tooltip — clarificação) |
| `td.small.text-muted` (Setor) com `{% if a.location and a.location.department %}` e fallback "—" | Setor (span interno cortável + tooltip; fallback fora do span) |
| `td.small.text-muted` (Localização) com `{% if a.location %}` e fallback "—" | Localização (span interno cortável + tooltip; fallback fora do span) |
| `.table-responsive` envolvendo a tabela | Contêiner de rolagem (rolagem confinada quando inevitável) |
| page-header, filtros, toolbar (`#select-all-page`, `#sel-count`, `#clear-selection`, `#print-selected`), contador, estado vazio | Fora do escopo — intocados; **comentários CSS/HTML novos não citam controles** (lição `b75ba99`) |
| `#labels-print-area` > `.label-card` (`.label-qr[data-label-qr]`, `.label-info`, `.label-logo`, `.label-tag`) | **Domínio da feature 013** — intocado (nenhuma regra nova, nenhuma classe alterada) |

## §2 Contrato de conteúdo (FR-015 — nada exibido é removido; C-4: nada oculto sem consulta)

Por linha da tabela, TODOS estes elementos permanecem renderizados como hoje:

1. Checkbox com estado coerente com a seleção.
2. Tombamento completo e legível (badge íntegro).
3. Nome do equipamento — **acessível por tooltip** quando visualmente truncado.
4. Marca/modelo quando houver — **acessível por tooltip** quando truncada.
5. Setor (ou "—") — **acessível por tooltip** quando truncado.
6. Localização (ou "—") — **acessível por tooltip** quando truncada.

## §3 Contrato de comportamento responsivo (FR-012/C-4)

| Viewport | Comportamento exigido |
|---|---|
| Desktop grande (≥1400px) | Tabela ocupa praticamente toda a largura útil do card; textuais (Equipamento/Setor/Localização) dominam; valores predominantemente em linha única (com corte controlado + tooltip quando excedem) |
| Desktop médio (768–1399px) | Mesmas proporções relativas; sem sobreposição; linha garantida mantida com corte controlado |
| Notebook (1024–1399px) | Leitura confortável; nomes/setores/locais íntegros ou com tooltip |
| Tablet (576–767px) | Rolagem horizontal (quando necessária) confinada ao `table-responsive`; todas as 5 colunas acessíveis |
| Celular (<576px) | Rolagem confinada (mecanismo do projeto); sem fonte reduzida excessivamente; sem conteúdo cortado sem consulta; checkboxes acessíveis (`.tag-badge` ≤479.98px com fallback global aceitável) |
| Zoom 80%–200% | Mesmos critérios de legibilidade, linha única e ausência de sobreposição (precedentes 036–043) |

## §4 Contrato de tooltips e tombamento (específico da 044 — clarificações)

- Tooltip Bootstrap (`data-bs-toggle="tooltip" data-bs-placement="top" title="..."`) em **nome do equipamento, marca/modelo, setor e localização** — sempre com o valor completo; sem JS novo (inicialização existente em `base.html:329–333`/`main.js`); sem tooltip em span vazio.
- **Tombamento sem ellipsis novo**: o `.tag-badge` mantém as regras globais de `style.css` (ellipsis embutido como fallback; `max-width:140px` ≤479.98px) — dado funcional íntegro; código completo consultável na ficha do bem.
- **Nenhuma regra nova em `#labels-print-area`/`.labels-sheet`/`.label-card`** e nenhum `@media print` novo (domínio da 013 intocado).
- JS de seleção em lote e checkboxes **não são afetados**.

## §5 Contrato de não-vazamento de escopo (FR-010/FR-016)

- CSS novo **escopado** à tabela de seleção (classe dedicada + `<style>` embutido): nenhuma outra tabela/página herda regra nova; nenhuma classe genérica; **nenhuma regra global em `.table`/`.tag-badge`** (a combinação `.table align-middle` em `table-responsive` serve dezenas de telas).
- Container da tela (page header, filtros, toolbar, contador, estado vazio) **inalterado**; nenhum `@media print` criado ou alterado (tela não-relatório — R10).
- `git diff` contendo **apenas** `app/web/templates/assets/labels.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).
- Tabelas das specs 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações), 040 (custodiantes), 041 (Relatório Contábil-Físico), 042 (Trilha de Auditoria), 043 (Usuários) e demais telas intocadas.

## §6 Critérios de violação do contrato

O contrato é violado se, após a alteração:

1. O checkbox deixar de refletir/alterar a seleção (classe `.asset-check`, valor e estado preservados).
2. Tombamento, nome, marca/modelo, setor ou localização deixarem de renderizar; fallback "—" desaparecer.
3. Nome, marca/modelo, setor ou localização ficarem truncados **sem tooltip** com o valor completo (C-4); tooltip em span vazio.
4. O `.tag-badge` do Tombamento quebrar o código no meio ou receber regra nova além das globais.
5. Cabeçalhos desalinharem do corpo (thead ≠ tbody) — incluindo a coluna do checkbox.
6. A folha de etiquetas (`#labels-print-area`), seu `@media print` em `style.css` ou o comportamento de impressão mudarem (domínio da 013).
7. Outra tabela/tela mudar de aparência (inclusive 036–043).
8. `style.css` ou `sw.js` forem modificados, ou o container/filtros/toolbar/estado vazio mudarem.
9. Alguma regra de seleção em lote/filtros/permissões mudar (FR-014) — a alteração é exclusivamente visual.
10. A página lançar erro de template (suíte pytest detecta; page-loads das páginas principais).
11. Um comentário CSS/HTML citar o nome de um controle (lição `b75ba99`).
