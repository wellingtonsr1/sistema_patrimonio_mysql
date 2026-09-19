# Relatório de Auditoria: Precedência da Configuração de Backup Automático e Retenção

**Feature**: 024 — Auditoria da Precedência da Configuração de Backup Automático | **Data**: 2026-09-19
**Natureza**: exclusivamente diagnóstica (somente leitura). **Nenhum arquivo de produção foi criado, alterado ou removido.** Nenhuma aplicação executada, nenhuma suíte rodada, nenhuma migration executada, nenhum acesso de escrita a banco.
**Método**: análise estática com evidência citável (`arquivo:linha` + trecho). Todas as linhas citadas foram verificadas nesta auditoria (não herdadas do plan/research).

---

## 1. Resumo executivo

**A arquitetura está correta e funcionando conforme documentada.** A configuração salva pela tela (tabela `backup_config`) é a **única fonte efetiva** do Backup Automático e da Retenção em runtime: o scheduler reavalia a configuração efetiva **a cada ciclo de 30 s** (`backup_scheduler.py:799`), aplicando alterações da tela **sem reinício**. As 8 constantes de `app/config.py:67–87` atuam **exclusivamente como bootstrap/fallback** — em dois papéis bem definidos e ambos aderentes à precedência documentada (persistido → env → default): (1) fallback por campo quando o valor persistido está indefinido (`backup_config_service.py:122–182`), e (2) bootstrap do snapshot de boot quando a leitura do banco falha (`backup_scheduler.py:116–124`). **Nenhuma ocorrência de classe D (constante usada como configuração efetiva) foi encontrada.** Não existe dupla fonte de verdade. Veredito global: **OK**, com 3 achados ATENÇÃO (documentação imprecisa, fallback de boot divergente, env `BACKUP_AUTO_ENABLED` ignorada dinamicamente) — nenhum INCONSISTÊNCIA, RISCO ou BLOQUEADOR.

## 2. Fonte efetiva da configuração (fluxo REAL, com evidência)

```text
Tela: modal #modalBackupConfig (templates/admin/backups.html:153, valores de config_form:840)
   ↓ POST /admin/backups/configuracoes (admin_routes.py:888–963)
   ↓   validação completa antes de escrever (backup_config_service.py:212–251)
   ↓   commit único na linha singleton (backup_config_service.py:255–263)
   ↓   auditoria BACKUP_CONFIGURACAO_ALTERADA before/after (admin_routes.py:925–963)
backup_config (models/backup_config.py:19 — singleton id=1; get_backup_config criação lazy :72–76)
   ↓ get_effective_config(db) — resolução POR CAMPO: persistido → env → default 020
   ↓   (backup_config_service.py:106–198; defaults _DEFAULT_* :25–32)
EffectiveBackupConfig (snapshot imutável — backup_config_service.py:44–57)
   ↓ backup_scheduler.refresh_effective_config() — a cada tick e no start
   ↓   (backup_scheduler.py:93–124; chamadas :790 e :799; _TICK_SECONDS=30 :64)
Scheduler ── decisão de disparo: _eff().auto_enabled / _effective_schedule() / _effective_time() / eff.weekday
         └── Retenção: _apply_retention lê eff.retention_* e eff.keep_pre_restore (:615–628)
```

Este é o fluxo real do código — coincide com o diagrama documentado em `app/config.py:63–65`.

## 3. Análise do config.py — ocorrências das 8 constantes

### 3.1 Inventário exaustivo classificado (rubrica A–H — research R2)

**Varredura executada** (padrões: `BACKUP_AUTO_(ENABLED|SCHEDULE|TIME|WEEKDAY)`, `BACKUP_RETENTION_(DAILY_DAYS|WEEKLY_WEEKS|MONTHLY_MONTHS|KEEP_PRE_RESTORE)`, `get_effective_config`, `backup_config`, `BackupConfig`, `scheduler`, `schedule`, `retention`, `cleanup`, `pre_restore`). Contagem: **44 matches de constantes em `app/`** + testes + docs (listados abaixo). Todas as ocorrências de código/teste individuais; docs agregadas por arquivo (divergência de formato aceita — ver achado AT-2).

