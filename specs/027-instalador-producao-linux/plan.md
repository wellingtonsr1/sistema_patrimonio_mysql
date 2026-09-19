# Implementation Plan: Instalador Automatizado de Produção Linux

**Branch**: `027-instalador-producao-linux` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/027-instalador-producao-linux/spec.md`

## Summary

O SisPatrimônio Pro hoje exige 10+ passos manuais de instalação (README §"Instalação em uma máquina nova"). A feature entrega um **instalador automatizado, idempotente e seguro** para servidores Debian/Ubuntu — artefato único `install.sh` na **raiz do repositório** (decisão D1), em **bash estrito** (`set -Eeuo pipefail`, sem dependências além de `sudo`/`git`/`curl`). O instalador: valida pré-requisitos (sudo, base Debian + systemd, conectividade); assegura **Python ≥ 3.10** via `apt` (com **verificação pós-install** — `apt install python3` pode ser no-op em Debian antigo; se a distro não provê 3.10+, aborta com orientação, sem repositórios de terceiros); detecta **MariaDB **ou** MySQL** (D3 — reutiliza o que existir; instala MariaDB se nenhum); cria banco+usuário dedicados (utf8mb4, privilégios mínimos, senha coletada **sem eco** — banner `set +x` + sufixo no log — ou gerada); clona o repositório para `/opt/SisPatrimonioPro`; cria venv; instala `requirements.txt` **a partir do próprio repositório recém-clonado** (nunca de uma cópia antiga); gera o `.env` (0600, `DATABASE_URL` com senha percent-encoded via Python, `APP_HOST=0.0.0.0` — o default de código `192.168.0.9` é específico do operador e não deve vazar para novas instalações, `APP_PORT=8000`, `MYSQLDUMP_PATH` só quando o utilitário não está no PATH do serviço); instala unit systemd baseada no padrão real do README com **usuário dedicado não-root** (dependência do banco = serviço real detectado, `mariadb.service` ou `mysql.service`); inicia o serviço e valida por `/health` (`healthy`/`degraded`=WARNING, explicado). Idempotência total: banco existente **nunca** é apagado (recriação só via `--recreate-db` com dupla confirmação interativa, proibida em `--non-interactive`); `.env` existente é preservado; venv inválido é reconstruído (casa com a regressão da 019/026); **zero diff esperado em `app/`** (FR-001/SC-004). Regressão: suíte verde pré/pós (o instalador não pode quebrar nada existente).

## Technical Context

**Language/Version**: Bash 4.x+ (strix — `set -Eeuo pipefail`), GNU coreutils/sed/grep; Python 3 do sistema apenas como utilitário embutido (percent-encoding, geração de segredo, teste de conexão).

**Primary Dependencies**: Nenhuma nova para a **aplicação** (Constitution; stack intocado). Para o **host**: pacotes Debian/Ubuntu — `python3 python3-venv python3-pip git mariadb-server` (ou `default-mysql-server`), `ca-certificates curl`; utilitários presentes em toda base Debian (`find xargs awk pgrep install useradd getent sha256sum python3 curl git sudo`). Systemd (requisito NFR-001).

**Storage**: MariaDB/MySQL no próprio servidor (produção); arquivo único `install.sh`; `.env` no diretório da aplicação (0600); log do instalador `/var/log/sispatrimonio-install.log` (0600, fora do repositório — evita misturar com logs rotativos de `data/logs/`); unit systemd `sispatrimoniopro.service`.

**Testing**: pytest existente como **regressão** (suíte verde pré/pós — o instalador não pode quebrar nada) + **shellcheck** (se disponível — apt package `shellcheck`, opcional) + validação operacional real (quickstart). **Não** há testes unitários de bash no projeto — a validação do script é funcional (bateria de cenários do quickstart, executada por humano em VM/servidor de teste).

**Target Platform**: Linux server Debian/Ubuntu/derivadas diretas com systemd (NFR-001); MariaDB/MySQL local ou remoto (remoto via parâmetros, não fluxo primário).

**Project Type**: instalador de produção (script de deploy versionado na raiz) + documentação; aplicação web existente intocada.

**Performance Goals**: instalação limpa em minutos (NFR-003) — etapas dominantes são downloads de pacotes e `pip install`; progresso etapa a etapa.

**Constraints**: PROIBIDO alterar `app/` (zero diff — FR-001), `requirements.txt`, banco/schema (instalador não cria tabelas — FR-011), fluxo POST/RBAC/scheduler (SC-004). Sem Docker/supervisor/gunicorn/novos wrappers (NFR-004) — **uvicorn roda processo único** (documentado nas specs 017/019/020): multi-worker quebraria flags em memória (manutenção 019) e o scheduler-thread de backup (020). Sem compilação C (PyMySQL puro — NFR-002). Operações destrutivas exigem confirmação explícita (SR-004); senhas nunca em log/argv visível (SR-001).

**Scale/Scope**: 1 arquivo novo na raiz (`install.sh`, ~600–900 linhas com heredocs e funções de log/ajuda), 2 docs atualizadas (README §"Instalação em uma máquina nova" + GUIA), 0 alterações em `app/`. Modo interativo + modo não interativo (FR-015), `--recreate-db` restrito (D2).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência/Justificativa |
|---|---|---|
| I — Preservação/escopo | ✅ PASS | Alteração 100% aditiva: 1 script novo + docs; `app/` com zero diff esperado (SC-004); nenhuma refatoração |
| II — Camadas | ✅ PASS | Nenhuma regra de negócio nova — o instalador consome mecanismos existentes (`init_db()`, `create-user`, `/health`), não reinterpreta |
| III — Regras nos services | ✅ PASS | O instalador não implementa regra de negócio da aplicação; criação de admin delegada aos mecanismos reais (FR-020) |
| IV/V — Patrimônio/Inventário | ✅ PASS | Fora de escopo |
| VI — Segurança/credenciais | ✅ PASS | Senha do banco coletada sem eco (`set +x` + sufixo), gerada por `secrets` (crypto-secure, SR-002); nunca em log/argv (SR-001); `.env` 0600; serviço não-root (SR-003); `--recreate-db` só interativo com dupla confirmação (D2/SR-004) |
| VII — MariaDB/dados | ✅ PASS | Instalador NÃO cria schema (delega ao `init_db()` — FR-011); banco existente intocável sem `--recreate-db` explícito; utf8mb4; privilégios mínimos (SR-003) |
| VIII — Testes | ✅ PASS | Suíte pytest é a regressão pré/pós (zero diff esperado em `app/`); validação do script é funcional (quickstart); nenhum teste existente tocado |
| IX — Auditoria | ✅ PASS | Nenhuma operação de aplicação nova; sem eventos novos a registrar (o instalador não toca a trilha) |
| X — Interface | ✅ PASS | Nenhuma tela alterada |
| XI — Documentação fiel | ✅ PASS | README + GUIA atualizados na mesma tarefa (FR-021) para referenciar o instalador; fluxo manual permanece como alternativa |
| XII — Spec + validação | ✅ PASS | Fluxo Spec Kit; validação = shellcheck (se disponível) + suíte pré/pós + cenários operacionais do quickstart em VM limpa |

**Veredito inicial**: ✅ PASS (sem violações — feature aditiva, fora de `app/`).

**Re-check pós-Phase 1**: ✅ PASS — artefatos confirmam: bash estrito com falha-fácil (consistente com SR-005), zero diff em `app/` preservado, privilégios de banco sem globais (SR-003), `EnvironmentFile` citado na unit (SR-001 — a aplicação lê o `.env` de forma privada), `--recreate-db` restrito a modo interativo com dupla confirmação (D2). Nenhuma violação a registrar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/027-instalador-producao-linux/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── installer-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
# ARQUIVOS A CRIAR (esperado):
install.sh                  # instalador único na raiz (D1): funções de log/validação,
                            # detecção, pacotes, banco, clone, venv, .env, unit, health

# ARQUIVOS A ATUALIZAR (FR-021):
README.md                   # §"Instalação em uma máquina nova": referência ao instalador + parâmetros
docs/GUIA_DE_MANUTENCAO.md  # seção operacional (requisitos do servidor, gerenciamento do serviço)

# INTOCADOS (SC-004 — qualquer diff aqui exige justificativa no relatório):
app/**                      # TODA a aplicação (FR-001): config, services, models, web, templates
requirements.txt            # dependências existentes (instalador consome, não duplica)
tests/**                    # suíte existente intocada (regressão pré/pós)
seed_demo.py                # fora do escopo (drop_all — exclusivo de banco de demo)

# APENAS LIDOS (referências):
run.py                      # ExecStart = python run.py via venv (processo único — sem gunicorn)
app/config.py               # DATABASE_URL obrigatória; APP_HOST/APP_PORT; AUTH_ADMIN_*; AD_*
app/database.py             # init_db() idempotente (instalador não cria schema)
app/main.py                 # /health (healthy/degraded); lifespan (init_db + admin + scheduler)
app/cli.py                  # mecanismo real do 1º admin (create-user)
app/logging_config.py       # logs da aplicação em data/logs/ (dono = usuário do serviço)
specs/017/019/020           # processo único — proíbe gunicorn/multi-worker na unit
.env.example                # referência de variáveis (MYSQLDUMP_PATH/BACKUP_IMPORT_TIMEOUT)
.gitignore                  # .env já bloqueado; install.log fora do repo (/var/log)
```

**Structure Decision**: Feature de deploy aditiva — 1 script na raiz + 2 docs. Nenhuma estrutura nova, nenhuma alteração em `app/`. O instalador adapta-se ao sistema existente (Constitution I).

## Complexity Tracking

> Sem violações de Constitution — seção vazia (nada a justificar).

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
