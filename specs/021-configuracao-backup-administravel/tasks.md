---

description: "Task list for feature 021 — Configuração Administrável do Backup Automático e Política de Retenção"
---

# Tasks: Configuração Administrável do Backup Automático e Política de Retenção

**Input**: Design documents from `/specs/021-configuracao-backup-administravel/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Incluídos conforme exigência da spec (briefing §33 — Testes A–R obrigatórios; Constitution VIII). TDD onde aplicável: testes escritos antes da implementação da respectiva story.

**Organization**: Tasks agrupadas por user story (spec.md §4: US1–US5). Fundação concentra os pré-requisitos compartilhados (model, service de leitura, ação de auditoria, config).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: User story à qual a task pertence (US1–US5)
- Caminhos exatos em cada descrição

## Path Conventions

- Projeto single-app FastAPI existente: `app/` + `tests/` na raiz (ver plan.md — Project Structure)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Estabelecer baseline de regressão antes de qualquer alteração

- [x] T001 Baseline da suíte: executar `python3 -m pytest -q` e registrar o resultado (esperado: 497 passed, 0 failed — pós-correções da 020). Meta da feature: manter 100% verde ao final. Nenhum código alterado nesta task

**Checkpoint**: baseline registrado — qualquer falha pré-existente deve ser reportada, não corrigida silenciosamente (Princípio I)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Model, service de leitura da configuração efetiva, ação de auditoria e ajuste de config — pré-requisitos de TODAS as stories

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase

- [x] T002 [P] Ajustar `app/config.py` (R8): manter as 8 constantes da 020 como bootstrap/fallback (NADA removido — mapeamento em research.md); garantir default `BACKUP_AUTO_ENABLED` = `"false"` com comentário coerente (FR-009) e acrescentar comentário de precedência (persistido → env → default). `MYSQLDUMP_PATH`, `BACKUP_DIR`, `BACKUP_IMPORT_TIMEOUT`, `DATABASE_URL` intocados (FR-005)
- [x] T003 [P] Criar `app/models/backup_config.py` — model `BackupConfig` (data-model §1): singleton `id=1`; `auto_enabled` Boolean default False não-nullable; `schedule` String(10) nullable; `time` String(5) nullable; `weekday` Integer nullable; `retention_daily_days`/`retention_weekly_weeks`/`retention_monthly_months`/`keep_pre_restore` Integer nullable ("não definido" = fallback env/default); `updated_at` DateTime `now_utc` onupdate; `updated_by` String(100) nullable. Adicionar import em `app/models/__init__.py` (`create_all` cria a tabela — aditivo, zero ALTER)
- [x] T004 [P] Adicionar em `app/services/audit_service.py` (contract §5): constante `ACTION_BACKUP_CONFIG_UPDATED = "BACKUP_CONFIGURACAO_ALTERADA"` + rótulo em `ACTION_LABELS` ("Configuração de Backup Alterada") — apenas aditivo
- [x] T005 Criar `app/services/backup_config_service.py` (contract §1; R2/R3): dataclass imutável `EffectiveBackupConfig` (8 campos + updated_at/updated_by); `get_backup_config(db)` (singleton lazy id=1 — padrão `get_ad_settings`); `get_effective_config(db)` — precedência ÚNICA por campo persistido(definido)→env→default da 020, env inválida tratada como ausente (nunca levanta; log técnico), snapshot imutável
- [x] T006 Criar `tests/test_backup_config.py` — fundação (depende de T005; sequencial no arquivo compartilhado): **Teste A** (primeiro uso: linha inexistente → criação lazy + efetiva = defaults 020: desativado/daily/02:00/dom/30/12/12/keep 0); precedência unitária por campo (persistido vence env; env vence default; campo None cai no fallback); env inválida → default sem crash; **anti-regressão FR-009** (default de `BACKUP_AUTO_ENABLED` é False); singleton permanece id=1 em chamadas repetidas. **Hermeticidade obrigatória (lição da 020 — 3 testes quebraram por ambiente)**: (a) os valores de fallback (env/default) dos testes de precedência e do Teste A são FIXADOS via monkeypatch das constantes em `backup_config_service`/`config` — nunca depender do `.env`/variáveis da máquina; (b) o teste anti-regressão FR-009 exercita o DEFAULT REAL do código, não o ambiente: subprocesso Python isolado (cwd fora do projeto ou .env temporariamente vazio + env var removida) importando `app.config` e afirmando `BACKUP_AUTO_ENABLED is False`
- [x] T007 Checkpoint: `python3 -m pytest tests/test_backup_config.py -q` verde (fundação) + suíte completa sem regressão (T001 baseline intacto)

**Checkpoint**: Foundation ready — user stories podem começar

---

## Phase 3: User Story 1 — Administrador ajusta o backup automático pela interface (Priority: P1) 🎯 MVP

**Goal**: Alterar horário (02:00 → 23:00) pela tela com persistência, confirmação e aplicação ao scheduler sem reinício

**Independent Test**: Com a aplicação no estado padrão, salvar nova configuração via POST → confirmação de sucesso → valor persistido (sobrevive a reinício) → auditoria com before/after → efetiva refletida nas leituras

### Tests for User Story 1 (mesmo arquivo — sequenciais entre si)

- [x] T008 [US1] Acrescentar em `tests/test_backup_config.py` (TDD — devem FAIL antes de T009–T011): **Teste K** (POST com 02:00→23:00 persiste na linha singleton e o form/GET exibe 23:00); **Teste R** (persistência sobrevive a "reinício": nova sessão + `create_all` idempotente → efetiva recarregada do banco); aplicação dinâmica (após salvar, `get_effective_config` reflete o novo valor na mesma aplicação, sem reinício); fluxo completo da rota (POST → redirect 303 com success=). **Wiring de sessão da suíte**: como os testes de fundação exercitam os services com `db_session`, todas as funções do `backup_config_service` recebem `db` como parâmetro explícito (padrão da 020 — sessão do chamador, sem SessionLocal interna nos caminhos testáveis)

### Implementation for User Story 1

- [x] T009 [US1] Implementar `save_backup_config(db, actor, *, auto_enabled, schedule, time, weekday, retention_daily_days, retention_weekly_weeks, retention_monthly_months, keep_pre_restore)` em `app/services/backup_config_service.py` (contract §1; R5/R6): valida faixas (schedule ∈ {daily,weekly}; time HH:MM; weekday 0–6; retenções ≥ 1; keep ≥ 0 — violação → `ValueError` ANTES de qualquer escrita); captura before (efetiva atual); aplica na linha singleton + `updated_by`/`updated_at`; **commit único**; retorna efetiva resultante
- [x] T010 [US1] Adicionar em `app/web/admin_routes.py` (contract §4): `GET /admin/backups/configuracoes` (contexto: valores da efetiva para o form + placeholders nos campos não definidos + updated_at/by) e `POST /admin/backups/configuracoes` (mesma permissão; fluxo §17 do briefing: before → `save_backup_config` → `ValueError` capturado → redirect com error= (nada persistiu) → sucesso: `write_change_audit` com `ACTION_BACKUP_CONFIG_UPDATED`, before/after por campo, module="Backup", resource="BackupConfig", resource_id=1, ip_address → redirect com success=). Ambas sob `Depends(require_permission("backup.gerenciar"))` — permissão EXISTENTE, sem permissão nova (FR-022)
- [x] T011 [US1] Acrescentar em `app/web/templates/admin/backups.html` (contract §6): seção "Configurações de Backup" abaixo do card de monitoramento — formulário único (POST na rota nova) com: Ativado (checkbox), Frequência (select Diário/Semanal), Horário (input HH:MM), Dia da semana (select 0–6 rotulado), Retenção diária/semanal/mensal (number), Pré-restauração (select "Preservar todos"/"Preservar N mais recentes" + number), exibição de updated_at/updated_by; campos **pré-preenchidos com `value=` dos valores efetivos** (data-model §3: campos obrigatórios no POST; salvar sem alterar materializa a efetiva — comportamento previsto); padrão visual do formulário "Integração AD" (card/dl/inputs/mensagens existentes; tema claro/escuro e responsividade herdados); NENHUM campo técnico (FR-005); nada removido do template (Princípio X)

**Checkpoint**: US1 funcional e testável isoladamente — Testes K/R/dinâmica verdes; administrador consegue alterar 02:00→23:00 pela tela; MVP validável

---

## Phase 4: User Story 2 — Valores inválidos e primeiro uso são seguros (Priority: P1)

**Goal**: Backend rejeita valores inválidos sem alterar o estado vigente; valores limítrofes válidos são aceitos

**Independent Test**: Submeter cada campo inválido via POST direto → rejeição com mensagem clara, nada persiste; submeter limítrofes válidos → aceitos

### Tests for User Story 2 (mesmo arquivo — sequencial após T008)

- [x] T012 [US2] Acrescentar em `tests/test_backup_config.py`: **Teste F** (horário "25:99" e "abc" → rejeição no backend, nada persiste, efetiva anterior intacta); retenção diária/semanal/mensal 0 e negativa → rejeição; weekday 7 → rejeição; schedule "mensal" → rejeição; **limítrofes válidos** (FR-016): "00:00", retenção 1, keep_pre_restore 0 e N>0 aceitos; POST direto sem JS (validação não depende do frontend — FR-015); **falha de persistência** (Edge case da spec, U1): commit/flush que falha (ex.: exceção simulada no commit via monkeypatch) → erro controlado, efetiva anterior permanece vigente, estado da linha singleton sem alteração parcial
- [x] T013 [US2] Verificar/ajustar `save_backup_config` em `app/services/backup_config_service.py`: mensagens de erro claras por campo; garantir ordem valida-tudo-antes-de-escrever (transação única abortada em qualquer violação — Edge case "falha de persistência": estado anterior vigente); validação do scheduler (_effective_*) permanece como segunda camada (R6)

**Checkpoint**: US2 completa — valores inválidos nunca alteram a configuração vigente; limítrofes válidos funcionam

---

## Phase 5: User Story 3 — Única fonte de verdade em execução (Priority: P1)

**Goal**: Scheduler, tela e retenção leem a mesma configuração efetiva; alteração aplicada sem reinício

**Independent Test**: Definir env divergente do banco → todas as leituras seguem o banco (precedência única); salvar pela tela → scheduler reflete no próximo tick sem reinício

### Tests for User Story 3 (mesmo arquivo — sequencial após T012)

- [x] T014 [US3] Acrescentar em `tests/test_backup_config.py`: **Teste L** (env com horário X + banco com Y → `_next_run_utc`/`scheduler_status`/retenção usam Y — precedência única); **Teste B** (efetiva `auto_enabled=false` → loop não dispara: nenhum BackupRecord AUTOMATICO criado — reusar padrão fresh_scheduler/clock fake da 020, com a linha singleton persistida na sessão de teste); **Teste C** (efetiva `true` + horário atingido → ciclo dispara via `generate_backup` existente); snapshot consistente (ciclo de retenção usa limites do MESMO snapshot do tick — sem combinação parcial); **Testes D/E** (próximo disparo diário/semanal correto a partir da efetiva — herda regras 020)
- [x] T015 [US3] Ajustar `app/services/backup_scheduler.py` (contract §3; R4/R5 — ÚNICA alteração no mecanismo existente): `_scheduler_loop` abre sessão curta **por tick** e obtém snapshot de `get_effective_config`; usa snapshot para enabled/schedule/weekday e cálculo `_next_run_utc`/catch-up; `_apply_retention` recebe limites do snapshot do ciclo (lógica GFS 020 INTACTA — só a origem muda); funções `_effective_*` migradas internamente para consumir o snapshot (validação de faixa preservada — 2ª camada); `scheduler_status()` reporta a partir da efetiva; `hour, minute` capturado no start deixa de ter função de configuração (fica só no log). SEM segundo scheduler, SEM reinício de thread, SEM hot reload genérico (briefing §12/§26)
- [x] T015b [US3] **Adaptar os testes da 020 ao novo mecanismo de leitura** (C1 — analise; 9 pontos patcheiam constantes DIRETAMENTE em `backup_scheduler`, o que fica inerte após T015): em `tests/test_backup_automatico.py` (linhas ~56, ~102, ~181, ~222, ~226, ~229), `tests/test_backup_retencao.py` (~186, ~199) e `tests/test_backup_monitoramento.py` (~99) — substituir `monkeypatch.setattr(backup_scheduler, "BACKUP_AUTO_*", ...)` por uma das formas equivalentes, preservando a INTENÇÃO de cada teste: (a) preferencial — semear a linha singleton `BackupConfig` com o valor desejado (via `get_backup_config` + setattr + commit na sessão de teste, ou `save_backup_config`); (b) para testes de fallback/env inválida (ex.: `25:99`, `xyz`, `0`) — patchear as constantes na FONTE de fallback (módulo `config`/service), SEM linha singleton definida, verificando que a efetiva cai no default. ZERO teste removido, desabilitado ou com cobertura reduzida (Constitution VIII — adaptação legítima do mecanismo, não enfraquecimento); asserts equivalentes mantidos
- [x] T016 [US3] Checkpoint US3: Testes B/C/D/E/L verdes + suíte da 020 (com os testes adaptados em T015b: `tests/test_backup_automatico.py`, `tests/test_backup_retencao.py`, `tests/test_backup_monitoramento.py`) 100% verde — nenhuma regressão no agendador existente

**Checkpoint**: US1+US2+US3 completas — configuração pela tela governa o scheduler em runtime com fonte única

---

## Phase 6: User Story 4 — Acesso controlado por RBAC com auditoria obrigatória (Priority: P2)

**Goal**: Somente autorizados leem/alteram; toda alteração auditada com before/after; nenhum segredo

**Independent Test**: Usuário sem permissão → 403 no GET e no POST direto; alteração → evento com usuário, data/hora, valores anterior/novo por campo

### Tests for User Story 4 (mesmo arquivo — sequencial após T014)

- [x] T017 [US4] Acrescentar em `tests/test_backup_config.py`: **Teste M** (alteração de 2 campos → evento `BACKUP_CONFIGURACAO_ALTERADA` com username, timestamp, before/after por campo alterado; zero segredos no evento — sem DATABASE_URL/credenciais); **Teste N** (usuário sem `backup.gerenciar`: GET e POST direto → 403; nada altera; acesso negado auditado pelo mecanismo existente); dois POSTs simultâneos/consecutivos (última escrita válida prevalece de forma determinística; 2 eventos de auditoria)
- [x] T018 [US4] Verificar/ajustar rota POST em `app/web/admin_routes.py` conforme T017: before/after apenas dos campos alterados (padrão `write_change_audit` — paridade do POST do AD); garantir ausência total de segredos no evento e no HTML da tela (FR-021)

**Checkpoint**: US4 completa — proteção backend comprovada (não basta esconder o botão — briefing §20)

---

## Phase 7: User Story 5 — Funcionalidades existentes intocadas e separação técnica/operacional (Priority: P2)

**Goal**: Backup manual, restauração, pré-restauração e retenção intactos; tela contém só as 8 configurações operacionais

**Independent Test**: Suíte de regressão de backup completa verde com a nova configuração vigente; inspeção do HTML da tela

### Tests for User Story 5 (mesmo arquivo — sequencial após T017)

- [x] T019 [US5] Acrescentar em `tests/test_backup_config.py`: **Teste O** (backup manual com configuração nova vigente → fluxo 020 intacto: registro MANUAL, eventos preservados); **Teste P** (restauração → ciclo 017/019 intacto: pré-restauração criado e marcado PRE_RESTAURACAO); **Teste Q** (retenção GFS com limites novos vindos da efetiva → âncoras/guardas 020 intactas); **Teste J** (pré-restauração: `keep_pre_restore=0` preserva TODOS; N>0 preserva os N mais recentes e os demais tornam-se candidatos — via `_apply_retention` com snapshot da efetiva, paridade do teste 020); HTML da tela NÃO contém campos/caminhos técnicos (`MYSQLDUMP_PATH`, `BACKUP_DIR`, `BACKUP_IMPORT_TIMEOUT`, `DATABASE_URL` — FR-005/FR-021)
- [x] T020 [US5] Corrigir qualquer regressão revelada por T019 (esperado: nenhuma — o design não toca esses fluxos; qualquer quebra indica desvio do plan/research a corrigir na origem)

**Checkpoint**: US5 completa — zero regressão comprovada; separação técnica×operacional verificada

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentação fiel (Constitution XI) e validação final

- [x] T021 [P] Atualizar `README.md` (§Backup): nova seção "Configurações de Backup" (tela, campos), regra de precedência (persistido → env → default), aplicação sem reinício (tick ≤ 30 s), `MYSQLDUMP_PATH`/`BACKUP_DIR`/`BACKUP_IMPORT_TIMEOUT` permanecem técnicos, defaults inalterados (desativado)
- [x] T022 [P] Atualizar `docs/ARQUITETURA_E_MANUTENCAO.md`: service `backup_config_service.py` (resolução da efetiva), model `backup_config` (singleton) no mapa de modelos, rotas `/admin/backups/configuracoes`, evento `BACKUP_CONFIGURACAO_ALTERADA`, precedência e snapshot por tick no fluxo do agendador
- [x] T023 [P] Atualizar `app/services/help_service.py` (artigo de backups): seção "Configurações de Backup" com comportamento real (quem pode, o que configura, precedência, aplicação sem reinício, o que nunca é editável pela tela) — sem inventar comportamento
- [x] T024 Validar `specs/021-configuracao-backup-administravel/quickstart.md` end-to-end: suíte completa verde (baseline T001 preservado + novos), Testes A–R executados e mapeados, validação manual documentada; marcar todas as tasks como concluídas; preparar dados do relatório final (briefing §39: arquivos analisados/alterados, solução escolhida e por quê, como scheduler/retenção/auditoria/RBAC usam a configuração, limitações restantes)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: sem dependências — imediato
- **Foundational (T002–T007)**: depende do baseline; BLOCKS todas as stories (model+service de leitura são pré-requisito de tudo)
- **US1 (T008–T011)**: depende da fundação; entrega o MVP (tela + persistência + auditoria)
- **US2 (T012–T013)**: estende `save_backup_config` da US1 (validação completa)
- **US3 (T014–T015b, T016)**: depende da fundação (`get_effective_config`); pode avançar em paralelo com US2 (arquivos distintos: scheduler × service) — mas valida melhor após US1/US2
- **US4 (T017–T018)**: depende da rota (US1) — verifica proteção e auditoria
- **US5 (T019–T020)**: depende de US1–US3 (regressão sobre o conjunto)
- **Polish (T021–T024)**: depende de todas as stories

### Within Each User Story

- Testes primeiro (TDD — devem FAIL antes da implementação)
- Service antes de rotas; rotas antes de template
- Checkpoint executável ao fim de cada story

### Parallel Opportunities

- **Fundação**: T002 (config.py) ∥ T003 (model) ∥ T004 (audit_service) — arquivos distintos; T005 depende de T003; T006 depende de T005
- **Testes**: T006/T008/T012/T014/T017/T019 compartilham `tests/test_backup_config.py` — **sequenciais entre si** (regra do formato: mesmo arquivo sem [P])
- **Polish**: T021 ∥ T022 ∥ T023 (arquivos distintos)
- US2 e US3 podem progredir em paralelo após US1 (service de validação × scheduler — arquivos distintos), mantendo os testes sequenciais no arquivo compartilhado

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Setup (T001) + Foundational (T002–T007)
2. US1 (T008–T011): administrador configura pela tela com persistência e auditoria
3. **STOP and VALIDATE**: Testes K/R + navegação manual
4. MVP entregável — mas NOTA: sem US3 o scheduler ainda não lê a efetiva (alteração exige reinício); sem US2 a validação pode ter lacunas — para produção, completar US2+US3 (ambas P1)

### Incremental Delivery

1. Fundação → model/service de leitura prontos
2. +US1 → tela funcional (MVP de interface)
3. +US2 → validação à prova de valores inválidos
4. +US3 → aplicação dinâmica sem reinício (fonte única — coração técnico)
5. +US4/+US5 → proteção comprovada + zero regressão
6. Polish → docs + validação quickstart

---

## Notes

- [P] = arquivos diferentes, sem dependência de task incompleta
- Testes A–R do briefing §33 (cobertura 18/18): A (T006), B/C/D/E/L (T014), F (T012), G/H/I (T019 — limites do snapshot na retenção), J (T019), K (T008), M (T017), N (T017), O/P/Q (T019), R (T008); + Edge case de falha de persistência (T012)
- Proibições permanentes (briefing §31/§35/§40): sem ConfigService genérico, sem segundo scheduler, sem alterar MYSQLDUMP/BACKUP_DIR, sem refatoração além do escopo
- Commit após cada task ou grupo lógico; parar em qualquer checkpoint para validar a story isoladamente
