---
description: "Task list for feature implementation"
---

# Tasks: Correção do Deadlock da Restauração de Backup (019)

**Input**: Design documents from `/specs/019-import-deadlock/`

**Prerequisites**: plan.md (required), spec.md (required), research.md (D1–D5/R1–R5), data-model.md, contracts/service-contract.md, quickstart.md

**Tests**: Incluídos — TDD obrigatório (Constitution VIII): testes escritos e executados **vermelhos antes** da implementação correspondente dentro de cada story.

**Organization**: Tasks grouped by user story (US1 P1 = restauração conclui; US2 P1 = deadline real; US3 P2 = modo manutenção).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: independente por ARQUIVO (nunca execução concorrente com a implementação que valida — lição 005)
- **[Story]**: US1/US2/US3 conforme spec.md
- Caminhos exatos em todas as descrições

## Path Conventions

- Single project: `app/` (service/web), `tests/` na raiz — conforme plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Alinhamento de escopo e patamar da suíte

- [x] T001 Ler plan.md, research.md (D1–D5, R1–R5), contracts/service-contract.md e quickstart.md da 019; confirmar que os arquivos afetados são exatamente: `app/database.py`, `app/services/backup_service.py`, `app/main.py`, `app/web/admin_routes.py`, `app/web/templates/admin/backups.html`, `app/web/templates/admin/503.html` (novo), `app/config.py`, `.env.example`, `tests/test_backup_restore.py`, README, docs — PARAR se o código real divergir dos contratos
- [x] T002 Executar `python -m pytest tests/ -q --tb=no` e registrar a baseline **439 passed / 1 failed** (lockout `test_rbac.py::test_lockout_after_failed_attempts` pré-existente) na seção Validation Results; política pós-019: patamar = **mesmas 1** + novos verdes; desvio ⇒ PARAR

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Gate dos fatos do diagnóstico antes de qualquer código

**⚠️ CRITICAL**: Nenhuma user story pode começar sem este gate

- [x] T003 Gate de fatos (research D1–D5) verificado no código real com as linhas citadas: D1 rota síncrona `admin_backup_restore_exec` (`app/web/admin_routes.py` L894–905) + import stdin no processo web (`_run_mysql_import`, `app/services/backup_service.py` L276+); D2 `proc.wait(timeout=)` não cobre o write do stdin; D3/D4 `get_db` fecha no fim do request (`app/database.py` L27–33) e `write_audit` comita na sessão recebida (`app/services/audit_service.py` L186); D5 privilégios sem global (SHOW GRANTS 2026-09-18 registrado). Registrar "OK" por fato em Validation Results — divergência ⇒ PARAR (FR-001/FR-002)

**Checkpoint**: Fundamentos confirmados — user stories podem começar

---

## Phase 3: User Story 1 — Restauração conclui sem travar o sistema (Priority: P1) 🎯 MVP

**Goal**: POST de restore valida/agenda e devolve o request; worker thread executa o ciclo destrutivo com sessões próprias e drena o pool antes do import — o dump não encontra metadata lock do próprio processo (SC-001, FR-003/FR-004/FR-006)

**Independent Test**: Com sessões abertas e pool em uso, iniciar restauração → conclui em tempo finito, banco íntegro (validação pós 017), aplicação responsiva, estado liberado

### Tests for User Story 1 (⚠️ escrever PRIMEIRO, executar VERMELHO)

- [x] T004 [P] [US1] Testes do worker/drenagem em `tests/test_backup_restore.py`: (a) `drain_engine()` fecha conexões ociosas do pool e aguarda quiescência (retorna bool); (b) worker do restore usa sessões próprias curtas — nenhuma sessão de request no ciclo destrutivo (spy: sessão passada ao restore NÃO aparece no import/pós-validação); (c) `restore_backup` valida a fonte e registra `BACKUP_RESTORE_INICIADO` ANTES de retornar (fluxo agendado); (d) backup de segurança criado e validado dentro do worker antes do import (ordem: validação → INICIADO → segurança → import — FR-004); (e) drenagem executada antes do import e pool utilizável na validação pós-restore; (f) falha na quiescência da drenagem → `BackupError` + estado liberado + backup de segurança disponível (sem falso sucesso). Fakes via `import_executor`/`security_backup_executor` (assinaturas 017 preservadas)
- [x] T005 [P] [US1] Testes do fluxo HTTP em `tests/test_backup_restore.py`: (a) POST `/admin/backups/{filename}/restaurar` válido responde **303** (padrão de redirect do fluxo web — não 202/JSON) sem bloquear o request até o fim do import (fake de import com `threading.Event`); (b) `GET /admin/backups/restaurar/status` retorna JSON `{active, phase, started_at, target_file, finished, ok, message}` sem segredos e exige `backup.restaurar`; (c) polling de status funciona durante (active=True, phase) e após (finished, ok); (d) concorrência: segunda restauração simultânea continua bloqueada pela guarda 017 (`_RESTORE_IN_PROGRESS`); (e) guarda externa de geração preservada: `generate_backup` SEM `_allow_during_restore` continua bloqueado durante a restauração em andamento (FR-015, regressão da 017). **Nota I7**: onde o worker tocar sessão, monkeypatch de `backup_service.SessionLocal` → `TestingSessionLocal` (padrão 018)

