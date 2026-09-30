# Guia de Implantação em Produção — SisPatrimônio Pro

**Público**: instalador/administrador do servidor de produção.
**Fluxo**: desenvolvimento acontece **somente** na pasta de dev (`sistema_patrimonio_mysql`). O `deploy.bat` publica para **dois repositórios GitHub com conteúdos distintos**: o da **dev** recebe o histórico completo; o da **produção** (`SisPatrimonioPro`) recebe um **snapshot filtrado** com apenas o necessário para rodar. A produção **nunca edita código** — só recebe via `git pull`.

```
[DESENVOLVIMENTO]                                [PRODUÇÃO]
D:\IA\sistema_patrimonio_mysql                    ...\SisPatrimonioPro (servidor)
        │                                               │
   edita → deploy.bat                          git pull + reinicia serviço
        │                                               │
        ├── push (histórico completo) ──→ github.com/wellingtonsr1/sistema_patrimonio_mysql
        └── push (snapshot filtrado)  ──→ github.com/wellingtonsr1/SisPatrimonioPro ──→ pull na produção
```

### O que o `deploy.bat` faz (3 etapas)

1. **Commit na dev** (se houver mudanças) — árvore limpa não impede a publicação;
2. **Push do histórico completo** → `sistema_patrimonio_mysql` (specs, testes, tudo);
3. **Snapshot filtrado** → `SisPatrimonioPro`: extrai a árvore do commit atual e publica com força (`--force`) um único commit de produção, referenciando o hash da dev na mensagem. Ou seja, **cada publicação substitui o conteúdo do repositório de produção** (não é acumulativo); para histórico de versões, use tags na dev (Seção 7).

**Conteúdo publicado no snapshot (whitelist)**:

| Entra | Não entra |
|---|---|
| `app/` | `specs/`, `tests/`, `.github/`, `.specify/`, `.freebuff/` |
| `docs/` | `deploy.bat`, scripts de instalação (`install.sh`, `uninstall.sh`) |
| `data/backups/` e `data/logs/` **apenas a estrutura vazia** (`.gitkeep`) | `data/patrimonio.db` (legado SQLite), logs e backups reais |
| `.gitignore`, `README.md`, `requirements.txt`, `run.py`, `seed_demo.py`, `sistema_patrimonio.png`, `SPEC-KIT-SISTEMA-ATUAL.md` | qualquer `.env` (nunca é versionado) |

Regras de ouro:

1. **Fonte da verdade única**: só se edita na dev. Produção só `pull`;
2. **Um servidor rodando por ambiente** — evita processos fantasmas com código desatualizado;
3. **Nada sensível vai pelo git** — o `.env` nunca é versionado; `data/` vai ao snapshot só como estrutura de pastas vazia, e cada ambiente mantém seus dados reais;
4. **Sempre atualize com tag de versão registrada** (Seção 7) — é o que permite voltar atrás (Seção 8).

---

## 1. Pré-requisitos do servidor

| Item | Requisito |
|---|---|
| SO | Windows ou Linux (o sistema roda nos dois; ver nota do backup na Seção 5) |
| Python | 3.10+ (mesma versão da dev, de preferência) |
| Banco | MariaDB/MySQL em execução, com usuário e senha criados |
| Utilitários | `mysqldump` instalado e acessível no `PATH` (backup/restauração). No Windows, se ficar fora do PATH, definir `MYSQLDUMP_PATH` no `.env` |
| Acesso GitHub | chave SSH ou token com acesso leitura a `wellingtonsr1/SisPatrimonioPro` |

---

## 2. Clone do repositório

```bash
# Linux
git clone git@github.com:wellingtonsr1/SisPatrimonioPro.git
cd SisPatrimonioPro

# Windows (PowerShell/CMD)
git clone git@github.com:wellingtonsr1/SisPatrimonioPro.git
cd SisPatrimonioPro
```

