---
description: "Task list for feature 026 — immediate status update of the automatic backup indicator"
---

# Tasks: Correção da Atualização Imediata do Status do Backup Automático

**Input**: Design documents from `/specs/026-correcao-status-backup/`

**Prerequisites**: plan.md, spec.md, research.md (causa R1, decisão R2/R3, testes R5), data-model.md (fluxo ANTES×DEPOIS), contracts/status-source-contract.md (fontes obrigatórias + proibições), quickstart.md (validação em 6 passos)

**Tests**: SIM — a spec exige testes do fluxo real (FR-009), reprodução da causa antes da correção (Assumption 1/§45.1) e regressão (FR-010). Ordem TDD: testes primeiro (falham no código antigo), depois a correção mínima.

**Organization**: Tasks por user story com ordem de execução TDD (US3 testes → US2 correção → US1 validação → US4 preservação/relatório). **Regra transversal** (contrato §2): proibido alterar `backup_scheduler.py`, `backup_service.py`, `backup_config_service.py`, `app/models/backup_config.py`, banco, docs; proibido reload JS/segunda fonte; proibido enfraquecer testes existentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- Projeto único: `app/` + `tests/` na raiz. Arquivos esperados no diff: `app/web/templates/admin/backups.html`, `app/web/admin_routes.py` (somente se indispensável), `tests/test_backup_config.py`, `specs/026-correcao-status-backup/relatorio.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline de preservação (briefing §44)

- [x] T001 Registrar baseline: `git status --porcelain` e `git diff --stat` no rascunho do relatório (`specs/026-correcao-status-backup/relatorio.md`) — condição esperada: limpo fora de `specs/026-…` e `.specify/feature.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Confirmar âncoras e ausência de dependência de testes existentes ao badge

**⚠️ CRITICAL**: Nenhuma alteração antes deste phase

- [x] T002 [P] Verificar âncoras no código atual e registrar no relatório: card "Backup Automático" em `app/web/templates/admin/backups.html` (~L93–101 — badge via `auto_status.enabled`), contextos `auto_status`/`config_form` em `app/web/admin_routes.py` (`admin_backups` ~L832/840; `admin_backup_config_form` ~L894/896) e consumidores de `scheduler_status()` (research R6); **confirmar que NENHUM teste existente afirma o badge via `auto_status`** (varredura em `tests/`) — se houver, registrar qual e planejar adaptação legítima mínima
- [x] T003 [P] Criar o esqueleto do relatório `specs/026-correcao-status-backup/relatorio.md` com as 6 seções do briefing §45 (causa / arquivos / motivos / fluxo corrigido / testes executados / limitações)

**Checkpoint**: Âncoras confirmadas — testes podem ser escritos

---

## Phase 3: User Story 3 — Testes do fluxo real e reprodução da causa (Priority: P1) 🎯 MVP

**Goal**: Testes automatizados escritos ANTES da correção: reproduzem o problema no código antigo (evidência da causa — §45.1) e cobrem o fluxo real (ativação, desativação, repetição, com outros campos, idempotência F5)

**Independent Test**: `pytest tests/test_backup_config.py -q` no código ANTIGO → testes de fluxo falham com o badge mostrando o valor antigo (reprodução)

### Tests for User Story 3 (TDD — escrever primeiro, ver FALHAR) ⚠️

- [x] T004 [US3] Escrever os novos testes em `tests/test_backup_config.py` (padrão/fixtures existentes: `client` admin, `fixed_fallbacks`, `seeded_config`): (a) **teste-documentação da causa** — monkeypatch de `backup_scheduler._current_effective` com `auto_enabled` CONTRÁRIO ao persistido, POST salvando o toggle oposto com `follow_redirects=True`, assert do badge "Agendamento" com o valor NOVO (no código antigo falha mostrando o antigo); (b) **ativação** — config off → POST `auto_enabled=true` → HTML contém badge "Ativado"; (c) **desativação** — config on → POST `false` → "Desativado"; (d) **repetição** off→on→off→on→off com assert a cada POST (briefing §26); (e) **com outros campos** — toggle+horário e desativar+retenção (§28); (f) **idempotência F5** — segundo GET consecutivo idêntico ao primeiro (§29). Executar NO CÓDIGO ANTIGO e registrar resultado da reprodução no relatório (§45.1)
- [x] T005 [P] [US3] Baseline de regressão pré-mudança: executar `pytest tests/test_backup_config.py tests/test_backup_automatico.py tests/test_backup_retencao.py tests/test_backup_monitoramento.py -q` no código antigo e registrar o estado (esperado: verde — baseline para comparação pós-correção)

**Checkpoint**: Causa reproduzida por teste (não hipótese) — correção liberada

---

## Phase 4: User Story 2 — Correção na origem, fonte única (Priority: P1)

**Goal**: Badge/frequência/horário do card passam a ler da configuração efetiva por request (`config_form.*`); running/próximo/último permanecem de `auto_status`; zero diff em scheduler/service/model/banco; sem reload/segunda fonte

**Independent Test**: contrato §1 conferido no template; suíte dos novos testes passa; diff mínimo (quickstart Passo 4)

### Implementation for User Story 2

