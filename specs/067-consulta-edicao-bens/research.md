# Research — 067-consulta-edicao-bens

**Data**: 2026-10-10 | **Status**: Unknowns resolvidos e **decisões de negócio P1–P5 APROVADAS em 2026-10-10** (spec §14 e Clarifications). As decisões das seções **R7 (P3), R8 (P4) e R10 (P5)** abaixo são exatamente as aprovadas; R4/R5 permanecem com a decisão técnica indicada.

> Todas as decisões abaixo foram tomadas sobre o código **real** (leitura em 2026-10-10) — nenhuma suposição sobre nomes de rotas, colunas ou permissões. Referências verificadas estão na spec §1.

## R1 — Onde entregar a consulta detalhada

**Decision**: **estender** `app/web/templates/assets/detail.html` (rota existente `GET /assets/{asset_id}`, já sob `patrimonio.visualizar`), acrescentando observações (`notes`), última atualização (`updated_at`), organização em seções e a ação "Editar bem".

**Rationale**: a tela já existe, já carrega `asset` com `location`/`custodian`/`movements`/`maintenances` por `joinedload` (`AssetService.get_by_id`) e já é o destino do QR Code das etiquetas (`/assets/{id}`) e do clique "Ver Detalhes" na listagem. Criar outra tela duplicaria layout e criaria duas URLs canônicas para o mesmo bem. Constitution I e X.

**Alternatives considered**:
- Nova rota `/assets/{id}/detail` ou modal com os dados: duplicação de tela e de padronagem; QR Code e listagem continuariam apontando para a antiga.
- Nova tela "ficha do bem" em PDF/impressão: resolveria outro problema (documento) e não a consulta interativa; fora do escopo.

## R2 — Rota e autorização da edição web

**Decision**: `GET /assets/{asset_id}/edit` e `POST /assets/{asset_id}/edit` em `app/web/routers/assets.py`, **ambas** com `dependencies=[Depends(require_permission("patrimonio.editar"))]`, renderizando `assets/edit.html` (GET) e redirecionando para `/assets/{asset_id}?updated=true` (POST).

**Rationale**: `require_permission` (deny by default, 403 + registro `ACESSO_NEGADO`, 404 amigável via `HTTPException` da rota) é o mecanismo vigente e já é usado pela rota de detalhe. `patrimonio.editar` **já existe** no `PERMISSION_CATALOG` ("Editar dados cadastrais de bens (ficha, fiscal, notas)") e já é concedida a Administrador, Gestor de TI e Patrimônio — criar permissão nova não tem necessidade demonstrada (Constitution VI, spec §9-F). O padrão de confirmação por querystring (`?created=true`) já existe em `detail.html`.

**Alternatives considered**:
- `POST /assets/{id}` (sem `/edit`) na mesma URL do detalhe: colidiria com o padrão GET/POST por recurso usado por `/assets/new` e misturaria leitura e escrita na mesma rota.
- Edição via API a partir do navegador (fetch para `/api/v1/assets/{id}`): criaria um segundo caminho de escrita web, com token/sessão e CSRF não tratados hoje — mais risco, sem ganho.
- Permissão nova (`patrimonio.editar_dados`): desnecessária (§9-F).

## R3 — Onde aplicar as validações novas sem alterar o contrato da API

**Decision**: aplicar nome obrigatório, limites de tamanho (150 name / 100 brand, model, serial_number, invoice_number / 150 supplier), valor de aquisição ≥ 0 e unicidade de nº de série **no service** (`AssetService.update`), levantando `ValueError` com mensagem de negócio; **não** adicionar restrições ao schema `AssetUpdate` (`app/schemas/asset.py`), que permanece idêntico.

**Rationale**: a API já converte `ValueError` em `HTTPException(400, detail=...)` nas duas rotas que usam o service (`app/api/assets_api.py` POST/PUT), então a regra passa a valer também para a API **sem** mudar o contrato declarado nem introduzir `422` de validação Pydantic (que seria uma mudança de comportamento observável). No fluxo web, a mensagem é exibida via `?error=` (padrão da casa). Fonte única da regra (Constitution III) — proibido duplicar no router ou no template.

**Alternatives considered**:
- Restrições no `AssetUpdate` (`ge=0`, `max_length`): mudaria o contrato da API de 400 para 422 em payloads que hoje passam (ex.: `purchase_value = -1` hoje é aceito e gravado) — mudança de contrato e risco de regressão em testes de API.
- Validação só no router web: duplicaria regra e deixaria a API sem proteção (violaria Constitution III e o objetivo de corrigir a lacuna §1.4 item 6).
- Schema web separado ESPELHANDO `AssetUpdate` + regra só no service: o schema separado seria uma duplicação sem função (o service já é autoridade); evitado.

## R4 — Operador autenticado na movimentação gerada pela edição

