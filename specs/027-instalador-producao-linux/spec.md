# Feature Specification: Instalador Automatizado de Produção Linux do SisPatrimônio Pro

**Feature Branch**: `feature-027-instalador-producao-linux`

**Created**: 2026-09-19

**Status**: Draft

**Input**: Criar um instalador automatizado capaz de preparar um servidor Linux (Debian/Ubuntu) para executar o SisPatrimônio Pro em produção — Python, Git, MariaDB, clone do repositório, venv, dependências, `.env`, banco, serviço systemd, verificação pós-instalação — de forma idempotente, segura e interativa (com modo não interativo), respeitando integralmente a arquitetura existente do sistema.

## Regra fundamental

> **O instalador se adapta ao SisPatrimônio Pro atual. Nada no projeto é alterado para acomodar o instalador.** Esta spec define COMPORTAMENTO do instalador; a implementação (futura, via `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`) não deve alterar código Python da aplicação, `requirements.txt`, modelos, banco ou fluxo de execução existentes (Constitution I). A única área de mudança é a adição de artefatos de instalação (script e documentação), fora de `app/`.

## Realidade verificada (análise somente leitura — 2026-09-19)

*Analisado antes de escrever a spec; a implementação DEVE reconfirmar no código da época, não presumir.*

1. **Ponto de entrada**: `run.py` importa `APP_HOST`/`APP_PORT`/`APP_NAME` de `app/config.py`, chama `init_db()` (idempotente) + `configure_logging()` e executa `uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, reload=False)` — reload desativado, adequado a produção via systemd.
2. **Host/porta**: `APP_HOST` default **`192.168.0.9`** e `APP_PORT` default **`8000`** (`app/config.py:93–94`) — defaults específicos do operador; o `.env` gerado pelo instalador DEVE definir `APP_HOST=0.0.0.0` (ou o IP do servidor) explicitamente.
3. **Banco**: MariaDB/MySQL exclusivo. `DATABASE_URL` é **obrigatória**: `app/config.py` faz `raise RuntimeError` se ausente — a aplicação não inicia sem ela. Formato: `mariadb+pymysql://USUARIO:SENHA_URL_ENC@HOST:3306/BANCO` (driver PyMySQL, 100% Python — sem dependência C; senha com caracteres especiais precisa percent-encoding, documentado no README).
4. **Sem fallback SQLite** na aplicação (Constitution VII): SQLite é restrito à suíte de testes. **Ponto de atenção registrado**: `.gitignore` e `docs/ARQUITETURA_E_MANUTENCAO.md` ainda contêm referências históricas a `data/patrimonio.db`/SQLite — resquícios documentais, sem dependência operacional do instalador (não corrigir nesta feature).
5. **Criação do schema**: `init_db()` (chamado no `run.py` antes do uvicorn e no lifespan de `app/main.py`) faz `Base.metadata.create_all` + `_ensure_schema_migrations()` (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, MariaDB 10.5+) — **migração automática, idempotente e sem comando manual**. O instalador NÃO cria tabelas por conta própria; apenas garante banco/usuário/permissões e deixa `init_db()` trabalhar.
6. **MariaDB requerido pela aplicação além do serviço**: backup/restore usa o utilitário nativo `mysqldump` (PATH do processo ou `MYSQLDUMP_PATH` no `.env`) e o import usa o cliente nativo — instalar o pacote do servidor MariaDB já provê ambos.
7. **Primeiro administrador — 3 mecanismos reais** (todos preservados, instalador não cria usuário): (A) env `AUTH_ADMIN_USERNAME`/`AUTH_ADMIN_PASSWORD` no primeiro start (o lifespan `ensure_admin_user` cria se senha definida); (B) página `/setup` quando não há usuários e `AUTH_ADMIN_PASSWORD` não definida (protegida por singleton `setup_claims`); (C) CLI `python -m app.cli create-user --username ... --password ... --name ... --admin` (senha mín. 8; o CLI chama `init_db()` + `ensure_default_roles` por si).
8. **Saúde**: `GET /health` é público e real (`app/main.py`) — retorna JSON com `status` global (`healthy`/`degraded`), `application`, `database` (`ok`/`warning`) e `ad`. É o ponto de verificação pós-instalação; NÃO inventar outro endpoint.
9. **Execução como serviço**: o README já documenta o padrão systemd real: `Type=simple`, `After=network-online.target mariadb.service`, `WorkingDirectory` no diretório do projeto, `EnvironmentFile=<dir>/.env`, `ExecStart=<dir>/.venv/bin/python <dir>/run.py`, `Restart=on-failure`, `RestartSec=5`, `WantedBy=multi-user.target` — o instalador deve gerar a unit a partir desse padrão, com usuário/grupo dedicados (não root, não o usuário pessoal do operador).
10. **`.env` real**: `.env.example` existe (com `MYSQLDUMP_PATH`/`BACKUP_IMPORT_TIMEOUT` comentados) mas é mínimo; o `.env` é carregado por `python-dotenv` a partir do diretório do projeto (CWD) — e, para o systemd, também por `EnvironmentFile`. Arquivo versionado? **Não** — `.gitignore` bloqueia `.env`/`.env.*` (exceto `.env.example`).
11. **Dependências**: `requirements.txt` único e completo (FastAPI, Uvicorn[standard], SQLAlchemy, Pydantic, Jinja2, python-multipart, **pytest**, requests, ldap3, PyMySQL, python-dotenv, openpyxl, reportlab). Nenhuma dependência de compilação C é necessária (PyMySQL é puro) — venv basta; sem `apt build-dep`.
12. **Logs da aplicação**: `configure_logging()` grava em `data/logs/` (rotativo); backups em `data/backups/` — ambos fora do versionamento. O usuário do serviço precisa de permissão de escrita no diretório `data/` do projeto.
13. **Distribuições**: o README e o histórico do operador apontam Debian/Ubuntu/Pop!_OS (base Debian, `apt`, systemd). A spec adota **base Debian oficialmente suportada**; outras distribuições ficam fora do escopo (NFR-001).
14. **Divergências README × código encontradas**: `APP_HOST=127.0.0.1` citado em `docs/ARQUITETURA_E_MANUTENCAO.md:74` ≠ real (`192.168.0.9`); typos no README (`SisPratrimonioPro`/`sis_pratrimonio_pro` no exemplo systemd, serviço `sispatrimonio` vs `sispatrimoniopro` nos comandos). A spec considera o **código** como fonte de verdade e exige que o instalador seja consistente internamente (não herda os typos).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instalação limpa ponta a ponta (Priority: P1)

