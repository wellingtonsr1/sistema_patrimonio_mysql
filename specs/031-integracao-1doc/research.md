# Phase 0 Research: Integração 1Doc — Comunicação Automática de Movimentações

**Feature**: 031-integracao-1doc | **Date**: 2026-09-23

Clarifications Q1–Q5 resolvidos na spec (2026-09-23). Esta pesquisa **não presume** a API 1Doc: cada decisão cita o fato verificado no código real (leituras desta sessão). A pendência externa (contrato do fornecedor) é documentada como tal — nunca inventada.

## Fatos verificados no código (leituras 2026-09-23)

| # | Fato | Evidência |
|---|---|---|
| F1 | `create_movement(db, data, notify=True, operator=None, ip_address=None)` — assinatura já estendida pela 030; hook pós-commit com `try/except` total no fim | `app/services/movement_service.py` L63-327 (hook L301-325) |
| F2 | `requests>=2.31.0` já em `requirements.txt` | `requirements.txt` L8 |
| F3 | Padrão de config de ambiente: `SMTP_*` em `app/config.py` L153-164, com comentário de segredo | `app/config.py` |
| F4 | Precedente de model com UNIQUE de idempotência: `Notification.movement_id` (`uq_notifications_movement_id`), registrado via `app/models/__init__.py` → `create_all` | `app/models/notification.py` L39-87 |
| F5 | Schema de entrada: `MovementCreate(BaseModel)` com campos opcionais default `None` | `app/schemas/movement.py` L7-16 |
| F6 | Rotas web: `GET/POST /movements/new` (`require_permission("movimentacao.criar")`), formulário com `Form(...)`, erro retorna à tela via `?error=` | `app/web/routes.py` L746-811 |
| F7 | Rota API: `POST /api/v1/movements` recebe `MovementCreate` direto (pass-through) e audita com `write_change_audit` | `app/api/movements_api.py` L58-89 |
| F8 | Catálogo de permissões: `PERMISSION_CATALOG` com precedente `notificacoes.gerenciar` (030, sem concessão default em banco existente) | `app/services/permission_service.py` L30-89 |
| F9 | Auditoria: `write_audit(user=None, ...)` nos eventos automáticos (precedente 020/030) + `ACTION_LABELS` | `app/services/audit_service.py` |
| F10 | Lote CSV: `import_service` chama `create_movement(..., notify=False)` | `app/services/import_service.py` (alteração da 030) |
| F11 | Tela admin mínima: padrão 021/030 (`admin_routes` + template + item de menu com `can()`) | `app/web/admin_routes.py`, `base.html` |
| F12 | Movimentação contém todos os dados da tabela: `asset` (name/tag via relação), `origin_location_name`, `destination_location_name` | `app/models/movement.py` (F7 da spec) |

## Decisões

### D1 — Onde mora o número do processo: registro de integração (não em `movements`)
**Decision**: tabela nova `onedoc_integrations` com `movement_id` UNIQUE + `process_number`, `status`, `message_id`, `attempt_count`, `last_attempt_at`, `last_error_at`, `sent_at`, `last_error`, `content_url` (NULL — link futuro, FR-017).
**Rationale**: `Movement` permanece modelo patrimonial puro; idempotência estrutural igual à 030 (F4); FR-008 exige estado próprio.
**Alternatives**: colunas novas em `movements` (contamina modelo, migração maior) — rejeitada.

### D2 — Configuração 100% por ambiente (`ONEDOC_*`), default desativado
**Decision**: `ONEDOC_ENABLED` (default **false**), `ONEDOC_API_URL`, `ONEDOC_API_TOKEN` (segredo), `ONEDOC_CONNECT_TIMEOUT` (3 s), `ONEDOC_READ_TIMEOUT` (10 s), `ONEDOC_MAX_ATTEMPTS` (3). Nenhum singleton em banco nesta versão.
**Rationale**: P-4 (spec §13); padrão `SMTP_*` (F3); sem credenciais reais ainda (Fase 1), tela de config seria inoperante.
**Alternatives**: singleton 021/030 em banco — avaliado e adiado para evolução (quando credenciais existirem, sem migração de dados).

### D3 — Provider isolado: `OneDocProvider` (protocolo) + `OneDocHttpClient` (requests)
**Decision**: protocolo com 2 operações: `find_process(process_number) -> bool | None` e `send_communication(process_number, subject, body_text, body_html) -> str | None` (id da mensagem; `None` = não informado — Q3).
**Rationale**: spec §8 proíbe inventar endpoints; interface estável permite implementar toda a mecânica interna com fakes e conectar o HTTP real quando C-1..C-4 chegarem (D5 do plan).
**Alternatives**: client concreto imediato (exigiria presumir endpoints) — proibido pelo input.

### D4 — Pendência externa explícita (Fase 1)
**Decision**: `OneDocHttpClient` implementado com estrutura pronta (autenticação por header, timeouts, mapeamento de erros) e **pontos de conexão marcados `[PENDING C-1..C-4]`** — sem URL/rota inventada; integração nasce `ONEDOC_ENABLED=false`.
**Rationale**: regra central do input ("não inventar endpoints"); spec §8 (C-1..C-4 confirmados antes de produção); permite concluir o restante da feature sem bloqueio.
**Alternatives**: aguardar fornecedor para planejar tudo (paralisaria a feature interna) — rejeitada; presumir API pública do 1Doc de exemplos de terceiros — proibida.

