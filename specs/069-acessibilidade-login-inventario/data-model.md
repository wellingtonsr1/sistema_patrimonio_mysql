# Data Model — 069-acessibilidade-login-inventario

> **Nenhuma entidade nova.** Esta feature não cria tabela, coluna, índice, enum, migração ou backfill. O "modelo" da feature é o **contrato de atributos de acessibilidade** nos templates dos dois fluxos + a **estrutura do teste estático** — nada de dados muda.

## 1. Entidades envolvidas (todas intocadas)

| Entidade (tabela) | Uso nesta feature | Alteração estrutural |
|---|---|---|
| `users` / `roles` / `permissions` | autenticação e autorização existentes (login e permissões dos fluxos de inventário) | **Nenhuma** |
| `assets` / `locations` / `custodians` | contexto apresentado nos formulários de conferência (somente leitura) | **Nenhuma** |
| `inventarios` / `inventario_itens` | fluxos paginados/conferidos já cobertos pela 068 — sem alteração aqui | **Nenhuma** |
| `audit_logs` | nenhuma escrita nova decorre de atributos de acessibilidade | **Nenhuma** |

**Zero DDL, zero migração** (o diff esperado da implementação é: `app/web/templates/**` (login, setup, inventarios/*), `app/static/css/style.css` **apenas se** o foco visível precisar de ajuste — ver R6, e `tests/test_acessibilidade_estatica_069.py` (novo). `docs/ARQUITETURA_E_MANUTENCAO.md` e artigo da central de ajuda, no passo de docs (T016-equivalente a 068/T028).

## 2. "Modelo" real — contrato de atributos de acessibilidade no DOM

Estado final previsto (o que o parser da suíte valida, fluxo a fluxo):

### 2.1 Login (`login.html`) e primeiro acesso (`setup.html`)

| Elemento | Estado hoje | Estado final | Validado por |
|---|---|---|---|
| `input#username`, `input#password` (e demais de setup) | `label[for]` correto | **intocado** (R7) | teste guarda "não regredir" |
| `button#togglePassword` (login+setup), `#toggleConfirmPassword` (setup) | ícone sem nome | `aria-label` que alterna "Mostrar senha"/"Ocultar senha" + `aria-pressed` controlado pelo JS do toggle | botão só-ícone tem nome acessível |
| alerta de erro | `role="alert"` presencial (server-side) | **preservado**; a leitura do anúncio pelo leitor de tela é validada no quickstart (manual) | `role=alert` presente nos alertas `alert-danger` de login/setup |

### 2.2 Inventário — listagem e criação

| Elemento | Hoje | Final |
|---|---|---|
| `inventarios/list.html` busca + status (2 controles) | sem nome acessível | `aria-label` no input ("Buscar inventários por código ou nome") e no select ("Status do inventário") |
| `inventarios/new.html` 4 campos | `<label>` sem `for` | `for`/`id` nos 4 (texto visível já existe — correção trivial) |
| `inventarios/list.html:44` — link "limpar filtros" | `title` apenas | `aria-label="Limpar filtros"` no `<a>` (o `title` fica por conta do tooltip nativo visual) |

### 2.3 Inventário — conferência (web e offline)

| Elemento | Hoje | Final |
|---|---|---|
| `conferir.html` + `detail.html` (modal) + `offline.html` — grupo de rádios "Resultado da conferência" | `<label>` implícito por rádio | `<fieldset>` + `<legend>` = "Resultado da conferência"; rádios intocados (associação implícita já correta) |
| "Local onde foi encontrado" / "Observação" (3 templates) | label solto, sem associação | `for=` + `id=` (e `id` único mesmo com modal por item em `detail.html` — sufixo `{{ item.id }}`) |
| `detail.html:189` campo tombamento (U4) | placeholder apenas (+ `autofocus` ✅ já presente) | `aria-label="Tombamento ou QR do bem"`; `autofocus` mantido |
| `detail.html:214-224` filtro da lista de itens (search/status/botão ícone) | sem nome / botão ícone sem nome | `aria-label` no input e select; `aria-label="Aplicar filtros"` no botão `bi-funnel` |
| mensagens de erro/estado (`conferir.html:17-19`, `detail.html` alertas, `offline.html` status de coleta) | renderizadas server-side no HTML | preservadas; `role="alert"` onde falta (único caso dos fluxos-alvo: o alerta de erro de `conferir.html`) e `role="status"` nos contadores dinâmicos da `offline.html` (rev. 2) |

### 2.4 Dicionário de técnicas (o parser lê isto)

| Técnica | Quando usar | Quando NÃO usar |
|---|---|---|
| `label[for]` + `id` | campo com `<label>` visível já existente (`new.html`, "Local/Observação") | nunca duplicar label |
| `aria-label` | controle ícone-único ou compacto sem espaço visual (busca, filtros, toggle de senha, botões ícone) | nunca substituir label visível existente |
| `fieldset`/`legend` | grupo de rádios com contexto único | em campos soltos |
| `aria-pressed` | botão toggle (mostrar/ocultar senha) | botão que não alterna |
| `role="alert"` | mensagem de erro server-side | em mensagens que requerem leitura sequencial sem urgência |
| `role="status"` | contador/status atualizado por JS na página offline (`inventarios/offline.html` — único fluxo com atualização dinâmica real; rev. 2 do `research.md`) | em mensagens estáticas |

## 3. Invariantes (o que nunca pode quebrar)

- **I1 — Nada visual muda**: nenhuma alteração de layout, cor, espaçamento; atributos ARIA e associação de label são invisíveis (o único risco visual é o radio `fieldset` — prevenido por `fieldset` sem borda padrão: reset inline `border:0;padding:0;margin:0` no próprio template, sem tocar `style.css`).
- **I2 — Nenhuma rota/method/cabecalho novo** → `tests/route_manifest.json` intocado.
- **I3 — Autenticação, permissões, validações e submissão dos formulários idênticas** (mesma `action`, `method`, `name` de campos; o parser também assegura que `name=` dos campos foi preservado — regressão garantida pelos testes funcionais existentes de login/inventário).
- **I4 — Zero DDL/dependência**: nada em `requirements.txt`, `migrations/`, `app/models/`, `app/schemas/`.
- **I5 — Testes existentes intocados**: `tests/test_acessibilidade_estatica_069.py` é o único arquivo de teste novo; nenhum teste editado/removido.
- **I6 — `autofocus` preservado onde existe** (login username, tombamento em detail) e **não** adicionado onde não existe.
- **I7 — IDs únicos por render**: em `detail.html` o modal é por item (loop) — qualquer `id=` novo **deve** incluir `{{ item.id }}` no sufixo para não gerar duplicidade (o parser da suíte valida unicidade de `id` na página toda).

## 4. Regras de corte (o que NÃO entra)

| Não incluído | Motivo |
|---|---|
| `aria-live` em mensagens estáticas server-side | `role="alert"` já anuncia; `aria-live` duplicaria (R3) |
| Playwright/axe-core com browser | precedentes 013/035 rejeitaram; nova dependência pesada sem aprovação (R5) |
| skip-link global em `base.html` | toca 50+ templates — postergado (R8, decisão P2) |
| contraste preventivo de CSS | sem medição; só via varredura axe futura ou correção constatada (R4) |
| hotkeys/`Enter confirma` som de feedback (U4) | o `submit` nativo por Enter já cobre no fluxo web; som/feedback do PWA offline é UX nova fora do escopo |
| indicador de foco global de CSS | a casa **não tem** `outline:none` (verificado); foco default do Bootstrap preservado — única lacuna é `.result-option`, tratada por P3/T024b (dispensa mudança global) |
