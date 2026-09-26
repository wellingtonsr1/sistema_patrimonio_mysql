# Research: Ajuste Responsivo da Tabela "Trilha de Auditoria & Fluxo" (042)

Incógnitas resolvidas com fatos do repositório e o mecanismo validado nas 036–041. Nenhum NEEDS CLARIFICATION restante — as 2 clarificações de spec (linha garantida com ellipsis; tooltip Bootstrap) estão registradas e incorporadas aos FRs. Especificidades da 042: **linha única garantida** nas textuais com corte controlado (C-4/clarificação) e **tooltip Bootstrap** (C-7).

## R1 — Onde vive o CSS: template embutido com classe de escopo (decisão 036–041, reusada)

**Decision**: CSS embutido em `reports/movements_report.html` (bloco `<style>` no topo do `{% block content %}`, com comentário de rastreabilidade "Feature 042") com classe de escopo própria na tabela (ex.: `.movrep-table`) e classe auxiliar de ellipsis (ex.: `.movrep-ellip`); `style.css` intocado. Distinto de `.mov-lista-table` (039, listagem de Movimentações).

**Rationale**: idêntico às anteriores — `style.css` é global e versionado em 2 pontos acoplados (base.html + SW allowlist); bump invalidaria cache de todo o sistema. Comentários não citam controles do header (lição `b75ba99`).

**Alternatives considered**: *`style.css` global*: rejeitado (cache global + FR-014 proíbe classes genéricas).

## R2 — `table-layout`: **fixed** justificado (C-5) — agora reforçado pela linha garantida

**Decision**: `table-layout: fixed` + `<colgroup>` com `<col class="cN">` estilizadas no `<style>` escopado; larguras determinadas por medição na implementação (C-1).

**Rationale**: (a) 10 colunas com conteúdos de comprimento muito variável — o auto layout redistribui a cada linha, incompatível com o objetivo de **linha única estável**; (b) com fixed + `white-space: nowrap` + `overflow: hidden` + `text-overflow: ellipsis`, o corte é **previsível e controlado** (não há sobreposição nem redistribuição por conteúdo); (c) `<colgroup>` resolve canonicamente a exigência thead=tbody (seção 22); (d) as 036–041 comprovaram o mecanismo.
- **Quando auto seria melhor**: tabelas de poucas colunas com larguras naturais estáveis — não é o caso.
- Risco conhecido: com nowrap, célula estreita cortaria o texto — mitigado por ellipsis **+ tooltip** (clarificação) e pelos pisos de largura da fonte real (R3/R11).

**Alternatives considered**: *auto*: rejeitado — larguras instáveis e quebra por conteúdo (o problema atual); *percentuais inline no colgroup*: rejeitado (lição da 036 — não sobrescrevível).

## R3 — Larguras iniciais de partida (a medir/refinar na implementação — C-1)

**Decision**: pontos de partida sugeridos (soma ≈ 1340px, coerente com o conjunto validado da 041): **Data/Hora ~130px** ("24/09/2026 12:20" ≈ 115–125px reais), **Tombamento ~110px** (mono 10–12ch), **Equipamento ~150px** (ellipsis + tooltip), **Tipo ~150px** (badge .68rem: "Entrada por Aquisição", "Atualização de Estado" ≈ 135px reais), **Origem ~145px**, **Destino ~145px** (ellipsis por linha), **Status ~125px** (pill "Em Manutenção" ≈ 97–126px), **Motivo ~170px** (maior textual), **Operador ~130px** (ellipsis), **Termo ~110px** (mono link "TR-2026-0439" ≈ 94px reais). Rígidas com folga ×1,25–1,30 (Plus Jakarta Sans; padding real `.5rem .5rem` = 16px/coluna — vendor Bootstrap). Valores finais por medição (V0 antes/depois).

## R4 — Mecanismo de linha única + tooltip Bootstrap (clarificações — o coração da 042)

**Decision**:
- Células de valor simples (Data/Hora, Tombamento, Tipo, Status, Termo): `white-space: nowrap` (Data/Hora já tem `text-nowrap`; demais via classe escopada) — conteúdo curto/identificador, sem corte esperado com os pisos da R3.
- **Textuais (Equipamento, Motivo, Operador)**: célula em `nowrap` + `overflow: hidden` + `text-overflow: ellipsis` com tooltip Bootstrap — `data-bs-toggle="tooltip" data-bs-placement="top" title="{{ ... }}"` no elemento do texto.
- **Origem/Destino (2 segmentos: local + custodião em `<br>` condicional)**: cada segmento em `span.movrep-ellip` próprio (nowrap + hidden + ellipsis, `max-width:100%`) com tooltip — a estrutura de 2 linhas informativa do template é preservada, e cada linha fica garantida em uma linha.
- **Tooltip Bootstrap**: mecanismo já auto-inicializado globalmente (`base.html:329–333` e `static/js/main.js:11–14` executam `new bootstrap.Tooltip(el)` para todo `[data-bs-toggle="tooltip"]`) — marcação server-rendered funciona sem JS novo; precedentes de markup: `movements/new.html:36`, `assets/form.html:35` (`data-bs-toggle="tooltip" data-bs-placement="top" title="..."`). Nota: a 039 usou tooltip nativo (`title` em `div.truncate-2`) — a 042 usa Bootstrap por decisão do solicitante.
- **Motivo**: remover a classe global `truncate-2` e o `max-width:200px` inline do `<td>`, substituindo pelo mecanismo acima (FR-010) — o C8 (que libera `truncate-2` no papel) deixa de se aplicar a esta tabela por não haver mais a classe; a neutralização de impressão passa a ser responsabilidade do bloco de segurança do template (R10).

