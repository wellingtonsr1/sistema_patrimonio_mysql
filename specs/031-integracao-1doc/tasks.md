---

description: "Task list for feature 031 - Integracao 1Doc"
---

# Tasks: Integração 1Doc — Comunicação Automática de Movimentações

**Input**: Design documents from `/specs/031-integracao-1doc/`

**Prerequisites**: plan.md ✅ · spec.md (Q1–Q5) ✅ · research.md ✅ · data-model.md ✅ · contracts/onedoc-contract.md ✅ · quickstart.md ✅

**Tests**: Incluídos por decisão do projeto — **TDD dentro de cada User Story**: os testes são escritos e executados **ANTES** da implementação correspondente (vermelho → verde). Nenhuma tarefa de teste roda em paralelo com a implementação da mesma story.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project (FastAPI monolito): `app/` e `tests/` na raiz — conforme plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline e leitura dos artefatos antes de qualquer edição

- [x] T001 Executar suíte baseline (`python -m pytest tests/ -q --tb=no`) e registrar contagem (esperado: 617 passed / 1 failed pré-existente ambiental `test_backup_config`); ler `app/services/movement_service.py` (hook 030, L295-327), `app/models/notification.py` (precedente UNIQUE) e `app/services/permission_service.py` (precedente catálogo)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura compartilhada por todas as stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 [P] Adicionar configuração `ONEDOC_*` em `app/config.py` seguindo o padrão `SMTP_*` (L153-164): `ONEDOC_ENABLED` (default `False` — integração nasce desativada), `ONEDOC_API_URL` (""), `ONEDOC_API_TOKEN` ("" — comentário "SEGREDO — somente ambiente, nunca em banco/logs"), `ONEDOC_CONNECT_TIMEOUT` (3.0), `ONEDOC_READ_TIMEOUT` (10.0), `ONEDOC_MAX_ATTEMPTS` (3); acrescentar bloco comentado equivalente ao `.env.example`
- [x] T003 [P] Criar model `OneDocIntegration` em `app/models/onedoc_integration.py` conforme data-model.md: `__tablename__ = "onedoc_integrations"`, `UniqueConstraint("movement_id", name="uq_onedoc_integrations_movement_id")`, campos `movement_id` (FK movements.id, NOT NULL), `process_number` String(60) NOT NULL, `status` String(20) NOT NULL default "PENDING", `message_id` String(100) NULL, `attempt_count` Integer NOT NULL default 0, `last_attempt_at`/`sent_at`/`last_error_at` DateTime NULL, `last_error` Text NULL, `content_url` String(500) NULL (reservado — permanece NULL); registrar import em `app/models/__init__.py` (create_all)
- [x] T004 [P] Adicionar 4 ações de auditoria em `app/services/audit_service.py`: `ACTION_INTEGRACAO_1DOC_SOLICITADA`, `ACTION_INTEGRACAO_1DOC_ENVIADA`, `ACTION_INTEGRACAO_1DOC_FALHOU`, `ACTION_INTEGRACAO_1DOC_REPROCESSADA` + rótulos em `ACTION_LABELS` ("Integração 1Doc Solicitada/Enviada/Falhou/Reprocessada") — padrão `ACTION_*` existente
- [x] T005 [P] Criar `app/services/onedoc_message.py` (funções PURAS — sem DB): `build_subject(tag)` → `[SisPatrimônio Pro] Movimentação patrimonial - <tag>` (NÃO reutiliza o assunto do e-mail 030); `build_greeting(now_local)` → "Bom dia!"/"Boa tarde!"/"Boa noite!" (P-2); `build_body_text(...)` e `build_body_html(...)` → saudação + tabela EXATA de 4 colunas (P-1): `Descrição do Material | Tombamento | Origem | Destino` com 1 linha (asset.name, asset.tag, movement.origin_location_name, movement.destination_location_name); sem link (FR-017)
- [x] T006 Criar `app/services/onedoc_client.py`: protocolo `OneDocProvider` com `find_process(process_number) -> bool | None` (`False`=inexistente, `None`=não suportado/indisponível — decisão Q2) e `send_communication(process_number, subject, body_text, body_html) -> str | None` (id da mensagem; `None` = não informado — decisão Q3); classe `OneDocHttpClient` com sessão `requests`, header de autenticação com `ONEDOC_API_TOKEN`, timeouts de config, classificação transitório (timeout/conexão/5xx) × permanente (4xx) e sanitização de erros removendo token/URL da mensagem (precedente `_sanitize_error_message` da 030) — **endpoints/paths/payloads marcados `[PENDING C-1..C-4]`: NENHUM inventado** (research D4)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Comunicação automática no processo 1Doc (Priority: P1) 🎯 MVP

**Goal**: Movimentação elegível (cautela/transferência) com processo informado gera comunicação no 1Doc com tabela fiel aos dados oficiais; sem processo, a conclusão é bloqueada (integração ativa)

