# Research: Backup Manual do SisPatrimônio Pro

**Feature**: 015-backup-manual | **Data**: 2026-09-17
**Entrada**: spec.md + verificação de código e ambiente (ferramentas e arquivos citados confirmados)

---

## R1. Mecanismo de dump: utilitário nativo do SGBD (`mysqldump`/`mariadb-dump`)

**Decisão**: a geração do backup executa o utilitário nativo do banco de produção via subprocesso.

**Rationale**: o servidor já dispõe de `/usr/bin/mysqldump` e `/usr/bin/mariadb-dump` (verificado no ambiente). É o mecanismo consistente com o README (backups operacionais do MariaDB/MySQL), produz um dump SQL textual consistente, independentemente do ORM — **sem nenhuma dependência Python nova**. Alternativas rejeitadas: (a) dump via SQLAlchemy (itere tabelas e serializar) — reinventaria o utilitário, risco de inconsistência transacional e código novo não-precedente; (b) `SELECT ... INTO OUTFILE` — requer FILE privilege e grava no servidor do banco, não da aplicação.

**Detalhe de execução (produção)**: `mysqldump --single-transaction --no-tablespaces <db>` → arquivo `.sql` em `data/backups/`. `--single-transaction` garante dump consistente sem travar o banco (InnoDB). O fluxo no banco de **teste** (SQLite) é simulado (R4) — a execução real só ocorre com MariaDB/MySQL.

---

## R2. Segurança das credenciais no subprocesso (Princípio VI)

**Decisão**: a senha do banco vai ao utilitário **exclusivamente pelo ambiente do subprocesso** (`env={"MYSQL_PWD": senha, ...}`), nunca em argv, logs, auditoria ou arquivos versionados. `user`/`host`/`db` são derivados de `DATABASE_URL` em memória.

**Rationale**: `mysqldump -pSENHA` na linha de comando expõe a senha na lista de processos (`ps`) — inaceitável pela Constitution. `MYSQL_PWD` é o mecanismo suportado pelo cliente MariaDB/MySQL e não aparece em `ps`. Em falha, o erro propagado ao usuário/auditoria é mensagem de status (código de saída + stderr resumido), **jamais** o comando completo.

**Alternativas rejeitadas**: option-file temporário (`--defaults-extra-file`) — válido, porém cria arquivo com credencial em disco que precisaria de limpeza garantida; `MYSQL_PWD` no ambiente do subprocesso atende sem artefatos residuais.

---

## R3. Armazenamento e identificação: `data/backups/` + timestamp com microssegundos

**Decisão**: diretório `data/backups/` (constante `BACKUP_DIR = DATA_DIR / "backups"` em `app/config.py`, criado on-demand); nome do arquivo `backup_YYYYMMDD_HHMMSS_micros.sql` (timestamp **UTC** com microssegundos — coerência com o padrão de datas do projeto, feature 004, e com a trilha de auditoria `datetime.utcnow()`; **remediação I1**: era "local", revisado para UTC).

**Rationale**: `DATA_DIR` é o padrão existente de artefatos de runtime (`data/logs/`); repositório dedicado separa backups de logs. Microssegundos no nome garantem unicidade em gerações repetidas na mesma operação (Edge Case da spec) e ordenação lexicográfica = cronológica. Nome padronizado permite à listagem reconhecer **apenas** artefatos desta funcionalidade (ignora arquivos alheios que o operador porventura deposite ali).

**Alternativas rejeitadas**: UUID no nome (não identificável por data/hora — FR-004); diretório fora de `data/` (quebraria o padrão existente).

---

## R4. Testabilidade: executor de dump isolado (SQLite nos testes)

**Decisão**: o subprocesso fica encapsulado em **uma função do service** (ex.: `_run_dump(path)`), única responsável por chamar o utilitário. Nos testes, essa função é substituída (monkeypatch/inyeção) para produzir conteúdo determinístico — o comportamento testado é o do service (criar arquivo, nomear, auditar, listar, servir download), não o do `mysqldump` em si.

**Rationale**: a suíte roda em SQLite em memória (conftest) — não há `mysqldump` aplicável. Testar o utilitário nativo seria teste de integração externa, fora do padrão da suíte. A validação real do dump nativo fica no quickstart §3 (ambiente com MariaDB), como roteiro manual.

