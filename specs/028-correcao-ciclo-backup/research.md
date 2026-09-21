# Phase 0 Research: Correção do Ciclo de Backup, Restauração e Agendamento Automático

**Feature**: 028-correcao-ciclo-backup | **Date**: 2026-09-18

Diagnóstico executado por leitura do código real nesta sessão (evidências com arquivo/linha).
Nenhum [NEEDS CLARIFICATION] permanece.

## 1. Diagnóstico conclusivo das três causas raiz

| # | Fato (prova) | Evidência |
|---|---|---|
| **D1** | **Causa A — substituição do banco sem reconciliação**: `BackupRecord` só é criado em 2 pontos, ambos dentro de `generate_backup` (L373 SUCCESS, L404 FAILURE). O ciclo de restauração cria o registro do pré-restauração ANTES do import (L1142: `generate_backup(..., backup_type=BACKUP_TYPE_PRE_RESTAURACAO)`), depois o `_run_mysql_import` substitui o conteúdo do banco pelo snapshot do dump — que não contém registros criados após a sua geração. Não existe NENHUMA reconciliação/refresh de registros após o import em `backup_service.py`. | grep `BackupRecord(` (2 ocorrências) + `_execute_restore_cycle` L1095–1224 |
| **D2** | **Causa A — prova empírica anterior**: na investigação do incidente de 2026-09-18 (feature 019) os IDs da trilha provaram que o banco pós-restore continha apenas o conteúdo do snapshot (eventos id 1–79 tirados às 15:16:53); eventos do próprio ciclo (INICIADO, pré-restauração) sumiram da tabela. Mesmo mecanismo atinge `backup_records`. | Registro da sessão 019 + mecanismo do import (D1) |
| **D3** | **Causa B — condição de disparo impossível**: `_next_run_utc` devolve SEMPRE a próxima ocorrência ESTRITAMENTE futura (`if candidate_utc > now: return`; daily: `if candidate_utc <= now: +1 dia`). O loop dispara com `next_run = _next_run_utc(_clock()); if _clock() >= next_run:` — recalculado a cada tick ⇒ `agora >= futuro` é impossível ⇒ o disparo por horário NUNCA ocorre. | `backup_scheduler.py` `_scheduler_loop` (bloco final) + `_next_run_utc` |
| **D4** | O catch-up de inicialização FUNCIONA porque usa outro critério: `_should_catch_up` = "horário do ciclo corrente já passou E o ciclo não tem SUCCESS" (semântica de execução devida correta). `next_run` é usado apenas para exibição em `scheduler_status()`. | `_should_catch_up` + `scheduler_status` |
| **D5** | **Causa C — whitelist sem a tela**: `_MAINTENANCE_WHITELIST_PREFIXES` inclui `/admin/backups/restaurar/status`, `/login`, `/logout`, `/health`, `/static/` — NÃO inclui `/admin/backups`. O POST de restauração redireciona para `/admin/backups?info=Restauração agendada...` ⇒ a tela de acompanhamento recebe 503 (log observado pelo usuário). | `main.py` L58–64 |
| **D6** | O gate de manutenção é prefixo + método-cego (`path.startswith(p)` para qualquer método). Adicionar `/admin/backups` à tupla sem refinar isentaria TAMBÉM os POSTs (gerar/restaurar/configurações) — violaria FR-018. A isenção precisa ser: caminho exato + somente leitura (GET/HEAD). | `maintenance_mode_middleware` L68–92 |
| **D7** | O contexto da rota depende de banco em 3 pontos: `types_by_filename` (query `BackupRecord`), `retention_monitoring_summary(db)` (queries), `config_form=get_effective_config(db, create=False)` (query). Durante o import, essas consultas podem falhar (banco em substituição) ⇒ a tela degradada não pode executá-las. `scheduler_status()` é seguro (nunca lança — `refresh_effective_config` engole exceções). Template JÁ É SEGURO para `config_form=None`: todos os usos estão guardados (visão rápida L103 `{% if config_form and config_form.auto_enabled %}`; modal inteiro envolto por `{% if config_form %}` L155); `retention_summary` (L112/L122–126) e `types_by_filename` (L271) também guardados — **nenhum ajuste de template é necessário** além do estado vazio da tabela. | `admin_routes.py` L803–841 + `backups.html` L103/L112/L122–126/L155/L271 |
| **D8** | **Baseline real medida nesta sessão: 543 passed / 1 failed** (`test_anti_regressao_default_desativado_no_codigo_real` — defasagem PRÉ-existente, não desta feature). Patamar pós-028 = 543 + novos verdes, mesma 1. | `python -m pytest tests/ -q` nesta sessão |

