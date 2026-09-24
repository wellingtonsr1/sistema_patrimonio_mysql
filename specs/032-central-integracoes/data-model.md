# Data Model: Central de Integrações (feature 032)

## Entidade nova: `IntegrationExecution` (`integration_executions`)

Histórico unificado de execuções de integração (decisão P-1/plan D2): **registra ocorrências**, não substitui a fonte de verdade do estado (que permanece em `notifications`, `onedoc_integrations`, `ad_settings`, `email_config`).

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `integration_key` | String(30), NOT NULL, index | `email` \| `onedoc` \| `ad` \| `glpi` \| futuras — chave do catálogo (plan D1) |
| `operation` | String(40), NOT NULL | tipo de operação: `SEND_EMAIL` \| `SEND_COMMUNICATION` \| `REPROCESS` \| `CONNECTION_TEST` \| `INTERNAL_CHECK` |
| `result` | String(20), NOT NULL, index | `SUCCESS` \| `FAILURE` (padrão `RESULT_*` do audit_service) |
| `duration_ms` | Integer, nullable | duração da execução/teste; NULL = não medido |
| `user_id` | Integer, FK `users.id` ON DELETE SET NULL, nullable | ator humano (teste/reprocesso); NULL = ator é o serviço (execuções automáticas — precedente 030/031) |
| `username` | String(100), nullable | snapshot do username (sobrevive à exclusão — padrão AuditLog) |
| `movement_id` | Integer, nullable, index | referência fraca à movimentação quando aplicável — SEM FK/UNIQUE (a fonte de verdade do vínculo 1:1 permanece nas tabelas de integração) |
| `detail` | Text, nullable | erro/informação **sanitizada** (mesma sanitização vigente — Constitution VI), máx. 2000 chars |
| `created_at` | DateTime, default `now_utc` | armazenamento UTC (convenção 004) |

**Índices** (suportam os filtros do FR-019 e a agregação D10): `(integration_key, created_at)`, `(integration_key, result, created_at)`, `created_at`.

**Política de retenção**: sem exclusão nesta versão (volume baixo — execuções por movimentação + testes manuais); evolução futura poderá podar por idade, se necessário.

## Entidades existentes (SOMENTE LEITURA — intocáveis)

| Entidade | Uso pela Central |
|---|---|
| `EmailConfig` (`email_config`) | ativação/destinatários → derivação de status do e-mail |
| `Notification` (`notifications`) | execução/sucesso/falha de e-mail por movimentação; contadores |
| `OneDocIntegration` (`onedoc_integrations`) | execução/sucesso/falha de 1Doc; contadores; reprocesso |
| `ADSettings` (`ad_settings`) | `enabled`, servidor/base DN → derivação de status do AD |
| `Movement` (`movements`) | propagação por movimentação (somente leitura) |
| `AuditLog` (`audit_logs`) | fontes de eventos já vigentes; destino dos novos eventos de teste |

## Configuração (nenhuma nova; fontes vigentes)

| Integração | Fonte da configuração efetiva | Segredo (nunca exibido) |
|---|---|---|
| E-mail | `email_config` + `SMTP_*` (env) | `SMTP_PASSWORD` |
| 1Doc | `ONEDOC_*` (env) | `ONEDOC_API_TOKEN` |
| AD | `ad_settings` + `AD_*` (env, fallback) | senha nunca persistida (bind direto) |
| GLPI | — (não configurada) | — |

## Catálogo de integrações (estrutura em código — plan D1, não é tabela)

Cada entrada declara: `key`, `name`, `description`, `purpose`, capacidades (`supports_test`, `supports_reprocess`, `supports_enable_disable`, `external`), `status_fn` (derivação §7 da spec) e referências de configuração/histórico. Extensível por adição de entrada (SC-007).

## Permissões (seed idempotente via catálogo existente)

| Permissão | Módulo | Concessão default |
|---|---|---|
| `integracoes.visualizar` | Integrações | NENHUMA (padrão 030/031); Administrador recebe via `DEFAULT_ROLES` |
| `integracoes.testar` | Integrações | NENHUMA; Administrador recebe via `DEFAULT_ROLES` |

## Regras de integridade

1. `integration_executions` é **append-only** pela aplicação: nenhuma rota/edit cria altera ou exclui registros (espelha o espírito somente-leitura do AuditLog).
2. Nenhum segredo em `detail` ou em qualquer campo — sanitização em profundidade vigente (NFR-002).
3. `record_execution` é best-effort: falha de gravação **nunca** propaga para a integração (plan D6).
4. Migração aditiva idempotente via `init_db`/`_ensure_schema_migrations` — nenhum dado existente é tocado (Constitution VII).
5. Eventos de auditoria novos (`TESTE_INTEGRACAO_*`) não duplicam eventos já vigentes (plan D7).
