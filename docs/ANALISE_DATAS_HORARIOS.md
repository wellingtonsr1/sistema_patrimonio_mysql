# Relatório Técnico — Análise Completa de Datas e Horários — SisPatrimônio Pro

> **Data da análise:** 15/09/2026
> **Natureza:** 100% somente leitura / diagnóstico. Nenhum arquivo foi criado, alterado ou removido; nenhuma consulta de escrita foi executada no banco; nenhuma configuração foi modificada.
> **Escopo:** Todo o projeto (`app/`, `tests/`, templates, serviços, modelos, rotas, relatórios, importações, movimentações, inventário, auditoria, autenticação/sessões e configurações), sem limite aos módulos de Inventário e Auditoria.
> **Relatório irmão (escopo reduzido):** `docs/ANALISE_TIMEZONE_INVENTARIO_AUDITORIA.md`

---

## A. Resumo executivo

O sistema usa **dois padrões simultâneos, sem conversão em nenhuma etapa**:

1. **UTC (`datetime.utcnow()`)** — usado por **todos os 19 defaults de models** e pelos services de **Auditoria, Inventário, Autenticação, Sessões, AD e Manutenção**. Esses valores são exibidos "crus" nos templates → aparecem **3h adiantados**.
2. **Hora local (`datetime.now()`)** — usado por **Movimentações (via services), Importação e Relatórios (carimbo "Gerado em")**. Esses valores são exibidos "crus" → aparecem **corretos**.

Todas as **28 colunas de data** do banco são `DATETIME` **sem fuso, sem default no banco, sem conversão automática** (verificado em `information_schema`). Não existe filtro Jinja de data, não existe JS manipulando datas, não existe configuração de timezone em lugar nenhum. A leitura é sempre transparente: o que foi gravado é o que é exibido.

Resultado prático atual: **não há padronização, e a "correção visual" que os usuários veem em Movimentações é um acidente do uso de `now()`**, não uma decisão arquitetural.

---

## B. Inventário de todas as fontes de data/hora

### B.1 — Geração em UTC (`datetime.utcnow()`), naive

| Arquivo | Linha | Mecanismo | Módulo | Finalidade | Persistido? |
|---|---:|---|---|---|---|
| `app/models/audit_log.py` | 21 | default= | Auditoria | timestamp do log | Sim |
| `app/models/movement.py` | 21 | default= | Movimentações | `timestamp` (fallback morto — services sobrescrevem com `now()`) | Sim |
| `app/models/movement.py` | 47 | default= | Movimentações | `created_at` | Sim |
| `app/models/asset.py` | 37–38 | default= + onupdate= | Patrimônio | `created_at`, `updated_at` | Sim |
| `app/models/inventario.py` | 48, 105 | default= | Inventário | `created_at` (Inventario e Item) | Sim |
| `app/models/maintenance.py` | 25, 27 | default= | Manutenção | `start_date` (default), `created_at` | Sim |
| `app/models/session.py` | 21 | default= | Sessões | `created_at` | Sim |
| `app/models/user.py` | 27 | default= | Usuários | `created_at` | Sim |
| `app/models/role.py` | 22 | default= | Perfis | `created_at` | Sim |
| `app/models/permission.py` | 22 | default= | Permissões | `created_at` | Sim |
| `app/models/ad_settings.py` | 40 | default= + onupdate= | AD | `updated_at` | Sim |
| `app/models/ad_group_role.py` | 25 | default= | AD | `created_at` | Sim |
| `app/models/setup_claim.py` | 26 | default= | Setup | `claimed_at` | Sim |
| `app/models/location.py` / `custodian.py` | 19 / 18 | default= | Cadastros | `created_at` | Sim |
| `app/services/audit_service.py` | 152 | `utcnow()` | Auditoria | timestamp explícito no `write_audit` | Sim |
| `app/services/inventario_service.py` | 34 | `utcnow().year` | Inventário | ano do código `INV-YYYY` | Não (código) |
| `app/services/inventario_service.py` | 251, 279, 283, 328, 339, 379 | `utcnow()` | Inventário | `checked_at` (×3), `started_at` (×2), `closed_at` | Sim |
| `app/web/routes.py` | 1945 | `utcnow()` | Inventário | `started_at` na rota `/iniciar` | Sim |
| `app/services/auth_service.py` | 136, 142, 153 | `utcnow()` | Auth | comparação `locked_until`, bloqueio, `last_login` | Sim (142/153) |
| `app/services/session_service.py` | 36, 53, 72 | `utcnow()` | Sessões | limpeza, `expires_at`, validação | Sim (53) |
| `app/services/maintenance_service.py` | 41, 77 | `utcnow()` | Manutenção | `start_date`, `end_date` | Sim |
| `app/services/ad_service.py` | 298, 303 | `utcnow()` | AD | `ad_last_sync`, `last_login` | Sim |
| `app/services/ad_ldap.py` | 344–345 | `_now_utc()` helper | AD | helper definido; **nenhum uso encontrado** | Não |
| `app/web/admin_routes.py` | 229 | `utcnow()` | Usuários | variável `now` p/ comparar `locked_until > now` no template | Não |
| `seed_demo.py` | 9 ocorrências (127–279) | `utcnow()` | Seed | `purchase_date`, `warranty_expiry` | Sim (demo) |

