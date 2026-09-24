---

description: "Task list for feature 032 — Central de Integrações"
---

# Tasks: Central de Integrações — Gerenciamento e Observabilidade

**Input**: Design documents from `/specs/032-central-integracoes/`
(plan.md D1–D11, spec.md US1–US6, research.md F1–F12/D1–D9, data-model.md, contracts/central-de-integracoes-contract.md, quickstart.md)

**Prerequisites**: plan.md + spec.md (obrigatórios); research.md, data-model.md, contracts/, quickstart.md (gerados).

**Tests**: INCLUÍDOS — exigidos pela spec (§22/SC-002..SC-010) e pela Constitution VIII. Padrão do projeto (030/031): **escrever os testes PRIMEIRO, executar e confirmar VERMELHO**, depois implementar até VERDE. Fakes sempre — nenhum serviço externo real na suíte.

**Organization**: Tarefas por User Story para implementação e validação independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: US1..US6 conforme spec.md
- Caminhos exatos em cada tarefa

## Path Conventions

Projeto monolítico existente: `app/` (models, services, web, templates) e `tests/` na raiz — conforme plan.md.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline e guardas de escopo antes de qualquer alteração.

- [X] T001 [P] Confirmar baseline da suíte verde (`python -m pytest tests/ -q`) e registrar contagem atual antes de qualquer mudança
- [X] T002 [P] Conferir lista de arquivos INTOCÁVEIS do plan.md (`movement_service`, `backup_*`, `ad_service`/`ad_ldap`, `onedoc_client`, telas admin existentes) — nenhuma tarefa subsequente pode alterá-los fora dos toques mínimos D6

**Checkpoint**: baseline registrado; escopo delimitado.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura compartilhada por TODAS as user stories (model, migração, permissões, auditoria, provider, service base, instrumentação).

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase.

- [X] T003 [P] Criar model `IntegrationExecution` em `app/models/integration_execution.py` conforme data-model.md (colunas verbatim: `integration_key` String(30) NOT NULL index; `operation` String(40) NOT NULL; `result` String(20) NOT NULL index; `duration_ms` Integer nullable; `user_id` FK `users.id` ON DELETE SET NULL nullable; `username` String(100) nullable snapshot; `movement_id` Integer nullable index SEM FK/UNIQUE; `detail` Text nullable, erro SANITIZADO máx. 2000 chars; `created_at` DateTime default `now_utc`; índices `(integration_key, created_at)`, `(integration_key, result, created_at)`, `created_at`; docstring append-only)
- [X] T004 Criar migração aditiva idempotente em `app/database.py` (`IntegrationExecution.__table__.create(checkfirst=True)` no fluxo `init_db` — precedente 030/031; nenhuma coluna existente alterada) (depends T003)
- [X] T005 [P] Adicionar permissões ao `PERMISSION_CATALOG` em `app/services/permission_service.py`: `integracoes.visualizar` e `integracoes.testar` (módulo "Integrações", labels/descriptions do contract §1) — SEM concessão default; incluir as duas em `DEFAULT_ROLES` → perfil Administrador (padrão 030/031)
- [X] T006 [P] Adicionar em `app/services/audit_service.py`: `ACTION_CENTRAL_TESTE_SUCESSO = "TESTE_INTEGRACAO_SUCESSO"`, `ACTION_CENTRAL_TESTE_FALHA = "TESTE_INTEGRACAO_FALHA"` + rótulos em `ACTION_LABELS` (module da rota: `central_integracoes`; events aditivos — nada existente alterado)
- [X] T007 [P] Implementar `check_connection() -> tuple[bool, str, int | None]` em `app/services/email_provider.py` (conecta `SMTP_HOST:PORT`, STARTTLS se `SMTP_USE_TLS`, login com `SMTP_USERNAME/PASSWORD`, encerra — **NENHUMA mensagem enviada**, P-6; mensagem sanitizada sem segredos; latência ms; `send()` e `_sanitize_error` intocados)
- [X] T008 Criar `app/services/integration_center_service.py` (contract §3): catálogo declarativo `INTEGRATIONS` com 4 entradas (`email`, `onedoc`, `ad`, `glpi` — key, nome, finalidade, capacidades `supports_test/supports_reprocess/supports_enable_disable`, `status_fn`); `record_execution(db, key, operation, result, *, duration_ms=None, user=None, movement_id=None, detail=None)` **best-effort (nunca levanta)** com sanitização de `detail`; `get_history(db, key, *, status, operation, days, page, page_size)` com paginação; `mask_secret()` (indicação "configurada" / máscara `************ABCD`) (depends T003)
- [X] T009 Instrumentação best-effort (plan D6 — toques MÍNIMOS): após estado final em `app/services/notification_service.py` (`record_execution("email", "SEND_EMAIL", ...)`), em `onedoc_service._send` em `app/services/onedoc_service.py` (`"onedoc", "SEND_COMMUNICATION"`, cobre envio e reprocesso) e no teste de conexão AD existente em `app/web/admin_routes.py` (`"ad", "CONNECTION_TEST"`) — cada ponto em try/except; duração medida; detail = erro já sanitizado; falha de registro NUNCA afeta a integração (depends T008)

