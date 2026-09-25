# Contract de UI: Tabela de Equipamentos (038)

Contrato de apresentação da tabela em `app/web/templates/assets/list.html` — define o que a mudança de larguras **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature.

## §1 Contrato DOM (JS/Bootstrap/template — identificadores e atributos funcionais intocados)

| Identificador | Função |
|---|---|
| link `tag-badge` → `/assets/{id}` | Navegação pela ficha a partir do tombamento |
| link `fw-semibold` → `/assets/{id}` | Navegação pelo nome do equipamento |
| link `/custodians/{id}` | Navegação para o colaborador responsável |
| `tag-badge`, `badge-soft-gray` | Visual de tombamento/categoria (classes preservadas) |
| `status-pill-{STATUS}` (+ `::before`) | Status pill com bolinha de cor (classes preservadas) |
| `a.btn.btn-ghost.btn-icon[title="Ver Detalhes"]` | Ação 1 (sempre presente) |
| `a.btn.btn-ghost.btn-icon[title="Movimentar"]` | Ação 2 — condicional a `can('movimentacao.criar')` (condição Jinja preservada) |
| `text-nowrap` nas células de Valor e Ações | Comportamento funcional existente a preservar |
| `.empty-state*` | Estado vazio da listagem (não tocar) |
| formulário `assets-filters` (`input[name="search"]`, selects) | Filtros (fora da tabela — não tocar) |

## §2 Contrato de conteúdo (FR-014 — nada exibido é removido)

Por linha da tabela, TODOS estes elementos permanecem renderizados como hoje:

1. Tombamento como link com `tag-badge`.
2. Nome do equipamento como link (`fw-semibold`, cor atual).
3. Linha auxiliar de marca/modelo e `S/N: <code>` quando existirem (`.76rem`).
4. Badge de categoria.
5. Status-pill com rótulo atual (Disponível/Em Uso/Em Manutenção/Em Trânsito/Baixado).
6. Responsável: link com ícone + nome + matrícula (`.72rem`) **ou** "Estoque Livre".
7. Localização: nome do local **ou** "Estoque Central".
8. Valor monetário formatado (`R$ X.YZZ,ZZ`, monospace).
9. Botões de Ação (1 ou 2 conforme permissão) com tooltips.

## §3 Contrato de comportamento responsivo (FR-012/C-4)

| Viewport | Comportamento exigido |
|---|---|
| Desktop grande (≥1400px) | Tabela ocupa praticamente toda a largura útil do card; textuais dominam; sem grandes vazios |
| Desktop médio (768–1399px) | Mesmas proporções relativas; sem sobreposição; textos longos quebram graciosamente |
| Notebook (1024–1399px) | Leitura confortável; cabeçalhos alinhados; badges/pills íntegros; valores e botões sem quebra |
| Tablet (576–767px) | Adaptação correta; rolagem horizontal (se inevitável) confinada ao `table-responsive`; controles utilizáveis |
| Celular (<576px) | Padrão responsivo do projeto (rolagem confinada para tabela larga de 8 colunas); sem conteúdo cortado indevidamente; ações acessíveis |
| Zoom 80%–200% | Mesmos critérios de legibilidade e ausência de sobreposição (precedentes 036/037) |

## §4 Contrato de não-vazamento de escopo (FR-011/FR-015)

- CSS novo **escopado** à tabela de equipamentos (classe dedicada + `<style>` embutido): nenhuma outra tabela/página herda regra nova; nenhuma classe genérica.
- Container da tela (page header, filtros, card, contagem) **inalterado**.
- Nenhum asset estático alterado → nenhum bump de cache (`style.css?v=` e SW allowlist como estão).
- Tabelas da 036 (inventarios/detail.html) e 037 (inventarios/list.html) intocadas.

## §5 Critérios de violação do contrato

O contrato é violado se, após a alteração:

1. Links (tombamento, nome, responsável) ou botões (Ver Detalhes, Movimentar) deixarem de funcionar/sumirem.
2. Algum item do §2 deixar de renderizar (incluídas linhas auxiliares, fallbacks "Estoque Livre"/"Estoque Central" e tooltips).
3. Outra tabela/tela mudar de aparência (inclusive 036/037).
4. `style.css` ou `sw.js` forem modificados, ou o container/filtros mudarem.
5. A condição de visibilidade do botão "Movimentar" deixar de respeitar `movimentacao.criar`.
6. A página lançar erro de template (suíte pytest detecta via testes de assets/movements/navbar).
