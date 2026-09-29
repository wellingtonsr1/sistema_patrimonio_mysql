# Quickstart: 054-suite-hermetica

## 1. Rodar a suíte sem MariaDB (a prova do M1)

Pare o MySQL/XAMPP (ou use uma DATABASE_URL de porta morta) e execute:

```bat
set DATABASE_URL=mariadb+pymysql://x:x@localhost:3390/inexistente
test.bat -q
```

Resultado esperado: **882 passed / 2 failed** (apenas os 2 pré-existentes de `test_backup_externo.py`) — idêntico ao resultado com o MariaDB real de pé.

## 2. Uso do runner

```bat
test.bat                      :: suíte completa (venv)
test.bat tests/test_inventario.py -q
test.bat -k hermeticidade -v
```

O `test.bat` fixa `.venv\Scripts\python.exe` (sem venv, cai para o `python` do PATH).

## 3. Guarda automatizada

```bash
python -m pytest tests/test_hermeticidade_suite.py -v
```

5 testes que provam: lifespan não toca banco real (TestClient sobe com engine apontando para porta morta), `app.main.SessionLocal` é o de teste, bootstrap não cria usuário global, `test.bat` usa o venv, README documenta.
