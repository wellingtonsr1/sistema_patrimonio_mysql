---
description: "Task list for feature implementation"
---

# Tasks: Correção do Backup Manual no Windows

**Input**: Design documents from `/specs/018-correcao-backup-windows/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/service-contract.md, quickstart.md

**Tests**: Incluídos por exigência da spec (FR-014/US2/US3 — Testes A–H do briefing) e Princípio VIII da Constitution. **TDD: escrever e executar ANTES da implementação correspondente (vermelho → verde).** `[P]` indica apenas independência de arquivo — NUNCA execução concorrente com a implementação que a valida (lição 005).

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Projeto single-app FastAPI: `app/` (config, services) + `tests/` na raiz.

---

## Phase 1: Setup (Contexto e Baseline)

**Purpose**: Carregar artefatos e garantir patamar da suíte antes de qualquer edição

- [x] T001 Ler os artefatos da feature (spec.md, plan.md, research.md D1–D7/R1–R6, contracts/service-contract.md, quickstart.md) e os arquivos-alvo: app/services/backup_service.py (funções `_run_mysqldump`, `_run_mysql_import`, `_sanitize_stderr`, `generate_backup`), app/config.py, tests/test_backup_manual.py e tests/conftest.py (descobrir como DATABASE_URL é fornecida à suíte — necessário para as monkeypatch dos testes)
- [x] T002 Rodar baseline da suíte: `python -m pytest tests/ -q --tb=no` — registrar o patamar real (medido em 2026-09-18: **420 passed / 4 failed**): 1 falha pré-existente de lockout (tests/test_rbac.py::test_lockout_after_failed_attempts — defasagem de tempo conhecida) + **3 falhas do ciclo de restauração 017** (tests/test_backup_restore.py::test_ciclo_completo_service_sucesso, ::test_web_post_executa_ciclo_completo, ::test_falha_no_import_sem_falso_sucesso) que invocam o dump REAL como backup de segurança e falham nesta máquina Windows pelo MESMO bug que a 018 corrige (resolução do executável — ver research D8). Política: patamar pós-018 = **essas mesmas 4** (as 3 de restauração permanecem dependentes de ambiente; fora do escopo alterá-las — Princípio I) + todos os testes novos verdes. Desvio ⇒ PARAR e reportar antes de prosseguir

---

## Phase 2: Foundational (Gate de Fatos — bloqueia as stories)

**Purpose**: Re-verificar no código real os fatos que sustentam as decisões R1–R6. Se qualquer fato divergir, PARAR e reportar

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Gate de fatos (somente leitura, registrar evidências no Validation Results): (a) `_run_mysqldump` constrói `env = {"MYSQL_PWD": ..., "PATH": "/usr/local/bin:/usr/bin:/bin"}` e chama `["mysqldump", ...]` por nome simples; (b) mesmo padrão de env em `_run_mysql_import` com `["mysql", ...]`; (c) `_sanitize_stderr(stderr_text, password)` existe e é usada pelo import; (d) `generate_backup` aceita `dump_executor` e `restore_backup` aceita `import_executor` (injeção para testes); (e) nesta máquina Windows: `shutil.which("mysqldump")` → None e `C:\xampp\mysql\bin\mysqldump.exe` existe (reexecutar as provas D2/D3); (f) `tests/conftest.py` não exige mysqldump real (executores FAKE — padrão 015–017); (g) `app/config.py` não possui variável de executável de dump hoje

**Checkpoint**: Fatos confirmados — implementação das stories pode começar

---

## Phase 3: User Story 1 - Backup manual funciona no Windows (Priority: P1) 🎯 MVP

**Goal**: Geração de backup bem-sucedida no Windows com o utilitário corretamente resolvido (config opcional `MYSQLDUMP_PATH` → fallback PATH) e ambiente de subprocesso herdado + `MYSQL_PWD`

**Independent Test**: Chamar `_run_mysqldump` com `MYSQLDUMP_PATH` apontando para um executável real qualquer → subprocesso executa (sem FileNotFoundError de PATH); com fallback no PATH → resolve; sem nenhum → `BackupError` "não encontrado" (prova por testes; prova real no navegador fica para o fechamento/operador)

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Criar testes TDD em tests/test_backup_manual.py (seção "018 — US1 resolução de executável e ambiente"): (a) executável configurado: monkeypatch `backup_service.MYSQLDUMP_PATH` → caminho real de um executável existente (usar `sys.executable`) e chamar `_run_mysqldump` com monkeypatch de `backup_service.DATABASE_URL` (`mariadb+pymysql://usuario:senha_falsa@localhost:3306/banco`) → NÃO levanta FileNotFoundError de resolução (pode levantar CalledProcessError, pois o executável não é um dump real — capturar e aceitar apenas CalledProcessError/BackupError "retornou erro"); assegurar que o argv recebido (fake de subprocess.run capturando args) começa com o caminho configurado; (b) fallback: `MYSQLDUMP_PATH=None` + monkeypatch `shutil.which` (no namespace onde a implementação o usa) retornando caminho fake `/usr/bin/mysqldump` → argv usa esse caminho (simula Linux — Teste F); (c) nada disponível: `MYSQLDUMP_PATH=None` + `which` → None → `BackupError` com mensagem distinta de "não encontrado" (Teste B — sem falso sucesso); (d) `MYSQLDUMP_PATH` apontando para caminho inexistente → `BackupError` "não encontrado" (falha clara antes do subprocesso); (e) helper de ambiente (R1): `os.environ.copy()` + `MYSQL_PWD` — env herdado contém o PATH do processo (não contém "/usr/local/bin:/usr/bin:/bin" fixo) e `env["MYSQL_PWD"]` = senha da URL; (f) senha NUNCA em argv: capturar argv do subprocesso e assegurar que a senha da URL não aparece em nenhum argumento (Teste H parcial)
- [x] T005 [US1] Validar TDD vermelho: rodar `python -m pytest tests/test_backup_manual.py -k 018_US1 -q` e confirmar falhas APENAS nos comportamentos novos (resolução/helper não existem). Registrar contagem no Validation Results