### Implementation for User Story 1

- [x] T006 [US1] Implementar `drain_engine()` em `app/database.py`: `engine.dispose()` + aguardar `pool.checkedout() == 0` com timeout curto; retorna bool; não altera `DATABASE_URL`, pool, URL nem engine existentes (contract §2)
- [x] T007 [US1] Implementar fluxo agendado + worker em `app/services/backup_service.py`: `restore_backup` (assinatura 017 preservada, `import_executor`/`security_backup_executor` mantidos) valida, audita INICIADO (worker, sessão própria), marca o slot de concorrência existente (`_RESTORE_LOCK`/`_RESTORE_IN_PROGRESS`/`_restore_slot` — **NÃO criar mecanismo paralelo**, FR-011) + `maintenance_mode` e retorna dict "em andamento"; nova `_execute_restore_cycle(...)` como thread com: backup de segurança → `drain_engine()` → `_run_mysql_import` → reabrir pool → `validate_post_restore` (sessão nova) → eventos SUCCESS/FAILURE; auditoria do worker SEMPRE em sessões próprias curtas (`SessionLocal()` no ponto de uso — D4/R5); `finally` libera o slot e encerra manutenção (contract §1.1–1.2)
- [x] T008 [US1] Atualizar rota `POST /admin/backups/{filename}/restaurar` (`admin_backup_restore_exec` em `app/web/admin_routes.py` — caminho EXISTENTE, PT) para fluxo 303 imediato + criar `GET /admin/backups/restaurar/status` (mesma permissão `backup.restaurar` — FR-014); rodar os testes de US1 até verde + regressão de `tests/test_backup_manual.py` e `tests/test_backup_restore.py` (patamar)

**Checkpoint**: US1 funcional e testável independentemente — restauração conclui sem auto-bloqueio (MVP!)

---

## Phase 4: User Story 2 — Falha de import é detectada em tempo finito (Priority: P1)

**Goal**: Deadline de relógio cobrindo TODAS as fases do import (write no stdin incluído — D2), limite configurável, diagnóstico técnico sem credenciais, estado liberado garantido (FR-007..FR-009, SC-002)

**Independent Test**: Import fake que bloqueia no write → aborta dentro do prazo configurado, `BACKUP_RESTORE_FALHA` com diagnóstico sanitizado, estado liberado, backup de segurança disponível

### Tests for User Story 2 (⚠️ escrever PRIMEIRO, executar VERMELHO)

- [x] T009 [P] [US2] Testes do deadline em `tests/test_backup_restore.py`: (a) import fake cujo stdin.write bloqueia (Evento segurado) com `BACKUP_IMPORT_TIMEOUT` baixo (monkeypatch em `backup_service`) → worker aborta dentro do prazo (assert de duração), subprocesso terminate()d, `BACKUP_RESTORE_FALHA` registrado e estado/manutenção liberados; (b) diagnóstico do timeout no log técnico contém etapa ("feed no stdin"), tempo decorrido e exit code — sem nunca conter a senha (padrão 018, Teste H); (c) import fake com returncode != 0 → falha honesta preservada (confirmação 017, sem falso sucesso); (d) arquivo parcial NUNCA é listado como backup válido (confirmação 015/017); (e) auditoria registra sucesso e falha conforme mecanismo existente (confirmação); (f) threads/processos não vazam: worker termina com timeout e o `join` não pendura o teste

### Implementation for User Story 2

