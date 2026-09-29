# Registro de Validação — Feature 057 (Constituição XII)

**Data**: 2026-09-29 · **Feature**: PWA instalável de qualquer tela
**Método**: diagnóstico de DOM (caminho do Chrome) + TDD estrutural (2 testes red→green) + prova em navegador real + régua de suíte completa.

## Alteração aplicada

| Arquivo | Mudança |
|---|---|
| `app/web/templates/login.html` | +4: `<link rel="manifest" href="/static/manifest.webmanifest">` (achado: login não declarava o manifest) |
| `app/web/templates/base.html` | Registro do SW incondicional (removida a condição `active_tab == 'inventarios'` da 033; FR-036/network-only preservado) |
| `tests/test_pwa_instalavel_057.py` | **Novo** — 2 guardas estruturais |
| `tests/test_https_config_056.py` | Correção de isolamento do teste (ver V3) |
| `docs/COLETA_OFFLINE.md` | Nota de instalação a partir de qualquer tela |

## V1 — Causa raiz provada (T002) ✅

DOM da página de login real (navegador sobre HTTPS): `<link rel="manifest">` **AUSENTE** e SW registrado apenas por visitas a inventários. Partindo do login, o Chrome não encontra os pré-requisitos de instalabilidade → "não é possível instalar o app". Com a CA importada pelo usuário (sem aviso de cert), esta era a causa restante.

## V2 — TDD (SC-001/SC-002) ✅

RED 2/2 (login sem manifest; base com condição). GREEN após as 2 correções: 2/2 + guardas da 053 verdes (7/7 no conjunto com test_sw — allowlist, network-only de `/api/*` e respondWith único intactos, FR-004).

## V3 — Régua e correção colateral ✅

- Suíte completa: **895 passed / 0 failed** (64,5s) = 893 + 2 da 057.
- Correção no teste da 056 (`test_defaults_sem_env_sao_none`): o reload do config lia o `.env` REAL (que agora tem `APP_SSL_*` — ativação permanente legítima). Isolamento duplo no teste: `delenv` + `load_dotenv` no-op durante o reload. Nenhum código de produção tocado.

## V4 — Prova em navegador real (SC-004) ✅

Sobre `https://localhost:8000/login` (servidor em execução): `manifestLink` presente (`/static/manifest.webmanifest`), `isSecureContext: true`, `swController: true`, SW `activated` (escopo `/`). Com manifest + SW na página, o Chrome habilita "Instalar app" — no celular, o mesmo vale a partir do login **ou de qualquer tela**.

## V5 — Observações

- **Nota para o aparelho**: se o Chrome ainda não mostrar "Instalar app" de imediato, limpar os dados do site (Configurações → Privacidade → Limpar dados) e reabrir — estado antigo pré-057 pode persistir; o prompt também pode exigir uma interação adicional (navegar 1 página) em alguns builds.
- O servidor em execução já serve os templates corrigidos (Jinja2 recarrega templates — confirmado via curl antes da prova).

## Resultado

**V1–V5: PASS** — SC-001..004 satisfeitos.