Fixe a versão desejada (recomendado — o snapshot é sempre "a última publicação"; para versões específicas, veja Seções 7 e 8 sobre tags e hashes):

```bash
git log -1                 # mostra 'commit dev <hash>' — a origem deste snapshot
```

> **Importante (natureza do snapshot)**: este repositório recebe force-push a cada
> publicação — o `deploy.bat` publica a árvore da dev como uma história nova, sem
> ancestral comum com o snapshot anterior. Consequências: **nunca dê `git push`**
> aqui (commits manuais são descartados pelo próximo deploy) e, em clones de
> inspeção no Windows, atualize com `git fetch origin` + `git reset --hard
> origin/main` (o `git pull` falha com *refusing to merge unrelated histories*).
> No servidor Linux de produção, `git pull` funciona normalmente (Seção 6).
> Detalhes: Seção 6.1.

---

## 3. Ambiente virtual e dependências

```bash
# Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 4. Configuração (`.env`)

Crie o `.env` **na raiz do projeto** — ele NÃO vem do git (propositamente). Modelo mínimo:

```ini
DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/sispatrimonio
SECRET_KEY=<gere uma chave única para este servidor>
TZ=America/Recife
# Opcional — caminho do mysqldump se não estiver no PATH (Windows):
# MYSQLDUMP_PATH=C:\Program Files\MariaDB 11.x\bin\mysqldump.exe
# Opcional — HTTPS nativo (PWA/coleta offline via IP — feature 056, ver §5.1):
# APP_SSL_CERTFILE=data/ssl/server.crt
# APP_SSL_KEYFILE=data/ssl/server.key
```

> `SECRET_KEY`: gere com `python -c "import secrets; print(secrets.token_hex(32))"`.
> Nunca reutilize a `SECRET_KEY` da dev aqui. Nunca committe o `.env`.

Confira se o `.gitignore` cobre `.env`, `data/logs/`, `data/backups/` e pastas de upload — é o que garante que os dados de produção não são sobrescritos por pull. **No snapshot de produção**, `data/` existe só com a estrutura vazia (`data/backups/.gitkeep`, `data/logs/.gitkeep`) — o banco real é o MariaDB configurado no `DATABASE_URL`, não arquivo em `data/`.

---

## 5. Primeira execução / serviço

Teste manual primeiro:

```bash
python run.py
```

Depois configure o serviço para iniciar com o servidor:

- **Linux**: `systemd` (unit com `ExecStart=/caminho/.venv/bin/python run.py`, `WorkingDirectory=` na raiz do projeto, `Restart=always`);
- **Windows**: `NSSM` (Non-Sucking Service Manager) apontando para `...\SisPatrimonioPro\.venv\Scripts\python.exe run.py`, ou Agendador de Tarefas no boot.

⚠️ Garanta **uma única instância** rodando (o incidente histórico de "processo fantasma" veio de dois servidores simultâneos com códigos diferentes).

Backup no Windows: funciona com `mysqldump` no PATH ou `MYSQLDUMP_PATH` configurado (feature 018).

### 5.1 HTTPS nativo (opcional, recomendado — PWA/coleta offline via IP — feature 056)

O Service Worker do PWA (feature 033) só existe em *secure context*: via IP puro
(`http://10.39.x.x:8000`) o app funciona, mas **sem** PWA/câmera/coleta offline.
O `run.py` sobe em HTTPS quando `APP_SSL_CERTFILE` e `APP_SSL_KEYFILE` estiverem
no `.env`. Sem elas, HTTP puro — nada muda (opt-in).

Passos no **servidor de produção** (uma vez):