- [x] T006 [US2] Aplicar a correção em `app/web/templates/admin/backups.html` (card "Backup Automático", ~L93–101): badge Ativado/Desativado ← `config_form.auto_enabled`; frequência exibida ← `config_form.schedule`; horário ← `config_form.time` (string "HH:MM" — mesmo formato; sem conversão); MANTER `running`/`next_run_local`/`last_result` de `auto_status.*` (contrato §1). `config_form` está sempre presente nos 2 GETs (injetado com `create=False` em `admin_routes.py:840`/`:894`) — sem guard adicional; nenhuma mudança visual/estrutural além da fonte dos valores
- [x] T007 [US2] Verificar se algum ajuste de contexto é INDISPENSÁVEL em `app/web/admin_routes.py` (esperado: NENHUM — ambas as rotas já fornecem `config_form`); se um ajuste mínimo for realmente necessário, aplicá-lo com justificativa registrada no relatório (§45.2/§45.3); executar `pytest tests/test_backup_config.py -q` e confirmar os novos testes verdes (reprodução da causa agora irrelevante ao resultado — fluxo correto independentemente do snapshot)

**Checkpoint**: US2 completa — correção na origem, testes verdes (US1 entregue em comportamento)

---

## Phase 5: User Story 1 — Validação do indicador imediato (Priority: P1)

**Goal**: Comportamento ponta a ponta confirmado: salvar → redirect → GET → badge correto imediatamente, nas duas direções e nas variações do briefing

**Independent Test**: suíte completa relacionada verde + quickstart Passos 1–5

### Implementation for User Story 1

- [x] T008 [US1] Executar a validação do `specs/026-correcao-status-backup/quickstart.md` (Passos 1–5): reprodução já registrada (Passo 1 — T004); novos testes verdes (Passo 2); regressão completa pós-mudança comparada ao baseline de T005 (Passo 3); inspeção do diff (Passo 4 — somente template/rota-se-necessário/testes); conferência do contrato de fontes no template (Passo 5); registrar cada resultado no relatório (§45.5 — somente o que foi executado)

**Checkpoint**: US1 validada por automação — indicador imediato comprovado (SC-001/SC-002/SC-003)

---

## Phase 6: User Story 4 — Preservação e relatório final (Priority: P2)

**Goal**: Preservação comprovada (SC-004) e relatório final completo (§45)

**Independent Test**: `git diff` confinado aos arquivos previstos; relatório com causa confirmada, arquivos/motivos, fluxo, testes executados e limitações

### Implementation for User Story 4

- [x] T009 [P] [US4] Verificação final de preservação (briefing §44): `git status`/`git diff --stat`/`git diff` — confirmar ZERO diff em `backup_scheduler.py`, `backup_service.py`, `backup_config_service.py`, `app/models/backup_config.py`, banco, migrations, docs, auditoria, RBAC; testes manuais de navegador quando o ambiente permitir (quickstart Passo 6: F5, botão direito, checkbox, reinício, dois navegadores) — registrar SOMENTE os executados
- [x] T010 [US4] Consolidar o relatório final `specs/026-correcao-status-backup/relatorio.md` (§45): causa confirmada com evidência (cadeia R1 + resultado da reprodução de T004); arquivos alterados e por quê; fluxo corrigido (POST → persistência → redirect 303 → GET → `get_effective_config` → template → indicador); testes executados com resultado; limitações honestas

**Checkpoint**: US4 completa — entrega validada, preservada e documentada

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA testes e correção (âncoras + ausência de dependência de testes antigos ao badge)
- **US3 (Phase 3)**: depende da Foundational — TDD: testes falham no código antigo (reprodução = evidência da causa)
- **US2 (Phase 4)**: depende de T004 (reprodução registrada) — T006 (template) então T007 (rota, só se indispensável + verificação verde)
- **US1 (Phase 5)**: depende de T007 — validação completa
- **US4 (Phase 6)**: depende de T008 — preservação e relatório final

### Parallel Opportunities

- T002 + T003 (Foundational) em paralelo
- T005 em paralelo com T004 (baseline de regressão no código antigo)
- T009 em paralelo com T010 (após T008)

### Critical Path

T001 → T002/T003 → T004 → T006 → T007 → T008 → T010

---

## Implementation Strategy

### MVP First (US3 → US2)

1. Complete Phase 1–2 (baseline + âncoras)
2. Complete Phase 3: US3 (testes + reprodução no código antigo) — **STOP and VALIDATE**: a causa está provada por teste
3. Complete Phase 4: US2 (correção mínima) — novos testes verdes

### Incremental Delivery

1. MVP (US3+US2) → comportamento corrigido e travado por testes
2. +US1 → validação ponta a ponta (quickstart)
3. +US4 → preservação comprovada + relatório final

### Notes

- Ordem TDD obrigatória: T004 ANTES de T006 (a reprodução no código antigo é a evidência exigida pelo §45.1)
- Correção predominante no template — as duas rotas JÁ fornecem `config_form` (research R3); `admin_routes.py` só entra em cena se algo indispensável for constatado (T007)
- Proibições do contrato §2 prevalecem sobre qualquer melhoria "óbvia" durante a edição
- Nenhum commit/push automático — decisão do usuário após a entrega
