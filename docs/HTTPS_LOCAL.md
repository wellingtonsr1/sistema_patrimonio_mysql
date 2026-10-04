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
| Uso real na **rede interna** (Linux) | Caddy com `tls internal` (roteiro adiante) — **DESATIVADO neste servidor** (ver aviso antes do roteiro) | ~15 min, uma vez |
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

> ⚠️ **`--force` regera CA + cert JUNTOS**: o script apaga `ca.key`/`ca.crt` e
> cria uma CA NOVA. Todos os aparelhos que confiavam na CA antiga voltam a ver
> "sua conexão não é privada" — é preciso reimportar a nova `ca.crt` em cada um.
> (Não existe hoje como reemitir SÓ o cert do servidor mantendo a CA — uma
> opção `--reuse-ca` seria o caminho, mas ainda não foi implementada.)

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

#### No PC Linux: ensine o SO e/ou o navegador a confiar na CA

Mesmo com o cert válido (SAN casa com o IP), o navegador mostra "conexão não
segura"/https riscado enquanto a CA local não for confiada no PC. Dois
caminhos — comece pela **Opção A** (foi a que resolveu o "sua conexão não é
privada" no Chrome flatpak do Pop!_OS, validado em campo em 2026-09-29);
guarde a B para o caso do navegador continuar reclamando.

**Opção A — trust store do sistema (recomendada, validada em campo):**

```bash
sudo cp data/ssl/ca.crt /usr/local/share/ca-certificates/sispatrimonio-local-ca.crt
sudo update-ca-certificates
```

- O arquivo PRECISA terminar em `.crt` — o `update-ca-certificates` só
  enxerga `*.crt` em `/usr/local/share/ca-certificates/`.
- Vale para todo app que lê a store do sistema; no Pop!_OS/Ubuntu o Google
  Chrome **flatpak** também a enxerga via p11-kit (runtime Freedesktop).
- Depois, feche o navegador POR COMPLETO e reabra (erro de certificado fica
  em cache — a reabertura completa é obrigatória).
- Reverter: `sudo rm /usr/local/share/ca-certificates/sispatrimonio-local-ca.crt`
  seguido de `sudo update-ca-certificates`.

**Opção B — banco NSS por navegador**: Chrome/Chromium nativo usa o banco
NSS do usuário (`~/.pki/nssdb`) e o Firefox tem `cert9.db` por perfil —
campos que a store do sistema não cobre em todas as builds. Com o
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
> A **Opção A acima costuma cobrir o flatpak de uma vez** (p11-kit expõe a
> store do sistema ao runtime Freedesktop — provado no Pop!_OS, 2026-09-29);
> o caminho NSS abaixo é o plano B.
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

## Dev Linux (Pop!_OS/Ubuntu nativo): gere e rode SEM sudo

O `run.py` sobe HTTPS lendo `data/ssl/server.crt|server.key` com o usuário que
executa a app. Se o `scripts/gera_cert_dev.py` rodar com `sudo`, os arquivos
nascem donos `root` (a chave nasce `0600`) e a app quebra no boot:

```
PermissionError: [Errno 13] Permission denied   (uvicorn → ctx.load_cert_chain)
```

**Regra (máquina de dev)**: `scripts/gera_cert_dev.py` e `run.py` rodam SEMPRE
com o seu usuário. `sudo` apenas no passo de CONFIANÇA da CA — a cópia para
`/usr/local/share/ca-certificates/` não altera os arquivos gerados:

```bash
# geração e execução (sem sudo):
.venv/bin/python scripts/gera_cert_dev.py                # detecta o IP da LAN
.venv/bin/python scripts/gera_cert_dev.py --ip 192.168.0.9 --force
.venv/bin/python run.py                                  # HTTPS em 0.0.0.0:8000

# único passo com sudo (confiança da CA — não toca em data/ssl/):
sudo cp data/ssl/ca.crt /usr/local/share/ca-certificates/sispatrimonio-local-ca.crt
sudo update-ca-certificates
```

### Reparo dos arquivos root-owned (uma vez por regeneração indevida com sudo)

Sintoma: `ls -l data/ssl/` mostra `root root` e o boot falha com o
`PermissionError` acima. Corrija a posse e as permissões:

```bash
sudo chown "$USER:" data/ssl/ca.* data/ssl/server.*
chmod 600 data/ssl/ca.key data/ssl/server.key
chmod 644 data/ssl/ca.crt data/ssl/server.crt
```

Dono/permissão ficam gravados no arquivo: o reparo vale até a próxima
regeneração. Regenerando SEM sudo (regra acima), nunca mais precisa.

> **Produção Linux (install.sh) não sofre disso**: o instalador gera os certs
> sob o usuário do serviço (`sispatrimonio`) e a unit systemd roda com ele —
> nada a fazer lá.

---

> **⚠️ ESTE SERVIDOR (Pop!_OS, 192.168.0.9) — rota Caddy 8443 DESATIVADA em 2026-09-29.**
> O roteiro abaixo permanece documentado como alternativa para OUTRAS máquinas
> (Linux onde a 056 nativa não for usada). Neste servidor ele foi **desligado de
> propósito**: com a 056 nativa ativa na 8000, o Caddy criava uma SEGUNDA entrada
> HTTPS na 8443 com outra CA ("Caddy Local Authority", não confiada pelos
> navegadores) — abrir `https://<ip>:8443` produzia o falso "sua conexão não é
> privada" e confundia o diagnóstico do cadeado. O bloco `https://192.168.0.9:8443`
> foi removido do `/etc/caddy/Caddyfile` e o Caddy recarregado — porta 8443
> **liberada, confirmado em 2026-09-29** (backup do Caddyfile: `/etc/caddy/Caddyfile.factory.bak`).
> NESTE servidor, use somente **`https://192.168.0.9:8000`
> (uvicorn nativo, feature 056)**. Para reativar o Caddy aqui, recrie o bloco
> e `sudo systemctl reload caddy` — mas escolha UMA das rotas, nunca as duas.

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

---

## Múltiplos servidores (Windows + Linux): CAs separadas — importação dupla

**Decisão** (2026-09-29): cada servidor mantém a PRÓPRIA CA local (a do
Windows não assina o Linux e vice-versa). Vantagens: nenhuma chave privada
circular entre máquinas; regenerar/derrubar um servidor não afeta a confiança
do outro; operação local simples. **Custo**: cada aparelho que usa os DOIS
servidores precisa importar as DUAS CAs (uma vez cada).

### Identifique a CA de cada servidor (o CN é igual nas duas!)

Ambas as CAs se chamam `CN = SisPatrimonio Pro - CA local (dev)` — o que
distingue é a impressão digital. No servidor, obtenha com:

```bash
openssl x509 -in data/ssl/ca.crt -noout -fingerprint -sha256
```

Ao distribuir os arquivos, renomeie para não confundir:
`ca-servidor-windows.crt` / `ca-servidor-linux-<ip>.crt`
(ex.: `ca-servidor-linux-192-168-0-9.crt`).

### Passo a passo por aparelho

**Celular Android (para cada servidor que usar):**
1. Copie o `ca.crt` DAQUELE servidor para o aparelho (e-mail/USB)
2. Configurações → Segurança → Mais configurações → Criptografia e credenciais →
   **Instalar um certificado → Autoridade CA** → escolha o arquivo
3. No Chrome: ⋮ → Informações do site → **Limpar e redefinir** (apaga o estado
   antigo do site com erro de cert), feche e reabra o Chrome
4. `https://<ip-daquele-servidor>:8000` → cadeado válido → login → ⋮ → Instalar app

**iPhone/iPad:** abrir o arquivo → instalar perfil → ativar confiança total
(Ajustes → Geral → Sobre → Configurações de confiança). Repita por servidor.

**PC Windows:** `certutil -user -addstore Root <ca-daquele-servidor>.crt`
(remover: `certutil -user -delstore Root "SisPatrimonio Pro - CA local (dev)"`).

**PC Linux (nativo E flatpak — ver seção acima para detalhes):** use um
APELIDO distinto por servidor no NSS (o apelido é a chave do registro — usar
o mesmo nome substituiria/colidiria):

```bash
# Chrome nativo + Firefox (perfis com cert9.db, navegador FECHADO):
NOME_LINUX="SisPatrimonio CA (Linux 192.168.0.9)"
NOME_WIN="SisPatrimonio CA (Windows <ip>)"
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n "$NOME_LINUX" -i ca-servidor-linux-<ip>.crt
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n "$NOME_WIN"   -i ca-servidor-windows.crt
# Chrome FLATPAK: repetir com -d sql:$HOME/.var/app/com.google.Chrome/.pki/nssdb
```

### Regras de convivência

- **Trocou o IP de um servidor?** Regenere com o novo IP
  (`python scripts/gera_cert_dev.py --ip <novo-ip> --force`) — ATENÇÃO: o
  `--force` regera TAMBÉM a CA (aviso no passo 1 da seção Windows nativo),
  então os aparelhos precisarão reimportar a nova `ca.crt` daquele servidor
  (reemissão mantendo a CA — tipo `--reuse-ca` — ainda não existe no script).
- **Regenerou a CA de um servidor?** Os aparelhos precisam reimportar a
  NOVA CA daquele servidor (a do outro continua valendo).
- **Backup**: guarde `ca.key` de cada servidor em local seguro — perdeu,
  regenera tudo e reimporta nos aparelhos.
- Se um dia a operação crescer para 3+ servidores ou exigir rotação, a
  unificação (uma CA única assinando todos) passa a valer a pena — exigiria
  uma opção `--reuse-ca` no `gera_cert_dev.py`, que hoje NÃO existe (todo
  `--force` cria CA nova).
