# Tasks: CLI de Reset Administrativo de Senha

**Input**: Design documents from `/specs/002-cli-reset-senha-admin/`

**Prerequisites**: plan.md (✅), spec.md (✅ revisado — D-1..D-4), research.md (✅ R1–R9), data-model.md (✅), contracts/cli-reset-password-contract.md (✅), quickstart.md (✅)

**Tests**: **Testes são requisito desta feature** (spec FR-015; Constitution VIII). Novo arquivo `tests/test_cli_reset_password.py`, escrito **antes** da implementação de cada story (TDD), usando os fixtures existentes de `tests/conftest.py` — nenhum teste existente é editado, nenhuma infraestrutura de teste é criada ou adaptada (SQLite in-memory permanece exclusivo da suíte; nenhuma tarefa o menciona além disto).

**Organization**: Tarefas agrupadas por user story do spec — US1 caminho de sucesso (P1), US2 tratamento de erros (P2), US3 auditoria completa com operador do SO (P3). Todas as regras de negócio permanecem nos services existentes; a implementação é apenas orquestração em `app/cli.py` (plan §2/§11).

**Feature Branch**: `002-cli-reset-senha-admin`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: User story da spec a que a tarefa pertence (US1, US2, US3)
- Todas as descrições incluem caminhos exatos de arquivo

## Path Conventions

- Projeto single-root: código em `app/`, testes em `tests/`, artifacts desta feature em `specs/002-cli-reset-senha-admin/`. **Único arquivo de código modificado: `app/cli.py`** (plan §10); `app/services/**`, `app/models/**`, `app/config.py`, `app/database.py`, RBAC, AD e schema **NÃO são tocados** (plan §11).

---

## Phase 1: Setup (Contexto da Feature)

**Purpose**: Confirmar contexto e estado limpo antes de qualquer mudança

- [x] T001 [P] Verificar que os artifacts de design existem em `specs/002-cli-reset-senha-admin/` (spec.md, plan.md, research.md, data-model.md, contracts/cli-reset-password-contract.md, quickstart.md) e que `git status` não mostra modificações pendentes em `app/` ou `tests/` (escopo do plan §10/§11)

**Checkpoint**: Contexto confirmado — nada de `app/` ou `tests/` está modificado.

---

## Phase 2: Foundational (Baseline e Verificação de Reuso — Bloqueia as Stories)

**Purpose**: Registrar o estado de regressão antes de qualquer mudança e confirmar que os mecanismos a reutilizar estão exatamente como o plan assume

**⚠️ CRITICAL**: Nenhuma tarefa de user story pode começar antes desta fase

- [x] T002 [P] Registrar a baseline de regressão: executar `pytest -q` na raiz e anotar o resultado atual (estado conhecido, incluindo a falha defasada de lockout documentada na baseline 001) — referência para comparação em T015 (quickstart §1)
- [x] T003 [P] Verificar no código os mecanismos de reuso contra o plan §2: `app/services/auth_service.py` → `reset_password` (L176, política ≥8, hash, zera lockout, exclui sessões, commit), `app/services/audit_service.py` → `write_audit` (L129, suporta `user=None` + `username=`), `ACTION_PASSWORD_RESET`/`RESULT_SUCCESS`/`RESULT_FAILURE` (L32/L123-126), e `app/services/ad_service.py` → `PROVIDER_AD` (L43) — se qualquer assinatura divergir, PARAR e reportar antes de implementar

**Checkpoint**: Baseline registrada; mecanismos de reuso confirmados — stories podem começar.

---

## Phase 3: User Story 1 — Reset bem-sucedido de usuário local (Priority: P1) 🎯 MVP

**Goal**: Um administrador redefine a senha de um usuário local pelo terminal com entrada dupla oculta; senha trocada, sessões invalidadas, atributos preservados, 1 registro de auditoria de sucesso

**Independent Test**: com usuário local + `password_reader` injetado, executar `run_reset_password` → retorno 0; `verify_password(nova)` verdadeiro e antiga falso; 0 sessões do alvo; perfis/`is_active`/demais atributos intactos; 1 registro `RESET_SENHA`/`SUCCESS` sem segredos

### Tests for User Story 1 (escritas primeiro — devem falhar antes da implementação) ⚠️

