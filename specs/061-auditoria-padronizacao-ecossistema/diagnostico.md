# Diagnóstico do ecossistema SisPatrimônio Pro — Feature 061 (Fase 1)

**Status**: Draft — **revisão 2** (aprofundamento de install.ps1/uninstall.ps1/Docker solicitado no gate T014) · **Data**: 2026-10-02 · **Executor**: Buffy · **Escopo**: somente leitura (nenhum arquivo funcional alterado)

## 1. Metodologia e ambiente

- Máquina: Linux (Pop!_OS). Repos examinados: dev (local), `SisPatrimonioPro` (clone raso `/tmp/pro-read-061`), `SisPatrimonioPro-install` (checkout local `~/IA/SisPatrimonioPro-install`).
- Ferramentas: `git status/branch/remote/log/ls-files/diff`, `grep -rni`, `diff -q`, `wc -l`, pytest. (Obs.: `rg` ausente na máquina; varreduras feitas com `grep`.)
- Todo achado abaixo tem evidência (arquivo:linha, diff ou comando reprodutível).

## 2. Estado do workspace (T002)

- Branch atual: `main` (a feature vive em `specs/061-.../`; branch git da feature não criada — sem hook `before_specify`).
- `git status --short`: apenas `?? specs/061-auditoria-padronizacao-ecossistema/` (artefatos da feature). Nenhum arquivo funcional tocado ✅.
- HEAD dev: `1245925 Ajustes finos` · remotos: dev `wellingtonsr1/sistema_patrimonio_mysql.git`, PRO `wellingtonsr1/SisPatrimonioPro.git`, install `wellingtonsr1/SisPatrimonioPro-install.git`.

## 3. Baseline de testes (T003)

| Métrica | Valor |
|---|---|
| Comando | `.venv/bin/python -m pytest -q` |
| Resultado | **923 passed, 1 skipped**, 3 warnings (DeprecationWarning pyasn1/ldap3) |
| Tempo | 76,4 s |
| Referência | baseline da 056 era 889 passed — suíte cresceu desde então; **923/1 é o baseline oficial desta feature** |

## 4. Arquitetura real e fluxo de deploy (T005)

**A arquitetura real tem 3 repositórios** (o diagrama do briefing §22 omitia o terceiro):

```text
sistema_patrimonio_mysql (dev, main)
   │  deploy.sh / deploy.bat: 1) commit  2) push origin main  3) snapshot whitelist → push --force
   ▼
SisPatrimonioPro (snapshot de produção, main)  ◀── clone dos instaladores
   ▲
SisPatrimonioPro-install (terceiro repo) — install.sh/install.ps1 (nativa) + variantes docker + README/TROUBLESHOOTING
   │  clona o PRO em C:\SisPatrimonioPro (Windows) ou /opt/SisPatrimonioPro (Linux) e instala
   ▼
Produção (serviço: Tarefa Agendada no Windows / systemd no Linux)
```

**Whitelists DIVERGENTES** (evidência: `deploy.sh` L166–172 vs `deploy.bat` L176–198):

| Item | deploy.sh (Linux) | deploy.bat (Windows) |
|---|---|---|
| `app/`, `data/`, `docs/*.md` (sem `doc_provi*`) | ✅ mantém | ✅ mantém |
| `scripts/` | ❌ **remove** | ✅ **mantém** |
| `migrations/` | ❌ **remove** | ✅ **mantém** |
| `.gitignore, README.md, requirements.txt, run.py, seed_demo.py, sistema_patrimonio.png, SPEC-KIT-SISTEMA-ATUAL.md` | ✅ | ✅ |
| `.env.example`, `install.sh`, `deploy.*`, `test.bat`, specs/, tests/ | ❌ | ❌ (`install.sh` e `deploy.*` nem existem no PRO) |

- Push `--force` no PRO (intencional — snapshot); rollback oficial via `deploy.sh rollback <hash-dev>` (recria snapshot com a mesma whitelist).

## 5. Snapshot PRO × whitelist (T008)

Estado atual do PRO (HEAD raso clonado):

