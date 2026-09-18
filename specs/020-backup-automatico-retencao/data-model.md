# Phase 1 — Data Model: Backup Automático e Política de Retenção

> Alteração de schema desta feature: **1 tabela NOVA** (`backup_records`), criada por `Base.metadata.create_all` em `init_db()` — aditiva, idempotente, zero `ALTER`, zero remoção (Constitution VII). Nenhuma tabela/coluna existente é alterada.

---

## 1. Nova entidade: `BackupRecord` (tabela `backup_records`)

Metadados determinísticos de cada backup gerado pelo sistema (briefing §13/§19). Um registro por tentativa de geração (sucesso ou falha).

| Coluna | Tipo | Constraints | Descrição |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | Identificador técnico |
| `filename` | VARCHAR(120) | NOT NULL, UNIQUE | Nome do arquivo gerado (padrão existente `backup_YYYYMMDD_HHMMSS_micros.sql.gz`) — liga o registro ao arquivo físico; nunca determina tipo sozinho. **Em FAILURE**: grava o nome FINAL projetado `{base}.sql.gz` (mesmo sufixo do sucesso — casa com `_BACKUP_NAME_RE`; sem colisão UNIQUE porque a geração falhou antes do rename e nenhum arquivo com esse nome existe; a geração seguinte tem timestamp com microssegundos distintos) |
| `backup_type` | VARCHAR(20) | NOT NULL | `MANUAL` \| `AUTOMATICO` \| `PRE_RESTAURACAO` (vocabulário controlado do serviço; paridade com `user_roles.assigned_by`) |
| `status` | VARCHAR(10) | NOT NULL | `SUCCESS` \| `FAILURE` |
| `timestamp` | DATETIME | NOT NULL, index | Início da geração — **UTC naive** (`now_utc()`, política da 004) |
| `size_bytes` | INTEGER | nullable | Tamanho do arquivo final (None em falha) |
| `sha256` | VARCHAR(64) | nullable | Hash do arquivo comprimido (None em falha) |
| `error_description` | VARCHAR(255) | nullable | Motivo da falha controlado (mesma mensagem segura da auditoria — nunca segredos) |
| `removed_at` | DATETIME | nullable | Quando o arquivo físico foi removido pela retenção (None = arquivo presente) — sustenta o §20/§33 (histórico preservado após remoção) |
| `removed_reason` | VARCHAR(40) | nullable | `RETENCAO_DIARIA` \| `RETENCAO_SEMANAL` \| `RETENCAO_MENSAL` \| `RETENCAO` (genérico) |
| `created_at` | DATETIME | default `now_utc()` | Criação do registro |

**Índices**: `ix_backup_records_timestamp` (`timestamp`), `ix_backup_records_type_status` (`backup_type`, `status`).

### Regras de validação (serviço, não banco)

- `backup_type` só aceita os 3 valores (função de normalização rejeita outro → `ValueError`);
- `filename` — tanto SUCCESS quanto FAILURE (nome final projetado) — só persiste se casa com `_BACKUP_NAME_RE` (âncora existente — proteção contra path traversal também nos metadados);
- Registro de FALHA nunca tem `size_bytes`/`sha256` (não há arquivo válido);
- `removed_at` só é preenchido pelo ciclo de retenção — nunca por download/restore.

### Transições de estado (ciclo de vida)

```text
                    generate_backup()
                          │
             ┌────────────┴─────────────┐
             ▼                          ▼
   [registro SUCCESS]           [registro FAILURE]
   filename, size, sha256       error_description
   arquivo físico existe        (sem arquivo válido; .part removido)
             │                          │ (terminal)
             │        retenção (se AUTOMATICO elegível)
             ├──────────────────────────┤
             ▼
   [REMOVIDO PELA RETENÇÃO]
   removed_at + removed_reason
   registro PRESERVADO (§20/§33)
```

- `SUCCESS → FAILURE`: não ocorre (falha gera registro próprio);
- `SUCCESS → REMOVIDO`: somente pela retenção, somente `AUTOMATICO` elegível;
- `FAILURE` é terminal (não é candidato a nada — §18);
- Backup legado (arquivo pré-feature sem registro): **sem registro** → tratado como não elegível (FR-014; listagem exibe `—`).

### Consultas derivadas (monitoramento — FR-032)

