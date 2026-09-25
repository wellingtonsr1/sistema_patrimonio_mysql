# Research: Ajuste Responsivo das Larguras das Colunas na Tabela de Conferência (036)

Todas as incógnitas técnicas resolvidas com fatos do repositório (nenhum NEEDS CLARIFICATION restante — as decisões de negócio vieram do solicitante C-1..C-4 e das clarificações Q1–Q3).

## R1 — Onde vive o CSS da alteração: template embutido vs `style.css` global

**Decision**: CSS da tela embutido no próprio `detail.html` (bloco `<style>` restrito), sem tocar `style.css`.

**Rationale**:
- O `style.css` é carregado por **todas** as páginas (`base.html` L29) e é versionado por querystring em **dois pontos acoplados**: `base.html` (`?v=20260924`) e allowlist do Service Worker (`sw.js` L18, mesma querystring). Alterá-lo obrigaria a bumpar a versão global e propagar cache para todo o sistema por uma mudança que interessa a uma tela — contrário à cirurgia do Princípio I.
- Precedente no repositório: `offline.html` usa `<style>` embutido (único template com `<style>`); a 035 alterou o CSS embutido da shell sem tocar `style.css` global.
- `detail.html` não tem block de `head` disponível em `base.html` (apenas `title`, `flash_messages`, `content`, `scripts`), então o `<style>` entra no topo do `{% block content %}` — CSS válido no `<body>` e suficiente para o seletor de escopo.
- A tabela-alvo não está dentro de um `{% for %}` que duplicaria o `<style>` (o loop começa depois); um único bloco por render da página.

**Alternatives considered**:
- *`style.css` global com classes novas*: rejeitado — cache global invalidado + risco de colisão com outras tabelas; FR-012 proíbe afetar outras telas.
- *Classes utilitárias Bootstrap puro sem CSS novo*: insuficiente — Bootstrap não fornece controle determinístico de proporção entre colunas de tabela (`table-layout`/`colgroup` não são utilitários de classe).

## R2 — Mecanismo de controle de largura: `table-layout: fixed` + `<colgroup>`

**Decision**: aplicar `table-layout: fixed` na tabela-alvo com `<colgroup>` definindo percentuais por coluna (referência: Tombamento ~14%, Bem ~30%, Local esperado ~34%, Resultado ~15%, Conferir ~7% — dentro do SC-001 indicativo: Bem+Local ~64% ≥ 50%; Resultado+Conferir ~22% < 25%).

**Rationale**:
- Hoje a tabela usa layout automático (`table-layout: auto`): o navegador dimensiona colunas pelo conteúdo — é exatamente a causa do problema (badge com local anexado e células com muito conteúdo alargam Resultado; textos longos de Bem/Local ficam comprimidos).
- `table-layout: fixed` + `<colgroup>` com percentuais é a forma nativa e determinística de fixar proporções independentemente do conteúdo; degrada bem com `table-responsive` existente.
- Percentuais mantêm a responsividade em qualquer largura de viewport (requisito FR-008) sem media queries por breakpoint de coluna.

**Alternatives considered**:
- *Larguras em `th` inline (`style="width:X%"` sem fixed)*: funciona parcialmente, mas o layout automático ainda ajusta conforme conteúdo (não determinístico; badge longo pode alargar).
- *Media queries por breakpoint redefinindo larguras*: complexidade desnecessária — percentuais já são responsivos; media queries ficariam apenas se um ajuste pontual em mobile se mostrar necessário (registro no tasks/validação).
- *Flexbox/Grid reescrevendo a tabela*: rejeitado — reescrita estrutural proibida (Princípio I, FR-011: nada funcional muda; tabelas semânticas têm melhor acessibilidade).

## R3 — Proteção de conteúdos longos dentro das colunas compactas (FR-005/edge cases)

**Decision**: na coluna Resultado, permitir quebra natural das linhas auxiliares (`observation` e metadados "quem/quando") com `word-break: break-word`/`overflow-wrap: anywhere` local; para o badge de LOCAL_DIFERENTE com local anexado, permitir quebra dentro do badge ou truncamento visual com título nativo (decisão fina na implementação, validada no quickstart V3).

**Rationale**: o FR-005 exige compactação SEM perder legibilidade das linhas auxiliares; com `table-layout: fixed`, texto longo sem estratégia de quebra transborda a célula. `overflow-wrap: anywhere` quebra apenas quando necessário (não quebra palavras curtas como "Pendente").

