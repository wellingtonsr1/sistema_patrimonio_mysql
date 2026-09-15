# SisPatrimônio Pro — Specify (Sistema Existente)

> **Documento gerado por engenharia reversa do código-fonte real do projeto.**
> Todas as afirmações abaixo foram verificadas nos arquivos indicados. Onde uma
> informação não pôde ser confirmada no código, está marcada explicitamente como
> **NÃO IDENTIFICADO NO CÓDIGO**, **NÃO FOI POSSÍVEL CONFIRMAR**, **PARCIAL** ou
> **PLANEJADO/NÃO IMPLEMENTADO**.
>
> Esta especificação descreve o sistema **como ele existe hoje**. Ela não propõe
> refatorações, não define requisitos futuros e não mistura recomendações com
> comportamento real (seção 25 separa problemas encontrados).

---

## 1. Contexto do Sistema

| Item | Valor verificado |
|---|---|
| Nome | SisPatrimônio Pro (`APP_NAME`, `app/config.py`) |
| Versão | `1.2.0` (`APP_VERSION`, `app/config.py`) |
| Finalidade | Gestão Patrimonial: controle de ativo fixo/equipamentos, com rastreamento auditável do fluxo de movimentação de cada bem |
| Status | Em desenvolvimento ativo; suíte de **154 testes** automatizados |
| Banco de produção | **MariaDB/MySQL** via SQLAlchemy (driver PyMySQL). **Não há fallback para SQLite na aplicação**: sem `DATABASE_URL`, `app/config.py` levanta `RuntimeError` e o sistema não inicia |
| Linguagem | Python 3.10+ |
| Framework web | FastAPI + Uvicorn (ASGI) |
| ORM | SQLAlchemy 2 (`Base = declarative_base()`, `app/database.py`) |
| Validação | Pydantic v2 |
| Templates | Jinja2 + Bootstrap 5.3.3 (CDN) + Bootstrap Icons |
| Frontend JS | Chart.js, QRCode.js (CDN, `app/web/templates/base.html`), `static/js/main.js` |
| Diretório | LDAP/LDAPS via `ldap3` (Microsoft AD ou Samba AD DC) |
| Exportações | CSV (UTF-8 BOM), Excel via OpenPyXL, PDF via ReportLab |
| Testes | pytest + TestClient do FastAPI |
| Configuração | `app/config.py` — único ponto, via variáveis de ambiente (`python-dotenv`, `.env` presente na raiz) |

Arquivos `.env` existentes na raiz: **SEGREDO/CONFIGURAÇÃO SENSÍVEL IDENTIFICADO — conteúdo omitido** (não lido intencionalmente durante a análise).

---

## 2. Objetivo

Documentar de forma fiel, estruturada e verificável o sistema existente, servindo de
base documental para o Spec Kit. Este documento é descritivo (estado atual), não
normativo; os princípios de governança estão na Constitution (`.specify/memory/constitution.md`).

---

## 3. Usuários e Perfis

Fonte única: `app/services/permission_service.py` (`PERMISSION_CATALOG`, `DEFAULT_ROLES`).

**Modelo de acesso:** `Usuário ──N:N──> Perfis (roles) ──N:N──> Permissões (modulo.acao)`.

**Catálogo de permissões (29, padrão `modulo.acao`):**

| Módulo | Permissões |
|---|---|
| Patrimônio | `patrimonio.visualizar`, `patrimonio.criar`, `patrimonio.editar`, `patrimonio.excluir` |
| Movimentação | `movimentacao.visualizar`, `movimentacao.criar`, `movimentacao.editar`, `movimentacao.cancelar` |
| Manutenção | `manutencao.visualizar`, `manutencao.criar`, `manutencao.editar`, `manutencao.finalizar` |
| Colaboradores | `colaboradores.visualizar`, `colaboradores.criar`, `colaboradores.editar` |
| Locais | `locais.visualizar`, `locais.criar`, `locais.editar` |
| Usuários | `usuarios.visualizar`, `usuarios.criar`, `usuarios.editar`, `usuarios.bloquear` |
| Perfis | `perfis.visualizar`, `perfis.criar`, `perfis.editar`, `perfis.excluir` |
| Relatórios | `relatorios.visualizar`, `relatorios.exportar` |
| Inventário | `inventario.visualizar`, `inventario.criar`, `inventario.conferir`, `inventario.encerrar` |
| Auditoria | `auditoria.visualizar` |

**Perfis padrão (7, `is_system=True`, não excluíveis — seed idempotente `ensure_default_roles`):**

| Perfil | O que pode (verificado em `DEFAULT_ROLES`) |
|---|---|
| Administrador | Todas as 29 permissões |
| Gestor de TI | Visualiza/cadastra/edita patrimônio, movimenta, manutenção completa, visualiza colaboradores/locais, relatórios + exportação |
| Técnico de TI | Visualiza patrimônio/movimentações, manutenção completa, visualiza colaboradores, relatórios (sem exportar) |
| Patrimônio | Patrimônio completo (visualizar/criar/editar), movimentar, inventário completo (criar/conferir/encerrar), colaboradores completos, locais (visualizar), relatórios + exportação |
| Almoxarifado | Visualiza patrimônio, movimenta, visualiza colaboradores/locais, relatórios |
| Auditor | Somente leitura (patrimônio, movimentações, manutenção, inventário, colaboradores, locais, relatórios + exportação) **e** `auditoria.visualizar` |
| Consulta | Somente leitura dos módulos listados (sem exportar, sem auditoria) |

**Superusuário:** o flag legado `users.is_admin` é tratado como bypass total das
verificações RBAC (`user_has_permission` retorna `True` sempre; `require_permission`
documenta "bypass total, auditado"). Recomendação de uso do perfil Administrador consta
apenas na documentação.

---

## 4. Arquitetura Existente

### 4.1 Camadas (reais, verificadas)

```text
Interface Web (Jinja2)               API REST (/api/v1)
app/web/routes.py                    app/api/*.py
app/web/admin_routes.py              (v1_router agrega: auth, assets,
app/web/help_routes.py                movements, custodians, locations, reports)
        └────────────┬──────────────┘
                     ↓
        Dependências de auth/RBAC (app/api/deps.py)
        require_api_auth · require_web_auth · require_permission
                     ↓
        Provedores de autenticação (app/services/auth_provider.py)
        local (PBKDF2) · AD (LDAP bind)
                     ↓
        Services (regras de negócio) — app/services/*.py (17 módulos)
                     ↓
        Models (SQLAlchemy) — app/models/*.py
                     ↓
        MariaDB/MySQL (DATABASE_URL, driver PyMySQL)
```

- As rotas **não** concentram regras de negócio: validam entrada via schemas Pydantic e
  delegam aos services. Exceção observada e documentada em §25: consultas ORM curtas
  inline em `app/web/admin_routes.py` e em algumas rotas web (ex.: busca de inventário).
- Frontend estático: `app/web/static/css/style.css` e `app/web/static/js/main.js`
  (dark mode, tooltips, alertas, sidebar mobile).
- Logs técnicos: `app/logging_config.py` → `data/logs/app.log` e `app.error.log`
  (rotação 5 MB × 5 backups), configurado por `run.py`.

### 4.2 Fluxo de uma requisição (real)

```text
Usuário/Navegador ou cliente HTTP
  ↓
FastAPI (app/main.py) — lifespan: init_db(), ensure_admin_user(), ensure_default_roles()
  ↓
Rota web (web_router) ou API (api_v1_router, prefixo /api/v1)
  ↓
Dependência: require_web_auth (redirect 303 → /login?next=) ou require_api_auth (401)
  ↓ (se a rota exigir)
require_permission("modulo.acao") → deny by default → 403 auditado (ACESSO_NEGADO)
  ↓
Service (regra de negócio, persistência via ORM)
  ↓
commit → trilha de auditoria (audit_logs) quando aplicável
  ↓
Resposta: Template Jinja2 (web) ou JSON/StreamingResponse (API)
```

### 4.3 Tratamento de erros

