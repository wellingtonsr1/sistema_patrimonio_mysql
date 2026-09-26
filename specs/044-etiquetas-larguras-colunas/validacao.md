# Validação: Ajuste Responsivo da Tabela "Etiquetas de Patrimônio" (044)

**Data**: 2026-09-25 · **Branch**: `044-etiquetas-larguras-colunas` · **Formato**: 036–043

## 1. Suíte de testes (SC-006)

| Momento | Comando | Resultado |
|---|---|---|
| Baseline (T002) | `.venv/bin/python -m pytest tests/ -q` | **728 passed** |
| Focado pós-alteração (T006) | `.venv/bin/python -m pytest tests/test_help.py tests/test_rbac.py -q` | **39 passed** |
| Completo pós-alteração (T006) | `.venv/bin/python -m pytest tests/ -q` | **728 passed** |

- **Baseline constatado (F1 do analyze, corrigido na spec)**: não existe arquivo de testes dedicado a `/assets/labels` (varredura em `tests/`) — o run focado usa `test_help.py` (regressão geral de páginas) + `test_rbac.py` (gates `patrimonio.visualizar` e páginas).

## 2. Baseline "antes" (V0 — seção 29 do pedido)

Distribuição do layout automático (sem colgroup): as 4 colunas de conteúdo competiam por espaço sem priorização — o **checkbox media apenas 13,6px** (área de clique reduzida pelo Bootstrap), Setor/Localização ficavam estreitos (221/281px em 1440px) e **nomes de equipamentos, setores e localizações quebravam em várias linhas** (sem nowrap). Saída integral em `validacao_local.v0.md` (cópia do out.md antes da alteração).

## 3. Comparação antes/depois (V1 — SC-001/SC-002)

Medições `validar_local.py` (WeasyPrint, media screen) — "depois":

| Viewport | Checkbox | Tombamento | Equipamento | Setor | Localização |
|---|---|---|---|---|---|
| 1440px (expandida) | 53,8px (3,7%) | 189,3px (13,2%) | **632,3px (44,0%)** | 251,9px (17,5%) | **310,7px (21,6%)** |
| ≤1152px (piso) | 45,6px | 160,4px | **535,7px (44,0%)** | 213,4px (17,5%) | **263,3px (21,6%)** |

- **Nota de medição**: o WeasyPrint distribui o excedente do container entre as colunas proporcionais; em 1440px a tabela expande de 1260px (soma do colgroup) para 1438px (largura útil). Em viewports menores o **piso** (soma 1260px → min-width) é mantido: **tabela ~1248px com rolagem confinada ao `table-responsive`** (comportamento esperado; em navegadores reais o `min-width: 1260px` impõe rolagem abaixo de ~1400px de janela). Como todas as células são `nowrap`, o WeasyPrint mede o piso pelo **conteúdo** (não pelos px declarados do colgroup) — em navegadores reais, com `table-layout: fixed`, os px declarados são honrados exatamente e o excesso é cortado pelos spans de ellipsis.
- Textuais (Equipamento+Setor+Localização): **83,1%** da tabela — maior bloco (SC-002 ✓); tabela em 100% da largura útil (SC-001 ✓).
- **Linha garantida**: nome do equipamento, marca/modelo, setor e localização com `.etiq-ellip` (nowrap + ellipsis + tooltip); tombamento com badge global íntegro em célula nowrap — **zero quebras no seed em 1440px** (V0 quebrava todos os campos longos).
- Checkbox: 13,6px → 46px de coluna (53,8px expandida) — área de clique restaurada.

## 4. Larguras finais adotadas (T003/T005 — C-1)

Conjunto **único** em px (soma 1260px → `min-width: 1260px`), sem media query de colunas (lição da 041):

| Col | Coluna | Final | Piso verificado (×1,25–1,30 da fonte real) |
|---|---|---|---|
| c0 | Checkbox | 46px | controle 20px + padding (16px) + folga |
| c1 | Tombamento | **180px** | `IMPJP679450VAL` (14 caracteres) monoespaçada (~130px) + padding + folga — ampliado duas vezes a pedido do solicitante (150 → 165 → 180px), garantindo o código sempre em uma linha sem ellipsis |
| c2 | Equipamento | 420px | maior textual; nomes longos cortam com tooltip (medido 536px) |
| c3 | Setor | 280px | "Gabinete da Superintendência" (~230px) cabe em uma linha |
| c4 | Localização | 334px | "IPMJP - Fundo Municipal de Previdência" (~300px) cabe em uma linha; maior parcela (C-2) |

## 5. Resultado por cenário

