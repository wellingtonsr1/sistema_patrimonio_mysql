# Aviso operacional — Restauração trava no Windows (bug da 017, bloqueante)

**Data**: 2026-09-18 · **Status**: diagnóstico concluído, correção pendente de especificação
**Relacionada**: features 015–018 (backup/restauração) · **Severidade**: ALTA para uso da restauração

## Sintoma observado (2026-09-18, ~09:21)

Restauração de backup iniciada pela tela travou indefinidamente:

- `SHOW PROCESSLIST` (MariaDB): `DROP TABLE IF EXISTS audit_logs` esperando
  **933 s** por *metadata lock*; uma conexão **Sleep** do pool da aplicação
  segurando o lock havia o mesmo tempo;
- Cliente `mysql.exe` do import vivo, sem consumir CPU (bloqueado no write
  do pipe com o processo web);
- Consultas ao banco pela aplicação (inclusive auditoria) davam timeout
  enquanto o travamento persistia;
- O `proc.wait(timeout=900)` da 017 **nunca dispara**: o timeout conta só o
  `wait()`, mas o bloqueio ocorre antes, no `proc.stdin.write(chunk)`.

## Causa (bug de arquitetura da 017, potencializado pelo ambiente Windows)

O import roda **dentro do processo web** e alimenta o cliente `mysql` via
stdin. O dump restaurado contém `DROP TABLE`/`CREATE TABLE` de **todas** as
tabelas, incluindo `audit_logs` e `user_sessions`. Conexões do pool
SQLAlchemy do mesmo processo ficaram com *metadata lock* pendente (sessões
abertas durante a operação) → o import espera o lock que **a própria
aplicação segura** → deadlock de auto-bloqueio. No Linux/servidor dedicado o
risco é o mesmo; no Windows de desktop (uso interativo simultâneo) é quase
certo de ocorrer.

## Estado do banco após destravar

- `mysql.exe` (PID 4440) finalizado via `taskkill`; lock liberado;
  aplicação voltou a responder (SELECT 1 = OK).
- **Banco em estado PARCIAL/INDEFINIDO**: o import pode ter reconstruído
  tabelas até `ad_settings` (ordem alfabética) e travou em `audit_logs`.
  O dump das 09:21 (`backup_20260918_122112_494468.sql.gz`) está íntegro na
  listagem.

## Remediação imediata (recomendada — executar com a aplicação PARADA)

Restaurar o banco ao estado das 09:21 **fora do sistema**, por linha de
comando:

```bat
C:\xampp\mysql\bin\mysql.exe -u patrimonio -p sispatrimoniopro < caminho\para\backup_20260918_122112_494468.sql
```

(Extrair o `.sql` do `.sql.gz` antes — p.ex. com 7-Zip.)

## Correção de código necessária (nova especificação)

Feature candidata: 019-import-deadlock — opções a avaliar no plan:

1. **Executar o import fora do processo web** (subprocesso independente) OU
   encerrar/drenar o engine da aplicação durante o import (com recriação);
2. `DROP/CREATE DATABASE` em vez de tabela a tabela, eliminando a
   dependência de locks por tabela;
3. Timeout real: vigiar o processo (poll + consumo do stderr em threads) em
   vez de `proc.wait(timeout=...)` após writes bloqueantes;
4. Impedir uso interativo do sistema durante a restauração (tela de
   manutenção), reduzindo a janela do lock.

## Backups disponíveis (integridade OK)

- `backup_20260918_121803_887383.sql.gz` (14.047 B, 09:18)
- `backup_20260918_122112_494468.sql.gz` (14.306 B, 09:21)
