# Feature Specification: Correção da Atualização Imediata do Status do Backup Automático

**Feature Branch**: `feature-026-correcao-status-backup`

**Created**: 2026-09-19

**Status**: Draft

**Input**: Problema observado na tela de Configurações de Backup Automático — após salvar, o indicador visual "Agendamento" nem sempre reflete imediatamente o novo estado (exige F5/atualizar/alterar outra configuração para mostrar o valor correto). Corrigir SOMENTE essa inconsistência de apresentação, pela menor alteração possível, preservando integralmente o sistema existente.

## Regra fundamental

> **Primeiro identificar exatamente por que a interface mostra estado antigo; depois fazer a menor alteração necessária para corrigir.** Proibido: `window.location.reload()` como correção principal; exigir F5/botão direito/alterar outra configuração para o indicador atualizar; criar segunda fonte de verdade; usar o snapshot interno do scheduler como fonte do estado exibido. **Se uma alteração não for indispensável para a tela refletir imediatamente a configuração recém-salva, NÃO fazer essa alteração** (briefing §46; Constitution I).

## Realidade verificada (causa mapeada no código atual — 2026-09-19)

*Analisado antes de escrever a spec; a implementação DEVE reconfirmar e medir, não presumir.*

1. **Página**: `GET /admin/backups` (`admin_backups`, `app/web/admin_routes.py:804–846`, guard `backup.gerenciar`), template `app/web/templates/admin/backups.html`.
2. **Indicador "Agendamento"**: card "Backup Automático" do template (`backups.html:93–101`) exibe o badge Ativado/Desativado a partir de **`auto_status.enabled`** (e `auto_status.schedule`/`auto_status.time_local`).
3. **`auto_status`** = `scheduler_status()` (`admin_routes.py:832`; função em `backup_scheduler.py:261–279`), que lê **`_eff()`** → snapshot module-level `_current_effective` do scheduler — renovado **apenas no start (`:790`) e a cada tick de 30 s (`:799`)**, NÃO por request.
4. **Checkbox do modal**: usa **`config_form.auto_enabled`** (`backups.html:169`) = `get_effective_config(db, create=False)` (`admin_routes.py:840`) — leitura **fresca do banco por request** (022, sem efeito colateral).
5. **POST**: `admin_backup_config_save` (`admin_routes.py:888–963`) valida → `save_backup_config` (commit único) → auditoria `BACKUP_CONFIGURACAO_ALTERADA` → **redirect 303** `/admin/backups?success=|error=`. O banco fica correto imediatamente.
6. **Causa provável (a confirmar/medir na implementação)**: após o redirect, o GET monta o indicador com o snapshot possivelmente **defasado até 30 s** (janela do tick) — por isso o estado novo aparece só "depois de um tempo", após F5, ou após alterar outra configuração (mais tempo decorrido). Configuração persistida ≠ estado exibido imediatamente. Intermitência explicada pela fase do tick relativa ao momento do salvamento.
7. **Uso intermediário**: `scheduler_status()` também alimenta o monitoramento da 020 (US7) — a correção NÃO deve alterar o que o scheduler de fato usa para executar (`_eff()` no loop), nem o mecanismo de refresh/agendamento (briefing §6/§20); a divergência a corrigir é **somente a fonte do indicador apresentado na página**.
8. **Arquitetura preservada** (auditoria 024): tela → POST → `backup_config` → `get_effective_config()` → `EffectiveBackupConfig` → scheduler/retenção. Nada disso muda.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Indicador reflete imediatamente a configuração salva (Priority: P1)

Um administrador abre Administração → Backups, abre o modal de Configurações, marca "Backup automático: Ativado" e salva. A página retornada (pós-redirect) exibe **imediatamente** "Agendamento: **Ativado**" — sem F5, sem botão direito→Atualizar, sem alterar outra configuração. O mesmo vale na direção inversa (marcar Desativado → "Agendamento: **Desativado**" imediato). O estado apresentado pela interface representa a configuração efetivamente persistida.

**Why this priority**: é o problema da feature — sem isso, a tela engana o operador sobre o estado real.

**Independent Test**: POST alterando `auto_enabled`, seguir o redirect, e verificar no HTML da resposta final que o badge "Agendamento" já mostra o novo valor — sem manipulação de tempo/refresh.

**Acceptance Scenarios**:

1. **Given** configuração desativada, **When** salva "Ativado", **Then** a página pós-redirect mostra "Agendamento: Ativado" imediatamente.
2. **Given** configuração ativada, **When** salva "Desativado", **Then** a página pós-redirect mostra "Agendamento: Desativado" imediatamente.
3. **Given** qualquer salvamento, **When** o GET pós-redirect renderiza a página, **Then** o indicador e o checkbox do modal representam o mesmo valor efetivo (consistência indicador = checkbox = persistido = efetivo).

---

### User Story 2 - Causa raiz corrigida na origem, sem reload e sem segunda fonte (Priority: P1)

A correção é feita na **origem do estado apresentado**: a página passa a derivar o estado Ativado/Desativado (e, quando aplicável, frequência/horário exibidos no card) da **configuração efetiva lida por request** — a mesma fonte já usada pelo formulário (`get_effective_config`), sem criar cache/variável global/tabela/sessão paralela e sem tornar a interface dependente do snapshot interno do scheduler. Nenhum `window.location.reload()` é introduzido; o fluxo POST → 303 → GET permanece o padrão existente. Os dados de **execução** (em execução? próximo disparo? último resultado?) continuam vindo do monitoramento do scheduler, pois descrevem execução, não configuração.

**Why this priority**: garante que o sintoma não seja mascarado (reload) e que a correção respeite a arquitetura (fonte única + briefing §17/§18/§19).

**Independent Test**: inspecionar o diff (nenhuma nova fonte de estado, nenhum reload) e o contexto do template (uma única fonte para checkbox e indicador).

**Acceptance Scenarios**:

1. **Given** a implementação, **When** o diff é revisado, **Then** não existem nova variável global, cache, tabela, sessão-permanente ou JS de reload; nenhuma alteração em `backup_scheduler.py`/`backup_service.py`/model/banco.
2. **Given** a página renderizada, **When** o contexto é analisado, **Then** indicador e checkbox derivam da configuração efetiva obtida por request (mesma leitura ou leituras equivalentes da mesma fonte).
3. **Given** os dados de execução do card, **When** analisados, **Then** continuam alimentados pelo mecanismo existente do scheduler, sem que o estado Ativado/Desativado dependa dele.

---

### User Story 3 - Testes automatizados do fluxo real e regressão (Priority: P1)

Novos testes reproduzem o problema e o fluxo real (rota/template — padrão pytest existente): com configuração `false`, POST salvando `true` → seguir redirect → GET → HTML contém "Agendamento: Ativado"; e o inverso (`true` → `false` → "Agendamento: Desativado"). A suíte existente relacionada (backup, `backup_config`, automático, retenção, monitoramento) é executada e permanece verde; nenhum teste existente é enfraquecido ou adaptado apenas para passar. Testes de alteração repetida (off→on→off→on→off), alteração de outros campos junto (horário/retenção) e F5-idempotência são cobertos pelos novos testes onde tecnicamente possível.

**Why this priority**: trava a correção contra regressão (Constitution VIII) e comprova o fluxo ponta a ponta (briefing §42).

**Independent Test**: rodar a suíte; os novos testes falham no código antigo e passam no corrigido (quando tecnicamente reproduzível).

**Acceptance Scenarios**:

1. **Given** o código corrigido, **When** os novos testes rodam, **Then** o fluxo POST→redirect→GET mostra o estado atualizado imediatamente em todas as variações testadas (simples, repetida, com outros campos).
2. **Given** a suíte completa relacionada, **When** executada, **Then** permanece verde sem modificações de testes existentes (exceto adaptação legítima mínima se um assert citar o comportamento corrigido — sem enfraquecimento).
3. **Given** o código anterior à correção (reprodução), **When** o teste do fluxo roda, **Then** o problema é reproduzível (badge com valor antigo), evidenciando que o teste cobre a causa.

---

### User Story 4 - Preservação total e relatório final (Priority: P2)

Nada além da apresentação/obtenção do estado é alterado: scheduler (tick, refresh, execução, catch-up, retenção), BackupService (dump/compressão/validação/restore), tabela `backup_config`/model, precedência de `get_effective_config()` (persistido → env → default) e defaults, auditoria (evento before/after existente), RBAC (guard `backup.gerenciar`), sessões. Testes manuais de validação (briefing §26–§37) são executados quando aplicáveis ao ambiente: alteração repetida, alteração com outros campos, F5 (antes = depois), botão direito→Atualizar, checkbox condizente, reinício (estado correto pós-restart), concorrência (sem estado global compartilhado). O relatório final entrega: causa confirmada (não hipótese), arquivos alterados e motivação, fluxo corrigido, testes executados (exatamente os que foram) e limitações.

