# Quickstart — Validação da Feature 063

**Pré-requisitos**: ambiente local funcionando (`.venv` com dependências; suíte verde no patamar **948 passed / 2 skipped / 0 failed**). Referências: [ui-contract.md](./contracts/ui-contract.md) (estado esperado do card flow-card) e [data-model.md](./data-model.md) (zero DDL).

## 1. Validação automatizada (régua principal)

```bash
# Suíte completa — deve permanecer 100% verde, SEM editar teste existente
python -m pytest

# Arquivo novo da feature (renderização da trilha + não-mutação)
python -m pytest tests/test_presentacao_trilha_063.py -v
```

Esperado: suíte completa no patamar anterior **+ os testes novos** (nenhuma falha, nenhum skip novo). O arquivo novo deve cobrir (desenho em [ui-contract.md](./contracts/ui-contract.md) §2/§4):

- **Renderização da trilha** (`GET /assets/{id}` com entrada + transferência entre locais padrão-de-produção): título = `department` nos pontos Origem/Destino; contexto `Sede • IPMJP - Sede`; snapshot cru formatado `IPMJP - Sede - Setor de Recadastramento (Sede - Setor de Recadastramento)` **ausente** do HTML; deduplicação no caso `name == department` (contexto reduz a `Clube`).
- **Não-mutação (US2)**: registrar `TRANSFERENCIA_LOCAL` escolhendo destino e provar que (a) o snapshot gravado está no formato atual `Unidade - Departamento (Nome)`; (b) `destination_location_id` = id escolhido; (c) a ENTRADA_AQUISICAO pré-existente permanece byte-a-byte idêntica; (d) a busca (Feature 049) encontra pelos mesmos termos. (Reforça a régua já existente: `test_import_asset_movements.py` L134/L216.)
- **Guardas de escopo**: dropdowns da 062 verdes sem edição (`test_departamento_destino_062.py`); seção "Custódia & Localização Atual" inalterada (assert de presença do bloco atual).

## 2. Smoke visual (prova de UX — AC01–AC04; spec §5 SC-006)

1. Subir a aplicação local e autenticar com usuário com `patrimonio.visualizar`.
2. **Antes**: capturar a seção "Trilha de Fluxo & Movimentações" de um equipamento com movimentações (formato duplicado atual).
3. **Depois**: abrir `/assets/{id}` e conferir:
   - Origem/Destino com o **Departamento/Setor** como linha principal — ex.: `Setor de Recadastramento` → `Divisão de Previdência`;
   - contexto `Localização • Unidade` — ex.: `Sede • IPMJP - Sede`;
   - colaborador e badges/tipo/termo/motivo como antes;
   - a seção "Custódia & Localização Atual" exatamente como antes.
4. Registrar print antes/depois no `validacao.md` (padrão da casa — criado na fase de implementação).

## 3. Prova ponta a ponta de não-mutação (US2 — interface)

1. Registrar uma **Transferência de Setor** escolhendo um destino na lista (dropdown 062 inalterado).
2. Abrir o histórico (`/movements`) e o detalhe do bem: a movimentação **nova** mantém o snapshot no formato atual (`IPMJP - Sede - Divisão de Previdência (Sede - Divisão de Previdência)`) — apenas a **exibição** na trilha muda para o novo padrão.
3. Na busca de movimentações, pesquisar por "Divisão de Previdência" e por "IPMJP - Sede": a movimentação nova é encontrada pelos mesmos termos que encontrariam uma antiga.
4. Conferir que nenhum registro antigo mudou de texto (snapshots imutáveis por construção; a prova automatizada é o teste do §1).

## 4. Critério de pronto

- [ ] Suíte completa verde sem edição de testes existentes (Princípio VIII).
- [ ] Testes novos cobrindo renderização da trilha e não-mutação (US1/US2).
- [ ] Smoke visual conforme §2, com prints.
- [ ] `git status` sem alterações fora de: 1 template (`assets/detail.html`), 1 arquivo de teste novo e os artefatos desta spec.
- [ ] `validacao.md` da feature escrito com os resultados (padrão da casa — criado na fase de implementação, não aqui).
