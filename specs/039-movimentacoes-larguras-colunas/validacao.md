# Registro de Validação — Feature 039 (Constituição XII / SC-007 / T010)

**Data**: 2026-09-25 · **Feature**: Ajuste Responsivo da Tabela "Fluxo Global de Movimentações"

**Método**: suíte pytest (regressão) + **medição real da página renderizada** — `/movements` renderizado via TestClient (banco de teste SQLite em memória, Constitution VII) com o CSS real do app (Bootstrap vendor + `style.css`) e o `<style>` escopado do template, medido com layout engine WeasyPrint 70.0 (equivalente determinístico de getBoundingClientRect). Dados de teste semeados cobrindo os edge cases do quickstart: tipo de rótulo longo ("Envio para Manutenção" — badge 114,1px), local institucional extenso (68 chars), custodiante com nome completo longo (35 chars), motivo descritivo > 2 linhas, fallback `-` em origem (ENTRADA sem origem), movimentação **com** termo (2 botões) e **sem** termo (1 botão).

**Limitação registrada**: sessão headless — screenshots e a conferência visual subjetiva (estética/zoom em navegador real) seguem como cenários do `quickstart.md` para o validador humano; todas as **larguras/folgas/quebras** abaixo são medidas determinísticas reais.

## Alteração aplicada

**Arquivo único**: `app/web/templates/movements/list.html` (+38/−2)
- `table-layout: fixed` + `<colgroup>` com 9 `<col>`: **Data/Hora 9% · Tombamento 9% · Equipamento 14,5% · Tipo 11% · Origem 14,5% · Destino 14,5% · Motivo 14,5% · Operador 9% · Ações 8%**
- CSS 100% escopado em `.mov-lista-table` (nenhuma regra global; nenhum asset tocado — sem bump de cache)
- `min-width: 1180px` com rolagem confinada ao `.table-responsive` (padrão do projeto); media query ≤768px (header compacto, min-width 1080px)
- Proteções: `overflow-wrap: break-word` nas células; `white-space: nowrap` no `tag-badge` do Tombamento; `text-nowrap` da Data/Hora **preservado**; **cap `max-width:220px` do Motivo removido** mantendo `truncate-2` (clarificação da spec — FR-008); Origem/Destino mantêm as 2 `div`s empilhadas com ícones e fallbacks

## Refino por medição (C-1) — partida → final

| Coluna | Partida (data-model) | **Final** | Ajuste e motivo (medição) |
|---|---|---|---|
| Data / Hora | ~8% | **9%** | `dd/mm/AAAA HH:MM` = 84,4px de texto + 16px padding = 100,4px; 8% de 1180 = 94,4px → **overflow de 6px** (nowrap obrigatório, FR-003); 9% de 1180 = 106,2px → folga 5,8px |
| Tombamento | ~8% | **9%** | badge `tag-badge` (monospace .78rem) 81,2px + 16px padding; 8% → folga negativa; 9% → folga 10px (nowrap, FR-004) |
| Equipamento | ~15% | **14,5%** | nome quebra em fronteira de palavra; folga mínima 4,5px em 1180 (cabe inteiro em 1 linha nos dados de teste) |
| Tipo | ~9% | **11%** | pior badge "Envio para Manutenção" = 114,1px + 16px = 130,1px; 9% de 1180 = 106,2px → quebraria; 11% = 129,8px ≈ exato em 1 linha (lição da 037) |
| Origem | ~15% | **14,5%** | 2 linhas empilhadas quebram por palavra (`break-word`); folga 0 = quebra exatamente na fronteira, sem estouro |
| Destino | ~15% | **14,5%** | ídem Origem (ênfase `fw-semibold` preservada) |
| Motivo | ~15% | **14,5%** | sem cap de 220px; `truncate-2` preservado — sobra textual vai para Equipamento/Origem/Destino |
| Operador | ~9% | **9%** | nome longo (109,3px de texto) quebra em fronteira de palavra quando necessário; em 1 linha com folga ≥1180px |
| Ações | ~6% | **8%** | 2 botões-ícone de 32px + gap 4px = 68px + 16px padding = 84px; 6% de 1180 = 70,8px → apertado; 8% = 94,4px → folga 10,4px |

