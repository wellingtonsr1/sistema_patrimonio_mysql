# Feature Specification: Backup Manual do SisPatrimônio Pro (Briefing Completo — Consolidação da 015)

**Feature Branch**: `016-backup-manual-completo`

**Created**: 2026-09-17

**Status**: Draft

**Input**: Briefing completo de "Backup Manual do SisPatrimônio Pro" (seções 4–40): análise obrigatória pré-implementação (banco, arquivos persistidos), conteúdo do backup, tipo/estratégia compatível com o banco real, armazenamento seguro, configuração, credenciais, nomenclatura, compressão, integridade (SHA-256), interface, criação, concorrência, download protegido, RBAC, administrador, auditoria, log técnico, proteção contra falhas (arquivo temporário → renomear), sem retenção/restauração/agendamento, testes A–J, critérios de aceitação, regra de mínima alteração e relatório final obrigatório.

---

## 0. Situação de partida — o que JÁ EXISTE (feature 015, em produção)

A análise somente-leitura **obrigatória** (seção 5/6 do briefing) foi realizada e o resultado central é: **a feature 015 já implementou a maior parte do briefing** e está em produção (commit `2abc1a4`). Esta especificação documenta o que existe, o que o briefing acrescenta e delimita **apenas o incremento necessário**.

### 0.1 Análise obrigatória (seções 5, 6, 7, 32, 33 do briefing) — fatos verificados

| # | Ponto do briefing | Realidade verificada no código/ambiente |
|---|---|---|
| 1 | Banco configurado (§6) | **MariaDB/MySQL** é o banco definitivo (`DATABASE_URL=mariadb+pymysql://...` em `.env`; `app/config.py` sem fallback SQLite na aplicação — Constitution VII). O driver é PyMySQL; conexão via `app/database.py` (SQLAlchemy engine); inicialização via `init_db()`/`ensure_default_roles()` no startup (`app/main.py`); schema criado/migrado de forma aditiva e idempotente (`_ensure_schema_migrations`) |
| 2 | Artefato SQLite encontrado (§7) | `data/patrimonio.db` (436 KB) **existe no disco mas NÃO é referenciado por nenhum código/config** (`grep` sem ocorrências em app/, run.py, .env); é resquício de desenvolvimento/análise. Classificação §7: **arquivo de desenvolvimento** — deliberadamente EXCLUÍDO do backup |
| 3 | Arquivos persistidos (§7) | Varredura de gravação em `app/`: **nenhum upload/anexo/documento/foto/termo é persistido em filesystem** — exportações (xlsx/pdf/csv) são geradas em memória e enviadas na resposta; termos PDF idem. Únicos artefatos de runtime: `data/logs/` (logs técnicos rotativos) e `data/backups/` (criado pela feature 015) |
| 4 | Conclusão do conteúdo (§8) | **Backup = dump consistente do banco** (todos os dados persistidos: usuários, perfis, permissões, colaboradores, bens, locais, movimentações, manutenções, inventários, auditoria, config AD persistida). **Nenhum arquivo externo ao banco precisa entrar** — não há dados da aplicação fora do banco |
| 5 | Estratégia (§9) | Dump **lógico** via utilitário nativo MariaDB (`mysqldump`/`mariadb-dump`, presentes: `/usr/bin/`) com `--single-transaction --no-tablespaces` (feature 015, research R1) |
| 6 | Metadados no banco (§10) | NÃO criados — listagem derivada dos arquivos (zero DDL) |
| 7 | Armazenamento (§11) | `data/backups/` (fora de `/static/`, não servido publicamente, acesso somente via rota autorizada) |
| 8 | Configuração (§12) | `BACKUP_DIR = DATA_DIR / "backups"` em `app/config.py` — sem variável de ambiente (diretório derivado do `DATA_DIR` existente); nenhuma senha em código |
| 9 | Credenciais (§13) | Derivadas de `DATABASE_URL` em memória; senha **exclusivamente** via `MYSQL_PWD` no ambiente do subprocesso — nunca em argv, logs, auditoria, interface |
| 10 | Nomenclatura (§14) | `backup_AAAAMMDD_HHMMSS_micros.sql` — identifica sistema/data/hora, sem nomes aleatórios; usuário não informa nome/caminho |
| 11 | Compressão (§15) | **Não implementada** na 015 (`.sql` puro). O briefing pede **avaliação** — ver incremento I2 |
| 12 | Integridade (§16) | Parcial: processo sem erro + arquivo existe + tamanho > 0. **SHA-256 não implementado** — ver incremento I2 |
| 13 | Interface (§17/§18) | Administração → **Backups** (`admin/backups.html`) com botão "Gerar backup", listagem (Data/Hora UTC, Tamanho, Baixar), tema claro/escuro e componentes existentes preservados |
| 14 | Criação (§19) | Autorização → geração → validação → armazenamento → auditoria → resultado; erro com **mensagem segura** (sem senha/stack trace) |
| 15 | Concorrência (§20) | Nomes únicos por microssegundos — nenhum backup sobrescreve outro (BV-3) |
| 16 | Download (§21/§22) | Rota `GET /admin/backups/{filename}/download` protegida; regex estrita impede path traversal/`../`/caminhos arbitrários; diretório não servido estaticamente |
| 17 | RBAC/Administrador (§23/§24) | Permissão única `backup.gerenciar` no catálogo (deny-by-default); seed idempotente concede ao perfil Administrador existente; bypass `is_admin` preservado — sem lógica paralela |
| 18 | Auditoria (§25) | Eventos `BACKUP_CRIADO` (SUCCESS/FAILURE) e `BACKUP_DOWNLOAD` via `write_audit` — **sem evento de início** e sem rótulo de ação `BACKUP_FALHA` (a falha usa `BACKUP_CRIADO`+`result=FAILURE`, equivalente funcional) — ver incremento I1 |
| 19 | Log técnico (§26) | **Não instrumentado** — o service não registra diagnóstico técnico em `data/logs/` — ver incremento I3 |
| 20 | Proteção contra falhas (§27) | Falha não é sucesso; artefato parcial removido. **Padrão temporário→renomear não implementado** — ver incremento I2 |
| 21 | Retenção/Restore/Agendamento (§28/§29/§30) | **NÃO implementados** (correto — exatamente o exigido) |
| 22 | Banco (§31) | Nenhuma alteração estrutural (correto) |
| 23 | Testes (§34) | Suíte 015 cobre A–I parcialmente; gaps: teste H (múltiplos backups **web**), teste I (checksum — depende do incremento) — ver incremento T |

