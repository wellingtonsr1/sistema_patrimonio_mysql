---
description: "Task list for feature 027 — Instalador Automatizado de Produção Linux"
---

# Tasks: Instalador Automatizado de Produção Linux

**Input**: Design documents from `/specs/027-instalador-producao-linux/`

**Prerequisites**: plan.md ✅ | spec.md ✅ (decisões D1–D4 registradas) | research.md (R1–R15) | data-model.md | contracts/installer-contract.md | quickstart.md

**Tests**: A suíte pytest é **regressão** (zero diff em `app/` — FR-001); a validação do `install.sh` é **funcional** (quickstart — cenários [OPERADOR] em VM limpa, marcados como tais). Nenhum teste de bash é criado.

**Organization**: Tarefas por user story. ⚠️ Quase todas as tarefas de código editam o **mesmo arquivo** (`install.sh`) → executar em ordem sequencial; apenas as tarefas de documentação são paralelizáveis entre si.

## Format: `[ID] [P?] [Story] Description`

- [x] T001 Capturar baseline de regressão: `pytest -q` verde pré-implementação e `git status --porcelain` limpo (nenhum diff pendente em `app/`/`tests/`); registrar contagens em Validation Results para comparação final (contract §2 — zero diff em `app/`)

## Phase 2: Foundational (bloqueia todas as stories — todas em `install.sh`)

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase. Nenhuma mutação no servidor durante o desenvolvimento (briefing: análise/spec → implementação do artefato; execução real só em VM).

- [x] T002 Criar esqueleto `install.sh` na raiz (decisão D1): bash estrito (`set -Eeuo pipefail`, `IFS=$'\n\t'`), `umask 027` global e janelas `umask 077` para segredos, trap ERR (etapa+linha+orientação de reexecução — FR-019), funções de log `[ * ]/​[OK]/[!!]/[XX]` gravando em `/var/log/sispatrimonio-install.log` (0600, `exec > >(tee ...) 2>&1` — R1/R2), verificação de utilitários mínimos via `command -v` (fail-fast — SR-005), chmod +x
- [x] T003 Implementar em `install.sh` o parser/validação de CLI (contract §1): todas as flags (`--non-interactive --install-dir --repo --branch --db-name --db-user --db-password --generate-db-password --app-host --app-port --service-name --service-user --recreate-db --update --help`) com defaults de `data-model §1.1`; validação TOTAL antes da primeira mutação (FR-015): identificadores SQL `[a-zA-Z_][a-zA-Z0-9_]*`, porta 1–65535, senha manual ≥ 12, obrigatórios do modo não interativo listados quando ausentes; **guardas**: `--recreate-db` + `--non-interactive` → exit 2 ANTES de qualquer mutação (D2); `--update` → mensagem "ainda não implementado" + exit 2 (NFR-005); modo interativo: prompts com defaults + coleta de senha SEM eco (`read -rs` 2×, janela `set +x`, prompt gravado no log ANTES do read — R2) e confirmação final do resumo antes da 1ª mutação (R12); `-r` a coleta NUNCA ecoa a senha

## Phase 3: User Story 1 — Instalação limpa ponta a ponta (Priority: P1) 🎯

**Goal**: `sudo bash install.sh` em servidor Debian/Ubuntu limpo prepara tudo e termina com serviço saudável + resumo (spec US1).

**Independent Test**: quickstart Passo 3 [OPERADOR] — instalação em VM limpa termina com `/health` OK e resumo completo.

