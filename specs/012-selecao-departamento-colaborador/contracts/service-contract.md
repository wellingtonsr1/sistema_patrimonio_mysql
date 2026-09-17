# Contract — Camada de Services (feature 012)

**Feature**: 012-selecao-departamento-colaborador | **Data**: 2026-09-17 (**REVISADO**)

> **Revisão**: fonte oficial = valores distintos de `Location.department`; integridade por **validação de texto**; `CustodianService` permanece **intocado**. Nenhum seed, nenhuma tabela nova.

Contratos das regras de negócio (Constitution II/III): regras vivem em services; rotas (web e API) consomem.

---

## 1. `DepartmentService` (NOVO — `app/services/department_service.py`)

Serviço de **leitura + validação** da fonte oficial. Sem estado, métodos estáticos (padrão dos services do projeto).

### 1.1 `list_official(db) -> List[str]`
- **Entrada**: sessão.
- **Saída**: lista dos valores **distintos, não nulos, trim ≠ ''** de `Location.department`, ordenada alfabeticamente (case-insensitive).
- **Regra**: derivada ao vivo a cada chamada — reflete imediatamente locais cadastrados/editados (R8 revista). Nenhum cache/seed.
- **Uso**: alimentar a seleção no render dos formulários (contract UI §4).

### 1.2 `ensure_official(db, department: str) -> str`
- **Entrada**: valor de departamento submetido pelo formulário (texto).
- **Saída**: a **forma canônica oficial** (o valor exato vigente na lista) quando houver correspondência; senão, levanta `ValueError`.
- **Regras**:
  1. Normaliza entrada (trim).
  2. Vazio → `ValueError("Departamento/Setor é obrigatório")` (FR-003/AC-03).
  3. Correspondência **case-insensitive** contra `list_official` (ex.: "SUPORTE", "suporte", "Setor de Suporte" → todos casam com o oficial "Setor de Suporte" quando é o único correspondente — a canonização elimina divergências de caixa/trim, R7).
  4. Sem correspondência (incluindo o caso de múltiplos oficiais diferenciados apenas por caixa — ambiguidade real de dados, rejeita-se para forçar seleção explícita da lista) → `ValueError("Departamento/Setor inválido — selecione um registro da lista oficial")` (FR-004/AC-02/AC-04).
- **Invocação**: exclusivamente pelos handlers web `create_custodian_form`/`update_custodian_form` **quando `department_source == "official"`** (contract UI §4; caminho legado não invoca — R6 revista).

### 1.3 O que este service NÃO faz (delimitação)
- Não cria/altera/remove valores oficiais (a criação é o fluxo existente de locais — R8).
- Não valida API/CSV/legado (caminhos fora do escopo — R6).
- Não gerencia ativo/inativo (fonte sem conceito — Q3 inoperante, R9 revista).

---

## 2. `CustodianService` — INTOCADO

`app/services/custodian_service.py` **não sofre nenhuma alteração** nesta feature.

- `create`/`update` continuam recebendo `department: str` (texto) com as validações atuais (obrigatório não vazio via schema `CustodianCreate.department: str` — rejeição Pydantic 422 nos caminhos de API).
- A canonização/validação oficial acontece **antes** (`DepartmentService.ensure_official`, chamado pela rota), de modo que o service grava o valor que recebe — agora, no formulário, sempre canônico.

| Caminho | Comportamento do `CustodianService` |
|---|---|
| Formulário (novo) | Recebe valor já validado/canônico pela rota → grava como hoje |
| API REST | Idêntico ao atual (texto livre; contrato inalterado — `api-contract.md`) |
| Importação CSV | Idêntico ao atual (`custodian_import_service.py` intocado) |
| Chamadas diretas (testes) | Idêntico ao atual — suíte existente verde sem edição (R6) |

---

## 3. Garantias transversais

- **Transacional**: qualquer `ValueError` de `ensure_official` ocorre **antes** de qualquer escrita — nada é gravado parcialmente (a rota converte o erro em redirect `?error=`, padrão existente).
- **PROV-***: nenhuma interação — `is_provisional` e regras de matrícula intocadas (FR-007).
- **Auditoria**: `write_change_audit` das rotas intocado; snapshot continua capturando o texto gravado (Constitution IX).
- **Escopo**: `LocationService`, `MovementService`, `InventarioService`, `AdService`, `CustodianImportService`, `CustodianService`, models e schemas — todos intocados (R10 revista).

---

## 4. Traçabilidade spec → contrato

| Requisito | Contrato |
|---|---|
| FR-001/AC-01 (seleção de registros existentes, lista do banco) | §1.1 `list_official` |
| FR-002/AC-02 (sem criação por digitação) | §1.2 regra 4 (sem correspondência → erro); UI não oferece criação |
| FR-003/AC-03 (obrigatório no backend) | §1.2 regra 2 |
| FR-004/AC-04 (validação backend da seleção) | §1.2 (regras 3–4) no caminho do formulário |
| FR-005/AC-05 (associação correta) | §2: valor canônico gravado em `custodians.department` |
| FR-006/AC-06 (edição com a mesma fonte) | §1.1/§1.2 também no `update_custodian_form` |
| FR-007/AC-07 (`PROV-*` normal) | §3 |
| FR-008/AC-08 (histórico intocado) | §3 + RV-6 (`data-model.md`) |
| FR-010/AC-10 (sem estrutura duplicada) | Nenhuma estrutura nova (R1/R2/R3 revisadas) |
| FR-012 (não-regressão) | §2 (caminhos legados idênticos) |
