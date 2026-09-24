---

description: "Task list for feature implementation"
---

# Tasks: Conferência de Inventário Offline — PWA + Service Worker + IndexedDB (033)

**Input**: Design documents from `/specs/033-inventario-offline-pwa/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/inventario-offline-contract.md, quickstart.md

**Tests**: incluídos — a suíte é requisito de não regressão (Constitution VIII) e o SC-010 exige os 19 cenários de origem em `tests/test_inventario_offline.py`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: `app/` em camadas (models → services → api/web) + `tests/` na raiz; JS estático sem build step em `app/web/static/js/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparação mínima — nada de infraestrutura nova de projeto (stack intocável, Constitution).

- [x] T001 Ler/confirmar padrões existentes de model, service, router API e permissões em `app/models/inventario.py`, `app/models/enums.py`, `app/services/inventario_service.py`, `app/api/deps.py`, `app/api/v1_router.py` e `app/services/permission_service.py` (sem alterar nenhum — insumo para as tasks seguintes)
- [x] T002 Atualizar `.specify/feature.json` para apontar para `specs/033-inventario-offline-pwa`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Entidades e eventos que TODAS as stories usam.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Criar enum `InventarioOfflineColetaStatus` em `app/models/enums.py` com valores exatos `ACCEPTED`, `DUPLICATED`, `CONFLICT`, `REJECTED`, `RECONCILED` (vocabulário controlado, aditivo — data-model.md)
- [x] T004 Criar model `InventarioOfflineColeta` em `app/models/inventario_offline.py` com todas as colunas, UNIQUE `(inventory_id, client_operation_id)` e índices `(inventory_id, status)`, `(inventory_id, asset_id)`, `device_id` exatamente conforme data-model.md (criação aditiva idempotente via `init_db` — Princípio VII)
- [x] T005 Registrar o model em `app/database.py` (import para criação da tabela pelo `init_db`)
- [x] T006 [P] Adicionar eventos de auditoria `INVENTARIO_OFFLINE_PREPARADO`, `INVENTARIO_OFFLINE_SYNC`, `INVENTARIO_OFFLINE_CONFLITO`, `INVENTARIO_OFFLINE_REJEITADO`, `INVENTARIO_OFFLINE_RECONCILED` em `app/services/audit_service.py`, no padrão existente e sem credenciais (FR-044/Princípio IX)

**Checkpoint**: Fundação pronta — model + enum + auditoria disponíveis; stories podem começar.

---

## Phase 3: User Story 1 - Preparar inventário para coleta offline (Priority: P1) 🎯 MVP

**Goal**: Usuário autorizado, conectado, gera e guarda no dispositivo o pacote offline derivado do snapshot `inventario_itens`, com somente os dados mínimos de conferência (FR-001..FR-005).

**Independent Test**: preparar o pacote conectado e verificar no dispositivo que constam apenas os dados mínimos do FR-003 e nada além (nem dados administrativos, nem credenciais) — não requer estar offline nem sincronizar.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T007 [P] [US1] Criar o arquivo `tests/test_inventario_offline.py` e escrever os testes primeiro: RBAC da preparação (401 sem sessão, 403 sem `inventario.conferir` auditado, sucesso com permissão); pacote contém somente campos do FR-003 (SC-008); 409 para inventário encerrado (C-2/P-2); 422 sem itens e acima de 1.000 itens (D9); teste de volume do pacote com 1.000 itens (SC-001); preparação não altera dados oficiais (FR-005); `snapshot_version` determinístico (FR-004); auditoria `INVENTARIO_OFFLINE_PREPARADO` sem credenciais

### Implementation for User Story 1