Um administrador de sistema, em um servidor Linux Debian/Ubuntu recém-instalado (ou sem o SisPatrimônio), executa o instalador (script único, a partir do clone ou baixado). O instalador verifica privilégios (sudo), detecta a distribuição, instala/verifica Python 3.10+, Git e MariaDB Server, cria banco e usuário dedicados com senha forte gerada ou informada (nunca exibida em claro além do necessário), clona o repositório oficial (`main`) para o diretório de instalação, cria o venv, instala `requirements.txt`, gera o `.env` (`DATABASE_URL`, `APP_HOST`, `APP_PORT`, secrets quando aplicável — permissões restritas ao dono), executa uma verificação de conexão com o banco, instala e habilita a unit systemd (usuário dedicado), inicia o serviço, aguarda a saúde da aplicação via `/health` e apresenta um resumo final (URL de acesso, `/docs`, `/health`, caminhos, como gerenciar o serviço, como criar o primeiro administrador pelos mecanismos reais). Nenhuma etapa destrutiva é executada sem confirmação explícita.

**Why this priority**: é o valor central da feature — servidor pronto sem seguir manualmente 10+ passos do README.

**Independent Test**: em máquina limpa de teste, executar o instalador e ao final validar: serviço ativo, `GET /health` respondendo `healthy`, `.env` com permissão 600, serviço rodando com usuário dedicado.

**Acceptance Scenarios**:

