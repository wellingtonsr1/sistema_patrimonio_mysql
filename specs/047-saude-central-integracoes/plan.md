# Implementation Plan: Central de Integrações — Saúde do Sistema e das Integrações (047)

**Branch**: `047-saude-central-integracoes` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/047-saude-central-integracoes/spec.md`

## Summary

Ampliar o catálogo declarativo da Central de Integrações (032, já implementada) com seis componentes de saúde do sistema — Aplicação, Banco de Dados, Armazenamento, Backup Local, Backup Externo e Agendador de Backup — derivando seus estados **exclusivamente** das fontes existentes (semântica do `/health`, `backup_records`, `retention_monitoring_summary`, `scheduler_status`, `backup_external_*`, `shutil.disk_usage`), sem I/O externo ao renderizar o painel, sem tabelas novas, sem permissões novas e sem nenhum mecanismo de teste duplicado. O painel `/admin/integracoes` torna-se a visão consolidada de saúde (grid de 3 colunas em telas grandes, na ordem do pedido); testes manuais continuam sendo ações explícitas reutilizando os mecanismos vigentes (a única extensão de dispatcher é `run_test(backup_externo)` **chamando a função `test_destination` existente** da 045).

## Technical Context

**Language/Version**: Python 3.10+ (venv em `.venv/`; rodar com `.venv/bin/python`)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Jinja2/Bootstrap 5 (stack vigente — Constitution); `shutil.disk_usage` (biblioteca padrão, já usada por `external_backup_service`)

**Storage**: MariaDB/MySQL em produção; SQLite em memória na suíte (`tests/conftest.py` — `engine`, `TestingSessionLocal`, `_override_get_db`). **Zero migração nesta feature** (nenhuma tabela/coluna nova — FR-028/SC-009)

**Testing**: pytest + TestClient (baseline: **748 passed**); fakes/tmp_path para sistema de arquivos e serviços externos — nunca serviços reais

**Target Platform**: Linux server (produção IPMJP); navegadores desktop/mobile

**Project Type**: Web application monolítica (app/web + app/services + app/models)

**Performance Goals**: renderização do painel sem I/O externo e sem operações caras (SC-002: 0 gerações de backup, 0 testes SMTP/LDAP/destino, 0 threads ao abrir a página); testes manuais ≤ 10 s (SC-005, herdados dos mecanismos vigentes)

**Constraints**: menor alteração possível (regra máxima do pedido); nenhuma regra global de CSS novo; nenhuma alteração em `app/main.py` (health), `backup_service`, `backup_scheduler`, `external_backup_service` (exceto **nenhuma** — ver R5), `ad_*`, `email_*`, `onedoc_*`, `permission_service`

**Scale/Scope**: 1 tela modificada (`admin/integracoes/list.html`), 1 service estendido (`integration_center_service.py`), 1 dispatcher de teste estendido (ramo `backup_externo`), 1 novo arquivo de testes, docs/ajuda atualizadas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Conformidade | Evidência |
|---|---|---|
| I. Evolução incremental / menor alteração | ✅ | Extensão do catálogo da 032 (mecanismo previsto por ela); nenhum módulo reescrito; F1–F14 |
| II/III. Camadas / regras nos services | ✅ | Todas as status_fn vivem em `integration_center_service.py`; rotas apenas delegam |
| IV/V. Integridade patrimonial/inventário | ✅ | Nenhuma alteração patrimonial; painel é somente leitura |
| VI. Segurança/RBAC/credenciais | ✅ | Permissões existentes reutilizadas (`integracoes.visualizar`/`integracoes.testar`); `mask_secret`/`_sanitize_detail` reutilizados; nenhum segredo novo em superfície |
| VII. Banco aditivo | ✅ | **Zero migração** — estados calculados (spec §10/FR-028) |
| VIII. Testes | ✅ | Novo `tests/test_central_saude.py`; suíte 748 verde (SC-006) |
| IX. Auditoria | ✅ | `record_execution` + `write_audit` existentes reutilizados; nenhum evento por carregamento |
| X. UI consistente | ✅ | Cards/badges/grid existentes; nenhum CSS global novo |
| XI. Documentação | ✅ | Ajuda da Central + docs na mesma tarefa |
| XII. Validação | ✅ | Suíte + validação manual registrada |

**Resultado: SEM violações — gate aprovado (reavaliado após Phase 1: sem alteração — o design não introduz nada além do previsto).**

## Project Structure

### Documentation (this feature)

```text
specs/047-saude-central-integracoes/
├── plan.md                     # Este arquivo
├── research.md                 # Phase 0 — decisões P-1/P-2/P-3 e fatos R1–R8
├── data-model.md               # Phase 1 — vocabulário de status, catálogo, derivações
├── contracts/
│   └── ui-contract-central-saude.md  # Phase 1 — contrato de UI do painel
├── quickstart.md               # Phase 1 — cenários de validação
├── checklists/requirements.md  # Da specify/clarify
└── tasks.md                    # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
app/
├── services/
│   └── integration_center_service.py   # ESTENDIDO: 6 status_fn + catálogo + dispatcher
├── web/
│   ├── admin_routes.py                 # intocado* (painel já deriva via get_panel)
│   └── templates/admin/integracoes/
│       └── list.html                   # ESTENDIDO: grid 3 colunas + pares de resumo
tests/
└── test_central_saude.py               # NOVO
docs/ + help_article_032.py             # ATUALIZADOS (ajuda da Central)
```

**Structure Decision**: Projeto único vigente (Constitution II). *`admin_routes.py` permanece intocado porque `get_panel(db)` já itera o catálogo e retorna cards — novos componentes aparecem automaticamente; nenhuma rota nova é criada.

## Decisões de plan (P-1/P-2/P-3 da spec + R1–R8 do research)

| ID | Decisão |
|---|---|
| **P-1 (keys)** | `app`, `database`, `storage`, `backup_local`, `backup_externo`, `scheduler` — inglês curto, padrão das keys existentes (`email`, `onedoc`, `ad`, `glpi`) |
| **P-2 (Armazenamento)** | Diretório verificado: o de backup local configurado (`BACKUP_DIR`/`backup_config`) e, se o destino externo estiver habilitado e configurado, também o dele. Referência da regra: `size_bytes` do último `BackupRecord` SUCCESS com `removed_at IS NULL` (consulta direta — `retention_monitoring_summary` não expõe tamanho). Espaço livre < tamanho de referência → `ATENCAO`; `disk_usage` levanta OSError ou diretório inexistente → `COM_ERRO`; sem backup válido de referência → `ATIVA` (nada indica risco; registrado no card como "sem backup de referência") |
| **P-3 (grid)** | Ordem do catálogo = ordem do pedido: app, database, storage, ad, email, glpi, backup_local, backup_externo, scheduler, onedoc. Template: `col-12 col-md-6 col-xl-4` (3 colunas em ≥1200px, 2 em tablet, 1 no celular). 1Doc fecha a lista (10º card) |
| **R1 (vocabulário)** | 1 constante nova **aditiva**: `STATUS_ATENCAO` (label "Atenção", badge `bg-warning text-dark` — mesma cor do amarelo vigente). Nenhum status existente muda de significado |
| **R2 (rótulos por componente)** | Entrada opcional `label_by_status` no catálogo (dict) — ex.: `app`: ATIVA→"Operacional"; `database`: ATIVA→"Conectado", COM_ERRO→"Falha". Fallback: `STATUS_LABELS` global. Extensão declarativa, sem alteração estrutural |
| **R3 (resumo do card)** | `status_fn` retorna `detail["summary"] = [(rótulo, valor), ...]` (1–3 pares). O template renderiza os pares quando presentes e mantém a `dl` atual (última execução/sucesso/falhas 24h/pendentes) para as integrações — nenhum card perde informação |
| **R4 (teste backup_externo)** | `run_test` ganha ramo `backup_externo` → `external_backup_service.test_destination(config.dest_path)` — **reuso da função existente da 045** (mesmo arquivo temporário gravado/lido/removido; nenhum segundo mecanismo). Registra via `record_execution` + `write_audit` existentes (op `OP_CONNECTION_TEST`) |
| **R5 (fontes intocadas)** | `backup_service`, `backup_scheduler`, `external_backup_service`, `main.py`, `ad_*`, `email_*`, `onedoc_*`, `permission_service`: **zero linhas alteradas** — as status_fn apenas os importam/consultam |
| **R6 (isolamento)** | Cada status_fn encapsula sua derivação em try/except; exceção → `{"status": STATUS_COM_ERRO, "detail": {"summary": [("Erro", "Não foi possível verificar este componente")]}}` — o painel inteiro nunca quebra por um card (SC-007) |
| **R7 (testes AD/GLPI/1Doc)** | Comportamento da 032 preservado: AD mantém teste na tela própria (guarda vigente — `run_test(ad)` continua conduzindo); GLPI sem teste enquanto não configurada; 1Doc mantém verificação interna |
| **R8 (help/docs)** | Atualizar `help_article_032.py` (artigo da Central) + `docs/` (INVENTARIO/ARQUITETURA se aplicável) refletindo os 10 componentes — Princípio XI |

## Research & design decisions

Ver `research.md` (fatos R1–R8 consolidados com alternativas consideradas), `data-model.md` (derivação por componente), `contracts/ui-contract-central-saude.md` (contrato de UI) e `quickstart.md` (cenários de validação A–M).

## Complexity Tracking

> Nenhuma violação de Constitution — tabela vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|