- **V1 (desktop)**: ✓ §3. Sem grandes vazios; sem colunas excessivamente estreitas; linha garantida.
- **V2 (conteúdos + tooltips)**: ✓ tooltip Bootstrap em nome, marca/modelo, setor e localização (marcação server-rendered, inicialização existente — base.html/main.js); tombamento completo e legível (badge íntegro, sem ellipsis novo); fallbacks "—" íntegros fora dos spans cortáveis; equipamento sem marca/modelo renderiza sem buraco; **checkbox funcional** (contagem/folha/URL intocados). *(Confirmação de hover no navegador no aceite final.)*
- **V3 (alinhamento/estabilidade)**: ✓ 5/5 sob os cabeçalhos (incluindo o cabeçalho vazio do checkbox); distribuição idêntica nas 7 linhas do seed (marca/modelo longa, sem marca, sem local) e entre temas; alturas uniformes.
- **V4 (responsividade)**: ✓ 1440: tabela expande com o container (soma = largura útil); ≤1152px: piso mantido com rolagem confinada ao `table-responsive` (em navegadores reais o min-width 1260px impõe rolagem antes); zoom 80–200% coberto pela estabilidade px; temas claro/escuro idênticos (contraste dos checkboxes em `style.css` intocado).
- **V5 (não-vazamento + impressão)**: ✓ `git diff` = apenas `app/web/templates/assets/labels.html` (36 inserções, 5 remoções); `style.css`/`sw.js` intocados; **folha `#labels-print-area` e o `@media print` de etiquetas da 013 intocados**; **nenhum `@media print` novo** (tela não-relatório — R10); telas 036–043 inalteradas; JS de seleção em lote intacto.

## 6. Zoom 80%–200%

Colunas px mantêm a distribuição em toda a faixa por construção; em janelas < ~1370px a rolagem confinada aparece (min-width 1230px); nenhuma fonte reduzida.

## 7. Observações

1. **Sem testes dedicados a etiquetas**: constatado no T002 e registrado na spec (correção do F1); run focado = help+rbac (39 passed).
2. **Sem bloco de impressão** (R10): tela não-relatório — nenhum `@media print` criado; a impressão de etiquetas segue o comportamento da 013, verificado como intocado.
3. **Tooltip sempre presente no markup**: decisão idêntica à da 043 — tooltips redundantes em valores não truncados são inofensivos e não exigem JS novo.
4. **WeasyPrint não impõe `min-width`** e, com células `nowrap`, mede o piso pelo conteúdo: os valores medidos refletem mínimos de conteúdo, não os px declarados do colgroup — em navegadores reais (comportamento de referência) os px declarados são honrados e a rolagem confinada ocorre abaixo de ~1400px de janela (min-width 1260px).
5. **`.tag-badge` ≤479.98px** (`style.css:1027`, max-width 140px): em navegadores, esse limite ficava **abaixo da célula fixa de 165px** e a fonte monoespaçada maior do dispositivo quebrava o código em 2 linhas no celular — **corrigido pós-feedback do solicitante** com regra escopada `.etiq-table .tag-badge { white-space: nowrap; max-width: 100%; }`: nowrap garante a linha única (o badge global não tinha `white-space` próprio) e `max-width: 100%` neutraliza o limite de 140px dentro desta tabela, mantendo o corte controlado (ellipsis) apenas para códigos maiores que a célula; nenhuma regra global alterada.
6. Colgroup posicionado **antes** do `<thead>` (consistência com 043/041/042/movements/inventarios; HTML permite colgroup como filho direto antes dos grupos de linhas). **Correção pós-feedback do usuário**: a classe de escopo `etiq-table` havia ficado **fora da tag `<table>`** (presente apenas no CSS) — o fixed/min-width/nowrap e a regra do badge ficavam "mortos" no navegador real (as medições WeasyPrint não detectaram porque o medidor valida colunas e badges diretamente, e os spans `.etiq-ellip` não dependem da classe da tabela). Corrigido em `labels.html:126` (`<table class="table align-middle etiq-table">`); com a classe ativa, o navegador aplica o colgroup em px e o tombamento fica em linha única em todas as viewports. **Ajustes pós-entrega (pedido do solicitante)**: Tombamento 150 → 165px (+≈2 caracteres monoespaçados; min-width 1230 → 1245px) e, depois, 165 → 180px para folga adicional no celular (min-width 1245 → 1260px) — Equipamento/Setor/Localização mantêm as proporções (fixed redistribui o restante).
7. Marca/modelo vazia: a `div` auxiliar renderiza vazia (comportamento original) e o span cortável não existe — sem tooltip em conteúdo vazio.

## 8. Decisões finas

- `.etiq-ellip` como span interno (padrão 042/043): separa a área cortável dos fallbacks "—" e preserva as classes originais dos `td`.
- Tooltips em **quatro elementos textuais** (nome, marca/modelo, setor, localização), cada um com seu valor completo (clarificações da spec).
- Tombamento **sem ellipsis novo**: célula nowrap + regras globais do `.tag-badge` preservadas (clarificação) — código completo nas larguras alvo. **Refinamento pós-feedback (celular)**: `white-space: nowrap` explícito escopado ao badge desta tabela (o global não define `white-space` e quebrava no ≤479.98px, onde o `max-width:140px` global era menor que a célula) + `max-width: 100%` (mantém o ellipsis global como corte controlado em códigos extremos).
- `brand_model` calculado com `|trim` no Jinja (sem duplicar a expressão nos atributos title/texto) — mesma concatenação do template original.
- Seed do medidor cobre os edge cases do quickstart (tombamento longo `IMPJP679450VAL`, nome longo, marca/modelo longa, setor "Gabinete da Superintendência", localizações longas com prefixo "IPMJP - ", sem marca e sem local).
