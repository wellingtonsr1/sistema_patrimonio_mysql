# Data Model — 068-paginacao-listas-e-relatorios-integros

> **Nenhuma entidade nova.** Esta feature não cria tabela, coluna, índice, enum, migração ou backfill (Constitution VII). O "modelo" da feature é o **contrato de parâmetros de página** e as **invariantes de apresentação**.

## 1. Entidades envolvidas (todas somente leitura / consulta paginada)

| Entidade (tabela) | Uso nesta feature | Alteração estrutural |
|---|---|---|
| `assets` | lista `/assets`, tela e exportações de relatório | **Nenhuma** |
| `movements` | lista `/movements`, exportação CSV | **Nenhuma** |
| `custodians` | lista `/custodians` (agora paginada) | **Nenhuma** |
| `locations` | lista `/locations` (agora paginada) | **Nenhuma** |
| `inventarios` / `inventario_itens` | listagem e itens da conferência (paginação + filtro no service) | **Nenhuma** |
| `audit_logs` | `/admin/audit` paginado + filtros de período/usuário | **Nenhuma** (somente leitura) |
| `users` / `user_roles` / `roles` / `permissions` | autorização existente, sem mudanças | **Nenhuma** |

## 2. Parâmetros de página (contrato comum)

| Parâmetro | Tipo | Default | Onde aparece | Regras |
|---|---|---|---|---|
| `page` | inteiro na query string | `1` | todas as 7 listas + tela de relatório | `parse_page()`: vazio/não numérico/`<=0` → `1`; maior que `pages` → última página |
| `page_size` | constante da casa | `200` | interno (não exposto) | P3 aprovada: **fixo**, sem seletor |
| `offset` | interno | `(page-1)*200` | service | sempre aplicado no banco (`.offset().limit()`), nunca em Python |
| `total` | inteiro retornado pelo service | — | contexto do template | `query.count()` do **mesmo filtro** da página |
| `pages` | inteiro | `ceil(total/200)`, `0` se `total=0` | contexto | controla a exibição do pager |

**Vocabulário idêntico** ao precedent `IntegrationCenterService.get_history` (`{rows, total, page, page_size, pages}`).

## 3. Matriz de rotas × parâmetros (estado final previsto)

| Rota | Permissão (inalterada) | Parâmetros lidos da query string | Contexto de página adicionado |
|---|---|---|---|
| `/assets` | `patrimonio.visualizar` | atuais (11 filtros) **+ `page`** | `total`, `page`, `pages`, `start`, `end` |
| `/movements` | `movimentacao.visualizar` | atuais (`movement_type`, `asset_id`, `search`) **+ `page`** | idem (o `total` já é retornado, **hoje não exibido**) |
| `/custodians` | `colaboradores.visualizar` | `search` **+ `page`** | idem (**novo indicador**) |
| `/locations` | `locais.visualizar` | `search` **+ `page`** | idem (**novo indicador**) |
| `/inventarios` | `inventario.visualizar` | `search`, `status_filter` **+ `page`** | idem + `summaries` global |
| `/inventarios/{id}` | `inventario.visualizar` | `search`, `status_filter` **+ `page`** | itens paginados + **contadores globais** |
| `/admin/audit` | `auditoria.visualizar` | atuais (`search`, `module`, `action`, `result`) **+ `page`, `start_date`, `end_date`, `user_id`** | `total`, `page`, `pages` |
| `/reports/inventory` e `/reports/movements` | `relatorios.visualizar` | atuais (11 filtros) **+ `page`** | `total`, `pages` + aviso prévio de PDF (P6 cobre as duas telas) |
| `/api/v1/reports/inventory/{csv,excel,pdf}` | `relatorios.exportar` | **inalterados** (nenhum parâmetro novo; exporta o conjunto completo) | — |

## 4. Invariantes (o que nunca pode quebrar)

- **I1 — Nenhum corte silencioso**: se `total > exibido`, a interface e/ou o arquivo informam `exibido X de Y` (FR-004/FR-013).
- **I2 — Contador ≠ página**: números de resumo globais (bens esperados, conferidas/restantes/divergências, resumo de inventários) **não** dependem de `page` (FR-005).
- **I3 — Filtro antes da página**: `total` é sempre do filtro; a página é recortada **depois** do filtro (nunca o inverso).
- **I4 — Mesmo filtro na URL**: `page` troca sem perder `search`/filtros (FR-007); a URL é compartilhável.
- **I5 — Compatibilidade retroativa**: qualquer chamador que **não** passe `skip/limit/offset` continua recebendo exatamente o que recebe hoje (`CustodianService.get_all`, `LocationService.get_all`, `InventarioService.get_all`, `get_audit_logs`, exportações).
- **I6 — Autorização anterior à página**: `require_permission` é avaliado na rota, independentemente de `page` (FR-015/AC10).
- **I7 — Só leitura**: nenhuma escrita em `assets`, `movements`, `custodians`, `locations`, `inventarios*`, `audit_logs` decorre da paginação ou da exportação.

## 5. Regras de corte/remoção (o que sai do código)

| Onde | Hoje | Depois |
|---|---|---|
| `report_service.get_filtered_assets` | `limit_query = limit if limit > 0 else 10000` (`report_service.py:47`) | **sem teto** — `limit=0` significa "todos", consumido em lotes pelo gerador |
| `view_inventory_report` e `view_movements_report` | `limit=1000` | paginação `page`/200 + total |
| `admin_audit_log` | `limit=min(limit,1000)` sem offset | `offset` + `page` (o `limit` por página vira 200 fixo) |
| `list_assets` / `list_movements_view` | `limit=200` sem offset | `limit=200` **+ offset** |
| `view_inventario` | filtro de itens em Python | filtro/paginação no `InventarioService` |

## 6. Dados existentes e integridade

- Nenhum dado é migrado, atualizado ou removido.
- `SELECT COUNT(*)` passa a ser executado **uma vez por request** de lista (é o que já ocorre em `AssetService.get_all`/`MovementService.get_all_movements`); nas listas que hoje fazem contagem por linha, a contagem vira **agregação única** (P5).
- Portabilidade: `OFFSET/LIMIT` e `GROUP BY` são suportados por MariaDB/MySQL (produção) e SQLite (suíte) — sem SQL específico de plataforma.
- Índices existentes (`assets.tag`, `assets.created_at`, `movements.timestamp`, `audit_logs.timestamp` etc.) continuam sustentando a ordenação; **nenhum índice novo** é criado (a análise P6 — busca full-text — fica para outra feature).