1. **Gerar a CA local e o certificado** (com o SAN do IP do servidor):

   ```bash
   # Linux (openssl disponível no instalador 027):
   .venv/bin/python scripts/gera_cert_dev.py --ip <IP-DO-SERVIDOR>
   # Windows:
   .venv\Scripts\python.exe scripts\gera_cert_dev.py --ip <IP-DO-SERVIDOR>
   ```

   Gera em `data/ssl/`: `ca.crt` (a instalar nos aparelhos), `server.crt`,
   `server.key` (**segredo do servidor — NUNCA versionar/copiar entre máquinas**;
   `data/ssl/` é gitignore — cada servidor gera o seu par). Alternativa segura:
   copiar apenas o `ca.crt` **existente** da dev e gerar a chave do servidor lá
   (o certificado é por máquina). Ou usar a CA corporativa (AD CS), gerando o
   cert no domínio — nesse caso pule o gerador e aponte as env vars para os
   arquivos emitidos.

2. **Apontar o `.env`** (modelo da Seção 4):

   ```ini
   APP_SSL_CERTFILE=data/ssl/server.crt
   APP_SSL_KEYFILE=data/ssl/server.key
   ```

3. **Reiniciar o serviço** (`systemctl restart sispatrimoniopro` / NSSM):
   o log passa a mostrar `Uvicorn running on https://0.0.0.0:8000`.

4. **Confiar na CA nos aparelhos** (uma vez por celular/tablet): importar
   `ca.crt` como autoridade (Android: Configurações → Segurança → Instalar
   certificado → CA; iPhone: perfil + confiança total). Depois:
   `https://<IP>:8000` com cadeado válido → PWA instala e a câmera funciona.

Notas:

- **Firewall**: liberar a porta 8000 TCP (já exigida antes; nada novo).
- **HTTP→HTTPS**: com as envs ativas a porta 8000 vira TLS-only (HTTP simples é
  recusado). Para manter HTTP e HTTPS simultâneos, use um proxy (roteiro Caddy
  em `HTTPS_LOCAL.md`).
- **Renovação**: a CA local vale ~10 anos e o certificado do servidor 825 dias
  (`--force` regera). Para domínio público, prefira Caddy/Nginx + Let's Encrypt
  (`HTTPS_LOCAL.md` / `docker-compose.yml`).

---

## 6. Atualização da produção (rotina)

Na **dev** (seu PC):

```bat
deploy.bat "mensagem do commit"     :: commita, envia o histórico para a dev
                                    :: e publica o snapshot filtrado no PRO
```

O que a produção recebe a cada publicação: a árvore completa do último commit da dev **limitada à whitelist** (Seção "O que o deploy.bat faz") — um único commit novo no `main` do `SisPatrimonioPro`.

Na **produção**:

```bash
git pull                            # traz a versão nova
source .venv/bin/activate           # ou .venv\Scripts\activate no Windows
pip install -r requirements.txt     # se dependências mudaram
# reinicie o serviço (systemd restart / restart no NSSM)
```

Para fixar uma versão específica em vez do último snapshot (ver Seção 8 sobre hashes):

```bash
git fetch origin
git checkout <hash-da-dev>     # ex.: 39d185f
# reinicie o serviço
```

### 6.1 Regras do repositório `SisPatrimonioPro` (onde se pode usar git)

Cada publicação do `deploy.bat` é um **force-push de uma história independente**
(a árvore da dev, filtrada pela whitelist, vira um snapshot com raiz nova). Dessa
natureza decoram três regras práticas, aprendidas na operação:

| Onde | Como atualizar | O que NUNCA fazer |
|---|---|---|
| **Servidor Linux (produção de verdade)** | `git pull` + `pip install -r requirements.txt` + restart do serviço (Seção 6) — o `git pull` funciona aí porque o checkout local segue exatamente o `origin/main` | `git push` (não há para onde: a saída é o `deploy.bat` da dev) |
| **Clone de inspeção no Windows** (ex.: `D:\IA\SisPatrimonioPro`) | `git fetch origin` + `git reset --hard origin/main` — espelha o snapshot atual; arquivos locais não versionados não são tocados | `git pull` (falha com `refusing to merge unrelated histories` — as histórias NÃO têm ancestral comum) e `git push` (commits manuais são descartados pelo próximo force-push do deploy) |
| **Dev** (`sistema_patrimonio_mysql`) | commits normais + `deploy.bat "mensagem"` | commitar direto no PRO |

