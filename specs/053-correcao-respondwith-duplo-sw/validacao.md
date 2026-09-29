# Registro de Validação — Feature 053 (Constituição XII)

**Data**: 2026-09-29 · **Feature**: Correção do respondWith duplo no Service Worker + bump CACHE_VERSION v32
**Método**: TDD estrutural (testes lendo o arquivo do disco, escritos e vistos falhar antes do fix) + suíte completa de regressão (Python do venv) + grep de versões legadas + `git diff --stat`.

## Alteração aplicada (diff confinado — FR-004)

| Arquivo | Mudança |
|---|---|
| `app/web/static/js/sw.js` | +5/−1: `return;` exclusivo no ramo `OFFLINE_NAV_RE` (FR-001) + comentário; `CACHE_VERSION` → `inventario-offline-v32` com changelog (FR-002) |
| `tests/test_sw_service_worker.py` | **Novo** — 5 testes estruturais (sem banco, rodam em qualquer ambiente) |
| `docs/COLETA_OFFLINE.md` | Nota da correção na seção "Dicas práticas" |
| `specs/053-correcao-respondwith-duplo-sw/` | 4 artefatos spec-kit (spec/plan/tasks/quickstart + esta validação) |

**Zero alteração** em: rotas, templates, services, models, `inventario_offline.js`, `qr_reader.js`, IndexedDB (`DB_VERSION=1`), permissões, auditoria, banco.

## V1 — Bug provado e corrigido (SC-001/FR-001) ✅

- **Antes (v31)**: dentro de `if (event.request.mode === "navigate")`, o sub-bloco `OFFLINE_NAV_RE` chamava `respondWith` e a execução **continuava** para o segundo `respondWith` (demais navegações) — segunda chamada no mesmo evento = `InvalidStateError` por spec Fetch, com resultado dependente de navegador/estado de cache. Compatível com o bug reincidente "página `null`" desde a 033 (análise de 2026-09-29, §2).
- **TDD**: `test_respondwith_unico_na_navegacao_offline` escrito antes e visto falhar (vermelho: `assert 2 == 1` nas chamadas dentro do sub-bloco). Após o `return;` (verde): sub-bloco com exatamente 1 chamada, terminando em `return;`, e os 2 `respondWith(` do bloco de navegação em ramos mutuamente exclusivos.

## V2 — Bump v32 e limpeza de dispositivos (SC-002/FR-002) ✅

`var CACHE_VERSION = "inventario-offline-v32"` com changelog encadeado (padrão v31→v30). Na primeira visita pós-deploy a uma página de inventário: `install` precacheia a allowlist no cache v32 → `activate` apaga `inventario-offline-v31` (mecanismo FR-037 da 033) → `skipWaiting`/`clients.claim` assumem as abas. Coletas offline (IndexedDB) não são tocadas.

## V3 — Escopo byte-a-byte (SC-004/FR-003) ✅

- `test_allowlist_precache_intacta`: as 14 entradas de `PRECACHE_URLS` presentes e contadas dentro do array (a URL `offline-start.html` também aparece no fallback de navegação — fora do array).
- `test_api_network_only_preservada`: guard `if (path.startsWith("/api/")) return;` intacto (FR-036 da 033 — nenhuma resposta de API cacheada).
- `git diff --stat`: **apenas** `app/web/static/js/sw.js` (+5/−1); demais mudanças são arquivo de teste novo, docs e specs.

## V4 — Varredura de versão legada (SC-002) ✅

`test_nenhuma_referencia_a_v31_no_codigo`: **0 ocorrências** de `inventario-offline-v31` em `app/` (runtime). Menções em `docs/`/`specs/` são changelog/documentação histórica e não executam — o teste é confinado ao código por design (decisão D2).

## V5 — Regressão (SC-003) ✅

Suíte completa com o Python do **venv** (o oficial do projeto): **882 passed / 2 failed em 115,6s**.

| Régua | Contagem |
|---|---|
| Baseline 050 (registrado na validação da 050) | 861 passed |
| + testes da 051 (rotas em facade, commit `dc05526`) | +16 |
| + testes estruturais da 053 (novo arquivo) | +5 |
| **Total final desta validação** | **882 passed** |

Os 2 failures são exatamente os pré-existentes de `test_backup_externo.py` (feature 045, baseline externo documentado — FR-021 da 050 proíbe tocar backup). **Nenhum teste que passava passou a falhar.**