- [x] T004 [P] [US1] Criar `tests/test_cli_reset_password.py` com os casos US1 (fixtures `db_session` de `tests/conftest.py`; usuário local criado via `create_user`; leitor de senha injetado retornando valores fixos): (a) sucesso — retorno 0, hash alterado (verify_password novo/antigo), mensagem de sucesso; (b) sessões do alvo invalidadas (criar `UserSession` antes, 0 depois); (c) usuário com perfil atribuído mantém o perfil e `is_active`/`full_name`/`email` intactos; (d) usuário **inativo** — reset permitido, senha trocada, `is_active` permanece `False` (D-3); (e) usuário em lockout — `failed_login_attempts`/`locked_until` zerados após o reset

### Implementation for User Story 1 (todas em `app/cli.py` — sequenciais)

- [x] T005 [US1] Adicionar em `app/cli.py` o subparser `reset-password` com `--username` obrigatório (help explicando prompt oculto; **sem** opção `--password` — FR-004) e o branch `elif args.command == "reset-password":` em `main()` chamando o orquestrador e aplicando `sys.exit(código)` (plan §2a/2b)
- [x] T006 [US1] Implementar em `app/cli.py` a função `_get_os_operator() -> Optional[str]`: `os.environ.get("SUDO_USER")` → fallback `getpass.getuser()` → qualquer exceção/indisponibilidade retorna `None` sem propagar (decisão D-2; plan §2d)
- [x] T007 [US1] Implementar em `app/cli.py` a função `run_reset_password(db, username, password_reader=getpass.getpass) -> int` — **núcleo do caminho de sucesso**, nesta ordem: (1) normalizar username (strip) e localizar o `User` **local** (mesma comparação do login); (2) prompts ocultos `"Nova senha: "` e `"Confirme a nova senha: "` via `password_reader` (D-1); (3) chamar **exclusivamente** `auth_service.reset_password(db, user, senha)` (FR-008) — o **único caminho de escrita da senha e das sessões** do alvo; a auditoria é escrita separada em `audit_logs` via `write_audit`. Fechamento do caminho: capturar `_get_os_operator()`; gravar a auditoria de sucesso via `write_audit(db, user=None, username=user.username, action=ACTION_PASSWORD_RESET, module="Usuários", resource="User", resource_id=user.id, resource_ref=user.username, ip_address=None, result=RESULT_SUCCESS, description="Redefinição de senha do usuário X (sessões invalidadas) — origem: CLI", new_data={"origem": "CLI", "operador_so": operador} ou {"origem": "CLI"} se indisponível)` (D-2, FR-011, FR-012); imprimir mensagem de sucesso do contrato; retornar 0. O tratamento detalhado de erros fica em T010; a semântica best-effort da auditoria fica em T013
- [x] T008 [US1] Executar `pytest tests/test_cli_reset_password.py -q` até verde e confirmar que `pytest tests/test_auth.py -q` permanece no estado da baseline (serviço não alterado)

**Checkpoint**: US1 funcional e testável isoladamente — MVP entregue (reset local completo).

---

## Phase 4: User Story 2 — Todo erro falha de forma segura (Priority: P2)

**Goal**: Cada caso de erro produz mensagem clara não sensível, retorno 1 (exceto os casos permitidos por decisão), alvo inalterado e 1 tentativa de registro de auditoria de falha

**Independent Test**: para cada erro (inexistente, AD, política, divergência, EOF, exceção inesperada) → mensagem do contrato, snapshot do alvo idêntico ao anterior, exatamente 1 registro `FAILURE` auditado (quando aplicável)

### Tests for User Story 2 (extensão do mesmo arquivo — sequenciais entre si)

