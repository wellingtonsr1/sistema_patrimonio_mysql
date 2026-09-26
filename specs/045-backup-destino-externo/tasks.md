---
description: "Task list for feature implementation"
---

# Tasks: Destino Externo para Backups (045)

**Input**: Design documents from `/specs/045-backup-destino-externo/`

**Prerequisites**: plan.md (required), spec.md (required), research.md (R1–R12), data-model.md, contracts/contrato-backup-externo.md, quickstart.md

**Tests**: **OBRIGATÓRIOS** (C-17; seções 36/37 do pedido — diferente das features visuais 036–044): `tests/test_backup_externo.py` cobrindo os cenários A–L mapeados no quickstart; destino externo de teste = diretório temporário (`tmp_path`); constantes de retry/espera/orçamento monkeypatcháveis (R4). Suíte existente (backup manual/automático/config/records/restore/retenção + full suite 728) permanece 100% verde.

**Organization**: Tasks grouped by user story (US1 mecanismo de cópia → US2 configuração/teste/tela → US3 resiliência/preservações), precedidas de setup/foundational e seguidas de polish. Décima feature da família — e a primeira **funcional**: Constitution VII (zero ALTER), VI (segredos/RBAC) e VIII (testes) são os princípios mais sensíveis aqui. Decisões-chave em research: **R1** gancho único pós-`_record_backup_success`; **R2** 2 tabelas aditivas; **R3** cópia atômica tmp oculto + sha256 + `os.replace`; **R4** retry 3×/2s/orçamento 120s; **R5** nunca propaga exceção; **R10** nenhuma rotina toca o destino.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: services em `app/services/`, models em `app/models/`, rotas em `app/web/admin_routes.py`, template em `app/web/templates/admin/backups.html`, testes em `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar os pontos de acoplamento e o estado verde de partida.

- [ ] T001 Confirmar os fatos de integração em `app/services/backup_service.py` (`generate_backup`: retorno `{filename, timestamp, size_bytes, sha256}` pós `_record_backup_success`; `_VALID_BACKUP_TYPES`; `_BACKUP_NAME_RE`) e `app/services/backup_scheduler.py` (`_run_scheduled_backup` chama o mesmo método; lock/catch-up/restauração) — sem alterar nada — e rodar a suíte BASELINE: `python -m pytest tests/ -q` (728 passed esperado; SC/§37)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Models aditivos + eventos de auditoria — bloqueiam todas as stories.

**⚠️ CRITICAL**: Nenhum ALTER em tabela existente (Constitution VII/clarificação); models registrados no mecanismo de import existente para o `create_all` (seguir o padrão de `backup_record`/`backup_config`).

- [ ] T002 Criar `app/models/backup_external_config.py` (singleton id=1: `enabled` Bool default False, `dest_type` String(20) default "PASTA_REDE", `dest_path` String(255) nullable, `updated_at`/`updated_by`) e `app/models/backup_external_record.py` (`filename` String(120) UNIQUE indexado, `backup_type`, `status` SUCCESS|FAILURE, `copied_at` default `now_utc()` indexado, `size_bytes`, `sha256`, `error_description` String(255), `created_at`) conforme data-model; registrar os imports no ponto usado pelo `create_all` (mesmo mecanismo dos models de backup existentes)
- [ ] T003 Em `app/services/audit_service.py`: adicionar as 4 constantes no padrão literal (`ACTION_BACKUP_DESTINO_EXTERNO_CONFIGURADO = "BACKUP_DESTINO_EXTERNO_CONFIGURADO"`, `ACTION_BACKUP_DESTINO_EXTERNO_TESTADO`, `ACTION_BACKUP_EXTERNO_SUCESSO`, `ACTION_BACKUP_EXTERNO_FALHA`) + labels PT no dicionário existente (contract §3)

**Checkpoint**: Estruturas aditivas e eventos prontos — stories podem começar.

---

## Phase 3: User Story 1 - Cópia externa após backup local válido (Priority: P1) 🎯 MVP

**Goal**: Todo backup local válido (MANUAL/AUTOMATICO/PRE_RESTAURACAO) é copiado atomicamente ao destino configurado (quando habilitado), validado por SHA-256, com registro final único e auditoria — e nenhuma falha externa afeta o local (quickstart C/D/G/H; FR-001/002/007/008/009/011).

**Independent Test**: com config habilitada apontando para `tmp_path`, gerar backup e confirmar arquivo externo com mesmo nome/sha256, registro único e eventos; com config desabilitada, confirmar zero I/O no destino.

### Implementation for User Story 1

- [ ] T004 [US1] Criar `app/services/external_backup_service.py` (research R3/R4/R5; contract §1): constantes de módulo `EXTERNAL_COPY_ATTEMPTS=3`, `EXTERNAL_RETRY_WAIT_SECONDS=2`, `EXTERNAL_COPY_BUDGET_SECONDS=120` (monkeypatcháveis); `get_external_config`; `copy_backup_to_external(filename, sha256_local, size_local, dest_path)` — validar caminho (absoluto, sem caracteres de controle, sem shell), verificar espaço via `shutil.disk_usage` quando possível, copiar streaming para `<dest>/.<filename>.tmp` com flush+fsync e orçamento por chunk, validar tamanho+sha256, idempotência (nome final existente: hash igual → sucesso, divergente → falha), `os.replace` para o nome final, remover tmp em qualquer erro; motivos controlados ("destino indisponível", "sem permissão de escrita", "espaço insuficiente no destino", "falha de integridade (sha256 divergente)", "tempo limite da cópia")
- [ ] T005 [US1] Em `app/services/external_backup_service.py`: `process_backup_after_success(result, backup_type)` — lê config (desabilitada ou sem `dest_path` → None/no-op sem I/O); habilitada → loop de tentativas com espera curta e orçamento total → grava **um único** `BackupExternalRecord` (sessão própria e curta, padrão `_worker_audit`/020) + evento `BACKUP_EXTERNO_SUCESSO|FALHA`; **try/except total: nunca propaga**; retorno `{"external_status": ..., "external_reason": ...}`
- [ ] T006 [US1] Em `app/services/backup_service.py`: inserir o gancho único em `generate_backup` imediatamente após `_record_backup_success(...)` (research R1): chamar `external_backup_service.process_backup_after_success(...)` em try/except local que nunca altera o fluxo; adicionar a chave `"external"` ao dict de retorno
- [ ] T007 [US1] Criar `tests/test_backup_externo.py` com os cenários do mecanismo (quickstart): C (`test_manual_com_externo_copia_validada`: mesmo nome, sha256 igual, registro+auditoria), D (`test_automatico_com_externo_copia_validada` via ciclo do scheduler com dump injetado), G (`test_hash_divergente_copia_invalida`), H (`test_sem_duplicidade_de_registro_e_copia`), no-op desabilitado (base de A/B) e validação de atomicidade (tmp oculto não permanece; nome final só aparece validado) — monkeypatch das constantes e do dump

**Checkpoint**: MVP — mecanismo completo funcionando end-to-end com config habilitada programaticamente; suíte existente continua verde.

---

## Phase 4: User Story 2 - Configuração, teste de destino e tela (Priority: P2)

**Goal**: Administrador configura/ativa/testa o destino na tela existente (sem tela/permissão nova) e acompanha resultado externo no histórico e status do destino (quickstart A/B/L + extras; FR-004/005/006/012/013/016/017-config/teste).

**Independent Test**: com `backup.gerenciar`, salvar configuração (singleton persiste), testar destino válido/inválido, verificar fieldset/coluna/card na tela e flashes local+externo no gerar; sem permissão → 403.

### Implementation for User Story 2

- [ ] T008 [US2] Em `app/services/external_backup_service.py`: `save_external_config(db, *, enabled, dest_path, updated_by)` (singleton id=1 criado sob demanda; audita `BACKUP_DESTINO_EXTERNO_CONFIGURADO` quando alterado) e `test_destination(path)` (§24/R8: configurado → existe e é diretório → cria/Escreve/lê/remove arquivo temporário oculto → (ok, mensagem controlada); sem backup completo)
- [ ] T009 [US2] Em `app/web/admin_routes.py` (contract §2): estender POST `/admin/backups/configuracoes` para persistir o singleton externo quando presente no formulário; nova POST `/admin/backups/externo/testar` (gate `backup.gerenciar`, audita TESTADO, redirect com flash); POST `/gerar` compõe o flash "Backup local: SUCESSO / Backup externo: SUCESSO|FALHA (motivo)" a partir da chave `external`; GET `/admin/backups` fornece ao template os registros externos (por filename) e o status derivado do último `BackupExternalRecord`
- [ ] T010 [US2] Em `app/web/templates/admin/backups.html` (contract §4): fieldset "Backup externo" no formulário existente (checkbox Ativado desmarcado por padrão; tipo fixo informativo "Pasta de rede/NAS"; input `dest_path`; botão "Testar destino" em formulário próprio), coluna "Externo" no histórico (✓ / ✗ com motivo no title / —) preservando tudo que existe, card "Destino externo" com última cópia/tentativa e último resultado (estado vazio quando nunca houve)
- [ ] T011 [US2] Em `tests/test_backup_externo.py`: completar cenários A/B/L (`test_externo_desabilitado_manual_somente_local`, `test_externo_desabilitado_automatico_somente_local`, `test_desativado_volta_somente_local` — zero I/O no destino), RBAC (403 sem `backup.gerenciar` em configurar/testar), "Testar destino" (válido/inválido) e persistência do singleton (config salva → recarregar página reflete)

**Checkpoint**: US1+US2 — feature operável pela tela com default OFF preservado (SC-001).

---

## Phase 5: User Story 3 - Resiliência e preservações (Priority: P2)

**Goal**: Falhas externas (indisponível, sem permissão, sem espaço, timeout) nunca afetam o local nem a aplicação; restore/pré-restauração/retenção/reinicialização preservados (quickstart E/F/I/J/K; FR-009/010/014/015/019/020).

**Independent Test**: simular destino inexistente/sem permissão/adulterado com retry encurtado e confirmar local SUCCESS, falha externa registrada+auditada com motivo, app íntegra, destino nunca varrido, config persistente.

### Implementation for User Story 3

- [ ] T012 [US3] Em `app/services/external_backup_service.py` (refinamento se a validação mostrar necessidade — research R4/R5): garantir orçamento total respeitado entre tentativas (sem bloquear além dele) e motivos distintos por tipo de falha; nenhum `mkdir` automático do destino; em `tests/test_backup_externo.py`: E (`test_destino_indisponivel_local_preservado`: local SUCCESS íntegro, falha registrada+auditada, app responde), F (`test_destino_sem_permissao` via `chmod`), I (`test_restore_e_pre_restauracao_intactos`: restore existente funciona; pré-restauração é copiado — clarificação), J (`test_retencao_nao_toca_destino`: ciclo de retenção não altera o diretório externo), K (`test_config_persiste_apos_reinicializacao`: nova sessão/engine reabre singleton e scheduler_status íntegro) e `test_zero_segredos_em_logs` (melhoria A2 do analyze — evidência automatizada do SC-007: com `caplog` capturando os cenários de falha E/F/G, assert de que nenhum registro de log ou descrição de auditoria gravada contém padrões de senha/credencial/token/segredo, ex.: "senha", "password", "token", "secret", "credential")

**Checkpoint**: US1+US2+US3 — mecanismo, operação e resiliência completos.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regressão completa, validação formal e documentação fiel.

- [ ] T013 Rodar a suíte completa: `python -m pytest tests/ -q` — 100% verde incluindo os novos testes (SC-008/§37) e `git diff` coerente com o plan (nenhuma tabela existente alterada, nenhum asset estático tocado)
- [ ] T014 Criar `specs/045-backup-destino-externo/validacao.md` (SC-009): resultado de cada cenário A–L, suíte final, verificação de auditoria (4 eventos, zero segredos) e o **relatório final obrigatório do §43** (arquivos alterados/novos, configuração, fluxos manual/automático, integridade, falhas, auditoria, testes, limitações reais — não inventar resultados)
- [ ] T015 Atualizar `docs/ARQUITETURA_E_MANUTENCAO.md` (Princípio XI): novas tabelas, serviço, rotas na listagem de endpoints e comportamento do backup com destino externo; marcar tasks concluídas e commit do grupo lógico no padrão do repositório (subject "Feature 045: ..." sem acentos, footer Codebuff)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: imediato; baseline obrigatório
- **Foundational (T002–T003)**: bloqueia todas as stories (models/eventos)
- **US1 (T004–T007)**: depende do Foundational; T004→T005→T006 no núcleo do serviço, T007 valida
- **US2 (T008–T011)**: depende de US1 (config/teste/tela operam o mecanismo)
- **US3 (T012)**: depende de US1+US2 (endurece e comprova preservações)
- **Polish (T013–T015)**: depende de tudo

### User Story Dependencies

- **US1 (P1)**: independente após Foundational — entrega o mecanismo completo (MVP programático)
- **US2 (P2)**: operacionaliza US1 pela tela; não faz sentido sem ela
- **US3 (P2)**: comprova/endurece US1+US2; testes podem ser escritos junto ao desenvolvimento de cada parte, mas a fase garante cobertura E/F/I/J/K

### Parallel Opportunities

- T002 e T003 são [P] (arquivos diferentes, sem interdependência)
- Demais tasks: sequenciais (mesmos arquivos/serviço ou dependência de estado), coerente com a alteração localizada (C-18)

---

## Implementation Strategy

### MVP First (US1)

1. Setup + Foundational (baseline, models, eventos)
2. US1 (T004–T007) → **STOP and VALIDATE**: cenários C/D/G/H verdes + suíte existente verde
3. Só então US2 (tela/rotas) e US3 (resiliência)

### Incremental Delivery

1. US1 → cópia validada com dump único e falha contida (mecanismo)
2. US2 → operação pela tela existente com default OFF (comportamento atual preservado)
3. US3 → resiliência e preservações comprovadas (E/F/I/J/K)
4. Polish → regressão total, validacao.md com relatório §43, docs, commit

---

## Notes

- **Zero ALTER**: `create_all` não altera tabelas existentes — por isso config e resultados externos vivem em tabelas NOVAS (clarificações); verificar que os models são importados antes do `init_db()`
- **Nunca propagar**: `process_backup_after_success` é à prova de exceção (C-8); a falha externa só existe nos registros/flash
- **Dump único**: a cópia é do arquivo local; `dump_executor` intocado (C-9)
- **Sem shell/sem segredos**: cópia e teste de destino 100% stdlib/pathlib; nenhum campo de credencial existe (C-4)
- **Resultado único**: `filename` UNIQUE em `BackupExternalRecord` — retry nunca duplica (C-16/Teste H)
- **Destino nunca varrido**: nenhuma retenção externa; limpeza operacional (C-12)
- Monkeypatch das constantes nos testes (tentativas/espera/orçamento) para suite rápida
- Commit após cada grupo lógico (US1; US2; US3; polish) — mensagens no padrão do repositório
- Evitar: novo scheduler, segunda tela, permissão nova, refatoração do `backup_service` além do gancho, alteração em restore/retenção
