# Research: Restauração Segura de Backup

**Feature**: 017-restauracao-segura-backup | **Data**: 2026-09-17
**Entrada**: spec.md + análise de código verificada (nada presumido)

> Todas as decisões foram verificadas contra o código real e o ambiente (arquivos/linhas citados). Nenhuma dependência nova é introduzida.

---

## R1. Import do dump — cliente nativo `mysql` via subprocesso (§17)

**Decisão**: o restore importa o dump com o cliente nativo **`mysql`** (MariaDB 10.6.23, `/usr/bin/mysql` — verificado) em subprocesso, lendo o dump **descomprimido por streaming do Python** (o Python abre o gzip e escreve no stdin do subprocesso). Mesmo padrão da geração (subprocesso + `stdout/stderr` controlados + timeout).

**Rationale**: o utilitário é o mecanismo apropriado para importar dumps (§17 veda "comandos SQL improvisados"); a descompressão no lado Python reutiliza a stdlib (zero dependência de `gunzip` no PATH) e evita pipelines de shell (§18 veda shell). Para `.sql` legados, o arquivo é lido diretamente. Credenciais derivadas de `DATABASE_URL` em memória, **senha exclusivamente via `MYSQL_PWD`** no ambiente do subprocesso (mesmo padrão de `_run_mysqldump`, research da 015) — nunca em argv/logs/erros.

**Alternativas rejeitadas**: `mariadb` client (equivalente, mesmo comportamento — `mysql` já está no PATH e é o binário canônico do MariaDB 10.6 no Debian); executar SQL via SQLAlchemy (improvisado, sem garantias de import de dump com `SET`, procedures de sessão e múltiplos statements — vedado).

## R2. Executor injetável para testes (§36, precedentes 015/016)

**Decisão**: o import fica encapsulado em **uma função de módulo** (`_run_mysql_import`), injetável via parâmetro `import_executor` nas funções de service e substituível por **monkeypatch** nos testes web — espelhando `_run_mysqldump` (remediação U1 da 015).

**Rationale**: a suíte roda em SQLite (sem cliente MariaDB) — a validação real do import nativo fica no quickstart §3 (MariaDB), como consolidado nas features 015/016.

## R3. Backup de segurança pré-restore = `generate_backup` existente (§14/§15)

**Decisão**: o backup de segurança é gerado chamando o **`generate_backup` existente** (mesmo executor, mesmo diretório, mesmo padrão de nome, auditoria `BACKUP_CRIADO` própria) imediatamente antes do import. O evento adicional `BACKUP_PRE_RESTORE_CRIADO` registra o **papel** do artefato (new_data referencia o arquivo do backup de segurança + o backup sendo restaurado) — sem duplicar geração, sem tabela, sem second store.

**Rationale**: §4/§15 exigem reutilizar o mecanismo da Feature 1. A auditoria da Feature 1 registra a geração (imutável, apensável); o evento novo do restore liga os dois artefatos (restaurado ↔ segurança) sem alterar o formato.

**Identificabilidade (§15/§28/FR-12)**: o operador identifica o backup de segurança pela trilha de auditoria (evento + `resource_ref`) e pela proximidade temporal na listagem; o nome mantém o padrão estrito da Feature 1 (a regex não pode ser estendida sem quebrar compatibilidade — evitar prefixos alternativos que exigiriam mudar `_BACKUP_NAME_RE` e revalidar tudo).

## R4. Validação do backup selecionado (§8) — composição das primitivas existentes

**Decisão**: a validação compõe funções já existentes: `get_backup_path(filename)` (regex estrita + existência → bloqueia path traversal e `.part*`), entrada da `list_backups()` (integridade) e uma **leitura de teste do gzip/dump** (gzip legível integralmente OU `.sql` com conteúdo SQL reconhecível). Critérios: existe → no diretório autorizado → formato reconhecido → tamanho > 0 → integridade ≠ CORROMPIDO → legível.

**Rationale**: §8 lista exatamente esses critérios; `integrity == "CORROMPIDO"` já é calculado pela 016 (leitura integral gzip); `—` (`.sql` legado, sem checksum) é restaurável com validação de legibilidade (spec Assumption 4).

## R5. Confirmação em duas etapas via padrão GET→POST existente (§11–§13)

**Decisão**: 3 rotas novas em `admin_routes.py`, todas com `require_permission("backup.restaurar")`:
1. `GET /admin/backups/{filename}/restaurar` — tela de informações + advertência (não executa nada; §10);
2. `POST /admin/backups/{filename}/restaurar` — confirmação explícita (executa o ciclo completo; §13 operação de escrita);
3. o botão de confirmação usa `confirm()` (padrão JS já usado em "Gerar backup" no mesmo template) + estado de processamento no submit (§12).

**Rationale**: padrão `GET (form) → POST (ação)` consolidado em `admin_routes.py` (ex.: users/new, roles/new); nunca GET para executar (§13); modal de duas etapas no template existente, sem página paralela.

## R6. Bloqueio de concorrência em memória do processo (§20/§21)

**Decisão**: flag de módulo em `backup_service.py` (`_RESTORE_IN_PROGRESS`, guardada com `threading.Lock` — stdlib, sem dependência) marcada durante todo o ciclo (backup de segurança → import → validação). Restore concorrente → rejeição com mensagem clara; **geração de backup manual também bloqueada** durante o restore (FR-17). Liberação em `finally` (sucesso ou falha).

