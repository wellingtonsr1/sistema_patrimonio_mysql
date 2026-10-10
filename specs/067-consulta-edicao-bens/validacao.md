# Validação — 067-consulta-edicao-bens

**Execução**: 2026-10-10 | **Estado**: **implementação completa** — Fases 1 e 2 (T001–T005), US1 (T006–T009), US2 (T010–T015 + T027), US3 (T016–T019) e Polish (T020–T026, T028) aplicadas e verificadas. Suíte final **1005 passed / 2 skipped** (baseline 979).

## 1. T001 — Baseline (antes da mudança)

```bash
.venv/bin/python -m pytest -q
```

Resultado registrado: **979 passed, 2 skipped, 3 warnings** (85,45s) — `exit=0`. Nenhum teste editado; patamar usado como comparador da validação final.

## 2. T002 — Conferência somente-leitura dos fatos da spec §1

Todos os cinco fatos **confirmados** (nenhuma divergência → não houve parada):

| # | Fato da spec §1 | Situação |
|---|---|---|
| a | `AssetUpdate` não contém `tag`/`status`/`location_id`/`custodian_id` | confirmado (schema com campos cadastrais editáveis apenas) |
| b | `AssetService.update` grava operador `"Sistema"` ao mudar `condition` | confirmado (literal no bloco da movimentação `ATUALIZACAO_ESTADO`) |
| c | `write_audit`/`write_change_audit` fazem `commit` interno | confirmado (`db.commit()` + `db.refresh()` incondicionais) |
| d | `tests/test_route_inventory.py` compara rotas com `tests/route_manifest.json` | confirmado |
| e | `assets/detail.html` não exibe `notes` nem `updated_at` | confirmado (0 ocorrências de `asset.notes` / `asset.updated_at`) |

## 3. Fase Foundational — T004 (`audit_service.py`) e T005 (`asset_service.py`)

Escopo aplicado exatamente conforme as tarefas:

- **T004**: parâmetro **aditivo** `commit: bool = True` em `write_audit` e em `write_change_audit` (propagado ao primeiro). `commit=True` → `db.commit()` + `db.refresh(entry)` (comportamento anterior intacto); `commit=False` → `db.flush()` apenas.
- **T005**: `AssetService.update(db, asset_id, data, *, operator_name=None, change_reason=None, expected_updated_at=None, commit=True)`, com V1 (nome não vazio), V2 (limites 150/100/100/100/100/150), V3 (`purchase_value >= 0`), V4 (unicidade de `serial_number` ignorando o próprio `id`), V9 (`AssetService.edit_changes` — sinal explícito de "nada mudou"), V10 (`AssetEditConflictError` por `updated_at`, precisão de segundo), V11 (`AssetNotEditableError` para bem `BAIXADO`); na movimentação de `condition`, `operator_name`/`change_reason` informados com fallback preservado (`"Sistema"` / motivo padrão). `create`/`get_all`/`get_by_id`/`calculate_depreciation` **não tocados**.

### 3.1 Verificação de comportamento (harness temporário)

Executado um harness temporário `tests/test_tmp_067_foundational.py` (10 asserções): operador autenticado + motivo na movimentação de condição, fallback `"Sistema"` sem parâmetros, `commit=False` desfeito por `rollback` do chamador (bem e trilha de auditoria), `commit=True` persistindo, V1/V2/V3 com limites exatos ainda aceitos, V10 (data divergente recusa / data correta passa), V11 (`BAIXADO` recusa), V9 (`edit_changes` vazio quando nada muda), serial duplicado recusado e limpeza de serial em dois bens sem colidir com a unicidade.

Resultado: **10 passed** (`exit=0`).

> **Nota de honestidade**: o harness foi **temporário e removido** ao final — a cobertura permanente desses comportamentos é atribuída à **T014** (`tests/test_assets.py`), que ainda não foi executada. Portanto esta rodada **não deixa suíte nova**; a verificação acima serve como evidência de que a camada de serviço se comporta como a spec exige.

## 4. Régua de regressão (sem edição de testes)

```bash
.venv/bin/python -m pytest -q
```

Depois da fase Foundational: **979 passed, 2 skipped, 3 warnings** (85,45s) — `exit=0`. Mesmo patamar do baseline, **0 falhas novas**. Esta é a régua relevante da fase: `AssetService.update` e as funções de auditoria são compartilhadas (web, API, movimentações, importação, AD, usuários).

Depois da US1 (T006–T009): **983 passed, 2 skipped, 3 warnings** (86,66s) — `exit=0` = baseline 979 + 4 testes novos; **0 falhas novas** (após corrigir o achado de hermeticidade relatado em §6.1).