**Alternatives considered**: *tooltip nativo (`title`)*: rejeitado — clarificação explícita pelo tooltip Bootstrap (padrão do projeto, leitura confortável); *quebra com colunas generosas (padrão 041)*: rejeitado — a clarificação exige linha garantida; *ellipsis sem tooltip*: rejeitado — C-7/seção 31 proíbe ocultar dado sem mecanismo de consulta (estado atual do Motivo viola isso).

## R5 — Aproveitamento total (C-3/FR-001/AC-01)

**Decision**: fixed + colgroup com soma ≈ container → tabela em praticamente 100% do card; nenhum `max-width` artificial (o `max-width:200px` inline do Motivo sai); container/header/cabeçalho interno intocados (FR-014). Medição V0 antes/depois documenta o aproveitamento.

## R6 — Responsividade e min-width (C-4: rolagem explicitamente permitida)

**Decision**: `min-width` único sincronizado com a soma do colgroup (≈1340px, a calibrar com a fonte real — lição 041: **um só conjunto, sem media query de colunas**, eliminou as invasões célula-a-célula da 041); abaixo disso, rolagem horizontal confinada ao `table-responsive` — comportamento **desejado e autorizado** para 10 colunas (seções 20/21); todas as colunas permanecem acessíveis e legíveis na rolagem; nenhuma fonte reduzida. Zoom 80%–200%: colunas px mantêm a distribuição.

**Rationale**: com linha garantida por ellipsis, não há "quebra vertical" para evitar — a tensão da 041 (colunas espremidas quebrando) desaparece; o conjunto único + rolagem é a solução mais estável comprovada.

## R7 — Temas e cores

**Decision**: nenhuma cor nova; apenas layout/quebra. Badge `badge-soft-primary`, pill `status-pill-*`, cores `var(--c-primary-text)` (Destino/link Termo) e `text-muted` herdam os temas via `style.css` intocado.

## R8 — Botões do header, RBAC e tooltips

**Decision**: nenhum toque no `page-header no-print` ("Baixar CSV" condicional a `relatorios.exportar` + "Imprimir") nem nas condições Jinja (`{% if m.term_code %}`, fallbacks "-"). **Comentários CSS/HTML novos NÃO citam controles do header** (lição `b75ba99`). Tooltips adicionam atributos `title` com **dados das linhas** (`m.reason`, nomes) — não são strings de controles; o RBAC de template valida botões/permissões, não dados (o padrão `title="Ajuda e Manual"` em base.html convive com os testes).

## R9 — Testes e validação (SC-006/SC-007/SC-008)

**Decision**: nenhum teste automatizado novo (seção 35 do pedido); suíte existente como regressão (baseline antes, focado durante, completo depois). Run focado: `pytest tests/test_report_print_smoke.py tests/test_movements.py tests/test_help.py tests/test_rbac.py -q` (o smoke renderiza `/reports/movements`; movements/help exercitam a página e o domínio; rbac o gate de exportação). Validação visual com medição real (V0–V6) registrada em `validacao.md` no formato das 036–041, **com verificação de impressão obrigatória** e conferência do tooltip no navegador (hover nas textuais).

## R10 — Preservação da impressão (C-6/FR-016/US3) — atenção extra ao ellipsis

**Decision**: a 042 NÃO edita nenhuma regra do bloco C1–C10 (`style.css`, compartilhado). O bloco de segurança `@media print` no `<style>` do template (precedente da 041) neutraliza em `.movrep-table`: `table-layout: auto !important; width: 100% !important; min-width: 0 !important`, `white-space: normal !important` em `th/td`, `width: auto !important` nas `col` — **e também nos spans internos `.movrep-ellip`** (`white-space: normal !important; overflow: visible !important; text-overflow: clip !important`): o C7 global só atinge `td/th`, e sem isso o ellipsis do span continuaria cortando o texto no papel. Tooltips não renderizam no papel (UI de hover) — sem tratamento. A âncora `class="card p-4 report-print"` permanece intacta (fixada por `test_report_print_smoke.py`).

**Alternatives considered**: *editar C7/C8 globais para alcançar spans*: rejeitado — bloco compartilhado com os outros 2 relatórios; *manter `truncate-2` no Motivo para o C8 cuidar do papel*: rejeitado — FR-010 substitui o mecanismo, e a neutralização escopada cobre o papel.

## R11 — Medição local com WeasyPrint (opcional, padrão 039/041)

**Decision**: reusar o script local (padrão `specs/041-relatorio-contabil-larguras-colunas/validar_local.py`): TestClient + login admin + seed de edge cases (motivo longo, origem/destino com e sem custodião, termo presente/ausente, tipo com label longo), medição das `<col>` via árvore de boxes em `media_type="screen"` (distribuição de tela) e `"print"` (V6 — paper). Limitações conhecidas: WeasyPrint usa fonte fallback (por isso os pisos ×1,25–1,30) e não impõe `min-width` de tabela em viewports pequenas (verificar pisos por coluna, não pela tabela); tooltips não são renderizados/medidos (verificação de tooltip é manual no navegador — V2/V6 do quickstart).
