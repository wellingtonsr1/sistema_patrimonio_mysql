# Research: Ajuste Responsivo da Tabela "Equipamentos" (038)

Incógnitas resolvidas com fatos do repositório e o mecanismo validado nas 036/037 (reuso aprovado pelo padrão das specs anteriores; C-1/C-5 deixam os valores finais para a medição na implementação). Nenhum NEEDS CLARIFICATION restante.

## R1 — Onde vive o CSS: template embutido com classe de escopo (decisão 036/037, reusada)

**Decision**: CSS embutido em `assets/list.html` (bloco `<style>` no topo do `{% block content %}`) com classe de escopo própria na tabela (ex.: `.assets-lista-table`); `style.css` intocado.

**Rationale**: idêntico às anteriores — `style.css` é global e versionado em 2 pontos acoplados (base.html + SW allowlist); bump invalidaria cache de todo o sistema. Precedente de comentário HTML de rastreabilidade da feature no `<style>` (036/037).

**Alternatives considered**: *`style.css` global*: rejeitado (cache global + FR-011 proíbe classes genéricas).

## R2 — `table-layout`: **fixed** justificado (C-5) — a análise, não a aplicação automática

**Decision**: `table-layout: fixed` + `<colgroup>` com `<col class="cN">` estilizadas no `<style>` escopado; larguras determinadas por medição na implementação (C-1).

**Rationale** (análise exigida pela seção 21 do pedido):
- **Por que fixed aqui**: (a) 8 colunas com conteúdos de comprimento muito variável (nomes de equipamentos, locais institucionais, S/N) — o auto layout redistribui a cada linha e é a causa da compressão atual das colunas textuais; (b) o resultado precisa ser estável entre páginas da paginação (conteúdo muda, larguras não); (c) as 036/037 comprovaram o mecanismo nas suas tabelas (5 e 6 colunas) com o mesmo perfil de problema; (d) `<colgroup>` resolve canonicamente a exigência thead=tbody (seções 18/19).
- **Quando auto seria melhor**: tabelas de poucas colunas com larguras naturais estáveis — não é o caso (8 colunas).
- Risco conhecido do fixed e mitigação: conteúdo mais largo que a coluna transborda → quebras locais (`break-word`) + `nowrap` nos identificadores (lições 036/037) + `min-width` com rolagem confinada.

**Alternatives considered**: *auto + min-width por coluna*: rejeitado — não garante proporção estável (causa do problema atual); *percentuais inline no colgroup*: rejeitado — não é sobrescrevível por media query (lição da 036).

## R3 — Larguras iniciais de partida (a medir/refinar na implementação — C-1)

**Decision**: pontos de partida sugeridos (soma 100%): **Tombamento ~11%**, **Equipamento/Modelo ~24%**, **Categoria ~9%**, **Status ~10%**, **Responsável ~15%**, **Localização ~19%**, **Valor ~7%**, **Ações ~5%**. Textuais somam ~58% (SC-002 indicativo ✓); Ações ~5% acomoda 2 botões-ícone lado a lado (~72px em ≥1440px).

**Rationale**: natureza do conteúdo (fatos do data-model): Equipamento/Modelo tem nome+auxiliar; Responsável tem nome+matrícula; Localização tem nomes institucionais longos; Categoria é badge curto; Valor é numérico nowrap curto; Status é 1 pill (rótulo mais longo "Em Manutenção"); Ações 1–2 ícones. A medição inicial (V0) e a validação refinam — o padrão das anteriores mostrou 1–2 iterações de ajuste fino.

## R4 — Proteções de quebra (padrão 036/037, mapeado para esta tabela)

**Decision**:
- `overflow-wrap: break-word` nas td/th (fronteira de palavra).
- `white-space: nowrap` no `tag-badge` do Tombamento (FR-003 — espelha 036/037).
- **Preservar** os `text-nowrap` existentes de Valor e Ações (funcionais: valor monetário e botões lado a lado não podem quebrar — são também a razão de `min-width` robusto).
- **Cuidado com o status-pill**: o rótulo ("Em Manutenção") com `::before` (bolinha) — se quebrar linha, o ponto desalinha. Estratégia: coluna Status dimensionada para o rótulo mais longo caber em 1 linha (medição; lição da 037 — badge "Em Andamento" precisou de célula ≥124px); se a medição mostrar impossibilidade sem roubar demais das textuais, permitir quebra no pill e compensar o alinhamento do ::before — decisão fina documentada em `validacao.md`.
- Linha auxiliar de Equipamento (marca/modelo • `S/N <code>`): `break-word` herdado; `<code>` não quebra no meio (comportamento padrão aceitável para serial).

**Alternatives considered**: *truncar S/N com ellipsis*: rejeitado — esconderia dado exibido hoje (FR-014).

## R5 — Aproveitamento total (C-3/FR-001/AC-01)

**Decision**: fixed + percentuais (soma 100%) garante a tabela em 100% do card — nenhum `max-width` artificial; container/filtros intocados (FR-011). Medição V0 antes/depois documenta o aproveitamento (esperado ~100% antes e depois; o ganho real é a distribuição, como verificado na 037).

## R6 — Responsividade e min-width (padrão 036/037)

**Decision**: `min-width` inicial ~1080px (8 colunas; a medir) — abaixo disso, `table-responsive` rola confinado (mecanismo do projeto); media query ≤768px para header compacto se a medição mostrar sobreposição. Proibido reduzir fonte drasticamente (seção 17 do pedido).

**Rationale**: mesma mecânica das anteriores, calibrada: a tabela de Equipamentos é a mais larga (8 colunas) — em tablet/celular a rolagem confinada é o comportamento esperado e documentado (C-4/contract §3).

## R7 — Temas e cores

**Decision**: nenhuma cor nova; apenas layout/quebra (mesma decisão das anteriores). `status-pill` e badges herdam os temas via `style.css` intocado.

## R8 — Botões de Ação condicionais (RBAC)

**Decision**: nenhum toque nas condições Jinja (`can('movimentacao.criar')`); a coluna acomoda 1–2 botões (largura mínima dimensionada para 2 ícones + gap); `text-end` e `text-nowrap` da célula preservados.

**Rationale**: FR-013 (nada funcional muda) — a largura da coluna não pode depender da permissão (coluna fixa por linhas).

## R9 — Testes e validação (SC-006/SC-007)

**Decision**: nenhum teste automatizado novo (seções 22/28 do pedido); suíte existente como regressão (baseline antes, focado durante, completo depois). Validação visual com medição real e screenshots nos cenários do pedido + zoom 80%–200%, registrada em `validacao.md` no formato das 036/037 (comparação antes/depois, tabelas de larguras com ajustes/motivos, decisões finas, observações preexistentes).

**Rationale**: processo validado duas vezes de ponta a ponta.