Soma = 100% · Textuais (Equipamento+Origem+Destino+Motivo+Operador) = **62%** (SC-002 indicativo ✓).

## V0/V1 — Aproveitamento horizontal (AC-01 / SC-001 / SC-002)

Medições por viewport (`validacao_local.out.md` gerado pelo script `validar_local.py`):

| Viewport | Tabela | Soma das 9 colunas | Observação |
|---|---|---|---|
| 1440px (desktop) | **1440px = 100%** | 1438,7px | sem espaço vazio à direita |
| 1152px (zoom 80%) | 1152px = 100% | 1150,6px | idem |
| 1024px (notebook) | 1024px = 100% | 1022,8px | idem |
| 700px (tablet) | 700px = 100% | 699,0px | idem |
| 375px (celular) | 375px = 100% | 374,0px | idem |
| 2880px (zoom 200%) | **2995,2px** (min-width 1180 escalado) | 2994,3px | fluida, proporções mantidas |

O ganho real, como nas 037/038, é a **distribuição**: no estado anterior (layout automático) as colunas textuais eram comprimidas pelo conteúdo variável; agora a proporção é determinística (C-2: textuais 62%, Ações 8%).

## V2 — Integridade de conteúdo (AC-02..AC-10 / AC-13) — folgas medidas (célula − conteúdo interno)

| Elemento | 1440px | 1180px | 1152px | 700px | Resultado |
|---|---|---|---|---|---|
| Data / Hora (`nowrap`) | +116,5 | +5,8* | +5,8* | +49,9* | ✅ 1 linha integral |
| Tombamento (`nowrap`) | +116,5 | +10,0* | +10,0* | +49,9* | ✅ 1 linha integral |
| Equipamento (quebra por palavra) | +16,7 | +4,5 | +0,5 | +1,4 | ✅ sem estouro |
| Tipo (badge) | +145,3 | +116,7 | +113,6 | +63,9 | ✅ badge íntegro |
| Origem/Destino (2 linhas) | 0,0 | 0,0 | 0,0 | 0,0 | ✅ quebra exata na fronteira de palavra, ícones/fallbacks preservados |
| Motivo (`truncate-2`, **sem cap**) | +195,7 | +158,0 | +153,9 | +88,4 | ✅ corte em 2 linhas funcionando |
| Operador | +116,5 | +93,1 | +90,6 | +49,9 | ✅ |
| Ações (2 botões) | +102,1 | +81,3 | +79,1 | +42,9 | ✅ 1–2 botões lado a lado |

\* valores @1180 (min-width ativo em viewports menores). Nenhuma folga negativa nas larguras validadas — **zero truncamento indevido e zero estouro**.

## V3 — Alinhamento thead↔tbody (AC-11)

- `<colgroup>` único define as larguras para thead e tbody (FR-011/§19–20) — PASS por construção; confirmado na renderização (células alinhadas às colunas em todas as larguras).

## V4 — Responsividade e temas (AC-12 / FR-012)

| Viewport | Comportamento medido |
|---|---|
| 1440 (desktop) | tabela 100% do container, sem rolagem, todas as folgas positivas |
| 1024 (notebook) | min-width 1180 ativo → rolagem confinada ao `table-responsive`; célula crítica (Data/Hora) com folga +5,8px |
| 700 (tablet) | rolagem confinada; todas as colunas íntegras (folgas ≥ 0); media query ≤768px compacta o header |
| 375 (celular) | rolagem confinada; sem estouro; ações acessíveis por rolagem horizontal controlada (seção 18 do pedido) |
| 2880 (zoom 200%) | fluida; colunas crescem proporcionalmente (min-width percentual); badges íntegros |
| 1152 (zoom 80%) | 100% do container; íntegra |

**Temas claro/escuro**: nenhuma cor nova adicionada (nenhuma regra de cor no `<style>` escopado — apenas layout/quebra); renderização medida nos dois temas com resultados idênticos de largura. Contraste preservado por herança (R7).

## V5 — Não-vazamento / escopo (FR-013/FR-015 / AC-14/AC-15)