**Independent Test**: com provider fake e integração ativa, concluir cautela com processo → comunicação gerada (`SENT`) com dados corretos; sem processo → erro antes de gravar; desativada → byte-idêntico ao atual

### Tests for User Story 1 ⚠️ (escrever PRIMEIRO, executar, confirmar VERMELHO)

- [x] T007 [US1] Criar `tests/test_onedoc.py` (parte 1 — cenários US1) com fixtures `db_session`, `FakeOneDocProvider` (injetável via `provider=`) e `onedoc_ativa` (monkeypatch `ONEDOC_ENABLED=True`): (a) cautela com processo + provider fake → registro `PENDING→SENT`, `message_id`, auditoria `_SOLICITADA`+`_ENVIADA` com `user=None`; (b) conteúdo da comunicação contém saudação + `asset.name`, `asset.tag`, origem, destino e NÃO contém "http" (FR-017); (c) cautela SEM processo (integração ativa) → `ValueError` antes de gravar, nenhum registro, nenhum e-mail (FR-002); (d) `find_process→False` (C-3 suportado) → `ValueError` "processo não encontrado", movimentação NÃO gravada (US1.3/Q2); (e) `find_process→None` → modo tolerante: grava e envia (US1.4/Q2); (f) integração DESATIVADA → nenhum campo exigido, nenhum registro, comportamento idêntico (US1.5); (g) tipos fora do alcance (devolução/manutenção/aquisição) → nenhuma interação mesmo ativo (Q1); (h) movimentação INVÁLIDA (VAL-002) → provider não chamado, nenhum registro (FR-002 da spec 030 análogo); (i) lote CSV → `onedoc_enforce=False`: sem exigência, sem registro (F6). Executar `python -m pytest tests/test_onedoc.py -q` e confirmar falha por módulo/behavior inexistente

### Implementation for User Story 1

- [x] T008 [US1] Criar `app/services/onedoc_service.py`: `NOTIFICABLE_TYPES = {ALOCACAO_CAUTELA, TRANSFERENCIA_LOCAL}` (Q1); `notify_movement(db, movement, process_number, *, operator=None, ip_address=None, provider=None)` com contrato "NUNCA levanta" (try/except total — espelha `notification_service.py` da 030): guardas (enabled, tipo, processo presente) → idempotência pré-insert (registro existente em {SENT, PENDING} → return) → cria `PENDING` (commit próprio; `IntegrityError` → rollback+return) → auditoria `_SOLICITADA` → monta conteúdo via `onedoc_message` → `provider.send_communication(...)` → `SENT` + `message_id` (None ok — Q3) + `sent_at` + commit + auditoria `_ENVIADA`
- [x] T009 [US1] Estender `app/services/movement_service.py`: (1) `create_movement(..., onedoc_process_number=None, onedoc_enforce=True)`; (2) validação condicional FR-002 antes de qualquer escrita: integração ativa E tipo elegível E `onedoc_enforce` E processo vazio → `ValueError("Informe o número do processo 1Doc para registrar esta movimentação no 1Doc.")`; normaliza trim/vazio→None; (3) validação Q2 via `onedoc_client.find_process` quando processo informado e integração ativa: `False` → `ValueError("O processo 1Doc informado não foi encontrado.")`; `None`/falha de rede → segue (tolerante); (4) hook pós-commit APÓS o bloco de e-mail 030 (L301-325): novo bloco try/except total chamando `onedoc_service.notify_movement(db, movement, onedoc_process_number, operator=operator, ip_address=ip_address)` — nada escapa (FR-007)
- [x] T010 [US1] Em `app/services/import_service.py`: chamada do lote passa `onedoc_enforce=False` (ao lado do `notify=False` existente) — lote CSV intocado (F6)
- [x] T011 [US1] Interface: em `app/schemas/movement.py` acrescentar `onedoc_process_number: Optional[str] = None` a `MovementCreate` (aditivo); em `app/web/routes.py` `POST /movements/new` acrescentar `onedoc_process_number: Optional[str] = Form(None)` e passar ao `MovementCreate`/`create_movement`; em `app/web/templates/movements/new.html` acrescentar campo "Processo 1Doc" renderizado SOMENTE quando integração ativa E tipo selecionado ∈ {cautela, transferência} (Q5) — rota GET passa flag de integração ativa ao template; API `POST /api/v1/movements` recebe via schema sem alteração de código (pass-through, contract §7)
- [x] T012 [US1] Verde + regressão: `python -m pytest tests/test_onedoc.py -q` (todos os cenários US1) e `python -m pytest tests/test_movements.py tests/test_import_asset_movements.py tests/test_notificacoes.py -q` (zero regressão; doubles que simulam `create_movement` podem precisar de `*args, **kwargs` — precedente da 030)

