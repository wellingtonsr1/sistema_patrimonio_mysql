# Specification Quality Checklist: 016-backup-manual-completo

**Purpose**: Validação da `spec.md` antes do planejamento.
**Created**: 2026-09-17
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] CHK001 — Análise obrigatória do briefing (§5/§6/§7/§32/§33) cumprida e documentada: banco (MariaDB/MySQL + PyMySQL), inicialização do banco, arquivos persistidos varridos, ambiente de execução
- [x] CHK002 — Situação de partida mapeada: feature 015 em produção; gap explícito (I1/I2/I3/T) vs. o que já está atendido (não reimplementar)
- [x] CHK003 — `data/patrimonio.db` investigado e classificado (resquício de desenvolvimento, não referenciado) — nada presumido
- [x] CHK004 — Inclusões/exclusões do backup formalizadas com classificação §7 e proibição de inventar arquivos respeitada (§8)

## Requirement Completeness

- [x] CHK005 — Proibições literais do §4 (25 itens) cobertas na Seção 8 "Não incluído"
- [x] CHK006 — Incrementos rastreáveis às seções do briefing: I1→§25, I2→§15/§16/§27, I3→§26, T→§34
- [x] CHK007 — Checklist §35 (27 itens) mapeado em AC-01..AC-27 com rastreabilidade
- [x] CHK008 — Testes obrigatórios A–J do §34 mapeados (T) com gaps identificados
- [x] CHK009 — Edge cases: gzip via stdlib (não assumir ferramenta externa §32), disco cheio, simultâneos, dump grande em streaming, compatibilidade `.sql` antigos

## Requirement Consistency

- [x] CHK010 — Sem contradição com a 015: incrementos aditivos; FR-008 preserva tudo que funciona; compatibilidade de transição `.sql`→`.sql.gz`
- [x] CHK011 — Sem conflito com a Constitution: zero DDL, RBAC existente, auditoria única, log técnico existente, sem mecanismos paralelos
- [x] CHK012 — Regra de mínima alteração (§36) explícita: R1 + impacto restrito (Seção 11)

## Requirement Quality

- [x] CHK013 — FRs binários e testáveis; prioridade §15 (válido + integridade + simplicidade + restaurabilidade) operacionalizada (gzip stdlib, SHA-256, .part→renomear)
- [x] CHK014 — User stories Given/When/Then com Independent Test; prioridades P1/P2 justificadas
- [x] CHK015 — Casos de erro (§19/§27) tabulados; proteção temporário→renomear como requisito (FR-001)

## Feature Readiness

- [x] CHK016 — Impacto (Seção 11) restrito a 5 arquivos confirmados; rota web explícitamente INTOCADA (servir arquivo é agnóstico a gzip)
- [x] CHK017 — Premissas verificadas (mysqldump presente; gzip stdlib; Linux/Uvicorn; sem privilégio de SO adicional §33)
- [x] CHK018 — Relatório final obrigatório (§39) previsto: lista de itens que o relatório de implementação deverá conter (incluso nas tasks/polish)
- [x] CHK019 — SC-005 define o gate de escopo por `git diff`
- [x] CHK020 — Sem [NEEDS CLARIFICATION]: decisões do briefing (compressão "avaliar" → sim, via stdlib; integridade "quando implementado" → SHA-256; menu "Backup"/"Backup e Restauração" → manter "Backups" existente, sem botão de restore)

## Notes

- A decisão de compressão (§15) foi "sim, via stdlib gzip" — não introduz dependência externa nem complexidade (streaming).
- A decisão de menu (§17) foi manter "Backups" (015) — o briefing admite "ou estrutura administrativa adequada já existente"; sem botão de restauração.
- Falha pré-existente RBAC lockout segue como baseline fora do escopo.
- Próximo passo: `/speckit-plan` (research confirmará detalhes do streaming gzip + compatibilidade).