**Alternatives considered**: *truncar observação com ellipsis global*: rejeitado — esconderia informação exibida hoje (violaria FR-011/AC-08).

## R4 — Bem/Local esperado em linha única quando houver espaço (FR-003/FR-004)

**Decision**: `white-space: normal` (padrão) nas colunas textuais; SEM `white-space: nowrap` global — a "linha única quando possível" emerge naturalmente das larguras generosas (Bem 30% / Local 34%); em larguras pequenas a quebra de linha é o comportamento responsivo desejado (spec: "comportamento responsivo adequado").

**Rationale**: forçar `nowrap` causaria overflow em mobile (violaria AC-07/SC-004); com colgroup generoso, desktop mantém linha única na prática (validado no quickstart V2 com os nomes institucionais reais de 35–45 caracteres).

**Alternatives considered**: *`white-space: nowrap` + `text-overflow: ellipsis` + `title` com valor completo*: rejeitado como padrão geral — esconderia conteúdo (FR-011); mantido como opção pontual apenas se a validação visual mostrar necessidade (decisão documentada em validacao.md).

## R5 — Coluna Conferir com `table-layout: fixed` (FR-006)

**Decision**: manter `text-end` no header/célula + largura ~7% no colgroup; botão-ícone (`btn-ghost btn-icon`) cabe com folga; nenhuma mudança no botão ou no modal (`#modalConferir{{ item.id }}` fica FORA da tabela, no fim do template — intocado).

**Rationale**: com fixed layout, 7% de uma tabela de ~1200px ≈ 84px — suficiente para o ícone + padding; alinhamento à direita preserva a convenção atual da coluna de ação.

**Alternatives considered**: *`width: 1%; white-space: nowrap` no auto layout*: hack inconsistente entre navegadores; fixed layout torna desnecessário.

## R6 — Inventário encerrado (edge case): coluna Conferir sem conteúdo

**Decision**: nenhuma regra condicional — com colgroup fixo, a coluna mantém a largura reservada mesmo sem botões (comportamento estável e previsível; header continua alinhado).

**Rationale**: a spec pede apenas "não reservar espaço vazio desproporcional" — 7% é proporcional por definição; regras condicionais por estado adicionariam complexidade sem benefício visual.

## R7 — Tema claro/escuro

**Decision**: nenhuma cor nova introduzida; a alteração é de largura/alinhamento apenas — nada a preservar além de não introduzir cores literais.

**Rationale**: o `<style>` embutido conterá apenas regras de layout (`table-layout`, `colgroup` é markup, `overflow-wrap`), sem propriedades de cor/tema (FR-043 da 033 herda aqui como bom princípio; AC do pedido: temas preservados).

## R8 — Versionamento de cache

**Decision**: NENHUM bump de versão — `detail.html` é template server-side (não cacheado pelo SW; navegações fora de `/offline` são network-only) e nenhum asset estático é alterado.

**Rationale**: o SW cacheia apenas a allowlist de estáticos + navegação `/inventarios/{id}/offline`; páginas de inventário (`/inventarios/{id}`) sempre vêm da rede — recarregar a página já entrega o novo HTML. Bump no `?v=` do `style.css` invalidaria cache global sem necessidade.

**Alternatives considered**: *bump preventivo do `?v=`*: rejeitado — efeito colateral global (todas as páginas rebaixam CSS), contrário à cirurgia.

## R9 — Testes automatizados

**Decision**: nenhum teste novo automatizado; suíte existente como proteção de regressão (SC-005/SC-006). O `test_conferencia_visual.py` e `test_inventario_reconferencia_ui.py` exercitam a renderização desta página e detectariam quebra estrutural do template.

**Rationale**: pytest não valida proporções visuais (sem infra de teste de UI — registrado na 035 como D7); criar testes artificiais de markup seria frágil e contra a spec (seção 15 do pedido: "não criar testes artificiais").

**Alternatives considered**: *teste de presença de `<colgroup>` no HTML renderizado*: possível mas frágil/low-value — o quickstart visual V1–V5 cobre o comportamento real.

## R10 — Validação e registro (SC-007)

**Decision**: seguir o padrão 033/035: suíte pytest verde + validação manual nos 4 cenários (desktop largo, desktop médio, tablet, celular) + faixa de zoom 80%–200%, registrada em `specs/036-conferencia-larguras-colunas/validacao.md` (arquivo criado na fase de implementação, como na 033).

**Rationale**: clarificação Q2 do solicitante definiu explicitamente este formato.
