# Quickstart: Validação da Auditoria da Precedência da Configuração de Backup

**Feature**: 024 | **Data**: 2026-09-19
**Natureza**: a feature é exclusivamente documental/diagnóstica — não há código novo para executar. A validação "end-to-end" é a **conferência do relatório** contra o checklist abaixo (equivalente aos testes desta feature — research R10).

---

## Pré-requisitos

- Repositório na branch de trabalho com as specs da 024 presentes.
- Ferramentas de conferência: `git status --porcelain`, busca textual do projeto (ripgrep/IDE).
- **Não é necessário**: banco de dados, `.env` real, execução da aplicação ou da suíte pytest.

## Passo 1 — Verificar o zero diff (SC-001)

```bash
git status --porcelain
```

**Esperado**: apenas caminhos sob `specs/024-auditoria-config-backup/` (e `.specify/feature.json` do fluxo Spec Kit). **Nenhum** arquivo de `app/`, `tests/`, `docs/`, `README.md`, templates ou configuração alterado. Se houver qualquer alteração de produção → falha (FR-001/NFR-001 violados).

## Passo 2 — Verificar a exaustão da varredura (SC-002)

Comparar o total de matches das buscas obrigatórias com as entradas do relatório:

```bash
rg -n "BACKUP_AUTO_(ENABLED|SCHEDULE|TIME|WEEKDAY)|BACKUP_RETENTION_(DAILY_DAYS|WEEKLY_WEEKS|MONTHLY_MONTHS|KEEP_PRE_RESTORE)" --stats
rg -n "get_effective_config|backup_config|BackupConfig" --stats
```

**Esperado**: cada ocorrência de código/teste está no inventário do relatório com classificação A–H; casos excluídos (ex.: `ACTION_BACKUP_AUTO_SUCCESS/FAILED` — rótulos de auditoria, research R7) estão listados com justificativa. Contagem do relatório ≥ contagem das buscas (menos falsos positivos justificados). Qualquer ocorrência sem classificação → falha.

## Passo 3 — Verificar as respostas-chave e os critérios (SC-004/SC-006)

Abrir `relatorio.md` e conferir:

- **7 respostas-chave** (§1.3 do contrato) — cada uma com veredito SIM/NÃO/PARCIAL + evidência `arquivo:linha`.
- **14 critérios de conclusão** (§1.4 do contrato) — cada um marcado com evidência citável.
- **Tabela das 8 env vars** (§1.2) — colunas completas (necessária? função atual? fonte efetiva? observação?), sem conclusão de remoção sem a devida análise.

**Falha se**: resposta sem evidência, critério solto sem marcação, ou tabela incompleta.

## Passo 4 — Verificar fluxos contra o código (spot-check independente)

Amostragem manual (não herdar do relatório — conferir o código):

1. **Scheduler não lê `BACKUP_AUTO_ENABLED` na decisão**: no loop (`app/services/backup_scheduler.py` ~L796–800), confirmar `refresh_effective_config()` + `_eff().auto_enabled`; a constante aparece só no fallback de boot (L117–124).
2. **Retenção lê a efetiva**: em `_apply_retention` (~L625–627), confirmar `eff.retention_*`.
3. **Tela persiste na singleton**: no POST (`app/web/admin_routes.py` ~L888–963), confirmar `save_backup_config` → commit único → auditoria `BACKUP_CONFIGURACAO_ALTERADA` → redirect 303.
4. **Instalação nova**: sem linha `backup_config`, `get_backup_config(db)` cria `id=1, auto_enabled=False` (service L72–76); efetiva = env → default; `BACKUP_AUTO_ENABLED` default `"false"` (config L67).

## Passo 5 — Verificar a qualidade das evidências (SC-007)

- Cada achado tem rótulo OK/ATENÇÃO/INCONSISTÊNCIA/RISCO/BLOQUEADOR + justificativa.
- Achados não-OK têm recomendação **sem implementação** (nada corrigido nesta feature).
- Nenhuma credencial/segredo citado no relatório (Constitution VI).

## Resultado esperado final

| Verificação | Critério de aprovação |
|---|---|
| Zero diff | `git status` limpo fora de `specs/024-…` |
| Exaustão | 100% das ocorrências classificadas ou excluídas com justificativa |
| Completude | 12 seções + 7 respostas + 14 critérios + tabela de 8 linhas |
| Evidência | Toda afirmação com `arquivo:linha` |
| Neutralidade | Nenhuma correção implementada; remoção só com análise completa |

Se todos os passos passam → a auditoria está completa e o relatório pronto para decisão do requisitante (eventual spec corretiva futura).