- [x] T004 [US1] Implementar em `install.sh` os gates de pré-requisitos (FR-002): sudo/EUID, distro base Debian via `/etc/os-release` (`ID`/`ID_LIKE`), systemd presente, conectividade (git ls-remote do repo + repositórios apt); falha → mensagem clara e abort sem mutação (SR-005)
- [x] T005 [US1] Implementar em `install.sh` a detecção de host (data-model §1.2): versão do Python via `python3 -c` (R3), git, SGBD por serviço/utilitários reais — `systemctl is-active mariadb.service || mysql.service` + `command -v mysqldump mysql` (D3/R4), porta `$APP_PORT` em uso (`ss -ltn`); resultados em variáveis `HAS_*` usados por todas as etapas seguintes
- [x] T006 [US1] Implementar em `install.sh` a etapa de pacotes (FR-003/FR-004/FR-005): instalar `python3 python3-venv python3-pip` apenas se versão < 3.10 ou ausentes, com **re-verificação da versão após o apt** (no-op do Debian antigo → abort com orientação — R3); `git` se ausente; **MariaDB** (`mariadb-server`) somente se NENHUM servidor (MariaDB/MySQL) detectado em T005 (D3); garantir serviço do banco ativo/habilitado (sem desconfigurar existente)
- [x] T007 [US1] Implementar em `install.sh` a etapa de banco (FR-006/FR-007): criar banco `utf8mb4`/`utf8mb4_unicode_ci` e usuário dedicado com `GRANT ALL PRIVILEGES ON <db>.* ` (somente no banco da aplicação — SR-003); SQL via cliente com senha em `MYSQL_PWD` no ambiente do processo (NUNCA argv — R5); teste de conexão real via engine do projeto no venv (`SELECT 1` + `SELECT DATABASE()`) após o venv existir (reordenar: conexão validada após T008 criar o venv, antes do `.env` final)
- [x] T008 [US1] Implementar em `install.sh` clone + venv (FR-008/FR-009, estados R7/R8): `git clone --branch $BRANCH --single-branch` para `$INSTALL_DIR` (default `/opt/SisPatrimonioPro`); venv via python do sistema; `pip install -r $INSTALL_DIR/requirements.txt` **a partir do repositório clonado**; validação final = imports do README (`fastapi sqlalchemy pymysql ldap3 reportlab openpyxl dotenv`)
- [x] T009 [US1] Implementar em `install.sh` a geração do `.env` (FR-010/R6): `umask 077` → 0600 por construção; `DATABASE_URL` com percent-encoding via `urllib.parse.quote_plus`, `APP_HOST=0.0.0.0`, `APP_PORT`, `MYSQLDUMP_PATH` apenas quando `command -v mysqldump` falhar; `AUTH_ADMIN_PASSWORD` gerada e exibida 1× somente se o admin escolher a via env (FR-020)
- [x] T010 [US1] Implementar em `install.sh` usuário/permissões/unit systemd (FR-012/R9/R10): system user `sispatrimonio` (`useradd --system --no-create-home --shell /usr/sbin/nologin`) + grupo; `chown -R` do diretório (aplicação escreve `data/logs/`+`data/backups/`); unit gerada do padrão real do README com `After=network-online.target <serviço-detectado>` (`mariadb.service` ou `mysql.service`), `EnvironmentFile`, `ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/run.py`, `Restart=on-failure`, `WantedBy=multi-user.target`; `daemon-reload` + `enable` (sem start ainda)
- [x] T011 [US1] Implementar em `install.sh` start + health (FR-013/R11): `systemctl start`, espera ativa até 90 s de `curl -fsS http://127.0.0.1:$APP_PORT/health` com parse de `status`; `healthy` = OK; `degraded` = WARNING com explicação (aplicação no ar); timeout → `journalctl -u $SERVICE -n 50 --no-pager` no log do instalador + falha clara (sem segredos)
- [x] T012 [US1] Implementar em `install.sh` a bateria pós-instalação + resumo final (FR-014/R14): checagens (python/venv/imports, banco ativo, conexão, tabela base existente via query do venv, unit ativa/enabled, HTTP `/health`) e resumo (URL, `/docs`, `/health`, caminhos, comandos `systemctl` do serviço real, local do `.env` e do log, instruções do 1º admin pelos 3 mecanismos reais — CLI recomendado; SEM exibir a senha do banco — SR-001)

**Checkpoint**: US1 independente — quickstart Passo 3 valida ponta a ponta.

## Phase 4: User Story 2 — Idempotência e reinstalação segura (Priority: P1)

**Goal**: 2ª execução reutiliza tudo, não destrói nada, termina consistente (spec US2; briefing §11).