#### `BACKUP_AUTO_ENABLED`

| Uso | Local | Trecho | Class. | Justificativa |
|---|---|---|---|---|
| Definição | `app/config.py:67` | `os.getenv("BACKUP_AUTO_ENABLED", "false").strip().lower() == "true"` | **A** | definição; default `False` |
| Fallback | `backup_config_service.py:155` | `auto_enabled=_env_bool(row.auto_enabled)` | **B*** | fallback **implícito**: o campo persistido é **não-null** (`models/backup_config.py:23`), logo a env nunca é consultada por este campo em runtime — a efetiva lê sempre a linha; ver AT-3 |
| Bootstrap | `backup_scheduler.py:117` | `auto_enabled=bool(BACKUP_AUTO_ENABLED)` | **C** | montagem do snapshot de boot quando `get_effective_config` levanta (`:107–112`) |
| Bootstrap | `backup_scheduler.py:32` | import das constantes | **C** | importa exclusivamente para o fallback de boot |
| Teste | `tests/test_backup_config.py:56,151–153` | `monkeypatch.setattr(config, "BACKUP_AUTO_ENABLED", False)`; subprocesso anti-regressão | **G** | fixação hermética + proteção do default real |
| Doc | `README.md:974` | tabela de variáveis | **H** | documentação fiel (default `false`, nasce desativado) |

#### `BACKUP_AUTO_SCHEDULE`

| Uso | Local | Trecho | Class. |
|---|---|---|---|
| A | `app/config.py:70` | `os.getenv("BACKUP_AUTO_SCHEDULE", "daily").strip().lower()` | definição (default `daily`) |
| B | `backup_config_service.py:122` | `schedule = _first_defined(row.schedule, config.BACKUP_AUTO_SCHEDULE)` | fallback por campo com prioridade ao persistido |
| C | `backup_scheduler.py:33,118` | import + `schedule=(BACKUP_AUTO_SCHEDULE if ... in ("daily","weekly") else "daily")` | fallback de boot com validação própria |
| G | `tests/test_backup_config.py:57,122,132`; `tests/test_backup_automatico.py:251` | monkeypatch (válido/inválido) | teste |
| H | `README.md:975` | doc fiel | doc |

#### `BACKUP_AUTO_TIME`

| Uso | Local | Trecho | Class. |
|---|---|---|---|
| A | `app/config.py:74` | `os.getenv("BACKUP_AUTO_TIME", "02:00").strip()` | definição (default `02:00`, America/Recife) |
| B | `backup_config_service.py:132` | `time_value = _first_defined(row.time, config.BACKUP_AUTO_TIME)` | fallback por campo |
| C | `backup_scheduler.py:34,119` | import + `time=(BACKUP_AUTO_TIME if ... len==5 else "02:00")` | fallback de boot com validação própria |
| G | `tests/test_backup_config.py:58,131,246`; `tests/test_backup_automatico.py:246` | monkeypatch (`25:99` → default) | teste |
| H | `README.md:976` | doc fiel | doc |

#### `BACKUP_AUTO_WEEKDAY`

| Uso | Local | Trecho | Class. |
|---|---|---|---|
| A | `app/config.py:77` | `int(os.getenv("BACKUP_AUTO_WEEKDAY", "0"))` | definição (default 0=domingo; semântica 0–6 confirmada em `models/backup_config.py:26`) |
| B | `backup_config_service.py:142` | `weekday = _first_defined(row.weekday, config.BACKUP_AUTO_WEEKDAY)` | fallback por campo |
| C | `backup_scheduler.py:35,120` | import + `weekday=(BACKUP_AUTO_WEEKDAY if 0 <= ... <= 6 else 0)` | fallback de boot com validação própria |
| G | `tests/test_backup_config.py:59,133`; `tests/test_backup_automatico.py` (semanal) | monkeypatch (`9` → default) | teste |
| H | `README.md:977,987` | doc fiel (0=domingo…6=sábado; weekly dispara no dia configurado) | doc |

#### `BACKUP_RETENTION_DAILY_DAYS`

