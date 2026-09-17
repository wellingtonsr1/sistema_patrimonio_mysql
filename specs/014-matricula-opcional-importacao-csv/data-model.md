# Data Model: Matrícula Opcional na Importação de Colaboradores via CSV

**Feature**: 014-matricula-opcional-importacao-csv | **Data**: 2026-09-17

> **Zero DDL (FR-009)**: nenhuma tabela, coluna, índice ou migration é criada ou alterada. Este documento descreve os **dados e estados do fluxo existente** sobre os quais a feature opera.

---

## 1. Entidade afetada

### `Custodian` (`app/models/custodian.py`) — INTOCADA

| Campo | Relevância nesta feature |
|---|---|
| `registration_code` | Alvo da regra. Já `UNIQUE` (garantia final de unicidade), já aceita `PROV-%06d` (feature 010 em produção). Nenhum DDL. |
| `name`, `email` (único na prática), `cpf`, `role`, `department`, `is_active` | Populados pelo importador exatamente como hoje. |

**Relacionamentos**: intocados (`Asset.custodian_id` etc. — a troca/geração de matrícula não toca histórico patrimonial; ver RV-4).

---

## 2. Estado do dado `matricula` no fluxo do importador

```text
                ┌────────────────────────────────────────────────────────┐
                │ célula no CSV                                          │
                └──────┬─────────────────────┬───────────────────────────┘
                       │                     │
              informada (≠ vazio)      ausente: vazio │ só espaços │ coluna inexistente
                       │                     │
        ┌──────────────▼──────────┐  ┌───────▼─────────────────────────┐
        │ trim + upper (regra     │  │ SEM ERRO (antes: "matricula é   │
        │ atual mantida)          │  │ obrigatória") → flag provisória │
        │ → usada como está       │  │ → gerada na EXECUÇÃO: PROV-%06d │
        └──────┬──────────────────┘  │   via fachada do gerador único  │
               │                     └───────┬─────────────────────────┘
     duplicada?│  sim → regra atual          │
               │       (skip ou update       │
               │        conforme             │
               │        skip_duplicates)     │
               │  não → criação normal       │
               └──────────────┬──────────────┘
                              ▼
                    Custodian criado/atualizado
                  (mesma transação e erros de hoje)
```

**Invariantes** (RV-1..RV-7):

- **RV-1** — A decisão "informada vs ausente" é **por linha** e feita **uma vez**, na execução, com base no valor após trim (Research R2/R11). Chave ausente, vazio e só espaços são o **mesmo estado**.
- **RV-2** — Nenhuma linha deixa de ser importada **apenas** pela ausência de matrícula; as demais validações (nome, e-mail, cargo, setor, `ativo`) permanecem idênticas (FR-008).
- **RV-3** — Provisórias geradas na mesma execução são **duas a duas distintas** (geração imediatamente antes de cada `db.add` + `db.flush()` já existente — a consulta do gerador enxerga a anterior; RV-1/R6 do research).
- **RV-4** — A geração não altera histórico: movimentações, termos, inventário e auditoria referem-se ao colaborador (id), não à matrícula; nada é reescrito retroativamente.
- **RV-5** — Matrícula informada: normalização (trim+upper), unicidade e duplicidade **byte-a-byte** iguais às atuais; nunca substituída por provisória (FR-003/FR-004).
- **RV-6** — Preview nunca fabrica número: linha sem matrícula exibe a matrícula vazia (flag `will_generate_provisional` disponível); o número só existe na execução (FR-007).
- **RV-7** — Unicidade global continua garantida pela constraint UNIQUE de `registration_code` + consulta pré-inserção do gerador (mesma estratégia da feature 010); janela teórica de corrida herdada, documentada (Research R7), não corrigida.

---

## 3. Fluxo entre estágios (sem alteração de transporte)

| Estágio | Entrada | Saída | Mudança nesta feature |
|---|---|---|---|
| `parse_custodian_csv(content)` | conteúdo CSV | `(rows, errors)` | `_validate_row` deixa de emitir o erro de matrícula obrigatória; linha sem matrícula **entra** em `rows` (chave `registration_code` presente vazia **ou ausente** — ambos válidos) |
| `preview_custodian_import(rows, db)` | rows válidas | `{previews, total, duplicates, new_items}` | duplicata verificada **só por e-mail** quando matrícula vazia; flag `will_generate_provisional` nas entradas sem matrícula; nenhum número fabricado |
| transporte web | preview | textarea `csv_data` (JSON) | **nenhum** — JSON preserva vazio/ausência (Research R5) |
| `execute_custodian_import(rows, db, skip_duplicates)` | rows | `{imported, skipped, errors, total_processed}` | no ramo de criação nova: matrícula vazia → gerar via fachada do gerador único; ramo de atualização (duplicata) **intocado** (não aplica a linha sem matrícula, que nunca duplica por matrícula) |

---

## 4. Regras de validação (estado final)

| Situação no CSV | Estado atual | Estado da feature |
|---|---|---|
| `matricula` informada válida | aceita (trim+upper) | **idêntico** (RV-5) |
| `matricula` informada duplicada no banco | skip/update conforme `skip_duplicates` | **idêntico** |
| `matricula` vazia / só espaços / coluna ausente | **erro** ("matricula é obrigatória") | **gera `PROV-%06d` única** (via gerador único) |
| nome/email/cargo/setor ausentes ou inválidos | erro | **idêntico** (continuam obrigatórios) |
| e-mail duplicado | erro/skip conforme `skip_duplicates` | **idêntico** |
| `ativo` inválido | erro | **idêntico** |
| duas linhas sem matrícula | — (não chegava aqui) | cada uma recebe provisória distinta (RV-3) |
