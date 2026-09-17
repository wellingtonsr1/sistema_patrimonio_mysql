# Data Model: Seleção de Departamento/Setor no Cadastro de Colaborador

**Feature**: 012-selecao-departamento-colaborador | **Data**: 2026-09-17
**Base**: spec.md (FRs, clarificações) + research.md (**REVISADO** — R1–R3, R6–R9)

> **Revisão 2026-09-17**: com a decisão de reutilizar `Location.department` (R1 revista), **não existem entidades novas nem colunas novas**. Este documento descreve o modelo **existente** e as **regras de validação** que o comportamento novo impõe sobre ele.

---

## Visão geral — ZERO DDL

```text
locations (EXISTENTE, intocada)         custodians (EXISTENTE, intocada)
┌───────────────────────────┐           ┌────────────────────────────┐
│ id            PK          │           │ id                  PK     │
│ name          UNIQUE      │           │ registration_code   UNIQUE │
│ branch        NOT NULL    │  fonte    │ department  String(100)    │
│ department    String(100) │───────►   │             NOT NULL       │
│   (texto, NÃO-NULL)       │  oficial  │   (único armazenamento;    │
│ building/floor/room...    │           │    valor validado no       │
└───────────────────────────┘           │    caminho do formulário)  │
                                        └────────────────────────────┘
        Nenhuma tabela nova · Nenhuma coluna nova · Nenhuma FK · Nenhum dado migrado
```

---

## "Entidade" da fonte oficial: valores distintos de `Location.department`

**Não é uma tabela** — é uma **visão derivada ao vivo**:

```text
Lista oficial = SELECT DISTINCT department FROM locations
                WHERE department IS NOT NULL AND TRIM(department) <> ''
                ORDER BY department
```

| Propriedade | Valor |
|---|---|
| Armazenamento | O próprio coluna `locations.department` (existente) |
| Identidade | O **valor textual** canônico (não há id endereçável — R2 revista) |
| Ciclo de vida | Nenhum (sem ativo/inativo — Q3 inoperante, R9 revista) |
| Criação de novo valor oficial | Cadastro/edição de **local** (fluxo existente — `locations/new`, permissão `locais.criar`) |
| Consumidores existentes da mesma lista | Filtros de bens (`routes.py` 342/406), escopo de inventário (`inventarios/new` 1806, `inventario_service._scope_query`), dashboard (`dashboard_service` agrupa por `Location.department`) |

---

## Entidade: `Custodian` (existente — nenhuma alteração estrutural)

| Campo | Estado | Papel nesta feature |
|---|---|---|
| `department` String(100) NOT NULL | **Inalterado** | Único armazenamento. No formulário, recebe a **forma canônica oficial** (o valor exato vigente em `locations.department` — normalização de caixa/trim no caminho validado). Caminhos legados (API/CSV/service) gravam como hoje |
| Demais campos (`registration_code`, `name`, `email`, `cpf`, `role`, `is_active`) | Inalterados | `role` permanece texto livre (FR-011); `PROV-*` sem regra nova (FR-007) |

**Consumidores do texto que continuam funcionando sem alteração** (nenhum é tocado): pesquisa 006 (`CustodianService.get_all` ilike), `report_service.generate_custodians_csv` (linha 439), `reports/custodians_report.html`, `custodians/list.html`, `custodians/detail.html`, `assets/form.html`, `movements/new.html`, `movements/term.html` (lê valor vivo na emissão), AD (lê, não escreve), importação CSV, suíte de testes existente.

---

## Regras de validação (o "modelo" do comportamento novo)

Como não há estrutura nova, o comportamento novo é um **contrato de validação** sobre o modelo existente:

| # | Regra | Origem |
|---|---|---|
| RV-1 | Lista oficial = valores distintos de `locations.department` (trim ≠ ''), derivada ao vivo no render do formulário | FR-001, R1/R8 |
| RV-2 | No caminho do formulário (`department_source=official`), o valor submetido DEVE corresponder (case-insensitive, trim) a um valor da lista oficial; grava-se a forma canônica oficial (ex.: submetido "SUPORTE" → grava "Setor de Suporte", a forma vigente). **Exceção (remediação I2, opção b)**: na edição, valor submetido idêntico ao vigente é aceito sem validação (FR-014) | FR-004, AC-04, R7 |
| RV-3 | Valor que não corresponde a nenhum oficial → rejeitado no backend (nada gravado) | FR-004, AC-02 |
| RV-4 | Campo obrigatório: vazio/ausente no caminho validado → rejeitado no backend | FR-003, AC-03 |
| RV-5 | Caminhos legados (API create, importação CSV, chamadas diretas ao service, formulário sem marcador) preservam o comportamento atual — texto livre obrigatório não vazio | FR-012, R6, escopo (Seção 8 da spec) |
| RV-6 | Colaboradores existentes não são alterados; histórico (movimentações, termos, inventários, auditoria) imutável | Q2/Q3, FR-014, FR-008 |
| RV-7 | Nenhuma regra nova por tipo de matrícula (`PROV-*` sem restrição) | FR-007 |

**Inexistente por decisão** (registrado para traçabilidade): FK/`department_id` (incoerente com fonte derivada — R2 revista); tabela `departments` (R1 revista); `is_active`/bloqueio Q3 (fonte sem conceito — R9 revista).

---

## Auditoria

Mecanismo intocado: `write_change_audit` continua capturando `department` (texto) nos snapshots before/after das rotas web existentes (`_custodian_audit_snapshot`). Nenhuma alteração de `audit_logs` nem de schemas de snapshot (Constitution IX).

---

## Estratégia de migração (resumo — Constitution VII)

**Não há migração.** Nenhum DDL, nenhum backfill, nenhum dado alterado. Rollback = reversão de código (nenhuma estrutura residual). O acervo de colaboradores existentes permanece byte-a-byte igual (RV-6).
