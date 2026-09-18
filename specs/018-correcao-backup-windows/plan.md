# Implementation Plan: Correção do Backup Manual no Windows

**Branch**: `018-correcao-backup-windows` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/018-correcao-backup-windows/spec.md`

## Summary

O backup manual falha no Windows porque `_run_mysqldump` substitui o ambiente inteiro do subprocesso por um PATH **fixo Unix** (`/usr/local/bin:/usr/bin:/bin`) e o utilitário `mysqldump` não está no PATH do Windows da máquina atual — ele existe apenas em `C:\xampp\mysql\bin\mysqldump.exe`. A falha (`FileNotFoundError` → ramo genérico "(erro de disco/subprocesso)") é **silenciada** porque o caminho do dump não registra diagnóstico técnico (o caminho de importação registra). A correção mínima, comprovada por diagnóstico reproduzido nesta máquina (research D1–D5): **(A)** derivar o ambiente do subprocesso de `os.environ.copy()` + `MYSQL_PWD` (senha continua fora do argv/logs), **(B)** resolver o executável do dump via variável opcional `MYSQLDUMP_PATH` com fallback para busca no PATH (executável direto, sem shell, sem auto-descoberta de XAMPP no código), **(C)** registrar log técnico no dump com exceção/código de retorno/stderr sanitizado, **(D)** mensagens amigáveis distintas para "utilitário não encontrado" vs. "utilitário retornou erro". Zero DDL, zero rotas novas, zero RBAC/AD, auditoria e telas intocadas. Linux preservado: fallback PATH continua encontrando o binário como hoje.

## Technical Context

**Language/Version**: Python 3.10+ (runtime do projeto)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Pydantic v2 (stack existente — intocados nesta feature)

**Storage**: MariaDB/MySQL produção (via `DATABASE_URL`); artefatos em `data/backups/` (`BACKUP_DIR` existente). Nenhuma alteração de schema — zero DDL.

**Testing**: pytest (suíte existente; executor de dump é FAKE nos testes — padrão 015–017; prova real do Windows é manual, quickstart §3)

**Target Platform**: Windows (XAMPP/MariaDB — ambiente atual do usuário) **e** Linux (preservação obrigatória)

**Project Type**: web-service (sistema existente)

**Performance Goals**: N/A (nenhum caminho quente alterado; fluxo de backup é operação manual on-demand)

**Constraints**: menor alteração possível (briefing §37); nunca registrar credenciais (Princípio VI); nunca falso sucesso (FR-011/FR-012); Linux byte-compatível em comportamento (FR-019); senha nunca em argv (FR-005)

**Scale/Scope**: 1 service (`app/services/backup_service.py`) + 1 módulo de configuração (`app/config.py`, 1 variável opcional) + testes + 2 artefatos de documentação. Zero alteração em rotas, templates, models, migrations, permissões, auditoria.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente / evolução incremental | ✅ PASS | Alteração mínima em `_run_mysqldump`/`_run_mysql_import` (ambiente + resolução de executável + log); nenhuma funcionalidade removida; `APP_HOST` pré-existente em `app/config.py` NÃO é tocado |
| II | Arquitetura em camadas | ✅ PASS | Toda mudança fica no service de backup; rotas/telas intocadas |
| III | Regras de negócio nos services | ✅ PASS | Resolução de executável e sanitização vivem em `backup_service` |
| IV | Integridade patrimonial/movimentações | ✅ PASS (N/A) | Nenhum bem/custódia/localização tocado |
| V | Integridade do inventário | ✅ PASS (N/A) | Nenhum fluxo de inventário tocado |
| VI | Segurança (auth, RBAC, AD, credenciais) | ✅ PASS | Senha continua EXCLUSIVAMENTE no ambiente do subprocesso (`MYSQL_PWD`), nunca em argv/logs/auditoria; stderr sanitizado com replace da senha; nenhuma rota/permissão nova |
| VII | Banco MariaDB e proteção dos dados | ✅ PASS | Zero DDL; `DATABASE_URL` intocado; restauração (017) intocada |
| VIII | Testes como requisito de não regressão | ✅ PASS | Testes novos para resolução de executável (config/PATH), sanitização e logs; suíte existente (312 passed / 1 failed pré-existente) deve permanecer no patamar |
| IX | Auditoria das operações relevantes | ✅ PASS | Eventos existentes (`ACTION_BACKUP_CREATED/FAILED`) reutilizados sem mudança de formato |
| X | Interface consistente | ✅ PASS | Tela intocada; só a mensagem de erro da geração ganha distinção (não encontrada vs. retornou erro) via `BackupError` existente |
| XI | Documentação fiel | ✅ PASS | Plano inclui atualização de README (§Backup: requisito do PATH/executável + nova variável) e docs de manutenção (log técnico) na mesma tarefa |
| XII | Especificação e validação | ✅ PASS | Fluxo Spec Kit seguido; validação = suíte + teste real no Windows (quickstart §3) + Linux quando disponível |

**Veredito pré-Phase 0: 12/12 PASS** — sem violações que exijam Complexity Tracking.

**Reavaliação pós-design (Phase 1): 12/12 PASS** — o design confirmou o gate: 1 variável opcional aditiva (`MYSQLDUMP_PATH`, sem segredo), alteração confinada ao service de backup (ambiente + resolução + log), paridade obrigatória no import para não quebrar a 017 no Windows, auditoria/telas/RBAC/DDL intocados, docs na mesma tarefa. Nenhuma complexidade adicional justificada.

## Diagnóstico (FR-001) — conclusivo, provado nesta máquina

> Resumo executivo; evidência completa em [research.md](./research.md) (D1–D7).

- **Causa**: ambiente do subprocesso construído do zero (`env = {"MYSQL_PWD": ..., "PATH": "/usr/local/bin:/usr/bin:/bin"}`) + `mysqldump` resolvido por nome simples fora do PATH do Windows → `FileNotFoundError` (`[WinError 2]`), reproduzido fielmente nesta máquina.
- **Por que funciona no Linux**: o PATH fixo Unix contém o binário no servidor Linux.
- **Por que falha no Windows**: diretórios Unix não existem; `C:\xampp\mysql\bin` não está no PATH do usuário (D3); nenhum mecanismo de configuração do executável existe no projeto (D6).
- **Trecho causador**: `app/services/backup_service.py`, linhas do `env =` em `_run_mysqldump` (e o mesmo padrão em `_run_mysql_import`).
- **Menor alteração**: (A) ambiente herdado + `MYSQL_PWD`; (B) `MYSQLDUMP_PATH` (opcional, com fallback PATH); (C) log técnico no dump; (D) mensagens distintas. Detalhes e alternativas rejeitadas: research R1–R6.
- **Continua no Linux?** Sim — fallback PATH reproduz o comportamento atual; com ambiente herdado o PATH do sistema é incluído (superset do PATH fixo atual; ver R2).

## Project Structure

### Documentation (this feature)

```text
specs/018-correcao-backup-windows/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — diagnóstico D1–D7 + decisões R1–R6
├── data-model.md        # Phase 1 output — N/A documentado (zero entidades/DDL)
├── quickstart.md        # Phase 1 output — validação manual Windows/Linux + cenários A–H
├── contracts/
│   └── service-contract.md  # Contrato do service de backup pós-correção
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── config.py                      # + MYSQLDUMP_PATH (opcional; APP_HOST pré-existente intocado)
└── services/
    └── backup_service.py          # _run_mysqldump/_run_mysql_import: env herdado + MYSQL_PWD,
                                    #   resolução do executável, log técnico, mensagens distintas
tests/
└── test_backup_manual.py          # + testes: resolução via MYSQLDUMP_PATH, fallback PATH,
                                   #   sanitização de stderr com senha, log técnico, Linux-regressão
                                   #   (executável fake no PATH), utilitário ausente
README.md                          # §Backup: requisito de PATH/executável + MYSQLDUMP_PATH
docs/ARQUITETURA_E_MANUTENCAO.md   # Log técnico do backup + variável nova (se houver seção aplicável)
```

**Structure Decision**: projeto single-app FastAPI existente; alterações confinadas ao service de backup + 1 variável de configuração + testes + docs. Nenhum arquivo fora disso.

## Complexity Tracking

> Sem violações da Constitution — seção não aplicável.
