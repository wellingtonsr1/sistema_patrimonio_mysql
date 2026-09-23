# Contract: Integração 1Doc (feature 031)

Contratos dos caminhos afetados. Tudo o que não está listado aqui permanece **byte-idêntico** ao comportamento atual — em especial com `ONEDOC_ENABLED=false` (default): nenhuma validação nova, nenhum campo obrigatório, nenhuma chamada externa.

## 1. Schema — `app/schemas/movement.py`

| Aspecto | Contrato |
|---|---|
| `MovementCreate` | **Aditivo**: `onedoc_process_number: Optional[str] = None`. Nenhum campo existente muda; defaults preservados; chamadores existentes não precisam de alteração |

## 2. Service — `app/services/movement_service.py`

### 2.1 `create_movement(...)` — assinatura estendida, fluxo preservado

| Aspecto | Contrato |
|---|---|
| Nova assinatura | `create_movement(db, data, notify=True, operator=None, ip_address=None, onedoc_process_number=None, onedoc_enforce=True)` |
| Validação nova (condicional) | Somente se: `ONEDOC_ENABLED` **e** tipo em `{ALOCACAO_CAUTELA, TRANSFERENCIA_LOCAL}` (Q1) **e** `onedoc_enforce` **e** `onedoc_process_number` vazio → `ValueError("Informe o número do processo 1Doc...")` **antes** de qualquer escrita (FR-002; erro 400 na API / redirect com error na web) |
| Validação de existência (Q2) | Somente se processo informado e integração ativa: `onedoc_client.find_process(num)` → `False` → `ValueError` (processo inexistente, US1.3); `None` → segue (modo tolerante); `True` → segue. Falha de rede na consulta → modo tolerante (registro no reprocessamento corrige) — nunca bloqueia por indisponibilidade |
| Normalização | `process_number` = trim; vazio vira `None`. **Validação de formato: SOMENTE trim na v1** (analyze U1) — o formato real dos números de processo chega com C-2/C-4 do fornecedor; máscara/regex fica para versão futura |
| Hook pós-commit | Após o bloco de e-mail (030), novo bloco `try/except` total chama `onedoc_service.notify_movement(...)` — nada escapa (FR-007) |
| Tipos fora do alcance | Devolução, manutenções, baixa, ajustes, aquisição: sem validação, sem campo exigido, sem integração (Q1/Q5) |
| Lote CSV | `import_service` passa `onedoc_enforce=False` (precedente `notify=False`) — lote intocado |

## 3. Service novo — `app/services/onedoc_service.py`

| Aspecto | Contrato |
|---|---|
| `notify_movement(db, movement, process_number, *, operator=None, ip_address=None, provider=None)` | **NUNCA levanta** (espelha contrato da 030). Sequência: guardas (`ONEDOC_ENABLED`, tipo elegível, `process_number` presente) → idempotência (registro existente em {`SENT`,`PENDING`} → return; `FAILED` **não** reenvia automaticamente) → cria `PENDING` (commit próprio; `IntegrityError` → rollback+return) → monta conteúdo (`onedoc_message`) → `provider.send_communication(...)` → `SENT` (+`message_id`, `sent_at`) + auditoria `_ENVIADA`; exceção → `FAILED` (+erro sanitizado) + auditoria `_FALHOU` |
| `reprocess(db, integration_id, *, user, ip_address=None)` | Exige registro `FAILED`; valida permissão **na rota** (RBAC); reexecuta o envio no mesmo registro; audita `_REPROCESSADA` com `user` real; nunca altera a movimentação; retorna (ok, motivo) |
| Auditoria | `write_audit(user=None, ...)` nos automáticos (precedente 020/030); `new_data={"processo": ..., "message_id": ...}`; erros sanitizados (nunca token) |

## 4. Provider — `app/services/onedoc_client.py`

| Aspecto | Contrato |
|---|---|
| Protocolo `OneDocProvider` | `find_process(process_number) -> bool \| None` (`False`=inexistente, `None`=não suportado/indisponível — Q2) e `send_communication(process_number, subject, body_text, body_html) -> str \| None` (id da mensagem; `None` = não informado — Q3) |
| `OneDocHttpClient` | Estrutura pronta: sessão `requests` com `ONEDOC_API_TOKEN` em header, `connect/read timeout` de config, mapeamento erro transitório (timeout/conn/5xx) × permanente (4xx). **Endpoints/paths/payloads: `[PENDING C-1..C-4]`** — nenhum inventado; implementação real quando o fornecedor confirmar o contrato |
| Sanitização | Toda exceção propagada tem `ONEDOC_API_TOKEN`/URL removidos da mensagem (precedente `_sanitize_error_message` da 030) |
| Fakes em teste | `FakeOneDocProvider` injetado via parâmetro `provider` — nunca HTTP real na suíte |