### B.2 — Geração em hora local (`datetime.now()`), naive

| Arquivo | Linha | Mecanismo | Módulo | Finalidade | Persistido? |
|---|---:|---|---|---|---|
| `app/services/movement_service.py` | 130 | `now()` | Movimentações | `Movement.timestamp` (aquisição/transferência/baixa/devolução) | Sim |
| `app/services/movement_service.py` | 116 | `now()` | Movimentações | `asset.updated_at` (sobrescreve default UTC do model!) | Sim |
| `app/services/movement_service.py` | 124 | `now().year` | Movimentações | ano do `term_code` TR-YYYY | Não (código) |
| `app/services/asset_service.py` | 147 | `now()` | Patrimônio | `purchase_date` fallback | Sim |
| `app/services/asset_service.py` | 178, 224 | `now()` | Patrimônio | `Movement.timestamp` (entrada inicial, edições) | Sim |
| `app/services/asset_service.py` | 191 | `now().year` | Patrimônio | ano do `term_code` TR-INIC | Não (código) |
| `app/services/asset_service.py` | 262 | `now()` | Patrimônio | cálculo de depreciação (idade do bem) | Não |
| `app/services/import_service.py` | 490 | `now()` | Importação | `purchase_date` fallback (CSV sem data) | Sim |
| `app/services/import_service.py` | 506 | `now()` | Importação | `Movement.timestamp` da entrada | Sim |
| `app/services/import_service.py` | 517 | `now().year` | Importação | ano do `term_code` TR-CSV | Não (código) |
| `app/services/report_service.py` | 297, 402, 682, 806 | `now()` | Relatórios | carimbo "Gerado em" em PDF/Excel | Não |
| `app/web/routes.py` | 124 | `now().year` | Jinja global | `current_year` (rodapé) | Não |

### B.3 — Parsing e formatação (sem geração de "agora")

