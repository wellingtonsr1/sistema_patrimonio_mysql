# Implementation Plan: Correção do Ciclo de Backup, Restauração e Agendamento Automático

**Branch**: `028-correcao-ciclo-backup` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/028-correcao-ciclo-backup/spec.md`

## Summary

Três correções cirúrgicas sobre o ciclo backup/restauração/agendamento (features 015–022), sem refatoração: **A** — reconciliação pós-import que devolve aos arquivos presentes no disco o tipo registrado capturado antes da substituição do banco (a causa é a substituição do conteúdo do banco pelo dump, que não contém registros posteriores ao snapshot); **B** — troca da condição impossível de disparo (`_clock() >= _next_run_utc(_clock())`, onde a função devolve sempre ocorrência estritamente futura) pela semântica de **execução devida** já usada pelo catch-up (`_should_catch_up`); **C** — isenção **somente-leitura e específica** da tela `/admin/backups` na whitelist de manutenção, reutilizando o mecanismo existente de consulta do estado da restauração.

## Technical Context

**Language/Version**: Python 3.10+ (stack da Constitution)

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2, Jinja2 + Bootstrap 5 — todos existentes, nenhuma dependência nova.

**Storage**: MariaDB/MySQL via `DATABASE_URL` (produção); SQLite apenas na suíte de testes (padrão do projeto).

**Testing**: pytest + TestClient (padrão do projeto).

**Target Platform**: Windows e Linux (deploy de processo único — premissa em vigor).

**Performance Goals**: N/A (correções de comportamento; nenhuma rota nova de negócio).

**Constraints**:
- **Baseline pré-028 medida nesta sessão: 543 passed / 1 failed** (`test_anti_regressao_default_desativado_no_codigo_real` — anti-regressão pré-existente, defasado; NÃO é desta feature).
- Patamar pós-028 = 543 + novos verdes, mesma 1 falha pré-existente (não enfraquecida — Princípio VIII).
- Ação do operador obrigatória: **restart do servidor** para o disparo do scheduler corrigido valer em produção.
- A reconciliação da US1 roda **dentro do ciclo de restauração existente** (worker thread), antes da liberação da manutenção — zero exposição a concorrência de requests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| 1 | I — Preservação do sistema existente | ✓ PASS | 3 correções pontuais em fluxos existentes (backup_service/scheduler/middleware); zero refatoração; problemas fora do escopo registrados no backlog (nota no research R7) |
| 2 | II — Arquitetura em camadas | ✓ PASS | Reconciliação e disparo ficam nos services; rota só ajusta contexto de template |
| 3 | III — Regras nos services | ✓ PASS | Regra de reconciliação = service; middleware só isenta caminho |
| 4 | IV — Integridade patrimonial | ✓ PASS | Nenhuma alteração em movimentações/bens |
| 5 | V — Integridade do inventário | ✓ PASS | Não toca inventário |
| 6 | VI — Segurança/RBAC/AD | ✓ PASS | Isenção de manutenção é somente-leitura, mantém auth (`require_web_auth` no router) e permissão (`backup.gerenciar`); zero credenciais em logs/auditoria |
| 7 | VII — Banco MariaDB/aditivo | ✓ PASS | Zero DDL; reconciliação regrava campos existentes de registros existentes (UPDATE) |
| 8 | VIII — Testes de não regressão | ✓ PASS | TDD por story; baseline 543/1 preservada + novos testes |
| 9 | IX — Auditoria | ✓ BACKLOG | Nenhum novo evento proposto; sugestão de evento `BACKUP_REGISTROS_RECONCILIADOS` registrada como **backlog** (fora do escopo aprovado) |
| 9 | IX — Auditoria (dentro do escopo) | ✓ PASS | Eventos existentes intactos; nenhum segredo |
| 9 | IX — Auditoria (item 27.12 do briefing original) | ✓ PASS | Antes/depois contabilizado no relatório final via git + Validation Results |
| 10 | X — Interface consistente | ✓ PASS | Tela e fluxo atuais mantidos; isenção reutiliza tela existente |
| 11 | XI — Documentação fiel | ✓ PASS | README + ARQUITETURA atualizados na mesma tarefa |
| 12 | XII — Spec-driven + validação | ✓ PASS | Fluxo Spec Kit seguido; validação via quickstart |

### Post-Design Re-check (após Phase 1)

| # | Princípio | Status | Evidência |
|---|---|---|---|
| 1–12 | Revalidação integral | ✓ PASS 12/12 | Sem DDL (data-model N/A documentado), sem nova dependência, escopo de arquivos fechado (Structure), quickstart com cenários das 3 stories; única dependência de ação humana: restart do servidor após deploy (registrar no relatório final). Nota: a reconciliação (US1) será auditada por diferença — sem novo evento; backlog registrado em R7. |

## Project Structure

### Documentation (this feature)

```text
specs/028-correcao-ciclo-backup/
├── plan.md              # This file
├── research.md          # Phase 0 output — diagnóstico D1–D8 + decisões R1–R8
├── data-model.md        # Phase 1 output — N/A documentado (zero DDL)
├── contracts/           # Phase 1 output — contrato por caminho afetado
│   └── service-contract.md   # service + scheduler + middleware + rota/template
└── quickstart.md        # Phase 1 output — validação ponta a ponta (suíte + manual)
```

### Source Code (repository root)

```text
app/
├── services/
│   ├── backup_service.py          # A: reconciliação pós-import no worker; C: nada
│   └── backup_scheduler.py        # B: condição de disparo (execução devida); TYPE_CHECKING
├── web/
│   ├── admin_routes.py            # C: contexto degradado quando em manutenção (mesma rota GET)
│   └── templates/admin/backups.html  # C: estado vazio quando dados indisponíveis
├── main.py                        # C: whitelist += /admin/backups (GET only, comentário)
tests/
├── test_backup_restore.py         # A (extensões)
├── test_backup_automatico.py      # B (extensões)
└── test_backup_manual.py          # C (extensões)
docs/                              # README.md + ARQUITETURA_E_MANUTENCAO.md (seção 028)
```

**Structure Decision**: projeto único existente (FastAPI). Nenhum arquivo novo de produção além de nenhum (não há novo módulo) — todas as alterações são em arquivos existentes do domínio backup.

## Complexity Tracking

> Vazio — nenhuma violação da Constitution a justificar.
