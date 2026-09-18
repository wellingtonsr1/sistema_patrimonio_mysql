# Contract — BackupService v2 (feature 016)

**Feature**: 016-backup-manual-completo | **Data**: 2026-09-17

Contrato v2 do `app/services/backup_service.py`. **Nenhuma assinatura pública é removida**; mudanças são aditivas ou internas (comportamento previsto na spec). Rotas web e permissão: INTOCADAS.

---

## 1. `generate_backup(db, user, ip_address, *, dump_executor=None) -> dict`

### Fluxo v2 (atômico — §27, research R1/R2)

1. `base = backup_YYYYMMDD_HHMMSS_micros` (UTC, microssegundos — inalterado); `part = BACKUP_DIR / f"{base}.part"`.
2. `LOG info` — início da geração.
3. Executor (fake nos testes / `_run_mysqldump` em produção) grava o dump em `part` (o executor recebe o caminho do temporário).
4. Compressão **streaming**: `part` → `part.gz` (blocos de 1 MB, `gzip.open` stdlib); `part` original removido após compressão bem-sucedida.
5. Validação: `part.gz` existe, tamanho > 0, abre/legível como gzip.
6. `sha256 = hashlib.sha256` streaming sobre `part.gz`.
7. **Renomear** `part.gz` → `BACKUP_DIR / f"{base}.sql.gz"` (atômico, mesmo filesystem).
8. `BACKUP_CRIADO`/SUCCESS com `new_data={"arquivo", "tamanho_bytes", "sha256"}` + `LOG info` (duração, tamanho, sha256).
9. Retorno: `{"filename", "timestamp", "size_bytes", "sha256"}` — **campo aditivo** `sha256`.

### Falha (qualquer passo 2–6)

- Remove `.part*` remanescentes (nunca há nome final parcial — BV-8).
- `BACKUP_FALHA`/FALHA com descrição segura (§19/§25) + `LOG error` (exceção controlada, sem segredos — §26).
- Propaga `BackupError` (rota 015 exibe mensagem controlada — inalterada).

**Restrições preservadas**: `dump_executor` injeção (research R4 da 015); sem argv/credenciais em erro/log/auditoria; nunca sobrescreve nome final existente (checagem prévia mantida).

## 2. `_run_mysqldump(path)` (função de módulo — inalterada)

Mesmo contrato da 015: parse de `DATABASE_URL`, `--single-transaction --no-tablespaces`, `MYSQL_PWD` no ambiente. Ponto único de monkeypatch dos testes web (remediação U1 da 015).

## 3. `list_backups() -> List[dict]`

```python
[{"filename": str,              # .sql (015) ou .sql.gz (016)
  "timestamp": datetime,        # do nome, UTC
  "size_bytes": int,
  "sha256": str | None,         # None p/ .sql antigos (BV-10)
  "integrity": "OK" | "CORROMPIDO" | "—"}, ...]   # campos aditivos
```

- Regex atualizada: `^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$` (compatibilidade R7); `.part` **nunca** casa.
- Ordenação desc por nome (mantida); diretório inexistente → [].
- `sha256`: streaming on-demand; `integrity`: OK (legível + hash presente + trailer gzip válido), CORROMPIDO (gzip ilegível/trailer inválido), — (`.sql` sem checksum).

## 4. `get_backup_path(filename)` (inalterado)

Regex estendida (aceita ambos os sufixos) + existência; `FileNotFoundError` → 404 na rota (015). `.part` rejeitado por não casar.

## 5. `audit_service.py` (+2 linhas aditivas)

```python
ACTION_BACKUP_FAILED = "BACKUP_FALHA"        # nova
ACTION_LABELS[ACTION_BACKUP_FAILED] = "Backup Falhou"
```

`BACKUP_CRIADO`/`BACKUP_DOWNLOAD` e demais eventos: intocados.

## 6. `admin/backups.html` (colunas — §18)

- Colunas: Arquivo · Data/Hora (UTC) · Tamanho · **Integridade** · **SHA-256** (truncado, `title` completo) · Ações.
- `integrity == "OK"` → badge verde; `—` → neutro; `CORROMPIDO` → badge vermelho.
- Nenhum botão de restauração; textos atualizados (`.sql.gz`).

## 7. Contrato de testes (§34 — A–J)

| Teste | Status na 015 | Ação na 016 |
|---|---|---|
| A autorizado (arquivo+tamanho+auditoria) | existe | adaptar: `.sql.gz` + `sha256` em new_data |
| B não autorizado | existe | manter |
| C/D download autorizado/negado | existe | adaptar conteúdo gzip |
| E inexistente → 404 | existe | manter |
| F path traversal | existe | reforço: `.part` também inacessível |
| G falha sem falso sucesso | parcial | **literal**: `BACKUP_FALHA` + sem parcial + log |
| H múltiplos sem sobrescrever | parcial (service) | **literal web**: 2 POSTs → 2 arquivos, listagem com 2 |
| I integridade (leitura + checksum) | ausente | **novo**: recomputar SHA-256 == exibido; gzip legível |
| J regressão | existe | suíte completa verde |
| — novo: atomicidade | — | `.part` inexistente ao final; nome final só pós-validação |
| — novo: compat `.sql` | — | `.sql` antigo listado/baixável, Integridade — |
