# Implementation Plan: Correção do respondWith duplo no SW (053)

**Branch**: `053-correcao-respondwith-duplo-sw` · **Spec**: [spec.md](spec.md) · **Created**: 2026-09-29

## Summary

Correção cirúrgica do `sw.js` (feature 033): `return` após o `respondWith` da navegação offline elimina a segunda chamada `respondWith` no mesmo evento (InvalidStateError por spec Fetch); `CACHE_VERSION` avança v31→v32 para que a ativação limpe os caches corrompidos dos dispositivos.

## Technical Context

**Arquivo único**: `app/web/static/js/sw.js` (~140 linhas, JS vanilla ES5, sem build step — Princípio da 033).
**Teste**: novo `tests/test_sw_service_worker.py` — teste **estrutural** (lê o arquivo do disco e faz asserts de texto/estrutura; nada de banco nem TestClient). Justificativa: a suíte não executa JS; um teste Python que parseie o arquivo garante regressão sem dependências (mesmo espírito do `test_route_inventory` da 051).

## Constitution Check

| Princípio | Status | Nota |
|---|---|---|
| I. Evolução incremental | PASS | Correção pontual; nada recriado |
| II. Arquitetura em camadas | PASS | Static client-side; sem camadas tocadas |
| III. Regras de negócio nos services | PASS | Zero regra de negócio |
| IV/V. Integridade patrimonial/inventário | PASS | Nenhum dado tocado |
| VI. Segurança RBAC | PASS | Intocada |
| VII. Banco protegido | PASS | Zero DDL; zero banco |
| VIII. Testes como não-regressão | PASS | Teste estrutural novo + suíte no patamar |
| IX. Auditoria | PASS | Intocada |
| XI. Documentação fiel | PASS | COLETA_OFFLINE.md atualizado (T006) |
| XII. Especificações e validação | PASS | validacao.md com evidências |

**GATE: PASS 10/10**

## Design

### D1 — A correção (diff-alvo, 1 linha funcional)

```js
if (OFFLINE_NAV_RE.test(path)) {
  event.respondWith(/* ... */);
  return; // FR-001: respondWith é único por evento — demais navegações têm o próprio ramo
}
event.respondWith(/* fetch + fallback offline-start */);
```

O `return` está dentro do `if (event.request.mode === "navigate")`, portanto **não** afeta os ramos seguintes (estáticos da allowlist, `/api/*` network-only — que já retornam antes).

### D2 — Por que bumpar a versão é seguro

Handler `activate` já remove qualquer cache `inventario-offline-*` ≠ `CACHE_VERSION` (FR-037 da 033); `skipWaiting` + `clients.claim` ativam a nova versão imediatamente. Custos do bump: re-download dos 14 recursos da allowlist uma única vez por dispositivo (pequeno, estáticos locais). Nenhum dado de coleta é afetado (IndexedDB `DB_VERSION=1` independente do cache — FR-038/SC-009 da 033).

### D3 — Teste estrutural (sem banco, roda em qualquer ambiente)

`tests/test_sw_service_worker.py`:
1. `test_respondwith_unico_na_navegacao_offline` — lê `app/web/static/js/sw.js`; extrai o bloco `if (event.request.mode === "navigate") { ... }` por chaves balanceadas; dentro dele, o sub-bloco `if (OFFLINE_NAV_RE.test(path)) { ... }` deve conter exatamente 1 `respondWith` e a função handler não pode conter 2 `respondWith` no mesmo caminho — assert objetivo: entre o primeiro `respondWith` do sub-bloco offline e o fechamento do sub-bloco existe um `return;`.
2. `test_cache_version_v32` — arquivo declara `var CACHE_VERSION = "inventario-offline-v32"`.
3. `test_allowlist_precache_intacta` — as 14 URLs da allowlist presentes (verificação FR-003/SC-004).
4. `test_api_network_only_preservada` — o guard `path.startsWith("/api/")` + `return;` presente antes de qualquer cache.
5. `test_sem_v31_no_repo` — grep: nenhuma ocorrência de `inventario-offline-v31` em `app/` e `docs/` (SC-002).

TDD: 1 e 2 escritos ANTES do fix e vistos falhar (vermelho); 3–5 servem de guarda contra mudança acidental além do escopo.

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Teste textual frágil (mudança de formatação quebra) | Asserts ancorados em tokens estáveis (`respondWith`, `return;`, `OFFLINE_NAV_RE`), não em linhas exatas; o arquivo não tem build step, logo é estável |
| Alguém reintroduz o padrão duplo | Teste 1 falha no CI |
| Bump não limpar dispositivos por SW antigo em memória | skipWaiting/clients.claim já existem; prova de campo fica como pendência operacional no validacao.md |

## Complexity Tracking

Nenhuma violação.