### 0.2 Incrementos necessários (gap 015 → briefing completo)

| ID | Incremento | Origem no briefing | Valor |
|---|---|---|---|
| **I1** | Evento de auditoria de falha com rótulo próprio `BACKUP_FALHA` (mantendo `BACKUP_CRIADO` p/ sucesso) + rótulos de exibição | §25 (evento BACKUP_FALHA com resultado FALHA) | Aderência literal ao modelo de eventos do briefing |
| **I2** | **Compressão gzip** (`.sql.gz` via `mysqldump --single-transaction ... \| gzip` ou gzip pós-dump em arquivo temporário) + **SHA-256** calculado após a conclusão + **padrão temporário→renomear** (arquivo `.part` durante a geração; renomeado ao final — nunca há parcial listável) + exibição de Integridade (OK) e SHA-256 na listagem | §15, §16, §27 | Prioridade do briefing: backup válido + integridade + simplicidade + restaurabilidade |
| **I3** | Instrumentação do **log técnico existente** (`logging` rotativo `data/logs/`) para diagnóstico de falhas — sem credenciais | §26 | Diagnóstico sem poluir a auditoria |
| **T** | Completar testes: H (múltiplos backups via web, nenhum sobrescreve), I (checksum SHA-256 correto; arquivo legível), F (path traversal já coberto — reforço), G (falha → `BACKUP_FALHA`, sem falso sucesso, sem parcial) | §34 | Cobertura literal dos testes obrigatórios |

