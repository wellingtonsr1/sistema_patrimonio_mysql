---
description: "Task list for feature 030 implementation"
---

# Tasks: Notificação por E-mail ao Setor de Patrimônio após Movimentação

**Input**: Design documents from `/specs/030-notificacao-email-movimentacoes/`

**Prerequisites**: plan.md (aprovado), spec.md (aprovada, com Clarifications Q1–Q4), research.md (decisões D1–D10), data-model.md, contracts/notifications-contract.md, quickstart.md

**Tests**: Incluídos — exigidos pela spec (Seção 14) e pelo usuário (TDD). **Dentro de cada User Story, os testes são escritos e executados como requisito TDD ANTES da implementação correspondente** (vermelho → verde). A tarefa de testes NÃO é paralela à implementação da mesma story.

**Organization**: Tasks agrupadas por user story para implementação e validação independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story a tarefa pertence (US1–US4 da spec)
- Caminhos exatos em cada descrição

## Path Conventions

Projeto existente monolítico (FastAPI em camadas): `app/` na raiz, `tests/` na raiz — conforme plan.md.

---

## Phase 1: Setup (Baseline)

**Purpose**: Estabelecer linha de base de regressão antes de qualquer alteração (Constitution VIII)

- [x] T001 Executar a suíte completa (`python -m pytest tests/ -q`) e registrar o baseline verde no relatório da feature — NENHUMA alteração de código nesta tarefa

**Checkpoint**: Suíte verde documentada. Qualquer falha pré-existente deve ser registrada e justificada antes de prosseguir.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelos, configuração de ambiente, auditoria e serviços-base que TODAS as stories consomem

**⚠️ CRITICAL**: Nenhuma user story começa antes deste phase estar completo

- [x] T002 [P] Adicionar variáveis SMTP ao `app/config.py` APÓS `load_dotenv()` (guarda da 018): `SMTP_HOST` (default ""), `SMTP_PORT` (587), `SMTP_USERNAME` (""), `SMTP_PASSWORD` ("" — segredo, somente ambiente, precedente `AD_BIND_PASSWORD`), `SMTP_FROM` (""), `SMTP_USE_TLS` (true), `SMTP_SEND_TIMEOUT` (10.0) — nomes e defaults exatos do contracts/notifications-contract.md §5, com bloco de comentários citando a feature 030
- [x] T003 [P] Criar `app/models/notification.py` com `EmailConfig` (singleton id=1: `notifications_enabled` Boolean default=False nullable=False; `recipients` Text nullable; `updated_at`/`updated_by` — data-model.md §1) e `Notification` (`movement_id` Integer **UNIQUE** FK→movements.id nullable=False; `status` String(20) default "PENDING"; `recipients` Text; `subject` String(255); `attempt_count` Integer default 0; `last_attempt_at`/`sent_at`/`created_at`/`updated_at` DateTime UTC; `error_message` Text; `content_url` String(500) nullable — **sempre NULL na v1**, RN-008; data-model.md §2) — tabela nova `notifications` + `email_config` via `create_all` (nenhum ALTER; `_ensure_schema_migrations` intocado)
- [x] T004 [P] Adicionar em `app/services/audit_service.py` as constantes `ACTION_NOTIFICACAO_ENVIADA = "NOTIFICACAO_ENVIADA"`, `ACTION_NOTIFICACAO_FALHOU = "NOTIFICACAO_FALHOU"`, `ACTION_NOTIFICACAO_CONFIG = "CONFIG_NOTIFICACAO_ALTERADA"` com rótulos em `ACTION_LABELS` ("Notificação Enviada", "Notificação Falhou", "Configuração de Notificação Alterada") — research.md D9
- [x] T005 Criar `app/services/email_config_service.py` (precedente 021): `get_effective_config(db, create=False)` leitura pura retornando dataclass congelada `EffectiveEmailConfig(enabled, recipients)`; `save_config(db, *, enabled, recipients, user)` com validação (ativado exige ≥1 destinatário válido — ValueError amigável; normaliza trim/lowercase, deduplica, máx. 10), persiste o singleton e grava `write_change_audit(ACTION_NOTIFICACAO_CONFIG, module="notificacoes", resource="email_config", before/after)` — contracts §4 (depende de T003, T004)
- [x] T006 [P] Criar `app/services/email_provider.py`: protocolo `EmailProvider` com `send(*, subject: str, body: str, recipients: list[str]) -> None` e `SMTPEmailProvider` usando stdlib (`smtplib.SMTP` com `timeout=SMTP_SEND_TIMEOUT`, STARTTLS se `SMTP_USE_TLS`, login se credenciais presentes, `email.message.EmailMessage` UTF-8 text/plain) — exceções de SMTP propagadas **sanitizadas** (nunca incluir senha/credenciais na mensagem de erro) — research.md D1/D2, contracts §3 (depende de T002)

