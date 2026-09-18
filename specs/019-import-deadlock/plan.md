# Implementation Plan: Correção do Deadlock da Restauração de Backup

**Branch**: `019-import-deadlock` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/019-import-deadlock/spec.md`

## Summary

A restauração (017) trava porque o import é alimentado **pelo processo web** enquanto conexões do pool do **mesmo processo** mantêm metadata locks sobre as tabelas que o dump recria (incidente real de 2026-09-18, duas ocorrências — diagnóstico abaixo). A correção, nas 3 camadas exigidas pela spec: **(1)** o ciclo do restore passa a rodar numa **thread de worker** que drena o pool de conexões da aplicação durante o import (o `DROP/CREATE` por tabela deixa de disputar locks com a própria aplicação; MariaDB 10.4 `KILL` como rede de segurança documentada); **(2)** **deadline de relógio** cobrindo todas as fases (write incluído) via vigilância do processo, com limite configurável `BACKUP_IMPORT_TIMEOUT`; **(3)** **modo de manutenção** servido em memória (sem tocar o banco) por middleware, com tela amigável, encerramento automático e crash-safety. Ciclo seguro 017, auditoria, RBAC, 018 e Linux preservados.

## Technical Context

**Language/Version**: Python 3.10+ (runtime do projeto)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 (QueuePool) + PyMySQL; stack intocado

**Storage**: MariaDB 10.4.32 (XAMPP/Windows; Linux em produção equivalente) — zero DDL

**Testing**: pytest (fakes para o cliente de import — padrão 015–018); prova real manual no Windows (quickstart)

**Target Platform**: Windows (XAMPP — ambiente do operador) e Linux (preservação obrigatória)

**Project Type**: web-service (sistema existente, uvicorn de processo único)

**Performance Goals**: N/A (operações manuais de administração)

**Constraints**: import sem auto-bloqueio (FR-003); deadline de relógio em todas as fases (FR-007); manutenção sem acesso ao banco (FR-010); crash-safety (FR-009/FR-011); sem bifurcação por SO (FR-016); zero credenciais (FR-009/SC-004)

**Scale/Scope**: `app/services/backup_service.py` (ciclo/thread/deadline), `app/database.py` (helpers de drenagem), `app/main.py` (middleware de manutenção), 1 template novo (`503.html`), rotas admin (via middleware), `app/config.py` (1 variável), testes, README/docs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação/incremental | ✅ PASS | O ciclo 017 é estendido (worker + deadline), não reescrito; eventos, validações e mensagens preservados |
| II | Camadas | ✅ PASS | Worker/deadline no service; middleware e drenagem na infraestrutura existente; rotas delegam |
| III | Regras nos services | ✅ PASS | Regra nova ("restauração em manutenção") vive no service/estado existente |
| IV/V | Integridade patrimonial/inventário | ✅ PASS (N/A) | Nada tocado |
| VI | Segurança | ✅ PASS | Manutenção responde sem banco (sem vazamento de dados); sessões continuam server-side; RBAC intocado (`backup.restaurar` continua governando); nenhuma credencial em log (stderr sanitizado padrão 018) |
| VII | MariaDB/dados | ✅ PASS | Zero DDL; a drenagem encerra conexões **ociosas do pool da aplicação** (nunca dados); fallback operacional documentado (KILL manual) preservado |
| VIII | Testes | ✅ PASS | Testes novos: drenagem, deadline com fake bloqueante, liberação de estado, manutenção, crash-safety; suíte no patamar |
| IX | Auditoria | ✅ PASS | Eventos 017 preservados (INICIADO/PRE_RESTORE/SUCCESS/FAILURE); failure do timeout usa o evento existente |
| X | Interface | ✅ PASS | Tela de manutenção no padrão visual (base existente); backups.html ganha indicador de estado |
| XI | Documentação | ✅ PASS | README (comportamento do restore + variável) e docs na mesma tarefa |
| XII | Especificação/validação | ✅ PASS | Diagnóstico D1–D5 abaixo; validação = suíte + teste real Windows |

**Veredito pré-Phase 0: 12/12 PASS.**

### Re-check pós-design (Phase 1)

Sem violação introduzida pelo design: worker/drenagem/deadline são extensão do ciclo 017 (I/II); sessões próprias e curtas no worker **reduzem** o tempo de vida de transações (VI/VII); manutenção em memória sem banco (VI — zero vazamento, zero query no caminho 503); eventos de auditoria preservados (IX); uma tela nova no padrão visual (X); docs planejadas (XI); testes cobrem cada propriedade nova (VIII); validação por suíte + teste real Windows (XII). **12/12 PASS mantido.**

## Diagnóstico (FR-001) — conclusivo

> Evidência completa em [research.md](./research.md) (D1–D5). Resumo:

- **(a) Onde o import executa**: `restore_backup()` é chamado **sincronamente pela rota** (`admin_routes.py` L894–905: `BackupService.restore_backup(db, actor, ...)`) **dentro do processo web**; `_run_mysql_import` (service L276+) escreve no stdin do cliente `mysql` **a partir do processo web** (pesquisa D1).
- **(b) Por que o timeout não dispara**: o `proc.wait(timeout=)` só cronometra a espera **final**; o bloqueio do incidente ocorreu **antes**, no `proc.stdin.write(chunk)` do loop de streaming (pesquisa D2 — Popen stdin=PIPE em L309).
- **(c) Quem segurava o lock**: conexão do **pool da aplicação** — mecanismo verificado: o fluxo é **síncrono**; a sessão do request (`get_db`, database.py L27–33) permanece checked-out e sua transação aberta (queries de autenticação da própria request; `write_audit` comita na sessão recebida — audit_service L186 — e novos usos reabrem transação na mesma conexão) durante o ciclo inteiro, porque o request só termina depois do import. Os metadata locks dessa conexão persistem até o fim do request → o `DROP TABLE audit_logs` do dump espera o lock que a própria aplicação detém (D3; incidente: 933 s e 852 s nas duas tentativas).
- **(d) Privilégios**: `GRANT ALL ON sispatrimoniopro.*` (sem global) → `DROP/CREATE DATABASE` **inviável**; reconstrução por tabela (o dump já contém `DROP/CREATE TABLE`) — Assumptions da spec já respondida (D5).
- **(e) Menor alteração**: fluxo 202 (rota valida/agenda, request encerra) + worker thread com sessões próprias + drenagem do pool + deadline de relógio + middleware de manutenção (detalhes e alternativas rejeitadas em R1–R5). Não quebra o Linux: mesmo mecanismo nos dois SO (a drenagem é do pool SQLAlchemy; o `terminate()` do processo é multiplataforma).

## Project Structure

### Documentation (this feature)

```text
specs/019-import-deadlock/
├── plan.md              # This file
├── research.md          # D1–D5 + decisões R1–R5
├── data-model.md        # N/A documentado (zero DDL; estado em memória)
├── contracts/
│   └── service-contract.md  # Contrato do ciclo de restore pós-019 + middleware
├── quickstart.md        # Validação manual (Windows) + cenários de regressão
└── tasks.md             # /speckit-tasks (não criado aqui)
```

### Source Code (repository root)

```text
app/
├── config.py                      # + BACKUP_IMPORT_TIMEOUT (opcional, default 900)
├── database.py                    # + drain_engine()/recreate_pool() (drenagem do pool)
├── main.py                        # + middleware de manutenção (em memória, sem banco)
├── services/
│   └── backup_service.py          # restore_backup → _execute_restore_cycle em worker thread;
│                                  #   deadline de relógio (vigilância); progress callbacks; estado p/ UI
└── web/
    ├── admin_routes.py            # POST /restaurar → 303 imediato; GET /restaurar/status (polling)
    └── templates/admin/
        ├── backups.html           # indicador "restauração em andamento" + polling leve
        └── 503.html               # página de manutenção amigável (sem banco)
tests/
└── test_backup_restore.py         # + testes 019 (drenagem, deadline, liberação, manutenção, crash-safety)
README.md                          # §Backup: comportamento do restore pós-019 + BACKUP_IMPORT_TIMEOUT
docs/ARQUITETURA_E_MANUTENCAO.md   # Worker/deadline/manutenção (seções análogas existentes)
```

**Structure Decision**: single-app FastAPI existente; mudanças confinadas ao service de backup + infraestrutura mínima (pool, middleware) + testes/docs.

## Complexity Tracking

> Sem violações — a única complexidade (thread de worker) é a solução do problema, justificada em R1.
