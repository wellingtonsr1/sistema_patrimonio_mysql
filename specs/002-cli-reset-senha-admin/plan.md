# Implementation Plan: CLI de Reset Administrativo de Senha

**Branch**: `002-cli-reset-senha-admin` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-cli-reset-senha-admin/spec.md`

## Summary

Adicionar o subcomando `reset-password` à CLI existente (`app/cli.py`), permitindo que um
administrador com acesso ao servidor redefina a senha de um usuário **local** via terminal,
com entrada oculta (dupla confirmação). A implementação é **um invocador terminal do
mecanismo existente**: toda a regra (política mín. 8 caracteres, hash PBKDF2 já em uso,
limpeza de lockout, invalidação de todas as sessões, gravação atômica) permanece em
`auth_service.reset_password` (linha 176), já usada pela administração web. Auditoria via
`audit_service.write_audit` com o eventoexistente `RESET_SENHA` — ator da aplicação nulo, username do alvo, origem `CLI` e
operador do SO capturado automaticamente (`SUDO_USER` → `getpass.getuser()`; decisão
D-2), nunca a senha. Semântica transacional reset×auditoria determinada no §5.1.
**Nenhuma alteração de schema,
RBAC, AD, configuração ou fluxos existentes.** Arquivo de código modificado: **apenas
`app/cli.py`** (+ novo arquivo de testes + atualização de documentação).

## Technical Context

**Language/Version**: Python 3.10+ (stack existente, inalterada)

**Primary Dependencies**: Nenhuma nova. Reutiliza: argparse + getpass (stdlib, já usados
em `app/cli.py`), `auth_service.reset_password`/`hash_password`, `audit_service.write_audit`.
Stack (FastAPI/SQLAlchemy/Jinja2/pytest) não é tocada por esta feature.

**Storage**: MariaDB (produção, via `DATABASE_URL`); SQLite in-memory na suíte de testes.
**Zero alteração de schema** — a feature usa apenas colunas existentes de `users`
(`password_hash`, `failed_login_attempts`, `locked_until`), linhas de `user_sessions`
(exclusão) e um append em `audit_logs`.

**Testing**: pytest ≥8 (padrão existente). Novo arquivo `tests/test_cli_reset_password.py`
com injeção do leitor de senha (sem depender de terminal interativo). Suíte existente
intacta — `tests/test_auth.py` é o regressão direto do serviço reutilizado.

**Target Platform**: Terminal do servidor (Linux/Uvicorn — mesmo ambiente de `run.py`).

**Project Type**: Extensão da CLI administrativa de um sistema web monolítico em camadas.

**Performance Goals**: Não aplicável (operação administrativa interativa, única por execução).

**Constraints**: A senha JAMAIS pode aparecer em: argv do processo, eco do terminal, logs
(`data/logs/`), trilha de auditoria, mensagens de erro/sucesso. Em erro **anterior à
gravação**, o comando falha com `exit code 1` e o estado do alvo permanece inalterado;
falha de auditoria **após** reset já efetivado não desfaz o reset — o comando termina
com `exit code 0` e aviso genérico ao operador (semântica real definida no §5.1).
`main()` da CLI executa `init_db()` — comportamento idêntico aos comandos existentes
(não alterado).

**Scale/Scope**: 1 subcomando novo; ~40–60 linhas em `app/cli.py`; 1 arquivo de testes
novo (~10 casos); 4 arquivos de documentação atualizados.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio (Constitution v1.0.0) | Status | Observação |
|---|---|---|
| I. Preservação / evolução incremental | ✅ PASS | Extensão puramente aditiva: novo subparser + novo branch + função auxiliar em `app/cli.py`. Nenhum comando, comportamento ou rota existente é alterado |
| II. Arquitetura em camadas | ✅ PASS | A CLI apenas orquestra entrada e mensagens; nenhuma regra de negócio nova fora do service |
| III. Regras de negócio nos services | ✅ PASS | Política, hash, lockout e invalidação de sessões permanecem 100% em `auth_service.reset_password` — o comando não reimplementa nada |
| IV. Integridade patrimonial / movimentações | ✅ PASS | Não toca bens, movimentações ou custódia |
| V. Integridade do inventário | ✅ PASS | Não toca inventário |
| VI. Segurança por padrão (auth, RBAC, AD, credenciais) | ✅ PASS | Senha só por prompt sem eco; proibido argv/env/arquivo; nada de credencial em log/auditoria. CLI sem login = padrão existente dos comandos atuais (barreira é o acesso ao servidor) — comportamento documentado, não alterado. AD nunca é modificado (recusa explícita) |
| VII. MariaDB / proteção de dados / DDL aditivo | ✅ PASS | **Zero DDL.** Apenas UPDATE de colunas existentes, DELETE de sessões do alvo e INSERT em `audit_logs` |
| VIII. Testes como não-regressão | ✅ PASS | Novos testes para o novo comportamento; suíte existente intacta; `test_auth.py` continua verde (serviço não é alterado) |
| IX. Auditoria das operações relevantes | ✅ PASS | 1 registro por execução (sucesso/falha) via `write_audit`, evento `RESET_SENHA` do catálogo — sem a senha (Princípio VI) |
| X. Interface consistente | ✅ PASS | Nenhuma UI web; mensagens da CLI seguem o padrão atual (`Erro:`/`Sucesso:`, pt-BR) e prompts espelham o `create-user` |
| XI. Documentação fiel | ✅ PASS | README, `docs/ARQUITETURA_E_MANUTENCAO.md`, `docs/GUIA_DE_MANUTENCAO.md` e artigo da central de ajuda atualizados na mesma tarefa (§12) |
| XII. Especificação + validação | ✅ PASS | Spec aprovada com decisões D-1..D-4; validação executável definida em `quickstart.md` |

**Resultado: 12/12 PASS — sem violações.** Re-check pós-Phase 1: mantém-se 12/12 (o
design não introduz nenhuma complexidade além da extensão aditiva da CLI).

## Project Structure

### Documentation (this feature)

```text
specs/002-cli-reset-senha-admin/
├── plan.md                             # This file
├── research.md                         # Phase 0 — decisões R1..R9 verificadas no código
├── data-model.md                       # Phase 1 — entidades tocadas (nenhum schema novo)
├── quickstart.md                       # Phase 1 — protocolo de validação executável
├── contracts/
│   └── cli-reset-password-contract.md  # Phase 1 — contrato do subcomando (interface CLI)
├── checklists/
│   └── requirements.md                 # (da etapa /speckit-specify)
└── tasks.md                            # Phase 2 output (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
app/
├── cli.py                          # ÚNICO arquivo de código modificado:
│                                   #   1. subparser "reset-password" (argparse)
│                                   #   2. branch no if/elif de main() [mesma função]
│                                   #   3. funções auxiliares run_reset_password(db, ...)
│                                   #      e _get_os_operator() (D-2)
├── services/
│   ├── auth_service.py             # NÃO modificado — reset_password (L176) é o caminho único
│   ├── audit_service.py            # NÃO modificado — write_audit + ACTION_PASSWORD_RESET reutilizados
│   └── help_service.py             # MODIFICADO (docs): artigo da central de ajuda que lista comandos CLI
└── (todo o restante intocado: api/, models/, schemas/, web/, config.py, database.py)

