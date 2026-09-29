# Quickstart: 053-correcao-respondwith-duplo-sw

Como validar a correção em 2 minutos.

## 1. Teste estrutural do SW

```bash
python -m pytest tests/test_sw_service_worker.py -v
# 5 passed — respondWith único, v32, allowlist intacta, /api/* network-only, sem v31
```

## 2. Prova do bug corrigido (código)

Antes (v31): dentro de `if (event.request.mode === "navigate")`, o sub-bloco `OFFLINE_NAV_RE` chamava `respondWith` e **continuava** para o segundo `respondWith` — segunda chamada no mesmo evento = `InvalidStateError` (spec Fetch).

Depois: o sub-bloco termina com `return;` — os caminhos são mutuamente exclusivos.

## 3. Efeito nos dispositivos

No primeiro acesso pós-deploy a uma página de inventário, o navegador busca o novo `/sw.js`, `install` precacheia a allowlist no cache `inventario-offline-v32`, `activate` apaga `inventario-offline-v31` e `clients.claim` assume as abas. Caches corrompidos somem; coletas offline (IndexedDB) não são tocadas.

## 4. Prova de campo (pendência operacional)

Com o servidor de pé: abrir `/inventarios/{id}/conferir/{asset_id}` (a) em janela normal e (b) em aba anônima. Ambas devem renderizar a página completa (nada de body `null`). Registrar no validacao.md.
