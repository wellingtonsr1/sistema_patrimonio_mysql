---
description: "Task list for feature implementation"
---

# Tasks: Central de Integrações — Saúde do Sistema e das Integrações (047)

**Input**: Design documents from `/specs/047-saude-central-integracoes/`

**Prerequisites**: plan.md (required), spec.md (required), research.md (R1–R8), data-model.md, contracts/ui-contract-central-saude.md, quickstart.md

**Tests**: Testes automatizados **SIM** (o pedido da 047 exige §25 Testes A–M — diferente das features de larguras): novo arquivo `tests/test_central_saude.py` com fakes/monkeypatch (nunca serviços externos reais — F10/032) + suíte existente como regressão (SC-006, baseline 748 passed). Superfícies: `app/services/integration_center_service.py` (extensão) e `app/web/templates/admin/integracoes/list.html` (apresentação) — **`admin_routes.py` intocado** (`get_panel` já propaga novos cards).

**Organization**: Tasks agrupadas por user story (US1 painel consolidado → US2 testes manuais → US3 segurança/auditoria → US4 responsividade), precedidas de setup e seguidas de polish. Regra máxima: **reutilizar mecanismos existentes** (R5 — `main.py`, `backup_*`, `ad_*`, `email_*`, `onedoc_*`, `permission_service` com zero linhas alteradas); zero migração de banco (SC-009); zero permissão nova (FR-020).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: service em `app/services/integration_center_service.py`; template em `app/web/templates/admin/integracoes/list.html`; testes em `tests/test_central_saude.py`; ajuda em `app/services/help_article_032.py`; docs em `docs/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar os fatos de integração e o estado verde de partida.

- [x] T001 Confirmar os fatos de integração em `app/services/integration_center_service.py` sem alterar nada: catálogo `INTEGRATIONS` (email/onedoc/ad/glpi com `status_fn`, `supports_test`, `config_route`), vocabulário `STATUS_*` + `STATUS_LABELS`, `mask_secret`/`_sanitize_detail`, `get_panel(db)` (itera catálogo + `_execution_counters` + `_pending_count`), `run_test(db, key, ...)` (dispatcher com ramos email/onedoc e `record_execution` + `write_audit` com `ACTION_CENTRAL_TESTE_*`), `_onedoc_internal_check`; confirmar fontes: `backup_scheduler.scheduler_status()` e `retention_monitoring_summary()` (sem segredos), `external_backup_service.get_external_config`/`test_destination`, modelos `BackupRecord` (status/`size_bytes`/`removed_at`/`timestamp`), `BackupExternalConfig` (enabled/`dest_path`), `BackupExternalRecord` (status/`copied_at`/`error_description`); confirmar template `app/web/templates/admin/integracoes/list.html` (cards, badges por status, dl de contadores, botões Detalhes/Testar/Configurar); rodar a suíte BASELINE: `.venv/bin/python -m pytest tests/ -q` (748 passed esperado)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Vocabulário e mecanismos compartilhados que TODAS as stories usam.

**⚠️ CRITICAL**: As status_fn e o dispatcher estendidos dependem destas adições aditivas.

- [x] T002 Em `app/services/integration_center_service.py`: adicionar constante **aditiva** `STATUS_ATENCAO = "ATENCAO"` com label "Atenção" em `STATUS_LABELS` (R1 — nenhum status existente muda de significado; badge amarelo `bg-warning text-dark` no template)
- [x] T003 Em `app/services/integration_center_service.py`: estender o dicionário retornado por `get_panel` para propagar o resumo por card — `status_detail["summary"]` já viaja dentro de `status_detail`; garantir que cards de componentes sem summary simplesmente não o exibam (R3; template decide a renderização). Nenhuma mudança de assinatura de rota

**Checkpoint**: Fundação pronta — status_fn dos componentes podem começar.

---

## Phase 3: User Story 1 - Painel de saúde consolidado (Priority: P1) 🎯 MVP

**Goal**: Os dez componentes (Aplicação, Banco, Armazenamento, AD, E-mail, GLPI, Backup Local, Backup Externo, Agendador, 1Doc) visíveis em `/admin/integracoes` com status padronizado e resumo útil, derivados somente das fontes existentes, sem I/O externo ao renderizar (quickstart Cenários A–I; FR-001…FR-012).

**Independent Test**: com estados conhecidos (fakes/seeds), `GET /admin/integracoes` exibe o status e o resumo corretos por componente — 0 chamadas a mecanismos de teste durante o GET.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Criar `tests/test_central_saude.py` com testes que FALHAM antes da implementação: painel renderiza 10 cards na ordem do catálogo (Cenário A); `_database_status_fn` ATIVA/FALHA (B); GLPI NAO_CONFIGURADA sem botão E 1Doc PENDENTE (C/D — US1.6); backup_externo ATIVA × COM_ERRO por `BackupExternalRecord` (E/F); `_scheduler_status_fn` ATIVA × DESABILITADA (I); backup_local com regra do clarify (ativo: OK/ATENCAO por ciclo perdido com folga de 1 ciclo, COM_ERRO sem válido; manual: espelha última falha, sem alerta por atualidade); storage com regra do clarify (ATENCAO quando livre < `size_bytes` do último SUCCESS com `removed_at IS NULL`; COM_ERRO em diretório ausente/OSError; ATIVA sem referência); **contagem de chamadas = 0** a `generate_backup`/`test_destination`/`check_connection`/`ad_ldap.test_connection` durante o GET (SC-002); isolamento: monkeypatch fazendo uma status_fn levantar exceção → card em COM_ERRO e demais renderizados (R6/SC-007)

### Implementation for User Story 1

- [x] T005 [US1] Em `app/services/integration_center_service.py`: criar as 6 status_fn com try/except total (R6 — exceção → `STATUS_COM_ERRO` + summary "Não foi possível verificar este componente", mensagem sanitizada): `_app_status_fn` (ATIVA "Operacional"; sem verificação ativa), `_database_status_fn` (`SELECT 1` na sessão da request — mesmo padrão do `/health`; apenas estado, sem latência — clarify), `_storage_status_fn` (diretórios de backup + destino externo se habilitado; `Path.exists()` + `shutil.disk_usage`; regra do clarify com referência = `size_bytes` do último `BackupRecord` SUCCESS `removed_at IS NULL`; sem escrever arquivos), `_backup_local_status_fn` (`retention_monitoring_summary` + regime pelo `scheduler_status()["enabled"]`; regra do clarify), `_backup_externo_status_fn` (config ausente → NAO_CONFIGURADA; enabled False → DESABILITADA; última cópia FAILURE → COM_ERRO; SUCCESS → ATIVA "OK"; habilitado sem cópia → INATIVA), `_scheduler_status_fn` (`scheduler_status()`; enabled False → DESABILITADA "Desabilitado"; `last_result` com erro → COM_ERRO) — cada uma retornando `detail["summary"]` com 1–3 pares (rótulo, valor) conforme data-model §4 (T004 passa a passar)
- [x] T006 [US1] Em `app/services/integration_center_service.py`: adicionar as 6 entradas ao catálogo `INTEGRATIONS` **na ordem** app, database, storage, ad, email, glpi, backup_local, backup_externo, scheduler, onedoc (P-1/P-3) com `label_by_status` (R2: app ATIVA→"Operacional"; database ATIVA→"Conectado"/COM_ERRO→"Falha"; storage ATIVA→"OK"/ATENCAO→"Espaço limitado"/COM_ERRO→"Falha"; backup_local ATIVA→"OK"/ATENCAO→"Sem backup recente"/COM_ERRO→"Falha"; backup_externo ATIVA→"OK"/COM_ERRO→"Falha"; scheduler ATIVA→"Ativo"/DESABILITADA→"Desabilitado"/COM_ERRO→"Falha"), `test_label` opcional (backup_externo → "Testar destino" — R4/E2; demais herdam "Testar conexão"), `supports_test` apenas para backup_externo entre os novos (R7 — AD mantém teste na tela própria, GLPI sem teste), `config_route="/admin/backups"` para storage/backup_local/backup_externo/scheduler, resolução do rótulo em `get_panel` como `label_by_status.get(status) or STATUS_LABELS.get(status)` e propagação de `test_label` no dict do card (T005 já concluída)
- [x] T007 [US1] Em `app/web/templates/admin/integracoes/list.html`: classes de coluna `col-12 col-md-6 col-xl-4` (grid 3 colunas ≥1200px — FR-023); badge `ATENCAO` → `bg-warning text-dark`; renderizar os pares `card.status_detail.get('summary')` em `div.small` (quando presentes) mantendo a `dl` existente para todos os cards; rótulo do botão de teste = `card.test_label or "Testar conexão"` (backup_externo exibe "Testar destino" — E2); sem CSS novo e sem JS novo (T006 concluída; Cenário A do quickstart passa)
- [x] T008 [US1] Rodar `.venv/bin/python -m pytest tests/test_central_saude.py tests/test_central_integracoes.py -q` (novos testes verdes; 032 sem regressão) e validar manualmente o Cenário A–I do quickstart com login admin

**Checkpoint**: MVP — painel consolidado com 10 componentes; suíte parcial verde; nenhum mecanismo duplicado.

---

## Phase 4: User Story 2 - Testes manuais não destrutivos (Priority: P1)

**Goal**: Ação "Testar" disponível apenas nos componentes com mecanismo existente; backup_externo usa a função `test_destination` da 045 (sem gerar backup, sem deixar arquivos); AD/E-mail/1Doc/GLPI mantêm comportamento da 032 (quickstart "Teste do destino externo"; FR-017/FR-021/R4).

**Independent Test**: POST `/admin/integracoes/backup_externo/testar` com destino válido (tmp_path) retorna a mensagem da função existente, registra `IntegrationExecution` + `write_audit`, não gera backup e não deixa arquivo no destino.

### Tests for User Story 2 ⚠️

- [x] T009 [P] [US2] Em `tests/test_central_saude.py`: testes do dispatcher — POST com `integracoes.testar` em backup_externo (tmp_path): sucesso registra `IntegrationExecution` (op `OP_CONNECTION_TEST`) + evento `ACTION_CENTRAL_TESTE_*` e **não deixa arquivo** no destino (Cenário US2.2); destino inválido → mensagem amigável sanitizada sem quebrar (US2.3); `run_test` para keys sem mecanismo (app/database/storage/backup_local/scheduler) retorna "Teste não suportado" (FR-017); botão não renderiza para esses keys; AD continua conduzindo à tela própria (R7)

### Implementation for User Story 2

- [x] T010 [US2] Em `app/services/integration_center_service.py`: estender `run_test` com o ramo `backup_externo` → `from app.services.external_backup_service import test_destination` + `get_external_config(db)` → `test_destination(config.dest_path)` (R4 — reuso integral da função existente da 045; nenhum segundo mecanismo; latência via `time.monotonic()` como nos ramos existentes); registro via `record_execution` + `write_audit` existentes (nenhum segredo no detail — `_sanitize_detail`); nenhuma alteração em `external_backup_service.py` (T006 concluída)
- [x] T011 [US2] Verificar `get_detail` + `app/web/templates/admin/integracoes/detail.html` com as 6 novas keys (E1): `GET /admin/integracoes/app` (e database/storage/backup_local/backup_externo/scheduler) renderiza o detalhe genérico existente sem erro — descrição, finalidade, status, contadores de execução ("—" quando vazios), botão de teste apenas quando `supports_test` e "Configurar" quando `config_route`; ajuste MÍNIMO apenas se algo quebrar (nenhuma seção nova de detalhe — spec §3). Em seguida rodar `.venv/bin/python -m pytest tests/test_central_saude.py tests/test_backup_externo.py tests/test_central_integracoes.py -q` e validar manualmente o POST com destino real configurado (o botão "Testar destino" aparece no card backup_externo)

**Checkpoint**: US1+US2 — painel + testes manuais com reutilização integral comprovada.

---

## Phase 5: User Story 3 - Segurança, auditoria e acesso (Priority: P1)

**Goal**: RBAC existente governa tudo; nenhum segredo em nenhuma superfície; nenhum evento de auditoria por carregamento de página (quickstart "Segurança e RBAC"; FR-019/FR-020/US3.4).

**Independent Test**: usuário sem `integracoes.visualizar` recebe 403; renderização do painel não contém segredos; GETs repetidos não criam eventos de auditoria.

### Tests for User Story 3 ⚠️

- [x] T012 [P] [US3] Em `tests/test_central_saude.py`: 403 para usuário sem `integracoes.visualizar` em `GET /admin/integracoes` e `GET /admin/integracoes/{key}` (negação padrão; demais rotas da Central — POST/histórico/propagação — permanecem cobertas pela suíte 032 via T008/T016, E4); varredura da renderização (com SMTP/1Doc configurados via monkeypatch de ambiente) sem ocorrência de `SMTP_PASSWORD`/`ONEDOC_API_TOKEN`/`AD_BIND_PASSWORD` (SC-003); GETs repetidos do painel criam **0** registros em `IntegrationExecution` e 0 em `audit_logs` (US3.4); caminhos longos de destino truncados no summary (sem segredo — data-model §6)

### Implementation for User Story 3

- [x] T013 [US3] Revisão de conformidade em `app/services/integration_center_service.py` + `app/web/templates/admin/integracoes/list.html`: confirmar que toda mensagem de erro passa por `_sanitize_detail`/padrão vigente antes de chegar ao summary, que caminhos aparecem truncados quando longos e que nenhum card exibe campo de credencial (T005/T007 concluídas; os testes T012 passam sem ajuste adicional se o design foi seguido)

**Checkpoint**: US1+US2+US3 — painel seguro, auditado e sem segredos.

---

## Phase 6: User Story 4 - Responsividade e consistência visual (Priority: P2)

**Goal**: Grid 3/2/1 colunas nos breakpoints, temas claro/escuro íntegros, componentes visuais existentes (quickstart Testes J/K; FR-022/FR-023/SC-008).

**Independent Test**: renderização em 1440/1024/375px nos dois temas, sem sobreposição, com badges legíveis — comparada ao padrão das demais telas admin.

- [x] T014 [US4] Validar responsividade e temas em `app/web/templates/admin/integracoes/list.html`: 1440px → 3 colunas na ordem do mock (linha 1: Aplicação/Banco/Armazenamento; linha 2: AD/E-mail/GLPI; linha 3: Backup Local/Backup Externo/Agendador; 1Doc no fechamento); 1024px → 2 colunas; 375px → 1 coluna sem sobreposição; tema escuro com contraste dos badges `bg-warning text-dark`, `bg-success`, `bg-danger`, `bg-secondary`; registro do resultado em `specs/047-saude-central-integracoes/validacao.md` (sem inventar medições; correções pontuais no template se necessário)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentação, regressão completa e validação formal.

- [x] T015 [P] Atualizar `app/services/help_article_032.py` (artigo da Central de Integrações na ajuda) refletindo os 10 componentes, o significado de ATENÇÃO e o "Testar destino" do backup externo; atualizar `docs/` (INVENTARIO_TECNICO/ARQUITETURA_E_MANUTENCAO) onde a Central é descrita — Princípio XI, sem inventar comportamento
- [x] T016 Rodar a suíte completa: `.venv/bin/python -m pytest tests/ -q` — 100% verde (SC-006; baseline 748 + novos) e `git diff` coerente com o plan: somente `integration_center_service.py`, `list.html`, `help_article_032.py`, `docs/`, `tests/test_central_saude.py` e arquivos da spec alterados; **zero linhas** em `app/main.py`, `backup_service.py`, `backup_scheduler.py`, `external_backup_service.py`, `ad_service.py`/`ad_ldap.py`, `email_provider.py`/`notification_service.py`, `onedoc_*`, `permission_service.py`, `admin_routes.py` (R5)
- [x] T017 Criar `specs/047-saude-central-integracoes/validacao.md` (SC-010): resultado de cada cenário do quickstart (A–M), comprovação consulta×teste (contagem de chamadas), prova de isolamento por card, verificação de segredos, responsividade/temas, suíte executada — não inventar resultados
- [ ] T018 Marcar tasks concluídas e commit do grupo lógico no padrão do repositório (subject "Feature 047: ..." sem acentos, footer Codebuff 🤖 Generated with Codebuff / Co-Authored-By: Codebuff <noreply@codebuff.com>) + relatório final da implementação conforme §27 do pedido (arquivos alterados/porquê, reutilizações, cadeias de status, permissões e auditoria reutilizadas, testes e resultados, arquivos NÃO alterados e porquê, limitações)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: imediato; baseline da suíte
- **Foundational (T002–T003)**: bloqueia US1 (vocabulário/summary)
- **US1 (T004–T008)**: T004 (testes primeiro, falhando) → T005 → T006 → T007 → T008
- **US2 (T009–T011)**: depende de T006 (catálogo com backup_externo) — T009 pode ser escrito em paralelo com T005
- **US3 (T012–T013)**: depende de T005/T007 (superfícies prontas para revisão)
- **US4 (T014)**: depende de T007 (grid aplicado)
- **Polish (T015–T018)**: depende de tudo

### User Story Dependencies

- **US1 (P1)**: independente após Foundational — entrega o painel consolidado (MVP)
- **US2 (P1)**: complementa a US1 no mesmo service (dispatcher); depende do catálogo ampliado
- **US3 (P1)**: verificação de segurança sobre as superfícies da US1/US2
- **US4 (P2)**: validação/apresentação sobre o template da US1

### Parallel Opportunities

- T004 e T009 e T012 são [P] (arquivo de testes único, mas escrevíveis em lotes independentes antes das respectivas implementações)
- T015 é [P] (help/docs, arquivo próprio)
- Nenhuma task de implementação paralela: service e template são arquivos únicos compartilhados pelas stories — alterações sequenciais evitam conflito

## Implementation Strategy

### MVP First (US1)

1. Setup + Foundational (T001–T003)
2. US1 (T004–T008) → **STOP and VALIDATE**: painel com 10 componentes, consulta sem I/O caro, suíte parcial verde
3. Só então US2 (testes manuais), US3 (segurança), US4 (responsividade) e Polish

### Incremental Delivery

1. US1 → visão consolidada operacional
2. US2 → diagnóstico ativo com reutilização integral
3. US3 → garantias de segurança/auditoria comprovadas por testes
4. US4 → conformidade visual/responsiva
5. Polish → docs, regressão total, validacao.md, commit + relatório

## Notes

- **Reuso acima de tudo**: cada verificação aponta o mecanismo existente reutilizado (R5) — proibido segundo health check/teste/scheduler/auditoria/backup/cliente
- **Consulta ≠ Teste**: 0 chamadas a mecanismos de teste durante o GET (SC-002, provado por contagem)
- **Zero migração** (SC-009), **zero permissão nova** (FR-020), **zero CSS/JS global novo** (FR-022)
- **Estados honestos**: GLPI "Não Configurada" e 1Doc "Pendente" até que existam implementações reais (FR-015/FR-016)
- **Sem nomes de controles em comentários novos** (lição `b75ba99`) e **sem `@media print`** (tela não-relatório)
- Commit após o grupo lógico (US1+US2+US3+US4+polish) — mensagem no padrão do repositório
- Evitar: refatoração do service da 032 além do previsto, alteração de rotas, regras globais de CSS, mudança em outras telas
