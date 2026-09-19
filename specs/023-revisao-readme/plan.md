# Implementation Plan: Revisão e Melhoria do README.md — SisPatrimônio Pro

**Branch**: `023-revisao-readme` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/023-revisao-readme/spec.md`

## Summary

O README atual já passou por revisão recente e está, em geral, fiel — a auditoria documental (research.md, inventário D1–D15) confirmou que a maioria das seções bate com o código (CLI, AD, RBAC, auditoria, banco, segurança, data/hora da feature 004). As divergências reais são pontuais: (1) a seção "Documentação" lista uma estrutura `docs/` **sugerida que não existe** (D1); (2) o catálogo de permissões omite `backup.gerenciar`/`backup.restaurar` (D6); (3) o acesso às configurações de backup não reflete a feature 022 (⚙/modal — D4); (4) a árvore de estrutura omite diretórios reais (`specs/`, `data/`, `docs/` já citados — D10); (5) precisão menor em "bens não previstos" do inventário (D9) e nas condições do `/setup` (D2). O plano aplica essas correções **somente em `README.md`**, preservando o conteúdo verificado, e produz o relatório de validação do briefing §41. **Nenhum código é alterado** — a feature é documental (spec FR-001/FR-004).

## Technical Context

**Language/Version**: Português técnico (Markdown); o projeto alvo é Python 3.10+ (apenas objeto da documentação)

**Primary Dependencies**: Nenhuma nova — documento estático; referências a `docs/` e `specs/` existentes

**Storage**: N/A (nenhum dado persistido)

**Testing**: Verificação documental estática (conferência comando a comando com `app/cli.py`, `app/config.py`, `app/main.py`, `app/web/routes.py`, `app/api/reports_api.py`, `requirements.txt`, estrutura real do repositório); suíte pytest do sistema só para confirmar informação documentada (não será modificada)

**Target Platform**: N/A (arquivo de documentação)

**Project Type**: documentação (web-service existente como objeto)

**Performance Goals**: N/A

**Constraints**: escopo-fonte = 1 arquivo (`README.md`); nenhuma informação não confirmável é documentada como fato; nenhum segredo/valor real de `.env`; sem números fixos de testes; referências externas somente para caminhos existentes; preservar o conteúdo já correto (briefing §2–§4, §28, §32, §38)

**Scale/Scope**: 1 arquivo editado (`README.md`, ~929 linhas na base); 15 divergências inventariadas (D1–D15) aplicáveis a ~10 seções; 0 alterações de código

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente / evolução incremental | ✅ PASS | Feature exclusivamente documental: nenhum módulo, comportamento ou arquivo de código tocado; README corrigido com base no sistema real (briefing §38/§42) |
| II | Arquitetura em camadas | ✅ PASS (N/A) | Nenhum código alterado; a arquitetura descrita no README continua representando a existente |
| III | Regras de negócio nos services | ✅ PASS (N/A) | Idem — nada movido ou duplicado |
| IV | Integridade patrimonial/movimentações | ✅ PASS | README descreve os 8 tipos reais do motor de movimentações; nada contraria o mecanismo |
| V | Integridade do inventário | ✅ PASS | Regra fundamental "inventário não altera cadastro" reforçada (FR-007; research D9) |
| VI | Segurança (auth, RBAC, AD, credenciais) | ✅ PASS | Regras AD autentica-mas-não-autoriza e RBAC deny-by-default conferidas; nenhum segredo no README (exemplos com placeholders — FR-009/FR-015/SC-006) |
| VII | Banco MariaDB e proteção dos dados | ✅ PASS | Nenhum DDL; README continua explicitando MariaDB/MySQL como produção e SQLite apenas em testes |
| VIII | Testes como requisito de não regressão | ✅ PASS | Suíte não é tocada; seção de testes sem números fixos (FR-019); suíte executada apenas para confirmação, se necessário |
| IX | Auditoria das operações relevantes | ✅ PASS (N/A) | Nenhuma operação nova; descrição da trilha conferida (FR-011) |
| X | Interface consistente | ✅ PASS (N/A) | Nenhuma UI alterada |
| XI | Documentação fiel ao comportamento real | ✅ PASS (é o objeto) | Princípio central da feature: toda afirmação verificável no código (FR-002/FR-003); referências só para caminhos existentes (FR-023) |
| XII | Especificação e validação | ✅ PASS | Fluxo Spec Kit seguido; validação = checklist §39 + relatório §41 (US3) |

**Veredito pré-Phase 0: 12/12 PASS** — reconfirmado após Phase 1 (design não introduz violação: artefatos da feature vivem em `specs/023-revisao-readme/`, fora do código).

## Project Structure

### Documentation (this feature)

```text
specs/023-revisao-readme/
├── plan.md              # This file (/speckit-plan command output)
├── spec.md              # Especificação (US1 auditoria · US2 reescrita · US3 validação)
├── checklists/
│   └── requirements.md  # Checklist de qualidade da spec (14/14)
├── research.md          # Phase 0 — inventário de divergências D1–D15 + decisões R1–R5
├── data-model.md        # Phase 1 — N/A de dados; inventário de fatos documentáveis
├── contracts/
│   └── readme-contract.md  # Contrato de conteúdo: seção → fatos verificáveis → fonte no código
├── quickstart.md        # Phase 1 — procedimento de validação documental (§39/§41)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
README.md   # ÚNICO arquivo alterado por esta feature (spec FR-001/NFR-002)
```

**Não alterados** (verificação explícita do briefing §3/§38): todo `app/` (models, schemas, services, api, web, config, database, main, cli), `tests/`, `requirements.txt`, `run.py`, `seed_demo.py`, `.env.example`, `docs/` (nenhum arquivo criado aqui), banco e configuração.

**Structure Decision**: feature de documentação em repositório único — nenhum código novo; o objeto da mudança é `README.md` na raiz, e os artefatos de planejamento vivem em `specs/023-revisao-readme/`.

## Complexity Tracking

*Nenhuma violação constitucional — tabela vazia.*
