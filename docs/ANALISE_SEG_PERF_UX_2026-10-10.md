# Análise técnica — Segurança, Desempenho, UX e Engenharia

**Data**: 2026-10-10
**Escopo**: leitura de código (`app/`, `tests/`, `docs/`, deploy), execução da suíte completa e **medição pontual** de tempo/queries de páginas reais.
**Modo**: diagnóstico — nenhuma alteração de código. Árvore limpa ao final (harness temporário de medição removido).

---

## 0. Método e limitações

| O que foi feito | Detalhe |
|---|---|
| Leitura de código | `app/main.py`, `app/config.py`, `app/api/*`, `app/web/*`, `app/services/*` (foco em auth, RBAC, sessão, backup, importação, relatórios) |
| Suíte | `.venv/bin/python -m pytest -q` → **1005 passed, 2 skipped em 88,79 s** (SQLite in-memory, padrão da casa) |
| Medição | Harness temporário (removido) com TestClient + SQLite in-memory, seed de **2.000 bens**, contagem de queries por evento `before_cursor_execute` |
| Estática | Buscas por CSRF/CSP/rate-limit/paginação/aria/template-safe/SQL crua, inspeção dos headers de resposta |

**Limitações**: medições em SQLite em memória (sem latência de rede nem custo real do MariaDB); sem execução em navegador (sem Chrome no ambiente); sem varredura de dependências (`pip-audit`/`bandit` não instalados); sem teste de carga concorrente.

---

## 1. Veredito rápido

Sistema **maduro e bem documentado** (67 specs, 24k linhas de Python, 1.005 testes verdes, RBAC deny-by-default, trilha de auditoria imutável, backup com retenção). Os riscos relevantes hoje não são de arquitetura, e sim de **camada de borda**: ausência de cabeçalhos de segurança/CSRF explícito, upload sem limite, ausência de rate limit por IP, **falta de paginação nas listas** (corte silencioso em 200/10.000 registros) e **ausência de CI/linter** — ou seja, nada que mude o modelo de domínio, tudo que muda a confiança de produção.

---

## 2. Segurança

### 2.1 O que está bom (confirmado no código)

- **RBAC deny-by-default** com dependência por rota (`app/api/deps.py:104`) e auditoria de acesso negado. Verifiquei rotas web e API: praticamente todas declaram `require_permission(...)` (exceção: `/` dashboard e rotas públicas `/login`, `/setup`, `/logout` — adequado).
- **Senha**: PBKDF2-HMAC-SHA256 com 600.000 iterações (OWASP), salt de 16 B/usuário, comparação com `hmac.compare_digest` e hash "dummy" para igualar tempo de resposta (`app/services/auth_service.py:61-83`).
- **Sessão server-side**: token `secrets.token_urlsafe(32)` gravado no banco apenas como hash SHA-256, cookie `HttpOnly` + `SameSite=Lax` + `Secure` configurável, TTL 8 h, revogação no logout (`app/services/session_service.py`).
- **Open redirect** mitigado (`app/web/routers/auth.py:46`); **path traversal** bloqueado por regex no download de backup (`app/services/backup_service.py:1392-1405`).
- **Auditoria imutável**: `audit_service.py` não expõe update/delete (grep negativo).
- **Segredos fora do repositório**: `.env`, `*.crt`, `*.key`, `*.pem` no `.gitignore` e não versionados (confirmei com `git ls-files`).
- **XSS de template**: Jinja2 autoescape ativo; nenhuma ocorrência de `|safe`/`Markup(` nos templates.
- **SQL**: nenhuma concatenação de entrada de usuário; único `text(f"...")` é em `backup_service.py:1031` (`SELECT COUNT(*) FROM {table}`) — conferir que `table` vem de lista fixa/metadata, nunca de input.
- **Primeiro acesso** com reivindicação atômica (`app/web/routers/setup.py:_claim_first_access`) — protegido contra corrida.
- **Imagem Docker** não embute `.env` (`.dockerignore`).

### 2.2 Achados (priorizados)

