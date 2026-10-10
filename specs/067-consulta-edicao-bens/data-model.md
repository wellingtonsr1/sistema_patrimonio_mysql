# Data Model — 067-consulta-edicao-bens

**Data**: 2026-10-10 | **DDL**: **ZERO** (Constitution VII) — nenhuma tabela, coluna, índice ou migração é criada/alterada. Todos os campos usados nesta feature **já existem**: `assets.notes` e `assets.updated_at` (editáveis/exibidos) e `audit_logs.*` (fonte do histórico).

## 1. Entidades envolvidas

### `Asset` (tabela `assets`) — estrutura inalterada

| Campo | Tipo / restrição | Papel nesta feature |
|---|---|---|
| `id` | Integer PK | Identificador do bem (URL `/assets/{id}`, QR Code, auditoria) — **nunca alterado** |
| `tag` | String(50) **UNIQUE** NOT NULL index | Tombamento — **PROTEGIDO** (não consta do schema de edição) |
| `name` | String(150) NOT NULL index | **Editável** (obrigatório, ≤150) |
| `category` | Enum(`AssetCategory`, 11) NOT NULL | **Editável** (vocabulário controlado) |
| `brand` / `model` | String(100) null | **Editáveis** (≤100) |
| `serial_number` | String(100) **UNIQUE** index null | **Editável** (≤100, único quando informado) |
| `specifications` | Text null | **Editável** (texto livre) |
| `purchase_date` / `warranty_expiry` | DateTime null | **Editáveis** (data válida) |
| `purchase_value` | Float NOT NULL default 0.0 | **Editável** (≥ 0) |
| `invoice_number` | String(100) null | **Editável** (≤100) |
| `supplier` | String(150) null | **Editável** (≤150) |
| `condition` | Enum(`AssetCondition`, 6) NOT NULL | **Editável**; mudança gera movimentação `ATUALIZACAO_ESTADO` (P2 aprovada) |
| `notes` | Text null | **Editável** — e **passa a ser exibido** no detalhe |
| `status` | Enum(`AssetStatus`, 5) NOT NULL | **PROTEGIDO** — só pelo motor de movimentações |
| `location_id` | FK `locations.id` null | **PROTEGIDO** — só pelo motor de movimentações (a tela exibe `Location.branch`/`department` da localização atual) |
| `custodian_id` | FK `custodians.id` null | **PROTEGIDO** — só pelo motor de movimentações |
| `created_at` | DateTime | Somente leitura |
| `updated_at` | DateTime (`onupdate=now_utc`) | **Passa a ser exibido** e serve de **versão lógica** para o controle de conflito (research R7) — sem coluna nova |

### `AuditLog` (tabela `audit_logs`) — reuso, nenhuma alteração

Fonte única do histórico de alterações cadastrais (Constitution IX). Campos usados na exibição: `timestamp`, `action`, `module`, `resource`, `resource_id`, `resource_ref`, `username`, `ip_address`, `result`, `description` ("Campos alterados: …") e `previous_data`/`new_data` (JSON desserializado).

- **Filtro do histórico cadastral do bem**: `resource == 'Asset' AND resource_id == <asset_id>`.
- **Escrita**: `write_change_audit(..., action=ACTION_UPDATE, module="Patrimônio", resource="Asset", resource_ref=asset.tag, resource_id=asset.id, before=..., after=..., commit=False)` na mesma transação da alteração.
- **Sem** rota de escrita/exclusão de trilha; **sem** credenciais.

### `Movement` (tabela `movements`) — imutável nesta feature

Único evento criado por efeito da edição: `MovementType.STATUS_UPDATE` (`ATUALIZACAO_ESTADO`) quando `condition` muda, agora com `operator_name` = usuário autenticado e `reason` informado (research R4). Movimentações históricas **nunca** são editadas ou removidas.

### `InventarioItem` / `Inventario` — somente leitura

Nenhuma escrita. A lista esperada (`expected_location_id/name`, `expected_custodian_name`) é snapshot de geração e permanece imune; a ata lê `tag`/`name`/`category` ao vivo (risco conhecido e **aceito** na P5 — spec §14 / research R10; dívida **M-003**).

## 2. Matriz de campos: editável × protegido × exibido

> **Fonte única desta matriz**: esta seção. Na spec, §1.3 é o **diagnóstico (as-is)** e §4.3 é a **decisão de negócio (to-be)**; havendo divergência futura, prevalece esta tabela, e §4.3/§1.3 devem ser corrigidos para refleti-la.

