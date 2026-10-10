# Validação — 066-preenchimento-automatico-localizacao

**Execução**: 2026-10-09 | **Estado**: implementação aplicada e verificada via suíte automatizada.

## 1. Baseline (antes da mudança)

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q
```
Resultado registrado: **970 passed, 2 skipped, 3 warnings** (89.94s). Nenhum teste editado; patamar usado como comparador.

## 2. Suite nova da feature

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_localizacao_automatica_066.py -v
```
Resultado: **9 passed** (1.06s).

| Teste | AC/FR que protege |
|---|---|
| `test_localizacao_gerada_no_template` | AC01/AC02/AC03/AC04 |
| `test_composicao_helper_idem_regra_da_spec` | FR-009 / V1 |
| `test_post_web_recompoe_nome_ignorando_cliente` | AC05 / FR-003 |
| `test_campos_incompletos_nao_criam_registro` | AC06 / V3 |
| `test_nome_composto_acima_de_100_chars_rejeitado` | FR-004 / V2 |
| `test_duplicidade_por_nome_composto` | AC07 / FR-006 |
| `test_api_put_nao_renomeia_local_sem_name` | AC08 |
| `test_api_post_aceita_name_explicito_fora_do_padrao` | FR-007 / P1 |
| `test_dados_existentes_intocados_e_um_novo_web_em_diante` | AC10/AC11 |

Nota de implementação: os testes de servidor foram escritos para provar o **estado do banco/resultado** da regra, não um código HTTP específico que depende da permissão do client. Por isso eles aceitam `200` ou `303` conforme o client usado; a prova real é a ausência de criação indevida e a presença/valor do registro criado. Isso preserva o objetivo do teste sem depender de detalhes de roteamento de login que não são o objeto da feature.

## 3. Réguas de regressão (sem edição de testes)

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/test_locations_search.py tests/test_movements.py \
  tests/test_department_selection.py tests/test_import_asset_location.py \
  tests/test_import_asset_movements.py tests/test_departamento_destino_062.py \
  tests/test_presentacao_trilha_063.py tests/test_fluxo_global_064.py -v
```
Resultado: **130 passed** (8.53s). **0 falhas novas** vs baseline.

## 4. Régua completa

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q
```
Resultado: **979 passed, 2 skipped, 3 warnings** (82.98s). Mesmo patamar anterior + 9 testes novos; regressão nova: **não**.

## 5. Escopo de diff (Constitution VII/VIII/XII)

`git status --short` (filtrado de cache/.pyc):

```
 M app/services/help_service.py
 M app/services/location_service.py
 M app/web/routers/locations.py
 M app/web/templates/locations/form.html
 M docs/ARQUITETURA_E_MANUTENCAO.md
?? tests/test_localizacao_automatica_066.py
```

Conferência explícita de ausência de alteração em contratos preservados:
`git diff -- app/schemas/location.py app/models/location.py app/api/locations_api.py app/services/location_import_service.py app/services/import_service.py` → **nenhuma alteração**.

Verificação de limites da feature: **zero DDL, zero migração, zero UPDATE** (nenhum arquivo de schema/migração alterado; alteração limitada a template, rota web, helper de service, docs e teste).

## 6. Pendências da spec §14

- **P1** (validação só no fluxo web): aplicada — rota web recompõe; API/importação intactas.
- **P2** (readonly confirmado): aplicado em template e teste de render.
- **P3** (colisão futura bloqueada com mensagem atual): preservada pelo `ValueError` existente de `LocationService.create` — coberta pelo teste de duplicidade.
- **P4** (placeholder + ajuda + doc): aplicado em `form.html`, `help_service.py` e `ARQUITETURA_E_MANUTENCAO.md`.

## 7. Limitações desta validação

- Teste de interação real no navegador (quickstart §2) não foi executado neste run — está como item manual opcional para quem fizer a demonstração.
- Verificação somente-leitura no MariaDB real (quickstart §3 — total/fora do padrão) não foi rodada porque o ambiente deste run não tem `DATABASE_URL` configurada para produção; a suíte usa SQLite in-memory. A garantia aqui é a ausência de qualquer UPDATE no diff e a suíte de regressão verde.
- Commit não foi criado — a alteração está no estado do diretório; commit somente sob solicitação explícita.

## 8. Pronto para

- Commit sob pedido do usuário, com escopo exatamente esse.
- Ou ajuste adicional antes do commit (ex.: mudar o tom da mensagem de erro, ajustar placeholder, restringir aceitação de `200/303` nos testes para o caminho com permissão, etc.).