**Decision**: `AssetService.update(db, asset_id, data, *, operator_name: Optional[str] = None, change_reason: Optional[str] = None)` — parâmetros **opcionais e aditivos**; quando informados, a movimentação `ATUALIZACAO_ESTADO` grava `operator_name` do usuário autenticado e `reason` do motivo informado. As rotas web e API passam `(user.full_name or user.username)` — o mesmo padrão já usado para o operador das movimentações/importação (`app/web/routers/assets.py` no import e `app/api/assets_api.py`).

**Rationale**: hoje o service grava `operator_name="Sistema"` **hardcoded** ao mudar a condição (spec §1.4 item 5), o que contraria o padrão instaurado pela feature 065 ("operador responsável autenticado") e deixa a movimentação de vistoria sem autor. O default `None` preserva exatamente o comportamento atual para chamadas diretas/serviços de teste (`tests/test_assets.py` chama `AssetService.update` sem operador) — Constitution I.

**Alternatives considered**:
- Tornar o operador obrigatório: quebraria `tests/test_assets.py` e qualquer chamador interno; mudança não exigida pela spec.
- Gravar o operador apenas na auditoria e deixar a movimentação com "Sistema": manteria a divergência com a 065 no artefato que o usuário vê (termo/histórico de movimentação).
- Retirar a edição de `condition` do fluxo cadastral: alternativa registrada como P2 e **descartada na aprovação de 2026-10-10** — a condição continua editável na ficha, com a movimentação gravando o operador autenticado (R4 aplica-se integralmente).

## R5 — Atomicidade entre alteração cadastral e registro de auditoria

**Decision**: adicionar o parâmetro aditivo **`commit: bool = True`** em `write_audit`/`write_change_audit` (`app/services/audit_service.py`) e em `AssetService.update` (`app/services/asset_service.py`). Nos fluxos web e API: `AssetService.update(..., commit=False)` → `write_change_audit(..., commit=False)` → `db.commit()` único, com `db.rollback()` em exceção.

**Rationale**: hoje o service faz `commit` e a rota grava a trilha em outro `commit` (spec §1.6 item 7) — falha entre os dois deixa a alteração sem rastro (viola FR-015/AC11). Parâmetros opcionais com default `True` mantêm **idêntico** o comportamento de todos os chamadores atuais (auditoria de login, movimento, importação, usuários etc.) — Constituição I preservada; é a menor mudança aditiva capaz de garantir a transação única exigida pelo briefing.

**Alternatives considered**:
- Novo mecanismo de auditoria transacional paralelo (ex.: `record_asset_change` no service): duplicaria a trilha (proibido — "não criar um segundo mecanismo de auditoria").
- Reverter a alteração manualmente quando a auditoria falhar (re-escrita dos campos): não garante atomicidade real (janela de inconsistência e perda de concorrência).
- Deixar como está e documentar: não atenderia AC08/AC11 pedidos pela spec.

## R6 — Histórico de alterações cadastrais na tela (separado das movimentações)

**Decision**: novo método **somente leitura** `AssetService.get_cadastral_history(db, asset_id, limit=50)` consultando `AuditLog` por `resource == 'Asset'` e `resource_id == asset_id`, com as ações cadastrais (`ALTERACAO`, `CRIACAO`) e a mesma desserialização de `previous_data`/`new_data` já praticada; `assets/detail.html` passa a renderizar **duas listas** — "Alterações cadastrais" e "Movimentações" — a partir de `timeline` (existente) e `cadastral_history` (novo). **`MovementService.get_timeline_for_asset` permanece intacto.**

**Rationale**: a timeline atual é consumida também pela API (`GET /api/v1/assets/{id}/timeline`, contrato) e aplica regras próprias (exclui `MOVIMENTACAO`/`MANUTENCAO`/`CRIACAO`, limita 50). Alterá-la para separar tipos mudaria payload de API. Uma leitura adicional indexada (os filtros `resource`/`resource_id` já são usados por essa mesma rotina) é o caminho de menor risco e mantém o padrão 063 de apresentação da trilha.

**Alternatives considered**:
- Alterar `get_timeline_for_asset` para retornar tipos separados: muda contrato da API e o payload consumido por templates/testes da 063/064.
- Nova tabela de histórico cadastral: DDL e duplicação da trilha (§9-E).
- Reaproveitar a página de auditoria com filtro por bem: exige `auditoria.visualizar` (permissão diferente de `patrimonio.visualizar`) e tira o histórico de perto do bem.

## R7 — Conflito de edição concorrente (P3 — aprovada: controle otimista)

**Decision (aprovada em 2026-10-10)**: controle **otimista** sem DDL — o formulário carrega `updated_at` em campo oculto; no POST, se o `updated_at` do banco for diferente do enviado, a gravação é recusada com mensagem "O bem foi alterado por outro usuário desde que você abriu esta tela. Recarregue e refaça a edição." e `?error=`; nenhuma sobrescrita silenciosa.