### D5 — Validação de existência (Q2) via `find_process`
**Decision**: com integração ativa + tipo elegível + enforce: (a) `find_process() -> False` → `ValueError` **antes** de gravar (processo inexistente — cenário US1.3); (b) `-> None` (sem suporte C-3) → modo tolerante, valida só formato local; (c) `-> True` → segue.
**Rationale**: implementa Q2 literalmente; `bool | None` expressa "confirmado | API não suporta" sem exceção de controle.
**Alternatives**: sempre tolerante (perde o bloqueio da Q2 quando suportado) — rejeitada.

### D6 — Campo no schema + parâmetros no `create_movement`
**Decision**: `MovementCreate.onedoc_process_number: Optional[str] = None`; `create_movement(..., onedoc_process_number=None, onedoc_enforce=True)`. `import_service` passa `onedoc_enforce=False` (F10 — precedent `notify=False`).
**Rationale**: F5 (schemas Pydantic é o canal existente); validação de negócio fica no service (Constitution III); lote CSV intocado (F6).
**Alternatives**: campo em `Form` apenas na rota web (API ficaria sem o processo — quebraria FR-001) — rejeitada.

### D7 — Ordem dos hooks: e-mail (030) → 1Doc, mesmo bloco pós-commit
**Decision**: após o bloco de notificação existente, novo bloco `try/except` total chama `onedoc_service.notify_movement(db, movement, onedoc_process_number, operator, ip_address)`.
**Rationale**: fluxo da spec §6 (passos 5→6); captura total garante FR-007 (F1 — ponto de não-retorno já provado pela 030).
**Alternatives**: fila/worker agora (P-5 rejeitado nesta versão; D9 do plan).

### D8 — Idempotência em 3 camadas
**Decision**: (1) UNIQUE `movement_id`; (2) checagem pré-insert (`status in {SENT, PENDING}` → return); (3) `IntegrityError` → rollback + return (corrida — igual T019 da 030).
**Rationale**: SC-003 (0 duplicatas) mesmo sob timeout duplo-click/reprocessamento concorrente.
**Alternatives**: chave de idempotência nativa da API (C-6 desconhecido) — registrada como reforço futuro.

### D9 — Reprocessamento manual com permissão dedicada
**Decision**: permissão `integracao1doc.reprocessar` no catálogo (F8), **sem concessão default**; rota `POST /admin/integracao-1doc/{id}/reprocessar` audita `INTEGRACAO_1DOC_REPROCESSADA` com `user` real (não None).
**Rationale**: Q4; padrão 030 (`notificacoes.gerenciar`); imutabilidade da trilha (Constitution IX).
**Alternatives**: reaproveitar permissão admin existente (menos granular) — rejeitada pela Q4.

### D10 — Conteúdo da comunicação em módulo puro (`onedoc_message.py`)
**Decision**: saudação por horário local (P-2: Bom dia!/Boa tarde!/Boa noite!) + tabela exata de 4 colunas (P-1): Descrição do Material (asset.name), Tombamento (asset.tag), Origem (origin_location_name), Destino (destination_location_name); gera `text` e `html` (o client escolhe pelo C-4).
**Rationale**: P-1/P-2 defaults confirmados; funções puras testáveis sem API (F12 fornece todos os dados); fiel ao modelo do setor (imagem do briefing).
**Alternatives**: incluir custodiante/termo (P-1 rejeitado — manter modelo exato) — registrado como evolução se o setor pedir.

### D11 — Eventos de auditoria
**Decision**: `ACTION_INTEGRACAO_1DOC_SOLICITADA/_ENVIADA/_FALHOU/_REPROCESSADA`, module `integracao_1doc`, `resource="movement"`, `resource_ref=tag`, `user=None` nos automáticos (F9), `new_data={"processo": ..., "destinatario_mensagem_id": ...}`; erros sanitizados (precedente `_sanitize_error_message` da 030 — token nunca em logs/auditoria).
**Rationale**: spec §11; simetria 030; Constitution VI/IX.

### D12 — Erros transitórios × permanentes
**Decision**: transitórios (timeout, conexão, 5xx) → estado `FAILED` com `attempt_count`, reprocessável (D9; retry automático efetivo só com worker — P-5); permanentes (4xx, processo inexistente pós-envio, credencial) → `FAILED` sem retentativa automática. `ONEDOC_MAX_ATTEMPTS` documenta o teto para a evolução worker.
**Rationale**: FR-010; sem loop infinito; volume baixo (D9 do plan).
**Alternatives**: backoff automático in-process (seguraria a request do usuário) — rejeitada (FR-013/§21).

## Pendências externas (Fase 1 — fornecedor 1Doc)

| Item | Status | Impacto |
|---|---|---|
| C-1 Autenticação | **A CONFIRMAR** | Header/token no `OneDocHttpClient` |
| C-2/C-3 Consulta/validação de processo | **A CONFIRMAR** | `find_process` (modo bloqueante vs tolerante da Q2) |
| C-4 Inclusão de comunicação + formatos | **A CONFIRMAR** | `send_communication` (text vs html) |
| C-5 Assinatura | **A CONFIRMAR** | Fora do escopo v1 (permanece manual no 1Doc) |
| C-6 Idempotência nativa | **A CONFIRMAR** | Reforço da D8 |
| C-7 Erros/limites | **A CONFIRMAR** | Mapeamento transitório × permanente |
| C-8 Homologação | **A CONFIRMAR** | Quickstart §5 (validação real) |

**Nenhum endpoint presumido.** Toda a mecânica interna é implementável com fakes; produção exige C-1..C-4 + credenciais + `ONEDOC_ENABLED=true`.
