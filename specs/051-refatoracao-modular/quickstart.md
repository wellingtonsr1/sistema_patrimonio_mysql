# Quickstart: 051-refatoracao-modular

Como validar a refatoração em 5 minutos (após o implement).

## 1. Inventário de rotas (prova principal)

```bash
DATABASE_URL_TEST="sqlite:///:memory:" .venv/bin/python -m pytest tests/test_route_inventory.py -q
```

Deve passar: paths + methods + nomes de endpoint idênticos ao manifesto capturado pré-refatoração.

## 2. Estrutura esperada

```bash
wc -l app/web/routes.py app/services/backup_service.py
ls app/web/routers/ app/services/backup/
```

- `routes.py` ≤ 200 linhas; `backup_service.py` ≤ 60 linhas
- `routers/`: shared, auth, setup, dashboard, assets, movements, custodians, locations, maintenances, reports, inventario
- `backup/`: `__init__`, paths, dump, restore, service, records

## 3. Consumidores intocados

```bash
git diff --name-only main...HEAD | grep -E "(main\.py|admin_routes\.py|help_routes\.py)"
```

Não deve retornar nada.

## 4. Suíte completa

```bash
DATABASE_URL_TEST="sqlite:///:memory:" .venv/bin/python -m pytest -q
```

Baseline: tudo verde exceto os 2 failures pré-existentes de `test_backup_externo.py` (fora de escopo).

## 5. Fumaça do ciclo sensível (restore 019)

```bash
DATABASE_URL_TEST="sqlite:///:memory:" .venv/bin/python -m pytest tests/test_backup_restauracao* tests/test_backup_ciclo* -q
```

Se existir teste do modo manutenção/503, é o canário de imports circulares do pacote `app/services/backup/`.