tests/
├── test_cli_reset_password.py      # NOVO — testes do subcomando (leitor de senha injetado)
└── (suíte existente intacta — conftest.py reaproveitado)

README.md                           # MODIFICADO (docs): seção de comandos CLI
docs/ARQUITETURA_E_MANUTENCAO.md    # MODIFICADO (docs): listas de comandos (linhas ~130 e ~1100)
docs/GUIA_DE_MANUTENCAO.md          # MODIFICADO (docs): procedimento de recuperação de acesso
```

**Structure Decision**: estrutura single-project existente mantida. A feature toca **um
arquivo de código** (`app/cli.py`), cria **um arquivo de testes** e atualiza **documentação**
— coerente com o escopo mínimo exigido pela spec (Out of Scope proíbe refatoração da CLI).

## Complexity Tracking

> Sem violações de Constitution — tabela vazia por design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

---

# Plano Técnico Detalhado

## 1. Fluxo da Solução (design)

```text
Operador (shell do servidor)
  ↓
python -m app.cli reset-password --username <usuario>
  ↓
main() — init_db() + ensure_default_roles() [padrão existente, inalterado]
  ↓
run_reset_password(db, username, password_reader=getpass.getpass)
  ├─ 1. Localiza User por username (strip; match exato — mesma normalização do login)
  │     ├─ não existe → write_audit(FAILURE, ref=username informado) → print "Erro:" → return 1
  │     └─ auth_provider == 'ad' → write_audit(FAILURE) → "Erro: usuário autenticado pelo
  │        Active Directory; este comando redefine apenas senha local..." → return 1
  ├─ 2. Nova senha = password_reader("Nova senha: ")      # sem eco
  │     Confirmação  = password_reader("Confirme a nova senha: ")  # sem eco
  │     ├─ divergem / vazias / EOFError → write_audit(FAILURE) → "Erro: as senhas não
  │     │  conferem." (ou mensagem de entrada indisponível) → return 1   [decisão D-1]
  ├─ 3. reset_password(db, user, nova_senha)   ← ÚNICA escrita; service existente:
  │        valida política (≥8) · hash PBKDF2 existente · zera falhas/lockout ·
  │        exclui sessões do usuário · commit atômico · ValueError em política
  │        [o commit interno do service EFETIVA a senha AQUI — antes da auditoria, §5.1]
  │     ├─ ValueError → write_audit(FAILURE) → "Erro: {mensagem atual da política}" → return 1
  │     └─ exceção inesperada (banco) → write_audit(FAILURE, description genérica)
  │        → "Erro: falha ao atualizar a senha. Tente novamente." → return 1
  │        [nenhum detalhe interno na mensagem]
  ├─ 4. operador_so = _get_os_operator()  # SUDO_USER → getpass.getuser(); indisponível → None (D-2)
  │     write_audit(SUCCESS, user=None, username=alvo, action=RESET_SENHA,
  │        module="Usuários", resource="User", resource_id, resource_ref=username,
  │        description="Redefinição de senha do usuário X (sessões invalidadas) — origem: CLI",
  │        new_data={"origem": "CLI", "operador_so": operador_so})  # operador omitido se None
  │        [decisão D-2; ip_address=None; NUNCA a senha]
  │     └─ write_audit lançar exceção → print "Atenção: não foi possível registrar o
  │        evento de auditoria." (sem detalhes internos) — o resultado do comando
  │        NÃO muda (§5.1)
  └─ 5. print "Sucesso: senha redefinida..." → return 0
