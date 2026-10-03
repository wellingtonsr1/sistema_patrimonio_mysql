# Implementation Plan — Feature 061 (auditoria e padronização do ecossistema SisPatrimônio Pro)

**Branch**: `061-auditoria-padronizacao-ecossistema` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification de `/specs/061-auditoria-padronizacao-ecossistema/spec.md` + 5 clarificações do responsável (2026-10-02, seção Clarifications da spec).

## Summary

Auditar (Fase 1, **somente leitura**) todo o ecossistema — dev (`sistema_patrimonio_mysql`, este repositório), snapshot PRO (`SisPatrimonioPro`), `deploy.sh`/`deploy.bat`, `install.sh` e o instalador Windows versionado — e corrigir, com alterações mínimas e cirúrgicas, as divergências que fazem o HTTPS se perder na instalação Windows e o Windows depender de XAMPP, padronizando MariaDB/MySQL exclusivamente por configuração (`DATABASE_URL`). A referência funcional é o baseline da dev (HTTPS nativo no Uvicorn da 056, **porta 8000**, sem redirect — decisões da spec D-002/D-006). A execução começa pela **Fase 1 — Diagnóstico** (relatório aprovado é o checkpoint para qualquer mudança), seguida de planejamento com lista de arquivos (contrato), implementação por lotes com suíte verde, validação nos 4 cenários e validação ponta a ponta do deploy.

## Technical Context

**Language/Version**: Python 3.10+ (aplicação, `run.py`); Bash (deploy.sh / install.sh / uninstall.sh); Batch/CMD (`deploy.bat`, `test.bat`) e PowerShell (diagnóstico Windows); Git 2.x
**Primary Dependencies**: FastAPI + Uvicorn (SSL nativo — 056), SQLAlchemy 2 + PyMySQL, python-dotenv; `openssl` CLI (CA + certificado, `scripts/gera_cert_dev.py`); systemd (Linux); serviço Windows do instalador (mecanismo a confirmar na Fase 1)
**Storage**: MariaDB (Linux) / MySQL Server nativo (Windows) via `mariadb+pymysql` / `mysql+pymysql`; SQLite restrito à suíte de testes (Constitution VII)
**Testing**: pytest — runner oficial `test.bat` no Windows (venv `Scripts\python.exe`); `.venv` no Linux; baseline da 056: 889 passed
**Target Platform**: Linux (Debian/Ubuntu + systemd) e Windows (dev e produção)
**Project Type**: web-service + scripts de deploy/instalação (ecossistema multiplataforma)
**Performance Goals**: n/a (infra) — instalação limpa completa em minutos (NFR-003 da 027); health check com timeout 120 s
**Constraints**: zero regressão da suíte (SC-001); zero segredo em Git/logs/argv (SC-009); sem XAMPP (SC-005); dados de produção intocáveis (FR-011); alterações limitadas à lista da Fase 2 (D-005); alterações de comportamento só as previstas na spec (Constitution I)

## Constitution Check

*GATE: avaliado antes da Fase 0 e re-avaliado após a Fase 1 (design).*

| Princípio | Status | Aplicação nesta feature |
|---|---|---|
| I — Preservação do existente | ✅ PASS | Fase 1 somente leitura; D-005 (lista de arquivos como contrato); nenhuma refatoração não relacionada |
| II/III — Camadas e services | ✅ N/A-PASS | Nenhuma alteração de app prevista; se o diagnóstico apontar necessidade, entra na Fase 2 com justificativa |
| IV/V — Movimentações e inventário | ✅ N/A-PASS | Sem alteração de regras de negócio |
| VI — Segurança | ✅ PASS | Nenhum segredo em Git/logs/argv (FR-026); `AUTH_COOKIE_SECURE=true` escrito pelo instalador apenas quando ativa TLS (FR-020) |
| VII — Banco e dados | ✅ PASS | Sem migração destrutiva; instaladores não criam schema (delegam a `init_db()`); banco existente intocável (FR-011, FR-017) |
| VIII — Testes | ✅ PASS | Baseline antes/depois (FR-003); suíte verde por lote; `test.bat` como runner oficial no Windows |
| IX/X — Auditoria de app e UI | ✅ N/A-PASS | Sem alteração de trilhas/rotas/telas previstas |
| XI — Documentação fiel | ✅ PASS | Docs atualizadas na mesma tarefa (FR-029); instruções XAMPP removidas |
| XII — Spec-driven | ✅ PASS | Este fluxo: specify → clarify → plan → tasks → implement |