1. **Given** servidor Debian/Ubuntu sem os pré-requisitos, **When** o instalador roda até o fim, **Then** Python, Git e MariaDB estão instalados, o projeto clonado, o venv criado, dependências instaladas, banco/usuário criados, `.env` gerado, unit systemd habilitada e a aplicação responde em `/health`.
2. **Given** a instalação concluída, **When** o servidor reinicia, **Then** o serviço sobe automaticamente (WantedBy=multi-user.target + After/wants no MariaDB) e a aplicação responde novamente.
3. **Given** qualquer falha de etapa crítica (rede, clone, pip, banco), **When** o instalador encontra o erro, **Then** ele para imediatamente com mensagem clara (INFO/OK/WARNING/ERROR diferenciados), registra diagnóstico em arquivo de log sem credenciais e não deixa o serviço habilitado em estado quebrado (desabilita/só habilita após o health check passar).

---

### User Story 2 - Idempotência e reinstalação segura (Priority: P1)

O administrador executa o instalador novamente (mesma máquina, parcialmente instalada ou já instalada). Cada etapa detecta o estado atual e reutiliza o que já existe: Python/Git/MariaDB presentes são reutilizados (versão verificada); diretório existente é avaliado (clone válido → reutilizar/atualizar referência; diretório não-vazio estranho → abortar pedindo decisão); banco existente **nunca é apagado nem recriado** (reutiliza e apenas valida conexão); usuário do banco existente é reutilizado (senha só alterada se explicitamente solicitado, com confirmação); venv existente é reutilizado (reconstruído apenas se inválido); dependências verificadas; `.env` existente **nunca é sobrescrito silenciosamente** (oferece gerar `.env.instalador-novo` para comparação); unit systemd existente é atualizada somente se o conteúdo mudaria; a execução repetida termina em estado consistente sem perda de dados.

**Why this priority**: operador roda o script mais de uma vez (tentativa falha, verificação, migração de servidor); perda de dados ou efeitos destrutivos acidentais seriam graves (Constitution VII).

**Independent Test**: executar o instalador duas vezes seguidas em sucesso; conferir que a segunda execução não altera dados do banco, não sobrescreve `.env`, mantém o serviço funcional e reporta "já instalado/reutilizado" nas etapas.

**Acceptance Scenarios**:

1. **Given** instalação completa anterior, **When** o instalador roda novamente, **Then** todas as etapas reportam reutilização, o banco e o `.env` permanecem intactos e o serviço continua saudável.
2. **Given** banco já existente com dados, **When** o instalador passa pela etapa de banco, **Then** nenhuma operação `DROP`/`TRUNCATE`/recriação é executada; apenas validação de conexão e (se faltando) concessões mínimas de privilégio.
3. **Given** `.env` já existente, **When** o instalador encontra o arquivo, **Then** ele é preservado (backup com sufixo antes de qualquer modificação consentida) e o instalador oferta apenas completar chaves ausentes, nunca apagar/sobrescrever valores existentes sem confirmação explícita.

---

### User Story 3 - Modo não interativo (Priority: P2)

Operadores de automação executam o instalador com parâmetros (equivalente a `./install.sh --non-interactive`): diretório de instalação, repositório/branch, nome do banco, usuário do banco, senha do banco (ou flag para gerar senha forte e gravar apenas no `.env`), porta da aplicação, usuário/grupo Linux do serviço, e política de confirmação de operações destrutivas (por padrão, abortar em vez de confirmar interativamente). Parâmetros obrigatórios ausentes em modo não interativo causam falha clara listando o que falta; nenhum prompt é apresentado. Os mesmos passos e as mesmas garantias de segurança (sem segredo em log/argv visível quando evitável) se aplicam.

**Why this priority**: permite reprodutibilidade (máquinas de teste/homologação) sem desvalorizar o modo interativo (produção).

**Independent Test**: executar com todos os parâmetros em máquina limpa via `--non-interactive` e verificar instalação equivalente ao modo interativo; omitir um parâmetro obrigatório e verificar falha clara sem prompt.

**Acceptance Scenarios**:

1. **Given** todos os parâmetros fornecidos, **When** o instalador roda em modo não interativo, **Then** a instalação completa acontece sem nenhum prompt, com o mesmo resultado e verificações do modo interativo.
2. **Given** parâmetro obrigatório ausente (ex.: senha do banco não informada nem marcada como "gerar"), **When** o instalador valida a entrada, **Then** ele falha imediatamente listando os parâmetros ausentes, sem prompt nem parcialidade (nenhum passo executado antes da validação completa).

---

### User Story 4 - Segurança, logs e diagnóstico (Priority: P1)

Durante toda a execução, o instalador: exige sudo/root apenas para as etapas que precisam (verificação inicial de privilégios); nunca roda a aplicação como root (usuário/grupo dedicado); gera secrets/senhas de forma criptograficamente segura quando solicitado; **nunca** grava senha de banco, segredos ou tokens no log do instalador (nem em argv de comandos registrados); cria o `.env` com permissões restritas; concede ao usuário do banco apenas os privilégios necessários (banco específico, não globais); registra log completo em arquivo (INFO/OK/WARNING/ERROR) preservando stdout amigável; e ao falhar preserva o log para diagnóstico com a etapa exata e o erro, sem mensagem confusa ou sigilosa.

**Why this priority**: o instalador manipula credenciais e serviços de sistema — falhas aqui anulam o valor da feature.

**Independent Test**: executar instalação com senha gerada; inspecionar arquivo de log e stdout procurando a senha (não pode aparecer); conferir permissão do `.env` (600, dono = usuário do serviço ou root) e privilégios do usuário do banco (apenas no banco da aplicação).

**Acceptance Scenarios**:

1. **Given** uma instalação qualquer, **When** o log é inspecionado, **Then** nenhuma senha/segredo aparece (nem em comandos registrados), e as etapas INFO/OK/WARNING/ERROR são distinguíveis.
2. **Given** a criação do usuário do banco, **When** os privilégios são concedidos, **Then** o usuário tem privilégios apenas sobre o banco da aplicação (sem privilégios globais/administrativos).
3. **Given** falha em qualquer etapa, **When** o instalador aborta, **Then** o log indica a etapa, o erro técnico sem credenciais e a sugestão de correção/reexecução (idempotência permite retomar).

---

### User Story 5 - Verificação pós-instalação e resumo para o administrador (Priority: P2)

Após iniciar o serviço, o instalador executa uma bateria de verificações (Python/venv/dependências, MariaDB ativo, conexão com o banco, tabelas existentes via verificação real da aplicação, unit systemd ativa, HTTP `/health` respondendo com `status: healthy` ou `degraded` explicado) e apresenta o **resumo final**: URL da aplicação, `/docs`, `/health`, diretório de instalação, nome do serviço, comandos de gerenciamento (status/start/stop/restart/logs), localização do `.env` e do log do instalador, e instruções do primeiro administrador conforme os mecanismos reais (env `AUTH_ADMIN_*` no primeiro start, `/setup` ou CLI `create-user`), deixando claro que a senha do banco não aparece no resumo.

**Why this priority**: fecha o ciclo — administrador sabe que está funcionando e o que fazer a seguir.

**Independent Test**: após instalação bem-sucedida, executar as verificações manualmente e conferir que o resumo corresponde ao estado real (serviço ativo, health OK, caminhos corretos).

**Acceptance Scenarios**:

1. **Given** instalação concluída, **When** as verificações pós-instalação rodam, **Then** todas as checagens da lista mínima (Python, venv, dependências, MariaDB, conexão DB, tabelas, systemd, HTTP `/health`) passam ou o instalador reporta exatamente qual falhou.
2. **Given** o resumo final apresentado, **When** o administrador segue as instruções de primeiro acesso, **Then** consegue autenticar usando um dos três mecanismos reais sem consultar o código.
3. **Given** `/health` retornando `degraded` (ex.: AD configurado e indisponível), **When** o instalador avalia o health check, **Then** trata como avisado (WARNING com explicação) e não como falha da instalação (a aplicação em si está no ar).