**Fora do gap (já atendido pela 015 — NÃO reimplementar)**: banco/estratégia/armazenamento/RBAC/administrador/download/segurança/fluxo/interface/concorrência/nomenclatura/auditoria de sucesso/download/sem-restore/sem-agendamento/sem-retenção/zero-DDL.

---

## 1. Conteúdo do backup — INCLUSÕES e EXCLUSÕES deliberadas (§8, obrigatoriedade do briefing)

### Incluído no backup

- **Dump lógico completo do banco MariaDB** (`--single-transaction`): todos os dados persistidos do sistema — usuários, perfis e permissões; colaboradores; bens/equipamentos; categorias; locais e departamentos; movimentações; manutenções; inventários e conferências; trilha de auditoria; configurações persistidas (Integração AD); relacionamentos — ou seja, **todo o schema e dados**, necessários e suficientes para uma futura restauração.

### Excluído deliberadamente (com classificação §7)

| Item | Classificação | Motivo |
|---|---|---|
| `data/patrimonio.db` (SQLite 436 KB) | Arquivo de desenvolvimento | Não referenciado por código/config algum; o banco definitivo é MariaDB |
| `data/logs/` (app.log, app.error.log) | Logs técnicos | Explorados pelo próprio briefing (§7); diagnóstico, não estado |
| `data/backups/` | Backups anteriores | Não são dados do sistema; incluir geraria crescimento exponencial |
| `.git`, `.venv`, `__pycache__` | Desenvolvimento/cache | Não são dados persistidos |
| Estáticos (`app/web/static/`) | Arquivos da aplicação | Código, não dados |
| Uploads/anexos/fotos | **Inexistentes** | A varredura confirmou: a aplicação não persiste arquivos fora do banco — não inventar (§8) |

**Conclusão formal**: o backup contém **exatamente o dump do banco** — isso preserva o estado integral dos dados do sistema (não há nenhum outro dado persistido).

---

## 2. Problema e objetivo

### Problema

A feature 015 entregou o mecanismo essencial (gerar/listar/baixar com auditoria e segurança), mas o briefing completo exige camadas que faltam: integridade verificável (SHA-256), compressão, padrão temporário→renomear (zero arquivo parcial), evento de falha com rótulo literal, log técnico de diagnóstico e cobertura de testes literal (A–J).

### Objetivo

Completar o mecanismo de backup manual do SisPatrimônio Pro **sem alterar o que já funciona**: `BackupService` passa a produzir backups comprimidos (`.sql.gz`), íntegros (SHA-256 exibido), atomicamente gerados (temporário→renomear), com falhas auditadas como `BACKUP_FALHA` e diagnóstico no log técnico — preservando integralmente rota, tela, permissão, RBAC, download e os demais módulos.

---

## 3. User Scenarios & Testing

### User Story 1 — Gerar backup comprimido e íntegro (Priority: P1) 🎯 MVP

**Independent Test**: Usuário autorizado gera → arquivo `.sql.gz` único, com SHA-256 calculado, listado com Integridade OK; nenhuma janela com arquivo parcial.

**Acceptance Scenarios**:

1. **Given** administrador autorizado, **When** cria backup, **Then** o processo executa em arquivo temporário e ao final renomeia para o nome definitivo — em nenhum momento existe parcial listável (§27).
2. **Given** backup concluído, **When** consultado, **Then** apresenta data/hora (UTC), tamanho, **SHA-256** e status de integridade **OK** (§16, §18).
3. **Given** o formato `.sql.gz`, **When** descompactado, **Then** o conteúdo é um dump SQL MariaDB válido, restaurável futuramente (§38).

### User Story 2 — Falha auditada e diagnosticada, sem falso sucesso (Priority: P1)

**Independent Test**: Executor falha → `BACKUP_FALHA` na auditoria, mensagem segura ao usuário, parcial removido, detalhe técnico no log — nunca sucesso (§19, §25, §26, §27).

**Acceptance Scenarios**:

