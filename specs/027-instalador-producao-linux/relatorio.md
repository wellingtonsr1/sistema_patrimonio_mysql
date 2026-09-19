# Relatório Final: Instalador Automatizado de Produção Linux — Feature 027

**Data**: 2026-09-19 (**atualizado na mesma data** — manutenção pós-entrega, §9) | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Tasks**: [tasks.md](./tasks.md)

---

## 1. Entrega principal

📄 **`install.sh`** (raiz do repositório, executável) — instalador único em bash estrito (`set -Eeuo pipefail`), conforme decisões D1–D4 da spec e contrato [installer-contract.md](./contracts/installer-contract.md).

## 2. Arquivos alterados/criados

| Arquivo | Alteração |
|---|---|
| `install.sh` | **NOVO** — instalador completo (15 etapas do fluxo normativo) |
| `README.md` | §"Instalação em uma máquina nova": seção do instalador (uso interativo/não interativo, tabela de opções, garantias de segurança/idempotência) antes do fluxo manual, que permanece como alternativa (FR-021) |
| `docs/GUIA_DE_MANUTENCAO.md` | Seção "Instalação de produção automatizada (feature 027)" em "Como executar o sistema": operação do serviço (`systemctl`/`journalctl`), regras operacionais (idempotência, `.env.bak`, log, sem schema próprio, `--update` reservado, HTTPS fora do escopo, `APP_HOST/APP_PORT` no `.env`) |

## 3. Implementação por requisito (mapa resumido)

