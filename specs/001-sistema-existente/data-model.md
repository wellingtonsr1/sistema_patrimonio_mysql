# Phase 1 — Data Model: 001-sistema-existente

**Feature**: SisPatrimônio Pro — Baseline do Sistema Existente | **Date**: 2026-09-14

> Espelho fiel dos modelos SQLAlchemy reais (`app/models/`) — **sem alteração de schema**.
> Fonte única verificável das 17 tabelas. Nenhuma entidade nova; nenhum campo novo.
> Estados (enums) conforme `app/models/enums.py`.

---

## 1. Visão geral dos relacionamentos

```text
User ──1:N── UserSession
User ──N:N── Role (via UserRole, assigned_by local|ad)
Role ──N:N── Permission (via RolePermission)
User ──1:N── AuditLog (FK SET NULL; username snapshot)
Asset ──N:1── Location (location_id, nullable)
Asset ──N:1── Custodian (custodian_id, nullable)
Asset ──1:N── Movement (CASCADE) ──N:1── Location×2 (origem/destino) ──N:1── Custodian×2
Asset ──1:N── Maintenance
Inventario ──1:N── InventarioItem (CASCADE) ──N:1── Asset
InventarioItem ──N:1── Location×2 (expected/found) ──N:1── User (checked_by, SET NULL)
Inventario ──N:1── Location (escopo) ──N:1── User (created_by, SET NULL)
ADGroupRole ──N:1── Role
ADSettings (singleton id=1) · SetupClaim (primeiro acesso)
```

**Observação estrutural (fidelidade ao real)**: "Setor" (department) **não é entidade** —
é campo texto em `Custodian.department`, `Location.department` e filtro
`Inventario.department`.

## 2. Domínio patrimonial

### 2.1 Asset — tabela `assets` (`app/models/asset.py`)
- **PK**: `id` (Integer, autoincrement, index).
- **Campos**: `tag` String(50) **unique+index+NOT NULL** (tombamento); `name` String(150)
  NOT NULL+index; `category` Enum(AssetCategory, 11) NOT NULL default OTHER; `brand`
  String(100) null; `model` String(100) null; `serial_number` String(100)
  **unique+index** null; `specifications` Text null; `purchase_date` DateTime null;
  `purchase_value` Float NOT NULL default 0.0; `invoice_number` String(100) null;
  `supplier` String(150) null; `warranty_expiry` DateTime null; `status`
  Enum(AssetStatus, 5) NOT NULL default AVAILABLE; `condition` Enum(AssetCondition, 6)
  NOT NULL default NEW; `notes` Text null; `created_at`/`updated_at` DateTime
  (utcnow/onupdate).
- **FKs**: `location_id` → `locations.id` (null); `custodian_id` → `custodians.id` (null).
- **Relacionamentos**: `movements` (1:N, cascade all/delete-orphan, order desc timestamp),
  `maintenances` (1:N, cascade), `location`, `custodian`.
- **Estados** (`AssetStatus`): DISPONIVEL · EM_USO · EM_MANUTENCAO · EM_TRANSITO ·
  BAIXADO. **Condição** (`AssetCondition`): NOVO · EXCELENTE · BOM · REGULAR · RUIM ·
  INSERVIVEL. **Categoria** (11): NOTEBOOK · DESKTOP · MONITOR · SERVIDOR ·
  REDE_E_CONECTIVIDADE · IMPRESSORA · SMARTPHONE_TABLET · MOBILIARIO · VEICULO ·
  EQUIPAMENTO_GERAL · OUTROS.

### 2.2 Movement — tabela `movements` (`app/models/movement.py`)
- **PK**: `id`; **`movement_uuid` String(36) unique+index** (uuid4).
- **FK**: `asset_id` → `assets.id` **ondelete CASCADE** NOT NULL+index.
- **Campos**: `movement_type` Enum(MovementType, 8) NOT NULL+index; `timestamp` DateTime
  NOT NULL+index; snapshots origem `origin_location_id` (FK locations) +
  `origin_location_name` String(150) + `origin_custodian_id` (FK custodians) +
  `origin_custodian_name`; snapshots destino `destination_location_id` +
  `destination_location_name` + `destination_custodian_id` + `destination_custodian_name`;
  transições `previous_status`/`new_status` (NOT NULL)/`previous_condition`/
  `new_condition` (Enums); **`reason` String(255) NOT NULL**; `operator_name` String(100)
  NOT NULL default "Sistema"; `term_code` String(50) index null (TR-AAAA-NNNN);
  `term_signed` Boolean default **False**; `notes` Text null; `created_at`.