- Handler central `http_exception_handler` em `app/main.py`: 403 e 404 retornam páginas
  HTML amigáveis (`403.html`, `404.html`).
- Status HTTP estabelecidos: `401` não autenticado · `403` sem permissão · `404` não
  encontrado · `423` conta bloqueada (lockout) · `503` AD indisponível.
- Services sinalizam erros de negócio com `ValueError` (mensagem em português), capturados
  pelas rotas.

---

## 5. Módulos Existentes

| # | Módulo | Componentes principais (verificados) |
|---|---|---|
| 1 | Dashboard | `dashboard_service.py` (`get_stats`: KPIs + recent_movements/recent_assets), `dashboard.html`, Chart.js |
| 2 | Patrimônio (bens) | `asset_service.py`, `assets_api.py`, rotas `/assets*`, templates `assets/*`, depreciação linear, etiquetas QR (`/assets/labels`) |
| 3 | Importação CSV | `import_service.py` (bens), `custodian_import_service.py` (colaboradores), `location_import_service.py` (locais) — fluxo pré-visualizar → confirmar |
| 4 | Movimentações | `movement_service.py` (`create_movement` = motor do fluxo), `movements_api.py`, rotas `/movements*`, templates `movements/*` |
| 5 | Termos | `MovementService.get_term_details`, template `movements/term.html`, rota `/movements/{id}/term` |
| 6 | Manutenções | `maintenance_service.py`, rotas `/maintenances*`, templates `maintenances/*` |
| 7 | Colaboradores | `custodian_service.py`, rotas `/custodians*`, templates `custodians/*` |
| 8 | Locais | `location_service.py`, rotas `/locations*`, templates `locations/*` |
| 9 | Inventário | `inventario_service.py`, rotas `/inventarios*` + `/api/v1/reports/inventarios/{id}/csv|excel|pdf`, templates `inventarios/*` |
| 10 | Relatórios | `report_service.py` (CSV/XLSX/PDF), `reports_api.py`, rotas `/reports/*` |
| 11 | Administração | `admin_routes.py`: `/admin/users*`, `/admin/roles*`, `/admin/audit`, `/admin/ad*`, `/profile/password` |
| 12 | Autenticação/Sessão | `auth_service.py`, `session_service.py`, `auth_provider.py`, rotas `/login`, `/logout`, `/setup`, API `/auth/*` |
| 13 | RBAC | `permission_service.py`, `require_permission` em `deps.py` |
| 14 | Auditoria | `audit_service.py`, modelo `AuditLog`, página `/admin/audit` |
| 15 | Integração AD | `ad_ldap.py` (protocolo), `ad_service.py` (integração), tela `/admin/ad` |
| 16 | Central de Ajuda | `help_service.py` (21 artigos, 12 FAQ, 7 categorias), `help_routes.py`, `/ajuda` |
| 17 | CLI | `app/cli.py`: `stats`, `list`, `show`, `move`, `create-user` (--role repetível) |

---

## 6. Entidades e Dados

Fonte: `app/models/` (17 arquivos). Banco real: MariaDB.

### 6.1 Domínio patrimonial

**`Asset` (tabela `assets`)** — o bem patrimonial.
- PK `id`; **`tag` único, indexado, não nulo** (tombamento, `String(50)`); **`serial_number` único quando informado** (nullable); `name` não nulo (150); `category` Enum(11 valores, default OTHER); dados fiscais (`purchase_date`, `purchase_value` não nulo default 0.0, `invoice_number`, `supplier`, `warranty_expiry`); estado (`status` Enum AssetStatus default AVAILABLE; `condition` Enum AssetCondition default NEW); FKs `location_id` → locations (nullable), `custodian_id` → custodians (nullable); `notes`, `created_at`, `updated_at`.
- Relacionamentos: `movements` (cascade delete-orphan), `maintenances` (cascade delete-orphan), `location`, `custodian`.

**`Movement` (tabela `movements`)** — histórico imutável do fluxo.
- PK `id`; **`movement_uuid` único** (String(36), uuid4); FK `asset_id` → assets **ondelete CASCADE**, não nulo; `movement_type` Enum(MovementType) não nulo; `timestamp` não nulo.
- Snapshots de origem: `origin_location_id` (FK) + `origin_location_name`; `origin_custodian_id` (FK) + `origin_custodian_name`.
- Snapshots de destino: `destination_location_id` (FK) + `destination_location_name`; `destination_custodian_id` (FK) + `destination_custodian_name`.
- Transições: `previous_status`, `new_status` (não nulo), `previous_condition`, `new_condition`.
- Operação: **`reason` não nulo** (String 255, justificativa obrigatória), `operator_name` não nulo default "Sistema", `term_code` (indexado, ex `TR-2026-0001`), `term_signed` Boolean default **False**, `notes`.

**`Maintenance` (tabela `maintenances`)** — ordem de serviço.
- `maintenance_type` Enum (PREVENTIVA/CORRETIVA/UPGRADE), `status` Enum (AGENDADA/EM_ANDAMENTO/CONCLUIDA/CANCELADA), `provider_name`, `description`, `solution`, `cost`, `start_date`, `end_date`; FK `asset_id`.

### 6.2 Pessoas e lugares

**`Custodian` (tabela `custodians`)** — colaborador/custodiante.
- PK `id`; **`registration_code` único não nulo** (matrícula); `name` não nulo; **`email` único não nulo**; `cpf` (nullable); `role` (cargo) não nulo; `department` (setor) não nulo; `is_active` default True.
- Relacionamento: `assets` (bens sob custódia).

**`Location` (tabela `locations`)** — localização física.
- PK `id`; **`name` único não nulo**; `branch` (filial) não nulo; `building`, `floor`, `room` (opcionais); `department` (setor) **não nulo**; `manager_name` (responsável, opcional); `description`.
- Relacionamento: `assets`.

> **Setor/departamento** não é entidade própria: é campo texto (`Custodian.department`,
> `Location.department`, `Inventario.department`). **Não identificada no código analisado**
> nenhuma tabela de setores.

### 6.3 Segurança e controle

**`User` (tabela `users`)** — PK `id`; `username` único não nulo; `password_hash` não nulo (`pbkdf2_sha256$iter$salt$hash`); `full_name`, `email`; `is_active` default True; `is_admin` default False; `auth_provider` String(20) default `'local'` (`local|ad`); `last_login`; `failed_login_attempts` default 0; `locked_until`; colunas AD (`ad_object_guid` indexado, `ad_dn`, `ad_last_sync`); rel: `sessions`, `user_roles`.

**`UserSession` (tabela `user_sessions`)** — `token_hash` **único** (SHA-256 do token; o token em texto nunca vai ao banco), `expires_at`, FK `users.id` CASCADE.

**`Role` (`roles`)** — `name` único; `description`; `is_system`. **`Permission` (`permissions`)** — `name` único (`modulo.acao`), `module`, `label`, `description`. **`UserRole` (`user_roles`)** — unique (user, role), **`assigned_by`** (`local|ad`, adicionada por migração leve). **`RolePermission` (`role_permissions`)** — unique (role, permission).

**`AuditLog` (`audit_logs`)** — trilha de auditoria (detalhe em §19): `timestamp` indexado; `user_id` FK **SET NULL**; `username` (snapshot textual, sobrevive à exclusão do usuário); `action` indexado (String 50); `module`; `resource`; `resource_id`; `resource_ref` (referência legível: tag, matrícula, username); `ip_address`; `result` default SUCCESS (`SUCCESS|FAILURE|DENIED|LOCKED`); `description`; `previous_data`/`new_data` (JSON em TEXT).

**`ADSettings` (`ad_settings`)** — singleton `id=1`: `enabled`, `server`, `port`, `use_ldaps`, `verify_tls`, `base_dn`, `search_dn`, `bind_user` (legado), `timeout_seconds`, `auto_create_user`, `link_by_email`, `group_role_priority`, `disabled_behavior`. **`ADGroupRole` (`ad_group_roles`)** — `group_name` único, FK `role_id`, `priority` (menor vence), `is_active`.