| Uso | Local | Trecho | Class. |
|---|---|---|---|
| A | `app/config.py:81` | `int(os.getenv(..., "30"))` | definição (default 30) |
| B | `backup_config_service.py:170–171` | `_effective_int(row.retention_daily_days, config.BACKUP_RETENTION_DAILY_DAYS, 30, ...)` | fallback por campo (env vence default; nunca o persistido) |
| C | `backup_scheduler.py:36,121` | import + fallback de boot (`>=1` senão 30) | bootstrap |
| G | `tests/test_backup_config.py:60,110,134,255` | monkeypatch (7; −3 → default) | teste |
| H | `README.md:978` | doc fiel | doc |

#### `BACKUP_RETENTION_WEEKLY_WEEKS`

| Uso | Local | Trecho | Class. |
|---|---|---|---|
| A | `app/config.py:82` | `int(os.getenv(..., "12"))` | definição |
| B | `backup_config_service.py:174–175` | idem padrão `_effective_int` | fallback |
| C | `backup_scheduler.py:39,122` | import + boot (`>=1` senão 12) | bootstrap |
| G | `tests/test_backup_config.py:61` | monkeypatch | teste |
| H | `README.md:979` | doc fiel (âncora semana ISO) | doc |

#### `BACKUP_RETENTION_MONTHLY_MONTHS`

| Uso | Local | Trecho | Class. |
|---|---|---|---|
| A | `app/config.py:83` | `int(os.getenv(..., "12"))` | definição |
| B | `backup_config_service.py:178–179` | idem padrão `_effective_int` | fallback |
| C | `backup_scheduler.py:38,123` | import + boot (`>=1` senão 12) | bootstrap |
| G | `tests/test_backup_config.py:62` | monkeypatch | teste |
| H | `README.md:980` | doc fiel (âncora mensal) | doc |

#### `BACKUP_RETENTION_KEEP_PRE_RESTORE`

| Uso | Local | Trecho | Class. |
|---|---|---|---|
| A | `app/config.py:87` | `int(os.getenv(..., "0"))` | definição (0 = preservar todos) |
| B | `backup_config_service.py:182–185` | `_effective_int(..., "keep")` (faixa ≥0) | fallback por campo |
| C | `backup_scheduler.py:37,124` | import + boot (`max(0, ... or 0)`) | bootstrap |
| D? | — | **nenhum uso direto na política** | **não-D** |
| G | `tests/test_backup_config.py:63,135`; `tests/test_backup_retencao.py:184,203` | monkeypatch; política keep-N | teste |
| H | `README.md:981,995` | doc fiel | doc |

### 3.2 Consumo da configuração efetiva (sem passagem pelas constantes)

`get_effective_config` (`backup_config_service.py:106`): 5 chamadores — rota da listagem `admin_routes.py:840` (`create=False`), POST `admin_routes.py:888` e `:925`, scheduler `backup_scheduler.py:109`, retorno do salvamento `backup_config_service.py:265`. Total: **15 matches** de `get_effective_config` em `app/` (todos listados).

### 3.3 Falsos positivos excluídos da classificação (prova de exaustão)

- `app/services/audit_service.py:69–70,90–91` — `ACTION_BACKUP_AUTO_SUCCESS/FAILED` ("BACKUP_AUTOMATICO_SUCESSO/FALHA"): **rótulos de eventos de auditoria**, não configuração. Consumidos em `backup_scheduler.py:460,502`.
- `backup_scheduler.py:625–627` — variáveis locais `daily_days/weekly_weeks/monthly_months = _effective_int(eff.retention_*, ...)`: **consumo da efetiva** (nome embutido só para mensagem de log), não leitura de constante.
- `app/main.py:35` e `specs/020/021/022/*` — menções textuais/comentários (contexto histórico; não são uso de código).
- `tests/test_backup_*` extras (`test_backup_manual.py`, `test_backup_records.py`, `test_backup_restore.py`) — não referenciam as 8 constantes (confere a varredura).

## 4. Análise do scheduler — fonte real de cada decisão

