# Specification Quality Checklist: Acessibilidade U3/U4 — Login e Inventário

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-12
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details in the requirements themselves (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded (§2.1 INCLUI × §2.2 NÃO INCLUI)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Evidência real (leitura somente-leitura, 2026-10-12, rev. 2)**: `research.md` confirma o que a
  análise de 2026-10-10 **não podia saber**: login/setup **já têm** `label[for]` correto
  (2/2 e 5/5); os gaps reais estão nos **fluxos de inventário** (labels soltos sem `for`
  em `new.html`/"Local/Observação" de conferir/detail/offline, controles de busca e filtros
  sem nome acessível, botões só-ícone sem `aria-label`, rádios sem `fieldset/legend`).
  **U4 já está parcialmente atendido**: `autofocus` existe no username do login e no campo
  de tombamento da conferência. Revisão rev. 2: base.html **já tem `<main>`**; botões
  "Filtrar"/"Localizar"/"Exportar" têm texto visível (não são só-ícone); os verdadeiros
  só-ícone são `togglePassword`, `bi-funnel` e o link limpar-filtros; `conferir.html` tem
  **alerta de erro sem `role="alert"`** (único dos fluxos-alvo); `.result-option` sem
  indicador de foco próprio é a única lacuna concreta de foco (nenhum `outline:none` no CSS
  da casa).
- **Divergência registrada da análise de origem**: "29 ocorrências de aria-*" é histórico;
  hoje são **33** (features 057/063/068 adicionaram atributos) e "0 em login.html" não
  considera o `role="alert"` já presente. Requisitos baseados na **recomendação**, não nos
  números (`research.md` R1).
- **axe-core delimitado**: a suíte atual roda **sem navegador**, então o critério
  automatizado desta feature é **estático** (parser HTML da stdlib, zero dependência nova):
  nomenclatura acessível de controles, `fieldset/legend`, `role=alert` nos erros. O
  "zero violações críticas/graves do axe" fica condicionado à varredura com browser —
  registrada no backlog (R5), não prometida aqui (evita critério inverificável).
- **Decisões pendentes do responsável (a fechar antes da implementação)**:
  - **P1** — técnica para controles compactos: `aria-label` direto *vs* label
    `visually-hidden` (recomendação: `aria-label`, preserva layout aprovado).
  - **P2** — skip-link em `base.html`: incluir agora (rev. 2 rebaixou o risco: `<main>`
    já existe; o skip-link é 1 `<a>` absoluto só no foco, nenhum template filho é tocado)
    ou postergar como spec futura (recomendação: **incluir**).
  - **P3** *(nova na rev. 2)* — indicador de foco dos `.result-option` (`style.css`, ~3
    linhas) (recomendação: incluir — única lacuna concreta de foco, U4).
  - **✅ APROVADAS em 2026-10-12**: **P1** (`aria-label`), **P2** (incluir skip-link) e
    **P3** (incluir indicador de foco) — conforme as recomendações da rev. 2 do `research.md`.
    Fase 5 liberada (T018–T027). Nenhum `[NEEDS CLARIFICATION]` remanescente.
- **Guardas de escopo**: I2/I4/I5 do `data-model.md` são verificáveis por `git diff`
  (`tests/route_manifest.json`, `requirements.txt`, `migrations/`, `app/models/` sem
  alteração; nenhum teste existente editado).
- **Origem**: item 8 (U3/U4) de `docs/ANALISE_SEG_PERF_UX_2026-10-10.md`.