**Conclusão**: as três causas são independentes, cada uma com correção localizada — nenhuma refatoração do módulo é necessária ou justificada.

## 2. Decisões de estratégia (justificadas, com alternativas rejeitadas)

### R1 — US1: reconciliação pós-import com captura pré-import (escolhida)

**Decisão**: dentro do worker existente `_execute_restore_cycle`, capturar ANTES da drenagem/import um snapshot **em memória** dos registros ativos (`removed_at IS NULL`) — `filename → {backup_type, status, timestamp, size_bytes, sha256}` — e, após o import ter executado (antes da liberação da manutenção), reconciliar: para cada arquivo do snapshot ainda presente no disco, (a) registro existente com tipo divergente → UPDATE do campo; (b) registro inexistente → INSERT com os dados capturados (única escrita via service/orm existente, respeitando UNIQUE de filename). Best-effort: falha de reconciliação é logada e NUNCA altera o resultado/auditoria do ciclo.

**Pontos de aplicação** (contrato §1): captura entre a auditoria PRE_RESTORE e a drenagem (inclui o registro do próprio pré-restauração, criado em D1-L1142); reconciliação logo após `validate_post_restore`, cobrindo sucesso e falha de validação (o banco foi substituído nos dois casos).

**Por quê**: é o único caminho que restaura a informação REAL (tipo persistido antes da substituição) sem inferência por nome — exigência FR-004 — e sem tocar o dump.

**Alternativas rejeitadas**:
- *Inferir tipo pelo padrão do nome* — proibida (FR-004; todos os tipos compartilham o mesmo padrão de nome, a informação não existe no nome).
- *Incluir `backup_records` no dump* — alteraria o conteúdo operacional do dump com metadados nossos e contaminaria o banco de destino com registros de outra instância (além de exigir mudança no gerador de dump — escopo maior).
- *Fallback para MANUAL* — proibido (mascara perda real; briefing §26).
- *Reconciliar fora do worker (1º request pós-restore)* — exporia a correção a concorrência e transformaria request em escritor (viola camadas/II-III); o worker já é o dono do ciclo.

### R2 — US1: escopo da captura = registros ATIVOS (decisão de borda)

**Decisão**: capturar somente registros com `removed_at IS NULL` (arquivos válidos em disco). Registros removidos pela retenção permanecem perdidos após o import — porém seus ARQUIVOS também foram removidos do disco; o caso residual (arquivo presente por falha histórica de `unlink`) é aceito e exibido como "—" (legítimo: sem registro recuperável). Documentado como limitação, não criado mecanismo extra.

### R3 — US2: disparo por "execução devida" com marca de ciclo tentado (escolhida)

**Decisão**: substituir o bloco de disparo do loop pelo mesmo critério do catch-up (`_should_catch_up(now, db)` — D4), com sessão curta por tick (padrão `refresh_effective_config`), acrescido de um controle em memória `_attempted_cycle_keys: set` (chave = início UTC da janela do ciclo corrente): um ciclo só dispara se ainda não foi tentado neste processo. O disparo (e o catch-up) marca o ciclo como tentado.

