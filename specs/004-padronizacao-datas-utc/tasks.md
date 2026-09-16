---
description: "Task list for feature 004 implementation"
---

# Tasks: Padronização de Data e Hora (UTC na persistência, America/Recife na apresentação)

**Input**: Design documents from `/specs/004-padronizacao-datas-utc/`

**Prerequisites**: `plan.md` ✅, `spec.md` ✅, `research.md` ✅, `data-model.md` ✅, `contracts/` ✅, `quickstart.md` ✅

**Tests**: INCLUÍDOS — a spec exige cobertura explícita (FR-015/FR-016) e o Constitution VIII requer testes para comportamento novo/alterado. Testes de cada story são escritos **antes** da implementação da story (TDD por story), seguindo o padrão existente da suíte (`pytest`, `TestClient` + `db_session` de `tests/conftest.py`).

**Organization**: Tasks agrupadas por user story (US1..US5 da spec) para implementação e validação independentes. Ver `plan.md` para o mapa completo de arquivos permitidos.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions.

## Path Conventions

Projeto monolítico em camadas (ver `plan.md`): `app/` (código), `tests/` (pytest), `specs/004-padronizacao-datas-utc/` (artefatos desta feature).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Mecanismo central de tempo — única infraestrutura nova da feature.

- [x] T001 Create `app/utils/__init__.py` (módulo utilitário vazio, se ainda não existir) e `app/utils/time_utils.py` com as 4 funções do contrato `contracts/time-utils-contract.md`:
  - `now_utc()` — retorna `datetime` naive representando UTC, via `datetime.now(timezone.utc).replace(tzinfo=None)`;
  - `utc_to_recife(value)` — `None`-safe; valor naive é tratado como UTC por FR-018; valor aware é respeitado; conversão via `zoneinfo.ZoneInfo("America/Recife")`; proibido offset fixo;
  - `local_to_utc(value)` — valor naive é interpretado como `America/Recife` e convertido para UTC naive; valor aware é respeitado como instante absoluto e convertido para UTC naive;
  - `format_local(value, fmt="%d/%m/%Y %H:%M")` — aplica `utc_to_recife()` + `strftime`; `None` retorna `""`.
- [x] T002 Register Jinja presentation mechanism in `app/web/routes.py`: `templates.env.filters["localtime"] = utc_to_recife` e alias em `templates.env.globals["localtime"] = utc_to_recife`, junto dos globals existentes (~linhas 120–125); importar o mecanismo de `app.utils.time_utils`. **Esta tarefa limita-se ao registro do mecanismo de apresentação; não adicionar regras de negócio ou conversão de filtros de consulta em `routes.py`.**

**Checkpoint**: mecanismo central importável e testável isoladamente; nenhum comportamento de tela alterado ainda.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: O mecanismo central (T001–T002) é a foundation compartilhada desta feature. Não há outra infraestrutura bloqueante.

**Regra transversal**: nenhum código de persistência deve continuar gerando “agora” por mecanismo próprio fora de `app.utils.time_utils`.

- [x] T003 [P] [FOUNDATION] Create `tests/test_datetime_convention.py` cobrindo isoladamente `app/utils/time_utils.py` conforme FR-015:
  - UTC → Recife com `ZoneInfo("America/Recife")`;
  - virada de dia (`2026-09-16 02:30 UTC` → `2026-09-15 23:30 Recife`);
  - preservação de segundos;
  - `None`-safe;
  - entrada aware respeitada;
  - `local_to_utc()` ida e volta;
  - `format_local()` com `None` → `""`;
  - uso de instantes fixos, sem depender de `now()` nas asserções;
  - ausência de offset fixo como `timedelta(hours=-3)`.

**Checkpoint**: T001–T003 concluídos e mecanismo central validado.

---

## Phase 3: User Story 1 — Visualização de horários corretos nas telas (Priority: P1) 🎯 MVP

**Goal**: Todas as telas listadas em FR-006 exibem timestamps armazenados em UTC convertidos para `America/Recife`, sem lógica de fuso duplicada por tela (SC-001).

**Independent Test**: Registrar uma ação em horário local conhecido e verificar que a tela correspondente exibe o mesmo horário local.

### Tests for User Story 1

- [x] T004 [US1] Add presentation-flow tests to `tests/test_datetime_flows.py`: com `TestClient` + usuários/objetos padrão da suíte, gravar `checked_at` de item e `timestamp` de `audit_logs` com instantes fixos em UTC (ex.: `datetime(2026, 9, 15, 22, 30)` ≡ 19:30 Recife) e assegurar que `/inventarios/{id}`, `/inventarios` e `/admin/audit` exibem **19:30** e não exibem **22:30** para esses timestamps.

