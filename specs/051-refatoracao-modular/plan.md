# Implementation Plan: Refatoração Modular — Rotas Web e Backup Service (051)

**Branch**: `051-refatoracao-modular` · **Spec**: [spec.md](spec.md) · **Created**: 2026-09-28

## Summary

Decompor `routes.py` (2.668 linhas → facade ≤ 200) em `app/web/routers/` por domínio e `backup_service.py` (1.381 linhas → facade) em pacote `app/services/backup/`, **movendo código literalmente** (sem reescrever), preservando a API pública via re-exports e provando não-regressão com snapshot de inventário de rotas + suíte completa verde.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI + SQLAlchemy 2 / Jinja2 / pytest
**Storage**: sem mudança de schema; testes com `DATABASE_URL_TEST="sqlite:///:memory:"`
**Testing**: pytest (baseline atual: 842+ passed / 2 failed pré-existentes de `test_backup_externo.py` — fora de escopo, documentados)

## Estratégia central

1. **Movimentação literal**: blocos de código são movidos byte a byte; diff revisável por "arquivo novo contém exatamente o que o antigo tinha".
2. **Compatibilidade por facade**: `routes.py` e `backup_service.py` viram re-exportadores; consumidores (`main.py`, `admin_routes.py`, `help_routes.py`, `backup_scheduler.py`, testes) **não são editados** (SC-004).
3. **Prova de não-regressão**: novo teste `test_route_inventory.py` captura `(path, methods, name, dependencies)` de todos os routes do app contra manifesto JSON versionado.
4. **Uma fase = um domínio**: cada fase termina com suíte verde; proibido acumular 2+ domínios quebrados simultaneamente.

## Sequência de decomposição (routes.py)

Ordem escolhida por dependência e risco (helpers primeiro, seção maior por último), preservando a ordem de registro:

| Fase | Domínio extraído | Destino | Linhas movidas (≈) |
|---|---|---|---|
| F1 | Infra compartilhada | `routers/shared.py` (helpers 048) + facade | 1–214 |
| F2 | Autenticação + Setup | `routers/auth.py`, `routers/setup.py` | 215–354, 1979–2167 |
| F3 | Dashboard + Relatórios | `routers/dashboard.py`, `routers/reports.py` | 356–367, 1884–1977 |
| F4 | Movimentações | `routers/movements.py` | 923–1071 |
| F5 | Colaboradores | `routers/custodians.py` | 1073–1422 |
| F6 | Locais | `routers/locations.py` | 1424–1778 |
| F7 | Manutenções | `routers/maintenances.py` | 1780–1882 |
| F8 | Inventário | `routers/inventario.py` | 2169–2668 |
| F9 | Bens (maior, por último) | `routers/assets.py` | 369–921 |

Cada fase F2–F9: mover seção literal → criar arquivo com imports necessários → registrar sub-router no facade na posição original → rodar suíte.

## Decomposição de backup_service.py (fase única B1)

> **⚠️ REVISADO PELO IMPLEMENT (2026-09-28) — Amendment A1 da spec: decomposição física REJEITADA com evidência.**
>
> Evidência coletada antes de mover uma linha: a suíte de testes usa o namespace do módulo como API de injeção —
> **42 pontos** de `monkeypatch.setattr(backup_service, ...)` / leitura direta cobrindo `SessionLocal`,
> `DATABASE_URL`, `BACKUP_DIR`, `MYSQLDUMP_PATH`, `BACKUP_IMPORT_TIMEOUT`, `drain_engine`, `maintenance_mode`,
> `_RESTORE_IN_PROGRESS`, `_run_mysqldump`, `_run_mysql_import`, `write_audit`, `subprocess`, `shutil`,
> `_BACKUP_NAME_RE`, `_RESTORE_LOCK`, `_maintenance_set`, `_import_with_deadline`, `_sanitize_stderr`.
> Em Python, o corpo de uma função resolve globais no módulo ONDE FOI DEFINIDA: movendo `generate_backup`
> para `service.py`, um patch em `backup_service._run_mysqldump` (feito pelo teste no facade) deixaria de
> ser visto — os ~40 testes de injeção quebrariam (viola NR-002) ou cada referência interna teria de ser
> reescrita para ler do facade (viola a movimentação literal/FR-009 e introduz exatamente o risco que a
> fase B1 queria evitar). O `global _RESTORE_IN_PROGRESS` do ciclo 019 agrava: a sincronização entre
> `restore_backup` e `_execute_restore_cycle` depende de viverem no MESMO namespace.
>
> **Decisão (Constituição I — evidência vence o plano): manter `backup_service.py` como módulo único.**
> Reorganização interna por seções com mapa de navegação no docstring (zero mudança de namespace, zero
> mudança de comportamento). A decomposição física em pacote fica registrada como candidata a spec futura,
> condicionada a: (a) os testes migrarem da injeção por namespace para fixtures de serviço, ou
> (b) emenda da spec aceitando a reescrita das referências internas.

