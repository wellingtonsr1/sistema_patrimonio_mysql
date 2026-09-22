# Phase 1 Contracts: Registrar no Fluxo as movimentações da importação CSV de equipamentos

**Feature**: 029-importacao-csv-fluxo | **Date**: 2026-09-21

Contratos dos pontos de integração afetados. Nenhum endpoint novo; nenhuma quebra de
assinatura existente (parâmetros novos são opcionais).

## C1 — `import_service.parse_csv(content) -> (rows, errors)` (contrato atual PRESERVADO)

- Comportamento atual mantido integralmente (aliases, delimitador, validações).
- **Novidade**: `_normalize_column_name` reconhece a coluna de custodiante via novas
  entradas em `COLUMN_ALIASES`, normalizadas para a chave canônica `custodiante`:
  - `custodiante`, `custodian`, `colaborador`, `responsavel`, `responsável`
    (e variações com espaço/underline — o normalizador existente trata espaços→underscore
    e acentos).
- Linhas continuam saindo como `dict` com chaves canônicas; a chave `custodiante`
  contém o texto da célula (str.strip() aplicado, padrão das demais colunas).

## C2 — `import_service.execute_import(rows, db, skip_duplicates=True, operator_name=None) -> Dict`

Assinatura: `operator_name` é **novo e opcional** (default `None`). Retorno e efeitos:

### Retorno (contrato atual PRESERVADO)

```python
{
  "imported": int,          # linhas criadas ou atualizadas com sucesso
  "skipped": int,           # duplicatas puladas (skip_duplicates=True)
  "errors": [str],          # mensagens por linha, ex.: "Linha 5: colaborador 'X' não encontrado no cadastro de colaboradores"
  "total_processed": int,   # imported + skipped + len(errors)
}
```

### Parâmetro `operator_name` (FR-005)

- `None` (omisso — chamadas antigas/testes): fallback de compatibilidade `"Importação CSV"` (o default atual do parâmetro passa a `None`).
- Rotas web/API: **sempre** `full_name` do usuário autenticado (`request.state.user`), ou `username` quando `full_name` for vazio. Jamais "Sistema", jamais o colaborador do CSV.

### Fluxo interno por linha (unidade transacional — FR-019/K)

1. Resoluções (falha → `errors.append`, rollback da linha, `continue`):
   - local pelo nome (`LocationService.get_by_name`) — inexistente = erro (FR-013, comportamento atual já conforme — sem alteração);
   - custodiante: precedência por `registration_code` quando o CSV informar matrícula; senão `Custodian.name` com match exato (ilike) **com `order_by(Custodian.id)`** para determinismo entre bancos em nomes duplicados (R2, remediação C1 do analyze) — inexistente = erro (FR-012).
2. Duplicata por `tag` (`skip_duplicates=True` → `skipped += 1`).
3. **Criação** (bem novo):
   - `Asset` com `status=AVAILABLE`, **sem** `custodian_id`;
   - movimentação de entrada `ENTRADA_AQUISICAO` construída no service (padrão do
     cadastro manual — research R1): origem real ("Fornecedor / Entrada Inicial" /
     "Almoxarifado Geral"), destino = local do CSV ou "Estoque Central", `operator_name`
     do parâmetro, termo `TR-INIC-{ano}-{id}`;
   - `db.flush()`;
   - **custódia**: se CSV informa custodiante → `MovementService.create_movement(db, MovementCreate(...))` com tipo de `resolve_movement_type(None, None, location_id, custodian_id)` (sempre `ALOCACAO_CAUTELA` para bem novo com custodiante) e `generate_term=True` → status `IN_USE`, termo `TR-{ano}-{seq:05d}` (FR-007);
   - `db.commit()` da linha; erro → `db.rollback()` + report.
