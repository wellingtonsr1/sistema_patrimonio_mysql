# Implementation Plan: Backup Manual do SisPatrimônio Pro

**Branch**: `015-backup-manual` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-backup-manual/spec.md`

## Summary

Implementar o mecanismo de **backup manual** do SisPatrimônio Pro: um administrador autorizado (permissão nova `backup.gerenciar`, deny-by-default) aciona a geração pela interface de Administração; o sistema produz um dump consistente do banco de dados via utilitário nativo do próprio SGBD (`mysqldump`/`mariadb-dump`, presentes no servidor — verificado), armazena o arquivo em `data/backups/` com nome identificável por data/hora (incluindo fração de segundo para gerações repetidas), lista os backups disponíveis (data/hora + tamanho, derivados do repositório de arquivos — **sem tabela nova**), permite o download do arquivo e registra cada operação (criação/falha/download) na trilha `audit_logs` existente via `write_audit`. Zero alteração de comportamento nas funcionalidades existentes.

## Technical Context

**Language/Version**: Python 3.10+ (stack estabelecido — nenhuma dependência nova; `mysqldump`/`mariadb-dump` já presentes: `/usr/bin/mysqldump`, `/usr/bin/mariadb-dump`)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Jinja2/Bootstrap 5 (existentes); utilitário nativo do SGBD para o dump

**Storage**: MariaDB/MySQL (produção, `DATABASE_URL`); artefatos em `DATA_DIR / "backups"` (`app/config.py` — `DATA_DIR` já existe com `data/logs/`); **sem DDL** (listagem derivada do repositório de arquivos)

**Testing**: pytest + TestClient (padrão existente); executor do dump isolado em ponto único para injetar resultado determinístico nos testes (banco de teste é SQLite em memória — sem mysqldump; ver research R4)

**Target Platform**: Servidor web existente (Uvicorn) — área Administração da interface web

**Project Type**: Web application monolítica (app/web + app/services)

**Performance Goals**: Sem requisito novo; duração do backup é a do dump nativo (fora do controle da aplicação)

**Constraints**: Zero alteração de comportamento existente (FR-009); permissão deny-by-default (FR-008); credenciais do banco NUNCA em logs/auditoria/argumentos de processo visíveis (Princípio VI — senha via `MYSQL_PWD` no ambiente do subprocesso, nunca na linha de comando)

**Scale/Scope**: 1 service novo + 1 router novo (3 rotas) + 1 template novo + item de menu + permissão no catálogo + 2 constantes de ação de auditoria + docs + testes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Aplicação nesta feature | Status |
|---|---|---|
| I. Preservação / evolução incremental | Funcionalidade 100% aditiva (novo service, novas rotas, novo template); nenhum módulo existente alterado além do catálogo de permissões, constantes de ação (precedente: `ACTION_AD_*`) e item de menu | ✅ PASS |
| II/III. Camadas e regras nos services | Toda a regra (nome/validação/listagem/download/auditoria) no novo service; rotas apenas autenticam, autorizam e delegam | ✅ PASS |
| IV/V. Integridade patrimonial/inventário | O backup é **leitura** do estado; nenhum dado do sistema é alterado | ✅ PASS |
| VI. Segurança/RBAC/AD | Nova permissão `backup.gerenciar` no padrão `modulo.acao` (deny-by-default); todas as rotas com `require_permission`; senha do banco via ambiente do subprocesso (`MYSQL_PWD`), nunca em argumentos, logs ou auditoria | ✅ PASS |
| VII. Banco de dados | **Zero DDL**: listagem deriva do repositório de arquivos; seed idempotente existente (`ensure_default_roles` no startup) cadastra a permissão e concede ao perfil Administrador automaticamente | ✅ PASS |
| VIII. Testes | Novo módulo cobrindo geração, listagem, download, 404, RBAC (negado/permitido) e auditoria; suíte verde como gate (falha pré-existente RBAC fora do escopo) | ✅ PASS |
| IX. Auditoria | Eventos `BACKUP_CRIADO` (sucesso/falha) e `BACKUP_DOWNLOAD` via `write_audit` existente, sem credenciais | ✅ PASS |
| X. UI consistente | Template nos padrões de Administração (Bootstrap 5, menu com `can()`, 403/404 existentes) | ✅ PASS |
| XI. Documentação fiel | README §💾 + central de ajuda atualizados na mesma tarefa | ✅ PASS |
| XII. Spec-driven + validação | Fluxo Spec Kit seguido; quickstart como parte do DoD | ✅ PASS |

**Conclusão**: PASS pré-design. Re-verificação pós-design no final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/015-backup-manual/
├── plan.md                  # Este arquivo
├── research.md              # Fase 0 — decisões R1–R8
├── data-model.md            # Fase 1 — artefato, permissão e eventos
├── contracts/
│   ├── service-contract.md  # Fase 1 — contrato do BackupService
│   └── ui-contract.md       # Fase 1 — contrato das rotas/template/menu
├── quickstart.md            # Fase 1 — roteiro de validação
└── tasks.md                 # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── services/
│   └── backup_service.py            # NOVO: geração/listagem/download/auditoria
├── web/
│   ├── admin_routes.py              # +3 rotas (/admin/backups*) com require_permission("backup.gerenciar")
│   └── templates/admin/
│       └── backups.html             # NOVO template (padrões de administração)
├── templates base.html              # +1 item de menu com can('backup.gerenciar')
├── services/permission_service.py   # +1 permissão no PERMISSION_CATALOG (seed idempotente concede ao Administrador)
├── services/audit_service.py        # +2 constantes de ação (precedente ACTION_AD_*)
├── config.py                        # +BACKUP_DIR = DATA_DIR / "backups" (constante, sem lógica)
tests/
└── test_backup_manual.py            # NOVO módulo de testes
```

**Structure Decision**: Padrão das features 010–014 — monólito FastAPI; regra em service; rota web em `admin_routes.py` (área Administração); artefatos em `data/`.

## Complexity Tracking

> Não utilizado — nenhuma violação de Constitution a justificar.

## Re-verificação da Constitution pós-design (Fase 1)

- **R3 (sem tabela de metadados)**: confirmada a listagem por repositório de arquivos — zero DDL (Princípio VII íntegro).
- **R4 (executor isolado)**: o subprocesso de dump fica em função única injetável nos testes; produção usa `mysqldump` com `MYSQL_PWD` no ambiente (Princípio VI íntegro — senha fora da linha de comando).
- **R5/R6 (constantes e permissão aditivas)**: `PERMISSION_CATALOG` e constantes `ACTION_*` são os pontos declarados de extensão do sistema (precedentes internos) — edições aditivas mínimas.
- **ui-contract**: todas as rotas com `require_permission("backup.gerenciar")` + `require_web_auth` global (Princípio VI íntegro).
- Constitution Check permanece **PASS** em todos os princípios.
