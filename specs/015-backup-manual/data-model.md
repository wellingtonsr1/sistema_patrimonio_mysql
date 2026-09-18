# Data Model: Backup Manual do SisPatrimônio Pro

**Feature**: 015-backup-manual | **Data**: 2026-09-17

> **Zero DDL**: nenhuma tabela/coluna é criada. Este documento descreve o **artefato de runtime**, a permissão e os eventos de auditoria da funcionalidade.

---

## 1. Artefato: arquivo de backup (runtime, não-entidade de banco)

| Atributo | Valor |
|---|---|
| Caminho | `DATA_DIR / "backups" / filename` (`BACKUP_DIR` em `app/config.py`) |
| Nome | `backup_YYYYMMDD_HHMMSS_micros.sql` — timestamp **UTC** com microssegundos (coerência com o padrão de datas do projeto — feature 004 — e com a trilha de auditoria; **remediação I1**) |
| Formato | Dump SQL textual do banco de produção (`mysqldump --single-transaction --no-tablespaces`) |
| Unicidade | Microssegundos no nome → gerações repetidas nunca colidem |
| Reconhecimento | Regex estrita `^backup_\d{8}_\d{6}_\d{6}\.sql$` — a listagem ignora arquivos que não casam (artefatos alheios, path traversal impossível por construção) |

**Metadados consultáveis** (derivados do arquivo — nada persistido): `filename`, `timestamp` (do nome), `size_bytes` (do disco).

## 2. Permissão (registro no catálogo existente — seed idempotente)

```python
{"name": "backup.gerenciar", "module": "Backup",
 "label": "Gerenciar backups",
 "description": "Gerar, listar e baixar backups manuais do sistema."}
```

- **Concessão**: perfil **Administrador** herda automaticamente (o papel seed referencia todas as permissões do catálogo); outras concessões pela gestão de perfis existente.
- **Bypass**: `User.is_admin` mantém o comportamento existente (auditado).

## 3. Eventos de auditoria (trilha `audit_logs` existente)

| Evento | Quando | Campos principais |
|---|---|---|
| `BACKUP_CRIADO` (action) | geração concluída | `module="Backup"`, `resource="backup"`, `result=SUCCESS`, `new_data={"arquivo": filename, "tamanho_bytes": n}` |
| `BACKUP_CRIADO` (falha) | geração falhou | `result=FAILURE`, `description` = mensagem de erro controlada (**sem** comando/credenciais/stderr completo) |
| `BACKUP_DOWNLOAD` | download servido | `module="Backup"`, `resource="backup"`, `result=SUCCESS`, `new_data={"arquivo": filename}` |

Regras: escrita **somente** via `write_audit` existente; usuário = operador autenticado; IP = `_client_ip` (padrão das rotas); nunca credenciais (Princípio VI). Acesso negado (403) continua auditado pelo mecanismo existente.

## 4. Estados da operação de geração

```text
[Solicitado] ── permissão ok? ──n──> 403 (auditado pelo mecanismo existente)
     │ sim
     ▼
[Executando dump] ── sucesso? ──s──> [Arquivo gravado] ──> BACKUP_CRIADO/SUCCESS ──> redirect com confirmação
     │ não
     ▼
[BACKUP_CRIADO/FAILURE] ──> tela de erro controlada (nenhum artefato parcial é listado —
                            o service só reconhece arquivos com o padrão de nome completo)
```

Invariantes:

- **BV-1** — A listagem reflete **exatamente** o repositório: arquivo presente = listado (se padrão ok); arquivo ausente = não listado; download de ausente = 404.
- **BV-2** — Nenhum estado é persistido em banco; reinicialização da aplicação não altera a listagem.
- **BV-3** — O service nunca sobrescreve um backup existente (nome único por microssegundos).
- **BV-4** — Falha de geração não deixa artefato reconhecível (gravação é atômica na prática: arquivo é criado pelo utilitário; em falha, o service remove qualquer `.sql` parcial que tenha iniciado — regex só casa o nome completo, e o arquivo parcial com nome completo é removido antes do evento de falha).

## 5. Fluxo de download (integridade)

`GET /admin/backups/{filename}/download` → regex valida `filename` → `FileResponse` com `filename=` (precedente de headers de exportação) → `BACKUP_DOWNLOAD` auditado. Conteúdo servido = bytes exatos do arquivo em disco (SC-003).
