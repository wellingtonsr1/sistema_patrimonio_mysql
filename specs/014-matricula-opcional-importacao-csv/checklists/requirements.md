# Specification Quality Checklist: 014-matricula-opcional-importacao-csv

**Purpose**: Validação da `spec.md` antes do planejamento. Cada item deve ser marcado ✅/❌ com evidência.

## Content Quality

- [x] CHK001 — Especifica a necessidade (por quê): inconsistência entre cadastro individual (feature 010) e importação CSV
- [x] CHK002 — Escopo mínimo claro: somente o importador CSV de colaboradores; lista explícita do que NÃO alterar
- [x] CHK003 — Termos objetivos: "ausente/vazia/espaços/coluna ausente" definidos operacionalmente; FR-002 define reutilização como proibição de segunda implementação
- [x] CHK004 — Exemplos concretos: importação mista com resultado esperado linha a linha; exemplo de CSV sem coluna
- [x] CHK005 — Estados/comportamentos de erro definidos: Seção 9 (tabela de casos de erro) + FR-004/FR-008

## Requirement Completeness

- [x] CHK006 — Todos os 8 cenários de teste do briefing mapeados (Seção 6, tabela final)
- [x] CHK007 — Regras de duplicidade/unicidade/transação preservadas explicitamente (FR-004, Edge Cases)
- [x] CHK008 — Preview/pré-validação coberto (US4, FR-007) — inclusive a proibição de fabricar número antecipado
- [x] CHK009 — Concorrência tratada conforme diretriz (reutilizar estratégia existente; vulnerabilidade → documentar, não corrigir — Edge Cases)
- [x] CHK010 — Critérios de aceitação verificáveis: AC-01..AC-11 com rastreabilidade bidirecional (FRs ↔ ACs ↔ USs ↔ Testes)

## Requirement Consistency

- [x] CHK011 — Sem contradição entre "opcional" e "informada é usada" (FR-001 vs FR-003 distinguem ausência de valor)
- [x] CHK012 — Sem conflito com a feature 010: a regra existente é reutilizada (caixa-preta), não modificada
- [x] CHK013 — "Não alterar" do briefing coberto por FR-010 + Seção 8 (Não incluído)

## Requirement Quality

- [x] CHK014 — FRs binários e testáveis (sem "adequado", "apropriado", "razoável")
- [x] CHK015 — Cada FR rastreável a AC/US/teste
- [x] CHK016 — Cenários no formato Given/When/Then

## Feature Readiness

- [x] CHK017 — Impacto esperado restrito a arquivos confirmados pela análise (Seção 11), sem nomes inventados
- [x] CHK018 — Procedimento de implementação respeitado: análise somente-leitura documentada na Seção 1 antes de qualquer alteração
- [x] CHK019 — Sucesso mensurável (Seção 7: SC-001..SC-006)
- [x] CHK020 — Documentação alvo identificada (tela de importação) com texto exigido pelo briefing

## Notes

- Análise somente-leitura completa documentada na Seção 1 da spec (11 pontos verificados com arquivo/linha).
- Causa raiz confirmada: obrigatoriedade em `_validate_row` + criação direta por modelo em `execute_custodian_import` (contorna o service da feature 010).
- Solução proposta: remover a obrigatoriedade e delegar a geração ao mecanismo único existente (`_next_provisional_code`), preservando todas as demais regras do importador.
- Falha pré-existente conhecida na suíte (RBAC lockout) — fora do escopo, baseline já registrado em features anteriores.
