# Contract — CLI, Banco de Dados e Configuração — estado atual

## 1. CLI (`app/cli.py`)
Comandos existentes (nenhum novo; nenhum alterado):

| Comando | Função |
|---|---|
| `python -m app.cli stats` | Resumo/KPIs do acervo |
| `python -m app.cli list [--search]` | Lista/busca equipamentos |
| `python -m app.cli show <tag>` | Detalhe + linha do tempo do bem |
| `python -m app.cli move <tag> --type <tipo> --custodian-id ... --reason ...` | Registra movimentação pelo terminal |
| `python -m app.cli create-user --username --password [--name] [--email] [--admin] [--role (repetível)]` | Cria usuário (sem --role/--admin = sem permissões, deny by default) |

Notas: `create-user` pede senha interativa se `--password` for omitido; `ensure_default_roles`
roda a cada execução do CLI.

## 2. Banco de dados
- **Produção**: MariaDB/MySQL — `DATABASE_URL` obrigatória (`mariadb+pymysql://...`);
  sem a variável, a aplicação **não inicia** (`app/config.py` levanta `RuntimeError`).
  Sem fallback para SQLite na aplicação.
- **Pool**: pool_size 10, max_overflow 20, pool_timeout 30, pool_recycle 1800,
  pool_pre_ping (`app/database.py`).
- **Migração leve**: `init_db()` = `create_all` + `_ensure_schema_migrations()`
  (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` idempotente — colunas de users
  (lockout/AD) e user_roles.assigned_by). **Nenhum dado é alterado/removido.**
- **Testes**: SQLite in-memory (default) ou `DATABASE_URL_TEST`.
- **Seed de demo**: `python seed_demo.py` faz `drop_all` + `create_all` — exclusivo para
  banco de demo/teste (nunca produção).

## 3. Configuração (`app/config.py` — único ponto, via env/dotenv)
| Grupo | Variáveis (default) |
|---|---|
| Banco | `DATABASE_URL` (obrigatória) |
| App | `APP_HOST` (192.168.0.9), `APP_PORT` (8000), `APP_NAME`, `APP_VERSION` (1.2.0) |
| Empresa (termos) | `COMPANY_NAME`, `COMPANY_CNPJ`, `COMPANY_ADDRESS` |
| Auth | `AUTH_PROVIDER` (local), `AUTH_SESSION_TTL` (28800 s), `AUTH_COOKIE_NAME` (session), `AUTH_COOKIE_SECURE` (false), `AUTH_PBKDF2_ITERATIONS` (600000), `AUTH_MAX_FAILED_ATTEMPTS` (10), `AUTH_LOCKOUT_SECONDS` (900), `AUTH_ADMIN_USERNAME` (admin), `AUTH_ADMIN_PASSWORD` (vazio), `AUTH_ADMIN_NAME` (Administrador) |
| AD | `AD_SERVER`, `AD_PORT` (636), `AD_USE_SSL` (false), `AD_BASE_DN`, `AD_USER_DN`, `AD_GROUP_BASE_DN`, `AD_BIND_USER`, `AD_BIND_PASSWORD` (somente ambiente — nunca no banco) |

**Segredos**: nenhuma credencial é reproduzida neste contrato (política da baseline).
`AD_BIND_PASSWORD` e `AUTH_ADMIN_PASSWORD` vivem exclusivamente em ambiente.

## 4. Logs
`app/logging_config.py` → `data/logs/app.log` (INFO) e `app.error.log` (WARNING+),
rotação 5 MB × 5 backups; configurado por `run.py`. Nunca registrar credenciais
(regra P19 da spec).