## 5. Escopo de diff (Constitution VII/VIII/XII)

```
 M app/services/asset_service.py
 M app/services/audit_service.py
 M docs/Melhorias_SisPatrimonio_Pro.md
?? specs/067-consulta-edicao-bens/
```

Verificação explícita de ausência de alteração em artefatos preservados:

```bash
git diff -- app/schemas/ app/models/ app/api/ app/web/ tests/ migrations/
```

→ **nenhuma alteração**. Zero DDL, zero migração, zero schema novo; nenhum teste editado; nenhum commit criado.

## 6. US1 — Consulta detalhada (T006–T009)

**Testes (T006/T007)** — `tests/test_consulta_edicao_bens_067.py` (novo):

| Teste | AC/FR |
|---|---|
| `test_detalhe_exibe_dados_completos` | AC01/AC02 (todos os campos, incl. `notes` e `updated_at`) |
| `test_detalhe_omite_campos_vazios` | AC02 (nada de dado fictício) |
| `test_detalhe_404_bem_inexistente` | FR-003 |
| `test_detalhe_403_sem_permissao` | AC07 (sem `patrimonio.visualizar`) |

Ciclo TDD observado: **RED** com o template anterior (`test_detalhe_exibe_dados_completos` falhava por ausência de observações/última atualização; os 3 demais já passavam como guardas), **GREEN** após a alteração do template.

**Implementação (T008)** — `app/web/templates/assets/detail.html`: card condicional **Observações** (`asset.notes`, `white-space:pre-line`, ausente quando vazio) e linha **Última atualização cadastral** (`asset.updated_at` com filtro `localtime`). Campos vazios permanecem como "não informado"/`-`: nenhuma seção nova quando não há conteúdo. Nenhum bloco existente foi redesenhado.

**T009** — `pytest tests/test_consulta_edicao_bens_067.py -k detalhe` → **4 passed** (`exit=0`).

### 6.1 Achado corrigido durante a rodada

O arquivo novo importava `from tests.conftest import TEST_PASSWORD`, o que **reexecuta o conftest como segundo módulo** (`tests.conftest`) e sobrescreve `app.main.SessionLocal` — quebrando `tests/test_hermeticidade_suite.py::test_sessionlocal_do_main_aponta_para_banco_de_teste` (1 failed / 982 passed na primeira rodada completa). Corrigido para o padrão da casa `from conftest import TEST_PASSWORD` (conforme o comentário do próprio `test_hermeticidade_suite.py`); a suíte voltou a **983 passed / 2 skipped** (`exit=0`). O comentário explicativo foi mantido no arquivo de teste.

## 7. US2 — Edição controlada (T010–T015, T027)

**Testes (T010)** — 14 testes acrescentados a `tests/test_consulta_edicao_bens_067.py` (todos **RED** antes da implementação):

| Teste | AC/FR |
|---|---|
| `test_editar_bem_sem_permissao_nega_e_audita` | AC07 (403 em GET/POST + `ACESSO_NEGADO` na trilha) |
| `test_editar_formulario_pre_preenchido_sem_campos_protegidos` | §4.3 (pré-preenchido; `expected_updated_at`; sem `tag`/`status`/`location_id`/`custodian_id`) |
| `test_editar_bem_autorizado_atualiza_mesmo_registro` | AC03/AC05 (mesmo `id`, contagem inalterada) |
| `test_editar_bem_autorizado_com_perfil_nao_admin` | AC03/AC07 (caminho RBAC real, perfil Gestor de TI) |
| `test_edicao_serial_duplicado_rejeitada` | §4.4 / V4 |
| `test_edicao_valida_limites_e_valor_negativo` | §4.4 / V1–V3 |
| `test_edicao_ignora_campos_protegidos_manipulados` | V5/V6 (requisição manipulada) |
| `test_edicao_grava_auditoria_com_before_after` | AC06/FR-006 (1 evento, autor, de → para) |
| `test_edicao_sem_alteracao_nao_grava` | V9 (sem auditoria vazia, sem movimentação) |
| `test_edicao_falha_nao_deixa_estado_parcial` | AC11 (transação única; `monkeypatch` na trilha) |
| `test_alteracao_de_condicao_gera_movimentacao_com_operador_autenticado` | V8/FR-012 |
| `test_edicao_de_bem_baixado_recusada` | P4 aprovada |
| `test_edicao_conflito_de_versao_recusada` | P3 aprovada |
| `test_put_api_grava_operador_autenticado_na_condicao` | FR-012 no `PUT /api/v1/assets/{id}` |

