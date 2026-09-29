# Quickstart: 057-pwa-instalavel-em-todas-as-telas

## No celular (após o deploy)

1. Abra `https://<IP>:8000` (com a CA já importada — cadeado válido).
2. A partir da **tela de login** ou de **qualquer página**: menu ⋮ → **"Instalar app"** / "Adicionar à tela inicial".
3. O ícone "SisPatrimônio" entra na tela inicial; ao abrir, roda standalone (sem barra do navegador), com "Ler QR" funcional.

## Validação técnica (desktop)

```js
// Em https://<IP>:8000/login — console do navegador:
document.querySelector('link[rel="manifest"]')?.href
// → "https://<IP>:8000/static/manifest.webmanifest"
(await navigator.serviceWorker.getRegistrations())[0].active.state
// → "activated"
```

Com manifest + SW ativados na página, o Chrome habilita "Instalar app".