---

## Requirements *(mandatory)*

### Funcionais

- **FR-001**: O instalador é um artefato novo de instalação (script executável no repositório, ex.: `install.sh` na raiz, com permissão de execução) que NÃO modifica código da aplicação, `requirements.txt`, modelos, banco, templates ou fluxo de execução existentes (Constitution I).
- **FR-002**: Antes de qualquer alteração, o instalador verifica: usuário com privilégios de administrador (sudo), distribuição Linux base Debian com systemd presente, conectividade necessária (repositório GitHub, repositórios de pacotes, porta do banco) — e aborta com mensagem clara em caso negativo.
- **FR-003**: O instalador verifica Python ≥ 3.10 (versão mínima do projeto); se ausente ou inferior, instala via gerenciador de pacotes da distribuição (sem compilar do código-fonte) e re-verifica; se a distribuição não provê versão suficiente, aborta com orientação (não adiciona repositórios de terceiros sem decisão explícita registrada).
- **FR-004**: O instalador verifica Git; instala quando ausente (requisito de clone).
- **FR-005**: O instalador verifica **MariaDB Server ou MySQL Server** (e os utilitários nativos `mysqldump`/cliente que acompanham o servidor — usados pelo backup/restore da aplicação); se **qualquer um** já existir, reutiliza e apenas valida o serviço (nunca desconfigura, reinicia de forma destrutiva ou sobrescreve); se **nenhum** existir, instala **MariaDB** (SGBD padrão desta feature) e garante o serviço ativo/habilitado.
- **FR-006**: O instalador cria o banco de dados da aplicação (charset `utf8mb4`, collation `utf8mb4_unicode_ci`) e um usuário dedicado com privilégios mínimos somente nesse banco, com senha informada ou gerada de forma segura; se banco e/ou usuário já existirem, reutiliza e apenas completa o que falta (concessões), **nunca apaga/recria** (regra de segurança do briefing §9).
- **FR-007**: O instalador testa a conexão real com o banco usando o driver do próprio projeto (via Python com o `DATABASE_URL` montado) antes de prosseguir para as etapas dependentes.
- **FR-008**: O instalador clona o repositório oficial (`main`) para o diretório de instalação configurável (default `/opt/SisPatrimonioPro`, alinhado ao README); diretório já existente com clone válido → reutilizar; não-vazio sem clone → abortar pedindo decisão; erro de rede/branch → mensagem específica.
- **FR-009**: O instalador cria o ambiente virtual dentro do diretório do projeto e instala `requirements.txt` a partir dele, validando a importação das dependências principais ao final (equivalente ao teste do README).
- **FR-010**: O instalador gera o `.env` no diretório do projeto com no mínimo: `DATABASE_URL` (senha percent-encoded corretamente, gerada pelo próprio instalador — nunca digitada manualmente), `APP_HOST` (default `0.0.0.0`, configurável) e `APP_PORT` (default `8000`), `MYSQLDUMP_PATH` quando o utilitário não estiver no PATH padrão do serviço, e chaves de segredo quando aplicável (ex.: `AUTH_ADMIN_PASSWORD` **somente** se o administrador escolher criar o admin por env, com senha gerada/definida no momento e não reexibida depois); permissões do arquivo restritas (0600); `.env` existente nunca sobrescrito sem confirmação e backup prévio.
- **FR-011**: A inicialização do schema fica a cargo do mecanismo existente (`init_db()` idempotente no start do serviço) — o instalador não cria tabelas, não roda SQL de schema e não implementa migração paralela.
- **FR-012**: O instalador cria um usuário/grupo Linux dedicado para o serviço (não root), concede propriedade do diretório de instalação a esse usuário e instala a unit systemd baseada no padrão real do README (`Type=simple`, `After=network-online.target mariadb.service`, `WorkingDirectory`, `EnvironmentFile`, `ExecStart` apontando para o python do venv e `run.py`, `Restart=on-failure`, `RestartSec=5`, `WantedBy=multi-user.target`), com nome de serviço configurável (default `sispatrimoniopro`) — consistente entre o nome do arquivo e os comandos enable/start. Quando o banco detectado for MySQL (D3), a dependência da unit usa o nome real do serviço detectado (ex.: `mysql.service` em vez de `mariadb.service`).
- **FR-013**: O instalador inicia o serviço, aguarda a aplicação responder em `/health` (com timeout e diagnóstico no log em caso de falha — incluindo trecho relevante do `journalctl` do serviço, sem segredos) e só então declara sucesso.
- **FR-014**: O instalador executa a bateria de verificação pós-instalação (Python, venv, dependências, MariaDB ativo, conexão DB, tabela base existente, unit ativa, HTTP `/health`) e apresenta resumo final com URL, `/docs`, `/health`, caminhos, comandos de gerenciamento do serviço e instruções do primeiro administrador (3 mecanismos reais), sem exibir a senha do banco.
- **FR-015**: O instalador suporta modo não interativo com parâmetros (equivalente a `--non-interactive`, `--install-dir`, `--db-name`, `--db-user`, `--db-password` | `--generate-db-password`, `--app-port`, `--repo`, `--branch`, `--service-name`, `--service-user`); parâmetro obrigatório ausente → falha imediata e clara, sem prompt e sem execução parcial. A flag `--recreate-db` (D2/FR-017) existe apenas no modo interativo — sua combinação com `--non-interactive` é rejeitada na validação inicial.
- **FR-016**: O instalador registra log completo da instalação em arquivo (fora do diretório versionado do projeto ou claramente identificado) com níveis INFO/OK/WARNING/ERROR e **nenhuma credencial** (senhas, segredos, tokens) — nem em mensagens, nem em comandos registrados.
- **FR-017**: Operações potencialmente destrutivas (ex.: sobrescrever `.env`, instalar pacote sobre serviço configurado, alterar senha de usuário de banco existente) exigem confirmação explícita no modo interativo; em modo não interativo, abortam por padrão. A única forma de recriar um banco existente é a flag dedicada `--recreate-db` (decisão D2), que exige **dupla confirmação interativa** (nome do banco digitado novamente) e é **proibida em `--non-interactive`** (combinação → falha imediata); a recriação afeta exclusivamente o banco da aplicação nomeado, nunca outros bancos.
- **FR-018**: O instalador pode ser executado novamente (idempotência de ponta a ponta): cada etapa detecta estado anterior e reutiliza conforme as regras de FR-005/FR-006/FR-008/FR-009/FR-010; execução repetida bem-sucedida não altera dados do banco nem configurações válidas existentes.
- **FR-019**: Em caso de falha, o instalador para na etapa, registra etapa+erro (sem credenciais) no log e orienta a correção e a reexecução; não há rollback inventado (não desinstala pacotes do sistema nem apaga o diretório de instalação em falha), mas evita habilitar/iniciar o serviço com instalação incompleta.
- **FR-020**: O instalador orienta a criação do primeiro administrador pelos mecanismos reais existentes (env `AUTH_ADMIN_USERNAME`/`AUTH_ADMIN_PASSWORD` no primeiro start, página `/setup` quando não há usuários, CLI `python -m app.cli create-user`) — sem criar mecanismo novo e sem executar a criação por conta própria (exceto quando o administrador escolher explicitamente a via env com senha fornecida/gerada no `.env`).
- **FR-021**: A documentação de instalação existente (README §"Instalação em uma máquina nova" e `docs/`) deve ser atualizada na mesma tarefa de implementação para referenciar o instalador e seus parâmetros, preservando o fluxo manual como alternativa (Constitution XI).

