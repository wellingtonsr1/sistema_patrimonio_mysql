---

description: "Task list for feature implementation"
---

# Tasks: Backup Manual do SisPatrimônio Pro

**Input**: Design documents from `/specs/015-backup-manual/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R8), data-model.md (BV-1..BV-4), contracts/service-contract.md, contracts/ui-contract.md, quickstart.md

**Tests**: Incluídos por exigência da spec (FR-012). TDD: escrever primeiro, garantir FALHA, depois implementar.

**Organization**: Por user story. Foundation = permissão/constantes/núcleo de listagem (bloqueia todas); US1 geração (service + rota web), US2 tela de listagem/menu, US3 download, US4 matriz de segurança/auditoria.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Projeto monolítico FastAPI existente: `app/services/`, `app/web/`, `tests/` na raiz.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline e padrões — nenhuma alteração de comportamento

- [x] T001 Rodar a suíte e registrar o baseline (`python3 -m pytest -q`): **362 passed + 1 falha pré-existente** `tests/test_rbac.py::test_lockout_after_failed_attempts` (fora do escopo — não corrigir, Princípio I). Capturar padrões para reuso: `app/web/admin_routes.py` (require_permission, mensagens de sucesso/erro por query param, `_client_ip`), `tests/test_rbac.py` (criação de usuário/perfil/permissão limitados para testes RBAC) e `tests/conftest.py` (fixture `client` admin) (depends: none)
- [x] T002 Criar o módulo de testes `tests/test_backup_manual.py` com infraestrutura: helper de **executor fake de dump** (grava conteúdo determinístico no caminho recebido — injeção via `dump_executor`, research R4), helper de limpeza de `data/backups/` gerados nos testes e helpers RBAC capturados em T001 — arquivo inicia sem testes de comportamento (depends: T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Permissão, constantes de auditoria, configuração e núcleo de listagem/validação — bloqueia TODAS as user stories

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase (RBAC e service núcleo são pré-requisito)

### Tests for Foundational (TDD — escrever primeiro, garantir FALHA)

- [x] T003 [P] Testes FALHANDO de permissão/seed em `tests/test_backup_manual.py`: `ensure_default_roles(db)` cria a permissão `backup.gerenciar` (módulo "Backup") e o perfil Administrador a possui; seed é idempotente (rodar 2x não duplica) (depends: T002)
- [x] T004 [P] Testes FALHANDO do núcleo do service em `tests/test_backup_manual.py`: `list_backups()` → [] com diretório vazio/inexistente; ignora arquivos fora do padrão `backup_YYYYMMDD_HHMMSS_micros.sql`; ordena do mais recente; `get_backup_path(nome)` → caminho em `data/backups/` para nome válido; levanta erro para nome fora do padrão (path traversal — R8) e para inexistente (depends: T002)

### Implementation for Foundational

- [x] T005 [P] Adicionar a permissão ao `PERMISSION_CATALOG` em `app/services/permission_service.py`: `{"name": "backup.gerenciar", "module": "Backup", "label": "Gerenciar backups", "description": "Gerar, listar e baixar backups manuais do sistema."}` — aditivo; seed idempotente existente concede ao Administrador (research R5)
- [x] T006 [P] Adicionar as constantes em `app/services/audit_service.py`: `ACTION_BACKUP_CREATED = "BACKUP_CRIADO"` e `ACTION_BACKUP_DOWNLOAD = "BACKUP_DOWNLOAD"` (precedente `ACTION_AD_*`; research R6)
- [x] T007 [P] Adicionar em `app/config.py`: `BACKUP_DIR = DATA_DIR / "backups"` (constante; criação on-demand fica no service — R3)
- [x] T008 Criar `app/services/backup_service.py` com o núcleo: regex estrita do padrão de nome, `list_backups()` (varredura, filtro por regex, ordenação desc, `{filename, timestamp, size_bytes}`), `get_backup_path(filename)` (valida regex + existência; erro → 404 na rota) — sem geração ainda (depends: T004, T007)
- [x] T009 Checkpoint foundational: `python3 -m pytest tests/test_backup_manual.py -q` verde (T003/T004) + suíte completa sem novas falhas além do baseline RBAC (depends: T003, T005, T006, T007, T008)

**Checkpoint**: Foundation pronta — permissão semeada, constantes disponíveis, listagem/validação de nome funcionando

---

## Phase 3: User Story 1 — Gerar backup manualmente (Priority: P1) 🎯 MVP

**Goal**: Usuário autorizado aciona a geração; sistema cria arquivo válido identificável por data/hora e audita o resultado

**Independent Test**: `generate_backup` com executor fake → arquivo em `data/backups/` com nome no padrão, retorno `{filename, timestamp, size_bytes}`, evento `BACKUP_CRIADO/SUCCESS`; falha → `FAILURE` sem artefato listado

### Tests for User Story 1 (TDD — escrever primeiro, garantir FALHA)

- [x] T010 [P] [US1] Testes FALHANDO da geração em `tests/test_backup_manual.py` (contract §1.1, data-model BV-3/BV-4): (a) sucesso com executor fake → arquivo criado, nome casa a regex, `size_bytes` > 0, retorno com os 3 campos; auditoria `BACKUP_CRIADO` com `result=SUCCESS` e `new_data={"arquivo", "tamanho_bytes"}`; (b) executor lança erro → exceção controlada propagada, auditoria `BACKUP_CRIADO` com `result=FAILURE` e descrição **sem** comando/credenciais, nenhum artefato listado após a falha; (c) gerações repetidas → nomes distintos (microssegundos) (depends: T009)
- [x] T011 [P] [US1] Testes FALHANDO da rota web em `tests/test_backup_manual.py` (ui-contract §1): POST `/admin/backups/gerar` com admin (executor fake **injetado no caminho web via monkeypatch de `backup_service._run_mysqldump`** — a rota de produção não passa o parâmetro `dump_executor`; **remediação U1**) → redirect para `/admin/backups` com mensagem de sucesso, arquivo criado e auditado; sem permissão → 403 e **nenhum** arquivo/evento (depends: T009)

### Implementation for User Story 1

- [x] T012 [US1] Implementar a geração em `app/services/backup_service.py`: `generate_backup(db, user, ip_address, *, dump_executor=None)` (contract §1.1: nome com microssegundos **em UTC** — remediação I1, garantir `BACKUP_DIR`, executor injetável, validação de arquivo > 0, auditoria SUCCESS/FAILURE, remoção de artefato parcial em falha) + `_run_mysqldump(path)` privado (contract §1.2: parse de `DATABASE_URL` em memória, `--single-transaction --no-tablespaces`, senha **somente** via `MYSQL_PWD` no ambiente do subprocesso — nunca em argv/erro; R1/R2) (depends: T008, T010)
- [x] T013 [US1] Implementar a rota POST `/admin/backups/gerar` em `app/web/admin_routes.py` (ui-contract §1: `require_permission("backup.gerenciar")`, chama o service, redirect com mensagem por query param no padrão existente; falha → mensagem de erro controlada) (depends: T011, T012)
- [x] T014 [US1] Checkpoint US1 (MVP de geração): testes T010/T011 verdes + suíte completa intacta (depends: T012, T013)

**Checkpoint**: US1 funcional e testável independentemente (service + acionamento web)

---

## Phase 4: User Story 2 — Listar e consultar backups (Priority: P1)

**Goal**: Tela Administração → Backups lista os backups disponíveis (data/hora, tamanho, mais recente primeiro) com item de menu por permissão

**Independent Test**: Após gerar via POST (US1), GET `/admin/backups` apresenta o backup no topo; sem permissão → 403; menu só com `can('backup.gerenciar')`

### Tests for User Story 2 (TDD — escrever primeiro, garantir FALHA)

- [x] T015 [P] [US2] Testes FALHANDO da tela em `tests/test_backup_manual.py` (ui-contract §2/§3): GET `/admin/backups` com admin → 200, colunas Arquivo/Data-Hora/Tamanho, ordenação desc (2+ backups pré-criados no repositório), estado vazio amigável; sem permissão → 403; `base.html` contém item "Backups" condicionado a `can('backup.gerenciar')` (ausente sem a permissão) (depends: T009)

### Implementation for User Story 2

- [x] T016 [US2] Implementar a tela: rota GET `/admin/backups` em `app/web/admin_routes.py` (chama `list_backups()`, formata tamanho human-readable no template) + template **novo** `app/web/templates/admin/backups.html` (ui-contract §2: card de listagem, botão "Gerar backup agora" → POST US1, links de download → US3, mensagens de sucesso/erro por query param) + item de menu "Backups" no bloco Administração de `app/web/templates/base.html` com `can('backup.gerenciar')` (depends: T015, T014)
- [x] T017 [US2] Checkpoint US2 (US1+US2 integradas): teste E2E — POST gerar → GET lista o novo backup no topo com data/hora e tamanho; suíte intacta (depends: T016)

**Checkpoint**: US1 + US2 funcionando juntas (geração refletida na listagem)

---

## Phase 5: User Story 3 — Baixar backup (Priority: P2)

**Goal**: Usuário autorizado baixa o arquivo armazenado; inexistente/fora do padrão → 404 sem tocar disco

**Independent Test**: GET download de backup existente serve exatamente os bytes gravados (attachment + auditoria); inexistente → 404 sem evento

### Tests for User Story 3 (TDD — escrever primeiro, garantir FALHA)

- [x] T018 [P] [US3] Testes FALHANDO do download em `tests/test_backup_manual.py` (contract §1.4, ui-contract §4, data-model BV-1): GET `/admin/backups/{filename}/download` com backup pré-criado → 200, corpo == bytes gravados (SC-003), header attachment com o nome, evento `BACKUP_DOWNLOAD` com `new_data={"arquivo"}`; sem permissão → 403; nome fora do padrão → 404 **sem** tocar disco e **sem** evento; nome válido inexistente → 404 **sem** evento (depends: T009)

### Implementation for User Story 3

- [x] T019 [US3] Implementar a rota GET `/admin/backups/{filename}/download` em `app/web/admin_routes.py`: valida via `get_backup_path` (404 antes de qualquer evento), `FileResponse` com attachment, `write_audit(ACTION_BACKUP_DOWNLOAD)` após servir (depends: T018, T008)
- [x] T020 [US3] Checkpoint US3: testes T018 verdes; todas as USs (1–3) funcionais (depends: T019)

**Checkpoint**: Ciclo completo gerar → listar → baixar funcionando

---

## Phase 6: User Story 4 — Matriz de segurança e rastreabilidade (Priority: P2)

**Goal**: Consolidação verificável do deny-by-default e da ausência de credenciais nos eventos

**Independent Test**: Matriz 3 rotas × (com/sem permissão) verde; eventos de auditoria contêm apenas filename/tamanho

### Tests for User Story 4 (consolidação — guardas da matriz completa)

- [x] T021 [P] [US4] Testes de guarda em `tests/test_backup_manual.py` (spec US4, SC-006): matriz completa — usuário autenticado **sem** `backup.gerenciar` recebe 403 em GET listagem, POST gerar e GET download (nenhum artefato/evento de backup criado nesses acessos); eventos `BACKUP_CRIADO`/`BACKUP_DOWNLOAD` da suíte contêm apenas `arquivo`/`tamanho_bytes` em `new_data` (sem credenciais/comando — Princípio VI) (depends: T020)
- [x] T022 [US4] Checkpoint US4: matriz verde; suíte intacta (depends: T021)

**Checkpoint**: Todas as user stories (1–4) concluídas e verificáveis

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentação, escopo e validação final

- [x] T023 [P] Atualizar documentação (Princípio XI, quickstart DoD): README seção 💾 (o que o backup contém, como gerar/listar/baixar, local `data/backups/`, **identificação por data/hora em UTC** — remediação I1, limitações: manual, sem agendamento, restauração por política operacional) + central de ajuda em `app/services/help_service.py` (nova seção Backup coerente com a tela)
- [x] T024 [P] Verificação estática de escopo via `git status`/`git diff` (quickstart DoD): alterações restritas a `backup_service.py` (novo), `admin_routes.py` (+3 rotas), `admin/backups.html` (novo), `base.html` (+1 item), `permission_service.py` (+1 permissão), `audit_service.py` (+2 constantes), `config.py` (+1 constante), `tests/test_backup_manual.py` (novo) — **zero** alterações em rotas/services/models existentes; `grep` garantindo nenhuma credencial em código/erros (Princípio VI)
- [x] T025 Validação final: executar o quickstart (§1 suíte; §2 cenários 1–7; §4 DoD) — §3 (dump real no MariaDB) fica como roteiro manual para o usuário; re-verificar a Constitution (checklist do plan.md); marcar todas as tarefas `[X]` em `tasks.md` e reportar (depends: T022, T023, T024)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — imediato
- **Foundational (Phase 2)**: depende do Setup; **BLOQUEIA todas as user stories** (permissão + constantes + núcleo do service)
- **US1 (Phase 3)**: primeira story — MVP de geração (service → rota web)
- **US2 (Phase 4)**: depende de US1 (a tela lista o que US1 gera; o botão aponta para a rota de US1)
- **US3 (Phase 5)**: depende da Foundation (service núcleo) e usa backups pré-criados/gerados — sequência natural após US2 (link na tela)
- **US4 (Phase 6)**: consolidação — depende de todas
- **Polish (Phase 7)**: depende de todas as stories

### Parallel Opportunities

- T003/T004 (testes foundation), T005/T006/T007 (edições aditivas em arquivos distintos) — paralelizáveis
- T010/T011 (US1), T015 (US2), T018 (US3), T021 (US4) — arquivos de teste distintos, mas no mesmo módulo: executar sequencialmente na prática para evitar conflito de edição
- T023/T024 (polish) paralelos

## Implementation Strategy

### MVP First (Foundation + US1)

1. Phases 1–2: Setup + Foundation (permissão semeada, constantes, núcleo)
2. Phase 3: US1 — geração completa (service + rota)
3. **STOP and VALIDATE**: geração via POST cria arquivo auditado (quickstart §2 cenário 1)

### Incremental Delivery

1. Foundation + US1 → geração auditada (MVP)
2. US2 → tela de listagem + menu
3. US3 → download com auditoria
4. US4 → matriz de segurança consolidada
5. Polish → docs, auditoria de escopo, DoD

### Notes

- TDD: cada bloco de testes escrito e FALHANDO antes da respectiva implementação
- Executor de dump sempre injetado nos testes (SQLite não roda mysqldump — research R4); dump real apenas no quickstart §3
- Segredo do banco: **somente** `MYSQL_PWD` no ambiente do subprocesso (R2) — nunca em argv/erros/auditoria
- Único arquivo de testes existente que NÃO é tocado: todos — o módulo novo é isolado; baseline RBAC permanece
- Commit após cada checkpoint
