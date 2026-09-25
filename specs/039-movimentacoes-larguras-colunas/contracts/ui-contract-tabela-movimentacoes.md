# Contract de UI: Tabela do Fluxo Global de Movimentações (039)

Contrato de apresentação da tabela em `app/web/templates/movements/list.html` — define o que a mudança de larguras **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature.

## §1 Contrato DOM (Jinja/Bootstrap/template — identificadores e atributos funcionais intocados)

| Identificador | Função |
|---|---|
| link `tag-badge` → `/assets/{{ m.asset_id }}` (Tombamento) | Navegação pela ficha a partir do tombamento |
| link com `color:var(--c-text);font-weight:600` → `/assets/{{ m.asset_id }}` (Equipamento) | Navegação pelo nome do bem |
| `a.btn.btn-ghost.btn-icon[title="Imprimir Termo"]` → `/movements/{{ m.id }}/term` | Ação condicional a `{% if m.term_code %}` (condição Jinja preservada) |
| `a.btn.btn-ghost.btn-icon[title="Ver Bem"]` → `/assets/{{ m.asset_id }}` | Ação sempre presente |
| `text-nowrap` na célula de Data / Hora | Comportamento funcional existente a preservar |
| `truncate-2` na célula de Motivo | Corte em 2 linhas existente a preservar (cap de 220px removido — clarificação) |
| ícones `bi-geo-alt`, `bi-person` (Origem) e `bi-geo-alt-fill`, `bi-person-fill` (Destino) | Semântica visual de local/custodiante (preservados junto aos textos) |
| `text-end` + `d-flex gap-1 justify-content-end` na célula de Ações | Alinhamento à direita dos botões |
| `badge-soft-primary` (Tipo), `tag-badge` (Tombamento) | Classes visuais preservadas |
| `.empty-state*` | Estado vazio da listagem (não tocar) |
| formulário de filtro (`form[action="/movements"]`, `select[name="movement_type"]`) | Filtros (fora da tabela — não tocar) |

## §2 Contrato de conteúdo (FR-014 — nada exibido é removido)

Por linha da tabela, TODOS estes elementos permanecem renderizados como hoje:

1. Data e hora em `dd/mm/AAAA HH:MM` (1 linha).
2. Tombamento como link com `tag-badge`.
3. Nome do equipamento como link (peso 600, cor atual).
4. Badge do tipo de movimentação com o rótulo atual (Entrada por Aquisição / Alocação / Cautela / Transferência de Local / Envio para Manutenção / Retorno de Manutenção / Devolução ao Estoque / Baixa / Descarte / Atualização de Estado).
5. Origem: linha do local **ou** `-` (com ícone) + linha do custodiante **ou** `-` (com ícone).
6. Destino: linha do local **ou** `-` (com ícone, `fw-semibold`) + linha do custodiante **ou** `-` (com ícone).
7. Motivo: texto descritivo com corte em 2 linhas (sem cap de 220px).
8. Operador (`small text-muted`).
9. Botões de Ação (1 ou 2 conforme `m.term_code`) com tooltips.

## §3 Contrato de comportamento responsivo (FR-012/C-4)

| Viewport | Comportamento exigido |
|---|---|
| Desktop grande (≥1400px) | Tabela ocupa praticamente toda a largura útil do card; textuais (Equipamento/Origem/Destino/Motivo/Operador) dominam; sem grandes vazios |
| Desktop médio (768–1399px) | Mesmas proporções relativas; sem sobreposição; textos longos quebram graciosamente |
| Notebook (1024–1399px) | Leitura confortável; cabeçalhos alinhados; badges íntegros; data/hora e botões sem quebra |
| Tablet (576–767px) | Adaptação correta; rolagem horizontal (se inevitável) confinada ao `table-responsive`; controles utilizáveis |
| Celular (<576px) | Padrão responsivo do projeto (rolagem confinada para tabela larga de 9 colunas); sem conteúdo cortado indevidamente; ações acessíveis |
| Zoom 80%–200% | Mesmos critérios de legibilidade e ausência de sobreposição (precedentes 036/037/038) |

## §4 Contrato de não-vazamento de escopo (FR-011/FR-015)

- CSS novo **escopado** à tabela de movimentações (classe dedicada + `<style>` embutido): nenhuma outra tabela/página herda regra nova; nenhuma classe genérica.
- Container da tela (page header, botões do header, filtro, card, contagem) **inalterado**.
- Nenhum asset estático alterado → nenhum bump de cache (`style.css?v=` e SW allowlist como estão).
- Tabelas da 036 (inventarios/detail.html), 037 (inventarios/list.html) e 038 (assets/list.html) intocadas.

## §5 Critérios de violação do contrato

O contrato é violado se, após a alteração:

1. Links (tombamento, equipamento) ou botões (Imprimir Termo, Ver Bem) deixarem de funcionar/sumirem.
2. Algum item do §2 deixar de renderizar (incluídos fallbacks `-`, ícones e tooltips).
3. O corte do Motivo em 2 linhas deixar de funcionar (texto completo explodindo a linha OU truncado em 1 linha).
4. A Data / Hora quebrar entre data e hora.
5. Outra tabela/tela mudar de aparência (inclusive 036/037/038).
6. `style.css` ou `sw.js` forem modificados, ou o container/filtro/contagem mudarem.
7. A condição de visibilidade do botão "Imprimir Termo" deixar de respeitar `m.term_code`.
8. A página lançar erro de template (suíte pytest detecta via testes de movements/web).