**Implementação** — `app/web/templates/assets/edit.html` (novo, T011: só os campos do §4.3 + `expected_updated_at` oculto, alerta `?error=` no topo), `app/web/routers/assets.py` (T012: `GET`/`POST /assets/{asset_id}/edit` com `require_permission("patrimonio.editar")`, conflito/validação/baixado, `commit=False` no serviço e na trilha + `db.commit()` único, `rollback` em exceção, sem vazar detalhes internos), `assets/detail.html` (T013: ação "Editar bem" só com `can('patrimonio.editar')` e oculta para `BAIXADO`; alertas `updated`/`unchanged`/`error`), `app/api/assets_api.py` (T027: operador autenticado e motivo no `AssetService.update` do `PUT`).

**T014** — 5 testes novos em `tests/test_assets.py` (operador+motivo na movimentação de condição, fallback `"Sistema"`, V1–V3 no serviço, `commit=False` no cadastro e na trilha). Nenhum teste existente foi alterado.

**T015/T019** — `pytest tests/test_consulta_edicao_bens_067.py tests/test_assets.py -v` → **26 passed** (`exit=0`); arquivo da feature isolado → **21 passed**.

### 7.1 Correções de causa durante a rodada

1. **Data do formulário × coluna `DateTime`**: o formulário envia `<input type="date">` (sem hora) enquanto a coluna guarda hora; a comparação de V9 tratava o formulário pré-preenchido como “alterado” (auditoria espúria e regravação da data à meia-noite). Corrigido em `AssetService.edit_changes` comparando `purchase_date`/`warranty_expiry` na **precisão de dia**.
2. **Chaves do histórico no Jinja**: `cadastral_history.items` resolvia para o método `items` do `dict` (`TypeError`). Renomeado para `eventos`/`total`/`truncado`.

## 8. US3 — Histórico cadastral + Polish (T016–T026, T028)

**Testes (T016)** — 3 testes novos: `test_historico_cadastral_separado_de_movimentacoes` (campo + de → para + autor; bloco recortado por marcadores do template sem conteúdo de movimentação), `test_historico_vazio_sem_erro` (estado vazio, HTTP 200) e `test_historico_limite_e_aviso_de_truncamento` (teto/`truncado`). **RED** antes da T017/T018.

**Implementação** — `AssetService.get_cadastral_history(db, asset_id, limit=50)` (T017): leitura **somente** de `AuditLog` (`resource='Asset'`, `resource_id`, ação `ALTERACAO`), com rótulos de negócio e `changed_fields` (mesmo padrão tolerante de `MovementService.get_timeline_for_asset`, que **não** foi alterado); `assets/detail.html` (T018): seção **"Alterações cadastrais"** (`id="historico-cadastral"`) separada da trilha, com aviso de truncamento e estado vazio; rota de detalhe passa a leitura no contexto.

> **Decisão registrada (divergência da letra da T017)**: a consulta filtra **somente `ALTERACAO`** — não `CRIACAO`. Motivo: spec §4.5 item 5 e FR-017 exigem estado vazio claro para bem sem alteração cadastral e dizem explicitamente que o cadastro inicial **não** é uma alteração (ele já é a movimentação `ENTRADA_AQUISICAO`); incluir `CRIACAO` faria `test_historico_vazio_sem_erro` (exigido pela T016) falhar e criaria a “informação enganosa” que a spec proíbe.

**T020** — `tests/route_manifest.json` regenerado pelo gerador documentado no próprio teste: `+14` linhas, exatamente as 2 rotas novas (`GET`/`POST /assets/{asset_id}/edit`); `pytest tests/test_route_inventory.py` → **1 passed**.

**T021** — `docs/ARQUITETURA_E_MANUTENCAO.md` §12.1: consulta completa, edição (`/assets/{id}/edit`), fonte única de regras (V1–V11), transação única, campos protegidos e histórico cadastral; duas linhas novas na tabela de rotas web.

**T022** — `app/services/help_service.py`: artigo `corrigir-informacoes` reescrito (o texto anterior dizia que a edição era “pela API do sistema”, agora falso) com passo a passo da tela, efeito da auditoria, conflito de versão e campos protegidos; artigo `detalhes-do-bem` atualizado (observações, última atualização e seção de alterações cadastrais).

**T023** — `assets/list.html`: ação de linha "Editar" visível só com `can('patrimonio.editar')` e oculta para bem `BAIXADO`; filtros/busca/paginação intocados.

**T025 — escopo do diff** (nenhum arquivo fora da spec §11; zero DDL/migração/dependência):

