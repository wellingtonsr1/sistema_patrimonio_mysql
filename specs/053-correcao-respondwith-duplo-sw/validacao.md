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

## V6 — Pendência operacional e decisões registradas ⏳

- **Prova de campo (R2 da análise)**: confirmar no dispositivo do usuário (servidor `10.39.0.16:8000` de pé) que a página de conferência renderiza integralmente — janela normal **e** aba anônima — após o SW v32 assumir. Pendente porque o servidor estava offline durante a implementação. A correção entregue é estrutural e comprovada por código/teste; a reprodução do bug exige o ambiente do usuário.
- **D1**: contagem de chamadas usa a âncora `respondWith(` (com parêntese) para não confundir com a palavra em comentários.
- **D2**: grep de v31 confinado a `app/` — docs/specs citam a versão antiga como changelog legítimo.
- **D3 (observação para o M1 da análise)**: com o Python do sistema (fora do venv), a suíte ganha um 3º failure ambiental (`test_backup_config.py::test_anti_regressao_*` — `dotenv` vive no user site-packages e o subprocesso do teste não o encontra) e o tempo varia; executar sempre via `.venv/Scripts/python.exe`.

## Resultado

**V1–V5: PASS** · V6 parcialmente pendente (prova de campo operacional) — 5/5 SCs verificáveis em ambiente satisfeitos.