### Implementation for User Story 1

- [x] T005 [P] [US1] Apply `| localtime` to audit trail display in `app/web/templates/admin/audit/list.html:85`, preservando segundos (`%d/%m/%Y %H:%M:%S`) e os guards existentes.
- [x] T006 [P] [US1] Apply `| localtime` to inventory templates:
  - `app/web/templates/inventarios/detail.html` nos pontos de `closed_at`, `checked_at`, `created_at` e `started_at`;
  - `app/web/templates/inventarios/list.html:72` (`inv.created_at`);
  - `app/web/templates/inventarios/conferir.html:65` (`item.checked_at`);
    manter todos os guards condicionais existentes.
- [x] T007 [P] [US1] Apply `| localtime` to user admin templates:
  - `app/web/templates/admin/users/list.html:101` (`u.last_login`, preservando “Nunca”);
  - `app/web/templates/admin/users/edit.html` nos pontos de `last_login`, `ad_last_sync` e `locked_until`.
- [x] T008 [US1] **First verify semantic classification** of `Maintenance.start_date` and `end_date` in `app/models/maintenance.py`, `app/services/maintenance_service.py` and usages relevantes. If they represent system timestamps, apply `| localtime` to `app/web/templates/maintenances/list.html:39`; if they represent pure business dates, preserve them without conversion. **If semantic classification remains ambiguous, stop this task and register the divergence instead of assuming.**
- [x] T009 [P] [US1] Apply `| localtime` to movement timestamp displays that will become UTC under US2:
  - `app/web/templates/movements/list.html:69`;
  - `app/web/templates/dashboard.html:258`;
  - `app/web/templates/reports/movements_report.html:48`;
  - `app/web/templates/assets/detail.html` nos pontos de `item.timestamp`.
    Não aplicar conversão a campos que sejam datas de negócio.
- [x] T010 [US1] Run User Story 1 validation: `pytest tests/test_datetime_convention.py tests/test_datetime_flows.py`; confirmar que os pontos de origem UTC definidos em FR-006 usam o mecanismo `localtime`; nenhum template deve conter aritmética manual de horas ou offset fixo.

**Checkpoint**: US1 funcional e testável independentemente — telas exibem horário de Recife sobre dados UTC.

---

## Phase 4: User Story 2 — Persistência padronizada em UTC (Priority: P2)

**Goal**: Todos os timestamps gerados pelo sistema gravam UTC; divergência intra-linha de `movements` eliminada (SC-002/SC-003).

**Independent Test**: Executar movimentação em horário local conhecido e verificar que o instante gravado corresponde ao UTC daquele momento.

### Tests for User Story 2

- [x] T011 [US2] Add UTC persistence tests to `tests/test_datetime_flows.py`: criar movimentação via `MovementService.create_movement` e via importação CSV; assegurar que `Movement.timestamp` e `asset.updated_at` correspondem ao UTC do instante de geração, com tolerância de segundos; verificar consistência entre `Movement.timestamp` e `Movement.created_at`.

### Implementation for User Story 2

- [x] T012 [US2] **Surgical model standardization**: nos modelos de `app/models/` identificados pelo `data-model.md` como utilizando `datetime.utcnow` em `default` ou `onupdate`, substituir **somente** esses geradores pelo `now_utc()` de `app.utils.time_utils`.
  - Não alterar colunas;
  - não alterar tipos;
  - não alterar schema;
  - não alterar relacionamentos;
  - não alterar regras de negócio;
  - não criar migration/DDL.
  - Modelos-alvo somente quando contiverem esses defaults/onupdate: `audit_log.py`, `movement.py`, `asset.py`, `inventario.py`, `maintenance.py`, `session.py`, `user.py`, `role.py`, `permission.py`, `ad_settings.py`, `ad_group_role.py`, `setup_claim.py`, `location.py`, `custodian.py`.
  - Não alterar usos de `datetime.utcnow` que pertençam explicitamente a lógica fora do escopo sem antes verificar a classificação.
