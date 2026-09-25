# Research: Ajuste Responsivo da Tabela "Fluxo Global de Movimentações" (039)

Incógnitas resolvidas com fatos do repositório e o mecanismo validado nas 036/037/038 (reuso aprovado pelo padrão das specs anteriores; C-1/C-5 deixam os valores finais para a medição na implementação). Nenhum NEEDS CLARIFICATION restante (a única clarificação de spec — cap do Motivo — já está registrada e incorporada ao FR-008).

## R1 — Onde vive o CSS: template embutido com classe de escopo (decisão 036/037/038, reusada)

**Decision**: CSS embutido em `movements/list.html` (bloco `<style>` no topo do `{% block content %}`) com classe de escopo própria na tabela (ex.: `.mov-lista-table`); `style.css` intocado.

**Rationale**: idêntico às anteriores — `style.css` é global e versionado em 2 pontos acoplados (base.html + SW allowlist); bump invalidaria cache de todo o sistema. Precedente de comentário HTML de rastreabilidade da feature no `<style>` (036/037/038).

**Alternatives considered**: *`style.css` global*: rejeitado (cache global + FR-011 proíbe classes genéricas).

## R2 — `table-layout`: **fixed** justificado (C-5) — a análise, não a aplicação automática

**Decision**: `table-layout: fixed` + `<colgroup>` com `<col class="cN">` estilizadas no `<style>` escopado; larguras determinadas por medição na implementação (C-1).

**Rationale** (análise exigida pela seção 22 do pedido):
- **Por que fixed aqui**: (a) 9 colunas com conteúdos de comprimento muito variável (nomes de equipamentos, locais institucionais, custodiantes, motivos descritivos) — o auto layout redistribui a cada linha e é a causa da compressão atual das colunas textuais; (b) o resultado precisa ser estável entre consultas/filtros (conteúdo muda, larguras não); (c) as 036/037/038 comprovaram o mecanismo nas suas tabelas (5, 6 e 8 colunas) com o mesmo perfil de problema — esta é a de maior número de colunas (9); (d) `<colgroup>` resolve canonicamente a exigência thead=tbody (seções 19/20 do pedido).
- **Quando auto seria melhor**: tabelas de poucas colunas com larguras naturais estáveis — não é o caso (9 colunas).
- Risco conhecido do fixed e mitigação: conteúdo mais largo que a coluna transborda → quebras locais (`break-word`) + `nowrap` nos identificadores (lições 036/037/038) + `min-width` com rolagem confinada.

**Alternatives considered**: *auto + min-width por coluna*: rejeitado — não garante proporção estável (causa do problema atual); *percentuais inline no colgroup*: rejeitado — não é sobrescrevível por media query (lição da 036).

## R3 — Larguras iniciais de partida (a medir/refinar na implementação — C-1)

**Decision**: pontos de partida sugeridos (soma 100%): **Data / Hora ~8%**, **Tombamento ~8%**, **Equipamento ~15%**, **Tipo ~9%**, **Origem ~15%**, **Destino ~15%**, **Motivo ~15%**, **Operador ~9%**, **Ações ~6%**. Textuais (Equipamento + Origem + Destino + Motivo + Operador) somam ~63% (SC-002 indicativo ✓); Ações ~6% acomoda 2 botões-ícone lado a lado (~72px em ≥1440px).

**Rationale**: natureza do conteúdo (fatos do data-model): Data / Hora é `dd/mm/AAAA HH:MM` nowrap (16 chars); Tombamento é `tag-badge` curta; Tipo é badge (rótulo mais longo ~22 chars); Origem/Destino têm 2 linhas (local + custodiante) com nomes potencialmente longos; Motivo é o texto descritivo mais variável; Operador é 1 linha de nome; Ações 1–2 ícones. A medição inicial (V0) e a validação refinam — o padrão das anteriores mostrou 1–2 iterações de ajuste fino.

## R4 — Proteções de quebra (padrão 036/037/038, mapeado para esta tabela)

