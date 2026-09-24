# Quickstart: Inventário — Remover colaborador responsável do snapshot (feature 034)

Guia de validação ponta a ponta. Referências: [contract](contracts/inventario-ata-contract.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`.venv/bin/python run.py`); usuário com
  `inventario.criar` + `inventario.conferir` + `inventario.visualizar` +
  `relatorios.exportar` (permissões existentes — nenhuma nova).
- Suíte de regressão: `.venv/bin/python -m pytest tests/ -q` (deve permanecer 100% verde).

## Cenários de validação

### V1 — Snapshot sem colaborador (US1)

1. Garanta um bem com colaborador cadastrado e outro sem, no mesmo local.
2. **Inventários** → criar inventário com esse local no escopo.
3. Esperado: lista de bens esperados com tombamento e local esperado; **sem** qualquer
   referência a colaborador/responsável (nem para o bem que tem custodiante).
4. Bem sem colaborador entra normalmente (nenhuma exigência de custódia).

### V2 — Conferência: responsável não é critério (US2)

1. Entre no inventário novo → conferir um item cujo bem tem colaborador cadastrado.
2. Esperado: tela de conferência **sem** "Colaborador esperado:".
3. Registre **Encontrado** no local esperado → resultado ENCONTRADO (conforme),
   mesmo com o responsável sendo outro ou inexistente no cadastro.
4. Ainda na tela do inventário: cards dos itens **sem** a linha de colaborador esperado.
5. Registre um item em **local diferente** → divergência LOCAL_DIFERENTE continua
   sendo gerada; o cadastro do bem não é alterado.

### V3 — Ata: novo sem coluna, legado com histórico (US2/US3 · H-2)

1. No inventário NOVO (encerrado ou em andamento): exportar CSV, Excel e PDF →
   **nenhuma** das três contém a coluna "Responsável Esperado".
2. Em um inventário criado ANTES da mudança (com histórico): exportar a ata →
   a coluna está presente com os valores gravados ("Estoque / Livre" nos itens sem
   custodiante) — histórico comprobatório preservado (H-2).

### V4 — Inventário legado íntegro (US3)

1. Abra um inventário anterior à mudança: consulta dos itens íntegra; se houver itens
   pendentes, conferir e encerrar funciona normalmente.
2. Verifique no banco (information_schema) que `inventario_itens.expected_custodian_name`
   continua existindo e com os dados históricos (H-1 — nenhuma migração executada).
3. Pacote offline de um inventário **legado** (feature 033): o payload **não** contém
   `expected_custodian_id`/`expected_custodian_name` (H-3 — remoção global no pacote).

## Automação (pytest — backend)

`.venv/bin/python -m pytest tests/test_inventario.py -q` cobre:
snapshot sem colaborador; responsável diferente sem divergência; bem sem responsável;
divergência de local; imutabilidade do snapshot; inventário não altera cadastro;
ata sem coluna (novo) e com coluna (legado) nos 3 formatos; inventários legados
consultáveis. Suíte completa: `.venv/bin/python -m pytest tests/ -q`.