**Checkpoint**: Foundation pronta — stories podem começar. Verificar que `init_db` cria as tabelas novas sem tocar nas existentes.

---

## Phase 3: User Story 1 — Setor de Patrimônio toma ciência da movimentação (Priority: P1) 🎯 MVP

**Goal**: Movimentação elegível (`ALOCACAO_CAUTELA`, `TRANSFERENCIA_LOCAL`, `DEVOLUCAO_ESTOQUE`) concluída por fluxo manual gera exatamente 1 e-mail institucional aos destinatários configurados, com assunto RN-005 e conteúdo FR-008.

**Independent Test**: Com notificações ativadas e destinatários configurados, concluir uma movimentação válida de tipo elegível e verificar 1 e-mail (via fake em teste) com todos os campos, registro `Notification` SENT e auditoria `NOTIFICACAO_ENVIADA`.

### Tests for User Story 1 ⚠️ (escrever PRIMEIRO, executar e ver FALHAR antes da implementação)

- [x] T007 [US1] Escrever testes falhando em `tests/test_notificacoes.py`: (a) movimentação `ALOCACAO_CAUTELA` com config ativada + fake provider → provider chamado 1× com destinatários exatos da config; (b) assunto igual a `[SisPatrimônio Pro] Nova movimentação patrimonial - <TAG>` (RN-005); (c) corpo contém tombamento, identificação do bem, rótulo do tipo via `.label`, origem/destino (nomes do Movement), custodiante anterior/atual, data/hora local America/Recife (padrão 004), operador = `operator_name` (RN-010) e NÃO contém URL/link (RN-008); (d) registro `Notification` criado com status SENT e vínculo movement_id; (e) auditoria `NOTIFICACAO_ENVIADA` com module="notificacoes", resource="movement", resultado SUCCESS, sem credenciais; (f) `TRANSFERENCIA_LOCAL` e `DEVOLUCAO_ESTOQUE` também notificam; (g) tipo fora do alcance (ex.: `ENTRADA_AQUISICAO`) → NENHUM e-mail e nenhum registro (RN-002/Q1); (h) movimentação INVÁLIDA — validação do `create_movement` levanta `ValueError` (ex.: VAL-002 nenhuma alteração efetiva) → provider NÃO chamado e NENHUM registro `Notification` criado (FR-002 — cenário 3 da spec Seção 14)

### Implementation for User Story 1

- [x] T008 [US1] Implementar `app/services/notification_service.py`: constante `NOTIFICABLE_TYPES = {MovementType.ALLOCATION, MovementType.TRANSFER, MovementType.RETURN_STOCK}`; `notify_movement(db, movement, *, operator=None, ip_address=None, provider=None) -> None` que (1) checa elegibilidade, (2) lê config (`get_effective_config`, leitura pura), (3) checa registro existente (idempotência — RN-007), (4) cria `Notification` PENDING com commit próprio, (5) monta assunto (função única RN-005) e corpo (FR-008/RN-009/RN-010, datas via `format_local`), (6) envia via provider, (7) atualiza estado/auditoria — **qualquer exceção capturada no serviço, nunca propagada** (contracts §2); eventos de auditoria gravados com `user=None` (ator = o serviço — precedente dos eventos automáticos de backup da 020) (depende de T003, T005, T006, T007)
- [x] T009 [US1] Adicionar hook pós-commit em `app/services/movement_service.py::create_movement`: novos parâmetros `notify=True, operator=None, ip_address=None` (aditivos — nenhum chamador existente muda); após `db.refresh(movement)` e antes do `return`, bloco `if notify:` com `try/except Exception` total (log técnico, nunca re-raise) chamando `notification_service.notify_movement` — contracts §1 (depende de T008)
- [x] T010 [US1] Alterar `app/services/import_service.py::execute_import` para passar `notify=False` em cada chamada de `create_movement` do lote — RN-002/Q2: importação CSV não gera e-mail por linha; restante do fluxo inalterado (depende de T009)
- [x] T011 [US1] Executar os testes de US1 até verde + suíte existente de movimentações (`tests/test_movements.py`) verde — checkpoint US1: story funcional e testável independentemente