### 6.4 Inventário

**`Inventario` (tabela `inventarios`)** — PK `id`; **`code` único** (`INV-AAAA-NNNN`); `name` não nulo; `status` Enum(`PLANEJADO`/`EM_ANDAMENTO`/`ENCERRADO`); escopo opcional `location_id` (FK) + `department` (texto); **`scope_filters`** snapshot textual dos filtros (comprovação); `notes`; `created_by_id` FK **SET NULL** + `created_by_name` (snapshot); `created_at`; `started_at`; `closed_at`; `closed_by_name`; `closure_notes`; rel `itens` (cascade delete-orphan).

**`InventarioItem` (tabela `inventario_itens`)** — **UniqueConstraint (`inventario_id`, `asset_id`)** nomeada `uq_inventario_item_asset`; FKs `inventario_id` (CASCADE) e `asset_id` (CASCADE), ambas não nulas; snapshot da expectativa: `expected_location_id` (FK) + `expected_location_name` + `expected_custodian_name`; resultado: `status` Enum(`PENDENTE`/`ENCONTRADO`/`LOCAL_DIFERENTE`/`NAO_ENCONTRADO`/`SEM_IDENTIFICACAO`), **`nao_previsto` Boolean não nulo default False**, `found_location_id` (FK) + `found_location_name` (snapshot), `observation`; comprovação: `checked_by_id` FK **SET NULL** + `checked_by_name` + `checked_at`; `created_at`.

**`SetupClaim` (`setup_claims`)** — usada no fluxo de primeiro acesso (`/setup`) para
verificação idempotente contra condição de corrida.

---

## 7. Regras de Negócio (efetivamente implementadas)

Marcadas no código (arquivo · localização aproximada):

1. **Unicidade de tombamento**: `AssetService.create` rejeita tag duplicada (normalizada para caixa alta) — `asset_service.py` `create()`. Também garantida por constraint `unique` no banco.
2. **Unicidade de número de série**: rejeitada quando informada duplicada — `asset_service.py` `create()`.
3. **Reason obrigatória em movimentação**: `Movement.reason` não nulo; schema `MovementCreate` exige `reason` min 3 (`app/schemas/movement.py`).
4. **Bloqueio de movimentação de bem baixado**: `MovementService.create_movement` levanta `ValueError` se `asset.status == WRITTEN_OFF` e o tipo não é aquisição — `movement_service.py:~25`.
5. **Alocação exige custodiante**: `ALLOCATION` sem `destination_custodian_id` levanta `ValueError` — `movement_service.py`.
6. **Transferência exige local de destino**: `TRANSFER` sem `destination_location_id` levanta `ValueError` — `movement_service.py`.
7. **Transições de status por tipo de movimentação** (regra central do motor):
   - `ALLOCATION` → status `IN_USE`; define custodiante; local opcionalmente.
   - `RETURN_STOCK` → status `AVAILABLE`; limpa custodiante; destino do custodiante gravado como "Almoxarifado / Estoque".
   - `TRANSFER` → define local; custodiante opcional; status `IN_USE` se com custodiante, senão `AVAILABLE`.
   - `MAINTENANCE_OUT` → status `IN_MAINTENANCE`.
   - `MAINTENANCE_IN` → status `AVAILABLE` (ou `IN_USE` se custodiante informado).
   - `WRITE_OFF` → status `WRITTEN_OFF`; limpa custodiante; condição default `INSERVIVEL` se não informada.
   - `STATUS_UPDATE` → mantém status/local/custodiante (destino = origem); altera condição.
8. **Termo sequencial**: gerado quando `generate_term=True` ou tipo ∈ {ALLOCATION, RETURN_STOCK}; numeração `TR-<ano>-<seq 5 dígitos>` contando movimentações de alocação+devolução — `movement_service.py:~135`.
9. **Depreciação linear contábil**: 20% ao ano sobre `purchase_value` (default do parâmetro `annual_rate=0.20`) — `asset_service.py:248 calculate_depreciation()`.
10. **Manutenção integrada ao fluxo**: abrir OS grava `MAINTENANCE_OUT` e conclui com `MAINTENANCE_IN` — `maintenance_service.py` `create()` e `complete_maintenance()`.
11. **RBAC deny by default**: `user_has_permission` retorna `False` sem permissão explícita; única exceção `is_admin` — `permission_service.py`.
12. **Perfis de sistema não excluíveis**: `is_system=True` (verificado no seed; verificação de exclusão em `admin_routes.py:509 delete`).
13. **Último administrador protegido**: bloqueio/desativação do último admin ativo é impedido (regra implementada em `admin_routes.py`; coberta por testes de RBAC).
14. **Auto-bloqueio não permitido**: usuário não pode bloquear a si mesmo — `admin_routes.py` (`toggle-active`).
15. **Lockout por conta**: após `AUTH_MAX_FAILED_ATTEMPTS` (default **10**) falhas consecutivas, `locked_until = agora + AUTH_LOCKOUT_SECONDS` (default 900 s); contador zerado ao bloquear — `auth_service.authenticate()`.
16. **Timing equalizado no login**: usuário inexistente verifica hash dummy para equalizar tempo de resposta — `auth_service.py` `_get_dummy_hash`.
17. **Política de senha mínima**: 8 caracteres para criação, troca e reset — `auth_service.py`.
18. **Troca/reset de senha invalida sessões**: todas as `UserSession` do usuário são apagadas — `auth_service.change_password/reset_password`.
19. **Sessão server-side**: banco guarda apenas hash SHA-256 do token; expiração no servidor (`AUTH_SESSION_TTL`, default 8 h); revogação no logout — `session_service.py`.
20. **Open redirect bloqueado**: `next` do login aceita apenas caminhos internos (`/...` sem `//`) — `app/web/routes.py` `_safe_next_url`.
21. **Inventário nunca altera o cadastro**: `record_check` e `register_unlisted_asset` não tocam em `Asset.location_id/custodian_id/status` — documentado no docstring e verificado no corpo dos métodos — `inventario_service.py`.
22. **Snapshot imutável da expectativa**: `generate_items` copia local/custodiante no momento da criação — `inventario_service.py`.
23. **Encerramento exige conferência total**: `close_inventario` rejeita se houver itens esperados `PENDENTE` — `inventario_service.py`.
24. **Itens travados após encerramento**: `record_check` levanta `ValueError` se inventário `CLOSED` — `inventario_service.py`.
25. **LOCAL_DIFERENTE exige local diverso do esperado**: validação explícita em `record_check` — `inventario_service.py`.
26. **Não previsto não duplica e não aceita resultado "esperado"**: `UniqueConstraint` + lógica em `register_unlisted_asset` (item criado com status `SEM_IDENTIFICACAO`); `record_check` limita não previstos a observação complementar.
27. **Primeira conferência inicia formalmente o inventário**: `started_at` + transição `PLANNED → EM_ANDAMENTO` — `inventario_service.py`.
28. **Códigos sequenciais**: inventário `INV-AAAA-NNNN` (por ano) — `InventarioService.next_code`.
29. **Importações CSV com pré-visualização**: fluxo em duas fases (parse/preview → execute/confirm) nos três importers; com alias de colunas e detecção de duplicatas — `import_service.py`, `custodian_import_service.py`, `location_import_service.py`.
30. **Admin só é criado com `AUTH_ADMIN_PASSWORD` definida** (env) ou via CLI/`/setup` — `auth_service.ensure_admin_user`, `app/web/routes.py` `/setup`.
31. **Primeiro acesso só em instalação nova**: `/setup` disponível apenas sem usuários no banco e sem `AUTH_ADMIN_PASSWORD`; idempotente via `SetupClaim` — `app/web/routes.py:1596-1750`.
32. **AD nunca concede permissão**: acesso somente com grupo mapeado para perfil existente; usuário sem mapeamento não é criado no banco — `ad_service.py` (docstring + `authenticate_and_sync`).
33. **Perfis manuais nunca removidos pela sincronização AD**: atribuições `assigned_by='local'` preservadas; perfis `assigned_by='ad'` são substituídos a cada login — `ad_service.py`.

