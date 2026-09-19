# Implementation Plan: Auditoria da Precedência da Configuração de Backup Automático

**Branch**: `024-auditoria-config-backup` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/024-auditoria-config-backup/spec.md`

## Summary

Auditoria **exclusivamente de leitura** que verifica se a configuração de Backup Automático e Retenção administrada pela tela (tabela `backup_config`) é a única fonte de verdade em runtime, e se as 8 constantes de `app/config.py` (`BACKUP_AUTO_*`, `BACKUP_RETENTION_*`) atuam somente como bootstrap/fallback. A abordagem é **análise estática com evidência citável** (arquivo/linha): varredura exaustiva das ocorrências (classificação A–H), rastreio dos fluxos de decisão do scheduler e da retenção, reconstrução do fluxo tela → persistência → leitura efetiva, investigação de cache/snapshot e comparação precedência documentada × real. Entrega: **relatório de diagnóstico** (artefato desta feature, dentro de `specs/024-…/`) com as 7 perguntas-chave respondidas, os 14 critérios de conclusão marcados e os achados classificados (OK/ATENÇÃO/INCONSISTÊNCIA/RISCO/BLOQUEADOR). **Zero diff** em código, testes, banco, configuração e docs de produção.

## Technical Context

**Language/Version**: Python 3.10+ (leitura de código; nenhuma execução da aplicação)

**Primary Dependencies**: N/A para a entrega (não se instala nada); código auditado usa FastAPI + SQLAlchemy 2 + Pydantic v2 + Jinja2/Bootstrap 5 (stack fixado pela Constitution)

**Storage**: MariaDB/MySQL em produção (via `DATABASE_URL`); **nenhum acesso de escrita** nesta feature — a estrutura da tabela `backup_config` é documentada a partir de `app/models/backup_config.py`, sem executar migrations nem consultar banco

**Testing**: pytest (suíte existente NÃO é executada nem alterada — auditoria é estática; a suíte é apenas inventariada como evidência de cobertura)

**Target Platform**: Linux server (aplicação web FastAPI existente)

**Project Type**: web-service (análise sobre projeto existente; entrega = artefatos de spec + relatório)

**Performance Goals**: N/A (não há execução de aplicação; varredura de código é instantânea)

**Constraints**: zero diff fora de `specs/` (SC-001); nenhuma recomendação sem evidência arquivo/linha; nenhuma correção implementada; nenhuma variável declarada desnecessária sem considerar bootstrap/fallback/instalação nova/compatibilidade/testes

**Scale/Scope**: 8 constantes × todas as ocorrências no projeto; 5 user stories; 12 seções de relatório; 7 perguntas-chave; 14 critérios de conclusão

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência/Justificativa |
|---|---|---|
| I — Preservação do sistema e escopo | ✅ PASS | A feature É a preservação: somente leitura (spec FR-001/NFR-001); nenhuma refatoração/correção fora de escopo; achados registrados, não corrigidos |
| II — Camadas Web/API → Services → Models | ✅ PASS | Nenhuma alteração de arquitetura; a auditoria apenas mapeia as camadas existentes |
| III — Regras nos services | ✅ PASS | Nada implementado; verificação de que a regra de resolução de config vive em `backup_config_service.py` |
| IV — Integridade patrimonial | ✅ PASS | Fora de escopo (backup/config não toca movimentações) |
| V — Integridade do inventário | ✅ PASS | Fora de escopo |
| VI — Segurança (auth/RBAC/AD/credenciais) | ✅ PASS | Nenhuma credencial/segredo citado no relatório (valores de env descritos por função, não por conteúdo real de `.env`) |
| VII — MariaDB e proteção de dados | ✅ PASS | Nenhum acesso de escrita ao banco; nenhuma migration executada; estrutura da tabela lida do model |
| VIII — Testes como não regressão | ✅ PASS | Suíte não alterada (nem executada — análise estática); testes inventariados como evidência |
| IX — Auditoria | ✅ PASS | Nenhuma operação relevante executada |
| X — Interface consistente | ✅ PASS | Nenhuma alteração de UI |
| XI — Documentação fiel | ✅ PASS | Divergências doc × código são **registradas** no relatório (nada alterado nesta feature); eventual correção documental virará tarefa própria |
| XII — Especificação e validação | ✅ PASS | Fluxo Spec Kit seguido; validação = checklist de critérios de conclusão do relatório (quickstart) |

**Veredito inicial**: ✅ PASS (sem violações — a natureza somente-leitura da feature elimina conflitos).

**Re-check pós-Phase 1**: ✅ PASS — os artefatos gerados (`research.md`, `data-model.md`, `contracts/audit-report-contract.md`, `quickstart.md`) são exclusivamente documentais e não introduzem alteração de código, banco, rota, permissão ou UI. O contrato do relatório **reforça** as garantias da Constitution: zero diff (Princípio I), sem credenciais no relatório (Princípio VI), nenhum acesso de escrita a banco/migration (Princípio VII), suíte intocada (Princípio VIII), divergências documentais registradas — não corrigidas (Princípio XI), validação por checklist (Princípio XII). Nenhuma violação a registrar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/024-auditoria-config-backup/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── audit-report-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
# NENHUM diretório/arquivo de produção é criado ou alterado nesta feature.
# Os "artefatos" da entrega são os documentos desta pasta specs/024-…, incluindo:
specs/024-auditoria-config-backup/relatorio.md   # Relatório final de diagnóstico (US5) — criado em /speckit-implement

# Código existente SOMENTE LIDO pela auditoria (mapa preliminar verificado nesta fase):
app/
├── config.py                        # definição das 8 constantes (L63–87) + comentário de precedência (L63)
├── main.py                          # lifespan: start_scheduler/stop_scheduler (L38–41)
├── models/backup_config.py          # model BackupConfig (singleton id=1)
├── models/__init__.py               # export de BackupConfig (create_all)
├── services/backup_config_service.py # get_backup_config / get_effective_config / EffectiveBackupConfig / save_backup_config
├── services/backup_scheduler.py     # scheduler: import das 8 constantes (L31–39) usadas SÓ no fallback (L117–124); snapshot _current_effective; consumo via _eff()/eff.retention_* (L625–627)
├── services/backup_service.py       # dumps/restore (NÃO consome as 8 constantes — confirmar na auditoria)
├── web/admin_routes.py              # GET/POST /admin/backups/configuracoes; GET /admin/backups (config_form, create=False)
└── web/templates/admin/backups.html # modal #modalBackupConfig (apresentação da efetiva)
tests/
├── test_backup_config.py            # precedência, fallback, inválidos, create=False, anti-regressão do default
├── test_backup_automatico.py        # scheduler/agendamento
├── test_backup_retencao.py          # retenção GFS
└── test_backup_monitoramento.py     # monitoramento
README.md, docs/ARQUITETURA_E_MANUTENCAO.md, docs/GUIA_DE_MANUTENCAO.md   # precedência DOCUMENTADA (a conferir)
run.py                                                                    # entrypoint (inicialização) — a conferir
```

**Structure Decision**: Projeto único existente (`app/` + `tests/` na raiz), conforme features anteriores. A feature não cria estrutura de código: sua "estrutura" é a pasta de spec (`specs/024-auditoria-config-backup/`), que receberá o relatório de diagnóstico como artefato de entrega. Árvore de produção exibida acima apenas como mapa de leitura (sem modificação).

## Complexity Tracking

> Sem violações de Constitution — seção vazia (nada a justificar).

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
