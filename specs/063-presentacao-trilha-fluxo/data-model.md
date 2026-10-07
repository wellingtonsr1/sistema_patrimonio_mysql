# Data Model — Feature 063: Padronização da Apresentação de Origem e Destino

**Natureza**: documento de **não-mudança**. A spec (FR-007) e o plano estabelecem **zero DDL**: nenhuma tabela, coluna, índice, FK, enum ou dado é criado, alterado ou migrado. Este registro torna explícito o que permanece intocado e de onde a apresentação lê seus dados.

## Entidades envolvidas (todas existentes, todas intocadas)

### `Movement` (tabela `movements`) — fonte de leitura

| Campo | Tipo atual | Papel nesta feature |
|---|---|---|
| `origin_location_id` / `destination_location_id` | FK nullable | relação carregada para o template (joinedload); quando presente, alimenta o novo render |
| `origin_location_name` / `destination_location_name` | String (snapshot imutável) | **formato preservado** `"{branch} - {department} ({name})"` (FR-003); fallback de exibição quando a relação não existe (FR-010); **nada é regravado** (FR-004) |
| `origin_custodian_name` / `destination_custodian_name` | String (snapshot imutável) | linha do colaborador — exibição inalterada |
| `movement_type`, `term_code`, `reason`, `notes`, `operator_name`, `timestamp` | — | exibidos como hoje, sem alteração |

### `Location` (tabela `locations`) — fonte de leitura (relação)

| Campo | Tipo atual | Papel nesta feature |
|---|---|---|
| `id` | Integer PK | — (nenhum vínculo novo) |
| `name` | String(100) UNIQUE NOT NULL | dá o `local_curto` do contexto (com remoção do sufixo ` - {department}` quando presente) |
| `branch` | String(100) NOT NULL | unidade administrativa do contexto (`Localização • Unidade`) |
| `department` | String(100) NOT NULL | **linha principal** (Departamento/Setor) e parâmetro da deduplicação |
| `building` / `floor` / `room` / `manager_name` / `description` | nullable | **não usados** — `building` é nullable e não populado na produção/importação (research R2) |

Sem alteração de tipo, constraint, índice ou valor.

### `Asset` (tabela `assets`) — intocada

- `location_id` / `custodian_id`: contexto atual da página ("Custódia & Localização Atual") — bloco intocado (FR-006).

### `Custodian` (tabela `custodians`) — intocada

- `department` do colaborador NÃO é unificado com `Location.department` (colunas distintas, sem FK) — apenas documentado (spec §10).

## Validações e regras (nenhuma nova)

- Nenhuma validação de negócio é criada ou movida (Princípio III). O backend continua validando movimentações como hoje (matriz da Feature 005) — regras intocadas.
- A deduplicação de rótulos (`local_curto`, omissão de componentes repetidos) é **regra de apresentação** no template — não valida, não normaliza e não persiste nada.

## Transições de estado

Nenhuma. Nenhum estado de bem, movimentação, inventário ou localização é alterado por esta feature.

## Diagrama do fluxo (inalterado no que grava; alterado só no que exibe)

```
movements (FK + snapshots imutáveis "{branch} - {department} ({name})")  ← intocado
        │
        │ MovementService.get_timeline_for_asset  ← intocado (joinedload já entrega Location)
        ▼
Template assets/detail.html — card flow-card                             ← ÚNICA MUDANÇA
        │  relação presente: título = department · contexto = local_curto • branch (dedup)
        │  relação ausente: snapshot cru como texto único (fallbacks atuais)
        ▼
HTML renderizado em /assets/{id}  ← apenas apresentação; busca/termo/relatórios fora do escopo
```
