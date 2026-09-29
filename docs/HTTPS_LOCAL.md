# HTTPS local para o PWA da coleta offline (dev/máquina própria)

> O PWA (Service Worker, instalação na tela inicial, leitura de QR via câmera/`BarcodeDetector`)
> só funciona em **contexto seguro**: HTTPS válido **ou** `localhost`.
> Referências: `app/web/static/js/sw.js` (feature 033) · `docs/COLETA_OFFLINE.md`.

## Resumo das opções

| Cenário | Solução | Custo |
|---|---|---|
| Testar agora no **desktop** | `http://localhost:8000` (localhost já é contexto seguro) | Zero |
| **Rede interna via IP — Windows nativo (este servidor)** | **TLS no próprio uvicorn** + CA local gerada pelo projeto (seção abaixo — feature 056) | ~5 min, uma vez |
| Testar no **celular via cabo** (Android) | Port forwarding do Chrome (`chrome://inspect`) → `http://localhost:8000` no celular | Zero |
| Teste temporário em **qualquer aparelho** | Túnel: `cloudflared tunnel --url http://localhost:8000` | Zero (URL pública temporária) |
| Uso real na **rede interna** (Linux) | Caddy com `tls internal` (roteiro adiante) | ~15 min, uma vez |
| **Produção** com domínio público | Caddy/Nginx + Let's Encrypt (automático) | Ver `docker-compose.yml` |

---

## Windows nativo: TLS no próprio uvicorn (feature 056 — recomendado neste servidor)

Sem proxy novo: o `run.py` sobe HTTPS quando as variáveis `APP_SSL_CERTFILE` e
`APP_SSL_KEYFILE` estiverem definidas no ambiente/.env (feature 056).

### 1. Gere a CA local e o certificado (com o SAN do IP)

```bat
.venv\Scripts\python.exe scripts\gera_cert_dev.py
```

Detecta o IP da LAN automaticamente (ex.: `10.39.0.16`) e gera em `data\ssl\`:
`ca.crt` (a importar nos aparelhos), `server.crt` e `server.key` (**não versionar**).
SAN inclui o IP, `localhost`, o hostname e `sispatrimoniopro.local`. Use
`--ip` para forçar outro IP e `--force` para regerar.

### 2. Configure o .env e reinicie

Use **barras `/`** — o app normaliza caminhos relativos contra a raiz do
projeto, então o MESMO .env funciona no Windows e no Linux (um .env copiado
do Windows com `data\ssl\server.crt` fazia o uvicorn falhar com
`FileNotFoundError` cru no Linux — não use `\`).

```bat
APP_SSL_CERTFILE=data/ssl/server.crt
APP_SSL_KEYFILE=data/ssl/server.key
```

O log passará a mostrar `https://0.0.0.0:8000`. Sem essas variáveis, o app
sobe HTTP idêntico ao atual (nada muda). Se os arquivos apontados não
existirem, o `run.py` falha rápido com mensagem explícita (gere-os com
`python scripts/gera_cert_dev.py` ou remova as variáveis para HTTP puro).

### 3. Confie na CA nos aparelhos (uma vez por aparelho)

- Copie `data\ssl\ca.crt` (e‑mail/USB) e importe:
  **Android**: Configurações → Segurança → Instalar certificado → CA ·
  **iPhone**: perfil → confiança total.
- No Windows da própria máquina, a CA pode ser confiada por usuário:
  `certutil -user -addstore Root data\ssl\ca.crt`
  (remover: `certutil -user -delstore Root "SisPatrimonio Pro - CA local (dev)"`).

#### No PC Linux: Chrome e Firefox NÃO usam a confiança do sistema

Mesmo com o cert válido (SAN casa com o IP), o navegador mostra "conexão não
segura"/https riscado enquanto a CA local não for confiada **no navegador**:
Chrome/Chromium usa o banco NSS do usuário (`~/.pki/nssdb`) e o Firefox tem
`cert9.db` por perfil — nenhum lê a trust store do SO por padrão. Com o
`libnss3-tools` instalado (`sudo apt install libnss3-tools`):

```bash
NOME="SisPatrimonio Pro - CA local (dev)"
# Chrome/Chromium:
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n "$NOME" -i data/ssl/ca.crt
# Todos os perfis do Firefox (com o FECHADO — o banco fica travado em uso):
for perfil in $HOME/.mozilla/firefox/*/; do
  [ -f "$perfil/cert9.db" ] && certutil -d "sql:$perfil" -A -t "C,," -n "$NOME" -i data/ssl/ca.crt
done
```

Confere com `certutil -d sql:$HOME/.pki/nssdb -L` (deve listar a CA com flags
`C,,`). Depois reinicie o navegador e acesse `https://<IP>:8000` — cadeado
válido, sem exceção manual. Se o navegador for snap/flatpak, o banco muda de
lugar (ex.: `~/snap/chromium/common/.pki/nssdb`).

