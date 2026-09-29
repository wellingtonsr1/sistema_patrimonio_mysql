# Implementation Plan: PWA instalável de qualquer tela (057)

**Branch**: `057-pwa-instalavel-em-todas-as-telas` · **Spec**: [spec.md](spec.md) · **Created**: 2026-09-29

## Summary

Duas linhas de template: `<link rel="manifest">` no `login.html` (achado de DOM — a página de login não o declara) e registro incondicional do SW no `base.html`. Zero mudança de lógica/cache.

## Constitution Check

| Princípio | Status | Nota |
|---|---|---|
| I. Evolução incremental | PASS | 2 linhas de template |
| II. Camadas | PASS | Só apresentação |
| III. Regras de negócio | PASS | Intocadas |
| IV/V. Integridade | PASS | Intocada |
| VI. Segurança RBAC | PASS | Intocada (SW não cacheia nada novo) |
| VII. Banco protegido | PASS | Zero DDL |
| VIII. Testes | PASS | Suíte no patamar + guardas 053 verdes |
| IX. Auditoria | PASS | Intocada |
| XI. Documentação fiel | PASS | COLETA_OFFLINE.md nota atualizada |
| XII. Especificações | PASS | validacao.md |

**GATE: PASS 10/10**

## Design

### D1 — `login.html` (head)

```html
<link rel="manifest" href="/static/manifest.webmanifest">
```

após o `<link rel="icon">` (mesma posição relativa do `base.html`).

### D2 — `base.html` (bloco final)

Remover a condição `{% if active_tab == 'inventarios' %}` mantendo o bloco `<script>` de registro do SW inalterado. Efeito: todas as páginas autenticadas registram o SW → página sob controle do SW → critério de instalação do Chrome atendido em qualquer tela.

Segurança (FR-036 da 033 permanece): o SW é **network-only** para tudo fora da allowlist de precache + rota offline — nenhum conteúdo novo é cacheado; navegações fora da allowlist ganham apenas o fallback offline-start quando não há rede (comportamento já existente, agora em mais páginas).

### D3 — Teste estrutural (`tests/test_pwa_instalavel_057.py`)

1. `login.html` contém `rel="manifest"` apontando para `/static/manifest.webmanifest` (SC-001).
2. `base.html` NÃO contém mais a condição `{% if active_tab == 'inventarios' %}` no bloco do SW, e contém o registro `serviceWorker.register('/sw.js')` fora de qualquer condicional (SC-002) — assert por proximidade: entre `{% block scripts %}` e `{% endif %}` não há `if` de active_tab.
3. Guardas 053 continuam verdes (suíte).

TDD: escritos antes, vistos falhar (login sem manifest hoje; base condicional hoje).

## Riscos

| Risco | Mitigação |
|---|---|
| Registro do SW em páginas admin causar prompt de notificação/persmission | O SW não pede nenhuma permissão nova (sem notifications/push); registro é silencioso |
| Fallback offline-start em páginas administrativas confundir usuário offline | Comportamento já existente na 033 para navegações gerais; texto do fallback orienta reconectar |
| Chrome antigo no celular não oferecer instalação | Fora de escopo: navegadores alvo são os atuais (mesma premissa da 033) |