**Why this priority**: protege o sistema existente (Constitution I) e garante entrega verificável (briefing §45).

**Independent Test**: `git diff` limitado aos arquivos estritamente necessários; relatório com causa/arquivos/fluxo/testes/limitações.

**Acceptance Scenarios**:

1. **Given** o diff final, **When** conferido, **Then** não altera `backup_scheduler.py`, `backup_service.py`, `backup_config_service.py`, `models/backup_config.py` nem banco — salvo necessidade comprovada e justificada no relatório (esperado: não).
2. **Given** o fluxo pós-correção, **When** F5 ou atualização manual é feita após salvar, **Then** o valor antes = depois (nada muda — o estado já estava correto).
3. **Given** o relatório final, **When** lido, **Then** distingue causa confirmada (com evidência) de hipóteses, lista testes realmente executados e limitações honestas.

---

### Edge Cases

- **Salvamento sem alteração do toggle** (só horário/retenção): indicador permanece consistente com o persistido (briefing §28) — o estado exibido nunca regride.
- **Valores inválidos no POST** (ex.: horário 25:99): fluxo atual preservado — redirect com `?error=`, nada persistido, indicador continua mostrando a configuração vigente (`test_backup_config.py:255` cobre).
- **Dois administradores simultâneos**: sem estado global compartilhado; cada GET lê o banco por request (comportamento atual preservado — briefing §37); última escrita válida prevalece (commit único existente).
- **Restart da aplicação**: estado exibido correto imediatamente após o primeiro GET (configuração vem do banco; briefings §33 — nada de estado temporário de navegador).
- **Falha de leitura do banco** (fallback de boot do scheduler): o indicador da página segue a fonte da efetiva por request; comportamento de exceção do scheduler (024/AT-2) permanece intocado e documentado.
- **Monitoramento da 020** (rota/dados de status, se existirem além da página): avaliar caso a caso — se outro consumidor exibir "Ativado/Desativado" com o mesmo problema de defasagem, a correção se aplica a ele também, sempre pela fonte da efetiva; dados de execução permanecem do scheduler.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O indicador visual "Agendamento" (badge Ativado/Desativado) da página Administração → Backups DEVE refletir a configuração efetiva **no momento do render** — imediatamente após o POST→redirect→GET, sem F5, sem atualização manual e sem alterar outra configuração.
- **FR-002**: O estado exibido pelo indicador e o estado do checkbox "Backup automático ativado" do modal DEVEM derivar da mesma fonte — a configuração efetiva obtida por request (leitura da configuração persistida via mecanismo existente) — representando o mesmo valor.
- **FR-003**: A correção DEVE ocorrer na origem do estado apresentado (fonte de dados do template/rota); é PROIBIDO introduzir `window.location.reload()`/`location.reload()` como correção e proibido criar segunda fonte de verdade (variável global, cache paralelo, JSON, sessão permanente, tabela paralela).
- **FR-004**: A interface NÃO DEVE depender do snapshot interno do scheduler (`scheduler_status()._eff()`) para exibir o estado Ativado/Desativado da configuração; dados de execução (running, próximo disparo, último resultado) continuam do mecanismo existente de monitoramento.
- **FR-005**: O fluxo de salvamento permanece: POST `/admin/backups/configuracoes` → validação → persistência (commit único) → auditoria `BACKUP_CONFIGURACAO_ALTERADA` → redirect 303 com `?success=`/`?error=` — nenhuma mudança de rota, método ou padrão.
- **FR-006**: Nenhuma alteração na tabela/modelo `backup_config`, na precedência de `get_effective_config()` (persistido → env → default), nos defaults da 020 ou no comportamento de fallback.
- **FR-007**: Nenhuma alteração em `backup_scheduler.py` (tick, refresh, agendamento, execução, catch-up, retenção, concorrência) e em `backup_service.py` (dump, compressão, validação, restore) — problemas independentes encontrados são registrados para feature futura, não corrigidos aqui.
- **FR-008**: Auditoria existente preservada (evento, before/after, sem novo evento); RBAC preservado (`backup.gerenciar` no GET e POST); sessões preservadas.
- **FR-009**: Novos testes automatizados (padrão pytest/`TestClient` do projeto) reproduzem o fluxo real e o problema: POST salvando o toggle (true e false) → seguir redirect → GET → assert no HTML do badge "Agendamento" com o valor novo; variações: alteração repetida (off→on→off→on→off), alteração do toggle junto com outros campos (horário; retenção), e idempotência de F5 (segundo GET idêntico ao primeiro). Quando a reprodução do problema no código antigo for tecnicamente viável, o teste deve evidenciá-la.
- **FR-010**: Testes existentes relacionados (backup, `backup_config`, automático, retenção, monitoramento, administração) são executados e permanecem verdes; nenhum teste é enfraquecido; adaptação legítima mínima apenas se um assert citar diretamente o comportamento corrigido.
- **FR-011**: Arquivos alterados: somente os estritamente necessários para a fonte do estado exibido (esperado: `app/web/admin_routes.py` e/ou `app/web/templates/admin/backups.html`); qualquer alteração além disso é justificada caso a caso no relatório.
- **FR-012**: Relatório final (briefing §45): causa confirmada com evidência do código (não hipótese), arquivos alterados + por quê, fluxo corrigido (POST → persistência → redirect → GET → efetiva → template → indicador), testes executados (somente os realmente executados, com resultado), limitações.