**Checkpoint**: MVP — o valor central (ciência por e-mail) funciona ponta a ponta com config ativada via service.

---

## Phase 4: User Story 2 — Falha de e-mail nunca afeta a movimentação (Priority: P1)

**Goal**: Com SMTP indisponível, a movimentação persiste concluída, a falha é registrada (estado + auditoria, sem segredos) e nada escapa ao operador.

**Independent Test**: Com fake provider que levanta exceção, concluir movimentação válida e verificar persistência normal, `Notification` FAILED com erro sanitizado, auditoria `NOTIFICACAO_FALHOU` e nenhuma exceção na resposta.

### Tests for User Story 2 ⚠️ (escrever PRIMEIRO, executar e ver FALHAR antes da implementação)

- [x] T012 [US2] Escrever testes falhando em `tests/test_notificacoes.py`: (a) fake provider levanta exceção → movimentação PERSISTIDA e concluída (estado do bem atualizado, resposta web sem erro — TestClient segue redirect normal); (b) registro Notification com status FAILED, attempt_count=1, error_message preenchido e SEM senha/credencial/host-sensível; (c) auditoria `NOTIFICACAO_FALHOU` com result FAILURE e descrição sanitizada; (d) erro na montagem do conteúdo (movimentação com dados ausentes) → mesmo comportamento de falha registrada; (e) nenhuma exceção propagada ao chamador em nenhum dos casos (spec Seção 11/US2)

### Implementation for User Story 2

- [x] T013 [US2] Completar tratamento de falha em `app/services/notification_service.py` e `app/services/email_provider.py`: captura de exceção do provider → estado FAILED (attempt_count incrementado, `last_attempt_at`, `error_message` sanitizado — remover valores de `SMTP_PASSWORD`/`SMTP_USERNAME` do texto), auditoria de falha; captura igualmente para exceções de montagem de conteúdo e de gravação do registro (log da aplicação, sem propagação) (depende de T008, T012)
- [x] T014 [US2] Executar os testes de US2 até verde + reexecutar US1 — checkpoint US2: US1 e US2 funcionam independentemente

**Checkpoint**: Regra fundamental (RN-001) garantida por testes: e-mail jamais afeta a operação patrimonial.

---

## Phase 5: User Story 3 — Administrador configura a notificação (Priority: P2)

**Goal**: Admin ativa/desativa e define destinatários pela tela `/admin/notificacoes` (padrão 021/022), com validação, RBAC e auditoria de configuração; desativado = zero e-mails.

**Independent Test**: Admin salva config ativada com destinatários → movimentação gera e-mail; desativa → nenhum e-mail; usuário sem permissão → acesso negado.

### Tests for User Story 3 ⚠️ (escrever PRIMEIRO, executar e ver FALHAR antes da implementação)

- [x] T015 [US3] Escrever testes falhando em `tests/test_notificacoes.py`: (a) GET `/admin/notificacoes` com permissão → 200 e formulário com estado atual (leitura pura — sem criar singleton); (b) POST ativado sem destinatário → erro de validação amigável (flash), nada persistido; (c) POST com e-mail inválido → rejeitado; (d) POST válido → config persistida, flash de sucesso, auditoria `CONFIG_NOTIFICACAO_ALTERADA` com before/after; (e) notificações desativadas → movimentação concluída gera NENHUM e-mail e NENHUM registro (FR-006/RN-006); (f) usuário sem `notificacoes.gerenciar` → GET/POST negados (403 padrão) e auditados como `ACESSO_NEGADO` (spec US3)

