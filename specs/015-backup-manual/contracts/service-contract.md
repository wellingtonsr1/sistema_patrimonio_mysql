# Contract — BackupService (feature 015)

**Feature**: 015-backup-manual | **Data**: 2026-09-17

Contrato do **novo** `app/services/backup_service.py` (regra de negócio centralizada — Princípios II/III). Nenhum service existente é alterado.

---

## 1. `BackupService` (novo)

### 1.1 `generate_backup(db: Session, user: User, ip_address: Optional[str], *, dump_executor: Optional[Callable] = None) -> dict`

Gera um backup do estado atual do sistema.

**Comportamento**:

1. Calcula `filename = backup_YYYYMMDD_HHMMSS_micros.sql` (timestamp **UTC** com microssegundos — coerência com o padrão de datas do projeto/feature 004; **remediação I1**).
2. Garante `BACKUP_DIR` existente.
3. Executa o dump via **`dump_executor`** se fornecido (ponto único de injeção para testes — R4); em produção usa o executor padrão `_run_mysqldump(path)` (R1/R2).
4. Em sucesso: valida que o arquivo existe e tem tamanho > 0; grava `ACTION_BACKUP_CREATED` com `RESULT_SUCCESS` e `new_data={"arquivo": filename, "tamanho_bytes": n}`; retorna o registro do backup.
5. Em falha: remove artefato parcial (BV-4); grava `ACTION_BACKUP_CREATED` com `RESULT_FAILURE` e descrição controlada; **propaga exceção** para a rota exibir erro controlado.

**Retorno (sucesso)**: `{"filename": str, "timestamp": datetime, "size_bytes": int}`

**Erros** (exceções propagadas, mensagem controlada, nunca detalhes do subprocesso): dump retornou erro (exit ≠ 0); arquivo vazio/ausente após execução; disco indisponível.

**Restrições**: NUNCA sobrescreve arquivo existente (BV-3); NUNCA registra comando/credenciais (Princípio VI); auditoria SEMPRE emitida (sucesso ou falha — FR-007/SC-004).

### 1.2 `_run_mysqldump(path: Path) -> None` (privado, executor padrão)

Deriva `user/host/port/db` de `DATABASE_URL` (parse em memória); executa `mysqldump --single-transaction --no-tablespaces` com `env` contendo `MYSQL_PWD` (R2); `stdout` → arquivo `path`; exit ≠ 0 → lança erro controlado. **Nunca** inclui a senha em argv/erro.

### 1.3 `list_backups() -> List[dict]`

Varre `BACKUP_DIR`; considera **somente** arquivos que casam a regex do padrão de nome (R3/R7); retorna lista ordenada do mais recente para o mais antigo:

```python
[{"filename": str, "timestamp": datetime, "size_bytes": int}, ...]
```

Diretório inexistente → lista vazia (nunca erro). Artefatos alheios → ignorados.

### 1.4 `get_backup_path(filename: str) -> Path`

Valida `filename` contra a regex estrita; retorna o caminho completo dentro de `BACKUP_DIR`. **Levanta erro** (→ 404 na rota) se o nome não casa ou o arquivo não existe. Impede path traversal por construção (R8).

---

## 2. Constantes de auditoria (aditivas em `audit_service.py`)

```python
ACTION_BACKUP_CREATED = "BACKUP_CRIADO"
ACTION_BACKUP_DOWNLOAD = "BACKUP_DOWNLOAD"
```

(Precedente: `ACTION_AD_CONNECTION_TESTED` etc.)

---

## 3. Permissão (aditiva em `permission_service.py`)

```python
{"name": "backup.gerenciar", "module": "Backup",
 "label": "Gerenciar backups",
 "description": "Gerar, listar e baixar backups manuais do sistema."}
```

Seed idempotente existente cadastra a permissão e a concede ao perfil Administrador no startup. Nenhuma alteração em `require_permission` ou nos perfis existentes.

---

## 4. Contrato de testes (mínimo — spec FR-012)

| Teste | Asserção mínima |
|---|---|
| Geração com executor fake | arquivo criado em `BACKUP_DIR`, nome casa regex, `size_bytes` > 0; retorno do service com os 3 campos |
| Auditoria da geração | `AuditLog` com `action=BACKUP_CRIADO`, `result=SUCCESS`, `new_data` com arquivo/tamanho |
| Auditoria da falha | executor fake lançando erro → `result=FAILURE`, nenhum artefato listado, exceção propagada |
| Listagem | 2+ backups → ordenados desc; arquivo alheio no diretório → ignorado |
| Download | conteúdo servido == conteúdo gravado (integridade — SC-003); header de attachment presente |
| Download inexistente | 404 (nome válido, arquivo ausente); nome fora do padrão → 404 (sem tocar disco) |
| RBAC negado | sem `backup.gerenciar` → 403 nas 3 rotas (e auditado pelo mecanismo existente) |
| RBAC concedido | admin/fake com permissão → 200 nas rotas |
| Menu | template contém item visível apenas com `can('backup.gerenciar')` |
| Zero-regressão | suíte completa verde (baseline RBAC exceto) |
