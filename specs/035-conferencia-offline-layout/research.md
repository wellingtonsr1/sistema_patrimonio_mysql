# Research: Conferência Offline — responsividade e padronização visual (035)

Referências: [spec](spec.md) · [data-model](data-model.md) · [contracts](contracts/ui-shell-offline-contract.md) · [quickstart](quickstart.md)

## D1 — Marca empilhada: restaurar o padrão do sistema

**Decisão**: restaurar o empilhamento logo-acima/nome-abaixo no bloco de marca da shell, espelhando o padrão já usado pelo sistema: `.navbar-brand` do `app/web/static/css/style.css` (L197-223) declara `flex-direction: column; row-gap: .3rem; text-align: center;` com comentário "Marca empilhada: logo acima do nome, ambos centralizados entre si", logo 32px (`object-fit: contain`).

**Rationale**: é literalmente o padrão visual vigente das demais telas (Constitution X) e é o estado que o próprio template da shell tinha **antes** do commit `30d051e` (o comentário do CSS local da shell registrou "Marca empilhada como na navbar principal" — restaurar é reverter um desvio, não inventar layout).

**Alternatives considered**: manter lado a lado (rejeitado — destoa do sistema; é o problema da spec); copiar o `.navbar-brand` global via base.html (rejeitado — traria navbar administrativa proibida offline, FR-030 da 033).

## D2 — Container/largura: mesmo padrão das demais telas com exceção mobile (C-1)

**Decisão**: `<main>` da shell passa a `container-fluid py-4 px-lg-5 mx-auto` com `max-width: 90%` (idêntico ao `base.html` L314) para **≥768px**; em **≤767px** mantém `max-width: 100%` + padding lateral reduzido (`.75rem`), como hoje.

**Rationale**: elimina a única diferença estrutural real (92% vs 90% vs px-lg-4) sem penalizar o dispositivo de campo; a exceção mobile preserva o espaço útil de coleta em tela estreita (decisão C-1 do clarify).

**Alternatives considered**: 90% estrito em todas as larguras (rejeitado — perde espaço em celular sem ganho de consistência perceptível); manter 92% (rejeitado — não é "o mesmo padrão", objetivo central da spec).

## D3 — Grid pesquisa + "Ler QR" + tabela

**Decisão**: manter a estrutura existente (pesquisa e tabela já estão no mesmo `card`), garantindo que a linha `d-flex` da pesquisa use a largura integral do card (`w-100` implícito pelo flex do Bootstrap) e que o botão permaneça `btn-outline-primary` com `flex-shrink-0` (decisão C-2). O `table-responsive` existente fica como mecanismo de rolagem restrita (Bootstrap: wrapper com `overflow-x: auto`).

**Rationale**: a estrutura já está correta — o problema reportado é de larguras/desalinhamento decorrentes das regras de `main` (92%) e do espaçamento, não de composição; mudança mínima = menor risco (Princípio I).

**Alternatives considered**: grid Bootstrap (`row`/`col`) para a linha de pesquisa (desnecessário — flex já resolve e é o padrão local); trocar tabela por cards empilhados em mobile (rejeitado — mudança estrutural além do escopo).

## D4 — Header em telas estreitas (C-3)

**Decisão**: ≥768px: linha única (marca empilhada | código + status + tema). ≤767px: código do inventário e indicador de conexão quebram para uma segunda linha do próprio cabeçalho (flex-wrap com ordem declarada), sem esconder nenhum elemento.

**Rationale**: com a marca em duas linhas, manter 4 blocos numa linha de 320px espreme o indicador de conexão — crítico no fluxo offline; a quebra preserva tudo (decisão C-3).

**Alternatives considered**: linha única sempre com encolhimento (rejeitado — compromete legibilidade do status); esconder o código em mobile (rejeitado — FR-030 exige que a shell identifique o inventário; nada administrativo ≠ nada identificador).

## D5 — Service Worker: bump de versão de cache

**Decisão**: `CACHE_VERSION` em `app/web/static/js/sw.js` v24 → v25 (`"inventario-offline-v25"`). Nenhuma outra linha do SW muda (allowlist intocada — os mesmos estáticos continuam válidos; a shell em navegação cache-first recebe o novo HTML no primeiro acesso online).

**Rationale**: o SW serve cache-first tanto os estáticos da allowlist (`style.css?v=20260924` está na lista) quanto a navegação da rota da shell — sem bump, os dispositivos continuariam no layout antigo até limpeza manual do cache.

**Alternatives considered**: bump da querystring do style.css (necessário **se** `style.css` mudar — ver data-model; se apenas o CSS embutido do template mudar, a querystring não precisa mudar porque o HTML novo já chega com o bump de navegação); não bumpar (rejeitado — propagação falha).

## D6 — Validação visual: checklist manual

**Decisão**: validação por inspeção nos tamanhos 320/375/390/430/768/1024/1280/1366/1440/1920px, claro/escuro, retrato/paisagem, tabelas com poucos/muitos registros e textos longos, via DevTools device emulation ou dispositivos reais, registrada em `validacao.md` da feature (padrão da 034, Constitution XII).

**Rationale**: o projeto não possui infraestrutura de teste de UI/visual regression; a suíte pytest cobre não-regressão funcional/RBAC da rota.

**Alternatives considered**: introduzir Playwright/puppeteer só para esta feature (rejeitado — nova dependência/infra fora do escopo; Constitution I).

## D7 — Testes automatizados: suíte como rede de não-regressão

**Decisão**: nenhum teste pytest novo ou alterado. `tests/test_inventario_offline.py` (34 testes) já cobre a rota da shell (200 autenticado, 401, 403) e o ciclo offline; a suíte completa deve permanecer 100% verde (FR-015/SC-005).

**Rationale**: asserts de posicionamento visual não são viáveis sem infra de UI test (D6); a garantia de "funcionalidade inalterada" é exatamente o que a suíte existente verifica.

**Alternatives considered**: testes de snapshot de HTML (rejeitados — frágeis para mudança de layout e sem prática prévia no repo).