**Checkpoint**: fundação pronta — model migrado, permissões seeded, eventos aditivos, `check_connection` sem envio, service base com catálogo/record/history, instrumentação ativa.

---

## Phase 3: User Story 1 — Painel com o estado real das integrações (Priority: P1) 🎯 MVP

**Goal**: Cards por integração (E-mail, 1Doc, GLPI, AD) com status padronizado, última execução, último sucesso, falhas recentes (24h) e pendentes — sem chamadas externas na renderização.

**Independent Test**: com estados conhecidos (fixtures/fakes/seed), `GET /admin/integracoes` exibe o status correto por integração — verificável isoladamente.

### Tests for User Story 1 ⚠️ (escrever PRIMEIRO, executar, confirmar VERMELHO)

- [X] T010 [P] [US1] Testes de derivação de status (spec §7) em `tests/test_central_integracoes.py`: e-mail — sem `SMTP_HOST`→NAO_CONFIGURADA, notificações desativadas→DESABILITADA, última execução FAILED→COM_ERRO, indisponibilidade→INDISPONÍVEL, sucesso recente→ATIVA, habilitado sem execuções→INATIVA; 1Doc — contrato `[PENDING C-1..C-4]`→PENDENTE (precedência sobre DESABILITADA); AD — `enabled=false`→DESABILITADA, sem server/base_dn→NAO_CONFIGURADA, teste falho→COM_ERRO/INDISPONÍVEL; GLPI — NAO_CONFIGURADA fixa
- [X] T011 [P] [US1] Testes do painel em `tests/test_central_integracoes.py`: `GET /admin/integracoes` renderiza 4 cards com nome, status, última execução, último sucesso, "Falhas recentes (24h): N" (janela explícita — P-4) e pendentes; contagens coerentes com seed de `integration_executions`/`notifications`/`onedoc_integrations`; **extensibilidade (SC-007/C1)**: registrar uma integração stub (ex.: `"webhook_exemplo"`) no catálogo em teste e afirmar que aparece no painel sem alteração estrutural da Central

### Implementation for User Story 1

- [X] T012 [US1] Implementar `get_panel(db)` + `status_fn` de cada integração em `app/services/integration_center_service.py` (derivação 100% service, precedência spec §7, sem I/O externo — NFR-004; agregações com janela 24h — plan D10) (depends T008, T010)
- [X] T013 [US1] Rota `GET /admin/integracoes` com `require_permission("integracoes.visualizar")` em `app/web/admin_routes.py` (padrão `active_tab="admin"`, contexto: cards + flash messages)
- [X] T014 [US1] Template `app/web/templates/admin/integracoes/list.html` no padrão visual vigente (cards Bootstrap, tema claro/escuro, badge por status, "—" para ausência de dado, botões Testar/Configurar condicionais a capacidades/permissões)
- [X] T015 [US1] Entradas de menu em `app/web/templates/base.html` sob `can('integracoes.visualizar')` (sidebar + dropdown Administração, ícone no padrão bi — único toque no template existente)

**Checkpoint**: US1 funcional e testável isoladamente (MVP).

---

## Phase 4: User Story 2 — Acesso restrito e segredos protegidos (Priority: P1)

**Goal**: Todas as rotas da Central negam acesso a não autorizados (deny by default) e nenhum segredo aparece em tela, auditoria, erros ou logs.

