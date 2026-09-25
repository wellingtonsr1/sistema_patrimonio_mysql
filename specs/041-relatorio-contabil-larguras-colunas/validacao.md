# Validação: Ajuste Responsivo da Tabela "Relatório Contábil-Físico do Patrimônio" (041)

**Data**: 2026-09-25 · **Branch**: `041-relatorio-contabil-larguras-colunas` · **Formato**: 036–040

## 1. Suíte de testes (SC-006)

| Momento | Comando | Resultado |
|---|---|---|
| Baseline inicial | `python -m pytest tests/ -q` | 727/728 — **1 falha PRÉ-EXISTENTE** (detalhe na §7) |
| Baseline corrigido (T002) | `python -m pytest tests/ -q` | **728 passed** |
| Focado pós-alteração (T006) | `pytest tests/test_report_print_smoke.py tests/test_rbac.py tests/test_help.py -q` | **42 passed** |
| Completo pós-alteração | `python -m pytest tests/ -q` | **728 passed** |

## 2. Baseline "antes" (V0 — seção 34 do pedido)

Medição com `validar_local.py` (WeasyPrint sobre o CSS real; screen = layout de tela):

| Viewport 1440px screen | Tombamento | Descrição | Categoria | Status | Localização | Responsável | Data Compra | Valor Aquisição | Depreciação | Valor Atual |
|---|---|---|---|---|---|---|---|---|---|---|
| ANTES (%) | 7,5 | **7,8** | 9,4 | 9,2 | **6,7** | **6,9** | 6,9 | 8,9 | 6,8 | 6,5 |

**Problema documentado**: no layout automático, as textuais eram as **menores** colunas da tabela (Descrição 7,8% < Categoria 9,4%) — o quadro que o pedido (seções 3/32) manda corrigir. No papel (print), o C3 já distribuía por conteúdo (Descrição 24,0%) — referência preservada.

## 3. Comparação antes/depois (V1 — SC-001/SC-002)

| Viewport 1440px screen | Tombamento | Descrição | Categoria | Status | Localização | Responsável | Data Compra | Valor Aquisição | Depreciação | Valor Atual |
|---|---|---|---|---|---|---|---|---|---|---|
| DEPOIS (%) | 9,8 | **15,7** | 10,9 | 8,4 | **11,0** | **9,0** | 7,7 | 9,4 | 9,0 | 9,0 |

- Tabela em **100% da largura útil** (SC-001 ≥95% ✓).
- Textuais em **valores absolutos**: Descrição 219px + Localização 153px + Responsável 125px ≈ **497px** (vs ~300px no V0 — ganho real de ~65%); continuam as 3 maiores colunas em px do conjunto desktop.
- **Nota sobre SC-002 (indicativo)**: a iteração de feedback real (§7.2) substituiu o esquema % (textuais somavam 44,6% no desktop) pelo esquema **all-px com pisos**, que prioriza estabilidade/legibilidade em toda a faixa (AC-13/AC-14) — o espaço extra acima do mínimo (ex.: 2880px) é distribuído pelo navegador, crescendo as textuais junto. Julgamento visual prevaleceu sobre a referência (C-1/SC-001: "referência indicativa, sujeita ao julgamento visual").
- Compactas contidas: Status 8,4% · Data 7,7% · Aquisição 9,4% · Depreciação 9,0% · Atual 9,0% — nenhuma dominante.

## 4. Larguras finais adotadas (T003/T005/T007 — C-1)

**Esquema final: TODAS as 10 colunas em px** (desktop + conjunto reduzido ≤768px). Nenhuma coluna depende de percentual do container — elimina a classe de falha observada em dispositivo real (§7.2), em que colunas textuais encolhiam abaixo do mínimo e o texto quebrava na vertical.

| Col | Coluna | Único conjunto (px) | Piso de conteúdo (estimativa ×1,25–1,30 da fonte real) |
|---|---|---|---|
| c1 | Tombamento | 134px | "TMB-2026-0439" mono ≈ 103–129px (nowrap) |
| c2 | Descrição | 148px | texto completo (quebra em fronteira de palavra) |
| c3 | Categoria | 128px | "Equipamento Geral" quebra em 2 linhas íntegras |
| c4 | Status | 132px | pill "Em Manutenção" ≈ 97–126px |
| c5 | Localização | 136px | texto completo |
| c6 | Responsável | 120px | header "Responsável" ≈ 77–100px |
| c7 | Data Compra | 124px | "24/09/2026" ≈ 73–95px (nowrap); header em 1 linha |
| c8 | Valor Aquisição | 148px | "R$ 120.000,00" ≈ 95–124px (nowrap) |
| c9 | Depreciação | 124px | header "Depreciação" ≈ 83–117px |
| c10 | Valor Atual | 148px | "R$ 120.000,00" + negrito ≈ 95–128px (nowrap) |

- **Soma 1342px → `min-width: 1345px`** — conjunto ÚNICO (sem media query de colunas): uma calibração só, pisos de fonte real garantidos em qualquer viewport/largura de janela.
- Correções de feedback real consolidadas: c7 100→124px (data transbordava sobre Valor Aquisição); **c8/c10 114/130→148px** ("R$ 120.000,00" nowrap no limite exato do útil — engrossadas com folga, útil ~130px ≥ pior caso 124–128px).
- Calibração da fonte real: pisos com fator ×1,25–1,30 sobre as métricas fallback (Plus Jakarta Sans via Google Fonts, base.html L23; padding real `.5rem .5rem` = 16px/coluna no vendor Bootstrap).
- Em viewports menores que (min-width + container), a tabela mantém o mínimo e a rolagem fica confinada ao `table-responsive` (FR-012; seções 20/21 do pedido).
- Distribuição do espaço acima do mínimo: navegador divide o excedente; as textuais (c2/c5/c6) continuam entre as maiores em px e crescem juntas.
- `table-layout: fixed` + `<colgroup>` (R2); `nowrap` apenas nas compactas (R4); `overflow-wrap: break-word` confinado a `@media screen`.

