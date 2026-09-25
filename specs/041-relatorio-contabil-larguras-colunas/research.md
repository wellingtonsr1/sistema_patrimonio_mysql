# Research: Ajuste Responsivo da Tabela "Relatório Contábil-Físico do Patrimônio" (041)

Incógnitas resolvidas com fatos do repositório e o mecanismo validado nas 036–040 (reuso aprovado pelo padrão das specs anteriores; C-1/C-5 deixam os valores finais para a medição na implementação). Nenhum NEEDS CLARIFICATION restante (a clarificação de spec — texto completo nas textuais — já está registrada e incorporada aos FRs). Novidade da 041: proteção de impressão (C-6/FR-013) elevada a decisão própria (R10).

## R1 — Onde vive o CSS: template embutido com classe de escopo (decisão 036–040, reusada)

**Decision**: CSS embutido em `reports/inventory.html` (bloco `<style>` no topo do `{% block content %}`) com classe de escopo própria na tabela (ex.: `.invrep-table`); `style.css` intocado.

**Rationale**: idêntico às anteriores — `style.css` é global e versionado em 2 pontos acoplados (base.html + SW allowlist); bump invalidaria cache de todo o sistema. Precedente de comentário HTML de rastreabilidade da feature no `<style>` (036–040).

**Alternatives considered**: *`style.css` global*: rejeitado (cache global + FR-011 proíbe classes genéricas).

## R2 — `table-layout`: **fixed** justificado (C-5) — a análise, não a aplicação automática

**Decision**: `table-layout: fixed` + `<colgroup>` com `<col class="cN">` estilizadas no `<style>` escopado; larguras determinadas por medição na implementação (C-1).

**Rationale** (análise exigida pelas seções 19/25 do pedido):
- **Por que fixed aqui**: (a) 10 colunas com conteúdos de comprimento muito variável (descrições com linha S/N, localizações institucionais, nomes completos, valores monetários de ordens de grandeza variadas) — o auto layout redistribui a cada linha e é a causa da distribuição irregular atual; (b) o resultado precisa ser estável entre filtros (o relatório já aceita parâmetros de filtro — conteúdo muda, larguras não); (c) as 036–040 comprovaram o mecanismo (5 a 9 colunas) com o mesmo perfil de problema; (d) `<colgroup>` resolve canonicamente a exigência thead=tbody (seções 18/22/23 do pedido — sem `width` somente no `<td>`).
- **Quando auto seria melhor**: tabelas de poucas colunas com larguras naturais estáveis — não é o caso (10 colunas com texto e valores variáveis).
- Risco conhecido do fixed e mitigação: como as textuais exibem **texto completo** (clarificação), elas quebram naturalmente dentro da coluna (`break-word`) — o fixed não trunca nada aqui porque não há nowrap/ellipsis nas textuais; as compactas (Tombamento/Categoria/Status/Data Compra/monetárias) ficam em **px com folga** (lição da 039 — Plus Jakarta Sans ~20–30% mais larga que fontes de medição fallback).
- **Interação com impressão**: o `@media print` do relatório (C3) já força `table-layout:auto!important; width:100%!important` em `.report-print table` — ou seja, o papel **não herda** o fixed da tela; essa é a proteção estrutural existente que a 041 deve preservar (R10).

**Alternatives considered**: *auto + min-width por coluna*: rejeitado — não garante proporção estável (causa do problema atual); *percentuais inline no colgroup*: rejeitado — não é sobrescrevível por media query (lição da 036).

## R3 — Larguras iniciais de partida (a medir/refinar na implementação — C-1)

**Decision**: pontos de partida sugeridos (soma 100%): **Tombamento ~8%**, **Descrição ~16%**, **Categoria ~8%**, **Status ~8%**, **Localização ~12%**, **Responsável ~11%**, **Data Compra ~7%**, **Valor Aquisição ~10%**, **Depreciação ~9%**, **Valor Atual ~11%**. Textuais (Descrição+Localização+Responsável) ≈ 39% — mas o objetivo da 041 é que, **somadas às compactas, as compactas somem o mínimo** (5 colunas compactas ≈ 45% em px); em desktop real as textuais devem dominar a distribuição relativa do espaço **variável** (SC-002). Os px das 5 compactas são calibrados pelos conteúdos máximos (data `dd/mm/YYYY`; `R$ 120.000,00`; `-99,9%`; pills/badges; tombamento mono) **com folga Plus Jakarta Sans** (lição 039) e o restante é dividido pelas 3 textuais + Tombamento/Categoria.