### Implementation for User Story 1

- [x] T006 [US1] Adicionar `MYSQLDUMP_PATH` (opcional, `os.getenv("MYSQLDUMP_PATH") or None`) em app/config.py junto das demais variáveis, com comentário explicando o uso (caminho do mysqldump; ex.: Windows/XAMPP). Criar `.env.example` contendo apenas `MYSQLDUMP_PATH=` com exemplo comentado `C:\xampp\mysql\bin\mysqldump.exe` — SEM nenhum segredo (briefing §19). NÃO tocar em nenhuma variável existente (inclui APP_HOST modificado localmente — fora do escopo)
- [x] T007 [US1] Implementar em app/services/backup_service.py (contract §3): (1) importar `MYSQLDUMP_PATH` de app.config; (2) helpers de módulo `_resolve_dump_executable()` → caminho efetivo do mysqldump: se `MYSQLDUMP_PATH` configurado, validar existência (Path.is_file) senão `BackupError("O utilitário de dump não foi encontrado no servidor...")`; senão `shutil.which("mysqldump")`; senão `BackupError` "não encontrado"; (3) helper `_dump_env(password)` → `os.environ.copy()` com `env["MYSQL_PWD"] = password` (R1 — substitui o env fixo Unix); (4) `_run_mysqldump` passa a usar os dois helpers (argv inalterado: `--single-transaction --no-tablespaces --host= --port= --user= <database>`; senha NUNCA em argv)
- [x] T008 [US1] Validar US1: testes novos verdes + `python -m pytest tests/test_backup_manual.py tests/test_backup_restore.py -q` no patamar (zero regressão). Registrar no Validation Results

**Checkpoint**: US1 funcional — resolução do executável e ambiente multiplataforma provados por teste

---

## Phase 4: User Story 2 - Falhas diagnosticáveis sem expor segredos (Priority: P1)

**Goal**: Log técnico no caminho do dump (paridade com o import) + mensagens amigáveis distintas, sem jamais registrar credenciais

**Independent Test**: Provocar falha controlada (executável que retorna erro) → caplog contém etapa, exit code e stderr SANITIZADO (senha mascarada); mensagem ao usuário distingue "não encontrado" de "retornou erro"

### Tests for User Story 2 ⚠️

- [x] T009 [P] [US2] Criar testes TDD em tests/test_backup_manual.py (seção "018 — US2 diagnóstico e segurança"): (a) log técnico em falha de retorno: `MYSQLDUMP_PATH` → `sys.executable` (executa Python com argumentos de dump → exit ≠ 0) + caplog → registro contém "dump" (etapa), exit code ≠ 0 e mensagem "retornou erro" (Teste D); (b) sanitização: monkeypatch `backup_service.DATABASE_URL` com senha `senha123` + monkeypatch de subprocess.run para levantar `CalledProcessError(returncode=2, cmd="mysqldump", stderr=b"Access denied ... senha123 ...")` → caplog contém `***` e NÃO contém `senha123` (Teste H); (c) mensagens distintas: utilitário ausente → mensagem menciona "não foi encontrado"; returncode ≠ 0 → mensagem "O utilitário de dump retornou erro." (duas mensagens diferentes); (d) usuário nunca vê stderr: a mensagem da BackupError de "retornou erro" NÃO contém o texto do stderr
- [x] T010 [US2] Validar TDD vermelho (falhas nos comportamentos novos — logging no dump não existe). Registrar no Validation Results

