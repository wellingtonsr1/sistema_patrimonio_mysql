# Quickstart — Validação da Feature 062

**Pré-requisitos**: ambiente local funcionando (`.venv` com dependências; suíte verde no patamar **923 passed / 1 skipped / 0 failed**). Referências: [ui-contract.md](./contracts/ui-contract.md) (estado esperado dos selects) e [data-model.md](./data-model.md) (zero DDL).

## 1. Validação automatizada (régua principal)

```bash
# Suíte completa — deve permanecer 100% verde, SEM editar teste existente
python -m pytest

# Arquivo novo da feature (renderização dos 2 forms + não-mutação)
python -m pytest tests/test_departamento_destino_062.py -v
```

Esperado: suíte completa no patamar anterior **+ os testes novos** (nenhuma falha, nenhum skip novo). O arquivo novo deve cobrir (desenho em [ui-contract.md](./contracts/ui-contract.md) §1/§2/§5):

- **Renderização movimentação** (`GET /movements/new` com ≥2 unidades): opções dentro de `optgroup` por unidade; rótulo `Departamento (Unidade)`; `value` = id do local; `-- Manter Local Atual --` primeira, fora de grupo.
- **Renderização equipamento** (`GET /assets/new`): mesmas regras; `-- Estoque Central / Almoxarifado --` primeira, fora de grupo.
- **Não-mutação (US3)**: registrar `TRANSFERENCIA_LOCAL` escolhendo destino e provar que (a) o snapshot gravado está no formato atual `Unidade - Departamento (Nome)`; (b) `destination_location_id` = id escolhido; (c) registros pré-existentes na mesma sessão de teste permanecem intocados. (Reforça a régua já existente: `test_import_asset_movements.py` L134/L216.)

## 2. Smoke visual (prova de UX — AC-01/AC-02/AC-06)

1. Subir a aplicação local e autenticar com usuário com `movimentacao.criar` e `patrimonio.criar`.
2. **Antes**: (opcional, para o print comparativo) capturar o select de destino de `/movements/new` no estado atual.
3. **Depois**: abrir `/movements/new` e conferir:
   - grupos na ordem `Clube`, `IPMJP - Sede`, `Shoping` (+ grupo próprio do registro com travessão, se existir);
   - opções começando pelo departamento — ex.: `Divisão de Previdência (IPMJP - Sede)`;
   - `-- Manter Local Atual --` como primeira opção, fora de grupo.
4. Abrir `/assets/new` e conferir o mesmo padrão no select de Localização (com `-- Estoque Central / Almoxarifado --` preservada).
5. Registrar print antes/depois na validação (padrão da casa — `validacao.md` na fase de implementação).

## 3. Prova ponta a ponta de não-mutação (US3 — interface)

1. Registrar uma **Transferência de Setor** escolhendo um destino na nova lista (ex.: `Divisão de Previdência (IPMJP - Sede)`).
2. Abrir o histórico (`/movements`) e o detalhe do bem: o destino da movimentação **nova** aparece no formato de snapshot atual (`IPMJP - Sede - Divisão de Previdência (Sede - Divisão de Previdência)`) — idêntico ao das movimentações antigas.
3. Na busca de movimentações, pesquisar por "Divisão de Previdência" e por "IPMJP - Sede": a movimentação nova é encontrada pelos mesmos termos que encontrariam uma antiga.
4. Conferir que nenhum registro antigo mudou de texto (comparar com print/consulta prévia — os snapshots são imutáveis por construção; a prova automatizada é o teste do §1).

## 4. Critério de pronto

- [ ] Suíte completa verde sem edição de testes existentes (Princípio VIII).
- [ ] Testes novos cobrindo renderização (2 forms) e não-mutação (US3).
- [ ] Smoke visual conforme §2, com prints.
- [ ] `git status` sem alterações fora de: 2 templates, 1 arquivo de teste novo e os artefatos desta spec.
- [ ] `validacao.md` da feature escrito com os resultados (padrão da casa — criado na fase de implementação, não aqui).
