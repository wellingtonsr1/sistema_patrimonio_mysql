# Quickstart — Validação: Backup Automático e Política de Retenção

> Guia de execução/validação (padrão 015–019). Implementação detalhada pertence a `tasks.md`/fase de implementação. Testes A–Q referenciam o briefing §39.

---

## 1. Pré-requisitos

- Suíte base verde: `pytest` (suíte existente — 313 testes);
- MariaDB acessível (produção/testes de integração) **ou** suíte padrão (SQLite em memória — restrito a testes, Constitution VII);
- Para validação real de SO: Linux e Windows com `mysqldump`/`mariadb-dump` acessível (`MYSQLDUMP_PATH` no Windows/XAMPP, se preciso — correção 018).

## 2. Configuração de teste (`.env`)

```env
# Cenário A — automático ativado, horário próximo (Recife):
BACKUP_AUTO_ENABLED=true
BACKUP_AUTO_SCHEDULE=daily
BACKUP_AUTO_TIME=02:00            # ajustar para 2–3 min no futuro durante o teste real
BACKUP_RETENTION_DAILY_DAYS=30
BACKUP_RETENTION_WEEKLY_WEEKS=12
BACKUP_RETENTION_MONTHLY_MONTHS=12
BACKUP_RETENTION_KEEP_PRE_RESTORE=0

# Cenário B — desativado (default seguro):
# BACKUP_AUTO_ENABLED=false  (ou variável ausente)
```

⚠️ Nenhum cenário de teste define retenção < 1 (validação do serviço impõe default) — impossível configurar exclusão indiscriminada (FR-035).

## 3. Validação automatizada (suíte)

```bash
pytest tests/test_backup_automatico.py -v   # novo módulo (Testes A–M, P, Q)
pytest                                       # suíte completa — zero regressão
```

Mapeamento briefing §39 → testes:

| Teste | Cenário | Verificação principal |
|---|---|---|
| A | Agendamento dispara | relógio fake atinge horário → `generate_backup` chamado com `AUTOMATICO` |
| B | Sucesso | arquivo válido + `BackupRecord(SUCCESS)` + `BACKUP_AUTOMATICO_SUCESSO` + `BACKUP_CRIADO` |
| C | Falha de subprocesso (fake exit≠0) | FAILURE + evento falha + log com etapa/exit (stderr sanitizado) |
| D | Executável inexistente | FAILURE com mensagem "não encontrado" |
| E | Espaço/permissão (OSError fake) | FAILURE, sem crash do scheduler |
| F | Arquivo parcial | `.part*` removido; FAILURE; não listável como válido |
| G | Retenção | automático fora de `DAILY_DAYS` (não âncora) é removido; âncoras semanais/mensais preservadas |
| H | Manual antigo | `MANUAL` nunca removido (mesmo expirado) |
| I | Pré-restauração | `PRE_RESTAURACAO` preservado (default); com `KEEP_PRE_RESTORE=N`, N mais recentes preservados |
| J | Último backup válido | remoção que deixaria 0 válidos é bloqueada + motivo registrado |
| K | Falha de limpeza | OSError na remoção → evento individual FAILURE + resultado PARCIAL |
| L | Histórico pós-remoção | `BackupRecord` permanece com `removed_at/reason` |
| M | Concorrência | 2º disparo simultâneo descartado (log); disparo durante restore adiado |
| P | Restore | backup automático válido restaurável pelo fluxo 017/019 existente (sem adaptação) |
| Q | Segurança | path traversal bloqueado; nada fora de `BACKUP_DIR` removido; nenhum segredo em logs/auditoria; RBAC: indicadores exigem `backup.gerenciar` |

Testes **N** (Windows) e **O** (Linux): manuais — seção 4.

## 4. Validação manual real (Testes N/O — Windows e Linux)

### 4.1 Ciclo automático (Testes A/B reais)

1. Configure `BACKUP_AUTO_ENABLED=true` e `BACKUP_AUTO_TIME` 2–3 min no futuro (Recife);
2. Inicie: `python run.py` (Linux) / `python run.py` (Windows/XAMPP com `MYSQLDUMP_PATH` se necessário);
3. No horário configurado:
   - [ ] Novo arquivo em `data/backups/backup_*.sql.gz` (padrão existente);
   - [ ] Tela **Administração → Backups**: card "Backup Automático" mostra SUCESSO + horário; coluna Tipo = `AUTOMATICO`;
   - [ ] Auditoria: `BACKUP_AUTOMATICO_SUCESSO` + `BACKUP_CRIADO` (ator "sistema");
   - [ ] `data/logs/app.log`: "Backup concluído" sem segredos.
4. Reinicie o servidor **antes** do horário do dia seguinte e confirme (catch-up R5):
   - [ ] Com ciclo corrente sem sucesso: 1 única execução de recuperação ~60 s após o start;
   - [ ] Com ciclo corrente já bem-sucedido: nenhuma re-execução; próxima execução futura exibida.

### 4.2 Desativado (Teste B-negativo)

1. `BACKUP_AUTO_ENABLED=false`; reinicie;
2. [ ] Nenhum dump executado no horário; card mostra "Desativado".

### 4.3 Retenção (Testes G–J reais)

1. Com backup automático ativado, reduza `BACKUP_RETENTION_DAILY_DAYS=1` em ambiente de TESTE;
2. Gere 2–3 automáticos (aguardar ciclos ou usar banco de teste), + 1 manual (botão) + simule pré-restauração (restore de teste);
3. Aguarde o próximo ciclo (retenção roda pós-backup);
4. Verificar:
   - [ ] Automáticos antigos (não âncora) removidos; registros preservados com `removed_at` (coluna Tipo continua, arquivo some);
   - [ ] Manual e pré-restauração **intactos**;
   - [ ] Auditoria: `BACKUP_REMOVIDO_RETENCAO` por arquivo + `BACKUP_RETENCAO_EXECUTADA` com contagens;
   - [ ] Pelo menos 1 backup válido permanece (guarda).

### 4.4 Restore de automático (Teste P real)

1. Na tela Backups, escolha um automático válido → Restaurar → confirmação explícita;
2. [ ] Fluxo 017/019 completo funciona: backup de segurança criado (Tipo `PRE_RESTAURACAO`), modo manutenção, import, validação pós, `BACKUP_RESTORE_SUCESSO`.

### 4.5 Segurança (Teste Q real)

- [ ] Usuário sem `backup.gerenciar`: card/coluna novos não quebram tela; rota continua 403 (deny-by-default);
- [ ] Tentar download/restaurar com nome manipulado (`../../x.sql.gz`): 404 (validação existente);
- [ ] `grep -i "senha\|MYSQL_PWD\|mariadb+pymysql" data/logs/app.log` → nenhuma ocorrência de credencial.

## 5. Critérios de aprovação

- [ ] Suíte completa verde (incl. `test_backup_automatico.py`);
- [ ] Cenários 4.1–4.5 aprovados em **Linux** (Teste O) e **Windows** (Teste N);
- [ ] Nenhum evento de falso sucesso em nenhum cenário de falha;
- [ ] Documentação atualizada na mesma tarefa (README: env vars + comportamento pós-restart; ARQUITETURA_E_MANUTENCAO: agendador/retenção/monitoramento).
