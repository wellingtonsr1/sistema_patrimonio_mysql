# Contract — BackupService v3: Restauração (feature 017)

**Feature**: 017-restauracao-segura-backup | **Data**: 2026-09-17

Extensão aditiva de `app/services/backup_service.py`. **Nenhuma assinatura pública existente é alterada** (`generate_backup`, `list_backups`, `get_backup_path`, `_run_mysqldump`, `_gzip_read_status` permanecem). Rotas, permissão `backup.gerenciar` e fluxos da Feature 1: intocados.

---

## 1. Estado de concorrência (R6 — FR-16/FR-17)

```python
_RESTORE_LOCK = threading.Lock()      # stdlib, nível de módulo
_RESTORE_IN_PROGRESS = False          # flag protegida pelo lock
```

- `restore_in_progress() -> bool` — consulta protegida.
- Aquisição no início do ciclo (context manager interno `_restore_slot()`): marca a flag, `finally` libera.
- **Geração de backup manual** (`generate_backup`) passa a recusar com `BackupError` enquanto a flag estiver ativa (1 guarda aditiva no início da função — comportamento da geração inalterado no restante).
- Tentativa de restore concorrente → `BackupError("Já existe uma restauração em andamento...")` → rota informa mensagem clara.

## 2. Validação do backup selecionado (R4 — FR-09)

```python
validate_restore_source(filename: str) -> dict
    # → {"path": Path, "is_gzip": bool, "size_bytes": int}
    # Levanta BackupError com motivo seguro se:
    #   - nome fora do padrão / fora do diretório / inexistente (reusa get_backup_path)
    #   - integridade == CORROMPIDO (consulta list_backups() do arquivo)
    #   - tamanho == 0
    #   - ilegível (gzip integral OU .sql com conteúdo não-vazio)
```

## 3. Import do dump (R1/R2 — FR-13/FR-14/FR-15)

```python
_run_mysql_import(path: Path, *, is_gzip: bool) -> None    # função de MÓDULO (monkeypatch)
```

- Produção: subprocesso do cliente nativo (`mysql`) com stdin alimentado pelo Python:
  - `is_gzip=True`: `gzip.open(path, "rb")` → blocos de 1 MB → stdin do subprocesso;
  - `is_gzip=False`: leitura direta em blocos.
  - Credenciais de `DATABASE_URL` em memória; **senha exclusivamente no ambiente (`MYSQL_PWD`)**; argv com host/port/user/database apenas (mesma disciplina de `_run_mysqldump`).
  - `stderr` capturado e **nunca propagado** (pode conter host) → `BackupError("O utilitário de importação retornou erro.")`.
  - `timeout` de módulo (`_IMPORT_TIMEOUT_SECONDS = 900`).
- Testes: executor fake grava marcador/conteúdo e simula falhas (R2).

## 4. Validação pós-restore (R7 — FR-20/FR-21)

```python
validate_post_restore(db: Session) -> None      # levanta BackupError com motivo seguro
```

Sequência **somente-leitura** sobre a sessão do banco alvo:
1. `SELECT 1` executável;
2. presença das **17 tabelas essenciais** (catálogo do banco; nomes extraídos dos `__tablename__` reais dos models — **remediação A1**, lista completa e autoritativa): `users`, `user_roles`, `user_sessions`, `roles`, `role_permissions`, `permissions`, `custodians`, `locations`, `assets`, `movements`, `maintenances`, `inventarios`, `inventario_itens`, `audit_logs`, `ad_settings`, `ad_group_roles`, `setup_claims`;
3. contagens somente-leitura (`users`, `assets`, `custodians`) executáveis.

Nenhuma escrita. Qualquer exceção vira `BackupError` com motivo seguro.

## 5. Orquestração do ciclo (data-model §2.1 — BV-R1..R4)

```python
@staticmethod
def restore_backup(db, user, ip_address, filename, *, import_executor=None, security_backup_executor=None) -> dict
```

Ordem **invariável** (todas as etapas dentro do slot de concorrência):

