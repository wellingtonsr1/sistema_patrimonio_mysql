# Specification Quality Checklist: Correção do Deadlock da Restauração

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-18
**Feature**: [specs/019-import-deadlock/spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *menções a "processo web", "pipe", "pool" e "metadata lock" descrevem o incidente e as restrições do mecanismo EXISTENTE; o comportamento requerido (import sem auto-bloqueio, timeout em tempo finito, manutenção amigável) é agnóstico*
- [x] Focused on user value and business needs — *US1 = restauração conclui; US2 = falha detectável; US3 = manutenção segura*
- [x] Written for non-technical stakeholders — *cenários em operação observável (iniciar, concluir, acessar páginas, reiniciar)*
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — *a escolha da abordagem (subprocesso independente vs. drenar pool; DROP DATABASE vs. recriação por tabela) é deliberadamente postergada ao plan com critério explícito (privilégios reais confirmados no diagnóstico, FR-001/002)*
- [x] Requirements are testable and unambiguous — *FR-003 define a propriedade exigível (o import não disputa locks com quem o executa); FR-007 define cobertura completa do timeout; FR-010 define o comportamento de manutenção por página*
- [x] Success criteria are measurable — *SC-001 (conclui com sistema em uso), SC-002 (aborta no prazo com fake bloqueante), SC-003 (100% das páginas)*
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined — *3 stories × cenários + 8 edge cases (sessões, crash, restart, privilégios, concorrência, encoding)*
- [x] Scope is clearly bounded — *FR-014..FR-018 travam preservação e proibições*
- [x] Dependencies and assumptions identified — *incidente documentado (docs/AVISO_RESTORE_DEADLOCK.md) como fato; privilégios do banco a confirmar no plan; processo web único*

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria — *18 FRs mapeados às stories e SCs*
- [x] User scenarios cover primary flows — *sucesso com sistema em uso (P1), timeout/falha (P1), manutenção (P2)*
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Padrão da 018 exigido: diagnóstico conclusivo (FR-001) antes de qualquer alteração; proibido presumir causa ou inventar arquitetura nova (FR-002).
- O travamento de 2026-09-18 é fato documentado (evidências de processlist no aviso) — não reaberto.
- Crash-safety é requisito explícito: nenhum estado persistido pode deixar o sistema em manutenção permanente ou slot ocupado (FR-009/FR-011).

### Revisão pré-plan (2026-09-18) — correções aplicadas

| ID | Severidade | Correção |
|---|---|---|
| F1 | MEDIUM | FR-010: página de manutenção DEVE ser servida sem acesso ao banco (verificação em memória, antes da autenticação) — caso contrário ela própria falharia com o banco indisponível/pool drenado |
| F2 | MEDIUM | FR-007: separado prazo total de relógio (obrigatório, cobre o write bloqueante do incidente) de detecção de falta de progresso (reforço opcional) |
| F3 | LOW | US3 alinhada ao FR-013: estado (em andamento/concluída/falha), sem promessa de progresso percentual |
| F4 | LOW | Edge case novo: custo de espaço em disco ao materializar o .sql descomprimido, se a abordagem exigir |
| F5 | LOW | Assumptions atualizada com fato confirmado (SHOW GRANTS 2026-09-18): privilégios escopados ao banco — DROP/CREATE DATABASE inviável; reconstrução por tabela |
| F6 | typo | "durante o restauração" → "durante a restauração" |

Fatos novos confirmados nesta revisão: MariaDB **10.4.32** (XAMPP); `GRANT ALL PRIVILEGES ON sispatrimoniopro.*` (sem global).

### Verificação pós-plan (2026-09-18)

- [x] O plan responde exatamente as questões postergadas — abordagem anti-deadlock **escolhida e justificada** (R1/R5: fluxo 202 + worker + drenagem; alternativas rejeitadas com motivos) e reconstrução **por tabela** (D5: privilégios sem global)
- [x] Causa-raiz confirmada no código real: fluxo síncrono mantém a sessão do request checked-out durante o import (get_db L27–33; write_audit comita na sessão recebida, L186); timeout existente não cobre o write (D2) — diagnóstico D1–D5 em research.md

**Veredito final: PRONTO para `/speckit-tasks`.**