**Rationale**: uvicorn roda **processo único** com `reload=False` (verificado em `run.py`) — não há segundo processo para competir; threads do event loop justificam lock (async handlers síncronos rodam em threadpool do Starlette). Solução mínima compatível com a arquitetura; filas/infraestrutura complexa são vedadas (§20). Limitação documentada: múltiplos workers no futuro exigirão revisão (spec Assumption 2).

## R7. Validação pós-restore real (§24/§25)

**Decisão**: após o import, o service valida pela **sessão SQLAlchemy do banco alvo**: (1) `SELECT 1` executável; (2) existência das tabelas essenciais (`users`, `permissions`, `roles`, `assets`, `custodians`, `locations`, `movements`, `maintenance`, `inventarios`, `audit_logs` — via consulta a `information_schema.tables` ou equivalente ORM); (3) consultas somente-leitura de contagem nos dados essenciais (usuários, bens, colaboradores). Qualquer falha → `BACKUP_RESTORE_FALHA` (nunca sucesso).

**Rationale**: §24 veda sucesso "apenas porque o comando retornou 0"; §25 exige validação somente-leitura compatível com a estrutura real. A lista de tabelas é derivada dos models existentes (17 tabelas confirmadas no dump da validação da 015/016).

## R8. Sessões e pool — comportamento natural documentado (§22/§23)

**Decisão**: nenhuma invalidação programática de sessões nem reconstrução de pool. Sessões são server-side no banco (`user_sessions`, hash do token — verificado em `session_service.py`): restaurar um backup faz os tokens posteriores ao backup deixarem de existir (cookies invalidam naturalmente) e sessões contemporâneas voltarem a valer. O pool (`pool_pre_ping=True`) se mantém — o cliente `mysql` atua no mesmo database/servidor; conexões SQLAlchemy permanecem válidas. A tela de confirmação documenta esse comportamento (FR-18).

**Rationale**: §22 veda invalidar arbitrariamente sem necessidade; §23 veda criar mecanismo de cache novo (não há cache de domínio — verificado). Durante o restore em si, a flag de concorrência (R6) impede outro restore/backup; requisições comuns são atômicas por transação.

## R9. Permissão `backup.restaurar` distinta (§32/§33)

**Decisão**: nova entrada no catálogo (`{"name": "backup.restaurar", "module": "Backup", ...}`) ao lado de `backup.gerenciar` (linha 85 de `permission_service.py`) — seed idempotente `ensure_default_roles` concede ao Administrador automaticamente. Rotas do restore exigem **somente** `backup.restaurar`.

**Rationale**: restaurar sobrescreve todos os dados (inclusive usuários/permissões) — impacto maior que gerar backup; separar permite delegar backup sem delegar restore (spec Assumption 1). Ação na UI condicionada a `can('backup.restaurar')` (padrão `base.html`).

## R10. Auditoria: 4 eventos aditivos + ACESSO_NEGADO existente (§30/§33)

**Decisão**: constantes novas em `audit_service.py` (padrão da 016): `ACTION_BACKUP_RESTORE_STARTED = "BACKUP_RESTORE_INICIADO"`, `ACTION_BACKUP_PRE_RESTORE = "BACKUP_PRE_RESTORE_CRIADO"`, `ACTION_BACKUP_RESTORE_SUCCESS = "BACKUP_RESTORE_SUCESSO"`, `ACTION_BACKUP_RESTORE_FAILED = "BACKUP_RESTORE_FALHA"` + rótulos ("Restauração Iniciada", "Backup Pré-Restore Criado", "Restauração Concluída", "Restauração Falhou"). `new_data` contém apenas `{backup, backup_seguranca, motivo?}` — sem segredos. Tentativas sem permissão seguem auditadas pelo mecanismo existente de acesso negado (403).

**Rationale**: trilha única imutável (Constitution IX); eventos literais do §30; nada de segundo mecanismo.

## R11. Compatibilidade `.sql`/`.sql.gz` (§35)

**Decisão**: o import aceita ambos os formatos da Feature 1 via a mesma `_BACKUP_NAME_RE` existente (`.sql` lido direto; `.sql.gz` descomprimido em streaming) — sem alterar a regex nem o formato. Arquivo ilegível → rejeição segura (FR-28), extensão correta não basta.

**Rationale**: §35 (backups existentes continuam válidos) + testes de compatibilidade consolidados na 016.

## R12. Mensagens e estados de falha (§26/§27/§29)

**Decisão**: falha em qualquer etapa → descrição **segura e controlada** (sem stderr bruto do cliente — pode conter host/credenciais; mesma disciplina de `_run_mysqldump`), evento `BACKUP_RESTORE_FALHA`, backup de segurança **nunca removido**, mensagem ao usuário orientando a restauração manual do backup de segurança se a falha foi no meio do import (estado parcial possível). Sucesso → mensagem com os dois arquivos (restaurado + segurança), conforme §29.

**Rationale**: §26 veda falso sucesso; §27 veda rollback automático complexo (spec Assumption 5); §29 define a mensagem de sucesso.
