# Relatório Final: Central de Integrações — Saúde do Sistema (047) + Correções Pós-Entrega dos Cards de Backup

**Feature**: 047 | **Entrega original**: 2026-09-26 (ver `validacao.md`) | **Correções pós-entrega**: 2026-09-27 | **Base**: `specs/047-saude-central-integracoes/` + `specs/032-central-integracoes/`

---

## 1. Escopo das correções pós-entrega (2026-09-27)

Após a entrega da 047, a conferência do card **Agendador de Backup** em homologação revelou que as linhas de execução não refletiam o backup automático das 02:00. A investigação estendeu-se aos três cards de backup (Agendador, Backup Local, Backup Externo), que compartilham a mesma causa. Nada disto altera os contratos da 047 (§9): continuam válidos R2/R4/R5/R6/R7, SC-002/SC-003/SC-004/SC-007/SC-009 — as fontes continuam sendo as tabelas/meios existentes, sem I/O externo no GET, sem componentes novos e sem permissões novas.

### 1.1 Causa-raiz 1 — "Último resultado: —" (bug de chave)

- O agendador (021/026) grava `_last_result = {"ok": ...}` **em memória** (`backup_scheduler.py:483/493/501`);
- A status_fn lia `last.get("result")` — chave que **nunca existiu** no formato real → sempre "—";
- Agravantes: o valor é volátil (some no restart) e o teste `test_scheduler_com_ultimo_resultado_erro` **mockava** `{"result": "FAILURE"}` — formato inexistente — mascarando o bug.

### 1.2 Causa-raiz 2 — "Última execução / Último sucesso / Falhas (24h): —" (por design, decisão de produto)

- As linhas da `dl` vêm do histórico `integration_executions` (032); **nenhum fluxo de backup grava lá** — registram em `backup_records`/`backup_external_records` + eventos de auditoria;
- O contrato de UI previa "componentes de saúde exibem `—` onde não se aplica" — decidido manter assim na entrega original. Na revisão pós-entrega, o usuário optou por **popular do banco** (decisão registrada em §4).

### 1.3 Causa-raiz 3 — datas ISO cruas na apresentação

- Os templates da Central exibiam `|localtime` sem `strftime`, renderizando o `str()` do datetime (`2026-09-27 02:00:21-03:00`) em vez do padrão do app `dd/mm/AAAA HH:MM` (convenção 004).

## 2. Arquivos alterados

| Arquivo | Alteração |
|---|---|
| `app/services/integration_center_service.py` | (a) `_scheduler_status_fn`: "Último resultado" derivado do último `BackupRecord` tipo `AUTOMATICO` (persistente); "Próximo backup" formatado `dd/mm HH:MM` (datetime já vem em America/Recife de `scheduler_status()` — só formata, sem reconverter); (b) novo `_backup_counters(db, key)`: contadores da `dl` a partir das tabelas persistentes — `scheduler` → `backup_records` (tipo `AUTOMATICO`), `backup_local` → `backup_records` (todos os tipos), `backup_externo` → `backup_external_records` (045, `copied_at`); mesmo formato de retorno de `_execution_counters` (`SimpleNamespace` com `.created_at`/`.detail`), desvio em `_execution_counters`; falhas 24h na janela P-4; "Último erro" do detalhe = `error_description` (já sanitizada, Princípio VI) |
| `app/web/templates/admin/integracoes/list.html` | `Última execução`/`Último sucesso` com `(…\|localtime).strftime('%d/%m/%Y %H:%M')` |
| `app/web/templates/admin/integracoes/detail.html` | Idem (páginas de detalhe) |
| `tests/test_central_saude.py` | Testes reformulados/novos (§3) |

**Zero linhas alteradas**: `backup_scheduler.py`, `backup_service.py`, `external_backup_service.py`, `admin_routes.py`, models, banco (nenhuma migration), auditoria, RBAC.

## 3. Testes (estado final: **82 passed** = 37 da 047 + 45 da 032)

| Teste | O que trava |
|---|---|
| `test_scheduler_ativo_e_desabilitado` | Preservado (ATIVA/DESABILITADA) |
| `test_scheduler_com_ultimo_resultado_erro` | **Reformulado**: último AUTOMATICO = FAILURE → COM_ERRO com ("Último resultado", "Falha") — antes mockava formato inexistente |
| `test_scheduler_ultimo_resultado_sucesso_do_banco` | Último AUTOMATICO = SUCCESS → ATIVA "Sucesso" (fonte no banco) |
| `test_scheduler_sem_backup_automatico_mostra_traco` | Sem automático → "—" + ATIVA (ausência ≠ falha, precedente 032) |
| `test_scheduler_ignora_backups_manuais_no_resultado` | MANUAL não conta como resultado do agendador |
| `test_scheduler_card_dl_populada_do_banco` | dl do card com timestamps do banco (falha 30h fora da janela + sucesso 2h) |
| `test_scheduler_card_falha_na_janela_24h` | FAILURE em 24h → `failures_24h = 1`, sem último sucesso, COM_ERRO |
| `test_scheduler_card_dl_ignora_manuais` | MANUAL/PRE_RESTAURACAO fora da dl do agendador |
| `test_scheduler_proximo_backup_formatado_ddmm_hhmm` | `Próximo backup` casa `\d{2}/\d{2} \d{2}:\d{2}` |
| `test_backup_local_card_dl_populada_do_banco` | dl de backup_local de `backup_records` (todos os tipos); regime manual espelha última falha → COM_ERRO (clarify) |
| `test_backup_externo_card_dl_populada_do_banco` | dl de backup_externo de `backup_external_records`; última cópia SUCCESS → ATIVA |
| `test_backup_externo_card_dl_sem_copia` | Habilitado sem cópia → dl "—" + INATIVA |

Execuções: `pytest tests/test_central_saude.py tests/test_central_integracoes.py -q` → **82 passed** (rodadas a cada passo; suíte completa da entrega original em `validacao.md`).

## 4. Decisões registradas

1. **Último resultado do Agendador pelo banco** (usuário, 2026-09-27): derivação do último `BackupRecord AUTOMATICO` em vez do `_last_result` em memória — persistente e correto em restart.
2. **Popular a dl dos três cards de backup** (usuário, 2026-09-27): supera o "—" por design da entrega original para os componentes cujas execuções vivem em `backup_records`/`backup_external_records`; a `dl` continua "—" para app/database/storage (sem execuções aplicáveis — contrato UI mantido onde "não se aplica").
3. **Formato de data**: padrão do app `dd/mm/AAAA HH:MM` (convenção 004) nos templates da Central; `Próximo backup` em `dd/mm HH:MM` (resumo do card, paridade com Backup Local/Externo).

## 5. Limitações / notas

- `Operações pendentes` permanece 0 nos três cards (não há tabela de pendências aplicável) — comportamento da 032 preservado.
- Falha de cópia externa antiga (fora de 24h) não entra em `failures_24h`, mas ainda define o status COM_ERRO do card Backup Externo (regra da entrega original, mantida).
- `total`/`failures` no detalhe dos cards de backup agora refletem os registros de backup (antes sempre 0) — muda a leitura de "Operações realizadas/com erro" na página de detalhe.
- Validação visual em homologação (recarregar `/admin/integracoes`) pendente de confirmação pelo operador — não executada neste ambiente.