1. **Given** falha do utilitário de dump, **When** o processo termina com erro, **Then** a operação é registrada como `BACKUP_FALHA` (resultado FALHA), o usuário vê "Backup não concluído" com motivo seguro e **nenhum** arquivo fica disponível.
2. **Given** a falha, **When** diagnosticada, **Then** o log técnico (`data/logs/`) contém o detalhe técnico **sem** credenciais (§26).

### User Story 2b — Acesso e download seguros (Priority: P1)

**Independent Test**: Matriz autorizado/não-autorizado × listar/gerar/baixar; path traversal bloqueado; 404 sem tocar disco — comportamento da 015 **preservado** (regressão).

### User Story 3 — Listagem e múltiplos backups (Priority: P2)

**Independent Test**: Vários backups coexistem com nomes únicos; listagem ordenada com Integridade OK; nenhum sobrescreve outro.

---

## 4. Edge Cases

- **`gzip` indisponível no PATH** (§32: não assumir ferramenta externa): a compressão pós-dump usa o módulo **Python `gzip`** (stdlib, sempre disponível) — nenhuma dependência externa nova; `mysqldump` continua pré-requisito documentado, com erro controlado se ausente (já implementado na 015).
- **Disco cheio durante a geração**: exceção → falha auditada (`BACKUP_FALHA`), `.part` removido, mensagem segura.
- **Dois backups simultâneos**: nomes com microssegundos distintos; cada processo grava o **seu** `.part` (nome único) e renomeia ao final — sem colisão possível (§20).
- **Arquivo renomeado/removido manualmente**: listagem deriva do disco; download inexistente → 404 (BV-1 da 015).
- **DUMP muito grande**: compressão em streaming (blocos) — sem carregar o dump inteiro em memória.
- **Checksum no nome não**: SHA-256 fica **junto ao registro de auditoria e à tela** (derivável do arquivo) — não no nome (nome identificável por sistema/data/hora, §14).

## 5. Requirements

### Functional Requirements

- **FR-001**: A geração DEVE produzir arquivo temporário (sufixo interno `.part` com o mesmo nome-base único) e **renomear para o nome definitivo somente após a conclusão validada** — em nenhum momento um arquivo parcial é listável ou baixável (§27).
- **FR-002**: O backup DEVE ser comprimido em **gzip** (`.sql.gz`), em streaming, utilizando mecanismo sempre disponível no ambiente (stdlib Python), sem dependência externa adicional (§15).
- **FR-003**: Após a conclusão, o sistema DEVE calcular o **SHA-256** do arquivo e registrá-lo na auditoria (evento de sucesso) e na listagem (§16).
- **FR-004**: A listagem DEVE apresentar, para cada backup: data/hora (UTC), tamanho, **SHA-256** (quando disponível — backups antigos `.sql` da 015 podem não ter) e coluna **Integridade** com status **OK** quando o checksum casa e o arquivo é legível (§18).
- **FR-005**: A falha de geração DEVE ser registrada na auditoria com o evento **`BACKUP_FALHA`** (resultado FALHA, descrição segura), mantendo `BACKUP_CRIADO` para sucesso (§25).
- **FR-006**: O log técnico existente DEVE receber o diagnóstico da geração (início, conclusão com duração/tamanho, falhas com exceção) — **sem** credenciais/segredos (§26).
- **FR-007**: O formato DEVE permanecer restaurável: gzip com dump SQL lógico MariaDB dentro (§38) — sem mecanismo proprietário.
- **FR-008**: Tudo o que já funciona na 015 DEVE permanecer: permissão `backup.gerenciar` (deny-by-default), rotas protegidas, anti-path-traversal, 404 seguro, nomenclatura por data/hora única, `data/backups/`, zero DDL, sem restore/agendamento/retenção (§§10, 11, 20–24, 28–31).
- **FR-009**: O briefing §7/§8 exige conteúdo documentado: backup contém **apenas** o dump do banco (análise formalizada na Seção 1) — nada incluído indiscriminadamente, nada inventado.
- **FR-010**: Os testes obrigatórios A–J do §34 DEVEM estar cobertos e passando (A autorizado; B não-autorizado; C/D download; E inexistente; F path traversal; G falha sem falso sucesso; H múltiplos sem sobrescrever; I integridade/checksum; J regressão).