**Independent Test**: quickstart Passo 4 [OPERADOR] — hash do `.env` e contagem de usuários inalterados após 2ª execução.

- [x] T013 [US2] Revisar cada etapa do `install.sh` para os caminhos de reuso (FR-018; R7/R8/R6/R9): clone válido → reutilizar e reportar HEAD; diretório não-vazio sem `.git` → ABORTAR pedindo decisão; alterações locais (`git status --porcelain`) → WARN sem `reset --hard`; venv válido (python+pip+imports) → reutilizar, inválido → remover e recriar (artefato regenerável); banco existente → INTOCÁVEL (validar + completar grants se faltando; DROP só com `--recreate-db` — R13 dupla confirmação: aviso destacado + nome do banco digitado 2×, exclusivamente do banco nomeado); usuário do banco existente → reutilizar (senha só com confirmação explícita); `.env` existente → NUNCA sobrescrever (backup `.env.bak-<ts>` + oferta de completar chaves ausentes); unit → reescrita somente se conteúdo difere (hash antes/depois)

## Phase 5: User Story 3 — Modo não interativo (Priority: P2)

**Goal**: instalação completa sem nenhum prompt; falha clara e sem parcialidade nos faltantes (spec US3; contract §1).

**Independent Test**: quickstart Passo 5 [OPERADOR] — instalação sem prompts; faltantes → exit 2 listado; guardas respeitadas.

- [x] T014 [US3] Garantir em `install.sh` o caminho `--non-interactive` ponta a ponta (FR-015/R12): nenhuma leitura de stdin no fluxo não interativo (todos os prompts condicionados); senha via `--db-password` ou `--generate-db-password` (`secrets.token_urlsafe(24)`); validação total na T003 já executada ANTES da primeira mutação; instalação com parâmetros em diretório/porta customizados flui idêntica ao interativo
- [ ] T015 [P] [US3] [OPERADOR] Executar quickstart Passo 5 em VM: `--non-interactive` sem obrigatórios → exit 2 listando faltantes; `--recreate-db --non-interactive ...` → exit 2 ANTES de qualquer mutação; instalação completa sem prompts; `--update` → mensagem + exit 2; registrar resultados em Validation Results (specs/027-instalador-producao-linux/tasks.md)

## Phase 6: User Story 4 — Segurança, logs e diagnóstico (Priority: P1)

**Goal**: nenhuma credencial em log/argv; `.env` 0600; privilégios mínimos; falha segura (spec US4; SR-001..005).

**Independent Test**: quickstart Passo 3 conferências [OPERADOR] — `grep` da senha no log vazio; `stat` do `.env` = `600 sispatrimonio`; grants sem globais.

- [x] T016 [US4] Auditoria de segurança do `install.sh` (checklist SR-001..SR-005 do plan): senha coletada sem eco e dentro de janela `set +x`; toda execução de cliente SQL usa `MYSQL_PWD` no ambiente (nenhuma senha em argv/comandos gravados no log); auto-check ao final da instalação — `grep -F` da senha no próprio log deve ser VAZIO (senão WARNING + revisão); `.env` 0600 dono do serviço; usuário do serviço sem login/root; grants somente no banco da aplicação; validar que o resumo nunca imprime a senha (nem a gerada do admin-via-env, que é exibida 1× apenas no momento da geração com instrução de removê-la)
- [ ] T017 [P] [US4] [OPERADOR] Executar conferências do contract §4 em VM: `grep -F '<SENHA>' /var/log/sispatrimonio-install.log` vazio; `stat -c '%a %U'` do `.env`; `SHOW GRANTS` sem privilégios globais; simular falha (sem rede p/ GitHub) e verificar log com etapa/erro sem credenciais e serviço não habilitado quebrado; registrar resultados

## Phase 7: User Story 5 — Verificação pós-instalação e resumo (Priority: P2)

**Goal**: bateria mínima completa + resumo que orienta o administrador sem consultar o código (spec US5).

**Independent Test**: quickstart Passos 3 (item 7) e 7 [OPERADOR] — resumo corresponde ao estado real; 1º admin criável pelos 3 mecanismos.

