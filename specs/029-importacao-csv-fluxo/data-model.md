# Phase 1 Data Model: Registrar no Fluxo as movimentações da importação CSV de equipamentos

**Feature**: 029-importacao-csv-fluxo | **Date**: 2026-09-21

## Conclusão: ZERO DDL

Nenhuma tabela, coluna, índice ou tipo de dado é criado, alterado ou removido. Todas as
entidades necessárias já existem e já suportam o histórico descrito pela spec
(Princípio VII — alterações aditivas controladas; FR-023 — nenhuma alteração de banco
sem necessidade comprovada). Este documento registra o **uso** das entidades existentes
pela nova lógica e as transições de estado que a importação passa a produzir.

## Entidades existentes utilizadas (nenhuma alterada)

### Asset (`assets`) — estado atual do bem

| Campo | Uso pela importação corrigida |
|---|---|
| `tag` (unique) | chave de reimportação (comportamento atual) |
| `status` | `AVAILABLE` na criação; passa a `IN_USE` apenas pela `ALOCACAO_CAUTELA` via motor |
| `location_id` (FK locations) | **deixa de ser escrito diretamente pelo importador na criação com custódia**; passa a ser derivado pela operação de domínio (entrada/alocação) |
| `custodian_id` (FK custodians) | passa a ser escrito **somente por `create_movement`** (hoje o importador nunca o escreve) |
| `condition`, `updated_at` | atualizados pelo motor quando há movimentação |

### Movement (`movements`) — histórico imutável (fonte do Fluxo)

Campos usados, sem alteração de estrutura:

- `movement_type` (Enum): apenas `ENTRADA_AQUISICAO` (entrada) e `ALOCACAO_CAUTELA` /
  `TRANSFERENCIA_LOCAL` (custódia via motor). **Nenhum tipo novo** (FR-003).
- `timestamp` (UTC via `now_utc`), `reason` (obrigatório), `operator_name` (usuário
  autenticado — FR-005), `term_code` (`TR-{ano}-{seq:05d}` gerado pelo motor para
  ALLOCATION — FR-007; entrada usa `TR-INIC-{ano}-{id}` como o cadastro manual),
- Snapshots de origem/destino (`*_location_id/name`, `*_custodian_id/name`) — preenchidos
  pelo motor a partir do estado real do bem (elimina os fabricados "Importação CSV"/"Sistema").
- `previous_status/new_status`, `previous_condition/new_condition` — preenchidos pelo motor.

### Custodian (`custodians`) — resolução da coluna do CSV

`name` (e `registration_code` como fallback documentado) usados para resolver a coluna
`Custodiante`/`colaborador` pelo cadastro existente. **Nenhum colaborador é criado pela
importação** (FR-001/FR-012).

### Location (`locations`) — resolução já existente

`LocationService.get_by_name` (comportamento atual mantido; local inexistente = erro de
linha — FR-013).

### AuditLog (`audit_logs`) — auditoria da operação de importação

Evento `ACTION_IMPORT` das rotas web/API permanece inalterado (FR-018). Distinto da
movimentação patrimonial.

## Transições de estado produzidas pela importação (após a correção)

### Caminho 1 — Equipamento NOVO

| Entrada do CSV | Estado final do bem | Movimentações criadas |
|---|---|---|
| sem custodiante, sem local | `AVAILABLE`, sem custodiante, sem local | `ENTRADA_AQUISICAO` (destino "Estoque Central") |
| sem custodiante, com local | `AVAILABLE`, com local | `ENTRADA_AQUISICAO` (destino = local do CSV) |
| com custodiante, com/sem local | `IN_USE`, custodiante do CSV, local do CSV (quando informado) | `ENTRADA_AQUISICAO` + `ALOCACAO_CAUTELA` (termo sequencial; operador autenticado) |

### Caminho 2 — REIMPORTAÇÃO (equipamento existente)

| Situação | Movimentação criada | Estado final |
|---|---|---|
| mesmos local e custodiante (idêntico) | **nenhuma** (FR-015) | inalterado |
| custodiante diferente (local igual ou diferente) | `ALOCACAO_CAUTELA` (VAL-007 — entrega com termo) | novo custodiante; novo local quando informado |
| só local diferente, mesmo custodiante | `TRANSFERENCIA_LOCAL` | novo local, mesmo custodiante |
| CSV sem custodiante (carga parcial) | nenhuma mudança de custódia (decisão R4 — devolução é manual) | custódia atual mantida |
| CSV sem local | local atual mantido | inalterado |
| bem baixado | erro de linha (regra do motor — não movimenta baixado) | inalterado |

## Invariantes

1. **Custodiante/local/status do bem** só mudam por operação de domínio (entrada no
   service de importação seguindo o padrão do cadastro manual; custódia exclusivamente
   via `MovementService.create_movement`) — elimina o caminho que contornava o motor.
2. **Movimentações são append-only** — nada é apagado ou sobrescrito (FR-017).
3. **Unidade transacional por linha**: `create_movement` comita a movimentação; o
   importador comita a linha; erro de linha → rollback da linha + report no resultado
   (sem estado parcial — FR-019/K).
4. **A matriz de decisão vive em `MovementService.resolve_movement_type`** (puro) e o
   executor em `create_movement` (intocado) — nenhum `if` de matriz no importador (FR-004).
5. `timestamp` das movimentações permanece UTC; exibição continua convertendo para local.