**Independent Test**: usuário sem permissão recebe 403 auditado em todas as rotas; varredura das respostas/auditoria não encontra credenciais — independente das demais histórias.

### Tests for User Story 2 ⚠️ (escrever PRIMEIRO, executar, confirmar VERMELHO)

- [X] T016 [P] [US2] Testes RBAC em `tests/test_central_integracoes.py`: cada uma das 5 rotas do contract §2 com usuário autenticado sem `integracoes.visualizar`/`integracoes.testar` → 403 amigável + evento `ACESSO_NEGADO` na auditoria; entrada de menu ausente; com `integracoes.testar` mas sem `visualizar` → POST de teste negado
- [X] T017 [P] [US2] Testes de segredos em `tests/test_central_integracoes.py` (SC-003): com ambiente fake contendo `SMTP_PASSWORD`/`ONEDOC_API_TOKEN` conhecidos, varrer HTML do painel/detalhe/histórico/propagação E registros de auditoria → 0 ocorrências dos valores; segredo aparece apenas como "configurada"/mascarado

### Implementation for User Story 2

- [X] T018 [US2] Garantir guardas por rota em `app/web/admin_routes.py` (contract §2): `require_permission` em todas; teste do AD redireciona à tela existente (guarda vigente `_ad_admin_guard` — P-3); links de reprocesso mantêm `integracao1doc.reprocessar`; nenhuma autorização paralela (depends T013)
- [X] T019 [US2] Aplicar `mask_secret()` do service aos contextos dos templates (detail/histórico) e mensagens flash em `app/web/admin_routes.py` + `app/services/integration_center_service.py` — segredo NUNCA em valor, apenas indicação de presença (depends T008)

**Checkpoint**: US1+US2 verdes — painel seguro (MVP completo de observação).

---

## Phase 5: User Story 3 — Teste de conexão auditado e não destrutivo (Priority: P2)

**Goal**: "Testar conexão" por integração com resultado amigável, registrado em histórico e auditoria, sem efeito externo.

**Independent Test**: fakes de provedor (sucesso/timeout/auth/indisponível) produzem resultado, classificação, registro em `integration_executions` e auditoria — por integração, isoladamente.

### Tests for User Story 3 ⚠️ (escrever PRIMEIRO, executar, confirmar VERMELHO)

- [X] T020 [P] [US3] Testes de `run_test` em `tests/test_central_integracoes.py`: e-mail — fake de `check_connection` (sucesso com latência; timeout→INDISPONÍVEL; auth inválida→COM_ERRO classificado "autenticação"); 1Doc — verificação INTERNA (nenhum HTTP; config ausente→mensagem clara; operação `INTERNAL_CHECK` — U1); ad — POST na rota da Central redireciona ao teste existente da tela AD (guarda vigente); glpi — teste não oferecido (404 amigável/botão ausente); cada teste grava `integration_executions` + `TESTE_INTEGRACAO_SUCESSO/FALHA`; **idempotência (SC-008/C3)**: executar o teste 2× seguidas → exatamente 2 execuções registradas (nada duplicado além do esperado); NENHUMA escrita externa ou patrimonial (FR-011/P-6)

### Implementation for User Story 3

- [X] T021 [US3] Implementar `run_test(db, key, *, user, ip_address)` em `app/services/integration_center_service.py` (delegação contract §3: email→`email_provider.check_connection`; onedoc→checagem interna de `ONEDOC_*` + estado do contrato; ad/glp→não suportado aqui) com `record_execution` + eventos de auditoria (depends T007, T008, T006)
- [X] T022 [US3] Rota `POST /admin/integracoes/{key}/testar` em `app/web/admin_routes.py` (`integracoes.testar`; ad→303 à tela AD; glpi→404 amigável; flash success/error com mensagem amigável classificada) (depends T021, T013)
- [X] T023 [US3] Botão "Testar conexão" no card de `app/web/templates/admin/integracoes/list.html` (visível só quando `supports_test` e usuário pode) (depends T022)

**Checkpoint**: US1–US3 verdes.

---

## Phase 6: User Story 4 — Histórico de execuções e diagnóstico por integração (Priority: P2)

**Goal**: Detalhe com contadores/diagnóstico e histórico paginado com filtros — respostas sem sair da Central (SC-005).

