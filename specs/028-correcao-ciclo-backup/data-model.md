# Data Model: Correção do Ciclo de Backup, Restauração e Agendamento Automático (028)

**N/A — zero DDL.** A 028 não cria, altera ou remove tabela/coluna/índice (Constitution VII; FR-025).

Uso exclusivo de entidades existentes, com campos já presentes:

| Entidade | Uso na 028 | Campos tocados |
|---|---|---|
| `backup_records` (`BackupRecord`) | Leitura do snapshot pré-import e reconciliação pós-import (UPDATE de campo divergente; INSERT apenas para registro perdido) | `filename` (UNIQUE preservada), `backup_type`, `status`, `timestamp`, `size_bytes`, `sha256` — nenhum campo novo |
| Estado em memória do scheduler | Nova variável de módulo `_attempted_cycle_keys: set` (marcas de ciclo já tentado neste processo) | — (não persistida; crash/restart limpa por construção) |
| Estado de manutenção/restauração (`maintenance_mode`) | Somente leitura pela rota em modo degradado (`restore_status()`) | — |

Regras de integridade mantidas: vocabulário de tipo controlado (`MANUAL`/`AUTOMATICO`/`PRE_RESTAURACAO`), `timestamp` UTC naive (política 004), `filename` único, `removed_at/removed_reason` exclusivos da retenção — a reconciliação NUNCA grava campos de retenção.