- [x] T018 [US5] Revisar em `install.sh` a bateria/resumo contra FR-014 item a item (implementado em T011/T012): cada checagem reporta OK/ERRO nomeado; `/health` `degraded` tratado como WARNING com explicação do campo degradado; resumo final inclui localização do log do instalador e NÃO inclui segredos; instruções do 1º admin citam os 3 mecanismos reais (env `AUTH_ADMIN_*` no 1º start, `/setup` quando não há usuários, CLI `python -m app.cli create-user`) sem criar mecanismo novo
- [ ] T019 [P] [US5] [OPERADOR] Executar quickstart Passo 6 (fluxos adversos: porta ocupada, diretório não-vazio sem `.git`, `.env` existente com backup+merge, banco existente sem DROP, `--recreate-db` interativo com dupla confirmação) e Passo 7 (1º admin via CLI + login na UI + card de Backups presente) em VM; registrar resultados

## Phase 8: Polish & Cross-Cutting

- [x] T020 [P] Atualizar `README.md` §"Instalação em uma máquina nova": referência ao `install.sh` (uso interativo e não interativo com tabela de flags do contract §1), fluxo manual mantido como alternativa, nota de idempotência e de que o instalador NÃO cria schema (delega ao `init_db()`); preservar o restante do README intocado (FR-021)
- [x] T021 [P] Atualizar `docs/GUIA_DE_MANUTENCAO.md`: seção operacional do instalador (requisitos do servidor Debian/Ubuntu+systemd, gerenciamento do serviço `sispatrimoniopro` via systemctl, localização de `.env`/logs/backups, `--update` reservado — NFR-005); sem segredos (SR-001)
- [x] T022 Fechamento: `pytest -q` verde (mesma contagem do T001 — zero diff em `app/`); `bash -n install.sh` + `shellcheck` (se disponível) sem erros; `git status --porcelain` confinado a `install.sh`, `README.md`, `docs/GUIA_DE_MANUTENCAO.md`, `specs/027-instalador-producao-linux/` (contract §2); consolidar Validation Results (incl. pendências [OPERADOR]) no relatório final da feature; marcar tasks concluídas

## Dependencies & Execution Order

```text
T001 (baseline)
  → T002 (esqueleto) → T003 (parser/validação/guardas)
    → T004 → T005 (gates/detecção)
      → US1: T006 → T007 ⤵ (conexão valida pós-venv) → T008 → T009 → T010 → T011 → T012
        → US2: T013 (reuso em todas as etapas)
          → US3: T014 → T015 [OPERADOR]
          → US4: T016 → T017 [OPERADOR]
          → US5: T018 → T019 [OPERADOR]
            → Polish: T020 ∥ T021 → T022 (fechamento)
```

- T002→T003→T004/T005→T006..T012: **sequenciais** (todas editam o mesmo `install.sh`).
- T015/T017/T019 são validações operacionais independentes entre si (podem ocorrer na mesma sessão de VM, em qualquer ordem após T014/T016/T018 correspondentes).
- T020 ∥ T021 (arquivos distintos).

## Parallel Execution Examples

- **Único arquivo de código**: as tarefas de `install.sh` NÃO são paralelizáveis entre si (mesmo arquivo, ordem de integração).
- **Paralelizáveis**: T020 ∥ T021 (docs); T015 ∥ T017 ∥ T019 (execuções operacionais, após seus pré-requisitos).

## Implementation Strategy

- **MVP**: T001→T012 (Foundational + US1) — instalação limpa ponta a ponta é o valor central.
- **Entrega incremental**: +T013 (idempotência) → +T014 (não interativo) → T016/T018 (segurança/resumo como revisões de endurecimento) → docs → T022 fecha.
- **Execução real**: apenas em VM/servidor de teste (tarefas [OPERADOR]); NUNCA contra o servidor de produção durante o desenvolvimento (Constitution I).
- **Barreiras do contrato**: qualquer diff em `app/`/`requirements.txt`/`tests/` quebra o contract §2 — verificar em T022.
