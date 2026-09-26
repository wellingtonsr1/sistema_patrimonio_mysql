# Research: Ajuste Responsivo da Tabela "Visão Geral do Patrimônio" (046)

Incógnitas resolvidas com fatos do repositório e o mecanismo validado nas 036–044. Nenhum NEEDS CLARIFICATION restante — as 4 clarificações de spec (tooltip Bootstrap; badge da Ação dimensionado pelos rótulos reais; controle de linha via classe de escopo; script de validação local) estão registradas e incorporadas aos FRs.

## R1 — Onde vive o CSS: template embutido com classe de escopo (decisão 036–044, reusada)

**Decision**: CSS embutido em `dashboard.html` (bloco `<style>` no topo do `{% block content %}`, com comentário de rastreabilidade "Feature 046") com classe de escopo própria na tabela de movimentações (ex.: `.dash-table`) e classe auxiliar de ellipsis (ex.: `.dash-ellip`, com tooltip Bootstrap); `style.css` intocado.

**Rationale**: idêntico às anteriores — `style.css` é global e versionado em 2 pontos acoplados (base.html + SW allowlist); bump invalidaria cache de todo o sistema. Cuidado redobrado aqui: o `style.css` concentra as **regras globais do `.tag-badge`** (`style.css:491` — `inline-block; max-width:100%; overflow:hidden; text-overflow:ellipsis` — e `style.css:1027` — `max-width:140px` ≤479.98px) usadas nesta tabela e em dezenas de outras. **Comentários novos não citam nomes de controles** do dashboard (lição `b75ba99`; o dashboard não tem teste RBAC de template dedicado, mas a lição permanece obrigatória).

**Alternatives considered**: *`style.css` global*: rejeitado (cache global + FR-012 proíbe classes genéricas; risco a dezenas de telas que usam `.table.align-middle`).

## R2 — `table-layout`: **fixed** justificado (C-6)

**Decision**: `table-layout: fixed` + `<colgroup>` com `<col class="cN">` estilizadas no `<style>` escopado; larguras determinadas por medição na implementação (C-1).

**Rationale**: (a) 7 colunas com conteúdos de comprimento variável (nomes de colaboradores/locais com prefixo "IPMJP - ", descrições de equipamentos) — o auto layout redistribui a cada linha, incompatível com a prioridade de **linha única estável** (C-4); (b) com fixed + nowrap/ellipsis, o corte é previsível e sem sobreposição; (c) `<colgroup>` resolve canonicamente thead=tbody (seção 21) sem regras por `<td>` (FR-011); (d) precedentes 041/042/043/044 comprovaram o mecanismo. Risco conhecido: células nowrap estreitas cortam texto — mitigado por ellipsis **+ tooltip Bootstrap** (clarificação) e pisos da fonte real (R3/R7).

**Alternatives considered**: *auto*: rejeitado — larguras instáveis e quebra por conteúdo; *percentuais inline no colgroup*: rejeitado (lição da 036).

## R3 — Larguras iniciais de partida (a medir/refinar na implementação — C-1)

**Decision**: pontos de partida sugeridos (soma ≈ 1330px, coerente com 043 (1330), 044 (1230) e 042 (1380) e calibrada à estrutura real de 7 colunas; ajustável ao conteúdo real): **Data ~135px** (16 caracteres `dd/mm/aaaa hh:mm` + padding; nowrap já existente), **Tombamento ~150px** (código monoespaçado; `IMPJP679450` a ×1,25 ≈ 137px), **Equipamento ~330px** (textual dominante, C-2), **Ação ~200px** (badge; rótulo mais longo "Entrada por Aquisição" ~25 caracteres a .68rem ≈ 170px + padding), **Destino ~330px** (textual dominante — colaborador completo ou "IPMJP - ..." + ícone, C-2), **Operador ~130px** (username curto — "wellington"/"admin"; suficiente para nomes em uma linha, C-2), **Ações ~95px** (par de botões-ícone `btn-ghost btn-icon` + padding; text-nowrap existente). Rígidas/nowrap com folga ×1,25–1,30 (Plus Jakarta Sans; padding `.5rem .5rem` = 16px/coluna). Valores finais por medição (V0 antes/depois).

## R4 — Mecanismo de linha garantida + tooltip Bootstrap (clarificações — o coração da 046)