- [x] T008 [US1] Implementar geração do pacote em `app/services/inventario_offline_service.py`: leitura do snapshot `inventario_itens`, `snapshot_version` = hash SHA-256 determinístico do conjunto ordenado `(asset_id, item_id, status)` (D9), campos mínimos por item conforme FR-003/contrato §2 (incl. `qr_url` = `{origin}/assets/{asset_id}` — D2), validação de estados preparáveis PLANNED/IN_PROGRESS apenas (409 se encerrado — C-2), 422 sem itens/acima de 1.000 itens, nenhum write no cadastro (FR-005)
- [x] T009 [US1] Criar router `app/api/inventario_offline_api.py` com `POST /api/v1/inventarios/{inventory_id}/offline/package` e schemas Pydantic do contrato §2; erros no padrão `{"detail": ...}` (401/403/404/409/422); permissão `inventario.conferir` (P-1/D11); auth por sessão via `require_api_auth` (C-1)
- [x] T010 [US1] Incluir o router em `app/api/v1_router.py` via `include_router(..., dependencies=[Depends(require_api_auth)])` (padrão existente)
- [x] T011 [US1] Registrar auditoria `INVENTARIO_OFFLINE_PREPARADO` na preparação (inventário, contagem de itens, snapshot_version — contrato §2)
- [x] T012 [P] [US1] Adicionar botão "Preparar coleta offline" em `app/web/templates/inventarios/detail.html` (visível via `can('inventario.conferir')`, apenas PLANNED/IN_PROGRESS), chamando o endpoint e salvando o pacote no dispositivo com confirmação "Pronto para uso offline"
- [x] T013 [US1] Implementar núcleo do `app/web/static/js/inventario_offline.js`: IndexedDB `sispatrimonio_offline` version 1 com stores `packages`/`coletas`/`sync_queue`/`device_info` e keyPaths do D3; migração versionada via `onupgradeneeded` que nunca apaga dados (FR-038/SC-009); `device_id` UUID persistente (FR-028) com `localStorage` restrito a `sp_device_id` (FR-006); salvar/ativar o pacote sem dados sensíveis (FR-031)
- [x] T014 [US1] Atualizar `docs/INVENTARIO_TECNICO.md` e o README (seção do módulo Inventário) com a preparação offline implementada (Princípio XI)

**Checkpoint**: US1 funcional e testável independentemente: pacote gerado, validado, auditado e salvo no dispositivo.

---

## Phase 4: User Story 2 - Coletar em campo sem conexão (Priority: P1)

**Goal**: Sem conexão, a área de coleta (servida pelo Service Worker) lista/pesquisa itens, lê QR/tombamento e registra conferências espelhando o vocabulário online (C-3), com divergências, bens não previstos e persistência durável (FR-006..FR-017).

**Independent Test**: com pacote no dispositivo e sem conexão, realizar conferências (inclusive divergência e bem não previsto), fechar e reabrir o navegador: tudo permanece lá e consistente.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T015 [P] [US2] Escrever testes primeiro em `tests/test_inventario_offline.py` (lado servidor usável pela coleta): rota da shell offline autenticada e com `inventario.visualizar`; sanitização de observação; validação de referências de local/responsável; derivação de resultado conforme regras do fluxo online (C-3)

### Implementation for User Story 2

