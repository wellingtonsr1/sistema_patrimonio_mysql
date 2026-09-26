# Research: Ajuste Responsivo da Tabela "Usuários do Sistema" (043)

Incógnitas resolvidas com fatos do repositório e o mecanismo validado nas 036–042. Nenhum NEEDS CLARIFICATION restante — as 2 clarificações de spec (tooltip Bootstrap; username e full_name ambos com linha garantida) estão registradas e incorporadas aos FRs.

## R1 — Onde vive o CSS: template embutido com classe de escopo (decisão 036–042, reusada)

**Decision**: CSS embutido em `admin/users/list.html` (bloco `<style>` no topo do `{% block content %}`, com comentário de rastreabilidade "Feature 043") com classe de escopo própria na tabela (ex.: `.usr-lista-table`) e classe auxiliar de ellipsis (ex.: `.usr-ellip`, com tooltip Bootstrap); `style.css` intocado.

**Rationale**: idêntico às anteriores — `style.css` é global e versionado em 2 pontos acoplados (base.html + SW allowlist); bump invalidaria cache de todo o sistema. Comentários não citam controles do header (lição `b75ba99` — e `test_rbac.py:213/221` valida strings de link no HTML desta página).

**Alternatives considered**: *`style.css` global*: rejeitado (cache global + FR-010 proíbe classes genéricas).

## R2 — `table-layout`: **fixed** justificado (C-5)

**Decision**: `table-layout: fixed` + `<colgroup>` com `<col class="cN">` estilizadas no `<style>` escopado; larguras determinadas por medição na implementação (C-1).

**Rationale**: (a) 7 colunas com conteúdos de comprimento variável (e-mails, nomes completos, múltiplos badges) — o auto layout redistribui a cada linha, incompatível com a prioridade de **linha única estável** (C-4); (b) com fixed + nowrap/ellipsis, o corte é previsível e sem sobreposição; (c) `<colgroup>` resolve canonicamente thead=tbody (seção 19); (d) precedentes 041/042 comprovaram o mecanismo.
- Risco conhecido: células nowrap estreitas cortam texto — mitigado por ellipsis **+ tooltip Bootstrap** (clarificação) e pisos da fonte real (R3/R11). **Badges são o caso especial** (R4).

**Alternatives considered**: *auto*: rejeitado — larguras instáveis e quebra por conteúdo; *percentuais inline no colgroup*: rejeitado (lição da 036).

## R3 — Larguras iniciais de partida (a medir/refinar na implementação — C-1)

**Decision**: pontos de partida sugeridos (soma ≈ 1330px, coerente com 041/042; ajustável ao conteúdo real): **Usuário ~150px** (username + ADMIN; full_name corta com tooltip), **E-mail ~200px** (maior textual — e-mails longos cortam com tooltip), **Origem ~120px** (badge "Active Directory" com ícone — pior caso), **Perfis ~150px** (badges flex-wrap), **Status ~90px** ("Bloqueado"), **Último Acesso ~150px** (`dd/mm/YYYY HH:MM`), **Ações ~70px** (1 botão-icon). Rígidas/nowrap com folga ×1,25–1,30 (Plus Jakarta Sans; padding `.5rem .5rem` = 16px/coluna). Valores finais por medição (V0 antes/depois).

## R4 — Mecanismo de linha garantida + tooltip Bootstrap (clarificações — o coração da 043)

**Decision**:
- **Rígidas**: Origem (badge curto "Local"/AD com ícone), Status (badge "Ativo"/"Bloqueado"), Último Acesso (`text-nowrap` já existente), Ações (`text-nowrap` já existente) — nowrap.
- **Textuais com linha garantida (ellipsis + tooltip Bootstrap)**: **E-mail**; e **as duas linhas da coluna Usuário** — username (span com tooltip; o ícone e o badge ADMIN ficam fora do span cortável) e `full_name` (span próprio com tooltip; segunda linha informativa preservada). Marcação: `data-bs-toggle="tooltip" data-bs-placement="top" title="{{ ... }}"` — auto-inicializada em `base.html:329–333`/`main.js` (mesmo mecanismo da 042).
- **Perfis (C-6, caso especial)**: os badges individuais **não** recebem ellipsis (nunca cortam o papel de usuário — dado funcional); o container `d-flex flex-wrap gap-1` permanece, permitindo organização entre badges quando a largura não bastar; cada badge quebra apenas entre palavras se necessário (`.usr-lista-table .badge { white-space: normal; }` — lição direta da 042, onde o nowrap embutido do Bootstrap transbordava a célula fixa).
- **Badge "Active Directory"** (Origem): idem — `white-space: normal` escopado para quebra entre palavras se a coluna ficar estreita; com a partida de ~120px normalmente cabe em uma linha.
- Último Acesso: sem truncamento necessário (largura fixa do conteúdo); "Nunca" sem tooltip.

