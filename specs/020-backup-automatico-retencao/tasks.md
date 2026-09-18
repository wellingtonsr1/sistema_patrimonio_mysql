# Tasks: Backup Automático e Política de Retenção

**Input**: Design documents from `/specs/020-backup-automatico-retencao/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/service-contract.md ✅, quickstart.md ✅

**Tests**: Incluídos e obrigatórios — o briefing (§39) e a spec (SC-007) exigem os Testes A–Q; padrão TDD da suíte (executores/relógio FAKE — research R12). Tests FIRST, fail before implementation.

**Organization**: Tasks agrupadas por user story (spec.md §4: US1–US7). Fundação (config/model/service/auditoria) concentra os pré-requisitos compartilhados.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: User story à qual a task pertence (US1–US7)
- Caminhos exatos em toda task

## Path Conventions

Projeto single-app FastAPI existente: `app/` (models/services/web), `tests/` na raiz.

---

## Phase 1: Setup

**Purpose**: Garantir base verde antes de qualquer alteração (Constitution VIII)

- [x] T001 Executar `pytest` e registrar o baseline (suíte existente deve estar verde) — nenhuma alteração antes deste checkpoint; qualquer vermelho pré-existente é reportado, não corrigido nesta feature (Princípio I)

**Checkpoint**: Baseline registrado — fundação pode começar.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura compartilhada por TODAS as stories: configuração, metadados de tipo, auditoria, extensão aditiva do serviço

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase

- [x] T002 [P] Adicionar as variáveis de configuração em `app/config.py` (APÓS `load_dotenv()`, guarda da 018): `BACKUP_AUTO_ENABLED` (bool, default False), `BACKUP_AUTO_SCHEDULE` (str, default "daily"), `BACKUP_AUTO_TIME` (str, default "02:00"), `BACKUP_AUTO_WEEKDAY` (int, default 0), `BACKUP_RETENTION_DAILY_DAYS` (int, default 30), `BACKUP_RETENTION_WEEKLY_WEEKS` (int, default 12), `BACKUP_RETENTION_MONTHLY_MONTHS` (int, default 12), `BACKUP_RETENTION_KEEP_PRE_RESTORE` (int, default 0) — conversão numérica/bool já em config; validação de faixas fica no serviço (contract §1); NADA de valores existentes alterados
- [x] T003 [P] Adicionar as 5 ações de auditoria ADITIVAS em `app/services/audit_service.py` (contract §6): `ACTION_BACKUP_AUTO_SUCCESS = "BACKUP_AUTOMATICO_SUCESSO"`, `ACTION_BACKUP_AUTO_FAILED = "BACKUP_AUTOMATICO_FALHA"`, `ACTION_RETENTION_EXECUTED = "BACKUP_RETENCAO_EXECUTADA"`, `ACTION_BACKUP_REMOVED_RETENTION = "BACKUP_REMOVIDO_RETENCAO"`, `ACTION_RETENTION_FAILED = "BACKUP_RETENCAO_FALHA"` + rótulos em `ACTION_LABELS` ("Backup Automático Sucesso", "Backup Automático Falhou", "Retenção de Backups Executada", "Backup Removido pela Retenção", "Retenção de Backups Falhou") — eventos existentes intocados
- [x] T004 Criar o model `BackupRecord` em `app/models/backup_record.py` (data-model §1 — constraints textuais): tabela `backup_records` com `id` (PK autoincrement), `filename` VARCHAR(120) NOT NULL UNIQUE, `backup_type` VARCHAR(20) NOT NULL (valores `MANUAL` | `AUTOMATICO` | `PRE_RESTAURACAO`), `status` VARCHAR(10) NOT NULL (`SUCCESS` | `FAILURE`), `timestamp` DATETIME NOT NULL indexado (UTC naive via `now_utc()`), `size_bytes` INTEGER nullable, `sha256` VARCHAR(64) nullable, `error_description` VARCHAR(255) nullable, `removed_at` DATETIME nullable, `removed_reason` VARCHAR(40) nullable, `created_at` DATETIME default `now_utc()`; índice composto `ix_backup_records_type_status`; importar em `app/models/__init__.py` (a tabela nova é criada por `create_all` — NENHUMA alteração em `app/database.py`, zero `ALTER`)
- [x] T005 Estender `BackupService.generate_backup` em `app/services/backup_service.py` (contract §3): novo parâmetro ADITIVO de keyword `backup_type: str = "MANUAL"` com validação (valor fora dos 3 → `ValueError` antes de qualquer dump); ao concluir SUCESSO ou FALHA, gravar `BackupRecord` com SESSÃO PRÓPRIA E CURTA (SessionLocal, abrir-fechar no ponto de uso — padrão `_worker_audit` da 019) em `try/finally`: SUCCESS grava `{filename, backup_type, timestamp, size_bytes, sha256}`; FAILURE grava `filename={base}.sql.gz` (nome FINAL projetado — casa com `_BACKUP_NAME_RE`; sem colisão UNIQUE pois a geração falhou antes do rename), `status="FAILURE"`, `error_description` (mesma descrição controlada da auditoria — nunca segredos); quando o cleanup de `.part*` existente falhar com `OSError`, registrar log técnico do leftover (F5 — a exceção não propaga); erro de gravação de metadados NUNCA invalida o backup físico (só loga); retorno existente e eventos `BACKUP_CRIADO`/`BACKUP_FALHA` existentes intocados
- [x] T006 [P] Criar `tests/test_backup_records.py` (fundação — Teste B parcial): backup manual via fluxo existente (executor FAKE — padrão 015) grava `BackupRecord(backup_type="MANUAL", status="SUCCESS")` com size/sha256; falha injetada grava FAILURE com `error_description` e SEM size/sha256, com `filename={base}.sql.gz` (nome final projetado) casando com `_BACKUP_NAME_RE` (C1); `backup_type` inválido → `ValueError` sem executor chamado; falha no cleanup de `.part*` (OSError simulado) → log técnico do leftover sem propagar exceção (F5); verificar que `init_db`/`create_all` cria `backup_records` sem tocar tabelas existentes (BV-1)
- [x] T007 Executar `pytest` — suíte completa verde (novos testes T006 + zero regressão) e botão manual funcionando identicamente (BV-2)

**Checkpoint**: Fundação pronta — metadados, config e auditoria existem; stories podem começar.

---

## Phase 3: User Story 1 — Backup automático dispara e reutiliza o mecanismo existente (P1) 🎯 MVP

**Goal**: Disparo agendado que gera backup pelo serviço EXISTENTE, identificado como `AUTOMATICO`, registrado na auditoria

**Independent Test**: relógio simulado no horário configurado → arquivo válido gerado sem ação manual, `BackupRecord(AUTOMATICO/SUCCESS)`, eventos `BACKUP_AUTOMATICO_SUCESSO` + `BACKUP_CRIADO` (Testes A/B/P)

### Tests for User Story 1 ⚠️ (FIRST — devem falhar antes da implementação)

- [x] T008 [P] [US1] Criar `tests/test_backup_automatico.py` com os Testes A/B (relógio FAKE injetável — research R12): horário atingido → `generate_backup` chamado UMA vez com `backup_type="AUTOMATICO"`; arquivo válido (gzip legível) + registro SUCCESS + eventos `BACKUP_AUTOMATICO_SUCESSO` (ator None + description "sistema") e `BACKUP_CRIADO`; backup desativado → nenhum dump (Teste B-negativo pode ficar na US2, T010)

### Implementation for User Story 1

- [x] T009 [US1] Criar `app/services/backup_scheduler.py` (contract §4): thread agendadora daemon com loop de verificação de 30 s via `stop_event.wait(30)`; dependências injetáveis (`clock` default `now_utc`, `stop_event`); `_run_scheduled_backup()` executando em WORKER THREAD com sessões próprias e curtas: guarda `_AUTO_RUNNING` (lock), `generate_backup(db, None, None, backup_type="AUTOMATICO")`, auditoria `BACKUP_AUTOMATICO_SUCESSO`/`BACKUP_AUTOMATICO_FALHA`, `finally` liberando a flag; `start_scheduler()`/`stop_scheduler()` idempotentes; `scheduler_status()` sem segredos (contract §4)
- [x] T010 [US1] Integrar o ciclo de vida no `app/main.py` (contract §8): no `lifespan`, APÓS `ensure_admin_user`/`ensure_default_roles`, chamar `start_scheduler()`; após `yield`, `stop_scheduler()` — middleware de manutenção 019, whitelist, rotas e handlers INTOCADOS
- [x] T011 [US1] Teste P em `tests/test_backup_automatico.py`: backup automático válido é aceito por `validate_restore_source` e restaurável pelo fluxo 017/019 existente com executores FAKE (import_executor/security_backup_executor) — restore concluído sem adaptação alguma (contract §3)

**Checkpoint**: MVP — backup automático funcional e restaurável; `pytest` verde.

---

## Phase 4: User Story 2 — Agendamento configurável e previsível após restart (P1)

**Goal**: Frequência/horário configuráveis; comportamento determinístico pós-restart; config inválida cai em default seguro

**Independent Test**: relógio fake → `_next_run_utc` determinística (diária/semanal); catch-up único quando ciclo corrente sem sucesso; valor inválido → default + log (Testes N/O reais ficam para o quickstart §4)

### Tests for User Story 2 ⚠️

- [x] T012 [US2] Adicionar em `tests/test_backup_automatico.py`: (mesmo arquivo de T008 — sequencial após T008) `_next_run_utc` para `daily` (próxima ocorrência futura do `HH:MM` Recife→UTC via `local_to_utc`) e `weekly` (próximo `BACKUP_AUTO_WEEKDAY`); `_should_catch_up` True só quando horário do ciclo corrente já passou SEM `BackupRecord(AUTOMATICO/SUCCESS)` na janela do ciclo (janela precisa do research R5: daily = dia calendário local Recife; weekly = semana iniciando 00:00 local no `WEEKDAY` — não ISO) e False quando já existe sucesso (ou quando ainda não chegou); config inválida (`BACKUP_AUTO_TIME="25:99"`, `SCHEDULE="xyz"`, retenção 0/negativa) → default seguro + log, sem crash; `BACKUP_AUTO_ENABLED=false` → nenhum disparo

### Implementation for User Story 2

- [x] T013 [US2] Implementar no `app/services/backup_scheduler.py`: `_next_run_utc(now_utc)` determinística (R5/R11 — conversão Recife↔UTC EXCLUSIVAMENTE via `app/utils/time_utils.local_to_utc`/`now_utc`); `_should_catch_up(now_utc)` consultando `BackupRecord` (janela do ciclo corrente); normalização/validação de config no serviço (contract §1 — valores fora de faixa → default + `logger.warning` com o valor ignorado, nunca crash do lifespan); catch-up executado UMA única vez por start, ~60 s após o start (nunca cascata); `scheduler_status()` expõe `next_run_local` (America/Recife) e `enabled`/`schedule`/`time_local`/`weekday`/`last_result`/`last_finished_at`/`running`

**Checkpoint**: Agendamento determinístico e configurável; restart previsível; `pytest` verde.

---

## Phase 5: User Story 3 — Sem execuções simultâneas nem conflito com restore (P1)

**Goal**: Guardas de concorrência: sobreposição de automáticos descartada; restore em andamento → adiamento

**Independent Test**: disparo enquanto `_AUTO_RUNNING` → descartado com log; disparo durante `restore_in_progress()` → adiado sem dump (Teste M)

### Tests for User Story 3 ⚠️

- [x] T014 [US3] Adicionar em `tests/test_backup_automatico.py` (Teste M — mesmo arquivo de T008/T012 — sequencial): segunda chamada de `_run_scheduled_backup` com `_AUTO_RUNNING` ativo → ZERO chamadas ao executor, apenas log técnico (sem evento de auditoria de falha); disparo com `restore_in_progress()` simulado (flag do service) → nenhum dump, adiamento registrado; backup manual durante automático → `BackupError` de concorrência com mensagem clara + `BACKUP_FALHA` existente (comportamento de guarda preservado — R10)

### Implementation for User Story 3

- [x] T015 [US3] Completar as guardas em `app/services/backup_scheduler.py` + `app/services/backup_service.py` (R4/R10): guarda 1 `_AUTO_RUNNING` (lock — descarte com log, contract §4 passo 1); guarda 2 `restore_in_progress()` → adiamento para o próximo ciclo com recálculo de `next_run` (contract §4 passo 2); `generate_backup` rejeita chamada manual enquanto `_AUTO_RUNNING` (paridade da guarda 017 — defesa em profundidade mantendo `_allow_during_restore` intacto); nenhuma fila criada

**Checkpoint**: Concorrência controlada; `pytest` verde (incl. testes 015–019 de guarda existentes).

---

## Phase 6: User Story 4 — Identificação determinística do tipo de backup (P1)

**Goal**: Manual/automático/pré-restauração distinguíveis por metadados; legados conservadoramente não elegíveis

**Independent Test**: gerar um backup de cada tipo → tipo correto consultável; arquivo sem registro → tratado como não elegível (base dos Testes G–I)

### Tests for User Story 4 ⚠️

- [x] T016 [P] [US4] Adicionar em `tests/test_backup_records.py`: manual via rota/serviço → `MANUAL`; automático via scheduler (fake) → `AUTOMATICO`; backup de segurança do restore → `PRE_RESTAURACAO`; arquivo legado (criado em disco SEM registro) → nenhum registro, tratado como não elegível pela consulta de elegibilidade (helper do service) e exibido como `—` (US7 consumirá); UNIQUE de `filename` impede registro duplicado (BV-4/BV-5)

### Implementation for User Story 4

- [x] T017 [US4] Marcar o backup de segurança do restore como `PRE_RESTAURACAO` em `app/services/backup_service.py` (única linha do ciclo 017/019 alterada — data-model BV-3): a chamada interna `generate_backup(...)` dentro de `_execute_restore_cycle` passa `backup_type="PRE_RESTAURACAO"`; ordem do ciclo, eventos e mensagens intocados; helper de classificação (registro por `filename` via sessão curta) disponível para listagem/elegibilidade reutilizado pela US5/US7

**Checkpoint**: Tipos determinísticos nos 3 fluxos; restore 017/019 verde com a marcação; `pytest` verde.

---

## Phase 7: User Story 5 — Retenção conservadora que só apaga elegíveis (P1)

**Goal**: GFS determinístico sobre automáticos elegíveis; proteções absolutas; guarda do último válido; histórico preservado

**Independent Test**: conjunto misto → só automáticos expirados não-âncora e íntegros removidos; manuais/pré-restauração/legados intactos; 0 válidos → nada removido; falha de remoção → PARCIAL (Testes G/H/I/J/L/K)

### Tests for User Story 5 ⚠️

- [x] T018 [P] [US5] Criar `tests/test_backup_retencao.py` (Testes G/H/I/J/L): seleção determinística — automático fora de `DAILY_DAYS` e não-âncora removido; âncora semanal (mais recente da semana ISO dentro de `WEEKLY_WEEKS`) e mensal (mais recente do mês dentro de `MONTHLY_MONTHS`) preservadas (data-model §3); MANUAL antigo NUNCA removido (Teste H); PRE_RESTAURACAO preservado por default e com `KEEP_PRE_RESTORE=N` preserva os N mais recentes (Teste I); guarda do último válido — remoção que deixaria 0 backups válidos (considerando todos os tipos no disco, incluindo legados gzip-legíveis — F7) bloqueada com motivo `ULTIMO_BACKUP_VALIDO` registrado em `preservados` do evento resumo (F4 — Teste J); remoção com integridade ≠ OK não ocorre; arquivo removido → `removed_at`/`removed_reason` no registro e histórico PRESERVADO (Teste L); legado sem registro jamais candidato (BV-5); resultado consolidado `COMPLETA`/`PARCIAL`/`FALHA` — PARCIAL nunca reportado como concluída (Teste K)

### Implementation for User Story 5

- [x] T019 [US5] Implementar `_apply_retention(db)` em `app/services/backup_scheduler.py` (contract §5): universo = `BackupRecord(AUTOMATICO/SUCCESS, removed_at IS NULL)` com arquivo presente; seleção conforme data-model §3 (janela diária + âncoras semanal ISO/mensal, determinística, timestamp UTC do registro); integridade via `_gzip_read_status` (016); remoção física EXCLUSIVAMENTE via `get_backup_path()` (regex + diretório oficial — path traversal estruturalmente impossível, §31) + `unlink` com try/except; por arquivo removido: `removed_at`/`removed_reason` + evento `BACKUP_REMOVED_RETENTION` (SUCCESS com `{motivo, faixa}`; FAILURE em OSError — não interrompe); resultado consolidado + evento `BACKUP_RETENCAO_EXECUTADA` com `{candidatos, removidos, falhas, resultado, preservados: {filename: motivo}}` — motivo ∈ {`ULTIMO_BACKUP_VALIDO`, `ANCORA_SEMANAL`, `ANCORA_MENSAL`, `INTEGRIDADE_NAO_OK`} (F4) e mesmo mapa no log técnico; erro inesperado do ciclo → `BACKUP_RETENTION_FAILED`; NENHUM glob/extensão/diretório externo
- [x] T020 [US5] Integrar a retenção ao ciclo (briefing §6/A8): `_run_scheduled_backup` executa `_apply_retention` APÓS a geração (sucesso ou falha — FR-021: falha de backup não dispara limpeza agressiva, guardas continuam valendo); execução também após decisão de catch-up no start; sem execução quando `BACKUP_AUTO_ENABLED=false` e sem ciclo

**Checkpoint**: Retenção segura e auditada; `pytest` verde.

---

## Phase 8: User Story 6 — Falhas honestas e diagnósticáveis (P1)

**Goal**: Todo falha → status FALHA + evento + log técnico sanitizado; arquivo parcial nunca válido

**Independent Test**: falhas injetadas (exit≠0, executável ausente, OSError, gzip inválido) → FAILURE registrado em `BackupRecord` + `BACKUP_AUTOMATICO_FALHA`, log com etapa/exit/stderr sanitizado, nenhum falso sucesso (Testes C/D/E/F/K)

### Tests for User Story 6 ⚠️

- [x] T021 [US6] Adicionar em `tests/test_backup_automatico.py` (Testes C/D/E/F — mesmo arquivo de T008/T012/T014 — sequencial): executor com `CalledProcessError` (exit≠0) → `BackupRecord(FAILURE)` + `BACKUP_AUTOMATICO_FALHA` + `BACKUP_FALHA` + log contendo "exit" e SEM a senha do banco (assert `MYSQL_PWD`/senha ausentes no caplog — Teste Q parcial); `FileNotFoundError` de executável → mensagem "não encontrado"; `TimeoutExpired` → mensagem "tempo limite"; OSError de disco → FAILURE sem crash do scheduler/thread; gzip inválido injetado → FAILURE e `.part*` não listados como válidos (Teste F); erro inesperado qualquer → thread do worker nunca propaga (crash-safety 019) e registra FAILURE

### Implementation for User Story 6

- [x] T022 [US6] Completar o tratamento de falhas no ciclo em `app/services/backup_scheduler.py` (contract §9): mapear cada exceção ao `BackupError` controlado (o executor da 018 já distingue não encontrado/erro/timeout — reuso); garantir `BackupRecord(FAILURE, error_description)` + `BACKUP_AUTOMATICO_FALHA` em TODOS os ramos; log técnico com `type(exc).__name__`, etapa e exit code, stderr via `_sanitize_stderr` existente (Princípio VI); `last_result`/`last_message` em memória para o monitoramento; FR-016: status SUCCESS somente com processo OK + arquivo existe + conteúdo + integridade OK (a validação de geração existente já cobre — não duplicar)

**Checkpoint**: Falhas honestas ponta a ponta; `pytest` verde.

---

## Phase 9: User Story 7 — Monitoramento e auditoria na área existente (P2)

**Goal**: Indicadores no card novo da tela de Backups; coluna Tipo; RBAC reutilizado; auditoria consultável

**Independent Test**: rota existente com `backup.gerenciar` exibe indicadores (data-model §1 consultas) e coluna Tipo; sem permissão → 403 (Testes do briefing §34/§35)

### Tests for User Story 7 ⚠️

- [x] T023 [P] [US7] Criar `tests/test_backup_monitoramento.py`: `GET /admin/backups` com permissão `backup.gerenciar` contém os indicadores (último automático + status, próxima execução, último válido, última falha, última retenção, válidos, removidos) e a coluna "Tipo" da listagem (`MANUAL`/`AUTOMATICO`/`PRE_RESTAURACAO`/`—`); usuário SEM `backup.gerenciar` → 403 (deny-by-default); card e listagem existentes intactos (sem remoção de elementos — Princípio X); nenhum segredo no HTML

### Implementation for User Story 7

- [x] T024 [US7] Estender `admin_backups` em `app/web/admin_routes.py` (contract §7): contexto ganha `auto_status = scheduler_status()` e `retention_summary` (consultas a `BackupRecord` via helper do service — data-model §1: último automático, último válido, última falha, válidos, removidos; última retenção do evento de auditoria); permissão `backup.gerenciar` reutilizada — SEM permissão nova; rota POST/manual/download intocados
- [x] T025 [US7] Atualizar `app/web/templates/admin/backups.html` (contract §7): card novo "Backup Automático" acima da listagem com componentes existentes (`card`, `badge`, `dt/dd` — paridade do card de restauração): ativado/desativado, frequência/horário local, próxima execução (`localtime`), último automático + status, último válido, última falha, última retenção (resultado + removidos), válidos/removidos; coluna "Tipo" aditiva na tabela existente; NADA removido do template

**Checkpoint**: Monitoramento disponível; `pytest` verde.

---

## Phase 10: Polish & Cross-Cutting

**Purpose**: Documentação fiel (Constitution XI) e validação final (XII)

- [x] T026 [P] Atualizar `README.md` (§Backup): novas 8 variáveis de ambiente (contract §1) com defaults, default DESATIVADO, regra pós-restart/catch-up (research R5), tabela `backup_records` (metadados, sem mudança de formato de arquivo), retenção e proteções (manuais/pré-restauração preservados)
- [x] T027 [P] Atualizar `docs/ARQUITETURA_E_MANUTENCAO.md`: módulo `backup_scheduler.py` (thread do processo), `backup_records` no mapa de models, retenção GFS, eventos de auditoria novos, monitoramento
- [x] T028 [P] Atualizar a central de ajuda em `app/services/help_service.py` (artigo de backup — padrão 015/016/017): seção "Backup automático e retenção" com comportamento real (configuração via `.env`, indicadores, o que a retenção apaga/preserva) — sem inventar comportamento
- [x] T029 Executar a validação completa do `quickstart.md`: `pytest` (suíte inteira verde), cenários automatizados dos Testes A–M/P/Q, checklists manuais 4.1–4.5 preparados para execução real nos dois SO (Testes N/O — registrar resultados/pendências); percorrer o checklist de conformidade da Constitution (escopo, credenciais, banco aditivo, testes, docs)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: imediato — baseline obrigatório
- **Foundational (T002–T007)**: T002/T003 paralelizáveis; T004 → T005 → T006 → T007; BLOQUEIA todas as stories
- **US1 (T008–T011)**: após Foundational — MVP
- **US2 (T012–T013)**: após US1 (scheduler existe)
- **US3 (T014–T015)**: após US1 (guardas do ciclo existem)
- **US4 (T016–T017)**: após Foundational (independente de US2/US3)
- **US5 (T018–T020)**: após US4 (elegibilidade usa tipos/legados) e US1 (ciclo)
- **US6 (T021–T022)**: após US1 (ciclo) — paralelizável com US3/US5
- **US7 (T023–T025)**: após US1–US6 (indicadores leem tudo)
- **Polish (T026–T029)**: após todas as stories

### User Story Dependencies

```text
Foundational ──► US1 (MVP) ──► US2 ─┐
                    │───► US3 ──────┤
                    │───► US6 ──────┤
      US4 ──────────┴───► US5 ──────┤
                                    ▼
                                   US7 ──► Polish (T026–T029)