- [x] T016 [P] [US2] Criar shell cacheável `app/web/templates/inventarios/offline.html` com tema claro/escuro e componentes Bootstrap existentes (FR-043), indicadores de modo offline (FR-041) e nada administrativo (FR-030)
- [x] T017 [P] [US2] Criar Service Worker `app/web/static/js/sw.js`: `CACHE_VERSION = "inventario-offline-v1"` acoplado ao schema do IndexedDB (D4); precache por allowlist explícita (shell + JS + CSS + manifest + ícones); cache-first apenas na allowlist e navegação cache-first apenas em `/inventarios/{id}/offline`; network-only para todo o resto, incluindo `/api/*` (FR-035/FR-036); ativação remove caches antigos; `skipWaiting` + `clients.claim()` controlados; fallback estático para navegação offline fora da allowlist
- [x] T018 [P] [US2] Criar `app/web/static/manifest.webmanifest` (nome, nome curto, start_url, display, ícones, tema/background) na identidade visual existente (FR-034)
- [x] T019 [P] [US2] Gerar ícones PWA em `app/web/static/icons/` a partir da identidade visual atual (FR-034)
- [x] T020 [P] [US2] Criar `app/web/static/js/qr_reader.js`: BarcodeDetector nativa como primário (D1), extração do `asset_id` por regex da URL do QR existente (D2), fallback permanente de digitação manual do tombamento/URL (FR-010/FR-011)
- [x] T021 [US2] Registrar o Service Worker e o `<link rel="manifest">` em `app/web/templates/base.html`, condicionados às páginas permitidas, sem afetar demais rotas (FR-035/FR-046)
- [x] T022 [US2] Implementar handler `GET /inventarios/{inventory_id}/offline` em `app/web/routes.py` (autenticado, permissão `inventario.visualizar` — D11), servido cache-first pelo SW apenas nesta rota
- [x] T023 [US2] Implementar coleta em `app/web/static/js/inventario_offline.js`: lista/pesquisa de itens com contadores (FR-009), registro de conferência espelhando o vocabulário online (C-3), com o responsável encontrado capturado somente para a coleta (sem gravação no item — ver Notas), derivação automática de `LOCAL_DIFERENTE` (FR-012), nenhuma alteração cadastral (FR-013), ocorrência de bem não previsto (FR-014), não-marcar NAO_ENCONTRADO por omissão (FR-015), persistência durável (FR-016) e gravação mesmo com sessão expirada (C-4)
- [x] T024 [US2] Implementar `GET /api/v1/inventarios/{inventory_id}/offline/ping` em `app/api/inventario_offline_api.py` (contrato §1): permissão `inventario.visualizar`, sem efeito colateral, retorna `ok`, `inventory_status` e `server_time` — base da verificação real de conectividade (FR-042); executar antes de T025 (painel client) e após a criação do router em T009/T010
- [x] T025 [US2] Implementar painel/indicadores em `app/web/static/js/inventario_offline.js`: online/offline com verificação leve real via `GET .../offline/ping` (FR-042) e estados locais visíveis (FR-009/FR-018)
- [x] T026 [US2] Atualizar `docs/INVENTARIO_TECNICO.md` e o README (seção do módulo Inventário) com a coleta offline (Princípio XI)

**Checkpoint**: Coleta offline completa e testável sem rede; sincronização ainda não implementada.

---

## Phase 5: User Story 3 - Sincronização confiável quando a rede retorna (Priority: P1)

**Goal**: Fila local envia coletas a `POST .../offline/sync`; servidor revalida tudo (FR-025) e grava exclusivamente via `InventarioService.record_check`/`register_unlisted_asset` (FR-026); resultado estruturado por operação; idempotência por UNIQUE `(inventory_id, client_operation_id)`; conflitos preservados (C-5/FR-027); coleta local nunca apagada antes de confirmação inequívoca (FR-019).

**Independent Test**: com coletas pendentes, sincronizar (incluindo reenvio, queda de rede no meio e conflitos) e verificar no banco oficial que aceitas estão registradas uma única vez, rejeitadas estão explicadas e nada foi perdido.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T027 [P] [US3] Escrever testes primeiro em `tests/test_inventario_offline.py`: sync com resultado estruturado (FR-024); idempotência por reenvio (SC-004) e resultado igual → `duplicated` (C-5); resultado diferente → `CONFLICT` com `client_payload` íntegro, nunca sobrescrita (C-5/FR-027/SC-006); revalidação do servidor (inventário encerrado → todas rejeitadas com motivo — C-2/FR-025; asset fora do snapshot; `snapshot_mismatch`); gravação exclusiva via services existentes (FR-026); sync parcial reenvia só pendentes (SC-005); `received_at` oficial + `collected_at` preservado (FR-045); auditoria `INVENTARIO_OFFLINE_SYNC/CONFLITO/REJEITADO` sem credenciais

### Implementation for User Story 3

