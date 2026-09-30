# Quickstart — Feature 059

## O que mudou
- `base.html`, `login.html`, `setup.html`: TODOS os assets de CDN → `/static/vendor/...` (Bootstrap, Icons, Chart.js 4.4.1, QRCode 1.0.0, fonte Plus Jakarta Sans local).
- `static/vendor/js/`: `chart.umd.js` (4.4.1), `qrcode.min.js` (1.0.0) — versões fixadas.
- `static/vendor/fonts/`: Plus Jakarta Sans 400–800 (woff2) + `plus-jakarta-sans.css` (@font-face).
- `sw.js`: allowlist com os novos assets; `CACHE_VERSION` → `inventario-offline-v33` (propaga aos dispositivos).

## Como validar
```powershell
# Guard anti-CDN + servimento dos vendors
.venv\Scripts\python.exe -m pytest tests/test_vendoring_059.py -v
# Régua completa
.venv\Scripts\python.exe -m pytest tests/ -q

# Smoke offline de verdade: desligue a internet/WAN, mantenha o app local:
# login, dashboard (gráficos) e etiquetas (QR) continuam íntegros.
```

## Rollback
`git revert` do commit da feature (arquivos vendor novos são aditivos; templates voltam ao CDN).