| Arquivo | Linha | Mecanismo | Finalidade |
|---|---:|---|---|
| `app/web/routes.py` | 321–322, 634–635, 1480–1481 | `strptime("%Y-%m-%d")` | filtros de data de compra (UI web) |
| `app/api/reports_api.py` | 52–53, 96–97, 140–141 | `strptime("%Y-%m-%d")` | filtros de data de compra (API) |
| `app/services/import_service.py` | 112 | `strptime` (%d/%m/%Y, %Y-%m-%d, %d-%m-%Y, %d/%m/%y) | **datas vindas do CSV** — naive, sem fuso |
| `app/web/routes.py` | 2159 | `isoformat()` | `closed_at` serializado no JSON da auditoria |
| `app/api/assets_api.py` | 27–29 | `strftime("%Y-%m-%d")` | snapshot de auditoria |
| `app/api/movements_api.py` | 21–22 | `Query(datetime)` | `start_date`/`end_date` comparados com `Movement.timestamp` (local) |
| Templates (24 pontos) | ver seção E | `strftime` | exibição, sem conversão |
| `app/services/movement_service.py` | 302 | `strftime` | `term.date` do Termo de Responsabilidade |
| `app/services/report_service.py` | 110, 204, 334, 473, 509–534, 609–618, 725–730 | `strftime` | PDF/Excel/CSV de relatórios |
| `app/web/static/js/main.js` | 150–158 | `toLocaleString('pt-BR')` | **formata números/contadores, não datas** — navegador não altera horários |

---

## C. Mapa dos campos de banco

Todas as 28 colunas de data do schema real (verificado via `information_schema`, somente leitura): **`DATETIME`, `COLUMN_DEFAULT = NULL`, `EXTRA` vazio** — nenhum `TIMESTAMP`, nenhum `CURRENT_TIMESTAMP`, nenhum default no banco. Todos os defaults são Python-side (`default=` do SQLAlchemy).

| Tabela | Campo | Origem do valor | Significado atual |
|---|---|---|---|
| `audit_logs` | `timestamp` | UTC (`utcnow`) | UTC gravado como se fosse local |
| `inventarios` | `created_at`, `started_at`, `closed_at` | UTC | idem |
| `inventario_itens` | `created_at`, `checked_at` | UTC | idem |
| `movements` | `timestamp` | **Hora local** (services) | hora local correta |
| `movements` | `created_at` | **UTC** (model default) | UTC — mesma linha com 2 padrões! |
| `assets` | `created_at` | UTC | UTC |
| `assets` | `updated_at` | **Misto**: UTC (model onupdate) / local (`movement_service.py:116`) | inconsistente por caminho |
| `assets` | `purchase_date`, `warranty_expiry` | dado informado / CSV / `now()` fallback / seed com `utcnow` | naive, fuso depende da origem |
| `maintenances` | `start_date`, `end_date`, `created_at` | UTC | UTC |
| `users` | `created_at`, `last_login`, `locked_until`, `ad_last_sync` | UTC | UTC |
| `user_sessions` | `created_at`, `expires_at` | UTC | UTC (comparações internas consistentes) |
| `roles`, `permissions`, `locations`, `custodians`, `ad_group_roles`, `ad_settings`, `setup_claims` | `created_at`/`updated_at`/`claimed_at` | UTC | UTC |

---

## D. Fluxo de cada módulo

### Inventário (UTC na origem, exibido sem conversão → 3h adiantado)

```text
GERAÇÃO      InventarioService (checked_at/started_at/closed_at) e defaults dos models
             → datetime.utcnow() — naive UTC
ARMAZENAMENTO SQLAlchemy → MariaDB DATETIME (sem conversão; valor trafega intacto)
LEITURA      ORM devolve o mesmo valor naive
APRESENTAÇÃO detail.html / list.html / conferir.html → strftime('%d/%m/%Y %H:%M')
             Relatórios (report_service 509–534, 609–618, 725–730) → strftime
             Nenhum filtro Jinja, nenhum JS → tela mostra UTC = local +3h ✗
```

### Auditoria (UTC na origem, exibido sem conversão → 3h adiantado)

```text
GERAÇÃO      audit_service.write_audit → datetime.utcnow() (audit_service.py:152)
ARMAZENAMENTO audit_logs.timestamp DATETIME (indexado)
LEITURA      get_audit_logs → order_by(timestamp desc), limit 200–1000, sem filtro de data na UI
APRESENTAÇÃO admin/audit/list.html:85 → strftime('%d/%m/%Y %H:%M:%S') → UTC ✗
             (JSON de "dados posteriores" usa isoformat de closed_at — também UTC)
```

### Movimentações (hora local na origem, exibida sem conversão → aparenta correto)

