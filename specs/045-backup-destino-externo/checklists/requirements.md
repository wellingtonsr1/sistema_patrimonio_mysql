# Specification Quality Checklist: Destino Externo para Backups (Pasta de Rede/NAS)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-26
**Feature**: [specs/045-backup-destino-externo/spec.md](../spec.md)

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

- Feature **funcional** (primeira fora do eixo visual 036–044): o pedido (44 seções) é autocontido e prescritivo — decisões **C-1 a C-18** registradas na spec; nenhum [NEEDS CLARIFICATION].
- **Regra máxima do pedido (C-1/C-18)**: extensão, não novo mecanismo — tipo continua MANUAL|AUTOMATICO (+PRE_RESTAURACAO), nova dimensão DESTINO LOCAL|EXTERNO; proibido novo scheduler, novo sistema de retenção/auditoria, segundo dump ou refatoração; sempre a alteração pequena e localizada.
- **Fatos do repositório levantados antes da spec**: serviço único com SHA-256 no streaming e guarda de restore; `BackupRecord` com vocabulário controlado e campos preenchidos exclusivamente pela retenção; scheduler com lock único + catch-up; `BackupConfig` singleton com resolução persistido→env→default e docstring proibindo segredos; rotas `backup.gerenciar`/`backup.restaurar`; eventos de auditoria literais PT; tela única estendível; schema aditivo via create_all (sem Alembic).
- **Decisões delegadas ao plan com restrição explícita**: armazenamento da configuração (FR-005), política de cópia do PRE_RESTAURACAO (C-11), retenção externa (C-12), retry (C-16) — **resolvidas nas clarificações de 2026-09-26**: tabela nova aditiva zero-ALTER para config e resultados externos; PRE_RESTAURACAO é copiado; retenção externa não implementada (cópias acumulam); retry imediato limitado no ciclo.
- **Testes automatizados obrigatórios** (C-17): cenários A–L do pedido como FR-021/SC-001..006 — difere do padrão visual da família (onde seções 28/29 diziam "sem testes novos"); aqui as seções 36/37 EXIGEM testes.
- Segurança de segredos (C-4/C-14/SC-007): pasta montada preferida; zero senha/token em logs, auditoria, argv ou nomes de arquivo.
- Restauração externa (C-10), provedores múltiplos (C-3) e credenciais gerenciadas (C-4) explicitamente fora de escopo.
