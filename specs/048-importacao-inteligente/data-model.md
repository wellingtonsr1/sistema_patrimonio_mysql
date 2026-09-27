# Data Model: 048 — Importação Inteligente

**Data**: 2026-09-26 · **Spec**: [spec.md](spec.md) · **Zero persistência nova**: toda a camada inteligente vive em memória entre as fases; os dados gravados continuam sendo os das tabelas existentes (assets/custodians/locations/movements/audit_logs).

---

## 1. Estruturas existentes consumidas (nenhuma alterada)

| Estrutura | Uso pela 048 |
|---|---|
| `COLUMN_ALIASES` (3 services) | Fonte da identificação automática de colunas (união, sem duplicar) |
| `_validate_row` (3 services) | Obrigatoriedade real por entidade (casca da classificação) |
| `_resolver_custodiante` (029) | Resolução de responsável por matrícula→nome (NUNCA cria) |
| `LocationService.get_by_name`, `_find_by_registration_code/email`, `_find_existing_location` | Duplicatas e relacionamentos no banco |
| `execute_import` / `execute_custodian_import` / `execute_locations_import` | Única instância de gravação (intocados salvo retorno aditivo — R8) |
| `MovementService.create_movement` / `resolve_movement_type` | Fluxo patrimonial (intocado — Constitution IV) |
| `write_audit` | Auditoria existente do confirm |

## 2. Estruturas em memória (novas — nunca persistidas)

### 2.1 Análise do arquivo (fase map)

```text
ColumnAnalysis {
  header: [str],                    # colunas originais do CSV (ordem do arquivo)
  suggestions: [ColumnSuggestion],  # uma por coluna
  total_rows: int,                  # contagem de registros de dados
  parse_errors: [str],              # guardas R6 (vazio/sem cabeçalho/corrompido)
  delimiter: str,                   # detectado pelo parser existente
}

ColumnSuggestion {
  column: str,                      # nome original da coluna
  field: str | None,                # nome canônico ("tombamento", "equipamento", ...)
  confidence: "auto" | "ambigua" | "desconhecida",
  candidates: [str] | [],           # campos candidatos quando ambigua
}
```

### 2.2 Mapeamento confirmado (fase map → analyze)

```text
mapping = { <coluna original>: <campo canônico | "" (ignorada)> }
```

- Colunas com `confidence=auto` vêm pré-selecionadas; `ambigua` vêm sem seleção (exigem escolha — FR-003); `desconhecida` vêm marcadas "não utilizada" (FR-005).
- Viaja para a próxima fase como JSON em campo oculto (mesmo transporte do `csv_rows|tojson` vigente).

### 2.3 Classificação por registro (fase analyze/preview)

```text
RowClassification {
  row_num: int,                     # nº da linha no arquivo (header = 1)
  status: "VALIDO" | "AVISO" | "DUPLICADO" | "ERRO" | "NAO_ENCONTRADO" | "IGNORADO",
  problems: [str],                  # motivos legíveis (ex.: "Tombamento já existe: TMB-0001")
  resolved_values: dict,            # linha renormalizada pelo mapping (para confirm)
  internal_dup_of: int | None,      # linha anterior com a mesma chave natural
  duplicates_in_db: bool,
}

PreviewSmart {
  rows: [RowClassification],        # ordenada por row_num
  summary: { total, validos, avisos, duplicados, erros, nao_encontrados, ignorados },
  mapping: dict,                    # eco do mapeamento confirmado
  needs_resolution: [row_num],      # linhas NAO_ENCONTRADO aguardando decisão (R4)
}
```

### 2.4 Resoluções interativas (fase analyze → confirm — R4)

```text
resolutions = { <row_num>: "skip" | "sem_custodia" | "assign:<custodian_id>" }
```

- Aplicadas pela camada **antes** do `execute_import`: `assign` → linha renormalizada com `custodiante` = valor do colaborador escolhido; `sem_custodia` → `custodiante` vazio; `skip` → linha removida do lote.
- `execute_import` recebe o lote como se o CSV tivesse chegado daquele jeito — nenhuma mudança de assinatura/semântica.

### 2.5 Resultado final (fase confirm — R8, retorno aditivo dos execute_*)

```text
result {
  imported: int, skipped: int, total_processed: int,   # existentes
  errors: [str],                                        # existente (mensagens agregadas)
  row_results: [                                        # NOVO (aditivo — R8)
    { row_num, status, tag/name, motivo }
  ],
}
```

## 3. Chaves de duplicidade por entidade (regras existentes)

| Entidade | Chave natural (duplicidade interna) | Verificação no banco (existente) |
|---|---|---|
| Equipamentos | `tombamento` (upper) | `Asset.tag` (+ `serial_number` único) |
| Colaboradores | `matricula` (se informada) + `email` | `_find_by_registration_code` / `_find_by_email` |
| Locais | `nome` (comparação normalizada) | `_find_existing_location` (`get_by_name`) |

## 4. Fluxo entre fases (sem sessão/temp-table)

```text
POST import (file)            → analyze_columns → render step=map (arquivo oculto em JSON)
POST import (step=analyze)    → re-parse + mapping aplicado + classify_rows → render preview
POST import/confirm           → resoluções aplicadas → execute_*(linhas resolvidas) → relatório
```

Cada fase **reexecuta a análise server-side** (nunca confia só no cliente); o que viaja entre fases: conteúdo do arquivo + mapping + resolutions (campos ocultos JSON — padrão vigente). Banco inalterado até o confirm.

## 5. Segurança

- Conteúdo do arquivo nunca executado/interpretado como código; JSON dos campos ocultos validado server-side a cada fase (`json.loads` + verificação de estrutura, como já faz o confirm atual).
- Nenhuma credencial/segredo em qualquer estrutura acima; mensagens de problema carregam apenas dados do próprio CSV (tombamento, nome, motivo).
- Tamanho máximo do upload (10 MB) e extensão `.csv` validados antes da análise.