- **Tipos** (`MovementType`): ENTRADA_AQUISICAO · ALOCACAO_CAUTELA ·
  TRANSFERENCIA_LOCAL · ENVIO_MANUTENCAO · RETORNO_MANUTENCAO · DEVOLUCAO_ESTOQUE ·
  BAIXA_DESCARTE · ATUALIZACAO_ESTADO.
- **Transições de status por tipo** (implementadas em `movement_service.py`):

| Tipo | Status final | Custódia | Termo |
|---|---|---|---|
| ENTRADA_AQUISICAO | — (criação) | inicial | não |
| ALOCACAO_CAUTELA | EM_USO | destino obrigatório | **sim (auto)** |
| TRANSFERENCIA_LOCAL | EM_USO ou DISPONIVEL | opcional | não |
| ENVIO_MANUTENCAO | EM_MANUTENCAO | mantém | não |
| RETORNO_MANUTENCAO | DISPONIVEL (ou EM_USO) | opcional | não |
| DEVOLUCAO_ESTOQUE | DISPONIVEL | limpa | **sim (auto)** |
| BAIXA_DESCARTE | BAIXADO | limpa; condição→INSERVIVEL | não |
| ATUALIZACAO_ESTADO | mantém | mantém | não |

### 2.3 Maintenance — tabela `maintenances` (`app/models/maintenance.py`)
- **FK**: `asset_id` → assets. **Campos**: `maintenance_type` Enum(3: PREVENTIVA ·
  CORRETIVA · UPGRADE); `status` Enum(4: AGENDADA · EM_ANDAMENTO · CONCLUIDA ·
  CANCELADA); `provider_name`; `description`; `solution`; `cost` Float; `start_date`;
  `end_date`. Integrada ao fluxo (abrir/fechar OS gera movimentações ENVIO/RETORNO).

## 3. Pessoas e lugares

### 3.1 Custodian — tabela `custodians` (`app/models/custodian.py`)
- **PK** `id`; `registration_code` String(50) **unique+index+NOT NULL** (matrícula);
  `name` String(150) NOT NULL+index; `email` String(150) **unique+NOT NULL**; `cpf`
  String(20) null; `role` (cargo) String(100) NOT NULL; `department` (setor) String(100)
  NOT NULL; `is_active` Boolean default True; `created_at`.
- **Relacionamento**: `assets` (1:N).

### 3.2 Location — tabela `locations` (`app/models/location.py`)
- **PK** `id`; `name` String(100) **unique+NOT NULL+index**; `branch` String(100)
  NOT NULL (filial); `building`/`floor`/`room` null; `department` String(100) NOT NULL;
  `manager_name` String(100) null; `description` Text null; `created_at`.
- **Relacionamento**: `assets` (1:N).

## 4. Segurança e controle

### 4.1 User — tabela `users` (`app/models/user.py`)
- **PK** `id`; `username` String(100) **unique+NOT NULL+index**; `password_hash`
  String(255) NOT NULL (pbkdf2_sha256$iter$salt$hash); `full_name`/`email` null;
  `is_active` default True; `is_admin` default False; `auth_provider` String(20) NOT
  NULL default 'local' (local|ad); `last_login` null; `created_at`;
  `failed_login_attempts` Integer NOT NULL default 0; `locked_until` DateTime null;
  AD: `ad_object_guid` String(64) index null, `ad_dn` String(400) null,
  `ad_last_sync` DateTime null.
- **Relacionamentos**: `sessions` (1:N cascade), `user_roles` (1:N cascade).

### 4.2 UserSession — tabela `user_sessions` (`app/models/session.py`)
- `token_hash` String **unique** (SHA-256 do token; token puro nunca no banco);
  `expires_at`; FK `users.id` **CASCADE**.

### 4.3 RBAC — `roles`, `permissions`, `user_roles`, `role_permissions`
- **Role** (`roles`): `name` unique; `description`; `is_system` (perfis padrão
  não-excluíveis).
- **Permission** (`permissions`): `name` **unique** (`modulo.acao` — 29 no catálogo);
  `module`; `label`; `description`.
- **UserRole** (`user_roles`): unique(user, role); `assigned_by` String(20) NOT NULL
  default 'local' (local|ad — coluna adicionada por migração leve).
- **RolePermission** (`role_permissions`): unique(role, permission).

### 4.4 AuditLog — tabela `audit_logs` (`app/models/audit_log.py`)
- **PK** `id`; `timestamp` DateTime NOT NULL+index; `user_id` FK users **SET NULL** +
  `username` String(100) snapshot; `action` String(50) NOT NULL+index; `module`
  String(50) index; `resource` String(100); `resource_id` Integer; `resource_ref`
  String(150) (tag/matrícula/username/código); `ip_address` String(45); `result`
  String(20) NOT NULL default SUCCESS (SUCCESS|FAILURE|DENIED|LOCKED); `description`
  Text; `previous_data`/`new_data` Text (JSON).