| Indicador | Consulta |
|---|---|
| Último backup automático | último `AUTOMATICO` por `timestamp` desc (status exibido) |
| Último backup válido | último `SUCCESS` com arquivo presente (qualquer tipo) |
| Última falha | último `FAILURE` (qualquer tipo) |
| Backups válidos | count `SUCCESS` com arquivo presente no disco (cruzado com `list_backups()`) |
| Removidos pela retenção | count `removed_at IS NOT NULL` |
| Última retenção | eventos `BACKUP_RETENCAO_EXECUTADA` da auditoria (motivo: fonte única já existente) |

---

## 2. Entidades existentes — apenas consumo (zero alteração)

| Entidade | Uso nesta feature |
|---|---|
| `AuditLog` | recebe 5 ações novas (research R8); `module="Backup"`; sem mudança de schema |
| Arquivos em `data/backups/` | fonte física da listagem (`list_backups()` intocada); tipo agregado via join com `backup_records.filename` |
| `User` | ator dos eventos manuais; automático/retenção audita com ator `None` (sistema) + description "sistema" |

---

## 3. Classificação GFS (regra de dados, determinística — briefing §22–§24)

Dados de entrada: registros `AUTOMATICO`/`SUCCESS` com `removed_at IS NULL` e arquivo presente, ordenados por `timestamp` (UTC) desc.

1. **Janela diária**: elegível se `timestamp < now_utc() − DAILY_DAYS`.
2. **Âncora semanal**: agrupar por semana ISO (segunda como início, UTC); em cada semana dentro das últimas `WEEKLY_WEEKS`, o automático **mais recente** é preservado (não elegível).
3. **Âncora mensal**: agrupar por mês-calendário (UTC); em cada mês dentro dos últimos `MONTHLY_MONTHS`, o automático **mais recente** é preservado.
4. **Guarda do último válido** (§28): se o conjunto remanescente de backups válidos no sistema (incluindo manuais, pré-restauração e legados presentes no disco e gzip legível — conservador, resolve F7) ficaria com **0** após a remoção, o candidato é preservado e o motivo registrado (`ULTIMO_BACKUP_VALIDO`); os demais motivos de preservação: `ANCORA_SEMANAL`, `ANCORA_MENSAL`, `INTEGRIDADE_NAO_OK` — todos reportados no `new_data.preservados` do evento `BACKUP_RETENCAO_EXECUTADA` (contract §5).
5. **Proteções absolutas** (§25/§26/§27): `MANUAL`, `PRE_RESTAURACAO`, legado sem registro, integridade ≠ OK → nunca elegíveis. `PRE_RESTAURACAO`: default preservar **todos**; se `KEEP_PRE_RESTORE = N > 0`, os N mais recentes são preservados e os demais tornam-se candidatos (política explícita do operador — FR-025).

Resultado por execução: `{candidatos, removidos, falhas, resultado: COMPLETA|PARCIAL|FALHA}` (§32).

---

## 4. Configuração (entidades de ambiente — research R2)

Sem entidade de banco. Valores vivem em `app/config.py` (env vars com defaults) e são **normalizados/validados no serviço** (valor inválido → default seguro + log técnico). Detalhes e tabela: [contracts/service-contract.md §1](./contracts/service-contract.md).

---

## 5. BVs — decisões verificáveis (paridade com specs anteriores)

- **BV-1**: `create_all` cria `backup_records` em banco existente sem tocar nada mais (verificado: tabelas novas são criadas automaticamente por `init_db`).
- **BV-2**: backup manual atual (botão) continua gravando `BACKUP_CRIADO` e agora `MANUAL` — nenhum campo obrigatório novo na API pública existente (parâmetro `backup_type` tem default).
- **BV-3**: backup de segurança do restore (017/019) passa a registrar `PRE_RESTAURACAO` sem alterar a ordem do ciclo (marcação é interna do `generate_backup` chamado pelo worker).
- **BV-4**: filename UNIQUE garante 1 registro por arquivo; tentativa duplicada (colisão de micros — impossível na prática) cai no fluxo de falha existente (BV-3 da 015). Em FAILURE, o filename é o nome final **projetado** (sem arquivo físico correspondente) — não representa ponto de restauração e a listagem/elegibilidade sempre cruzam registro com arquivo presente no disco;
- **BV-5**: retenção nunca remove arquivo cujo registro não confirme `AUTOMATICO` + integridade OK — arquivos órfãos (sem registro) são intocados.
