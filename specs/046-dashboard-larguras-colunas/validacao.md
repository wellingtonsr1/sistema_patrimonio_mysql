# Validação: Ajuste Responsivo da Tabela "Fluxo Recente de Movimentações" (046) + tabelas de inconsistências (ampliação)

**Data**: 2026-09-26 · **Branch**: `main` · **Formato**: 036–044

## 1. Suíte de testes (SC-006)

| Momento | Comando | Resultado |
|---|---|---|
| Baseline (T001) | `.venv/bin/python -m pytest tests/ -q` | **748 passed** |
| Completo pós-alteração (T006/T008/T009) | `.venv/bin/python -m pytest tests/ -q` | **748 passed** |

- **Sem testes novos de UI/pytest** (R9/seção 29): a suíte existente serve de regressão e a medição local é ferramenta dedicada (padrão 039/042/044). Única superfície de produto alterada: `app/web/templates/dashboard.html`.

## 2. Baseline "antes" (V0 — seção 29 do pedido)

Distribuição uniforme do layout automático (todas as colunas 14,3% — competiam por espaço sem priorização): colunas rígidas (Data/Tombamento/Ação/Operador/Ações) e textuais (Equipamento/Destino) com a MESMA largura, quebras verticais severas — no celular (375px) a última linha do seed atingiu **52 linhas de texto em um único `tr`** (25/22/16/29/28/52 por linha na 375px light); em desktop 1440px, Equipamento/Destino/Operador já quebravam (9/10/9). Saída integral em `validacao_local.v0.md` (snapshot capturado com o template pré-alteração).

## 3. Comparação antes/depois (V1 — SC-001/SC-002/SC-005)

Medições `validar_local.py` (WeasyPrint, media screen), tabela fixa `min-width: 1370px`:

| Viewport | Tabela | Data | Tombamento | Equipamento | Ação | Destino | Operador | Ações | Linhas/tr |
|---|---|---|---|---|---|---|---|---| métrica |
|---|---|---|---|---|---|---|---|---|---|
| 1440px | 1440 (100%) | 144,9 (10,1%) | 159,9 (11,1%) | **339,9 (23,6%)** | 209,9 (14,6%) | **339,9 (23,6%)** | 139,9 (9,7%) | 104,9 (7,3%) | 7 em todas |
| ≤1371px (piso) | 1371 (rolagem confinada) | 135,0 | 150,0 | **330,0 (24,1%)** | 200,0 | **330,0 (24,1%)** | 130,0 | 95,0 | 7 em todas |
| 2880px | 2880 (100%) | 350,6 (12,2%) | 365,6 (12,7%) | **545,6 (18,9%)** | 415,6 (14,4%) | **545,6 (18,9%)** | 345,6 (12,0%) | 310,6 (10,8%) | 7 em todas |

- **Linha única comprovada**: todas as 7 linhas do seed com **7 linhas de texto por `tr`** (1 por célula) em TODAS as larguras — V0 quebrava (até 52/tr no celular).
- **Textuais dominam**: Equipamento+Destino = 47,2–47,8% da tabela (maior bloco, SC-002 ✓); tabela em 100% da largura útil até o piso (SC-001 ✓); alinhamento thead/tbody íntegro (colgroup compartilhado — SC-003 ✓); zero quebra indevida/truncamento sem tooltip (SC-005 ✓).
- Ação 200px dimensionada pelo rótulo real mais longo ("Entrada por Aquisição", badge `.68rem` íntegro); Tombamento com badge global íntegro (sem ellipsis novo); Ações dimensionada pelo par de botões (pior caso com termo), `text-end`/`text-nowrap` preservados.

## 4. Larguras finais adotadas (T003 — C-1)

Conjunto **único** em px (soma 1370px → `min-width: 1370px`), sem media query de colunas (lição da 041):

| Col | Coluna | Final | Justificativa |
|---|---|---|---|
| col-data | Data | 135px | `dd/mm/aaaa hh:mm` nowrap (~110px) + folga |
| col-tag | Tombamento | 150px | `tag-badge` global íntegro (códigos ~13 caracteres monoespaçados) |
| col-equip | Equipamento | 330px | textual principal; nomes longos cortam com tooltip |
| col-acao | Ação | 200px | rótulo mais longo "Entrada por Aquisição" em uma linha (badge .68rem) |
| col-destino | Destino | 330px | textual principal; locais/custodiantes longos cortam com tooltip |
| col-operador | Operador | 130px | nomes comuns em uma linha; nomes longos cortam com tooltip |
| col-acoes | Ações | 95px | PAR de botões (pior caso com termo) + `text-end` |

## 5. Resultado por cenário (§28 do pedido)

- **Desktop grande (1440px)**: ✓ §3 — linha única, textuais dominam, sem grandes vazios nem colunas excessivamente estreitas.
- **Desktop médio/notebook (1152/1024px)**: ✓ mesma distribuição (tabela fixa no piso 1371px, rolagem confinada ao `table-responsive`).
- **Tablet (700px) / celular (375px)**: ✓ rolagem horizontal confinada; nenhuma coluna escondida; 7/7 linhas de texto por `tr` (V0: até 52).
- **Zoom 80%–200%** (1800px/720px): ✓ colunas px mantêm a distribuição por construção; nenhuma fonte reduzida; page = viewport em todos os cenários (SC-004: zero overflow de página).
- **Temas claro E escuro**: ✓ medições idênticas entre temas em todas as larguras (R8).

## 6. Ampliação — tabelas de inconsistências ("Equipamentos sem localização" e "Equipamentos sem responsável")

