# Implementation Plan: Correção da Atualização Imediata do Status do Backup Automático

**Branch**: `026-correcao-status-backup` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/026-correcao-status-backup/spec.md`

## Summary

O indicador "Agendamento" da página Administração → Backups mostra estado antigo após salvar a configuração do backup automático: ele é alimentado por `auto_status.enabled`, que vem de `scheduler_status()` (`admin_routes.py:832/896`) → **snapshot interno do scheduler** (`_eff()`, renovado só no start e a cada tick de 30 s), enquanto o checkbox do modal usa `config_form = get_effective_config(db, create=False)` — leitura fresca do banco por request (`:840/894`). A feature troca a **fonte do estado exibido** no card "Backup Automático" para a configuração efetiva obtida por request (a mesma do formulário), nos **2 GETs que renderizam o template** (`admin_backups` e `admin_backup_config_form`), deixando os dados de execução (running/próximo disparo/último resultado) no mecanismo existente do scheduler. Fluxo de salvamento, scheduler, service, model, banco, auditoria e RBAC intocados. Novos testes do fluxo real (POST→redirect→GET) reproduzem o problema no código antigo e travam a correção.

## Technical Context

**Language/Version**: Python 3.10+ (FastAPI + Jinja2 + SQLAlchemy 2); Jinja2 template `admin/backups.html`

**Primary Dependencies**: Stack existente (Constitution) — nenhuma dependência nova

**Storage**: MariaDB/MySQL via SQLAlchemy (nenhum acesso de escrita além do fluxo existente de salvamento; nenhuma migration)

**Testing**: pytest + TestClient (padrão do projeto); novos testes em `tests/test_backup_config.py` (fluxo real POST→redirect→GET)

**Target Platform**: Linux server (aplicação web existente)

**Project Type**: web-service (feature de correção localizada de apresentação)

**Performance Goals**: N/A (nenhum caminho novo de performance; leitura de efetiva já feita por request hoje para o `config_form`)

**Constraints**: mínimo invasivo — alteração limitada a `admin_routes.py` (2 contextos) + `backups.html` (badge) + testes; PROIBIDO reload JS, segunda fonte, alteração em `backup_scheduler.py`/`backup_service.py`/`backup_config_service.py`/model/banco (SC-004); indicador e checkbox da mesma fonte; dados de execução continuam do scheduler

**Scale/Scope**: 2 contextos de rota, 1 trecho de template, ~3–5 testes novos; scheduler/service/model/banco com zero diff

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência/Justificativa |
|---|---|---|
| I — Preservação e escopo | ✅ PASS | Correção localizada (2 rotas + badge + testes); scheduler/service/model/banco intocados; nenhum comportamento além do previsto na spec |
| II — Camadas | ✅ PASS | Rota continua delegando ao service (`get_effective_config`); nenhuma regra de negócio nova na rota (apenas a fonte de leitura para exibição) |
| III — Regras nos services | ✅ PASS | Nenhuma regra nova criada; reutiliza `get_effective_config()` — sem função paralela (briefing §16) |
| IV/V — Patrimônio/Inventário | ✅ PASS | Fora de escopo |
| VI — Segurança/RBAC/credenciais | ✅ PASS | Guards existentes preservados; `scheduler_status()` continua sem segredos; nada novo exposto |
| VII — MariaDB/dados | ✅ PASS | Nenhuma migration/escrita nova; leitura por request da efetiva (padrão 022) |
| VIII — Testes como não regressão | ✅ PASS | Novos testes do fluxo real + suíte existente verde; nenhum teste enfraquecido |
| IX — Auditoria | ✅ PASS | Evento `BACKUP_CONFIGURACAO_ALTERADA` existente intocado |
| X — Interface consistente | ✅ PASS | Badge/estrutura do card preservados — muda apenas a fonte do valor; sem JS/CSS novo; fluxo server-rendered mantido |
| XI — Documentação fiel | ✅ PASS | Documentação atual (025) descreve a efetiva como fonte da tela; a correção APROXIMA o código da doc — nenhum doc precisará mudar |
| XII — Spec + validação | ✅ PASS | Fluxo Spec Kit; validação = novos testes + suíte + relatório final (briefing §45) |

**Veredito inicial**: ✅ PASS (sem violações — correção de apresentação com escopo fechado).

**Re-check pós-Phase 1**: ✅ PASS — os artefatos (`research.md`, `data-model.md`, `contracts/status-source-contract.md`, `quickstart.md`) confirmam o desenho mínimo: correção predominante no template (fonte do badge/frequência/horário → efetiva por request), nenhuma alteração em services/model/banco, nenhuma segunda fonte, sem reload; validação inclui reprodução da causa antes de corrigir (briefing §45.1). Nenhuma violação a registrar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/026-correcao-status-backup/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── status-source-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
# ARQUIVOS A ALTERAR (esperado — confirmar na implementação):
app/web/admin_routes.py               # admin_backups (:804–846) e admin_backup_config_form (:886–905):
                                      #   contexto do card passa a incluir config da efetiva por request
app/web/templates/admin/backups.html  # card "Backup Automático" (:93–101): badge/schedule/time
                                      #   a partir da efetiva; running/next/last continuam de auto_status
tests/test_backup_config.py           # novos testes do fluxo real (POST→redirect→GET + variações)

# INTOCADOS (SC-004 — qualquer diff aqui exige justificativa no relatório):
app/services/backup_scheduler.py      # _TICK_SECONDS=30, refresh por tick, _eff(), scheduler_status()
app/services/backup_config_service.py # get_effective_config / precedência / defaults
app/services/backup_service.py        # dump/restore
app/models/backup_config.py           # modelo/tabela
tests/test_backup_automatico.py, test_backup_retencao.py, test_backup_monitoramento.py  # intocados

# APENAS LIDOS (referências):
app/config.py                         # defaults/precedência (intocado)
specs/024-auditoria-config-backup/relatorio.md  # arquitetura confirmada
specs/025-documentacao-config-backup/relatorio.md  # docs fiéis (nenhuma mudança documental prevista)
```

**Structure Decision**: Projeto único existente; correção em 2 contextos de rota + 1 trecho de template + testes. Nenhum arquivo novo; nenhuma estrutura nova.

## Complexity Tracking

> Sem violações de Constitution — seção vazia (nada a justificar).

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