- [x] T028 [US3] Implementar processamento do lote em `app/services/inventario_offline_service.py`: revalidação completa por operação (inventário aberto, `snapshot_version`, asset/item do snapshot, enums, local/responsável existentes — `found_custodian_id` validado como referência e preservado somente na coleta/`client_payload`, nunca aplicado ao item nem alterando `record_check`; ver Notas), idempotência por UNIQUE + resultado igual → `duplicated` (C-5), resultado diferente → `CONFLICT` preservando `client_payload` (C-5/FR-027), rejeições com `reason` estável e `detail` claro, gravação só via `record_check`/`register_unlisted_asset` (FR-026), resposta `accepted`/`duplicated`/`conflicts`/`rejected` (contrato §3), `received_at` UTC (FR-045), processamento por operação que preserva aceitas em queda de rede (FR-022/SC-005)
- [x] T029 [US3] Adicionar `POST /api/v1/inventarios/{inventory_id}/offline/sync` em `app/api/inventario_offline_api.py` (contrato §3): schemas Pydantic do lote (até 1.000 operações — D5), permissão `inventario.conferir`, resposta estruturada
- [x] T030 [US3] Registrar auditoria do sync no service: `INVENTARIO_OFFLINE_SYNC` (contagens, device_id), `INVENTARIO_OFFLINE_CONFLITO` por conflito, `INVENTARIO_OFFLINE_REJEITADO` por rejeição, sem credenciais (FR-044)
- [x] T031 [US3] Adicionar `GET .../offline/coletas?status=&device_id=` (contrato §4) e `POST .../offline/coletas/{coleta_id}/reconcile` (contrato §5) em `app/api/inventario_offline_api.py`: consulta exige `inventario.visualizar`, reconcile exige `inventario.conferir`
- [x] T032 [US3] Implementar no service a consulta de coletas (filtros, sem credenciais) e a reconciliação `KEEP`/`APPLY` (D8): `KEEP` mantém estado do item; `APPLY` grava via `record_check` com inventário aberto; coleta → `RECONCILED` com `reconciled_at`/`reconciled_by`/`reconcile_action`; 409 para coleta não-CONFLICT ou inventário encerrado no APPLY; auditoria `INVENTARIO_OFFLINE_RECONCILED`
- [x] T033 [US3] Implementar fila e sync client em `app/web/static/js/inventario_offline.js`: estados `PENDING → SYNCING → SYNCED / FAILED → PENDING / CONFLICT` (FR-018), `client_operation_id` UUID gerado no dispositivo (FR-020), lote de pendentes (máx. 1.000), reenvio parcial (FR-022/SC-005), retry com limite (FR-023), nunca apagar coleta antes de confirmação inequívoca (FR-019), FAILED preserva payload/motivo, SYNCED retido até limpeza (FR-040); tratamento da resposta estruturada com "Sincronização concluída N/N" (FR-024/FR-041)
- [x] T034 [US3] Atualizar `docs/INVENTARIO_TECNICO.md` e o README (seção do módulo Inventário) com a sincronização (Princípio XI)

**Checkpoint**: Ciclo preparar → coletar → sincronizar funcionando e testável; conflitos preservados e reconciliáveis.

---

## Phase 6: User Story 4 - Múltiplos dispositivos no mesmo inventário (Priority: P2)

**Goal**: Mesmo inventário preparado em dispositivos distintos; coletas consolidadas com rastreabilidade de origem (device_id) e mesma regra de conflito da US3.

**Independent Test**: preparar o mesmo inventário em dois dispositivos (identificadores distintos), coletar em ambos, sincronizar e verificar consolidação com rastreabilidade de origem.

### Tests for User Story 4 ⚠️

- [x] T035 [P] [US4] Escrever testes primeiro em `tests/test_inventario_offline.py`: sync de dois `device_id` distintos sobre bens distintos consolida no mesmo inventário; rastreabilidade de origem (device_id/username em `GET .../coletas` — contrato §4); mesmo bem de dois dispositivos com resultados divergentes → conflito (C-5)

### Implementation for User Story 4