**Regras aparentemente desejadas, mas NÃO encontradas no código (não implementadas):**
- Cancelamento de movimentação (`movimentacao.cancelar` existe no catálogo e na permissão, mas **NÃO FOI POSSÍVEL CONFIRMAR** rota/endpoint que a execute; a permissão é descrita como "reservado" no próprio catálogo).
- Exclusão de bens via interface/página (permissão `patrimonio.excluir` existe; rota web de exclusão **NÃO IDENTIFICADA NO CÓDIGO**; a permissão faz parte do catálogo/seed).
- Edição de movimentações (`movimentacao.editar` no catálogo; nenhuma rota de edição de movimentação encontrada).
- Edição/exclusão de locais pela web (existe `PUT /api/v1/locations/{id}` na API; rota web de edição de local **NÃO IDENTIFICADA** — somente criação e importação).
- Recuperação de senha por e-mail/autoatendimento (**NÃO IMPLEMENTADO**; existe apenas troca própria com senha atual e reset administrativo).
- Controle de escopo por unidade/setor no usuário (avaliado e adiado conforme `docs/ARQUITETURA_E_MANUTENCAO.md`/README).

---

## 8. Autenticação

Verificado em `app/services/auth_service.py`, `session_service.py`, `auth_provider.py`, `app/api/auth_api.py`, `app/web/routes.py`.

- **Login web**: `GET/POST /login`. `POST` autentica via `resolve_authentication`, trata `AccountLockedError` (mensagem de bloqueio), cria sessão (`create_session`), grava cookie (`set_session_cookie`), audita `LOGIN`/`LOGIN_FALHA`/`LOGIN_BLOQUEADO` com IP.
- **Login API**: `POST /api/v1/auth/login` (form), `POST /api/v1/auth/logout`, `GET /api/v1/auth/me` (dados do usuário + permissões).
- **Logout**: `POST /logout` (web) e API — revoga a sessão no servidor e limpa o cookie; audita `LOGOUT`.
- **Sessão**: token `secrets.token_urlsafe(32)`; cookie `HttpOnly`, `SameSite=Lax`, `Secure` conforme `AUTH_COOKIE_SECURE` (default false); banco guarda **apenas** `sha256(token)`; TTL default 28800 s (8 h); `purge_expired_sessions` remove expiradas.
- **Senha local**: PBKDF2-HMAC-SHA256, salt de 16 bytes por usuário, `AUTH_PBKDF2_ITERATIONS` default 600000, formato `pbkdf2_sha256$iter$salt$hash`; verificação com `hmac.compare_digest` (timing-safe). Somente biblioteca padrão.
- **Lockout**: ver regra 15/16 (§7). Bloqueio por conta no servidor; API responde `423 Locked`.
- **Troca de senha própria**: `GET/POST /profile/password` — exige senha atual, valida mínimo 8 caracteres, invalida sessões existentes.
- **Reset administrativo**: `POST /admin/users/{id}/reset-password` (permissão `usuarios.editar`) — valida política, zera lockout, invalida sessões.
- **Recuperação de senha por e-mail**: **NÃO IMPLEMENTADO** (ver §7).
- **Primeiro acesso**: tela `/setup` (instalação nova) ou env `AUTH_ADMIN_USERNAME/AUTH_ADMIN_PASSWORD` (cria admin no start) ou CLI `create-user --admin`.
- **Credenciais**: nunca logadas/auditadas; verificação de código não encontrou gravação de senha/token em trilhas (as chamadas `write_audit` de autenticação não incluem senha).

---

## 9. Autorização

- **Mecanismo**: dependências FastAPI em `app/api/deps.py`:
  - `require_api_auth` → 401 sem sessão; protege todo o roteador de negócio em `/api/v1` (inclusive GET e exportações).
  - `require_web_auth` → redirect `303 /login?next=<caminho original>`; caminhos públicos: `/login`, `/logout`, `/setup`.
  - `require_permission("modulo.acao")` (fábrica, com `web=True` para páginas) → 403 sem permissão, **auditado** como `ACESSO_NEGADO` com módulo, recurso (a permissão) e path.
- **Deny by default**: sem permissão explícita = negado; usuário novo sem perfil não executa nada.
- **Cache por requisição**: `stash_access` pré-computa permissões/perfis em `request.state`, reutilizado pelo menu dinâmico (context processor `_inject_current_user` expõe `can('modulo.acao')` aos templates).
- **Backend é a autoridade**: menu/botões via `can()` são apenas apresentação.
- **Proteção aplicada**: todas as rotas web de negócio usam `require_permission` (74 ocorrências verificadas em `app/web/*.py`); endpoints API de negócio protegidos por `require_api_auth` + permissões conforme §20.
- **Endpoints de administração**: `/admin/users*` → `usuarios.*`; `/admin/roles*` → `perfis.*`; `/admin/audit` → `auditoria.visualizar`; `/admin/ad*` → **superusuário OU (`usuarios.editar` + `perfis.editar`)** — verificado em `admin_routes.py:633-770`.

---

## 10. Gestão Patrimonial

- **Cadastro**: `GET/POST /assets/new` (web, `patrimonio.criar`) e `POST /api/v1/assets`. Campos obrigatórios no create: `tag`, `name`, `category` (schema `AssetCreate`). Regras: tag única normalizada (uppercase), serial único quando informado. Status inicial: `IN_USE` se criado com `initial_custodian_id`, senão `AVAILABLE`. Bem criado com local/custodiante iniciais pode registrar movimentação `ENTRADA_AQUISICAO` (parâmetros `initial_location_id`, `initial_custodian_id`, `initial_operator` no schema).
- **Pesquisa/listagem**: `GET /assets` com filtros: busca textual (tag, nome, marca, modelo, serial, nota fiscal, nome do custodiante, todos os campos do local), status, categoria, local, custodiante, marca, modelo, departamento, situação de manutenção (`open`/`closed`), período de compra — `AssetService.get_all`. Paginação (`skip`/`limit`) e total.
- **Visualização**: `GET /assets/{id}` — ficha completa + timeline + depreciação + QR Code; `GET /assets/tag/{tag}` e `GET /api/v1/assets/tag/{tag}` por tombamento; timeline combinada (movimentações + auditoria) em `MovementService.get_timeline_for_asset` (com dedup de `MOVIMENTACAO`/`MANUTENCAO`/`CRIACAO` para não duplicar eventos).
- **Edição**: `GET/POST /assets/{id}/edit` existe? — **NÃO IDENTIFICADA rota web de edição com esse caminho**; a edição está em `PUT /api/v1/assets/{id}` (`patrimonio.editar`) e a interface consome via formulário — verificado apenas o endpoint da API e o schema `AssetUpdate`. (**Parcial**: edição via API confirmada; caminho web exato não mapeado nesta análise.)
- **Depreciação**: `GET /assets/{id}/depreciation` (API) — linear 20%/ano (ver regra 9).
- **Etiquetas**: `GET /assets/labels` — seleção de bens e folha de etiquetas com QR Code (`assets/labels.html`, QRCode.js, URL absoluta `/assets/{id}`).
- **Importação CSV**: `GET/POST /assets/import` + `POST /assets/import/confirm` (pré-visualização → confirmação); API `POST /api/v1/assets/import/csv`; audita `IMPORTACAO`.
- **Estado do bem**: controlado pelos enums `AssetStatus` (5 valores) e `AssetCondition` (6 valores); alterações de estado/custódia/localização ocorrem pelo motor de movimentações (§14).

---

## 11. Colaboradores