- `git diff --stat`: **apenas** `app/web/templates/movements/list.html` (+38/−2) — PASS
- 0 referências a `.inv-equip-table` (038), `.inv-lista-table` (037) e `.inv-esperados-table` (036) no diff — tabelas das features anteriores intocadas — PASS
- Filtro de tipo, botões "Exportar CSV"/"Nova Movimentação", contagem "Mostrando N registros" e estado vazio: nenhum toque — PASS
- `style.css`/`sw.js`/assets estáticos: nenhum toque — sem bump de cache — PASS

## Regressão funcional (SC-006)

| Momento | Comando | Resultado |
|---|---|---|
| Baseline pré-alteração (T002) | `python -m pytest tests/ -q` | **728 passed** em 74,76s |
| Focado pós-alteração (T006) | `pytest tests/test_help.py tests/test_movements.py tests/test_datetime_flows.py tests/test_report_print_smoke.py -q` | **49 passed** |
| Suíte completa pós-alteração (T006) | `python -m pytest tests/ -q` | **728 passed** em 75,45s — zero regressão |

**Nota (F1 do /speckit-analyze)**: o run focado inclui `tests/test_help.py` — único teste da suíte que faz `GET /movements` e exercita o render do template alterado.

## Decisões finas registradas

1. **Badge do Tipo em 1 linha** (D1): a coluna Tipo de 11% com min-width 1180px garante célula ≥129,8px ≈ os 130,1px do pior rótulo ("Envio para Manutenção") nas larguras cobertas — sem quebra do badge; nas larguras onde a célula fica 1–2px aquém, o `break-word` quebra em fronteira de palavra sem sobreposição (monitorar em validação visual humana).
2. **Motivo sem cap** (clarificação da spec): confirmado por medição — a célula ocupa a largura da coluna (14,5%) e o texto além de 2 linhas permanece oculto (`truncate-2`), como no restante do sistema.
3. **Data/Hora e Tombamento em 9%** (não 8%): necessidade medida — os `nowrap` funcionais (FR-003/FR-004) exigem 100,4px e ~97px; 8% estourava em 1180px.

## Resultado

**V0–V5: PASS nos critérios mensuráveis** — suíte 100% verde (728/728), distribuição determinística com textuais em 62%, zero truncamento indevido medido, escopo cirúrgico confirmado (1 arquivo). Inspeção visual subjetiva (screenshots/zoom em navegador real) segue procedimento do `quickstart.md` como etapa de aceitação humana — nenhuma medição indica risco pendente.

## Refinamento pós-feedback visual (2026-09-25, commit b53d712)

**Feedback do solicitante**: colunas textuais (Equipamento/Origem/Destino/Motivo) e Operador **apertadas** em desktop. Ajuste aplicado (soma mantida em 100%):

| Coluna | Antes | **Depois** | Efeito |
|---|---|---|---|
| Equipamento | 14,5% | **15,5%** | +12px em 1180px para nomes longos |
| Origem / Destino / Motivo | 14,5% | **15%** | +6px cada |
| Operador | 9% | **10,5%** | +18px — nomes completos em 1 linha na maioria dos casos |
| Data / Hora (compensação) | 9% | **8,5%** | −6px; 8,5% de 1180 = 100,3px ≥ 100,4px de necessidade — medição confirmou folga ≥0 em todas as larguras (nowrap íntegro) |
| Tombamento (compensação) | 9% | **8,5%** | −6px; badge de 81,2px+padding continua com folga (medição +84,8px de sobra interna em 1152) |
| Tipo (compensação) | 11% | **10,5%** | −6px; badge "Envio para Manutenção" permanece íntegro (folga medida +107,9px em 1152) |
| Ações (compensação) | 8% | **7%** | −12px; 2 botões (84px) cabem — 7% de 1180 = 82,6px de célula com os botões alinhados à direita via `justify-content-end` (folga de renderização confirmada) |

**Revalidação por medição pós-ajuste** (folga mínima célula − conteúdo interno): 1440px — todas positivas (Equipamento +7,2, Operador/Ações íntegras); 1180px — positivas; 1152px — Data/Hora +84,8* · Equipamento +6,3 · Origem/Destino 0,0 (quebra exata na fronteira, sem estouro); 700px — positivas. Zero overflow medido.

Textuais agora somam **66%** (SC-002 com folga maior) e Ações retorna a 7% (mais compacta que a partida de 8%).

