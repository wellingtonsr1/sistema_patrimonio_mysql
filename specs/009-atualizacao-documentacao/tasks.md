# Tasks: Atualização da Ajuda/Manual e do README.md (feature 009)

**Input**: Design documents from `/specs/009-atualizacao-documentacao/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ (D1–D4) · data-model.md ✅ · contracts/ — não aplicável (research D4) · quickstart.md ✅

**Tests**: **Sem testes novos** — decisão registrada no plan (§Testing Strategy): a feature não altera comportamento, portanto não há o que testar além da não-regressão; a validação é a suíte existente no patamar atual (281 passed / 1 failed conhecido), `tests/test_help.py` 100% verde, renderização no navegador e escopo fechado por `git status` (Constitution VIII/XII). Nenhum teste existente é editado.

**Organization**: Tasks agrupadas por user story. Feature documental: **nenhuma task cria código, testes, templates, permissões ou configuração**; os únicos arquivos alteráveis são `app/services/help_service.py` (conteúdo textual das listas `ARTICLES`/`FAQ`/`CATEGORIES` — sem lógica/estrutura) e `README.md` (FR-012/SC-006).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Carregar contexto e estabelecer a baseline de não-regressão antes de qualquer edição

- [x] T001 Ler os artefatos da feature (spec.md, plan.md §Implementation Flow, research.md D1–D3, data-model.md, quickstart.md) e os arquivos-alvo: `app/services/help_service.py` (estruturas `ARTICLES` ~L33–L789, `FAQ`, `CATEGORIES` — apenas conteúdo), `README.md` (raiz), e as fontes de verdade citadas no research D2/D3: `app/config.py`, `run.py`, `app/database.py` (`init_db`), `app/cli.py` (`create-user`), rota `/setup` e `GET /assets/labels` em `app/web/routes.py`
- [x] T002 Executar a baseline de não-regressão e registrar em Validation Results: `python -m pytest tests/ -q --tb=no` (patamar de referência desta sessão: **281 passed / 1 failed** — lockout defasado conhecido) e `python -m pytest tests/test_help.py -q` (100% verde) — nenhuma linha editada antes do baseline

**Checkpoint**: Contexto carregado e baseline registrada — nenhum arquivo alterado ainda.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verificar, em código real, os fatos que a documentação afirmará (gates de leitura — PROIBIDO editar nesta fase)

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase

- [x] T003 Verificar (somente leitura) e registrar em Validation Results: (a) as divergências D2 continuam atuais — `README.md` cita "154 testes" (L23/seção 🧪), `APP_HOST=127.0.0.1` (L134), tabela de endpoints SEM `GET /api/v1/reports/locations/csv`, funcionalidades SEM pesquisas 006/007, exportação de locais 008 e Etiquetas em lote `/assets/labels` (rota real em `app/web/routes.py` ~L370); (b) estado real da ajuda — contagem de artigos/FAQ/categorias de `app/services/help_service.py` (referência da análise: 21/12/7), artigo `exportar-csv` sem menção a locais, seções 007/006 em `cadastrar-locais`/`cadastrar-colaboradores` presentes e coerentes; (c) `tests/test_help.py` não fixa contagens de artigos/FAQ (nenhum conflito esperado); (d) localizar no código o `PERMISSION_CATALOG` real (fonte exata em `app/services/`) para a conferência do catálogo no README; (e) caminhos reais do futuro guia: `run.py` chama `init_db()`, `app/config.py` exige `DATABASE_URL` (raise se ausente), 3 caminhos de primeiro admin (env `AUTH_ADMIN_USERNAME`/`AUTH_ADMIN_PASSWORD`, tela `/setup`, CLI `python -m app.cli create-user --admin`). Qualquer divergência em relação ao plan → PARAR e reportar antes de seguir

**Checkpoint**: Fatos confirmados — user stories liberadas.

---

## Phase 3: User Story 1 - Ajuda/Manual reflete as funcionalidades reais (Priority: P1) 🎯 MVP

**Goal**: A central de ajuda (`/ajuda`) descreve as telas, botões, filtros e permissões reais — incluindo 006, 007 e 008 — sem instrução contraditória (SC-001/SC-002).

**Independent Test**: Percorrer os artigos da `/ajuda` e comparar com as telas reais; nenhum passo descreve fluxo inexistente e as funcionalidades 006/007/008 estão cobertas (quickstart §3).

### Implementation for User Story 1 (edits are surgical — same file, sequential)

> **NOTE**: Ajustes cirúrgicos por `str_replace`, preservando tom, formato das seções (`heading`/`steps`/`body`/`note`), `keywords`, `audience` e a estrutura das listas — nada de lógica, chaves novas de estrutura, `id`s alterados ou artigos renomeados (FR-011/data-model).

- [x] T004 [US1] Atualizar o artigo `exportar-csv` em `app/services/help_service.py`: acrescentar a exportação de locais (feature 008) — botão "Exportar CSV" no cabeçalho da tela de Locais, download direto de `locais.csv`, conjunto completo de locais, sem colunas de interface ("Ações"/"Bens"), permissão `relatorios.exportar` — e ajustar `summary`/`keywords` para incluir "locais" (FR-002); Colaboradores, Dashboard e Movimentações permanecem citados
- [x] T005 [US1] Validar/ajustar o artigo `cadastrar-locais` em `app/services/help_service.py` contra a tela real: pesquisa de locais (007) — campo único por **Nome / Identificação**, par Filtrar (com ícone)/Limpar (só texto), correspondência parcial e case-insensitive, mensagem exata "Nenhum local encontrado." — e exportação (008) coerente com o texto do artigo `exportar-csv` (FR-003); ajuste SOMENTE se a revisão evidenciar divergência
- [x] T006 [US1] Validar/ajustar o artigo `cadastrar-colaboradores` em `app/services/help_service.py` contra o comportamento real da pesquisa (006): termo único correspondendo a matrícula, nome, cargo, departamento ou e-mail, correspondência parcial e case-insensitive (FR-004); ajuste SOMENTE se a revisão evidenciar divergência
- [x] T007 [US1] Varredura guarda-chuva (SC-001) dos demais 18 artigos + `FAQ` em `app/services/help_service.py` contra as telas reais: corrigir APENAS instruções contraditórias com o funcionamento atual; permissões/telas reservadas (ex.: `movimentacao.cancelar`) permanecem marcadas como reservadas (FR-008); registrar cada achado (ou "nenhum") em Validation Results — sem reescrita gratuita de conteúdo já correto (edge case da spec)
- [x] T008 [US1] Validar US1: `python -m pytest tests/test_help.py -q` 100% verde (não-regressão do mecanismo — FR-011) + renderização no navegador dos artigos alterados via `/ajuda` (estrutura, formatação, pesquisa client-side e tooltips como antes — cenários 3.1–3.4 do quickstart); registrar em Validation Results

**Checkpoint**: US1 (MVP) completa — a ajuda reflete o sistema; PARAR E VALIDAR antes de US2/US3.

---

## Phase 4: User Story 2 - README.md reflete o estado real do projeto (Priority: P2)

**Goal**: Zero afirmação factual contraditória com o código (contagens, padrões, endpoints, permissões, funcionalidades) — SC-004.

**Independent Test**: Verificar cada afirmação factual do README contra a fonte correspondente (`app/config.py`, rotas, catálogo de permissões, `pytest`) — nenhuma contradição permanece (quickstart §4.1–4.3/4.6).

### Implementation for User Story 2 (same file, sequential)

- [x] T009 [US2] Correções factuais cirúrgicas em `README.md`: (a) contagem de testes — substituir "154 testes... 153 passando e 1 falhando" pelo quantitativo verificado nesta revisão (**282 testes; 281 passed / 1 failed — lockout defasado conhecido**) acompanhado de instrução de como obter o número atual com `pytest` (edge case anti-envelhecimento da spec); (b) padrões reais `APP_HOST`/`APP_PORT` conforme `app/config.py` (192.168.0.9 / 8000) no lugar de 127.0.0.1; (c) tabela de endpoints protegidos — acrescentar `GET /api/v1/reports/locations/csv` → `relatorios.exportar`; (d) catálogo de permissões conferido linha a linha contra o `PERMISSION_CATALOG` real localizado em T003d, com reservadas mantidas marcadas como tal
- [x] T010 [US2] Seção "Principais Funcionalidades" de `README.md`: acrescentar exportação CSV de locais (008), pesquisa de colaboradores (006), pesquisa de locais (007) e Etiquetas em lote (`/assets/labels`) — nada inexistente listado (FR-008/FR-010); conferir que a CLI (`create-user`, `reset-password`, `stats`, `list`, `show`, `move`) já está documentada (research D2 #7: `reset-password` já citado ~L588) e ajustar apenas se faltar algo; atualizar a seção "Central de Ajuda e Manual" apenas se citar contagens alteradas; acrescentar link para a nova seção de instalação (US3) em "Como Executar o Sistema"
- [x] T011 [US2] Validar US2 (quickstart §4.1–4.3 e §4.6): conferência cruzada leitura/grep de cada afirmação editada contra `app/config.py`, `app/web/routes.py`, `app/api/reports_api.py`, catálogo de permissões e saída do `pytest`; registrar resultado em Validation Results

**Checkpoint**: US1 + US2 funcionando — README sem contradições factuais.

---

## Phase 5: User Story 3 - Guia único de instalação em máquina nova (Priority: P3)

**Goal**: Seção "Instalação em uma máquina nova" no README cobrindo os 11 pontos (FR-006/SC-003) sobre a configuração REAL (research D3), sem comando inventado e sem credencial real.

**Independent Test**: Seguir o guia do zero em máquina limpa executando apenas os comandos documentados; sistema sobe, banco estruturado automaticamente, admin criado e login efetuado (quickstart §4.4–4.5).

### Implementation for User Story 3 (same file, sequential)

- [x] T012 [US3] Criar a seção "Instalação em uma máquina nova" em `README.md`, cobrindo os 11 pontos do FR-006 sobre a configuração real (research D3): 1) pré-requisitos (SO, Python 3.10+, Git, MariaDB/MySQL); 2) obtenção do projeto; 3) ambiente virtual com variantes Linux/Windows (edge case da spec); 4) `pip install -r requirements.txt`; 5) instalação/inicialização do MariaDB (variantes do ambiente real); 6) criação de banco/usuário/permissões (SQL de exemplo); 7) criação manual do `.env` — `DATABASE_URL` obrigatória (`mariadb+pymysql://usuario:senha@host:3306/banco`), **não existe `.env.example` no repositório** (guiar a criação manual, sem inventar arquivo), menção às `AD_*` para quem integrar AD (FR-007); 8) estrutura do banco criada automaticamente pelo `init_db()` no `python run.py` — **PROIBIDO inventar comando de migração**; 9) primeiro administrador pelos 3 caminhos reais (env `AUTH_ADMIN_USERNAME`/`AUTH_ADMIN_PASSWORD` no primeiro start; tela `/setup` quando não há usuários; CLI `python -m app.cli create-user --username ... --password ... --name ... --admin`); 10) inicialização e primeiro acesso (host/porta de `APP_HOST`/`APP_PORT`; Swagger `/docs`); 11) validação da instalação (health público `/health`, acesso web, suíte `pytest`) + diagnóstico dos problemas comuns (`DATABASE_URL` ausente, banco inacessível) — zero credenciais/senhas/IPs reais de produção, exemplos com placeholders fictícios (FR-015)
- [x] T013 [US3] Validar US3: revisão da seção contra o quickstart §4.4 (11 pontos presentes, sem comando inventado, 3 caminhos de admin, placeholders fictícios) e revisão anti-credencial dedicada (FR-015) — nenhuma senha/IP/credencial real no texto; quando possível, execução real do guia em ambiente limpo (§4.5) pelo operador; registrar em Validation Results

