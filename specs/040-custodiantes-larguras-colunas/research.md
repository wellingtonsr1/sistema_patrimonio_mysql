# Research: Ajuste Responsivo da Tabela "Colaboradores & Custodiantes" (040)

Incógnitas resolvidas com fatos do repositório e o mecanismo validado nas 036–039 (reuso aprovado pelo padrão das specs anteriores; C-1/C-5 deixam os valores finais para a medição na implementação). Nenhum NEEDS CLARIFICATION restante (as clarificações de spec — texto completo nas textuais — já estão registradas e incorporadas aos FRs).

## R1 — Onde vive o CSS: template embutido com classe de escopo (decisão 036–039, reusada)

**Decision**: CSS embutido em `custodians/list.html` (bloco `<style>` no topo do `{% block content %}`) com classe de escopo própria na tabela (ex.: `.cust-lista-table`); `style.css` intocado.

**Rationale**: idêntico às anteriores — `style.css` é global e versionado em 2 pontos acoplados (base.html + SW allowlist); bump invalidaria cache de todo o sistema. Precedente de comentário HTML de rastreabilidade da feature no `<style>` (036–039).

**Alternatives considered**: *`style.css` global*: rejeitado (cache global + FR-010 proíbe classes genéricas).

## R2 — `table-layout`: **fixed** justificado (C-5) — a análise, não a aplicação automática

**Decision**: `table-layout: fixed` + `<colgroup>` com `<col class="cN">` estilizadas no `<style>` escopado; larguras determinadas por medição na implementação (C-1).

**Rationale** (análise exigida pela seção 20 do pedido):
- **Por que fixed aqui**: (a) 7 colunas com conteúdos de comprimento muito variável (nomes completos, cargos, departamentos institucionais, e-mails) — o auto layout redistribui a cada linha e é a causa da compressão atual das textuais; (b) o resultado precisa ser estável entre pesquisas (conteúdo muda, larguras não); (c) as 036–039 comprovaram o mecanismo (5 a 9 colunas) com o mesmo perfil de problema; (d) `<colgroup>` resolve canonicamente a exigência thead=tbody (seções 17/18 do pedido).
- **Quando auto seria melhor**: tabelas de poucas colunas com larguras naturais estáveis — não é o caso (7 colunas com texto variável).
- Risco conhecido do fixed e mitigação: como as textuais exibem **texto completo** (clarificação), elas quebram naturalmente dentro da coluna (`break-word`) — o fixed não trunca nada aqui porque não há nowrap/ellipsis nas textuais; as rígidas (Matrícula/Bens/Ações) ficam em **px com folga** (lição da 039 — Plus Jakarta Sans ~20–30% mais larga que fontes de medição fallback).

**Alternatives considered**: *auto + min-width por coluna*: rejeitado — não garante proporção estável (causa do problema atual); *percentuais inline no colgroup*: rejeitado — não é sobrescrevível por media query (lição da 036).

## R3 — Larguras iniciais de partida (a medir/refinar na implementação — C-1)

**Decision**: pontos de partida sugeridos (soma 100%): **Matrícula ~11%**, **Nome ~19%**, **Cargo ~15%**, **Departamento ~16%**, **E-mail ~19%**, **Bens ~8%**, **Ações ~12%**. Textuais (Nome+Cargo+Departamento+E-mail) somam ~69% (SC-002 indicativo ✓); Ações ~12% acomoda o botão "Ver Bens" **com texto** (~90px) + "Editar" ícone (32px) + gap — a coluna de Ações mais larga da família 036–039 por exigência do conteúdo.

**Rationale**: natureza do conteúdo (fatos do data-model): Nome com ícone + nome completo (link); Cargo texto livre variável; Departamento em badge (texto completo — clarificação); E-mail sempre razoavelmente longo; Matrícula `tag-badge` monoespaçada + badge "provisória" condicional; Bens é 1 pill centralizado; Ações 2 controles. A medição inicial (V0) e a validação refinam — o padrão das anteriores mostrou 1–2 iterações de ajuste fino.