> **Google Chrome FLATPAK** (ID `com.google.Chrome`): o banco NSS é
> `~/.var/app/com.google.Chrome/.pki/nssdb` — o caminho nativo `~/.pki/nssdb`
> é IGNORADO pelo sandbox. Sintoma de CA faltando aqui: "sua conexão não é
> privada" no PC e, mesmo passando pelo aviso, "não é possível instalar o
> app" (o Chrome recusa instalar PWA em página com erro de certificado).
> Correção:
>
> ```bash
> NSSDIR=$HOME/.var/app/com.google.Chrome/.pki/nssdb
> mkdir -p "$NSSDIR"
> certutil -d "sql:$NSSDIR" -N --empty-password   # só se o banco não existir
> certutil -d "sql:$NSSDIR" -A -t "C,," -n "SisPatrimonio Pro - CA local (dev)" -i data/ssl/ca.crt
> ```
>
> Fechar o Chrome POR COMPLETO e reabrir (o banco só é lido no start).

### 4. Acesse e valide

`https://<IP>:8000` — cadeado válido (SAN casa com o IP), Service Worker
registra, PWA instala e a câmera funciona no "Ler QR". Prova desta feature:
`Invoke-WebRequest https://10.39.0.16:8443/health` (validação sem `-k`) → 200.

> **Nota**: com TLS no uvicorn não há proxy — as URLs do QR saem `https://`
> nativamente (`request.base_url`), sem ajuste de `proxy_headers`.
> Para não expor HTTP na rede, rode só o HTTPS (ou bloqueie a 8000 no firewall).

---

---

## Roteiro principal: Caddy + certificado interno na sua máquina Linux

### 0. Descubra o IP da sua máquina na rede

```bash
ip a | grep "inet " | grep -v 127.0.0.1
# ex.: 192.168.1.20 — é o que o celular vai usar
```

### 1. Instale o Caddy (Ubuntu/Debian)

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

### 2. Configure o Caddyfile (certificado interno automático)

```bash
sudo tee /etc/caddy/Caddyfile > /dev/null <<'EOF'
https://192.168.1.20:8443 {
    tls internal
    reverse_proxy 127.0.0.1:8000
}
EOF
sudo systemctl reload caddy
```

> Substitua `192.168.1.20` pelo IP do passo 0. O `tls internal` faz o Caddy
> **criar uma CA local e emitir o certificado sozinho** — nada de autoassinado na mão.

Se houver firewall: `sudo ufw allow 8443/tcp`.

### 3. Faça o celular confiar na CA do Caddy (uma vez por aparelho)

```bash
# exporta o certificado raiz da CA local do Caddy
sudo cp /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt /tmp/caddy-root.crt
sudo chmod 644 /tmp/caddy-root.crt
# mande para o celular (e-mail, USB, etc.)
```

**Android**: Configurações → Segurança → Mais configurações → Criptografia e credenciais →
**Instalar um certificado → Autoridade de certificação (CA)** → escolha `caddy-root.crt`.

**iPhone/iPad**: abra o arquivo → instalar perfil → depois ative confiança total em
Ajustes → Geral → Sobre → **Configurações de confiança de certificado**.

### 4. Suba o app e acesse

```bash
.venv/bin/python run.py
```

No celular (mesma rede Wi‑Fi): **`https://192.168.1.20:8443`** — o cadeado fica válido,
o Service Worker registra e o PWA instala ("Adicionar à tela inicial"), com a câmera
funcionando para o "Ler QR".

---

## Notas técnicas

- **Headers de proxy (QR do pacote)**: a `qr_url` do pacote offline é montada com
  `request.base_url` (`app/api/inventario_offline_api.py`). Como o Caddy roda na mesma
  máquina (127.0.0.1), o uvicorn **já confia nos headers por padrão**
  (`proxy_headers=True`, `forwarded_allow_ips=127.0.0.1`) e as URLs saem `https://...`
  corretamente — **nenhuma mudança de código** neste cenário. Se o proxy rodar em
  **outro host/container**, configure explicitamente `proxy_headers=True` e
  `forwarded_allow_ips` com o IP do proxy na chamada do `uvicorn.run` (`run.py`).
- **Porta do app**: o app continua na 8000; o HTTPS fica na 8443. Para não expor o HTTP
  na rede, faça o app escutar em `127.0.0.1` (`APP_HOST=127.0.0.1 .venv/bin/python run.py`).
- **Produção**: use domínio público + Caddy/Nginx com Let's Encrypt (renovação automática),
  ou certificado da **CA do domínio** (AD CS/Samba) em redes corporativas com os aparelhos
  gerenciados. Autoassinado caseiro não é recomendado (confiança manual por aparelho e
  recursos bloqueados).