**Checkpoint**: Todas as user stories funcionando.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validação final de não-regressão, revisão manual e fechamento de escopo (Constitution VIII/XI/XII)

- [x] T014 Executar a suíte completa final: `python -m pytest tests/ -q --tb=no` → patamar idêntico à baseline (281 passed / 1 failed conhecido; nenhum teste novo, nenhum editado) e `python -m pytest tests/test_help.py -q` verde — registrar números exatos em Validation Results
- [x] T015 Validação manual pelo operador conforme quickstart: §3 (navegador — artigos alterados na `/ajuda`, pesquisa da central, cenários 3.1–3.6 incluindo ausência de credenciais) e §4.1–4.6 (README vs código; §4.5 instalação em ambiente limpo quando possível); registrar resultado e data em Validation Results
- [x] T016 Fechamento: checklist Constitution (plan §Constitution Check), `git status --porcelain` com escopo FECHADO — somente `app/services/help_service.py`, `README.md` e artefatos de `specs/009-atualizacao-documentacao/` (nenhum código, teste, template, config ou doc de `docs/` alterados) —, registro das fontes verificadas para rastreabilidade (FR-014: `app/config.py`, `run.py`, `app/database.py`, `app/cli.py`, rotas web/API, `PERMISSION_CATALOG`, saídas pytest) e síntese dos Success Criteria (SC-001..SC-006) em Validation Results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato, sem dependências
- **Foundational (T003)**: depende do Setup; BLOQUEIA todas as user stories (gate de fatos — qualquer divergência ⇒ PARAR)
- **US1 (T004–T008)**: após T003 — todos os edits no MESMO arquivo (`help_service.py`), portanto estritamente sequenciais
- **US2 (T009–T011)**: após US1 completa (T008) — arquivo distinto (`README.md`), mas seguem a ordem do plan (ajuda → README); independente da US1 em conteúdo
- **US3 (T012–T013)**: após US2 (T011) — o guia reutiliza os valores já corrigidos/citados no README (contagem, host/porta) e é o maior acréscimo
- **Polish (T014–T016)**: após todas as stories

