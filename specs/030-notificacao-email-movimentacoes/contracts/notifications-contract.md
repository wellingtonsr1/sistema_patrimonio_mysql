# Contract: Notificação por E-mail de Movimentações (feature 030)

Contratos dos caminhos afetados. Tudo o que não está listado aqui permanece **byte-idêntico** ao comportamento atual.

## 1. `MovementService.create_movement` — contrato estritamente aditivo

| Aspecto | Contrato |
|---|---|
| Assinatura | `create_movement(db, data)` → `create_movement(db, data, notify=True, operator=None, ip_address=None)` — parâmetros **novos com default**; nenhum chamador existente é obrigado a mudar |
| Retorno | **Inalterado** (`Movement` persistido) — o hook roda antes do `return`, mas não altera o valor |
| Validações | **Inalteradas** (VAL-002..008 intocadas; nenhum e-mail para movimentação inválida — FR-002) |
| Transação | **Inalterada** — hook roda **após** `db.commit()` + `db.refresh()`; falha do hook NUNCA desfaz o commit (RN-001) |
| Erros do hook | `try/except Exception` total: log técnico (logger `app.services.notification_service`), nunca re-raise (FR-003) |
| Comportamento default | Idêntico ao atual + tentativa silenciosa de notificação (que, com a config default **desativada**, é um early-return sem efeito) |

## 2. `NotificationService.notify_movement` — nova função (ponto único de entrada)

| Aspecto | Contrato |
|---|---|
| Assinatura | `notify_movement(db, movement, *, operator=None, ip_address=None, provider=None) -> None` |
| Garantias | (a) nunca levanta exceção ao chamador; (b) no máx. 1 registro `Notification` por `movement_id` (UNIQUE + checagem prévia); (c) só envia se config `enabled` e tipo em `NOTIFICABLE_TYPES` |
| Sequência | checa elegibilidade → checa config → checa registro existente (idempotência) → cria `Notification` PENDING (commit próprio) → monta assunto/corpo → `provider.send(...)` (timeout) → atualiza estado (SENT/FAILED, commit próprio) → auditoria |
| Auditoria | sucesso → `write_audit(ACTION_NOTIFICACAO_ENVIADA, result=SUCCESS)`; falha → `write_audit(ACTION_NOTIFICACAO_FALHOU, result=FAILURE, description=erro sanitizado)`; ambas: `module="notificacoes"`, `resource="movement"`, `resource_id=movement.id`, `resource_ref=asset.tag`, `new_data={destinatários}`, **`user=None`** (ator = o serviço — precedente dos eventos automáticos de backup da 020; o usuário que concluiu a movimentação já consta no evento `MOVIMENTACAO` e em `operator_name`) — **sem credenciais** |
| Sem config válida ativada | sem envio; auditoria de falha de configuração (spec Seção 11); nenhum erro visível |
| Exceção no registro/auditoria | capturada e logada; não propaga (spec Seção 11, última linha) |

## 3. `EmailProvider` / `SMTPEmailProvider` — novo módulo isolado

| Aspecto | Contrato |
|---|---|
| Protocolo | `send(*, subject: str, body: str, recipients: list[str]) -> None` (levanta exceção em falha — quem trata é o `NotificationService`) |
| Implementação | `smtplib.SMTP` com `timeout=SMTP_SEND_TIMEOUT`; `STARTTLS` se `SMTP_USE_TLS`; login se `SMTP_USERNAME`/`SMTP_PASSWORD` presentes; `EmailMessage` UTF-8 (`text/plain`) |
| Erro | exceções de SMTP propagam **sanitizadas** (a mensagem nunca inclui senha/credenciais — o provider remove valores de credenciais do texto do erro) |
| Testes | fake injetável via `provider=` (D2); nenhum SMTP real na suíte |

## 4. `email_config_service` — nova configuração (precedente 021)

| Aspecto | Contrato |
|---|---|
| `get_effective_config(db, create=False)` | leitura pura; dataclass congelada `EffectiveEmailConfig(enabled, recipients)`; `create=True` (default no POST) cria singleton lazy |
| `save_config(db, *, enabled, recipients, user)` | valida (ativado exige ≥1 e-mail válido; máx. 10; normaliza/deduplica); persiste singleton; grava `write_change_audit(ACTION_NOTIFICACAO_CONFIG, module="notificacoes", resource="email_config", before/after)`; retorna config salva |
| Erros de validação | `ValueError` com mensagem amigável (rota converte em flash de erro) |

## 5. `app/config.py` — variáveis novas (bootstrap, após `load_dotenv()`)

| Variável | Default | Segredo? |
|---|---|---|
| `SMTP_HOST` | `""` (sem host = provider inoperante) | Não |
| `SMTP_PORT` | `587` | Não |
| `SMTP_USERNAME` | `""` | Não (identificação, mas tratada como sensível em logs) |
| `SMTP_PASSWORD` | `""` | **Sim — somente ambiente** (precedente `AD_BIND_PASSWORD`) |
| `SMTP_FROM` | `""` (fallback: `SMTP_USERNAME`) | Não |
| `SMTP_USE_TLS` | `true` | Não |
| `SMTP_SEND_TIMEOUT` | `10.0` (segundos) | Não |

## 6. Rota admin — `/admin/notificacoes` (GET + POST)

| Aspecto | Contrato |
|---|---|
| Autorização | `dependencies=[Depends(require_permission("notificacoes.gerenciar"))]` — deny by default (Constitution VI) |
| GET | formulário com estado atual (`get_effective_config(create=False)`); leitura pura |
| POST | campos `notifications_enabled` + `recipients` (textarea, um e-mail por linha ou separados por vírgula); chama `save_config`; sucesso/erro → flash + redirect |
| Auditoria | via `save_config` (`write_change_audit` — antes/depois, sem segredos) |
| Permissão nova | `notificacoes.gerenciar` adicionada ao catálogo **sem concessão default** (nenhum perfil recebe automaticamente) |

## 7. `import_service.execute_import` — única mudança em chamador existente

| Aspecto | Contrato |
|---|---|
| Chamada | `create_movement(..., notify=False)` — lote CSV não notifica (RN-002/Q2). Restante do fluxo de importação **inalterado** |

## 8. Compatibilidade (não-regressão)

- Com notificações **desativadas** (estado de fábrica): zero e-mails, zero registros `Notification`, zero eventos de auditoria novos, zero mudança perceptível em qualquer rota de movimentação (web/API/CLI/maintenance/seed) — suíte existente 100% verde;
- Com notificações **ativadas**: comportamento adicional exclusivo = 1 e-mail por movimentação elegível concluída; falha de e-mail invisível ao operador;
- Nenhuma rota, template, validação ou permissão existente é alterada (exceto: `import_service` passa `notify=False` — §7; menu admin ganha entrada condicionada à permissão nova).