**Independent Test**: execuções semeadas em estados variados → filtros/paginação/contadores retornam exatamente o esperado — isolado.

### Tests for User Story 4 ⚠️ (escrever PRIMEIRO, executar, confirmar VERMELHO)

- [X] T024 [P] [US4] Testes do detalhe em `tests/test_central_integracoes.py`: contadores (realizadas/com erro/pendentes), última execução/último sucesso/última falha, dimensões de diagnóstico (configurada/disponível/autenticada/operacional quando verificável — FR-009), integração sem execução exibe "—" sem erro
- [X] T025 [P] [US4] Testes do histórico em `tests/test_central_integracoes.py`: filtros período/status/operação **e usuário (FR-019/C2 — execuções com `user` preenchido filtram por username; automáticas aparecem sem filtro)**; paginação (NFR-001, `page_size` limitado); lista vazia amigável; `detail` sanitizado (erro fake contendo segredo → exibido limpo); ordenação desc por `created_at`

### Implementation for User Story 4

- [X] T026 [US4] Implementar `get_detail(db, key)` em `app/services/integration_center_service.py` (usa catálogo + fontes existentes + agregações de `integration_executions`) (depends T008, T024)
- [X] T027 [US4] Rota `GET /admin/integracoes/{key}` em `app/web/admin_routes.py` (`integracoes.visualizar`; key inválida→404 amigável) (depends T026)
- [X] T028 [US4] Template `app/web/templates/admin/integracoes/detail.html` (diagnóstico, contadores, erro sanitizado, ações condicionais a capacidades/permissões) (depends T027, T019)
- [X] T029 [US4] Rota `GET /admin/integracoes/{key}/historico` + template `app/web/templates/admin/integracoes/historico.html` (filtros + paginação, usa `get_history`) (depends T026)

**Checkpoint**: US1–US4 verdes — observabilidade completa.

---

## Phase 7: User Story 5 — Propagação de movimentações (Priority: P2)

**Goal**: Visão somente leitura do estado por integração de uma movimentação (✓/⚠/—), identificando o que precisa de ação.

**Independent Test**: movimentações com estados conhecidos (fixtures) → estados corretos por integração; antiga sem registros → "—" — isolado.

### Tests for User Story 5 ⚠️ (escrever PRIMEIRO, executar, confirmar VERMELHO)

- [X] T030 [P] [US5] Testes de propagação em `tests/test_central_integracoes.py`: movimentação com e-mail SENT + 1Doc PENDING → "✓ enviado / ⚠ pendente / — não aplicável (GLPI)"; 1Doc FAILED → indicativo de reprocessar (link à tela existente); movimentação anterior às integrações → todas "—"; nenhuma alteração na movimentação (somente leitura); **idempotência no reprocesso (SC-008/C3)**: após `reprocess` (fake provider) retornando sucesso, a movimentação continua com exatamente 1 registro em `onedoc_integrations` (UNIQUE respeitado, nada duplicado)

### Implementation for User Story 5

- [X] T031 [US5] Implementar `get_movement_propagation(db, movement_id)` em `app/services/integration_center_service.py` (leituras `notifications`/`onedoc_integrations`; sem lógica patrimonial) (depends T008, T030)
- [X] T032 [US5] Rota `GET /admin/integracoes/movimentacao/{movement_id}` + template `app/web/templates/admin/integracoes/movimentacao.html` (inclui link de reprocesso quando `integracao1doc.reprocessar`) + link no detail.html (depends T031, T028)

**Checkpoint**: US1–US5 verdes.

---

## Phase 8: User Story 6 — Administração: habilitar/desabilitar e configurações (Priority: P3)

**Goal**: Condução às configurações existentes e reflexo de DESABILITADA — sem interruptor paralelo (FR-015).

**Independent Test**: atalhos respeitam as guardas das telas de destino; desativação pelas telas existentes reflete no status — isolado.

### Tests for User Story 6 ⚠️ (escrever PRIMEIRO, executar, confirmar VERMELHO)

- [X] T033 [P] [US6] Testes de condução em `tests/test_central_integracoes.py`: atalho Notificações exige `notificacoes.gerenciar` na tela de destino; tela AD mantém guarda `usuarios.editar`+`perfis.editar`; tela 1Doc mantém `integracao1doc.reprocessar`; após desativar notificações/toggle AD nas telas existentes → card reflete DESABILITADA; 1Doc indica "ativação por ambiente (`ONEDOC_ENABLED`)" sem interruptor novo