### Implementation for User Story 3

- [x] T016 [US3] Implementar tela de configuração: rotas `GET`/`POST` `/admin/notificacoes` em `app/web/admin_routes.py` com `dependencies=[Depends(require_permission("notificacoes.gerenciar"))]` delegando a `email_config_service` (sem regra na rota — Constitution II/III); template `app/web/templates/admin/notificacoes.html` (estende base admin, componentes padrão 021/022, textarea de destinatários — um por linha ou vírgula, switch de ativação); registrar permissão `notificacoes.gerenciar` no catálogo existente **sem conceder a nenhum perfil**; entrada de menu Administração condicionada à permissão (contracts §6, research D10) (depende de T005, T015)
- [x] T017 [US3] Executar os testes de US3 até verde + reexecutar US1/US2 — checkpoint US3: configuração operável pela tela; default desativado preserva comportamento atual

**Checkpoint**: Feature operável de ponta a ponta por administrador sem tocar código.

---

## Phase 6: User Story 4 — Trazibilidade e não duplicidade (Priority: P3)

**Goal**: Auditoria responde (qual movimentação, quando, para quem, sucesso/falha) e uma movimentação nunca gera mais de um e-mail, mesmo em reprocesso.

**Independent Test**: Concluir movimentação, inspecionar trilha (eventos presentes, sem segredos) e executar `notify_movement` novamente para a mesma movimentação → nenhum segundo e-mail/registro.

### Tests for User Story 4 ⚠️ (escrever PRIMEIRO, executar e ver FALHAR antes da implementação)

- [x] T018 [US4] Escrever testes falhando em `tests/test_notificacoes.py`: (a) segunda chamada de `notify_movement` para movimentação já notificada → provider NÃO chamado de novo, NENHUM novo registro (idempotência RN-007 — UNIQUE(movement_id) + checagem prévia); (b) tentativa de inserir 2ª Notification para o mesmo movement_id é rejeitada pelo banco (IntegrityError); (c) inspeção da trilha: eventos de notificação contêm destinatários/resultado e NÃO contêm senha/token/credencial (SC-005); (d) `content_url` da Notification é NULL (RN-008 — preparado para link futuro sem reestruturar); (e) lote CSV (`execute_import`): nenhuma Notification criada para movimentações do lote (RN-002/Q2 — reforço do T010)

### Implementation for User Story 4

- [x] T019 [US4] Endurecer idempotência em `app/services/notification_service.py`: tratamento defensivo de `IntegrityError` na criação do registro (corrida teórica — tratar como "já notificado" e sair sem reenviar); garantir que a checagem prévia e o UNIQUE são os dois mecanismos ativos; nenhum caminho reenvia para `SENT` (data-model.md §4) (depende de T008, T018)
- [x] T020 [US4] Executar os testes de US4 até verde + suíte de notificações completa — checkpoint US4: trazibilidade e unicidade garantidas

**Checkpoint**: Todas as stories funcionam independentemente e integradas.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentação (Constitution XI), segurança e validação final (Constitution XII)

