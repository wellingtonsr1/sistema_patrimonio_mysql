# Research — 069-acessibilidade-login-inventario

> Decisões técnicas levantadas na **leitura de código (somente leitura)**. Cada `R` responde a uma pergunta concreta e aponta para a evidência usada. Nenhum arquivo foi alterado nesta etapa; a implementação futura deve partir daqui — **não** da suposição da análise de origem.
>
> **Rev. 2 (2026-10-12)** — revisão linha a linha contra o código antes da aprovação de P1/P2. Correções principais: `base.html` **já tem** `<main>` (R8 reescrito); os botões "Filtrar"/"Localizar" **têm texto visível** (riscos de ícone puro reduzidos ao verdadeiramente só-ícone — R7); contagens de `role="alert"` e de `conferir.html` corrigidas; trechos corrompidos do R5 reescritos; contraste com base real nos estilos da casa (R4); `conferir.html` **alerta de erro sem `role="alert"`** confirmado (RN-6 segue válido).

## R1 — Confirmação do que são U3 e U4 (T001/T005 do tasks.md)

- **U3** (`docs/ANALISE_SEG_PERF_UX_2026-10-10.md:115`): "Acessibilidade fraca" — 29 ocorrências de `aria-*` em 53 templates; **0** em `dashboard.html`, `login.html`, `403.html`, `404.html`; recomendação de axe/Lighthouse, `label[for]` nos inputs, `aria-live` em mensagens de erro, `aria-label` em botões só-ícone, contraste dos estados de status.
- **U4** (idem, linha seguinte): foco/teclado no campo de trabalho — `autofocus` em "apenas 2 templates"; recomendado no campo de leitura da conferência de inventário (`inventarios/detail`, `/inventarios/{id}/offline`) + "Enter confirma" + som de feedback.
- **Correção de contexto (2026-10-12, rev. 2)**: os templates hoje são **54** e os atributos ARIA já somam **47 ocorrências** (33 de `aria-*` + 36 de `role="*"`, com sobreposição em elementos que têm ambos). O número 29 é histórico. A afirmação "0 em login.html" contava só `aria-*` — o `role="alert"` do erro de login (`login.html:58`) não entra nessa conta.
- **Decisão**: os requisitos desta spec usam a **recomendação** (labels, alertas, axe, teclado), não os números, que são pontos de partida.

## R2 — Inventário dos formulários dos fluxos-alvo (T002/T003)

Contagens medidas por arquivo (rev. 2):

| Arquivo | `<input|select|textarea>` | `<label>` | com `for=` | Observação |
|---|---|---|---|---|
| `login.html` | 3 (2 visíveis + 1 hidden) | 2 | **2** (`username`, `password`) | ✅ os dois campos têm label correto |
| `setup.html` (primeiro acesso) | 5 | 5 | **5** | ✅ correto |
| `inventarios/list.html` | 2 (busca + status) | **0** | — | ❌ dois controles sem rótulo (busca e status do filtro) |
| `inventarios/new.html` | 4 | 4 | **0** | ❌ labels presentes, sem `for` |
| `inventarios/detail.html` | 15 | 10 | **0** | ❌ tombamento + filtro da lista + "Local/Observação" dos modais |
| `inventarios/conferir.html` | 9 | 9 | **0** | só "Local/Observação" soltos + grupo de rádios |
| `inventarios/offline.html` | 7 | 7 | **0** | mesmo padrão da conferência |

**Detalhes importantes (quase-acertos, não erros):**

- **Rádios de resultado**: em `conferir.html:70-84`, `detail.html:431-447` e `offline.html:307-323`, cada `input[type=radio]` está **dentro de um `<label>`** → associação implícita correta (o texto do card vizinho "Resultado da conferência" é o rótulo do grupo, `conferir.html:68`, `detail.html:429`, `offline.html:307`; **mas `<label>` com `for` solto sem campo** — ver R7). O que falta é o `fieldset`/`legend`.
- **"Local onde foi encontrado" e "Observação"**: `<label>` **não envolve** o campo e **não tem `for=`** (`conferir.html:88,97,117,126`, `offline.html:327,332`, `detail.html:449,458`) → **sem associação**. Este é um achado real.
- **Busca da lista de inventários** (`list.html:32-34`) e **status** (`list.html:37-42`): input e select com placeholder/opção dummy, ícone decorativo em `span` (não é rótulo). Placeholder não é nome acessível.
- **Campo de tombamento** (`detail.html:189`): tem `placeholder` descritivo e `autofocus` ✅ — mas nenhum rótulo programático.
- **Filtro da lista de itens** (`detail.html:214-222`): input `search` + select `status_filter` (mesmo padrão sem rótulo) + **botão só-ícone `bi-funnel` sem `aria-label`** (`detail.html:222`) — único botão pure-icon dos fluxos-alvo.
- **`togglePassword`** (`login.html:78-80`, `setup.html:97-100` e `toggleConfirmPassword` `setup.html:101-104`): botão só-ícone **sem `aria-label`, sem `title`, sem `aria-pressed`**; o ícone muda (eye↔eye-slash) e o nome anunciado fica vazio.
- **Link "Limpar Filtros"** (`list.html:41`): `<a>` com `title` no `a` e ícone `bi-x-lg` — `title` nem sempre é lido por leitores de tela; `aria-label` explícito é o fix (RN-4).
- **Exportar dropdown** (`detail.html:18`): botão dropdown **com texto visível** ("Exportar") — `aria-expanded` presente; não requer fix. *(Correção da rev. 1, que listava como só-ícone.)*
- **Botões "Filtrar"** (`list.html:43`) e **"Localizar"** (`detail.html:192`): texto visível + ícone que só se sobrepõe a texto em largura mínima (`w-100` cola ícone e texto) — **não são só-ícone**; sem fix. *(Correção da rev. 1.)*
- **`btn-close`** dos modais: `detail.html:415,481`, `offline.html:299` já têm `aria-label="Fechar"` (Bootstrap). `conferir.html` não abre modal (página dedicada) ✅.

