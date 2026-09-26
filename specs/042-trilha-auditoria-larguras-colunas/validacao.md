# Validação: Ajuste Responsivo da Tabela "Trilha de Auditoria & Fluxo" (042)

**Data**: 2026-09-25 · **Branch**: `042-trilha-auditoria-larguras-colunas` · **Formato**: 036–041

## 1. Suíte de testes (SC-006)

| Momento | Comando | Resultado |
|---|---|---|
| Baseline (T002) | `python -m pytest tests/ -q` | **728 passed** |
| Focado pós-alteração (T006) | `pytest tests/test_report_print_smoke.py tests/test_movements.py tests/test_help.py tests/test_rbac.py -q` | **65 passed** |
| Completo pós-alteração (e após ajuste de feedback) | `python -m pytest tests/ -q` | **728 passed** |

## 2. Baseline "antes" (V0 — seção 36 do pedido)

Medição com `validar_local.py` (screen 1440px, layout automático):

| | Data/Hora | Tombamento | Equipamento | Tipo | Origem | Destino | Status | Motivo | Operador | Termo |
|---|---|---|---|---|---|---|---|---|---|---|
| ANTES (px) | 121,9 | 106,1 | 99,0 | 160,3 | **78,8** | 93,0 | 130,8 | **106,8** | **75,5** | 92,8 |

- **Problema documentado**: tabela de 1395,9px mas soma das colunas **1065px** (~331px desperdiçados); Origem (78,8px) e Operador (75,5px) espremidas; Motivo truncado em 200px **sem tooltip** (dado indisponível — C-7); quebras verticais frequentes nas textuais.
- Referência de impressão V6 capturada (paper com C1–C10 ativos).

## 3. Comparação antes/depois (V1 — SC-001/SC-002)

Conjunto final (1440px screen):

| | Data/Hora | Tombamento | Equipamento | Tipo | Origem | Destino | Status | Motivo | Operador | Termo |
|---|---|---|---|---|---|---|---|---|---|---|
| DEPOIS (px) | 146 | 126 | **138** | 136 | **146** | **146** | 130 | **156** | 106 | **146** |

- **Decisão final de trade-off (solicitante)**: caber em 1440px **sem rolagem** aceitando mais reticências — soma 1376px / tabela 1390px (100% do container em 1440px). Com a fonte real, reticências aparecerão com frequência nas textuais — sempre com tooltip Bootstrap com o valor completo (C-7).
- Pisos anti-estouro preservados nas `nowrap`: Data/Hora 146 · Tombamento 126 · Status 130 · **Termo 146** (cobre `TR-INIC-2026-0039`, 15–17ch reais) — identificadores e data nunca quebram nem estouram (AC-02/03/11).
- **Linha garantida**: rígidas em nowrap (Data/Hora com `text-nowrap` original; Tombamento/Status/Termo via `.nw`); textuais com `.movrep-ellip` (nowrap + ellipsis) — nenhuma quebra vertical; **Tipo sem ellipsis** (FR-006: badge pode quebrar entre palavras quando inevitável; pior caso "Entrada por Aquisição" cabe em 150px úteis).

## 4. Larguras finais adotadas (T003/T005 — C-1, após iteração de feedback real)

Conjunto **único** em px (soma 1376px → `min-width: 1380px`), sem media query de colunas (lição da 041):

| Col | Coluna | Final | Piso verificado |
|---|---|---|---|
| c1 | Data/Hora | 146px | "24/09/2026 12:20" ≈ 127px + padding (nowrap) |
| c2 | Tombamento | 126px | mono 10ch ≈ 103px + padding (nowrap) |
| c3 | Equipamento | 138px | ellipsis + tooltip (nomes reais longos cortam) |
| c4 | Tipo | 136px | badge **com quebra entre palavras** (`white-space: normal` escopado — o padrão Bootstrap `.badge` é nowrap e transbordava a célula fixa; FR-006; precedente 040/Departamento) |
| c5/c6 | Origem/Destino | 146px | ellipsis + tooltip por segmento (locais reais longos cortam) |
| c7 | Status | 130px | pill "Em Manutenção" ×1,25 + padding (nowrap) |
| c8 | Motivo | 156px | ellipsis + tooltip (maior textual) |
| c9 | Operador | 106px | ellipsis + tooltip |
| c10 | Termo | 146px | **termos reais 15–17ch** (`TR-INIC-2026-0039`) + padding (nowrap) — identificador nunca corta |

## 5. Resultado por cenário

