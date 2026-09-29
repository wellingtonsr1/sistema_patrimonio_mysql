# Quickstart: 056-https-nativo-uvicorn-pwa

HTTPS para o PWA na rede via IP — 3 comandos (Windows nativo, sem proxy).

## 1. Gerar CA + certificado com o SAN do seu IP

```bat
.venv\Scripts\python.exe scripts\gera_cert_dev.py
:: detecta o IP da LAN (ex.: 10.39.0.16) e gera em data\ssl\
:: (--ip 10.39.0.99 para forçar; --force para regerar)
```

## 2. Subir o app com TLS

```bat
set APP_SSL_CERTFILE=data\ssl\server.crt
set APP_SSL_KEYFILE=data\ssl\server.key
.venv\Scripts\python.exe run.py
:: [>>] Interface Web: https://0.0.0.0:8000
```

## 3. Confiar na CA nos aparelhos (uma vez)

- Copie `data\ssl\ca.crt` para o celular (e-mail/USB).
- **Android**: Configurações → Segurança → Instalar certificado → CA.
- **iPhone**: instalar perfil → Ativar confiança total.

Acesse `https://<IP>:8000` — cadeado válido, Service Worker registra, PWA instala, câmera funciona para "Ler QR".

## Notas

- Sem as envs `APP_SSL_*`, o app sobe HTTP idêntico ao atual (nada muda).
- Produção com domínio público: prefira Caddy/Nginx + Let's Encrypt (roteiro na mesma doc).