- [x] T036 [US4] Garantir rastreabilidade de origem em `app/services/inventario_offline_service.py` e na consulta de coletas: `device_id` e `username` registrados por coleta (FR-028), sem credenciais (FR-044)
- [x] T037 [US4] Adicionar seção "Conflitos offline" na tela do inventário (`app/web/templates/inventarios/detail.html` + handler em `app/web/routes.py`, leitura via service com `inventario.visualizar` — D11): coletas concorrentes lado a lado para reconciliação (P-3/FR-027) e visão das coletas por dispositivo

**Checkpoint**: US1–US4 integradas; múltiplos dispositivos consolidam com rastreabilidade e conflitos visíveis.

---

## Phase 7: User Story 5 - Controles de ciclo de vida: expiração, limpeza e evidências (Priority: P3)

**Goal**: Pacote expira ao encerramento/re-preparo (P-2); limpeza local só após sync completo confirmado, informando o que será removido; arquitetura prevê metadados de evidência sem sistema de fotos (FR-017).

**Independent Test**: com coletas sincronizadas, encerrar a coleta local e verificar a limpeza segura; preparar pacote, forçar expiração (encerrar/re-preparar) e verificar bloqueio com orientação.

### Tests for User Story 5 ⚠️

- [x] T038 [P] [US5] Escrever testes primeiro em `tests/test_inventario_offline.py`: re-preparo gera nova `snapshot_version` → coletas da base antiga rejeitadas com motivo `snapshot_mismatch` (FR-004/D9); encerramento bloqueia coleta/sync com motivo claro (C-2/P-2)

### Implementation for User Story 5

- [x] T039 [US5] Implementar bloqueio por pacote expirado no client (`app/web/static/js/inventario_offline.js`): coleta bloqueada com orientação para reconectar/re-preparar (FR-039/P-2); re-preparo substitui o pacote de forma controlada preservando coletas pendentes compatíveis e explicando incompatibilidades (edge case da spec)
- [x] T040 [US5] Implementar limpeza local segura no client (`app/web/static/js/inventario_offline.js`): "Encerrar coleta neste dispositivo" informa exatamente o que será removido, é impedida com pendências (FR-040) e, confirmada, apaga os dados temporários
- [x] T041 [US5] Documentar limitação de fotos/evidências e metadados previstos na arquitetura em `docs/INVENTARIO_TECNICO.md` e README (FR-017/Princípio XI)

**Checkpoint**: Ciclo de vida controlado; higiene e governança do pacote entregues.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Consistência, segurança, regressão e validação final (Constitution XI/XII).

- [x] T042 [P] Atualizar central de ajuda embutida (`/ajuda`) com a conferência offline (Princípio X/XI)
- [x] T043 [P] Revisar segurança conforme quickstart C5: nenhum segredo no IndexedDB/localStorage além de `sp_device_id` (FR-031), Service Worker nunca cacheia respostas sensíveis (FR-036), observações sanitizadas (FR-044)
- [x] T044 Verificar não-regressão global: suíte completa `.venv/Scripts/python -m pytest tests/ -q` verde (SC-010), fluxo online de conferência inalterado (FR-046), nenhum módulo não relacionado alterado (Princípio I)
- [x] T045 Rodar o quickstart.md completo (C1–C5; caminhos `.venv/bin` do doc em estilo Linux — no Windows usar `.venv/Scripts/python`) e registrar o resultado da validação em `specs/033-inventario-offline-pwa/` (Constitution XII)
- [x] T046 Revisão final de documentação fiel: README, `docs/INVENTARIO_TECNICO.md` e `/ajuda` compatíveis com o comportamento implementado (Princípio XI)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — inicia imediatamente
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as user stories
- **User Stories (Phases 3–7)**: dependem da Foundational
  - US1 → US2 → US3 formam o ciclo de valor P1 (pacote → coleta → sync)
  - US4 (P2) e US5 (P3) dependem do ciclo P1 completo
- **Polish (Phase 8)**: depende de todas as stories completas

### User Story Dependencies