## R3 — `aria-live` / mensagens dinâmicas (T004)

- `aria-live` = **0 ocorrências** em todo `app/web/templates/` (rev. 2 confirmado).
- `role="alert"` tem **36 ocorrências** no total (rev. 2; 30 atribuídos por grep e 6 via formulários de alerta com `role` herdado), inclusive no erro de login (`login.html:58`) e nos alertas de `detail.html` (sucesso/erro) ✅. São todas server-side no HTML da resposta.
- **Achado real nos fluxos-alvo**: `conferir.html:17-20` — o **alerta de erro vindo da submissão do formulário NÃO tem `role="alert"`** (ao contrário de `login.html:58`). É o único dos fluxos-alvo sem o atributo no alerta de erro; corrigir (RN-6/T024).
- **Mensagens de estado** (`offline.html` — status de coleta, contador da caixa): text updates dinâmicos em JS. **Sem `role="status"`/`aria-live`** hoje. **Decisão**: `role="status"` nos contadores (`offline.html`), inclusive no **contador de coletas do formulário** quando a conta de "coletas desta caixa" muda.
- **Modais**: Bootstrap 5 modal já gerencia foco/aria por si (`aria-hidden`, `tabindex=-1` em `offline.html:291`, `detail.html:408,475`) — nenhuma violação de *live region* a corrigir.
- **Exceção justificada (a documentar no AC-A2/A4)**: se entrar AJAX de conferência fora da página offline (fora do escopo), aí sim entra `aria-live="polite"` em `div` de status.

## R4 — Contraste e estados de status (T009)

- **Base real da casa (rev. 2; a rev. 1 não olhou o CSS)**: `app/web/static/css/style.css` já tem estilos de foco: `.form-control:focus`/`.form-select:focus` com `border-color + box-shadow` (L585-591). Os `btn-*` e itens dropdown recebem estilos de hover/focus que **preservam o foco visível default do navegador** (nenhum `outline:none`/`outline-0` no arquivo — verificado por grep). Com Bootstrap 5.0+ e `:focus-visible` nativo, o foco **não está invisível** — só os `.result-option` (grandes, customizados) têm `cursor:pointer` e **sem indicador de foco próprio** (L518, só borda): risco específico e justificado nestes itens.
- Badges `badge-soft-*`/`status-pill-*` sobre `--c-*` claro/escuro: **sem medição** nesta etapa; os tokens da casa estão centrais e consistentes (`style.css` direciona `--c-*` a cada tema).
- **Decisão**: contraste fica **subordinado a varredura axe em estado real** (claro + escuro); intervenção preventiva em CSS **só** onde o fix é barato e comprovado — **adicionar indicador de foco visível para `.result-option`** (o único caso com evidência concreta de baixa visibilidade, decisão P3). Nada de mudança global (Constitution I).

## R5 — Infraestrutura de testes de interface (T011)