**Rationale**: natureza do conteúdo (fatos do data-model): Tombamento `font-monospace fw-bold` (código íntegro, sem quebra — FR-003); Descrição = `<strong>` + linha S/N condicional; Categoria badge curto; Status pill; Localização institucional longa; Responsável nome completo; Data `dd/mm/YYYY` ou "-"; monetárias `text-end` com prefixo "R$ " e `-XX%` na Depreciação; Valor Atual `fw-bold`. A medição inicial (V0) e a validação refinam — o padrão das anteriores mostrou 1–2 iterações de ajuste fino.

## R4 — Proteções de quebra e texto completo (clarificação, mapeado para esta tabela)

**Decision**:
- `overflow-wrap: break-word` nas td/th (fronteira de palavra — nunca no meio de palavra).
- **Descrição, Localização e Responsável: texto completo, sem clamp nem reticências** (clarificação) — as linhas crescem conforme o conteúdo; nada de `white-space: nowrap`/`text-overflow: ellipsis` nessas células. Detalhe da Descrição: nome em `<strong>` e linha `S/N` ficam em elementos de bloco distintos (a linha S/N já é uma `div` no template) — preservar essa estrutura evita sobreposição entre as duas linhas.
- `white-space: nowrap` **apenas nas células compactas** (Tombamento, Data Compra, monetárias): conteúdo curto conhecido não quebra; as colunas recebem px com folga para isso ser seguro.
- **Preservar** `font-monospace fw-bold` (Tombamento), badge de Categoria, pill de Status, `text-end small` (monetárias), `-XX%` vermelho e valor atual verde `fw-bold` (contract §1–§2).
- Badge de Categoria e pill de Status: comportamento visual atual (quebra evitada por dimensão da coluna, não por nowrap forçado).

**Alternatives considered**: *clamp/ellipsis nas textuais (padrão da 039 para Motivo)*: rejeitado — a clarificação do solicitante exige texto completo (mesma decisão da 040). *Truncar valores*: rejeitado — esconderia dado contábil exibido hoje (FR-015).

## R5 — Aproveitamento total (C-3/FR-001/AC-01)

**Decision**: fixed + percentuais (soma 100%) garante a tabela em 100% do card — nenhum `max-width` artificial; container/header/cabeçalho interno do relatório intocados (FR-011). Medição V0 antes/depois documenta o aproveitamento (esperado ~100% antes e depois; o ganho real é a distribuição, como verificado na 037–040).

## R6 — Responsividade e min-width (padrão 036–040)

**Decision**: `min-width` inicial ~1480px (10 colunas; 5 compactas em px + 3 textuais + 2 intermediárias — alinhado ao perfil da 039, que também tem colunas monetárias/datas rígidas; a medir) — abaixo disso, `table-responsive` rola confinado (mecanismo do projeto); media query ≤768px com min-width reduzido para header/células compactas, se a medição mostrar sobreposição. Proibido reduzir fonte drasticamente (seção 19 do pedido).

**Rationale**: mesma mecânica das anteriores, calibrada pelo conteúdo: as textuais com texto completo precisam de largura razoável para não gerar linhas altas demais; em tablet/celular a rolagem confinada é o comportamento esperado e documentado (C-4/contract §3; seções 20/21 do pedido — "não sacrificar a legibilidade apenas para eliminar a rolagem").

## R7 — Temas e cores

**Decision**: nenhuma cor nova; apenas layout/quebra (mesma decisão das anteriores). Badge `badge-soft-gray`, pill `status-pill-*`, cores `var(--red)`/`var(--green)` e `font-monospace` herdam os temas via `style.css` intocado.

## R8 — Botões do header e RBAC

