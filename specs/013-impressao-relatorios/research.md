# Research: Correção da Impressão A4 dos Relatórios

**Feature**: 013-impressao-relatorios | **Data**: 2026-09-17
**Entrada**: spec.md + análise de código verificada (somente leitura) + validação da cascata CSS

> Todas as decisões abaixo foram verificadas contra o código real (arquivos e linhas citados). Nenhuma técnica nova é introduzida sem precedente no projeto.

---

## R1. Causa real da página em branco — tabela inquebrável (REVISADA)

- **Decision**: A causa da primeira página em branco é `table { page-break-inside: avoid }` do bloco PRINT global (style.css linha ~968), que torna a **tabela inteira um bloco inquebrável**. Com relatórios cuja tabela excede uma página, o navegador empurra o bloco inteiro para a página 2 — a página 1 fica vazia (o cabeçalho do relatório é `.no-print` e o card não é impresso com borda) e o excedente é truncado.
- **Rationale (validação da cascata)**: a hipótese inicial da spec (padding inline do body não neutralizado) foi **refutada nesta fase**: `html, body { padding: 0 !important }` do bloco PRINT existente (linha ~918) vence o `<body style="padding-top: 90px">` inline (regra de folha de estilo com `!important` prevalece sobre declaração inline sem `!important`), e `main { padding: 0 !important }` (linha ~922) já anula o `py-4`. Os paddings não são a causa.
- **Alternatives considered**: editar o bloco PRINT global removendo o `avoid` — **rejeitada**: alteraria o Termo de Responsabilidade (que depende desse comportamento para blocos curtos) e viola a garantia de não editar regras existentes. A correção é **revogar o `avoid` por sobrecarga seletiva no escopo dos relatórios** (bloco novo, especificidade maior).

## R2. Ancoragem por seletor — classe de escopo nos 3 templates

- **Decision**: adicionar a classe `report-print` ao container `.card` dos 3 templates de relatório (`reports/movements_report.html`, `custodians_report.html`, `inventory.html`). O novo bloco `@media print` usa seletores do tipo `.report-print ...` para sobrescrever o comportamento herdado.
- **Rationale**: CSS puro não consegue isolar "as páginas dos 3 relatórios" sem `:has()` (vetado — compatibilidade Firefox) ou sem editar as regras globais (vetado). Uma classe de escopo no container existente é o mecanismo padrão, toca apenas 1 atributo `class` por arquivo e não altera dados/colunas/estrutura.
- **Alternatives considered**: `body:has(...)` como nas Etiquetas — rejeitada (requisito FR-012/quickstart: sem `:has()`); `#page-id` no body via Jinja — exigiria alterar `base.html` (fora do escopo).

## R3. Quebra de tabela — `auto` no escopo + linha indivisível

- **Decision**: no escopo dos relatórios, `table { page-break-inside: auto !important; break-inside: auto !important }` (revoga o `avoid` herdado), `thead { display: table-header-group !important }` (cabeçalho repete a cada página — comportamento padrão de tabelas em navegadores, garantido explicitamente), e `tr { page-break-inside: avoid; break-inside: avoid }` (linha indivisível).
- **Rationale**: restaura o mecanismo nativo de paginação de tabelas do navegador (usado implicitamente pelo Termo em tabelas curtas) e atende FR-004/FR-005. A linha indivisível evita corte ao meio (AC-06).
- **Alternatives considered**: `tbody` com `break-inside: auto` apenas — desnecessário; quebra natural entre `tr` já decorre do `auto` na tabela.

## R4. Largura e layout de colunas — revogar o espremimento