### Regras (síntese)

- R1 — Menor alteração possível sobre a 015: incrementos localizados no `BackupService`, rota de download (servir gzip), tela (colunas Integridade/SHA-256) e constantes (`BACKUP_FALHA`).
- R2 — Prioridade §15: backup válido + integridade + simplicidade + restaurabilidade.
- R3 — Nenhuma das proibições das seções 4/28/29/30/31: sem restore, sem agendamento, sem retenção, sem alteração de banco/ORM/modelos/regras.

## Key Entities

- **Arquivo de backup (v2)**: `backup_AAAAMMDD_HHMMSS_micros.sql.gz` (+ variação `.part` interna durante a geração, sempre com nome-base único). Metadados derivados do arquivo: timestamp (UTC), tamanho, SHA-256.
- **Constantes de auditoria**: `BACKUP_CRIADO` (sucesso), **`BACKUP_FALHA`** (novo), `BACKUP_DOWNLOAD` — na trilha existente, sem mecanismo paralelo.
- **Compatibilidade**: backups `.sql` não-comprimidos gerados pela 015 continuam listáveis/baixáveis (transição suave).

## 6. Critérios de Aceitação (rastreabilidade — checklist §35)

| AC | Enunciado (§35) | Coberto por |
|---|---|---|
| AC-01 | Sistema permite criar backup manual | US1/AS1; FR-008 (015) |
| AC-02 | Somente autorizados criam | US2b; FR-008 |
| AC-03 | Backup representa os dados persistidos atuais | Seção 1 (dump completo do banco); FR-009 |
| AC-04 | Banco identificado antes da implementação | Seção 0.1 (MariaDB/MySQL + PyMySQL) |
| AC-05 | Estratégia compatível com o banco real | Seção 0.1 (dump lógico nativo); FR-007 |
| AC-06 | Arquivos persistidos identificados antes | Seção 0.1/1 (nenhum fora do banco) |
| AC-07 | Temporários/desnecessários não incluídos | Seção 1 (exclusões deliberadas); FR-009 |
| AC-08 | Backup fora de diretório público | FR-008 (015: `data/backups/`) |
| AC-09 | Nome identificável | FR-008 (§14) |
| AC-10 | Backups não se sobrescrevem | US3; FR-008 (microssegundos) |
| AC-11 | Resultado validado | US1/AS2; FR-003/FR-004 |
| AC-12 | Falhas ≠ sucesso | US2/AS1; FR-005 |
| AC-13 | Download exige autorização | US2b; FR-008 |
| AC-14 | Path traversal bloqueado | US2b; FR-008 |
| AC-15 | Auditoria existente utilizada | US2/AS1; FR-005 |
| AC-16 | Senhas/segredos não registrados | US2/AS2; FR-006 |
| AC-17 | Logging existente preservado | FR-006 |
| AC-18 | Nenhuma restauração | FR-008 (§29) |
| AC-19 | Nenhum agendamento | FR-008 (§30) |
| AC-20 | Nenhuma retenção automática | FR-008 (§28) |
| AC-21 | Arquitetura do banco inalterada | FR-008 (§31); zero DDL |
| AC-22 | Dados patrimoniais inalterados | FR-008 |
| AC-23 | RBAC existente preservado | FR-008 (§23/§24) |
| AC-24 | Testes existentes passando | FR-010 (Teste J) |
| AC-25 | Testes de backup executados | FR-010 (A–I) |
| AC-26 | Backup adequado para futura restauração | US1/AS3; FR-007 |
| AC-27 | Nenhum módulo não relacionado alterado | Regra de mínima alteração (R1) |

## 7. Success Criteria