## V6 — Prova de campo executada (2026-09-29, pós-deploy) ✅ + decisões

### Prova de campo (R2 da análise) — SERVIDOR DE PÉ (`10.39.0.16:8000` = `localhost:8000`)

**Setup**: usuário temporário `fieldtest_tmp` (admin, id=4) criado via `create_user` para a prova e **desativado** ao final (login rastreável na auditoria; nenhum dado de negócio tocado).

| # | Cenário | Resultado |
|---|---|---|
| F1 | **Janela normal**, origin `10.39.0.16:8000` → login → `/inventarios/1/conferir/1` | **PASS** — página completa (título, card do bem IPMJP1456, resultado anterior, formulário com 4 opções + select de locais); `document.body.innerText` sem a palavra "null" |
| F2 | Mesma página com console/monitoramento | **PASS** — console **vazio** (zero erros de JS); todas as requisições 200 |
| F3 | **Origin `localhost:8000`** (secure context, onde o SW da 033 registra): visita a `/inventarios/1` → SW registrado e **ativado** (`inventario-offline-v32`, 14 entradas precacheadas) → navegação a `/inventarios/1/conferir/1` **com o SW interceptando** | **PASS** — página íntegra (1.929 chars, `contemNull=false`), navegação concluída sem `InvalidStateError` — o caminho exato do respondWith duplo exercitado com a correção em produção |
| F4 | **Aba anônima** (contexto isolado, sem SW/cache prévios): login → acesso direto a `/inventarios/1/conferir/1` | **PASS** — página idêntica (1.929 chars, zero "null", console vazio) |

**Screenshots**: ambas as janelas (normal com SW v32 ativo e anônima) renderizam a ficha de conferência completa — header "Conferência de Inventário", badge INV-2026-0001, card do bem com status, resultado anterior ("Conferido por admin em 24/09/2026 11:40") e o formulário de resultado com as 4 opções.

### Achado técnico da prova (importante — explica a "invisibilidade" do bug no IP)

Em `http://10.39.0.16:8000` (IP puro, sem HTTPS), `navigator.serviceWorker` é **undefined** — origin de IP não é *secure context*, então o SW **não registra aí** (o `if ('serviceWorker' in navigator)` do base.html pula silenciosamente). Consequências:

1. No acesso por IP, o bug "null" NUNCA foi causado por SW — a causa compatível com os sintomas no IP é cache HTTP corrompido do navegador (o v31 era servido e guardado também em acessos por localhost/PWA instalado) ou proxy local.
2. O PWA/coleta offline (033) **só funciona de fato via `localhost` ou HTTPS** — na instalação atual (acesso por IP sem TLS), os dispositivos não têm SW; isso alinha com o M6/R3 da análise (HTTPS local é pré-requisito para o PWA na rede).
3. A correção da 053 vale integralmente para os acessos por localhost/HTTPS (prova F3); para acessos por IP, o fim do bug depende da limpeza do cache HTTP (novo deploy força revalidação dos estáticos com `?v=`; páginas HTML não são cacheadas pelo SW).

**Conclusão da prova**: 4/4 PASS — a página de conferência renderiza integralmente nas 4 condições; nenhuma ocorrência de "null". Correção 053 validada em campo no cenário onde o SW atua (F3).

### Decisões registradas

- **D1**: contagem de chamadas usa a âncora `respondWith(` (com parêntese) para não confundir com a palavra em comentários.
- **D2**: grep de v31 confinado a `app/` — docs/specs citam a versão antiga como changelog legítimo.
- **D3 (observação para o M1 da análise)**: com o Python do sistema (fora do venv), a suíte ganha um 3º failure ambiental (`test_backup_config.py::test_anti_regressao_*` — `dotenv` vive no user site-packages e o subprocesso do teste não o encontra) e o tempo varia; executar sempre via `.venv/Scripts/python.exe`. *(Observação: resolvido na 054 — runner `test.bat` fixa o venv.)*
- **D4 (desta prova)**: usuário temporário criado/desativado — não removido para preservar a trilha de auditoria da prova (login/logout rastreáveis); reativável se necessário.

## Resultado

**V1–V5: PASS** · **V6: PASS (prova de campo 4/4)** — 5/5 SCs satisfeitos e pendência operacional encerrada.
