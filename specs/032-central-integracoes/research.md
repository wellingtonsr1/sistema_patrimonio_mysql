# Phase 0 Research: Central de Integrações — Gerenciamento e Observabilidade

**Feature**: 032 | **Data**: 2026-09-23 | **Spec**: [spec.md](spec.md)

## Fatos verificados no código (leituras 2026-09-23)

| # | Fato | Fonte |
|---|---|---|
| F1 | `notification_service.notify_movement(db, movement, *, operator, ip_address, provider)` — nunca levanta; estados PENDING/SENT/FAILED com UNIQUE em `movement_id`; erro sanitizado | `app/services/notification_service.py` |
| F2 | `onedoc_service.notify_movement(...)` + `onedoc_service.reprocess(db, integration_id, *, user, ip_address, provider)` — mesmo contrato best-effort; `_send(db, integration, movement, provider)` é o ponto único de envio (cobre 1º envio e reprocesso) | `app/services/onedoc_service.py` |
| F3 | `email_provider.SMTPEmailProvider.send(...)` — único ponto que conhece SMTP; já sanitiza erros; `SMTP_HOST/PORT/USERNAME/PASSWORD/FROM/USE_TLS/SEND_TIMEOUT` em ambiente | `app/services/email_provider.py`, `app/config.py` |
| F4 | AD: tela `/admin/ad` com guarda `_ad_admin_guard` (`usuarios.editar` + `perfis.editar`), teste de conexão auditado (`TESTE_CONEXAO_AD`), singleton `ad_settings` + fallback env `AD_*` | `app/web/admin_routes.py`, `app/services/ad_service.py` |
| F5 | GLPI: **zero** ocorrências no código — integração inexistente | varredura do repositório |
| F6 | Hooks pós-commit em `movement_service.create_movement` (030 e-mail → 031 1Doc), best-effort, captura total — ponto de não-retorno após `db.commit()` | `app/services/movement_service.py` L340–385 |
| F7 | RBAC: `PERMISSION_CATALOG` (lista de dicts), seed idempotente `ensure_default_roles`; permissões 030/031 sem concessão default; Administrador = lista completa do catálogo | `app/services/permission_service.py` |
| F8 | Auditoria: `write_audit(db, user=..., action=..., module=..., resource=..., resource_id=..., resource_ref=..., ip_address=..., result=..., description=..., new_data=...)`; constantes `ACTION_*` + `ACTION_LABELS` | `app/services/audit_service.py` |
| F9 | Migração aditiva idempotente no `init_db` (`_ensure_schema_migrations` com ALTER condicional) — precedente das features 021/030/031 | `app/database.py` |
| F10 | Menu: sidebar + dropdown Administração em `base.html`, guardado por `can('permissao')`; telas admin usam `active_tab="admin"` | `app/web/templates/base.html` |
| F11 | Suíte pytest com fakes via `provider=None` → parâmetro `provider` injetável nos services 030/031; TestClient; SQLite em memória | `tests/test_onedoc.py`, `tests/test_notificacoes.py`, `tests/conftest.py` |
| F12 | Fuso do operador: `format_local` (America/Recife) para exibição; `now_utc` para armazenamento (convenção 004) | `app/utils/time_utils.py` |

## Decisões

### D1 — Catálogo declarativo no service da Central (não no banco)
- **Decisão**: as integrações se registram em uma estrutura Python declarativa (`INTEGRATIONS`) dentro de `integration_center_service.py`; o banco guarda apenas o histórico unificado de execuções.
- **Rationale**: o catálogo descreve código (capacidades, função de status de cada integração) — não é dado de negócio; tabelas de registro exigiriam seed/sincronização sem ganho. Extensibilidade (FR-005/SC-007) preservada: nova integração = nova entrada declarativa.
- **Alternativas consideradas**: tabela `integrations` em banco (descartada — metadado de código em banco, sincronização extra); descoberta automática por convenção (descartada — mágica implícita, contra a simplicidade exigida).

### D2 — Histórico unificado em tabela aditiva (P-1 decidida no clarify)
- **Decisão**: tabela `integration_executions` alimentada por `record_execution` nos pontos de estado final (hooks 030/031, testes da Central, teste AD).
- **Rationale**: filtros/paginação eficientes (FR-019/SC-009), lugar natural para execuções que não têm tabela própria (testes de conexão), sem duplicar a fonte de verdade do **estado** (que permanece em `notifications`/`onedoc_integrations`/`ad_settings`).
- **Alternativas consideradas**: UNION sob consulta (descartada — consultas caras, sem registro para testes da Central); híbrido (descartado — dois caminhos de leitura).