- **Contém** `migrations/` (alembic) e `scripts/gera_cert_dev.py` → a última publicação partiu do **Windows** (`deploy.bat`).
- **Contém residuais commitados da dev**: `app/config.py~` e `app/.config.py.un~` (lixeira de editor publicada em produção — erro).
- **Não contém** `.env.example` (nenhum dos dois scripts o inclui) — classificar necessidade.
- `SPEC-KIT-SISTEMA-ATUAL.md` presente no PRO — classificar (documento interno de specs).
- **Risco concreto da divergência**: uma publicação pelo `deploy.sh` (Linux) **apagaria** `migrations/` e `scripts/` do PRO. Sem `migrations/`, o boot segue (warning em `app/database.py:_ensure_alembic_state`) mas o versionamento de schema fica degradado ("deltas futuros EXIGEM este diretório" — L106) e `gera_cert_dev.py` sumiria do PRO, quebrando a base da correção HTTPS planejada (T016).

## 6. Baseline HTTPS da dev (T007) — mecanismo funcional (056)

1. `run.py` L29–60: lê `APP_SSL_CERTFILE`/`APP_SSL_KEYFILE` de `app/config.py`; valida existência dos arquivos com mensagem clara; passa `ssl_certfile/ssl_keyfile` ao `uvicorn.run`; sem envs → HTTP puro (byte-a-byte).
2. `app/config.py` L93–120: `APP_PORT` default **8000**; `_normaliza_caminho_cert()` converte `\`→`/` e resolve relativo contra `BASE_DIR` (o mesmo `.env` funciona no Windows e no Linux).
3. `app/config.py` L142–143: `AUTH_COOKIE_SECURE` (default `false`), aplicado no cookie em `session_service.py` L98.
4. `scripts/gera_cert_dev.py` (143 linhas, openssl CLI, sem dependência Python nova): gera `data/ssl/ca.crt|ca.key|server.crt|server.key`; SAN = `IP:<lan>`, `DNS:localhost`, `DNS:<hostname>`, `DNS:sispatrimoniopro.local`; validade CA 3650 d / servidor 825 d; idempotente com `--force`.
5. `.env.example` L25–34 documenta `APP_SSL_*` + `AUTH_COOKIE_SECURE` (com aviso de que `true` sem HTTPS **quebra o login** — importante para a correção).
6. Sem redirect HTTP→HTTPS (decisão 056, mantida pela 061/D-002).

**Conclusão**: o HTTPS da dev é 100% dirigido por envs do `.env`. Qualquer ambiente que não escreva essas envs roda em HTTP — o que nos leva à causa raiz.

## 7. Instaladores — repositório de instalação (T009)

**Terceiro repositório**: `wellingtonsr1/SisPatrimonioPro-install.git` (checkout local, branch `main`, HEAD `496794c`). Conteúdo:

| Caminho | Papel | Observação |
|---|---|---|
| `install no windows/nativa/install.ps1` | **instalador Windows nativo** (982 linhas, 15 etapas, v1.1.0-win) | alvo da correção (T016) |
| `install no windows/nativa/uninstall.ps1` | desinstalador | revisar na correção |
| `install no linux/nativa/install.sh` | instalador Linux | **idêntico** ao `install.sh` da dev (diff vazio; 1198 linhas) |
| `install no linux/nativa/uninstall.sh` | desinstalador Linux | — |
| `install no {windows,linux}/docker/` | variantes Docker | classificar suporte (fora do escopo nativo) |
| `README.md` (38 KB) + `TROUBLESHOOTING.md` | docs de instalação | **zero menções a https/ssl/cert** |

`install.ps1` — fluxo verificado (com evidências): pré-requisitos admin → Python 3.12/Git/MariaDB via **winget** (MariaDB.Server quando nenhum serviço `^(MariaDB|MySQL)` existe — D3; serviço MySQL existente é **reutilizado**) → clone do PRO → venv+requirements → `DATABASE_URL` com **percent-encoding via Python** (`quote`, senha nunca em argv/log) → banco `utf8mb4/utf8mb4_unicode_ci` + usuário (`localhost` e `127.0.0.1`, grants só no banco) → `.env` com ACL restrita (icacls; nunca sobrescrito; backup `.bak-<ts>`) → teste de conexão real → **Tarefa Agendada** (`AtStartup` +30 s, restart 3×/1 min, SYSTEM) → sanity → init_db explícito → health HTTP 120 s → bateria pós-instalação → self-check de senha no log → regra de firewall idempotente `SisPatrimonio Pro (<porta>)` → resumo em `http://`.

