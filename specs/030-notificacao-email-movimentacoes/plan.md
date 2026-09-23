# Implementation Plan: Notificação por E-mail ao Setor de Patrimônio após Movimentação

**Branch**: `030-notificacao-email-movimentacoes` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/030-notificacao-email-movimentacoes/spec.md` (com Clarifications 2026-09-23: Q1–Q4 resolvidas).

## Summary

Disparar automaticamente um e-mail institucional ao setor de Patrimônio após a conclusão e persistência bem-sucedida de movimentações dos tipos `ALOCACAO_CAUTELA`, `TRANSFERENCIA_LOCAL` e `DEVOLUCAO_ESTOQUE` concluídas por fluxos manuais (web/API). O disparo é best-effort e **isolado do commit** da movimentação (falha de e-mail jamais afeta a operação patrimonial — RN-001). A infraestrutura é nova e isolada: `NotificationService` (orquestra idempotência/configuração/registro/auditoria) + provedor de e-mail (único ponto SMTP, `smtplib` da stdlib — **zero dependências novas**). Configuração segue o precedente 021: destinatários/ativação persistidos em singleton administrável por tela (`/admin/notificacoes`, permissão nova `notificacoes.gerenciar`); credenciais SMTP exclusivamente em ambiente (`SMTP_*` em `.env` — padrão `AD_BIND_PASSWORD`). Idempotência estrutural: tabela nova `notifications` com vínculo **um-para-um** com a movimentação (garantia de no máximo 1 e-mail por movimentação — RN-007). Auditoria com 3 ações novas no padrão `ACTION_*` + rótulos. Nascida **desativada** (comportamento atual preservado até ativação explícita).

## Technical Context

**Language/Version**: Python 3.10+ (stack existente — Constitution, Restrições de Tecnologia)

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2 (PyMySQL), Pydantic v2, Jinja2 + Bootstrap 5 — **todos existentes; nenhuma dependência adicionada** (envio SMTP via `smtplib`/`email.message` da stdlib)

**Storage**: MariaDB/MySQL produção (`DATABASE_URL=mariadb+pymysql://...`); SQLite exclusivo da suíte de testes. Alteração de schema: **1 tabela nova** (`notifications`) via `Base.metadata.create_all` — aditiva, idempotente, precedente `backup_records` (020); `_ensure_schema_migrations` não precisa ser estendido (nenhuma coluna nova em tabela existente)

**Testing**: pytest + TestClient (padrões existentes); fakes do provedor de e-mail — nunca SMTP real na suíte

**Target Platform**: Windows e Linux (ambos já suportados pelo projeto — NFR-005)

**Project Type**: Aplicação web existente (FastAPI monolítica em camadas: web/API → services → models)

**Performance Goals**: conclusão da movimentação não degrada além do timeout de envio configurável (default 10 s); notificação disparada somente para tipos elegíveis (RN-002)

**Constraints**: envio best-effort pós-commit com timeout curto; **zero** segredo em logs/auditoria; default **desativado**; e-mail sem link de consulta nesta versão (RN-008 — campo de conteúdo reservado no modelo, sem URL gerada agora); retry automático fora da v1 (P-1)

