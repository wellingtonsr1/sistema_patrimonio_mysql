# Relatório Final: Correção da Atualização Imediata do Status do Backup Automático

**Feature**: 026 | **Data**: 2026-09-19 | **Base**: auditoria 024 + spec/plan/contract de `specs/026-correcao-status-backup/`

---

## 1. Causa encontrada (confirmada por reprodução — não hipótese)

O indicador **"Agendamento"** (badge Ativado/Desativado) do card "Backup Automático" era alimentado por `auto_status.enabled`, que vem de `scheduler_status()` (`admin_routes.py:832/896`) → `_eff()` → snapshot module-level `_current_effective` do scheduler (`backup_scheduler.py:90`) — renovado **apenas no start (`:790`) e a cada tick de 30 s (`:799`)**, nunca por request. Já o checkbox do modal usava `config_form = get_effective_config(db, create=False)` (`admin_routes.py:840/894`) — leitura fresca do banco por request.

**Por que "salvar → tela mostrava estado anterior"**: o POST persistia e commitava corretamente (`backup_config_service.py:255–263`), mas o GET do redirect renderizava o badge com o **snapshot defasado** (até 30 s). A intermitência relatada (às vezes atualizava sozinha/ao alterar outra configuração) é a **fase do tick** relativa ao momento do salvamento: quanto mais tempo passava, maior a chance de um tick ter renovado o snapshot.

**Reprodução por teste** (registrada antes da correção): com snapshot existente e defasado (estado real de produção entre ticks), o fluxo POST→redirect→GET no código antigo resultava em `assert 'Desativado' == 'Ativado'` — badge mostrando o valor antigo. Teste-documentação: `test_026_causa_snapshot_defasado_reproduz_problema` (agora também documenta a correção: o badge ignora o snapshot defasado).

## 2. Arquivos alterados

| Arquivo | Alteração |
|---|---|
| `app/web/templates/admin/backups.html` | Card "Backup Automático": badge/frequência/horário do "Agendamento" passam a ler de `config_form.*` (efetiva por request) em vez de `auto_status.*`; dados de execução (Próxima execução, Último disparo) permanecem de `auto_status.*` |
| `tests/test_backup_config.py` | Seção FEATURE 026: 6 testes novos (fluxo real POST→redirect→GET + causa) + helpers `_badge`/`_post_config_follow` |

## 3. Por que cada alteração foi necessária

**`app/web/templates/admin/backups.html`** — Motivo: é onde o estado exibido era derivado da fonte errada (snapshot do scheduler). Corrigir na origem = trocar a fonte do valor no template (o `config_form` já era fornecido por request pelas 2 rotas que renderizam a página), atendendo FR-002/FR-003/FR-004 sem tocar em services.

**`tests/test_backup_config.py`** — Motivo: FR-009/FR-010 — travar o comportamento corrigido com testes do fluxo real (briefing §42) e reproduzir o problema no código antigo como evidência de causa (§45.1).

**`app/web/admin_routes.py` — NENHUMA alteração foi necessária**: ambas as rotas que renderizam o template já injetavam `config_form = get_effective_config(db, create=False)` — a correção foi 100% na fonte de leitura do template (research R3 confirmado na execução).

## 4. Fluxo corrigido

```text
Tela (modal) → POST /admin/backups/configuracoes
   → validação (save_backup_config)
   → persistência backup_config (commit único)
   → auditoria BACKUP_CONFIGURACAO_ALTERADA (before/after) — intocada
   → redirect 303 /admin/backups?success=|error=
GET /admin/backups
   → config_form = get_effective_config(db, create=False)   ← leitura fresca por request
   → template: badge/frequência/horário ← config_form.*      ← FONTE CORRIGIDA
              (running/próximo disparo/último disparo ← auto_status.* — mantido)
   → indicador atualizado imediatamente (mesma fonte do checkbox)
```

## 5. Testes executados (somente os realmente executados)

| Teste | Resultado |
|---|---|
| Novos testes 026 no **código antigo** (reprodução): 6 falharam — badge mostrava valor antigo (`'Desativado' == 'Ativado'`); 1ª rodada: 5 falhas mecânicas (helper sem seguir redirect) corrigidas para reprodução causal | ✅ causa reproduzida |
| Novos testes 026 no **código corrigido**: `pytest tests/test_backup_config.py -k "026"` → **6 passed** | ✅ |
| Regressão completa: `pytest tests/test_backup_config.py tests/test_backup_automatico.py tests/test_backup_retencao.py tests/test_backup_monitoramento.py` → **81 passed** | ✅ |
| Varredura prévia: nenhum teste existente afirma o badge via `auto_status` (T002) → nenhuma adaptação de teste necessária | ✅ |
| Inspeção de diff (§44): somente template + testes; **zero** em `backup_scheduler.py`, `backup_service.py`, `backup_config_service.py`, `models/backup_config.py`, banco, migrations, docs, auditoria, RBAC | ✅ |
| **NÃO executados** (limitação de ambiente — quickstart Passo 6): testes manuais de navegador (F5, botão direito→Atualizar, reinício da aplicação, dois navegadores simultâneos). A idempotência de F5 e a repetição off→on→off estão cobertas pelos testes automatizados (`test_026_f5_idempotente`, `test_026_alteracao_repetida_off_on_off`); reinício coberto pelo teste existente `test_r_persistencia_sobrevive_a_reinicio` | ⚠️ ver §6 |

## 6. Limitações

1. **Testes manuais de navegador não executados** neste ambiente (não há navegador/servidor de desenvolvimento aqui). Os fluxos correspondentes foram automatizados quando possível (F5 = GET consecutivo; alteração repetida; checkbox na mesma resposta). Recomenda-se a checagem visual do operador (Passo 6 do quickstart) antes de considerar a experiência validada em produção.
2. O teste-documentação da causa simula a defasagem do snapshot (estado real entre ticks) via o próprio valor do snapshot após o refresh — não manipula o relógio/tick da thread; a equivalência com produção é estrutural (mesma fonte de leitura), confirmada pela correção do comportamento.
3. Nenhum commit/push foi feito — decisão do usuário (Assumption 6 da spec).

---

**Critérios de aceitação (briefing §43)**: todos os itens automatizáveis ✅ (indicador imediato nas 2 direções; sem F5; checkbox = indicador; persistido/efetivo corretos; scheduler/retenção/backup manual/restore/auditoria/RBAC preservados — regressão 81 passed; nenhuma nova fonte de verdade; nenhum cache; zero diff de banco/scheduler/BackupService). Itens de navegador: pendentes de checagem visual pelo operador (§6.1).