**Violações**: nenhuma. Re-check pós-design (Fase 1): nenhuma complexidade nova introduzida — sem dependências novas, sem código de app alterado além do previsto (D-002 mantém o comportamento da 056); firewall/cookie são artefatos de instalador/`.env`, não código de aplicação.

## Plano de execução (a Fase 1 vem primeiro — pedido do responsável)

### Fase 1 — Diagnóstico (somente leitura; checkpoint obrigatório)

Entregável: `docs/` ou `specs/061.../diagnostico.md` (decidir local na tasks; conteúdo = Entregável A da spec). Atividades e comandos-base:

1. **Inventário da dev**: `git status/branch -a/remote -v/log --oneline -30/diff --stat`; varredura `xampp|XAMPP` (no versionado: **0 ocorrências já confirmadas no plan**; reconfirmar em arquivos ignorados e na máquina Windows), `mariadb|mysql+pymysql|DATABASE_URL|APP_SSL|APP_PORT|AUTH_COOKIE_SECURE|uvicorn|nginx|apache|systemd`.
2. **Residuais da dev** (já identificados no plan, a classificar): `app/config.py~` (backup do editor com defaults antigos `APP_HOST=10.39.0.16`), `..env.un~`, `uninstall.sh-old`, `_teste_smtp_direto.py`, `mnt/backup-sispatrimoniopro/` (mount vazio).
3. **Snapshot PRO e repositório de instalação**: clonar/obter `git@github.com:wellingtonsr1/SisPatrimonioPro.git` (leitura) e comparar com a whitelist real de `deploy.sh`/`deploy.bat` (extraída no plan, §research F1): PRO recebe **apenas** `app/`, `data/` (com `.gitkeep` em backups/logs), `docs/*.md` (sem `doc_provi*`), `.gitignore`, `README.md`, `requirements.txt`, `run.py`, `seed_demo.py`, `sistema_patrimonio.png` — **não** recebe `specs/`, `tests/`, `scripts/`, `install.sh`, `deploy.*`, `test.bat`, Docker. Verificar: (a) algo necessário à produção fora da whitelist; (b) equivalência `.sh` × `.bat`; (c) paridade com o **terceiro repositório** `SisPatrimonioPro-install` (localizado: `~/IA/SisPatrimonioPro-install`; `install no linux/nativa/install.sh` já confirmado **idêntico** à dev; `install.ps1` 982 linhas sem SSL/cert — research F5).
4. **Baseline HTTPS da dev**: rastrear `run.py` → `app/config.py` (`APP_SSL_CERTFILE`/`APP_SSL_KEYFILE` + `_normaliza_caminho_cert`) → `scripts/gera_cert_dev.py` (CA + SAN IP/localhost/sispatrimoniopro.local, `data/ssl/` fora do Git) → `.env` real (na máquina) → serviço; comparar com o que o instalador Windows produz (causa raiz da perda do HTTPS — FR-018).
5. **Banco**: auditar `app/config.py`/`database.py`/models/`init_db` (engine, pool, charset, DDL idempotente) e preencher a matriz MariaDB × MySQL (Entregável B) a partir do código.
6. **Baseline de testes**: executar a suíte completa e registrar o resultado (comando no quickstart.md).
7. **Ambientes**: comandos Windows (`Get-Service`, `mysql --version`, `where.exe mysql`, `Get-NetFirewallRule`) e Linux (`systemctl`, `mariadb --version`, `which mysql`) conforme disponibilidade real.

**Checkpoint**: relatório de diagnóstico revisado pelo responsável → libera a Fase 2. Nenhum arquivo funcional modificado (`git status` limpo ao fim).

### Fase 2 — Planejamento (contrato de arquivos)

