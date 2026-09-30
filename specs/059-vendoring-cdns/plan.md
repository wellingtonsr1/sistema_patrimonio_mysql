# Plan — Feature 059 (vendoring M6)

## Decisões

**D1 — Origem dos arquivos**: baixados de jsdelivr com versão EXATA fixada no download (chart.js@4.4.1 UMD `chart.umd.js`; qrcodejs@1.0.0 `qrcode.min.js`), commitados ao repo. Bootstrap 5.3.3 + Icons 1.11.3 já vendored (reuso integral, incluindo `fonts/`).

**D2 — Fonte Plus Jakarta Sans**: baixados os 5 pesos (400/500/600/700/800) em woff2 do gstatic via CSS da Google, servidos de `static/vendor/fonts/` com `@font-face` em CSS local (`vendor/fonts/plus-jakarta-sans.css`). Fallback do stack (`system-ui, sans-serif`) cobre ausência do arquivo (FR-003) — degrade estético, nunca funcional.

**D3 — login.html e setup.html**: são templates independentes (não estendem base) e duplicam os links CDN — também migrados para vendor (FR-001), mantendo inline-block deles mesmos.

**D4 — SW (FR-005)**: os 2 JS novos + CSS/fontes da fonte entram no allowlist do precache; `CACHE_VERSION` → `inventario-offline-v33` (bump propaga a allowlist nova aos dispositivos — mesmo mecanismo da 053).

**D5 — Guard anti-CDN (FR-004)**: teste varre TODOS os templates por `cdn.jsdelivr|fonts.googleapis|fonts.gstatic|googleapis` e falha se encontrar; exceção nenhuma — o objetivo é zero dependência externa.

## Alternativas rejeitadas

- *SRI (integrity hash) mantendo CDN*: mitiga adulteração mas mantém dependência de rede — não resolve o problema.
- *Self-host da fonte via CDN baixado na instalação*: complexidade de install.sh sem ganho; arquivos são pequenos (~90 KB total).
- *Bundlers (Vite/esbuild)*: fora do padrão da casa (templates server-side + JS solto); sobre-engenharia para o porte.

## Riscos

| Risco | Mitigação |
|---|---|
| Arquivo vendor com nome/pasta errada → 404 em tela | Smoke visual nas telas-chave + teste de servimento (SC-004) + rede requests no preview |
| Chart.js UMD difere do bundle esperado pelo dashboard | Download do build UMD oficial 4.4.1 (mesma API usada: `new Chart(ctx, config)`); smoke do dashboard renderizando 3 gráficos |
| SW v33 sem bump esquecido → dispositivos com allowlist antiga | Bump incluído no mesmo commit + guard do teste 053 (14 entradas) atualizado |
| Licença dos assets | Todos os vendored são MIT/OFL (Bootstrap MIT, Chart.js MIT, qrcodejs MIT, Jakarta Sans OFL) — uso institucional permitido; fontes OFL carregam licença no repo das fontes |
