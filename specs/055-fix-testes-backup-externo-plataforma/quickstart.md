# Quickstart: 055-fix-testes-backup-externo-plataforma

## 1. O arquivo histórico (agora verde)

```bash
python -m pytest tests/test_backup_externo.py -v
# 20 passed — incluindo test_destino_sem_permissao e test_zero_segredos_em_logs
```

## 2. Régua nova da casa

A partir da 055, a suíte completa deve terminar com **0 failed**:

```bat
test.bat -q
:: 889 passed, 0 failed
```

As 2 falhas "aceitas" desde a 045 deixam de existir: a régua de regressão das próximas features fica mais forte (qualquer novo failure é regressão real).

## 3. Como a simulação funciona (Windows)

`icacls <dest> /deny *S-1-1-0:(WD)` nega a permissão de escrita ao SID Everyone (bem-conhecido, imune a locale). A etapa 6 da cópia (`open(tmp,"wb")`) levanta `PermissionError` — a mesma exceção que o service da 045 mapeia para "sem permissão de escrita". Em POSIX, o `chmod r-x` original é preservado no helper.
