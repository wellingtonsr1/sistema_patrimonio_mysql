# Service Contract — Configuração Administrável do Backup (feature 021)

> Contratos das superfícies tocadas. Padrão das specs 015–020: nomes finais podem variar minimamente na implementação, semântica não. Confinado a services + rotas da área de Backups (Constitution II/III). Fonte única de configuração efetiva (spec FR-006/007).

---

## §1. Service NOVO — `app/services/backup_config_service.py`

Service **específico** de configuração de backup (proibido serviço genérico — briefing §31). Funções públicas:

### `get_backup_config(db) -> BackupConfig`
- Retorna a linha singleton `id=1`; cria-a (lazy, campos "não definidos") se ausente — padrão `get_ad_settings` (R3);
- Nunca levanta por linha ausente; commit da criação é da função (autocadastro do singleton), leituras subsequentes não escrevem.

### `get_effective_config(db) -> EffectiveBackupConfig`
- Resolve a configuração efetiva por campo: **persistido (definido) → env → default da 020** (R2 — regra única, FR-007);
- Retorna objeto **imutável** (snapshot) com os 8 campos + `updated_at`/`updated_by` (para exibição);
- Env inválida = tratada como ausente; **nunca levanta** (falha de resolução → default + log técnico);
- Única via de leitura de configuração operacional por scheduler, tela, retenção e monitoramento (FR-010).

### `save_backup_config(db, actor, *, auto_enabled, schedule, time, weekday, retention_daily_days, retention_weekly_weeks, retention_monthly_months, keep_pre_restore) -> EffectiveBackupConfig`
- **Valida** (R6 — FR-014/015): `schedule ∈ {daily, weekly}`; `time` HH:MM válido; `weekday ∈ 0–6`; `retention_daily_days ≥ 1`; `retention_weekly_weeks ≥ 1`; `retention_monthly_months ≥ 1`; `keep_pre_restore ≥ 0`. Qualquer violação → `ValueError` com mensagem clara, **antes** de qualquer escrita (nada persiste, estado vigente intacto);
- Captura `before` (valores efetivos atuais), aplica os novos valores na linha singleton, define `updated_by=actor.username`, `updated_at=now_utc()`, **commit único** (atômico — R5);
- Retorna a configuração efetiva resultante. **Auditoria é responsabilidade da rota** (padrão AD: rota monta before/after e chama `write_change_audit`) — o service não audita, para manter o padrão existente da área.

### `EffectiveBackupConfig` (dataclass imutável)
Campos: `auto_enabled: bool`, `schedule: str`, `time: str`, `weekday: int`, `retention_daily_days: int`, `retention_weekly_weeks: int`, `retention_monthly_months: int`, `keep_pre_restore: int`, `updated_at`, `updated_by`. Sem segredos (FR-021).

---

## §2. Modelo — `app/models/backup_config.py` (NOVO)

`BackupConfig` conforme data-model §1: singleton `id=1`, campos operacionais nullable ("não definido"), `auto_enabled` booleano default `False`, `updated_at`/`updated_by`. Import adicionado a `models/__init__.py` → `create_all` cria a tabela (aditivo, idempotente). `config.py`: constantes da 020 **preservadas** (bootstrap/fallback), comentário de precedência acrescentado, default `BACKUP_AUTO_ENABLED="false"` explicitado (já correto no código atual — R8).

---

## §3. Scheduler — `backup_scheduler.py` (ajuste da origem dos valores)

### Leitura por tick (R4/R5 — aplicação sem reinício, FR-011/FR-012)
- `_scheduler_loop` abre sessão curta **por tick** e obtém `effective = get_effective_config(db)` (snapshot do ciclo); usa `effective.auto_enabled`, `effective.schedule`, `effective.weekday` e calcula `_next_run_utc` a partir do snapshot;
- `_run_scheduled_backup` e `_apply_retention` recebem o **mesmo snapshot** do ciclo (limites de retenção dele); retenção 020 intacta em lógica — só a origem muda (spec FR-003);
- Catch-up 020 (R5/020): avaliado 1× por start, lendo a efetiva do momento — regra do ciclo corrente preservada;
- Funções `_effective_time/_effective_schedule/_effective_weekday/_effective_int` são migradas internamente para consumir o snapshot (validação de faixa permanece como segunda camada — R6); assinaturas públicas do módulo não quebram;
- Proibições mantidas: **sem** segundo scheduler, **sem** reinício de thread a cada salvamento, **sem** hot reload genérico (briefing §12/§26).

