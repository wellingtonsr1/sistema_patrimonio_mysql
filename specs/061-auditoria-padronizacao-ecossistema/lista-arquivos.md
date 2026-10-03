# Listas de arquivos — Fase 2 (Feature 061)

**Contrato**: esta lista é o contrato da Fase 3 (decisão D-005 da spec). Qualquer arquivo fora dela exige atualização da lista **antes** da mudança. Base: `diagnostico.md` (revisão 2, aprovado em T014).

---

## §HTTPS — lote US2 (T015)

**Objetivo**: reproduzir o baseline HTTPS da 056 (contrato C2) nos dois instaladores — TLS na porta da aplicação (8000), `AUTH_COOKIE_SECURE=true`, firewall, sem segunda implementação, sem redirect.

### Alterar

| # | Arquivo | Mudança |
|---|---|---|
| H-1 | `SisPatrimonioPro-install/install no windows/nativa/install.ps1` | (a) nova função `Ensure-Certificates` após `Ensure-Venv`: localizar `openssl` (PATH → `C:\Program Files\Git\usr\bin\openssl.exe` — o próprio instalador instala Git) e executar `.venv\Scripts\python.exe scripts\gera_cert_dev.py` (idempotente; `--force` apenas com nova flag `-RegenerateCert`); validar `data\ssl\server.crt`/`server.key`; (b) `Ensure-EnvFile`: incluir `APP_SSL_CERTFILE=data/ssl/server.crt`, `APP_SSL_KEYFILE=data/ssl/server.key` (caminhos relativos — normalização 056 resolve contra `BASE_DIR`, portável) e `AUTH_COOKIE_SECURE=true` no `.env` novo; em `.env` existente, apenas completar chaves ausentes com consentimento (jamais sobrescrever); (c) health check e bateria pós-instalação passam a `https://127.0.0.1:$AppPort/health` com bypass local de validação de certificado (PS 5.1: `ServerCertificateValidationCallback` — sonda local, SAN não tem 127.0.0.1); (d) resumo final em `https://` + instrução de importar `data\ssl\ca.crt` nos clientes (1×); (e) firewall: manter regra idempotente e corrigir regra órfã ao mudar a porta (D-12) |
| H-2 | `SisPatrimonioPro-install/install no linux/nativa/install.sh` | Mesmo contrato C2: etapa de certificado (venv python `scripts/gera_cert_dev.py`; openssl nativo Debian/Ubuntu), `.env` com `APP_SSL_*` + `AUTH_COOKIE_SECURE=true`, health `curl -k https://127.0.0.1:$APP_PORT/health` (L966/1069), resumo `https://` (L1093) e **etapa de firewall nova** (decisão A do clarify: `ufw allow 8000/tcp` quando ufw ativo; best-effort com AVISO senão — hoje não existe etapa de firewall) |
| H-3 | `sistema_patrimonio_mysql/install.sh` (dev) | **Sincronizar** com H-2 (arquivos gêmeos desde a 027; `diff` vazio hoje — manter idênticos) |
| H-4 | `SisPatrimonioPro-install/README.md` e `install no windows/TROUBLESHOOTING.md` | Seções HTTPS: geração, importação da CA nos clientes (1×), regeneração (`--force`), novos sintomas de TLS (FR-029) |

### Criar

- Nada. (Reuso integral do mecanismo 056 — proibida segunda implementação; D-003.)

### Remover

- Nada.

### Não alterar

- `scripts/gera_cert_dev.py` (dev) — reutilizado sem modificação.
- `run.py`, `app/config.py`, `app/` — baseline intocado.
- `uninstall.ps1`/`uninstall.sh` — `data/ssl/` já coberto pela remoção opt-in do diretório.
- Whitelists de deploy (`deploy.sh`/`deploy.bat`) — lote US4 (T027), fora deste lote.

---

## §MySQL/XAMPP/Atualização — lote US3 (T021)

**Objetivo**: `Windows → MySQL Server nativo → SisPatrimônio Pro` sem XAMPP; matriz MariaDB×MySQL sem célula quebrada; fluxo de atualização existente (CS-5).

### Alterar

