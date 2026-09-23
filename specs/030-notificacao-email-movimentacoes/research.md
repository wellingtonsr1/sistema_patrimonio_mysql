# Phase 0 Research: Notificação por E-mail de Movimentações

**Feature**: 030-notificacao-email-movimentacoes | **Date**: 2026-09-23

Todos os NEEDS CLARIFICATION da spec foram resolvidos no `/speckit-clarify` (Q1–Q4, 2026-09-23). Esta pesquisa **não presume** nada: cada decisão cita o fato verificado no código real (leituras desta sessão).

## Fatos verificados no código (leituras 2026-09-23)

| # | Fato | Evidência |
|---|---|---|
| F1 | `MovementService.create_movement` valida (VAL-002..VAL-008), cria o `Movement` com origem/destino/custodiantes (`*_name` formatados), `operator_name`, `reason`, `term_code`, e faz `db.commit()` + `db.refresh(movement)` **antes do `return`** — ponto exato e seguro para o hook pós-commit. Chamadores: rotas web, `movements_api`, `cli.py`, `maintenance_service`, `seed_demo.py`, `import_service` (loop). | `app/services/movement_service.py` L79–288 |
| F2 | 8 tipos em `MovementType` (`_LabeledEnum` com `.label` em pt-BR — reutilizado no corpo do e-mail); identificadores: `ALLOCATION`=`ALOCACAO_CAUTELA`, `TRANSFER`=`TRANSFERENCIA_LOCAL`, `RETURN_STOCK`=`DEVOLUCAO_ESTOQUE`. | `app/models/enums.py` L137–146 |
| F3 | Nenhuma dependência de e-mail em `requirements.txt` (fastapi, uvicorn, sqlalchemy, pydantic, jinja2, python-multipart, pytest, requests, ldap3, pymysql, python-dotenv, openpyxl, reportlab). `smtplib`/`email` são stdlib. | `requirements.txt` |
| F4 | `write_audit(db, user=, action=, module=, resource=, resource_id=, resource_ref=, ip_address=, result=, description=, previous_data=, new_data=, username=)` — faz o próprio `commit`/`refresh`; constantes `ACTION_*` + `ACTION_LABELS` + `RESULT_SUCCESS/FAILURE/DENIED/LOCKED`; `write_change_audit` calcula diff before/after. | `app/services/audit_service.py` L130–193 |
| F5 | Precedente completo de config persistida: `BackupConfig` singleton id=1 + `backup_config_service.get_effective_config` com precedência **persistido → env → default**, dataclass congelada `EffectiveBackupConfig`, `create=False` para leitura pura (022), `save_backup_config` persistindo. | `app/services/backup_config_service.py` L26–200 |
| F6 | Rota admin de config: `@admin_router.get("/admin/backups", dependencies=[Depends(require_permission("backup.gerenciar"))])` — padrão a replicar. | `app/web/admin_routes.py` L803 |
| F7 | Migração: tabela **nova** é criada por `Base.metadata.create_all` no `init_db` (precedente `backup_records`/020 — sem ALTER em tabela existente, sem tocar `_ensure_schema_migrations`). | `app/database.py` L63–131; `specs/020/research.md` |
| F8 | Padrão de variável de ambiente não-secreta e secreta em `app/config.py`, ambas **após `load_dotenv()`** (guarda da 018): `MYSQLDUMP_PATH` (caminho), `AD_BIND_PASSWORD` (segredo — somente ambiente). | `app/config.py` L39–55, L110+ |
| F9 | Enum de status com labels em pt-BR já é o padrão do projeto (`_LabeledEnum.label`). | `app/models/enums.py` |
| F10 | Apresentação de datas: `app/utils/time_utils.py` (`now_utc`, `format_local`) — padrão 004 (America/Recife para pessoas). | `app/utils/time_utils.py` |

## Decisões

### D1 — Envio SMTP: stdlib (`smtplib` + `email.message.EmailMessage`), zero dependências novas
- **Decisão**: usar exclusivamente a stdlib do Python para SMTP.
- **Rationale**: F3 mostra que nenhuma lib de e-mail existe; adicionar dependência (ex.: `emails`, `aiosmtplib`) viola o princípio de alteração mínima (Constitution I) sem ganho real para envio síncrono simples. `EmailMessage` resolve cabeçalhos, encoding UTF-8 e corpo text/plain.
- **Alternatives considered**: bibliotecas de terceiros (rejeitadas — dependência nova sem necessidade; deploy/acoplamento); envio assíncrono com fila (rejeitado na v1 — fora de escopo, arquitetura preparada via provedor injetável).