### Non-Functional Requirements

- **NFR-001** (Mínima alteração): nenhuma refatoração, reorganização de serviços, novo serviço, alteração de banco, de scheduler ou de arquitetura — correção localizada na apresentação/obtenção do estado.
- **NFR-002** (Consistência): indicador = checkbox = configuração persistida = configuração efetiva, em todos os fluxos testados.
- **NFR-003** (Sem regressão): suíte relacionada verde; comportamento de backup manual, automático, restore, retenção, histórico, auditoria, RBAC e sessões preservado integralmente.
- **NFR-004** (Interface): nenhum JS novo de refresh; nenhum CSS novo; consistência visual e acessibilidade do card preservadas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após salvar "Ativado", a página pós-redirect exibe "Agendamento: Ativado" imediatamente; o mesmo para "Desativado" — comprovado por teste automatizado do fluxo real (sem F5/refresh).
- **SC-002**: F5/atualização manual após salvar não altera o valor exibido (idempotência — antes = depois).
- **SC-003**: Indicador, checkbox, configuração persistida e configuração efetiva representam o mesmo valor em todos os cenários testados.
- **SC-004**: `git diff` não contém alterações em `backup_scheduler.py`, `backup_service.py`, `backup_config_service.py`, `models/backup_config.py`, banco, migrações, RBAC ou sessões (salvo necessidade comprovada e justificada — esperado: nenhuma).
- **SC-005**: Suíte existente relacionada verde + novos testes do fluxo real passando (e reproduzindo o problema no código antigo, quando tecnicamente possível).
- **SC-006**: Relatório final produzido com causa confirmada (evidência), arquivos/motivos, fluxo corrigido, testes executados e limitações — sem apresentar hipótese como causa.

## Assumptions

1. A causa provável mapeada (indicador alimentado pelo snapshot do scheduler com defasagem de até 30 s) foi confirmada por leitura do código atual e será **validada por teste de reprodução** na implementação antes da correção — o relatório final só registra causa confirmada (briefing §45.1).
2. A fonte correta do estado exibido é a configuração efetiva por request (mesma do `config_form`); nenhum mecanismo novo de obtenção é criado (briefing §16/§17).
3. O refresh do scheduler por tick (30 s) permanece como está — a defasagem é aceitável para **execução** (domínio do scheduler), não para **exibição** na página (briefing §6/§20).
4. Se o diagnóstico da implementação revelar causa diferente da mapeada (ex.: ordem de execução, cache HTTP), a spec continua válida: corrige a origem do estado exibido, mantendo as proibições (§3) e o escopo mínimo (§39).
5. Testes manuais de navegador (F5, botão direito, reinício) seguem validação pelo operador quando o ambiente permitir (como nas features anteriores); os testes automatizados cobrem o fluxo POST→redirect→GET e a idempotência de GET.
6. Nenhum commit/push é feito automaticamente — decididos pelo usuário após a entrega.
