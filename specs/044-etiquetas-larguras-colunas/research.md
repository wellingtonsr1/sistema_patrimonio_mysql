# Research: Ajuste Responsivo da Tabela "Etiquetas de Patrimônio" (044)

Incógnitas resolvidas com fatos do repositório e o mecanismo validado nas 036–043. Nenhum NEEDS CLARIFICATION restante — as 3 clarificações de spec (tooltip Bootstrap; tombamento com regras globais preservadas; marca/modelo com ellipsis + tooltip) estão registradas e incorporadas aos FRs.

## R1 — Onde vive o CSS: template embutido com classe de escopo (decisão 036–042, reusada)

**Decision**: CSS embutido em `assets/labels.html` (bloco `<style>` no topo do `{% block content %}`, com comentário de rastreabilidade "Feature 044") com classe de escopo própria na tabela de seleção (ex.: `.etiq-table`) e classe auxiliar de ellipsis (ex.: `.etiq-ellip`, com tooltip Bootstrap); `style.css` intocado.

**Rationale**: idêntico às anteriores — `style.css` é global e versionado em 2 pontos acoplados (base.html + SW allowlist); bump invalidaria cache de todo o sistema. Aqui o cuidado é redobrado: o `style.css` concentra o **`@media print` de etiquetas da feature 013** (`style.css:1605–1645`, ancorado em `body:has(#labels-print-area)`), o **contraste dos checkboxes** `.asset-check`/`#select-all-page` no tema claro (`style.css:1595`) e as **regras globais do `.tag-badge`** (`style.css:491` — `inline-block; max-width:100%; overflow:hidden; text-overflow:ellipsis` — e `style.css:1027` — `max-width:140px` ≤479.98px). **Comentários novos não citam nomes de controles** do header/toolbar/filtros (lição `b75ba99`) — a página não tem teste RBAC de template dedicado, mas a lição permanece obrigatória.

**Alternatives considered**: *`style.css` global*: rejeitado (cache global + FR-010 proíbe classes genéricas; risco ao domínio 013).

## R2 — `table-layout`: **fixed** justificado (C-5)

**Decision**: `table-layout: fixed` + `<colgroup>` com `<col class="cN">` estilizadas no `<style>` escopado; larguras determinadas por medição na implementação (C-1).

**Rationale**: (a) 5 colunas com conteúdos de comprimento variável (nomes longos de equipamentos, setores e locais com prefixo "IPMJP - ") — o auto layout redistribui a cada linha, incompatível com a prioridade de **linha única estável** (C-4); (b) com fixed + nowrap/ellipsis, o corte é previsível e sem sobreposição; (c) `<colgroup>` resolve canonicamente thead=tbody (seção 19) e absorve o `style="width:36px"` inline do `th` do checkbox sem perda de alinhamento (FR-009); (d) precedentes 041/042/043 comprovaram o mecanismo. Risco conhecido: células nowrap estreitas cortam texto — mitigado por ellipsis **+ tooltip Bootstrap** (clarificação) e pisos da fonte real (R3/R11).

**Alternatives considered**: *auto*: rejeitado — larguras instáveis e quebra por conteúdo; *percentuais inline no colgroup*: rejeitado (lição da 036).

## R3 — Larguras iniciais de partida (a medir/refinar na implementação — C-1)

**Decision**: pontos de partida sugeridos (soma ≈ 1230px, coerente com 042 (1380) e 043 (1330) e calibrada à estrutura real de 5 colunas; ajustável ao conteúdo real): **checkbox ~46px** (36px atuais + folga para padding e área clicável; piso 46px), **Tombamento ~150px** (código monoespaçado + padding; `IMPJP679450` a ×1,25 ≈ 137px), **Equipamento ~420px** (nome + linha auxiliar — maior textual, C-2), **Setor ~280px** (nomes completos — "Gabinete da Superintendência" a ×1,30 ≈ 265px), **Localização ~334px** (maior parcela entre as textuais — "IPMJP - Fundo Municipal de Previdência" a ×1,25 ≈ 317px). Rígidas/nowrap com folga ×1,25–1,30 (Plus Jakarta Sans; padding `.5rem .5rem` = 16px/coluna). Valores finais por medição (V0 antes/depois).

## R4 — Mecanismo de linha garantida + tooltip Bootstrap (clarificações — o coração da 044)

**Decision**:
- **Rígidas**: checkbox (coluna mínima) e **Tombamento** (nowrap na célula; o `.tag-badge` já tem ellipsis global embutido como fallback) — sem ellipsis novo (clarificação).
- **Textuais com linha garantida (ellipsis + tooltip Bootstrap)**: **Equipamento** — **duas linhas cortáveis**: o `span.fw-semibold` do nome (span interno ellipsis + tooltip) e a **linha auxiliar de marca/modelo** (`div.text-muted` com span interno ellipsis + tooltip — clarificação); **Setor** (`td.small.text-muted` → span interno ellipsis + tooltip, fallback "—" fora do span cortável); **Localização** (idem, fallback "—" fora do span cortável). Marcação: `data-bs-toggle="tooltip" data-bs-placement="top" title="{{ ... }}"` — auto-inicializada em `base.html:329–333`/`main.js` (mesmo mecanismo das 042/043).
- **Padrão de marcação (precedentes 042/043)**: span interno com classe auxiliar (ex.: `.etiq-ellip`): `display:inline-block; max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; vertical-align:bottom`; fallback "—" e ícones fora dos spans cortáveis.
- **Sem badges nesta tabela** — as lições da 042/043 sobre `white-space: normal` escopado para `.badge` não se aplicam aqui; o único elemento tipo-chip é o `.tag-badge` do Tombamento, com regras globais preservadas.
- Equipamento sem marca/modelo: a `div` auxiliar renderiza vazia — estrutura preservada, sem tooltip em span vazio.