### D2 — Provedor de e-mail isolado e injetável (`EmailProvider` protocol + `SMTPEmailProvider`)
- **Decisão**: módulo `app/services/email_provider.py` com um protocolo mínimo (`send(subject, body, recipients)`) e a implementação SMTP concreta; `NotificationService` recebe o provedor (parâmetro com default = instância SMTP).
- **Rationale**: spec §7 (arquitetura do briefing) e NFR-004; único ponto que conhece SMTP — mock trivial nos testes (Seção 14: fakes, nunca SMTP real); futura troca por fila/worker ou outros canais não toca o domínio.
- **Alternatives considered**: lógica SMTP dentro do `NotificationService` (rejeitada — acopla orquestração e transporte, dificulta mock e a evolução).

### D3 — Orquestração central: `NotificationService.notify_movement(db, movement, operator=..., ip_address=...)`
- **Decisão**: serviço novo `app/services/notification_service.py` com função única de entrada por movimentação, responsável por: elegibilidade (RN-002/D5), idempotência (RN-007/D7), leitura da config (D6), montagem de assunto (RN-005) e corpo (FR-008), envio via provedor (D2), atualização de estado do registro e auditoria (D9). Qualquer exceção é capturada dentro do serviço — nada escapa ao chamador (FR-003/Seção 11 da spec).
- **Rationale**: Constitution II/III (regras em services); ponto único de extensão futura (inventários, baixas etc.).
- **Alternatives considered**: espalhar a lógica nas rotas (rejeitado — viola II/III); hook dentro de cada rota (rejeitado — duplicação; o service de movimentação é o ponto comum).

### D4 — Hook pós-commit em `create_movement` + parâmetro aditivo `notify: bool = True`
- **Decisão**: acrescentar parâmetro `notify=True` (default preserva todos os 6 chamadores existentes) e, **após `db.refresh(movement)`**, antes do `return`, um bloco protegido: `if notify: _disparar_notificacao(db, movement, operator, ip)` com `try/except Exception` total (log técnico, nunca re-raise).
- **Rationale**: F1 mostra que o fim de `create_movement` é pós-commit (movimentação persistida — RN-003); default True evita alterar qualquer chamador; `import_service` passa `notify=False` (RN-002 — lote não notifica, decisão Q2). Contrato byte-idêntico para chamadores existentes.
- **Alternatives considered**: callback/observer/event bus (rejeitado — mecanismo novo sem precedente no projeto, complexidade sem ganho); disparo nas rotas após chamar o service (rejeitado — CLI/maintenance/seed deixariam de disparar; regra ficaria espalhada).

### D5 — Elegibilidade por conjunto de tipos (constante de módulo) com dupla checagem
- **Decisão**: constante `NOTIFICABLE_TYPES = {MovementType.ALLOCATION, MovementType.TRANSFER, MovementType.RETURN_STOCK}` em `notification_service`; checada no hook (evita chamar o service) e novamente dentro de `notify_movement` (defesa em profundidade; o service também é seguro se chamado diretamente no futuro).
- **Rationale**: decisão Q1 do clarify (apenas os 3 tipos principais); regra de negócio num único ponto (Constitution III).
- **Alternatives considered**: filtrar por canal de origem (rejeitado — a RN-002/029 já trata o lote via `notify=False`; origem não é critério).

### D6 — Configuração persistida: `EmailConfig` singleton + `email_config_service` (precedente 021)
- **Decisão**: model `EmailConfig` (singleton id=1) com `notifications_enabled` (default False) e `recipients` (Text, JSON array de e-mails validados) + metadados `updated_at/updated_by`; service com `get_effective_config()` (dataclass congelada; leitura pura com `create=False`) e `save_config()` (valida: ativado exige ≥1 destinatário válido — RFC simples de formato; grava via `write_change_audit`).
- **Rationale**: F5 é o precedente exato (persistido → env → default); spec FR-005/FR-006 e US3; segredo **nunca** no banco (apenas ativação/destinatários — não-secretos).
- **Alternatives considered**: config só em `.env` (rejeitado — US3 exige alteração pela tela sem reinício); config geral em settings genéricos (rejeitado — não existe esse mecanismo no projeto; criar um é escopo novo).

### D7 — Idempotência estrutural: tabela nova `notifications` com vínculo único com a movimentação
- **Decisão**: model `Notification` (`__tablename__ = "notifications"`, tabela **nova** por `create_all` — F7) com `movement_id` (FK único, unique constraint — 1:1), `status` (enum interno `PENDING/SENT/FAILED`), `recipients` (JSON/texto do efetivamente usado), `subject`, `attempt_count`, `last_attempt_at`, `sent_at`, `error_message` (sem segredos), `content_url` (**nulo nesta versão** — RN-008 reserva para o link futuro) e timestamps UTC.
- **Rationale**: RN-007/Seção 13 da spec — a unicidade estrutural garante no máximo 1 notificação por movimentação mesmo sob reprocesso; `content_url` torna o link futuro uma mudança só de template (RN-008); campo de estado prepara retry futuro sem migração (FR-017/P-1).
- **Alternatives considered**: consulta "já existe e-mail?" sem registro persistido (rejeitado — sem garantia estrutural nem histórico para auditoria/retry); colunas na tabela `movements` (rejeitado — ALTER em tabela existente e acoplamento de domínios).

