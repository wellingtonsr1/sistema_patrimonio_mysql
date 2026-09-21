# Tasks: Correção do Ciclo de Backup, Restauração e Agendamento Automático

**Feature**: 028-correcao-ciclo-backup · **Branch**: `028-correcao-ciclo-backup` · **Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md)

**Baseline pré-028 (medida em 2026-09-18): 543 passed / 1 failed** (`tests/test_backup_config.py::test_anti_regressao_default_desativado_no_codigo_real` — defasagem PRÉ-existente, fora do escopo; NÃO enfraquecer).

## Conventions

- **TDD por story**: os testes da story são escritos e executados VERMELHOS antes da implementação correspondente (Constitution VIII; lição 005). `[P]` marca independência de ARQUIVO entre blocos de teste — nunca execução concorrente com a implementação que valida.
- Worker/thread de teste: monkeypatch `SessionLocal` → `TestingSessionLocal` no módulo alvo (padrão 018/019 — lição conftest); executores injetados (`import_executor`/`security_backup_executor` — fakes 017/019 continuam válidos).
- Nenhuma credencial/segredo em logs, testes ou auditoria (Constitution VI). Auditoria: nenhum evento novo (research R6).

## Phase 1 — Setup

- [x] T001 Confirmar escopo e símbolos citados nos contratos no código atual: `_execute_restore_cycle` (backup_service.py), bloco de disparo + `_should_catch_up`/`_cycle_window_utc` (backup_scheduler.py), `_MAINTENANCE_WHITELIST_PREFIXES` + middleware (main.py), contexto de `admin_backups` (admin_routes.py) — divergência com contracts/service-contract.md ⇒ PARAR e reportar
- [x] T002 Medir baseline real da suíte (`python -m pytest tests/ -q`) e registrar no Validation Results — patamar esperado 543/1; divergência ⇒ investigar antes de qualquer edição

## Phase 2 — Foundational (gate de fatos)

- [x] T003 Reconfirmar no código real os fatos D3/D5/D7 do research.md com linhas: condição impossível de disparo no `_scheduler_loop`; ausência de `/admin/backups` na whitelist; middleware por prefixo método-cego; dependências de banco no contexto da rota (`types_by_filename`, `retention_monitoring_summary`, `config_form`) vs. segurança de `scheduler_status()`/`restore_status()` — divergência ⇒ PARAR

## Phase 3 — US1: Tipo dos backups preservado após restauração (P1)

**Goal**: reconciliação pós-import devolve aos arquivos presentes no disco o tipo capturado antes da substituição do banco (pré-restauração permanece PRE_RESTAURACAO; sem fallback MANUAL; sem inferência por nome).

**Independent test**: worker com executores injetados — ciclo conclui e arquivos/registros mantêm tipos.

- [x] T004 [P] [US1] Testes TDD vermelhos em tests/test_backup_restore.py: (1) snapshot capturado antes da drenagem inclui o registro do próprio pré-restauração; (2) após ciclo com import_executor que substitui os registros (simulação do import), arquivos presentes no disco recuperam tipo/status/timestamp/size/sha capturados (INSERT para perdido; UPDATE para divergente); (3) pré-restauração permanece PRE_RESTAURACAO (nunca MANUAL); (4) best-effort: falha de reconciliação não altera resultado do ciclo, auditoria emitida nem liberação de slot/manutenção; (5) arquivo inexistente no disco → nenhum registro criado; (6) `removed_at/removed_reason` nunca tocados; (7) nenhum duplicado (UNIQUE filename respeitada)
- [x] T005 [US1] Implementar em app/services/backup_service.py (contracts §1.2): captura do snapshot em memória entre a auditoria PRE_RESTORE e a fase `importando` (sessão própria e curta) + reconciliação após `validate_post_restore` e no caminho pós-falha-de-validação, sempre antes do `finally`; best-effort com log; assinatura do `_execute_restore_cycle` preservada; `generate_backup` intocado
- [x] T006 [US1] Verde US1 + regressão do módulo: testes 017/019 de restore continuam passando (adaptações só se comportamento previsto nos contratos)

## Phase 4 — US2: Backup automático executa no horário (P1)

**Goal**: disparo por execução devida (critério do catch-up) com 1 tentativa por ciclo; guardas e catch-up existentes intactos.

