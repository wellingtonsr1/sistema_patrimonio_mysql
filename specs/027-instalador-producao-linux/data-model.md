# Data Model: Instalador Automatizado de Produção Linux — Feature 027

**Data**: 2026-09-19 | **Natureza**: feature de deploy — entidades conceituais do instalador; **nenhuma entidade da aplicação é criada ou alterada** (Constitution VII).

---

## 1. Entidades conceituais do instalador

### 1.1 `InstallConfig` — configuração coletada/decidida (em memória, não persistida além do `.env`)

| Campo | Origem | Default | Validação |
|---|---|---|---|
| `install_dir` | interativo/`--install-dir` | `/opt/SisPatrimonioPro` | caminho absoluto; não-vazio sem `.git` → abortar (R7c) |
| `repo_url` | interativo/`--repo` | `https://github.com/wellingtonsr1/sistema_patrimonio_mysql.git` | URL https |
| `branch` | interativo/`--branch` | `main` | existe no clone → clone falha com mensagem específica (FR-008) |
| `db_name` | interativo/`--db-name` | `sispatrimonio` | `[a-zA-Z_][a-zA-Z0-9_]*` (evita aspas no SQL — R5) |
| `db_user` | interativo/`--db-user` | `sispat` | idem |
| `db_password` | interativo (sem eco)/`--db-password`/gerada | gerada (`secrets.token_urlsafe(24)`) | ≥ 12 quando manual; nunca logada (SR-001) |
| `db_host`/`db_port` | interativo | `localhost`/`3306` | remoto permitido (Assumption da spec) |
| `app_host` | interativo/`--app-host` | `0.0.0.0` | IP/hostname válido |
| `app_port` | interativo/`--app-port` | `8000` | 1–65535; livre antes do start (risco porta ocupada) |
| `service_name` | interativo/`--service-name` | `sispatrimoniopro` | `[a-z-]+` (unit + systemctl consistentes — FR-012) |
| `service_user`/`service_group` | interativo/`--service-user` | `sispatrimonio` | criado se ausente (system user, sem login) |
| `admin_via_env` | interativo | `false` | `true` → `AUTH_ADMIN_PASSWORD` gerada no `.env`, exibida 1× (FR-020) |
| `recreate_db` | `--recreate-db` (só interativo) | `false` | `true` com `--non-interactive` → falha imediata (D2/FR-015) |
| `non_interactive` | `--non-interactive` | `false` | obrigatórios ausentes → falha listando o que falta (FR-015) |

**Invariantes**: `db_password` nunca serializada em log/argv (SR-001); validação total ANTES da primeira mutação no modo não interativo (R12).

### 1.2 `HostState` — estado detectado do servidor (somente leitura)

| Fato | Método de detecção | Uso na decisão |
|---|---|---|
| privilégios | `[ "$EUID" -eq 0 ] \|\| sudo -v` | gate inicial (FR-002) |
| distro | `/etc/os-release` (`ID`/`ID_LIKE` contém `debian`) + `systemd` presente (`pidof systemd`/`/run/systemd/system`) | NFR-001 — abortar com orientação se não-Debian |
| python | `python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")'` | ≥ 3.10? senão apt + re-verificar (R3) |
| git | `command -v git` | instalar se ausente (FR-004) |
| sgbd | `systemctl is-active mariadb.service \|\| mysql.service`; `command -v mysqldump mysql` | MariaDB **ou** MySQL (D3/R4); serviço real vai para a unit |
| conectividade | HEAD no repo (git ls-remote) + repositórios apt | gate inicial (FR-002) |
| porta | `ss -ltn` (ou `bash /dev/tcp` probe) em `$app_port` | livre antes do start (risco da spec) |

### 1.3 `RepoState` — estado do diretório de instalação (R7)

| Estado | Detecção | Ação |
|---|---|---|
| inexistente | `! -d $install_dir` | clone `--branch $branch --single-branch` |
| clone válido | `.git` presente + `git rev-parse --is-inside-work-tree` = true | reutilizar; reportar `git rev-parse --short HEAD` |
| não-vazio sem `.git` | `-d` e conteúdo e sem `.git` | **abortar** — decisão do operador (não sobrescreve) |
| clone com alterações locais | `git status --porcelain` ≠ vazio | WARN; nunca `reset --hard` sem confirmação |

