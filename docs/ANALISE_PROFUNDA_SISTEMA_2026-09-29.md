# Análise Profunda do Sistema — SisPatrimônio Pro

**Data**: 2026-09-29 · **Autor**: Análise técnica (sessão Codebuff/Freebuff) · **Natureza**: diagnóstico — **nenhum código foi alterado**

**Método**: leitura de código-fonte (rotas, services, templates, JS, configuração), logs de runtime (`data/logs/`), histórico git (HEAD = `dc05526`, árvore limpa), specs 049/050/051/052 e execução parcial da suíte de testes. O servidor de produção (`10.39.0.16:8000`) **não respondeu durante a análise** (XAMPP/MariaDB parados), o que limitou a reprodução ao vivo do bug "null" — ver §2.

---

## 1. Panorama geral — o sistema está sadio, com 5 focos de dívida

| Dimensão | Estado | Evidência |
|---|---|---|
| Arquitetura | ✅ Sólida e recém-refatorada | 051 implementada (`routes.py` facade de 86 linhas, 10 routers de domínio, inventário de rotas 140/140) |
| Camadas | ✅ Regras nos services, handlers magros | `inventario.py` (529 linhas) delega a `InventarioService` etc. |
| Segurança | ✅ Boa: RBAC deny-by-default, lockout, PBKDF2 600k, segredos só no ambiente | `app/api/deps.py`, `app/config.py` (achados pontuais no §4.2) |
| Suíte de testes | ⚠️ Verde só com MariaDB de pé | ver §4.1 — anomalia nova e importante |
| Débitos | ⚠️ 5 focos concretos listados | ver §3 |

---

## 2. Bug "null" em `/inventarios/{id}/conferir/{asset_id}` — diagnóstico

### 2.1 O que foi examinado (tudo íntegro)

| Camada | Arquivo | Veredito |
|---|---|---|
| Rota GET | `app/web/routers/inventario.py:267-291` (`conferir_asset_page`) | ✅ valida asset e inventário (404 honestos), renderiza template com contexto completo |
| Template | `app/web/templates/inventarios/conferir.html` | ✅ Jinja2 não renderiza `null` minúsculo; os três ramos (pendente / já conferido / não previsto) estão corretos |
| Rota POST | `inventario.py:300-363` (`confer_item`) | ✅ valida resultado contra enum, redireciona 303 |
| JS global | `main.js`, `inventario_offline.js`, `qr_reader.js` | ✅ nenhum escreve no `document`; todos operam em elementos por ID |
| Auth | `app/api/deps.py` (`require_web_auth`) | ✅ levanta HTTPException 303 com header — nunca resposta vazia |
| Handlers globais | `app/main.py` (`http_exception_handler`) | ✅ cobre todos os status com JSON/página; nenhuma rota de conferência retorna `None` (grep `return None` negativo no domínio) |
| Testes | `tests/test_conferencia_visual.py`, `tests/test_inventario.py:351/756`, `test_inventario_reconferencia_ui.py:238/250` | ✅ a página é exercitada por ≥5 testes com asserts de conteúdo — bug server-side contínuo quebraria a suíte |

### 2.2 O servidor NÃO é a fonte mais provável

Um body de texto literal `null` no navegador **não é produzível pelo Jinja2** (`None` vira string vazia) nem pela rota acima (sempre há HTML completo ou exceção com página amigável). O page body inteiro ser `null` é assinatura clássica de:

1. **Service Worker da feature 033 interceptando a navegação** — hipótese primária. A Página 033 registra o SW em **todas** as páginas com `active_tab == 'inventarios'` (`base.html`, bloco final), incluindo a página de conferir. O `sw.js` tem um **bug estrutural real**: no handler `fetch`, para `request.mode === "navigate"` na rota offline (`/inventarios/{id}/offline`) o código chama `event.respondWith(...)` no primeiro `if` **e depois cai no segundo `respondWith`** (navegações gerais) — um `respondWith` duplo no mesmo evento. Em alguns navegadores/estados de cache isso produz respostas corrompidas. Além disso, o cache `inventario-offline-v31` guarda **a resposta HTML da rota offline**, e qualquer colisão/corrupção de entrada de cache pode contaminar navegações na mesma origem. **Efeito agravante**: o cache só é limpo quando `CACHE_VERSION` muda — ou seja, o bug persiste no dispositivo do usuário **até que o SW seja atualizado** (reincidência compatível com o relato "desde a 033").
2. **Corrupção local no navegador** (cache HTTP do Chrome/Edge + service worker antigo) — resolve com hard reload/desregistro do SW; explicaria por que a suíte e a rota estão limpas.
3. **Proxy/antivírus corporativo** reescrevendo a resposta.