**Linhas-chave mapeadas** (revisão 2): `Find-DbClientExe` L332–344 · `Ensure-Packages` L373–436 · `Invoke-DbSql` (MYSQL_PWD no ambiente) L442–457 · `Build-DatabaseUrl` L636–648 (scheme fixo `mariadb+pymysql` em L640) · `Test-DbConnection` L653–663 · `Ensure-EnvFile` L671–726 (`.env` novo L710–721) · `Ensure-ServiceTask` L730–755 · `Init-Database` L781–793 · health `http://` L802/852 · resumo `http://` L898–900 · firewall L967–976 (só se `AppHost ≠ 127.0.0.1`; regra nomeada com a porta — **regra órfã se a porta mudar**) · `-Update` reservado (L131, L206).

**`uninstall.ps1` (377 linhas) — segurança verificada**: remoção do diretório opt-in (default preserva); remoção do banco exige **digitar o nome** para confirmar (L271–274) e é evitável com `-KeepDb` (L255–257); usuário do banco é removido só com confirmação própria (L283–293); `-PurgeMariaDb` (destrutivo, todos os bancos) é flag separada com dupla confirmação (L295+). Nenhum dado apagado silenciosamente ✅ (política Constitution VII preservada).

**Variantes Docker** (`install no windows/docker/install-docker.ps1`): usam o `docker-compose.yml` **do próprio PRO** (containers `sispat-app` + `sispat-db` mariadb:11), obrigam troca de `changeme-root`, segredos só no `.env` com ACL. Classificação: variante suportada paralela — fora do escopo nativo da 061 (documentar como alternativa).

**Atualização (update) — LACUNA CONFIRMADA (CS-5)**: `-Update`/`--update` não implementado (NFR-005; `die "ainda nao esta implementada"`); `Ensure-Repo` reutiliza clone existente **sem `git pull`** — reexecutar o instalador **não avança o código**; README não documenta `git pull` como procedimento de atualização. Ou seja: **não há caminho implementado/documentado para atualizar uma instalação Windows** — afeta diretamente o cenário "atualização" da spec (FR-022/FR-027/FR-028) e a sobrevivência do HTTPS após atualização.

**TROUBLESHOOTING.md**: índice de sintomas T1–T14 (nativa + Docker), sem nenhuma entrada de HTTPS/certificado — após a correção, ganhará entradas novas (FR-029).

## 8. Causa raiz — HTTPS perdido na instalação Windows (T010) ✅ CONFIRMADA

**Evidência principal** — `install.ps1` `Ensure-EnvFile` (L~770–790), conteúdo integral do `.env` gerado:

```text
DATABASE_URL=mariadb+pymysql://...
APP_HOST=0.0.0.0
APP_PORT=8000
MYSQLDUMP_PATH=<se encontrado>   # opcional
```

- **Zero** ocorrências de `APP_SSL_CERTFILE`/`APP_SSL_KEYFILE`/`AUTH_COOKIE_SECURE`/geração de certificado nas 982 linhas; health check e resumo usam `http://` (L~880, L~900); docs do repo de instalação não mencionam HTTPS.
- A Tarefa Agendada executa `python.exe run.py` — e `run.py` só liga TLS se as envs existirem. **Logo o sistema instalado sobe em HTTP puro.**

**Causa raiz (confirmada)**: o `install.ps1` é o port da decisão **D4 da 027** ("HTTPS fora do escopo"), criado **antes** da 056 e nunca atualizado. A dev ganhou TLS nativo (056) dirigido por envs; o instalador nunca passou a escrevê-las. Não há "perda" de configuração — há **configuração que nunca existiu no instalador**. O mecanismo correto já existe (056) e o PRO já distribui seu gerador (`scripts/gera_cert_dev.py`) — a correção é plugar o baseline 056 no instalador (T016), sem criar nada novo.

**Causas secundárias confirmadas no mesmo exame**:

