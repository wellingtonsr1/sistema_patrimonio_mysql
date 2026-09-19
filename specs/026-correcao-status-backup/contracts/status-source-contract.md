# Contract: Fonte do Estado do Card "Backup Automático" (Feature 026)

**Feature**: 026 | **Data**: 2026-09-19
Este contrato fixa a **fonte de cada dado exibido** no card e as proibições da correção (spec FR-002–FR-007; briefing §14/§17–§22).

---

## 1. Contrato de fontes (template `app/web/templates/admin/backups.html`, card "Backup Automático")

| Dado exibido | Fonte OBRIGATÓRIA após a correção | Variável de contexto |
|---|---|---|
| Badge "Ativado/Desativado" (Agendamento) | Configuração efetiva por request | `config_form.auto_enabled` |
| Frequência exibida | Configuração efetiva por request | `config_form.schedule` |
| Horário exibido ("HH:MM") | Configuração efetiva por request | `config_form.time` |
| "Em execução" / running | Monitoramento do agendador (mantido) | `auto_status.running` |
| Próximo disparo | Monitoramento do agendador (mantido) | `auto_status.next_run_local` |
| Último resultado | Monitoramento do agendador (mantido) | `auto_status.last_result` |

**Invariantes**:
- `config_form` é fornecido pelos 2 GETs que renderizam o template (`admin_backups` e `admin_backup_config_form`) via `get_effective_config(db, create=False)` — **nenhuma chamada nova, nenhum objeto novo**.
- O checkbox do modal permanece `config_form.auto_enabled` → badge e checkbox **sempre** da mesma fonte.
- O formato do horário exibido não muda ("HH:MM" America/Recife).

## 2. Proibições (briefing §3/§17–§22/§39)

1. `window.location.reload()`/`location.reload()` ou qualquer JS de refresh — proibidos.
2. Criar variável global, cache, arquivo JSON, sessão permanente, tabela paralela ou função paralela de leitura de configuração — proibido (reutilizar `get_effective_config`).
3. Fazer a interface depender do snapshot do scheduler para exibir **configuração** (Ativado/Desativado, frequência, horário) — proibido.
4. Alterar `app/services/backup_scheduler.py` (inclui `_TICK_SECONDS`, `_eff()`, `refresh_effective_config()`, `scheduler_status()`), `app/services/backup_service.py`, `app/services/backup_config_service.py`, `app/models/backup_config.py` ou qualquer migration — proibido nesta feature (salvo necessidade comprovada e justificada no relatório; esperado: nenhuma).
5. Alterar fluxo do POST (validação → persistência → auditoria → redirect 303), auditoria, RBAC, sessões — proibido.
6. Alterar testes existentes para "passar" — proibido (apenas adaptação legítima mínima se um assert citar o comportamento corrigido, sem enfraquecimento).
7. Alterar documentação — fora de escopo (025 já está fiel).

## 3. Comportamento obrigatório pós-correção

- POST salvando toggle → redirect → GET: badge exibe o **novo** valor no primeiro render (SC-001), em qualquer fase do tick.
- F5/atualização manual após salvar: valor antes = depois (SC-002).
- Dois administradores simultâneos: cada request lê o banco — nenhum estado compartilhado (briefing §37).
- Reinício: primeiro GET já mostra o estado persistido (briefing §33).
- Valores inválidos no POST: comportamento atual (redirect `?error=`, nada persistido) preservado.

## 4. Critério de conformidade

- [ ] Badge/frequência/horário do card = `config_form.*` (efetiva por request).
- [ ] Running/próximo/último = `auto_status.*` (mantido).
- [ ] Zero diff em scheduler/service/model/banco/docs.
- [ ] Novos testes do fluxo real verdes; suíte relacionada verde.
- [ ] Reprodução da causa executada antes da correção (relatório registra resultado).
