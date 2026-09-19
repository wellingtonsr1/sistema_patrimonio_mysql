# Research: Correção da Atualização Imediata do Status do Backup Automático

**Feature**: 026 | **Data**: 2026-09-19
**Base**: código verificado nesta sessão + relatório da auditoria 024. Causa mapeada linha a linha; decisões abaixo definem o desenho da correção mínima.

---

## R1 — Causa raiz confirmada (evidência)

**Cadeia do problema**:

```text
POST /admin/backups/configuracoes → save_backup_config (commit) → redirect 303 → GET /admin/backups
   GET monta contexto:
     auto_status = scheduler_status()          ← admin_routes.py:832 (e :896 na rota dedicada)
                    ↓ backup_scheduler.py:268–279 → "enabled": _eff().auto_enabled
                    ↓ _eff() → _current_effective (snapshot module-level, :90)
                    ↓ renovado APENAS no start (:790) e a cada tick de 30 s (:799) — NÃO por request
   template: badge "Agendamento" ← auto_status.enabled (backups.html:95–99)
```

O POST persiste e commita (`backup_config_service.py:255–263`), mas o GET seguinte renderiza o badge com o **snapshot** do scheduler, que só se atualiza no próximo tick (≤ 30 s). Logo:

- Estado novo aparece "depois de um tempo" (próximo tick) ou após F5/outra alteração (tempo adicional decorrido) — **intermitência = fase do tick** relativa ao salvamento.
- O checkbox do modal (`config_form.auto_enabled`, `backups.html:169` ← `get_effective_config(db, create=False)` `admin_routes.py:840`) nunca sofre do problema — leitura fresca por request.

**Conclusão**: configuração persistida ≠ estado exibido imediatamente, porque **indicador e checkbox usam fontes diferentes** (exatamente o cenário proibido pelo briefing §14).

**Validação por reprodução (obrigatória antes de corrigir — spec Assumption 1)**: teste que (a) fixa o snapshot do scheduler desatualizado (monkeypatch de `_current_effective` ou de `scheduler_status`), (b) salva o toggle oposto, (c) segue o redirect e verifica o badge — no código atual ele deve falhar mostrando o valor antigo. A implementação executa esse teste **antes** da correção para confirmar a causa (briefing §45.1 — causa confirmada, não hipótese).

## R2 — Decisão: fonte única = configuração efetiva por request

**Decision**: o card "Backup Automático" passa a derivar **estado/frequência/horário exibidos** da configuração efetiva obtida por request — a mesma leitura já feita para o `config_form` (`get_effective_config(db, create=False)`), reutilizada (nada novo criado; briefing §16/§17). Dados de **execução** (running, próximo disparo, último resultado) continuam de `auto_status = scheduler_status()`.

**Rationale**: atende FR-002/FR-004 (mesma fonte do checkbox; sem dependência do snapshot para exibir configuração); mínima invasão — a rota já chama `get_effective_config` por request; nenhum cache/variável global/sessão (briefing §17); não usa o scheduler como fonte da interface (§18); não altera o scheduler (§20).

**Alternatives considered**:
- Forçar `refresh_effective_config()` no GET — rejeitada: alteraria o mecanismo interno do scheduler a partir da rota (efeito colateral em módulo proibido; briefing §20) e acoplaria rota → estado interno da thread.
- Exibir `config_form` diretamente no badge mantendo `auto_status` só para execução — **é a decisão**, com o detalhe de que frequência/horário do card também migram para a efetiva (são configuração, não execução); `running`/`next_run`/`last_result` permanecem de `auto_status`.

## R3 — Pontos de alteração (2 contextos + 1 trecho de template)

**Decision**:
1. `admin_backups` (`admin_routes.py:804–846`): o contexto já possui `config_form` (efetiva, `create=False`) — o template passa a usá-lo para o badge (nenhuma mudança de rota necessária neste GET, salvo ajuste mínimo se a implementação optar por variável explícita de status).
2. `admin_backup_config_form` (`:886–905`): idem — já possui `config_form = eff` (`:894`).
3. `backups.html` card "Backup Automático" (`:93–101`): badge/schedule/time passam a ler de `config_form` (`auto_enabled`, `schedule`, `time`); `running`/`next_run_local`/`last_result` continuam de `auto_status`.