### D8 — Variáveis de ambiente SMTP em `app/config.py` (após `load_dotenv()`)
- **Decisão**: acrescentar `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USERNAME`, `SMTP_PASSWORD` (segredo — somente ambiente, precedente `AD_BIND_PASSWORD`), `SMTP_FROM`, `SMTP_USE_TLS` (default true), `SMTP_SEND_TIMEOUT` (default 10.0 s). Nomes exatamente os do briefing; comentário do bloco cita a feature 030.
- **Rationale**: F8 define o lugar e a guarda (pós `load_dotenv` — bug histórico da 018); Constitution VI (segredo fora de código/repo/banco); FR-016 (timeout configurável).
- **Alternatives considered**: segredo no banco (rejeitado — Constitution VI); nomes diferentes (rejeitado — briefing fixa os nomes).

### D9 — Auditoria: 3 ações novas no padrão existente
- **Decisão**: em `audit_service.py`: `ACTION_NOTIFICACAO_ENVIADA = "NOTIFICACAO_ENVIADA"` (rótulo "Notificação Enviada"), `ACTION_NOTIFICACAO_FALHOU = "NOTIFICACAO_FALHOU"` (rótulo "Notificação Falhou"), `ACTION_NOTIFICACAO_CONFIG = "CONFIG_NOTIFICACAO_ALTERADA"` (rótulo "Configuração de Notificação Alterada"). Eventos de envio: `module="notificacoes"`, `resource="movement"`, `resource_id=movement.id`, `resource_ref=asset.tag`, `new_data={destinatarios, assunto? — sem segredos}`; falha usa `result=RESULT_FAILURE` e `description` técnica sanitizada; config usa `write_change_audit` (before/after).
- **Rationale**: F4 (padrão `ACTION_*` + rótulos + `write_audit`/`write_change_audit`); Seção 10 da spec (decisão D6 da spec: sem evento "solicitada" — par enviado/falhou basta).
- **Alternatives considered**: evento `NOTIFICACAO_SOLICITADA` (rejeitado — ruído na trilha, não adiciona resposta às perguntas exigidas); tabela própria de log de notificação substituindo auditoria (rejeitado — Seção 11 da spec pede integração à trilha existente; o `Notification` guarda o estado técnico, a trilha guarda o evento institucional).

### D10 — Tela admin: `/admin/notificacoes` (padrão 021/022) com permissão nova
- **Decisão**: rota `GET` (formulário com estado atual) e `POST` (salvar) em `admin_routes.py`, `dependencies=[Depends(require_permission("notificacoes.gerenciar"))]`; template `app/web/templates/admin/notificacoes.html` (estende o base admin, mesmos componentes); no `POST`: valida (ativado exige ≥1 e-mail válido), salva via `email_config_service.save_config`, audita via `write_change_audit`, flash de sucesso/erro. Permissão nova criada no catálogo **sem concessão default** (admin concede a quem precisar).
- **Rationale**: F6 é o padrão a replicar; spec US3/FR-014; Constitution X (consistência visual) e VI (deny by default).
- **Alternatives considered**: reaproveitar a tela de backups (rejeitado — acopla módulos distintos; spec Q3 decidiu ciência de falhas só na auditoria); config sem tela (rejeitado — US3 exige).

## Outros pontos resolvidos

- **Assunto (RN-005)**: `"[SisPatrimônio Pro] Nova movimentação patrimonial - {tag}"` construído em função única do `notification_service` (nenhum assunto montado em outro lugar).
- **Corpo (FR-008/RN-009/RN-010)**: `text/plain` institucional com: título, tombamento, identificação do bem, tipo (`.label` do enum — F9), origem/destino (nomes já formatados no `Movement` — F1), custodiante anterior/atual, data/hora via `format_local` (F10), operador = `movement.operator_name` (RN-010 — usuário autenticado, web ou API). Sem link (RN-008); `content_url` permanece nulo.
- **Runtime sem destinatário válido**: não envia; registra auditoria de falha de configuração (spec Seção 11) — sem erro ao operador.
- **Import CSV (Q2)**: `import_service.execute_import` passa `notify=False` — nenhuma notificação por linha.
- **Fuso (F10)**: datas no e-mail em `America/Recife` (padrão 004); timestamps do registro em UTC.
- **Testes (Seção 14)**: fake de provider injetado no `NotificationService` (D2); banco SQLite em memória via fixtures existentes; 13 cenários mapeados.

## Coverage de NEEDS CLARIFICATION

Nenhum `NEEDS CLARIFICATION` resta: as 4 dúvidas de negócio foram resolvidas no clarify (Q1–Q4 integradas à spec) e as decisões técnicas acima derivam de fatos verificados (F1–F10). Pendência P-1 (retry) permanece deliberadamente fora da v1 (FR-017) — o modelo D7 já guarda o estado necessário.
