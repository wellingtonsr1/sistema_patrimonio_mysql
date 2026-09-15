# Phase 1 — Data Model: 002-cli-reset-senha-admin

**Feature**: CLI de Reset Administrativo de Senha | **Date**: 2026-09-15

> **Nenhuma entidade nova. Nenhuma coluna, tabela, índice ou constraint nova (zero DDL).**
> Este documento mapeia as entidades **existentes** tocadas pela feature e as transições
> que o comando produz — todas via `auth_service.reset_password` (comportamento atual,
> preservado).

---

## 1. Entidades tocadas

### 1.1 User — tabela `users` (`app/models/user.py`) — **UPDATE de 3 campos**

| Campo | Tipo atual | Efeito do reset | Quem escreve |
|---|---|---|---|
| `password_hash` | String(255) NOT NULL | Substituído por novo hash PBKDF2 do formato existente `pbkdf2_sha256$iter$salt$hash` | `auth_service.reset_password` |
| `failed_login_attempts` | Integer NOT NULL default 0 | Zerado | idem |
| `locked_until` | DateTime null | Zerado (`None`) | idem |
| `auth_provider` | String(20) NOT NULL default 'local' | **Intocado** — `'ad'` causa recusa antes de qualquer escrita | — |
| `is_active` | Boolean default True | **Intocado** (decisão D-3: inativo permanece inativo) | — |
| `username`, `full_name`, `email`, `is_admin`, AD_* | — | **Intocados** | — |

Regras herdadas (já implementadas no service, sem alteração):
- Política de senha: mínimo **8 caracteres** → `ValueError("A nova senha deve ter no mínimo 8 caracteres.")`.
- Hash: PBKDF2-HMAC-SHA256, salt de 16 bytes por senha, `AUTH_PBKDF2_ITERATIONS`
  (default 600000; 1000 na suíte de testes).
- Gravação atômica: hash + sessões no mesmo `commit` (sem alteração parcial).

### 1.2 UserSession — tabela `user_sessions` (`app/models/session.py`) — **DELETE do alvo**

| Campo | Papel |
|---|---|
| `token_hash` (String, unique) | SHA-256 do token — **nunca** exposto/logado |
| `user_id` (FK users, CASCADE) | Filtro da exclusão: todas as sessões do usuário alvo |

Efeito: `reset_password` exclui todas as sessões do alvo → próximo acesso exige novo
login com a nova senha. Idêntico ao comportamento de `change_password` e da admin web.

### 1.3 AuditLog — tabela `audit_logs` (`app/models/audit_log.py`) — **INSERT (append)**

Um registro por execução do comando (sucesso ou falha). Campos preenchidos:

| Campo | Valor |
|---|---|
| `timestamp` | `utcnow()` (padrão do service) |
| `user_id` / `username` | `NULL` / username do **alvo** (ator da aplicação nulo — decisão D-2; precedente `ad_service`) |
| `action` | `RESET_SENHA` (`ACTION_PASSWORD_RESET`, catálogo existente) |
| `module` / `resource` | `"Usuários"` / `"User"` |
| `resource_id` | id do alvo (quando existente) ou `NULL` |
| `resource_ref` | username |
| `ip_address` | `NULL` (sem contexto HTTP na CLI) |
| `result` | `SUCCESS` \| `FAILURE` |
| `description` | Texto curto não sensível (motivo/origem CLI) — **jamais** a senha |
| `new_data` | `{"origem": "CLI", "operador_so": "<usuário do SO>"}` — operador capturado automaticamente (`SUDO_USER` → `getpass.getuser()`; ausente → campo omitido, sem falhar a operação — D-2). **Jamais** contém a senha ou o hash |
| `previous_data` | `NULL` (não usado — conteria o hash anterior, material sensível) |

Imutabilidade preservada: append-only, sem rota de edição/exclusão (Princípio IX).

---

## 2. Transições de estado (comando ↔ entidades)

```text
                              ┌────────────────────────────────────────────┐
        execução do comando   │  users (alvo)      user_sessions  audit_logs │
┌──────────────────────────┐  ├──────────────────  ─────────────  ───────────┤
│ sucesso (local)          │→│ hash↑ falhas=0 lock=NULL  0 linhas   +1 SUCCESS│
│ sucesso (inativo, D-3)   │→│ hash↑ falhas=0 lock=NULL  0 linhas   +1 SUCCESS│
│                          │  │ (is_active permanece False)                  │
│ inexistente              │→│ —                  —             +1 FAILURE  │
│ AD (auth_provider='ad')  │→│ — (sentinela !ad-external intacta)  +1 FAILURE  │
│ política (<8)            │→│ — (nada persistido) —             +1 FAILURE  │
│ confirmação divergente   │→│ —                  —             +1 FAILURE  │
│ EOF/entrada vazia        │→│ —                  —             +1 FAILURE  │
│ falha de banco           │→│ — (commit atômico evita parcial)    +1 FAILURE  │
└──────────────────────────┘  └────────────────────────────────────────────┘
```

Observações:
- "hash↑" = substituição do hash (o hash anterior não é retido — não há histórico de
  senhas no modelo, comportamento existente preservado).
- Nenhum efeito em: `roles`, `user_roles`, `permissions`, `custodians`, `assets`,
  `movements` ou qualquer outra tabela.
- Em caso de falha do próprio `write_audit`, o reset pode já ter sido gravado (commit do
  service antecede a auditoria) — aceito e registrado no plan §9 (risco baixo).

## 3. Impacto de schema desta feature

**NENHUM.** Nenhuma tabela, coluna, índice ou constraint é criado, alterado ou removido.
Mecanismo de evolução (referência, não usado aqui): `app/database.py` → `init_db()` +
`_ensure_schema_migrations()` (aditivo, idempotente).
