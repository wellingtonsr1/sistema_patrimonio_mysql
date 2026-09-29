# Feature Specification: PWA instalável de qualquer tela (057)

**Feature Branch**: `057-pwa-instalavel-em-todas-as-telas`

**Created**: 2026-09-29

**Status**: Implemented (2026-09-29 — validacao.md PASS; login com manifest + SW ativado provado em navegador)

**Input**: No celular, com a CA já importada (sem aviso de certificado), o Chrome responde "não é possível instalar o app". Diagnóstico com evidência de DOM (2026-09-29): a página de **login** é template separado (`login.html`, não estende `base.html`) e **não possui `<link rel="manifest">`** — ao abrir ⋮ → "Instalar app" partindo do login, o Chrome não encontra o manifest e recusa a instalação. Agravante: o Service Worker (033) só registra em telas com `active_tab == 'inventarios'`, e a página precisa estar sob controle do SW para o prompt de instalação funcionar de forma confiável.

---

## 1. Requisitos

### Functional Requirements

- **FR-001**: `app/web/templates/login.html` MUST declarar o manifest: `<link rel="manifest" href="/static/manifest.webmanifest">` (mesma referência do `base.html`).
- **FR-002**: O registro do Service Worker MUST ocorrer em todas as páginas que estendem `base.html` (remoção da condição `{% if active_tab == 'inventarios' %}` do bloco final de `base.html`) — o SW é network-only fora da allowlist (FR-036 da 033): nenhuma resposta sensível é cacheada; nada muda em comportamento de cache.
- **FR-003**: Nenhuma mudança de lógica de negócio, rotas, permissões ou cache (o `sw.js` não é alterado).
- **FR-004**: A mudança não pode afetar o modo offline existente: allowlist precache, cache-first da rota offline e `/api/*` network-only permanecem intocados (guardas dos testes 053 continuam passando).

### Não-requisitos

- Não alterar `sw.js` (a estratégia de cache permanece a mesma).
- Não criar novo mecanismo de instalação (banner customizado, etc.).

## 2. Critérios de sucesso

| # | Critério |
|---|---|
| SC-001 | A página de login contém `<link rel="manifest" href="/static/manifest.webmanifest">` (teste estrutural) |
| SC-002 | `base.html` registra o SW incondicionalmente (sem a condição de `active_tab`) |
| SC-003 | Suíte completa 893 passed / 0 failed (nenhuma regressão) |
| SC-004 | No navegador: login e dashboard ambos com manifest linkado + SW ativado; instalável de qualquer tela (critério do Chrome atendido) |

## 3. Assumptions

- Com manifest na página + SW ativado (escopo `/`), o Chrome passa a oferecer "Instalar app" em qualquer tela autenticada — inclusive partindo do login, onde o usuário naturalmente tenta.
- O fallback offline-start do SW (navegações gerais em falta de rede) passa a cobrir todas as páginas — melhoria coerente com o PWA, sem tocar nada.