| Requisito | Onde está no `install.sh` |
|---|---|
| FR-002 gates (sudo/distro/systemd/conectividade) | `require_root`, `check_distro`, `check_connectivity` |
| FR-003 Python ≥ 3.10 + **re-verificação pós-install** (R3) | `ensure_packages` → `python_at_least` após `apt-get install` (no-op do Debian antigo → abort com orientação, sem repositórios de terceiros) |
| FR-004 Git | `ensure_packages` (instala se ausente) |
| FR-005/FR-012 D3 (MariaDB **ou** MySQL; unit usa serviço real) | `detect_host` (por `systemctl is-active mariadb/mysql` + binários), `ensure_packages` (instala `mariadb-server` só se nenhum), unit com `After=… $BANCO_SERVICE_DETECTED` |
| FR-006 banco/usuário/grants mínimos (SR-003) | `ensure_database` (utf8mb4/utf8mb4_unicode_ci; `GRANT … ON db.*` apenas) |
| FR-007 teste de conexão via engine do projeto | `test_db_connection` (venv + `app.config.DATABASE_URL` + `SELECT DATABASE()`) — executado **após** venv (resolve achado I1 do analyze) |
| FR-008/FR-009 clone/venv idempotentes (R7/R8) | `ensure_repo` (4 estados), `ensure_venv` (válido→reutiliza; inválido→recria; imports do README como validação) |
| FR-010 `.env` 0600, percent-encoding, nunca sobrescrito (SR-002, R6) | `build_database_url` (`quote(safe='')` — espaço→`%20`; ver §9.2), `ensure_env_file` (`umask 077`, backup `.env.bak-<ts>`, merge só de chaves ausentes com consentimento) |
| FR-011 sem schema próprio | Nenhuma DDL de tabela no script — criação delegada ao `init_db()` no start do serviço |
| FR-013 start + `/health` (degraded=WARNING) | `start_and_health_check` (90 s; timeout → `journalctl -n 50` no log) |
| FR-014 bateria + resumo (R14) | `post_install_checks` (7 checagens nomeadas OK/ERRO; tabela base = `users` — resolve achado A1), `print_summary` (URL//docs//health/systemctl/log/1º admin pelos 3 mecanismos reais; **sem senha**) |
| FR-015 não interativo (validação antes de mutar) | `parse_args`/`validate_inputs` (obrigatórios listados; `--recreate-db`+`--non-interactive` → exit 2; `--update` → exit 2 — NFR-005) |
| FR-016 log com níveis + arquivo 0600 (R1/R2) | `setup_logging` (`/var/log/sispatrimonio-install.log` via `tee`), `info/ok/warn/err` — **canal único stderr sem buffering** (ordem garantida em console lento; §9.1) |
| FR-017/FR-018 D2 `--recreate-db` | `confirm_recreate_db` (dupla confirmação digitando o nome do banco; DROP apenas do banco nomeado) |
| FR-019 falha segura | `trap … on_error` (etapa+linha+orientação de reexecução); serviço habilitado só após health OK |
| FR-020 1º admin pelos mecanismos reais | `print_summary` (CLI recomendado / `/setup` / env — sem mecanismo novo) |
| SR-001 senha nunca em log/argv | `MYSQL_PWD` no ambiente do processo (padrão da aplicação 018); coleta `read -rs` com janela `set +x`; **auto-check** `security_self_check` (grep da senha no log deve ser vazio) |
| SR-002 senha com caracteres especiais íntegra | `quote(safe='')` na `DATABASE_URL` (espaço→`%20`, `@`→`%40`, `#`→`%23`…); **backslash rejeitado antes de qualquer mutação** (`validate_inputs`, `collect_secrets`, `sql_escape`) — §9.2 |

## 4. AT-1/AT-2/AT-3 — não se aplicam (feature 027 não é documental da 025); decisões D1–D4 aplicadas

| Decisão | Como foi implementada |
|---|---|
| **D1** `install.sh` na raiz | Arquivo único versionado, executado a partir do clone |
| **D2** `--recreate-db` | Dupla confirmação interativa; proibido em `--non-interactive` (validação inicial) |
| **D3** MariaDB + MySQL | Detecção por serviço/binários reais; reutiliza qualquer um; instala MariaDB se nenhum |
| **D4** HTTPS fora do escopo | Sem nginx/TLS; `AUTH_COOKIE_SECURE` configurável no `.env` (documentado no GUIA) |

## 5. Validações executadas (somente as reais)

| Validação | Resultado |
|---|---|
| `git status` pré (T001) | Limpo (só `specs/027-*/`) |
| **Suíte pytest pré** (T001) | **544 passed** |
| `bash -n install.sh` | OK |
| `shellcheck -S warning install.sh` | **CLEAN** (0 warnings após correções SC2034/SC2155) |
| **Suíte pytest pós** (T022) | 1ª execução: 543 passed + 1 flaky (`test_019_webPostRestaurarResponde303Imediato` — timing de thread do worker 019; **passou isolada** e na reexecução da suíte completa: **544 passed**) — nenhum teste alterado; o instalador não toca `app/` |
| `git status`/`git diff --stat` pós (T022) | Escopo confinado a `install.sh` (novo) + `README.md` (+32) + `docs/GUIA_DE_MANUTENCAO.md` (+28) + `specs/027-*/` — **zero diff em `app/`, `tests/`, `requirements.txt`** (contract §2) |

## 6. Validações operacionais pendentes [OPERADOR] (quickstart Passos 3–7)

Estas exigem uma **VM/servidor limpo** e não podem ser executadas nesta máquina de desenvolvimento:

- **Passo 3** — instalação limpa interativa ponta a ponta + conferências do contract §4 (senha ausente do log; `.env` = `600 <service_user>`; grants sem globais; `/health` OK);
- **Passo 4** — idempotência (2ª execução: `.env` byte-idêntico por hash; contagem de `users` inalterada);
- **Passo 5** — modo não interativo + guardas (exit 2 sem parcialidade; combinação proibida rejeitada);
- **Passo 6** — fluxos adversos (porta ocupada, diretório não-vazio sem `.git`, `.env` existente com backup, banco existente sem DROP, dupla confirmação do `--recreate-db`);
- **Passo 7** — 1º admin via CLI + login na UI + `init_db()` criando schema no start.

## 7. Limitações honestas

- A validação **funcional real** do instalador depende de servidor limpo (tarefas [OPERADOR] acima) — aqui foram validados sintaxe, shellcheck, escopo do diff e regressão da suíte;
- `--update` é deliberadamente não implementado (NFR-005 — mensagem clara e exit 2);
- MySQL Oracle: suportado **apenas na detecção/reuso** (D3); a instalação automática é sempre MariaDB;
- O auto-check de segurança (grep da senha no log) cobre o log do instalador — não substitui auditoria de segurança do host.

## 8. Divergências deixadas para features futuras

Nenhuma nova. Resquícios documentais pré-existentes (SQLite em `.gitignore`/ARQUITETURA §891/§1148 e `APP_HOST=127.0.0.1` no ARQUITETURA:74, divergência já conhecida da análise da spec) permanecem registrados e fora do escopo (Constitution I).

## 9. Manutenção pós-entrega (2026-09-19 — mesma data do relatório)

Correções aplicadas após os primeiros testes reais em VM, registradas aqui para manter este relatório fiel ao estado atual do instalador. Commits: `c909fc5` (visual/correção do serviço de banco), `9a2a115` (canal único), `4ead6be` (senha com caracteres especiais + desinstalador no canal único) e a linha de fixes `a0eea87`–`7d2fa6d`–`3d26814`–`d4e1dff`–`2b71857` (reexecução/reparo). Detalhes das duas correções principais:

### 9.1 Saída em canal único não-bufferizado (install.sh e uninstall.sh)

**Sintoma real em VM (console lento — serial/VNC)**: o prompt `Confirmar e iniciar a instalação? (s/N)` e a mensagem de senha gerada **saltavam para frente do RESUMO DA INSTALAÇÃO**. **Causa**: dois canais com velocidades diferentes — stdout do script sob o pipe do `tee` (buffer de bloco da libc quando não é tty) versus prompts escritos direto no `/dev/tty` (imediato); em console lento o canal direto vencia a corrida. **Correção**: todo o output (tags, títulos, resumo, prompts, stdout de apt/pip) passa pelo **stderr sem buffering**; pós-`setup_logging` stderr == stdout (mesmo pipe → tee → tela+log), um único canal FIFO garante a ordem em qualquer terminal. O log continua recebendo texto limpo (sem ANSI) e os prompts vão ao log sem segredos. Mesma correção aplicada ao `uninstall.sh` (onde o padrão ainda existia).

### 9.2 Senha com caracteres especiais (2 gaps corrigidos — verificação empírica)

| Gap | Sintoma | Correção |
|---|---|---|
| **Espaço na senha** | `quote_plus` codifica espaço como `+`, mas o parse de URL do SQLAlchemy **não** decodifica `+` como espaço → senha corrompida → `Access denied` | `quote(safe='')` em `build_database_url` (espaço→`%20`) e no comando manual do README (com explicação) |
| **Backslash na senha** | `sql_escape` só dobrava aspas; o MySQL interpreta `\n`/`\t` dentro de string literal (sem `NO_BACKSLASH_ESCAPES`) → senha gravada errada no `CREATE/ALTER USER` | Backslash **rejeitado antes de qualquer mutação** (`validate_inputs` no CLI, `collect_secrets` interativo e `sql_escape`); a senha gerada (`token_urlsafe`) nunca contém `\` |

Round-trip verificado com o SQLAlchemy real do projeto para 7 senhas hostis (`pa ss`, `p@ss:w0rd#1`, `senha+mais`, `100%!/$&?`, `çãõ espaços`, `Min#ha%20Senha`, `aspas'dupla'`): **todos OK**. Documentação: comando manual corrigido no README + regras de senha do banco registradas no GUIA ("Regras operacionais do instalador"). O default `DEFAULT_REPO_URL` passou a apontar para `SisPatrimonioPro.git` (repo renomeado).

### 9.3 Validações da manutenção

| Validação | Resultado |
|---|---|
| Reprodução empírica da ordem (padrão antigo vs canal único sob pipe) | canal único preserva a ordem exata |
| Round-trip `quote(safe='')` via SQLAlchemy (7 senhas hostis) | **todos OK** |
| `sql_escape` com backslash no meio | **REJEITADA** |
| `bash -n` + `shellcheck -S warning` (install.sh e uninstall.sh) | **CLEAN** |
| Suíte pytest pós-manutenção | **544 passed** (o flaky `test_019_webPostRestaurarResponde303Imediato` já documentado no §5 passou isolada e na reexecução) |
| Smoke do `uninstall.sh` (gate de root + funções sob pipe bufferizado) | ordem e renderização corretas |

### 9.4 Pendências [OPERADOR] adicionais

- Instalação real com senha contendo **espaço** e `@ #` — confirmar login da aplicação (o round-trip local já cobre o parse, falta o ciclo com MariaDB real);
- Confirmar em console serial/VNC que o RESUMO e os prompts aparecem **na ordem** (correção §9.1 foi verificada sob pipe, não em console físico lento);
- Desinstalação real em VM (`uninstall.sh`) — os smokes desta máquina cobriram apenas o gate e a renderização.