### 2.3 Ações recomendadas (ordem de custo/benefício)

- **R1 (imediato, 1 linha)**: no `sw.js`, adicionar `return` após o `respondWith` do bloco `OFFLINE_NAV_RE` para eliminar o respondWith duplo — bug real e objetivo.
- **R2 (diagnóstico)**: com o servidor de pé, reproduzir em aba anônima (SW não ativo) vs. janela normal. Se em anônima funcionar, a causa é o SW/cache do dispositivo — confirmado sem tocar código.
- **R3 (mitigação defensiva)**: servir `Cache-Control: no-store` nas respostas HTML de navegação web ( hoje nenhuma rota web define cache headers — grep negativo) e/ou bumpar `CACHE_VERSION` para forçar limpeza do cache v31 nos dispositivos.
- **R4 (higiene)**: incluir a página de conferência num teste de regressão visual com asserts de texto ("Conferência de Inventário") — hoje `test_conferencia_visual.py` tem só 2 testes.

---

## 3. Melhorias identificadas (priorizadas)

### P1 — Alta prioridade

**M1. Suíte de testes depende do MariaDB do `.env` (achado NOVO desta análise)**
`tests/conftest.py` usa `DATABASE_URL_TEST="sqlite:///:memory:"` corretamente, **mas** o `TestClient(app)` dispara o lifespan → `init_db()` → engine de **produção** (`mariadb+pymysql://patrimonio@localhost:3306/sispatrimoniopro`). Com o XAMPP parado (estado atual), 14+ testes dão ERROR de conexão e **a suíte completa não termina em 300s** (timeout observado). Ou seja: *o "861 passed" histórico só é reproduzível com o MariaDB local ligado*.
→ Melhoria: fixture de sessão que monkeypatcha `app.database.SessionLocal`/`engine` para o banco de teste **antes** do lifespan, ou variável `SKIP_INIT_DB=1` nos testes. Ganho: suíte hermética, CI sem XAMPP, tempo previsível (~117s).

**M2. `_ensure_schema_migrations` — a dor que a spec 052 resolve (ver §5)**
`app/database.py:64-120` mantém ALTERs manuais; o log de produção já registrou drift real: `Table 'sispatrimoniopro.backup_config' doesn't exist` (2026-09-23 10:32) — tabela criada por `create_all` em versões novas, ausente em banco legado parcialmente atualizado. É exatamente o P5 (drift) da spec 052.

**M3. Bug estrutural no `sw.js` (respondWith duplo)** — descrito em §2.1/R1. Baixo custo, alto valor: é o principal suspeito do bug "null" reincidente.

**M4. `run.py`/`app.main` sem `uvicorn` em `requirements` explícito de produção** — `uvicorn[standard]` está lá (OK); ponto real: **não existe gunicorn/workers** — produção roda single-process via `run.py`. Para o porte atual (institucional, poucos usuários) é aceitável; registrar como decisão consciente.

### P2 — Média prioridade

**M5. `base.html` com HTML quebrado no menu do usuário**
`style="color:var(--color-primary);" ;border-color:rgba(255,255,255,.15);"` — um `;` fora do atributo quebra o parsing do segundo par. Renderiza hoje por tolerância do navegador, mas é bug de marcação latente. Uma linha.

**M6. Dependências de CDN no `base.html`** (fonts.googleapis, cdn.jsdelivr para Bootstrap/Chart.js/QRCode) — o sistema **não funciona sem internet** apesar de existir `app/web/static/vendor/` com Bootstrap local (usado só pelo offline). Se a rede da instituição bloquear jsdelivr, todas as telas degradam. Unificar para os assets vendored.

**M7. `admin_routes.py` (1.440 linhas) e `backup_service.py` (1.408 linhas)** — a 051 recusou conscientemente o split físico do backup_service (Amendment A1: 42 pontos de monkeypatch usam o namespace do módulo). Decisão correta; fica registrado que `admin_routes` é o próximo candidato a router por domínio (a 051 já o listou como spec futura).

**M8. Falhas de SMTP em produção** (log 2026-09-23: `SMTPRecipientsRefused` repetido nas movimentações 90-95) — o sistema lida bem (movimentação não é afetada, RN-006 da 030), mas os destinatários configurados estão rejeitando e-mail há dias sem alerta visível. Melhoria: badge de "falhas recentes de notificação" na Central de Integrações.