| Decisão | Fluxo real (evidência) | Constante usada diretamente? |
|---|---|---|
| **Ativado?** | loop `backup_scheduler.py:796–800`: `refresh_effective_config()` por tick → `enabled = _eff().auto_enabled` → efetiva (`row.auto_enabled` não-null da linha, commitada pelo POST) → **SIM usa a configuração da tela** | **NÃO** (constante só no boot-fallback `:117`) |
| **Frequência** | `_effective_schedule()` (`:136–137`) → `eff.schedule`; usada em `_next_run_utc` (`:175,213`) e no log do start (`:794`) | **NÃO** (`:118` só no boot) |
| **Horário** | `_effective_time()` (`:140`) → `eff.time` ("HH:MM" America/Recife) → convertido para UTC nas comparações (`:174,243,271,791`) | **NÃO** (`:119` só no boot) |
| **Dia da semana** | `eff.weekday` 0–6 em `_next_run_utc`/weekly (`:213`) — semântica **0=domingo…6=sábado** (`models/backup_config.py:26`, `config.py:76`) | **NÃO** (`:120` só no boot) |
| **Catch-up** | 1×/start (`:802–821`): se `enabled` e ciclo corrente sem sucesso → worker +60 s (`_CATCHUP_DELAY_SECONDS=60`, `:67`); lê a efetiva do momento | **NÃO** |
| **Fluxo resumido** | `Scheduler → get_effective_config() → backup_config → configuração efetiva` — **exatamente o fluxo documentado** | ✔ |

## 5. Análise da retenção — fonte real de cada valor

`_apply_retention` (`backup_scheduler.py:615`), executada após cada ciclo (`_apply_retention_after_cycle` `:767–776`; chamadas `:472,482,490`):

| Valor | Fonte real | Evidência |
|---|---|---|
| Janela diária | `eff.retention_daily_days` (efetiva) | `:625` |
| Janela semanal | `eff.retention_weekly_weeks` (efetiva) | `:626` |
| Janela mensal | `eff.retention_monthly_months` (efetiva) | `:627` |
| `keep_pre_restore` | `eff.keep_pre_restore` (efetiva) — consumo em `:628` e `:700–702` (preserva todos se 0; remove excedente além dos N mais recentes) | `:628` |

**Nenhum dos 4 valores lê `config.BACKUP_RETENTION_*` diretamente na decisão.** A política GFS (âncoras semanal ISO/mensal, guarda do último válido, integridade antes de remover, marcação `removed_at`) está em `:615–736` — fora do escopo desta auditoria, apenas confirmado que consome a efetiva. Cobertura por testes: `tests/test_backup_retencao.py:559` (`test_q_retencao_usa_limites_da_efetiva`) e `:184,203` (política pre-restore).

## 6. Análise da tela — fluxo real de persistência

1. **Recebimento**: `POST /admin/backups/configuracoes` (`admin_routes.py:888–963`), campos como `Form(...)` — ex.: `keep_pre_restore: int = Form(0)` (`:920`); guard da rota (mesma permissão `backup.gerenciar` da página).
2. **Validação**: `save_backup_config` valida **todos os campos antes de qualquer escrita** (`backup_config_service.py:212–251` — `ValueError` não persiste nada; horário HH:MM 00:00–23:59, weekday 0–6, retenções ≥1, keep ≥0).
3. **Persistência**: linha singleton `id=1` da tabela **`backup_config`** (model `BackupConfig`, `models/backup_config.py:19`), aplicação dos 8 campos + `updated_by`/`updated_at` UTC e **commit único** (`:255–263` — atômico; última escrita válida prevalece).
4. **Auditoria**: `BACKUP_CONFIGURACAO_ALTERADA` com before/after (`admin_routes.py:925,963`).
5. **Leitura posterior**: efetiva resolvida por campo (`get_effective_config` `:106–198`); sem valor persistido → env → default 020 (`_DEFAULT_*` `:25–32`); leitura pura sem criação via `create=False` (`get_backup_config` `:59–76`, usado na listagem `admin_routes.py:840`).
6. **Chegada ao scheduler**: renovação do snapshot **a cada tick de 30 s** (`backup_scheduler.py:799`) — sem reinício. **Chegada à retenção**: os mesmos limites via o mesmo snapshot (`:625–628`), executada pós-ciclo.

Fluxo real = `Tela → POST → Route → Service → Persistência → get_effective_config() → Scheduler/Retention` — **idêntico ao esperado pelo briefing §13**.