**Rationale**: ambas as rotas que renderizam o template já carregam a efetiva por request — a correção é predominantemente **no template**, com zero alteração de services; mínimo invasivo (briefing §39).

**Alternatives considered**: mudar `scheduler_status()` para ler o banco por chamada — rejeitada: alteraria `backup_scheduler.py` (proibido, §20) e o monitoramento da 020 tem semântica própria (estado do agendador, não da configuração).

## R4 — Formato do horário exibido

**Decision**: a efetiva expõe `time` como string "HH:MM" (America/Recife) e `auto_status` expõe `time_local` no mesmo formato — a exibição no card mantém o formato atual ("{{ schedule }} às {{ time }}"), apenas trocando a fonte (`config_form.time`). Sem conversão nova; fuso/documentação (025) permanecem corretos.

**Rationale**: FR-002 (mesma fonte) sem alterar a apresentação; evita qualquer risco de fuso duplo.

## R5 — Testes do fluxo real (US3)

**Decision**: novos testes em `tests/test_backup_config.py` (arquivo da 021/022 — contexto e fixtures existentes: `client` admin, `fixed_fallbacks`, `seeded_config`), seguindo o padrão do projeto:

1. **Ativação**: config desativada → POST salvando `auto_enabled=true` (+ follow_redirects) → assert "Ativado" no HTML e badge condizente.
2. **Desativação**: config ativada → POST `false` → assert "Desativado".
3. **Repetição**: off→on→off→on→off — a cada POST, o HTML seguinte reflete o novo estado (briefing §26).
4. **Com outros campos**: salvar toggle + horário alterado; e desativar + alterar retenção — indicador coerente (§28).
5. **Idempotência de F5**: segundo GET consecutivo idêntico ao primeiro (§29 — versão automatizável).
6. **Reprodução da causa**: com `_current_effective` desatualizado propositalmente (monkeypatch), o GET antigo exibiria valor errado — teste-documentação da causa (executado antes da correção; após a correção, o teste de fluxo passa independentemente do snapshot).

**Rationale**: FR-009/FR-010; briefing §41/§42; Constitution VIII. Testes existentes intocados (nenhum assert atual depende do badge vindo de `auto_status` — confirmar na execução; se houver, adaptação legítima mínima registrada).

## R6 — Outros consumidores de `scheduler_status()` (escopo)

**Decision**: varredura encontrou `scheduler_status()` usado em: `admin_routes.py:832` e `:896` (contexto dos 2 GETs) e `tests/test_backup_automatico.py:119` (teste da 020 — comportamento do agendador). A correção **não altera a função**; apenas deixa de usar `enabled/schedule/time_local` do `auto_status` **no badge do card**. O teste da 020 permanece verde (função intocada).

**Rationale**: FR-007/SC-004; escopo mínimo — o problema é a fonte do indicador, não a função de monitoramento.

## R7 — Sem alteração documental

**Decision**: a documentação atual (025) já descreve a efetiva como fonte da tela; após a correção o código passa a coincidir integralmente — **nenhum doc precisa mudar**. Se a implementação revelar algo não coberto, registrar no relatório (sem editar docs fora de tarefa própria).

**Rationale**: Constitution XI; NFR-001 (mínima alteração).

## R8 — Validação e relatório

**Decision**: validação = novos testes (R5) + suíte relacionada existente (`test_backup_config.py`, `test_backup_automatico.py`, `test_backup_retencao.py`, `test_backup_monitoramento.py` + RBAC/admin se aplicável) + `git diff` conferindo SC-004 + testes manuais de navegador (F5/botão direito/reinício) quando o ambiente permitir — registrados no relatório **somente os realmente executados** (briefing §45.5). Relatório final em `specs/026-correcao-status-backup/relatorio.md` com os 6 itens do §45.

**Rationale**: FR-012; briefing §44/§45.
