# Contract: Central de Integrações (feature 032)

Rotas web (padrão `require_permission`; autenticação web vigente; negações auditadas — Constitution VI).

## 1. Permissões — `app/services/permission_service.py`

`PERMISSION_CATALOG` recebe (aditivo):

```python
{"name": "integracoes.visualizar", "module": "Integrações", "label": "Visualizar Central de Integrações", "description": "Painel, detalhes, histórico de execuções e propagação por movimentação."},
{"name": "integracoes.testar", "module": "Integrações", "label": "Testar conexões de integrações", "description": "Executar o teste de conexão das integrações sem guarda dedicada (e-mail e 1Doc interno)."},
```

Sem concessão default (perfil Administrador recebe via `DEFAULT_ROLES`). Guardas vigentes intocadas: AD (`usuarios.editar` + `perfis.editar`), reprocesso 1Doc (`integracao1doc.reprocessar`), notificações (`notificacoes.gerenciar`).

## 2. Rotas — `app/web/admin_routes.py`

| Método | Caminho | Permissão | Função |
|---|---|---|---|
| GET | `/admin/integracoes` | `integracoes.visualizar` | Painel: card por integração (status, última execução, último sucesso, falhas 24h, pendentes) — **sem chamadas externas** |
| GET | `/admin/integracoes/{key}` | `integracoes.visualizar` | Detalhe/diagnóstico (configurada/disponível/autenticada/operacional quando verificável; contadores; erro sanitizado; ações) |
| GET | `/admin/integracoes/{key}/historico` | `integracoes.visualizar` | Histórico paginado com filtros: período, status, operação, usuário (opcional — FR-019; execuções automáticas aparecem quando não filtrado) |
| POST | `/admin/integracoes/{key}/testar` | e-mail/1doc: `integracoes.testar`; ad: redirect ao teste da tela AD (guarda vigente); glpi: 404 amigável/botão ausente | Executa teste seguro, registra `integration_executions` + auditoria, redireciona com mensagem |
| GET | `/admin/integracoes/movimentacao/{movement_id}` | `integracoes.visualizar` | Propagação por movimentação (somente leitura) |

`{key}` válido: `email`, `onedoc`, `ad`, `glpi` (catálogo — plan D1). Chave inválida → 404 amigável.

## 3. Service novo — `app/services/integration_center_service.py`

```python
def get_panel(db) -> list[dict]                 # cards do painel (derivação sem I/O externo)
def get_detail(db, key) -> dict                 # diagnóstico da integração
def get_history(db, key, *, status, operation, days, page, page_size, user=None) -> dict  # user opcional (FR-019)
def get_movement_propagation(db, movement_id) -> dict
def run_test(db, key, *, user, ip_address) -> tuple[bool, str]   # delega: email→check_connection; onedoc→config interna; ad/glp→não suportado
def record_execution(db, key, operation, result, *, duration_ms=None, user=None, movement_id=None, detail=None) -> None  # best-effort, NUNCA levanta
```

Catálogo declarativo `INTEGRATIONS` (key, nome, finalidade, capacidades, `status_fn`). Vocabulário de status (spec §7): `NAO_CONFIGURADA`, `PENDENTE`, `DESABILITADA`, `ATIVA`, `COM_ERRO`, `INDISPONIVEL`, `INATIVA` (+ dimensões de diagnóstico configurada/disponível/autenticada/operacional).

## 4. Provider — `app/services/email_provider.py` (toque mínimo)

```python
def check_connection() -> tuple[bool, str, int | None]  # (ok, mensagem sanitizada, latency_ms)
```

Conecta a `SMTP_HOST:PORT`, STARTTLS quando `SMTP_USE_TLS`, login com `SMTP_USERNAME/PASSWORD`, encerra. **Nenhuma mensagem enviada** (P-6). `send()` permanece intocado.

## 5. Instrumentação (toque mínimo nos services existentes — plan D6)

| Ponto | Gravação |
|---|---|
| `notification_service` — após estado final do envio (SENT/FAILED) | `record_execution("email", "SEND_EMAIL", result, duration_ms, detail=erro sanitizado)` |
| `onedoc_service._send` — após estado final (cobre envio e reprocesso) | `record_execution("onedoc", "SEND_COMMUNICATION", result, ..., movement_id=movement.id)` |
| Teste de conexão AD (rota existente) | `record_execution("ad", "CONNECTION_TEST", result, ...)` |
| Testes da Central (`run_test`) | `record_execution(...)` + eventos `TESTE_INTEGRACAO_*` |

Todos best-effort (try/except; falha de registro nunca afeta a integração).

## 6. Auditoria — `app/services/audit_service.py` (aditivo)

```python
ACTION_CENTRAL_TESTE_SUCESSO = "TESTE_INTEGRACAO_SUCESSO"
ACTION_CENTRAL_TESTE_FALHA = "TESTE_INTEGRACAO_FALHA"   # module="central_integracoes" + rótulos
```

Demais ações continuam com eventos já vigentes (sem duplicação — plan D7). Nunca credenciais.

## 7. Templates — `app/web/templates/admin/integracoes/`

`list.html` (cards), `detail.html` (diagnóstico + ações), `historico.html` (tabela + filtros + paginação), `movimentacao.html` (propagação) — padrão visual vigente, `active_tab="admin"`, tema claro/escuro. `base.html`: entrada de menu sob `can('integracoes.visualizar')`.

## 8. Migração — `app/database.py`

`IntegrationExecution.__table__.create(checkfirst=True)` no fluxo do `init_db` (padrão 030/031), índices conforme data-model.md. Nenhuma coluna de tabela existente é alterada.

## 9. Testes — `tests/test_central_integracoes.py`

Fakes de provider (nunca SMTP/HTTP real); RBAC (autorizado × não autorizado em todas as rotas); status para cada estado do §7; teste de conexão (sucesso/timeout/auth/indisponível) com registro; histórico/filtros/paginação; segredo não exposto (varredura de `SMTP_PASSWORD`/`ONEDOC_API_TOKEN` nas respostas e auditoria); propagação; idempotência/sem-duplicação; suíte existente verde.