- [x] T021 [P] Atualizar `README.md`: seção de notificações por e-mail — variáveis `SMTP_*` do `.env` (marcando `SMTP_PASSWORD` como segredo), tela Administração → Notificações, permissão `notificacoes.gerenciar`, comportamento de falha (movimentação nunca afetada) e default desativado
- [x] T022 [P] Atualizar `docs/ARQUITETURA_E_MANUTENCAO.md`: módulos novos na árvore e tabelas (`app/services/notification_service.py`, `email_provider.py`, `email_config_service.py`, `app/models/notification.py`, tabela `notifications`/`email_config`, rota `/admin/notificacoes`) e os 3 eventos de auditoria — fiel ao comportamento real
- [x] T023 [P] Adicionar artigo "Notificações por E-mail" na central de ajuda (`/ajuda`, padrão das features 009): como configurar destinatários, ativar/desativar, o que o e-mail contém, onde ver falhas (auditoria) e por que o default é desativado
- [x] T024 Auditar segurança da implementação: buscar `SMTP_PASSWORD`/`SMTP_USERNAME` em logs, mensagens de erro, auditoria e templates (grep no código alterado + inspeção dos eventos gravados nos testes) — zero ocorrências (NFR-003/SC-005); validar que a permissão nova não foi concedida a nenhum perfil
- [x] T025 Executar a suíte completa (`python -m pytest tests/ -q`) — 100% verde incluindo não-regressão — e executar os cenários do `quickstart.md` (A–E) registrando resultados
- [x] T026 Validar escopo final: `git status`/`git diff` — somente os arquivos previstos no plan.md foram alterados/criados; nenhuma regra patrimonial, tipo de movimentação, RBAC existente ou tela não relacionada modificada (Constitution I/XII)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: imediato — baseline obrigatório antes de qualquer edição
- **Foundational (T002–T006)**: após T001 — BLOQUEIA todas as stories (T005 depende de T003+T004; T006 depende de T002; T002/T003/T004 paralelizáveis entre si)
- **US1 (T007–T011)**: após Foundational — 🎯 MVP
- **US2 (T012–T014)**: após US1 (consome o service do T008)
- **US3 (T015–T017)**: após US2 (pode ser implementada em paralelo com US2 em outro agente, mas valida com o service existente)
- **US4 (T018–T020)**: após US3 (valida o sistema completo de notificação)
- **Polish (T021–T026)**: após todas as stories

### Within Each User Story

- **Testes PRIMEIRO**: escritos e executados como requisito TDD antes da implementação correspondente (vermelho → verde). A tarefa de testes de uma story NÃO é paralela à implementação dessa story
- Service → hook/integração → validação do checkpoint
- Story completa antes da próxima prioridade

### Parallel Opportunities

- **Entre fases/arquivos**: T002, T003, T004 são [P] (arquivos distintos e independentes); T006 é [P] após T002; T021, T022, T023 são [P] entre si (documentos distintos)
- **Dentro de cada User Story NÃO há paralelismo entre testes e implementação**: os testes da story precedem e bloqueiam sua implementação (TDD). Tarefas de implementação de uma story que tocam arquivos distintos podem ser executadas sequencialmente na ordem listada (as dependências estão anotadas em cada tarefa)
- Stories diferentes são sequenciais por prioridade (P1 → P2 → P3); com equipe múltipla, US2 e US3 podem divergir após US1, mas a validação de cada checkpoint continua independente

---

## Parallel Example: Foundational Phase

```bash
# T002, T003, T004 juntos (arquivos diferentes, sem dependência mútua):
Task: "Adicionar variáveis SMTP ao app/config.py (T002)"
Task: "Criar app/models/notification.py com EmailConfig + Notification (T003)"
Task: "Adicionar constantes ACTION_* de notificação ao audit_service (T004)"

# Depois, em paralelo (dependências distintas já satisfeitas):
Task: "Criar app/services/email_config_service.py (T005, depende de T003+T004)"
Task: "Criar app/services/email_provider.py (T006, depende de T002)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1 (T001 — baseline)
2. Completar Phase 2 (T002–T006 — foundation)
3. Completar Phase 3 (T007–T011 — US1)
4. **STOP and VALIDATE**: movimentação elegível → 1 e-mail (config ativada via service); suíte verde
5. Deploy/demo se pronto

### Incremental Delivery

1. Setup + Foundational → foundation pronta
2. US1 → testar independentemente (MVP!)
3. US2 → regra fundamental testada → o sistema fica seguro para produção
4. US3 → operação pela tela sem tocar código
5. US4 → trazibilidade/idempotência garantidas
6. Polish → documentação + validação final (Constitution XII)

### Notas

- [P] = arquivos diferentes, sem dependências pendentes
- Testes usam SEMPRE fake provider (nunca SMTP real — spec Seção 14)
- Cada checkpoint valida a story isoladamente antes de avançar
- Commit por tarefa ou grupo lógico, conforme prática do repositório