- [x] T013 [P] [US2] Replace local clock with `now_utc()` in `app/services/movement_service.py`: linha correspondente a `asset.updated_at = datetime.now()` e linha correspondente a `timestamp=datetime.now()`. Manter o cálculo de `TR-{datetime.now().year}` **intocado**, pois o ano do código de movimentação está fora do escopo.
- [x] T014 [P] [US2] Replace local clock with `now_utc()` in `app/services/asset_service.py` somente nos timestamps de movimentação (`timestamp=datetime.now()`). Manter `purchase_date`, ano do `TR-INIC` e lógica de depreciação **intocados**.
- [x] T015 [P] [US2] Replace local clock with `now_utc()` in `app/services/import_service.py` somente no timestamp da movimentação de entrada. Manter `_parse_date`, `purchase_date` e ano do `TR-CSV` **intocados**.
- [x] T016 [US2] Run User Story 2 validation:
  - `pytest tests/test_datetime_flows.py`;
  - varredura de `datetime.now()` / `datetime.utcnow()` em `app/`;
  - confirmar que chamadas restantes são somente pontos classificados explicitamente como fora do escopo ou que não representam geração de timestamps persistidos;
  - nenhum timestamp persistido novo deve usar relógio local diretamente fora de `time_utils.py`.

**Checkpoint**: US2 funcional — novos timestamps persistidos usam UTC e `movements` deixa de possuir geração local para `timestamp`/`updated_at`.

---

## Phase 5: User Story 3 — Datas de negócio preservadas (Priority: P2)

**Goal**: `purchase_date`, `warranty_expiry` e datas de CSV/formulários permanecem exatamente como informadas, sem conversão de fuso (SC-004).

**Independent Test**: Cadastrar/importar bem com data de compra `15/09/2026` e verificar que permanece `15/09/2026`.

### Tests for User Story 3

- [x] T017 [US3] Add business-date preservation tests to `tests/test_datetime_flows.py`:
  - importar CSV com `purchase_date = 15/09/2026`;
  - assegurar `Asset.purchase_date == date(2026, 9, 15)`;
  - assegurar exibição `15/09/2026`;
  - cadastrar bem via formulário com compra `15/09/2026` e garantia `15/09/2028`;
  - assegurar que os filtros de `purchase_date` continuam funcionando;
  - estes testes devem passar antes e depois da implementação da feature.

### Implementation for User Story 3

- [x] T018 [US3] Verify no-conversion guarantee by inspection: confirmar que a implementação não aplica `utc_to_recife()`/`localtime` a `purchase_date`, `warranty_expiry`, `_parse_date`, datas puras de CSV/formulários ou filtros de data de compra. **Não editar esses pontos salvo se uma divergência diretamente ligada à feature for encontrada.**
- [x] T019 [US3] Run User Story 3 validation: `pytest tests/test_datetime_flows.py`; confirmar SC-004 e ausência de deslocamento em datas de negócio.

**Checkpoint**: US3 validada — semântica de datas de negócio intacta.

---

## Phase 6: User Story 4 — Relatórios e documentos com horário correto (Priority: P3)

**Goal**: Exports (PDF/Excel/CSV/HTML) exibem timestamps persistidos convertidos para `America/Recife`; o carimbo **“Gerado em”** é tratado separadamente como horário do momento da geração.

**Independent Test**: Gerar documento com timestamps conhecidos em UTC e verificar apresentação em Recife.

### Tests for User Story 4

- [x] T020 [US4] Add export presentation tests to `tests/test_datetime_flows.py`: com timestamps fixos UTC (ex.: `2026-09-15 22:30` ≡ 19:30 Recife), assegurar que CSV/PDF/Excel/estruturas intermediárias de inventário e CSV de movimentações exibem `19:30` para timestamps dos dados e não `22:30`. Para `"Gerado em"`, verificar somente que o valor corresponde ao horário local do momento da geração, dentro da tolerância definida, sem aplicar conversão dupla.

### Implementation for User Story 4

- [x] T021 [US4] Convert inventory export timestamps in `app/services/report_service.py` via `format_local()`:
  - bloco `_inventario_rows`;
  - `generate_inventario_csv`;
  - ata PDF;
  - ata Excel.
    Manter formatos atuais, fallbacks `-` e condicionais.
- [x] T022 [US4] Convert movements export timestamp in `app/services/report_service.py`: campo `m.timestamp.strftime("%d/%m/%Y %H:%M:%S")` → `format_local(m.timestamp, "%d/%m/%Y %H:%M:%S")`.
- [x] T023 [US4] **First verify semantic classification of `term.date`**. Confirm in `app/services/movement_service.py` and related models/routes that the field returned by `get_term_details()` represents `Movement.timestamp`. If confirmed, replace its formatting with `format_local(movement.timestamp, "%d/%m/%Y às %H:%M")`. If it represents a business date instead, preserve it without timezone conversion. If ambiguous, stop and register the divergence.
- [x] T024 [US4] Run User Story 4 validation: `pytest tests/test_datetime_flows.py`; gerar manualmente CSV/PDF/Excel de inventário e documento de termo conforme `quickstart.md`; verificar timestamps dos dados em Recife e `"Gerado em"` sem dupla conversão.