- **Não existe teste de interface com navegador** no projeto: `requirements.txt` não traz Playwright/Selenium/Cypress; prefixo `axe` não aparece em nenhuma dependência. Testes atuais: **pytest + FastAPI TestClient** (`tests/conftest.py`, SQLite in-memory) → válido sobre HTML server-side, **sem executar JavaScript**; portanto axe-core (JS, precisa de browser) não roda neles.
- Precedentes rejeitados por mesma razão: `specs/013-impressao-relatorios/research.md:61` (Playwright/PDF diff — rejeitado) e `specs/035-conferencia-offline-layout/research.md:51` (Playwright/puppeteer só para a feature — rejeitado, "nova dependência/infra fora do escopo").
- **Alternativas avaliadas (rev. 2 — texto reescrito)**:
  1. **Playwright + axe** (bundle de browser ~150-300 MB): cobre tudo de ARIA semântico, inclusive contrastes computados; porém dependência pesada nova, contra os precedentes e sem aprovação do responsável.
  2. **axe via node/CDN**: sai do stack Python/uvicorn e exige node em máquina de operação — arquitetura nova fora do certificado/portas padrão da casa; inviável sem aprovação.
  3. **Verificação estática dos HTML com parser da stdlib** (`html.parser`): sem binário, sem browser, sem dependência; cobre o subconjunto de regras "presença de nomenclatura e associação" (label+for / label implícito / aria-label / aria-labelledby; radios com fieldset; role=alert nos alertas de erro; ids únicos). **Não cobre**: contraste (precisa de render), semântica de anúncio de foco (não é atributo) e eficácia real com leitor de tela.
- **Decisão (T012/T013)**: **opção 3** — `tests/test_acessibilidade_estatica_069.py`, parser `html.parser`, aplicado ao HTML das **rotas existentes** (nada de rota nova → `tests/route_manifest.json` não muda; Constitution). **Correção de expectativa para AC-A3/SC-A3**: a suíte é critério de aceitação do **subconjunto**, não "zero violações críticas/graves do axe" — o axe com browser fica no backlog (`docs/Melhorias_SisPatrimonio_Pro.md`) como evolução futura.

## R6 — Teclado e foco (T014, U4)

- `login.html:70`: username tem `autofocus` ✅ e `autocomplete="username"`; password `autocomplete="current-password"` ✅ (ordem DOM lógica: user → senha → Entrar → Primeiro acesso).
- `inventarios/detail.html:189`: tombamento tem `autofocus` ✅. **"Enter confirma"** no formulário web é submissão nativa do form (Enter submete) — nada a construir, só verificar (o "Enter confere + som de feedback" do U4 pertence ao **offline**, o PWA — fora do escopo web desta spec).
- `inventarios/offline.html:285`: botão "Ler QR" é `<button>` **teclável por default** e já tem `aria-label="Ler QR do tombamento"` ✅ (Bootstrap `data-bs-toggle=modal`).
- **Foco visível**: `form-control`/`form-select` e `btn-*` **keep o foco default do Bootstrap/navegador** (nenhum `outline:none` no `style.css` da casa — verificado) ✅. **Lacuna concreta e pequena: `.result-option`** (cards grandes de rádio da conferência) não tem indicador de foco próprio no CSS da casa (L518: só borda) — o percursor do teclado é o `:focus` nativo do `input[type=radio]` inside (pode não ser visível dentro do card com borda própria). **Fix proposto (barato, local e documentado)**: regra para `.result-option:has(input:focus)` ou `input:focus + span` (adicionar `outline` no card) — decisão P3 abaixo.
- **Ordem de tabulação**: DOM em ordem lógica nos dois fluxos (header → formulário → botões); nada de `tabindex` positivo (não encontrado) — sem intervenção.

## R7 — Regras propostas para `label[for]` campo a campo (T006)

| Arquivo | Campo | Hoje | Regra proposta |
|---|---|---|---|
| `login.html` | username / password | ✅ `for` correto | **não tocar** |
| `setup.html` | todos | ✅ `for` correto | **não tocar** |
| `inventarios/list.html` | busca | ❌ sem rótulo | técnica P1 (abaixo) — `aria-label="Buscar inventários por código ou nome"` |
| `inventarios/list.html` | status | ❌ | técnica P1 — `aria-label="Status do inventário"` |
| `inventarios/new.html` | nome/local/setor/obs | ❌ labels sem `for` | **adicionar `for=`/`id=`** (labels visíveis existentes — correção trivial; RN-2) |
| `conferir.html` · `detail.html` · `offline.html` | "Local onde foi encontrado" / "Observação" | ❌ | **adicionar `for=`/`id=`** (em `detail.html`, sufixo `{{ item.id }}` nos `id` — RN-7) |
| `conferir.html:68` · `detail.html:429` · `offline.html:307` | `<label>` "Resultado da conferência" | ✅ ** título atual é `label` sem `for`** | **converter para `<legend>` de um `<fieldset>`** (o grupo é de rádios; `label` solto sem `for` é inválido) — RN-5 |
| `inventarios/detail.html` | tombamento (U4) | placeholder apenas | técnica P1 — `aria-label="Escaneie ou digite o tombamento"`; `autofocus` mantido |
| `inventarios/detail.html` | filtro search/status | ❌ | técnica P1 — input + select com `aria-label` |
| login/setup | `togglePassword` / `toggleConfirmPassword` | ❌ sem nome | `aria-label="Mostrar senha"`/`"Ocultar senha"` + `aria-pressed` sincronizado no JS do toggle |
| `detail.html:222` | botão `bi-funnel` | ❌ só-ícone | `aria-label="Aplicar filtros"` |
| `list.html:41` | link "Limpar filtros" | `title` apenas | `aria-label="Limpar filtros"` no `<a>` |