- **V1 (desktop)**: ✓ §3. Sem grandes vazios; sem colunas excessivamente pequenas; linha garantida.
- **V2 (conteúdos + tooltips)**: ✓ tooltip Bootstrap em Equipamento, Motivo, Operador e segmentos de Origem/Destino — marcação server-rendered inicializada pela infraestrutura existente (`base.html:329–333`/`main.js`); Motivo sem `truncate-2`/`max-width:200px`; fallbacks "-", estrutura local+custodião, link do Termo e cores íntegros. *(Confirmação de hover no navegador no aceite final.)*
- **V3 (alinhamento/estabilidade)**: ✓ 10/10 sob os cabeçalhos; distribuição idêntica nas 4 linhas do seed e entre temas; alturas uniformes.
- **V4 (responsividade)**: ✓ colunas px idênticas de 375 a 1440px (nenhuma coluna colapsa); tabela mantém o mínimo (1533px) e rola confinada ao `table-responsive` em janelas menores (comportamento autorizado C-4); zoom 80–200% coberto pela estabilidade px; temas idênticos.
- **V5 (não-vazamento)**: ✓ `git diff` = apenas `reports/movements_report.html`; `style.css`/`sw.js` intocados; `.mov-lista-table` (039) e os outros 2 relatórios inalterados.
- **V6 (impressão — US3/SC-007)**: ✓ paper: tabela 100% da página, `table-layout:auto` (C3), **Motivo 317px no papel (texto completo — spans de ellipsis neutralizados, pois o C7 global só atinge td/th)**; smoke `report-print` verde; CSV intocado (`test_rbac.py` verde).

## 6. Zoom 80%–200%

Colunas px mantêm a distribuição em toda a faixa por construção; em zoom alto a rolagem confinada aparece antes (tabela ≥1535px), sem perda de legibilidade; nenhuma fonte reduzida.

## 7. Observações

1. **Iterações de feedback real (pós-implementação)**: (1ª) ellipsis indevido no badge de Tipo (removido — FR-006) e Termo 116px estourado (engrossado). (2ª) reticências/estouro persistiram nos dados reais: termos têm 15–17ch (`TR-INIC-{ano}-{id:04d}` — `asset_service.py:192`), nomes/locais reais excedem 170–190px → conjunto generoso (min-width 1785px) com rolagem como plano B. (3ª, **decisão final do solicitante**) troca de trade-off: **caber em 1440px sem rolagem** aceitando mais reticências → soma 1376px (min-width 1380px), pisos anti-estouro preservados nas `nowrap` (Termo 146px cobre os termos reais), tooltip Bootstrap garantindo acesso ao conteúdo completo nas textuais (C-7).
2. **Tooltip sempre presente no markup** (F3 do analyze): decisão simples — tooltips redundantes em valores não truncados são inofensivos e não exigem JS novo.
3. **Estouro do badge de Tipo (feedback real)**: o `.badge` Bootstrap carrega `white-space: nowrap` embutido — mesmo sem a classe `.nw` da célula, "Entrada por Aquisição" (bloco inquebrável ≈ 136px) transbordava o útil de ~118px sobre a coluna Origem. Correção: `.movrep-table .badge { white-space: normal; }` — quebra apenas ENTRE palavras ("Entrada por / Aquisição"), nunca no meio; no papel o C7 global já normaliza o texto. Conta no piso: c4 136px acomoda a palavra mais larga do label ("Aquisição" ≈ 74px ×1,25 + padding).
4. **WeasyPrint não impõe `min-width`**: estabilidade verificada por coluna; em navegadores reais, rolagem confinada apenas abaixo de ~1515px de janela (min-width 1380px + margens) — em 1440px caberá sem rolagem; a medição local usa fonte fallback, os pisos nowrap incluem fator da fonte real.
5. **Service Worker verificado (sw.js)**: navegação da trilha é network-only (cache-first apenas em `/inventarios/{id}/offline` e allowlist de estáticos) — as correções chegam ao navegador sem bump de cache; Ctrl+Shift+R descarta cache HTTP local.
6. O bloco de segurança de impressão cobre nowrap **e** ellipsis (spans) no papel — textos completos impressos.
7. Nenhuma interação com `tag-badge` ≤479px (este template não usa `tag-badge`).

## 8. Decisões finas

- `.movrep-ellip` em **elemento interno** (span) com `display:inline-block; max-width:100%`: tooltip por segmento em Origem/Destino sem quebrar a estrutura `<br>` condicional; `vertical-align: bottom` mantém a baseline alinhada.
- Badge de Tipo **sem ellipsis** (voltou ao markup original) — a quebra entre palavras é o fallback da spec (FR-006), não o corte.
- Termo Dimensionado para 12ch mono com fator da fonte real: identificadores nunca cortam (FR-012).
- Bloco de segurança de impressão inclui `.movrep-ellip` (`white-space:normal; overflow:visible; text-overflow:clip`) — o papel imprime o texto integral.
- Seed do medidor cobre os edge cases do quickstart (motivo longo, sem custodião, sem termo, labels longos).
