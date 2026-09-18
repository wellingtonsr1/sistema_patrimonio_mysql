# Specification Quality Checklist: 015-backup-manual

**Purpose**: Validação da `spec.md` antes do planejamento.
**Created**: 2026-09-17
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] CHK001 — Escopo claro e delimitado: somente mecanismo de backup manual (gerar → validar → armazenar → auditar → listar → baixar)
- [x] CHK002 — Restrições do briefing respeitadas: preservar integralmente o sistema (FR-009/AC-10); restauração e agendamento fora do escopo
- [x] CHK003 — Todos os 8 objetivos do briefing mapeados em FRs/ACs (iniciar, gerar válido, armazenar, identificar por data/hora, listar, informações básicas, baixar, auditar)
- [x] CHK004 — Análise somente-leitura documentada na Seção 1 com fatos verificados no código (sem mecanismo existente; precedentes citados)

## Requirement Completeness

- [x] CHK005 — Sem [NEEDS CLARIFICATION]: decisões de design (formato do dump, tabela vs arquivos) delegadas ao plan como "confirmação técnica", sem ambiguidade de requisito
- [x] CHK006 — Requisitos testáveis e binários (DEVE/é PROIBIDO), sem termos vagos ("adequado", "apropriado" qualificados operacionalmente — ex.: FR-003 define "repositório dedicado no diretório de dados")
- [x] CHK007 — Success criteria mensuráveis (SC-001..SC-006: contagens, integridade, 100% dos eventos)
- [x] CHK008 — Edge cases definidos: disco cheio, gerações em sequência, artefatos alheios, 404, sem autenticação, limites do mecanismo
- [x] CHK009 — Escopo negativo explícito (Seção 8 "Não incluído"): agendamento, restauração, retenção, nuvem, logs

## Requirement Consistency

- [x] CHK010 — Coerência interna: FRs ↔ ACs ↔ USs ↔ cenários ↔ SCs com rastreabilidade bidirecional (Seção 6)
- [x] CHK011 — Sem conflito com a Constitution: nova permissão deny-by-default (VI), auditoria via write_audit (IX), regras em service (II/III), UI consistente (X), docs fiéis (XI)
- [x] CHK012 — "Preservar integralmente o funcionamento atual" expresso como FR-009/AC-10 e SC-005 (suíte como gate)

## Requirement Quality

- [x] CHK013 — User stories no formato Given/When/Then com Independent Test por story
- [x] CHK014 — Prioridades atribuídas (P1 geração+listagem, P2 download+segurança) com justificativa de MVP
- [x] CHK015 — Casos de erro tabulados (Seção 9) com comportamento definido para cada situação

## Feature Readiness

- [x] CHK016 — Impacto esperado (Seção 11) restrito a componentes confirmados pela análise (novo service, novas rotas web, permissão nova, data/, docs, testes) — nada inventado
- [x] CHK017 — Premissas registradas (Seção 10): concessão da permissão ao perfil admin, repositório em data/, dump pelo utilitário do próprio banco
- [x] CHK018 — "Estado atual do sistema" definido operacionalmente (dump consistente do banco; empacotamento adicional decidido no plan, spec não obriga)
- [x] CHK019 — Próximo passo claro: /speckit-plan (research confirmará viabilidade do dump e da listagem por arquivos)
- [x] CHK020 — Nenhum vazamento de implementação (linguagem/framework) nos requisitos; menções técnicas apenas na análise (Seção 1) e premissas

## Notes

- Spec pronta para `/speckit-plan`. Pontos técnicos a confirmar no plan (já sinalizados): utilitário de dump do MariaDB/MySQL acionável pela aplicação; listagem derivada do repositório de arquivos (sem tabela nova); precisão do timestamp no nome do arquivo.
- Falha pré-existente da suíte (`test_rbac.py` lockout) permanece registrada como baseline de outras features — fora do escopo desta.