- **SC-001**: 100% dos novos backups são `.sql.gz` com SHA-256 calculado e exibido; 0 arquivos parciais listáveis em qualquer ponto do fluxo.
- **SC-002**: Falha de geração → evento `BACKUP_FALHA` + diagnóstico no log técnico + mensagem segura; 0 falsos sucessos.
- **SC-003**: Testes A–J cobertos e verdes; suíte completa verde (exceto baseline pré-existente RBAC lockout).
- **SC-004**: Backups `.sql` da 015 continuam listáveis/baixáveis (compatibilidade de transição).
- **SC-005**: `git diff` restrito a `backup_service.py`, `audit_service.py` (+1 constante/rótulo), `admin/backups.html` (colunas), `tests/test_backup_manual.py`, `README.md`, `help_service.py` (docs — remediação I2) — rota web de download/geração sem alteração (servir arquivo é agnóstico a gzip).

## 8. Escopo

### Incluído

- Incrementos I1 (BACKUP_FALHA), I2 (gzip + SHA-256 + temporário→renomear + colunas de Integridade), I3 (log técnico) e T (testes A–J) sobre a base da 015;
- Documentação fiel do conteúdo do backup (inclusões/exclusões da Seção 1) no README/ajuda;
- Compatibilidade de transição com backups `.sql` antigos.

### Não incluído (proibições literais do §4 — exaustivo)

Restauração (automática/manual/botão/recuperação) · agendamento/backup periódico/cron/scheduler/tarefas em segundo plano · política automática de retenção/exclusão automática · replicação/nuvem/S3/Google Drive/OneDrive/NAS · alteração de arquitetura do banco/migração/novo banco/substituição de banco/ORM/modelos patrimoniais/regras de negócio existentes.

## 9. Casos de erro (§19/§27 — comportamento definido)

| Situação | Comportamento |
|---|---|
| Utilitário de dump ausente/falha (exit ≠ 0) | `BACKUP_FALHA` + "Backup não concluído" com motivo seguro + `.part` removido + detalhe no log técnico |
| Disco cheio/erro de escrita no `.part` | idem acima |
| Arquivo vazio após dump | Falha (já na 015) + `BACKUP_FALHA` |
| Erro na compressão/checksum | Falha; o `.part` é removido; nada é listado |
| Download de inexistente/fora do padrão | 404 seguro (015, preservado) |
| Sem permissão | 403 auditado (015, preservado) |

## 10. Premissas e dependências

- `mysqldump`/`mariadb-dump` presentes (verificado: `/usr/bin/`); **`gzip` não é requisito externo** — compressão via stdlib Python (§32: não assumir ferramenta; não instalar software pela aplicação).
- Backups antigos `.sql` da 015: SHA-256 não retroativo (coluna Integridade exibe "—" para eles; download permanece).
- Ambiente real: Linux (Uvicorn via `run.py`); execução como usuário comum — o backup exige apenas permissões de leitura do banco (via credenciais de `DATABASE_URL`) e escrita em `data/backups/` (nenhum privilégio de SO adicional — §33).

## 11. Impacto esperado (componentes confirmados — nada inventado)

| Arquivo | Alteração |
|---|---|
| `app/services/backup_service.py` | Núcleo dos incrementos: `.part`→renomear, gzip streaming, SHA-256, evento `BACKUP_FALHA`, log técnico |
| `app/services/audit_service.py` | +1 constante `ACTION_BACKUP_FAILED = "BACKUP_FALHA"` + rótulo de exibição |
| `app/web/templates/admin/backups.html` | Colunas Integridade e SHA-256 (truncado) na listagem; textos |
| `tests/test_backup_manual.py` | Testes H/I/G literais + ajustes do formato gzip |
| `README.md` + `help_service.py` | Conteúdo do backup (inclusões/exclusões), `.sql.gz`, SHA-256 |
| Rotas web, permissão, RBAC, banco, demais módulos | **INTOCADOS** |

---

*Esta especificação cumpre a ANALISE OBRIGATÓRIA do briefing (seções 5–8): banco identificado (MariaDB/MySQL + PyMySQL), arquivos persistidos varridos (nenhum fora do banco; `data/patrimonio.db` classificado como resquício de desenvolvimento), conteúdo do backup definido com inclusões/exclusões explícitas — e delimita a menor alteração possível (seção 36) sobre a feature 015 já em produção.*