**Checkpoint**: US4 funcional — documentos comprobatórios apresentam timestamps no horário de Recife.

---

## Phase 7: User Story 5 — Filtros por período confiáveis (Priority: P3)

**Goal**: Intervalos informados em horário local são convertidos para UTC antes de comparar com `Movement.timestamp` (SC-005); filtros de data de negócio permanecem intactos.

**Independent Test**: Consultar intervalo local conhecido e verificar inclusão/exclusão correta de movimentações próximas à meia-noite.

### Tests for User Story 5

- [x] T025 [US5] Add period filter tests to `tests/test_datetime_flows.py`:
  - registro `2026-09-15 22:00 UTC` ≡ 19:00 Recife deve ser retornado pelo intervalo local de 15/09;
  - registro 23:50 Recife (`02:50 UTC` de 16/09) deve ser retornado pelo filtro do dia 15/09;
  - o mesmo registro não deve aparecer no filtro de 14/09;
  - intervalo com offset explícito deve ser respeitado como instante absoluto;
  - filtros de `purchase_date` permanecem inalterados.

### Implementation for User Story 5

- [x] T026 [US5] Apply `local_to_utc()` to period filters in `app/services/movement_service.py`, no ponto imediatamente anterior à comparação com `Movement.timestamp`. Converter `filters.start_date` e `filters.end_date` conforme o contrato:
  - valor naive recebido pelo filtro = horário `America/Recife`;
  - valor aware = instante absoluto;
  - comparação no banco = UTC naive.
    Manter `MovementFilter` e a rota sem alterações, salvo necessidade diretamente comprovada.
- [x] T027 [US5] Run User Story 5 validation: `pytest tests/test_datetime_flows.py`; executar cenário manual do `quickstart.md` com intervalo local e offset explícito.

**Checkpoint**: US5 funcional — filtros de período trabalham com a mesma convenção UTC da persistência.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Conformidade, não-regressão e documentação (Constitution VIII, XI, XII).

- [x] T028 [P] Update surgical assertions in `tests/test_inventario_reconferencia_ui.py`: pontos que atualmente comparam `item.checked_at.strftime(...)` com o HTML devem comparar o valor convertido por `utc_to_recife(item.checked_at).strftime(...)`, mantendo a força da asserção. **Nenhum outro teste existente deve ser alterado.**
- [x] T029 Run full regression suite: `pytest` completo. Investigar qualquer falha como possível regressão da convenção; ajustar somente quando diretamente dependente desta feature e registrar cada ajuste.
- [x] T030 [P] Update documentation for the new convention in `README.md` ou `docs/ARQUITETURA_E_MANUTENCAO.md`:
  - timestamps de sistema são gerados/persistidos em UTC naive via `app.utils.time_utils`;
  - `localtime`/`format_local` convertem para `America/Recife` na apresentação;
  - valores naive provenientes de `DATETIME` são tratados como UTC pelo contrato da aplicação;
  - datas de negócio não são convertidas;
  - não documentar comportamento que não esteja efetivamente implementado.
- [x] T031 Run compliance sweeps (SC-008/SC-009):
  - `grep -rn "timedelta(hours=3)\|hours=-3" app/` deve retornar vazio;
  - `grep -rn "datetime.now()\|datetime.utcnow()" app/ --include="*.py"` deve mostrar somente ocorrências classificadas e justificadas fora do mecanismo central, sem geração indevida de timestamps persistidos;
  - confirmar que nenhum código de persistência usa `func.now()` ou `CURRENT_TIMESTAMP` como mecanismo alternativo;
  - confirmar que não houve alteração de schema, DDL ou migration;
  - confirmar que `app/config.py` permanece intocado, salvo necessidade absolutamente indispensável e diretamente comprovada;
  - executar protocolo completo de `specs/004-padronizacao-datas-utc/quickstart.md` (seções 2–6) e registrar resultado.

**Checkpoint final**: suite completa, conformidade e quickstart validados.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: inicia imediatamente.
- **Foundational (Phase 2)**: depende de T001–T002; T003 valida o mecanismo.
- **US1 (Phase 3)**: depende de T001–T003; opera sobre dados já armazenados em UTC.
- **US2 (Phase 4)**: depende de T001–T003; pode ser implementada independentemente da US1.
- **US3 (Phase 5)**: depende de T001–T003; é uma guarda de não-regressão.
- **US4 (Phase 6)**: depende de T001–T003 e, para validação integrada, dos resultados de US2.
- **US5 (Phase 7)**: depende da conclusão da US2, porque os filtros precisam comparar contra `Movement.timestamp` padronizado em UTC.
- **Polish (Phase 8)**: depende das stories aplicáveis estarem concluídas.