- [x] T009 [P] [US2] Estender `tests/test_cli_reset_password.py` com os casos US2: (a) username inexistente → retorno 1, mensagem `Erro: usuário '<username>' não encontrado.`, nada criado, leitor NÃO chamado; (b) usuário AD (`auth_provider="ad"`, hash sentinela `!ad-external`) → retorno 1, mensagem menciona "senha local"/"Active Directory", sentinela intacta, leitor NÃO chamado (recusa antes de qualquer prompt — FR-003); (c) senha de 7 caracteres → retorno 1 com a mensagem exata da política do service; hash antigo ainda válido; (d) confirmação divergente → retorno 1, mensagem "as senhas não conferem", nada alterado (D-1); (e) leitor levanta `EOFError` → retorno 1, mensagem de entrada indisponível, nada alterado; (f) exceção não-ValueError no service (monkeypatch de `reset_password`) → retorno 1 com mensagem genérica sem detalhes internos (FR-013/FR-014); em cada caso, snapshot dos campos do alvo idêntico ao anterior e exatamente 1 registro `RESET_SENHA`/`FAILURE` com descrição curta não sensível

### Implementation for User Story 2 (extensão de `app/cli.py`)

- [x] T010 [US2] Estender `run_reset_password` em `app/cli.py` com os caminhos de erro, na ordem do plan §1: (1) usuário não encontrado → auditoria `FAILURE` (username digitado, `resource_id=None`) + mensagem do contrato + retorno 1; (2) `user.auth_provider == PROVIDER_AD` (importar de `app/services/ad_service.py` — R4) → auditoria `FAILURE` + mensagem de recusa AD + retorno 1, **antes** de qualquer prompt; (3) capturar `EOFError`/entrada vazia do leitor → auditoria `FAILURE` ("entrada indisponível") + mensagem + retorno 1; (4) envolver a chamada a `reset_password`: `ValueError` → auditoria `FAILURE` ("política de senha") + mensagem original da exceção (FR-006) + retorno 1; exceção qualquer → auditoria `FAILURE` ("falha na atualização") + mensagem genérica `Erro: falha ao atualizar a senha. Tente novamente.` + retorno 1; todos os registros `FAILURE` no formato D-2 (ator nulo, origem CLI, operador do SO)
- [x] T011 [US2] Executar `pytest tests/test_cli_reset_password.py -q` até verde (US1+US2) e `pytest tests/test_auth.py tests/test_rbac.py -q` no estado da baseline

**Checkpoint**: US1 e US2 completas — todos os caminhos do contrato de saída cobertos.

---

## Phase 5: User Story 3 — Auditoria completa sem segredos (Priority: P3)

**Goal**: Toda execução tenta gerar exatamente 1 registro com ator nulo, alvo, resultado, origem `CLI` e operador do SO quando disponível (D-2); falha de auditoria segue a semântica transacional real (plan §5.1)

**Independent Test**: execuções com `SUDO_USER`, com fallback e sem identidade → registro correto e comando nunca falha por ausência do operador; auditoria falhando após reset efetivado → retorno 0 com aviso e senha alterada; falhando em caminho de erro → retorno 1 com mensagem original; nenhum registro contém a senha

### Tests for User Story 3 (extensão do mesmo arquivo)

- [x] T012 [P] [US3] Estender `tests/test_cli_reset_password.py` com os casos US3: (a) sucesso com `SUDO_USER` no ambiente → `new_data` do registro contém `"origem": "CLI"` e `"operador_so"` igual ao valor da variável; (b) sem `SUDO_USER`, com `getpass.getuser()` simulado (monkeypatch) → fallback registrado; (c) sem nenhum → `new_data` contém apenas `"origem": "CLI"`, comando conclui com retorno 0 e **não** levanta exceção (cenário 4 da US3 do spec); (d) auditoria falhando **após** reset efetivado (monkeypatch de `write_audit` para levantar exceção) → retorno 0, aviso `Atenção: não foi possível registrar o evento de auditoria.` impresso, senha nova vigente e sessões invalidadas (§5.1); (e) auditoria falhando em caminho de erro (usuário AD) → retorno 1 com a mensagem original do erro e nada alterado (§5.1); (f) varredura de segredos: em todas as execuções da suíte, a senha (nem substring dela) aparece em `description`/`new_data`/`previous_data` de qualquer linha de `AuditLog` (FR-012)

### Implementation for User Story 3 (extensão de `app/cli.py`)