Lista **Alterar / Criar / Remover / Não alterar** com justificativa (Entregável D), a partir do diagnóstico. Critérios: alterações mínimas; nenhuma segunda implementação de HTTPS (D-003); instalador Windows corrigido no próprio arquivo versionado (D-004); docs afetadas listadas (FR-029).

### Fase 3 — Implementação (lotes cirúrgicos)

Lotes pequenos, cada um terminando com suíte verde (SC-001). Ordem provável (ajustada pela Fase 2): (1) causa raiz do HTTPS no instalador Windows; (2) MySQL nativo sem XAMPP + firewall auto + `AUTH_COOKIE_SECURE`; (3) paridade das whitelists `.sh`×`.bat` e conteúdo do snapshot; (4) `DATABASE_URL` percent-encoding e compatibilidade MariaDB/MySQL nos pontos apontados pela matriz; (5) idempotência/segurança dos instaladores; (6) documentação (remoção XAMPP obsoleto).

### Fase 4 — Validação (quickstart.md)

Matriz completa: dev/prod × Linux-MariaDB/Windows-MySQL + instalação limpa, atualização, reinstalação, banco existente/inexistente, HTTPS após reboot/reinício/atualização/reinstalação (SC-003/SC-004), varredura de segredos (SC-009).

### Fase 5 — Deploy ponta a ponta

`deploy.sh` e `deploy.bat` publicando a mesma dev com snapshots equivalentes (SC-007); instalação a partir do PRO comprovando o fluxo completo (FR-028).

## Project Structure

### Documentation (this feature)

```text
specs/061-auditoria-padronizacao-ecossistema/
├── plan.md                     # este arquivo
├── research.md                 # Fase 0 — decisões e fatos verificados
├── data-model.md               # Fase 1 — entidades de infraestrutura do ecossistema
├── quickstart.md               # Fase 1 — guia de validação por fase
├── contracts/
│   └── ecossistema-contratos.md  # Fase 1 — contratos estáveis (snapshot PRO, .env, serviço)
├── checklists/requirements.md  # da specify/clarify
└── spec.md
```

### Source Code (repository root)

```text
app/
├── config.py               # APP_HOST/APP_PORT(8000)/APP_SSL_*/AUTH_COOKIE_SECURE — referência do baseline
└── ...                     # (nenhuma alteração prevista; se o diagnóstico apontar, entra na Fase 2)
run.py                      # uvicorn + ssl_certfile/ssl_keyfile quando envs definidos (056)
scripts/
└── gera_cert_dev.py        # CA + cert SAN (openssl CLI) → data/ssl/ (fora do Git)
data/ssl/                   # certificados/chaves — NUNCA versionados (FR-025)
deploy.sh | deploy.bat      # publicar/pre/historico/rollback — whitelist a auditar (research D3)
install.sh | uninstall.sh   # instalador Linux 027 (1198 linhas, 15 etapas, idempotente)
test.bat                    # runner pytest oficial no Windows
docs/                       # HTTPS_LOCAL.md e afins — atualização na Fase 3/6
mnt/, TASKS/, *_~, *-old    # residuais a classificar no diagnóstico
specs/027-instalador-producao-linux/contracts/installer-contract.md  # contrato do instalador Linux (referência)
```

**Structure Decision**: projeto único (padrão da casa) — nenhum componente novo de aplicação; novos artefatos desta feature vivem em `specs/061.../`; o instalador Windows já está localizado no **terceiro repositório** `SisPatrimonioPro-install` (checkout `~/IA/SisPatrimonioPro-install`; `install no windows/nativa/install.ps1`, 982 linhas, PowerShell, serviço via Tarefa Agendada) e é corrigido **nele** (D-004), com a alteração espelhada/registrada para o fluxo dev→GitHub; o `install no linux/nativa/install.sh` do mesmo repo está **idêntico** ao `install.sh` da dev (auditar sincronização após a Fase 3). Contrato do instalador Linux segue o padrão da 027 (`contracts/installer-contract.md`).

## Complexity Tracking

> Nenhuma violação de Constitution a justificar — seção vazia por design (sem novos projetos, sem padrões extras, sem dependências novas).
