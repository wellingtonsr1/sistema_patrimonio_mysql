# Data Model: Correção do Deadlock da Restauração (feature 019)

## Veredito: N/A — zero alterações de dados

A 019 **não cria, altera ou remove tabelas, colunas, índices ou constraints**. Nenhuma migration. Nenhum DDL (Constitution VII; spec FR-015).

## Estado novo (apenas em memória do processo — não é banco)

```text
backup_service.maintenance_mode:
  active: bool          # middleware consulta; worker define/limpa em finally
  started_at: datetime  # para a tela de manutenção
  phase: str            # "validando" | "seguranca" | "importando" | "verificando"
  target_file: str      # nome do backup sendo restaurado (feedback da tela de backups)
```

- **Persistência**: nenhuma (deliberada — R3: crash/restart limpa o modo de manutenção por construção, FR-011).
- **Processo único**: uvicorn single-worker no deploy atual — a flag em memória é suficiente e o contract do quickstart valida isso.

## Configuração nova (1 variável, opcional)

| Variável | Default | Significado |
|---|---|---|
| `BACKUP_IMPORT_TIMEOUT` | `900` (segundos) | Deadline de relógio para a fase de import (todas as fases do subprocesso: feed no stdin incluído). Estourou → `terminate()` + `BACKUP_RESTORE_FALHA` |

Documentada no `.env.example` (sem segredos) e no README — mesmo padrão da `MYSQLDUMP_PATH` da 018.