- [x] T010 [US2] Adicionar `BACKUP_IMPORT_TIMEOUT` (opcional, default 900) em `app/config.py` — lida **APÓS** `load_dotenv()` (guarda da 018 contra o bug de posicionamento) e documentar em `.env.example` sem segredos (contract §5)
- [x] T011 [US2] Implementar watchdog do import em `app/services/backup_service.py`: feed do dump por **thread escritora dedicada**; worker aguarda término com prazo `BACKUP_IMPORT_TIMEOUT` (cobre o bloqueio no write — D2); estouro → `terminate()` (pipe quebra, escritora desbloqueia) + kill de segurança; diagnóstico técnico: etapa, tempo, exit code, stderr **sanitizado** (senha mascarada, padrão 018); rodar testes US2 até verde + regressão dos módulos de backup

**Checkpoint**: US1+US2 completas — restauração conclui E toda falha é detectada em tempo finito com diagnóstico

---

## Phase 5: User Story 3 — Sistema em manutenção durante a restauração (Priority: P2)

**Goal**: Middleware em memória (sem banco) serve 503 amigável em todas as páginas durante a restauração, com whitelist mínima, encerramento automático e crash-safety (FR-010..FR-013, SC-003)

**Independent Test**: Restauração ativa → outra sessão acessa páginas → recebe manutenção amigável; concluída → acesso normal retorna; restart do processo → sistema NÃO persiste em manutenção

### Tests for User Story 3 (⚠️ escrever PRIMEIRO, executar VERMELHO)

- [x] T012 [P] [US3] Testes da manutenção em `tests/test_backup_restore.py`: (a) middleware ativo responde HTTP 503 com `admin/503.html` em rota qualquer SEM tocar o banco (dependência `get_db` quebrada no teste — a resposta não falha: FR-010/F1 da revisão); (b) whitelist mínima: rota de status do restore e login/health acessíveis; NADA além (as demais 503); (c) RBAC intacto: rotas isentas mantêm suas permissões atuais; (d) encerramento automático: sucesso e falha do worker limpam a manutenção (finally — FR-012); (e) crash-safety: exceção na thread do worker → manutenção encerrada, estado liberado, falha auditada (FR-011/FR-009); (f) estado nunca persistido: novo processo/teste começa sem manutenção (flag em memória — R3)

### Implementation for User Story 3

- [x] T013 [US3] Implementar `maintenance_mode` (dict em memória: active/started_at/phase/target_file) em `app/services/backup_service.py` (gerido pelo slot de concorrência existente `_restore_slot` — FR-011) + middleware em `app/main.py` checando ANTES de qualquer dependência de banco (gate em memória, F1) com resposta 503 renderizando o novo template `app/web/templates/admin/503.html` (padrão visual do sistema, zero queries) + whitelist como constantes (contract §3)
- [x] T014 [US3] Indicador na tela de backups `app/web/templates/admin/backups.html`: banner "restauração em andamento — modo manutenção ativo" + polling leve (~3 s) do status enquanto ativa + botão de restaurar desabilitado durante a operação (defesa extra — FR-013/R4); rodar testes US3 até verde

**Checkpoint**: US1+US2+US3 completas — ciclo seguro, falha diagnosticável e manutenção protegida

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regressão global, documentação, fechamento e prova real

- [x] T015 Suíte completa `python -m pytest tests/ -q --tb=no` no patamar: **439 + novos verdes / 1 failed** (apenas o lockout pré-existente); investigar QUALQUER falha além dela — zero regressão (FR-014..FR-017, SC-005)
- [x] T016 [P] Documentação: `README.md` (§Backup: comportamento do restore pós-019 — 202/polling/manutenção — + variável `BACKUP_IMPORT_TIMEOUT`) e `docs/ARQUITETURA_E_MANUTENCAO.md` (worker/drenagem/deadline/manutenção, atualizar a nota do aviso `docs/AVISO_RESTORE_DEADLOCK.md` — correção implementada)
- [x] T017 Fechamento: conferir via `git status` que o escopo são exatamente os arquivos do T001 (zero models/rotas de outros módulos/RBAC/AD); preencher Validation Results; marcar tasks concluídas
- [ ] T018 Teste real no Windows pelo operador (quickstart §3): gerar backup → registro rastreável → restaurar pela tela → 202 + manutenção → conclusão com dado de volta → auditoria coerente; opcional: timeout com `BACKUP_IMPORT_TIMEOUT=5` + cliente renomeado; Linux quando disponível (quickstart §4)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)**: imediato
- **Foundational (2)**: depende do Setup — BLOQUEIA todas as stories
- **US1 (3)** → **US2 (4)**: US2 estende o import do worker criado em US1 (mesmo arquivo, `backup_service.py`) — sequencial por arquivo
- **US3 (5)**: depende de US1 (o worker é quem define/limpa a manutenção)
- **Polish (6)**: depende de todas as stories concluídas