| # | Achado | Evidência | Impacto |
|---|---|---|---|
| CS-1 | `migrations/versions/0002` usa `ADD COLUMN IF NOT EXISTS`/`CREATE INDEX IF NOT EXISTS` — **MariaDB 10.5+; MySQL não suporta** | `0002_migracoes_legadas_idempotentes.py` L18–66; doc `ANALISE_PROFUNDA_2026-09-29.md` L114 já registrava ("MySQL puro quebra") | Instalação nova com **MySQL nativo**: `init_db()` → stamp 0001 → `upgrade head` → 0002 → **erro de sintaxe** → retry → `raise` → **instalador morre em "Inicializacao do schema"**. Quebra o objetivo Windows+MySQL desta feature |
| CS-2 | `DATABASE_URL` com scheme **fixo** `mariadb+pymysql://` mesmo quando o servidor detectado é MySQL | `install.ps1 Build-DatabaseUrl` L~700 | Funciona contra MySQL na prática (PyMySQL), mas o dialecto `mariadb` do SQLAlchemy pode mascarar diferenças de versão/features — risco a validar na Fase 4 |
| CS-3 | Instalador **reutiliza** o serviço do XAMPP se ele existir (regex `^(MariaDB\|MySQL)` pega o serviço do XAMPP) | `Detect-Host`/`Ensure-Packages` | Perpetua XAMPP na produção (arquitetura §FR-013 pede MySQL nativo); T012 na máquina real confirma o estado |
| CS-3b | No servidor de produção atual (XAMPP), `Find-DbClientExe` (L332–344) procura o cliente **apenas em `Program Files\MariaDB*`/`Program Files\MySQL*`/PATH** — não em `C:\xampp\mysql\bin` (fora do PATH por padrão) | `install.ps1` L332–344 + `Ensure-Packages` L426–428 | Instalador **morre na etapa 1** ("Cliente SQL (mysql/mariadb) nao encontrado...") na máquina real de hoje — a atualização via instalador exige MySQL/MariaDB nativo (reforça a estratégia §FR-013) |
| CS-4 | Firewall já automático e idempotente (alinhado à decisão A do clarify Q5) — mas porta única HTTP; regra nomeada pela porta fica **órfã** se a porta mudar; só criada quando `AppHost ≠ 127.0.0.1` | `install.ps1` L967–976 | Ajuste mínimo na correção |
| CS-5 | **Nenhum fluxo de atualização implementado**: `-Update` reservado (die L206); `Ensure-Repo` nunca faz `git pull`; README não documenta procedimento de atualização | `install.ps1` L131/L206/L614–625; README L187 | "Atualização" da spec (FR-022/FR-027/FR-028) não tem caminho — precisa de mecanismo (ou procedimento documentado) na Fase 2/3 |

## 9. Banco de dados — auditoria e matriz MariaDB × MySQL (T011) — Entregável B

Fundação verificada: `DATABASE_URL` obrigatória sem fallback SQLite (`app/config.py` L27–36); engine QueuePool (pool_size 10, max_overflow 20, timeout 30, recycle 1800, pre_ping) (`app/database.py` L14–22); `init_db()` = `create_all` tolerante à corrida (erro 1050 → 1 retry) + `_ensure_alembic_state()` (SQLite no-op; stamp `0001` baseline zero-DDL; `upgrade head`; warning se `migrations/` ausente; falha persistente relançada) (L56–177). Migrations: `0001_baseline` (no-op) e `0002_migracoes_legadas_idempotentes` (ALTERs idempotentes MariaDB-only).

| Componente | MariaDB | MySQL | Status da verificação |
|---|---|---|---|
| Driver (PyMySQL ≥1.1.0) | ✅ | ✅ (protocolo compatível) | verificado (requirements + comment) |
| URL scheme via env | ✅ `mariadb+pymysql` | ⚠️ app aceita `mysql+pymysql` por env; **instalador fixa `mariadb+pymysql`** | verificado (código) |
| SQLAlchemy ≥2.0 + pool | ✅ | ✅ (agnóstico) | verificado (`database.py`) |
| CREATE TABLE (`create_all`) | ✅ | ✅ (SQLAlchemy gera por dialecto) | verificado |
| **ALTER TABLE idempotente (migrations 0002)** | ✅ (10.5+) | ❌ **`IF NOT EXISTS` não existe no MySQL** | **confirmado (código + doc de análise)** |
| Alembic stamp/upgrade flow | ✅ | ✅ mecanismo; ✗ conteúdo 0002 | verificado (`_ensure_alembic_state`) |
| Race 1050 (create_all) | ✅ | ✅ (código de erro comum) | verificado |
| Datetime / Boolean | ✅ | ✅ (tipos SQLAlchemy agnósticos) | verificado (models) |
| JSON | ✅ (LONGTEXT-JSON) | ✅ (JSON nativo) | verificado por uso de `JSON` do SQLAlchemy em 7+ models |
| Enum | ⚠️ | ⚠️ | `enums.py` + `_register_all_enums` (alembic); natureza (nativo vs VARCHAR) a confirmar em teste real (Fase 4) |
| Transações (SessionLocal) | ✅ | ✅ (agnóstico) | verificado |
| Charset/collation do banco | ✅ utf8mb4/utf8mb4_unicode_ci | ✅ (instaladores criam com esse charset) | verificado (install.sh/ps1); conexão não fixa charset na URL (nota) |
| Backup/restore (`mysqldump`) | ✅ | ✅ (binário próprio do MySQL Server) | verificado (config MYSQLDUMP_PATH) |
| SQL de instalação | ✅ | ✅ (CREATE DATABASE/USER/GRANT padrão) | verificado (ambos instaladores) |

