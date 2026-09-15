# Phase 0 — Research & Decisions: 002-cli-reset-senha-admin

**Feature**: CLI de Reset Administrativo de Senha | **Date**: 2026-09-15

> Não há unknowns de tecnologia (stack existente). Toda decisão abaixo foi validada por
> leitura dos arquivos citados. As decisões D-1..D-4 já foram aprovadas pelo responsável
> (registradas no spec) — R1..R9 cobrem as decisões **técnicas** de integração.

---

## R1. Reusar o serviço existente ou criar caminho próprio?

- **Decision**: Reutilizar exclusivamente `auth_service.reset_password(db, user, new_password)`.
- **Rationale**: já concentra exatamente as regras exigidas pela spec (política ≥ 8,
  hash existente, zera `failed_login_attempts`/`locked_until`, exclui `UserSession` do
  usuário, commit atômico) e é o mesmo caminho da administração web — zero duplicação,
  zero divergência comportamental.
- **Alternatives considered**: duplicar a lógica no CLI — rejeitada (Constitution III:
  proíbe segunda implementação de regra; spec FR-007/FR-008 proíbem).
- **Verificação**: `app/services/auth_service.py:176-191`; uso web em
  `app/web/admin_routes.py:360-384`.

## R2. Como integrar ao padrão da CLI existente?

- **Decision**: seguir o padrão do `create-user`: (a) `subparsers.add_parser("reset-password", ...)`
  com `--username` obrigatório; (b) branch `elif args.command == "reset-password":` no
  if/elif de `main()`; (c) lógica em **função de módulo** `run_reset_password(db, username,
  password_reader) -> int` chamada pelo branch.
- **Rationale**: função de módulo (em vez de lógica inline no branch) permite teste direto
  com sessão injetada e leitor de senha injetado — necessário porque `main()` executa
  `init_db()` contra o banco de `DATABASE_URL` e não é testável isoladamente.
- **Alternatives considered**: lógica inline no branch (padrão atual dos comandos) —
  rejeitada para este comando porque os requisitos de teste (FR-015) e de injeção de
  entrada exigem o auxiliar; refatorar os demais comandos para o mesmo estilo — rejeitada
  (spec Out of Scope; Constitution I).
- **Verificação**: estrutura de `app/cli.py` (subparsers L32+; branches L68+; `create-user`
  L51–59/143–176).

## R3. Como receber a senha sem expô-la?

- **Decision**: dois prompts via `getpass.getpass` (sem eco), **sem** opção `--password`.
  O leitor é parâmetro injetável (`password_reader=getpass.getpass`) e os prompts são
  "Nova senha: " / "Confirme a nova senha: " (decisão D-1).
- **Rationale**: spec FR-004 proíbe argv/env/arquivo; `getpass` já é o padrão do projeto
  (`create-user`); a injeção viabiliza os testes sem terminal.
- **Alternatives considered**: opção `--password` como no `create-user` — rejeitada: a
  spec **exige** mais restrição que o comando existente (senha não pode aparecer em
  argv/processo; `ps` a revelaria). Divergência deliberada e documentada (risco §9 do plan).
- **Verificação**: `app/cli.py:144-151` (getpass + confirmação no create-user);
  `app/services/ad_service.py` usa `user=None` na auditoria — sem relação.

## R4. Como identificar e recusar usuários AD?

