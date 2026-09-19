# Contract: Instalador de Produção Linux — Feature 027

**Data**: 2026-09-19 | **Escopo**: contrato do artefato `install.sh` (raiz — decisão D1) e de seus efeitos colaterais permitidos. A implementação deve satisfazer cada item; o quickstart valida.

---

## 1. Interface de linha de comando

```bash
sudo bash install.sh                        # modo interativo (default)
sudo bash install.sh --non-interactive \
  --db-name sispatrimonio --db-user sispat \
  --generate-db-password                    # modo automatizado (FR-015)
```

| Flag | Valores | Obrigatório | Notas |
|---|---|---|---|
| `--non-interactive` | — | não | nenhum prompt; falha se faltar obrigatório |
| `--install-dir` | caminho absoluto | não | default `/opt/SisPatrimonioPro` |
| `--repo` / `--branch` | URL / nome | não | default repo oficial / `main` |
| `--db-name` / `--db-user` | identificador SQL | não interativo: **sim** | validação de identificador |
| `--db-password` \| `--generate-db-password` | segredo \| flag | não interativo: **uma das duas** | senha nunca em log/argv (SR-001) |
| `--app-port` | 1–65535 | não | default `8000`; porta livre exigida |
| `--service-name` / `--service-user` | identificador | não | default `sispatrimoniopro` / `sispatrimonio` |
| `--recreate-db` | — | não | **só interativo**; com `--non-interactive` → exit 2 na validação (D2) |
| `--update` | — | — | reconhecido → mensagem "ainda não implementado" + exit 2 (NFR-005) |
| `--help` | — | — | uso e defaults |

**Exit codes**: `0` sucesso · `2` uso inválido/validação de entrada · `1` falha de execução (etapa registrada no log).

## 2. Efeitos colaterais permitidos (universo fechado)

1. Instalar pacotes apt: `python3 python3-venv python3-pip git mariadb-server` (apenas quando ausentes/detecção R3/R4), `ca-certificates curl`.
2. Criar: diretório de instalação + clone; venv; banco/usuário/grants (R5/R13); `.env` (0600); usuário/grupo de sistema; unit systemd; `/var/log/sispatrimonio-install.log`.
3. Habilitar/iniciar: serviço MariaDB/MySQL detectado (quando recém-instalado) e `sispatrimoniopro.service`.

**PROIBIDO (qualquer diff aqui quebra o contrato)**:

- alterar qualquer arquivo em `app/`, `requirements.txt`, `tests/`, `seed_demo.py` (zero diff — FR-001/SC-004);
- criar tabelas/schema/migração própria (delegado a `init_db()` — FR-011);
- apagar/recriar banco sem `--recreate-db` com dupla confirmação interativa (D2/SR-004);
- sobrescrever `.env` existente (backup + merge consentido apenas — FR-010);
- registrar senha/segredo em log, argv de comando gravado ou mensagem (SR-001);
- rodar a aplicação como root ou criar fonte de configuração paralela ao `.env` (SR-003/§17 do briefing da 026);
- repositórios apt de terceiros para Python (FR-003);
- executar a suíte pytest ou seed_demo (Assumptions da spec).

## 3. Comportamento obrigatório (resumo normativo)

| # | Requisito | Referência |
|---|---|---|
| 1 | Gates iniciais: sudo, distro Debian (`/etc/os-release` + systemd), conectividade; falha → mensagem clara e abort | FR-002 |
| 2 | Python ≥ 3.10 com **re-verificação pós-install** (no-op do Debian antigo detectado) | FR-003/R3 |
| 3 | SGBD: detecta MariaDB **ou** MySQL por serviço/utilitários reais; instala MariaDB só se nenhum | FR-005/D3/R4 |
| 4 | Banco utf8mb4/utf8mb4_unicode_ci; grants **só** no banco da aplicação; `MYSQL_PWD` (nunca argv) | FR-006/SR-003/R5 |
| 5 | Teste de conexão real via engine do projeto no venv antes de prosseguir | FR-007 |
| 6 | Clone idempotente por estado (inexistente/válido/não-vazio-sem-.git/alterações locais) | FR-008/R7 |
| 7 | `requirements.txt` instalado a partir do **repositório clonado**; validação = imports do README | FR-009/R7/R8 |
| 8 | `.env` 0600 com `DATABASE_URL` (percent-encoded via `quote_plus`), `APP_HOST=0.0.0.0`, `APP_PORT`, `MYSQLDUMP_PATH` condicional; existente → nunca sobrescrito | FR-010/SR-002/R6 |
| 9 | Unit systemd do padrão real do README + usuário dedicado; dependência = serviço de banco **detectado**; reescrita só se conteúdo muda | FR-012/R9 |
| 10 | Start + espera `/health` (90 s; `degraded`=WARNING com explicação; timeout → `journalctl` no log) | FR-013/R11 |
| 11 | Bateria pós-instalação + resumo final (URL, /docs, /health, systemctl, log, 1º admin por env//setup/CLI; sem senha do banco) | FR-014/R14 |
| 12 | Log com níveis `[ * ]/[OK]/[!!]/[XX]` em `/var/log/sispatrimonio-install.log` (0600); trap ERR com etapa/linha | FR-016/FR-019/R1/R2 |
| 13 | Idempotência de ponta a ponta: 2ª execução reutiliza tudo, não altera dados do banco nem `.env` válido | FR-018 |

## 4. Critérios de aceite do contrato (verificáveis)

- `grep -F "$DB_PASSWORD" /var/log/sispatrimonio-install.log` → **vazio** (com a senha usada na instalação).
- `stat -c '%a %U' $INSTALL_DIR/.env` → `600 sispatrimonio` (usuário do serviço).
- `mysql -e "SHOW GRANTS FOR '$DB_USER'@'localhost'"` → apenas privilégios em `sispatrimonio`.* — nenhum global (`*.*` ausente).
- `git status --porcelain` no repositório pós-instalação → nenhum diff em `app/` (zero diff de aplicação).
- Segunda execução completa → exit 0, "reutilizado" reportado nas etapas, banco e `.env` byte-idênticos (hash antes/depois).
- `--recreate-db --non-interactive` → exit 2 **antes de qualquer mutação**.