```text
GERAÇÃO      movement_service.py:130 / asset_service.py:178,224 / import_service.py:506
             → datetime.now() — naive local (UTC-3 do servidor)
ARMAZENAMENTO movements.timestamp DATETIME
LEITURA      ORM; ordenação desc; filtros start/end da API comparam com valores locais
APRESENTAÇÃO movements/list.html:69, dashboard.html:258, movements/term.html (via
             get_term_details:302), reports/movements_report.html:48 → strftime → correto ✓
             ⚠ movement.created_at (UTC) e assets.updated_at (misto) fogem do padrão
```

### Importação (duas naturezas de data)

```text
DATA DO ARQUIVO   _parse_date (import_service.py:112) → strptime naive, sem fuso,
                  4 formatos aceitos → purchase_date gravada como veio
DATA DO SISTEMA   datetime.now() → timestamp da entrada, fallback de purchase_date,
                  ano do term_code (local)
ARMAZENAMENTO     assets.purchase_date, movements.timestamp (DATETIME)
APRESENTAÇÃO      assets/detail.html:130,136 e relatórios → strftime → local ✓
```

### Relatórios e documentos

```text
Carimbo "Gerado em": datetime.now() (report_service 297, 402, 682, 806) → local ✓
Dados exibidos: strftime puro sobre valores do banco → herdam o padrão de origem:
  - movements (local) → correto ✓
  - inventário (UTC) → 3h adiantado ✗ (CSV e PDF do inventário)
  - purchase_date → dia puro; seed gravou com utcnow (dias corretos na prática)
Filtros de período: strptime de datas de compra (%Y-%m-%d), naive
```

---

## E. Templates

Todas as exibições de data do projeto — **nenhuma converte timezone; nenhuma usa filtro customizado ou JS**:

| Template:linha | Campo | Padrão de origem | Exibição resultante |
|---|---|---|---|
| `admin/audit/list.html:85` | `log.timestamp` | UTC | +3h ✗ |
| `inventarios/detail.html:14,192,239,275,277,280,307` | `closed_at`, `checked_at`, `created_at`, `started_at` | UTC | +3h ✗ |
| `inventarios/list.html:72` | `created_at` | UTC | +3h ✗ |
| `inventarios/conferir.html:65` | `checked_at` | UTC | +3h ✗ |
| `admin/users/list.html:101`, `admin/users/edit.html:23` | `last_login` | UTC | +3h ✗ |
| `admin/users/edit.html:100` | `ad_last_sync` | UTC | +3h ✗ |
| `admin/users/edit.html:116` | `locked_until` | UTC | +3h ✗ |
| `movements/list.html:69`, `dashboard.html:258`, `reports/movements_report.html:48`, `assets/detail.html:216,249` | `m.timestamp` | local | correto ✓ |
| `assets/detail.html:130,136`, `reports/inventory.html:57` | `purchase_date` | data informada | correto ✓ |
| `maintenances/list.html:39` | `start_date` | UTC (**só a data é exibida**) | pode pular 1 dia ✗ |

`main.js` usa `toLocaleString('pt-BR')` apenas para animação de números/valores — **o navegador nunca altera horários**.

---

## F. Configuração de timezone

| Item | Estado atual |
|---|---|
| `app/config.py` | **Nenhuma** configuração de TZ |
| `.env` | Apenas `DATABASE_URL` |
| `app/main.py` / `app/database.py` | Nenhuma; engine criado sem `connect_args` de fuso |
| Jinja2 (`routes.py:114–124`) | Nenhum filtro/global de data (só `current_year`) |
| Timezone do processo Python | Herdado do SO (UTC-3) — `datetime.now()` correto, `utcnow()` +3h |
| MariaDB | `system_time_zone='-03'`, `global`/`session` = `SYSTEM`, `NOW()` correto |
| Conexão SQLAlchemy/pymysql | Nenhuma configuração de `time_zone` na sessão |
| Bibliotecas de TZ | `pytz`, `tzdata`, `python-dateutil` instaladas no ambiente, **nenhuma usada no código**; `zoneinfo` stdlib disponível (America/Recife testado OK) |
| `DateTime(timezone=True)` | Não usado em nenhum model |

