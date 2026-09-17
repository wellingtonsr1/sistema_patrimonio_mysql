# Quickstart — Validação da feature 012

**Feature**: 012-selecao-departamento-colaborador
**Objetivo**: provar, de ponta a ponta, que o Departamento/Setor do colaborador passou a ser seleção de valores oficiais (derivados de `Location.department`) validada no backend no caminho do formulário — **sem DDL e sem regressões**.

> Referências: [research.md](./research.md) (R1–R10 revisadas) · [data-model.md](./data-model.md) (RV-1..RV-7) · [contracts/](./contracts/) · spec (AC-01..AC-10).

---

## Pré-requisitos

1. Ambiente do projeto pronto (`requirements.txt` instalado; Python 3.10+).
2. Suíte executável: `pytest` (SQLite em memória via `tests/conftest.py`; sem MariaDB).
3. Para validação manual (opcional): `DATABASE_URL` MariaDB/MySQL de teste e `python run.py`, com **pelo menos um local cadastrado** (a lista oficial deriva de `locations.department` — banco sem locais → lista vazia; pré-condição operacional, research R1 trade-off 2).

---

## 1. Regressão — suíte existente permanece verde (FR-012, Constitution VIII)

```bash
pytest -q
```

**Esperado**: 100% dos testes existentes passando **sem nenhuma edição** — o caminho legado (texto livre) é preservado em API (10 POSTs: `test_api.py`, `test_rbac.py`, `test_custodian_provisional.py`, `test_custodian_import.py`), service (28 chamadas) e web (6 POSTs em `test_custodian_provisional.py`).

**Falha se**: qualquer teste existente precisar ser alterado, ou qualquer caminho legado começar a rejeitar texto que hoje aceita.

## 2. Testes novos da feature (US1–US4, AC-01..AC-10)

```bash
pytest tests/test_department_selection.py -q
```

**Esperado**: todos verdes. Cobertura mínima exigida:

| Bloco | Cenários |
|---|---|
| Fonte oficial (RV-1) | `list_official` retorna os distintos de `locations.department`, ordenados, sem nulos/vazios; criação/edição de **local** altera a lista no próximo render (derivação ao vivo — sem seed) |
| US1/AC-01, AC-02, AC-05 | GET do formulário renderiza **dropdown (campo de seleção)** com os oficiais; POST web com `department_source=official` + valor oficial → 303 e gravação do valor **canônico**; valor fora da lista → rejeitado; nenhum path do formulário cria denominação nova |
| Canonização (RV-2) | Submeter "SUPORTE" (variação de caixa de um oficial) → gravado como a forma canônica oficial; sem erro por caixa |
| US1/AC-03 (Cenário 2) | POST web sem seleção (vazio) → redirect com erro "Departamento/Setor é obrigatório"; nada gravado |
| US2/AC-04 (Cenário 3) | POST web **com marcador** e valor inexistente → redirect com erro "inválido"; nada gravado |
| Caminho legado (RV-5) | POST web **sem marcador** com texto arbitrário → comportamento atual (grava); POST API com `"TI"` → 201 (teste de caracterização da não-mudança — api-contract §3) |
| US3/AC-06 (Cenário 5) | Editar selecionando outro oficial → novo valor canônico gravado; mesma lista do cadastro |
| US4/AC-07 (Cenário 6) | Cadastro com matrícula vazia → `PROV-*` **e** seleção oficial funcionando juntos |
| US4/AC-08 | Colaborador com movimentação anterior → trocar departamento (formulário) → `movements`, `audit_logs`, termos anteriores **intactos** (assert de não-rewrita) |
| AC-09/FR-011 | `locations`, `locations.department` e o campo `role` inalterados (snapshot comparativo) |
| Q2/FR-014 (RV-6) | Colaboradores pré-existentes não são alterados por seed/carga (não existe seed) |

> **Nota (Q3/FR-015)**: a regra de bloqueio por inativos é **inoperante** nesta fonte (`Location` não possui ativo/inativo — research R9 revista; spec tornou a regra condicional). Não há cenário de teste para ela; a condicional está documentada em spec/clarificações.

## 3. Validação manual (opcional, com banco de demo contendo locais)

1. Subir o app e abrir **Cadastrar Colaborador** (`/custodians/new`).
   - **Esperado (AC-01)**: campo é um **dropdown (campo de seleção)**; opções = valores distintos de departamento dos **locais** cadastrados; nenhuma lista fixa no HTML (opções vêm do contexto server-side).
2. Tentar salvar sem selecionar.
   - **Esperado (AC-03)**: rejeição no servidor (alerta padrão; nada criado) — mesmo com `required` contornado no navegador.
3. Selecionar um valor oficial (ex.: "Tecnologia da Informação") e salvar.
   - **Esperado (Cenário 1/AC-05)**: colaborador criado exibindo o valor canônico na listagem/detalhe/relatório.
4. ~~Digitar variação de caixa~~ (suplantado — dropdown não aceita digitação; a canonização case-insensitive permanece garantida no backend por `ensure_official`).
5. Submeter via devtools um valor que não corresponde a nenhum oficial (com o marcador).
   - **Esperado (Cenário 3/AC-04)**: rejeição no servidor — "inválido — selecione um registro da lista oficial".
6. Editar o colaborador e trocar para outro oficial.
   - **Esperado (AC-06)**: troca aceita; **histórico de movimentações anterior inalterado** (AC-08).
7. ~~Pesquisar digitação parcial~~ (suplantado pela decisão de UX 2026-09-17 — dropdown sem campo de pesquisa; a lista completa é apresentada no controle).
8. Cadastrar deixando matrícula vazia (vira `PROV-*`) e selecionando departamento.
   - **Esperado (AC-07)**: cadastro normal; badge "provisória" da feature 010 intacta.
9. Cadastrar/editar um **local** com um departamento novo e reabrir o formulário de colaborador.
   - **Esperado**: o novo valor aparece na lista oficial (derivação ao vivo).

## 4. Definição de pronto (validação final — Constitution XII)

- [ ] Suíte completa verde (sem edição em testes existentes).
- [ ] Testes novos cobrindo todos os blocos da Seção 2.
- [ ] Zero DDL confirmado (`git diff` sem alteração em `app/models/`, `app/database.py`, `app/schemas/`, `app/api/`).
- [ ] Documentação atualizada (README/docs/ajuda — Princípio XI): comportamento do campo e regra da lista derivada de locais.
- [ ] Checklist da Constitution (plan.md) re-verificado.