## 7. Análise de precedência — DOCUMENTADO × REAL

| # | Afirmação documentada | Fonte | Veredito |
|---|---|---|---|
| 1 | Precedência única por campo: persistido (tela) → env → default 020 | `README.md:972–973`; `app/config.py:63–66`; `backup_config_service.py:3–10` | **FIEL** — confirmado em código (`_first_defined`/`_effective_int`, `:122–185`) |
| 2 | `BACKUP_AUTO_ENABLED` default `false`, sistema nasce desativado | `README.md:974`; `config.py:66–67` | **FIEL** — `os.getenv(...,"false")` → `False`; teste anti-regressão via subprocesso (`test_backup_config.py:144–204`) |
| 3 | Agendador: thread interna, verifica a cada 30 s, weekly no dia configurado | `README.md:987` | **FIEL** — `_TICK_SECONDS = 30` (`backup_scheduler.py:64`), loop `:796–826`, weekly `:213` |
| 4 | Catch-up único ~60 s após start quando ciclo sem sucesso | `README.md:988` | **FIEL** — `_CATCHUP_DELAY_SECONDS = 60` (`:67`), catch-up `:802–821` |
| 5 | Snapshot renovado por tick — aplicação sem reinício | `docs/ARQUITETURA_E_MANUTENCAO.md:1215`; `backup_scheduler.py:786–788` | **FIEL** — `refresh_effective_config()` em `:790/:799` |
| 6 | Tabela `backup_config`: singleton, campos None = "não definido" → fallback env/default; listagem lê com `create=False` | `docs/ARQUITETURA_E_MANUTENCAO.md:264` | **FIEL** — model `:21–39`; `get_backup_config(create=False)` `:59–76` |
| 7 | "as env `BACKUP_*` são fallback **da primeira inicialização**" | `docs/GUIA_DE_MANUTENCAO.md:113` | **IMPRECISO** — as envs são fallback **por campo e a cada resolução** enquanto o campo não estiver persistido (ex.: campo salvo `None` cai na env dinamicamente, `backup_config_service.py:122`); a frase restringe o papel ao 1º boot → **achado AT-1** |
| 8 | Pré-restauração preservada por padrão; `KEEP_PRE_RESTORE > 0` → N mais recentes | `README.md:995`; `config.py:86–87` | **FIEL** — `:628,700–702` (fonte = efetiva; o nome da env no README é a forma de referenciar o campo administrável) |
| 9 | Env inválida cai no default sem derrubar o sistema | `README.md:994` | **FIEL** — `_env_time_valid`/`_effective_int` com log técnico (`backup_config_service.py:83–102,148–166`); não levanta |

**ORDEM DOCUMENTADA**: persistido → env → default.
**ORDEM REAL ENCONTRADA**: persistido → env (se campo persistido é `None`; para `auto_enabled`, nunca — AT-3) → default 020; adicionalmente **fallback de boot** (env/default) apenas quando a leitura do banco falha (`backup_scheduler.py:107–124`).
**Divergência estrutural**: nenhuma. A única diferença real vs documentada é o fallback de boot (não mencionado na precedência do README), que é um caminho de exceção com os mesmos valores — AT-2.

## 8. Dupla fonte de verdade

**Não existe** — justificativa com evidência:

- **Consumidores runtime** (scheduler `:800,794` e retenção `:625–628`) leem **exclusivamente** o `EffectiveBackupConfig` resolvido por `get_effective_config` — nenhuma decisão lê `config.BACKUP_*` diretamente (seções 4/5).
- **Cenário do briefing §19.1** (tela DESATIVADO + env `BACKUP_AUTO_ENABLED=true` + scheduler lendo a env): **impossível** — `enabled = _eff().auto_enabled` (`:800`) vem da linha persistida (campo não-null, `models/backup_config.py:23`), que o POST grava (`backup_config_service.py:256`).
- **Cenário do briefing §19.2** (tela 03:00 + scheduler usando 02:00): **impossível** em regime normal — snapshot renovado por tick (`:799`); `_effective_time()` (`:791`) reflete o novo valor no próximo ciclo (≤ 30 s).
- **Único caminho em que env/default decidem** (ALÉM do fallback por campo documentado): o **fallback de boot** (`:116–124`) quando `get_effective_config` levanta (ex.: banco indisponível no 1º tick) — nesse caso o scheduler usa env/default até a próxima renovação bem-sucedida. Comportamento crash-safe intencional (`:94–97`), com log "Falha ao ler configuração efetiva — mantendo snapshot anterior" (`:110`). Registrado como **AT-2**.
- Defaults do service ≠ constantes do config **por design** (duplicação intencional — research R6): a env válida vence o **default**, jamais o **persistido**; a env inválida é tratada como ausente e cai no default (`:148–166`), protegido por testes (`test_backup_config.py:129–142,246–255`).