### D3 — Teste de conexão por integração (P-3/P-6 decididas no clarify)
- **Decisão**: e-mail → `email_provider.check_connection()` nova função (conexão + STARTTLS + login + encerramento, **sem envio**); 1doc → verificação interna de configuração (sem chamada externa enquanto `[PENDING C-1..C-4]`); ad → mecanismo existente da tela AD (guarda vigente, a Central linka em vez de duplicar); glpi → sem teste.
- **Rationale**: mantém a garantia de teste não destrutivo (FR-011) e a autorização vigente por integração (FR-013/P-3); reusa `SMTP_*`/timeout vigentes; zero endpoints inventados.
- **Alternativas consideradas**: e-mail com mensagem de teste (descartada — P-6); teste 1Doc via `find_process` (descartado — exigiria endpoint real não confirmado).

### D4 — Derivação de status 100% no service, sem chamada externa no GET do painel
- **Decisão**: o painel deriva status de configuração efetiva + tabelas + `integration_executions`; chamadas externas só no POST de teste (com timeout).
- **Rationale**: NFR-004 (sem cascata de health checks); renderização do painel determinística e rápida; SC-005 sem consultas manuais ao banco.
- **Alternativas consideradas**: health check automático em background (descartado nesta versão — P-5 adiada); status persistido (descartado — duplicaria verdade).

### D5 — Permissões próprias da Central (P-2 decidida no clarify)
- **Decisão**: `integracoes.visualizar` + `integracoes.testar` no `PERMISSION_CATALOG`, sem concessão default, Administrador via catálogo; guardas vigentes permanecem por ação específica.
- **Rationale**: padrão 030/031; permite delegar a observabilidade sem expor telas de configuração.
- **Alternativas consideradas**: reuso de `is_admin` (descartado — menos granular); só `visualizar` (descartado — contradiz P-2).

### D6 — Instrumentação best-effort (D3 do plan) em 3 pontos existentes
- **Decisão**: `record_execution` chamado em (a) fim do fluxo de envio da `notification_service`, (b) `_send` da `onedoc_service` (cobre 1º envio e reprocesso), (c) teste de conexão AD na rota existente; sempre em try/except, nunca altera o resultado da integração.
- **Rationale**: mínimo toque (Constitution I); falha de observabilidade nunca vira falha de integração (mesmo espírito do best-effort dos hooks).
- **Alternativas consideradas**: eventos de banco/triggers (descartados — fora do padrão do projeto); reescrever services (proibido).

### D7 — Auditoria aditiva no padrão ACTION_*
- **Decisão**: `TESTE_INTEGRACAO_SUCESSO` / `TESTE_INTEGRACAO_FALHA` (module `central_integracoes`); demais ações continuam com seus eventos já vigentes (ALTERACAO_CONFIG_AD, CONFIG_NOTIFICACAO_ALTERADA, INTEGRACAO_1DOC_REPROCESSADA...).
- **Rationale**: evita duplicação de eventos já existentes (F8); trilha única imutável (Princípio IX).
- **Alternativas consideradas**: eventos novos para habilitar/desabilitar (desnecessário — já existem pelas telas vigentes).

### D8 — Zero dependências novas
- **Decisão**: verificação SMTP via `smtplib` (stdlib, já usada); sem libs de health check; `requests` permanece para o futuro 1Doc/GLPI.
- **Rationale**: requirements.txt intocado; superfície de segurança inalterada.

### D9 — Documentação e ajuda central na mesma tarefa
- **Decisão**: README/docs + `help_service`/artigo de ajuda recebem a nova tela e permissões (Princípio XI); padronizar com o precedente do artigo de ajuda da 030 (`help_article_030.py`).

## Pendências externas (não bloqueiam a Central — espelham spec §18)

1. **1Doc (C-1..C-8)**: contrato real pendente do fornecedor — solicitação formal em `docs/SOLICITACAO_API_1DOC.md`. Enquanto isso: status PENDENTE, teste interno apenas.
2. **GLPI**: versão/API/autenticação/vínculo de equipamentos a investigar na instalação real — nada implementado nesta feature.
3. **P-7 encerrada**: nomes finais decididos neste plano (D1–D9 do plan.md e acima).

## NEEDS CLARIFICATION do Technical Context

- Nenhum — stack, storage, testes e plataforma extraídos da Constitution e do código (fatos F1–F12).
