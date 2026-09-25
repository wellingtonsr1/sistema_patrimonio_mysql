# Research: Ajuste Responsivo da Tabela "Inventário Patrimonial" (037)

Incógnitas técnicas resolvidas com fatos do repositório e com as decisões validadas na feature 036 (mesma família de problema — o mecanismo foi explicitamente aprovado para reuso na clarificação de 2026-09-25). Nenhum NEEDS CLARIFICATION restante.

## R1 — Onde vive o CSS: template embutido com classe de escopo (decisão da 036, reusada)

**Decision**: CSS da tela embutido em `list.html` (bloco `<style>` no topo do `{% block content %}`), com classe de escopo própria na tabela (ex.: `.inv-lista-table`); `style.css` global intocado.

**Rationale**:
- Idêntico ao R1 da 036: `style.css` é carregado por todas as páginas e versionado em 2 pontos acoplados (`base.html` + allowlist do SW) — bump invalidaria cache global por uma mudança de uma tela.
- `list.html` não tem block de `head`; `<style>` no início do `content` é válido e já é o padrão do repositório (`offline.html`, `detail.html` da 036).
- O comentário HTML no `<style>` segue o padrão deixado pela 036 (rastreabilidade da feature no código).

**Alternatives considered**: *`style.css` global*: rejeitado (cache global + FR-011 proíbe classes genéricas que afetem outras tabelas).

## R2 — Mecanismo de layout: `table-layout: fixed` + larguras por classes (da 036), com medição antes

**Decision**: `table-layout: fixed` + `<colgroup>` com `<col class="cN">` estilizadas no `<style>` escopado. As larguras específicas são determinadas pela implementação por **medição da renderização atual** (C-1: a spec não fixa percentuais), seguindo a prioridade C-2 (Inventário/Escopo maiores; Código/Progresso/Status intermediários; Ações mínima).

**Rationale**:
- O mesmo mecanismo foi validado na 036 com 5 problemas reais detectados e corrigidos pela validação visual (badge nowrap transbordando, headers sobrepostos em tablet, quebra no meio de palavra, tombamento espremido, largura mínima) — reusar reduz risco a quase zero.
- Por que fixed aqui: as colunas têm conteúdo de comprimento muito variável (`scope_filters` String(255), nomes longos) e o layout automático é a causa atual da má distribuição; fixed com larguras bem medidas dá estabilidade (seção 19 do pedido pede análise — esta é a análise, com precedente comprovado).
- `<colgroup>` garante a mesma estrutura para thead e tbody (FR-009 — a seção 17 do pedido exige consistência estrutural; col/colgroup é o mecanismo canônico para isso).

**Alternatives considered**:
- *Auto layout com `min-width` por coluna*: rejeitado — não garante proporção estável (o navegador continua redistribuindo por conteúdo; foi a causa do problema na 036).
- *Percentuais inline no colgroup*: rejeitado — não é sobrescrevível por media query (lição da 036: classes permitem ajuste responsivo).

## R3 — Larguras iniciais de partida (a medir/refinar na implementação)

**Decision**: pontos de partida sugeridos para a medição (ajustáveis pela implementação): **Código ~11%** (código `INV-YYYY-NNNN` = 12 chars + badge), **Inventário ~30%** (nome + linha "Criado em … por …"), **Escopo ~26%** (`scope_filters` longo), **Progresso ~17%** (badges empilhados + "X/Y conferidos"), **Status ~9%** (badges curtos), **Ações ~7%** (1 botão-ícone). Inventário+Escopo ≈ 56% (SC-002 indicativo ✓).

**Rationale**: derivado da natureza do conteúdo (fatos do data-model) e do resultado final validado da 036 (Tombamento 20/Bem 26/Local 29/Resultado 15/Conferir 10 — mesma lógica de dimensionar por conteúdo + header bold). A validação visual refinaria caso algum badge/valor estourasse.

## R4 — Proteções de quebra (padrão da 036, adaptado)

**Decision**:
- `overflow-wrap: break-word` nas td/th (quebra prefere fronteira de palavra; nunca `anywhere` como padrão).
- `white-space: nowrap` no `tag-badge` da coluna Código (código integral — FR-003; espelha o tombamento da 036).
- `white-space: normal` nos `.badge` da tabela (Bootstrap é nowrap: os badges do Progresso precisam poder quebrar/empilhar dentro da coluna — lição direta da 036).
- Linhas auxiliares ("Criado em…", "X/Y conferidos") herdam `break-word`.
- **Código da coluna Código**: o valor `INV-YYYY-NNNN` contém hífens — sem `nowrap` excessivo além do badge (o badge em si não quebra; o colgroup garante largura).
- Status: badge íntegro (nowrap normal do Bootstrap fica OK pois rótulos são curtos — "Em andamento" cabe em ~9% de ≥1200px; se a medição mostrar quebra inadequada, aplicar `white-space: normal` como nos demais badges).

**Rationale**: exatamente o conjunto validado na 036 (R3/R4 dela), mapeado para os conteúdos desta tabela.

## R5 — Aproveitamento total da largura (C-3/FR-001/AC-01)

**Decision**: a tabela já é `width: 100%` dentro do `card` — o aproveitamento total decorre naturalmente do layout fixed com percentuais (que sempre somam 100%); **nenhum `max-width` artificial**; o container (`base.html` + `card`) **não é alterado** (FR-011).

**Rationale**: se houver "tabela pequena com espaço vazio" no estado atual, é efeito da distribuição automática das colunas (colunas de texto comprimidas não empurram a tabela a expandir — a tabela tem 100% de width mas o espaço se concentra mal). Com fixed+percentuais, o espaço passa a ser distribuído por decisão, não por conteúdo. Medição inicial na implementação confirmará o baseline (print antes/depois para o validacao.md, seção 25 do pedido).

## R6 — Responsividade e min-width (padrão da 036)

**Decision**: `min-width` na tabela (valor inicial ~860px a medir — 6 colunas com conteúdo mínimo legível); abaixo disso o `table-responsive` existente rola horizontalmente **dentro do card** (comportamento do projeto, contract §3); media query ≤768px apenas para header compacto (fonte/padding), se a medição mostrar sobreposição.

**Rationale**: mesma mecânica validada na 036 (min-width 700px lá; aqui a tabela tem 6 colunas e Progresso é mais largo — o valor exato sai da medição). Evita cabeçalhos sobrepostos e badges espremidos em tablet/celular (seção 14/15 do pedido), sem reduzir fontes drasticamente (proibição explícita da seção 15).

## R7 — Temas e cores

**Decision**: nenhuma cor nova; apenas propriedades de layout/quebra. Nada a preservar além de não introduzir cores literais (mesma decisão R7 da 036).

## R8 — Testes e validação (SC-006/SC-007)

**Decision**: nenhum teste automatizado novo (seção 26 do pedido: não criar testes artificiais; sem infra de UI test — D7 da 035, mantido na 036). Suíte existente como regressão (baseline antes + após). Validação visual com medição real e screenshots nos cenários do pedido (desktop grande/médio, notebook, tablet, celular) + zoom 80%–200%, registrada em `validacao.md` no mesmo formato da 036 (que incluiu: tabelas de larguras adotadas, observações preexistentes fora de escopo, decisões finas).

**Rationale**: processo validado na 036 de ponta a ponta (spec → tasks → implement → validação → deploy).