### Implementation for User Story 2

- [x] T011 [US2] Implementar em app/services/backup_service.py (contract §2.1/§3, R5/R6): no except de `CalledProcessError` do dump — registrar `logger.error` com etapa "dump", `exc.returncode` e `_sanitize_stderr(stderr_decodificado, password)` (reuso do helper existente; NUNCA propagar stderr ao usuário/auditoria); levantar `BackupError("O utilitário de dump retornou erro.")` (mensagem existente mantida). Nos pontos de resolução (T007), garantir que a mensagem de "não encontrado" é a distinta do R6. Nenhum handler novo; mesmo `logger = logging.getLogger(__name__)` (briefing §22)
- [x] T012 [US2] Validar US2: testes novos verdes + regressão da suíte de backup. Registrar no Validation Results

**Checkpoint**: US2 funcional — qualquer falha de dump é diagnosticável pelo log sem expor segredos

---

## Phase 5: User Story 3 - Robustez de falhas e preservação do Linux (Priority: P2)

**Goal**: Paridade da correção no import (restauração 017 não ficar quebrada no Windows) + provas de robustez (returncode ≠ 0, arquivo parcial, auditoria, credenciais, fallback Linux)

**Independent Test**: Suíte cobre: import resolve/executa com as mesmas regras; falhas → FALHA registrada sem falso sucesso; parcial nunca listado; zero credenciais em logs

### Tests for User Story 3 ⚠️

- [x] T013 [P] [US3] Criar testes TDD em tests/test_backup_manual.py (seção "018 — US3 robustez e paridade"): (a) resolução do import: `MYSQLDUMP_PATH` configurado → executável do import derivado do mesmo bin (mesmo sufixo, p.ex. `...\bin\mysqldump.exe` → `...\bin\mysql.exe`); derivado inexistente → fallback `shutil.which("mysql")`; ambos ausentes → `BackupError` "não encontrado" (R4); (b) paridade de ambiente no import: `_run_mysql_import` usa env herdado + MYSQL_PWD (verificar via captura de Popen com fake — monkeypatch de subprocess.Popen capturando kwargs) (R1); (c) Teste D (returncode ≠ 0 no import): fake de Popen com returncode ≠ 0 → `BackupError` "retornou erro" + log com exit e stderr sanitizado (paridade com o comportamento existente do import — confirmar, não regredir); (d) Teste E (parcial): `generate_backup` com `dump_executor` que falha → nenhum `.part`/`.part.gz` listado em `list_backups()` e auditoria FAILURE (se já coberto pelos testes 015/016, registrar como confirmação e apenas assegurar que a mudança não o quebrou); (e) Teste G (auditoria): falha de geração por utilitário ausente registra `ACTION_BACKUP_FAILED` com descrição controlada; (f) Teste H (credenciais): em todos os testes 018, caplog nunca contém a senha falsa usada nas URLs de teste
- [x] T014 [US3] Validar TDD vermelho (paridade do import não existe). Registrar no Validation Results

### Implementation for User Story 3

- [x] T015 [US3] Implementar em app/services/backup_service.py (contract §4, R4): helper `_resolve_import_executable()` → deriva o cliente do mesmo bin de `MYSQLDUMP_PATH` (trocar stem `mysqldump`→`mysql`, preservando sufixo) se existir; senão `shutil.which("mysql")`; senão `BackupError` "não encontrado"; `_run_mysql_import` usa esse helper + `_dump_env(password)` (mesma correção do dump). Streaming, validação pós-restore, auditoria e guard da 017 INALTERADOS
- [x] T016 [US3] Validar US3: testes novos verdes + provas de robustez registradas (returncode, parcial, auditoria, credenciais — Testes D/E/G/H) + fallback Linux provado (Teste F — caso (b) do T013 e (b) do T004). Registrar no Validation Results

**Checkpoint**: Todas as stories funcionalmente completas

> **Nota de aceite (I1 do analyze)**: a distinção de "permissão negada" (FR-014, "quando possível") permanece no ramo genérico de OSError/SubprocessError — o log técnico novo (US2) torna a causa diagnosticável (`PermissionError`/"Access is denied" aparecem no log com tipo e mensagem), sem mensagem amigável dedicada.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Suíte completa, documentação e fechamento