## 10. XAMPP — inventário e classificação (T012)

| Local | Ocorrência | Classe | Ação proposta (Fase 2) |
|---|---|---|---|
| `app/config.py:40` | comentário "Exemplo (Windows/XAMPP): MYSQLDUMP_PATH=C:\xampp\..." | exemplo em código | substituir exemplo por MySQL nativo (sem remover a variável) |
| `.env.example:10–11` | exemplo XAMPP para MYSQLDUMP_PATH | documentação | atualizar exemplo |
| `.env` local (dev, não versionado, L7–8) | comentário exemplo XAMPP | documentação local | atualizar na máquina (não versionado) |
| `docs/ARQUITETURA_E_MANUTENCAO.md:245` | "necessário no Windows/XAMPP" | documentação | atualizar (FR-029) |
| `docs/ANALISE_PROFUNDA_*.md` (2026-09-29/30) | menções históricas (produção XAMPP parada, suíte dependente de XAMPP) | **histórico** | manter (documento datado) |
| `specs/021/...` | histórico | histórico | manter |
| **Repositório de instalação** | **0 ocorrências** | — | nada |
| **Snapshot PRO** | 0 ocorrências | — | nada |
| Máquina Windows de produção | **PENDENTE** (docs indicam que produção roda sobre XAMPP/MariaDB — "10.39.0.16 não respondeu, XAMPP/MariaDB parados") | ambiente real | checklist §13 |

**Dependência funcional de XAMPP no código: NENHUMA.** A dependência é ambiental (produção Windows usa o MariaDB do XAMPP; o instalador ainda a reutilizaria — CS-3).

## 11. Divergências dev × PRO × install (Entregável D — rascunho)

| # | Divergência | Classe |
|---|---|---|
| D-1 | Whitelist `deploy.sh` ≠ `deploy.bat` (`scripts/` e `migrations/` só no `.bat`) | **erro** (quebra SC-007; publicar do Linux degrada o PRO) |
| D-2 | Residuais commitados na dev e publicados no PRO (`app/config.py~`, `app/.config.py.un~`; raiz: `..env.un~`, `_teste_smtp_direto.py`, `uninstall.sh-old`) | erro (limpeza + guard na whitelist) |
| D-3 | Instalador Windows sem qualquer configuração TLS (causa raiz §8) | erro (dor central da feature) |
| D-4 | `migrations/0002` MariaDB-only | erro/risco (bloqueia Windows+MySQL — CS-1) |
| D-5 | `DATABASE_URL` scheme fixo `mariadb+pymysql` no instalador | risco (CS-2) |
| D-6 | PRO sem `.env.example`; `SPEC-KIT-SISTEMA-ATUAL.md` no PRO | classificar (necessária/obsoleta) |
| D-7 | Instalador reutiliza MariaDB do XAMPP se presente | decisão (FR-013 — MySQL nativo) |
| D-8 | Docs de instalação sem menção a HTTPS | erro documental (FR-029) |
| D-9 | `DbName` default diverge: `sispatrimoniopro` (ps1) × `sispatrimoniopro_db` (sh) | inconsistência menor |
| D-10 | Residual `backup-$` na raiz do repo de instalação | obsoleto |
| D-11 | Sem fluxo de atualização implementado/documentado no Windows (CS-5) | lacuna |
| D-12 | Regra de firewall nomeada pela porta fica órfã ao mudar a porta; criada só quando `AppHost ≠ 127.0.0.1` | risco menor |

## 12. Causas prováveis × confirmadas (resumo executivo)

