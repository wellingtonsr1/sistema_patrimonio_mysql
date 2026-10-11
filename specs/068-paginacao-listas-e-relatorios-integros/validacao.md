# Validação — 068-paginacao-listas-e-relatorios-integros

**Execução**: 2026-10-11 | **Estado**: **Phases 1, 2 e 3 (US1) concluídas** — Phase 1: T001–T003. Phase 2: T004/T005 (helper + macro). Phase 3: T006–T013 (US1: `/assets`, `/movements`, `/custodians`, `/locations` paginadas). Suíte atual: **1023 passed / 1 failed (RED esperado, AC15 de US2/US3) / 2 skipped**.

---

## 1. T001 — Baseline (antes de qualquer mudança)

```bash
.venv/bin/python -m pytest -q
```

Resultado registrado: **1005 passed, 2 skipped, 3 warnings em 81,24 s (0:01:21)** — `exit=0`. (Avisas: `starlette.testclient` `BlockingPortal` deprecated; `ldap3` `typeMap`/`tagMap` deprecated.)

- Patamar igual ao medido em 2026-10-10 (1005/2) → **sem regressão pendente**.
- **Nenhum teste editado, removido ou pulado.** Este número é o comparador da validação final (T031).

## 2. T002 — Conferência somente-leitura dos fatos da spec §1

Todos os seis fatos **confirmados** (nenhuma divergência → não houve parada):

| # | Fato da spec §1 | Situação / evidência |
|---|---|---|
| a | Nenhum template com `pagination`/`page-item` | **confirmado** — `grep -rl "pagination\|page-item" app/web/templates` → **0 arquivos** |
| b | `report_service.py:47` aplica `limit 10000` | **confirmado** — linha 47: `limit_query = limit if limit > 0 else 10000` |
| c | `view_inventory_report` usa `limit=1000` e o template não exibe `total` | **confirmado** — `app/web/routers/reports.py:57` (`limit=1000`); `reports/inventory.html` → **0** ocorrências de `total` |
| d | `get_audit_logs` já aceita `user_id`/`start_date`/`end_date` | **confirmado** — `app/services/audit_service.py:323-334` (assinatura completa) |
| e | `CustodianService.get_all`/`LocationService.get_all` não têm `limit` | **confirmado** — `custodian_service.py:135` e `location_service.py:20` (sem parâmetro de limite) |
| f | `tests/route_manifest.json` tem 142 rotas | **confirmado** — `grep -c '"path"'` → **142** |

## 3. T003 — Decisões P1–P5 registradas

| Decisão | Registro | Status |
|---|---|---|
| P1 aviso + exportação completa | `spec.md` Clarifications (2026-10-10) + §14 | ✅ aprovada 2026-10-10 |
| P2 todas as listas do escopo | idem | ✅ aprovada 2026-10-10 |
| P3 `page_size` 200 fixo | idem | ✅ aprovada 2026-10-10 |
| P4 relatório web paginado | `spec.md` Clarifications (2026-10-11) + §14 | ✅ aprovada 2026-10-11 |
| P5 eliminar N+1 das listas | idem | ✅ aprovada 2026-10-11 |

`grep` de pendências no diretório (`PROPOSTA`/`aguardando aprovação`) → **nenhuma**. **T018 e T027 liberadas.**

## 4. Achado adicional (fora da spec §1.1) — decisão de escopo pendente

Durante a T002 foi observado algo **além dos seis fatos listados** (não é divergência deles, e por isso não houve parada, mas muda o escopo se for incluído):

| Rota | Evidência | Comportamento |
|---|---|---|
| `/reports/movements` | `app/web/routers/reports.py:86` → `MovementService.get_all_movements(db, limit=1000)` | **corta em 1.000**; o template mostra `{{ total }} registros` (`movements_report.html:61`) **sem avisar** que só 1.000 estão na tela |
| `/reports/custodians` | `app/web/routers/reports.py:101` → `CustodianService.get_all(db)` + `count_assigned_assets` por linha | **sem corte** (`total = len(...)`, coerente), porém **N+1** e carga não paginada |

**Impacto**: a spec 068 (RF04/**FR-008**/SC-006/AC05/T018) cita apenas `/reports/inventory`. Cobrir `/reports/movements` seria escopo novo (pequeno: mesma paginação/indicador); `/reports/custodians` cairia no N+1 (já tratado pelo P5 **apenas nas listas paginadas** — esta tela não está nelas).

