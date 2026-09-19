# Data Model — Revisão do README (feature 023)

> **Nenhuma entidade, tabela, coluna ou registro é criado ou alterado.** A feature é documental. Este documento registra o "modelo de fatos" que o README pode afirmar — cada fato com sua fonte verificável no código.

## 1. Inventário de fatos documentáveis (fonte única para o README)

### 1.1 Identidade e versão

| Fato | Valor confirmado | Fonte |
|---|---|---|
| Nome da aplicação | `SisPatrimônio Pro` | `app/config.py` L90 |
| Descrição | "Sistema Integrado de Gestão Patrimonial e Fluxo de Movimentação de Equipamentos" | `app/config.py` L91 |
| Versão | `1.2.0` | `app/config.py` L92 |
| Status | Em desenvolvimento ativo | Histórico do repositório (specs 001–022) |

### 1.2 Stack (requirements.txt real, versões mínimas)

| Pacote | Versão mínima |
|---|---|
| fastapi | >= 0.110.0 |
| uvicorn[standard] | >= 0.28.0 |
| sqlalchemy | >= 2.0.0 |
| pydantic | >= 2.6.0 |
| jinja2 | >= 3.1.3 |
| python-multipart | >= 0.0.9 |
| pytest | >= 8.0.0 |
| requests | >= 2.31.0 |
| ldap3 | >= 2.9.1 |
| pymysql | >= 1.1.0 |
| python-dotenv | >= 1.0.0 |
| openpyxl | >= 3.1.0 |
| reportlab | >= 4.0.0 |

Frontend: Bootstrap 5 + Bootstrap Icons, Chart.js, QRCode.js (templates). Banco: MariaDB/MySQL via `mariadb+pymysql://`. Testes: SQLite em memória ou `DATABASE_URL_TEST` (`tests/conftest.py` L26–28).

### 1.3 Endpoints públicos/principais verificados

| Rota | Tipo | Observação | Fonte |
|---|---|---|---|
| `/` | GET | Dashboard (autenticado) | `routes.py` L273 |
| `/login`, `/logout` | GET/POST | Autenticação local/AD | `routes.py` L147/L159/L248 |
| `/setup` | GET/POST | Primeiro administrador — enquanto não houver usuário (singleton `setup_claims.id=1`) | `routes.py` L1644/L1658, L1625 |
| `/docs` | GET | Swagger UI | `main.py` |
| `/health` | GET | Público (healthcheck) | `main.py` L144 |
| `/ajuda`, `/ajuda/{id}` | GET | Central de ajuda | `help_routes.py` L31/L52 |
| `/assets/labels` | GET | Etiquetas QR A4 | `routes.py` L373 |
| `/api/v1/*` | — | API protegida (deps de auth/RBAC) | `api/v1_router.py` |

### 1.4 CLI (`python -m app.cli`) — comandos reais

| Comando | Parâmetros | Fonte |
|---|---|---|
| `stats` | — | `cli.py` L206 |
| `list` | `--search/-s`, `--status` | `cli.py` L209–212 |
| `show` | `tag` | `cli.py` L214 |
| `move` | `tag`, `--type` (obrigatório), `--reason` (obrigatório), `--custodian-id`, `--location-id`, `--operator` | `cli.py` L218–225 |
| `create-user` | `--username` (obrig.), `--password` (opcional → interativo), `--name`, `--email`, `--admin`, `--role` (repetível) | `cli.py` L227–235 |
| `reset-password` | `--username` (senha oculta ×2, somente usuário local) | `cli.py` L236+ |

### 1.5 Configuração (`app/config.py`) — variáveis reais

`DATABASE_URL`, `MYSQLDUMP_PATH`, `BACKUP_IMPORT_TIMEOUT(900)`, `BACKUP_AUTO_*` (ENABLED/SCHEDULE/TIME/WEEKDAY), `BACKUP_RETENTION_*` (DAILY/WEEKLY/MONTHLY/KEEP_PRE_RESTORE), `APP_HOST`, `APP_PORT(8000)`, `AUTH_*` (PROVIDER, SESSION_TTL 28800, COOKIE_NAME session, COOKIE_SECURE false, PBKDF2_ITERATIONS 600000, MAX_FAILED_ATTEMPTS 10, LOCKOUT_SECONDS 900, ADMIN_USERNAME/PASSWORD/NAME), `AD_*` (SERVER, PORT 636, USE_SSL, BASE_DN, USER_DN, GROUP_BASE_DN, BIND_USER, BIND_PASSWORD).

Exemplo seguro (nunca valor real): `DATABASE_URL=mariadb+pymysql://usuario:SENHA@localhost:3306/banco`.

### 1.6 Perfis padrão e catálogo de permissões

Perfis (`permission_service.py` L88–180): `Administrador, Gestor de TI, Técnico de TI, Patrimônio, Almoxarifado, Auditor, Consulta` (system roles não excluíveis).

Permissões reais (36): `patrimonio.*` (4), `movimentacao.*` (4, `cancelar` reservada), `manutencao.*` (4), `colaboradores.*` (3), `locais.*` (3), `usuarios.*` (4), `perfis.*` (4), `relatorios.*` (2), `inventario.*` (4), `auditoria.visualizar`, **`backup.gerenciar`, `backup.restaurar`** — os dois últimos ausentes do catálogo do README (divergência D6).

### 1.7 Estrutura real da raiz do repositório

```text
app/  tests/  data/  docs/  specs/  TASKS/
README.md  requirements.txt  run.py  seed_demo.py  sistema_patrimonio.png  SPEC-KIT-SISTEMA-ATUAL.md
```

`docs/` real: `ARQUITETURA_E_MANUTENCAO.md`, `GUIA_DE_MANUTENCAO.md`, `INVENTARIO_TECNICO.md`, `AVISO_RESTORE_DEADLOCK.md`, `configuração mariaDB.md`, `doc_proviśorios/`.

## 2. Relações relevantes para o README (inalteradas — referência)

- AD: autentica → grupos → mapeamento (`ad_group_roles.priority`, menor = maior) → perfil → permissões do perfil; sem mapeamento = sem acesso/provisionamento.
- RBAC: usuário → perfis (`user_roles`) → permissões (`role_permissions`), deny-by-default, validação no backend (`require_permission`).
- Inventário: snapshot na criação; itens `nao_previsto` = observação complementar; encerramento trava; nunca altera cadastro (`inventario_service.py` L305).
- Backup: `backup_records` (registros/tipos MANUAL/AUTOMATICO/PRE_RESTAURACAO) e `backup_config` (singleton da 021/022).
- Data/hora: UTC persistido → America/Recife apresentado (`app/utils/time_utils.py`, feature 004 implementada).