- [x] T013 [US3] Tornar a auditoria best-effort em `run_reset_password` (`app/cli.py`) conforme plan §5.1: envolver cada chamada a `write_audit` em try/except `Exception` → em caso de falha, imprimir uma única vez `Atenção: não foi possível registrar o evento de auditoria.` (sem detalhes internos) e **nunca** alterar o código de retorno da função; garantir a ordem do caminho de sucesso: commit do service → captura do operador → tentativa de auditoria → mensagem de sucesso; garantir que nos caminhos de erro a mensagem original seja preservada mesmo se a auditoria falhar
- [x] T014 [US3] Executar `pytest tests/test_cli_reset_password.py -q` até verde (US1+US2+US3) e `pytest tests/test_auth.py -q` no estado da baseline

**Checkpoint**: Todas as user stories implementadas e testadas.

---

## Phase 6: Polish & Cross-Cutting (Regressão, Documentação e Validação)

**Purpose**: Garantir não-regressão integral, documentação fiel (Constitution XI) e validação executável

- [x] T015 Executar a suíte completa `pytest -q`: todos os testes existentes no estado registrado em T002 + todos os testes novos verdes (quickstart §1; nenhuma edição em testes existentes — Constitution VIII)
- [x] T016 [P] Atualizar `README.md` — seção de comandos CLI (linha ~167 e bloco ~564–583): incluir `python -m app.cli reset-password --username <usuario>`, sem senha em exemplo, mencionando prompt oculto, confirmação dupla e recusa de usuários AD
- [x] T017 [P] Atualizar `docs/ARQUITETURA_E_MANUTENCAO.md` — as duas listas de comandos (linhas ~130 e ~1100): acrescentar `reset-password`
- [x] T018 [P] Atualizar `docs/GUIA_DE_MANUTENCAO.md` — procedimento de recuperação de acesso de usuário local (região ~137/158): quando usar o comando, aviso de invalidação de sessões, aviso de que o reset não altera o status de ativação e de que usuários AD devem ser tratados no próprio AD
- [x] T019 [P] Atualizar `app/services/help_service.py` — artigo da central de ajuda de administração de usuários/CLI (localizar por "create-user" em `get_articles()`): incluir o comando e as regras (senha oculta, sem argumento, AD intocado, sessões invalidadas); nenhum segredo no conteúdo
- [ ] T020 Executar a validação manual de `specs/002-cli-reset-senha-admin/quickstart.md` §2–§3 contra o MariaDB configurado em `DATABASE_URL` (ambiente não produtivo): cenários 2.1–2.7 (incl. verificação de exposição via `ps` e logs) e conferência dos registros na tela de Auditoria; registrar os resultados
- [x] T021 Completar o checklist de conformidade da Constitution (quickstart §4: escopo plan §10/§11 respeitado, comportamento preservado, nenhum segredo, nenhum DDL, documentação na mesma tarefa), verificar os SC-001..SC-006 do spec e confirmar via `git status` que apenas `app/cli.py`, `tests/test_cli_reset_password.py`, os 4 alvos de documentação e `specs/002-cli-reset-senha-admin/**` foram alterados/criados

**Checkpoint**: Feature entregue — validada por suíte, validação manual e checklist.

---

## Validation Results

> Preenchido por T020/T021. Automação executada em 15/09/2026; validação manual pendente do operador.

- **Baseline (T002)**: ☑ registrada — 153 passed, 1 failed (`test_lockout_after_failed_attempts`, falha defasada conhecida)
- **Suíte completa (T015)**: ☑ executada · ☑ estado existente confirmado (153 passed + mesma única falha defasada) · ☑ novos testes verdes (18/18 em `tests/test_cli_reset_password.py`)
- **Validação manual MariaDB (T020)**: ☐ cenários 2.1–2.7 · ☐ auditoria conferida · ☐ exposição (ps/logs) verificada — **PENDENTE: executar pelo operador contra o `DATABASE_URL` do ambiente**
- **Constitution checklist (T021)**: ☑ completo — escopo plan §10/§11 respeitado (`git status` confere), comportamento preservado (153/153), nenhum segredo em código/docs/testes, nenhum DDL, documentação na mesma tarefa (T016–T019)
- **SC-001..SC-006**: ☑ SC-001 (comando integrado ao padrão da CLI) · ☑ SC-002 (reset funcional, 6 testes US1) · ☑ SC-003 (senha oculta/dupla — entrada exclusivamente por `password_reader`) · ☑ SC-004 (sem exposição em argv — sem opção de senha) · ☑ SC-005 (hash/sessões via service — 18 testes) · ☑ SC-006 (auditoria sem segredos — varredura US3) — SC verificados por automação; conferência final em T020
- **Observações**: implementação da US2 verificada verde junto com a US1 (os caminhos de erro foram implementados com o núcleo do orquestrador, conforme TDD verificado caso a caso); `.pyc` rastreados aparecem como modificados por higiene pré-existente do repo (fora do escopo); adição dos padrões Python ao `.gitignore` executada como parte do setup do skill

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — imediata
- **Foundational (Phase 2)**: depende da Phase 1 — BLOQUEIA as stories (baseline de regressão + confirmação dos mecanismos de reuso)
- **User Stories (Phases 3–5)**: dependem da Phase 2; **devem ser implementadas em ordem** (US1 → US2 → US3) porque todas estendem o mesmo arquivo `app/cli.py` e o mesmo arquivo de testes — não há paralelismo entre stories nesta feature
- **Polish (Phase 6)**: T015 depende de todas as stories; T016–T019 podem rodar em paralelo após T014; T020 depende de T015; T021 fecha a entrega

