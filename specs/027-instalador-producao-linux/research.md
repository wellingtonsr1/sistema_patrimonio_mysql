# Research: Instalador Automatizado de Produção Linux — Feature 027

**Feature**: 027 — `specs/027-instalador-producao-linux/` | **Data**: 2026-09-19
**Base**: spec.md (decisões D1–D4 registradas), código real lido nesta sessão, plan.md. A implementação DEVE reconfirmar âncoras no código da época.

---

## R1 — Linguagem e estilo do instalador: bash estrito, arquivo único

**Decisão**: `install.sh` em **bash** com `set -Eeuo pipefail`, funções puras de etapa (uma função por fase do fluxo da spec), arquivo único na raiz (D1).

**Rationale**: o alvo é servidor Debian/Ubuntu (NFR-001) — bash é universal lá, sem instalar nada para instalar; arquivo único é auditável e versionável (briefing §10). Alternativas rejeitadas: **Python** (exigiria Python ≥ 3.10 ANTES de garantir Python — problema de ovo e galinha em servidor limpo), **Ansible** (dependência de controladora externa, fora da realidade de 1 servidor), **Makefile** (não descreve fluxo com estados e confirmações).

**Detalhes operacionais**:
- `IFS=$'\n\t'`; `umask 027` no início (arquivos criados já nascem restritos);
- `umask 077` nas janelas que geram/escrevem `.env` e coletam senha (0600 garantido por construção — SR-002);
- trap `ERR` que imprime linha/etapa e orienta reexecução (idempotência permite retomar — FR-019);
- comandos externos verificados com `command -v` antes do uso (fail-fast — SR-005).

## R2 — Logs: nível por símbolo, arquivo em /var/log, sufixo no prompt de senha

