# Implementation Plan: Backup Manual — Briefing Completo (Consolidação da 015)

**Branch**: `016-backup-manual-completo` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-backup-manual-completo/spec.md`

## Summary

Completar o mecanismo de backup manual (base: feature 015 em produção) com 4 incrementos delimitados pela análise de gap: **I1** — evento de falha `BACKUP_FALHA` na auditoria; **I2** — compressão gzip (`.sql.gz`, streaming via stdlib), cálculo de **SHA-256** registrado na auditoria e exibido na listagem, e geração **atômica** (arquivo `.part` único → renomear ao validar — nunca há parcial listável); **I3** — diagnóstico no log técnico existente (sem credenciais); **T** — testes A–J literais do briefing. Tudo o mais da 015 permanece intacto: rotas, permissão `backup.gerenciar`, RBAC, download protegido, `data/backups/`, zero DDL, sem restore/agendamento/retenção. Backups `.sql` antigos continuam listáveis/baixáveis (compatibilidade).

## Technical Context

**Language/Version**: Python 3.10+ (sem dependências novas — `gzip`/`hashlib` são stdlib; §32 do briefing: nenhuma ferramenta externa adicional assumida)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Jinja2 (existentes); `mysqldump` nativo (já validado no ambiente); `logging` rotativo existente (`data/logs/`, configurado por `app/logging_config.py`, precedentemente usado por `ad_service.py`)

**Storage**: MariaDB/MySQL (produção); artefatos em `BACKUP_DIR` (`data/backups/`) — **zero DDL**

**Testing**: pytest + TestClient; executor de dump injetável (padrão da 015) — fake grava dump "real" que o service comprime; SHA-256 verificado por recomputação no teste

**Target Platform**: Servidor Linux (Uvicorn via run.py) — usuário comum; apenas leitura do banco (credenciais de `DATABASE_URL`) + escrita em `data/backups/` (§33)

**Project Type**: Web application monolítica (incremento em `app/services/` + template)

**Performance Goals**: Sem requisito novo; compressão em **streaming** (blocos de 1 MB) — dump nunca carregado inteiro em memória

**Constraints**: Regra de mínima alteração (§36 do briefing): 5 arquivos no máximo (`backup_service.py`, `audit_service.py`, `admin/backups.html`, `tests/test_backup_manual.py`, docs); rota web de download/geração INTOCADA (servir `.sql.gz` é agnóstico a extensão); senha apenas via `MYSQL_PWD` (preservado)

**Scale/Scope**: I1 + I2 + I3 + T conforme spec §0.2; 27 ACs do §35 do briefing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Aplicação nesta feature | Status |
|---|---|---|
| I. Preservação / evolução incremental | Incrementos aditivos sobre a 015 (funções novas no service, +1 constante, colunas no template); nada existente é substituído; backup `.sql` antigo segue listável (compatibilidade) | ✅ PASS |
| II/III. Camadas e regras nos services | gzip/SHA-256/.part/log técnico TODOS no `BackupService`; rota e template apenas exibem | ✅ PASS |
| IV/V. Integridade patrimonial/inventário | Backup é leitura do estado; nenhum dado alterado | ✅ PASS |
| VI. Segurança/RBAC/AD | Permissão/rotas/download intocados; `.part` com nome único dentro de `BACKUP_DIR` (sem path traversal); credenciais continuam só no `MYSQL_PWD`; logs sem segredos | ✅ PASS |
| VII. Banco de dados | Zero DDL (checksum derivado do arquivo, não persistido em tabela) | ✅ PASS |
| VIII. Testes | T: testes A–J literais; suíte verde como gate (baseline RBAC exceto) | ✅ PASS |
| IX. Auditoria | Trilha existente; +1 constante aditiva (`BACKUP_FALHA` — precedente `ACTION_AD_*`); sem mecanismo paralelo | ✅ PASS |
| X. UI consistente | Só colunas/texto no template existente; tema claro/escuro e componentes preservados | ✅ PASS |
| XI. Documentação fiel | README/ajuda atualizam: conteúdo (inclusões/exclusões), `.sql.gz`, SHA-256 | ✅ PASS |
| XII. Spec-driven + validação | Fluxo Spec Kit; quickstart + relatório final (§39 do briefing) no DoD | ✅ PASS |

**Conclusão**: PASS pré-design. Re-verificação pós-design no final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/016-backup-manual-completo/
├── plan.md                  # Este arquivo
├── research.md              # Fase 0 — decisões R1–R9
├── data-model.md            # Fase 1 — artefato v2 (.sql.gz/.part), estados, auditoria
├── contracts/
│   ├── service-contract.md  # Fase 1 — contrato v2 do BackupService
│   └── ui-contract.md       # Fase 1 — colunas Integridade/SHA-256
├── quickstart.md            # Fase 1 — roteiro de validação + relatório final §39
└── tasks.md                 # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── services/
│   ├── backup_service.py            # I2: .part→renomear, gzip streaming, SHA-256; I1: BACKUP_FALHA; I3: logging
│   └── audit_service.py             # +1 constante ACTION_BACKUP_FAILED + rótulo
├── web/templates/admin/
│   └── backups.html                 # +colunas Integridade/SHA-256 (truncado)
tests/
└── test_backup_manual.py            # T: testes H/I/G literais + ajustes gzip
README.md, app/services/help_service.py  # docs (conteúdo do backup, .sql.gz, SHA-256)
```

**Structure Decision**: Mesma estrutura da 015; nenhuma rota nova, nenhum model novo, nenhuma dependência nova.

## Complexity Tracking

> Não utilizado — nenhuma violação de Constitution a justificar.

## Re-verificação da Constitution pós-design (Fase 1)

- **R2 (atomicidade)**: o `.part` usa o nome-base único do backup (mesma proteção de regex/colisão) e só existe dentro de `BACKUP_DIR`; renomeação é atômica no mesmo filesystem — invariante "nunca parcial listável" verificável em teste (I do §34 + novo teste de atomicidade).
- **R3 (checksum)**: SHA-256 derivado do arquivo em disco (não persistido) — zero DDL mantido; retroativo para `.sql` antigos fica "—" (UI), download intacto.
- **R5 (eventos)**: `BACKUP_FALHA` é constante aditiva com rótulo — trilha única preservada; `BACKUP_CRIADO`/`BACKUP_DOWNLOAD` sem alteração semântica.
- **R6 (log técnico)**: `logging.getLogger(__name__)` — usa a configuração rotativa existente (`logging_config.py`), sem segundo sistema (precedente `ad_service.py`).
- Constitution Check permanece **PASS** em todos os princípios.