### Implementation for User Story 6

- [X] T034 [US6] Links "Configurar" por integração no `list.html`/`detail.html` (destinos: `/admin/notificacoes`, `/admin/ad`, `/admin/integracao-1doc`) + indicação de onde ativar quando sem mecanismo de UI (depends T014, T028)

**Checkpoint**: todas as US verdes.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentação, validação ponta a ponta e verificação de escopo.

- [X] T035 [P] Atualizar documentação (Constitution XI): seção da Central em `README.md`/`docs/` (tela, permissões, status, janela 24h, teste sem envio) + artigo na ajuda central via `app/services/help_service.py` no padrão `help_article_030.py`
- [X] T036 [P] Conferir `.env.example`/docs: nenhuma variável nova (Central não introduz configuração) — nota de que o status reflete as variáveis existentes
- [X] T037 Executar validação do `specs/032-central-integracoes/quickstart.md` ponta a ponta (RBAC manual, mascaramento, teste com fake + SMTP real opcional, histórico, propagação, janela 24h)
- [X] T038 Validação final (Constitution XII): suíte completa verde incluindo novos testes; `git status --short` confere escopo do plan.md (nenhum arquivo intocável alterado); checklist da Constitution revisado

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: imediato, sem dependências
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as US (T004←T003; T008←T003; T009←T008; demais [P] independentes)
- **User Stories (Phases 3–8)**: dependem da Phase 2; ordem recomendada P1→P1→P2→P2→P2→P3
- **Polish (Phase 9)**: depende de todas as US desejadas

### User Story Dependencies

- **US1 (P1)**: após Foundational — nenhuma dependência de outra US
- **US2 (P1)**: após Foundational; usa rotas/rotas-base da US1 (T013) para os testes de negação — mantém-se testável isoladamente com seed próprio
- **US3 (P2)**: após Foundational (usa T006/T007/T008); botão no card da US1 (T023←T014)
- **US4 (P2)**: após Foundational; detail reusa `mask_secret` (T019)
- **US5 (P2)**: após Foundational; link a partir do detail (T032←T028)
- **US6 (P3)**: após US1/US4 (coloca links nas telas prontas)

### Within Each User Story

- Tests PRIMEIRO (VERMELHO) → implementation → VERDE
- Service antes de rota; rota antes de template
- Story completa antes da próxima prioridade

### Parallel Opportunities

- Phase 2: T003/T005/T006/T007 em paralelo; T009 após T008
- Tests [P] de cada US em paralelo entre si
- US3/US4/US5 podem progredir em paralelo após Foundational (arquivos de template distintos; rotas em `admin_routes.py` — coordenar merges)

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Phase 1 (Setup) → Phase 2 (Foundational)
2. US1 (painel) + US2 (acesso/segredos) → **STOP and VALIDATE**: RBAC + mascaramento + status corretos
3. Entregável: observação segura das 4 integrações

### Incremental Delivery

- +US3 → diagnóstico ativo (teste de conexão auditado)
- +US4 → histórico/diagnóstico detalhado (SC-005 completo)
- +US5 → propagação por movimentação
- +US6 → condução administrativa finalizada

### Nota de produção (pendências externas — spec §18)

- A Central opera integralmente SEM o fornecedor: 1Doc permanece PENDENTE (aguardando C-1..C-8, `docs/SOLICITACAO_API_1DOC.md`) e GLPI NÃO CONFIGURADA.
- Ativação do 1Doc (`ONEDOC_ENABLED=true`) e implementação do GLPI são features/fases futuras dentro da estrutura já criada — nenhum retrabalho da Central.

## Notes

- [P] = arquivos diferentes, sem dependência pendente
- Todos os testes com fakes (`provider` injetável / monkeypatch) — precedentes `test_onedoc.py`, `test_notificacoes.py`
- Commit após cada tarefa ou grupo lógico coerente
- Evitar: tarefas vagas, conflito no mesmo arquivo (`admin_routes.py` e `list.html` são compartilhados — sequenciar), dependência cruzada que quebre independência