**P1 — técnica para os controles compactos (decisão do responsável, pendente)**:
- **Proposta recomendada**: `aria-label` direto no input/select. Preserva layout aprovado; bootstrap do `input-group` e `table-header` dos filtros não têm espaço para label crescer; o texto do placeholder dá redundância visual para quem lê a tela.
- **Alternativa rejeitada por custo de revisão**: `<label class="visually-hidden">` — tecnicamente melhor (label real) e compatível com Bootstrap, mas exige `id` em cada campo + stats de estilo; não é a escolha mínima. Se o responsável preferir rigor WCAG máximo, aceitar que o fix dos filtros seja maior.

**P3 — foco nos `.result-option` (pendente)**: incluir no CSS da casa um indicador visível do card focado (a alternativa é marcar `.result-option` como dentro do `label`), recomendado **sim** — barato, arquivo próprio (`style.css`, 3 linhas), sem tocar layout.

## R8 — Semântica global do base.html (T011/T014)

- **Correção da rev. 1**: `base.html:313` **já tem `<main class="container-fluid ...">`** ✅ — a feature de login (standalone) e a offline (markup próprio, `.offline-*`, sem `base.html`) não usam `<main>`; nestas duas apenas, avaliar adicionar `<main>` (login e offline renderizam conteúdo único na página = semântica natural de região principal). `[SEM UMA BARRA DE NAVEGAÇÃO]` no login é aceitável — página de login autocontida.
- **Skip-link**: nenhum mecanismo "pular para conteúdo" em `base.html`. A navegação da sidebar já é marcada com `aria-label` em alguns botões (`darkToggle`, "Abrir menu", "Ajuda e Manual"); landmarks necessários: `<nav>` já fornecido implicitamente (sidebar é `<nav>`, linha ~150) e `<main>` existe — a lacuna real é o **skip-link do header para o conteúdo**. **P2 (decisão)**: incluir skip-link global agora (1 link invisível na abertura, foca no topo do `<main>` — risco de layout baixo: posição `absolute`, só aparece ao foco) ou postergar para spec própria. A recomendação da casa é **incluir** (mínimo invasivo — apenas um `<a>`, sem tocar nenhum template filho; testes existentes não dependem do DOM do header).
- Landmarks adicionais (`header`, `footer`): fora do escopo imediato (o `<nav>` da sidebar e o `<main>` já bastam para a navegação por leitor de tela nesta feature).

## R9 — Estratégia de testes e regressão

- **Suíte nova** (estática, sem browser): `tests/test_acessibilidade_estatica_069.py` com:
  - `client.get('/login')`, `client.get('/setup')`, `client.get('/inventarios')` (com permissão), `client.get('/inventarios/new')` (com `inventario.criar`), `client.get('/inventarios/{id}')`, `client.get('/inventarios/{id}/conferir/{item_id}')`, `client.get('/inventarios/{id}/offline')` — rotas **existentes**, nenhuma nova (Constitution → `tests/route_manifest.json` intocado);
  - parser `html.parser` com contadores de: inputs sem nome acessível (label+for / label ancestral / aria-label / aria-labelledby), botões só-ícone sem nome, radios sem `fieldset`/`legend`, alertas de erro sem `role="alert"`, `id` duplicados;
  - **critérios** (rev. 2): **0 controles sem nome acessível** nas 7 páginas; 0 radios sem `fieldset` na conferência; `role="alert"` presente no erro de login **e** no de conferir; 0 `id` duplicado por página.
- **Regressão obrigatória**: `tests/test_inventario.py`, `tests/test_inventario_offline.py`, `tests/test_rbac.py`, `tests/test_help.py`, `tests/test_route_inventory.py` (manifesto intacto), suíte completa no final. Nenhum teste existente editado.
- **O que NÃO testar**: JS não é executado (contrário a testar `aria-pressed` do toggle — o critério fica na presença do atributo inicial; o JS do `main.js` deve manter sincronização, verificada no quickstart). Contraste não é mensurável sem render (manual/axe-futuro).
- **TDD**: testes estáticos escritos primeiro contra os templates atuais (**RED** com as contagens de hoje), depois os fixes até **GREEN**.
- **P2/P3 retornam ao diff**: só se aprovadas; escopo do diff esperado: `app/web/templates/{login,setup,inventarios/*}.html` (+ `base.html` apenas se P2 = incluir skip-link; + `style.css` apenas se P3 aprovado, ~3 linhas).