**Scale/Scope**: volume de movimentações manuais do órgão (baixo — envio síncrono pós-commit é adequado; fila/worker é evolução futura preparada)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência/Justificativa |
|---|---|---|
| I. Preservação do sistema existente / evolução incremental | ✅ PASS | Tudo é extensão: 1 service novo, 1 provedor novo, 1 model/tabela nova, rota admin nova, hook **aditivo** no fim de `create_movement`. Nenhum módulo reescrito; nenhuma funcionalidade removida. Com `notificações desativadas` (default) o comportamento do sistema é byte-idêntico ao atual. Regra de escopo respeitada: nenhuma refatoração não relacionada |
| II. Arquitetura em camadas | ✅ PASS | Regras de notificação 100% em services (`notification_service`, `email_provider`, `email_config_service`); rotas admin apenas autenticam/autorizam/validam e delegam; o disparo é **solicitado pelo service de movimentação** (não montado por rotas) |
| III. Regras de negócio nos services | ✅ PASS | Elegibilidade de tipos (RN-002), montagem de assunto/corpo (RN-005/FR-008), idempotência (RN-007) e tratamento de falhas vivem em `notification_service`; nenhum template/rota contém regra |
| IV. Integridade patrimonial e movimentações | ✅ PASS | `MovementService.create_movement` permanece a **única** porta de alteração de estado/local/custódia; a feature não altera nenhuma validação (VAL-002..008), tipos ou trilha de movimentação; hook é pós-commit e silencioso por contrato |
| V. Integridade do inventário | ✅ PASS | Inventário não é tocado (fora de escopo) |
| VI. Segurança por padrão (auth/RBAC/AD/credenciais) | ✅ PASS | Rota nova `/admin/notificacoes` com `require_permission("notificacoes.gerenciar")` (deny by default, permissão nova criada sem conceder a ninguém por padrão); `SMTP_PASSWORD` **somente ambiente** (precedente `AD_BIND_PASSWORD`), nunca em banco/logs/auditoria/erros; destinatário sempre da configuração oficial (RN-004) |
| VII. Banco MariaDB e proteção dos dados | ✅ PASS | Única alteração: tabela **nova** `notifications` (aditiva, criada por `create_all` no `init_db` — precedente `backup_records`/020); nenhum ALTER/drop/renome; nenhum dado existente tocado; `_ensure_schema_migrations` intocado |
| VIII. Testes como requisito de não regressão | ✅ PASS | Novo módulo de testes cobre os 13 cenários da spec (Seção 14); suíte existente permanece intacta e verde (com default desativado, nenhum teste existente é afetado) |
| IX. Auditoria das operações relevantes | ✅ PASS | 3 ações novas (`NOTIFICACAO_ENVIADA`, `NOTIFICACAO_FALHOU`, `CONFIG_NOTIFICACAO_ALTERADA`) no padrão `ACTION_*` + `ACTION_LABELS`, via `write_audit`/`write_change_audit`, sem credenciais; trilha permanece imutável |
| X. Interface consistente e funcional | ✅ PASS | Tela admin nova segue o padrão 021/022 (layout, componentes, tooltips); menu admin ganha entrada conforme permissão; nenhum fluxo existente alterado |
| XI. Documentação fiel | ✅ PASS | Tarefa de documentação no escopo: README (variáveis `SMTP_*`), docs/ARQUITETURA (módulos novos) e central de ajuda `/ajuda` (artigo da configuração) — Constitution XI |
| XII. Spec-first e validação | ✅ PASS | Fluxo Spec Kit seguido (spec → clarify → plan → tasks → implement); validação final = suíte + quickstart |

**GATE: 12/12 PASS — prosseguir para Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/030-notificacao-email-movimentacoes/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — decisões D1–D10 com evidência
├── data-model.md        # Phase 1 output — EmailConfig + Notification
├── quickstart.md        # Phase 1 output — validação ponta a ponta
├── contracts/           # Phase 1 output — contratos dos caminhos afetados
│   └── notifications-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
app/
├── config.py                        # + variáveis SMTP_* e SMTP_SEND_TIMEOUT (bootstrap, pós load_dotenv)
├── models/
│   └── notification.py              # NOVO: EmailConfig (singleton) + Notification
├── services/
│   ├── email_config_service.py      # NOVO: get/save configuração (precedente 021: persistido → env → default)
│   ├── notification_service.py      # NOVO: elegibilidade, idempotência, assunto/corpo, auditoria
│   ├── email_provider.py            # NOVO: protocolo EmailProvider + SMTPEmailProvider (único ponto SMTP)
│   └── movement_service.py          # + hook pós-commit (chamada única, aditiva) + parâmetro notify=True
├── services/import_service.py       # + notify=False na chamada em lote (RN-002 — lote não notifica)
├── services/audit_service.py        # + 3 constantes ACTION_* + rótulos
├── web/
│   ├── admin_routes.py              # + GET/POST /admin/notificacoes (require_permission notificacoes.gerenciar)
│   └── templates/admin/
│       └── notificacoes.html        # NOVO: tela de configuração (padrão 021/022)
└── (demais arquivos intocados)