**Independent test**: `start_scheduler(clock=injetado)` + sessões de teste — 1 AUTOMATICO/SUCCESS por ciclo, sem duplicados.

- [x] T007 [P] [US2] Testes TDD vermelhos em tests/test_backup_automatico.py com relógio injetado: (1) horário devido no ciclo sem SUCCESS → 1 backup AUTOMATICO/SUCCESS; (2) tick seguinte (30 s) → nenhum segundo backup no mesmo ciclo; (3) semanal → só no dia configurado; (4) catch-up + disparo normal no mesmo ciclo → no máximo 1 execução (marca de ciclo cobre os dois caminhos); (5) enabled=False → nada dispara e nada é marcado; (6) restore em andamento → adiado (guarda preservada) e ciclo não consumido indevidamente; (7) falha do backup no ciclo → sem retry a cada 30 s (1 tentativa por ciclo); (8) `scheduler_status()` intacto (`next_run_local` para exibição)
- [x] T008 [US2] Implementar em app/services/backup_scheduler.py (contracts §2): bloco de disparo do `_scheduler_loop` → sessão curta por tick + `_should_catch_up(now, db)` + marca `_attempted_cycle_keys` (chave = início UTC da janela; anti-crescimento; limpa por restart); catch-up também marca; TYPE_CHECKING para `EffectiveBackupConfig` (R5); guardas `_AUTO_RUNNING`/`restore_in_progress()`/`generate_backup` em ordem invariável; `scheduler_status`/`start_scheduler`/`stop_scheduler` intactos
- [x] T009 [US2] Verde US2 + regressão do scheduler: testes existentes das features 020/021/022 (tests/test_backup_automatico.py, tests/test_backup_retencao.py, tests/test_backup_config.py) continuam passando

## Phase 5 — US3: Acompanhamento da restauração sem 503 indevido (P2)

**Goal**: durante manutenção, GET `/admin/backups` responde em modo degradado (sem queries); POSTs continuam 503; 503 legítimo preservado no resto.

**Independent test**: TestClient com manutenção ativa e executores injetados — GET 200 degradado, POSTs bloqueados.

- [x] T010 [P] [US3] Testes TDD vermelhos em tests/test_backup_manual.py (padrão de client existente — testes web de backups L234+): (1) manutenção ativa + GET /admin/backups com usuário `backup.gerenciar` → 200 (não 503) com contexto degradado (`config_form=None`, `types_by_filename={}`, `restore_status` presente); (2) nenhuma query de listagem executada no modo degradado (spy/monkeypatch em BackupRecord query ou equivalentes); (3) POST /admin/backups/gerar durante manutenção → 503 (FR-018); (4) POST restaurar durante manutenção → 503; (5) sem permissão `backup.gerenciar` → acesso negado existente (middleware não concede); (6) outra página administrativa → 503 legítimo; (7) template renderiza com `config_form=None` (guardas existentes L103/L155); (8) término do ciclo → tela volta ao normal
- [x] T011 [US3] Implementar: main.py — caso especial no middleware (método GET/HEAD no caminho exato `/admin/backups`, comentado com justificativa D6; whitelist de prefixos intacta); admin_routes.py — `admin_backups` em modo degradado quando `restore_status()["active"]` (sem queries; mantém `restore_status` + `auto_status`); backups.html — estado vazio da tabela com mensagem "listagem indisponível durante a restauração" (guardas de `config_form` JÁ EXISTEM em L103/L155 — nenhum guarda novo); banner/polling/botões da 019 reutilizados sem alteração
- [x] T012 [US3] Verde US3 + regressão dos testes de manutenção da 019 (isenção não quebra whitelist/status)

## Phase 6 — Polish & Cross-Cutting