**Status**: **decidido em 2026-10-11 (decisão P6)** — responsável aprovou **incluir `/reports/movements`**; a spec foi amendada (Clarifications, §1.1, §1.2, RF04/FR-008, SC-006, AC05, §11, §12, §14) e as tarefas **T014/T018** agora cobrem as duas telas. **`/reports/custodians` fica fora do escopo** e foi registrado como dívida **M-004** em `docs/Melhorias_SisPatrimonio_Pro.md`.

## 5. Estado das fases

| Fase | Tarefas | Estado |
|---|---|---|
| 1 — Setup | T001, T002, T003 | ✅ **concluída** (este documento) |
| 2 — Foundational | T004 (`app/utils/pagination.py`), T005 (macro `pagination.html`) | ✅ **concluída** (ver §6) |
| 3 — US1 (navegar nas listas) | T006–T013 | ✅ **concluída** (ver §7) |
| 4–6 — US2/US3/Polish | T014–T032 | ⏳ não iniciadas |

## 7. Phase 3 — User Story 1 (T006–T013)

| Tarefa | Entregue |
|---|---|
| T006/T007 (RED) | `tests/test_paginacao_relatorios_068.py` — 8 testes: AC01/AC02 (200+total, página 2), AC03/FR-002 (page inválida), AC04 (lista pequena sem pager), AC10/SC-012 (403 + trilha DENIED), FR-007 (filtros preservados), AC15 (pager nas 7 listas + relatório), AC11 (API intacta) |
| T008/T009 | `assets.py::list_assets` lê `page`, passa `skip=offset_for(page)`/`limit=200` e expõe `meta`; `assets/list.html` com indicador `Mostrando X–Y de Z` + `{% import %}` da macro `pager` |
| T010 | `movements.py::list_movements_view` + `movements/list.html` — idem; **o `total` que a rota já recebia agora é exibido** (antes: só o tamanho da página) |
| T011 | `custodian_service.py::get_all` ganha `skip=0, limit=0` **aditivos** (`0` = sem teto → API/chamadores intactos, FR-017/I5) + novo `CustodianService.count`; rota + template paginados com novo indicador |
| T012 | Idem para `location_service.py` (`get_all` aditivo + `count`), rota e template |
| T013 | Regressão `test_assets.py`, `test_movements_search.py`, `test_api.py`, `test_rbac.py`, `test_route_inventory.py` (manifesto sem mudança — AC12/FR-003) e `test_central_integracoes.py` → **103 passed**; nenhum teste existente editado |

**Suíte completa**: **1023 passed, 1 failed, 2 skipped** — a única falha é
`test_pager_renderiza_nas_sete_listas` (RED esperado de TDD: cobre `/inventarios`,
itens de conferência e `/admin/audit` — escopo da **US3** — e `/reports/inventory`
— escopo da **US2**). Fica GREEN à medida que as fases 4 e 5 forem entregues.

**Achados durante a T006–T007 (corrigidos no teste, não no código)**: (a) a ordenação
de `assets`/`movements`/`inventários`/`audit` é **desc** — a página 2 mostra os registros
mais antigos; o teste foi ajustado para os marcadores corretos (a implementação está
certa); (b) o nome do membro do enum é `MovementType.ALLOCATION` (o valor gravado é
`ALOCACAO_CAUTELA`) — o seed do teste usava o valor como nome.

**Nenhum teste existente alterado** (Constitution VIII); **nenhuma rota nova**
(`tests/route_manifest.json` válido — AC12/FR-003); **API REST intacta** (AC11).

## 6. Phase 2 — Foundational (T004/T005)

| Tarefa | Entregue | Validação |
|---|---|---|
| T004 | `app/utils/pagination.py`: `parse_page`, `offset_for`, `page_meta` (vocabulário de `get_history` + `start`/`end`/`has_prev`/`has_next`; `DEFAULT_PAGE_SIZE=200`) | `tests/test_pagination_util_068.py` — **8 testes** (normalização `abc`/`0`/`-1`/`>pages`, estado vazio, `page_size` inválido) |
| T005 | `app/web/templates/macros/pagination.html`: macro `pager(...)` com `data-testid="pager"`, oculta quando `pages <= 1` (FR-006), filtros preservados (FR-007) e markup responsivo (FR-022) | **3 testes** de renderização isolada (macro passada por argumento — Jinja não herda contexto) |

**Suíte completa após a Phase 2**: **1016 passed, 2 skipped** em 81,68 s — `exit=0`
(baseline 1005 + 11 novos; **nenhuma regressão**, nenhum teste existente editado).