**Rationale**: `assets.updated_at` existe com `onupdate=now_utc` (spec §1.3) e é suficiente como versão lógica, sem coluna nova (Constitution VII). É o comportamento pedido por RF-018/AC11 ("conflito entre edições concorrentes" tratado, sem perda silenciosa).

**Alternatives considered**:
- "Last write wins" documentado: mais simples, porém perde a alteração do primeiro usuário silenciosamente (contraria o objetivo de confiabilidade).
- `SELECT ... FOR UPDATE`/bloqueio pessimista: segura a transação durante a edição inteira, com risco de contenção e sem ganho no cenário de duas abas.
- Coluna `version`/`If-Match`: DDL desnecessária para o ganho.

## R8 — Edição de bem `BAIXADO` (P4 — aprovada: bloquear)

**Decision (aprovada em 2026-10-10)**: **bloquear** a edição cadastral de bem com `status = BAIXADO` (a rota recusa com mensagem clara, sem gravar; o botão "Editar bem" não é exibido), mantendo a coerência com a UI atual, que já esconde Movimentar/Manutenção em bens baixados.

**Rationale**: baixa é evento patrimonial encerrado; permitir edição irrestrita de cadastro em bem baixado conviveria mal com a imutabilidade esperada para registros encerrados (Constitution IV). A correção, se necessária, deve passar por procedimento administrativo próprio.

**Alternatives considered**: permitir com aviso (mantém correção de dados possível, mas amplia o risco de alterar dado de bem já baixado e de afetar relatórios/atas) — **descartada na aprovação (P4)**.

## R9 — Rotas novas e o manifesto de rotas (feature 051)

**Decision**: atualizar `tests/route_manifest.json` na mesma tarefa, registrando as duas rotas novas (`GET`/`POST /assets/{asset_id}/edit`, endpoint names correspondentes), no formato exato consumido por `tests/test_route_inventory.py`.

**Rationale**: verificado no código — `test_route_inventory.py` compara **todas** as rotas do app (path, métodos, nome do endpoint) com o manifesto e falha em qualquer diferença; sem a atualização, a suíte fica vermelha (AC15). O manifesto é artefato de teste (não é código funcional), e a feature 051 o define como prova de não regressão.

**Alternatives considered**: não criar as rotas web (só API) — descartado na spec §9-C; alterar o teste para ignorar rotas novas — proibido (enfraquecer teste, Constitution VIII).

## R10 — Ata de inventário e exportações (P5 — aprovada: manter leitura viva)

**Decision (aprovada em 2026-10-10)**: **não alterar** `report_service`/`InventarioItem` nesta feature. A ata continua lendo `asset.tag`/`asset.name`/`asset.category` ao vivo (comportamento atual, spec §1.7) e o risco é documentado como limitação conhecida; a criação de snapshots no item de inventário (DDL aditivo + mudança de geração de documentos) é remetida a **feature própria**.

**Rationale**: congelar esses campos exigiria DDL aditivo e alteraria a geração de documentos comprobatórios (mudança de comportamento fora do escopo desta spec — Constitution I). Como o tombamento fica imutável (P1) e a edição de `name`/`category` é justamente o caso de uso legítimo da feature, a decisão precisa ser consciente e explícita — o que a spec faz em §14 P5, com AC10/SC-007 medindo a integridade do que já é snapshot (movimentações, `expected_*`). A dívida está registrada como **M-003** em `docs/Melhorias_SisPatrimonio_Pro.md`.

**Alternatives considered**:
- Snapshot de `name`/`tag`/`category` em `inventario_itens` (DDL aditivo) + uso na ata: solução correta a médio prazo; escopo e risco maiores (migração de dados existentes sem origem histórica) → feature própria.
- Bloquear a edição de `name`/`category` quando o bem participa de inventário encerrado: regra de negócio nova e pouco previsível para o usuário, não pedida pelo briefing.

## R11 — Estratégia de testes e regressão

**Decision**: arquivo novo `tests/test_consulta_edicao_bens_067.py` (fixtures `client`/`db_session`), cobrindo AC01–AC15 com os casos da spec §12; estender `tests/test_assets.py` para o operador autenticado/validações no service; atualizar `tests/route_manifest.json`; réguas de regressão sem edição (`test_assets.py`, `test_api.py`, `test_rbac.py`, `test_route_inventory.py`, `test_import_asset_location.py`, `test_import_asset_movements.py`, `test_movements.py`, `test_localizacao_automatica_066.py`, `test_presentacao_trilha_063.py`, `test_fluxo_global_064.py`) + régua completa.

**Rationale**: Constitution VIII (suíte existente é a base de regressão; nada removido/enfraquecido) e padrão da casa (arquivo de teste por feature: 062/063/064/066). O teste de falha simulada (AC11) usa `monkeypatch` para provocar exceção na gravação da trilha e provar o rollback — sem tocar em banco real.

**Alternatives considered**: estender apenas `test_assets.py` — mistura escopos e dificulta rastrear AC↔teste; a casa usa arquivo novo por feature.
