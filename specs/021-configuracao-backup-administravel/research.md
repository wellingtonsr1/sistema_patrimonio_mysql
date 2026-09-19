# Research: Configuração Administrável do Backup Automático e Política de Retenção

**Feature**: 021 | **Data**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

Decisões de design resolvidas na Phase 0. Cada decisão cita a alternativa avaliada e o motivo da escolha.

---

## R1 — Armazenamento: tabela nova aditiva `backup_config` (singleton), seguindo o precedente `ADSettings`

**Decision**: persistir as 8 configurações operacionais em tabela nova `backup_config` (registro único `id=1`, criada por `create_all`), acessada por um service específico de configuração de backup.

**Rationale**: o sistema **já possui** esse padrão validado (`ADSettings` singleton + tela + env como fallback + evento `ALTERACAO_CONFIG_AD`): reutilizá-lo é a menor alteração coerente (Constitution I), atende ao objetivo (configuração pela interface, persistente, sem reinício) e não cria arquitetura paralela (briefing §31 — o service é específico de backup, não genérico).

**Alternatives considered**:
- **A — manter somente `config.py`/env**: não atende ao objetivo (exige servidor + reinício); descartada como solução única (constantes permanecem para bootstrap/fallback);
- **B — `.env`**: continua exigindo acesso ao servidor e reinício; briefing proíbe adicionar variáveis de backup ao `.env` automaticamente; descartada;
- **C — persistir no banco sem precedente**: subsumida por D — a tabela nova segue o padrão do precedente existente;
- **D — mecanismo existente**: escolhida (esta decisão). `ConfigService`/`SettingsService` genérico foi explicitamente rejeitado (§31; Constitution III — a lógica pertence ao domínio de backup).

## R2 — Precedência (fonte única em runtime): configuração salva governa; env/default = bootstrap e fallback

**Decision**: função única `get_effective_config(db)` resolve cada campo nesta ordem: **(1)** valor persistido na linha singleton, quando definido; **(2)** variável de ambiente (`config.py`); **(3)** default da 020. A resolução é a MESMA para todos os 8 campos e é a única via de leitura do scheduler, da tela e da retenção.

**Rationale**: espelha exatamente `_effective_settings` do `ad_service` (precedente documentado, comportamento já compreendido pelos operadores); elimina comportamento indefinido (spec FR-006/FR-007): para cada campo há sempre UMA resposta determinística.

**Alternatives considered**: env sempre vence banco (quebraria a expectativa do operador que salvou pela tela); banco sempre vence env ignorando fallback (impediria bootstrap limpo em instalação nova); último-a-escrever por campo sem regra explícita (indefinido — proibido pelo §7).

## R3 — Primeira inicialização: linha singleton criada lazily com valores "não definidos"; efetiva = defaults da 020

**Decision**: `get_backup_config(db)` cria a linha `id=1` se ausente (padrão `get_ad_settings`), com campos de agendamento/retenção **nulos** ("não definidos"); a configuração efetiva nesse estado é exatamente os defaults da 020 (`enabled=false`, `daily`, `02:00`, domingo, 30/12/12, pré-restauração preservar todos). O primeiro salvamento pela tela define os campos explicitamente.

**Rationale**: scheduler nunca fica em estado indefinido (spec FR-008; briefing §16); campos nulos distinguish "nunca configurado" de "configurado com o default", mantendo o fallback env útil para quem já opera por variáveis (FR-026 — nenhum deploy quebra). O backend continua validando faixas (defesa em profundidade já existente no scheduler via `_effective_int`).

**Alternatives considered**: linha criada já com defaults gravados — perde a distinção "não definido" e congela os valores no momento da instalação (mudança futura de default não se aplicaria a quem nunca configurou); sem linha e sem fallback — estado indefinido, proibido.

## R4 — Aplicação dinâmica no scheduler: leitura da configuração efetiva POR TICK (sem reinício, sem segundo scheduler, sem hot reload genérico)

**Decision**: o loop `_scheduler_loop` passa a obter um **snapshot** de `get_effective_config()` a cada tick (30 s) e usar esse snapshot para `enabled`, `schedule`, `weekday` e o cálculo `_next_run_utc`/catch-up; `_apply_retention` recebe os limites do mesmo snapshot do ciclo. O `hour, minute` capturado no start da thread (hoje usado só no log de inicialização) deixa de ter função de configuração.

**Rationale**: descoberta técnica verificada no código da 020: o loop **já reavalia** `BACKUP_AUTO_ENABLED` e `_next_run_utc(_clock())` a cada tick — a configuração capturada no start é apenas o log. Portanto, trocar constantes importadas por valor (topo do módulo) pela leitura viva da configuração efetiva entrega "sem reinício" (spec FR-011) com alteração mínima e localizada, sem criar segundo scheduler (briefing §12) nem mecanismo de hot reload (§26). O catch-up (020 R5) continua avaliado 1× por start, mas agora lendo a configuração efetiva do momento.

**Alternatives considered**: reiniciar a thread a cada salvamento (complexidade de ciclo de vida sem benefício — o tick de 30 s já é o ciclo natural); mensageria/fila de invalidação (infraestrutura externa proibida); manter captura no start + exigir reinício documentado (aceitável pelo FR-011, mas desnecessário dado o tick existente — rejeitada por ser pior para o operador sem ser mais simples).

## R5 — Consistência por ciclo: snapshot único por tick; salvamento atômico (briefing §27)