---

## G. Inconsistências encontradas

### Problema confirmado

1. Inventário e Auditoria exibem +3h: `utcnow()` gravado em `DATETIME` e exibido sem conversão (evidências nas seções B/D/E).
2. **Mesma tabela com dois padrões**: `movements.timestamp` (local, via services) vs `movements.created_at` (UTC, default do model) — mesma linha, 3h de diferença entre colunas.
3. `assets.updated_at` misto: UTC pelo `onupdate` do model, local quando escrito por `movement_service.py:116` — valor depende do caminho que alterou o bem.
4. Telas de admin de usuários exibem `last_login`/`locked_until`/`ad_last_sync` +3h (UTC bruto).
5. Manutenções: `start_date`/`end_date` em UTC, exibindo **apenas a data** — um evento entre 21h e 24h local grava o dia seguinte em UTC e a tela mostra um dia errado.

### Possível risco

6. Código sequencial com fuso misto: `INV-YYYY` usa `utcnow().year` (`inventario_service.py:34`) e `TR-YYYY` usa `now().year` — na virada de ano entre 21h e 24h de 31/12, geram anos diferentes.
7. Filtros de período da API de movimentações comparam datetimes informados (assumidos locais) contra `timestamp` local — funciona hoje por coincidência; quebraria se a origem mudar.
8. Filtros `purchase_date_from/to` (strptime naive) contra `purchase_date` — seguro hoje por serem datas puras, frágil se fallback `utcnow` cair perto da meia-noite.
9. Seed (`seed_demo.py`) grava `purchase_date`/`warranty_expiry` com `utcnow` — datas de demo com 3h de deslocamento (irrelevante em dia cheio, visível perto da meia-noite).
10. `auth_service` compara `locked_until > utcnow()`: consistente enquanto tudo for UTC; qualquer alteração parcial de padrão desbloqueia/bloqueia contas com 3h de erro.

### Comportamento correto (não é bug)

11. Sessões: `expires_at = utcnow + TTL` comparado com `utcnow` — fuso internamente consistente; apenas a exibição (se houvesse) mostraria +3h.
12. Ordenações (`audit_logs.timestamp desc`, `Movement.timestamp desc`): coerentes enquanto cada tabela mantiver um único padrão.
13. Carimbos "Gerado em" dos relatórios: `now()` local — correto.
14. Navegador: zero influência (nenhum JS de data).

### Precisa apenas de documentação

15. Convenção de fato: "UTC para dados de compliance/trilha (auditoria, inventário, auth) e local para operacional (movimentações, importação)". Não está escrita em lugar nenhum e não é observada por todos os campos (ex.: `movements.created_at` quebra o próprio padrão operacional).

---

## H. Impacto de uma futura padronização (persistir UTC, apresentar em America/Recife)

### Alterações necessárias (núcleo)

- Filtro/global Jinja de conversão UTC→Recife (ex.: `filters["localtime"]` em `app/web/routes.py`) — 1 ponto central.
- 11 pontos de template listados na seção E com origem UTC (audit, inventários ×9, usuários ×4, manutenções ×1).
- Exportações de Inventário/Auditoria em `app/services/report_service.py` (linhas 509–534, 609–618, 725–730) para converter antes do `strftime`.

### Alterações provavelmente necessárias (para tornar o padrão verdadeiro)

- Migrar `movement_service.py:130`, `asset_service.py:147/178/224`, `import_service.py:490/506/517` de `now()` → `utcnow()` (ou helper central).
- Corrigir a gravação de `asset.updated_at` (`movement_service.py:116`) para o padrão único.
- Converter os filtros de período (`routes.py:321/634/1480`, `api/reports_api.py`, `api/movements_api.py`) de local → UTC antes de comparar.
- Ajustar `asset_service.py:262` (depreciação) para base UTC consistente.
- Fallback se algum módulo ficar de fora: helper único (ex.: `now_utc()` em um `app/utils/time.py`) substituindo chamadas diretas.