**Decision**:
- **Rígidas**: **Data** (nowrap já presente na `td` — preservado), **Tombamento** (nowrap na célula; o `.tag-badge` já tem ellipsis global embutido como fallback) e **Ações** (`text-nowrap` já presente — preservado) — sem ellipsis novo (clarificação).
- **Textuais com linha garantida (ellipsis + tooltip Bootstrap)**: **Equipamento** (o `a.fw-semibold` recebe span interno com classe auxiliar ellipsis + tooltip — o atributo `style="color:var(--c-text)"` do link é preservado), **Destino** (os DOIS ramos do if/else recebem span interno ellipsis + tooltip com o valor completo — colaborador **ou** local/"Estoque"; os ícones `bi-person`/`bi-geo-alt` ficam FORA do span cortável; fallback "Estoque" fora do span), **Operador** (`td.text-muted.small` → span interno ellipsis + tooltip). Marcação: `data-bs-toggle="tooltip" data-bs-placement="top" title="{{ ... }}"` — auto-inicializada em `base.html:329–333`/`main.js` (mesmo mecanismo das 042/043/044).
- **Padrão de marcação (precedentes 042/043/044)**: span interno com classe auxiliar (ex.: `.dash-ellip`): `display:inline-block; max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; vertical-align:bottom`; ícones e fallbacks fora dos spans cortáveis; sem tooltip em span vazio.
- **Ação (badge `.badge-soft-primary`)**: **sem ellipsis no badge** — a coluna é dimensionada para os rótulos reais em uma linha nas larguras alvo (clarificação; o rótulo vem de `movement_type.label`, vocabulário fixo de 8 valores); em viewport muito estreita vale a rolagem confinada. Diferente das 042/043 (que tinham badges status + `white-space: normal` escopado): aqui NÃO há badges de status multi-linha na tabela — não se aplica a lição do `white-space: normal`.
- **Ações**: estrutura condicional `{% if m.term_code %}` preservada (par Termo+Ver Bem vs. só Ver Bem); `text-nowrap` e alinhamento à direita existentes mantidos; a coluna é dimensionada pelo PAR (pior caso), evitando desalinhamento entre linhas.

**Alternatives considered**: *ellipsis no `.tag-badge`*: rejeitado — dado funcional íntegro (regras globais preservadas; fallback ≤479.98px aceitável); *tooltip nativo*: rejeitado — clarificação explícita pelo Bootstrap; *quebra generosa nas textuais (padrão 041)*: rejeitado — C-4 prioriza linha única com corte controlado (padrão 042/043/044).

## R5 — Escopo restrito DENTRO do próprio template (novo risco específico da 046)

**Decision**: a tabela-alvo recebe classe dedicada (ex.: `.dash-table`); a **outra tabela do template** ("Necessitam de atenção", L182–200 — `.table.align-middle.table-sm`) e os demais cards/KPIs **não recebem nenhuma regra nova** e não têm classe alterada.

**Rationale**: única feature da família cujo template contém **duas tabelas** no mesmo arquivo — o seletor do CSS embutido deve ancorar na classe de escopo (não em `.table` genérico), senão a tabela de observações herdaria o colgroup/fixed indevidamente. Validado no script de medição local: a tabela de observações deve permanecer byte-a-byte idêntica nas medições (larguras naturais, quebras) antes e depois.

**Alternatives considered**: *renomear/marcar ambas as tabelas*: rejeitado — Princípio I (menor alteração; a outra tabela funciona e não é alvo).

## R6 — Validação: script de medição local + inspeção manual (clarificação)

**Decision**: `specs/046-dashboard-larguras-colunas/validar_local.py` no padrão das 039/042/044: renderiza as duas fases (estado V0 pré-alteração e V1 pós-alteração), mede por coluna (largura renderizada, quebras de linha por célula, alinhamento thead/tbody, truncamento sem tooltip), nas larguras de referência (desktop grande/médio, notebook, tablet, celular e zoom 80%–200%), e emite relatório comparativo antes/depois em `validacao_local.out.md`. Complemento manual: `validacao.md` com os cenários do pedido (SC-007). O script é ferramenta de validação pontual — **não entra na suíte pytest** (seção 29: sem testes artificiais).

**Rationale**: decisão explícita do solicitante (clarificação 2026-09-26); evidência reproduzível e comparável, mesmo mecanismo das irmãs.

## R7 — Fonte real e pisos (lição 036–044, reusada)

**Decision**: pisos de largura calibrados com a Plus Jakarta Sans (×1,25–1,30 sobre larguras monospace/fallback), padding real `.5rem .5rem` (16px/coluna), conjunto único em px sem media query de colunas (lição da 041), `min-width` da tabela ≈ soma das colunas com rolagem confinada ao `table-responsive` em viewport mínima.

## R8 — Tema claro/escuro e acessibilidade (preservação)

**Decision**: nenhuma cor/contraste novo é introduzido (apenas largura/quebra/truncamento); o `style="color:var(--c-text)"` inline do link do Equipamento permanece; tooltips usam o tema Bootstrap vigente (auto-inicializados); alinhamento à direita do header de Ações (`th.text-end`) e do corpo (`td.text-end`) preservados; controles permanecem clicáveis e acessíveis em todas as larguras validadas (FR-009/FR-014).

## R9 — Testes (seção 29 do pedido)

**Decision**: nenhum teste novo de UI/pytest (sem testes artificiais). Suíte existente como regressão (run focado: `test_rbac.py` + suíte completa no polish). Validação visual/medição via script local + registro manual (R6). O template do dashboard não possui teste dedicado de larguras — o gate de regressão é a suíte verde + medições comparativas.

## R10 — Documentação (Princípio XI)

**Decision**: `docs/ARQUITETURA_E_MANUTENCAO.md` não descreve larguras/responsividade de tabelas individuais (padrão 036–044 — nenhuma das irmãs atualizou o doc); a documentação fiel fica nos artefatos da spec (plan/data-model/contract/quickstart/validação). Sem atualização de doc global.