### Segurança

- **SR-001**: Nenhuma senha, segredo ou token aparece em stdout, arquivo de log, argv de comando registrado ou mensagem de erro; senhas são coletadas ocultas (equivalente a leitura sem eco) ou geradas.
- **SR-002**: O `.env` é criado com permissão 0600 e propriedade do usuário do serviço; segredos gerados usam fonte criptograficamente segura.
- **SR-003**: A aplicação roda com usuário/grupo dedicado sem privilégios de root; o usuário do banco tem privilégios apenas no banco da aplicação.
- **SR-004**: Operações destrutivas exigem confirmação explícita (interativo) ou abortam (não interativo); banco existente nunca é apagado/recriado automaticamente.
- **SR-005**: O instalador valida privilégios e para de forma segura em erro — nunca deixa serviço habilitado apontando para instalação inválida.

### Não funcionais / Compatibilidade

- **NFR-001**: Distribuições oficialmente suportadas: Debian/Ubuntu e derivadas diretas com `apt` e systemd (ex.: Pop!_OS); outras distribuições não são objetivo desta feature (registradas como evolução futura).
- **NFR-002**: O instalador não exige compilação de pacotes C (stack do projeto é compatível — driver PyMySQL puro); `python3-venv`/`python3-pip` são providos quando a distribuição os separa do Python base.
- **NFR-003**: Tempo alvo de instalação limpa (com rede e pacotes disponíveis): minutos, não horas — a etapa mais lenta esperada é a instalação de pacotes do sistema; o instalador informa progresso etapa a etapa.
- **NFR-004**: A instalação resultante deve ser equivalente à instalação manual documentada (mesma estrutura: diretório + venv + `.env` + systemd), sem criar arquitetura paralela (nem Docker, nem supervisor, sem alterar `run.py`).
- **NFR-005**: Atualização futura (`--update`) é avaliada e reservada na interface (flag reconhecida e documentada como ainda não implementada, ou implementada se a análise do plan indicar baixo custo) — sem prometer comportamento não especificado.

