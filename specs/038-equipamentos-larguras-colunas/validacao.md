# Registro de Validação — Feature 038 (Constituição XII / SC-007 / T010)

**Data**: 2026-09-25 · **Feature**: Ajuste Responsivo da Tabela "Equipamentos"
**Método**: suíte pytest (regressão) + inspeção visual/medição real da página renderizada (dados de teste: 4 equipamentos cobrindo os edge cases — status-pill mais longo "Em Manutenção", local institucional longo de 57 caracteres, responsável com nome longo + matrícula, fallback "Estoque Livre"/"Estoque Central", S/N com `<code>`, 2 botões de ação) — renderização via TestClient com SQLite temporário e embutimento do CSS real do app (bootstrap + style.css) no HTML de preview.

## Alteração aplicada

**Arquivo único**: `app/web/templates/assets/list.html` (+43 linhas)
- `table-layout: fixed` + `<colgroup>`: **Tombamento 12% · Equipamento/Modelo 20% · Categoria 9% · Status 12% · Responsável 14% · Localização 17% · Valor 9% · Ações 7%**
- CSS 100% escopado em `.inv-equip-table` (nenhuma regra global; nenhum asset tocado — sem bump de cache)
- Padding 8px nas colunas compactas (Tombamento, Status, Valor) e 4px em Ações
- `min-width: 1180px` com rolagem confinada ao `.table-responsive` (padrão do projeto)
- Tombamento `nowrap` integral (FR-003); quebras textuais em fronteira de palavra (`break-word`)

## V0 — Baseline antes/depois (seção 27 do pedido)

| Métrica (desktop 1440px, container 1188px) | Antes | Depois |
|---|---|---|
| Tombamento | **quebrado em 2 linhas** ("TMB-2026-" / "1204") | 1 linha integral (badge 94–112px, célula 127px) |
| Status | 12,9% (espremendo textuais) | 12% com folga real (127px ≥ 121,6px do pior pill) |
| Ações | 8,4% | 7% (75px ≥ 68px dos 2 botões) |
| Textuais (Equip+Resp+Local) | 49,2% | **51%** dominando |
| Aproveitamento do container | 92,4% (tabela não expandia) | **100%** (fixed + width:100%) |

## V1 — Aproveitamento horizontal (AC-01)

- Desktop 1440: tabela 1188,1px = **100% do container** (antes 92,4%) — PASS
- Zero espaço vazio à direita; distribuição proporcional ao conteúdo (FR-002/C-2) — PASS

## V2 — Integridade de conteúdo (AC-05/06/07/08/12) — medições por célula

| Elemento | Necessário | Útil (célula − padding) | Resultado |
|---|---|---|---|
| Badge tombamento (nowrap) | 112,1px | 127px | ✅ 1 linha |
| Pior status-pill "Em Manutenção" | 121,6px | 127px | ✅ 1 linha (altura 27px) |
| Valor monetário maior "R$ 120.000,00" | 85,1px | 91px | ✅ sem quebra (nowrap preservado) |
| 2 botões de ação | 68px | 75px | ✅ 1 linha, lado a lado |
| Nome + marca + S/N `<code>` | — | col. 20% | ✅ quebra só em fronteira de palavra |
| Fallbacks "Estoque Livre"/"Estoque Central" | — | — | ✅ presentes |

**Correções aplicadas durante a validação** (refino por medição, C-1/C-5):
1. Partida 11% → **12% Tombamento** (badge de 112,1px não caberia em 11% com padding 8px; e o scrollbar surgia com min-width 1200 > 1188 internos → min-width ajustado para **1180px**, eliminando rolagem desnecessária no desktop).
2. Valor 8% → **9%** (déficit medido de 5px: 85,1px de conteúdo vs 80px úteis).
3. Ações com padding 4px (déficit de 0,8px com padding 8px).

## V3 — Alinhamento thead↔tbody (AC-10)

- `<colgroup>` único define as larguras para thead e tbody (FR-011/§19) — PASS
- Headers verificados visualmente alinhados com o conteúdo em todas as larguras — PASS

## V4 — Responsividade (FR-012/AC-11)

| Viewport | Comportamento | Integridade | Overflow página |
|---|---|---|---|
| 1440 (desktop) | tabela 100% do container, sem rolagem | ✅ todos os elementos | ✅ nenhum |
| 1024 (notebook, 929px úteis) | rolagem confinada (1180 > 929) | ✅ pill/tomb/valor/botões medidos íntegros | ✅ nenhum |
| 700 (tablet) | rolagem confinada, scrollbar visível | ✅ 2 botões acessíveis, 1 linha | ✅ nenhum |
| 375 (celular) | rolagem confinada; botões verificados acessíveis ao final da rolagem (`scrollIntoView` + medição) | ✅ | ✅ nenhum |
| 2880 (zoom 200%) | fluida, sem rolagem (2494px), pill íntegro | ✅ | ✅ nenhum |
| Zoom 80% (1152) | rolagem confinada, tudo íntegro | ✅ | ✅ nenhum |

**Temas**: dark e light verificados com screenshots — pills legíveis e íntegros nos dois (nenhuma regra de cor adicionada; herança preservada).

## V5 — Não-vazamento / escopo (FR-013/015, AC-14)

- `git diff --stat`: **apenas** `app/web/templates/assets/list.html` (+43/−1) — PASS
- 0 referências a `.inv-esperados-table` (036) e `.inv-lista-table` (037) no diff — tabelas das features anteriores intocadas — PASS
- Filtros, botões do header, paginação e demais componentes da página: nenhum seletor global adicionado — PASS

## Regressão funcional (SC-006 / F1 decidido: suíte completa em T006)

- Baseline pré-alteração: **728 passed**
- Suíte completa pós-alteração (T006): **728 passed em 88,77s** — zero regressão
- Suíte inclui `test_assets.py`, `test_movements.py` e `test_navbar.py` (tela exercitada), além de toda a aplicação

## Decisão registrada (D1 do /speckit-analyze)

Status-pill mantido em **linha única** (não quebra): a coluna Status de 12% com min-width 1180px garante 127px úteis ≥ 121,6px do pior rótulo ("Em Manutenção") em todas as larguras cobertas — sem necessidade de realinhar o `::before` do ponto. Escolha validada por medição em 1440/1152/1024/700/375/2880.

## Resultado

**V0–V5: PASS em todos os critérios** — 14/14 ACs satisfeitos, suíte verde, escopo cirúrgico confirmado.
