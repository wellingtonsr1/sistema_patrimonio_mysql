# Contract — Services da importação (feature 014)

**Feature**: 014-matricula-opcional-importacao-csv | **Data**: 2026-09-17

Contratos das assinaturas/comportamentos alterados. **Nenhuma assinatura pública é removida ou renomeada**; todas as mudanças são aditivas ou de comportamento previsto na spec.

---

## 1. `CustodianService` (`app/services/custodian_service.py`) — fachada mínima

### NOVO — `generate_available_provisional_code(db: Session) -> str`

```python
@staticmethod
def generate_available_provisional_code(db: Session) -> str:
    """Feature 014: fachada pública do gerador único (feature 010).
    Retorna o próximo PROV-%06d disponível: delega a _next_provisional_code
    (lógica interna INTOCADA) e repete enquanto o código existir
    (get_by_registration_code — já existente), replicando a verificação
    pré-inserção do create. A constraint UNIQUE permanece a garantia final."""
```

- **Comportamento**: loop `_next_provisional_code` + `get_by_registration_code` até código livre; retorna o código (não persiste nada).
- **Restrições**: NÃO altera `_next_provisional_code`, `_PROV_*`, `create`, `update` (cadastro individual intacto — FR-010).
- **Rationale**: research R1; FR-002 (uma só implementação de geração no sistema).

---

## 2. `custodian_import_service` (`app/services/custodian_import_service.py`)

### 2.1 `_validate_row(row, row_num) -> List[str]` — assinatura igual, comportamento alterado (previsto)

| Antes | Depois |
|---|---|
| `registration_code` vazio → erro `"Linha N: matricula é obrigatória"` | **Sem essa regra** — matrícula ausente/vazia/espaços é válida nesta validação |

- **Intocado**: nome, e-mail (obrigatório + regex), cargo, setor, `ativo` (valores inválidos) — byte-a-byte (FR-008).

### 2.2 `parse_custodian_csv(content) -> Tuple[List[Dict[str, str]], List[str]]` — assinatura igual

- Linhas sem matrícula agora entram em `rows` (antes: só em `errors`).
- Célula vazia/só espaços chega como `""`; **coluna ausente** pode chegar como chave ausente — ambos válidos (o consumidor usa `row.get("registration_code", "")`).
- Erros restantes: idênticos aos atuais.

### 2.3 `preview_custodian_import(rows, db) -> Dict` — assinatura igual, campo aditivo

```python
{
  "previews": [
    {
      "registration_code": str,            # "" quando ausente (novo caso possível)
      "name": str, "role": str, "department": str, "email": str,
      "existing_custodian_id": int | None,
      "is_duplicate": bool,                # vazia → verificação SÓ por e-mail (research R3)
      "will_generate_provisional": bool,   # NOVO (aditivo): True quando matrícula vazia
    }, ...
  ],
  "total": int, "duplicates": int, "new_items": int,   # semântica inalterada
}
```

- **Regra de duplicata**: `existing = _find_by_registration_code(...) if reg_code else None` → `or _find_by_email(...)` — quando matrícula vazia, a busca por matrícula é suprimida (evita consulta por `""`; duplicata por e-mail preservada).
- **FR-007**: nenhum número de matrícula é fabricado no preview; a indicação de provisória é **permissiva** (remediação I1) — a flag `will_generate_provisional` é a sinalização disponível, sem mudança visual obrigatória no template atual.

### 2.4 `execute_custodian_import(rows, db, skip_duplicates=True) -> Dict` — assinatura igual

Comportamento por linha (somente o ramo de **criação nova** muda):

| Caso | Comportamento |
|---|---|
| Matrícula informada, nova | igual ao atual (cria com o valor normalizado) |
| Matrícula informada, duplicada | **igual ao atual**: skip (`skip_duplicates=True`) ou atualização in-place — nunca vira provisória (FR-004) |
| **Matrícula vazia (vazio/espaços/chave ausente)** | **gera `PROV-%06d` via `CustodianService.generate_available_provisional_code(db)` imediatamente antes de criar**; `db.flush()` seguinte (já existente) torna a provisória visível para as linhas seguintes → RV-3 (unicidade intra-importação) |
| E-mail duplicado (novo) | igual ao atual (skip/erro conforme `skip_duplicates`) |
| Exceção de linha | igual ao atual: `"Linha N: ..."` em `errors` + commit parcial |

- **Retorno**: shape inalterado (`imported`, `skipped`, `errors`, `total_processed`).
- **Transação**: `db.commit()` final igual ao atual; nenhum rollback novo.
- **Colisão concorrente**: cai no `except` existente do loop (erro "Linha N: ..." + commit parcial) — regra atual preservada (research R7).

---

## 3. Rotas e template

- **`app/web/routes.py`**: **INTOCADO** (o fluxo de 3 estágios chama os services como hoje — research R5).
- **`app/web/templates/custodians/import.html`**: somente textos de documentação (docstring do módulo do service espelha): `matricula` sai da lista de obrigatórias; badge "Sim"→"Não" + observação da regra; exemplo de CSV com linhas com e sem matrícula (research R9). Nenhum controle/fluxo alterado.

---

## 4. API pública do sistema

- **Nenhuma alteração de código**: o endpoint REST `POST /api/v1/custodians/import/csv` (`app/api/custodians_api.py:77`, permissão `colaboradores.criar`) consome `parse_custodian_csv` + `execute_custodian_import` e **herda a nova regra automaticamente**; as rotas web `/custodians/import` e `/custodians/import/confirm` mantêm método, permissão, formulários e respostas.

---

## 5. Contrato de testes (RF do briefing → casos)

| Teste | Cenário | Asserção mínima |
|---|---|---|
| T1 | matrícula informada `MAT-1045` | criado com `MAT-1045`; não é provisória |
| T2 | célula vazia | criado; `registration_code` casa `PROV-\d{6}`; sem erro de matrícula ausente |
| T3 | só espaços `"   "` | idem T2 (tratada como ausente) |
| T4 | coluna ausente do CSV | importação válida; todos com `PROV-*` |
| T5 | mista | informadas mantêm valor; ausentes recebem `PROV-*`; todos importados |
| T6 | informada duplicada | regra atual: skip ou update conforme `skip_duplicates`; sem substituição por provisória |
| T7 | várias sem matrícula | provisórias duas a duas distintas |
| T8 | regressão | suíte existente verde (única edição: teste que asserta o erro removido — research R10) |
