# Implementation Plan: Restauração Segura de Backup — SisPatrimônio Pro

**Branch**: `017-restauracao-segura-backup` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/017-restauracao-segura-backup/spec.md`

## Summary

Implementar a **restauração segura de backups** reutilizando integralmente a infraestrutura da Feature 1 (features 015/016): seleção a partir da listagem existente, validação prévia do arquivo, confirmação explícita em duas etapas (POST, nunca GET), **backup de segurança obrigatório e validado** antes de qualquer alteração, import do dump via **cliente nativo MariaDB** (`mysql`) com senha exclusivamente por `MYSQL_PWD`, validação pós-restore real (conexão + tabelas + dados essenciais), 4 eventos de auditoria aditivos, permissão própria `backup.restaurar` (deny-by-default, seed idempotente ao Administrador) e bloqueio em memória de operações concorrentes (processo único uvicorn). Falhas nunca são sucesso; o backup de segurança é sempre preservado. Zero DDL.

## Technical Context

**Language/Version**: Python 3.10+ (verificado em execução)

**Primary Dependencies**: FastAPI + Uvicorn (processo único, `reload=False`), SQLAlchemy 2 (QueuePool `pool_size=10`, `pool_pre_ping=True`), Jinja2 + Bootstrap 5, PyMySQL — todas já presentes, nenhuma dependência nova

**Storage**: MariaDB 10.6 (`sispatrimoniopro`) — produção; SQLite em memória — suíte de testes (executor do cliente nativo injetável para testes, como na 015/016); artefatos de backup em `data/backups/` (filesystem, mecanismo existente)

**Testing**: pytest + TestClient (padrão existente: `tests/test_backup_manual.py` como referência direta — fixtures, `_fake_dump`, monkeypatch do executor)

**Target Platform**: Linux server (Debian, `mysql` 10.6.23 em `/usr/bin/`)

**Project Type**: Web application monolítica (FastAPI + Jinja2), arquitetura em camadas Web/API → Services → Models

**Performance Goals**: restore síncrono para os volumes atuais (dump ≈ 200 KB comprimido; import em segundos); UI responsiva com estado de processamento durante a operação

**Constraints**: operação destrutiva — prioridade máxima é proteger os dados atuais (§40); nenhuma credencial fora do ambiente do subprocesso; nenhuma restauração concorrente; zero DDL; nenhuma alteração em módulos não relacionados (§38)

**Scale/Scope**: 1 tela existente estendida (`backups.html`), 1 service estendido (`backup_service.py`), +1 permissão, +4 eventos de auditoria, +1 módulo de testes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Veredito | Evidência |
|---|---|---|
| I. Preservação e evolução incremental | ✅ PASS | Extensão aditiva de `backup_service.py` e `admin_routes.py`; geração/listagem/download da Feature 1 intocados; reuso explícito (spec FR-01/02/03) |
| II. Arquitetura em camadas | ✅ PASS | Toda regra do restore em `backup_service.py` (service); rotas apenas autenticam/autorizam/delegam |
| III. Regras nos services | ✅ PASS | Validações, import e pós-restore no service; template só apresenta |
| IV/V. Integridade patrimonial/inventário | ✅ PASS | Nenhuma regra patrimonial tocada; restore importa dump integral (comportamento documentado) |
| VI. Segurança (auth/RBAC/AD/credenciais) | ✅ PASS | `require_permission("backup.restaurar")` deny-by-default; senha só via `MYSQL_PWD` no subprocesso; sem segredos em logs/auditoria (FR-15/25) |
| VII. Banco MariaDB e proteção de dados | ✅ PASS | Zero DDL (estado do restore em memória; artefato é arquivo); cliente nativo do banco real; sem `drop_all`; import com o utilitário do próprio SGBD |
| VIII. Testes como não regressão | ✅ PASS | +1 módulo de testes cobrindo A–K; suíte existente deve permanecer verde (397 passed + RBAC lockout pré-existente) |
| IX. Auditoria | ✅ PASS | 4 eventos aditivos via `write_audit` existente; trilha única imutável; sem credenciais |
| X. UI consistente | ✅ PASS | Ação/telas dentro de `backups.html` existente, padrões Bootstrap/tema/`can()`; nenhuma quebra de fluxo |
| XI. Documentação fiel | ✅ PASS | README + help_service atualizados na mesma tarefa (comportamento de sessões, backup de segurança) |
| XII. Orientação por especificação | ✅ PASS | Fluxo Spec Kit em execução; validação (suíte + testes A–K) no DoD |

**Nenhuma violação.** Re-verificação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/017-restauracao-segura-backup/
├── plan.md              # This file
├── research.md          # Phase 0 (decisões R1–Rn verificadas)
├── data-model.md        # Phase 1 (conceitos, estados da operação, invariantes)
├── quickstart.md        # Phase 1 (suíte, testes A–K, validação MariaDB, relatório §39)
├── contracts/
│   ├── service-contract.md   # Contrato das funções de restore no BackupService
│   └── ui-contract.md        # Rotas, telas de confirmação e ação na listagem
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
app/
├── services/
│   ├── backup_service.py        # EXTENSÃO: validação de restore, _run_mysql_import,
│   │                            #   pós-restore, flag de operação em andamento
│   ├── audit_service.py         # +4 constantes/rótulos (aditivo)
│   └── permission_service.py    # +1 permissão backup.restaurar (aditivo, seed idempotente)
├── web/
│   ├── admin_routes.py          # +rotas de confirmação/execução do restore (padrão existente)
│   └── templates/admin/
│       └── backups.html         # ação Restaurar (can()), telas de info/confirmação, processamento
└── (models/ — INTOCADO: zero DDL)

tests/
└── test_backup_restore.py       # NOVO: testes A–K (executor de import injetável)
```

**Structure Decision**: projeto monolítico existente — extensão aditiva nos mesmos arquivos da Feature 1 (backup_service/admin_routes/backups.html), seguindo o padrão consolidado nas features 015/016.

## Complexity Tracking

> Sem violações de Constitution a justificar — seção não utilizada.
