# Specification Quality Checklist: 050-importacao-locais-nomenclatura

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-28
**Feature**: [spec.md](../spec.md) — Compatibilização da Importação Inteligente de Localizações com a Nova Nomenclatura (048 → 050)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — campos canônicos (`name`/`branch`/`department`) citados como contrato real do sistema (fatos verificados), não como decisão de implementação
- [x] Focused on user value and business needs — CSV oficial passa a importar; interface e mensagens refletem a terminologia oficial
- [x] Written for non-technical stakeholders — seções de contexto/problema legíveis; evidências técnicas isoladas em tabelas de fatos
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — 3 decisões registradas na seção Clarifications (aliases coexistem; sem mudança de schema; compatibilidade apenas com o que já era reconhecido)
- [x] Requirements are testable and unambiguous — FR-001..FR-025 com MUST/MAY e critérios verificáveis
- [x] Success criteria are measurable — SC-001..SC-007 (importação ponta a ponta, zero duplicidades, suíte verde, diff confinado, 0 migração)
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined — via FR-022 (12 cenários de teste do contrato) + edge cases herdados da 048 preservados
- [x] Edge cases are identified — Riscos e cuidados (§11) + FR-009 (colisões) + FR-008 (formas nunca reconhecidas)
- [x] Scope is clearly bounded — §12 lista explicitamente o que NÃO alterar; §10 arquivos intocáveis
- [x] Dependencies and assumptions identified — Assumptions (§13) + base da 048 documentada (§4)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows — US1 contrato oficial, US2 compatibilidade, US3 interface/mensagens, US4 semântica/dados, US5 preservação da 048
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Clarify (2026-09-28): +3 decisões integradas — export de locais incluído (FR-026/027, round-trip oficial), API intocada (campos name/branch/department nunca renomeados), varredura de legados restrita ao domínio de locais (FR-010a, inclui assertions de testes). Total: 6 decisões registradas em Clarifications.

- Fatos A1–A11 e o Problema 1 foram **verificados por execução real** do parser nesta sessão (o CSV oficial novo falha hoje: "Linha 2: filial é obrigatória") — a spec reflete o código real, não suposições.
- Matriz de compatibilidade (§6) preenchida com evidências de código, não com suposições (exigência §18 do pedido).
- Baseline da suíte a confirmar no implement (última confirmada nesta sessão: 728 na 038; SC-005 registra 789 a validar).
