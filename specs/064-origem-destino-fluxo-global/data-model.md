# Data Model — Feature 064: Fluxo Global de Movimentações (Origem/Destino)

**Data**: 2026-10-07 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> **Documento de NÃO-MUDANÇA** (padrão da 063): esta feature é de apresentação. **Zero DDL, zero migração, zero alteração de modelo.** Este artefato registra as entidades envolvidas SOMENTE-LEITURA para dar rastreabilidade ao plano.

## Entidades envolvidas (nenhuma é alterada)

### Movement (`app/models/movement.py`, tabela `movements`) — IMUTÁVEL

| Campo | Tipo | Uso na feature |
|---|---|---|
| `origin_location_id` / `destination_location_id` | FK → `locations.id`, nullable | relação preferida para exibição quando não-nula |
| `origin_location_name` / `destination_location_name` | String(150), nullable | snapshot imutável; **fonte de fallback** (exibida byte-a-byte) e base da busca 049 (L533–534) |
| `origin_custodian_id` / `destination_custodian_id` | FK → `custodians.id`, nullable | colaborador (exibição inalterada) |
| `origin_custodian_name` / `destination_custodian_name` | String(150), nullable | snapshot do colaborador (`Nome (Matrícula)`) |
| `movement_type`, `timestamp`, `reason`, `operator_name`, `term_code` | — | demais colunas da tabela, intocadas |

**Regras de gravação preservadas** (`create_movement`, `movement_service.py` L136/L148/L307–311): snapshot = `f"{branch} - {department} ({name})"`; literais especiais: origem `Não definido` / `Nenhum / Estoque`; entrada inicial `Fornecedor / Entrada Inicial` (Feature 029); termo usa fallback `Almoxarifado / Estoque` (L613). Nenhum registro existente é regravado (guarda por teste).

### Location (`app/models/location.py`, tabela `locations`) — SOMENTE LEITURA

| Campo | Tipo | Uso na feature |
|---|---|---|
| `name` | String(100), NOT NULL, unique | entrada da macro `_local_curto` (remove sufixo ` - {department}`) |
| `branch` | String(100), NOT NULL | unidade administrativa no contexto (`local_curto • branch`) |
| `department` | String(100), NOT NULL | **linha principal** da célula |
| `building`/`floor`/`room`/`manager_name`/`description` | nullable | **não usados** (fora do padrão 063; nenhuma composição nova) |

### Custodian — SOMENTE LEITURA, sem FK com Location

`Custodian.department` é conceito distinto de `Location.department` (sem FK entre si) — a feature usa **apenas** `Location.department` para a apresentação da localização (spec §10/§16; já decidido na 063).

### Relações carregadas (já existentes, nenhuma nova)

`get_all_movements` (L479–485) carrega por `joinedload`: `Movement.asset`, `origin_location`, `destination_location`, `origin_custodian`, `destination_custodian`. **Nenhuma query nova, nenhum JOIN novo, nenhum campo novo.**

## Contraste Snapshot × Cadastro atual (decisão da clarificação)

| Superfície | Fonte exibida | Afetada pela feature? |
|---|---|---|
| Tabela Fluxo Global (`movements/list.html`) | **cadastro atual** quando relação existe; snapshot caso contrário | **SIM** (única superfície alterada) |
| Banco (`movements.*_location_name`) | snapshot imutável na gravação | NÃO (zero DDL, zero UPDATE) |
| Busca 049 (`ilike` sobre snapshot) | snapshot | NÃO |
| CSV (`generate_movements_csv`) | snapshot bruto | NÃO (guarda byte-a-byte) |
| Termo (`get_term_details`) | snapshot | NÃO |
| Dashboard / relatório / trilha 063 / dropdown 062 | cada um, formatação própria | NÃO |

## Validações e transições de estado

Nenhuma nova validação; nenhum estado transitado. A feature não toca `create_movement`, `MovementService`, schemas Pydantic (`MovementCreate`/`MovementFilter`) nem nenhum caminho de escrita.

## Compatibilidade de dados históricos

Registros antigos podem ter snapshot em qualquer formato (incluindo literais e dados pré-Feature 005): o fallback ao snapshot cru exibe qualquer conteúdo sem interpretá-lo — a página nunca quebra e nunca inventa dados (spec §12, casos 5–8). Não há auditoria linha a linha dos snapshots de produção; a robustez vem do fallback, não de suposições sobre o formato (incerteza (c) registrada na spec §22).