## Fluxo de instalação (resumo normativo)

```text
verificações prévias (sudo, distro, systemd, conectividade)
  → Python ≥ 3.10 (instalar se preciso)
  → Git (instalar se preciso)
  → MariaDB Server (instalar se preciso; garantir serviço ativo)
  → banco + usuário dedicados (criar ou reutilizar; privilégios mínimos)
  → teste de conexão real (driver do projeto)
  → clone do repositório (ou reutilizar clone existente válido)
  → venv + pip install -r requirements.txt (+ validação de import)
  → .env gerado/validado (DATABASE_URL, APP_HOST, APP_PORT; 0600)
  → usuário/grupo Linux dedicado + permissões do diretório
  → unit systemd instalada/habilitada (padrão real do README)
  → start do serviço + espera do /health
  → bateria de verificação pós-instalação
  → resumo final (URL, /docs, /health, gerenciamento, 1º admin, sem segredos)
```

Fluxo de reinstalação: mesmo fluxo, com cada etapa no modo "detectar → reutilizar/validar/completar" (nunca destruir); alterações em arquivos existentes só com confirmação + backup prévio (`*.bak`).

## Key Entities

- **Instalação**: diretório (default `/opt/SisPatrimonioPro`), repositório/branch (`main`), venv dentro do diretório, `.env` (0600), log do instalador.
- **Banco**: nome, usuário dedicado, senha (nunca logada), host/porta (default localhost:3306), charset `utf8mb4`/`utf8mb4_unicode_ci`; criação das tabelas delegada ao `init_db()` existente.
- **Serviço**: nome (default `sispatrimoniopro`), usuário/grupo Linux dedicados, unit systemd baseada no padrão do README (After/Wants no MariaDB e rede, EnvironmentFile, ExecStart via venv, Restart=on-failure, multi-user.target).
- **Resumo final**: URL, `/docs`, `/health`, comandos de gerenciamento, caminhos, instruções do 1º admin (env / `/setup` / CLI), localização do log — sem segredos.

## Assumptions

- O instalador roda no próprio servidor de destino (não é instalador remoto/orquestrador).
- Acesso à internet (GitHub + repositórios de pacotes) está disponível na instalação; ambientes air-gapped ficam fora do escopo.
- O repositório é público/acessível no servidor (credenciais Git interativas não são tratadas; se o clone exigir autenticação, o instalador aborta com orientação).
- MariaDB no próprio servidor (localhost); banco remoto é configurável por parâmetro do modo não interativo (host/porta) mas não é o fluxo primário validado.
- A suíte pytest não é executada pelo instalador (tempo/escopo); a validação é a bateria pós-instalação + `/health`.
- `AUTH_ADMIN_PASSWORD` só entra no `.env` por escolha explícita do administrador (não é default); o mecanismo preferencial de 1º admin no resumo é o CLI/`/setup`.

