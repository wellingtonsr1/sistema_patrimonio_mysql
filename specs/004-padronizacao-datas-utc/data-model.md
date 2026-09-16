# Data Model: Padronização de Data e Hora (feature 004)

**Feature**: 004-padronizacao-datas-utc | **Date**: 2026-09-15
**Natureza**: nenhum schema novo, nenhuma tabela/coluna nova, nenhum estado novo. Este documento
**classifica os campos existentes** (validação da regra da spec) e define os contratos de valor por
campo. Classificação conferida contra o código nesta sessão (fonte: models em `app/models/`,
services em `app/services/`, análise `docs/ANALISE_DATAS_HORARIOS.md` seção C).

---

## 1. Convenção aplicada (contrato da aplicação, não do banco)

| Conceito | Definição |
|---|---|
| **Timestamp** | Instante no tempo. Gerado pelo sistema via `now_utc()` (naive UTC). Persistido em coluna `DATETIME` sem fuso representando **UTC** (FR-018). Exibido sempre convertido para `America/Recife` via mecanismo central (FR-003/005). |
| **Data de negócio** | Data pura (sem hora, sem fuso). Vem de formulário/CSV/seed. Persistida e exibida **exatamente como informada** (FR-014). Nunca passa por conversão de fuso. |
| **Leitura (naive do banco)** | Todo `datetime` com `tzinfo=None` lido de coluna classificada como timestamp é tratado como **UTC** (FR-018). |

## 2. Campos classificados como **Timestamp** (regem a convenção)

Verificação de origem conferida: coluna "Origem pós-feature" indica o gerador após a
implementação. Todos persistem UTC (hoje ou após a mudança); todos os pontos de exibição listados
passam pela conversão para `America/Recife`.

| Entidade (tabela) | Campo | Origem pós-feature | Alteração nesta feature | Exibições convertidas |
|---|---|---|---|---|
| AuditLog (`audit_logs`) | `timestamp` | `audit_service.py:152` (`utcnow`) — já UTC | Nenhuma na gravação | `admin/audit/list.html:85` |
| Inventario (`inventarios`) | `created_at` | default do model (`utcnow`) — já UTC | Nenhuma | `inventarios/list.html:72`, `detail.html:275` |
| Inventario | `started_at` | `inventario_service.py:283,339`, `routes.py:1945` (`utcnow`) — já UTC | Nenhuma | `detail.html:14,277` |
| Inventario | `closed_at` | `inventario_service.py:379` (`utcnow`) — já UTC | Nenhuma | `detail.html:14,280` |
| InventarioItem (`inventario_itens`) | `created_at` | default do model — já UTC | Nenhuma | (sem exibição atual de timestamp — nada a fazer) |
| InventarioItem | `checked_at` | `inventario_service.py:251,279,328` (`utcnow`) — já UTC | Nenhuma | `detail.html:192,239,307`, `conferir.html:65` |
| Movement (`movements`) | `timestamp` | **MUDA**: services usavam `now()` local → `now_utc()` | `movement_service.py:130`, `asset_service.py:178,224`, `import_service.py:506` | `movements/list.html:69`, `dashboard.html:258`, `reports/movements_report.html:48`, `assets/detail.html:216,249`, `report_service` (CSV movimentações `:474`), `movement_service.py:302` (term.date) |
| Movement | `created_at` | default do model (`utcnow`) — já UTC | Nenhuma | (sem exibição atual — nada a fazer) |
| Asset (`assets`) | `created_at` | default do model — já UTC | Nenhuma | (sem exibição atual — nada a fazer) |
| Asset | `updated_at` | **MUDA**: `movement_service.py:116` usava `now()` local → `now_utc()` (o `onupdate` do model já é UTC) | 1 ponto | (sem exibição atual — nada a fazer) |
| Maintenance (`maintenances`) | `start_date` | `maintenance_service.py:41` (`utcnow`) — já UTC | Nenhuma na gravação; **classificação confirmada** (ver R5 do research) | `maintenances/list.html:39` (exibe só data → resolve deslocamento de dia) |
| Maintenance | `end_date` | `maintenance_service.py:77` (`utcnow`) — já UTC | Nenhuma | (sem exibição atual — nada a fazer) |
| Maintenance | `created_at` | default do model — já UTC | Nenhuma | (sem exibição atual — nada a fazer) |
| User (`users`) | `created_at` | default do model — já UTC | Nenhuma | (sem exibição atual — nada a fazer) |
| User | `last_login` | `auth_service.py:153`, `ad_service.py:303` — já UTC | Nenhuma (FR-013) | `admin/users/list.html:101`, `admin/users/edit.html:23` |
| User | `locked_until` | `auth_service.py:142` — já UTC | Nenhuma (FR-013) | `admin/users/edit.html:116` |
| User | `ad_last_sync` | `ad_service.py:298` — já UTC | Nenhuma (FR-013) | `admin/users/edit.html:100` |
| UserSession (`user_sessions`) | `created_at` / `expires_at` | `session_service.py:53` — já UTC | Nenhuma (FR-013) | (não exibidos — sem conversão) |
| Role / Permission / Location / Custodian / ADGroupRole | `created_at` | defaults dos models — já UTC | Nenhuma | (sem exibição atual — nada a fazer) |
| ADSettings (`ad_settings`) | `updated_at` | default `+ onupdate` do model — já UTC | Nenhuma | (sem exibição atual — nada a fazer) |
| SetupClaim (`setup_claims`) | `claimed_at` | default do model — já UTC | Nenhuma | (sem exibição atual — nada a fazer) |

