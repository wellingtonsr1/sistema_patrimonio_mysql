# Data Model — Feature 061 (entidades de infraestrutura do ecossistema)

*Entidades de infraestrutura/operador (não há alteração no modelo de dados da aplicação — Constitution VII). Esta feature não altera tabelas nem campos da aplicação.*

## 1. Ambiente (desenvolvimento/produção)

| Campo | Descrição | Valores / Estado |
|---|---|---|
| nome | identidade | `sistema_patrimonio_mysql` (dev) / `SisPatrimonioPro` (PRO, snapshot) |
| SO alvo | plataforma de execução | Linux (Debian/Ubuntu) / Windows |
| banco | SGBD esperado | MariaDB (Linux) / MySQL Server nativo (Windows) |
| xampp | dependência permitida | `false` em todos os cenários finais |
| https | política | TLS nativo no servidor da aplicação (056), porta `APP_PORT` |

**Transições**: dev → (commit) → GitHub dev → (snapshot whitelist) → PRO → (instalador Linux/Windows) → produção instalada.

## 2. Snapshot de produção (entidade derivada)

| Campo | Regra |
|---|---|
| origem | `git archive HEAD` (commit dev), passado pela whitelist de `deploy.sh`/`deploy.bat` |
| conteúdo autorizado | `app/`, `data/` (+ `.gitkeep` backups/logs), `docs/*.md` (sem `doc_provi*`), `.gitignore`, `README.md`, `requirements.txt`, `run.py`, `seed_demo.py`, `sistema_patrimonio.png`, `SPEC-KIT-SISTEMA-ATUAL.md` |
| proibido | `specs/`, `tests/`, `scripts/`, `install.sh`, `uninstall.sh`, `deploy.*`, `test.bat`, Docker, artefatos gerados (venv, `data/ssl/`, `data/logs/*`, `data/backups/*` reais, `.env`) |
| residuais proibidos | `*~`, `*-old`, `_teste_*`, `app/config.py~` e similares |
| rastreabilidade | assinatura: mensagem "… (snapshot de produção de `<host>`, commit dev `<hash>`)" |
| propriedade crítica | determinista: mesma dev → mesmo conteúdo, independente do SO que publica (`deploy.sh` ≡ `deploy.bat`) |

**Estado inválido (aprovável só com classificação explícita)**: diferença dev×PRO divergente da whitelist; arquivo necessário ausente; residual gerado incluído.

## 3. Configuração HTTPS (entidade aplicada por ambiente)

| Campo | Fonte de verdade | Regras |
|---|---|---|
| `APP_SSL_CERTFILE` | `.env` do ambiente | caminho do certificado; com `APP_SSL_KEYFILE` presente → TLS ativo (run.py) |
| `APP_SSL_KEYFILE` | `.env` | caminho da chave privada; **nunca versionado** (FR-025) |
| `APP_PORT` | `.env` | porta única da aplicação; TLS escuta nela (D-006: 8000 na instalação) |
| `AUTH_COOKIE_SECURE` | `.env` | `true` obrigatório quando o instalador ativa TLS (FR-020); dev sem TLS mantém default |
| certificados | `data/ssl/` | CA (`ca.crt`) + servidor; SAN com `IP:<lan>`, `DNS:localhost`, `DNS:sispatrimoniopro.local`; regeneração idempotente com `--force` |
| trust store | client SO/navegador | CA importada nos aparelhos (uma vez); roteiro em `docs/HTTPS_LOCAL.md` |

**Estados**: `HTTP` (envs vazios — comportamento da dev atual), `HTTPS` (envs + cert válido no SAN). Transição segura HTTP→HTTPS e reverso não podem quebrar serviço/cookie.

## 4. Instalação (entidade resultante do instalador)

| Campo | Linux (027, referência) | Windows (a auditar/corrigir) |
|---|---|---|
| diretório | `/opt/SisPatrimonioPro` | a confirmar na Fase 1 |
| venv | `.venv` no diretório | idem |
| `.env` | 0600; `DATABASE_URL` percent-encoded, `APP_HOST=0.0.0.0`, `APP_PORT=8000` | idem, com MySQL nativo |
| banco | MariaDB (se nada existir), banco/usuário dedicados, sem destruição | MySQL Server nativo (detectar versão/serviço), sem XAMPP |
| serviço | systemd `sispatrimoniopro`, usuário dedicado | mecanismo a confirmar (serviço do instalador versionado) |
| firewall | regra para porta 8000, automática e idempotente (clarify Q5) | idem (regra nomeada `netsh`/equivalente) |
| HTTPS | herda baseline 056: cert + envs + cookie seguro | idem — correção da causa raiz (FR-018) |
| idempotência | reexecução reutiliza tudo; nenhuma recriação sem `--recreate-db` dupla confirmação | mesmo contrato |

**Regras transversais**: nenhuma senha em argv/log (027 SR-001); nenhum dado apagado; `.env` nunca sobrescrito sem backup+confirmação.

## 5. Instalador Windows (entidade versionada)

| Campo | Valor/Estado |
|---|---|
| localização | versionado (PRO ou dev) — Fase 1 localiza (clarify Q3) |
| estado atual | funcional para rodar a aplicação; **HTTPS perdido na instalação** (motivo da feature) |
| estado alvo | reproduz o baseline 056: gera/aponta cert, envs TLS, cookie seguro, firewall, serviço, MySQL nativo |
| mecanismo de serviço | a confirmar (Agendador/serviço nativo/NSSM?) — decide na Fase 1 |

## 6. Relatório de diagnóstico (entregável A da 061)

| Campo | Regra |
|---|---|
| seções | arquitetura real; fluxo deploy verificado; fluxo instalação; fluxo banco; fluxo HTTPS; divergências classificadas (intencional/necessária/obsoleta/erro/risco); problemas; causas prováveis/confirmadas |
| evidência | toda causa confirmada por arquivo:linha, comando reprodutível ou teste |
| imutabilidade de fato | só registros; nenhuma alteração durante a produção do relatório |

## 7. Matriz MariaDB × MySQL (entregável B)

- Linhas: driver, SQLAlchemy, PyMySQL, CREATE/ALTER TABLE, índices, constraints, datetime, boolean, enum, JSON, transações, pool, charset, collation, SQL da instalação/inicialização.
- Células preenchidas só com resultado de análise executável (código real ou teste em banco); compatibilidade não verificada fica explícita como não verificada (spec FR-007).