**Alternatives considered**: *ellipsis nos badges de Perfis*: rejeitado — cortaria informação funcional (C-6); *tooltip nativo*: rejeitado — clarificação explícita pelo Bootstrap; *quebra generosa nas textuais (padrão 041)*: rejeitado — C-4 prioriza linha única com corte controlado (padrão 042).

## R5 — Aproveitamento total (C-3/FR-001/AC-01)

**Decision**: fixed + colgroup com soma ≈ container → tabela em praticamente 100% do card; nenhum `max-width` artificial; container/header/filtro/estado vazio intocados (FR-010). Medição V0 antes/depois documenta o aproveitamento.

## R6 — Responsividade e min-width (padrão 041/042: conjunto único)

**Decision**: `min-width` único sincronizado com a soma do colgroup (≈1330px, a calibrar) — abaixo disso, rolagem confinada ao `table-responsive` (mecanismo do projeto); sem media query de colunas (lição da 041). Em janelas ≥ ~1470px, sem rolagem; em menores, rolagem autorizada. Zoom 80%–200% coberto pela estabilidade px.

## R7 — Temas e cores

**Decision**: nenhuma cor nova; apenas layout/quebra. Badges `badge-soft-*`, `bg-success-subtle`, cores `var(--c-text)` e `text-muted` herdam os temas via `style.css` intocado.

## R8 — RBAC e comentários

**Decision**: nenhum toque nas condições Jinja (`{% if u.is_admin %}`, `{% if u.full_name %}`, `{% if u.role_names %}`, `{% if can('usuarios.editar') %}`, `{% if u.auth_provider == 'ad' %}`) e fallbacks. **Comentários CSS/HTML novos NÃO citam controles do header** (lição `b75ba99`); atenção redobrada porque `test_rbac.py:213/221` valida presença/ausência do link `/admin/users` no HTML desta página — a alteração não introduz nem remove strings de controles.

**Rationale**: FR-013; os tooltips carregam **dados das linhas** (username, full_name, e-mail), não strings de controles.

## R9 — Testes e validação (SC-006/SC-007)

**Decision**: nenhum teste automatizado novo (seção 28 do pedido); suíte existente como regressão. Run focado: `pytest tests/test_help.py tests/test_rbac.py tests/test_admin_users.py -q` (renderizam a página/exercitam o domínio e os gates; **identificar o arquivo exato de testes de admin/users no baseline** — se não existir, o focado é help+rbac). Validação visual V0–V5 (sem bloco de impressão nesta tela — não é relatório) registrada em `validacao.md` no formato das anteriores, **com conferência dos tooltips no navegador**.

**Rationale**: processo validado sete vezes; F1 da 039 (run focado = testes que renderizam a página).

## R10 — Sem bloco de impressão (diferença da 041/042)

**Decision**: `admin/users/list.html` **não é relatório** — não possui `.report-print` nem participa do `@media print` dos relatórios; a 043 NÃO adiciona bloco de impressão. A tabela em impressão segue o comportamento global existente (fora do escopo). Nenhuma regra `@media print` é criada ou alterada.

**Rationale**: seção 24 do pedido ("Não alterar impressão/outras telas"); evita vazar escopo para o domínio de impressão das 013/041/042.

## R11 — Medição local com WeasyPrint (opcional, padrão 039–042)

**Decision**: reusar o script local (padrão 041/042): TestClient + login admin + seed de edge cases (admin com ADMIN, full_name longo, e-mail longo, múltiplos perfis, "Sem perfil", AD e Local, "Nunca", usuário sem permissão de editar), medição das `<col>` em `media_type="screen"` (não há passada print nesta tela). Limitações: fonte fallback (pisos ×1,25–1,30) e `min-width` não imposto pelo WeasyPrint (verificar pisos por coluna); tooltips não são medidos (verificação manual no navegador).