## R4 — Proteções de quebra e texto completo (clarificação, mapeado para esta tabela)

**Decision**:
- `overflow-wrap: break-word` nas td/th (fronteira de palavra — nunca no meio de palavra).
- **Nome, Cargo, Departamento e E-mail: texto completo, sem clamp nem reticências** (clarificação) — as linhas crescem conforme o conteúdo; nada de `white-space: nowrap`/`text-overflow: ellipsis` nessas células.
- `white-space: nowrap` no `tag-badge` da Matrícula (badge não quebra no meio; espelha 036–039). O badge "provisória" condicional fica ao lado, podendo quebrar para a segunda linha da célula sem problema (fronteira entre elementos).
- Badge do Departamento: `white-space: normal` (texto completo pode ocupar 2+ linhas dentro do badge — clarificação).
- **Preservar** `text-center` do Bens e `text-end`/`d-flex gap-1 justify-content-end` das Ações (contract §1).
- E-mail: quebra natural em fronteira de palavra quando inevitável (e-mails têm poucos pontos de quebra — coluna dimensionada para os e-mails reais).

**Alternatives considered**: *clamp/ellipsis nas textuais*: rejeitado — a clarificação do solicitante exige texto completo (diferente da 039, onde Motivo ficou em linha única; aqui o usuário pediu explicitamente o contrário). *Truncar e-mail*: rejeitado — esconderia dado exibido hoje (FR-013).

## R5 — Aproveitamento total (C-3/FR-001/AC-01)

**Decision**: fixed + percentuais (soma 100%) garante a tabela em 100% do card — nenhum `max-width` artificial; container/filtro/estados vazios intocados (FR-010). Medição V0 antes/depois documenta o aproveitamento (esperado ~100% antes e depois; o ganho real é a distribuição, como verificado na 037–039).

## R6 — Responsividade e min-width (padrão 036–039)

**Decision**: `min-width` inicial ~1150px (7 colunas; a medir — menor que a 039/1480px por ter menos colunas, mas maior que a 038/1180px por causa do "Ver Bens" com texto) — abaixo disso, `table-responsive` rola confinado (mecanismo do projeto); media query ≤768px para header compacto se a medição mostrar sobreposição. Proibido reduzir fonte drasticamente (seção 15 do pedido).

**Rationale**: mesma mecânica das anteriores, calibrada pelo conteúdo: as textuais com texto completo precisam de largura razoável para não gerar linhas altas demais; em tablet/celular a rolagem confinada é o comportamento esperado e documentado (C-4/contract §3; seção 16 do pedido).

## R7 — Temas e cores

**Decision**: nenhuma cor nova; apenas layout/quebra (mesma decisão das anteriores). `tag-badge`, badges `badge-soft-gray` e o pill de Bens herdam os temas via `style.css` intocado.

## R8 — Botões de Ação condicionais (RBAC)

**Decision**: nenhum toque nas condições Jinja (`can('colaboradores.editar')`); a coluna acomoda "Editar" (ícone 32px) + "Ver Bens" (ícone + texto, ~90px) — largura mínima dimensionada para o caso de 2 controles; `text-end` e o `d-flex gap-1 justify-content-end` internos preservados.

**Rationale**: FR-012 (nada funcional muda) — a largura da coluna não depende da permissão (coluna fixa por linhas).

## R9 — Testes e validação (SC-006/SC-007)

**Decision**: nenhum teste automatizado novo (seções 22/27 do pedido); suíte existente como regressão (baseline antes, focado durante, completo depois). Validação visual com medição real e screenshots nos cenários do pedido + zoom 80%–200%, registrada em `validacao.md` no formato das 036–039 (comparação antes/depois, tabelas de larguras com ajustes/motivos, decisões finas, observações preexistentes).

**Rationale**: processo validado quatro vezes de ponta a ponta. F1 da 039 aplicado por padrão: o run focado inclui os testes que efetivamente renderizam a página (identificar no baseline — ex.: `test_help.py`).