## 9. Cache e atualização

- **Cache do service**: **não existe** — cada `get_effective_config` consulta a tabela (`backup_config_service.py:108`); o valor reflete o banco no instante da chamada.
- **Cache do scheduler**: **existe, por design** — `_current_effective` module-level (`backup_scheduler.py:90`), snapshot imutável (`EffectiveBackupConfig` frozen, `backup_config_service.py:44`). Criado **lazidamente** no 1º uso (`_eff()` `:128–133`); **renovado no start** (`:790`) e **a cada tick de 30 s** (`:799`).
- **Janela máxima de desatualização: 30 s** (`_TICK_SECONDS = 30`, `:64`). Cenário do briefing §16 (altera 02:00 → 03:00): o banco passa a valer 03:00 no commit (`backup_config_service.py:262`); o scheduler usa 03:00 **no próximo tick (≤ 30 s), sem reinício** — confirmado por teste (`test_backup_config.py:242` `test_aplicacao_dinamica_sem_reinicio`, e `test_k_..._persiste` `:207`).
- **Modo de falha**: renovação que levanta **mantém o snapshot anterior** (`:107–112`) — nunca fica sem configuração; sem snapshot anterior, monta o de boot via env/default (`:116–124`).
- **Pós-reinício**: configuração persistida volta a valer (singleton no banco); snapshot reconstruído do banco no 1º tick — testes `test_r_persistencia_sobrevive_a_reinicio` (`test_backup_config.py:223`) e `test_l_precedencia_no_scheduler` (`:337`).

## 10. Testes existentes (inventário — NÃO executados)

| Arquivo | Testes relevantes | Tema (briefing §26) |
|---|---|---|
| `tests/test_backup_config.py` | `test_primeiro_uso_aplica_defaults_da_020` (:80); `test_precedencia_persistido_vence_env_vence_default` (:105); `test_env_invalida_cai_no_default_sem_crash` (:129); `test_anti_regressao_default_desativado_no_codigo_real` (:144 — subprocesso isolado); `test_k_alteracao_pela_interface_persiste` (:207); `test_r_persistencia_sobrevive_a_reinicio` (:223); `test_aplicacao_dinamica_sem_reinicio` (:242); inválidos/limítrofes (:255, :265, :281); `test_falha_de_persistencia_mantem_estado_anterior` (:296); `test_l_precedencia_no_scheduler` (:337); snapshot consistente (:431); auditoria before/after (:444); RBAC (:463); 022 modal/`create=False` (:581–:796) | **persistida ✔ fallback ✔ defaults ✔ precedência ✔ tela ✔ inválidos ✔ instalação-nova ✔** |
| `tests/test_backup_automatico.py` | disparo no horário (:69); desativado não dispara (:104); next-run diário/semanal determinístico a partir da efetiva (config `test_d`/`test_e` :402,415 + arquivo :186,212); catch-up (:212); config inválida → default sem crash (:234); concorrência/restore guard (:267,289,312) | **scheduler ✔ precedência ✔ inválidos ✔** |
| `tests/test_backup_retencao.py` | política GFS: âncoras (:122), janela diária (:154), manuais preservados (:167), pre-restore default/keep-N (:184,:203), guarda último válido (:232), histórico (:264), PARCIAL (:293), integridade (:331), `test_q_retencao_usa_limites_da_efetiva` (:559) | **retenção ✔ (usa efetiva)** |
| `tests/test_backup_monitoramento.py` | indicadores da página (:53), legado (:78), sem segredos (:129), `retention_monitoring_summary` unitário (:141) | **apresentação da efetiva ✔** |