| # | Achado | Evidência | Risco | Recomendação |
|---|---|---|---|---|
| S1 | **Sem cabeçalhos de segurança** — resposta de `/login` veio apenas com `content-length` e `content-type` (medido) | nenhum middleware de headers em `app/main.py` | Alto | Middleware global: `Content-Security-Policy` (hoje há script inline em `base.html`, começar com `'unsafe-inline'` e evoluir), `X-Frame-Options: DENY`/`frame-ancestors`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy` e `Strict-Transport-Security` quando `AUTH_COOKIE_SECURE=true` |
| S2 | **Sem token CSRF** (documentado como dívida em `docs/ARQUITETURA_E_MANUTENCAO.md:1037`) | nenhum `csrf` no código | Médio | Mitigação atual é só `SameSite=Lax`; adicionar token sincronizado por sessão nos POSTs de formulário (double-submit) — barato e elimina a classe inteira |
| S3 | **Sem rate limit por IP** — o lockout é apenas por conta (10 tentativas / 900 s) | grep sem `slowapi`/`limiter` | Médio | Limiter em `/login` e `/api/v1/auth` (ex.: 20 req/min por IP + backoff exponencial). Hoje é possível varrer muitas contas em paralelo |
| S4 | **Upload CSV sem limite de tamanho** — `raw = file.file.read()` carrega o arquivo inteiro na memória | `app/web/routers/shared.py:103` | Médio | Limite explícito (ex.: 10 MB / 50k linhas) com mensagem amigável; recusar antes de `read()` via `Content-Length`/leitura incremental |
| S5 | **Flag legada `is_admin` = bypass total** coexistindo com perfis | `app/services/permission_service.py:253,273` | Médio | Decidir institucionalmente: migrar contas para perfil `Administrador` e tornar o flag somente-leitura/depreciado; auditar quem ainda o usa |
| S6 | **Cookie `Secure` default `false` e sem HSTS** | `app/config.py` (`AUTH_COOKIE_SECURE`) | Médio (produção) | Exigir `AUTH_COOKIE_SECURE=true` + HSTS no instalador quando HTTPS estiver ativo; adicionar checagem no `/health` ou no boot |
| S7 | **`/health` público** expõe estado de BD/AD | `app/main.py:153` | Baixo | Manter público só `/health` minimal (200 ok) e mover o detalhado para rota autenticada |
| S8 | **Docker: container roda como root**; `SECRET_KEY` exigido no `docker-compose.yml` mas **nunca lido** por `app/config.py` | `Dockerfile` sem `USER`; `grep SECRET_KEY app/` = 0 | Baixo | Criar usuário não-root no Dockerfile; remover `SECRET_KEY` do compose (config morte que induz a erro) ou passar a usá-lo |
| S9 | **Sem "esqueci minha senha"** por e-mail | `docs/` já registra como decisão institucional | Institucional | Se AD/SMTP forem a base, habilitar fluxo por email ou por admin; hoje a recuperação é manual (CLI/admin) |
| S10 | **Sem varredura de dependências** (`pip-audit`/`bandit`/Dependabot) | sem configuração | Médio | Rodar `pip-audit` no CI e ligar Dependabot |

### 2.3 Pontos que não são vulnerabilidade (não investir agora)

- Força bruta distribuída mitigada parcialmente por lockout por conta + auditoria de falhas.
- Enumeração de usuários mitigada por hash dummy (timing igualado).
- `SameSite=Lax` já bloqueia POST cross-site com cookie — o CSRF (S2) é reforço, não remendo de buraco aberto.

---

## 3. Desempenho

### 3.1 Medição (2.000 bens, SQLite in-memory, TestClient)

| Rota | Mediana | Queries | Observação |
|---|---|---|---|
| `/` (dashboard) | **24,1 ms** | 16 | dashboard dispara ~16 consultas separadas |
| `/assets` | **32,7 ms** | 7 | limitado a 200 linhas |
| `/assets?search=Notebook&status=AVAILABLE` | **38,2 ms** | 7 | `ilike '%...%'` em 6 colunas + relações |
| `/movements` | **10,3 ms** | 4 | ok |
| `/reports/inventory` | **94,4 ms** | 4 | carrega todos os bens filtrados (limit 10.000) e renderiza HTML |
| `GET /api/v1/reports/inventory/csv` | **187,7 ms** | 4 | 260 KB em memória (2.000 linhas) |

Leitura: **a aplicação é rápida no volume atual**. Os riscos são de escala (volume × HTML gigante × exportações em memória), não de latência por request.

### 3.2 Achados

| # | Achado | Evidência | Recomendação |
|---|---|---|---|
| P1 | **Sem paginação nas listas web** — `/assets` traz `limit=200` e o template mostra *"Mostrando X de Y"* sem controles de página | `app/web/routers/assets.py` (`limit=200`), `templates/assets/list.html:164`; grep por `pagination`/`page-item` = **0 arquivos** | Implementar paginação (offset/limit + controles) em Assets, Movimentações, Colaboradores, Locais, Audit log. Hoje registros além dos 200 são **inacessíveis** sem filtro |
| P2 | **Corte silencioso nos relatórios/exportações**: `limit_query = limit if limit > 0 else 10000` | `app/services/report_service.py:39` | Avisar na tela/CSV quando o total > limite, ou remover o teto com streaming |
| P3 | **Exportações montam tudo em memória** | `report_service.py:488` (`db.query(Movement)...all()`), CSV/XLSX/PDF como string/bytes | `StreamingResponse` com `yield` por lote (CSV) e paginação em lotes para XLSX/PDF |
| P4 | **Dashboard com ~16 consultas por request e sem cache** | `app/services/dashboard_service.py:11-60` | Consolidar em 3-4 agregações (`GROUP BY`) + cache curto (30-60 s) por usuário/sistema |
| P5 | **`joinedload(Asset.maintenances)` junto de `LIMIT`** na listagem | `app/services/asset_service.py:164-166, 237` | Confirmar no MariaDB real (log de SQL) que o LIMIT é aplicado ao subquery; se não, explodir linhas em volume |
| P6 | **Busca com `ilike '%x%'` em 6 colunas + 2 relações**, sem índice utilizável | `asset_service.py:168-198`; `Location.department` DISTINCT por request | Full-text (MariaDB `FULLTEXT`/MFTS) ou coluna normalizada + índice; cachear a lista de departamentos |
| P7 | **Sem `Cache-Control`/`ETag`** em estáticos e páginas | headers medidos | Cache longo com hash/immutável para `/static/vendor/*` (hoje só o CSS tem `?v=`); páginas autenticadas: `no-store` explícito |
| P8 | **`purchase_value` como `Float`** | `app/models/asset.py:24` | Migrar para `Numeric(12,2)` (soma de patrimônio e depreciação não devem somar ponto flutuante) — exige migração Alembic (`migrations/versions/`) |
| P9 | **Processo único** (uvicorn `run.py`, sem `--workers`) | `run.py` | Ok para a carga atual; se crescer, subir workers ou atrás de reverse proxy com cache |
| P10 | Pool saudável (`pool_size=10`, `max_overflow=20`, `pre_ping`, `recycle=1800`) | `app/database.py:16-24` | Manter; monitorar esgotamento do pool em produção |

---

## 4. UX / Front-end

### 4.1 O que está bom

- Assets 100% locais (zero CDN) → funciona atrás de firewall e com PWA offline (`base.html:21-32`).
- Tema claro/escuro com anti-flash e sincronia com Bootstrap (`static/js/main.js:38-55`).
- Sidebar responsiva (mobile + overlay), menu dinâmico por permissão (`can(...)`).
- Empty states presentes em 16 templates; confirmação em 9 ações destrutivas (`confirm(`).
- Formulários com validação HTML5 (`required`) e mensagens de erro de negócio visíveis.
- Otimismo concorrente na edição de bem (`expected_updated_at` → conflito explícito) — UX correta para edição multiusuário.

### 4.2 Achados

| # | Achado | Evidência | Recomendação |
|---|---|---|---|
| U1 | **Sem feedback de carregamento** — 0 templates com spinner/loading; sem proteção contra duplo submit | grep por `spinner`/`loading` = 0 arquivos; nenhum `submitting`/`data-busy` | Botão "Salvando…" com `disabled` + spinner; para importações/geração de PDF, barra de progresso |
| U2 | **Mensagens de sucesso/erro na query string** (`?error=`, `?success=`, `?moved=true`) | 10 rotas em `admin_routes.py` + `templates/assets/detail.html:8-44`, `inventarios/new.html:18` | Flash via cookie/sessão com auto-dismiss (toast). Hoje a mensagem persiste no refresh, polui a URL e é compartilhável/acessível por histórico |
| U3 | **Acessibilidade fraca** | 29 ocorrências de `aria-*` em **53 templates**; **0** em `dashboard.html`, `login.html`, `403.html`, `404.html` | Rodar axe/Lighthouse; associar `label[for]` em todos os 159 inputs, `aria-live` em mensagens de erro, `aria-label` em botões só-ícone, contraste dos estados de status |
| U4 | **Foco/teclado no campo de trabalho** — `autofocus` em apenas 2 templates | grep `autofocus` = 2 | Crítico na conferência de inventário (`inventarios/detail`, `/inventarios/{id}/offline`): autofocus no campo de leitura + "Enter confirma" + som de feedback |
| U5 | **Paginação ausente também no audit log e listas grandes** (ver P1) | `admin/audit/list.html` | Paginar e oferecer filtro por período/usuário/módulo — hoje é uma tabela potencialmente enorme |
| U6 | **Sem atalhos/UX de lote em movimentações** (hipótese a validar com usuários) | — | Priorizar a partir de uso real: medir tarefas mais repetitivas (etiquetas, inventário, transferência em lote) |
| U7 | **Backlog de UX espalhado** em 3 arquivos | `docs/Coisas a corrigir ou melhorar.md`, `docs/Melhorias_SisPatrimonio_Pro.md`, `docs/ANALISE_PROFUNDA_*` | Consolidar em um único backlog versionado com prioridade/estado (o padrão de specs do repo já é excelente — aplicar o mesmo rigor ao backlog) |

---

## 5. Engenharia, testes e operação

| # | Achado | Evidência | Recomendação |
|---|---|---|---|
| E1 | **Sem CI** — `.github/` contém apenas `skills/`, nenhum workflow | `ls .github` | GitHub Actions: `pytest -q` + `ruff check` + `pip-audit` em PR; custo baixo, elimina regressão silenciosa (já houve 4 failures ambientais documentados) |
| E2 | **Sem linter/formatter/pre-commit** (sem `pyproject.toml`, `ruff`, `black`, `mypy`) | `ls pyproject.toml` = inexistente | Adicionar `ruff` (lint+format) com regras mínimas; `pre-commit` opcional |
| E3 | **Suíte saudável**: 1005 passed / 2 skipped / 88,79 s | execução real | Ótimo; registrar baseline no CI (falha se passar a cair) |
| E4 | **`Makefile` com 1 alvo** (`validation-064`) | `cat Makefile` | Padronizar: `make test`, `make lint`, `make serve`, `make validation-<spec>` |
| E5 | **Observabilidade limitada**: log rotativo em arquivo + `/health`; sem métricas nem log de request/latência | `app/logging_config.py` | Middleware de access log estruturado (método, rota, status, ms, user_id) + métricas simples (ou Prometheus) e alerta de falha de backup já parcialmente existente |
| E6 | **Alembic com apenas 2 revisões + `create_all` tolerante** | `migrations/versions/` | Manter a regra "DDL só via migração" documentada na 052; evitar regressão para `ALTER` em `database.py` |
| E7 | **Testes em SQLite** e validação real em MariaDB pendente | `validacao.md` (limitações) | Rodar a suíte também contra MariaDB (compose de teste) — cobre colações, `ilike`, `ENUM` e o `LIMIT + joinedload` (P5) |
| E8 | **Backup/restauração nunca exercitados em produção** (documentado) | `docs/BACKUP_*` | Game day: restaurar de fato em ambiente de homologação e registrar tempo/resultados |

---

## 6. Plano sugerido (prioridade)

**P0 — próximas 1-2 semanas (borda de segurança + CI)**
1. Middleware de cabeçalhos de segurança (S1) — ~1 dia.
2. Limite de tamanho no upload CSV (S4) — horas.
3. Rate limit por IP no login (S3) — 1 dia.
4. CI com `pytest` + `ruff` (E1/E2) — 1 dia, ganho permanente.
5. Auditoria/decisão sobre `is_admin` (S5).

**P1 — mês seguinte (UX e escala)**
6. Paginação real nas listas + aviso de corte nos relatórios (P1/P2/U5).
7. Flash messages (toast) em vez de query string (U2) e estados de carregamento/duplo submit (U1).
8. Acessibilidade: `label[for]`, `aria-live`, axe no fluxo de login e inventário (U3/U4).
9. Dashboard agregado + cache curto (P4); streaming nas exportações (P3).
10. Docker não-root + limpeza do `SECRET_KEY` do compose (S8).

**P2 — trimestre (plataforma)**
11. CSRF token (S2), HSTS/Secure obrigatório em produção (S6).
12. Migração `purchase_value → Numeric` (P8) e busca full-text (P6).
13. Métricas/observabilidade e suíte contra MariaDB (E5/E7).
14. `pip-audit`/Dependabot (S10) e game day de backup (E8).

---

## 7. Conclusão

Não há fragilidade estrutural: autenticação, autorização, auditoria e backup estão acima da média de sistemas internos. O que separa o sistema de um patamar "pronto para produção institucional" é o **acabamento de borda** — cabeçalhos/CSRF/limites de entrada, paginação honesta (não cortar dados em silêncio), feedback de interface e um pipeline que rode os 1.005 testes a cada push. Todos os itens acima são incrementalmente aplicáveis sem tocar no modelo de domínio nem nas 67 specs existentes.