```
app/services/backup_service.py  # MÓDULO ÚNICO (A1) — seções na ordem atual:
# [1] Dump       — _dump_env, _resolve_tool_executable, _resolve_import_executable, _run_mysqldump
# [2] Restore    — BackupError, restore_in_progress, restore_status, _restore_slot,
#                  _run_mysql_import, _import_with_deadline, _iter_dump_chunks, _maintenance_set
# [3] Service    — class BackupService (generate/list/validate/restore)
# [4] Records    — _write_backup_record, _record_backup_success/failure, _worker_audit,
#                  _capture_backup_snapshot, _reconcile_backup_records, _execute_restore_cycle
# [5] Paths      — get_backup_path + vínculo estático na classe
```

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Imports circulares entre routers (ex.: shared ↔ domain) | **Verificado no implement**: resolvido com `routers/templates_env.py` (config Jinja2 sem dependência de domínios); routers importam `templates` de lá, nunca do facade |
| Ordem de rotas alterada muda matching (ex.: rota genérica captura antes de específica) | FR-005: ordem de inclusão = ordem atual das seções; teste de inventário valida paths + methods — **140/140 idênticos** |
| Estado de módulo (ex.: `maintenance_mode` dict global em backup_service) quebra ao duplicar | **Maturado em Amendment A1**: o estado de módulo é também a API de injeção dos testes (42 pontos) — decomposição física rejeitada; módulo único preserva namespace |
| Testes importam privates (`_claim_first_access`, `routes.<algo>`) | Facade re-exporta; **verificado no implement**: `_claim_first_access`, `_safe_next_url`, snapshots de auditoria e helpers 048 re-exportados |
| Teste de inspeção de fonte da 050 (`inspect.getsource(routes)`) quebrar com rotas movidas | Assertion ajustada para somar o fonte do módulo do domínio (`routers/locations.py`) — apenas import/teste, NR-002, documentado em validacao.md |
| FastAPI lazy (`_IncludedRouter`) esconder rotas do inventário | Walker do teste desce recursivamente por `original_router.routes` — **140 rotas capturadas** |

## Complexity Tracking

Nenhuma violação de constituição: mudança estrutural pura, zero comportamento, zero schema, RBAC/auditoria intocados por construção (código movido literalmente).

## Micro-remediações do /speckit-analyze (aplicadas 2026-09-28, antes do implement)

- **A1 (MEDIUM)**: FR-006 da spec prometia comparar "dependências de permissão" no inventário de rotas, mas o manifesto definido em tasks (T002) só captura path+methods+endpoint — promessa não verificável pelo mecanismo previsto. Corrigido: FR-006 alinhado ao manifesto; cobertura de permissões garantida pelos testes RBAC existentes + T013 reforçado com `test_rbac.py` completo.
- **A2 (LOW)**: FR-008 da spec deixava em aberto ("decidir em plan") algo que o plan já decidia — contradição spec↔plan. Spec atualizada com a decisão (facade re-exportador).
- **B1 (LOW)**: Faltava canário barato de imports circulares: T020 criado (`test_routers_structure.py`, importa cada módulo isoladamente) — complementa SC-005 sem esperar a suíte completa; T019 passa a registrar o resultado do RBAC em validacao.md.
- **C1 (INFO)**: tasks numeradas pulavam T014–T016 do US2 (design já cobria) — sequência F1→F9/B1 conferida contra o plan, sem gap real de execução.

## Remediações do IMPLEMENT (2026-09-28 — pós-evidência)

- **I1 (HIGH — Amendment A1)**: decomposição física do `backup_service.py` rejeitada com evidência (42 pontos de monkeypatch no namespace; funções resolvem globais no módulo de definição). Spec FR-007/FR-008/SC-003 e fase B1 do plan reescritos; módulo único + mapa de navegação. Detalhes em validacao.md §Achados.
- **I2 (MEDIUM)**: import circular facade↔domínios (primeira tentativa) — resolvido com `routers/templates_env.py`; FR-004 preservado (configuração única, agora no módulo de ambiente de templates).
- **I3 (LOW)**: `test_048_rotas_e_execute_intocados` (050) inspeciona fonte de `routes` — assertion ajustada para concatenar o módulo do domínio; strings verificadas idênticas; único teste existente editado (NR-002, documentado).
- **I4 (INFO)**: FastAPI lazy (`_IncludedRouter`) — walker do inventário desce recursivamente; 140 rotas capturadas.
- **I5 (INFO)**: `locais.csv` de docs com alteração pré-existente na working tree revertida (fora de escopo).
