# Registro de Validação — Feature 059 (Vendoring dos CDNs — M6)

**Data**: 2026-09-30 · **Feature**: todos os assets de front-end servidos de `/static/vendor/` — zero dependência de CDN externo
**Método**: TDD (7 testes; RED 6 failed + 1 passed Bootstrap-vendor-existente comprovado antes) + smoke visual em navegador real sobre o app em produção local + régua completa.

## Alteração aplicada

| Arquivo | Mudança |
|---|---|
| `app/web/templates/base.html`, `login.html`, `setup.html` | TODAS as referências CDN (jsdelivr ×4, googleapis/gstatic ×3 por template) → `/static/vendor/...` local |
| `static/vendor/js/chart.umd.js` (novo) | Chart.js **4.4.1** UMD (205 KB) — antes era `npm/chart.js` SEM versão (risco de major nova quebrar o dashboard) |
| `static/vendor/js/qrcode.min.js` (novo) | qrcodejs 1.0.0 (19 KB) |
| `static/vendor/fonts/` (novo) | Plus Jakarta Sans **variável** (wght 200–800, 27 KB, subset latin; licença OFL) + `plus-jakarta-sans.css` com `@font-face` e `font-display: swap` |
| `sw.js` | Allowlist do precache: +4 entradas (chart, qrcode, css e woff2 da fonte) = 18; `CACHE_VERSION` → **v33** (propaga aos dispositivos) |
| `tests/test_vendoring_059.py` (novo) | 7 testes: guard anti-CDN em TODOS os templates (FR-004), vendors versionados presentes, fonte local íntegra (valida cada `url()` do CSS), allowlist e bump do SW |
| `tests/test_sw_service_worker.py` | Guardas da 053 atualizados: CACHE_VERSION aceita v32 **ou** v33; allowlist 14 → 18 entradas |

## Validação (V1–V6)

| # | Critério | Prova | Resultado |
|---|---|---|---|
| V1 | **SC-001** — zero CDN nos templates | guard varre todos os `*.html` (regex `cdn\.jsdelivr\|googleapis\|gstatic`): 0 ocorrências; `grep` manual confirma | ✅ |
| V2 | **SC-004** — vendors servidos pelo app | navegador real: 6 requisições vendor (css/js/woff2), **0 requisições externas** no login | ✅ |
| V3 | **SC-002 (login)** — fonte carregando | `document.fonts.check('400 16px "Plus Jakarta Sans"')` = **true**; body computado com a família | ✅ |
| V4 | **SC-002 (dashboard)** — Chart.js local | `Chart` definido, **4 canvases** renderizados, `chart.umd.js` servido de `/static/vendor/js/`, 0 externos; screenshot do dashboard (tema escuro) íntegro | ✅ |
| V5 | **SC-002 (etiquetas)** — QRCode local | `QRCode` definido, servido de `/static/vendor/js/`; QR gerado com sucesso em teste no DOM; 0 externos | ✅ |
| V6 | **SC-003** — régua sem regressão | **919 passed / 1 skipped (condicional MariaDB, por design) / 0 failed** (63,9s) — 912 + 7 novos; guardas da 053 atualizados para v33/18 legitimamente | ✅ |

## Notas

- **SC-002 offline real (rede WAN bloqueada)**: a prova mais forte é a estrutura — TODAS as requisições das telas-chave são locais (V2–V5 com 0 externas); o precache do SW v33 cobre inclusive a primeira visita offline às telas de inventário. Smoke com WAN fisicamente bloqueada fica como teste de campo opcional nos coletores.
- Usuário temporário do smoke (`smoke059_7306`) **desativado** ao final (rastro de auditoria).
- Fonte variável única (27 KB) substitui 5 arquivos — pesos 400/500/600/700/800 cobertos pelo eixo `wght 200-800`.
- Risco de licença registrado no plan (MIT/OFL — uso institucional permitido).
