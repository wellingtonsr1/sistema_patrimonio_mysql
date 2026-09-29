# Feature Specification: Refatoração Modular — Rotas Web e Backup Service (051)

**Feature Branch**: `051-refatoracao-modular`

**Created**: 2026-09-28

**Status**: Draft

**Input**: Decompor os dois maiores arquivos do projeto — `app/web/routes.py` (2.668 linhas) e `app/services/backup_service.py` (1.381 linhas) — em módulos por domínio/responsabilidade, **sem nenhuma mudança de comportamento**. Regra máxima: **MOVER, NÃO REESCREVER** — nenhuma regra de negócio, mensagem, URL, permissão ou auditoria pode mudar.

---

## 1. Contexto (fonte: código real, 2026-09-28)

### 1.1 `app/web/routes.py` — 2.668 linhas, 10 domínios em um arquivo

Mapa de seções (marcadores `# =====` reais do arquivo):

| Linhas | Domínio |
|---|---|
| 1–214 | Imports, helpers compartilhados (`_confirm_payload_rows`, `_apply_mapping_to_rows` — Feature 048), config Jinja2, injeção global de variáveis nos templates |
| 215–354 | AUTENTICAÇÃO (login/logout/primeiro acesso) |
| 356–367 | DASHBOARD |
| 369–921 | BENS/EQUIPAMENTOS (maior seção: ~550 linhas, inclui importação) |
| 923–1071 | MOVIMENTAÇÃO |
| 1073–1422 | COLABORADORES |
| 1424–1778 | LOCAIS E DEPARTAMENTOS |
| 1780–1882 | MANUTENÇÕES |
| 1884–1977 | RELATÓRIOS |
| 1979–2167 | PRIMEIRO ACESSO / SETUP |
| 2169–2668 | INVENTÁRIO PATRIMONIAL |

### 1.2 `app/services/backup_service.py` — 1.381 linhas, 5 responsabilidades

| Linhas | Responsabilidade |
|---|---|
| 84–288 | Dump: resolução de executáveis, `_run_mysqldump`, helpers de timestamp |
| 289–637 | Restore: `BackupError`, `restore_in_progress`/`restore_status`, `_restore_slot`, `_run_mysql_import`, `_import_with_deadline`, modo manutenção (`_maintenance_set`) |
| 639–1083 | Classe `BackupService` (backup manual, listagem, exclusão) |
| 1084–1364 | Registros e reconciliação: `_worker_audit`, `_capture_backup_snapshot`, `_reconcile_backup_records`, `_execute_restore_cycle` |
| 1365–1381 | `get_backup_path` |

### 1.3 Acoplamentos externos que DEVEM ser preservados (evidência)

| Consumidor | Import |
|---|---|
| `app/main.py` L15 | `from app.web.routes import web_router, templates` |
| `app/web/admin_routes.py` L61 | `from app.web.routes import templates` |
| `app/web/help_routes.py` L18 | `from app.web.routes import templates` |
| `tests/test_setup_first_access.py` L7 | `from app.web.routes import _claim_first_access` |
| `tests/test_location_nomenclatura_050.py` L326 | `from app.web import routes` |
| `app/services/backup_scheduler.py`, `app/main.py`, `admin_routes.py`, testes | símbolos públicos de backup_service: `BackupService`, `BackupError`, `restore_in_progress`, `restore_status`, `maintenance_mode`, `get_backup_path`, `drain_engine` (este último é de `database.py`) |

## 2. Problema identificado

1. **Custo de manutenção**: qualquer alteração em bens, locais ou inventário edita o mesmo arquivo de 2.668 linhas — alto risco de conflito e de regressão em seções vizinhas.
2. **Navegação e revisão inviáveis**: diffs de PR misturam domínios distintos; code review perde eficácia.
3. **`backup_service.py` mistura dump, restore, manutenção, auditoria e reconciliação** — o ciclo de restore (feature 019) é código delicado embutido no meio do service de backup.
4. **Sem guardrails estruturais**: nada impede o arquivo de voltar a crescer (já absorveu 10 domínios).

## 3. Objetivo

Decompor ambos os arquivos em módulos coesos, mantendo 100% do comportamento observável: URLs, métodos HTTP, códigos de status, mensagens, validações, permissões, auditoria, templates e ordem de registro de rotas (FastAPI faz matching na ordem de inclusão — a ordem atual entre seções DEVE ser preservada). A suíte de testes existente (~847 testes) é a régua de não-regressão.

## 4. Não-objetivo

- Reescrever handlers, renomear funções públicas, alterar assinaturas ou mover lógica para services (a camada já existe; handlers continuam handlers).
- Decompor `admin_routes.py` (~1.400 linhas) e `help_routes.py` — fora do escopo (candidatos a spec futura).
- Qualquer mudança de schema, permissão ou URL.

## 5. Requisitos

### Functional Requirements

**US1 — Decomposição de routes.py (P1)**