**Por quê**: reutiliza a semântica correta já existente (D4), preserva o ciclo de 30 s, a thread única e as guardas (FR-011/FR-012); a marca de ciclo evita (i) corrida catch-up (60 s) × disparo normal no mesmo ciclo (FR-013 — sem dupla execução) e (ii) retry a cada 30 s após falha (evita tempestade de FAILURE/auditoria — briefing §11: um disparo por ciclo). Crash/restart limpa por construção (mesma filosofia da 019).

**Alternativas rejeitadas**:
- *`agora >= próximo_meio-dia_fixo` recomputado só quando muda de ciclo* — recriaria em miniatura o mecanismo de janela já existente (`_cycle_window_utc`/`_cycle_has_success`), duplicando lógica (proibido briefing §9).
- *Remover o catch-up e deixar o disparo normal cobrir startup* — o briefing §12 exige preservar o catch-up existente e diferenciá-lo do disparo normal; mantido intacto.
- *Segundo agendador/cron externo* — proibido (§10, FR-011).

### R4 — US3: isenção somente-leitura e específica no gate + modo degradado na rota (escolhida)

**Decisão**: (1) o gate de manutenção passa a permitir **apenas** `GET`/`HEAD` no caminho exato `/admin/backups` (caso especial explícito e comentado — D6 mostra que a tupla de prefixos não pode receber o caminho cru); (2) a rota GET, quando a manutenção está ativa (`restore_status()`), monta o contexto em **modo degradado** sem tocar o banco: `types_by_filename={}`, `retention_summary={}`, `config_form=None`, mantendo `restore_status` (fonte do banner/polling existente) e `auto_status` (seguro — D7); (3) template: apenas o estado vazio da tabela (os usos de `config_form`, `retention_summary` e `types_by_filename` JÁ são guardados — D7). Botões desabilitados e polling da 019 permanecem (reuso integral do mecanismo de status — FR-016).

**Por quê**: cumpre a mensagem prometida ao operador ("acompanhe o resultado nesta tela"), mantém a permissão `backup.gerenciar` (as dependencies do router continuam valendo — o middleware NÃO concede acesso), não libera nenhuma escrita (FR-018/019) e preserva o 503 legítimo para todo o resto (FR-022).

**Alternativas rejeitadas**:
- *Adicionar `/admin/backups` à tupla de prefixos* — isentaria POSTs (D6) ⇒ viola FR-018.
- *Página nova de acompanhamento* — criaria segunda tela/mechanismo de status (proibido §17/FR-016).
- *Desligar manutenção para a tela* — remove a proteção (proibido §16/FR-017).

### R5 — Aviso de análise estática `EffectiveBackupConfig` (FR-015)

**Decisão**: manter os imports lazy de runtime como estão (não há ciclo real hoje — `backup_config_service` não importa o scheduler; lazy é prevenção) e corrigir APENAS a referência de tipagem de `_eff()` com `TYPE_CHECKING` (`from typing import TYPE_CHECKING; if TYPE_CHECKING: from ... import EffectiveBackupConfig`). Zero alteração de arquitetura de imports.

### R6 — Sem auditoria nova (escopo)

Reconciliação será observável por auditoria indireta (eventos do ciclo) e testes. Evento dedicado `BACKUP_REGISTROS_RECONCILIADOS` registrado como **backlog** (fora do escopo aprovado da 028) — Constituição I.

### R7 — Fuso e nomes

Persistência continua UTC (`now_utc`), exibição via `| localtime`; padrão de nome `_BACKUP_NAME_RE` inalterado. Nenhuma decisão nova de tempo.

### R8 — Testes: estratégia

Unitários/integração nos padrões existentes (`test_backup_restore.py`, `test_backup_automatico.py`, `test_backup_manual.py`): worker com `import_executor`/`security_backup_executor` injetados (padrão 017/019), relógio injetável do scheduler (`start_scheduler(clock=...)`), `TestClient` para o gate/rota degradada. Monkeypatch de `SessionLocal` → `TestingSessionLocal` onde o worker roda em thread (padrão 018/019 — lição conftest). Nenhum teste existente enfraquecido; os 3 testes adaptados da 019 continuam valendo.
