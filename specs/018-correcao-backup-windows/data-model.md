# Data Model: Correção do Backup Manual no Windows

**Feature**: 018-correcao-backup-windows | **Date**: 2026-09-18

## Entidades: NENHUMA ALTERAÇÃO (zero DDL)

Esta feature **não cria, altera ou remove** entidades, tabelas, colunas, índices ou
relacionamentos. A verificação das entidades existentes tocadas *indiretamente* (somente
leitura durante a geração) segue documentada abaixo para rastreabilidade.

## Estado tocado pela feature

| "Estado" | Alteração | Nota |
|---|---|---|
| Atributo `class` de elementos HTML | Nenhum | Nenhuma tela tocada |
| Ambiente do subprocesso do dump/import | **Sim** — de PATH fixo Unix para ambiente herdado + `MYSQL_PWD` | Único estado de runtime alterado (R1); sem persistência |
| `audit_logs` | Nenhum | Mesmos eventos, mesmo formato (FR-016) |
| Arquivos em `data/backups/` | Nenhum | Mesmos padrões `.part` → `.sql.gz` (regex `^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$` intocada) |

## Configuração (única adição)

| Variável | Tipo | Default | Uso |
|---|---|---|---|
| `MYSQLDUMP_PATH` | string opcional | `None` | Caminho absoluto do executável `mysqldump` do servidor (ex.: `C:\xampp\mysql\bin\mysqldump.exe`). Configurada → usada diretamente para o dump e derivada para o cliente de import (mesmo `bin`, R4). Ausente → fallback `shutil.which` no PATH do processo |

Segurança: a variável contém **caminho de executável**, nunca credencial. `.env.example`
recebe a linha de exemplo **sem segredo algum** (briefing §19).

## Invariantes preservados (verificação por teste)

1. Padrão do nome de backup (`_BACKUP_NAME_RE`) — intocado.
2. Temporários `.part`/`.part.gz` nunca casam o regex final — intocado.
3. Senha EXCLUSIVAMENTE no ambiente do subprocesso (`MYSQL_PWD`) — preservado e reforçado (R1).
4. Falha → remoção dos `.part*` + auditoria `ACTION_BACKUP_FAILED` + `BackupError` — intocado.
5. Guard "não gerar durante restauração" (017) — intocado.
6. Suíte: executores FAKE (nenhum subprocesso real nos testes) — padrão mantido.