| # | Arquivo | Mudança |
|---|---|---|
| M-1 | `sistema_patrimonio_mysql/migrations/versions/0002_migracoes_legadas_idempotentes.py` | Tornar compatível com MariaDB **e** MySQL: detectar o dialecto (MariaDB vs MySQL via versão do servidor) e, em MySQL, executar os ALTER condicionalmente via `information_schema` (coluna/índice existe?) em vez de `IF NOT EXISTS`; idempotência preservada nos dois bancos; `0001` intocado |
| M-2 | `SisPatrimonioPro-install/install no windows/nativa/install.ps1` | (a) `Build-DatabaseUrl` (L636–648): detectar o servidor real (`SELECT VERSION()`) e escrever `mysql+pymysql://` para MySQL Oracle, `mariadb+pymysql` para MariaDB (hoje fixo em L640); (b) SGBD nativo: quando nenhum serviço adequado existir, instalar **MySQL Server nativo** (winget — id a confirmar na implementação) em vez de MariaDB; **guard XAMPP**: se o serviço detectado aponta para binário em `C:\xampp`, NÃO reutilizar — avisar e instalar nativo (FR-013; hoje reutilizaria — CS-3); (c) implementar `-Update` (CS-5): `git fetch` + `pull --ff-only` (aborta com aviso se árvore suja — nunca reverter código), `pip install -r` idempotente, parada da tarefa, `init_db()` (migrações), start + health, bateria — `.env` e dados intocados |
| M-3 | `SisPatrimonioPro-install/install no linux/nativa/install.sh` + `sistema_patrimonio_mysql/install.sh` (dev) | Espelhar o `-Update` como `--update` (mesmo fluxo Linux: fetch/pull --ff-only, pip, init_db, restart systemd, health); scheme da URL já é MariaDB no Linux (documentar) |
| M-4 | `SisPatrimonioPro-install/README.md` | Seção "Atualização" (fluxo `-Update`/`--update`), faixa de versões suportadas (MySQL 8.0+; MariaDB 10.5+), XAMPP não suportado como banco do sistema (FR-013) |
| M-5 | `sistema_patrimonio_mysql/requirements.txt` | **Emenda (2026-10-02, fluxo D-005 — incluída à lista ANTES da mudança)**: adicionar `cryptography>=42.0.0`. O MySQL 8 (Oracle) autentica por `caching_sha2_password` e o PyMySQL exige `cryptography` quando a conexão com o banco não usa TLS (os instaladores não configuram TLS no banco) — sem o pacote, `mysql+pymysql` falha no login com senha correta. Não usada no caminho MariaDB (inócua). Requisito do lote M-2 (MySQL nativo no Windows) |

### Criar

- Nada neste lote (o teste de contrato do snapshot `tests/test_deploy_snapshot.py` é do lote US4/T028).

### Remover

- `SisPatrimonioPro-install/backup-$` — residual obsoleto (D-10; arquivo de 6 bytes sem função).

### Não alterar

- `app/` inteiro **exceto** `migrations/versions/0002...py` (M-1) — regras de negócio, rotas, models, serviços intocados.
- Dados de produção, `.env` de máquinas, credenciais — nunca.
- Whitelists de deploy (lote US4) e variantes Docker (documentadas como alternativas).

---

## Pendências de validação (máquina Windows real — §13 do diagnóstico)

Bloqueiam a **validação** (Fase 4), não a implementação: prova do 0002 em MySQL real (banco de teste), versão/estado do serviço de banco, IP/hostname para SAN, HTTPS pós-reboot (SC-004).

## Riscos do lote

| Risco | Mitigação |
|---|---|
| openssl ausente/fora do PATH no Windows | instalador já instala Git; localizar em `Git\usr\bin`; mensagem clara se não achar |
| `AUTH_COOKIE_SECURE=true` com HTTPS inoperante quebraria login | TLS é ativado na mesma instalação; `.env.example` documenta o risco; health https prova o TLS antes do resumo |
| `-RegenerateCert` apagando cert válido | default idempotente (sem `--force` não regenera); reinstalação reutiliza cert válido (FR-022) |
| `pull --ff-only` falhando em clone divergido | aborta com aviso (nunca força; nunca reverte alterações locais) |
| MySQL winget id incorreto | confirmar na implementação; fallback: orientar instalação manual e reexecutar (idempotência) |

---

## §Deploy — lote US4 (T026)