**Regra de validação da classificação (da spec)**: conferida. `Maintenance.start_date`/`end_date`
têm semântica de instante (origem `utcnow()` do service; o formulário web não coleta data —
verificado em `maintenances/new.html`). Nenhuma divergência a registrar.

## 3. Campos classificados como **Data de negócio** (intocados)

| Entidade | Campo | Origem | Tratamento |
|---|---|---|---|
| Asset | `purchase_date` | formulário (`%Y-%m-%d` strptime), CSV (`_parse_date`, 4 formatos), fallback `now()` (`asset_service.py:147`, `import_service.py:490`), seed | Sem conversão de fuso na gravação nem na exibição (`assets/detail.html:130,136`, `reports/inventory.html:57`, exports). Filtros de período de compra permanecem comparação de data pura (`routes.py:321–322,634–635,1480–1481`, `api/reports_api.py`) |
| Asset | `warranty_expiry` | formulário, seed | Idem — sem conversão |
| Importação (em geral) | datas interpretadas do CSV | `_parse_date` (`import_service.py:112`) | Formato e semântica preservados (FR-008); parser não alterado |

**Nota (sem alteração)**: os fallbacks de `purchase_date` usam `datetime.now()` e permanecem — são
fallback de "data de hoje" (negócio), não instante sistêmico (R6 do research).

## 4. Campos fora da convenção, fora do escopo (registrados, não alterados)

| Campo/Uso | Motivo de ficar fora |
|---|---|
| `inventario_service.py:34` (`utcnow().year` → código `INV-YYYY`) | Spec: códigos sequenciais fora do escopo |
| `movement_service.py:124`, `asset_service.py:191`, `import_service.py:517` (`now().year` → `TR-YYYY`) | Idem |
| `asset_service.py:262` (`now()` na idade p/ depreciação) | Spec: depreciação fora do escopo |
| `report_service.py:297,402,682,806` (carimbo "Gerado em", `now()` local) | Já correto (US4): carimbo é horário local atual, não dado armazenado — permanece `now()` |
| `admin_routes.py:229` (`now` p/ comparar `locked_until` no template) | Comparação interna UTC×UTC, não exibição (FR-013) |
| `ad_ldap.py:344–345` (`_now_utc()` helper sem uso) | Código morto, fora do escopo |
| `seed_demo.py` (`utcnow` em datas de demo) | Banco de demo, fora do escopo da spec |
| `routes.py:2159` (`closed_at.isoformat()` no JSON de auditoria) | Dado bruto UTC na trilha — permanece UTC (convenção de persistência); exibição humana é que converte |
| `api/assets_api.py:27–29` (snapshot `strftime` de datas de compra) | Data de negócio |

## 5. Estado/validação (sem transições novas)

Nenhum estado de entidade é alterado. Validações existentes (inventário, movimentações, RBAC,
sessão/bloqueio) permanecem: as comparações internas de auth/sessão continuam UTC×UTC (FR-013).
Únicas comparações cujos operandos mudam de significado: filtros de período de movimentações
(`movement_service.py:272–275`) — passam a comparar UTC (convertido) × UTC (gravado), mantendo o
resultado esperado pelo usuário (US5).
