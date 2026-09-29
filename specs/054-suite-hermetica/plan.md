# Implementation Plan: Suíte de testes hermética (054)

**Branch**: `054-suite-hermetica` · **Spec**: [spec.md](spec.md) · **Created**: 2026-09-29

## Summary

O conftest passa a redirecionar a fonte de dados do lifespan (`app.main.SessionLocal` + fallback `app.database.SessionLocal`) para o banco de TESTE e torna o bootstrap do lifespan no-op sob a suíte — eliminando a dependência do MariaDB do `.env`. Runner `test.bat` fixa o Python do venv. Produção intocada.

## Technical Context

**Arquivos**: `tests/conftest.py` (correção), `tests/test_hermeticidade_suite.py` (novo, TDD), `test.bat` (novo), `README.md` (doc). Nada em `app/`.

## Constitution Check

| Princípio | Status | Nota |
|---|---|---|
| I. Evolução incremental | PASS | Somente a suíte ganha isolamento; produção intocada |
| II. Arquitetura em camadas | PASS | Conftest é infra de teste |
| III. Regras de negócio nos services | PASS | Zero regra tocada |
| IV/V. Integridade patrimonial/inventário | PASS | Nenhum dado tocado; protege até o banco REAL de escritas acidentais do bootstrap |
| VI. Segurança RBAC | PASS | Intocada |
| VII. Banco protegido | PASS | Suíte deixa de abrir conexões com o banco real (ganho) |
| VIII. Testes como não-regressão | PASS | Régua: suíte completa com DATABASE_URL morta = baseline |
| IX. Auditoria | PASS | Intocada |
| XI. Documentação fiel | PASS | README atualizado (FR-007) |
| XII. Especificações e validação | PASS | validacao.md com evidências |

**GATE: PASS 10/10**

## Design

### D1 — O patch no conftest (import-time, uma vez)

```python
# 054 (M1): hermeticidade — o lifespan NÃO pode tocar o banco real.
import app.main as _app_main
import app.database as _app_database
from app.services import auth_service as _auth_service

_app_main.SessionLocal = TestingSessionLocal      # fonte de dados do lifespan
_app_database.SessionLocal = TestingSessionLocal  # fallback p/ importadores tardios
_app_main.init_db = lambda: None                  # create_all já é feito pelos fixtures
_app_main.ensure_admin_user = lambda *a, **k: None
_app_main.ensure_default_roles = lambda *a, **k: None
```

Justificativas:
- **`app.main.SessionLocal`** é o nome que o lifespan usa (`db = SessionLocal()` em `main.py`) — redirecioná-lo é suficiente para o bootstrap.
- **`app.database.SessionLocal`** cobre importadores tardios (`from app.database import SessionLocal` dentro de funções — padrão existente em `templates_env._inject_current_user` etc.), que sob a suíte também devem cair no banco de teste.
- **`init_db` no-op**: o create_all por teste (`db_session` fixture) já cria TODAS as tabelas; rodar `create_all`+ALTERs do MariaDB no boot de cada TestClient é trabalho morto e a fonte do acoplamento.
- **`ensure_admin_user`/`ensure_default_roles` no-op**: hoje escrevem no banco REAL durante os testes (efeito colateral da 020/documentado no conftest). O estado visível dos testes não muda: nenhum teste lê o admin global — os usuários vêm de `_create_test_user`/fixtures.
- **Scheduler**: já neutralizado por teste (`_scheduler_session_isolation` monkeypatcha `start_scheduler`/`stop_scheduler`); o no-op do `init_db` não interfere.

### D2 — Por que é seguro (riscos examinados)

| Risco | Análise | Mitigação |
|---|---|---|
| Algum teste lê o usuário `admin` criado pelo lifespan | Verificado por grep: nenhum teste referencia `AUTH_ADMIN_USERNAME`/usuário global; todos criam os próprios usuários | `test_suilen_anterior_produzia_erros_de_setup` fixa que não há `admin` no banco de teste |
| Teste de backup/restore usa o `engine` real | `test_backup_manual/externo` monkeypatcham `backup_service.DATABASE_URL`/`_run_mysqldump` (dumps fake); nada abre `app.database.engine` | grep negativo no recon |
| Middleware de manutenção lê `backup_service.maintenance_mode` | Flag em MEMÓRIA, sem banco (F1 da 019) | Intocado |
| Scheduler real disparar durante a suíte | Já monkeypatchado por teste (021) | Intocado |
| `health_check` toca `SessionLocal()` (import tardio de `app.database`) | Coberto pelo fallback `app.database.SessionLocal` → TestingSessionLocal (D1); o teste de health existente continua válido pois o SELECT 1 no SQLite funciona | Teste existente de /health como régua |

### D3 — Runner `test.bat`

```bat
@echo off
REM Suíte do SisPatrimônio Pro — SEMPRE com o Python do venv
REM (fora do venv, o subprocesso de anti-regressão não encontra o dotenv: 053/D3)
setlocal
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m pytest %*
```

Pass-through de argumentos (`test.bat tests/test_inventario.py -q`, `test.bat -q`, `test.bat -k hermeticidade`). Fallback para `python` do PATH se o venv não existir (ex.: clone fresco em CI antes do venv — documentado).

### D4 — Ordem de validação (régua F2 da 050)

1. RED: os 4 testes novos falham (prova 2026-09-29).
2. Aplicar D1 + D3 + doc.
3. GREEN arquivo novo.
4. **Régua final**: suíte completa com `DATABASE_URL` morta via venv → 882/2 (SC-002).

## Complexity Tracking

Nenhuma violação.