1. `validate_restore_source(filename)` — falha → `BACKUP_RESTORE_FALHA` + raise (banco intocado).
2. `BACKUP_RESTORE_INICIADO` (SUCCESS, `{backup}`).
3. `generate_backup(...)` (mecanismo existente) → **backup de segurança**; falha → `BACKUP_RESTORE_FALHA` + raise (**restore não inicia**; banco intocado). **`security_backup_executor` é delegado como o `dump_executor` do próprio `generate_backup`** — `generate_backup(..., dump_executor=security_backup_executor)`; default `None` = executor padrão de produção (nenhum segundo caminho de geração — FR-02; **remediação U1**).
4. Validação do backup de segurança (existe, tamanho > 0, integridade OK do artefato) — falha → idem passo 3.
5. `BACKUP_PRE_RESTORE_CRIADO` (SUCCESS, `{backup, backup_seguranca}`).
6. `import_executor or _run_mysql_import(path, is_gzip)` — falha → `BACKUP_RESTORE_FALHA` + raise (**nunca sucesso**; backup de segurança preservado).
7. `validate_post_restore(db)` — falha → idem passo 6.
8. `BACKUP_RESTORE_SUCESSO` (SUCCESS, `{backup, backup_seguranca}`) → retorno:
   `{"restaurado": filename, "backup_seguranca": <nome>, "size_bytes": n}`.

Erros de concorrência (flag já ativa) **não** geram evento (nada foi iniciado) — mensagem ao usuário.

> Nota: em produção a sessão `db` da rota aponta para o banco real — após o import, o service valida nessa mesma sessão (novo `SELECT` com `pool_pre_ping` cobre reconexão). Em testes (SQLite) o fluxo idêntico é exercitado com executores fake.

## 6. audit_service.py (+8 linhas aditivas)

Constantes + rótulos (padrão 016): `ACTION_BACKUP_RESTORE_STARTED`/"Restauração Iniciada", `ACTION_BACKUP_PRE_RESTORE`/"Backup Pré-Restore Criado", `ACTION_BACKUP_RESTORE_SUCCESS`/"Restauração Concluída", `ACTION_BACKUP_RESTORE_FAILED`/"Restauração Falhou". Eventos e rótulos da 015/016 intocados.

## 7. permission_service.py (+1 linha aditiva)

`{"name": "backup.restaurar", "module": "Backup", "label": "Restaurar backups", "description": "Restaurar backups manuais do sistema (operação destrutiva com backup de segurança automático)."}` — seed idempotente concede ao Administrador; demais perfis: somente atribuição explícita.

## 8. Rotas web (admin_routes.py — R5; detalhe visual no ui-contract)

| Rota | Método | Permissão | Efeito |
|---|---|---|---|
| `/admin/backups/{filename}/restaurar` | GET | `backup.restaurar` | Tela de informações + advertência + confirmação (nada executa) |
| `/admin/backups/{filename}/restaurar` | POST | `backup.restaurar` | Executa o ciclo completo (§5) e redireciona com mensagem |

Nunca GET para executar; padrão `require_permission` existente; `_client_ip` para auditoria.

## 9. Mapa de testes (spec §8 — A–K)

| Teste | Cobertura |
|---|---|
| A | Ciclo completo com executor fake → success + eventos + backup de segurança listado |
| B | Sem permissão → 403 nas 2 rotas; sem evento de restore; banco inalterado |
| C | Cancelar (não confirmar) → nenhum evento de execução, nenhum backup de segurança |
| D | Backup corrompido (`integrity=CORROMPIDO`) → falha em `validate_restore_source`, sem backup de segurança |
| E | Inexistente → `FileNotFoundError` → 404/falha segura |
| F | Path traversal → rejeitado por `get_backup_path` |
| G | Executor de segurança fake que falha → restore não inicia, banco intocado, evento de falha |
| H | Executor de import fake que falha → `BACKUP_RESTORE_FALHA`, sem falso sucesso, backup de segurança preservado |
| I | Pós-restore: `validate_post_restore` verde após ciclo (SQLite) |
| J | Segunda chamada concorrente (monkeypatch segurando o slot) → rejeitada |
| K | Regressão completa (suíte 397 + novos) |