**Por quê**: um commit manual no PRO (ex.: limpeza de doc) ou um `git pull` num clone Windows parecem funcionar, mas no próximo deploy são sobrescritos (force-push) ou travam (histórias sem ancestral). Alteração de código/docs nasce SEMPRE na dev e chega ao PRO exclusivamente via `deploy.bat`.

**Nota operacional (multi-máquina)**: se mais de uma máquina publica snapshots (ex.: postos distintos), todas precisam do MESMO `deploy.bat` (whitelist e filtros idênticos). Um deploy a partir de um script defasado re-publica a árvore sem diretórios novos da whitelist (ex.: `migrations/`, `scripts/`) e pode quebrar o boot da produção. Em caso de dúvida, publique sempre da máquina de referência.

---

## 7. Tags de versão (registradas na dev)

**Atenção**: o snapshot publicado no SisPatrimonioPro é **substituído a cada deploy** (push forçado, 1 commit). Por isso, a rastreabilidade de versões vem das **tags na dev** — que carregam o histórico completo.

Antes de cada atualização relevante da produção, marque a versão na dev:

```bash
git tag v1.0.1
git push origin main --tags         # tags vão para o GitHub da dev (histórico completo)
```

> Tags não são propagadas para o snapshot do SisPatrimonioPro — lá o `main` é sempre "a última publicação". Para identificar a versão instalada, o commit do snapshot cita o hash da dev na mensagem (ex.: `... commit dev 39d185f`).

Vantagem: a produção pode fixar exatamente uma versão via hash da dev (`git checkout 39d185f`) em vez de "o último main".

---

## 8. Rollback (voltar para uma versão anterior)

Na produção:

```bash
git fetch origin
git checkout <hash-da-dev-da-versão-boa>   # ex.: 39d185f — veja a mensagem do commit anterior
# reinicie o serviço
```

> Como o snapshot é forçado, o histórico anterior pode não estar presente no clone — por isso **anote o hash da dev** da versão em produção (o `git log -1` de lá mostra `commit dev <hash>`), ou adicione o GitHub da dev como remote extra (`git remote add dev git@github.com:wellingtonsr1/sistema_patrimonio_mysql.git`) para poder buscar hashes antigos.

Isso NÃO mexe no banco nem nos arquivos de dados — só no código. Se a versão anterior exigia estrutura de banco diferente, restaure o backup mais recente compatível (Administração → Backups → Restaurar) **antes** de reabrir o sistema.

Para reverter a dev ao mesmo ponto:

```bash
git revert <hash-do-commit-problematico>   # histórico preservado
git push origin main
deploy.bat "Reversão de <hash>"           # republica o snapshot corrigido no PRO
```

---

## 9. Implantação via Docker (alternativa às Seções 2–5)

O repositório inclui `Dockerfile` + `docker-compose.yml` (app + MariaDB juntos). Nesse modo, **não** há venv nem serviço do host — o Docker cuida de tudo.

### 9.1 Pré-requisitos

| Item | Requisito |
|---|---|
| Docker | Engine 24+ com `docker compose` (v2) disponível |
| Porta | 8000 livre no host (ou ajuste o mapeamento no compose) |
| Código | o snapshot de produção já traz `Dockerfile` e `docker-compose.yml` |

> Backup/restauração **funcionam dentro do container**: a imagem já instala `default-mysql-client` (mysqldump) — sem necessidade de `MYSQLDUMP_PATH`.

### 9.2 Configuração (`.env` do compose)

Crie o `.env` **ao lado do `docker-compose.yml`** (não versionado) com apenas:

```ini
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
DB_PASSWORD=<senha do banco>
TZ=America/Recife
```

