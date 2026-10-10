# Contract — Contratos PRESERVADOS (não alterados pela feature 067)

**Feature**: 067-consulta-edicao-bens | **Data**: 2026-10-10 | **Decisões P1–P5**: aprovadas em 2026-10-10 (spec §14 / Clarifications)

Esta feature **adiciona** um fluxo web de edição e complementa a tela de detalhes. Tudo o que já existe e é correto permanece com o **mesmo contrato**. Abaixo, o que é garantido e como é verificado.

| # | Contrato preservado | Garantia | Verificação prevista |
|---|---|---|---|
| 1 | **`PUT /api/v1/assets/{id}`** (`patrimonio.editar`) | Mesmos campos de `AssetUpdate`, mesma resposta `AssetRead`, mesmos códigos (404 inexistente, 400 para `ValueError`). As validações novas vivem no **service** e a API já converte `ValueError` em `400` (research R3) — **sem** novo `422` e **sem** restrição adicionada ao schema. *Nota*: a validação nova de valor negativo pode transformar um `200` anterior em `400` — mudança controlada listada abaixo, não mudança de mapeamento de códigos | `test_put_api_mantem_contrato` (payload atual continua aceito e audita before/after) + `test_put_api_grava_operador_autenticado_na_condicao` (a rota passa o operador autenticado — mudança controlada da tabela abaixo) |
| 2 | **`GET /api/v1/assets`** e **`GET /api/v1/assets/{id}`** (`patrimonio.visualizar`) | Respostas `AssetRead` inalteradas; `AssetService.get_all`/`get_by_id` inalterados | réguas `test_api.py` |
| 3 | **`GET /api/v1/assets/tag/{tag}`** | Resolução por tombamento com `strip().upper()` inalterada | réguas `test_api.py` |
| 4 | **`GET /api/v1/assets/{id}/timeline`** | Payload inalterado — **`MovementService.get_timeline_for_asset` não é modificado** (o histórico cadastral usa leitura nova e separada, research R6) | réguas 063/064 + `test_api.py` |
| 5 | **`GET /api/v1/assets/{id}/depreciation`** | Cálculo linear 20%/ano inalterado | `test_assets.py` |
| 6 | **`POST /api/v1/assets`** e **`POST /assets/new`** (cadastro) | Fluxo de criação, movimentação `ENTRADA_AQUISICAO`, `term_code` e validações de tombamento/série inalterados | `test_assets.py`, réguas de importação |
| 7 | **Movimentações** (`MovementService.create_movement` e rotas `/movements*`) | Motor intocado; a edição cadastral **não** oferece atalho para localização/custódia/situação; snapshots de origem/destino intactos | `test_movements.py`, `test_presentacao_trilha_063.py`, `test_fluxo_global_064.py` |
| 8 | **Custódia e localização** | Somente pelo fluxo de movimentação (`tag`/`status`/`location_id`/`custodian_id` fora do schema de edição) | `test_edicao_ignora_campos_protegidos_manipulados` |
| 9 | **Inventário** | Nenhuma escrita em `inventarios`/`inventario_itens`; lista esperada (`expected_*`) e resultados intactos; ata exportável inalterada | réguas de inventário + `test_historico_*`; leitura viva de `tag`/`name`/`category` **mantida por decisão P5 aprovada** (dívida M-003) |
| 10 | **Relatórios, CSVs, Excel, PDF** | `report_service.py` **não** é alterado; contratos de colunas e cabeçalhos permanecem | réguas de relatórios/exportação |
| 11 | **Termos e documentos** | Snapshots de movimentação congelados; nada regravado | `test_movements.py` |
| 12 | **Importação CSV de bens** (`/assets/import*`, `POST /api/v1/assets/import/csv`) | Upsert por tombamento inalterado; como o tombamento é imutável nesta feature (P1 aprovada), a chave de dedupe permanece estável | `test_import_asset_location.py`, `test_import_asset_movements.py` |
| 13 | **Permissões e perfis** | Nenhuma permissão nova, nenhum perfil novo, nenhuma alteração no `PERMISSION_CATALOG`/`DEFAULT_ROLES`; `patrimonio.excluir` continua reservada | `test_rbac.py` |
| 14 | **Auditoria** | Trilha única (`audit_logs`), imutável, sem rota de escrita/exclusão; eventos de autenticação/movimento/importação inalterados; credenciais nunca registradas | `test_rbac.py` (auditoria de mutação e acesso negado) |
| 15 | **Inventário de rotas (feature 051)** | `tests/route_manifest.json` **atualizado** com as rotas novas; nenhuma rota existente removida/renomeada | `tests/test_route_inventory.py` |
| 16 | **Banco de dados** | Zero DDL, zero migração, zero backfill, zero `UPDATE` em massa — apenas a atualização do bem editado | revisão de diff + suíte |
| 17 | **Comportamento das telas existentes** | Listagem, busca/filtros, etiquetas, dashboard e central de ajuda continuam funcionando; mudanças limitadas ao detalhe (+ ação de editar) e ao formulário de edição | réguas + `quickstart.md` |

## Comportamentos internos que mudam de forma **controlada** (não são contrato)

| Comportamento | Antes | Depois | Justificativa |
|---|---|---|---|
| Operador da movimentação `ATUALIZACAO_ESTADO` gerada por mudança de condição | `"Sistema"` (hardcoded) | Usuário autenticado (`full_name` ou `username`) | Padrão da feature 065 (operador responsável autenticado) — FR-012 |
| Atomicidade alteração + auditoria | dois `commit` separados | uma transação | FR-015/AC11 |
| Validação de `purchase_value` negativo / limites de texto na edição | aceito e gravado | recusado com `ValueError` (API: `400`; web: mensagem amigável) | FR-006/AC04 |
| Chamadas diretas a `AssetService.update` / `write_audit` sem os novos parâmetros | `commit` imediato | **idêntico** (default `commit=True`, `operator_name=None`) | Constitution I — nenhum comportamento existente alterado |
| Ata de inventário / CSV de movimentações (leitura viva de `tag`/`name`/`category`) | leitura viva | **leitura viva** (sem alteração) | Decisão **P5 aprovada** nesta feature; snapshots remetidos à dívida **M-003** |