- **FR-001**: `routes.py` MUST ser decomposto em routers por domínio em `app/web/routers/` (autenticação, dashboard, assets, movements, custodians, locations, maintenances, reports, setup, inventario, imports/048), com `routes.py` reduzido a **facade** que agrega os routers e re-exporta os símbolos de compatibilidade (`web_router`, `templates`, `_claim_first_access`).
- **FR-002**: O arquivo `routes.py` resultante MUST ter ≤ 200 linhas (facade + injeção global de templates).
- **FR-003**: Helpers compartilhados entre domínios (`_confirm_payload_rows`, `_apply_mapping_to_rows` e afins) MUST morar em módulo único (`app/web/routers/shared.py`) importado pelos domínios — **proibida duplicação**.
- **FR-004**: A injeção global de variáveis nos templates (L201–213) e a configuração Jinja2 MUST ocorrer **exatamente uma vez** (no facade), permanecendo `templates` importável de `app.web.routes` por `admin_routes.py`, `help_routes.py` e `main.py` sem alteração nesses arquivos.
- **FR-005**: A ordem de inclusão dos sub-routers em `web_router` MUST reproduzir a ordem atual das seções (matching de rotas do FastAPI é ordenado).
- **FR-006**: O inventário de rotas (path + methods + nome do endpoint) MUST ser **idêntico antes e depois**, provado por teste novo (`test_route_inventory.py`) que captura snapshot de `app.routes` e compara contra manifesto versionado. A cobertura de permissão por rota permanece garantida pelos testes RBAC existentes — a movimentação literal (NR-003) não altera nenhum decorator `require_permission`.

**US2 — Decomposição de backup_service.py (P1 — inviabilizada com evidência durante o implement; ver Amendment A1)**

- **FR-007**: ~~`backup_service.py` MUST ser decomposto em pacote `app/services/backup/`~~. **AMENDMENT A1 (2026-09-28, pós-evidência)**: a decomposição física foi REJEITADA porque a suíte de testes usa o namespace de módulo como API de injeção — 42 pontos de monkeypatch/setattr em `backup_service` (`SessionLocal`, `DATABASE_URL`, `BACKUP_DIR`, `MYSQLDUMP_PATH`, `BACKUP_IMPORT_TIMEOUT`, `drain_engine`, `maintenance_mode`, `_RESTORE_IN_PROGRESS`, `_run_mysqldump`, `_run_mysql_import`, `write_audit`, `subprocess`, `shutil`) mais leituras diretas (`_BACKUP_NAME_RE`, `_RESTORE_LOCK`, `_maintenance_set`, `_import_with_deadline`). Funções Python resolvem globais no módulo ONDE SÃO DEFINIDAS: qualquer split físico faria os patches do facade deixarem de ser vistos pelo código movido, quebrando os testes (NR-002) ou exigindo reescrita das referências internas (contrária à movimentação literal e ao FR-009). Em substituição: reorganização INTERNA por seções com mapa documentado (mesmo arquivo, zero mudança de namespace).
- **FR-008**: Todos os imports existentes de `app.services.backup_service` MUST continuar funcionando sem edição (`backup_scheduler.py`, `main.py`, `admin_routes.py`, testes). **Cumprido integralmente** — o arquivo permanece módulo único, logo a superfície de monkeypatch é preservada.
- **FR-009**: O comportamento do ciclo de restore (feature 019: modo manutenção, whitelist, `_execute_restore_cycle`, dreno de pool) MUST permanecer bit-a-bit equivalente — é o código de maior risco do projeto e NÃO pode ser "melhorado" nesta spec. **O Amendment A1 elimina o maior risco desta spec.**

**US3 — Guardrails e documentação (P2)**

- **FR-010**: Documentação `docs/ARQUITETURA_E_MANUTENCAO.md` MUST ser atualizada com o novo mapa de módulos (rotas e backup).
- **FR-011**: Nenhum arquivo novo MAY exceder ~800 linhas; os domínios de routes ficam entre 100 e 600 linhas cada (exceção legítima: assets, maior seção).

### Requisitos de não-regressão (transversais)

- **NR-001**: Suíte completa MUST permanecer verde (baseline medido no setup; únicas falhas permitidas: as 2 pré-existentes de `test_backup_externo.py`, fora do escopo).
- **NR-002**: Nenhum teste MAY ter assertions alteradas; apenas imports podem ser tocados se um shim não for viável.
- **NR-003**: `git diff` não MAY conter linhas de lógica alterada dentro dos blocos movidos — movimentação literal (revisável por diff de movimentação).

## 6. Critérios de sucesso

| # | Critério |
|---|---|
| SC-001 | `test_route_inventory.py`: inventário de rotas pós-refatoração == snapshot pré-refatoração (0 diferenças) — **CUMPRIDO (140/140)** |
| SC-002 | Suíte completa verde (mesmo baseline do setup) |
| SC-003 | ~~`routes.py` ≤ 200 linhas; `backup_service.py` ≤ 60 linhas (facade)~~ → ajustado pelo A1: `routes.py` ≤ 200 (**cumprido: 86**); `backup_service.py` permanece módulo único (A1), apenas reordenado em seções com mapa de navegação no cabeçalho |
| SC-004 | `main.py`, `admin_routes.py`, `help_routes.py` sem nenhuma edição (evidência `git diff`) |
| SC-005 | Fluxo web real de backup + restore exercitado via TestClient no ambiente de testes (o ciclo 019 é o mais sensível à quebra de import circular) — suíte de backup/restore integralmente verde |