## 5. Resultado por cenário (medições `validar_local.py` — saída integral em `validacao_local.out.md`)

- **V1 (desktop)**: ✓ §3. Sem grandes vazios; sem colunas excessivamente largas; textuais são as 3 maiores.
- **V2 (conteúdos)**: ✓ Tombamento sem quebra; Descrição nome + S/N íntegros, texto completo; badge/pill íntegros; Localização/Responsável completos; data sem quebra; monetárias `text-end` íntegras (`-XX%` vermelho, valor atual verde em negrito); fallbacks renderizados no seed.
- **V3 (alinhamento/estabilidade)**: ✓ 10/10 sob os cabeçalhos (`<colgroup>` único); distribuição idêntica entre linhas do seed e entre temas; **pisos de coluna garantidos em todos os viewports medidos** (1440/1024/768/375: nenhuma coluna abaixo do mínimo).
- **V4 (responsividade)**: ✓ 1440/1024: mesma distribuição (colunas px estáveis); 768/375: tabela mantém o mínimo (medido 1192–1222px) com rolagem confinada ao `table-responsive` — **nenhuma coluna colapsada, nenhum texto vertical, nenhum transbordo nowrap** (todos os pisos ≥ conteúdo máximo); temas claro/escuro idênticos.
- **V5 (não-vazamento)**: ✓ `git diff` = `reports/inventory.html` + `assets/list.html` (**exceção justificada** — §7.1); `style.css`/`sw.js` intocados; outros relatórios inalterados (classe `.invrep-table` escopada).
- **V6 (impressão — US3/SC-007)**: ✓ paper media: tabela 100% da página, `table-layout:auto` (C3), mesma forma da referência V0 (Descrição 24,9% @1440 vs 24,0% antes — artefato uniforme do WeasyPrint documentado em §8); smoke `report-print` verde; CSV/Excel/PDF intocados (`test_rbac.py` verde).

## 6. Zoom 80%–200%

80% de 1440 ≈ 1152px ✓ e 200% ≈ 2880px ✓ (medidos): com colunas em px, a distribuição relativa mantém-se por construção; em zoom alto a tabela cresce com o container (rolagem confinada abaixo do mínimo); nenhuma fonte reduzida.

## 7. Observações

1. **Falha pré-existente no baseline (fora do escopo da 041)**: `test_rbac.py::test_web_action_buttons_hidden_without_permission` falhava em `main` limpo (`b75ba99`) — comentário CSS de `assets/list.html` (L127, commit `dd88428` da 038) citava o nome de um controle do header, mesmo padrão já corrigido em Locais por `b75ba99`. Correção: comentário reescrito sem citar controles (nenhuma regra alterada). Entra no commit da 041 como exceção justificada ao critério "git diff = 1 arquivo" do V5.
2. **Iteração de feedback real (pós-implementação)**: com o esquema inicial (% nas textuais + `min-width`), o uso real em tela menor reportou **títulos sobrepostos e textos na vertical** — colunas textuais encolhendo abaixo do mínimo (a resolução de % dentro do `fixed` varia por navegador/nível de zoom). Correção definitiva: **todas as colunas em px** com dois conjuntos (desktop 1191px e ≤768px 1062px) e `min-width` sincronizado — coluna px não encolhe em `table-layout: fixed`, eliminando a classe de falha em qualquer motor de renderização. Pisos verificados contra os conteúdos máximos (tombamento mono, `R$ 120.000,00`, headers "Responsável"/"Depreciação" com padding Bootstrap 32px).
3. **`min-width` e o WeasyPrint**: o layout engine de medição não impõe `min-width` de tabela em viewports menores; a verificação do piso foi feita pela métrica por coluna (nenhuma abaixo do mínimo especificado). Em navegadores reais o `min-width` é imposto e a rolagem confinada ocorre antes — padrão 036–040.
4. **Artefato de medição do print com `<colgroup>`**: no papel, o WeasyPrint distribui o espaço livre de forma ligeiramente diferente na presença de `<col>` (deltas uniformes ~13px/coluna), preservando a distribuição relativa. Em navegadores reais, `<col>` com `width:auto!important` (bloco de segurança) não interfere no `table-layout:auto`.
5. Nenhuma interação com o `max-width:140px` global do `tag-badge` ≤479px (este template não usa `tag-badge`).

## 8. Decisões finas

- **Todas as colunas em px** (2 conjuntos sincronizados com o `min-width`): robustez entre motores de renderização acima de tudo (lição do feedback real); o navegador distribui o espaço excedente, e as textuais continuam crescendo mais em telas largas.
- `overflow-wrap: break-word` confinado a `@media screen`: o papel fica com o comportamento puro do C7 (`anywhere`), sem alterar o min-content das colunas no modo auto.
- `nowrap` nas 4 compactas: seguro pelos pisos (§4) calibrados com folga Plus Jakarta Sans (lição 039); Descrição/Localização/Responsável **sem clamp/ellipsis/nowrap** (clarificação — texto completo).
- Regra de segurança de impressão (T009/R10) mantida mesmo redundante ao C3/C6/C7: defesa em profundidade, escopada a `.invrep-table`, sem tocar o bloco compartilhado C1–C10.