```
 M app/api/assets_api.py              M docs/ARQUITETURA_E_MANUTENCAO.md
 M app/services/asset_service.py      M docs/Melhorias_SisPatrimonio_Pro.md
 M app/services/audit_service.py      M tests/route_manifest.json
 M app/services/help_service.py       M tests/test_assets.py
 M app/web/routers/assets.py          ?? app/web/templates/assets/edit.html
 M app/web/templates/assets/detail.html  ?? tests/test_consulta_edicao_bens_067.py
 M app/web/templates/assets/list.html    ?? specs/067-consulta-edicao-bens/
```

`git diff -- app/schemas/ app/models/ migrations/` → **nenhuma alteração** (schema e modelos preservados).

### 8.1 T028 — FR-020/SC-009/SC-010 (AC14)

- **Responsividade**: as três telas alteradas usam as classes do grid (`col-12 col-md-*`) — ocorrências: `detail.html` 3, `edit.html` 12, `list.html` 7; nenhum layout novo de largura fixa introduzido.
- **Ausência de N+1 novo**: medição com contador de `before_cursor_execute` no `GET /assets/{id}` — **8 statements com 1 evento cadastral** e **8 statements com 8 eventos** (constante; o histórico é lido em 2 consultas fixas). Harness temporário, removido após a medição.
- **Cenário em 360 px**: **não executado** neste ambiente (sem navegador) — limitação declarada em §11.

## 9. Réguas finais (T024)

```bash
.venv/bin/python -m pytest tests/test_consulta_edicao_bens_067.py -v        # 21 passed
.venv/bin/python -m pytest tests/test_route_inventory.py -q                # 1 passed
.venv/bin/python -m pytest tests/test_assets.py tests/test_api.py tests/test_rbac.py \
  tests/test_import_asset_location.py tests/test_import_asset_movements.py \
  tests/test_movements.py tests/test_localizacao_automatica_066.py \
  tests/test_presentacao_trilha_063.py tests/test_fluxo_global_064.py \
  tests/test_locations_export.py tests/test_report_print_smoke.py tests/test_inventario.py \
  tests/test_datetime_flows.py tests/test_route_inventory.py -q            # 201 passed
.venv/bin/python -m pytest -q                                             # 1005 passed, 2 skipped
```

Todas com `exit=0`. Baseline (T001): 979 passed / 2 skipped → **+26 testes novos, 0 regressão** (os 2 skips são os mesmos do baseline).

## 10. Checklist da Constitution (T026)

| Princípio | Situação |
|---|---|
| Escopo (VII) | ✅ diff restrito aos arquivos da spec §11; nenhum arquivo funcional fora do escopo |
| Comportamento / serviços (III) | ✅ regras de edição centralizadas em `AssetService.update`/`edit_changes` (web e API usam a mesma fonte) |
| Movimentações | ✅ `condition` continua gerando `ATUALIZACAO_ESTADO` via o mesmo fluxo, agora com operador autenticado (FR-012) |
| Banco (VI) | ✅ zero DDL, zero migração, zero coluna/índice; histórico lê a trilha existente |
| Testes (VIII) | ✅ nenhum teste existente alterado/removido/enfraquecido; 26 testes novos (21 + 5) |
| Docs (XI) | ✅ `ARQUITETURA_E_MANUTENCAO.md` e central de ajuda atualizados |
| Decisões P1–P5 (T003) | ✅ P1 tombamento imutável · P2 condição editável com operador · P3 conflito por `updated_at` · P4 baixado bloqueado · P5 leitura viva (dívida **M-003** registrada em `docs/Melhorias_SisPatrimonio_Pro.md`) |

## 11. Limitações desta validação

- **Cenários manuais do quickstart §2–§4 (navegador) não executados**: o ambiente desta rodada não tem navegador/`Chrome` disponível. A cobertura equivalente foi feita por HTTPS (TestClient) — incluindo 403/404, RBAC real com perfil não-admin, colisão de série, conflito de versão, bem baixado e trilha. Ficam pendentes apenas a inspeção visual (360 px/desktop) e a leitura humana dos textos.
- **Suíte em SQLite in-memory** (padrão da casa): a precisão de data do MariaDB é tratada na comparação em segundos (V10) e na comparação por dia (`purchase_date`/`warranty_expiry`), mas não foi exercitada contra o MariaDB real.
- **Verificação somente-leitura em produção** (contagens/trilha no MariaDB real) não foi executada — não há `DATABASE_URL` de produção neste ambiente.
- Os dois harnesses temporários usados para medir (fase Foundational e N+1) foram **removidos**; a cobertura permanente está em `tests/test_assets.py` (T014) e `tests/test_consulta_edicao_bens_067.py`.
- **Commit não criado** — a alteração está no diretório de trabalho; commit apenas sob pedido explícito.