### 1.4 `VenvState` (R8)

| Estado | Detecção | Ação |
|---|---|---|
| válido | `.venv/bin/python` + `-m pip --version` + imports OK | reutilizar |
| inválido | qualquer checagem falha | remover e recriar (artefato regenerável) + `pip install -r requirements.txt` |
| novo | sem `.venv` | criar + instalar |

### 1.5 `DbState` (R4/R5/R13)

| Estado | Ação |
|---|---|
| banco não existe | `CREATE DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci` |
| banco existe (sem `--recreate-db`) | **intocável** — validar conexão; completar grants se faltando |
| banco existe + `--recreate-db` | aviso → 2× nome digitado → `DROP`/`CREATE` **do banco nomeado** + recriar user/grants |
| usuário não existe | `CREATE USER ... IDENTIFIED BY` (via `MYSQL_PWD`, nunca argv) |
| usuário existe | reutilizar; senha só alterada com confirmação explícita |
| grants | `GRANT ALL PRIVILEGES ON <db>.* TO ...` — **somente** no banco da aplicação (SR-003) |
| conexão | `SELECT 1` + `SELECT DATABASE()` via engine do projeto no venv (FR-007) |

**Nota**: criação de tabelas NUNCA é do instalador — `init_db()` no start do serviço (FR-011/Realidade 5).

### 1.6 `ServiceState` (R9/R10)

| Item | Valor |
|---|---|
| unit | `/etc/systemd/system/$service_name.service` — gerada do padrão real do README; reescrita só se conteúdo difere (idempotência) |
| dependência de banco | `After=... <serviço-detectado>` (`mariadb.service` ou `mysql.service`) |
| ExecStart | `$install_dir/.venv/bin/python $install_dir/run.py` |
| EnvironmentFile | `$install_dir/.env` (0600, dono `service_user`) |
| usuário | system user `--no-create-home --shell /usr/sbin/nologin`; `chown -R` do diretório |
| ciclo | `daemon-reload` → `enable --now` → espera `/health` (90 s; `degraded`=WARNING) |

---

## 2. Arquivos produzidos pela instalação (visão final do filesystem)

```text
/opt/SisPatrimonioPro/            # dono: sispatrimonio:sispatrimonio
├── app/ … run.py … requirements.txt   # clone (main)
├── .venv/                        # venv do sistema (python3 -m venv)
├── .env                          # 0600 — DATABASE_URL, APP_HOST, APP_PORT, (MYSQLDUMP_PATH)
└── data/                         # logs/backups da aplicação (dono service_user)
/etc/systemd/system/sispatrimoniopro.service
/var/log/sispatrimonio-install.log   # 0600 root — log do instalador
```

Nenhum arquivo novo dentro de `app/`; nenhum artefato da aplicação alterado.

---

## 3. Fluxo de estados da instalação (máquina de estados simplificada)

```text
PRÉ-CHECK (gates duros: sudo/distro/systemd/conectividade)
  → COLETA (interativo c/ confirmação final | não-interativo: validação total antes de mutar)
  → PACOTES (python3/venv/pip/git/sgbd — cada etapa detecta→reutiliza)
  → BANCO (create|reuse|recreate D2; grants mínimos; teste de conexão)
  → REPO (clone|reuse; requirements do repo clonado)
  → VENV (create|reuse|rebuild; pip; validação de imports)
  → ENV (.env 0600; existente → backup+merge consentido)
  → SERVIÇO (user/group; unit; daemon-reload; enable --now)
  → HEALTH (espera 90 s; degraded=WARNING; timeout → journalctl no log + falha)
  → BATERIA + RESUMO (FR-014/FR-020; sem segredos)
```

Falha em qualquer etapa → trap ERR: etapa+linha no log, orientação de reexecução, serviço não habilitado com instalação inválida (FR-019/SR-005).