**Alternativas rejeitadas**: simular banco MariaDB em container — infraestrutura nova proibida (sem dependências novas); testar `subprocess` real — frágil e dependente de ambiente.

---

## R5. Permissão nova: `backup.gerenciar` no `PERMISSION_CATALOG`

**Decisão**: uma única permissão cobre as três operações (gerar, listar, baixar). Registro aditivo em `PERMISSION_CATALOG` (`app/services/permission_service.py`), módulo "Backup": `{"name": "backup.gerenciar", "module": "Backup", "label": "Gerenciar backups", "description": "Gerar, listar e baixar backups manuais do sistema."}`.

**Rationale**: deny-by-default (Princípio VI); o seed idempotente existente (`ensure_default_roles` no startup — `app/main.py:31`) cadastra a permissão e a concede ao perfil **Administrador** automaticamente (o papel referencia todas as permissões do catálogo). Precedente de granularidade: `auditoria.visualizar` cobre toda a tela de auditoria — operações de backup são um bloco coeso de administração, não justificando 3 permissões separadas.

**Alternativas rejeitadas**: `backup.criar`/`backup.baixar` separadas — granularidade sem demanda no briefing, adicionando superfície de configuração sem valor.

---

## R6. Eventos de auditoria: constantes aditivas + `write_audit` existente

**Decisão**: duas constantes novas em `audit_service.py` (precedente: `ACTION_AD_CONNECTION_TESTED`/`ACTION_AD_SETTINGS_UPDATED`):
- `ACTION_BACKUP_CREATED = "BACKUP_CRIADO"` — `result=RESULT_SUCCESS` com `new_data={arquivo, tamanho_bytes}` ou `result=RESULT_FAILURE` com descrição do erro (sem detalhes sensíveis);
- `ACTION_BACKUP_DOWNLOAD = "BACKUP_DOWNLOAD"` — `new_data={arquivo}`.
Downloads NÃO falham auditavelmente (arquivo inexistente → 404 antes de qualquer evento — rota valida existência primeiro).

**Rationale**: Princípio IX — a trilha registra operações relevantes; importações CSV já são precedentes de eventos de funcionalidade. `write_audit` aceita `module`, `resource`, `result`, `new_data` — encaixe direto, sem mudança no audit_service além das constantes.

---

## R7. Listagem por repositório de arquivos (sem tabela nova)

**Decisão**: a listagem deriva do diretório `data/backups/` — varre arquivos que casam o padrão de nome (R3) e expõe `{filename, timestamp, size_bytes}` ordenado do mais recente para o mais antigo. Sem tabela, sem DDL, sem migration.

**Rationale**: a spec (Seção 10) já sinalizava esta opção; metadados requeridos pelo briefing (data/hora e tamanho) são atributos do próprio arquivo — persisti-los em banco introduziria estado duplicado e necessidade de sincronização (ex.: arquivo removido manualmente pelo operador ficaria "fantasma" na tabela). Zero DDL atende o Princípio VII.

**Alternativas rejeitadas**: tabela `backups` (estado duplicado, DDL desnecessário); include de arquivos alheios (confundiria o operador e exporia arquivos arbitrários ao download — risco de segurança).

---

## R8. Rotas na área Administração + item de menu

**Decisão**: router novo `backups_router` dentro de `admin_routes.py` (ou anexo a ele), rotas: `GET /admin/backups` (listagem + botão Gerar), `POST /admin/backups/gerar`, `GET /admin/backups/{filename}/download`. Todas com `Depends(require_permission("backup.gerenciar"))`. Template `admin/backups.html` nos padrões visuais existentes; item de menu em `base.html` dentro do bloco Administração com `can('backup.gerenciar')`.

**Rationale**: funcionalidade administrativa por natureza (mesma audiência de usuários/perfis/auditoria); `require_permission` + `require_web_auth` global cobrem Princípio VI; menu conforme permissões é o padrão (Princípio X). Download por **filename** validado contra o padrão de nome (R3) — impede path traversal (`../`) por construção (nome validado por regex estrita antes de qualquer acesso ao disco).

**Alternativas rejeitadas**: API REST adicional — o briefing é orientado à interface (o admin opera pela tela); download via POST/redirect — desnecessário (GET com permissão basta, precedentes de exportação).
