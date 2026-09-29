# Registro de Validação — Feature 054 (Constituição XII)

**Data**: 2026-09-29 · **Feature**: Suíte de testes hermética (achado M1 da análise) + runner com venv
**Método**: TDD (5 testes novos escritos e vistos falhar antes da implementação) + régua comparativa dupla (suíte completa com `DATABASE_URL` MORTA × suíte completa com MariaDB real) + smoke do runner + `git diff --stat`.

## Alteração aplicada (diff confinado — SC-004)

| Arquivo | Mudança |
|---|---|
| `tests/conftest.py` | +25: patch de hermeticidade — `app.main.SessionLocal`/`app.database.SessionLocal` → `TestingSessionLocal`; `init_db`/`ensure_admin_user`/`ensure_default_roles` no-op no lifespan |
| `tests/test_hermeticidade_suite.py` | **Novo** — 5 testes (TDD) |
| `tests/test_backup_restore.py` | +11 (Amendment A1): `_patch_worker_sessions` também fakeia o executor do dump de segurança (`_run_mysqldump`) — zero assertions alteradas |
| `test.bat` | **Novo** — runner oficial com `.venv\Scripts\python.exe` + pass-through |
| `README.md` | Seção "Testes Automatizados": hermeticidade, runner, nota da 045 |
| `specs/054-suite-hermetica/` | Artefatos spec-kit completos |

**Zero alteração** em: `app/` (produção intocada), nenhum assertion de teste alterado.

## V1 — Prova do problema (RED) ✅

- `DATABASE_URL=...localhost:3390 (porta morta)` + `pytest tests/test_inventario.py` → **12 errors de conexão no setup** (20 passed) — a dependência do MariaDB real provada antes da correção.
- Arquivo novo no RED: 4 failed (lifespan tocava banco real; `SessionLocal` do main não era a de teste; `test.bat` inexistente; README sem hermeticidade).

## V2 — Lifespan hermético (SC-001/FR-001/FR-002) ✅

`test_lifespan_nao_toca_banco_real`: `TestClient(app)` sobe E desce com `app.database.engine` apontando para porta morta — sem erro. `test_sessionlocal_do_main_aponta_para_banco_de_teste`: `app.main.SessionLocal` ≡ `TestingSessionLocal`. Bootstrap no-op: nenhum usuário global criado pelo lifespan (dados vêm dos fixtures — comportamento idêntico ao anterior, eliminado o efeito colateral de escrever no banco REAL durante os testes).

## V3 — Dependências ocultas eliminadas (Amendment A1) ✅

Diagnóstico pós-régua: além do lifespan, o **ciclo de restore** (019) tinha 2 caminhos para o banco/servidor real: (a) o worker usa `backup_service.SessionLocal` (já coberto pela fixture existente); (b) o **dump de segurança pré-restauração** usava `_run_mysqldump` REAL — com URL morta, 14 testes do ciclo abortavam (`ACTION_BACKUP_RESTORE_SUCCESS` nunca auditado). Correção confinada ao helper `_patch_worker_sessions` (que já existia para isso), fake com o mesmo padrão do `test_backup_manual._fake_dump`. Escopo por-teste de propósito: `test_backup_manual` exercita o executor REAL (fake global os quebraria).

## V4 — Régua comparativa dupla (SC-002/FR-006) ✅

| Execução (Python do venv) | Resultado | Tempo |
|---|---|---|
| Suíte completa com `DATABASE_URL` **morta** (porta 3390) | **887 passed / 2 failed** | 64,2s |
| Suíte completa com MariaDB real de pé | **887 passed / 2 failed** | 61,8s |
| Baseline pré-054 (validação da 053) | 882 passed / 2 failed | 115,6s |

882 mantidos + 5 novos da 054 = 887. Os 2 failures são exatamente os pré-existentes de `test_backup_externo.py` (045, fora de escopo). **Nenhum teste que passava passou a falhar.** Bônus medido: suíte ~2× mais rápida (o bootstrap real em cada TestClient custava ~50s de suíte). Isolado pós-A1: `test_019_webPostRestaurarResponde303Imediato` 1 passed.

## V5 — Runner com venv (SC-003/FR-004/FR-007) ✅

`test.bat` presente, fixa `.venv\Scripts\python.exe` (fallback: `python` do PATH), pass-through provado (`test.bat tests\test_hermeticidade_suite.py -q` → 5 passed). README documenta hermeticidade + runner + `DATABASE_URL_TEST`. Guardas: `test_test_bat_usa_python_do_venv`, `test_readme_documenta_hermeticidade`.

## V6 — Escopo, decisões e limitações

- `git diff --stat`: 3 arquivos editados (+54/−6) + 2 novos (`test.bat`, `tests/test_hermeticidade_suite.py`) + specs — FR-003/SC-004 cumprido.
- **D1**: patch no import do conftest (custo zero por teste); cobertura dupla (`app.main` + `app.database`) para importadores tardios (health_check, templates_env).
- **D2 (A1)**: único arquivo de teste existente tocado é `test_backup_restore.py`, somente infraestrutura de helper — nenhuma assertion alterada (espírito NR-002 da 051).
- **D3**: `DATABASE_URL_TEST` continua suportado (roda contra MariaDB quando configurado) — nada foi removido.
- **Limitação**: testes que param a thread do scheduler seguem com o patch existente (021); novo bootstrap de banco em `app.main` quebrará o guarda (intencional).

## Resultado

**V1–V5: PASS** · V6: escopo cumprido, decisões registradas — SC-001..004 satisfeitos.