## Decisões registradas (D1–D4 — resolvidas pelo responsável em 2026-09-19)

- **D1 — Entrega do instalador**: artefato único `install.sh` na **raiz do repositório**, versionado e auditável; execução a partir do clone (sem `curl | bash`). Git como pré-requisito natural do fluxo.
- **D2 — Recriação de banco**: permitida somente pela flag explícita `--recreate-db`, com **dupla confirmação interativa**; **proibida em `--non-interactive`**; afeta exclusivamente o banco da aplicação. Sem a flag, banco existente é intocável (FR-017).
- **D3 — SGBD suportado**: detecção aceita **MariaDB ou MySQL** — se qualquer um existir, é reutilizado (instalador se adapta); instalação de SGBD só ocorre se nenhum existir, e nesse caso instala **MariaDB** (padrão da feature). A unit systemd referencia o serviço de banco real detectado (FR-012).
- **D4 — HTTPS/reverse proxy**: **fora do escopo** desta feature — produção inicial em HTTP na rede interna (`APP_HOST` explícito no `.env`); `AUTH_COOKIE_SECURE` permanece configurável pelo administrador; nginx/TLS fica para feature futura.

## Risks

- **Python da distribuição < 3.10** (Debian antigo): mitigação — verificação de versão e orientação clara de distribuições suportadas; sem repositórios de terceiros automáticos.
- **Porta 8000/3306 em conflito**: detecção de porta em uso antes do start e mensagem específica.
- **Instalação interrompida** (rede, energia): idempotência permite reexecutar; log preserva etapa.
- **Divergência de pacotes entre versões Debian/Ubuntu**: comandos de instalação centralizados por família, com teste de existência do pacote antes do uso.
- **Senhas com caracteres especiais**: instalador sempre gera/aplica percent-encoding programaticamente (nunca montagem manual da URL pelo operador).
- **MariaDB preexistente com bind-address restrito ou socket auth**: testes de conexão explícitos com mensagens de diagnóstico específicas.
- **Diferenças MariaDB × MySQL** (D3 — nomes de serviço `mariadb.service`/`mysql.service`, variantes de pacotes e versões do cliente): mitigação — detecção pelos comandos reais (servidor + `mysqldump` presente) e unit systemd adaptada ao serviço detectado; MySQL Oracle sem comunidade/pacote em algumas versões Debian/Ubuntu → mensagem de orientação quando instalável.

## Decisões técnicas (base de código real)

- Ponto de entrada permanece `python run.py` via venv (systemd `ExecStart`), exatamente como o README documenta — sem gunicorn/supervisor/novos wrappers.
- `APP_HOST`/`APP_PORT` definidos no `.env` gerado (a aplicação lê de lá; o default de código `192.168.0.9` é específico do operador e não deve vazar para novas instalações).
- Instalação de dependências exclusivamente via `requirements.txt` (nenhuma duplicação de dependências no instalador).
- Unit systemd derivada do padrão real documentado no README (ajustada para usuário dedicado), não uma unit genérica copiada de tutoriais.
- Nome do serviço default `sispatrimoniopro` corrige a inconsistência de nomes do README (arquivo `sispatrimonio.service` × comandos `sispatrimoniopro`) — o instalador é consistente internamente; a correção do README é parte de FR-021.
- Artefato instalador: **`install.sh` na raiz do repositório** (decisão D1) — versionado, auditável, executado a partir do clone; sem distribuição `curl | bash`.
- HTTPS/reverse proxy deliberadamente fora do escopo (decisão D4): HTTP na rede interna nesta feature; `AUTH_COOKIE_SECURE` e proxy ficam como evolução futura documentada.