```

Pontos de segurança do design:

- A senha existe **apenas** em memória (variável local) entre o prompt e a chamada do
  service; nunca é impressa, logada, gravada ou serializada.
- O leitor de senha é **injetável** (`password_reader`), permitindo testes sem terminal
  e garantindo que a implementação de produção use `getpass.getpass` (sem eco).
- A auditoria é gravada em **transação própria** (commit interno de `write_audit`),
  separada do commit do reset — não existe atomicidade entre elas na arquitetura atual,
  e esta feature não cria uma (§5.1). Falha de auditoria é não-bloqueante e nunca
  expõe detalhes internos (SQL, stack trace).

## 2. Componentes Afetados (arquivos e funções reais)

| Arquivo | Ação | O quê exatamente |
|---|---|---|
| `app/cli.py` | **MODIFICAR** | (a) `subparsers.add_parser("reset-password", help=...)` + `add_argument("--username", required=True)`; (b) branch `elif args.command == "reset-password":` chamando o auxiliar; (c) nova função de módulo `run_reset_password(db, username, password_reader=getpass.getpass) -> int` que orquestra localização → prompts → `reset_password` → auditoria → mensagens; (d) função auxiliar `_get_os_operator() -> Optional[str]` para a decisão D-2 (ver §5). Imports: `getpass` (topo do módulo, no padrão existente), `os`, `reset_password` e `write_audit`/`ACTION_PASSWORD_RESET`/`RESULT_*` |
| `app/services/auth_service.py` | **NÃO modificar** | `reset_password` (L176–191) já faz: política ≥8 (`ValueError`), `hash_password`, zera `failed_login_attempts`/`locked_until`, exclui `UserSession` do usuário, `commit` único |
| `app/services/audit_service.py` | **NÃO modificar** | `write_audit` (L129) já suporta `user=None` + `username=` (usado no fluxo AD); `ACTION_PASSWORD_RESET="RESET_SENHA"` (L32); `RESULT_SUCCESS/FAILURE` (L123–126) |
| `app/services/ad_service.py` | **NÃO modificar** | Constantes `PROVIDER_LOCAL/PROVIDER_AD` (L43–44) e sentinel `password_hash="!ad-external"` (L285) são a base da recusa AD — somente lidos |
| `app/models/user.py`, `session.py`, `audit_log.py` | **NÃO modificar** | Entidades usadas como estão |
| `tests/test_cli_reset_password.py` | **CRIAR** | Casos listados em §10; usa fixtures `db_session` do `conftest.py` existente |
| `README.md` | **MODIFICAR (docs)** | Seção de comandos CLI (exemplos em L167/564–583): incluir `reset-password` (sem senha em exemplo — só o formato do comando) |
| `docs/ARQUITETURA_E_MANUTENCAO.md` | **MODIFICAR (docs)** | Listas de comandos (L130 e L1100): acrescentar `reset-password` |
| `docs/GUIA_DE_MANUTENCAO.md` | **MODIFICAR (docs)** | Procedimento operacional de recuperação de acesso (L137/158 região de usuários): quando usar, aviso de sessões invalidadas e de que não altera AD |
| `app/services/help_service.py` | **MODIFICAR (docs)** | Artigo da central de ajuda que cobre administração de usuários/CLI: acrescentar o novo comando (artigo exato identificado na tarefa de implementação — busca por "create-user" em `get_articles()`) |
| `app/config.py`, `app/database.py`, RBAC, AD, templates | **NÃO modificar** | Nenhuma necessidade — confirmado pela análise (sem nova variável de ambiente, sem DDL, sem permissão nova) |

## 3. Decisões D-1..D-4 do spec — como são atendidas

| Decisão | Atendimento no design |
|---|---|
| **D-1** — dupla entrada oculta | Dois prompts `password_reader` ("Nova senha:" / "Confirme a nova senha:"); divergência → abort sem alteração (espelha `create-user` L147–151) |
| **D-2** — ator nulo + origem CLI + operador do SO | `write_audit(user=None, username=<alvo>, description="... — origem: CLI", new_data={"origem": "CLI", "operador_so": ...})`; operador capturado por função auxiliar `_get_os_operator()` (`SUDO_USER` → `getpass.getuser()` → `None`), **sem** argumento `--operator`; indisponibilidade não falha o comando. Precedente `user=None`: fluxo AD |
| **D-3** — reset permitido p/ inativo sem reativar | Nenhuma verificação de `is_active` no comando — o service não a faz; `is_active` permanece intocado (o reset limpa apenas lockout temporário, não desativação) |
| **D-4** — nome `reset-password` | `subparsers.add_parser("reset-password")` — kebab-case inglês como `create-user` |

## 4. Segurança e Autorização

- **Hash**: o existente (`pbkdf2_sha256$iter$salt$hash`, PBKDF2-HMAC-SHA256, salt por
  senha, `AUTH_PBKDF2_ITERATIONS`, default 600000). Nenhuma segunda implementação.
- **Política de senha**: a atual (mínimo 8 caracteres, validada no service). Nenhuma
  política nova; nenhuma enfraquecida.
- **Exposição no processo**: senha nunca em argv (não existe opção para isso), nunca em
  env, nunca em arquivo; apenas variável local em memória. `getpass` desabilita eco.
- **Exposição em logs**: nada é escrito em `data/logs/`; mensagens do comando não
  reproduzem a senha nem partes dela; falhas de banco viram mensagem genérica.
- **Sessões**: exclusão de todas as `UserSession` do alvo é feita pelo service (efeito
  obrigatório do reset — coerente com `change_password` e com a admin web).
- **Autorização**: a barreira é o acesso ao shell do servidor — idêntico aos comandos
  `create-user` e `move` existentes (a CLI não autentica; padrão preservado, registrado
  na spec como premissa). O comando não concede nem verifica permissões RBAC.
- **AD**: recusa explícita antes de qualquer prompt de senha; nenhum código de
  comunicação com AD é tocado; o sentinel `!ad-external` nunca é sobrescrito.

## 5. Auditoria (rastreabilidade)

Um registro por execução (sucesso **ou** falha), no formato do precedente web
(`admin_routes.admin_reset_password`):

| Campo | Valor |
|---|---|
| `action` | `RESET_SENHA` (`ACTION_PASSWORD_RESET` — catálogo existente) |
| `module` / `resource` | `Usuários` / `User` |
| `resource_id` / `resource_ref` | id do alvo (quando existente) / username |
| `user_id` / `username` | `NULL` / username do **alvo** (ator da aplicação nulo — D-2; precedente `ad_service`) |
| `ip_address` | `NULL` (sem contexto HTTP na CLI) |
| `result` | `SUCCESS` ou `FAILURE` |
| `description` | "Redefinição de senha do usuário X (sessões invalidadas) — origem: CLI" (sucesso); falhas com motivo curto e não sensível ("usuário não encontrado", "usuário AD", "senhas não conferem", "política de senha", "falha na atualização") |
| `new_data` | `{"origem": "CLI", "operador_so": "<usuário do SO>"}` quando identificado; `{"origem": "CLI"}` quando indisponível (campo do operador permanece nulo — D-2). **Jamais** contém a senha ou o hash |
| `previous_data` | **Não usado** — conteria o hash anterior (material sensível) |

### 5.1 Semântica transacional reset × auditoria (determinada do código)

- `reset_password` grava hash + sessões e efetiva com **commit interno** — a senha nova
  vale a partir desse momento, **antes** de qualquer auditoria.
- `write_audit` faz seu próprio `db.add + db.commit` (transação separada;
  `audit_service.py:172-175`) — **não existe atomicidade** entre reset e auditoria na
  arquitetura atual, e esta feature **não cria uma** (nenhuma alteração em
  `auth_service.py` ou `audit_service.py`).
- **Caminhos de erro ANTES do service** (inexistente, AD, confirmação divergente, EOF,
  política): nada foi alterado; a auditoria de falha é tentada e, se ela própria falhar,
  o resultado permanece **exit 1** com a mensagem original do erro.
- **Caminho de sucesso**: se `write_audit` falhar, o reset **já está efetivado** (senha
  nova vigente, sessões invalidadas). O comando informa sucesso, imprime um único aviso
  ("Atenção: não foi possível registrar o evento de auditoria.") e termina com **exit 0**
  — o exit code reflete o estado efetivo do alvo (senha alterada), evitando que o
  operador acredite que o reset falhou e o repita. Nenhum detalhe interno é exposto
  (FR-013); a tentativa de auditoria é sempre executada (best-effort — FR-011).

## 6. Tratamento de Erros (contrato de saída)

| Situação | Saída do comando | Estado do alvo | Audit |
|---|---|---|---|
| Sucesso | `Sucesso: senha redefinida para o usuário '<username>'. Sessões ativas foram invalidadas.` → exit 0 | senha nova válida; sessões antigas mortas; lockout zerado; demais atributos intactos | 1× SUCCESS |
| Usuário inexistente | `Erro: usuário '<username>' não encontrado.` → exit 1 | — (nada) | 1× FAILURE |
| Usuário AD | `Erro: '<username>' autentica pelo Active Directory. Este comando redefine apenas a senha local do SisPatrimônio e não altera credenciais do AD.` → exit 1 | hash sentinela intacto | 1× FAILURE |
| Senha < 8 caracteres | `Erro: A nova senha deve ter no mínimo 8 caracteres.` (mensagem atual do service) → exit 1 | hash antigo intacto; nada mudou | 1× FAILURE |
| Confirmação divergente | `Erro: as senhas não conferem.` → exit 1 | nada mudou | 1× FAILURE |
| Entrada vazia / EOF / Ctrl-D durante prompt | `Erro: entrada de senha indisponível. Operação abortada.` → exit 1 | nada mudou | 1× FAILURE |
| Falha de banco/inesperada na gravação | `Erro: falha ao atualizar a senha. Tente novamente.` → exit 1 | commit atômico do service evita alteração parcial | 1× FAILURE (descrição genérica) |
| Auditoria falha APÓS reset efetivado (§5.1) | `Sucesso: ...` + `Atenção: não foi possível registrar o evento de auditoria.` → **exit 0** | **senha nova vigente; sessões invalidadas** (já commitadas antes da auditoria) | 0 registros desta execução (best-effort) |
| Auditoria falha em caminho de erro (§5.1) | mensagem original do erro + aviso de auditoria → exit 1 | nada alterado | 0 registros desta execução |
| Usuário local inativo | **Permite** (D-3): fluxo normal de sucesso; `is_active` permanece `False` | idem sucesso | 1× SUCCESS |
| Usuário local em lockout | **Permite** (fluxo normal): service zera `locked_until`/`failed_login_attempts` | desbloqueado como parte do reset | 1× SUCCESS |

## 7. Testes — Estratégia

**Novo arquivo `tests/test_cli_reset_password.py`** (pytest, fixtures do `conftest.py`
existente: `db_session`; PBKDF2 reduzido p/ velocidade). A função `run_reset_password`
recebe `password_reader` injetável → testes não usam terminal:

1. **Sucesso**: hash muda (`verify_password(nova)` true / antiga false); exit 0; usuário
   com perfil atribuído mantém o perfil; `is_active`/`email`/`full_name` intactos.
2. **Sessões invalidadas**: criar `UserSession` p/ o alvo → após reset, 0 sessões.
3. **Lockout zerado**: alvo com `failed_login_attempts=9`, `locked_until` futuro → após
   reset, zerados (e continua o que era quanto a `is_active`).
4. **AD recusado**: `User(auth_provider="ad", password_hash="!ad-external")` → exit 1,
   hash intacto, mensagem menciona AD/local, 0 prompts consumidos (reader não chamado).
5. **Inexistente**: exit 1, nada criado/alterado, 0 prompts consumidos.
6. **Política**: senha de 7 caracteres → exit 1, `ValueError` do service propagada como
   mensagem atual; hash antigo intacto.
7. **Confirmação divergente**: reader retorna "A", depois "B" → exit 1, nada mudou.
8. **Inativo**: `is_active=False` → exit 0, senha trocada, `is_active` permanece `False` (D-3).
9. **EOF na entrada**: reader levanta `EOFError` → exit 1, nada mudou.
10. **Auditoria sem segredos**: para sucesso e para falhas → 1 registro por execução;
    `action == "RESET_SENHA"`; `result` correto; `username` = alvo; e a senha
    (nem substring) aparece em `description`/`new_data`/`previous_data` de **qualquer**
    registro.
11. **Operador do SO (D-2)**: com `SUDO_USER` no ambiente → `new_data` contém esse valor;
    sem `SUDO_USER`, com `getpass.getuser()` simulado → fallback usado; sem nenhum →
    `new_data` contém apenas `origem: CLI`, o comando não falha e não levanta exceção
    (US3 cenário 4 do spec).
12. **Falha de auditoria (§5.1)**: `write_audit` simulado para lançar exceção —
    (a) após reset efetivado: exit 0, aviso impresso, senha alterada e sessões
    invalidadas; (b) em caminho de erro (ex.: usuário AD): exit 1, mensagem original,
    nada alterado.
13. **Regressão indireta**: rodar a suíte existente — `tests/test_auth.py` (17) e
    `tests/test_rbac.py` continuam com o comportamento atual (serviço não alterado).

**Nenhum teste existente é editado** (Constitution VIII). `main()` não é exercitado nos
testes (executa `init_db()` no banco de `DATABASE_URL`) — a unidade testada é
`run_reset_password` com a sessão do fixture.

## 8. Estratégia de Migração / Compatibilidade

- **Migração**: nenhuma (zero DDL; sem variável de ambiente nova; sem seed).
- **Compatibilidade comportamental**: 100% — nenhum comando, rota, fluxo ou tela existente
  muda. O único efeito colateral visível é a nova linha na ajuda da CLI (`--help`).
- **Compatibilidade de dados**: apenas UPDATE de `users.<3 colunas>`, DELETE de
  `user_sessions` do alvo e INSERT em `audit_logs` — todos efeitos do serviço existente.
- **Baseline 001**: o contrato `specs/001-sistema-existente/contracts/cli-db-contract.md`
  é um snapshot datado ("estado atual" de 14/09/2026) e **não será editado** nesta feature;
  o contrato desta feature vive em `contracts/cli-reset-password-contract.md`. Registrado
  como risco documental baixo (§11) — eventual atualização da baseline é tarefa própria.

## 9. Riscos

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Operador espera `--password` (como `create-user` oferece) e tenta passar a senha em argv | Média | Baixo | O comando recusa entrada não interativa por design; help text do subparser explica o prompt oculto; docs destacam a diferença deliberada |
| Reset executado por engano no usuário errado (CLI não confirma identidade do operador) | Baixa | Médio | Dupla confirmação de senha (D-1) + auditoria obrigatória por execução (D-2) + username explícito no argumento e nas mensagens |
| `write_audit` falhar (banco) após reset efetivado | Baixa | Médio | §5.1: exit 0 + aviso único ao operador (o estado do alvo é a verdade); sem detalhes internos; tentativa de auditoria sempre executada |
| Documentação da baseline 001 ficar defasada quanto à lista de comandos | Alta | Baixo | Aceito e registrado (§8/§11); atualização da baseline é tarefa própria |

## 10. Arquivos que serão modificados (resumo da entrega)

1. `app/cli.py` — subcomando `reset-password` + função `run_reset_password` (único código).
2. `tests/test_cli_reset_password.py` — novo arquivo de testes (§7).
3. `README.md`, `docs/ARQUITETURA_E_MANUTENCAO.md`, `docs/GUIA_DE_MANUTENCAO.md`,
   `app/services/help_service.py` — documentação fiel (Constitution XI), na mesma tarefa.

## 11. Arquivos que NÃO devem ser modificados

`app/services/auth_service.py` · `app/services/audit_service.py` · `app/services/ad_service.py`
· `app/models/**` · `app/api/**` · `app/web/**` · `app/schemas/**` · `app/config.py` ·
`app/database.py` · `tests/conftest.py` e demais testes existentes · `.env`/`.env.un~` ·
`requirements.txt` · `specs/001-sistema-existente/**` (baseline — snapshot datado) ·
`run.py`, `seed_demo.py` · banco de dados (nenhum DDL, nenhuma migração).

## 12. Documentação (mesma tarefa — Constitution XI)

| Arquivo | Conteúdo a acrescentar |
|---|---|
| `README.md` | Linha na lista de comandos CLI: `python -m app.cli reset-password --username <usuario>` (senha sempre por prompt oculto; nunca como argumento) |
| `docs/ARQUITETURA_E_MANUTENCAO.md` | Atualizar as 2 listas de comandos (L~130, L~1100) |
| `docs/GUIA_DE_MANUTENCAO.md` | Procedimento "Recuperação de acesso de usuário local": quando usar, aviso de invalidação de sessões, aviso de que usuários AD devem ser tratados no AD |
| `app/services/help_service.py` | Artigo de administração de usuários/CLI: incluir o comando e a regra AD (artigo exato a confirmar na implementação) |

## 13. Estratégia de Implementação Incremental

1. **T1 — CLI**: subparser + `run_reset_password` + `_get_os_operator` + branch em `main()`
   (código mínimo, sem tocar em mais nada).
2. **T2 — Testes**: `tests/test_cli_reset_password.py` (casos §7) — rodar isolado.
3. **T3 — Regressão**: suíte completa (`pytest`) — resultado esperado: todos os testes
   existentes no estado atual (153/154 com a falha defasada conhecida de lockout,
   documentada em 001) + novos testes verdes.
4. **T4 — Docs**: README + 2 docs de manutenção + artigo da central de ajuda.
5. **Validação final**: protocolo de `quickstart.md` (testes + verificação manual com
   banco de destino).

Cada etapa é verificável isoladamente; nenhuma etapa toca arquivos de §11.
