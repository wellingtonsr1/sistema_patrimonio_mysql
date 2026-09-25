# Specification Quality Checklist: Ajuste Responsivo da Tabela "Relatório Contábil-Físico do Patrimônio"

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-25
**Feature**: [specs/041-relatorio-contabil-larguras-colunas/spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
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
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Spec alinhada ao padrão validado das specs 036–040: mesma priorização de colunas (textuais no topo, compostas no meio, numéricas/datas/status compactas), mesma abordagem de responsividade (rolagem confinada ao contêiner da tabela, faixa de zoom 80%–200%) e mesmo critério de validação (suíte pytest verde + inspeção manual registrada em `validacao.md`).
- Lição da 039 incorporada como premissa: a fonte real do app (Plus Jakarta Sans) é mais larga que fontes de fallback — medições devem incluir folga (o título "Valor Aquisição" é o header mais largo entre as 10 colunas).
- Especificidades desta tabela registradas nos FRs: linha S/N condicional na Descrição, fallbacks "Estoque Geral"/"Livre"/"-", pill de Status, badge de Categoria, formato `-XX%` da Depreciação e alinhamento à direita consistente das 3 colunas monetárias.
- **Novidade da 041**: User Story 3 dedicada à preservação da impressão/exportação (C-6, seção 36 do pedido), com FR-013 exigindo neutralização em `@media print` de qualquer largura de tela introduzida — o bloco C1–C10 é compartilhado por 3 relatórios e não pode ser editado. SC-007 mede a igualdade da pré-visualização de impressão antes/depois.
- Larguras deliberadamente NÃO fixadas (decisão C-1, padrão 037–040): a implementação determina as larguras após análise, e a spec restringe apenas prioridade relativa e limites; `table-layout` é decisão da implementação (C-5).
- Nenhum marcador [NEEDS CLARIFICATION]: o pedido é autocontido (seções 1–38), com decisões C-1 a C-6 registradas na spec.
