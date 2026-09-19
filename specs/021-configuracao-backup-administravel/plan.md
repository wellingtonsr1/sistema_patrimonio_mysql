# Implementation Plan: Configuração Administrável do Backup Automático e Política de Retenção

**Branch**: `021-configuracao-backup-administravel` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-configuracao-backup-administravel/spec.md`

## Summary

As 8 configurações operacionais da feature 020 (ativado, frequência, horário, dia da semana, retenção diária/semanal/mensal, política de pré-restauração) vivem exclusivamente em `config.py` (env vars lidas uma vez no import): alterar o horário do backup exige acesso ao servidor **e** reinício. Este plano torna essas configurações administráveis pela interface reutilizando o **precedente existente** de configuração persistente do sistema (padrão `ADSettings`): **tabela nova aditiva `backup_config`** (registro único `id=1`, criada por `create_all` — zero `ALTER`, zero dado tocado), **resolução de "configuração efetiva" no serviço** (registro salvo governa; env/default como bootstrap e fallback — regra única de precedência, fonte única em runtime), **tela "Configurações de Backup" dentro da área de Backups existente** (`GET/POST /admin/backups/configuracoes`, RBAC `backup.gerenciar` reutilizado, validação no backend), **evento de auditoria dedicado** com before/after (`BACKUP_CONFIGURACAO_ALTERADA`) e **aplicação dinâmica sem reinício**: o scheduler passa a ler a configuração efetiva **por tick** (a descoberta técnica chave é que o loop da 020 já reavalia `enabled` e `_next_run_utc()` a cada tick de 30 s — o `hour, minute` capturado no start serve apenas ao log; basta trocar a leitura de constantes de módulo por leitura viva da configuração efetiva, com snapshot consistente por ciclo). Mecanismo de backup, retenção (lógica GFS), Restore 017/019, RBAC e auditoria existentes ficam intocados — apenas a **origem** dos valores muda.

## Technical Context

**Language/Version**: Python 3.10+ (runtime do projeto)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Pydantic v2 + Jinja2/Bootstrap 5 (stack existente — intocados; nenhuma dependência nova)

**Storage**: MariaDB/MySQL produção (via `DATABASE_URL`); **1 tabela NOVA** `backup_config` via `Base.metadata.create_all` (aditiva, idempotente, singleton `id=1`; zero DDL de alteração); suíte de testes em SQLite (padrão existente)

**Testing**: pytest (suíte existente 497 testes; relógio e fakes injetáveis — padrão 015–020; prova real em Windows/Linux é manual, quickstart)

**Target Platform**: Linux (produção atual) **e** Windows (XAMPP/MariaDB) — paridade herdada; nenhuma dependência de plataforma nova

**Project Type**: web-service (sistema existente, processo uvicorn único)

**Performance Goals**: N/A (leitura da configuração efetiva: 1 query por tick de 30 s no scheduler + por render da tela — caminhos frios; backup em si não é alterado)

**Constraints**: menor alteração possível (briefing §35/§40); fonte ÚNICA de verdade em runtime (§7); nenhuma credencial/caminho editável pela tela (§28/§29); `MYSQLDUMP_PATH`/`BACKUP_DIR`/`BACKUP_IMPORT_TIMEOUT`/`DATABASE_URL` intocados (§5/§29); defaults da 020 preservados (desativado — FR-009); scheduler nunca em estado indefinido (§16); snapshot consistente por ciclo (§27)

**Scale/Scope**: 1 model novo (`backup_config.py`) + 1 service novo pequeno e específico (`backup_config_service.py` — resolução de configuração efetiva, sem serviço genérico) + `backup_scheduler.py` (troca de leitura de constantes por configuração efetiva) + `admin_routes.py` (2 rotas novas na área existente) + `backups.html` (formulário aditivo seguindo padrão do formulário AD) + `audit_service.py` (+1 ação com rótulo) + `config.py` (default de `BACKUP_AUTO_ENABLED` alinhado e comentários) + testes + 3 docs. Zero alteração em: lógica GFS da retenção, Restore, RBAC (permissões), AD, autenticação, módulos patrimoniais.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente / evolução incremental | ✅ PASS | Tudo é extensão: tabela nova, rota nova na área existente, scheduler ajustado apenas na origem dos valores; nenhuma funcionalidade removida ou reescrita; defaults da 020 preservados |
| II | Arquitetura em camadas | ✅ PASS | Resolução de configuração efetiva e validações em services; rotas autenticam/autorizam e delegam; template só apresenta |
| III | Regras de negócio nos services | ✅ PASS | Validação de faixas, precedência e snapshot vivem em `backup_config_service.py` + validação existente do scheduler preservada |
| IV | Integridade patrimonial/movimentações | ✅ PASS (N/A) | Nenhum bem/custódia/localização/movimentação tocado |
| V | Integridade do inventário | ✅ PASS (N/A) | Nenhum fluxo de inventário tocado |
| VI | Segurança (auth, RBAC, AD, credenciais) | ✅ PASS | Rotas novas sob `require_permission("backup.gerenciar")` (existente — sem permissão nova; justificativa: mesma área, mesmo risco, spec A1); validação no backend (POST direto → 403); nenhum segredo/caminho/comando editável pela tela; evento de auditoria sem credenciais |
| VII | Banco MariaDB e proteção dos dados | ✅ PASS | Única alteração de schema é **tabela nova** `backup_config` via `create_all` — aditiva, idempotente, singleton; nenhum dado/coluna/tabela existente tocado |
| VIII | Testes como requisito de não regressão | ✅ PASS | Testes novos para as 18 situações do briefing §33 (A–R); suíte 497 existente deve permanecer verde — nada removido/enfraquecido; teste anti-regressão do default `BACKUP_AUTO_ENABLED=false` (FR-009) |
| IX | Auditoria das operações relevantes | ✅ PASS | +1 ação aditiva `BACKUP_CONFIGURACAO_ALTERADA` (constante + rótulo) gravada via `write_change_audit` existente com before/after — padrão do evento AD |
| X | Interface consistente | ✅ PASS | Formulário aditivo na tela `admin/backups.html` existente, seguindo o padrão visual do formulário "Integração AD" (cards/dl/inputs/mensagens success= / error=); nada removido; tema claro/escuro e responsividade herdados |
| XI | Documentação fiel | ✅ PASS | README (nova tela + precedência), ARQUITETURA_E_MANUTENCAO (service/model/rotas) e central de ajuda atualizados na mesma tarefa |
| XII | Especificação e validação | ✅ PASS | Fluxo Spec Kit seguido; validação = suíte pytest + Testes A–R + quickstart (incl. reinício real da aplicação) |

**Veredito pré-Phase 0: 12/12 PASS** — sem violações que exijam Complexity Tracking.

**Reavaliação pós-design (Phase 1): 12/12 PASS** — o design confirmou o gate: tabela nova aditiva única; service específico (não genérico) de configuração; precedência única documentada; scheduler lê snapshot por ciclo (sem segundo scheduler, sem hot reload genérico); permissão existente reutilizada com justificativa registrada; docs na mesma tarefa. Nenhuma complexidade adicional justificada.

## Project Structure

### Documentation (this feature)

```text
specs/021-configuracao-backup-administravel/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — decisões R1–R8 (armazenamento, precedência, aplicação dinâmica…)
├── data-model.md        # Phase 1 output — entidade BackupConfig + regra de configuração efetiva + validações
├── quickstart.md        # Phase 1 output — validação end-to-end (Testes A–R do briefing §33)
├── contracts/
│   └── service-contract.md  # Contratos: service de config, rotas, scheduler, auditoria, UI
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── config.py                        # default de BACKUP_AUTO_ENABLED explicitado ("false") + comentário
│                                    #   de precedência (banco → env → default); constantes PRESERVADAS
│                                    #   (bootstrap/fallback — nada removido, imports não quebram)
├── models/
│   ├── backup_config.py             # NOVO: BackupConfig (singleton id=1) — 8 campos operacionais
│   │                                #   + updated_at/updated_by (espelha ADSettings)
│   └── __init__.py                  # + import de BackupConfig (create_all cria a tabela)
├── services/
│   ├── backup_config_service.py     # NOVO: get_backup_config / get_effective_config (precedência única)
│   │                                #   + save_backup_config (validação de faixas + snapshot) — específico,
│   │                                #   não genérico (briefing §31)
│   ├── backup_scheduler.py          # troca a leitura de constantes importadas por get_effective_config()
│   │                                #   POR TICK (loop já reavalia enabled/next_run — descoberta técnica);
│   │                                #   _apply_retention lê limites do snapshot; regra de catch-up preservada
│   └── audit_service.py             # +1 ação aditiva: BACKUP_CONFIGURACAO_ALTERADA (+ rótulo)
└── web/
    ├── admin_routes.py              # +2 rotas na área Backups: GET /admin/backups/configuracoes (formulário)
    │                                #   e POST (valida → persiste → audita → redirect); RBAC backup.gerenciar
    └── templates/admin/backups.html # +formulário "Configurações de Backup" (padrão visual do form AD);
                                     #   card de monitoramento existente intacto

tests/
└── test_backup_config.py            # NOVO: Testes A–R do briefing §33 (precedência, validações, RBAC,
                                     #   auditoria, aplicação dinâmica, reinício)

README.md                            # §Backup: tela de configuração, precedência, aplicação sem reinício
docs/ARQUITETURA_E_MANUTENCAO.md     # backup_config_service, modelo backup_config, rotas, precedência
app/services/help_service.py         # artigo de backup: seção "Configurações de Backup" (comportamento real)
```

**Structure Decision**: projeto single-app FastAPI existente; alterações confinadas à configuração de backup (model/service novos, scheduler ajustado na origem dos valores, rotas+template da área existente, auditoria +1 evento) + testes + docs. Nenhum arquivo fora disso.

## Complexity Tracking

> Sem violações da Constitution — seção não aplicável.