**Nenhum comportamento de produção alterado** — helper e macro são **aditivos** e ainda não são
referenciados por rota/template (consumo começa na T008/T009); `tests/route_manifest.json` intacto.

**Achado e correção durante a T005**: `request.query_params.mutablecopy()` não existe na versão
instalada do Starlette (macro quebraria em runtime) → a montagem usa `dict(...)` + filtro
`urlencode`, com teste cobrindo o link gerado. Documentado aqui para o revisor (Constitution XII).

**Nenhum commit criado** (padrão da casa: apenas sob pedido explícito).

---

## 8. Phase 6 — Polish & Cross-Cutting Concerns (T027–T032)

**Estado geral**: **parcialmente entregue — só o artigo da central de ajuda está pronto**.
O `validacao.md` anterior não registrava esta fase; o que segue é o registro feito agora.

| Tarefa | O que a tarefa pede | Estado real (inspeção) | Registro |
|---|---|---|---|
| T027 | Eliminar N+1 das listas paginadas por agregação única (`GROUP BY`) + teste `test_listas_sem_n1_de_contagem` (AC13/SC-010/FR-020) | **Não entregue** — não existe teste `test_listas_sem_n1_de_contagem` rodando nem registro de redução de queries por linha; P5 está liberada, mas a tarefa não está implementada aqui | ❌ pendente |
| T028 | Documentação: `docs/ARQUITETURA_E_MANUTENCAO.md` (listagens paginadas + integridade de exportações) + artigo da central de ajuda (`app/services/help_service.py`, FR-021) | **Entregue (completado)** — `docs/ARQUITETURA_E_MANUTENCAO.md` §12.8 registra listagens paginadas + integridade de exportações (FR-001/FR-004/FR-007/FR-008/FR-009/FR-010/FR-011/FR-012/FR-013) + artigo `paginação-e-relatórios` integrado em `app/services/help_service.py` | ✅ entregue (ver §12.8 de `ARQUITETURA_E_MANUTENCAO.md`) |
| T029 | Medição de desempenho (AC13/SC-010/SC-011) com o harness da análise 2026-10-10 (SQLite in-memory + TestClient, 2.000 bens); registrar antes/depois em `validacao.md` e remover o harness | **Não entregue** — não há medição registrada em `validacao.md`, nem harness removido, nem antes/depois com o critério SC-011 | ❌ pendente |
| T030 | Verificar `git diff`: `tests/route_manifest.json`, `requirements.txt`, `app/models/`, `migrations/` sem alteração (FR-016/FR-018); executar `tests/test_route_inventory.py` e registrar que nenhuma rota nova foi criada (AC12); nenhum teste existente modificado (AC14) | **Não devidamente registrado** — até aqui não há registro formal em `validacao.md` dessa verificação; a ausência de diff funcional observada informalmente não substitui o registro exigido pela tarefa | ❌ pendente de registro/verificação formal |
| T031 | Régua completa `.venv/bin/python -m pytest -q` + validação manual do `quickstart.md` §2 (incl. 360 px) + registro final em `validacao.md` | **Não entregue como registro final** — a régua completa não foi executada neste ciclo (timeout) e não há registro final em `validacao.md` com o resultado e a validação manual do quickstart | ❌ pendente |
| T032 | Confirmar em `spec.md` §14 e `checklists/requirements.md` que **P1–P5** constam aprovadas (2026-10-10 / 2026-10-11); commit apenas sob pedido explícito | **Registrado no specification package, mas não fechado como tarefa de validação** — `spec.md` §14 e `checklists/requirements.md` já trazem P1–P5 aprovadas; a tarefa T032 é de confirmação/fechamento e ainda não foi executada como tal | ⏳ confirmação/fechamento pendente |

**Evidência usada nesta validação**:
- Artigo da central de ajuda: `app/services/help_article_068.py` e import em `app/services/help_service.py`.
- Documentação de arquitetura: `docs/ARQUITETURA_E_MANUTENCAO.md` §12.8 (nova).
- Dívida correlata: `docs/Melhorias_SisPatrimonio_Pro.md` (M-004) e referências cruzadas em `research.md`/`spec.md` §14.
- `checklists/requirements.md`: confirma P1–P5 aprovadas, mas não substitui a execução das tarefas T027/T029/T030/T031/T032.

**Próximo passo**: completar T027/T029/T030/T031 antes de marcar o Phase 6 como concluído.
