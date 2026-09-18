# Implementation Plan: Backup Automático e Política de Retenção

**Branch**: `020-backup-automatico-retencao` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/020-backup-automatico-retencao/spec.md`

## Summary

O SisPatrimônio Pro só gera backup por ação manual e não possui retenção: cópias acumulam indefinidamente e não há distinção persistida entre backup manual, automático e pré-restauração. Este plano adiciona, de forma incremental sobre o mecanismo existente: **(1)** um **agendador interno ao processo** (thread daemon iniciada no `lifespan`, sem Celery/Redis/APScheduler) que dispara o **mesmo** `BackupService.generate_backup()` na frequência/horário configurados (America/Recife para o horário, UTC para a operação — política da 004); **(2)** **metadados determinísticos de tipo** em tabela nova `backup_records` (criada por `create_all` — zero `ALTER`, zero mudança no formato/nome de arquivo), preenchida pelo próprio `generate_backup` (que ganha parâmetro aditivo `backup_type`); **(3)** **política de retenção GFS configurável** (diária 30 d, semanal 12 sem, mensal 12 meses — env vars) que atua **somente** sobre backups `AUTOMATICO` elegíveis, com âncoras semanais/mensais determinísticas, preservação total de manuais, pré-restauração e legados, guarda do último backup válido e resultado PARCIAL em falhas; **(4)** **monitoramento** na tela de Backups existente (indicadores reutilizando componentes atuais) e **5 eventos de auditoria novos aditivos**. Falhas são honestas e diagnósticáveis no log técnico (padrão 018: stderr sanitizado, senha só no `MYSQL_PWD`). Windows e Linux idênticos por herdar a correção multiplataforma da 018.

## Technical Context

**Language/Version**: Python 3.10+ (runtime do projeto)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Pydantic v2 (stack existente — intocados; nenhuma dependência nova)

**Storage**: MariaDB/MySQL produção (via `DATABASE_URL`); **1 tabela NOVA** `backup_records` via `Base.metadata.create_all` (aditiva, idempotente, zero DDL de alteração); artefatos em `data/backups/` (`BACKUP_DIR` existente, intocado)

**Testing**: pytest (suíte existente; executor de dump e relógio são FAKE/injetáveis — padrão 015–019; prova real em Windows e Linux é manual, quickstart §4)

**Target Platform**: Linux (produção atual) **e** Windows (XAMPP/MariaDB) — paridade obrigatória herdando a resolução de executável da 018

**Project Type**: web-service (sistema existente, processo uvicorn único)

**Performance Goals**: N/A (backup é operação de fundo de baixa frequência; nenhum caminho quente alterado — overhead do agendador: 1 verificação de relógio a cada ~30 s)

**Constraints**: menor alteração possível (briefing §41/§44); nunca registrar credenciais (Princípio VI); nunca falso sucesso (FR-016); retenção conservadora — nunca deixar 0 backups válidos (FR-027); nenhum backup manual/pré-restauração removido (FR-024/FR-025); catch-up determinístico sem cascata (FR-009)

**Scale/Scope**: 2 services (`backup_service.py` estendido; `backup_scheduler.py` novo) + 1 model novo + config (+~8 env vars) + 1 rota estendida + 1 template estendido + auditoria (+5 eventos) + `main.py` (lifespan) + testes + 2 docs. Zero alteração em: Restore (017/019), RBAC, AD, autenticação, módulos patrimoniais, formato de arquivo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente / evolução incremental | ✅ PASS | Tudo é extensão: `generate_backup` ganha parâmetro ADITIVO com default compatível (`MANUAL`); botão/fluxo/auditoria do manual preservados (FR-004); Restore 017/019 intocado exceto marcação de tipo (Assumption 6); nenhuma funcionalidade removida |
| II | Arquitetura em camadas | ✅ PASS | Agendador, retenção e metadados vivem em services (`backup_scheduler.py`, `backup_service.py`); rota apenas consulta status e delega; nada de regra em template |
| III | Regras de negócio nos services | ✅ PASS | Classificação GFS, elegibilidade, guardas de proteção e catch-up: toda a lógica concentrada em `backup_service.py`/`backup_scheduler.py` |
| IV | Integridade patrimonial/movimentações | ✅ PASS (N/A) | Nenhum bem/custódia/localização/movimentação tocado |
| V | Integridade do inventário | ✅ PASS (N/A) | Nenhum fluxo de inventário tocado |
| VI | Segurança (auth, RBAC, AD, credenciais) | ✅ PASS | Sem rota nova pública: indicadores entram na rota existente que já exige `backup.gerenciar` (FR-034, reuso — sem permissão nova); senha continua EXCLUSIVAMENTE no `MYSQL_PWD` do subprocesso; stderr sanitizado (padrão 018); eventos novos sem segredos |
| VII | Banco MariaDB e proteção dos dados | ✅ PASS | Única alteração de schema é **tabela nova** (`backup_records`) criada por `create_all` — aditiva, idempotente, nenhum dado existente tocado; nenhum `ALTER`/drop/renome (mecanismo `_ensure_schema_migrations` não precisa ser estendido) |
| VIII | Testes como requisito de não regressão | ✅ PASS | Testes novos (`tests/test_backup_automatico.py`) para agendamento, catch-up, concorrência, tipo, retenção GFS, guardas, falhas, path traversal, RBAC; suíte existente (313 testes) deve permanecer verde — nenhum teste removido/enfraquecido |
| IX | Auditoria das operações relevantes | ✅ PASS | 5 eventos novos aditivos em `audit_service.py` (constantes + rótulos), gravados via `write_audit` existente; eventos do manual preservados |
| X | Interface consistente | ✅ PASS | Indicadores entram no card da tela `admin/backups.html` existente com componentes atuais (badge/dd/small); nenhum redesenho; nada é removido da tela |
| XI | Documentação fiel | ✅ PASS | Plano inclui README (novas env vars + comportamento pós-restart) e `docs/ARQUITETURA_E_MANUTENCAO.md` (módulo/agendador/monitoramento) na mesma tarefa |
| XII | Especificação e validação | ✅ PASS | Fluxo Spec Kit seguido; validação = suíte pytest + Testes N/O reais em Windows e Linux + cenários do quickstart |

**Veredito pré-Phase 0: 12/12 PASS** — sem violações que exijam Complexity Tracking.

**Reavaliação pós-design (Phase 1): 12/12 PASS** — o design confirmou o gate: 1 tabela nova aditiva (sem ALTER), parâmetro aditivo em `generate_backup` com default retrocompatível, zero mudança no Restore/flush 019 além da marcação de tipo, retenção confinada ao service com guardas em camadas, permissão reutilizada, docs na mesma tarefa. Nenhuma complexidade adicional justificada.

## Project Structure

### Documentation (this feature)

```text
specs/020-backup-automatico-retencao/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — decisões R1–R9 (agendador, config, tipo, GFS, catch-up…)
├── data-model.md        # Phase 1 output — entidade BackupRecord + regras de classificação/estado
├── quickstart.md        # Phase 1 output — validação end-to-end (Testes A–Q do briefing §39)
├── contracts/
│   └── service-contract.md  # Contratos: config env, generate_backup, scheduler, retenção, auditoria, UI
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── config.py                      # + env vars: BACKUP_AUTO_ENABLED/SCHEDULE/TIME/WEEKDAY,
│                                  #   BACKUP_RETENTION_DAILY_DAYS/WEEKLY_WEEKS/MONTHLY_MONTHS
│                                  #   (defaults seguros + validação no serviço — nada hardcoded na regra)
├── main.py                        # lifespan: iniciar/parar o agendador (thread daemon)
├── models/
│   ├── backup_record.py           # NOVO: BackupRecord (metadados determinísticos de tipo/status/remoção)
│   └── __init__.py                # + import de BackupRecord (create_all cria a tabela)
├── services/
│   ├── backup_service.py          # generate_backup(+backup_type) + escrita de BackupRecord
│   │                              #   (sucesso E falha) + helpers: contagem de válidos, listagem com tipo
│   ├── backup_scheduler.py        # NOVO: thread agendadora + execução automática (worker c/ sessões
│   │                              #   próprias) + retenção GFS + catch-up determinístico + guardas
│   └── audit_service.py           # +5 ações aditivas: BACKUP_AUTOMATICO_SUCESSO/FALHA,
│                                  #   BACKUP_RETENCAO_EXECUTADA, BACKUP_REMOVIDO_RETENCAO,
│                                  #   BACKUP_RETENCAO_FALHA (+ rótulos)
└── web/
    ├── admin_routes.py            # admin_backups: contexto ganha indicadores (consulta ao scheduler/records)
    └── templates/admin/backups.html  # card "Backup Automático" com indicadores (componentes existentes)

tests/
└── test_backup_automatico.py      # NOVO: Testes A–M, P, Q do briefing §39 (executores/relógio fake)

README.md                          # §Backup: env vars novas, default DESATIVADO, comportamento pós-restart
docs/ARQUITETURA_E_MANUTENCAO.md   # Agendador (thread do processo), retenção GFS, monitoramento
```

**Structure Decision**: projeto single-app FastAPI existente; alterações confinadas a backup (services/model/config/rota da tela existente/lifespan) + testes + docs. Nenhum arquivo fora disso.

## Complexity Tracking

> Sem violações da Constitution — seção não aplicável.
