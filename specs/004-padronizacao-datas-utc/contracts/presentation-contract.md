# Contract: Apresentação e Persistência por Fluxo (feature 004)

**Feature**: 004-padronizacao-datas-utc | **Date**: 2026-09-15
**Escopo**: contrato de comportamento observável por módulo — o que cada tela/export/fluxo deve
produzir após a implementação. Base para testes de `tests/test_datetime_flows.py` e para o
quickstart. Formatos visuais existentes são preservados; muda apenas o fuso do valor exibido.

---

## 1. Trilha de Auditoria (US1)

| Aspecto | Contrato |
|---|---|
| Gravação | `audit_service.write_audit` continua gravando UTC (intocado) |
| Tela | `admin/audit/list.html` exibe `log.timestamp` convertido para `America/Recife` |
| Formato | `%d/%m/%Y %H:%M:%S` preservado **com segundos** (edge case "segundos") |
| Cenário de aceite | Registro gravado com instante UTC ≡ 19:30 local → linha mostra `15/09/2026 19:30:xx` |

## 2. Inventário (US1/US4)

| Aspecto | Contrato |
|---|---|
| Gravação | `InventarioService` intocado (já grava UTC: `checked_at`, `started_at`, `closed_at`) |
| Telas | `detail.html` (7 pontos), `list.html` (1), `conferir.html` (1) exibem horário convertido |
| Exports | `report_service`: CSV da ata (`Criado em`, `Conferência iniciada em`, `Encerrado em`, `conferido_em` das linhas), PDF da ata (mesmos campos) e Excel — convertidos via `format_local` |
| Valor ausente | `checked_at`/`closed_at` vazios continuam exibindo `-`/condicional atual sem erro |
| Cenário de aceite | Conferência às 19:30 locais → detalhes do inventário e ata CSV/PDF mostram 19:30, não 22:30 |

## 3. Movimentações (US1/US2)

| Aspecto | Contrato |
|---|---|
| Gravação | `Movement.timestamp` gravado por `movement_service`/`asset_service`/`import_service` representa **UTC** (`now_utc()`); `assets.updated_at` idem — mesma linha, mesmo instante de referência (SC-003) |
| Carimbos auxiliares | `movements.created_at` (default do model) já UTC — sem divergência intra-linha |
| Telas | `movements/list.html`, `dashboard.html`, `reports/movements_report.html`, `assets/detail.html` (2 pontos) exibem `m.timestamp` convertido |
| Termo (TR) | `movement_service.get_term_details` (`term.date`) imprime `movement.timestamp` convertido |
| Export | CSV de movimentações do `report_service` (`m.timestamp` → `format_local`) |
| Cenário de aceite | Movimentação registrada às 19:30 locais → coluna `movements.timestamp` no banco ≡ 22:30 UTC; tela/TR/CSV exibem 19:30 |

## 4. Importação CSV (US2/US3)

| Aspecto | Contrato |
|---|---|
| Timestamps do sistema | Movimentação de entrada (`Movement.timestamp`) gravada em UTC (`now_utc()`) |
| Datas do arquivo | `purchase_date` do CSV permanece exatamente como informada (parser `_parse_date` intocado) |
| Fallback | `purchase_date` ausente no CSV → fallback atual de data (intocado — data de negócio) |
| Cenário de aceite | CSV com compra "15/09/2026" → armazenado e exibido como 15/09/2026; carimbo da entrada ≡ UTC do momento |

## 5. Administração de Usuários (US1)

| Aspecto | Contrato |
|---|---|
| Lógica | `auth_service`/`ad_service` intocados (FR-013): bloqueio, último acesso e sync AD continuam UTC internamente |
| Telas | `admin/users/list.html` (`last_login`), `edit.html` (`last_login`, `ad_last_sync`, `locked_until`) exibem horário convertido |
| Valor ausente | "Nunca" preservado |
| Cenário de aceite | Usuário bloqueado até 20:00 locais → aviso mostra 20:00, não 23:00 |

## 6. Manutenções (US1)

| Aspecto | Contrato |
|---|---|
| Gravação | `maintenance_service` intocado (já UTC) |
| Tela | `maintenances/list.html` exibe `m.start_date` convertido — OS aberta após 21h locais mostra o **dia local** correto (hoje mostra o dia seguinte) |
| Cenário de aceite | OS aberta às 21:30 locais de 15/09 → lista mostra 15/09 |

## 7. Relatórios gerais (US4)

| Aspecto | Contrato |
|---|---|
| Dados armazenados | Timestamps de dados (inventário, auditoria, movimentações) convertidos para Recife nos exports PDF/Excel/CSV/HTML |
| Carimbo "Gerado em" | Permanece `now()` local — comportamento atual correto (intocado) |
| Datas de negócio | `purchase_date`/`warranty_expiry` nos exports: sem conversão |

## 8. Filtros de período (US5)

| Aspecto | Contrato |
|---|---|
| API movimentações | `start_date`/`end_date` naive informados são interpretados em `America/Recife` e convertidos para UTC antes de comparar com `Movement.timestamp`; datetimes com offset explícito (ISO-8601) são respeitados como absolutos |
| Filtros de compra | `purchase_date_from/to` (web e API) permanecem comparação de data pura — intocados |
| Cenário de aceite | Registro às 19:00 locais (22:00 UTC) é retornado pelo filtro local 15/09 00:00–23:59; nenhum registro de dia adjacente é incluído/excluído por deslocamento |

## 9. Testes (FR-015/FR-016)

| Aspecto | Contrato |
|---|---|
| Novos | `tests/test_datetime_convention.py`: conversão UTC→Recife, virada de dia (UTC 02:30 de 16/09 → 15/09 23:30 local), preservação de segundos, `None`-safe, idempotência de uso (dupla conversão detectável), `local_to_utc` |
| Novos | `tests/test_datetime_flows.py`: gravação UTC em movimentação/importação, divergência intra-linha eliminada, filtros de período, apresentação de inventário/auditoria |
| Ajustes permitidos | Somente as 2 asserções de `strftime` em `tests/test_inventario_reconferencia_ui.py:133,245` passam a comparar o valor convertido — cobertura mantida |
| Intactos | Demais testes (`test_auth.py`, `test_cli_reset_password.py`, `test_assets.py`, `test_inventario.py` etc.) — suíte permanece verde |