4. **Atualização** (reimportação, `skip_duplicates=False`):
   - campos cadastrais como hoje (D3/research);
   - **custódia**: `type = MovementService.resolve_movement_type(asset.location_id, asset.custodian_id, csv_location_id, csv_custodian_id)`; `None` → nenhuma movimentação (FR-015); senão `create_movement(...)` (FR-016);
   - CSV sem custodiante = manter custódia atual (R4 — sem devolução fabricada);
   - commit da linha / rollback da linha como acima.
5. Exceção de `create_movement` (ex.: validação da matriz, bem baixado) → rollback da
   linha + `errors.append("Linha {i}: {msg}")` — sem estado parcial (K).

## C3 — `MovementService.resolve_movement_type(current_location_id, current_custodian_id, dest_location_id, dest_custodian_id) -> Optional[MovementType]` (NOVO, estático, puro)

- **Entrada**: ids efetivos (ou `None`) de local/custodiante atuais e de destino.
- **Saída**: tipo de movimentação a executar, ou `None` quando não há mudança efetiva.

| current_location × dest_location | current_custodian × dest_custodian | resultado |
|---|---|---|
| iguais (inclusive ambos None) | iguais (inclusive ambos None) | `None` |
| iguais | diferentes (destino não None) | `ALOCACAO_CAUTELA` |
| diferentes | iguais (não None) | `TRANSFERENCIA_LOCAL` |
| diferentes | diferentes (destino não None) | `ALOCACAO_CAUTELA` (VAL-007 — entrega com termo) |
| sem custodiante atual (estoque) → destino com custodiante | — | `ALOCACAO_CAUTELA` |
| com custodiante atual → destino sem custodiante | — | **fora de escopo do CSV** (devolução é manual — R4); comportamento: `None` apenas se local também não mudar; se local mudar e custodiante destino for None, devolve `TRANSFERENCIA_LOCAL` apenas quando o chamador confirma preservação de custódia — no importador, destino sem custodiante em reimportação NUNCA chama o motor para custódia (R4) |

- **Sem DB, sem efeitos colaterais**; não substitui as validações de `create_movement`
  (o motor continua validando/executando — o método apenas decide o tipo).
- `create_movement` permanece **INTOCADO** (nenhuma mudança de assinatura, validações
  VAL-002..VAL-008, geração de termo, snapshots e commit).

## C4 — Rotas (nenhuma rota nova; mudança = repasse do operador)

### Web `POST /assets/import/confirm` (`web/routes.py confirm_import_assets`)

- Continua: upload/preview em 2 passos, permissão `patrimonio.criar`, render do resultado.
- Muda: chama `execute_import(rows, db, skip_duplicates=skip_duplicates, operator_name=_display_name(request.state.user))` onde `_display_name(u) = u.full_name or u.username`.
- Continua: `write_audit(ACTION_IMPORT, ...)` após a execução (intocado — R9).

### API `POST /api/v1/assets/import/csv` (`api/assets_api.py import_csv_api`)

- Continua: `UploadFile` + `skip_duplicates` (Form), permissão `patrimonio.criar`, mesmo JSON de retorno (+`parse_errors`).
- Muda: `operator_name` repassado como acima.
- Continua: `write_audit(ACTION_IMPORT, ...)` após a execução (intocado — R9).

### Fluxo (INTOCADO — C2.6 da spec)

- `MovementService.get_timeline_for_asset`, tela de detalhe do bem e
  `GET /api/v1/assets/{id}/timeline` — **nenhuma alteração** (a movimentação persistida
  pela importação é recuperada pela consulta existente — SC-004/L).

## C5 — Contrato de erros por linha (mensagens)

| Situação | Mensagem (padrão "Linha {i}: ...") |
|---|---|
| local inexistente | `Linha {i}: local '{x}' não encontrado no cadastro de locais` (atual) |
| colaborador inexistente | `Linha {i}: colaborador '{x}' não encontrado no cadastro de colaboradores` (novo) |
| falha do motor (matriz/bem baixado) | `Linha {i}: {mensagem do ValueError do create_movement}` |
| sem mudança efetiva na reimportação | linha processada sem movimentação — **não é erro** |