- **Decision**: no escopo, `.table-responsive { overflow: visible !important; min-width: 0 !important }` e `table { table-layout: auto !important; width: 100% !important }` com `td/th { overflow-wrap: anywhere }` (remediação A3 do /speckit-analyze: `word-break: break-word` é valor obsoleto da spec CSS e `overflow-wrap: anywhere` cobre os navegadores-alvo).
- **Rationale**: o `table-layout: fixed !important` global (linha ~936) distribui colunas igualmente e corta conteúdo em tabelas de 8–10 colunas; o layout automático dimensiona colunas pelo conteúdo dentro da largura da folha, e o `word-break` garante que textos longos (e-mail, motivo) quebrem em vez de estourar.
- **Alternatives considered**: manter `fixed` com larguras explícitas por coluna via `<colgroup>` — rejeitado: altera a marcação dos 3 templates de forma mais intrusiva e quebra com dados variáveis.

## R5. Corte de texto de tela desligado na impressão

- **Decision**: no escopo, `.truncate-2 { display: block !important; overflow: visible !important; -webkit-line-clamp: unset; }` e `td { white-space: normal !important }` (revoga `text-nowrap` de células), além de revogar `max-width` inline da célula de Motivo via seletor de atributo (`td[style] { max-width: none !important }` no escopo).
- **Rationale**: FR-010 — clamp/nowrap/max-width existem para compactar a tela; no papel ocultam conteúdo. O texto inteiro do motivo é dado do relatório e deve aparecer.
- **Alternatives considered**: remover as classes dos templates — rejeitada: alteraria a tela (fora do escopo; a correção é só de impressão).

## R6. `@page` — margens determinísticas, orientação selecionável (REVISADA 2026-09-17)

- **Decision (revisada — decisão do usuário durante a implementação)**: o novo bloco define `@page { margin: 10mm }` **sem a propriedade `size`**. O tamanho e a orientação do papel ficam a cargo do diálogo de impressão do navegador — A4 retrato permanece o padrão do sistema e a **paisagem fica liberada** para o usuário escolher.
- **Rationale**: fixar `size: A4` travava a orientação em alguns navegadores (diálogo sem opção de paisagem). As margens 10mm permanecem determinísticas, e o layout fluido (R4: `width: 100%` + `table-layout: auto`) se adapta naturalmente à largura extra da paisagem — tabelas de 10 colunas ganham mais área útil.
- **Alternatives considered**: `size: A4` fixo — **superseded**: travava a orientação (problema relatado pelo usuário); `size: A4 landscape` — rejeitada: forçaria paisagem para todos, o oposto do desejado.

## R7. Tipografia e cores na impressão

- **Decision**: no escopo, `font-size: 8.5pt` na tabela (mantém legibilidade e reduz páginas), fundo branco e texto escuro (reuso do mecanismo do bloco PRINT II, que já força paleta clara — as regras novas não o anulam), badges/pills com borda sutil para contraste em P&B.
- **Rationale**: 8–10 colunas em A4 com 10mm de margem exigem fonte compacta; a escala atual de tela (Bootstrap `small` ≈ 0.875rem) estoura a largura.
- **Alternatives considered**: orientação `landscape` — rejeitada nesta feature: muda o resultado esperado do usuário (retrato é o padrão atual); pode ser avaliada depois.

## R8. Documentação (Princípio XI)

- **Decision**: nenhuma atualização obrigatória de README/docs/ajuda.
- **Rationale**: verificado — README/help_service não documentam comportamento de impressão dos 3 relatórios (apenas exportações CSV/Excel/PDF). A correção restaura o comportamento esperado; não cria fluxo novo documentável. Se a implementação alterar algo visível documentado, atualiza na mesma tarefa.

## R9. Validação e testes

- **Decision**: validação de impressão manual/visual (roteiro no quickstart) + suíte pytest existente como guarda (nenhum teste editado; nenhum teste novo de layout — pytest não renderiza CSS). Teste de fumaça opcional: assert de que os 3 templates contêm a classe de escopo `report-print` (pytest-verificável via render das rotas já cobertas por test_rbac/test_auth).
- **Rationale**: layout de impressão não é verificável sem navegador; a suíte existente cobre render 200/dados das 3 rotas.
- **Alternatives considered**: Playwright/PDF diff — rejeitado: introduz dependência pesada fora do stack (Constitution X).
