# Feature Specification: Suíte de testes hermética (054)

**Feature Branch**: `054-suite-hermetica`

**Created**: 2026-09-29

**Status**: Draft

**Input**: Resolver o achado M1 da análise profunda de 2026-09-29 (`docs/ANALISE_PROFUNDA_SISTEMA_2026-09-29.md`): a suíte pytest, apesar de usar `DATABASE_URL_TEST="sqlite:///:memory:"`, depende do MariaDB local do `.env` porque o lifespan do `TestClient` executa `init_db()` → `app.database.engine` (banco REAL). Com o XAMPP parado ou `DATABASE_URL` apontando para porta morta, a suíte produz `ERROR at setup` em massa e não é executável. Fixar também o uso do Python do venv (D3 da validação da 053: fora do venv, `test_backup_config.py::test_anti_regressao_*` falha por `dotenv` invisível ao subprocesso).

---

## 1. Contexto (fonte: código real, 2026-09-29)

- `tests/conftest.py` cria o engine de TESTE (`sqlite:///:memory:` + StaticPool) e sobrepõe `get_db` — porém `app/main.py` importa `SessionLocal` e `init_db` de `app.database` (banco REAL) e o `TestClient(app)` executa o lifespan a cada fixture `client`/`unauth_client`.
- Prova RED (2026-09-29): `DATABASE_URL=...localhost:3390 (porta morta) python -m pytest tests/test_inventario.py` → **12 errors** de conexão no setup, 20 passed.
- Prova RED complementar (053/D3): com o Python do sistema (fora do venv), a suíte completa rende um 3º failure (`test_backup_config::test_anti_regressao_default_desativado_no_codigo_real` — o subprocesso com env enxuto não encontra o `dotenv` do user site-packages).
- Nenhum teste toca o banco real intencionalmente; os dumps de backup são fake (`_run_mysqldump` monkeypatchado — padrão 015–020) e o CLI é exercitado sobre a sessão de teste.

## 2. Objetivo

1. **US1**: o lifespan, sob a suíte, NÃO toca o banco real — nenhum teste depende do estado do MariaDB local; a suíte roda em qualquer máquina/CI.
2. **US2**: runner único e documentado (`test.bat`) que fixa o Python do venv, eliminando failures ambientais por interpretador.

## 3. Requisitos

### Functional Requirements

- **FR-001**: `tests/conftest.py` MUST garantir que, sob a suíte, `app.main.SessionLocal` (e o fallback `app.database.SessionLocal` para importadores tardios) apontem para a sessionmaker do banco de TESTE.
- **FR-002**: O bootstrap do lifespan sob a suíte (`init_db`, `ensure_admin_user`, `ensure_default_roles`, start/stop do scheduler) MUST ser no-op ou operar exclusivamente no banco de teste — o estado visível dos testes não muda: dados vêm exclusivamente dos fixtures (o comportamento ATUAL de fato: `ensure_admin_user` hoje escreve no banco real, efeito colateral indesejado que a correção elimina).
- **FR-003**: Nenhum arquivo de teste existente MAY ter assertions alteradas; apenas o `conftest.py` e adições (runner/documentação/teste novo) são permitidos.
  - **AMENDMENT A1 (2026-09-29, pós-evidência)**: o helper `_patch_worker_sessions` de `tests/test_backup_restore.py` (infraestrutura de teste, chamado pelos ciclos de restore) foi estendido para fakear também o executor do dump de segurança (`_run_mysqldump`) — sem nenhuma assertion alterada. Evidência: o ciclo de restore cria o pré-restauração com `_run_mysqldump` REAL (mysqldump + servidor do `DATABASE_URL`); com URL morta isso abortava 14 testes do ciclo (`ACTION_BACKUP_RESTORE_SUCCESS` nunca auditado). O fake segue o mesmo padrão do `test_backup_manual._fake_dump` e é confinado ao helper (por teste) porque `test_backup_manual` exercita o executor REAL — um fake global no conftest os quebraria.
- **FR-004**: Um runner `test.bat` na raiz MUST executar a suíte com `.venv\Scripts\python.exe -m pytest`, aceitando argumentos pass-through (ex.: `test.bat tests/test_inventario.py -q`).
- **FR-005**: `tests/test_hermeticidade_suite.py` (novo) MUST guardar: (a) subir/descer o app com `app.database.engine` apontando para porta morta sem erro; (b) `app.main.SessionLocal` ≡ sessionmaker de teste; (c) `test.bat` com o Python do venv; (d) README documentando hermeticidade e runner.
- **FR-006**: A régua de não-regressão é a suíte completa com `DATABASE_URL` MORTA: resultado idêntico ao baseline do venv (882 passed / 2 failed de `test_backup_externo.py`) — nenhum teste novo dependente de MariaDB.
- **FR-007**: `README.md` (seção "Testes Automatizados") MUST documentar: hermeticidade (banco real nunca tocado), runner `test.bat` e que `DATABASE_URL_TEST` continua disponível para rodar contra MariaDB.

### Não-requisitos

- Não alterar `app/main.py` nem `app/database.py` (produção intocada; a correção é confinada à suíte).
- Não migrar a suíte para MariaDB nem criar testes condicionais de infraestrutura (candidato futuro junto da 052/T010).
- Não tocar `backup_service.py`/`backup_scheduler.py` (A1 da 051: namespace de monkeypatch é API).

## 4. Critérios de sucesso

| # | Critério |
|---|---|
| SC-001 | `TestClient(app)` sobe/desce com `app.database.engine` apontando para porta morta, sem erro (teste novo) |
| SC-002 | Suíte completa com `DATABASE_URL=...porta morta` via **venv**: 882 passed / 2 failed — idêntica ao baseline com MariaDB real |
| SC-003 | `test.bat` presente, usando o venv; execução documentada no README |
| SC-004 | `git diff` confinado a: `tests/conftest.py`, `tests/test_hermeticidade_suite.py` (novo), `test.bat` (novo), `README.md` |

## 5. Assumptions

- `StaticPool` + `sqlite:///:memory:` já garante um banco por processo; a troca da fonte de dados do lifespan não afeta isolamento por teste (fixtures criam/derrubam tabelas por teste).
- O patch do lifespan é aplicado no import do conftest (módulo único de bootstrap da suíte), sem fixtures adicionais por teste — zero custo por teste.
- Se no futuro `app.main` ganhar novo bootstrap de banco, o teste (a) de FR-005 falhará — guardrail intencional.
