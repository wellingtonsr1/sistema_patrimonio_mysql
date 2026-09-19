# Research — Revisão e Melhoria do README.md (feature 023)

*Baseado na análise real do código (executada em 2026-09-18). Nenhum NEEDS CLARIFICATION restante.*

## Inventário de divergências README ↔ código (US1 da spec)

### D1 — Seção "Documentação" lista estrutura `docs/` fictícia (CONFIRMADO, §32/FR-023)

O README (L899–922) apresenta uma "Sugestão" de `docs/` com 12 arquivos (`instalacao.md`, `configuracao.md`, `autenticacao.md`…). **Nenhum existe.** O conteúdo real de `docs/`:

```text
docs/ARQUITETURA_E_MANUTENCAO.md
docs/GUIA_DE_MANUTENCAO.md
docs/INVENTARIO_TECNICO.md
docs/AVISO_RESTORE_DEADLOCK.md
docs/configuração mariaDB.md
docs/doc_proviśorios/
```

**Decisão**: substituir a lista fictícia pelas referências reais (caminhos verificados). "Sugestão" removida — o briefing proíbe estrutura de documentação fictícia.

### D2 — `/setup` documentado corretamente, mas condições incompletas (CONFIRMADO, §26/FR-017)

- `/setup` GET/POST existe (`app/web/routes.py` L1644/L1658) via `SetupClaim` singleton;
- CLI `create-user` existe (`app/cli.py` L227) com `--username/--password/--name/--email/--admin/--role` (repetível) — README já correto nos parâmetros;
- `AUTH_ADMIN_USERNAME/AUTH_ADMIN_PASSWORD/AUTH_ADMIN_NAME` existem (`app/config.py` L130–132).

**Decisão**: manter os 3 mecanismos, explicitar a condição real do `/setup` (disponível enquanto não houver usuário cadastrado — registro singleton `setup_claims.id=1`) e quando cada caminho se aplica.

### D3 — CLI confirmado; nenhum comando obsoleto encontrado (FR-018)

`stats`, `list [--search/-s, --status]`, `show <tag>`, `move <tag> --type --reason [--custodian-id --location-id --operator]`, `create-user`, `reset-password` — todos existem e batem com o README. **Decisão**: preservar, com parâmetros conferidos um a um.

### D4 — Backup/restauração documentado conforme specs 015–022 (CONFIRMADO, FR-006)

Rotas existentes verificadas em `admin_routes.py`: manual (`/admin/backups/gerar`), automático + retenção (020), configurável pela tela com modal (021/022 — o README ainda não menciona o acesso atual via ⚙ na página de Backups). Tabelas `backup_records`/`backup_config` reais. **Decisão**: atualizar a descrição do acesso às configurações (⚙ no topo direito abre o modal; rota `/admin/backups/configuracoes` mantida por compatibilidade).

### D5 — Regras de AD corretas no README (CONFIRMADO, FR-009)

Fluxo AD → autenticação → grupo mapeado → perfil → permissões do perfil; prioridade numérica do mapeamento (`ad_group_role.priority`, menor = maior, default 10); usuários AD sem mapeamento não são provisionados; conta de serviço apenas consulta. Tudo verificado (`ad_group_role.py`, `ad_service.py`, `auth_service.py`). **Decisão**: preservar, apenas conferindo coerência.

### D6 — RBAC correto, mas catálogo de permissões incompleto (FR-010)

O README lista 10 módulos; o catálogo real (`permission_service.py`) inclui também **`backup.gerenciar` e `backup.restaurar`** (features 015+). Perfis padrão conferidos um a um: `Administrador, Gestor de TI, Técnico de TI, Patrimônio, Almoxarifado, Auditor, Consulta` — batem com `_seed_default_roles`. `movimentacao.cancelar` reservada — correto no README. **Decisão**: adicionar o módulo Backup ao catálogo.

### D7 — Configurações reais: `AUTH_*` conferidas (FR-015)

`AUTH_PROVIDER, AUTH_SESSION_TTL(28800), AUTH_COOKIE_NAME(session), AUTH_COOKIE_SECURE(false), AUTH_PBKDF2_ITERATIONS(600000), AUTH_MAX_FAILED_ATTEMPTS(10), AUTH_LOCKOUT_SECONDS(900), AUTH_ADMIN_*` — todas existem (`config.py` L107–132); 423 Locked confirmado (`auth_service.py`). **Decisão**: tabela de lockout preservada (valores conferidos).

### D8 — Data e hora (§21/FR-012): Feature 004 ESTÁ implementada (CONFIRMADO)

`app/utils/time_utils.py` implementa o contrato UTC→America/Recife (persistência naive UTC, apresentação Recife, datas de negócio sem fuso). **Decisão**: a seção pode permanecer (não é spec sem implementação) — manter com referência à spec 004.

### D9 — Inventário: regra fundamental e ciclo corretos (FR-007)

Snapshot na criação, status `PENDENTE/ENCONTRADO/LOCAL_DIFERENTE/NAO_ENCONTRADO/SEM_IDENTIFICACAO`, re-conferência deliberada (spec 003), encerramento trava itens, divergências não alteram cadastro (`inventario_service.py` L305). Bens **não previstos**: o código trata via `item.nao_previsto` como observação complementar — o README diz "aceita bens encontrados que não estavam na lista" (correto em essência; precisar a redação). Ata comprobatória: CSV (`generate_inventario_csv`), PDF (`generate_inventario_pdf`), **Excel** (`generate_inventario_excel` — existe, L731). **Decisão**: preservar com ajuste de precisão em "bens não previstos".

