# Data Model: Restauração Segura de Backup

**Feature**: 017-restauracao-segura-backup | **Data**: 2026-09-17

> **Zero DDL**: nenhuma tabela/coluna nova. A operação de restauração é um conceito **efêmero em memória**; os artefatos persistidos são os arquivos de backup do mecanismo existente e os eventos apensáveis da trilha `audit_logs`.

---

## 1. Entidades

| Entidade | Natureza | Persistência | Notas |
|---|---|---|---|
| **Backup** (existente, 015/016) | Arquivo em `data/backups/` | Filesystem | Padrão estrito `backup_YYYYMMDD_HHMMSS_micros.sql(.gz)?`; timestamp UTC; campos derivados: `size_bytes`, `integrity` (OK/—/CORROMPIDO), `sha256` (`.sql.gz`) — consumido como está |
| **Backup de segurança pré-restore** | Papel do mesmo artefato Backup | Filesystem | Gerado por `generate_backup` imediatamente antes do import; identificável pelo evento de auditoria (R3); nunca removido automaticamente |
| **Operação de Restauração** | Conceito efêmero | **Memória do processo** (flag + `threading.Lock`) | Ciclo validar → confirmar → segurança → import → pós-restore; estado "em andamento" usado apenas para bloqueio concorrente (R6); some ao fim da operação |
| **Permissão `backup.restaurar`** | Catálogo RBAC | Tabela `permissions` (seed idempotente existente) | Módulo `Backup`; concedida ao Administrador pelo `ensure_default_roles` — nenhuma atribuição manual necessária |
| **Eventos de auditoria** | Apêndices na trilha | Tabela `audit_logs` | 4 eventos novos (§2.2) — trilha única e imutável |

## 2. Estados da Operação de Restauração

### 2.1 Máquina de estados (ciclo síncrono, uma por vez)

```text
[NÃO INICIADA] ──(GET tela de informações)──> [EXIBINDO INFORMAÇÕES]   (nada executado)
      │                                              │
      │ (GET não executa restore)                    │ (POST confirmação)
      ▼                                              ▼
[CANCELADA] ◄──(cancelar em qualquer etapa)── [VALIDANDO BACKUP]
      │                                              │ falha → [FALHA_VALIDACAO] (banco intocado; evento)
      │                                              ▼ ok
      │                                        [CRIANDO BACKUP SEGURANÇA]
      │                                              │ falha → [FALHA_SEGURANCA] (banco intocado; evento; restore NÃO inicia)
      │                                              ▼ ok
      │                                        [VALIDANDO BACKUP SEGURANÇA]
      │                                              │ falha → [FALHA_SEGURANCA]
      │                                              ▼ ok
      │                                        [IMPORTANDO DUMP]  (cliente nativo; flag ativa)
      │                                              │ falha → [FALHA_RESTORE] (estado parcial possível →
      │                                              │            backup de segurança preservado; orientação manual)
      │                                              ▼ ok
      │                                        [VALIDANDO PÓS-RESTORE]
      │                                              │ falha → [FALHA_RESTORE]
      │                                              ▼ ok
      └──────────────────────────────────> [SUCESSO]  (evento; mensagem com os 2 arquivos)
```

**Invariantes de transição**:
- **BV-R1** — Nenhum estado de escrita no banco é alcançado sem: backup selecionado validado + confirmação explícita (POST) + backup de segurança validado. (spec FR-09/FR-10/FR-11)
- **BV-R2** — A flag "restore em andamento" fica ativa de `[CRIANDO BACKUP SEGURANÇA]` até a saída (sucesso ou falha) e é liberada em `finally`; nesse intervalo, novo restore e geração de backup manual são rejeitados. (R6/FR-16/FR-17)
- **BV-R3** — `[FALHA_*]` nunca produz mensagem de sucesso; `[SUCESSO]` só é alcançado após `[VALIDANDO PÓS-RESTORE]` aprovado. (FR-20/FR-22)
- **BV-R4** — Em qualquer `[FALHA_*]`, o backup de segurança permanece listável/baixável. (FR-11/§28)

### 2.2 Eventos de auditoria (§30 — literais)

| Evento | Estado de origem | Resultado | `new_data` (sem segredos) |
|---|---|---|---|
| `BACKUP_RESTORE_INICIADO` | entrada em `[VALIDANDO BACKUP]` (após confirmação) | SUCCESS | `{backup: <arquivo>}` |
| `BACKUP_PRE_RESTORE_CRIADO` | saída de `[CRIANDO BACKUP SEGURANÇA]` | SUCCESS | `{backup: <restaurado>, backup_seguranca: <arquivo>}` |
| `BACKUP_RESTORE_SUCESSO` | `[SUCESSO]` | SUCCESS | `{backup: <restaurado>, backup_seguranca: <arquivo>}` |
| `BACKUP_RESTORE_FALHA` | qualquer `[FALHA_*]` | FAILURE | `{backup: <arquivo>, motivo: <descrição segura>}` |

Rótulos de interface: "Restauração Iniciada" · "Backup Pré-Restore Criado" · "Restauração Concluída" · "Restauração Falhou". Tentativas não autorizadas (403) seguem pelo mecanismo existente de acesso negado. Nota: a **geração** do backup de segurança também produz o evento `BACKUP_CRIADO` padrão da Feature 1 (trilha apensável — os dois eventos coexistem).

## 3. Compatibilidade de artefatos (§35 — matriz)

| Entrada em `data/backups/` | Listagem (016) | Restaurável? | Observação |
|---|---|---|---|
| `backup_*.sql.gz` (016) | sim | **sim** (descompressão streaming) | Rejeitado se `integrity == CORROMPIDO` |
| `backup_*.sql` (015, legado) | sim | **sim** (leitura direta) | `integrity == —` (sem checksum); validação por legibilidade |
| `*.part` / `*.part.gz` | nunca | **nunca** (regex rejeita) | Temporários da geração |
| Nomes fora do padrão | nunca | **nunca** | Path traversal impossível por construção |
| Diretórios/alien no diretório | nunca (`is_file()`) | **nunca** | Defesa em camadas |

## 4. Tabelas essenciais para validação pós-restore (§25 — estrutura real)

`users`, `user_roles`, `user_sessions`, `roles`, `role_permissions`, `permissions`, `custodians`, `locations`, `assets`, `movements`, `maintenances`, `inventarios`, `inventario_itens`, `audit_logs`, `ad_settings`, `ad_group_roles`, `setup_claims` — **17 tabelas**, nomes extraídos dos `__tablename__` reais dos models (`app/models/*.py`; **remediação A1**: lista completa e autoritativa no contract §4) — presença verificada por consulta somente-leitura ao catálogo do banco; dados essenciais por contagem somente-leitura (usuários, bens, colaboradores).
