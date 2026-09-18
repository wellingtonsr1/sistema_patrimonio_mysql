# Tasks: Restauração Segura de Backup (feature 017)

**Input**: Design documents from `/specs/017-restauracao-segura-backup/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅ · quickstart.md ✅

**Tests**: Obrigatórios (briefing §36 — Testes A–K), escritos ANTES da implementação (TDD, padrão das features 015/016).

**Organization**: Tasks agrupadas por user story (US1–US5 da spec), com fases de setup/foundational bloqueantes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Path Conventions

Projeto monolítico existente: `app/services/`, `app/web/`, `tests/` na raiz (conforme plan.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline e infraestrutura de testes

- [x] T001 Rodar a suíte e registrar o baseline (`python3 -m pytest -q`): **397 passed + 1 falha pré-existente** `tests/test_rbac.py::test_lockout_after_failed_attempts` (fora do escopo — não corrigir, Princípio I). Criar `tests/test_backup_restore.py` com infraestrutura: docstring de cobertura A–K; helpers `_make_backup_file(name, payload=b"...")` (grava `.sql.gz` gzip válido ou `.sql` legado em `BACKUP_DIR`), `_corrupted_gz(name)` (bytes truncados no meio do fluxo → integrity CORROMPIDO), `_fake_import(path, *, is_gzip=False)` (executor fake — lê/verifica acessibilidade, research R2), `_failing_import(...)` (leva erro), `_failing_security_backup(...)` (para o Teste G); fixture autouse de limpeza reutilizando o padrão de `tests/test_backup_manual.py` (inclui `nao-e-backup.txt`); imports reutilizados de `tests.test_rbac` (`PASSWORD`, `_make_user`, `_login`) (depends: none)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Permissão, eventos de auditoria, bloqueio de concorrência e validação do backup — base de TODAS as stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 [P] Testes FALHANDO da permissão em `tests/test_backup_restore.py`: seed `ensure_default_roles` cria `backup.restaurar` (module "Backup") e o Administrador a recebe (seed idempotente — 1 linha por chamada repetida); um perfil comum não a recebe (research R9) (depends: T001)
- [x] T003 [P] Adicionar em `app/services/permission_service.py`: entrada `{"name": "backup.restaurar", "module": "Backup", "label": "Restaurar backups", "description": ...}` ao lado de `backup.gerenciar` (contract §7 — aditivo, seed idempotente concede ao Administrador) (depends: T002)
- [x] T004 [P] Adicionar em `app/services/audit_service.py`: `ACTION_BACKUP_RESTORE_STARTED = "BACKUP_RESTORE_INICIADO"`, `ACTION_BACKUP_PRE_RESTORE = "BACKUP_PRE_RESTORE_CRIADO"`, `ACTION_BACKUP_RESTORE_SUCCESS = "BACKUP_RESTORE_SUCESSO"`, `ACTION_BACKUP_RESTORE_FAILED = "BACKUP_RESTORE_FALHA"` + rótulos "Restauração Iniciada"/"Backup Pré-Restore Criado"/"Restauração Concluída"/"Restauração Falhou" em `ACTION_LABELS` (contract §6 — aditivo, eventos 015/016 intocados, research R10) (depends: T001)
- [x] T005 Testes FALHANDO do slot de concorrência em `tests/test_backup_restore.py`: `restore_in_progress()` → False por padrão; com o slot ocupado (acesso interno ao context manager/flag), `generate_backup` levanta `BackupError` com mensagem clara (BV-R2, FR-17; research R6) (depends: T001)
- [x] T006 Implementar em `app/services/backup_service.py`: `_RESTORE_LOCK` (threading.Lock), `_RESTORE_IN_PROGRESS` (bool), context manager `_restore_slot()` (marca/libera em finally), `restore_in_progress()` e **guarda aditiva** no início de `generate_backup` (recusa se restore em andamento — único toque no fluxo da Feature 1, comportamento restante inalterado) (contract §1; depends: T005)
- [x] T007 Testes FALHANDO de `validate_restore_source` em `tests/test_backup_restore.py`: `.sql.gz` válido → dict com path/is_gzip/size_bytes; `.sql` legado → dict com is_gzip=False; `CORROMPIDO` (via fixture `_corrupted_gz` + listagem) → `BackupError`; tamanho 0 → `BackupError`; traversal (`../../etc/passwd`) e inexistente → erro (BV via `get_backup_path`; spec FR-09, Testes D/E/F service-level) (depends: T006)
- [x] T008 Implementar `validate_restore_source(filename)` em `app/services/backup_service.py`: reuso de `get_backup_path` (regex/existência/path traversal), integridade via `list_backups()` (CORROMPIDO rejeita; `—` do `.sql` legado passa com validação de legibilidade), leitura de teste (gzip integral ou conteúdo `.sql` não vazio) (contract §2, research R4/R11; depends: T007)
- [x] T009 **Checkpoint foundational**: testes T002–T008 verdes; suíte completa intacta (397 + novos, RBAC lockout exceto) (depends: T002–T008)

---

## Phase 3: User Story 1 — Restaurar um backup válido (Priority: P1) 🎯 MVP

**Goal**: Usuário autorizado seleciona backup → informações → confirmação explícita → backup de segurança validado → restore → validação pós-restore → sucesso auditado

**Independent Test**: Teste A ponta a ponta (service + web): ciclo completo com executores fake gera sucesso, eventos completos e backup de segurança listado

### Implementation (TDD)

- [x] T010 [P] [US1] Testes FALHANDO do ciclo no service (Teste A service-level) em `tests/test_backup_restore.py`: `restore_backup(...)` com `_fake_import` → retorno `{restaurado, backup_seguranca, size_bytes}`; eventos na trilha na ordem `BACKUP_RESTORE_INICIADO` → `BACKUP_PRE_RESTORE_CRIADO` → `BACKUP_RESTORE_SUCESSO` (results SUCCESS; `new_data` referencia os 2 arquivos sem segredos); backup de segurança listado com Integridade OK; flag liberada ao final (BV-R1..R4; contract §5) (depends: T009)
- [x] T011 [US1] Implementar `BackupService.restore_backup(db, user, ip_address, filename, *, import_executor=None, security_backup_executor=None)` em `app/services/backup_service.py`: ordem invariável do contract §5 (valida fonte → INICIADO → backup de segurança via `generate_backup` — **`security_backup_executor` delegado como `dump_executor` do `generate_backup` (contract §5 passo 3, remediação U1); nenhum segundo caminho de geração (FR-02)** → valida segurança → PRE_RESTORE_CRIADO → import via `_run_mysql_import` — **função de módulo com implementação real** (credenciais via `MYSQL_PWD`, stderr nunca propagado, timeout); fake apenas nos testes via monkeypatch (remediação I1) → `validate_post_restore` → SUCCESS); falhas em qualquer etapa → `BACKUP_RESTORE_FALHA` com motivo seguro + raise `BackupError` (**nunca falso sucesso**; backup de segurança nunca removido — BV-R4); slot ocupado durante todo o ciclo, liberado em `finally` (depends: T010, T006, T008)
- [x] T012 [P] [US1] Testes FALHANDO web (Teste A web-level) em `tests/test_backup_restore.py`: admin autenticado; `GET /admin/backups/{name}/restaurar` → 200 com nome do arquivo, data/hora, tamanho, integridade, advertências (substituição + backup de segurança + nota de sessões) e **nenhum efeito** (sem eventos de execução, sem backup de segurança); `POST` do formulário → 303 redirect; após o redirect: mensagem de sucesso com os 2 arquivos; eventos completos na trilha (depends: T009)
- [x] T013 [US1] Rotas em `app/web/admin_routes.py` (contract §8): `GET /admin/backups/{filename}/restaurar` e `POST` de mesmo caminho, ambas `dependencies=[Depends(require_permission("backup.restaurar"))]`; GET coleta dados via `list_backups()` e renderiza o template (nunca executa); POST chama `restore_backup` com `_client_ip`, captura `BackupError` (mensagem segura no redirect) e redireciona para `/admin/backups` (padrão de flash da 015; depends: T011, T012)
- [x] T014 [US1] Template `app/web/templates/admin/backups.html` (ui-contract §§1–4): coluna/ação **Restaurar** por linha condicionada a `can('backup.restaurar')` (btn-outline-danger, ícone bi-arrow-counterclockwise); bloco de tela de informações (GET) com advertências em alert-danger, nota de sessões e formulário POST com botão "SIM, RESTAURAR BACKUP" + `confirm()` + desabilitar/"Restaurando…" no submit; estado `CORROMPIDO` → banner de erro e botão desabilitado; mensagens de sucesso/falha/concorrência (alerts; nenhum template novo, nenhum menu novo); **identificabilidade do backup de segurança (FR-12, remediação U2)**: nome exibido na mensagem de sucesso (ui-contract §4) + evento `BACKUP_PRE_RESTORE_CRIADO` na trilha; listagem da 016 inalterada (decisão R3 do research) (depends: T013)
- [x] T015 **Checkpoint US1 (MVP)**: Testes A (service + web) verdes; **Feature 1 inalterada** — `tests/test_backup_manual.py` 100% verde (depends: T011–T014)

---

## Phase 4: User Story 2 — Operação inacessível a não autorizados (Priority: P1)

**Goal**: Restore restrito por permissão própria, no backend e na UI

**Independent Test**: Teste B — usuário sem `backup.restaurar` recebe 403 nas duas rotas, sem eventos, sem alterações

- [x] T016 [P] [US2] Testes em `tests/test_backup_restore.py`: usuário do perfil Consulta → 403 no GET e no POST; **nenhum** evento `BACKUP_RESTORE_*`; banco inalterado (contagens estáveis); nenhum backup de segurança criado; usuário com `backup.gerenciar` mas **sem** `backup.restaurar` → 403 (separação das permissões — research R9); página da listagem renderiza a ação Restaurar **apenas** para quem tem a permissão (`can()`) (depends: T015)

---

## Phase 5: User Story 3 — Cancelamento e validações que impedem o restore (Priority: P1)

**Goal**: Nada executa sem condições seguras: cancelar não tem efeito; backups inválidos/inexistentes/fora do padrão nunca restauram

**Independent Test**: Testes C/D/E/F — cada recusa deixa o banco intocado

- [x] T017 [P] [US3] Testes em `tests/test_backup_restore.py`: **C** — cancelar = `confirm()` recusado ou navegação de volta (nenhum POST é enviado — remediação C1): GET da tela de informações não cria eventos de execução nem backup de segurança; **D** — backup `CORROMPIDO` → POST recusa com `BACKUP_RESTORE_FALHA`, banco intocado, **nenhum** backup de segurança criado (validação antes de tudo — BV-R1); **E** — inexistente → 404 sem eventos de execução; **F** — `../../etc/passwd` → bloqueado (404/400, nenhum evento) (depends: T015)

---

## Phase 6: User Story 4 — Falhas seguras e proteção de concorrência (Priority: P1)

**Goal**: Falha no backup de segurança não inicia restore; falha no import nunca é sucesso e preserva o backup de segurança; restore concorrente rejeitado

**Independent Test**: Testes G/H/J — cada falha registrada, nenhum falso sucesso, backup de segurança sempre disponível

- [x] T018 [P] [US4] Testes em `tests/test_backup_restore.py`: **G** — `security_backup_executor` que falha → `BACKUP_RESTORE_FALHA`, **nenhum** `BACKUP_PRE_RESTORE_CRIADO`/`SUCESSO`, banco intocado (contagens estáveis), slot liberado; **H** — `_failing_import` → `BACKUP_RESTORE_FALHA` com motivo seguro, backup de segurança **preservado e listado** (BV-R4), sem falso sucesso; **J** — com o slot ocupado (flag interna), segunda chamada → `BackupError` "Já existe uma restauração em andamento" **sem** evento novo; e `generate_backup` recusado durante restore (BV-R2) (depends: T015)

---

## Phase 7: User Story 5 — Confiança no resultado (Priority: P2)

**Goal**: Validação pós-restore real (conexão + tabelas essenciais + dados essenciais) antes de qualquer mensagem de sucesso

**Independent Test**: Teste I — `validate_post_restore` verde após o ciclo; sucesso só depois da validação

- [x] T019 [P] [US5] Testes em `tests/test_backup_restore.py`: `validate_post_restore(db_session)` direto → OK (SELECT 1 executável; tabelas essenciais presentes no SQLite de teste; contagens executáveis — somente leitura); após `restore_backup` de sucesso, a ordem dos eventos comprova que SUCESSO só ocorre **depois** da validação (BV-R3); falha simulada de pós-restore (monkeypatch que faz uma consulta essencial falhar) → `BACKUP_RESTORE_FALHA` (depends: T011)

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentação, escopo e validação final

- [x] T020 [P] Documentação (Princípio XI, quickstart DoD): `README.md` — seção de restauração (fluxo, confirmação, backup de segurança obrigatório, comportamento de sessões pós-restore, restauração manual como alternativa); `app/services/help_service.py` — seção coerente com a tela (o que acontece ao restaurar, backup de segurança, sessões) (depends: T015)
- [x] T021 [P] Verificação estática de escopo via `git diff` (quickstart DoD §4): alterações restritas a `backup_service.py`, `audit_service.py` (+8 linhas), `permission_service.py` (+1 permissão), `admin_routes.py` (+2 rotas), `admin/backups.html` (ação + telas), `tests/test_backup_restore.py` (novo), `README.md`, `help_service.py` — **rotas/fluxo da Feature 1, models e demais módulos intocados**; `grep` garantindo nenhuma credencial em código/logs/eventos (Princípio VI) (depends: T015)
- [x] T022 Validação final: regressão completa (`python3 -m pytest -q` verde, RBAC lockout exceto); quickstart §2 (A–K conferido); quickstart §3 no MariaDB real (com o usuário — se indisponível, registrar como limitação pendente); **Relatório Final Obrigatório §39** com as declarações literais (REUTILIZADO/IMPLEMENTADO/NÃO IMPLEMENTADO); marcar todas as tarefas `[X]` em `tasks.md` e reportar (depends: T015–T021)

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (T001)**: imediato — baseline e infra de testes
- **Foundational (T002–T009)**: BLOCKS todas as stories (permissão, eventos, slot, validação)
- **US1 (T010–T015)**: MVP — ciclo completo funcionando
- **US2/US3/US4 (T016–T018)**: todas dependem do checkpoint T015 (exercitam o ciclo pronto); entre si são paralelizáveis ([P])
- **US5 (T019)**: depende do orquestrador T011; paralelizável com US2–US4
- **Polish (T020–T022)**: após todas as stories

### Within US1
- Testes antes da implementação (T010/T012 vermelhos) → service (T011) → rotas (T013) → template (T014) → checkpoint (T015)

### Parallel Opportunities
- T002/T003 (seed) e T004 (audit) paralelizáveis com T005–T008 (arquivos distintos)
- T010/T012 (testes service/web) paralelizáveis
- T016/T017/T018/T019 (stories distintas, mesmo arquivo de teste — seções independentes) e T020/T021 (docs/escopo)

---

## Implementation Strategy

- **MVP primeiro**: Foundation + US1 → ciclo completo de restauração segura funcionando ponta a ponta com executores fake
- **Segurança como stories**: US2 (RBAC), US3 (recusas), US4 (falhas/concorrência) exercitam o ciclo pronto com contorno adversarial
- **Confiança por último**: US5 formaliza a validação pós-restore como critério de sucesso
- **Dump real**: apenas no quickstart §3 (MariaDB), como consolidado nas features 015/016

---

## Notes

- Executor de import sempre FAKE na suíte (SQLite) — dump real apenas na validação §3
- A única alteração no fluxo da Feature 1 é a **guarda de concorrência** no início de `generate_backup` (FR-17) — todo o restante intocado
- `git diff` como gate de escopo (T021) e relatório final §39 obrigatório (T022)
