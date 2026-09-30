# Quickstart — Feature 058

## O que mudou
1. `app/web/templates/base.html` — botão do menu do usuário com atributo `style` íntegro (color + border-color no mesmo atributo).
2. `app/logging_config.py` — `_AsyncioNoiseFilter`: suprime do log registros do logger `asyncio` cuja exceção seja desconexão benigna de cliente (`ConnectionResetError`/`ConnectionAbortedError`/`BrokenPipeError`, os WinError 10054/10053/10038). Erros reais seguem íntegros.

## Como validar
```powershell
# Régua
.venv\Scripts\python.exe -m pytest tests/test_higiene_058.py -v
.venv\Scripts\python.exe -m pytest tests/ -q

# Filtro em ação (com o servidor de pé): derrubar uma conexão abruptamente e conferir
# que o app.error.log NÃO ganha traceback de 10054 — ex.: fechar o navegador à bruta.
```

## Rollback
Reverter os 2 arquivos (`git checkout -- app/web/templates/base.html app/logging_config.py`).