**Decision**: nenhum toque no `page-header no-print` ("Baixar CSV" condicional a `relatorios.exportar` + "Imprimir") nem nos fallbacks condicionais Jinja. **Regra herdada da lição `b75ba99` (039/040)**: comentários CSS/HTML novos NÃO citam nomes de controles do header ("Baixar CSV", "Imprimir", "Exportar CSV") — strings de controles em comentários vazam para o HTML e os testes RBAC de template falham; comentários citam apenas "header" e "controles do relatório".

**Rationale**: FR-014 (nada funcional muda); `test_rbac.py` valida o gate `relatorios.exportar` no CSV e o RBAC de template pode detectar strings no HTML final.

## R9 — Testes e validação (SC-006/SC-007/SC-008)

**Decision**: nenhum teste automatizado novo (seção 33 do pedido); suíte existente como regressão (baseline antes, focado durante, completo depois). Run focado: `pytest tests/test_report_print_smoke.py tests/test_rbac.py tests/test_help.py -q` (renderizam/exercitam a página e o domínio de relatórios). Validação visual com medição real e screenshots nos cenários do pedido + zoom 80%–200%, registrada em `validacao.md` no formato das 036–040 (comparação antes/depois, tabelas de larguras com ajustes/motivos, decisões finas, observações preexistentes) — **com verificação de impressão obrigatória** (V6).

**Rationale**: processo validado cinco vezes de ponta a ponta. F1 da 039 aplicado por padrão: o run focado inclui os testes que efetivamente renderizam a página (`test_report_print_smoke.py` renderiza `/reports/inventory`; `test_help.py:109`; `test_rbac.py`).

## R10 — Preservação da impressão (específica da 041 — C-6/FR-013/US3)

**Decision**: a 041 NÃO edita nenhuma regra do bloco `@media print` dos relatórios (C1–C10 em `style.css`, ancorado em `.report-print` e **compartilhado** com `movements_report.html` e `custodians_report.html`). A proteção é estrutural: o C3 já força `table-layout:auto!important; width:100%!important` e o C6 zera `min-width` do `.table-responsive` — o papel não herda o fixed/min-width da tela. A 041 adiciona, **no `<style>` embutido do template**, uma regra de segurança escopada dentro de `@media print` (ex.: `@media print { .invrep-table { table-layout: auto !important; width: 100% !important; } .invrep-table th, .invrep-table td { white-space: normal !important; } .invrep-table col { width: auto !important; } }`), garantindo que nenhuma largura/nowrap da tela alcance o papel mesmo se o mecanismo C1–C10 mudar no futuro. A âncora `class="card p-4 report-print"` é fixada por `test_report_print_smoke.py` — o contract §1 protege esse atributo exato.

**Rationale**: C-6/seção 36 do pedido; US3/SC-007 medem a igualdade da pré-visualização antes/depois; o bloco compartilhado não pode ser editado (afetaria os outros 2 relatórios, violando FR-016). A regra extra é redundante por design (defesa em profundidade) e escopada à tabela da 041 — não vaza para outros templates.

**Alternatives considered**: *editar o bloco C1–C10 para "conhecer" a tabela da 041*: rejeitado — CSS global compartilhado, bump de cache e impacto nos outros relatórios; *não adicionar regra nenhuma*: rejeitado — a proteção ficaria implícita apenas no comportamento atual do C3/C6/C7 (frágil a ajustes futuros do print).

## R11 — Medição local com WeasyPrint (opcional, padrão 039)

**Decision**: quando não houver navegador disponível para V0/V1, reusar o script de medição local (padrão `specs/039-movimentacoes-larguras-colunas/validar_local.py`, WeasyPrint 70.0 já no `.venv`): renderiza via TestClient (SQLite em memória, login de admin), injeta o CSS real (vendor bootstrap + style.css), `@page size:<vp>px` por último (vence o `@page size:Auto` do print) e mede as `<col>` pela árvore de boxes (`el.tag=="col"`, primeira classe em `el.get("class")`).

**Rationale**: mesmo motor de renderização e método de medição já validados; adaptação é copiar o script do padrão 039 e trocar a rota alvo por `/reports/inventory` + a classe de escopo da 041. Cuidado: WeasyPrint usa fontes fallback (mais estreitas que Plus Jakarta Sans) — daí as folgas nas rígidas em px (lição 039).