- [x] T013 Suíte completa no patamar: `python -m pytest tests/ -q` → **543 + novos verdes / mesma 1 failed pré-existente** — registrar no Validation Results (nenhuma nova falha permitida)
- [x] T014 [P] Documentação fiel (Constitution XI): README.md + docs/ARQUITETURA_E_MANUTENCAO.md — seção 028: reconciliação pós-import (o que é capturado/retornado), disparo por execução devida com 1 tentativa por ciclo, acompanhamento durante manutenção (GET degradado, escritas bloqueadas), exigência de restart após deploy
- [x] T015 Fechamento: escopo via `git status --porcelain` == {backup_service.py, backup_scheduler.py, main.py, admin_routes.py, backups.html, tests, docs, specs/028*}; nenhum segredo/credencial em logs/testes/auditoria; marcar tasks concluídas e preencher Validation Results
- [x] T016 Validação manual pelo operador (quickstart §4, Windows/MariaDB real): restart do servidor; backup automático dispara no horário (sem duplicados); tipos corretos após restore; acompanhamento sem 503 na tela durante ciclo; 503 legítimo em outra página — marcar somente após execução real

## Dependency Graph

```text
T001 → T002 → T003 ─┬─→ [US1] T004 → T005 → T006 ─┐
                    ├─→ [US2] T007 → T008 → T009 ─┼─→ T013 → T014/T015 → T016
                    └─→ [US3] T010 → T011 → T012 ─┘
```

US1/US2/US3 são independentes entre si (arquivos distintos); todas dependem do gate T003.

## Parallel Opportunities

- T004/T007/T010 são blocos de teste em arquivos distintos (independentes entre si) — mas cada bloco é escrito e executado vermelho ANTES da sua implementação (nunca em paralelo com ela).
- T014 (docs) é independente do código em execução.

## Implementation Strategy

- **MVP**: US1 + US2 (P1) — confiança na tela e proteção automática de dados restauradas. US3 (P2) completa a experiência do operador.
- **Ordem sugerida**: gate → US1 → US2 → US3 → polish → validação manual.
- A qualquer divergência código × contrato: PARAR e reportar (não improvisar).

## Validation Results

- [x] Baseline medida (T002): **543 passed / 1 failed** (anti-regressão pré-existente)
- [x] Gate de fatos D3/D5/D7 (T003) — provas frescas com linhas (L826 scheduler; whitelist sem a tela; guardas L103/L155)
- [x] US1 testes vermelhos (T004): 5/5 (comportamento ausente)
- [x] US1 verde (T006) — 5/5 novos + 46/46 no módulo restore
- [x] US2 testes vermelhos (T007): 7/8 (7 falham por `_evaluate_tick` inexistente; 1 verde é o de status existente — correto)
- [x] US2 verde (T009) — 23/23 no módulo scheduler
- [x] US3 testes vermelhos (T010): 3/3 (503 atual / modo degradado ausente)
- [x] US3 verde (T012) — 14/14 us3 no módulo manual
- [x] Suíte completa (T013): **564 passed / 1 failed** (a 1 pré-existente; 543 + 21 novos — zero novas falhas)
- [x] Docs (T014) — README (seções backup automático e restauração) + ARQUITETURA_E_MANUTENCAO (linha Backup/restauração)
- [x] Escopo + sem segredos (T015) — `git status` exato ao previsto; nenhum segredo/credencial
- [x] Validação manual Windows (T016) — **executada em produção real (MariaDB, 21/09)**: restart do servidor (12:29) → scheduler leu config persistida (enabled=True, daily); disparo por execução devida **provado ao vivo**: registro do ciclo marcado FAILURE artificialmente → tick seguinte gerou 1× AUTOMATICO/SUCCESS (12:50:39, evento BACKUP_AUTOMATICO_SUCESSO) e o tick 30 s seguinte **não duplicou**; tipos renderizados na tela real (badge PRÉ-RESTAURAÇÃO visível no print do operador; registros MANUAL/AUTOMATICO/PRE_RESTAURACAO mapeados); tela /admin/backups acessível ao operador durante ciclos de restore reais (12:12–12:31, modo degradado ativo). Status do registro alterado no teste foi restaurado ao real (SUCCESS). Confirmação opcional: ciclo natural de amanhã 12:32

**Limitação registrada (infra de teste, pré-existente)**: executando `test_backup_restore.py` ANTES de `test_backup_automatico.py` (ordem não-canônica), os dumps falsos dos testes de restore recriam as tabelas no SQLite compartilhado e a linha `backup_config` da fixture se perde → os ticks do scheduler não disparam nessa ordem. Nunca ocorre na suíte real (ordem alfabética: scheduler antes de restore) nem em produção (MariaDB, conexões independentes). Não é código da 028 nem de produção — sem correção nesta feature (fora de escopo).