### 4.5 AD — `ad_settings`, `ad_group_roles`
- **ADSettings** (`ad_settings`): singleton **id=1** — `enabled`, `server`, `port`,
  `use_ldaps`, `verify_tls`, `base_dn`, `search_dn`, `bind_user` (legado),
  `timeout_seconds`, `auto_create_user`, `link_by_email`, `group_role_priority`,
  `disabled_behavior`.
- **ADGroupRole** (`ad_group_roles`): `group_name` **unique**; FK `role_id` → roles;
  `priority` Integer (menor vence); `is_active`.

## 5. Inventário

### 5.1 Inventario — tabela `inventarios` (`app/models/inventario.py`)
- **PK** `id`; **`code` String(50) unique+NOT NULL+index** (INV-AAAA-NNNN); `name`
  String(150) NOT NULL; `status` Enum(InventarioStatus: PLANEJADO · EM_ANDAMENTO ·
  ENCERRADO) NOT NULL default PLANEJADO+index; escopo `location_id` FK locations null +
  `department` String(100) null; **`scope_filters` String(255)** (snapshot textual dos
  filtros); `notes` Text; `created_by_id` FK users **SET NULL** + `created_by_name`
  snapshot; `created_at`; `started_at` null; `closed_at` null; `closed_by_name` null;
  `closure_notes` Text null.
- **Relacionamento**: `itens` 1:N cascade, order id.

### 5.2 InventarioItem — tabela `inventario_itens`
- **Constraint**: **UniqueConstraint(`inventario_id`, `asset_id`)**
  name=`uq_inventario_item_asset`.
- **FKs NOT NULL**: `inventario_id` → inventarios **CASCADE**; `asset_id` → assets
  **CASCADE** (ambas indexadas).
- **Snapshot da expectativa**: `expected_location_id` (FK) + `expected_location_name`
  String(150) + `expected_custodian_name` String(150).
- **Resultado**: `status` Enum(InventarioItemStatus) NOT NULL default PENDENTE+index;
  **`nao_previsto` Boolean NOT NULL default False**; `found_location_id` (FK) +
  `found_location_name` snapshot; `observation` Text.
- **Comprovação**: `checked_by_id` FK users **SET NULL** + `checked_by_name` +
  `checked_at`; `created_at`.
- **Estados** (`InventarioItemStatus`): PENDENTE · ENCONTRADO · LOCAL_DIFERENTE ·
  NAO_ENCONTRADO · SEM_IDENTIFICACAO.

### 5.3 SetupClaim — tabela `setup_claims`
- Suporte ao primeiro acesso idempotente (`/setup`), contra condição de corrida.

## 6. Regras de validação relevantes (implementadas, por entidade)

| Entidade | Regra | Onde |
|---|---|---|
| Asset | tag única (normalizada uppercase); serial único se informado | `asset_service.create` + unique no banco |
| Movement | reason obrigatória (min 3 no schema); bem BAIXADO não movimenta; alocação exige custodiante; transferência exige local | `movement_service.create_movement`; `schemas/movement.py` |
| Movement | termo TR-AAAA-NNNN para alocação/devolução (generate_term ou tipo) | `movement_service` |
| Custodian | matrícula e e-mail únicos | unique no banco |
| Location | nome único; branch e department obrigatórios | unique/NOT NULL |
| User | username único; senha ≥ 8 caracteres (hash PBKDF2) | `auth_service.create_user` |
| Inventario | código INV-AAAA-NNNN sequencial; encerramento exige 0 pendentes | `inventario_service.next_code/close_inventario` |
| InventarioItem | (inventário, bem) único; LOCAL_DIFERENTE exige local ≠ esperado; não previsto não aceita resultado padrão | unique constraint; `record_check` |
| UserSession | token hash único; expiração no servidor | `session_service` |
| UserRole | assigned_by preserva perfis manuais na sync AD | `ad_service` |

## 7. Impacto de schema desta feature

**NENHUM.** Nenhuma tabela, coluna, índice ou constraint é criado, alterado ou removido.
Mecanismo de evolução futura (referência): `app/database.py` → `init_db()`
(`Base.metadata.create_all`) + `_ensure_schema_migrations()` (`ALTER TABLE ... ADD
COLUMN IF NOT EXISTS` — aditivo, idempotente, MariaDB 10.5+).
