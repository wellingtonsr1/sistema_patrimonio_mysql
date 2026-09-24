# Implementation Plan: Central de Integrações — Gerenciamento e Observabilidade

**Branch**: `032-central-integracoes` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/032-central-integracoes/spec.md`

## Summary

Criar a **Central de Integrações** — área de Administração com painel, detalhe/diagnóstico, teste de conexão, histórico de execuções e visão de propagação por movimentação para as integrações E-mail (030), 1Doc (031), GLPI (prevista) e Active Directory (existente). A Central é uma **camada de observabilidade**: consome um catálogo declarativo, deriva status padronizados das fontes existentes, registra um histórico unificado aditivo (decisão P-1) e delega cada ação (reprocessar, habilitar, configurar) aos mecanismos já vigentes. Nenhuma integração é reimplementada; nenhum endpoint externo é inventado.

## Technical Context

**Language/Version**: Python 3.10+ (stack vigente — Constitution)

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2, Pydantic v2, Jinja2 + Bootstrap 5, pytest — **zero dependências novas** (verificação de SMTP via `smtplib` já usada pelo `email_provider`; `requests` já presente para 1Doc/GLPI futuros)

**Storage**: MariaDB/MySQL (PyMySQL) — SQLite apenas na suíte de testes; migração aditiva idempotente via `init_db`/`_ensure_schema_migrations` (precedente 030/031)

**Testing**: pytest + TestClient com fakes (padrão `test_onedoc.py`/`test_notificacoes.py`); nenhum serviço externo real na suíte

**Target Platform**: Linux server (deploy existente `install.sh`/Docker), navegador desktop + resoluções menores, tema claro/escuro

**Project Type**: Web application monolítica em camadas (Web/API → Services → Models)

**Performance Goals**: painel renderiza agregações limitadas (contagens com janela 24h); histórico paginado (NFR-001) — sem varreduras ilimitadas

**Constraints**: nenhuma chamada externa na renderização do painel (NFR-004); teste de conexão com timeout vigente de cada integração; segredos mascarados em toda superfície (SC-003); suíte existente 100% verde (SC-006)

**Scale/Scope**: 4 integrações no catálogo na entrega; volume típico do órgão (centenas de movimentações/mês); 1 tela nova + 3 subtelas + estrutura de histórico

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Evidência no plano |
|---|---|---|
| I. Preservação e evolução incremental | ✅ PASS | Somente adições: novo service, novo model, novas rotas, novos templates; `email_provider` recebe função de diagnóstico isolada (`check_connection`) sem tocar `send`; nenhuma refatoração não relacionada |
| II. Arquitetura em camadas | ✅ PASS | Rotas autenticam/autorizam e delegam ao `integration_center_service`; regras de derivação de status moram no service |
| III. Regras nos services | ✅ PASS | Catálogo, derivação de status e orquestração de testes no service; templates apenas exibem |
| IV. Integridade patrimonial | ✅ PASS | Nenhuma alteração em `movement_service` (motor e hooks pós-commit intocados); propagação é somente leitura |
| V. Integridade do inventário | ✅ PASS | Fora de alcance (não toca inventário) |
| VI. Segurança/RBAC/credenciais | ✅ PASS | `require_permission("integracoes.visualizar"/"integracoes.testar")` + guardas existentes (AD, reprocesso 1Doc, notificações); segredos mascarados (FR-017); `check_connection` sem envio (P-6) |
| VII. Banco aditivo e idempotente | ✅ PASS | 1 tabela nova (`integration_executions`) via mecanismo existente; nenhuma coluna removida/alterada |
| VIII. Testes como regressão | ✅ PASS | Novo `tests/test_central_integracoes.py` com fakes; suíte existente intacta |
| IX. Auditoria | ✅ PASS | Eventos `ACTION_*` aditivos (`TESTE_INTEGRACAO_*`) + trilha existente; testes e reprocessos auditados, sem credenciais |
| X. Interface consistente | ✅ PASS | Templates no padrão `admin/`, tema claro/escuro, menu por permissão (`can()`), 403 amigável herdado |
| XI. Documentação fiel | ✅ PASS | README/docs/ajuda central atualizados na mesma tarefa (T-fase Polish) |
| XII. Spec-driven + validação | ✅ PASS | Fluxo Spec Kit seguido; quickstart.md define validação |

**Re-check pós-Phase 1**: ✅ PASS — o design (data-model/contracts) não introduz violação: única entidade nova é o histórico aditivo; nada duplica fonte de verdade (estado permanece em `notifications`/`onedoc_integrations`/`ad_settings`/`email_config`).

## Decisões (D1–D11 — resolve P-7 da spec)

- **D1 — Service novo**: `app/services/integration_center_service.py`. Contém: catálogo declarativo (`INTEGRATIONS`, cada entrada declara key, nome, finalidade, capacidades e função de derivação de status), derivação de status por integração (vocabulário da Seção 7 da spec), agregações do painel (contagens 24h, pendentes), orquestração dos testes da Central e `record_execution` (gravação best-effort no histórico — nunca levanta).
- **D2 — Modelo novo**: `app/models/integration_execution.py` → tabela `integration_executions` (data-model.md). Migração aditiva idempotente no `init_db` existente (padrão 030/031: `create_all` + guardas condicionais).
- **D3 — Instrumentação mínima** (únicos toques em arquivos existentes): chamadas `record_execution` após o estado final de (a) `notification_service._send`/fluxo de envio (e-mail), (b) `onedoc_service._send` (cobre envio e reprocesso), (c) teste de conexão AD existente (`admin_routes`), (d) testes da Central. Cada ponto envolto em try/except best-effort — registrar histórico nunca afeta a integração.
- **D4 — Permissões (P-2 aprovada)**: `PERMISSION_CATALOG` recebe `integracoes.visualizar` e `integracoes.testar` (módulo "Integrações"), sem concessão default; perfil Administrador recebe via seed idempotente existente (`DEFAULT_ROLES` lista o catálogo completo). Guardas vigentes permanecem: AD (`usuarios.editar`+`perfis.editar`), reprocesso 1Doc (`integracao1doc.reprocessar`), notificações (`notificacoes.gerenciar`).
- **D5 — Rotas web** (em `admin_routes.py`, padrão `require_permission`):
  - `GET /admin/integracoes` — painel (cards)
  - `GET /admin/integracoes/{key}` — detalhe/diagnóstico
  - `GET /admin/integracoes/{key}/historico` — histórico com filtros + paginação
  - `POST /admin/integracoes/{key}/testar` — teste de conexão (email/1doc: `integracoes.testar`; **ad**: redireciona ao teste existente da tela AD — guarda vigente preservada, P-3; **glpi**: rota inexistente — botão desabilitado)
  - `GET /admin/integracoes/movimentacao/{movement_id}` — propagação por movimentação (somente leitura)
- **D6 — Auditoria (aditiva)**: `audit_service.py` recebe `ACTION_CENTRAL_TESTE_SUCESSO = "TESTE_INTEGRACAO_SUCESSO"`, `ACTION_CENTRAL_TESTE_FALHA = "TESTE_INTEGRACAO_FALHA"` + rótulos; `module="central_integracoes"`. Execuções automáticas seguem gravando seus eventos já existentes (030/031/AD).
- **D7 — Derivação de status** (função por integração, precedência da spec §7): e-mail (SMTP_HOST ausente → NÃO CONFIGURADA; notificações desativadas → DESABILITADA; última execução FAILED → COM ERRO/INDISPONÍVEL conforme classe; sucesso recente → ATIVA; habilitada sem execuções → INATIVA); 1Doc (contrato `[PENDING C-1..C-4]` não confirmado → **PENDENTE** (aguardando fornecedor) com precedência sobre DESABILITADA — a integração nunca operou; após contrato: regra do e-mail com `ONEDOC_ENABLED`); AD (`enabled=false` → DESABILITADA; server/base_dn ausentes → NÃO CONFIGURADA; último teste falhou → COM ERRO/INDISPONÍVEL; senão ATIVA com última verificação); GLPI (NÃO CONFIGURADA fixa).
- **D8 — Teste de conexão**: e-mail → nova `email_provider.check_connection()` (conecta, STARTTLS, login, encerra — **nenhuma mensagem enviada**, P-6); 1doc → verificação **interna** de configuração (presença de URL/token + estado do contrato), sem chamada externa enquanto `[PENDING C-*]`; ad → mecanismo existente (`TESTE_CONEXAO_AD`); glpi → não suportado. Todo teste registra `record_execution` + auditoria (FR-012).
- **D9 — Templates**: `app/web/templates/admin/integracoes/{list,detail,historico,movimentacao}.html` no padrão visual vigente; `base.html` recebe entradas de menu (sidebar + dropdown Administração) sob `can('integracoes.visualizar')` — único toque em template existente.
- **D10 — Janela de falhas (P-4)**: contagem `result='FAILURE'` nas últimas 24 h em `integration_executions`, rotulada "Falhas recentes (24h)" no card.
- **D11 — Pendências externas**: Fase 1 (fornecedor 1Doc / investigação GLPI) **não bloqueia a Central**; bloqueia apenas a ativação do 1Doc e a implementação do GLPI (spec §18). A Central representa os bloqueios (PENDENTE/NÃO CONFIGURADA).

## Project Structure

### Documentation (this feature)

```text
specs/032-central-integracoes/
├── plan.md                                  # Este arquivo
├── research.md                              # Phase 0 output
├── data-model.md                            # Phase 1 output
├── quickstart.md                            # Phase 1 output
├── contracts/
│   └── central-de-integracoes-contract.md   # Phase 1 output
└── tasks.md                                 # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── models/
│   └── integration_execution.py             # NOVO — IntegrationExecution
├── services/
│   ├── integration_center_service.py        # NOVO — catálogo, status, testes, record_execution
│   ├── email_provider.py                    # TOQUE MÍNIMO — + check_connection() (send intocado)
│   ├── notification_service.py              # TOQUE MÍNIMO — + record_execution pós-estado final
│   ├── onedoc_service.py                    # TOQUE MÍNIMO — + record_execution em _send
│   ├── permission_service.py                # TOQUE MÍNIMO — + 2 permissões no catálogo
│   └── audit_service.py                     # TOQUE MÍNIMO — + eventos TESTE_INTEGRACAO_*
├── database.py                              # TOQUE MÍNIMO — migração aditiva da tabela nova
├── web/
│   ├── admin_routes.py                      # TOQUE — rotas da Central + record no teste AD
│   └── templates/
│       ├── admin/integracoes/*.html         # NOVO — 4 templates
│       └── base.html                        # TOQUE MÍNIMO — entradas de menu
docs/                                        # Atualização na mesma tarefa (Constitution XI)
tests/
└── test_central_integracoes.py              # NOVO — fakes; nenhum serviço externo real
```

**Intocáveis** (Constitution I): `movement_service` (motor + hooks pós-commit), `backup_*`, regras de `ad_service`/`ad_ldap`, `onedoc_client` (`[PENDING C-*]` permanece), telas administrativas existentes (Notificações, AD, 1Doc), suíte de testes existente.

**Structure Decision**: estrutura monolítica vigente mantida (Option única do projeto); nenhuma árvore paralela criada.

## Complexity Tracking

> Sem violações de Constitution — tabela vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (nenhuma) | — | — |