- **Modelo**: `Custodian` (§6.2) — matrícula (`registration_code`, única, obrigatória), nome, e-mail (único, obrigatório), CPF opcional, cargo obrigatório, **setor obrigatório** (`department`, texto livre), `is_active`.
- **Rotas**: `GET /custodians` (lista), `GET/POST /custodians/new`, `GET/POST /custodians/{id}/edit`, `GET /custodians/{id}` (detalhe com bens sob custódia); API `GET/POST /custodians`, `GET/PUT /custodians/{id}`, `GET /custodians/{id}/assets`; permissões `colaboradores.*`.
- **Importação CSV**: `GET/POST /custodians/import` + confirm; API `POST /api/v1/custodians/import/csv`.
- **Exclusão**: **NÃO IDENTIFICADA** rota/endpoint de exclusão de colaborador (apenas edição e `is_active`).
- **Vínculo com patrimônio**: `Asset.custodian_id`; contagem de bens sob custódia (`count_assigned_assets`, `active_assets_count`).
- **Vínculo com AD**: no provisionamento AD, o usuário do diretório é vinculado ao **colaborador existente** por e-mail/matrícula (`find_linked_custodian`), sem duplicar cadastro e sem sobrescrever dados patrimoniais (matrícula, CPF, cargo, setor).

---

## 12. Setores e Localizações

- **Localização** = `Location`: nome único, filial (obrigatória), prédio/andar/sala (opcionais), **departamento obrigatório** (texto), `manager_name` (responsável pelo setor, opcional), descrição.
- **Setor** não é entidade: é campo `department` em `Location` e `Custodian`, e filtro em `Inventario`.
- **Rotas**: `GET /locations`, `GET/POST /locations/new`, importação `GET/POST /locations/import` + confirm (CSV com obrigatórios nome/filial/departamento; opcionais prédio, andar, sala, gestor, descrição); API `GET/POST /locations`, `GET/PUT /locations/{id}`; permissões `locais.*`.
- **Alteração de localização de um bem** não é feita editando `Location`: ocorre por **movimentação** (`TRANSFERENCIA_LOCAL`) que atualiza `Asset.location_id` e grava o histórico (§14). A edição do cadastro do local (`PUT /api/v1/locations/{id}`) altera os dados do local em si; **efeito sobre bens já vinculados via snapshot textual**: movimentações e itens de inventário guardam **nomes snapshot**, que não se atualizam retroativamente (comportamento verificado: snapshots são gravados no momento do evento).

---

## 13. Alocação e Responsabilidade

Fluxo real da **Alocação/Cautela** (`ALOCACAO_CAUTELA`):

```text
Usuário com movimentacao.criar
  ↓ Tela /movements/new (formulário de movimentação)
  ↓ POST /movements/new (web) ou POST /api/v1/movements (API)
  ↓ Schema MovementCreate valida (reason ≥ 3, tipo, destino)
  ↓ MovementService.create_movement:
      - bem existe? bem não está BAIXADO?
      - tipo ALLOCATION exige destination_custodian_id (ValueError se ausente)
      - asset.custodian_id = destino; local atualizado se informado
      - status → EM_USO
      - term_code TR-AAAA-NNNN gerado automaticamente
      - Movement gravada com snapshots origem → destino
  ↓ Auditoria: ACTION_MOVEMENT (write_change_audit na API; rotas web registram)
  ↓ Resposta: redirect/JSON + termo disponível em /movements/{id}/term
```

- **Quem pode executar**: portadores de `movimentacao.criar` (Gestor de TI, Patrimônio, Almoxarifado, Administrador/superusuário).
- **Situações bloqueadas**: bem `BAIXADO`; alocação sem custodiante; custodiante/local inexistentes (FK/validação).
- **Entidades alteradas**: `assets` (custodian_id, location_id opcional, status, condition opcional, updated_at) + nova linha em `movements` (imutável).
- **Termo**: gerado automaticamente para alocação; `term_signed` inicia `False` e **não existe código que o altere** (ver §17).
- **Histórico**: aparece na timeline do bem (`get_timeline_for_asset`) e na listagem `/movements`.

---

## 14. Movimentações

**Motor**: `MovementService.create_movement` (átomo: atualiza o bem + grava registro imutável + commit). Tipos implementados (Enum `MovementType`, 8 valores) e seus efeitos (regra 7, §7):

| Tipo | Finalidade | Origem→Destino | Efeito no bem | Termo |
|---|---|---|---|---|
| `ENTRADA_AQUISICAO` | Cadastro/incorporação | — → local inicial | criação/status inicial | não |
| `ALOCACAO_CAUTELA` | Entrega a colaborador | estoque/local → custodiante | custodiante + `EM_USO` | **sim (auto)** |
| `TRANSFERENCIA_LOCAL` | Mudança de local/departamento | local → local | location_id; custodiante opcional | não |
| `ENVIO_MANUTENCAO` | Saída para reparo | → assistência | `EM_MANUTENCAO` | não |
| `RETORNO_MANUTENCAO` | Volta do conserto | assistência → estoque/custódia | `AVAILABLE` (ou `IN_USE`) | não |
| `DEVOLUCAO_ESTOQUE` | Recolhimento (demissão/troca) | custodiante → estoque | custodiante limpo + `AVAILABLE` | **sim (auto)** |
| `BAIXA_DESCARTE` | Descarte definitivo | — | `WRITTEN_OFF`, custodiante limpo, condição default `INSERVIVEL` | não |
| `ATUALIZACAO_ESTADO` | Vistoria de conservação | mesma localização | condição; status mantido | não |

- **Gravação**: cada movimentação registra data/hora (`timestamp`), `movement_uuid`, snapshots (nome/filial/setor da origem e do destino), status/condição anteriores e novos, `reason` obrigatória, `operator_name`, `term_code` quando houver, `notes`.
- **Consulta**: `GET /movements` com filtros (asset, tipo, período); API `GET /api/v1/movements`, `GET /api/v1/movements/{id}`, `GET /api/v1/movements/{id}/term`; exportação CSV `GET /api/v1/reports/movements/csv` (`relatorios.exportar`).
- **Imutabilidade**: o modelo é conceitualmente apensável ("Gravação imutável", docstring); **não existem rotas de edição/exclusão de movimentações** (ver §7 — permissões de editar/cancelar são reservadas no catálogo).
- **Auditoria**: eventos `MOVIMENTACAO` registrados nas operações (API e web).

---

## 15. Inventário

Módulo detalhado — fontes: `app/services/inventario_service.py` (384 linhas), rotas em `app/web/routes.py:1750-2164`, modelo §6.4, testes `tests/test_inventario.py` (21 testes).

### Fluxo completo implementado

1. **Criação** (`GET/POST /inventarios/new`, permissão `inventario.criar`): nome obrigatório; escopo opcional por `location_id` e/ou `department` (texto) — vazio = todo o acervo. Gera código `INV-AAAA-NNNN`, status `PLANEJADO`, **snapshot textual dos filtros** (`scope_filters`) e **gera imediatamente a lista de bens esperados** (`generate_items`): todos os bens não baixados no escopo, copiando para cada item o local e o custodiante **do momento** (`expected_*`). Idempotente (não duplica itens). Audita `INVENTARIO`.
2. **Busca/conferência em campo** (`inventario.conferir`):
   - `POST /inventarios/{id}/buscar`: recebe o **tombamento** digitado ou escaneado do QR (o QR aponta para a ficha do bem); localiza o bem por `tag` (case-insensitive). Se o bem está na lista → abre o modal/página de conferência; se existe no cadastro mas não está na lista → orienta registrar como **não previsto**; se não existe → erro.
   - `GET /inventarios/{id}/conferir/{asset_id}`: página de conferência do bem (ficha + formulário de resultado, com lista de locais para divergência).
   - `POST /inventarios/{id}/conferir/{item_id}`: registra o resultado via `record_check`.
   - `POST /inventarios/{id}/nao-previsto`: registra bem não previsto via `register_unlisted_asset`.
   - Alternativamente, a conferência pode ser disparada pela **ficha do bem** (fluxo QR: ficha → conferir).
