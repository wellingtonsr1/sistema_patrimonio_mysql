# Contract de UI: Tabela de Colaboradores & Custodiantes (040)

Contrato de apresentação da tabela em `app/web/templates/custodians/list.html` — define o que a mudança de larguras **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature.

## §1 Contrato DOM (Jinja/Bootstrap/template — identificadores e atributos funcionais intocados)

| Identificador | Função |
|---|---|
| `span.tag-badge` (Matrícula) | Visual monoespaçado do código (classe preservada) |
| badge condicional "provisória" (`{% if is_provisional(c.registration_code) %}`, `badge-soft-gray`, tooltip) | Indicador de matrícula provisória (condição e tooltip preservados) |
| link `fw-semibold` com `bi-person-circle` → `/custodians/{{ c.id }}` (Nome) | Navegação para a ficha do colaborador |
| `badge-soft-gray` (Departamento) | Visual do departamento (classe preservada) |
| badge pill de Bens (`active_assets_count`, `text-center`) | Contagem de bens sob custódia (classe/estilo preservados) |
| `a.btn.btn-ghost.btn-icon[title="Editar Colaborador"]` → `/custodians/{{ c.id }}/edit` | Ação condicional a `{% if can('colaboradores.editar') %}` (condição Jinja preservada) |
| `a.btn.btn-ghost.btn-sm` "Ver Bens" (ícone `bi-laptop` + texto) → `/custodians/{{ c.id }}` | Ação sempre presente (texto do botão preservado) |
| `text-center` na célula de Bens; `text-end` + `d-flex gap-1 justify-content-end` em Ações | Alinhamentos existentes |
| `.empty-state*` (2 variantes) | Estados vazios da listagem (não tocar) |
| formulário de pesquisa (`form[action="/custodians"]`, `input[name="search"]`) | Pesquisa (fora da tabela — não tocar) |

## §2 Contrato de conteúdo (FR-013 — nada exibido é removido)

Por linha da tabela, TODOS estes elementos permanecem renderizados como hoje:

1. Matrícula como `tag-badge` + badge "provisória" quando aplicável.
2. Nome como link com ícone `bi-person-circle`.
3. Cargo (`small`).
4. Departamento como badge `badge-soft-gray` (texto completo).
5. E-mail (`small text-muted`).
6. Pill de Bens com `active_assets_count`.
7. Botões de Ação: "Editar Colaborador" (se permissão) + "Ver Bens" — com tooltips.

## §3 Contrato de comportamento responsivo (FR-011/C-4)

| Viewport | Comportamento exigido |
|---|---|
| Desktop grande (≥1400px) | Tabela ocupa praticamente toda a largura útil do card; textuais (Nome/Cargo/Departamento/E-mail) dominam; sem grandes vazios |
| Desktop médio (768–1399px) | Mesmas proporções relativas; sem sobreposição; textos longos quebram em fronteira de palavra |
| Notebook (1024–1399px) | Leitura confortável; cabeçalhos alinhados; badges íntegros; "Ver Bens" íntegro |
| Tablet (576–767px) | Adaptação correta; rolagem horizontal (se inevitável) confinada ao `table-responsive`; controles utilizáveis |
| Celular (<576px) | Padrão responsivo do projeto (rolagem confinada); sem conteúdo cortado indevidamente; ações acessíveis |
| Zoom 80%–200% | Mesmos critérios de legibilidade e ausência de sobreposição (precedentes 036–039) |

## §4 Contrato de não-vazamento de escopo (FR-010/FR-014)

- CSS novo **escopado** à tabela de custodians (classe dedicada + `<style>` embutido): nenhuma outra tabela/página herda regra nova; nenhuma classe genérica.
- Container da tela (page header, botões, pesquisa, card, estados vazios) **inalterado**.
- Nenhum asset estático alterado → nenhum bump de cache (`style.css?v=` e SW allowlist como estão).
- Tabelas da 036 (inventarios/detail.html), 037 (inventarios/list.html), 038 (assets/list.html) e 039 (movements/list.html) intocadas.

## §5 Critérios de violação do contrato

O contrato é violado se, após a alteração:

1. Link do Nome ou botões (Editar Colaborador, Ver Bens) deixarem de funcionar/sumirem.
2. Algum item do §2 deixar de renderizar (incluído badge "provisória", ícone do Nome, tooltips).
3. Nome/Cargo/Departamento/E-mail forem truncados com clamp/ellipsis (contraria a clarificação de texto completo).
4. O badge "provisória" sumir ou quebrar no meio do texto da matrícula.
5. Outra tabela/tela mudar de aparência (inclusive 036–039).
6. `style.css` ou `sw.js` forem modificados, ou o container/pesquisa/estados vazios mudarem.
7. A condição de visibilidade do botão "Editar Colaborador" deixar de respeitar `colaboradores.editar`.
8. A página lançar erro de template (suíte pytest detecta via testes de custodians/help/rbac).