### `scheduler_status()` (020)
Continua existindo; passa a reportar a partir da efetiva (mesma fonte da tela — FR-010). Sem segredos.

---

## §4. Rotas — `admin_routes.py` (área Backups existente)

### `GET /admin/backups/configuracoes` (HTML)
- `require_permission("backup.gerenciar")` (existente — sem permissão nova; spec A1/R7);
- Contexto: `config_form` (valores da efetiva para o form — placeholders nos campos não definidos), `config_updated_at/updated_by`, `active_tab="admin"`.

### `POST /admin/backups/configuracoes` (form + redirect 303)
- Mesma permissão; validação **no backend** (POST direto sem permissão → 403 auditado — FR-022/FR-023);
- Fluxo (FR-017 do briefing §17): monta `before` (efetiva atual) → chama `save_backup_config` → captura `ValueError` → redirect com mensagem de erro (nada persistiu) → em sucesso: `write_change_audit` com before/after **por campo alterado** → redirect com mensagem de sucesso;
- Auditoria: `action=ACTION_BACKUP_CONFIG_UPDATED` (`BACKUP_CONFIGURACAO_ALTERADA`), `module="Backup"`, `resource="BackupConfig"`, `resource_id=1`, `ip_address`, antes/depois — **sem segredos** (padrão exato do POST `/admin/ad/settings` — R7).

---

## §5. Auditoria — `audit_service.py` (+1 ação aditiva)

| Constante | Valor | Rótulo |
|---|---|---|
| `ACTION_BACKUP_CONFIG_UPDATED` | `BACKUP_CONFIGURACAO_ALTERADA` | "Configuração de Backup Alterada" |

- Gravado via `write_change_audit` existente (before/after JSON por campo — usuário, data/hora, valores anterior/novo: FR-020);
- Nenhuma ação da 020 é alterada ou removida; nenhum segredo em nenhum campo (FR-021).

---

## §6. UI — `templates/admin/backups.html` (aditivo)

- Nova seção **"Configurações de Backup"** na tela, abaixo do card de monitoramento (componentes existentes: card/dl/inputs/checkbox/select — padrão visual do formulário "Integração AD"; tema claro/escuro e responsividade herdados — FR-018);
- Campos (FR-019): Ativado (checkbox) · Frequência (select Diário/Semanal) · Horário (input HH:MM) · Dia da semana (select 0–6 com rótulos) · Retenção diária/semanal/mensal (number) · Pré-restauração (select "Preservar todos" / "Preservar N mais recentes" + number) · exibição de `updated_at/updated_by`;
- Formulário único → POST na rota do §4; mensagens success/error pelo padrão da tela; **nenhum campo técnico** (caminhos/executáveis/credenciais — FR-005); nada removido do template (card de monitoramento e listagem intactos — Princípio X);
- Central de ajuda: artigo de backup ganha seção "Configurações de Backup" (comportamento real: precedência, aplicação por tick ~30 s, o que nunca é editável pela tela).

---

## §7. Compatibilidade e reinício

- Deploys que operam por env **sem nunca usar a tela**: comportamento idêntico ao atual (efetiva = env/default — precedência R2; FR-026);
- `.env` não recebe nenhuma variável nova automaticamente (briefing §8);
- Persistência sobrevive a reinício (create_all idempotente; Teste R);
- Aplicação da nova configuração pelo scheduler: **sem reinício** — efetiva no próximo tick (≤ 30 s) (R4);
- Linux/Windows: nenhum caminho de código novo dependente de SO (FR-025).

---

## §8. Matriz de erros

| Situação | Resultado |
|---|---|
| Valor de campo inválido (ex.: "25:99", retenção 0) | `ValueError` → redirect com erro; **nada persiste**; estado vigente intacto |
| POST sem `backup.gerenciar` | 403 + evento de acesso negado (padrão existente); nada persiste |
| Falha de banco no commit | Erro controlado → mensagem de erro; configuração anterior vigente |
| Linha singleton ausente | Criada lazily com campos "não definidos"; efetiva = defaults (nunca indefinido) |
| Env inválida/ausente | Tratada como ausente → default da 020 (log técnico, sem crash) |
| Dois POSTs simultâneos | Commits atômicos; última escrita válida prevalece; ambos auditados |
