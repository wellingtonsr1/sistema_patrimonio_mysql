# Contract de UI: Tabela de Listagem "Inventário Patrimonial" (037)

Contrato de apresentação da tabela de listagem em `app/web/templates/inventarios/list.html` — define o que a mudança de larguras **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature.

## §1 Contrato DOM (JS/Bootstrap/template — identificadores e atributos funcionais intocados)

| Identificador | Função |
|---|---|
| `input[name="search"]` | Campo de busca por código/nome (formulário de filtros — fora da tabela, não tocar) |
| `select[name="status_filter"]` | Filtro de status (idem) |
| link `fw-semibold` → `/inventarios/{id}` | Navegação para o inventário a partir do nome |
| `.tag-badge` | Visual do código (sem alteração de classe) |
| `.badge .badge-soft-{green,amber,red,gray,primary}` | Badges de progresso e status (classes preservadas) |
| `a.btn.btn-ghost.btn-icon[title="Abrir"]` | Botão-ícone de Ações com tooltip "Abrir" |
| `.empty-state*` | Estado vazio da listagem (não tocar) |

## §2 Contrato de conteúdo (FR-013 — nada exibido é removido)

Por linha da tabela, TODOS estes elementos permanecem renderizados como hoje:

1. Código como `tag-badge` (`INV-YYYY-NNNN`).
2. Nome do inventário como link (`fw-semibold`, cor atual).
3. Linha auxiliar "Criado em {data} por {autor}" (`.74rem`) quando existir.
4. Escopo (`scope_filters`) — texto completo, sem truncamento.
5. Badges de progresso presentes conforme resumo: ✓ encontrados, ⚠ local diferente, ✕ não encontrados, "+N não previstos" (condicional) + "X/Y conferidos".
6. Badge de status com rótulo atual (Planejado/Em andamento/…).
7. Botão "Abrir" com ícone `bi-eye` e tooltip.

## §3 Contrato de comportamento responsivo (FR-010/C-4)

| Viewport | Comportamento exigido |
|---|---|
| Desktop grande (≥1400px) | Tabela ocupa praticamente toda a largura útil do card; Inventário/Escopo dominam; sem grandes vazios |
| Desktop médio (768–1399px) | Mesmas proporções relativas; sem sobreposição; textos longos quebram graciosamente |
| Notebook (1024–1399px) | Leitura confortável; cabeçalhos alinhados; ações acessíveis |
| Tablet (576–767px) | Proporções mantidas; rolagem horizontal (se inevitável) confinada ao `table-responsive`; controles utilizáveis |
| Celular (<576px) | Padrão responsivo do projeto; sem conteúdo cortado indevidamente; ações acessíveis |
| Zoom 80%–200% | Mesmos critérios de legibilidade e ausência de sobreposição (clarificação 2026-09-25) |

## §4 Contrato de não-vazamento de escopo (FR-011/FR-014)

- CSS novo **escopado** à tabela da listagem (classe dedicada + `<style>` embutido): nenhuma outra tabela/página herda regra nova; nenhuma classe genérica (`table {}`, `td {}` sem escopo).
- Container da tela (`page-header`, `card`, paddings) **inalterado**.
- Nenhum asset estático alterado → nenhum bump de cache (`style.css?v=` e SW allowlist como estão).
- Formulário de filtros e estado vazio intocados.

## §5 Critérios de violação do contrato

O contrato é violado se, após a alteração:

1. O link do nome, o botão "Abrir" (ou seu tooltip) ou os filtros deixarem de funcionar.
2. Algum item do §2 deixar de renderizar (incluídas linhas auxiliares e badges condicionais).
3. Outra tabela/tela mudar de aparência.
4. `style.css` ou `sw.js` forem modificados.
5. O container da tela for alterado.
6. A página lançar erro de template (suíte pytest detecta via testes de inventário/navbar).