### User Story Dependencies

- **US1**: Foundation → T004–T010.
- **US2**: Foundation → T011–T016.
- **US3**: Foundation → T017–T019.
- **US4**: Foundation + persistência UTC → T020–T024.
- **US5**: Foundation + US2 → T025–T027.

### Within Each User Story

1. Testes devem ser escritos antes da implementação.
2. Verificações semânticas devem ocorrer antes de qualquer alteração quando a classificação do campo for relevante.
3. Serviços/mecanismos devem ser ajustados antes das integrações dependentes.
4. Tarefa de validação encerra cada story no checkpoint.
5. Se uma dúvida de classificação não puder ser resolvida pelo código/documentação existente, **parar e registrar a divergência**, sem assumir.

### Parallel Opportunities

- T001 → T002 são sequenciais.
- T004 pode ser preparado independentemente de T005–T009.
- T005–T007 e T009 atuam em arquivos de template diferentes e podem ser paralelos.
- T008 deve permanecer separado porque depende da verificação semântica de Maintenance.
- T011 e T017 alteram o mesmo `tests/test_datetime_flows.py`: **não executar em paralelo**.
- T013–T015 atuam em services distintos e podem ser paralelos após T011, desde que não haja conflito de importações.
- T021 e T022 alteram o mesmo `report_service.py`: **executar serialmente**.
- T023 altera `movement_service.py`, portanto deve ser coordenada com T013/T026.
- T028 e T030 atuam em arquivos distintos e podem ser paralelos.
- T029/T031 devem ocorrer após todas as alterações.

---

## Implementation Strategy

### MVP First — User Story 1

1. Complete T001–T003.
2. Complete T004–T010.
3. **STOP and VALIDATE**: telas exibem horário de Recife sobre timestamps UTC existentes.
4. Confirmar que nenhuma gravação foi alterada indevidamente.
5. Só então avançar para US2.

### Incremental Delivery

1. Setup + US1 → correção da apresentação.
2. US2 → padronização da gravação.
3. US3 → proteção de datas de negócio.
4. US4 → documentos e relatórios.
5. US5 → filtros.
6. Polish → regressão, documentação e conformidade.

### Parallel Team Strategy

Para implementação por agentes/IA:

1. Todos começam por T001–T003.
2. Após Foundation:
   - Agente A → US1;
   - Agente B → US2;
   - Agente C → US3.
3. **Não paralelizar tarefas que editam o mesmo arquivo.**
4. Após US2:
   - US5 pode ser executada;
   - US4 pode ser executada com coordenação nos arquivos compartilhados.
5. Todos → Polish.

Para uma única sessão de Copilot/IA, preferir execução **sequencial por story**, validando cada checkpoint antes de avançar.

---

## Notes

- `[P]` significa somente que as tarefas podem ser executadas em paralelo sem editar o mesmo arquivo e sem dependência.
- `[Story]` identifica a user story para rastreabilidade.
- Cada user story possui teste e checkpoint.
- Testes devem ser escritos antes da implementação correspondente.
- Commit após cada tarefa ou grupo lógico validado.
- Parar em qualquer checkpoint se houver regressão.
- **Proibições transversais**:
  - zero DDL/migration;
  - zero offset fixo;
  - zero dupla conversão;
  - zero alteração de schema;
  - zero alteração de auth/sessões/AD/RBAC;
  - datas de negócio intocadas;
  - códigos `INV-/TR-` fora do escopo;
  - depreciação fora do escopo;
  - parser CSV fora do escopo;
  - browser JavaScript não deve fazer conversão de timezone;
  - `app/config.py` não deve ser alterado salvo necessidade absolutamente indispensável.
- Alterações em `app/models/` são permitidas **somente** para substituir geradores `datetime.utcnow` por `now_utc()` em defaults/onupdate identificados, sem qualquer mudança de schema ou comportamento de negócio.
- **Dúvida de classificação**: interromper a tarefa e registrar a dúvida; não assumir.
- `Maintenance.start_date/end_date` e `term.date` devem ter sua semântica confirmada antes de qualquer conversão.
- `purchase_date`, `warranty_expiry` e datas puras de CSV/formulários não recebem conversão UTC/Recife.
- Evitar tarefas vagas, conflitos no mesmo arquivo e paralelização artificial.
- Não usar migração para converter dados históricos; os dados de movimentação atualmente existentes são dados de teste e serão descartados antes da utilização final do sistema.