**Decision**:
- `overflow-wrap: break-word` nas td/th (fronteira de palavra).
- `white-space: nowrap` no `tag-badge` do Tombamento (FR-004 — espelha 036/037/038).
- **Preservar** o `text-nowrap` existente da célula de Data / Hora (funcional: `dd/mm/AAAA HH:MM` não pode quebrar entre data e hora — FR-003; é também a razão de `min-width` robusto).
- **Motivo (específico da 039)**: remover o cap `max-width:220px` inline (clarificação da sessão de clarify); **manter** `truncate-2` (corte em 2 linhas — padrão do sistema; FR-008). O corte continua dependente de `max-width`? Não — `truncate-2` usa `-webkit-line-clamp` + `overflow:hidden` e funciona com a largura que a coluna tiver; sem cap, a coluna aproveita o espaço disponível e o texto além de 2 linhas permanece oculto como hoje.
- **Origem/Destino multilinha**: cada célula tem 2 `div`s (local + custodiante, com ícones e fallbacks `-`); `break-word` em cada `div`; as duas linhas permanecem empilhadas (nunca lado a lado); ícones `bi bi-geo-alt`/`bi bi-person` preservados com os textos.
- Badge do Tipo (`badge-soft-primary`): coluna dimensionada para o rótulo mais longo ("Envio para Manutenção" ~22 chars) caber em 1 linha se possível (medição; lição da 037); se impossível sem roubar demais das textuais, permitir quebra do badge em fronteira de palavra e documentar em `validacao.md`.

**Alternatives considered**: *remover também o `truncate-2` (texto completo)*: rejeitado — alteraria o padrão visual do sistema (linhas altas); a clarificação do solicitante optou por manter 2 linhas. *Truncar local/custodiante com ellipsis*: rejeitado — esconderia dado exibido hoje (FR-014).

## R5 — Aproveitamento total (C-3/FR-001/AC-01)

**Decision**: fixed + percentuais (soma 100%) garante a tabela em 100% do card — nenhum `max-width` artificial (após remover o cap do Motivo, nenhuma largura máxima permanece na tabela); container/filtro/contagem intocados (FR-011). Medição V0 antes/depois documenta o aproveitamento (esperado ~100% antes e depois; o ganho real é a distribuição, como verificado na 037/038).

## R6 — Responsividade e min-width (padrão 036/037/038)

**Decision**: `min-width` inicial ~1180px (9 colunas; a medir) — abaixo disso, `table-responsive` rola confinado (mecanismo do projeto); media query ≤768px para header compacto se a medição mostrar sobreposição. Proibido reduzir fonte drasticamente (seção 17 do pedido).

**Rationale**: mesma mecânica das anteriores, calibrada: esta é a tabela mais larga do sistema (9 colunas) — em tablet/celular a rolagem confinada é o comportamento esperado e documentado (C-4/contract §3; seção 18 do pedido admite rolagem controlada quando necessária).

## R7 — Temas e cores

**Decision**: nenhuma cor nova; apenas layout/quebra (mesma decisão das anteriores). Badges `badge-soft-primary`, links com `color:var(--c-text)`/`var(--c-primary-text)` e `tag-badge` herdam os temas via `style.css` intocado.

## R8 — Botões de Ação condicionais (por conteúdo)

**Decision**: nenhum toque na condição Jinja (`{% if m.term_code %}`); a coluna acomoda 1–2 botões ("Imprimir Termo" + "Ver Bem", ou só "Ver Bem"); `text-end` da célula e o `d-flex gap-1 justify-content-end` internos preservados.

**Rationale**: FR-013 (nada funcional muda) — a largura da coluna não pode depender do conteúdo da linha (coluna fixa por linhas); dimensionada para o caso de 2 botões.

## R9 — Testes e validação (SC-006/SC-007)

**Decision**: nenhum teste automatizado novo (seções 22/29 do pedido); suíte existente como regressão (baseline antes, focado durante, completo depois). Validação visual com medição real e screenshots nos cenários do pedido + zoom 80%–200%, registrada em `validacao.md` no formato das 036/037/038 (comparação antes/depois, tabelas de larguras com ajustes/motivos, decisões finas, observações preexistentes).

**Rationale**: processo validado três vezes de ponta a ponta.
