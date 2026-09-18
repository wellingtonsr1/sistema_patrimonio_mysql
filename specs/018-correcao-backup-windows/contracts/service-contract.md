# Contract: Correção do Backup Manual no Windows (feature 018)

Contrato dos caminhos de escrita/leitura afetados. Tudo o que NÃO está listado aqui
permanece **byte-idêntico** ao comportamento atual (Princípio I).

## 1. `app/config.py` — adição única

| Aspecto | Contrato |
|---|---|
| Nova variável | `MYSQLDUMP_PATH = os.getenv("MYSQLDUMP_PATH") or None` (opcional, sem default de caminho) |
| Efeito colateral | **Nenhum** — nenhuma variável existente é tocada (inclui `APP_HOST` pré-existente modificado localmente, fora do escopo) |

## 2. `BackupService.generate_backup` — invariante total da orquestração

| Aspecto | Contrato |
|---|---|
| Assinatura | Inalterada |
| Nome do artefato, `.part` → `.sql.gz`, gzip streaming, SHA-256, rename atômico | Inalterados |
| Validações (vazio, gzip legível) | Inalterados |
| Auditoria `ACTION_BACKUP_CREATED` SUCCESS/FAILURE | Mesmos eventos, mesmos campos, mesmas descrições controladas |
| Guard de restauração em andamento (017) | Inalterado |
| Retorno de sucesso `{filename, timestamp, size_bytes, sha256}` | Inalterado |

### 2.1 Comportamento de falha novo (única mudança de superfície)

| Causa | Antes | Depois |
|---|---|---|
| Executável ausente (Windows hoje) | `BackupError("Falha na geração do backup manual (erro de disco/subprocesso).")` — genérico | `BackupError` com mensagem distinta: utilitário **não encontrado** (menciona `MYSQLDUMP_PATH`/PATH, sem segredo); log técnico registra etapa + tipo/mensagem da exceção |
| Utilitário retorna erro | Mesma mensagem genérica | Mantém "O utilitário de dump retornou erro." + log técnico com exit code e stderr sanitizado |
| Timeout | "excedeu o tempo limite." | Inalterado |
| Qualquer outra falha | Descrições atuais | Inalteradas (ramo OSError/SubprocessError genérico permanece para casos remanescentes, p.ex. disco cheio) |

## 3. `_run_mysqldump` — ambiente e resolução do executável

| Aspecto | Contrato |
|---|---|
| Ambiente do subprocesso | `os.environ.copy()` + `MYSQL_PWD` (senha EXCLUSIVAMENTE no ambiente — FR-005). Nada de PATH fixo Unix |
| Executável | `MYSQLDUMP_PATH` configurado (falha clara se inexistente) → senão `shutil.which("mysqldump")` → senão `BackupError` "não encontrado" |
| Argumentos | Inalterados (`--single-transaction`, `--no-tablespaces`, `--host=`, `--port=`, `--user=`, database) — senha NUNCA em argv |
| stdout/stderr | Inalterado (stdout→arquivo, stderr capturado e NUNCA propagado ao usuário) |
| Log técnico em falha | NOVO: etapa "dump", tipo/mensagem da exceção, exit code (quando houver), stderr sanitizado por `_sanitize_stderr` (replace da senha + trunc 500) |
| Timeout | `_DUMP_TIMEOUT_SECONDS` (600s) inalterado |

## 4. `_run_mysql_import` (feature 017) — paridade mínima

| Aspecto | Contrato |
|---|---|
| Ambiente do subprocesso | Mesma correção (herdado + `MYSQL_PWD`) — sem isso a restauração ficaria quebrada no Windows após o dump voltar a funcionar |
| Executável `mysql` | Derivado de `MYSQLDUMP_PATH` (mesmo `bin`, R4) → senão `shutil.which("mysql")` → senão `BackupError` "não encontrado" |
| Streaming/validação pós-restore/auditoria/017 | Inalterados |

## 5. Rotas/telas (`admin_routes.py`, templates) — invariante

Nenhuma mudança. A tela exibe as mensagens `BackupError` como hoje (redirect com
`error=...`), agora com as duas mensagens distintas.

## 6. Documentação (Princípio XI)

| Arquivo | Contrato |
|---|---|
| `README.md` | §Backup ganha parágrafo: requisito do utilitário no PATH ou `MYSQLDUMP_PATH` no `.env` (exemplo Windows XAMPP), sem segredos |
| `docs/ARQUITETURA_E_MANUTENCAO.md` | Registro da variável + do log técnico de diagnóstico do backup (onde seções análogas existem) |

## 7. Garantias de não-regressão

1. Linux: fallback `shutil.which` reproduz a resolução atual (ambiente herdado ⊇ PATH fixo) — Teste F.
2. Suíte existente de backup (015/016/017) permanece verde com executores FAKE.
3. Nenhum argv novo contendo senha; nenhum log novo contendo senha (Teste H).
4. `MYSQLDUMP_PATH` ausente em um servidor Linux saudável: comportamento idêntico ao atual.
5. Nenhuma mudança em models/migrations/permissões/rotas/templates.
