# Phase 1 — Data Model: 006-pesquisa-colaboradores

**Feature**: Pesquisa de Colaboradores | **Date**: 2026-09-16

> **Nenhuma entidade nova. Nenhuma coluna, tabela, índice ou constraint nova (zero DDL).**
> A feature é exclusivamente de **consulta**: filtra a entidade existente por colunas já
> existentes e renderiza o resultado na tela existente.

---

## 1. Entidade consultada

### 1.1 Custodian — tabela `custodians` (`app/models/custodian.py`) — **SELECT com filtro (read-only)**

| Campo | Papel na feature |
|---|---|
| `registration_code` | Campo pesquisável nº 1 (matrícula) — exibido como `tag-badge` |
| `name` | Campo pesquisável nº 2 (nome) — renderiza o link para `/custodians/{id}` |
| `role` | Campo pesquisável nº 3 (cargo) |
| `department` | Campo pesquisável nº 4 (departamento) |
| `email` | Campo pesquisável nº 5 (e-mail) |
| `id` | Identificador para links/ações (intocado) |
| `is_active` | Filtro `active_only` existente (chamadores externos) — não alterado |

Nenhum campo é gravado, alterado ou removido. Nenhuma relação nova.

### 1.2 Valor calculado exibido — `active_assets_count`

- Calculado na rota por colaborador visível via `CustodianService.count_assigned_assets`
  (mecanismo atual, preservado). A pesquisa apenas define **quais** colaboradores aparecem;
  o valor exibido é idêntico ao de antes (RN-003/FR-012).

## 2. Fluxo de consulta (única operação da feature)

```text
GET /custodians[?search=<termo>]
  → SELECT * FROM custodians
      [WHERE registration_code ILIKE %t% OR name ILIKE %t% OR role ILIKE %t%
             OR department ILIKE %t% OR email ILIKE %t%]        ← novo, somente com termo
      ORDER BY name                                              ← existente, preservado
  → para cada resultado: COUNT de bens ativos (existente, preservado)
  → renderização: tabela (mesma) | "Nenhum colaborador encontrado." | "Nenhum colaborador cadastrado"
```

Sem INSERT/UPDATE/DELETE em qualquer tabela. Sem auditoria (consulta não é operação
auditável — padrão do sistema para listagens).

## 3. Impacto de schema desta feature

**NENHUM.** Mecanismo de evolução do projeto (`init_db` + `_ensure_schema_migrations`) não é
acionado. O ILIKE usa os índices existentes da tabela (scan em `custodians`, volume pequeno);
nenhum índice novo é criado nesta feature (candidato a tarefa própria se o volume crescer).