3. **Resultados possíveis** (Enum `InventarioItemStatus`): `PENDENTE` → `ENCONTRADO` · `LOCAL_DIFERENTE` (exige `found_location_id` **diverso** do esperado) · `NAO_ENCONTRADO` · `SEM_IDENTIFICACAO`. Cada conferência grava: resultado, local encontrado (snapshot textual), observação, conferente (`checked_by_id` + snapshot do username) e `checked_at`.
4. **Divergências**: **o cadastro nunca é alterado** — `Asset.location_id/custodian_id/status` permanecem intactos; a divergência fica registrada no item para tratamento posterior pelos fluxos próprios (movimentação/cadastro). Bem presente sem tombo legível → `SEM_IDENTIFICACAO` (ou registro como não previsto).
5. **Responsável (custodiante)**: a expectativa é snapshot textual (`expected_custodian_name`); o sistema **não registra** "custodiante diferente" como estado do item — divergência de custódia é tratada observando/registrando e posteriormente via movimentação. (**Comportamento real**; não existe campo `found_custodian` no modelo.)
6. **Setor**: entra como filtro de escopo na criação (`department`) e na busca do acervo; dentro do inventário, o local encontrado é o dado de comparação.
7. **Alterações permitidas durante o inventário**: apenas os campos da conferência (status, found_location, observação, checked_*). **Dados do bem, do inventário (nome/escopo) e do cadastro não são modificáveis** pelo fluxo de inventário. Após encerramento, nenhuma conferência nova é aceita.
8. **Início formal**: automático na primeira conferência efetiva, ou manual via `POST /inventarios/{id}/iniciar` (audita "iniciado formalmente").
9. **Consolidação**: `summary` por status (esperados) + contagem de não previstos; exibida na página do inventário.
10. **Encerramento** (`POST /inventarios/{id}/encerrar`, permissão `inventario.encerrar`): exige **zero itens esperados pendentes**; grava `closed_at`, `closed_by_name`, `closure_notes`; trava itens; audita.
11. **Ata/exportações** (página e API): `GET /api/v1/reports/inventarios/{id}/csv|excel|pdf` — exige `inventario.visualizar` **+** `relatorios.exportar` (verificado em `reports_api.py`); PDF via ReportLab contendo a ata comprobatória (status, não previstos, conferentes).
12. **Consulta posterior**: `GET /inventarios` (lista com busca por nome/código e filtro de status) e `GET /inventarios/{id}` (detalhe, lista de itens, painel de conferência).
13. **Templates**: `inventarios/index.html`, `inventarios/new.html`, `inventarios/detail.html`, `inventarios/conferir.html` (nomes conforme diretório `app/web/templates/inventarios/`).
14. **Testes**: `tests/test_inventario.py` — fluxo completo via web, RBAC das 4 permissões, encerramento com pendentes bloqueado, não previstos, exportações CSV/Excel/PDF.

---

## 16. QR Code

- **Geração (client-side, verificado)**: biblioteca **QRCode.js** via CDN (`base.html`); usada em três lugares:
  - Ficha do bem (`assets/detail.html`): QR com a URL `/assets/{id}`.
  - Etiquetas em lote (`assets/labels.html`): QR com URL **absoluta** `origin + /assets/{id}`; folha para impressão.
  - Termo de responsabilidade (`movements/term.html`): QR de validação do termo.
- **Leitura**: **NÃO IDENTIFICADO NO CÓDIGO** leitor/decoder de QR no backend; a leitura é feita por scanner externo configurado como teclado (o campo do inventário recebe o tombamento) ou pela câmera do dispositivo — a rota `/inventarios/{id}/buscar` apenas recebe o texto (`tag`) do formulário.
- **Consulta por QR**: o QR aponta para a ficha web (`/assets/{id}`), que exige login + `patrimonio.visualizar` (a ficha não é pública).
- **Validação de acesso**: as páginas de destino do QR passam pelas dependências de auth/RBAC normais.

---

## 17. Termos (Responsabilidade e Cautela)

- **Criação**: automática na movimentação (`term_code` gerado quando `generate_term=True` ou tipo alocação/devolução — §7 regra 8). **Não existe criação manual de termo isolado.**
- **Associação**: termo pertence a uma `Movement` (que referencia o bem e os snapshots de origem/destino, incluindo o colaborador) — não há tabela própria de termos.
- **Numeração**: `TR-<ano>-<sequência 5 dígitos>`, sequência global de alocações+devoluções, indexado (`term_code`), único por movimentação geradora (não há constraint unique no campo).
- **Visualização/impressão**: `GET /movements/{id}/term` (web, `movimentacao.visualizar`) e `GET /api/v1/movements/{id}/term` — template `movements/term.html` com dados da empresa (`COMPANY_NAME/CNPJ/ADDRESS` em `app/config.py`), especificações do bem, custodiante, QR de validação; pronto para impressão (estilos de impressão no template).
- **Status de assinatura**: `Movement.term_signed` default `False`; **nenhum código encontrado altera `term_signed` para True** — a confirmação/assinatura eletrônica é **PARCIAL/NÃO IMPLEMENTADA** (o campo existe e é exibido; o fluxo de "assinar" não).
- **Validações**: termo disponível apenas para movimentação existente; sem permissão própria (usa `movimentacao.visualizar`).

---

## 18. Baixa

- **Mecanismo**: movimentação do tipo `BAIXA_DESCARTE` via `/movements/new` ou `POST /api/v1/movements` (permissão `movimentacao.criar`).
- **Condições implementadas**: bem não pode já estar `WRITTEN_OFF` (§7 regra 4); condição final default `INSERVIVEL` se não informada; custodiante é limpo; status final `BAIXADO`.
- **Campos**: `reason` obrigatória; `new_condition` opcional; `destination_location_id` opcional.
- **Após a baixa**: o bem permanece cadastrado com status `BAIXADO`; **não pode mais ser movimentado** (exceto re-aquisição, tipo aquisição); **excluído da geração de listas de inventário** (`_scope_query` filtra `status != WRITTEN_OFF`).
- **Histórico preservado**: a movimentação de baixa fica na timeline; nenhuma exclusão de dados.
- **Auditoria**: evento `MOVIMENTACAO` na baixa.
- **Documentos associados**: **NÃO IDENTIFICADO** termo/laudo específico de baixa (sem geração de documento próprio para baixa).

---

## 19. Auditoria

Fonte: `app/services/audit_service.py` (273 linhas), modelo `AuditLog` (§6.3), página `/admin/audit`.

- **Eventos registrados** (constantes verificadas): gerais — `LOGIN`, `LOGIN_FALHA`, `LOGIN_BLOQUEADO`, `LOGOUT`, `CRIACAO`, `ALTERACAO`, `EXCLUSAO`, `BLOQUEIO`, `DESBLOQUEIO`, `RESET_SENHA`, `TROCA_SENHA`, `ALTERACAO_PERFIL`, `CRIACAO_PERFIL`, `ALTERACAO_PERFIL_PERMISSOES`, `EXCLUSAO_PERFIL`, `MOVIMENTACAO`, `MANUTENCAO`, `IMPORTACAO`, `INVENTARIO`, `ACESSO_NEGADO`; AD (13) — `LOGIN_AD`, `LOGIN_AD_AUTORIZADO`, `LOGIN_AD_FALHA`, `CONTA_AD_DESABILITADA`, `USUARIO_AD_PROVISIONADO`, `USUARIO_AD_VINCULADO_COLABORADOR`, `GRUPOS_AD_IDENTIFICADOS`, `GRUPO_AD_SEM_MAPEAMENTO`, `PERFIL_SINCRONIZADO_AD`, `CONFLITO_GRUPOS_AD`, `FALHA_COMUNICACAO_AD`, `ALTERACAO_CONFIG_AD`, `TESTE_CONEXAO_AD`.
- **Informações gravadas por evento**: timestamp (UTC), usuário (FK SET NULL) **+ snapshot do username**, ação, módulo, recurso (tipo), id do recurso, referência legível (`resource_ref`: tag, matrícula, username, código), IP do cliente, resultado (`SUCCESS/FAILURE/DENIED/LOCKED`), descrição, **dados anteriores e posteriores em JSON** (`write_change_audit` calcula diff com `changed_fields`).
- **Origem**: IP capturado por `_client_ip` (deps); não há campo separado de "origem" (web/API) além do módulo/recurso — **NÃO IDENTIFICADO** campo de canal (web vs API).
- **Somente-leitura**: não existe rota de escrita/exclusão; consulta `/admin/audit` exige `auditoria.visualizar`, com filtros (busca, ação, módulo, resultado) e paginação; rótulos amigáveis via `action_label`.
- **Acessos negados (403)**: auditados automaticamente pela dependência `require_permission`.