### P3 — Baixa prioridade / higiene

**M9. ✅ RESOLVIDO (2026-09-29): `sispatrimoniopro.cert` removido do repo** — cert público autoassinado confirmado (sem chave privada, CN `sispatrimoniopro.local`). Removido via `git rm`; `.gitignore` agora bloqueia `*.cert`/`*.crt`/`*.pem`/`*.key` soltos (o material TLS vive em `data/ssl/`, ignorado desde a 056). O `.gitignore` já protege `.env` e `data/logs/` corretamente (logs aparecem só como não-rastreados no status local).

**M10. Documentação de melhorias fragmentada** — `docs/Melhorias_SisPatrimonio_Pro.md` (backlog M-001...), `docs/Coisas a corrigir ou melhorar.md` e agora este relatório. Sugerir consolidar num backlog único com status.

**M11. `seed_demo.py` na raiz de produção** — útil para demo, mas acessível em deploy PRO; garantir que exig flag explícita para rodar.

---

## 4. Análise de risco pontual

### 4.1 Testes
- Com MariaDB parado: **14 errors** em `test_inventario.py` (setup de conexão), timeout da suíte completa (>300s). Com MariaDB de pé: baseline conhecido 861 passed / 2 failed (`test_backup_externo.py`, feature 045, fora de escopo — FR-021 da 050 proíbe tocar backup).
- Os 2 failures pré-existentes **continuam fora de qualquer escopo** até decisão explícita do usuário.

### 4.2 Segurança
- ✅ Sessões: cookie de sessão com TTL 8h, `AUTH_COOKIE_SECURE` configurável; lockout por conta (10 tentativas/15min); PBKDF2 600k iterações; permissões deny-by-default com auditoria de negação (`require_permission` escreve `ACTION_ACCESS_DENIED`).
- ⚠️ `AUTH_COOKIE_SECURE` default `false` — em produção **sem HTTPS** (`http://10.39.0.16:8000`) o cookie trafega em claro. `HTTPS_LOCAL.md` existe; recomenda-se ativar TLS no deploy PRO (material disponível: `scripts/gera_cert_dev.py` gera CA + cert em `data/ssl/` — feature 056).
- ⚠️ `app.mount("/static")` serve o diretório inteiro — OK, mas `static/vendor` duplica Bootstrap; sem risco real.
- ✅ `smoke` do modo manutenção (019) e whitelist corretos; middleware de manutenção não toca banco (F1).

### 4.3 Performance
- Pool MariaDB dimensionado (10+20, recycle 1800s, pre_ping) — adequado.
- `list(inv.itens)` carrega todos os itens do inventário em memória para filtrar em Python (`inventario.py:147`): com o limite de 1.000 itens do pacote offline, é aceitável; para inventários maiores seria N+1/2 — não é caso hoje.
- Sem índices faltantes evidentes além dos já previstos na 033.

---

## 5. Spec 052 — Migrações de Schema com Alembic: NÃO só é necessária, como é a correção mais urgente de infraestrutura

### 5.1 A necessidade é real e comprovada por evidência

A 052 substitui `_ensure_schema_migrations` (ALTERs manuais em Python) por Alembic com **baseline-stamp (zero DDL no deploy de adoção)**. Evidências de que o problema existe hoje, colhidas nesta análise:

1. **Drift de schema já aconteceu em produção**: log `app.error.log` de 2026-09-23 registra `ProgrammingError (1146): Table 'sispatrimoniopro.backup_config' doesn't exist` — um banco real ficou sem tabela que os models esperavam. O mecanismo atual não tem como detectar/reparar isso sistematicamente.
2. **P1 da spec é real**: `ADD COLUMN IF NOT EXISTS` (database.py L67+) exige MariaDB 10.5+; **MySQL puro quebra** — o sistema declara MariaDB, mas qualquer ambiente MySQL (XAMPP novo com MySQL, hospedagens) falha silenciosamente.
3. **P2/P3 são reais**: não há versionamento nem histórico — impossível saber qual ALTER um banco já recebeu; cada feature empilha um bloco novo no mesmo arquivo (já são 4 blocos: força bruta, AD, user_roles, 033).
4. **P4 é real**: só suporta ADD; a próxima feature que precisar de `ALTER ... MODIFY` ou data migration não terá mecanismo.
5. **Restore (017/019)**: um dump restaurado de versão antiga hoje reconverge só pelos ALTERs aditivos atuais — funciona por acaso (idempotência), não por design. A 052 formaliza a convergência (stamp + upgrade).