- **US1 (P1)**: após Foundational — sem dependência de outras stories
- **US2 (P1)**: usa o pacote da US1 como base de coleta; os arquivos novos (shell, SW, manifest, ícones, qr_reader) são independentes e podem avançar em paralelo com US1
- **US3 (P1)**: usa as coletas da US2 para teste ponta a ponta — depende de US2
- **US4 (P2)**: estende US3 (device_id já existe) — depois de US3
- **US5 (P3)**: estende US3 (expiração/limpeza) — depois de US3

### Within Each User Story

- Tests before implementation (TDD — Constitution VIII)
- Service antes da rota; service antes do client JS
- Story completa antes da próxima prioridade

### Parallel Opportunities

- Tasks [P] dentro de cada fase: arquivos distintos, sem dependências (T003, T006, T007, T012, T015, T016–T020, T027, T035, T038, T042, T043)
- Diferentes stories em paralelo se houver capacidade, respeitando a cadeia pacote → coleta → sync

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tasks that are marked [P] together:
Task: "Testes US1 em tests/test_inventario_offline.py" (T007)
Task: "Botão preparar offline em app/web/templates/inventarios/detail.html" (T012)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (pacote offline)
4. **STOP and VALIDATE**: verificar o pacote no dispositivo (Independent Test da US1)
5. Deploy/demo se pronto

### Incremental Delivery

1. Setup + Foundational → fundação pronta
2. US1 → pacote no dispositivo → validar
3. US2 → coleta sem conexão → validar (C2 do quickstart)
4. US3 → sincronização → validar (C3 do quickstart)
5. US4 → múltiplos dispositivos → validar (C3.4/C3.6)
6. US5 → ciclo de vida → validar (C4 do quickstart)
7. Cada story agrega valor sem quebrar as anteriores

### Parallel Team Strategy

1. Equipe completa Setup + Foundational juntas
2. Depois da Foundational:
   - Desenvolvedor A: US1 (pacote + rota + botão)
   - Desenvolvedor B: US2 (SW/manifest/ícones/qr_reader/shell)
   - Desenvolvedor C: US3 (sync service + endpoints)
3. Stories completam e integram independentemente

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD — Constitution VIII)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
- Nenhuma permissão nova no catálogo (P-1/D11); nenhuma tabela além de `inventario_offline_coletas` (Princípio VII); nenhuma credencial em payloads, logs ou armazenamento local (FR-031/FR-044)
- Service Worker nunca cacheia `/api/*` nem páginas sensíveis (FR-036); gravação patrimonial só via services existentes (FR-026/Princípios III e V)
- Validação final (Constitution XII): suíte verde + quickstart C1–C5 + documentação fiel
- Decisão da análise de consistência (2026-09-24): "responsável encontrado" (C-3/FR-012) fica registrado somente na coleta offline (`found_custodian_id`/`client_payload` em `inventario_offline_coletas`); `InventarioService.record_check` não recebe custodiante e NÃO é alterado (Princípio I); limitação documentada para o usuário
- Análise de especificação (2026-09-24): deriva de nomenclatura aceita conscientemente — eventos novos de auditoria usam sufixos em inglês (`INVENTARIO_OFFLINE_PREPARADO/SYNC/CONFLITO/REJEITADO/RECONCILED`) enquanto eventos existentes usam português (ex.: `BACKUP_CRIADO`, `LOGIN_FALHA`); aditivo, sem conflito com o Princípio IX
- Ajuste D9 durante a implementação (2026-09-24): `snapshot_version` = SHA-256 do conjunto ordenado `(asset_id, item_id)` da base de coleta — SEM o `status` do item; conferências online e coletas aceitas alteram o status durante o inventário válido por design (C-3/C-5), e incluir o status invalidaria o pacote na própria sincronização (quebra da idempotência C-5). A versão identifica a base (quais itens eram esperados), não o estado mutável; `snapshot_mismatch` continua detectando re-preparo/encerramento pela regra de estados (C-2/P-2)