**Cobertura da precedência: COMPLETA** — todos os 9 temas do briefing §26 têm testes (não executados nesta auditoria; inventário por leitura). Nenhum teste alterado.

## 11. Problemas encontrados

| ID | Rótulo | Achado | Evidência |
|---|---|---|---|
| — | **OK** | Arquitetura de precedência implementada exatamente como documentada; tela = fonte única; sem classe D | seções 2–8 |
| **AT-1** | **ATENÇÃO** | `docs/GUIA_DE_MANUTENCAO.md:113` diz que as env `BACKUP_*` são fallback "da primeira inicialização", mas são fallback **por campo, a cada resolução**, enquanto o campo não estiver persistido (dinâmico, não só no boot) | `backup_config_service.py:122–185` |
| **AT-2** | **ATENÇÃO** | O **fallback de boot** (`backup_scheduler.py:116–124`) não consta da precedência documentada (README/config): se a leitura do banco falha no 1º tick, o scheduler usa env/default até a próxima renovação — caminho de exceção crash-safe e coerente em valores, porém não documentado como parte do fluxo | `:107–124`; `config.py:63–66` |
| **AT-3** | **ATENÇÃO** | `BACKUP_AUTO_ENABLED` é o único campo **não-nullable** (`models/backup_config.py:23`) — logo sua env **nunca** é consultada dinamicamente pela efetiva (`backup_config_service.py:155` lê direto a linha), diferente dos outros 7 campos. A env vale efetivamente só no fallback de boot e como referência operacional. Comportamento correto (estado sempre conhecido), mas assimétrico em relação aos demais campos | `:23`; `:155` vs `:122` |
| — | INCONSISTÊNCIA / RISCO / BLOQUEADOR | **Nenhum encontrado** | — |

## 12. Recomendação (para eventual tarefa futura — NADA implementado nesta auditoria)

1. **AT-1** — Reescrever a frase de `docs/GUIA_DE_MANUTENCAO.md:113` para: "as env `BACKUP_*` são fallback **por campo**, aplicadas a cada resolução da configuração efetiva enquanto o campo correspondente não estiver persistido (e no fallback de boot do scheduler)". Correção puramente documental (Constitution XI — tarefa própria).
2. **AT-2** — Acrescentar uma linha na precedência documentada (README §Backup automático e comentário de `config.py`) mencionando o fallback de boot do scheduler ("em caso de falha de leitura do banco, o scheduler mantém o último snapshot ou usa env/default"). Documental.
3. **AT-3** — Opcional: documentar a assimetria do campo `auto_enabled` (não-nullable → env sempre ignorada dinamicamente). Nenhuma mudança de código é recomendada — o comportamento é seguro e testado.
4. **Constantes** — Todas as 8 **DEVE SER MANTIDAS COMO FALLBACK**: são o valor inicial de instalações novas (antes da primeira configuração pela tela), o fallback por campo, o bootstrap do scheduler sem banco, a interface de deploys automatizados (README:973) e são exercitadas pela suíte de testes. **Nenhuma é POTENCIALMENTE REMOVÍVEL** (ver tabela §13).

---

## Tabela das variáveis de ambiente (briefing §18)

| Variável | Necessária? | Função atual | Fonte efetiva | Observação |
|---|---|---|---|---|
| `BACKUP_AUTO_ENABLED` | **SIM** (manter) | Valor inicial/fallback; bootstrap do scheduler sem banco | Persistido (campo não-null — env nunca consultada dinamicamente, AT-3) | Default `false` correto (nasce desativado); protegido por teste anti-regressão |
| `BACKUP_AUTO_SCHEDULE` | **SIM** (manter) | Fallback por campo + boot | Persistido → env → `daily` | Útil em deploys automatizados antes da 1ª configuração |
| `BACKUP_AUTO_TIME` | **SIM** (manter) | Fallback por campo + boot | Persistido → env → `02:00` | Inválida → default com log (nunca crash) |
| `BACKUP_AUTO_WEEKDAY` | **SIM** (manter) | Fallback por campo + boot | Persistido → env → `0` | Semântica 0=domingo…6=sábado |
| `BACKUP_RETENTION_DAILY_DAYS` | **SIM** (manter) | Fallback por campo + boot | Persistido → env → `30` | |
| `BACKUP_RETENTION_WEEKLY_WEEKS` | **SIM** (manter) | Fallback por campo + boot | Persistido → env → `12` | |
| `BACKUP_RETENTION_MONTHLY_MONTHS` | **SIM** (manter) | Fallback por campo + boot | Persistido → env → `12` | |
| `BACKUP_RETENTION_KEEP_PRE_RESTORE` | **SIM** (manter) | Fallback por campo + boot | Persistido → env → `0` | 0 = preservar todos (conservador) |