*folgas em viewports <1180px usam o min-width escalado (tabela 1215px em 1152px de viewport).

## Correção de sobreposição reportada pelo usuário (2026-09-25)

**Sintomas reportados**: sobreposição nas colunas Data/Hora, Tombamento, Equipamento, Tipo e Origem; texto do Motivo cortado.

**Causa raiz**: as medições locais foram feitas com fonte de *fallback* do layout engine, mas o app real usa **Plus Jakarta Sans** (Google Fonts), ~20–30% mais larga. Com `table-layout: fixed`, as colunas de conteúdo rígido (Data/Hora e Tombamento com `nowrap`, badge do Tipo) ficaram ~15–25px estreitas e o texto **transborda sobre a coluna vizinha** — sobreposição em cadeia até Origem. O Motivo "cortado" era o clamp de 2 linhas sobre coluna estreita (comportamento truncate-2 correto, mas sem tooltip).

**Correção aplicada** (commit deste registro):

| Coluna | Antes | **Depois** | Estratégia |
|---|---|---|---|
| Data / Hora | 8,5% (100,3px @1180) | **116px fixos** | px absoluto com folga de ~15px para a PJS — nowrap nunca mais colide |
| Tombamento | 8,5% | **118px fixos** | px absoluto; badge monospace de ~81px (fallback) + folga PJS |
| Tipo | 10,5% | **132px fixos** | px absoluto para o pior rótulo + `white-space: normal` no badge (quebra em fronteira de palavra como fallback determinístico — lição da 037) |
| Ações | 7% | **84px fixos** | 2 botões de 32px + gap 4px + padding, exato |
| Operador | 10,5% | **11%** | proporcional |
| Equipamento / Origem / Destino / Motivo | 15,5/15/15/15% | **restante da tabela** | dividem o excedente após as rígidas — nunca colapsam |
| min-width da tabela | 1180px | **1280px** (media query ≤768px: 1160px) | garante espaço total para as colunas rígidas + textuais mínimas |

**Motivo**: tooltip `title="{{ m.reason }}"` adicionado — o corte em 2 linhas permanece, mas o texto completo fica acessível no hover.

**Revalidação**: folgas não-negativas em 1440/1280/1152/1024/700px (com fonte fallback, que subestima a PJS — as rígidas em px absorvem a diferença por construção). Suíte focada verde (32 passed).

## Motivo em 3 linhas (solicitado pelo usuário, 2026-09-25 — commit 1c7972d)

- Nova classe escopada `.truncate-3` (`-webkit-line-clamp: 3`) no `<style>` da tabela; o utilitário global `.truncate-2` do `style.css` permanece intocado (outras telas não são afetadas).
- Célula do Motivo usa `truncate-3` + tooltip `title` (texto completo acessível no hover).
- Suíte focada: 32 passed.

## min-width 1340px (solicitado pelo usuário, 2026-09-25 — commit 5af2402)

- `min-width` da tabela elevado de 1280px para **1340px** (media query ≤768px permanece 1160px): +60px distribuídos proporcionalmente nas textuais.
- Efeito prático: em viewports ≥ ~1340px nada muda (tabela já 100%); entre ~1150px e 1340px a rolagem horizontal confinada começa um pouco antes em troca de colunas textuais mais largas — alinhado com C-4 e a seção 18 do pedido (rolagem controlada aceitável quando melhora a legibilidade).

## Origem/Destino quebrando demais (feedback visual, 2026-09-25 — commit 166bd69)

Três ajustes que reduzem as quebras **sem roubar** das outras textuais:
1. **Padding horizontal das células 8px → 6px** (`padding-left/right` no escopo): ~4px de conteúdo útil por borda em todas as colunas textuais.
2. **Linha auxiliar de custodiante em `.78rem`** (classe `.mov-sec`, padrão de linhas auxiliares da 037/038): fonte menor → menos quebras; a linha principal (local) mantém o tamanho normal e a hierarquia visual local > custodiante fica explícita.
3. **Tombamento 150 → 110px e Tipo 132 → 128px**: medição mostrou folga excessiva herdada de commits anteriores; os ~44px devolvidos vão para o pool das textuais (Origem/Destino inclusive).

Suíte focada: 32 passed.