```

### Parallel Opportunities

- Foundational: T002 ∥ T003; T006 ∥ (nada — usa T005)
- Testes FIRST de stories distintas podem paralelizar POR ARQUIVO: T008 ∥ T016 ∥ T018 ∥ T023; T012/T014/T021 NÃO têm [P] (compartilham `tests/test_backup_automatico.py` com T008 — sequenciais entre si; F6)
- Polish: T026 ∥ T027 ∥ T028

---

## Implementation Strategy

### MVP First (US1 apenas)

1. T001 → T002–T007 (fundação)
2. T008–T011 (US1) → **STOP**: validar backup automático end-to-end com executor fake + restore (Teste P)
3. Deploy/demo se pronto (default DESATIVADO em produção até validação real)

### Incremental Delivery

1. Fundação + US1 → MVP (automático funcionando)
2. + US2 (config/catch-up) → agendamento confiável
3. + US3 + US4 + US6 → operação segura e honesta
4. + US5 (retenção) → disco controlado
5. + US7 + Polish → monitoramento e docs — feature completa (Testes N/O reais)

### Notes

- [P] = arquivos diferentes, sem dependência de task incompleta
- Nenhuma task altera: Restore 017/019 (exceto T017, marcação única), RBAC, AD, auth, módulos patrimoniais, formato/nome de arquivo
- Commit sugerido após cada task ou grupo lógico (Constitution XII: suíte verde a cada checkpoint)
