# Research: Atualização da Ajuda/Manual e do README.md (feature 009)

**Data**: 2026-09-16 · Todas as decisões verificadas no código real (somente leitura) antes do desenho.

## D1 — Onde vive a ajuda: **`app/services/help_service.py` (conteúdo), apresentada em `/ajuda`**

- **Decisão**: a Ajuda/Manual do input é o conjunto `ARTICLES` / `FAQ` / `CATEGORIES` em `app/services/help_service.py`, servido por `app/web/help_routes.py` (`GET /ajuda`, `GET /ajuda/{article_id}`, templates `ajuda/index.html` / `ajuda/article.html`), com pesquisa client-side e tooltips.
- **Evidência**: 21 artigos listados por `id` (L33–L789), `FAQ` (12 itens, chaves `question`/`answer`), `CATEGORIES` (7 categorias com `article_ids`); entrada na sidebar/topbar (`base.html` L122/L250); `test_help.py` valida bloqueio sem login e renderização (não fixa contagens).
- **Alternativas rejeitadas**: `docs/*.md` (não são a ajuda do usuário final — ficam fora do escopo); templates como alvo de conteúdo (apenas apresentam; conteúdo vive no service); criar "arquivo de manual" novo (não existe no projeto e o input manda descobrir o mecanismo real, não criar outro).

## D2 — Divergências reais encontradas (docs vs. código verificado)

| # | Divergência | Documento | Comportamento real verificado |
|---|---|---|---|
| 1 | Contagem de testes "154 testes... 153 passando e 1 falhando" (L23 e seção de testes) | README | Suíte atual: **282 testes** (281 passed / 1 failed — lockout defasado, registrado nas specs 007/008 e conferido nesta sessão) |
| 2 | "padrões do projeto: `APP_HOST=127.0.0.1` e `APP_PORT=8000`" (L134) | README | `app/config.py`: `APP_HOST = os.getenv("APP_HOST", "192.168.0.9")`, `APP_PORT = 8000` |
| 3 | Exportação CSV de locais (feature 008) ausente | README e ajuda | `GET /api/v1/reports/locations/csv` (`locais.csv`), botão na tela de Locais, gate `relatorios.exportar` — implementada e validada |
| 4 | Pesquisa de colaboradores (006) e pesquisa de locais (007) não citadas nas funcionalidades | README | Ambas implementadas (`LocationService.get_all(search=...)`; pesquisa multi-campo de colaboradores) |
| 5 | Etiquetas em lote não listadas | README | Rota real `GET /assets/labels` (`routes.py` L370, gate `patrimonio.visualizar`); README só cita "geração dinâmica de etiquetas QR" |
| 6 | Artigo `exportar-csv` da ajuda não menciona locais | Ajuda (`exportar-csv`, L670) | Exportação de locais existe (008) |
| 7 | (Correção da análise preliminar) CLI `reset-password` | README | **Já documentado** (L588–596) — sem gap; a nota anterior do checklist foi corrigida |

## D3 — Configuração real para a seção "Instalação em uma máquina nova"

- **Runtime**: Python 3.10+; dependências em `requirements.txt` (FastAPI, Uvicorn, SQLAlchemy 2, Pydantic v2, Jinja2, PyMySQL, python-dotenv, openpyxl, reportlab, ldap3, pytest, requests).
- **Banco**: MariaDB/MySQL via `DATABASE_URL` (`mariadb+pymysql://...`) — **obrigatória**, sem fallback SQLite na aplicação (`config.py` raise se ausente; SQLite restrito a testes). `docs/configuração mariaDB.md` existe como referência interna (não alvo de alteração).
- **Estrutura do banco**: criada automaticamente por `init_db()` no start (`run.py` chama `init_db()` antes do uvicorn; `database.py` L75 + `_ensure_schema_migrations` idempotente). **Não há comando de migração manual** — o guia deve dizer isso, não inventar.
- **Primeiro admin — 3 caminhos reais**: (1) env `AUTH_ADMIN_USERNAME`/`AUTH_ADMIN_PASSWORD` no primeiro start; (2) tela `/setup` ("Primeiro acesso") quando não há usuários e não há `AUTH_ADMIN_PASSWORD`; (3) CLI `python -m app.cli create-user --username ... --password ... --name ... --admin` (senha mín. 8; PBKDF2-HMAC-SHA256).
- **Inicialização**: `python run.py` → host/porta de `APP_HOST`/`APP_PORT` (padrões reais: `192.168.0.9`/`8000`); Swagger em `/docs`; health em `/health` (público, `main.py` L94).
- **Testes**: `pytest` (suíte usa SQLite em memória por padrão; `DATABASE_URL_TEST` opcional).
- **`.env`**: carregado por `python-dotenv` (`config.py`); **não existe `.env.example` no repositório** — o guia deve mostrar a criação manual do `.env` com variáveis mínimas (`DATABASE_URL`), sem inventar o arquivo de exemplo.

## D4 — Contratos: **não aplicáveis** nesta feature

- **Decisão**: `contracts/` não será gerado — a feature não altera nenhuma interface de API, CLI ou UI; os "consumidores" (roteador da ajuda, pytest) continuam consumindo as mesmas estruturas.
- **Rationale**: o único "contrato" relevante é o formato interno das listas `ARTICLES`/`FAQ`/`CATEGORIES`, já documentado no `data-model.md` desta feature (estrutura preservada).
- **Alternativas rejeitadas**: gerar contrato vazio por formalidade (ruído sem valor).

## Verificações pontuais (fatos, não decisões)

| Fato | Evidência |
|---|---|
| 21 artigos / 12 FAQ / 7 categorias atuais | Execução `python3 -c` importando `help_service` nesta sessão |
| `test_help.py` não fixa contagens de artigos/FAQ | grep em `tests/test_help.py` (nenhum `len(ARTICLES)`/`== 21`) |
| `README` cita "154 testes" e `APP_HOST=127.0.0.1` | grep no `README.md` (L23, L134) |
| Rota `/assets/labels` existe e não está nas funcionalidades do README | `routes.py` L370 + grep (ausente no README) |
| Suíte atual 282 testes (281/1) | Execuções pytest das specs 007/008 (sessões desta feature) |
| `init_db` automático no start | `run.py` (chamada antes do uvicorn) |
| `.env.example` inexistente; `.env` existente (fora do escopo) | glob na raiz |
