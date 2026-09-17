# Contract — API REST (feature 012)

**Feature**: 012-selecao-departamento-colaborador | **Data**: 2026-09-17 (**REVISADO**)

> **Documento de NÃO-MUDANÇA**: com a revisão da fonte oficial (reuso de `Location.department`) e da estratégia de integridade (validação por texto no caminho do formulário — research R2/R6/R7 revisadas), **a API REST de colaboradores permanece integralmente inalterada nesta feature**. Este contrato registra isso explicitamente para o plan/tasks/testes.

Superfície: `app/api/custodians_api.py` (router `/api/v1/custodians`).

---

## 1. Schemas (`app/schemas/custodian.py`) — inalterados

- `CustodianCreate` / `CustodianUpdate` / `CustodianRead`: **nenhum campo novo** (não existe `department_id` — decisão revista R2).
- `department: str` segue obrigatório em `Create` e opcional em `Update`, como hoje.

## 2. Endpoints — comportamento atual preservado (100%)

| Endpoint | Permissão (atual) | Mudança nesta feature |
|---|---|---|
| `POST /api/v1/custodians` | `colaboradores.criar` | **Nenhuma** — `department` textual aceito como hoje (ex.: `"TI"`), mesmo sem local correspondente |
| `PUT /api/v1/custodians/{id}` | `colaboradores.editar` | **Nenhuma** |
| `GET /api/v1/custodians` / `/{id}` / `/{id}/assets` | `colaboradores.visualizar` | **Nenhuma** |
| `POST /api/v1/custodians/import` (CSV) | `colaboradores.criar` | **Nenhuma** — grava texto como hoje (fora do escopo — spec Seção 8) |

- Formato de erro, autenticação, RBAC, auditoria e payloads: idênticos aos atuais.
- **Nenhum endpoint de departamentos é criado** (a lista oficial é server-side no formulário — `ui-contract.md` §4; research R4).

## 3. Por que a API não é estrita (decisão registrada)

A validação estrita aplica-se **apenas ao caminho do formulário** (marcador `department_source=official` — `ui-contract.md` §4). Rationale quantificado (research R6 revista):

- A suíte existente envia textos arbitrários (`"TI"`, `"D"`, `"RH"`, `"R"`, `"UX"`…) em **10 POSTs de API** (`test_api.py` ×5, `test_rbac.py` ×2, `test_custodian_provisional.py` ×2, `test_custodian_import.py` ×1) e **28 chamadas** diretas ao service — sem locais correspondentes no banco por-teste; validação estrita quebraria dezenas de testes (Constitution VIII veda editá-los) e mudaria contratos vigentes (FR-012).
- O alvo do briefing é a **interface de cadastro/edição** ("o usuário não consegue criar denominação digitando") — atendida pelo formulário + `ensure_official`.
- **Risco residual registrado (AC-04)**: chamadas diretas à API/serviço continuam podendo gravar texto arbitrário — **comportamento vigente pré-existente**, preservado por FR-012 e pelo escopo (Seção 8 da spec: importação/CSV e API fora do alvo). Normalização progressiva desses caminhos é feature futura candidata (backlog).

## 4. Traçabilidade dos FRs de API

| Requisito | Status |
|---|---|
| FR-012 (não-regressão de caminhos existentes) | ✅ Integral — nenhum endpoint muda |
| FR-011 (Cargo/Função inalterado) | ✅ `role` permanece texto livre |
| FR-007/AC-07 (`PROV-*`) | ✅ Nenhuma regra nova de matrícula |
| FR-013 (auditoria existente) | ✅ `write_change_audit` intocado |
| AC-04 (validação backend) | ✅ Garantido **no caminho do formulário** (alvo da feature); API segue padrão vigente — risco residual registrado no §3 |
| AC-08/AC-09 (histórico e Localização intocados) | ✅ Nenhum efeito sobre API de movimentações/locais/inventário |

## 5. Impacto em testes

- Suíte existente: **zero edição** (todos os POSTs/PUTs atuais seguem válidos).
- Testes novos (`tests/test_department_selection.py`): exercitam o formulário web (marcador `official`) e registram **teste de caracterização** do caminho API (POST com texto livre → 201) como garantia explícita da não-mudança (quickstart §2).