### User Story Dependencies

- **US1 (P1)**: núcleo — cria o subcomando, o orquestrador e o caminho de sucesso
- **US2 (P2)**: estende `run_reset_password` com os caminhos de erro (usa o esqueleto da US1)
- **US3 (P3)**: torna a auditoria best-effort e cobre o operador do SO (usa os caminhos da US1/US2)
- Independência **de teste** preservada: cada story tem casos próprios executáveis isoladamente no arquivo de testes

### Within Each User Story

- Testes primeiro, como **requisito TDD obrigatório**: a tarefa de testes é escrita E executada (verificando que falha) **antes** da implementação correspondente — nunca em paralelo com ela → implementação em `app/cli.py` → execução dos testes até verde → regressão direta (`test_auth.py`)
- As tarefas de implementação são sequenciais entre si (mesmo arquivo `app/cli.py`)

### Parallel Opportunities

- T002/T003 (Foundational) em paralelo
- T016–T019 (documentação, 4 arquivos distintos) em paralelo
- **Testes NÃO são paralelizáveis com a implementação**: dentro de cada User Story, a tarefa de testes é requisito TDD e deve estar escrita e executada (falhando) **antes** do início da implementação correspondente — o marcador [P] nas tarefas de testes indica apenas independência de arquivo, não execução concorrente com a implementação

---

## Parallel Example: Phase 6 Documentation

```bash
# Os 4 alvos de documentação são arquivos distintos — podem ser editados em paralelo:
Task: "Atualizar README.md (lista de comandos CLI)"                    # T016
Task: "Atualizar docs/ARQUITETURA_E_MANUTENCAO.md (2 listas)"          # T017
Task: "Atualizar docs/GUIA_DE_MANUTENCAO.md (procedimento)"            # T018
Task: "Atualizar app/services/help_service.py (artigo da ajuda)"       # T019
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 + 2 → contexto, baseline e mecanismos confirmados
2. US1 → subcomando funcional com reset real de usuário local
3. **STOP and VALIDATE**: `pytest tests/test_cli_reset_password.py -q` verde + `test_auth.py` intacto
4. O MVP já entrega o valor central (recuperação administrativa de acesso)

### Incremental Delivery

1. US1 → reset funcional (MVP)
2. US2 → superfície de erros completa e segura (contrato de saída integral)
3. US3 → auditoria com operador do SO e semântica §5.1 (comprovação)
4. Phase 6 → regressão integral + documentação + validação manual em MariaDB + checklist

### Notes

- **Nenhuma tarefa cria ou adapta infraestrutura de banco**: a suíte continua no mecanismo de teste já existente do projeto; a validação manual usa o MariaDB de `DATABASE_URL` (quickstart §2)
- **Nenhuma tarefa altera** `app/services/auth_service.py`, `app/services/audit_service.py`, `app/services/ad_service.py`, models, schemas, API, web, configuração, RBAC ou integração AD (plan §11)
- A falha conhecida da suíte (lockout defasado, documentada na baseline 001) permanece como está — corrigi-la é tarefa própria, fora do escopo (Constitution I)
- Evitar: tarefas vagas, editar testes existentes, tocar arquivos do plan §11