| Campo (negócio) | Coluna | Editável nesta feature | Exibido no detalhe (após a feature) |
|---|---|---|---|
| Nome do bem | `name` | ✅ (obrigatório) | ✅ |
| Categoria | `category` | ✅ | ✅ (badge) |
| Marca / Modelo | `brand` / `model` | ✅ | ✅ |
| Nº de série | `serial_number` | ✅ (único) | ✅ |
| Especificações técnicas | `specifications` | ✅ | ✅ (condicional: só se preenchido) |
| Aquisição/fiscal | `purchase_date`, `purchase_value`, `invoice_number`, `supplier`, `warranty_expiry` | ✅ | ✅ |
| Condição | `condition` | ✅ (P2 aprovada) | ✅ |
| Observações | `notes` | ✅ | ✅ **novo** |
| Última atualização | `updated_at` | ❌ | ✅ **novo** |
| **Tombamento** | `tag` | ❌ | ✅ |
| **Situação patrimonial** | `status` | ❌ | ✅ |
| **Localização / Unidade / Departamento** | `location_id` → `locations.*` | ❌ | ✅ |
| **Custodiante** | `custodian_id` → `custodians.*` | ❌ | ✅ |
| Criação | `created_at` | ❌ | — |

## 3. Regras de validação (derivadas da spec §4)

| # | Regra | Onde é aplicada | Origem |
|---|---|---|---|
| V1 | `name` obrigatório e não vazio após `strip()` | Servidor (service) | FR-006, AC04 |
| V2 | `len(name) ≤ 150`; `len(brand/model/serial_number/invoice_number) ≤ 100`; `len(supplier) ≤ 150` — excedeu → rejeição com mensagem, **sem truncamento** | Servidor (service) | FR-006, AC04 |
| V3 | `purchase_value ≥ 0` | Servidor (service) | FR-006, AC04 |
| V4 | `serial_number` único quando informado, ignorando o próprio `id` (mensagem atual: "Já existe um equipamento com o número de série '…'") | Servidor (`AssetService.update`, regra existente preservada) | FR-010, AC04 |
| V5 | `tag` **não** pode ser alterado: campo fora do schema; valor enviado é ignorado | Schema + service | FR-009, AC06 |
| V6 | `status`, `location_id`, `custodian_id` **não** podem ser alterados: fora do schema; valores enviados são ignorados | Schema + service | FR-011, AC12 |
| V7 | `category` e `condition` devem pertencer aos vocabulários controlados (`AssetCategory`/`AssetCondition`); valor inválido → rejeição | Pydantic (tipo) + service | FR-006 |
| V8 | Mudança de `condition` gera **um** evento `ATUALIZACAO_ESTADO` com operador autenticado | Serviço (`AssetService.update` + `MovementService`/modelo) | FR-012, AC12 |
| V9 | **Nada mudou** → nenhuma auditoria e nenhuma movimentação gerada; usuário informado | Serviço/rota | FR-019, AC11 |
| V10 | **Conflito de edição** → `updated_at` enviado ≠ gravado recusa a gravação com mensagem (P3 aprovada) | Serviço/rota (controle otimista) | FR-018, AC11 |
| V11 | **Bem `BAIXADO`** → edição recusada com mensagem clara (P4 aprovada) | Rota/serviço | FR-018 |
| V12 | Alteração e auditoria na **mesma transação**; falha → rollback total | Rota (orquestração) + parâmetro `commit` aditivo | FR-015, AC11 |
| V13 | Requisições sem `patrimonio.editar` (web ou API) → 403 sem gravação, com `ACESSO_NEGADO` na trilha | `require_permission` | FR-005/FR-018, AC07 |
| V14 | Bem inexistente → 404 amigável, sem gravação | Rota | FR-003/FR-018 |

## 4. Transições de estado

- **Nenhuma transição nova de `AssetStatus`** é introduzida por esta feature (localização/custódia/situação seguem exclusivamente `MovementService.create_movement`).
- A única consequência de estado é a **movimentação `ATUALIZACAO_ESTADO`** já existente quando `condition` muda (agora com operador/motivo corretos).

## 5. Dados existentes e integridade

- Nenhum dado é migrado, regravado ou normalizado (zero UPDATE em massa).
- Termos e snapshots de movimentação permanecem congelados (`Movement.origin_*`/`destination_*`).
- `InventarioItem.expected_*` permanece congelado; itens e resultados não são tocados.
- Ressalva conhecida e registrada: ata de inventário e CSV de movimentações leem `tag`/`name`/`category` do cadastro **atual** (spec §1.7) — decisão **P5 aprovada**: manter como está nesta feature (dívida M-003).
- Histórico cadastral: leitura de `audit_logs` limitada aos **50 eventos mais recentes**, com aviso ao usuário quando houver mais (FR-016) — mesmo teto da trilha atual.