### D10 — Estrutura do projeto: quase correta (FR-020)

Raiz real inclui também `sistema_patrimonio.png`, `SPEC-KIT-SISTEMA-ATUAL.md`, `TASKS/`, `specs/` (ausentes da árvore do README); `data/`, `docs/`, `tests/`, `seed_demo.py`, `run.py`, `requirements.txt` confirmados. **Decisão**: árvore atualizada com os diretórios reais relevantes (specs/ incluído, pois a Constituição e várias features o referenciam); arquivos binários/auxiliares não entram (listagem não exaustiva, §29).

### D11 — Tecnologias (FR-013): versões mínimas confirmáveis

`requirements.txt` real: `fastapi>=0.110.0, uvicorn[standard]>=0.28.0, sqlalchemy>=2.0.0, pydantic>=2.6.0, jinja2>=3.1.3, python-multipart>=0.0.9, pytest>=8.0.0, requests>=2.31.0, ldap3>=2.9.1, pymysql>=1.1.0, python-dotenv>=1.0.0, openpyxl>=3.1.0, reportlab>=4.0.0`. `APP_VERSION = "1.2.0"` (`config.py` L92). Python 3.10+ (runtime observado: 3.10). **Decisão**: tabela com versões mínimas do requirements (confirmáveis) + menção à versão da aplicação do código.

### D12 — Testes sem números fixos (FR-019)

README atual já segue a regra (L724). Suíte real cobre os módulos listados + backup (7 arquivos de teste de backup não citados). **Decisão**: manter a regra, ampliar a lista de cobertura (backup manual/automático/retenção/config/restore).

### D13 — Endpoints públicos principais (SC-002)

Confirmados: `/` (dashboard), `/login`, `/setup` (condicional), `/docs` (Swagger), `/health` (público, `main.py` L144), `/ajuda` (`help_routes.py` L31), `/api/v1` (protegida), `/assets/labels` (etiquetas A4). **Decisão**: lista de endpoints do README ajustada a este conjunto verificado.

### D14 — Auditoria e segurança (FR-011/FR-022)

Campos de `audit_logs` e a lista de eventos batem com o código; "credenciais não são registradas" correto. Seção Segurança já separa "implementado" × "recomendações" — estrutura correta, preservada. **Decisão**: preservar; conferir menções pontuais (open redirect no `next` — confirmado no padrão do projeto).

### D15 — Banco de dados (FR-021)

Produção MariaDB/MySQL (`mariadb+pymysql://`); sem fallback SQLite (SQLite só em testes via `DATABASE_URL_TEST`); `init_db()` + `_ensure_schema_migrations()` idempotente — tudo confirmado. Tabelas citadas existem como models. **Decisão**: preservar com ajustes mínimos (ex.: citar `backup_records`/`backup_config`, que já existem e são relevantes).

## Decisões de execução (R1–R5)

### R1 — Estratégia de edição: revisão por seção guiada pelo inventário D1–D15

**Decisão**: editar o README seção a seção, aplicando cada divergência; preservar o que já está correto (a revisão é fundamentada, não reescrita por reescrita).
**Racional**: minimiza risco de regressão documental; o README atual é em geral fiel — as divergências são pontuais.
**Alternativas descartadas**: reescrita total do zero (perde conteúdo verificado); apenas correções pontuais sem reorganização (não atende §37).

### R2 — Ordem das seções

**Decisão**: manter a ordem atual do README (que já é próxima da sequência §37 do briefing): Introdução → Funcionalidades → Modelo Conceitual → Tecnologias → Arquitetura → Como Executar/Instalação → Autenticação → AD → RBAC → Proteções → Auditoria → Banco → CLI → Ajuda → Testes → Estrutura → Escopo → Segurança → Backup → Documentação → Licença.
**Racional**: o README atual já está organizado; reordenar causaria diff desnecessário sem ganho de fidelidade. O briefing §37 permite ajuste se a estrutura real justificar.

### R3 — Tratamento de `docs/doc_proviśorios/` e arquivos com nome não-ASCII

**Decisão**: referenciar apenas os 4 arquivos `.md` estáveis de `docs/`; `doc_proviśorios/` e `configuração mariaDB.md` são mencionados nominalmente apenas se úteis, sem criar expectativa de documentação estruturada.
**Racional**: o README é porta de entrada; apontar para conteúdo real evita 404 documental, mas a organização interna de docs/ não é normalizada.

### R4 — Versionamento de informações voláteis

**Decisão**: `APP_VERSION` citado uma única vez (seção Status), marcado como "conforme `app/config.py`"; contagens de testes não entram; suíte descrita por cobertura.
**Racional**: reduz pontos de desatualização (§28/§34/FR-019/NFR-004).

### R5 — Validação da instalação (SC-003)

**Decisão**: validação de comandos é estática (conferência com `run.py`, `cli.py`, `config.py`, `database.py`); não executar instalação real em máquina nova (fora do escopo e sem ambiente disponível). O quickstart registra o procedimento de verificação por inspeção.
**Racional**: a feature é documental; rodar instaladores/banco aqui teria efeitos fora do projeto.
**Alternativa descartada**: instalação em contêiner descartável (dependência de Docker não confirmada no ambiente).