---

## 20. Relatórios e Consultas

**Dashboard** (`GET /`, `relatorios.visualizar`): KPIs (`DashboardService.get_stats`), gráficos de pizza/barras (Chart.js), últimas movimentações e últimos bens.

**Relatórios web** (`/reports/inventory`, `/reports/movements`, `/reports/custodians`; `relatorios.visualizar`): telas com filtros (mesmos parâmetros de `AssetService.get_all` para inventário de bens) e links de exportação.

**Exportações API** (`/api/v1/reports/*`; `relatorios.exportar`):
- `GET /reports/inventory/csv|excel|pdf` — bens filtrados (CSV UTF-8 BOM, XLSX OpenPyXL, PDF ReportLab).
- `GET /reports/movements/csv` e `GET /reports/custodians/csv` — movimentações e colaboradores (CSV).
- `GET /reports/inventarios/{id}/csv|excel|pdf` — ata comprobatória do inventário (exige `inventario.visualizar` **e** `relatorios.exportar`).
- `GET /reports/dashboard-stats` — KPIs em JSON (`relatorios.visualizar`).

**Consultas**: listagem/ficha/timeline/depreciação do bem; bens por custodiante (`/custodians/{id}/assets`); histórico de movimentações com filtros; auditoria filtrável; central de ajuda com pesquisa em texto completo.

---

## 21. Interface

- **Layout**: `base.html` — sidebar de navegação dinâmica conforme permissões (`can()`), cabeçalho com usuário logado e botão Sair, tema claro/escuro (`static/js/main.js`), Bootstrap 5.3.3 + Bootstrap Icons + Chart.js + QRCode.js via CDN, fonte Plus Jakarta Sans.
- **Páginas principais (rota → template)**: login (`login.html`), primeiro acesso (`setup.html`), dashboard (`dashboard.html`), bens (`assets/index|new|detail|edit?|labels|import`), movimentações (`movements/index|new|term`), colaboradores (`custodians/*` com detalhe e importação), locais (`locations/*` com importação), manutenções (`maintenances/*`), relatórios (`reports/*`), inventários (`inventarios/*` incl. `conferir`), administração (`admin/users*`, `admin/roles*`, `admin/audit`, `admin/ad`), perfil (`profile/password`), ajuda (`ajuda/*`), erros amigáveis (`403.html`, `404.html`).
  - Nota: template de **edição de bem** — diretório `assets/` contém index, new, detail, labels, import; página dedicada de edição **NÃO FOI CONFIRMADA** na listagem do diretório (edição disponível via API).
- **Formulários**: validação server-side (Pydantic/ValueError) com mensagens em português; confirmações em ações destrutivas (ex.: exclusão de perfil); tooltips contextuais e botões "Como faço isso?" (central de ajuda).
- **Mensagens**: feedback via parâmetros `?error=`/`?search=` em redirects (padrão visto nas rotas de inventário) e alertas Bootstrap (`main.js`).
- **Impressão**: termo de responsabilidade e folha de etiquetas com estilos de impressão; ata de inventário exportável em PDF.
- **Responsividade**: sidebar mobile e layout Bootstrap (verificado em `main.js`/`style.css`).
- **Nenhuma alteração visual** foi feita nesta análise (documentação apenas).

---

## 22. Integrações

- **Active Directory / Samba AD (LDAP/LDAPS)** — implementada e testada contra AD real (README/docs + código):
  - Protocolo: `ad_ldap.py` (`authenticate_ad`, `test_connection`, `get_user_groups`, `UAC_DISABLED_BIT`, normalização de `objectGUID`).
  - Integração: `ad_service.py` — configuração singleton (`ad_settings`) com fallback para env `AD_*`; **bind direto do usuário** (senha digitada valida no diretório) com leitura de atributos/grupos na mesma conexão autenticada; conta de serviço (`AD_BIND_USER`) para consultas, senha **somente em variável de ambiente** (`AD_BIND_PASSWORD`), nunca no banco.
  - Regras: conta `auth_provider='local'` sempre autentica local; `auth_provider='ad'` sempre no AD; provisionamento só após grupo mapeado; vínculo com colaborador existente por e-mail/matrícula; perfis `assigned_by='ad'` resincronizados a cada login, manuais (`'local'`) preservados; conta desabilitada (`userAccountControl`) → acesso negado; sem mapeamento → `ADNoProfileError`, **nenhum usuário criado**, tentativa auditada.
  - Erros tipados: `ADNotConfiguredError`, `ADAuthenticationError` (401), `ADUnavailableError` (503), `ADNoProfileError` (401 com mensagem específica).
  - Tela: `GET /admin/ad` + `POST /admin/ad/settings|test|mappings`, `POST /admin/ad/mappings/{id}/delete`.
- **Nenhuma outra integração externa** (e-mail, webhooks, APIs de terceiros) foi identificada no código.

---

## 23. Testes

- **Framework**: pytest (+ TestClient do FastAPI); `tests/conftest.py` configura banco de teste **SQLite em memória** (StaticPool) por padrão, ou `DATABASE_URL_TEST` (MariaDB) se definido; PBKDF2 reduzido para 1000 iterações nos testes.
- **Quantidade**: **154 funções de teste** (contagem `def test_`); README reporta 153 passando e **1 falhando**.
- **Distribuição por arquivo**: `test_ad.py` (32 — integração AD com LDAP mockado, inclui regressões de `Connection.search()` bool e `raw_values` do objectGUID), `test_rbac.py` (30 — autorização por perfil em APIs e páginas, deny by default, menu dinâmico, bloqueio/desbloqueio, lockout, auditoria, último admin, escalação de privilégios), `test_inventario.py` (21 — fluxo completo via web, RBAC, exportações), `test_auth.py` (17), `test_custodian_import.py` (13), `test_import_asset_location.py` (12), `test_help.py` (9), `test_api.py` (7), `test_movements.py` (5), `test_navbar.py` (4), `test_setup_first_access.py` (3), `test_assets.py` (1).
- **Natureza**: maioria são testes de integração de rotas (TestClient) cobrindo autenticação, autorização, fluxos patrimoniais e inventário; não há separação formal unit/integration.
- **Testes NÃO executados nesta análise** (leitura apenas; nenhum comando de teste foi rodado).

---

## 24. Fluxos Principais

**Login**
```text
Usuário → /login → POST (username, password)
  → resolve_authentication (local ou AD) → lockout/falha? → mensagem + auditoria
  → create_session (hash no banco) → cookie HttpOnly → redirect next (internos apenas)
```

**Movimentação (ex.: alocação)**
```text
Usuário (movimentacao.criar) → /movements/new → POST
  → MovementCreate (Pydantic) → MovementService.create_movement
  → validações (bem existe, não baixado, custodiante obrigatório)
  → atualiza Asset + grava Movement (snapshots) + commit
  → auditoria MOVIMENTACAO → termo (se alocação/devolução) → redirect
```

**Inventário (ciclo completo)**
```text
Criar (inventario.criar) → snapshot dos esperados
  → Conferir (inventario.conferir): buscar por tombamento/QR → página de conferência
      → resultado ENCONTRADO/LOCAL_DIFERENTE/NAO_ENCONTRADO/SEM_IDENTIFICACAO
      → item atualizado (cadastro intocado) → auditoria INVENTARIO
  → Não previsto (se encontrado em campo) → registro como ocorrência
  → Encerrar (inventario.encerrar) → exige 0 pendentes → trava itens
  → Ata CSV/XLSX/PDF (inventario.visualizar + relatorios.exportar)
```

