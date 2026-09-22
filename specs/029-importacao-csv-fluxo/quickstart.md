# Quickstart: Validação da feature 029 — importação CSV × Fluxo patrimonial

**Feature**: 029-importacao-csv-fluxo | **Date**: 2026-09-21

Guia de validação ponta a ponta. Pré-requisitos: venv do projeto ativo
(`source .venv/bin/activate`; se o TestClient reclamar de `httpx2`, é ambiente —
`pip install httpx2`), banco de teste SQLite em memória via fixtures.

## 1. Suíte de regressão (gate obrigatório)

```bash
python -m pytest tests/ -q
```

**Esperado**: baseline desta sessão **565 passed / 0 failed** + os novos testes de
`tests/test_import_asset_movements.py` (cenários A–L) — todos verdes, nenhuma falha
pré-existente introduzida. Nenhum teste existente é modificado:
`tests/test_import_asset_location.py` permanece integral (o comportamento de erro para
local inexistente já é o exigido pela FR-013).

```bash
python -m pytest tests/test_import_asset_movements.py tests/test_import_asset_location.py tests/test_movements.py -q
```

**Esperado**: 100% verdes.

## 2. Cenário manual ponta a ponta (produção/staging)

Pré-requisitos: usuário com permissão `patrimonio.criar`; colaborador cadastrado
(ex.: `Mariana Souto Soares`); local cadastrado (ex.: `Divisão de Previdência`).

### 2.1 CSV de teste

```csv
tombamento;equipamento;categoria;Custodiante;localização
TESTE029A;Computador;DESKTOP;Mariana Souto Soares;Divisão de Previdência
TESTE029B;Monitor;MONITOR;;Divisão de Previdência
TESTE029C;Impressora;PRINTER;Mariana Souto Soares;
TESTE029D;Teclado;OTHER;;
```

### 2.2 Passos

1. Login com usuário autenticado (anote o nome de exibição — será o operador).
2. Menu **Equipamentos & Bens → Importar CSV** → enviar o arquivo → revisar preview → confirmar.
3. Resultado esperado na tela: 4 importados, 0 ignorados, 0 erros.
4. Abrir cada bem (`/assets/{id}`) e conferir a **Trilha de Fluxo & Movimentações**:
   - **TESTE029A**: movimentação `ENTRADA_AQUISICAO` (destino = Divisão de Previdência) **e** movimentação `ALOCACAO_CAUTELA` (destino = Mariana Souto Soares + local), com **código de termo `TR-2026-XXXXX` sequencial** (nunca `TR-CSV-...`), **operador = usuário logado**, status do bem `EM USO`.
   - **TESTE029B**: apenas `ENTRADA_AQUISICAO` com o local de destino; status `DISPONÍVEL`; **nenhuma alocação**.
   - **TESTE029C**: `ENTRADA_AQUISICAO` (destino "Estoque Central") + `ALOCACAO_CAUTELA` (colaborador, sem local de destino — o bem fica com local do estoque até nova transferência); status `EM USO`.
   - **TESTE029D**: apenas `ENTRADA_AQUISICAO`; status `DISPONÍVEL`; sem custodiante, sem local.
5. **Termo de responsabilidade**: abrir o termo da `ALOCACAO_CAUTELA` de TESTE029A — dados do bem e do colaborador corretos, operador = usuário logado.
6. **Reimportação idêntica**: importar o mesmo arquivo novamente com "ignorar duplicatas" **desmarcado** → nenhuma movimentação nova nos 4 bens; histórico idêntico ao anterior (contagem de movimentações inalterada).
7. **Reimportação com mudança**: CSV com `TESTE029A` apontando outro colaborador (ex.: `Micael de Araújo Silva`) → nova `ALOCACAO_CAUTELA` no Fluxo; movimentação anterior intacta.
8. **Erro de linha**: CSV com colaborador inexistente (`Custodiante = Fulano Inexistente`) → resultado exibe `Linha X: colaborador 'Fulano Inexistente' não encontrado no cadastro de colaboradores`; bem **não** é criado; demais linhas importam.
9. **Auditoria**: em Relatórios → Trilha de Auditoria, constata-se o evento `IMPORTACAO` (Patrimônio/Asset) das operações — independente das movimentações.

### 2.3 Verificação da API (opcional)

```bash
curl -s -H "Cookie: session=<sessão válida>" \
  "http://localhost:8000/api/v1/assets/<id>/timeline" | python -m json.tool
```

**Esperado**: as movimentações criadas pela importação aparecem na timeline
(mesma consulta do Fluxo — SC-004), sem qualquer alteração nesse endpoint.

## 3. Checklist de não regressão visual (rápido)

- Cadastro manual de bem (com alocação inicial) → Fluxo com `ENTRADA_AQUISICAO` como antes.
- Movimentação manual (alocação/transferência/devolução) → funciona como antes, termo sequencial.
- Importação de colaboradores e de locais → intocadas.
- Inventário → intocado (não altera cadastro).
- Exportações CSV/Excel/PDF → intocadas.

> Este guia valida comportamento; detalhes de implementação estão em
> [contracts/service-contract.md](./contracts/service-contract.md) e
> [research.md](./research.md). A decomposição em tarefas será gerada por
> `/speckit-tasks` (tasks.md).