**Alternatives considered**: *ellipsis no `.tag-badge` da 044*: rejeitado — dado funcional íntegro (regras globais preservadas; fallback ≤479.98px aceitável); *tooltip nativo*: rejeitado — clarificação explícita pelo Bootstrap; *quebra generosa nas textuais (padrão 041)*: rejeitado — C-4 prioriza linha única com corte controlado (padrão 042/043).

## R5 — Aproveitamento total (C-3/FR-001/AC-01)

**Decision**: fixed + colgroup com soma ≈ container → tabela em praticamente 100% do card; nenhum `max-width` artificial; container/header/filtros/toolbar/estado vazio intocados (FR-010). Medição V0 antes/depois documenta o aproveitamento.

## R6 — Responsividade e min-width (padrão 041/042/043: conjunto único)

**Decision**: `min-width` único sincronizado com a soma do colgroup (≈1230px, a calibrar) — abaixo disso, rolagem confinada ao `table-responsive` (mecanismo do projeto); sem media query de colunas (lição da 041). Em janelas ≥ ~1370px, sem rolagem; em menores, rolagem autorizada. Zoom 80%–200% coberto pela estabilidade px.

## R7 — Temas e cores

**Decision**: nenhuma cor nova; apenas layout/quebra. `.tag-badge`, `text-muted`, `fw-semibold` e `var(--c-text)` herdam os temas via `style.css` intocado; **o contraste dos checkboxes no tema claro (`style.css:1595`) permanece intacto** (nenhum toque em `.asset-check`/`#select-all-page`).

## R8 — RBAC e comentários

**Decision**: nenhum toque nas condições Jinja (`{% if a.location and a.location.department %}`, `{% if a.location %}`, `{% if a.brand or a.model %}`, `{% if a.id|string in selected_list %}`) e fallbacks; nenhum id/classe funcional novo em controles. **Comentários CSS/HTML novos NÃO citam controles do header/toolbar/filtros** (lição `b75ba99`) — a página não tem teste RBAC de template dedicado, mas a lição permanece obrigatória. Tooltips carregam **dados das linhas** (nome, marca/modelo, setor, localização), nunca strings de controles.

**Rationale**: FR-013/FR-014; gate `patrimonio.visualizar` intocado; o JS inline de seleção em lote (estado via URL `?selected=`) não é referenciado nem alterado.

## R9 — Testes e validação (SC-006/SC-007)

**Decision**: nenhum teste automatizado novo (seção 29 do pedido); suíte existente como regressão. Run focado: `pytest tests/test_help.py tests/test_rbac.py -q` (**baseline: nenhum teste dedicado à página de etiquetas** — constatado por busca em `tests/`; `test_help.py` cobre a regressão geral de páginas e `test_rbac.py` os gates `patrimonio.visualizar`). Validação visual V0–V5 (sem bloco de impressão nesta tela — não é relatório) registrada em `validacao.md` no formato das anteriores, **com conferência dos tooltips e da impressão de etiquetas no navegador**.

**Rationale**: processo validado oito vezes; F1 da 039 (run focado = testes que exercitam a página/área).

## R10 — Sem bloco de impressão; domínio 013 protegido (diferença da 041/042)

**Decision**: `assets/labels.html` **não é relatório** — não possui `.report-print` e a tela NÃO recebe `@media print` novo (R10 da 043; seção 24 do pedido: "não alterar impressão"). A **folha de etiquetas** `#labels-print-area`/`.labels-sheet`/`.label-card`, o `@media print` de etiquetas em `style.css:1605–1645` (âncora `body:has(#labels-print-area)`) e o comportamento de impressão da 013 permanecem **intocados**; a tabela de seleção e a toolbar são `no-print` e seguem como estão. Nenhuma regra `@media print` é criada ou alterada nesta feature.

**Rationale**: evita vazar escopo para o domínio de impressão da 013; validação inclui conferir que a impressão de etiquetas continua igual.

## R11 — Medição local com WeasyPrint (opcional, padrão 039–043)

**Decision**: reusar o script local (padrão 041/042/043, copiando de `specs/043-usuarios-larguras-colunas/validar_local.py`): TestClient + login admin + seed de edge cases (tombamento longo `IMPJP679450`, nome longo de equipamento, marca/modelo longa, setor longo "Gabinete da Superintendência", localização longa "IPMJP - Fundo Municipal de Previdência", e sem local/setor para os fallbacks "—"), medição das `<col>` pela árvore de boxes em `media_type="screen"` (não há passada print nesta tela). Limitações: fonte fallback (pisos ×1,25–1,30) e `min-width` não imposto pelo WeasyPrint (verificar pisos por coluna); tooltips não são medidos (verificação manual no navegador).