- [x] T017 Rodar suíte completa: `python -m pytest tests/ -q --tb=short` — patamar esperado: **420 + novos passed, mesmas 4 falhas pré-existentes** (1 lockout + 3 do ciclo 017 dependentes de ambiente Windows — research D8; a 018 não as conserta por estarem fora do escopo). Qualquer regressão além das 4 ⇒ corrigir antes de prosseguir
- [x] T018 [P] Atualizar README.md §Backup: parágrafo sobre o requisito do utilitário (no PATH do servidor OU `MYSQLDUMP_PATH` no `.env`, exemplo Windows/XAMPP) + nota de que falhas agora são diagnosticáveis no log técnico. Sem segredos
- [x] T019 [P] Atualizar docs/ARQUITETURA_E_MANUTENCAO.md: registrar a variável `MYSQLDUMP_PATH` e o log técnico de diagnóstico do backup (onde há seções análogas de configuração/logging). Sem segredos
- [x] T020 Fechamento: `git status --porcelain` — escopo confinado a app/config.py (só a variável nova; APP_HOST local intocado), app/services/backup_service.py, tests/test_backup_manual.py, .env.example, README.md, docs/ARQUITETURA_E_MANUTENCAO.md e specs/018-*/; preencher Validation Results consolidado; marcar tasks concluídas; deixar T021 (validação real no Windows — quickstart §3) para o operador
- [ ] T021 [OPERADOR] Teste real no Windows conforme quickstart §3 (configurar MYSQLDUMP_PATH no .env, reiniciar, gerar backup pela tela, conferir Integridade OK/SHA-256/download/auditoria, validar o caminho de falha com executável renomeado) + teste real no Linux quando disponível (quickstart §4). Registrar o resultado no Validation Results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 → T002 (baseline antes de qualquer edição)
- **Foundational (Phase 2)**: T003 — bloqueia todas as stories (gate de fatos D1–D7)
- **US1 (Phase 3)**: T004 (testes, vermelho) → T005 (validar vermelho) → T006–T007 (implementação) → T008 (verde + regressão)
- **US2 (Phase 4)**: depende de US1 (o logging usa os pontos de falha criados em T007): T009 → T010 → T011 → T012
- **US3 (Phase 5)**: depende de US1/US2 (paridade reusa os helpers `_dump_env`/resolução): T013 → T014 → T015 → T016
- **Polish (Phase 6)**: depende de todas as stories: T017 → T018/T019 (paralelizáveis entre si) → T020 → T021 (operador)

### Within Each User Story

- **Testes primeiro (TDD)**: cada bloco de testes é escrito e executado como requisito TDD **antes** da implementação correspondente — a marcação `[P]` indica apenas independência de arquivo, nunca execução paralela com a implementação que os valida (lição 005)
- Implementação antes da validação; validação (verde + regressão) antes de avançar de story

### Parallel Opportunities

- T018 e T019 (arquivos distintos) podem ser editados em paralelo
- Os arquivos de teste das stories são o MESMO arquivo (tests/test_backup_manual.py) em seções distintas — escrever sequencialmente, uma story por vez
- Nenhuma tarefa de teste pode ser executada em paralelo com o início da implementação que as valida (TDD obrigatório — Constitution VIII)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003 — gate)
3. Complete Phase 3: User Story 1 (T004–T008)
4. **STOP and VALIDATE**: resolução do executável e ambiente provados; suíte no patamar
5. US2/US3 completam o diagnóstico e a paridade — baratas após US1 (mesmo arquivo, padrões estabelecidos)

### Incremental Delivery

1. Setup + Foundational → fatos confirmados
2. US1 → Windows resolve o executável (MVP!)
3. US2 → falhas diagnosticáveis sem segredos
4. US3 → import em paridade + robustez provada
5. Polish → suíte, docs, fechamento; T021 real fica para o operador

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Executor de dump/import é SEMPRE fake na suíte (nenhum mysqldump real nos testes — padrão 015–017); a prova real é o T021 (operador)
- NUNCA registrar credenciais em logs/testes (usar senha falsa nas URLs de teste e assegurar ausência nos logs — Teste H)
- `APP_HOST` modificado localmente em app/config.py é pré-existente e FORA do escopo — não tocar
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently

---

## Validation Results