**Confirmadas** (evidência de código/execução):
1. HTTPS não sobrevive à instalação Windows porque o `install.ps1` nunca escreve `APP_SSL_*`/`AUTH_COOKIE_SECURE` nem gera certificado (§8) — port da D4/027 anterior à 056.
2. Instalação nova com **MySQL nativo falha no `init_db`** por `0002` usar sintaxe MariaDB-only (§9/CS-1).
3. Whitelists de deploy divergentes; publicar pelo Linux remove `migrations/`+`scripts/` do PRO (§4/§5).
4. Residuais de editor commitados e publicados em produção (§5).

**Prováveis** (a confirmar na máquina real — §13):
5. Produção Windows atual roda sobre o MariaDB do XAMPP; o instalador a reutilizaria (CS-3) — e **moriria na etapa 1** por não achar o cliente (CS-3b).
6. `mariadb+pymysql` contra MySQL Server funciona, mas pode mascarar diferenças de dialecto (CS-2).
7. Atualizações de produção Windows hoje são feitas manualmente (git pull ad hoc) — sem procedimento documentado nem mecanismo (CS-5).

## 13. Pendências que exigem a máquina Windows real

- [ ] Estado real do serviço de banco na produção (XAMPP? MySQL nativo? versão exata — `Get-Service`, `mysql --version`).
- [ ] `.env` real da instalação atual (sem copiar segredos: apenas verificar chaves presentes/ausentes — `APP_SSL_*`?).
- [ ] Prova do erro do `0002` em MySQL real (teste controlado em banco de teste, **nunca em produção**).
- [ ] IP/hostname da LAN para SAN do certificado; validar cadeia com a CA em um cliente.
- [ ] Comportamento do Tarefa Agendada + TLS após reboot (validação SC-004).

## 14. Aprovação do responsável (gate T014)

- **2026-10-02 — APROVADO** (responsável, via gate interativo).
- Revisão 1: não aprovada — solicitação de aprofundamento do `install.ps1`/`uninstall.ps1`/Docker.
- Revisão 2 (aprofundamento com CS-3b e CS-5): **aprovada**. Libera a Fase 2 (listas de arquivos dos lotes HTTPS, MySQL/XAMPP e atualização) e a implementação (US2/US3).

## 15. Validação — lote US4/deploy (T029, parte local)

**2026-10-02 — simulação local do snapshot** (mesmos comandos do `deploy.sh`: `git -c core.autocrlf=false -c core.eol=lf archive` + filtro whitelist + `.gitkeep` de `data/`; executada contra a árvore de trabalho pós-T027 via índice temporário + `commit-tree` sem criar ref — **nenhum push, produção intocada**):

- [x] Raiz do snapshot = whitelist canônica exata: `app/`, `data/`, `docs/`, `scripts/`, `migrations/`, `.gitignore`, `README.md`, `requirements.txt`, `run.py`, `seed_demo.py`, `sistema_patrimonio.png`.
- [x] `scripts/gera_cert_dev.py` e `migrations/{alembic.ini, env.py, script.py.mako, versions/}` presentes (D-1 corrigido — publicar do Linux não degrada mais o PRO).
- [x] `SPEC-KIT-SISTEMA-ATUAL.md` ausente do snapshot; `.env`, residuais (`*~`/`*.un~`/`*-old`) e `data/ssl` ausentes (zero ocorrências).
- [x] `data/backups/.gitkeep` e `data/logs/.gitkeep` criados; `docs/` apenas `*.md`, sem `doc_provi*`.
- [x] **0 arquivos-texto com CRLF** no snapshot extraído (line endings determinísticos).
- [x] **`./deploy.sh pre` (somente leitura) validado em runtime**: conectividade OK com os 2 remotes (dev GitHub `b50f55f` sincronizada; PRO atual `8592ba5`, gerado da dev `b50f55f`); lista de pendências confere exatamente com o lote US4 aprovado; guard D-2 não disparou (residuais já removidos).
- [ ] **Pendência do operador (produção/Windows)**: (a) publicação real pelo `deploy.sh` (push para dev + snapshot no PRO — a publicação auto-commita a árvore pendente); (b) publicação equivalente pelo `deploy.bat` na máquina Windows e comparação dos snapshots; (c) `./deploy.sh rollback <hash-dev>` restaurando o PRO (com pull na produção de teste).
