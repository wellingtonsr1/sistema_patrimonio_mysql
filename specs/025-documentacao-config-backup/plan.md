# Implementation Plan: Correção da Documentação da Configuração de Backup

**Branch**: `025-documentacao-config-backup` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/025-documentacao-config-backup/spec.md`

## Summary

Feature **exclusivamente documental** que alinha a documentação ao comportamento real confirmado pela auditoria 024 (relatório **OK**, achados AT-1/AT-2/AT-3): (AT-1) as env `BACKUP_*` deixam de ser descritas como fallback "da primeira inicialização" e passam a ser descritas como **fallback por campo, dinâmico**, + bootstrap/fallback de boot; (AT-2) o **fallback de boot** do scheduler entra na precedência documentada (falha → mantém snapshot anterior → sem snapshot → bootstrap env/default); (AT-3) documenta a particularidade do `auto_enabled` não-nullable (env não reconsultada dinamicamente após a linha existir). Consolidam-se nas docs: precedência persistido → env → default via `get_effective_config()`, scheduler/retenção como consumidores da efetiva, sem dupla fonte, atualização sem reinício (≤ 30 s), primeiro uso. **Edições restritas a** `README.md`, `docs/GUIA_DE_MANUTENCAO.md`, `docs/ARQUITETURA_E_MANUTENCAO.md` — somente onde incompleto/incorreto; texto já correto é preservado. **Zero diff** em código, testes, banco, configuração ou interface.

## Technical Context

**Language/Version**: Português técnico — Markdown (edição de documentação existente); código verificado (não alterado): Python 3.10+ (FastAPI/SQLAlchemy 2)

**Primary Dependencies**: N/A (nenhuma dependência nova); artefatos-alvo são arquivos Markdown já versionados

**Storage**: N/A — nenhum acesso a banco; a tabela `backup_config` é apenas **citada** na documentação

**Testing**: Nenhum teste novo; suíte NÃO executada nem alterada; validação = checklist documental (quickstart) + `git diff`

**Target Platform**: Documentação do repositório (lida por mantenedores/operadores; README também no GitHub)

**Project Type**: web-service existente — feature apenas documental

**Performance Goals**: N/A (texto estático)

**Constraints**: diff somente nos 3 arquivos do FR-002 (SC-001); nenhuma frase "fallback da primeira inicialização" remanescente; nenhuma afirmação de fonte concorrente; nenhuma credencial citada; re-verificação obrigatória do código antes de editar (FR-015)

**Scale/Scope**: 3 correções (AT-1/AT-2/AT-3) + consolidação do fluxo; ~6–10 inserções pontuais em 3 arquivos; 1 relatório final (13 itens do briefing §39)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência/Justificativa |
|---|---|---|
| I — Preservação e escopo | ✅ PASS | Altera somente docs dos arquivos do FR-002; nenhuma refatoração; correção fundamentada nos achados AT-1/2/3 |
| II — Camadas | ✅ PASS | Nenhuma alteração de arquitetura; docs apenas descrevem as camadas existentes |
| III — Regras nos services | ✅ PASS | Nada implementado; docs apontam `get_effective_config()` no service como resolvedor |
| IV/V — Patrimônio/Inventário | ✅ PASS | Fora de escopo (nada tocado) |
| VI — Segurança/credenciais | ✅ PASS | Nenhuma `BACKUP_*` tratada como segredo; nenhuma credencial adicionada (FR-014) |
| VII — MariaDB/dados | ✅ PASS | Nenhum acesso a banco; nenhuma migration; `backup_config` só citada |
| VIII — Testes | ✅ PASS | Suíte intocada (não executada — feature documental); briefing §27 |
| IX — Auditoria | ✅ PASS | Nenhuma operação relevante executada |
| X — Interface | ✅ PASS | Nenhuma alteração de UI/rotas/perm |
| XI — Documentação fiel | ✅ PASS | É o objetivo central da feature: docs passam a refletir o comportamento real (código = fonte de verdade) |
| XII — Spec + validação | ✅ PASS | Fluxo Spec Kit; validação = quickstart + relatório final (briefing §39) |

**Veredito inicial**: ✅ PASS (sem violações — a natureza documental e as restrições do briefing eliminam conflitos).

**Re-check pós-Phase 1**: ✅ PASS — os artefatos gerados (`research.md`, `data-model.md`, `contracts/doc-edit-contract.md`, `quickstart.md`) são documentais e não alteram produção. O contrato fixa **4 edições fechadas** (E1–E4) com invariantes de preservação e lista de proibições — reforça os Princípios I (escopo mínimo), VI (sem credenciais) e XI (docs fiéis ao código); nenhum conflito novo; Complexity Tracking permanece vazio.

## Project Structure

### Documentation (this feature)

```text
specs/025-documentacao-config-backup/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── doc-edit-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
# ARQUIVOS A EDITAR (únicos da feature — todos já existem):
README.md                          # precedência + fallback de boot (AT-2) + particularidade auto_enabled (AT-3) + cláusulas de consolidação
docs/GUIA_DE_MANUTENCAO.md         # AT-1: reescrever a frase "fallback da primeira inicialização" (~L111–113)
docs/ARQUITETURA_E_MANUTENCAO.md   # cláusula do fallback de boot no registro do fluxo de config (~L1215)

# APENAS LIDOS/VERIFICADOS (NUNCA alterados nesta feature):
app/config.py                      # constantes + defaults (fonte dos valores documentados) — comentário interno permanece
app/services/backup_config_service.py  # get_effective_config / precedência por campo / _DEFAULT_*
app/services/backup_scheduler.py   # _TICK_SECONDS=30 / refresh por tick / fallback de boot / _apply_retention
app/models/backup_config.py        # auto_enabled não-nullable
app/web/admin_routes.py            # rotas GET/POST (citadas na doc, sem alteração)
tests/test_backup_*.py             # suíte intocada (briefing §27)
specs/024-auditoria-config-backup/relatorio.md  # referência dos achados AT-1/2/3

# ENTREGA ADICIONAL (criada na implementação):
specs/025-documentacao-config-backup/relatorio.md   # relatório final (briefing §39) — artefato da feature
```

**Structure Decision**: Projeto único existente; a feature altera apenas 3 arquivos Markdown de documentação e cria seu relatório em `specs/025-…/`. Nenhuma estrutura nova em produção.

## Complexity Tracking

> Sem violações de Constitution — seção vazia (nada a justificar).

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
