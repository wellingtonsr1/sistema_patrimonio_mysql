# Preserved Contracts — Contratos Congelados da Feature 070

A feature é de **apresentação**; os contratos abaixo são **réguas de regressão** — qualquer mudança neles falha a feature (spec FR-008/AC07/AC15/AC16/AC17).

| # | Contrato | Detalhe verificado | Régua de regressão |
|---|---|---|---|
| C1 | `MovementService.get_timeline_for_asset` | `movement_service.py` L410–473 — consulta, dedup (`MOVIMENTACAO`/`MANUTENCAO`/`CRIACAO`), desserialização tolerante, ordenação e teto de 50 | Arquivo **não editado**; `test_movements.py`, `test_import_asset_movements.py`, `test_departamento_destino_062.py` verdes |
| C2 | `GET /api/v1/assets/{asset_id}/timeline` | `assets_api.py` L78–130 — payload `{type, timestamp, data}`; audit com `previous_data`/`new_data` desserializados | `test_api.py` verde + teste novo comparando payload com/sem a feature (idêntico) |
| C3 | Gravação de auditoria | `write_audit`/`write_change_audit` (`audit_service.py`) — incluso o texto `"Campos alterados: …"` gerado em L289 | Arquivos **não editados**; nenhum teste de escrita alterado |
| C4 | Registros históricos | `audit_logs` byte-a-byte após renderização | Teste novo de não-mutação (query antes/depois do GET da página) |
| C5 | Painel "Alterações cadastrais" (067) | `get_cadastral_history` + bloco `id="historico-cadastral"` | `test_consulta_edicao_bens_067.py` verde sem edição |
| C6 | Cartões de movimentação (063/064) | Bloco `{% else %}` do loop + macros `locations.html` | `test_presentacao_trilha_063.py` + `test_fluxo_global_064.py` verdes sem edição |
| C7 | Permissões e autenticação | Rota `GET /assets/{id}` com `require_permission("patrimonio.visualizar")`; nenhum dado novo buscado | Sem mudança de rota; `test_rbac.py`/`test_consulta_edicao_bens_067.py` verdes |
| C8 | Datas (Feature 004) | Exibição via filtro `localtime` (UTC → America/Recife) | `test_datetime_flows.py` verde |
| C9 | Banco de dados | Zero DDL, zero migração | Nenhum arquivo em `migrations/` tocado |
| C10 | Demais consumidores da auditoria | `/admin/audit`, dashboard, relatórios, exportações, CSV/Excel/PDF | Fora do escopo — nenhum arquivo tocado |

**Nota — Implementação permitida**: `app/services/asset_service.py` (novo método somente-leitura), `app/web/routers/assets.py` (aplicação do helper em `view_asset_detail` — ~3–10 linhas no contexto) e `app/web/templates/assets/detail.html` (ramo de auditoria). Nada além disso sem atualizar este contrato e a spec.
