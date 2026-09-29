# Tasks: 054-suite-hermetica

**Input**: plan.md + spec.md de `specs/054-suite-hermetica/`

## Phase 1: TDD

- [x] T001 RED: `tests/test_hermeticidade_suite.py` com os 5 testes (lifespan/porta morta, SessionLocal de teste, sem admin vindo do bootstrap, test.bat com venv, README) — 4 failed registrados em 2026-09-29
- [x] T002 RED: prova de dependência — `DATABASE_URL=...:3390 (porta morta) pytest tests/test_inventario.py` → 12 errors de setup (20 passed); registrada no validacao.md

## Phase 2: Implementação

- [x] T003 D1: patch no `tests/conftest.py` (app.main/app.database SessionLocal → TestingSessionLocal; init_db/ensure_admin_user/ensure_default_roles no-op)
- [x] T004 D3: criar `test.bat` (venv + pass-through)
- [x] T005 FR-007: README — hermeticidade + runner `test.bat` + DATABASE_URL_TEST

## Phase 3: Validação

- [x] T006 GREEN: arquivo novo 5/5
- [x] T007 Régua (SC-002): suíte completa com DATABASE_URL morta via venv → 882 passed / 2 failed (idêntica ao baseline)
- [x] T008 `git diff --stat` confinado (conftest, teste novo, test.bat, README) — FR-003/SC-004
- [x] T009 Escrever `validacao.md` (V1–V6)