| Task | Verificação | Resultado |
|---|---|---|
| T002 | Baseline medida nesta sessão (2026-09-18) | **420 passed / 4 failed** — 1 lockout (test_rbac) + 3 do ciclo 017 dependentes de ambiente Windows (research D8: invocam o dump real pelo mesmo bug) |
| T003 | Gate de fatos (a)–(g) | ✓ todos confirmados: env fixo Unix em dump e import; `_sanitize_stderr` existente; injeção de executores; `shutil.which("mysqldump")`→None nesta máquina; `C:\xampp\mysql\bin\mysqldump.exe` presente; suíte SQLite in-memory com monkeypatch de `backup_service.DATABASE_URL` (padrão de test_backup_restore.py:570); sem variável de executável prévia |
| T004/T005 | TDD vermelho US1 | ✓ 5 failed / 1 passed (o guard de argv já passava — comportamento existente) |
| T006 | `MYSQLDUMP_PATH` em app/config.py + `.env.example` | ✓ sem segredos; nenhuma variável existente tocada (APP_HOST local do operador intocado). **Incidente pós-entrega (2026-09-18, 09:03)**: a leitura da variável havia sido posicionada ANTES de `load_dotenv()` no config — com a variável existindo só no `.env`, `os.getenv` sempre via `None` mesmo reiniciando o servidor. Corrigido (leitura movida para depois do `load_dotenv`, junto do padrão do DATABASE_URL) + guarda de regressão `test_018_us3_config_le_apos_load_dotenv` |
| T007 | Helpers `_dump_env`/`_resolve_tool_executable`/`_resolve_import_executable` + dump/import usando-os | ✓ argv inalterado; senha exclusivamente no ambiente; `FileNotFoundError` pós-resolução tratado com mensagem clara (defesa em profundidade) |
| T008 | US1 verde + regressão backup | ✓ 6/6 US1; módulos de backup nas 3 falhas ambientes exatas do baseline (refinamento do design: resolução do import não falha antecipadamente — os fakes de Popen da suíte 017 precisam ser alcançados) |
| T009–T012 | US2 (Teste D + H + FR-014) | ✓ 4/4 — log com etapa=dump/exit/stderr sanitizado (`***`), senha nunca em log nem na mensagem ao usuário, mensagens distintas "não foi encontrado" vs "retornou erro" |
| T013–T016 | US3 (R4/R1 + Testes D/E/G/H/F) | ✓ 5/5 — import derivado do mesmo bin, env herdado, ausência com mensagem clara, auditoria FAILURE no utilitário ausente, zero credenciais; Teste E (parcial) confirmado pelos testes 015/016 existentes (intocados e verdes); Teste F (Linux) pelo fallback PATH (T004b) |
| T017 | Suíte completa | **435 passed / 4 failed** (420 + 15 novos; exatamente as mesmas 4 pré-existentes — zero regressão). Durante a execução, 1 falha transitória provocada pelo próprio teste de auditoria (mutação manual de `backup_service.shutil` sem monkeypatch envenenando o módulo) — corrigida no teste, sem alteração de código de produção. **Após a correção do incidente do T006** (ordem load_dotenv): suíte nesta máquina = **439 passed / 1 failed** (só o lockout) — as 3 falhas do ciclo 017 passaram porque o dump real passou a funcionar (esses testes invocam o dump real como backup de segurança; rodam contra sessão SQLite de teste — confirmado: ZERO eventos RESTORE na auditoria do banco real; o dump é somente leitura) |
| T018/T019 | README §Backup + ARQUITETURA_E_MANUTENCAO | ✓ requisitos do utilitário/`MYSQLDUMP_PATH` + diagnóstico no log; sem segredos |
| T020 | Escopo (`git status`) | ✓ exato: app/config.py, app/services/backup_service.py, tests/test_backup_manual.py, .env.example (novo), README.md, docs/ARQUITETURA_E_MANUTENCAO.md + specs/018-* — zero models/rotas/templates/RBAC/AD (SC-006 ✓) |
| T021 | Teste real no Windows (quickstart §3) | **Dump real OK (2026-09-18, sessão do agente)**: `MYSQLDUMP_PATH=C:\xampp\mysql\bin\mysqldump.exe` no `.env` local; resolução confirmada (dump → mysqldump.exe, import → mysql.exe derivado); **dump REAL: 70.438 bytes, cabeçalho "MariaDB dump 10.19 Distrib 10.4.32" do sispatrimoniopro**. Incidente do T006 diagnosticado pela trilha: as tentativas das 08:58/09:03 falharam com o servidor JÁ reiniciado — causa era o posicionamento no config, não o operador. **Pendente do operador: reiniciar o servidor novamente (o processo 09:03 ainda carrega o config antigo) e gerar o backup pela tela** (Integridade OK/SHA-256/download/auditoria — §3.3–3.5; caminho de falha §3.6). Linux §4 quando disponível |