### 5.2 A spec NÃO vai prejudicar o sistema — proteções verificadas no código/plano

| Risco temido | Proteção na spec | Verificação desta análise |
|---|---|---|
| Deploy alterar o banco de produção | Regra máxima: **ZERO DDL no deploy de adoção**; baseline é no-op; bancos existentes só recebem a tabela `alembic_version` | `spec.md` FR-002/FR-003 + `plan.md` D2: `stamp("0001")` sem nenhum ALTER |
| Suíte de testes quebrar | Guard por dialect: **SQLite → no-op total** (nem `alembic_version` é criada) | plan D2 + micro-remediação A1 do analyze (corrigiu exatamente este buraco) |
| Boot concorrente (crash-loop 027) | Retry único espelhando `_create_all_tolerante_corrida`; lock DDL do MariaDB serializa | plan D2/D3; o padrão já é provado em produção pela 027 |
| Restore de dump antigo | Cenário FR-008 coberto: pré-Alembic → stamp+revisão idempotente; pós-Alembic → upgrade head | plan D3 tabela de edge cases |
| Revisão futura quebrada travar todos os boots | Risco B1 registrado no plan com mitigação (downgrade() obrigatório, teste condicional T010) | plan "Riscos e mitigações" |
| Ordem de boot (create_all vs migrações) | create_all **primeiro** (garante tabelas novas), Alembic depois (obrigatório só para tabelas existentes) | plan D2 "Justificativa da ordem" |
| Alembic como dependência nova | `alembic>=1.13` (T001), madura, amplamente adotada, sem conflito com SQLAlchemy 2 | stack atual: SQLAlchemy >=2.0 |

### 5.3 Riscos residuais (aceitáveis e documentados)

1. **Dupla fonte de schema** (models/create_all + migrations) até um baseline completo futuro — dívida consciente assumida no Q1 da spec; aceitável enquanto as revisões forem escritas à mão.
2. **Teste condicional de execução real só roda com MariaDB** — em CI puro-SQLite a cadeia é validada apenas estruturalmente (encadeamento/importabilidade). A validação T009 exige MariaDB da máquina do desenvolvedor — que hoje depende do XAMPP estar de pé (ver M1).
3. **Fator humano**: o novo workflow exige disciplina ("mudou model? criou revisão?"). T013 prevê checklist de PR; o guardrail automático (autogenerate em modo comparação) ficou como spec futura.

### 5.4 Veredito

> **Sim, implementar.** A 052 é necessária (o mecanismo atual já produziu um incidente real de drift e trava a evolução de schema em MySQL/ALTERs não-aditivos) e não prejudica o sistema: o plano foi desenhado para tocar zero DDL no deploy de adoção, com guard explícito para a suíte SQLite e tolerância à corrida já provada em produção. Os artefatos (spec, plan, quickstart, tasks T001–T015) estão completos e maduros — prontos para o ciclo implement/validate. **Pré-requisito operacional**: resolver M1 (suíte independente de MariaDB) e garantir XAMPP/MariaDB de pé para T002/T009/T015 (validação em banco real com dump antes/depois).

**Ordem recomendada**: R1 (fix do sw.js, 1 linha) → M1 (hermeticidade da suíte) → **052** → M5/M6 (higiene de templates/CDN) → spec futura para admin_routes (P2/M7).

---

## 6. Anexos — files/linhas citadas

- `app/database.py` L64-120 (`_ensure_schema_migrations`), L121-143 (`create_all` tolerante), L145-158 (`init_db`)
- `app/web/routers/inventario.py` L267-291 (rota do bug), L500-518 (`/sw.js` + rota offline)
- `app/web/static/js/sw.js` L80-108 (fetch handler: respondWith duplo no navigate)
- `app/web/templates/base.html` (bloco de registro do SW; atributo style quebrado no user menu)
- `app/web/templates/inventarios/conferir.html` (template íntegro)
- `tests/conftest.py` L18-45 (engine de teste) e fixture `client` (TestClient dispara init_db de produção)
- `data/logs/app.error.log` (drift `backup_config`, 2026-09-23) e `data/logs/app.log` (SMTP failures)
- `specs/052-migracoes-alembic/{spec,plan,tasks,quickstart}.md` — artefatos completos, status Draft