### Within Each User Story

- Edits cirúrgicos no mesmo arquivo — **sem paralelismo intra-story** (risco de conflito de `str_replace`)
- Artigos/seções existentes antes dos novos acréscimos (T009 antes de T010; T010 (link) antes de T012)
- Story completa (checkpoint validado) antes de avançar para a próxima prioridade

### Parallel Opportunities

- **Nenhuma task `[P]`**: US1 e US2-to-US3 compartilham respectivamente um único arquivo por story (`help_service.py`; `README.md`) e a ordem do plan é sequencial
- T015 (validação manual do operador) pode ocorrer em paralelo com o fechamento administrativo T016, desde que T014 já tenha corrido verde

## Parallel Example: User Story 1

```bash
# Sequência estrita (mesmo arquivo, edits cirúrgicos sobrepostos):
T004 (exportar-csv) → T005 (cadastrar-locais) → T006 (cadastrar-colaboradores) → T007 (varredura) → T008 (validação US1)
# Sem [P]: todas as tasks tocam app/services/help_service.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fases 1–2 (Setup + Foundational): T001–T003
2. US1 completa: T004–T008 (ajuda fiel, incl. 006/007/008)
3. **STOP and VALIDATE**: `test_help.py` verde + renderização dos artigos no navegador
4. MVP entregável: manual do usuário final alinhado ao sistema

### Incremental Delivery

1. Setup + Foundational → fatos verificados
2. US1 → ajuda fiel (P1)
3. US2 → README sem contradições factuais (P2)
4. US3 → guia de instalação completo em máquina nova (P3)
5. Polish → suíte final, validação manual do operador, fechamento de escopo

---

## Notes

- Feature documental: **nenhum arquivo além de `app/services/help_service.py` (conteúdo) e `README.md`** pode ser alterado (FR-012/SC-006); `docs/*.md` e specs ficam FORA do escopo
- `help_service.py` é editado SOMENTE em conteúdo textual das listas `ARTICLES`/`FAQ`/`CATEGORIES` — nenhuma lógica, estrutura, rota ou comportamento (FR-011)
- Sem testes novos e sem edição de testes existentes (plan §Testing Strategy; Constitution VIII)
- Nenhuma credencial/senha/IP real nos textos; reservadas permanecem marcadas (FR-008/FR-015)
- Comportamento real vence documento: divergência nova encontrada → corrigir na documentação e registrar, nunca no código
- Commit after each task or logical group — somente se o usuário solicitar
- Stop at any checkpoint to validate story independently

---

## Validation Results

> Preenchido durante a execução (T002, T003, T008, T011, T013, T014, T015, T016). Não marcar antecipadamente.

### Baseline (T002)

- `python -m pytest tests/ -q --tb=no` → **281 passed / 1 failed** (lockout defasado conhecido — `test_lockout_after_failed_attempts`); `python -m pytest tests/test_help.py -q` → **9 passed**. Nenhuma linha editada antes do baseline.

### Fatos verificados (T003)

- Divergências D2 confirmadas atuais: README cita "154 testes" (L5 e L644), `APP_HOST=127.0.0.1` (L134), tabela de endpoints sem `GET /api/v1/reports/locations/csv`, funcionalidades sem pesquisas 006/007, exportação de locais e Etiquetas em lote; rota real `/assets/labels` em `app/web/routes.py` L370 (gate `patrimonio.visualizar`).
- Ajuda: **21 artigos / 12 FAQ / 7 categorias** (execução Python de `help_service`); `tests/test_help.py` não fixa contagens (grep: nenhum `len(ARTICLES)`/`== 21`).
- `PERMISSION_CATALOG` localizado em `app/services/permission_service.py` L30 — 33 permissões em 10 módulos; `movimentacao.cancelar` descrita "(reservado)" e sem uso em rotas/services (grep: 0 ocorrências) → reservada.
- Caminhos do guia confirmados: `run.py` chama `init_db()` antes do uvicorn; `app/config.py` faz raise sem `DATABASE_URL`; 3 caminhos de primeiro admin (env `AUTH_ADMIN_*`, tela `/setup` em `routes.py` L1606/L1620, CLI `create-user`/`reset-password` em `app/cli.py`).
- **Divergência plan vs workspace (registrada)**: `app/config.py` atual tem `APP_HOST` padrão **10.39.0.16** (não 192.168.0.9 do research) — alteração local não commitada, pré-existente a esta feature (confirmação: `git diff app/config.py` muda apenas esse padrão; o arquivo já constava modificado no início da sessão). Aplicada a regra da spec (código atual vence) e a restrição FR-015 (nenhum IP real no README): o texto cita o **mecanismo** (`APP_HOST`/`APP_PORT` configuráveis; padrões vivos em `app/config.py`) sem fixar valor de rede no documento.

### Validação US1 (T008)

- `tests/test_help.py` → **9 passed** após os edits (não-regressão do mecanismo — FR-011); estrutura intacta: 21 artigos / 12 FAQ / 7 categorias; arquivo verificado como UTF-8 íntegro.
- Conteúdo: artigo `exportar-csv` cobre os 4 botões de tela (Colaboradores, Dashboard, Movimentações, **Locais**/`locais.csv`) + permissão; rótulos conferidos nos templates: "Exportar CSV" (4 telas), "Baixar CSV" (3 relatórios), "Concluir Tombamento", "Novo Equipamento", "Importar CSV", "Abrir Nova OS", "Cadastrar Colaborador", "Cadastrar Novo Local", "Alterar senha", "Etiquetas" — todos existentes.
- **Correções da varredura (T007)**: (1) artigo `finalizar-manutencao` dizia "Clique em Concluir", mas o botão real é "Finalizar Manutenção" (`maintenances/list.html` L110) — corrigido; (2) FAQ "Como exportar os dados?" não citava os botões de tela — complementado. Artigos `cadastrar-locais` (007+008) e `cadastrar-colaboradores` (006) conferidos contra as telas: conformes, nenhum ajuste necessário.
- Renderização visual no navegador: automatizada via `test_help.py`; percorrida visual fica para o operador (T015, cenários 3.1–3.6).