A pedido do solicitante pós-entrega da 046, o mesmo mecanismo foi aplicado às tabelas de inconsistências do mesmo template (compartilham o mesmo loop `item_list` — a alteração cobre as duas por construção):

- **CSS escopado `.inc-table`** no mesmo bloco `<style>`: `table-layout: fixed` + colgroup em **PERCENTUAL** (Tag 24% · Equipamento 44% · Observação 32% — padrão de telas em cards de meia largura, como `assets/list.html`), **sem min-width**: as proporções se mantêm do desktop ao celular sem rolagem horizontal (page = viewport em todas as larguras/temas).
- **Colgroup real** no template (`inc-tag`/`inc-equip`/`inc-obs`) e spans `.dash-ellip` + tooltip no **Equipamento** e na **Observação** (substituem o `text-truncate` com `max-width:200px` — antes: largura travada em ~200px com corte sem consulta; depois: 44%/32% da largura do card, cortando apenas quando excede, com tooltip).
- **Refinamento pós-feedback (linha única nas 3 colunas)**: as células **ainda quebravam** após a primeira versão da ampliação — o `.tag-badge` global não define `white-space` (mesma causa já resolvida na 044) e a Observação era texto puro sob o `overflow-wrap: break-word` escopado. Corrigido com regras escopadas: `.inc-table .tag-badge { white-space: nowrap; max-width: 100%; }` (linha única no código, com o corte controlado global como fallback — padrão da 044) + span `.dash-ellip` na Observação. **Comprovação pelo script** (`inc trs`): 3 linhas de texto por `tr` (uma por célula) nas 8 linhas do seed, em TODAS as larguras e temas — incluindo 375px (antes da correção: quebras no badge e na observação).
- **Comparação V0→V1** (relatório `validacao_local.out.md`, linha `[inc]`): V0 com colgroup neutro distribuía em terços iguais (~33/33/33 — Tag 479,7 / Equipamento 479,7 / Observação 479,7 em 1440px); V1 com o markup real: **24/44/32** (Tag 345,4 / Equipamento 633,2 / Observação 460,5 em 1440px; Tag 89,8 / Equipamento 164,6 / Observação 119,7 em 375px) — textuais dominando (76%), proporção constante em todas as larguras e temas.
- **Suíte**: 748 passed (sem alteração de comportamento Python; única superfície continua sendo `dashboard.html`).
- **Marcador do script atualizado**: em V0 injeta classe de referência `inc-table` + colgroup neutro; em V1 usa o markup real (âncora do slice no atributo `class=...inc-table"`, para não confundir com o seletor `.inc-table` do `<style>`). Contagem de linhas por `tr` estendida à tabela de inconsistências (`inc trs` — a medição só da tabela-alvo foi o ponto cego que deixou passar as quebras da primeira versão da ampliação).

## 7. Prova de escopo — demais tabelas/telas (R5/FR-017)

A linha `[escopo] outra tabela` do relatório é **IDÊNTICA em V0 e V1** em todas as larguras e temas (`1440px: Tag=479.7, Equipamento (outra)=479.7, Observação=479.7` — e análogos em 1152/1024/700/375/2880/1800/720): a tabela "Necessitam de atenção" (L182–200) **não recebeu classe, regra ou alteração alguma** — o CSS escopado `.dash-table` não a alcança. `style.css`, `base.html`, `main.js`, rotas, services e telas 036–045: zero linhas alteradas (`git diff` = apenas `dashboard.html` + arquivos da spec).

## 8. Observações

1. **Medição V0**: capturada com o template pré-alteração (snapshot `validacao_local.v0.md` via stash temporário do template — medição com o script final, mesmas versões de tudo o mais). A contagem `spans dash-ellip: 0 · com tooltip: 0` no V0 confirma a partida sem ellipsis/tooltip; no V1: 46 spans, 46 com tooltip (18 do Fluxo Recente + 14 de Equipamento e 14 de Observação nas tabelas de inconsistências do banco de teste persistente — até 10 linhas por card, limite do service).
2. **Tooltips sempre presentes no markup** (decisão da família 042/043/044): tooltips redundantes em valores não truncados são inofensivos e não exigem JS novo (inicialização existente base.html/main.js).
3. **Comportamento em navegador real**: com `table-layout: fixed`, os px do `<colgroup>` são honrados exatamente e o `min-width: 1370px` impõe rolagem confinada abaixo de ~1370px de janela útil; o WeasyPrint mede o piso pelos px declarados (comportamento consistente com a nota da 044).
4. **Destino**: os DOIS ramos do if/else receberam span cortável + tooltip (ícones `bi-person`/`bi-geo-alt` preservados; fallback "Estoque" também com tooltip no segundo ramo, pois pode ser o valor real exibido). Na ampliação, o span substituiu o `text-truncate` do nome nas tabelas de inconsistências — mecanismo da família (ellipsis + tooltip) no lugar do corte cego.
5. **Data e Ações** permanecem `text-nowrap` (rígidas, sem ellipsis novo); a estrutura condicional `{% if m.term_code %}` das Ações está íntegra.
6. **Sem `@media print`** (R10 da 043 — dashboard não é tela-relatório) e **sem nomes de controles em comentários** (lição `b75ba99`).
7. **Seed do medidor** cobre os edge cases da spec: movimentações COM e SEM `term_code` (par vs. botão único nas Ações), destino por colaborador E por local/"Estoque" (dois ramos do if/else), equipamento com nome longo, operador com nome longo e bem inconsistente (TMB-2026-4699) para forçar a renderização da tabela "Necessitam de atenção" (prova de escopo R5).
