# Feature Specification: Correção do respondWith duplo no Service Worker (053)

**Feature Branch**: `053-correcao-respondwith-duplo-sw`

**Created**: 2026-09-29

**Status**: Draft

**Input**: Corrigir o bug estrutural do handler `fetch` do Service Worker da feature 033 (`app/web/static/js/sw.js`): na navegação da rota offline (`/inventarios/{id}/offline`) o código chama `event.respondWith(...)` duas vezes no mesmo evento — o primeiro (cache-first da rota offline) e o segundo (navegações gerais) —, comportamento que lança `InvalidStateError` (spec Fetch: respondWith só pode ser chamado uma vez) e cujo resultado varia por navegador/estado de cache. Em conjunto, avançar a `CACHE_VERSION` para v32 para que a ativação do SW atualizado remova os caches `inventario-offline-v31` dos dispositivos, que podem conter entradas corrompidas. Fonte: análise profunda de 2026-09-29 (`docs/ANALISE_PROFUNDA_SISTEMA_2026-09-29.md`, §2.1/§2.3-R1) — hipótese primária do bug reincidente "página `null`" desde a 033.

---

## 1. Contexto (fonte: código real, 2026-09-29)

`app/web/static/js/sw.js`, handler `fetch`:

```js
if (event.request.mode === "navigate") {
    if (OFFLINE_NAV_RE.test(path)) {
      event.respondWith(/* cache-first da rota offline */);   // 1º respondWith
    }                                                          // ← SEM return
    event.respondWith(/* fetch com fallback offline-start */); // 2º respondWith — SEMPRE executa
}
```

Per spec Fetch (§ FetchEvent.respondWith): a segunda chamada no mesmo evento lança `InvalidStateError`; o comportamento observável varia por navegador (resposta do 1º + exceção não capturada no SW, ou rede morta). A reincidência do bug "null" no dispositivo do usuário desde a 033 é compatível com cache/SW em estado corrompido que só é limpo quando `CACHE_VERSION` muda.

## 2. Regra máxima

**MOVER NADA, MUDAR O MÍNIMO**: a correção é `return` após o primeiro `respondWith` + bump de versão com comentário de changelog. Zero mudança de comportamento além disso: allowlist de precache, regra network-only de `/api/*`, cache-first de estáticos, install/activate e as rotas servidas permanecem intocados.

## 3. Requisitos

### Functional Requirements

- **FR-001**: O handler `fetch` NÃO PODE chamar `event.respondWith` mais de uma vez para o mesmo evento: a navegação da rota offline DEVE retornar imediatamente após o seu `respondWith` (o ramo de demais navegações fica mutuamente exclusivo).
- **FR-002**: `CACHE_VERSION` DEVE avançar para `inventario-offline-v32`, com comentário de changelog encadeado (padrão v31→v30→…), garantindo que a ativação do SW atualizado remova os caches `inventario-offline-v31` dos dispositivos (mecanismo já existente do handler `activate` + `skipWaiting`/`clients.claim`).
- **FR-003**: `PRECACHE_URLS`, a regra de rede obrigatória para `/api/*` e o cache-first de estáticos da allowlist DEVEM permanecer byte-a-byte equivalentes (nenhuma mudança de comportamento além de FR-001/FR-002).
- **FR-004**: Nenhuma rota, template, service, modelo, permissão, auditoria ou DDL pode ser alterada — a feature é exclusivamente client-side estático.
- **FR-005**: A correção DEVE ser guardada por teste estrutural (leitura do arquivo, sem banco de dados) que (a) prove a exclusividade do `respondWith` por caminho de navegação e (b) fixe a versão mínima do cache — impedindo regressão futura ao padrão duplo ou ao v31.

### Não-requisitos

- Não alterar a estratégia de cache das navegações gerais (fallback offline-start permanece).
- Não servir `Cache-Control: no-store` nas páginas web (R3 da análise — candidato a feature própria, tocando rotas).
- Não alterar o `inventario_offline.js`, `qr_reader.js`, IndexedDB (`DB_VERSION=1`) nem o conteúdo da rota offline.

## 4. Critérios de sucesso

| # | Critério |
|---|---|
| SC-001 | Teste estrutural prova `respondWith` único por caminho no bloco de navegação (TDD red→green: falha antes, passa depois) |
| SC-002 | `sw.js` declara `inventario-offline-v32`; grep não encontra referência alguma a `v31` no repositório |
| SC-003 | Suíte de testes no patamar atual (nenhuma regressão; únicas falhas permitidas: as 2 pré-existentes de `test_backup_externo.py`) |
| SC-004 | Comportamento offline preservado: allowlist de precache com as mesmas 14 entradas e regra `/api/*` network-only intactas (asserts do teste estrutural) |

## 5. Assumptions

- A confirmação visual do fim do bug "null" no dispositivo do usuário depende de reprodução ao vivo com o servidor de pé (R2 da análise) — esta feature entrega a correção defensiva comprovável por código/teste; a prova de campo fica registrada no validacao.md como pendência operacional.
- Navegadores alvo: os já suportados pela aplicação (Chrome/Edge modernos; SW é opcional e sua falha nunca bloqueia o app — FR-046 da 033).