## 5. Conteúdo — `app/services/onedoc_message.py` (funções puras)

| Aspecto | Contrato |
|---|---|
| `build_subject(tag)` | `[SisPatrimônio Pro] Movimentação patrimonial - <tag>` (diferente do assunto do e-mail — não reutiliza `build_subject` da 030) |
| `build_body_text/build_body_html(movement, asset_name, asset_tag)` | Saudação por horário local (P-2) + tabela **exata** (P-1): `Descrição do Material | Tombamento | Origem | Destino` — 1 linha: asset.name, asset.tag, origin_location_name, destination_location_name. Fontes: somente a movimentação registrada (FR-004/FR-005). Sem link (FR-017) |

## 6. Rotas web — `app/web/routes.py` + `movements/new.html`

| Aspecto | Contrato |
|---|---|
| `GET /movements/new` | Template recebe flag de integração ativa (config) — campo "Processo 1Doc" renderizado **somente** nos formulários de cautela/transferência (Q5); visibilidade também exige `ONEDOC_ENABLED` |
| `POST /movements/new` | **Aditivo**: `onedoc_process_number: Optional[str] = Form(None)` → passa ao `create_movement`; `ValueError` de 1Doc segue o fluxo existente de erro (redirect com `?error=...`) |

## 7. API — `app/api/movements_api.py`

| Aspecto | Contrato |
|---|---|
| `POST /api/v1/movements` | Pass-through: `data.onedoc_process_number` chega ao service via schema; `ValueError` de 1Doc → HTTP 400 (padrão existente de validações) — nenhum endpoint novo |

## 8. Admin — `app/web/admin_routes.py` + `admin/onedoc.html`

| Aspecto | Contrato |
|---|---|
| `GET /admin/integracao-1doc` | `require_permission("integracao1doc.reprocessar")` — lista integrações (movimentação, processo, status, tentativas, último erro/último sucesso) |
| `POST /admin/integracao-1doc/{id}/reprocessar` | Mesma permissão; chama `onedoc_service.reprocess`; flash de resultado; **menos-granular não existe** — sem concessão default (Q4) |
| Menu | Item "Integração 1Doc" com `can()` (padrão 021/030) |

## 9. Permissões — `app/services/permission_service.py`

| Aspecto | Contrato |
|---|---|
| Catálogo | +`{"name": "integracao1doc.reprocessar", "module": "Integração 1Doc", "label": "Reprocessar integração 1Doc", ...}` (precedente `notificacoes.gerenciar`) |
| Concessão | Banco **novo**: Administrador recebe (semântica pré-existente do seed); banco **existente**: ninguém recebe automaticamente (mecanismo atual `ensure_default_roles`) |

## 10. Auditoria — `app/services/audit_service.py`

| Aspecto | Contrato |
|---|---|
| Novas ações | `ACTION_INTEGRACAO_1DOC_SOLICITADA` / `_ENVIADA` / `_FALHOU` / `_REPROCESSADA` + rótulos em `ACTION_LABELS` ("Integração 1Doc Solicitada", etc.) |
| Garantias | `user=None` nos automáticos; usuário real no reprocessamento; **nunca** token/credencial (Constitution VI/IX) |

## 11. Config — `app/config.py`

| Aspecto | Contrato |
|---|---|
| Novas variáveis | `ONEDOC_ENABLED` (default `false`), `ONEDOC_API_URL` (""), `ONEDOC_API_TOKEN` ("" — SEGREDO), `ONEDOC_CONNECT_TIMEOUT` (3.0), `ONEDOC_READ_TIMEOUT` (10.0), `ONEDOC_MAX_ATTEMPTS` (3) — padrão `SMTP_*` |
| `.env.example` | Bloco `ONEDOC_*` comentado documentando os 6 itens |

## 12. E-mail 030 — intocabilidade

| Aspecto | Contrato |
|---|---|
| `notification_service` / `email_provider` / `email_config_service` / `email_config` | **Byte-idênticos** — nenhuma linha alterada; assunto/corpo do e-mail não mudam; ordem: e-mail primeiro, 1Doc depois (independentes — FR-015) |