### Validação US2 (T011)

- Contagem: README agora cita **282 testes (281 passed / 1 failed)** + instrução `pytest -q` para o número atual — igual à execução real desta sessão.
- `APP_HOST`/`APP_PORT`: texto cita o mecanismo e remete a `app/config.py` (ver nota da divergência em T003).
- Tabela de endpoints: linha de exportações agora inclui `GET /api/v1/reports/locations/csv` → `relatorios.exportar` (endpoint real em `app/api/reports_api.py` L230).
- Catálogo de permissões conferido item a item contra `PERMISSION_CATALOG`: **idêntico** (10 módulos, 33 permissões); nota acrescentada marcando `movimentacao.cancelar` como reservada (FR-008).
- Funcionalidades acrescentadas: pesquisa de colaboradores (006), pesquisa de locais + exportação CSV de locais (007/008), Etiquetas em lote (`/assets/labels`), botão Exportar CSV nas 4 telas; CLI já documentada por completo (stats/list/show/move/create-user/reset-password — nada a acrescentar, research D2 #7).

### Validação US3 (T013)

- Seção "Instalação em uma máquina nova" criada com os **11 pontos** (pré-requisitos → obtenção → venv Linux/Windows → dependências → MariaDB → banco/usuário/permissões → `.env` → `init_db` automático → 3 caminhos de admin → iniciar/acessar → validação + problemas comuns).
- Sem comando de migração inventado (grep `alembic|flask-migrate|python manage` = 0); `.env.example` não inventado (guia orienta criação manual, como no repo real); 3 caminhos de admin documentados com exemplos.
- Revisão anti-credencial (FR-015): somente placeholders fictícios (`SenhaForte@123`, usuário `sispat`, banco `sispatrimonio`, `localhost`); **nenhum IP/senha/credencial real** no texto — o padrão de rede do `config.py` não foi copiado para o documento (nota T003).
- Execução real do guia em máquina limpa (quickstart §4.5): condicionada à disponibilidade de ambiente — a executar pelo operador quando possível.

### Suíte completa (T014)

- Execução final: **281 passed / 1 failed** — patamar idêntico à baseline (a única falha é o lockout defasado pré-existente); `test_help.py` **9 passed**. Nenhum teste novo criado e nenhum teste existente editado (plan §Testing Strategy).

### Validação manual (T015)

- **2026-09-17 — EXECUTADA** (com participação do operador, que abriu o servidor): servidor de produção **`10.39.0.16:8000` saudável** — `/health` respondeu `{"status":"healthy","database":"ok"}` e `/ajuda` sem sessão redireciona 303 → `/login` (proteção confirmada no ar). Como a ajuda exige login, a percorrida dos artigos foi executada contra o **mesmo pipeline de renderização da aplicação** (TestClient + SQLite em memória, a mesma infraestrutura da suíte), com **20/20 verificações aprovadas**: cenários 3.1 (artigo `exportar-csv`: botão, 4 telas, `locais.csv`, permissão, download no cabeçalho), 3.2 (`cadastrar-locais`: Nome / Identificação, Filtrar/Limpar, parcial/case-insensitive, seção de exportação), 3.3 (`cadastrar-colaboradores`: 5 campos, parcial/case-insensitive), 3.4 (termos "locais.csv" e "exportar" presentes no índice da pesquisa da central), 3.5 (`finalizar-manutencao` com o rótulo real, sem "Clique em Concluir"; os 4 artigos renderizam 200 com o layout padrão "Voltar à Central de Ajuda") e 3.6 (nenhuma credencial/valor de rede real nas páginas).
- Quickstart §4 (README vs código) verificado por grep/leitura: 4.1 contagem (282; 281/1 — igual às execuções desta sessão) · 4.2 `APP_HOST`/`APP_PORT` citados via mecanismo com remissão a `app/config.py` (sem IP fixo no texto) · 4.3 `reports/locations/csv` na tabela (1 ocorrência) · 4.4 seção de instalação presente com os 11 pontos · 4.6 funcionalidades 006/007/008 e Etiquetas em lote listadas.
- Falhas encontradas: **nenhuma**. Único item condicional remanescente: §4.5 (execução do guia de instalação em **máquina/ambiente limpo**) — marcado no quickstart como "quando possível"; fica a critério do operador, pois exige um ambiente novo dedicado.

### Validação manual (T015) — ADENDO 2026-09-17 (revisão do operador)

- **Achado do operador na revisão visual da central**: o módulo **Inventários** (presente no menu do sistema, gate `inventario.visualizar`) não tinha NENHUM artigo/carta na ajuda — lacuna de cobertura não detectada na análise da 009 (o Dashboard em si está coberto no artigo "Conhecendo a interface"). Enquadra-se no guarda-chuva do SC-001/FR-010 ("nenhuma funcionalidade existente relevante sem cobertura") e foi corrigida na documentação (código intocado):
  - **2 artigos novos** em `app/services/help_service.py`: `inventarios-overview` (o que é, ciclo de vida `PLANEJADO → EM_ANDAMENTO → ENCERRADO`, resultados `PENDENTE/ENCONTRADO/LOCAL_DIFERENTE/NAO_ENCONTRADO/SEM_IDENTIFICACAO`, "o inventário nunca altera o cadastro", 4 permissões) e `conferir-inventario` (Iniciar Inventário, conferência por bem/QR Code, resultado da conferência com os rótulos reais das telas — Encontrado/Local diferente/Não encontrado/Sem identificação —, re-conferência com confirmação, Registrar como não previsto, Encerrar Inventário e ata em CSV/Excel/PDF);
  - **Categoria nova "Inventários"** em `CATEGORIES` (card na central, entre Manutenções e Colaboradores & Locais);
  - **FAQ nova**: "Como o inventário é concluído?";
  - README: lista de módulos da ajuda atualizada (inventários incluído).
  - Rótulos verificados contra os templates reais (`inventarios/list.html`, `new.html`, `detail.html`, `conferir.html`) e rotas (`app/web/routes.py` L1760–L2131).
- Revalidação: estrutura da ajuda agora **23 artigos / 13 FAQ / 8 categorias**; `tests/test_help.py` **9/9** verde; renderização dos artigos novos via TestClient — **18/18 verificações aprovadas** (conteúdos, layout, card na central e FAQ); suíte completa estável em **281 passed / 1 failed** (mesma falha pré-existente); script temporário de validação removido. Escopo segue restrito a `help_service.py` + `README.md`.

### Validação manual (T015) — ADENDO 2, 2026-09-17 (artigo de Integração AD)

- **Artigo novo `integracao-active-directory`** (`audience="admin"`) criado em `app/services/help_service.py`, cobrindo a tela real Administração → Integração AD (`app/web/admin_routes.py` L633, guard `_ad_admin_guard`; template `admin/ad/settings.html`): ativação (Habilitar integração com Active Directory, Servidor AD, Porta 389/636, Usar LDAPS, Validar certificado TLS, Base DN, DN de busca de usuários, Testar Conexão, Salvar Configuração), mapeamentos Grupo AD → Perfil existente → Prioridade (Adicionar Mapeamento/Remover mapeamento), variáveis `AD_*` como fallback, primeiro login/provisionamento (vinculação por e-mail, dados patrimoniais preservados), mensagens de erro reais (perfil não autorizado, credencial inválida, conta desabilitada, AD indisponível, armadilha do DN de busca) e segurança (senha nunca armazenada/logada/auditada).
- Vínculos: categoria Administração passou a listar o artigo (4 artigos admin); FAQ de AD remete ao artigo. README: nota "incluindo a integração AD" na seção da ajuda.
- Revalidação: estrutura **24 artigos / 13 FAQ / 8 categorias**; `tests/test_help.py` **9/9**; renderização via TestClient **18/18** (conteúdo com os rótulos reais da tela, layout, card admin, e gate — usuário com perfil Consulta: artigo ausente da central e acesso direto **403**); suíte completa **281 passed / 1 failed** (mesma falha pré-existente). Escopo segue restrito a `help_service.py` + `README.md`.

### Fechamento (T016)

- `git status --porcelain` (excluindo `__pycache__`): **`README.md`** e **`app/services/help_service.py`** (escopo da feature), **`specs/009-atualizacao-documentacao/tasks.md`** (artefato) e **`app/config.py`** — alteração local **pré-existente** à feature (não modificada por esta execução; registrada em T003). Nenhum template, rota, teste, config ou doc de `docs/` alterado (SC-006 ✅ com a nota do config).
- Fontes verificadas (FR-014): `app/config.py`, `run.py`, `app/database.py`, `app/cli.py`, `app/web/routes.py` (incl. `/setup` L1606, `/assets/labels` L370), `app/api/reports_api.py` (L230), `app/services/permission_service.py` (L30), templates de assets/custodians/locations/movements/maintenances/reports/dashboard/base, `tests/test_help.py`, saídas pytest desta sessão.
- **Success Criteria**: SC-001 ✅ (varredura dos 21 artigos + FAQ: 2 contradições corrigidas, rótulos conferidos; leitura visual pendente apenas no T015) · SC-002 ✅ (006/007/008 na ajuda e no README) · SC-003 ✅ (11 pontos presentes e verificados contra config real; execução em máquina limpa condicionada ao operador) · SC-004 ✅ (zero contradições factuais: contagem, endpoints, catálogo, funcionalidades) · SC-005 ✅ (281/1 idêntico à baseline; `test_help.py` 9/9) · SC-006 ✅ (escopo restrito a `help_service.py` + `README.md` + artefato; nota sobre o `app/config.py` pré-existente).