### Áreas que não precisam ser alteradas

- Models (defaults `utcnow` já conformes, inclusive `movement.created_at`).
- `auth_service`, `session_service`, `ad_service`, `ad_ldap`, `maintenance_service` (já UTC).
- `main.js` (não trata datas), `app/config.py`, engine SQLAlchemy.

### Dados históricos

- `audit_logs`, `inventarios`, `inventario_itens`, `users`, `user_sessions`, `maintenances`, `roles/permissions/locations/custodians`, `assets.created_at/updated_at(UTC)`: já UTC → **nenhuma migração**.
- `movements.timestamp` (~202 registros, verificados: distribuição de horas 14–21h = expediente local): estão em **hora local** → precisariam de conversão `+ INTERVAL 3 HOUR` (ou migração de dados) para o padrão único — **não executada nesta análise**. Sem ela, a tabela ficaria 3h atrás das demais e a ordenação global cruzada (audit × movement) ficaria distorcida.
- `assets.purchase_date/warranty_expiry`: mistas (CSV/local/seed-UTC) — avaliar caso a caso; impacto baixo (datas puras).

### Testes que assumem o padrão atual

- `tests/test_auth.py:175` (`expires_at = utcnow - 1s`) e `tests/test_cli_reset_password.py:120,127,184,431` — consistentes com UTC; se `session_service`/`auth_service` mudarem de fuso, precisam de ajuste.
- `tests/test_assets.py:10` — cria asset com `utcnow - 365d` enquanto a depreciação usa `now()`: hoje passa; com padronização, deve ser alinhado.
- `tests/test_inventario_reconferencia_ui.py:131,245` — compara `strftime` do valor recém-criado com a tela: sobrevive a qualquer padrão (compara origem com origem), só deixaria de pegar regressão de exibição.
- Nenhum teste atual quebraria com a alternativa "converter só na apresentação" mantendo UTC na gravação.

---

## I. Pontos fora do escopo de uma correção de timezone

- `datetime.utcnow().year` para `INV-YYYY` (`inventario_service.py:34`) — implica virada de ano (21h–24h de 31/12), mas não é problema de exibição; mereceria correção própria.
- `now().year` dos `term_code` (`asset_service.py:191`, `movement_service.py:124`, `import_service.py:517`) — mesmo tema, padrão oposto.
- Cálculo de depreciação por mês (`asset_service.py:262`) — questão contábil, não de exibição.
- `locked_until`/`expires_at`/`last_login`/`ad_last_sync` — lógica de autenticação/sessão/AD; tocar nelas exige análise de segurança específica.
- Formatos aceitos pelo parser de CSV (`_parse_date`) — questão de dados de entrada.
- `pytz`/`dateutil` instaladas mas não usadas — decisão de dependência é separada.
- `_now_utc()` (`ad_ldap.py:344`) — helper morto, sem chamadas.

---

## J. Recomendação técnica (neutra, sem implementar)

### 1. Persistir tudo em UTC e converter para `America/Recife` só na apresentação *(objetivo declarado da tarefa)*

- **Vantagens:** convenção canônica universal; ordenação e filtros robustos e independentes de servidor; compatível com ~90% do código atual (models, auth, sessões, inventário, auditoria já gravam UTC); base histórica majoritariamente já conformes; viabiliza servidores em fuso diferente no futuro.
- **Desvantagens:** exige introduzir camada de apresentação (filtro Jinja + conversão nos exports); exige migração pontual de `movements.timestamp` (e revisão de `purchase_date` mistas); exige disciplina para não gravar local por engano (risco de dupla conversão = 6h).
- **Impacto:** ~1 arquivo novo/helper, ~11 pontos de template, ~1 trecho do report_service, 3 services de movimentação/importação, filtros de período, 1 migração de dados de `movements`.
- **Riscos:** dupla conversão; esquecer um ponto de exibição; confusão com `movements.created_at` já UTC.
- **Compatibilidade:** alta — é uma generalização do que a maior parte do código já faz.

