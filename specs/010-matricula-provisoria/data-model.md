# Data Model: Identificador Provisório de Colaborador (feature 010)

**Natureza**: **zero DDL** — nenhuma tabela, coluna, índice ou constraint é criada ou alterada (Constitution VII / SC-007). O "modelo" abaixo descreve a **semântica estendida** de campos existentes.

## Entidade `Custodian` (existente — inalterada na estrutura)

| Campo | Tipo atual | Semântica nova |
|---|---|---|
| `registration_code` | `String(50)`, `NOT NULL`, `UNIQUE`, indexado | Passa a abrigar **dois domínios**: matrícula oficial (informada, como hoje) ou identificador provisório `PROV-` + 6 dígitos (`PROV-000001`..`PROV-999999`), gerado pelo sistema. **O prefixo `PROV-` é o marcador** da condição provisória — não há flag separada. Unicidade garantida pela `UNIQUE` existente (permanente — `PROV-*` nunca é reutilizado) |
| demais campos | (inalterados) | — |

### Validações da semântica nova (aplicadas no service — Constitution III)

1. **Criação**: campo ausente/vazio (após trim) → geração automática do próximo `PROV-%06d` (maior existente + 1, retentativa limitada sobre colisão da `UNIQUE`).
2. **Anti-fabricação** (criação e atualização, web e API): valor fornecido pelo usuário que case com `PROV-` + 6 dígitos é **rejeitado** — o prefixo é exclusivo do sistema.
3. **Substituição**: valor `PROV-*` atual pode ser trocado por matrícula oficial (fluxo de edição; web restringe ao caso provisório; API mantém validações atuais) — **mesmo registro** (`id` imutável), unicidade validada como hoje.
4. **Formato**: `PROV-` literal maiúsculo + exatamente 6 dígitos (`000000`–`999999`); 1 milhão de identificadores provisórios simultâneos é ordem de grandeza muito acima da necessidade real.

## Entidades consumidoras (nenhuma alterada — comportamento atual)

| Entidade | Relação com a matrícula | Impacto da feature |
|---|---|---|
| `Asset.custodian_id` | FK para `custodians.id` | **Nenhum estrutural** — FK por `id`: substituição `PROV-*` → oficial preserva a custódia automaticamente |
| `Movement.origin/destination_custodian_id` + `*_name` | FK + snapshot textual "Nome (MAT-xxxx)" gravado na época | **Nenhum estrutural** — snapshots históricos imutáveis (Constitution IV); novos snapshots gravam o valor vigente no momento (podendo ser `PROV-*`) |
| `movements/term.html` | exibe `term.custodian.registration_code` (matrícula viva) | Exibição ganha a marcação "provisória" quando o colaborador é `PROV-*` (apresentação apenas) |
| `InventarioItem.expected_custodian_name` | snapshot textual de **nome** | **Nenhum** — inventário não usa matrícula |
| `User` / sessões / AD | sem FK com `Custodian`; AD casa `registration_code == username AD` (L213) | **Nenhum** — `PROV-*` não casa com username de domínio real; mecanismo intocado |

## Transições de estado do identificador

```text
[informada] ────────────────> Matrícula oficial (estado atual — inalterado)
[vazia] ──> geração ────────> PROV-000NNN (provisória)
                                  │
                                  └── substituição (colaboradores.editar) ──> Matrícula oficial
                                                                             (mesmo registro; sem volta a PROV-*)
```

Regras de transição: `PROV-*` → oficial é a **única** transição nova; oficial → `PROV-*` não existe (anti-fabricação impede); oficial → oficial segue o comportamento atual (API com unicidade; web bloqueada).

## Validações e regras de integridade

- `UNIQUE` de `registration_code` cobre **todos** os registros (oficiais e provisórios) — nenhum DDL novo.
- `NOT NULL` nunca é violado: a geração ocorre **antes** do insert.
- Auditoria: criação e substituição seguem os mecanismos existentes (`write_change_audit`), com before/after no caso da substituição — sem dado sensível.