**Decisão**: funções `info/ok/warn/err` com prefixo visual (`[ * ]`, `[OK]`, `[!!]`, [XX]`); log completo em `/var/log/sispatrimonio-install.log` (0600) via `exec > >(tee ...) 2>&1` **com exceção da coleta de senha**.

**Rationale**: atende briefing §13 (diferenciação INFO/OK/WARNING/ERROR + arquivo) e SR-001 (nunca credenciais). A senha do banco é coletada com `read -rs` (sem eco) **dentro de uma janela `set +x`** (defesa contra `xtrace` acidental) e o prompt usa **sufixo em vez de prefixo** (`"Senha: "` → output vai para o tee antes do eco ser desativado? Não — o problema real: `read -rs` com `tee` no stdout não ecoa a senha, mas o **terminal local** pode; padrão seguro consolidado: prompt gravado no log com `printf` ANTES do `read`, leitura com `-s`, newline manual depois). **Regra verificável**: `grep` do log NUNCA contém a senha (validação do quickstart usa a própria senha gerada).

## R3 — Python ≥ 3.10: via apt, com verificação pós-install (o "no-op" do Debian antigo)

**Decisão**: fluxo — `command -v python3` → versão via `python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")'` (sem sair do bash; evita divergência de formato). Se < 3.10: `apt-get install -y python3` → **re-verificar a versão**; se ainda < 3.10, **abortar** com orientação (distro não suportada — sem repositórios de terceiros, FR-003).

**Rationale**: em Debian antigo o `python3` pode já existir em versão inferior e o `apt install` ser no-op — a re-verificação é a única forma honesta de falhar (risco "Python da distribuição < 3.10" da spec). Ubuntu 20.04/22.04/24.04 e Debian 11/12 provêm 3.8+/3.9+/3.11+ — Pop!_OS atual provê 3.10+. Instalar também `python3-venv python3-pip` (separados da base em Debian/Ubuntu — NFR-002).

## R4 — SGBD: detecção MariaDB **ou** MySQL (D3), instalação só se nenhum existir

**Decisão**: detecção por **comandos reais**, não por pacote (nomes/pacotes variam): servidor = `systemctl is-active` em `mariadb.service` **ou** `mysql.service`, ou socket local; utilitários = `command -v mysqldump mysql`. Se **qualquer** servidor existe → reutilizar e **não instalar nada** (unit usará o serviço real detectado — FR-012). Se nenhum → instalar `mariadb-server` (D3 — padrão da feature; `default-mysql-server` como alternativa equivalente em algumas versões).

**Rationale**: D3 rejeitou a restrição a MariaDB; a detecção por comportamento (serviço + cliente) é a única robusta entre variantes Debian/Ubuntu (o pacote `mariadb-server` às vezes provê binários `mysql*` shim). O instalador nunca desconfigura/reinicia destrutivamente um servidor existente (FR-005).

## R5 — Credenciais do banco: coleta sem eco, geração crypto-secure, SQL sem senha em argv

**Decisão**:
- **Interativo**: `read -rs` duas vezes (confirmação); vazia → gerar automaticamente (`secrets.token_urlsafe(24)` via Python stdlib — SR-002);
- **Não interativo**: `--db-password` ou `--generate-db-password` (FR-015 — sem parâmetro → falha na validação inicial);
- **Execução SQL** (CREATE DATABASE/USER/GRANT): senha enviada via **`MYSQL_PWD` no ambiente do processo** (mesma técnica da aplicação 018 — `_dump_env`), **nunca em argv** (argv fica visível em `/proc/<pid>/cmdline` para outros usuários do host — SR-001);
- **DATABASE_URL**: percent-encoding via `urllib.parse.quote_plus` (mesma orientação do README — senha com `@ # % : /` nunca quebra a URL);
- **Validação de força**: exigir ≥ 12 caracteres quando fornecida manualmente (senha gerada já atende).

**Rationale**: espelha o padrão de segurança que a própria aplicação já usa (018: `MYSQL_PWD`, senha nunca em argv/log); `secrets` é stdlib (zero dependência).

## R6 — .env gerado: variáveis mínimas + segredos, 0600, nunca sobrescrito

**Decisão**: gerar com `umask 077` → 0600 por construção (SR-002). Conteúdo mínimo: `DATABASE_URL` (R5), `APP_HOST=0.0.0.0` (default explicito — o default de código `192.168.0.9` é do operador, spec §Realidade 2), `APP_PORT=8000`, `MYSQLDUMP_PATH` **só quando** `command -v mysqldump` falhar no PATH do serviço (comentado no gerado). `AUTH_ADMIN_PASSWORD` **só** se o admin escolher a via env (FR-020 — gerada e mostrada UMA vez, instrução de removê-la do `.env` após o primeiro login). `.env` existente → **nunca sobrescrito**: backup `.env.bak-<ts>` + opção de completar apenas chaves ausentes (FR-010/FR-018).

**Rationale**: espelha `.env.example` (que já usa `MYSQLDUMP_PATH`/`BACKUP_IMPORT_TIMEOUT`); 0600 porque contém credencial do banco (SR-002).

## R7 — Clone: idempotente por estado do diretório, requirements do próprio repositório

**Decisão**: default `/opt/SisPatrimonioPro` (README). Estados — (a) inexistente → `git clone --branch main --single-branch` (FR-008); (b) clone válido (`.git` + `git rev-parse --is-inside-work-tree`) → reutilizar, reportar commit atual; (c) não-vazio sem `.git` → **abortar** pedindo decisão (não sobrescreve — briefing §7); (d) clone com alterações locais (`git status --porcelain` não-vazio) → avisar e continuar **somente** para reinstalação (nunca `reset --hard` sem confirmação — R11). `requirements.txt` é instalado **a partir do repositório recém-clonado** (`$INSTALL_DIR/requirements.txt`) — nunca de uma cópia antiga do instalador (framing do plan).

**Rationale**: cobre os estados do briefing §7 sem comportamento destrutivo; `--single-branch` minimiza superfície.

## R8 — venv: reuso ou reconstrução por integridade (não por idade)

**Decisão**: venv válido = `$INSTALL_DIR/.venv/bin/python` existe E `-m pip --version` funciona E `import fastapi, sqlalchemy, pymysql, ldap3, reportlab, openpyxl, dotenv` funciona (o teste de import do próprio README). Válido → reutilizar; inválido → remover e recriar (`rm -rf` do venv é seguro — artefato regenerável, nunca dado); rodar `pip install -r requirements.txt` sempre que (re)criado ou quando `--force-deps`; validação final = o mesmo one-liner de imports (FR-009).

**Rationale**: casa com a regressão real do projeto (venv inválido/dependência faltando foi causa de falha em sessão 019/026); recriar venv nunca toca dados (Constitution VII).

## R9 — Unit systemd: padrão do README + usuário dedicado + serviço de banco real

**Decisão**: unit baseada no padrão real do README (Type=simple, `After=network-online.target` + serviço de banco **detectado em R4** — `mariadb.service` ou `mysql.service`, `Wants=network-online.target`, `WorkingDirectory=$INSTALL_DIR`, `EnvironmentFile=$INSTALL_DIR/.env`, `ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/run.py`, `Restart=on-failure`, `RestartSec=5`, `WantedBy=multi-user.target`) — **sem gunicorn/multi-worker** (processo único é requisito arquitetural: flags em memória da 019 e scheduler-thread da 020 quebrariam — plan §Constraints). Usuário dedicado: default `sispatrimonio` (system user via `useradd --system --no-create-home --shell /usr/sbin/nologin`), propriedade do diretório (R10). `daemon-reload` + `enable` sempre; unit só reescrita se conteúdo mudar (idempotência — FR-018).

**Rationale**: NFR-004 (sem arquitetura paralela); FR-012 (D3 — dependência do banco real).

## R10 — Permissões: dono do diretório = usuário do serviço; log do instalador fora do repo

**Decisão**: `chown -R sispatrimonio:sispatrimonio $INSTALL_DIR` (aplicação escreve `data/logs/` e `data/backups/` — Realidade 12); `.env` 0600 dono `sispatrimonio`; log do instalador em **`/var/log/sispatrimonio-install.log`** (0600, root) — fora do repositório (não mistura com logs rotativos da aplicação; `.gitignore` não precisa mudar).

**Rationale**: Realidade 12 da spec; `.env` é credencial (0600 — SR-002); log fora do repo evita versionar artefato (briefing §13).

## R11 — Health check: espera ativa com timeout, `degraded` = WARNING

**Decisão**: após `systemctl start`, loop até 90 s: `curl -fsS http://127.0.0.1:$APP_PORT/health` → parse de `status` (`healthy` = OK; `degraded` = **WARNING** com explicação — aplicação no ar, item degradado é AD/banco indicado no corpo — Realidade 8; nunca falha a instalação). Timeout → `journalctl -u <service> -n 50 --no-pager` (sem segredos — Realidade: a aplicação sanitiza logs) no log do instalador + falha clara (FR-013/FR-019).

**Rationale**: `/health` é o endpoint real e público (não inventar outro — briefing §17); `degraded` é estado legítimo pós-instalação (AD configurado mas indisponível).

## R12 — Modo não interativo: validação total ANTES da primeira mutação

**Decisão**: parser de flags (`--non-interactive --install-dir --db-name --db-user --db-password --generate-db-password --app-port --repo --branch --service-name --service-user --recreate-db`); obrigatórios no modo não interativo: db-name, db-user, (db-password | generate); `--recreate-db` + `--non-interactive` → **falha imediata** na validação inicial (D2/FR-015). **Nenhuma mutação (pacote, arquivo, serviço) acontece antes da validação completa** (FR-015 — "sem execução parcial"). No interativo, defaults sensatos com confirmação final "Configuração resumida — confirmar? (s/N)" antes da primeira mutação.

**Rationale**: FR-015 exige falha clara sem prompt e sem parcialidade; confirmação final protege o interativo (briefing §14).

## R13 — --recreate-db (D2): dupla confirmação interativa, escopo do banco nomeado

**Decisão**: flag só existe no interativo; fluxo — (1) aviso destrutivo destacado; (2) digitar o NOME do banco para confirmar (1ª); (3) re-digitar (2ª); (4) recria **somente** o banco nomeado (DROP/CREATE do banco da aplicação + recria usuário/grants) — nunca outros bancos. Sem a flag: banco existente é **intocável** (reutiliza + valida + completa grants se faltando).

**Rationale**: decisão D2 aprovada pelo responsável; dupla confirmação (nome digitado 2×) é barreira suficiente para uso consciente em homologação.

## R14 — Validação pós-instalação: bateria + resumo final

**Decisão**: bateria (FR-014) — Python/venv/deps (imports R8) · MariaDB/MySQL ativo (`systemctl is-active`) · conexão DB (SELECT 1 via venv) · tabelas (verificação real: o próprio start do serviço roda `init_db()`; o instalador confirma a presença de tabela base via query do venv) · unit ativa/enabled · HTTP `/health`. Resumo final (FR-014/FR-020): URL `http://<host>:<port>` (e `http://<ip>:<port>` detectado), `/docs`, `/health`, caminhos, comandos `systemctl` reais (`sispatrimoniopro`), local do log, instruções do 1º admin (CLI `create-user` recomendado; `/setup` alternativa; env opcional), **sem exibir senha do banco** (SR-001).

**Rationale**: fecha o ciclo do briefing §38-estilo (onde configuro / onde salvo / quem usa); resumo é o contrato do operador.

## R15 — Update futuro (--update) e suíte pytest como regressão

**Decisão**: `--update` reconhecido e documentado como **ainda não implementado** (spec NFR-005 — mensagem clara, exit 2, aponta para o fluxo manual do README). Suíte pytest **não** é executada pelo instalador (Assumption da spec); a regressão desta feature é: suíte verde pré/pós (zero diff em `app/`) + validação funcional em VM limpa (quickstart).

**Rationale**: NFR-005 proíbe prometer comportamento não especificado; pytest dentro do instalador alongaria instalação (Assumption — tempo/escopo).