- **Decision**: verificar `user.auth_provider == "ad"` **antes** de qualquer prompt de
  senha; recusar com mensagem explícita ("redefine apenas senha local / não altera
  credenciais do AD"). Constante de comparação: literal `"ad"` no CLI ou import de
  `PROVIDER_AD` de `ad_service` — **a definir na tarefa de implementação** (preferência:
  importar a constante, sem duplicar vocabulário). O checador nunca consulta o AD.
- **Rationale**: usuários AD têm `password_hash="!ad-external"` (sentinela propositalmente
  inválida) — sobrescrevê-la criaria hash local válido para conta cuja autenticação
  legítima é externa, quebrando o modelo de provedor.
- **Alternatives considered**: permitir reset (sobrescreveria a sentinela) — rejeitada
  (spec FR-003; Constitution VI: AD autentica, não autoriza — e nunca é modificado);
  detectar AD pelo sentinel `!ad-external` em vez de `auth_provider` — rejeitada: campo
  dedicado existe e é o padrão usado nos templates/rotas.
- **Verificação**: `app/services/ad_service.py:282-288` (provisionamento grava sentinela +
  `PROVIDER_AD`), `app/services/ad_service.py:43-44` (constantes), `auth_provider.py:90-97`
  (roteamento por provedor).

## R5. Como registrar a auditoria (ator nulo)?

- **Decision**: `write_audit(db, user=None, username=<alvo>, action=ACTION_PASSWORD_RESET,
  module="Usuários", resource="User", resource_id=<id|None>, resource_ref=<username>,
  ip_address=None, result=SUCCESS|FAILURE, description=...,
  new_data={"origem": "CLI", "operador_so": <operador|omitido>})`.
- **Rationale**: `write_audit` já suporta `user=None` + `username=` explicitamente
  (docstring: "quando o usuário não existe ou não autenticou"); o fluxo AD grava assim.
  Decisão D-2 **revisada pelo responsável**: além do ator nulo e da origem `CLI`, o
  operador do SO é capturado automaticamente — prioridade `SUDO_USER` (execução via
  `sudo`), fallback `getpass.getuser()`, sem argumento manual; se indisponível, o campo
  permanece ausente/ nulo e a operação NÃO falha por isso. O operador do SO vai em
  `new_data` (não há coluna dedicada para ele; `username` permanece reservado ao alvo,
  coerente com o modelo atual em que `username` identifica quem agiu ou o alvo do login).
- **Alternatives considered**: campo `previous_data` — não usado (conteria o hash
  anterior, material sensível); coluna nova para operador de SO — rejeitada (exigiria DDL,
  fora do escopo); `--operator` — proibido pela D-2 revisada.
- **Verificação**: `app/services/audit_service.py:129-152` (assinatura + docstring),
  `ad_service.py:263-278` (precedente `user=None`), `admin_routes.py:370-381` (precedente
  web do `RESET_SENHA`).

## R6. Usuário inativo e usuário em lockout — permitir?

- **Decision**: permitir ambos (D-3 aprovada): **nenhuma** verificação de `is_active` no
  comando; o service zera lockout temporário como parte do reset; `is_active` não é tocado.
- **Rationale**: coerente com a administração web atual (que também não impede); útil em
  recuperação de acesso (reativar acesso exige passo separado de desbloqueio, explícito).
- **Alternatives considered**: recusar inativos — rejeitada (criaria passo extra sem
  ganho de segurança: quem tem shell já pode reativar pelo admin web).
- **Verificação**: `reset_password` (L176–191) não consulta `is_active`;
  `admin_reset_password` (L360–384) também não.

## R7. Contrato de saída e códigos de erro

- **Decision**: função auxiliar retorna `int` (0 sucesso / 1 falha); o branch em `main()`
  faz `sys.exit(code)`. Mensagens no padrão existente `Erro:`/`Sucesso:` em pt-BR.
  Exceção inesperada → mensagem genérica ("falha ao atualizar a senha. Tente novamente."),
  sem detalhes internos; `EOFError`/entrada vazia → "entrada de senha indisponível".
- **Rationale**: `sys.exit(1)` é o padrão atual da CLI; separar retorno de saída permite
  testar o auxiliar sem encerrar o processo de teste. `run()` principal mantém o padrão
  dos demais comandos.
- **Alternatives considered**: exit codes múltiplos por tipo de erro — rejeitada (nenhum
  consumidor de script exige; simplicidade do padrão atual).
- **Verificação**: padrão `Erro:`/`sys.exit(1)` em `app/cli.py` (`show` L83–84,
  `create-user` L174–176).

## R8. Estratégia de testes sem terminal (e sem depender do MariaDB de produção)

- **Decision**: testar `run_reset_password` diretamente com a sessão do fixture
  `db_session` (SQLite in-memory) e `password_reader` injetado (lista/lambda/EOFError).
  `main()` não é exercitado. Auditoria verificada consultando `AuditLog` na mesma sessão.
- **Rationale**: `main()` executa `init_db()` no banco de `DATABASE_URL` (indisponível/
  indesejado nos testes); os caminhos testáveis são exatamente os que contêm comportamento.
  O banco da suíte permanece o existente (SQLite in-memory via `tests/conftest.py`,
  infraestrutura de teste já do projeto — nenhuma adaptação criada para esta feature).
- **Alternatives considered**: testar via subprocesso com pty — rejeitada: frágil,
  dependente de plataforma e desnecessário dado o design injetável; mockar `init_db` para
  testar `main()` — rejeitada: testaria colagem, não comportamento.
- **Verificação**: `tests/conftest.py` (fixtures `db_session`, PBKDF2=1000 em teste);
  `app/database.py` (engine construído no import — por isso `main()` fora da unidade de teste).

## R9. Documentação a atualizar (Constitution XI)

- **Decision**: 4 alvos, todos com localização verificada: `README.md` (lista de comandos
  CLI, L167 e bloco L564–583), `docs/ARQUITETURA_E_MANUTENCAO.md` (L130 e L1100),
  `docs/GUIA_DE_MANUTENCAO.md` (região L137/158 — procedimento de usuários),
  `app/services/help_service.py` (central de ajuda — artigo de administração de
  usuários/CLI a localizar por "create-user" em `get_articles()`).
- **Rationale**: são os únicos lugares que enumeram comandos CLI ou procedimentos de
  usuário; nenhum exemplo de doc conterá senha (o `create-user` atual mostra senha em
  exemplo — o novo comando não terá exemplo com senha, apenas o formato).
- **Alternatives considered**: atualizar a baseline 001 (contracts) — rejeitada: snapshot
  datado; atualização de baseline é tarefa própria (risco registrado no plan §9).

---

## Resumo de resolução de unknowns

| Unknown/decisão | Resolução |
|---|---|
| Mecanismo de reset | Reuso total de `auth_service.reset_password` (R1) |
| Integração CLI | Subparser + branch + função auxiliar testável (R2) |
| Entrada da senha | getpass duplo, sem argv, reader injetável (R3) |
| Usuários AD | Recusa antes do prompt por `auth_provider` (R4) |
| Auditoria | `write_audit` `user=None` + `username` do alvo + origem CLI + operador do SO (SUDO_USER→getpass.getuser→nenhum) em `new_data` (R5) |
| Inativo/lockout | Permitidos, `is_active` intocado (R6) |
| Saída/erros | return int → `sys.exit`; padrão Erro:/Sucesso: (R7) |
| Testes | Auxiliar + fixtures existentes; `main()` fora de escopo de teste (R8) |
| Docs | 4 alvos mapeados (R9) |