**Decision**: cada tick lê a configuração efetiva **uma única vez** e o ciclo inteiro (disparo, retenção, status) usa esse objeto imutável em memória; o POST salva todos os campos numa única transação (`db.commit()` único). Assim nunca existe combinação parcial (novo horário + frequência antiga) nem duas escritas entrelaçadas.

**Rationale**: FR-012/FR-013; resolução determinística "última escrita válida prevalece" vem da transação única (mesmo comportamento do singleton ADSettings sob concorrência); sem necessidade de lock adicional — a thread lê snapshot, o request escreve atomicamente, o próximo tick vê o estado novo completo.

**Alternatives considered**: lock de leitura no salvamento (complexidade sem ganho: leitura é de linha única e a transação já é atômica); aplicar campo a campo (cria exatamente o estado parcial proibido).

## R6 — Validação: backend é a barreira; faixas por campo; serviço de config + validação existente do scheduler preservadas

**Decision**: `save_backup_config` valida: `schedule ∈ {daily, weekly}`; horário HH:MM válido (00:00–23:59); `weekday ∈ 0–6`; retenção diária ≥ 1; semanal ≥ 1; mensal ≥ 1; `keep_pre_restore ≥ 0`. Falha → `ValueError` com mensagem clara; a rota converte em mensagem de erro e **não persiste nada**. A validação defensiva já existente no scheduler (`_effective_int`, parse de horário com fallback) permanece como segunda camada.

**Rationale**: spec FR-014–FR-016 (briefing §14: "A validação do backend continua sendo obrigatória"); valores limítrofes válidos (00:00, retenção 1) são aceitos; rejeição não altera o estado vigente (transação única abortada).

**Alternatives considered**: validação só na UI (proibida — §20); relaxar faixas para aceitar 0 dias de retenção (contraria a semântica da 020 — 0 desligaria a janela diária de forma não prevista).

## R7 — Auditoria e RBAC: evento dedicado + permissão existente `backup.gerenciar`

**Decision**: nova ação aditiva `BACKUP_CONFIGURACAO_ALTERADA` (constante + rótulo "Configuração de Backup Alterada") gravada com `write_change_audit` (before/after por campo, padrão do POST do AD). Rotas GET/POST `/admin/backups/configuracoes` sob `require_permission("backup.gerenciar")` — **nenhuma permissão nova**.

**Rationale**: spec FR-020/FR-022 (briefing §18/§19: procurar permissão existente adequada); a área é a mesma já protegida por `backup.gerenciar` e o risco é o mesmo (operação de backup), logo criar permissão nova seria burocracia sem ganho de segurança; acesso negado gera 403 auditado pelo mecanismo existente.

**Alternatives considered**: permissão nova `backup.configurar` — rejeitada por não haver risco distinto que a justifique (spec A1; §19 exige justificativa, e ela não existe); reutilizar `ALTERACAO_CONFIG_AD` — semanticamente errado (módulo distinto).

## R8 — `config.py`: constantes preservadas (bootstrap/fallback); default `BACKUP_AUTO_ENABLED` já correto e protegido por teste

**Decision**: nenhuma constante da 020 é removida de `config.py` (FR-026; briefing §37 — mapear consumidores antes de alterar; os imports existentes não quebram). O comentário do default é mantido coerente com o código (`"false"` — a inconsistência apontada pelo briefing §15/§38 já foi corrigida no commit `cf43cb7`); adiciona-se comentário apontando a precedência (banco → env → default). Teste anti-regressão fixa o default desativado.

**Rationale**: consumidores mapeados: `backup_scheduler` (importa as 7 constantes restantes no topo — passa a consumi-las via configuração efetiva; os imports são redirecionados internamente, sem assinatura pública quebrada), `admin_routes`/docs (nenhum uso). Remover as constantes agora quebraria o bootstrap de instalações novas e a compatibilidade de quem opera por env (FR-026) sem ganho.

**Alternatives considered**: remover constantes e ler só do banco — quebra instalação nova antes do primeiro acesso à tela (bootstrap impossível) e deploys por env; duplicar defaults em dois lugares — risco de divergência (proibido §7).

---

## Mapeamento dos consumidores das constantes (briefing §37)

| Constante (`config.py`) | Consumidores atuais | Após a feature |
|---|---|---|
| `BACKUP_AUTO_ENABLED` | `backup_scheduler` (loop, catch-up, status) | via `get_effective_config()` (constante = fallback) |
| `BACKUP_AUTO_SCHEDULE` | `backup_scheduler` (`_effective_schedule`) | idem |
| `BACKUP_AUTO_TIME` | `backup_scheduler` (`_effective_time`) | idem |
| `BACKUP_AUTO_WEEKDAY` | `backup_scheduler` (`_effective_weekday`) | idem |
| `BACKUP_RETENTION_DAILY_DAYS` | `backup_scheduler` (`_apply_retention`) | idem |
| `BACKUP_RETENTION_WEEKLY_WEEKS` | `backup_scheduler` (`_apply_retention`) | idem |
| `BACKUP_RETENTION_MONTHLY_MONTHS` | `backup_scheduler` (`_apply_retention`) | idem |
| `BACKUP_RETENTION_KEEP_PRE_RESTORE` | `backup_scheduler` (`_apply_retention`) | idem |

Nenhum outro módulo consome essas 8 constantes (verificado por busca em `app/`); `MYSQLDUMP_PATH`, `BACKUP_DIR`, `BACKUP_IMPORT_TIMEOUT`, `DATABASE_URL` permanecem exclusivamente técnicos, intocados.