O `DATABASE_URL` **não** vai no `.env`: o compose monta automaticamente `mariadb+pymysql://sispatrimonio:$DB_PASSWORD@db:3306/sispatrimonio_pro` (host do banco é o serviço `db`). Agendamento do backup automático (opcional): `BACKUP_AUTO_ENABLED=true`, `BACKUP_AUTO_SCHEDULE`, `BACKUP_AUTO_TIME` também no `.env`.

### 9.3 Primeira subida

```bash
docker compose up -d --build
docker compose logs -f app      # "iniciado com sucesso" => http://localhost:8000
```

O healthcheck do MariaDB segura o app até o banco aceitar conexões (sem erro de boot). Persistência: **`db-data`** (dados do banco) e **`app-data`** (`/app/data` — backups e logs) sobrevivem a `down`/recriação.

### 9.4 Migração do banco atual (servidor MariaDB existente → Docker)

O banco do compose nasce **vazio**. Para trazer os dados do servidor atual:

```bash
# no servidor ATUAL: exporte um backup
mysqldump --single-transaction --routines --triggers \
  -u usuario -p sispatrimonio_pro > migra.sql

# no servidor DOCKER: suba o app, restaure pela interface
# (Administração → Backups → Restaurar, enviando o .sql.gz/.sql)
#   OU direto no container:
docker compose exec -T db mariadb -u sispatrimonio -p$DB_PASSWORD sispatrimonio_pro < migra.sql
```

Depois confira: contagem de bens/colaboradores, login e um **backup manual** pela tela (que já fica no volume `app-data`).

### 9.5 Atualização de versão (Docker)

```bash
git pull                        # novo snapshot do SisPatrimonioPro
docker compose up -d --build    # recria a imagem do app e reinicia
```

O banco **não** é tocado (volume `db-data` permanece). Rollback: `git checkout <hash-da-dev>` + `up -d --build` (o mesmo mecanismo da Seção 8).

### 9.6 Backup e restauração no modo Docker

- **Pela interface** (recomendado): Administração → Backups — o `mysqldump` interno da imagem grava em `/app/data/backups` (volume `app-data`);
- **Arquivos na máquina host**: o volume `app-data` fica em `/var/lib/docker/volumes/<projeto>_app-data/_data` — copie esse diretório na sua rotina de backup do servidor;
- **Dump manual direto**:

```bash
docker compose exec db sh -c 'exec mariadb-dump --single-transaction -u root -p"$MARIADB_ROOT_PASSWORD" sispatrimonio_pro' > backup-manual.sql
```

- **Restauração**: use a tela (que roda o import em processo separado, feature 019) ou `docker compose exec -T db mariadb ... < arquivo.sql` (9.4).

### 9.7 Checklist Docker

- [ ] `.env` do compose criado (SECRET_KEY, DB_PASSWORD, TZ)
- [ ] `docker compose up -d --build` sem erro; `logs -f app` mostra inicialização limpa
- [ ] Login funciona em `http://<host>:8000`
- [ ] Banco migrado (9.4) e dados conferidos
- [ ] Backup manual gerado e visível na tela (volume `app-data`)
- [ ] Rotina de cópia do volume `app-data` + dump do `db` agendada no servidor

---

## 10. Checklist de primeira implantação (modo serviço, Seções 2–5)

- [ ] `git clone` concluído (`SisPatrimonioPro` — snapshot de produção)
- [ ] Conteúdo conferido: `app/`, `docs/`, arquivos da raiz e `data/` só com `.gitkeep`
- [ ] venv criado e `pip install -r requirements.txt` sem erros
- [ ] `.env` criado localmente (DATABASE_URL, SECRET_KEY própria, TZ)
- [ ] `mysqldump` acessível (ou `MYSQLDUMP_PATH` definido)
- [ ] `python run.py` sobe sem erro e o login funciona
- [ ] Serviço configurado e **único** (só 1 processo do sistema)
- [ ] Primeiro **backup manual** gerado e verificado na tela Administração → Backups
- [ ] Hash da dev em produção anotado (`git log -1` → `commit dev <hash>`)