**Checkpoint**: US1 funcional e testável independentemente — MVP entrega o valor central

---

## Phase 4: User Story 2 — Falha do 1Doc nunca afeta a movimentação (Priority: P1)

**Goal**: Qualquer falha externa (indisponível, timeout, credencial, 4xx/5xx) resulta em registro `FAILED` sanitizado + auditoria, com a movimentação permanecendo válida e o e-mail 030 intocado

**Independent Test**: provider fake que lança exceção/timeout → movimentação gravada e válida, registro `FAILED` com erro sem token, auditoria `_FALHOU`, e-mail enviado normalmente

### Tests for User Story 2 ⚠️ (escrever PRIMEIRO, executar, confirmar VERMELHO)

- [x] T013 [US2] Acrescentar a `tests/test_onedoc.py` (parte 2 — cenários US2): (a) provider lança `Exception("...token-SEGREDO...")` → movimentação válida, registro `FAILED`, `last_error` contém `***` e NÃO contém o segredo, auditoria `_FALHOU` result FAILURE, `new_data` sem credenciais; (b) provider lento (sleep > timeout fake) → chamada interrompida no timeout configurado, estado `FAILED`, resposta da movimentação não fica presa (SC-004); (c) erro permanente (4xx fake) → `FAILED` sem nova tentativa automática; (d) e-mail 030 + 1Doc falho na mesma movimentação → e-mail SENT e 1Doc FAILED independentes (FR-015); (e) crash do provider entre insert e envio (PENDING órfão) → não quebra movimentações seguintes. Executar e confirmar vermelho nos pontos de tratamento ausentes

### Implementation for User Story 2

- [x] T014 [US2] Completar tratamento de falha em `app/services/onedoc_service.py`: bloco `except` do envio → `status=FAILED`, `last_error` sanitizado via helper local (remover `config.ONEDOC_API_TOKEN` e `ONEDOC_API_URL`; máx. 2000 chars), `last_error_at`, `attempt_count += 1`, commit defensivo (falha ao registrar estado não levanta), auditoria `_FALHOU`; captura final `except Exception` no nível de `notify_movement` com log (precedente 030); garantir classificação transitório × permanente do client usada apenas para registro (retry automático efetivo fica para worker — P-5)
- [x] T015 [US2] Verde: `python -m pytest tests/test_onedoc.py -q` (US1+US2) e conferir que nenhum teste de US1 regrediu

**Checkpoint**: US1 + US2 independentes e funcionais

---

## Phase 5: User Story 3 — Ciência, reprocessamento e idempotência (Priority: P2)

**Goal**: Admin lista integrações falhas e reprocessa com permissão dedicada (sem default); idempotência endurecida garante 0 duplicatas; auditoria de reprocessamento com usuário real

**Independent Test**: provocar falha → usuário com permissão reprocessa → `SENT` com UMA comunicação; usuário sem permissão → 403; reprocessar `SENT` → nada reenviado

### Tests for User Story 3 ⚠️ (escrever PRIMEIRO, executar, confirmar VERMELHO)

- [x] T016 [US3] Acrescentar a `tests/test_onedoc.py` (parte 3 — cenários US3): (a) reprocessar integração `FAILED` via service/rota → `SENT`, MESMO registro (id preservado — UNIQUE), `attempt_count` incrementado, auditoria `_REPROCESSADA` com `user` REAL (não None); (b) reprocessar integração `SENT` → nenhum reenvio, provider não chamado (Q3/D8); (c) corrida de idempotência: dois `notify_movement` simultâneos (simular `IntegrityError`) → apenas 1 registro, sem segunda comunicação (SC-003); (d) rota `POST /admin/integracao-1doc/{id}/reprocessar` sem permissão → 403; com `integracao1doc.reprocessar` concedida explicitamente → ok; (e) rota `GET /admin/integracao-1doc` lista processo/status/tentativas; (f) `content_url` permanece NULL após todos os fluxos (FR-017). Usar padrão de fixtures web da suíte (`client` + `create_all` + `_create_test_user()`, como `tests/test_notificacoes.py` US3). Executar e confirmar vermelho (rota/permissão inexistentes → 404)

### Implementation for User Story 3