### 2. Persistir horário local em tudo

- **Vantagens:** telas passam a exibir certo sem camada de apresentação; não há migração para Movimentações (já local).
- **Desvantagens:** UTC que hoje está correto (auth/sessões) teria que migrar ou virar local — **comparações de sessão/bloqueio precisariam migrar juntas**, senão expiram/desbloqueiam com 3h de erro; ordenação fica presa ao fuso do servidor; migrar servidor de fuso ou rodar multi-fuso quebra o sistema; toda a base UTC (auditoria, inventário, users, sessions, maintenances, assets) precisaria de `UPDATE` de conversão — operação sensível sobre trilha de auditoria imutável por natureza.
- **Impacto:** maior superfície (7 services + 19 defaults de models + migração ampla de dados).
- **Riscos:** dupla conversão de dados históricos; perda de ambiguidade zero nos timestamps; virada de ano/dia com comportamento surpreendente.
- **Compatibilidade:** baixa com o código atual — inverte a convenção dominante.

### 3. Abordagem existente no projeto a aproveitar: conversão num único ponto de leitura via helper (variante pragmática da 1)

- O projeto já centraliza a apresentação em `templates` + `report_service`; um helper único (ex.: filtro Jinja `localtime` usando `zoneinfo.ZoneInfo("America/Recife")`, stdlib, sem dependência nova) aplicado só nos pontos de exibição, **mantendo cada tabela com seu fuso atual de gravação**, é a menor mudança possível.
- **Vantagens:** nenhuma migração de dados; zero risco às comparações internas de sessão/auth; reversível.
- **Desvantagens:** perpetua a dualidade interna (exige mapa por tabela de "qual fuso está gravado" — risco de alguém aplicar o filtro num campo local e atrasar 3h); não resolve ordenação cruzada audit × movement.
- **Impacto:** 1 filtro + ~12 pontos de exibição.
- **Riscos:** aplicação incorreta do filtro em campos locais; documentação vira peça crítica.
- **Compatibilidade:** máxima.

---

## Anexo — Arquivos potencialmente afetados por uma futura implementação (lista consolidada, nada alterado agora)

- `app/web/routes.py` (filtro Jinja; filtros de data 321/634/1480; `started_at:1945`)
- `app/web/admin_routes.py` (`now` do template:229, se exibição mudar)
- `app/web/templates/admin/audit/list.html` (85)
- `app/web/templates/inventarios/detail.html` (7 pontos), `list.html` (72), `conferir.html` (65)
- `app/web/templates/admin/users/list.html` (101), `admin/users/edit.html` (23, 100, 116)
- `app/web/templates/maintenances/list.html` (39)
- `app/services/report_service.py` (509–534, 609–618, 725–730)
- `app/services/movement_service.py` (116, 124, 130), `app/services/asset_service.py` (147, 178, 191, 224, 262), `app/services/import_service.py` (490, 506, 517)
- `app/api/movements_api.py`, `app/api/reports_api.py` (filtros de período)
- Migração/one-off de dados: `movements.timestamp`
- Testes: `test_auth.py`, `test_cli_reset_password.py`, `test_assets.py`, `test_inventario_reconferencia_ui.py` (revisão, conforme alternativa)

---

## Critérios de conclusão

Atendidos: todas as fontes varridas (69 ocorrências em `app/` + seed + testes + templates + JS), os 5 módulos obrigatórios mapeados (Inventário, Auditoria, Movimentações, Importação, Relatórios), 28 colunas de banco inspecionadas via `information_schema`, amostras de dados comparadas com `NOW()`/`UTC_TIMESTAMP()` (somente SELECT), 4 arquivos de teste analisados, inconsistências classificadas, **zero arquivos alterados**.