## Respostas-chave (briefing §28)

| # | Pergunta | Veredito | Evidência principal |
|---|---|---|---|
| 1 | A configuração da tela é a fonte efetiva? | **SIM** | scheduler por tick `backup_scheduler.py:799–800`; retenção `:625–628` |
| 2 | `config.py` é apenas fallback? | **SIM** | únicos usos: fallback por campo (`backup_config_service.py:122–182`) e boot (`backup_scheduler.py:116–124`); zero classe D |
| 3 | Existe dupla fonte de verdade? | **NÃO** | seção 8 — todos os cenários-limite evidenciados |
| 4 | O scheduler usa a configuração da tela? | **SIM** | `_eff().auto_enabled` `:800`; `_effective_schedule/_time` `:136–140` |
| 5 | A retenção usa a configuração da tela? | **SIM** | `eff.retention_*` `:625–628`; teste `test_backup_retencao.py:559` |
| 6 | `get_effective_config()` realmente centraliza a configuração? | **SIM** | 5 chamadores (§3.2); resolução por campo `:106–198` |
| 7 | Alguma constante pode ser removida? | **NÃO** — todas **DEVE SER MANTIDA COMO FALLBACK** | §12.4 (bootstrap, instalação nova, deploys, testes) |

## Critérios de conclusão (briefing §31)

- [x] **Onde a tela persiste** — tabela `backup_config`, linha singleton `id=1` (`backup_config_service.py:255–263`; model `models/backup_config.py:19`)
- [x] **Onde a efetiva é lida** — `get_effective_config` (`backup_config_service.py:106–198`); scheduler `backup_scheduler.py:109` por tick
- [x] **`get_effective_config()` existe e funciona como documentado** — precedência persistido→env→default por campo, validação, `create` (`:59–198`)
- [x] **Scheduler usa a efetiva** — `:799–800,794,791` (nunca constante direta na decisão)
- [x] **Retenção usa a efetiva** — `:625–628`
- [x] **Função real das constantes** — A definição + B fallback por campo + C bootstrap de boot + G teste + H doc (§3)
- [x] **Env = fallback ou efetiva?** — fallback (por campo e de boot); nunca efetiva com persistido definido (§13)
- [x] **Dupla fonte de verdade** — não existe (seção 8)
- [x] **Cache** — snapshot `_current_effective` no scheduler (`:90`), renovado por tick (`:799`); sem cache no service
- [x] **Aplicação sem reinício** — sim, ≤ 30 s (`_TICK_SECONDS=30` `:64`; `:799`; teste `test_backup_config.py:242`)
- [x] **Instalação nova sem `backup_config`** — criação lazy `BackupConfig(id=1, auto_enabled=False)` (`backup_config_service.py:72–76`) → campos None → env → default; **nasce DESATIVADA** (`config.py:67`)
- [x] **Defaults coerentes** — `false/daily/02:00/0/30/12/12/0` idênticos em `config.py:67–87` e `_DEFAULT_*` (`backup_config_service.py:25–32`); documentados no README (`:974–981`); conservadores
- [x] **Testes da precedência** — completos (9/9 temas, §10)
- [x] **Risco de a tela ser ignorada** — nenhum em operação normal; único desvio = fallback de boot em falha de banco (AT-2, crash-safe)

---

**Conformidade da auditoria**: análise 100% estática; zero diff em produção (`git status` limpo fora de `specs/024-auditoria-config-backup/` — verificado em 2026-09-19); nenhuma credencial citada; suíte não executada nem alterada.