**Objetivo**: `deploy.sh` e `deploy.bat` publicam snapshots **equivalentes** para a mesma dev — tudo que a produção precisa e nada indevido (contrato C1, FR-015). Base: diagnostico.md §5 (T008) e D-1/D-2.

### Alterar

| # | Arquivo | Mudança |
|---|---|---|
| DE-1 | `sistema_patrimonio_mysql/deploy.sh` | (a) whitelist **INCLUI** `scripts` e `migrations` nos 2 filtros (publicar + rollback) — hoje o `.sh` os apagaria do PRO (D-1: publicar do Linux degrada produção; `gera_cert_dev.py` é pré-requisito do contrato C2 e `migrations/` do versionamento 052); (b) whitelist **EXCLUI** `SPEC-KIT-SISTEMA-ATUAL.md` (documento interno de specs — nada indevido em produção); (c) line endings determinísticos: `git -c core.autocrlf=false -c core.eol=lf archive` nos 2 pontos (publicar + rollback) — snapshot idêntico publicado do Linux ou do Windows; (d) guard de residuais: se a árvore rastreada contiver `*~`/`*.un~`/`*-old`, abortar com lista (D-2) |
| DE-2 | `sistema_patrimonio_mysql/deploy.bat` | Espelho exato de DE-1: incluir `scripts`/`migrations`, excluir `SPEC-KIT-SISTEMA-ATUAL.md`, `git -c core.autocrlf=false -c core.eol=lf archive` nos 2 filtros, guard de residuais — equivalência `.sh` ≡ `.bat` (SC-007) |

### Criar

| # | Arquivo | Conteúdo |
|---|---|---|
| DE-3 | `sistema_patrimonio_mysql/tests/test_deploy_snapshot.py` | Teste de contrato do snapshot (padrão da casa, T028): (a) keep-list de diretórios `.sh` ≡ `.bat` (parse dos filtros dos dois scripts); (b) keep-list de arquivos idem; (c) flags de line endings presentes nos dois (publicar + rollback); (d) proibidos ausentes dos keep-lists: `.env`, `specs`, `tests`, `.venv`, `data/ssl` (e `.gitignore` da dev cobre `data/ssl/` e certificados — T018); (e) essenciais presentes: `app/`, `run.py`, `requirements.txt`, `README.md`, `scripts/`, `migrations/` nos keep-lists **e** na dev real; (f) residuais: `git ls-files` da dev sem nenhum `*~`/`*.un~`/`*-old` (valida D-2 na origem) |

### Remover (da dev — residuais D-2; param de existir no repositório e, portanto, nos snapshots)

- `..env.un~` (raiz) · `_teste_smtp_direto.py` (raiz) · `app/.config.py.un~` · `app/config.py~` · `uninstall.sh-old` (raiz). Todos rastreados hoje; os 2 em `app/` atravessam a whitelist e já foram publicados no PRO (diagnóstico §5). Sem função — lixeira de editor/teste ad-hoc.

### Não alterar

- `app/` (regras de negócio), `.gitignore` (já cobre `data/ssl/`, `.env`, certificados — T018), `run.py`, `seed_demo.py`, `sistema_patrimonio.png` (permanecem na whitelist), instaladores (lotes anteriores), variantes Docker.
- `data/` — snapshot leva apenas `.gitkeep` de `backups/` e `logs/` (dados de produção NUNCA — Constitution VII).
- Classificações aprovadas: `.env.example` **não** entra no snapshot (instalador gera o `.env` completo; referência permanece na dev); `docs/` mantém o filtro atual (só `*.md`, exceto `doc_provi*`); `SPEC-KIT-SISTEMA-ATUAL.md` sai da whitelist (some do PRO na próxima publicação — 1 commit full replace).

### Riscos do lote

| Risco | Mitigação |
|---|---|
| Próxima publicação apaga `SPEC-KIT-SISTEMA-ATUAL.md` do PRO | é o comportamento desejado (full replace); rollback recria via `git archive` da dev antiga se necessário |
| Guard de residuais bloqueando publicação legítima | padrão restrito a sufixos óbvios (`~`, `.un~`, `-old`); falso-positivo: renomear o arquivo |
| Windows sem `git -c` (versão antiga) | suportado desde git 1.x; deploy.bat já exige git moderno (winget) |
| scripts/ contendo algo indevido no futuro | teste de contrato (DE-3) + guard varrem a árvore antes do push |