- [x] T017 [US3] Endurecer `app/services/onedoc_service.py`: `reprocess(db, integration_id, *, user, ip_address=None, provider=None) -> tuple[bool, str]` — exige registro `FAILED` (SENT → return (False, "já enviada")), reexecuta envio no MESMO registro, incrementa `attempt_count`, audita `_REPROCESSADA` com `user` real; manter `IntegrityError` → rollback+return (T008) como defesa de corrida
- [x] T018 [US3] Em `app/services/permission_service.py`: acrescentar ao `PERMISSION_CATALOG` `{"name": "integracao1doc.reprocessar", "module": "Integração 1Doc", "label": "Reprocessar integração 1Doc", "description": "Reprocessar a inclusão de comunicações de movimentação no processo 1Doc que falharam."}` — SEM concessão default em banco existente (precedente `notificacoes.gerenciar`, decisão Q4)
- [x] T019 [US3] Rotas + interface: em `app/web/admin_routes.py` criar `GET /admin/integracao-1doc` e `POST /admin/integracao-1doc/{id}/reprocessar` com `require_permission("integracao1doc.reprocessar")`, flash de resultado e auditoria; criar `app/web/templates/admin/onedoc.html` (lista: movimentação, processo, status, tentativas, último erro/sucesso, botão "Reprocessar" apenas em FAILED — padrão visual 021/030); item de menu "Integração 1Doc" em `app/web/templates/base.html` com `can()`
- [x] T020 [US3] Verde: `python -m pytest tests/test_onedoc.py -q` completo (US1+US2+US3)

**Checkpoint**: All user stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentação, segurança e validação final

- [x] T021 [P] Documentação: README.md — seção "Integração 1Doc" (visão, variáveis `ONEDOC_*`, permissão, estado atual "desativada por padrão — exige contrato do fornecedor") + lista de auditoria; docs/ARQUITETURA_E_MANUTENCAO.md — árvore de serviços/models novos + eventos `ACTION_INTEGRACAO_1DOC_*`
- [x] T022 [P] Artigo na central de ajuda: novo módulo em `app/services/help_article_031.py` (padrão `help_article_030.py`) e registro em `app/services/help_service.py` — "Integração 1Doc: como informar o processo, o que fazer em caso de falha, quem pode reprocessar"
- [x] T023 Auditoria de segurança de credenciais: verificar que `ONEDOC_API_TOKEN` aparece SOMENTE em `app/config.py` e no uso sanitizado em `onedoc_client`/`onedoc_service` (grep); zero ocorrência em templates/logs/auditoria; erros sanitizados cobertos por testes (US2-a); `.env` real não versionado
- [x] T024 Suíte completa + quickstart: `python -m pytest tests/ -q --tb=no` (esperado: baseline + novos, apenas a 1 falha pré-existente ambiental); percorrer `specs/031-integracao-1doc/quickstart.md` §3 (desativada) e §4 (ativada com fake) registrando resultados
- [x] T025 Validação de escopo (Constitution XII): `git status --porcelain` deve conter EXATAMENTE os arquivos do plan.md (config, model novo + __init__, schema, movement_service, import_service, onedoc_message/client/service, permission_service, audit_service, routes web/admin, templates new.html/onedoc.html/base.html, tests/test_onedoc.py, docs, .env.example); confirmar byte-idênticos: `notification_service.py`, `email_provider.py`, `email_config_service.py`; marcar todas as tarefas `[x]` no tasks.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: sem dependências — imediato
- **Foundational (T002–T006)**: bloqueia todas as stories
- **US1 (T007–T012)**: após Foundation
- **US2 (T013–T015)**: após US1 (reusa `notify_movement`)
- **US3 (T016–T020)**: após US2 (reprocessa estados criados por US1/US2)
- **Polish (T021–T025)**: após todas as stories

### Within Each User Story

- **TDD**: testes escritos e executados ANTES da implementação (vermelho → verde) — sem paralelismo entre testes e implementação da mesma story
- Model/services antes de rotas; core antes de integração
- Story completa antes da próxima prioridade

### Parallel Opportunities

- **Entre tarefas de arquivos distintos** (marcadas [P]): T002/T003/T004/T005 (Foundation) e T021/T022 (Polish)
- **Entre stories**: NÃO paralelizável neste caso (US2/US3 dependem do service de US1)
- Dentro de cada story: testes → implementação → verde, em ordem estrita

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 (baseline) → T002–T006 (foundation)
2. T007–T012 (US1 completa)
3. **STOP and VALIDATE**: cautela com processo via tela/API → comunicação `SENT` com tabela fiel; sem processo → bloqueio; desativada → byte-idêntico
4. MVP entrega o valor central (elimina redigitação)

### Incremental Delivery

1. +US2 (T013–T015) → falha externa segura → validação independente
2. +US3 (T016–T020) → reprocessamento operável → validação independente
3. Polish (T021–T025) → documentação + validação final

### Nota de produção (Fase 1 — fornecedor 1Doc)

- Todo o desenvolvimento acima usa **fakes** (nunca API real);
- `OneDocHttpClient` fica com `[PENDING C-1..C-4]`; produção só liga `ONEDOC_ENABLED=true` com credenciais + contrato confirmado + homologação (quickstart §5);
- Nenhuma tarefa presume endpoints — a conexão real é tarefa futura própria, pós-fornecedor.

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Evitar: tarefas vagas, conflito de mesmo arquivo, dependência cruzada entre stories