**Manutenção**
```text
Abrir OS (manutencao.criar) → MaintenanceService.create → OS EM_ANDAMENTO
  → movimento ENVIO_MANUTENCAO automático → bem EM_MANUTENCAO
Finalizar (manutencao.finalizar) → complete_maintenance → CONCLUIDA
  → movimento RETORNO_MANUTENCAO automático → bem AVAILABLE
```

**Importação CSV (bens/colaboradores/locais)**
```text
Upload → parse + preview (tabela de validação/duplicatas) → confirm
  → execute_* → criação em lote → auditoria IMPORTACAO
```

---

## 25. Problemas e Pontos de Atenção

> **Nada foi corrigido.** Itens registrados apenas para conhecimento; não são requisitos.

| # | Severidade | Problema | Arquivo/local |
|---|---|---|---|
| 1 | Alto | **Teste falhando**: `test_lockout_after_failed_attempts` espera bloqueio após **5** tentativas, mas `AUTH_MAX_FAILED_ATTEMPTS` default passou a **10** (suite: 153/154) | `tests/test_rbac.py:327-335`; `app/config.py` |
| 2 | Médio | `term_signed` nunca é setado `True` — fluxo de assinatura de termo inexistente (campo apenas exibido) | `app/models/movement.py`; grep `term_signed` (apenas default False) |
| 3 | Médio | Regra de numeração de termo usa `count()+1` sobre movimentações de alocação/devolução — sob concorrência pode gerar `term_code` duplicado (sem constraint unique) | `app/services/movement_service.py:~135` |
| 4 | Médio | `InventarioService.next_code` ordena por string (`code.desc()`) — lacunas/ordenação lexicográfica podem colidir com códigos existentes sob concorrência (sem lock) | `app/services/inventario_service.py:~30` |
| 5 | Médio | Rotas web fazem consultas ORM diretas (ex.: busca de bem no inventário, trechos de `admin_routes.py`), contornando parcialmente a camada de services | `app/web/routes.py:~1902`; `app/web/admin_routes.py` |
| 6 | Baixo | Permissões `movimentacao.editar`, `movimentacao.cancelar`, `patrimonio.excluir` existem no catálogo/perfis, mas não há rotas que as consumam (superfície de permissão maior que a funcionalidade) | `app/services/permission_service.py` |
| 7 | Baixo | Sem rota web de edição de local e de exclusão de colaborador/bem (somente API/ausência), enquanto a UI sugere gestão completa | `app/web/routes.py` |
| 8 | Baixo | `get_auth_provider()` documentado como "sem chamadores" (INVENTARIO_TECNICO.md) — código potencialmente morto | `app/services/auth_provider.py` |
| 9 | Baixo | Mistura de `datetime.now()` (local) e `datetime.utcnow()` no mesmo service (movement usa `now()`, inventário usa `utcnow()`) — risco de inconsistência de fuso nos registros | `app/services/movement_service.py` vs `inventario_service.py` |
| 10 | Observação | `docs/Melhorias_SisPatrimonio_Pro.md` lista desejos (busca global, filtros avançados etc.) — são **sugestões**, não funcionalidades existentes | `docs/` |
| 11 | Observação | `.env` presente na raiz do projeto (não lido); recomendação de não versionar credenciais | raiz |

---

## 26. Funcionalidades Existentes

| Funcionalidade | Existe | Estado | Principais componentes |
|---|---|---|---|
| Autenticação local (login/logout/sessão/lockout) | Sim | Completa | `auth_service`, `session_service`, `deps.py`, `/login` |
| Primeiro acesso (/setup) e admin via env/CLI | Sim | Completa | `routes.py /setup`, `SetupClaim`, `cli.py` |
| RBAC (perfis/permissões, deny by default) | Sim | Completa | `permission_service`, `require_permission` |
| Integração AD/LDAP com mapeamento grupo→perfil | Sim | Completa | `ad_ldap`, `ad_service`, `/admin/ad` |
| Auditoria somente-leitura | Sim | Completa | `audit_service`, `AuditLog`, `/admin/audit` |
| CRUD de bens (criar/editar via API/visualizar) | Sim | Completa* | `asset_service`, `assets_api` (*exclusão web não identificada) |
| Busca/filtros avançados de bens | Sim | Completa | `AssetService.get_all` |
| Depreciação linear | Sim | Completa | `calculate_depreciation` |
| Etiquetas QR em lote | Sim | Completa | `/assets/labels`, QRCode.js |
| Movimentações (8 tipos) com trilha imutável | Sim | Completa | `movement_service` |
| Termo de responsabilidade/cautela | Sim | **Parcial** (assinatura não implementada) | `term_code`, `term.html` |
| Manutenções (OS + integração com fluxo) | Sim | Completa | `maintenance_service` |
| Colaboradores (CRUD + importação CSV) | Sim | Completa* | `custodian_service` (*sem exclusão) |
| Locais (criar + importação CSV; editar via API) | Sim | Completa* | `location_service` (*edição web não identificada) |
| Inventário patrimonial (ciclo completo + ata) | Sim | Completa | `inventario_service`, `/inventarios*` |
| Dashboard com KPIs/gráficos | Sim | Completa | `dashboard_service` |
| Relatórios/exportações CSV/XLSX/PDF | Sim | Completa | `report_service`, `reports_api` |
| Central de ajuda integrada | Sim | Completa | `help_service`, `/ajuda` |
| CLI administrativa | Sim | Completa | `app/cli.py` |
| Importação CSV de bens | Sim | Completa | `import_service` |
| Cancelamento/edição de movimentação | Não | Catálogo reserva a permissão | — |
| Recuperação de senha por e-mail | Não | Não implementado | — |
| Leitor de QR no backend | Não | Não implementado (scan externo) | — |
| Escopo por unidade/setor no usuário | Não | Avaliado e adiado (docs) | — |

---

## 27. Restrições para Evolução

Restrições explícitas para futuras alterações (alinhadas à Constitution `.specify/memory/constitution.md`):

1. O sistema **já existe e está em uso** — não deve ser reescrito.
2. Novas funcionalidades devem **aproveitar a arquitetura existente** (Web/API → Services → Models) e o padrão de rotas/permissions/schemas.
3. Alterações devem ser **incrementais**; **não** devem ocorrer refatorações não relacionadas ao escopo da tarefa.
4. Funcionalidades e comportamentos existentes devem ser **preservados** (nenhuma mudança de comportamento correto fora da especificação aprovada).
5. **Banco de dados**: apenas evolução aditiva controlada (o mecanismo atual é `init_db` + `_ensure_schema_migrations`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, idempotente); MariaDB é o banco de produção; SQLite é exclusivo dos testes.
6. **Autenticação, autorização, integrações** não devem ser alteradas sem necessidade explícita e especificação.
7. Mudanças devem permanecer **dentro do escopo da feature**.
8. Mudanças devem possuir **testes apropriados**; a suíte existente (154 testes) é a base de regressão e não deve ser removida/enfraquecida.
9. **Dados históricos e registros de auditoria devem ser preservados** (trilha imutável; movimentações apensáveis; snapshots não retroativos).

---

## 28. Conclusão

O SisPatrimônio Pro é um sistema de gestão patrimonial maduro, com arquitetura em camadas
consistentemente aplicada (FastAPI → Services → SQLAlchemy → MariaDB), RBAC deny-by-default
com 29 permissões e 7 perfis padrão, autenticação híbrida local+AD com sessão server-side,
trilha de auditoria imutável cobrindo autenticação, operações, movimentações e acessos
negados, motor de movimentações com 8 tipos e snapshots de origem/destino, inventário
comprobatório com snapshot de expectativa que jamais altera o cadastro, termos sequenciais
parciais (sem assinatura), exportações CSV/XLSX/PDF e suíte de 154 testes com 1 falha
conhecida de defasagem entre teste e configuração. As lacunas relevantes estão
consolidadas em §25 e §26, e as restrições de evolução em §27.

---

*Fim da especificação. Documento gerado exclusivamente por leitura do código; nenhum
arquivo do sistema foi modificado durante a análise (única criação: este arquivo).*