### User Story Dependencies

- **US1 (P1)**: start após Foundational — sem dependência de outras stories (MVP)
- **US2 (P1)**: requer worker de US1 (o watchdog vive no ciclo do worker)
- **US3 (P2)**: requer fluxo agendado de US1 (a flag existe antes da thread iniciar — nenhuma janela sem manutenção)

### Within Each User Story

- Testes PRIMEIRO (vermelho confirmado), depois implementação, depois verde + regressão
- Services antes de rotas/telas
- **[P] marca independência de arquivo entre blocos de teste — os testes de uma story NUNCA rodam em paralelo com a implementação que os valida** (lição 005)

### Parallel Opportunities

- T004 ∥ T005 (mesma story, arquivos de teste distintos dos de produção — escrever juntos, executar vermelhos juntos)
- T009 ∥ T012 (blocos de teste de stories diferentes)
- T016 é o único [P] do Polish (documentação, arquivo próprio)
- Nenhuma implementação paralela: `backup_service.py` é o gargalo deliberado (US1→US2→US3)

---

## Parallel Example: User Story 1

```bash
# Escrever os dois blocos de teste juntos, depois rodar vermelhos juntos:
Task: "T004 [P] [US1] Testes do worker/drenagem em tests/test_backup_restore.py"
Task: "T005 [P] [US1] Testes do fluxo HTTP em tests/test_backup_restore.py"

# Implementação sequencial (mesma cadeia de dependências):
T006 drain_engine → T007 worker → T008 rotas → verde + regressão
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fases 1–2: Setup + gate de fatos
2. Fase 3: US1 completa (worker + drenagem + 202)
3. **STOP and VALIDATE**: suíte no patamar + teste real manual
4. A auto-deadlock já está eliminada no MVP

### Incremental Delivery

- +US2: toda falha detectável em tempo finito com diagnóstico
- +US3: manutenção amigável protege a operação e informa o operador
- Polish: docs + prova real no Windows

---

## Validation Results

> Preencher durante o implement — NADA marcado antecipadamente

### Baseline (T002)

- [x] Suíte antes das mudanças: **439 passed / 1 failed** (lockout `test_rbac.py::test_lockout_after_failed_attempts` pré-existente — medido nesta sessão)

### Gate de fatos (T003)

- [x] D1 (rota síncrona + import stdin no processo web): **OK** — `admin_backup_restore_exec` L892–905 chamava `restore_backup(db, actor, ...)` sincronamente; `_run_mysql_import` L276+ alimenta stdin no processo web
- [x] D2 (wait não cobre o write): **OK** — `proc.wait(timeout=_IMPORT_TIMEOUT_SECONDS)` só após o loop `stdin.write(chunk)` sem limite
- [x] D3/D4 (get_db + write_audit L186): **OK** — `get_db` fecha no fim do request; `write_audit` comita na sessão recebida (audit_service L186)
- [x] D5 (privilégios sem global — SHOW GRANTS 2026-09-18): **OK** — registrado na revisão da spec

### Suíte por story

- [x] US1 vermelho (T004/T005): **15/15 failed** antes da implementação (TDD)
- [x] US1 verde + regressão (T008): **verde** + `test_backup_manual.py` intocado
- [x] US2 vermelho (T009): incluído no vermelho inicial (T009a/b/c)
- [x] US2 verde + regressão (T011): **verde** (timeout aborta no prazo; diagnóstico sem credenciais)
- [x] US3 vermelho (T012): incluído no vermelho inicial (503/whitelist/crash-safety)
- [x] US3 verde (T014): **verde** (503 sem banco, whitelist mínima, encerramento automático, crash-safety, não-persistência)
- [x] Suíte final no patamar (T015): **454 passed / 1 failed** (439 + 15 novos; a única falha é o lockout pré-existente)

### Prova real (T018 — operador)

- [ ] Windows: pendente (quickstart §3 — restauração pela tela com manutenção, 303 imediato, dado de volta, auditoria; opcional timeout com `BACKUP_IMPORT_TIMEOUT=5`)
- [ ] Linux (quando disponível): pendente (quickstart §4)

---

## Notes

- [P] tasks = arquivos distintos, sem dependência de tarefas incompletas
- [Story] label mapeia para a spec para rastreabilidade
- Cada story é independente e testável; parar nos checkpoints valida o incremento
- Verificar testes vermelhos antes de implementar
- Commit após cada tarefa ou grupo lógico
- Evitar: tarefas vagas, conflito de arquivo, dependência entre stories que quebre independência
