# Feature Specification: Vendoring dos CDNs (M6)

**Feature Branch**: `059-vendoring-cdns`
**Created**: 2026-09-30
**Status**: Implemented

## Problema

O `base.html`, `login.html` e `setup.html` carregam Bootstrap, Bootstrap Icons, Chart.js, QRCode.js e a fonte Plus Jakarta Sans de CDNs externos (jsdelivr/googleapis/gstatic). Consequências verificadas:

1. **Contradição com o PWA offline (033)**: a coleta offline funciona sem rede, mas a primeira carga das telas depende de internet (o `static/vendor/` já existe com Bootstrap e é precacheado pelo SW — mas os templates apontam para o CDN).
2. **Rede institucional restritiva**: firewall bloqueando jsdelivr/googleapis degrada TODAS as telas (sem CSS).
3. **Risco latente**: `cdn.jsdelivr.net/npm/chart.js` **sem versão fixada** — uma publicação major nova no CDN quebra o dashboard sem nenhuma mudança local.

## Requisitos funcionais

- **FR-001**: `base.html`, `login.html` e `setup.html` MUST carregar todos os assets (Bootstrap CSS/JS, Bootstrap Icons + fontes, Chart.js, QRCode.js, fonte Plus Jakarta Sans) de `/static/vendor/...` local — zero referência a `cdn.jsdelivr`, `fonts.googleapis` ou `fonts.gstatic`.
- **FR-002**: Chart.js e QRCode.js MUST ser vendored com **versão fixada** (chart.js UMD 4.4.x; qrcodejs 1.0.0), em `static/vendor/js/`.
- **FR-003**: A fonte Plus Jakarta Sans MUST ser vendored (woff2 com `font-display: swap`) via `@font-face` em CSS local; se o arquivo faltar, o fallback do stack de fontes aplica sem quebrar.
- **FR-004**: Teste guarda: qualquer retorno de referência CDN nos templates da aplicação FAILA a suíte (impece regressão).
- **FR-005**: O precache do SW (allowlist 033) MUST incluir os assets vendor novos (chart/qrcode/fonts), mantendo a coleta offline funcional e o CACHE_VERSION bumpado (v33) para propagar.
- **FR-006**: Nenhuma regra de negócio, rota, service ou banco é alterada (feature de infraestrutura de front-end).

## Critérios de aceitação

- **SC-001**: `grep` de CDN nos 3 templates = 0 ocorrências (guard de teste verde).
- **SC-002**: login, dashboard (gráficos Chart.js renderizando) e etiquetas (QRCode gerando) funcionam com rede externa BLOQUEADA (smoke visual).
- **SC-003**: suíte completa 100% verde (sem regressão).
- **SC-004**: os arquivos vendor são servidos pelo app (200) e presentes no precache do SW v33.