tests/
└── test_notificacoes.py             # NOVO: 13 cenários da spec Seção 14 (fakes de provider)

README.md, docs/ARQUITETURA_E_MANUTENCAO.md, app/web/templates/base (menu)  # documentação + entrada de menu
```

**Structure Decision**: estrutura monolítica em camadas existente preservada — nada de novos pacotes/top-level. Os módulos novos entram exatamente onde os precedentes estão (`app/services/` para regras, `app/models/` para entidades, `app/web/templates/admin/` para a tela admin), maximizando reuso e consistência (FR-015).

## Resumo das Decisões (detalhadas em research.md)

| # | Decisão | Fundamento |
|---|---|---|
| D1 | SMTP via stdlib (`smtplib` + `email.message.EmailMessage`), sem dependência nova | Menor risco; Constitution I; zero impacto em deploy |
| D2 | Provedor isolado injetável (`EmailProvider` protocol + `SMTPEmailProvider`) | Único ponto que conhece SMTP; mock trivial nos testes; troca por canal/fila no futuro sem tocar o domínio |
| D3 | Orquestração em `NotificationService.notify_movement(db, movement)` | Chamada única a partir de `create_movement`; idempotência/config/auditoria centralizadas |
| D4 | Hook pós-commit no fim de `create_movement` + parâmetro **aditivo** `notify: bool = True` | Default True preserva todos os chamadores; `import_service` passa `notify=False` (RN-002 lote); exceção do hook jamais escapa |
| D5 | Elegibilidade por conjunto de tipos `{ALLOCATION, TRANSFER, RETURN_STOCK}` (constante do módulo) | RN-002/Q1; dupla checagem (hook + service) por defesa em profundidade |
| D6 | `EmailConfig` singleton (precedente BackupConfig) + `email_config_service` | Persistido → env (bootstrap) → default; tela admin padrão 021 |
| D7 | `Notification` (tabela nova `notifications`, vínculo único com `movement_id`) | Garantia estrutural da idempotência (RN-007); campo `content_url` reservado **nulo** (RN-008 — link futuro sem reestruturar) |
| D8 | Credenciais exclusivamente em `SMTP_*` (env); demais parâmetros idem | Constitution VI; precedente `AD_BIND_PASSWORD`/`MYSQLDUMP_PATH` em `app/config.py` |
| D9 | 3 eventos de auditoria: `NOTIFICACAO_ENVIADA`, `NOTIFICACAO_FALHOU`, `CONFIG_NOTIFICACAO_ALTERADA` | Padrão `ACTION_*` + rótulos (Seção 10 da spec — D6 da spec: sem evento "solicitada") |
| D10 | Timeout de envio `SMTP_SEND_TIMEOUT` (default 10 s) + na tela apenas ativação/destinatários | FR-016/SC-006; config admin mínima (US3); segredos nunca na tela/banco |

## Complexity Tracking

> Nenhuma violação de Constitution — seção vazia por design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (nenhuma) | — | — |

## Post-Design Constitution Check (re-avaliação após Phase 1)

| Princípio | Status | Nota pós-design |
|---|---|---|
| I, II, III, IV | ✅ PASS | Contrato de `create_movement` é **estritamente aditivo** (`notify=True` default — nenhum chamador existente muda comportamento; ver contracts/notifications-contract.md §1). Hook não altera retorno nem validações |
| V, X, XI, XII | ✅ PASS | Sem alteração de inventário/UI existente; doc no escopo das tarefas |
| VI | ✅ PASS | Permissão nova `notificacoes.gerenciar` criada no catálogo **sem concessão default**; `SMTP_PASSWORD` fora de banco/tela/logs (contract §5) |
| VII | ✅ PASS | `data-model.md`: apenas tabela nova; nenhum dado/coluna/tabela existente tocado |
| VIII, IX | ✅ PASS | Estratégia de testes preserva suíte; eventos de auditoria sem segredos (contract §4) |

**GATE pós-design: 12/12 PASS.**
