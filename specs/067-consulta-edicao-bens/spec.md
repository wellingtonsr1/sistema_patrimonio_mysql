# Feature Specification: Consulta Detalhada e Edição Controlada de Bens Patrimoniais

**Feature Branch**: `067-consulta-edicao-bens`

**Created**: 2026-10-10

**Status**: **APROVADA (2026-10-10)** — todas as pendências decididas pelo responsável: P1–P5 aprovadas (ver Clarifications e §14). Artefatos de planejamento completos (`plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`); pronta para implementação pelo `tasks.md`. Responde ao Ponto 3 de `specs/001-sistema-existente/spec.md` §11 (edição de bem existe na API, não na interface web).

**Input**: User description: "Criar especificação para consulta completa dos dados cadastrais de um bem patrimonial e edição controlada de suas informações, respeitando permissões, regras de negócio, integridade e rastreabilidade; incluir consulta ao histórico de alterações cadastrais quando o recurso não existir ou não atender. Somente Spec e artefatos de planejamento — nada de implementação."

---

## Clarifications

### Session 2026-10-10 (aprovação do responsável)

- Q: A alteração do **Número de Tombamento / Tag** entra nesta feature? (P1) → A: **Não.** O tombamento permanece **imutável**: não há campo na interface, ele não consta do schema de edição e requisições manipuladas que o enviem são ignoradas. Alterá-lo exigirá **procedimento próprio** em feature futura (rastreamento de etiquetas/QR já impressos, impacto na deduplicação da importação por tombamento e auditoria específica com valores anterior/novo).
- Q: A **condição de conservação** (`condition`) continua editável na ficha de edição? (P2) → A: **Sim, continua editável** (comportamento atual da API preservado), mas a movimentação `ATUALIZACAO_ESTADO` correspondente passa a gravar o **operador autenticado** e o motivo informado, no padrão da feature 065 — encerrando o `operator_name="Sistema"` hardcoded.
- Q: Como tratar **edições concorrentes** no mesmo bem (duas abas ou dois usuários)? (P3) → A: **Controle otimista** por `updated_at`, sem DDL: o formulário envia a versão lida e, se o registro mudou antes do salvamento, a gravação é recusada com aviso para recarregar e refazer — **sem** sobrescrita silenciosa ("last write wins" descartado).
- Q: A edição cadastral é permitida em **bem com situação `BAIXADO`**? (P4) → A: **Não** — a edição de bem baixado é **bloqueada** (mensagem clara, sem gravação; o botão "Editar bem" não é exibido), coerente com a UI atual, que já esconde Movimentar/Manutenção em bens baixados. Correção, se necessária, por procedimento administrativo próprio.
- Q: A **ata de inventário** e o **CSV de movimentações**, que hoje leem `tag`/`name`/`category` do cadastro **atual**, devem passar a usar snapshot? (P5) → A: **Não nesta feature** — o comportamento atual é mantido (sem DDL aditivo e sem alterar a geração de documentos comprobatórios); a consequência fica registrada como limitação conhecida (AC10/SC-007 medem a integridade do que **já** é snapshot) e a criação de snapshots de `name`/`tag`/`category` no item de inventário é remetida a **feature própria** (dívida **M-003** registrada em `docs/Melhorias_SisPatrimonio_Pro.md`).

---

## 1. Diagnóstico do comportamento atual (Fase 1 — somente leitura, verificado 2026-10-10)

Método: leitura do código real (`app/models/`, `app/schemas/`, `app/services/`, `app/api/`, `app/web/routers/`, `app/web/templates/`), da `Constitution` (`.specify/memory/constitution.md`), de `tests/` e das specs anteriores. **Nenhum arquivo da aplicação foi alterado, nenhuma migração executada, nenhum commit feito.**

### 1.1 Rotas e endpoints relacionados a bens

| # | Rota | Método | Permissão | Arquivo / linha | Comportamento |
|---|---|---|---|---|---|
| 1 | `/assets` | GET | `patrimonio.visualizar` | `app/web/routers/assets.py` L58 | Listagem com busca e 10 filtros; padrão `limit=200` |
| 2 | `/assets/labels` | GET | `patrimonio.visualizar` | `app/web/routers/assets.py` L128 | Seleção/impressão de etiquetas (somente leitura) |
| 3 | `/assets/new` | GET/POST | `patrimonio.criar` | `app/web/routers/assets.py` L390/L408 | Formulário de cadastro; ao criar redireciona para `/assets/{id}?created=true` |
| 4 | `/assets/{asset_id}` | GET | `patrimonio.visualizar` | `app/web/routers/assets.py` L472 | **Tela de detalhes já existente** → `assets/detail.html` com `asset`, `timeline`, `depreciation`, `open_inventarios`; 404 se não existir |
| 5 | `/assets/import` + `/assets/import/confirm` | GET/POST | `patrimonio.criar` | `app/web/routers/assets.py` L223/L233/L308 | Importação CSV com pré-visualização |
| 6 | `/api/v1/assets` | GET | `patrimonio.visualizar` | `app/api/assets_api.py` L34 | Lista paginada |
| 7 | `/api/v1/assets/{asset_id}` | GET | `patrimonio.visualizar` | `app/api/assets_api.py` L50 | Detalhe completo (`AssetRead`) — 404 se não existir |
| 8 | `/api/v1/assets/tag/{tag}` | GET | `patrimonio.visualizar` | `app/api/assets_api.py` L61 | Busca por tombamento |
| 9 | `/api/v1/assets/{asset_id}/timeline` | GET | `patrimonio.visualizar` | `app/api/assets_api.py` L72 | Linha do tempo unificada (movimentações + auditoria) |
| 10 | `/api/v1/assets/{asset_id}/depreciation` | GET | `patrimonio.visualizar` | `app/api/assets_api.py` L131 | Depreciação linear 20%/ano |
| 11 | `/api/v1/assets` | POST | `patrimonio.criar` | `app/api/assets_api.py` L139 | Criação |
| 12 | **`/api/v1/assets/{asset_id}`** | **PUT** | **`patrimonio.editar`** | `app/api/assets_api.py` L161 | **Edição cadastral já existe — somente via API**; grava auditoria `ALTERACAO` com before/after |
| 13 | `/api/v1/assets/import/csv` | POST | `patrimonio.criar` | `app/api/assets_api.py` L188 | Importação via API |

**Fato comprovado 1**: **não existe rota web de edição de bem** (nem `GET /assets/{id}/edit`, nem `POST` de atualização). Varredura de todos os decoradores `@web_router.*` do router de bens e do manifesto `tests/route_manifest.json`: as únicas rotas de escrita web são `/assets/new` e `/assets/import*`. Isso já estava registrado como ponto em aberto em `specs/001-sistema-existente/spec.md` §11 item 3 ("Edição/exclusão via interface: edição de bem e de local existem confirmadas na API; não foi identificada página web dedicada — a interface deve expor essas operações?").

**Fato comprovado 2**: a edição pela API **não cria um novo bem** — atualiza o registro existente (`AssetService.update`) e mantém as movimentações já gravadas.

### 1.2 Templates Jinja2 de bens

| Template | Papel | Pontos relevantes verificados |
|---|---|---|
| `app/web/templates/assets/list.html` | Listagem | Ações por linha: apenas "Ver Detalhes" (`/assets/{id}`, L233). **Sem botão Editar** (L196–254) |
| `app/web/templates/assets/form.html` | Cadastro (`/assets/new`) | Formulário completo: tag, nome, categoria, marca, modelo, nº de série, especificações, dados fiscais, condição, local/custodiante iniciais, operador, observações |
| `app/web/templates/assets/detail.html` | Detalhes (`/assets/{id}`) — 333 linhas | Hero (tag, nome, situação, categoria, condição) + botões **Movimentar** (`movimentacao.criar`), **Manutenção** (`manutencao.criar`), **Inventário** (dropdown, se houver inventário aberto), **Voltar**. Coluna esquerda: Custódia & Localização Atual, Ficha Técnica & Dados Fiscais (marca/modelo, nº de série, data de compra, NF, fornecedor, garantia, especificações **somente se preenchidas**), Contabilidade & Depreciação, QR Code. Coluna direita: **Trilha de Fluxo & Movimentações** (timeline unificada com "Antes/Depois" em JSON e "Registrado por") |
| `app/web/templates/assets/labels.html` | Etiquetas | QR Code aponta para `/assets/{id}` |
| `app/web/templates/assets/import.html` | Importação CSV | Fluxo de mapeamento/pré-visualização |

**Lacunas da tela de detalhes (comprovadas por leitura integral do template)**:
- **não há ação "Editar bem"** em nenhum ponto;
- `asset.notes` (Observações) **não é exibido** — o único `notes` renderizado é o da movimentação (L292);
- `asset.updated_at` **não é exibido** (nenhum template de bens o exibe);
- a "Ficha Técnica" **omite especificações** quando vazias (comportamento correto: não simula dado inexistente) e **não mostra** o campo de observações;
- a trilha é **unificada** (cadastral + movimentação no mesmo fluxo) e limitada a 50 eventos de auditoria.

### 1.3 Modelo `Asset` e mapeamento real dos campos (o prompt usa nomes de negócio; o código usa outros)

`app/models/asset.py` — tabela `assets`:

| Nome de negócio (prompt) | Coluna real | Tipo / restrição | Obrigatório | Exibido no detalhe | **Editável hoje (API PUT)** |
|---|---|---|---|---|---|
| Número de Tombamento / Tag | `tag` | String(50) **UNIQUE** index NOT NULL; normalizada para UPPER em `create` | Sim | Hero + QR | **NÃO** (fora de `AssetUpdate`) |
| Nome / Descrição do Bem | `name` | String(150) NOT NULL index | Sim | Hero | **Sim** |
| Categoria | `category` | Enum(`AssetCategory`, 11 valores) NOT NULL default `OUTROS` | Sim | Badge no hero | **Sim** |
| Marca / Fabricante | `brand` | String(100) nullable | Não | Ficha técnica | **Sim** |
| Modelo | `model` | String(100) nullable | Não | Ficha técnica | **Sim** |
| Número de Série | `serial_number` | String(100) **UNIQUE** index nullable | Não | Ficha técnica | **Sim** (com validação de unicidade no service) |
| Especificações Técnicas Detalhadas | `specifications` | Text nullable | Não | Ficha técnica (condicional) | **Sim** |
| Data de compra / Valor / NF / Fornecedor / Garantia | `purchase_date`, `purchase_value`, `invoice_number`, `supplier`, `warranty_expiry` | DateTime / Float NOT NULL default 0.0 / String(100) / String(150) / DateTime | Só `purchase_value` | Ficha técnica + depreciação | **Sim** |
| Situação patrimonial | `status` | Enum(`AssetStatus`, 5: DISPONIVEL/EM_USO/EM_MANUTENCAO/EM_TRANSITO/BAIXADO) NOT NULL | Sim | Pill no hero | **NÃO** (protegido; alterado via movimentação) |
| Condição / Estado de conservação | `condition` | Enum(`AssetCondition`, 6) NOT NULL default `NOVO` | Sim | Badge no hero | **Sim** (gera movimentação `ATUALIZACAO_ESTADO` quando muda) |
| Localização atual | `location_id` → `locations.id` | FK nullable | Não | "Custódia & Localização Atual" (`asset.location.name/branch/department`) | **NÃO** (protegido; fluxo de movimentação) |
| Responsável / Custodiante | `custodian_id` → `custodians.id` | FK nullable | Não | "Custódia & Localização Atual" (`asset.custodian.name/role/registration_code`) | **NÃO** (protegido; fluxo de movimentação) |
| Unidade administrativa | `Location.branch` (da localização atual) | String NOT NULL em `locations` | Sim (no local) | Exibido sob a localização | **NÃO** por esta via (é dado do local) |
| Departamento / Setor | `Location.department` | String NOT NULL em `locations` | Sim (no local) | Exibido sob a localização | **NÃO** por esta via (é dado do local) |
| Observações | `notes` | Text nullable | Não | **Não exibido** | **Sim** |
| Metadados | `created_at`, `updated_at` | DateTime (`onupdate=now_utc`) | Sim | Não exibido | Não |

**Fato comprovado 3 — proteções já existentes no schema**: `AssetUpdate` (`app/schemas/asset.py`) **não contém** `tag`, `status`, `location_id` e `custodian_id`. Portanto, hoje **não existe nenhum caminho** (web ou API) que altere tombamento, situação, localização ou custódia por edição cadastral. O tombamento é imutável em todas as camadas.

**Fato comprovado 4 — risco documental real (snapshot parcial)**: a ata de inventário (`app/services/report_service.py::_inventario_rows`, L~541–546) lê **ao vivo** `asset.tag`, `asset.name` e `asset.category.label`, enquanto local/responsável esperados vêm de snapshots `InventarioItem.expected_*` (`app/models/inventario.py`). O mesmo vale para o CSV de movimentações (`report_service.py` L510–511 usa `m.asset.tag`/`m.asset.name` atuais, embora origem/destino sejam snapshots em `Movement`). **Consequência**: renomear/reclassificar um bem altera o conteúdo da ata de um inventário **já encerrado** e de exports de movimentações já emitidos. Este é o principal risco de "edição comprometer histórico" e foi decidido em P5 (§14/Clarifications): **mantido como está** nesta feature, com a dívida **M-003** registrada para feature própria.

### 1.4 Serviços e regras de negócio

| # | Ponto | Realidade verificada |
|---|---|---|
| 1 | Leitura | `AssetService.get_by_id` (`app/services/asset_service.py` L115) já carrega `location`, `custodian`, `movements` e `maintenances` com `joinedload` — a tela de detalhes não gera N+1 por relacionamento |
| 2 | Busca por tombamento | `AssetService.get_by_tag` normaliza `strip().upper()` |
| 3 | Criação | `AssetService.create` (L126): unicidade de `tag` (mensagem "Já existe um equipamento com o tombamento '<TAG>'"), unicidade de `serial_number` quando informado, status inicial derivado (`EM_USO` se houver custodiante, senão `DISPONIVEL`), e **grava a movimentação inicial `ENTRADA_AQUISICAO`** com snapshots + `term_code` `TR-INIC-{ano}-{id:04d}` |
| 4 | Atualização | `AssetService.update` (L201): unicidade de `serial_number` excluindo o próprio `id`; aplica `data.model_dump(exclude_unset=True)`; se `condition` mudou, grava `Movement(MovementType.STATUS_UPDATE)` com notas "Estado de conservação alterado de X para Y"; `commit` ao final |
| 5 | **Lacuna comprovada no operador** | A movimentação gerada por edição grava `operator_name="Sistema"` **hardcoded** (L~245) — não o usuário autenticado. Contraria o padrão da feature 065 (operador responsável autenticado nas movimentações) |
| 6 | **Lacuna comprovada de validação** | `AssetUpdate.purchase_value: Optional[float]` **sem** `ge=0`; `name` sem limite explícito em Pydantic (o limite de 150 vem só da coluna); nada valida tamanho de `brand`/`model`/`serial_number` antes do banco |
| 7 | **Lacuna comprovada de concorrência** | Não há versão/`If-Match`/checagem de `updated_at`: duas edições simultâneas → "last write wins" silencioso |
| 8 | **Lacuna comprovada de regra para baixados** | Nenhuma regra impede editar cadastro de bem com `status = BAIXADO`; a UI apenas esconde Movimentar/Manutenção (template L~217) |
| 9 | Movimentação | `MovementService.create_movement` é o motor oficial de localização/custódia/status (Constitution IV) — a edição cadastral não pode contorná-lo |
| 10 | Importação | `import_service.py` faz **upsert controlado**: atualiza bens existentes por tombamento (dedupe) — ou seja, já existe escrita cadastral em massa fora da tela |

### 1.5 Perfis, permissões e autorização

| # | Ponto | Realidade verificada |
|---|---|---|
| 1 | Catálogo (`app/services/permission_service.py` `PERMISSION_CATALOG`) | `patrimonio.visualizar`, `patrimonio.criar`, **`patrimonio.editar`** ("Editar dados cadastrais de bens (ficha, fiscal, notas)"), `patrimonio.excluir` |
| 2 | Perfis padrão (`DEFAULT_ROLES`) — **7 perfis reais**, verificados em execução em 2026-10-10 | **Com `patrimonio.editar`** (e `visualizar`+`criar`): **Administrador** (39/39 permissões), **Gestor de TI**, **Patrimônio**. **Somente `patrimonio.visualizar`** (sem editar): **Técnico de TI**, **Almoxarifado**, **Auditor**, **Consulta** |
| 3 | `patrimonio.excluir` | Permissão existe **sem nenhuma rota que a consuma** (já registrado em `specs/001-sistema-existente/spec.md` §11 item 2) |
| 4 | Aplicação no backend | `require_permission(permission, *, web=False)` (`app/api/deps.py` L104): deny by default; não autenticado → 401 (API) / redirect `/login` (web); sem permissão → **403 registrado na trilha como `ACESSO_NEGADO`**; `is_admin` faz bypass |
| 5 | Interface | Menu/botões usam `can('permissao')` — apresentação apenas; a autoridade é o backend (Constitution VI) |
| 6 | Conclusão para esta feature | **Não é necessário criar permissão nova**: `patrimonio.visualizar` cobre a consulta detalhada e `patrimonio.editar` cobre a edição — ambas já existem, já são concedidas a perfis coerentes e já são exigidas pela API |

### 1.6 Auditoria e histórico

| # | Ponto | Realidade verificada |
|---|---|---|
| 1 | Trilha | `audit_logs` (somente leitura; não há rota de escrita/exclusão) — `app/services/audit_service.py` |
| 2 | Gravação de alteração | `write_change_audit` monta `description` = "Campos alterados: ..." e grava `previous_data`/`new_data` em **JSON**, com `user_id`, `username` snapshot, `ip_address`, `module`, `resource`, `resource_id`, `resource_ref`, `timestamp` |
| 3 | Uso atual na edição | `PUT /api/v1/assets/{id}` **já grava** `ACTION_UPDATE` (`ALTERACAO`), `module="Patrimônio"`, `resource="Asset"`, `resource_ref=asset.tag`, `resource_id=asset.id`, com `before`/`after` do snapshot `_asset_snapshot` (17 campos) |
| 4 | Criação | `POST /assets/new` e `POST /api/v1/assets` gravam `ACTION_CREATE` com `after` |
| 5 | Consumo no histórico do bem | `MovementService.get_timeline_for_asset` (L410) une movimentações + auditoria (`resource='Asset' AND resource_id=asset_id`), ordena desc, **limita a 50 eventos de auditoria** e **exclui** `MOVIMENTACAO`, `MANUTENCAO` e **`CRIACAO`** (porque o movimento inicial já representa o cadastro) |
| 6 | Conclusão | **O mecanismo de registro de alterações cadastrais JÁ EXISTE e atende** aos requisitos de ator/data/campo/valor anterior/valor novo (o "campo alterado" está em `description`, os valores em `previous_data`/`new_data`). Não é necessário criar segundo mecanismo (Constitution IX / instrução do prompt: não criar auditoria paralela) |
| 7 | Lacunas comprovadas | (a) não há garantia de **mesma transação** entre a alteração e o evento: `AssetService.update` faz `commit` e a rota grava a auditoria **depois**, com outro `commit` — falha entre os dois grava a mudança sem trilha; (b) `write_audit`/`write_change_audit` chamam `commit()` internamente; (c) o "Antes/Depois" aparece na tela como **JSON bruto** (`tojson`), pouco legível; (d) o histórico mistura cadastral e movimentação sem separação visual por tipo; (e) limite de 50 eventos sem paginação |

### 1.7 Documentos, relatórios e exportações (o que usa snapshot e o que lê ao vivo)

| Artefato | Fonte dos dados | Efeito de uma edição cadastral |
|---|---|---|
| Termo de cautela (`/movements/{id}/term`) | `Movement`: snapshots `origin_*`/`destination_*` (`*_name` String) + `term_code` | **Preservado** (texto congelado no evento) |
| Movimentações (tela, CSV, PDF) | Nomes de origem/destino: snapshots. **Tombamento/nome do bem: leitura ao vivo de `asset.*`** | CSV/PDF de movimentações pode exibir o novo nome/tag |
| Ata de inventário (CSV/PDF) | `expected_location_name`/`expected_custodian_name` = snapshot; **`tag`, `nome`, `categoria` = leitura ao vivo** | Ata de inventário encerrado muda se `tag`/`name`/`category` forem editados |
| Inventário — lista de bens esperados | `InventarioItem` criado por snapshot na geração (`expected_*`), imune a edição posterior | **Preservado** |
| Relatórios/dashboards/exportações de bens | Leitura ao vivo do cadastro | Refletem o valor atual (esperado: relatório é do estado atual) |
| Etiquetas/QR | QR aponta para `/assets/{id}` (URL estável); etiqueta exibe `tag` | **Preservado** o vínculo (o QR usa `id`, não a tag) — mas a etiqueta impressa antiga exibe a tag antiga |
| Importação CSV | Dedupe/upsert pelo **tombamento** | Tombamento não muda nesta feature (P1 aprovada: imutável), então a chave de dedupe permanece estável |

### 1.8 Testes e cobertura existente

| Arquivo | Cobertura relacionada |
|---|---|
| `tests/test_assets.py` | `AssetService.create` + depreciação + `AssetService.update` (notas e condição) — **sem** teste de rota web de bens |
| `tests/test_rbac.py` | Seeding de perfis/permissões, 403/401, botões ocultos sem permissão (`test_web_action_buttons_hidden_without_permission`), APP 403 sem permissão, auditoria de mutação e de acesso negado |
| `tests/test_route_inventory.py` | Compara **todas** as rotas do app com `tests/route_manifest.json` (path, métodos, endpoint) — **qualquer rota nova quebra este teste até o manifesto ser atualizado** |
| `tests/test_api.py`, `tests/test_import_asset_*`, `tests/test_locations_*` | Fluxos de API/importação de bens |
| Nenhum teste cobre | `PUT /api/v1/assets/{id}` via HTTP (permissão, before/after na trilha), tela de detalhes web, edição web |

**Fato comprovado 5**: o `PUT` da API é exercitado apenas indiretamente (`AssetService.update`), **sem teste de autorização nem de auditoria** — lacuna de cobertura a suprir nesta feature.

### 1.9 Specs anteriores relacionadas

| Spec | Relação |
|---|---|
| `specs/001-sistema-existente` | Baseline; §11 itens 2 e 3 registram justamente as lacunas de edição via interface e de permissões reservadas sem funcionalidade. §11 item 3 é o **gatilho desta feature** |
| `specs/063-presentacao-trilha-fluxo` | Padrão de apresentação da trilha de fluxo (usado pela timeline do detalhe) |
| `specs/064-origem-destino-fluxo-global` | Snapshots de origem/destino nas movimentações (base da preservação histórica) |
| `specs/065-operador-responsavel-autenticado` | Operador das movimentações = usuário autenticado; **contraste direto** com a lacuna §1.4 item 5 |
| `specs/066-preenchimento-automatico-localizacao` | Precedente de campo `readonly` e de validação autoritativa no servidor |
| `specs/007`, `008`, `049`, `050` | Pesquisa de locais, exportação de locais, busca e nomenclatura — nenhuma cobre edição de bem |

### 1.10 Recursos equivalentes já implementados (reaproveitamento obrigatório)

1. **Tela de detalhes** `/assets/{id}` (`assets/detail.html`) — cobre a maior parte de RF01; **estender**, não recriar.
2. **Edição cadastral no service** `AssetService.update` + schema `AssetUpdate` — reutilizar como única fonte de regra.
3. **Autorização** `require_permission("patrimonio.visualizar"/"patrimonio.editar")` — sem permissão nova.
4. **Auditoria** `write_change_audit` + `_asset_snapshot` — reutilizar a trilha única.
5. **Histórico unificado** `MovementService.get_timeline_for_asset` — reutilizar/estender.
6. **Formulário de cadastro** `assets/form.html` — reutilizar o padrão de campos/validações do form de edição.
7. **Controle de acesso na UI** `can()` — botão "Editar bem" condicional.

---

## 2. Problema e motivação

O sistema já permite editar dados cadastrais **apenas por API** (`PUT /api/v1/assets/{id}`), e a tela de detalhes do bem já existe, mas:

1. **não há como corrigir um dado pela interface**: um erro de digitação no nome, na marca, no modelo ou no nº de série obriga hoje a usar a API ou recadastrar o bem — e recadastrar é impossível para o mesmo tombamento (UNIQUE), o que empurra o usuário para workarounds (tombamento "corrigido" à mão, duplicidade artificial);
2. **a tela de detalhes é incompleta** para conferência cadastral: não mostra observações (`notes`) nem a data da última alteração, e não há indicação de quais campos são editáveis;
3. **não há ação visível de edição**, embora o perfil `patrimonio.editar` já exista e já esteja concedido aos perfis Gestor de TI e Patrimônio — a capacidade existe no backend e é invisível para o usuário;
4. **a edição pela API é frágil em três pontos**: (a) quando a `condition` muda, a movimentação `ATUALIZACAO_ESTADO` é gravada com operador `"Sistema"` em vez do usuário autenticado (padrão 065); (b) não há validação de valor negativo em `purchase_value` nem de tamanho dos textos antes do banco; (c) não há proteção contra edições concorrentes;
5. **a alteração e seu registro de auditoria não são atômicos**: o service faz `commit` e a rota grava a trilha em outro `commit`; falha no meio deixa alteração sem rastro;
6. **o histórico cadastral existe, mas é pouco utilizável**: aparece em JSON bruto misturado às movimentações, sem separação por tipo, limitado a 50 eventos de auditoria;
7. **há risco comprovado de a edição alterar documento histórico**: a ata de inventário lê `tag`/`name`/`category` ao vivo (§1.4/§1.7), então corrigir o nome de um bem muda a ata de um inventário já encerrado;
8. **não há regra definida** para editar bem baixado (`BAIXADO`) nem para conflito entre edições.

---

## 3. Objetivo e escopo

**Objetivo**: permitir que o usuário autorizado **consulte todos os dados cadastrais** de um bem pela tela de detalhes já existente e **corrija dados cadastrais** de forma controlada por um formulário de edição web, com validações preservadas, autorização no backend, registro de auditoria confiável e histórico de alterações consultável — **sem** criar novo bem, **sem** contornar os fluxos de movimentação/custódia/baixa e **sem** alterar o conteúdo de documentos históricos.

**INCLUI (escopo)**:
- Complementar a tela `/assets/{id}` (detalhes) com os dados cadastrais faltantes e indicação clara do que é editável.
- Ação **"Editar bem"** na tela de detalhes (obrigatória) e, como polimento opcional, também na listagem de bens — sempre condicionada a `patrimonio.editar` e oculta para bem baixado (P4 aprovada).
- Formulário web de edição (`/assets/{id}/edit`) que reutiliza campos, validações e o service existentes.
- Restrição explícita dos campos editáveis nesta feature (nome, categoria, marca, modelo, nº de série, especificações, dados fiscais, condição, observações).
- **Proteção do tombamento** (`tag`) e das propriedades patrimoniais (situação, localização, custódia) fora da edição cadastral.
- Registro de auditoria da alteração reutilizando `write_change_audit`, com before/after, e garantia de atomicidade com a gravação.
- Consulta ao **histórico de alterações cadastrais** do bem, separado das movimentações, com valores anterior/novo legíveis.
- Validação de unicidade de nº de série, campos obrigatórios, limites de tamanho, valor não negativo, e mensagens de erro amigáveis.
- Tratamento de: bem inexistente/removido, sem permissão, falha de gravação, conflito de edição concorrente, salvar sem alterações e cancelamento.
- Testes automatizados novos + regressão completa.

**NÃO INCLUI (fora do escopo)**:
- Alterar o **tombamento** (`tag`) — imutável nesta feature (P1 aprovada); o procedimento próprio fica para feature futura.
- Alterar **situação** (`status`), **localização** ou **custódia** pela edição cadastral — continuam exclusivamente pelo motor de movimentações (`MovementService.create_movement`).
- Exclusão de bens (`patrimonio.excluir` segue reservada — `specs/001` §11 item 2).
- Edição web de **locais**, colaboradores, usuários ou manutenções (features próprias).
- Criar tabela/mecanismo de auditoria paralelo.
- Snapshotar nome/tag/categoria na ata de inventário ou no CSV de movimentações (efeito colateral do §1.7): **P5 aprovada mantém o comportamento atual**; a criação de snapshots é dívida registrada (M-003) para feature própria.
- Alterar a API REST `PUT` existente em contrato (compatibilidade preservada; apenas correções internas previstas).
- Redesenho visual, nova biblioteca, novo framework, nova dependência, DDL destrutivo ou migração de dados.
- Edição em massa/corretiva de vários bens por planilha (a importação CSV já faz upsert — §1.4 item 10).

---

## 4. Comportamento funcional esperado

### 4.1 Consulta detalhada (RF01)

1. A tela `/assets/{id}` (já existente) passa a apresentar **todos** os dados cadastrais relevantes, em seções, no padrão visual atual: identificação (tombamento, nome, categoria, situação, condição), ficha técnica (marca, modelo, nº de série, especificações), aquisição/fiscal (data, valor, NF, fornecedor, garantia), localização e custódia atuais, observações, depreciação, etiqueta/QR e histórico.
2. **Observações (`notes`)** passam a ser exibidas quando preenchidas.
3. **Última atualização cadastral** (`updated_at`) passa a ser exibida.
4. Campos vazios continuam **omitidos ou marcados como não informados** — nunca exibidos como se estivessem cadastrados.
5. A consulta exige `patrimonio.visualizar`; sem permissão → 403 na API e página amigável na web; bem inexistente → **404**.
6. A tela permanece acessível a partir da listagem (`/assets` → "Ver Detalhes") e por QR Code (URL `/assets/{id}`).

### 4.2 Acesso à edição (RF02)

1. A tela de detalhes ganha a ação **"Editar bem"**, visível **somente** com `can('patrimonio.editar')` e **oculta para bem baixado** (P4 aprovada: edição bloqueada).
2. A ação conduz a `/assets/{id}/edit`, que exige `patrimonio.editar` no backend (GET e POST) e reutiliza o layout/componentes do formulário de cadastro (`assets/form.html`) e as validações já existentes.
3. Sem permissão: 403 registrado como `ACESSO_NEGADO` na trilha (comportamento atual do `require_permission`).
4. Bem inexistente: 404 amigável, sem qualquer gravação.

### 4.3 Campos editáveis × restritos (RF03/RF04/RF05 — matriz definitiva)

| Campo (negócio) | Coluna real | Editável nesta feature | Regra/validação |
|---|---|---|---|
| Nome / Descrição do bem | `name` | **SIM** | Obrigatório, `strip`, ≤150 caracteres (limite da coluna), não vazio |
| Categoria | `category` | **SIM** | Deve ser valor válido do vocabulário `AssetCategory` |
| Marca / Fabricante | `brand` | **SIM** | ≤100 caracteres |
| Modelo | `model` | **SIM** | ≤100 caracteres |
| Nº de Série | `serial_number` | **SIM** | ≤100 caracteres; **único** (excluindo o próprio bem) — mensagem atual "Já existe um equipamento com o número de série '...'" |
| Especificações Técnicas | `specifications` | **SIM** | Texto livre |
| Data de compra / Valor / NF / Fornecedor / Garantia | `purchase_date`, `purchase_value`, `invoice_number`, `supplier`, `warranty_expiry` | **SIM** | Valor **≥ 0**; datas válidas; `invoice_number` ≤100; `supplier` ≤150 |
| Condição de conservação | `condition` | **SIM** (P2 aprovada) | Valor do vocabulário `AssetCondition`; ao mudar, gera movimentação `ATUALIZACAO_ESTADO` **com o operador autenticado** |
| Observações | `notes` | **SIM** | Texto livre |
| **Tombamento / Tag** | `tag` | **NÃO** | Identificador patrimonial crítico: imutável nesta feature (P1 aprovada); alteração exigirá procedimento próprio |
| **Situação patrimonial** | `status` | **NÃO** | Continua exclusivamente pelo motor de movimentações |
| **Localização / Unidade / Departamento** | `location_id` (→ `Location.branch/department`) | **NÃO** | Somente pelo fluxo de movimentação |
| **Custodiante / Responsável** | `custodian_id` | **NÃO** | Somente pelo fluxo de movimentação |
| Criação/atualização | `created_at`, `updated_at` | **NÃO** | Gerenciados pelo sistema |

**Regra de integridade**: o backend **ignora** qualquer campo não autorizado enviado na requisição (não basta esconder no formulário) — a lista fechada acima é aplicada no schema/serviço.

### 4.4 Edição: fluxo, validação e erros (RF08)

| Situação | Comportamento esperado |
|---|---|
| Campos obrigatórios inválidos (nome vazio) | Rejeitar com mensagem no formulário; **nada gravado** |
| Nº de série duplicado | Rejeitar com a mensagem de unicidade existente; **nada gravado** |
| Valor de aquisição negativo | Rejeitar com mensagem clara; **nada gravado** |
| Texto acima do limite da coluna | Rejeitar com mensagem clara (sem truncamento silencioso) |
| Sem permissão (interface ou requisição direta) | 403 + `ACESSO_NEGADO` na trilha; **nada gravado** |
| Bem inexistente ou removido no meio da edição | 404 amigável; **nada gravado** |
| Falha de gravação (ex.: banco indisponível) | Rollback completo: nenhum campo parcialmente atualizado e **nenhum registro de auditoria órfão** (alteração e trilha na mesma transação) |
| Conflito entre edições concorrentes | Detectado e informado ao usuário (o registro mudou desde que o formulário foi aberto); **sem sobrescrita silenciosa** (P3 aprovada: controle otimista por `updated_at`) — **escopo: formulário web de edição**; a API `PUT` mantém o contrato atual |
| Salvar sem alterações | Informar que nada mudou; **não** gravar auditoria vazia; não gerar movimentação |
| Cancelamento | Voltar ao detalhe sem gravar nada |
| Edição de bem `BAIXADO` | **Bloqueada** (P4 aprovada): mensagem clara e nenhuma gravação |
| Requisição manipulada com `tag`/`status`/`location_id`/`custodian_id` | Campo ignorado; registro permanece íntegro; tentativa registrada na trilha (quando aplicável) |

Mensagens de erro **não** expõem detalhes internos (SQL, stack, nomes de tabela) — apenas mensagem de negócio no padrão atual (`?error=`/alert Bootstrap).

### 4.5 Histórico de alterações (RF06/RF07)

1. **Gravação**: cada edição bem-sucedida grava **um** evento na trilha `audit_logs` com: bem (`resource_id`/`resource_ref`), usuário autenticado (`user_id` + `username` snapshot), data/hora, campos alterados (com valores anterior e novo). Reutiliza `write_change_audit` — **não** há segundo mecanismo.
2. **Identificação e atomicidade**: a alteração do cadastro e o registro de auditoria na **mesma transação**; falha em qualquer etapa desfaz ambas.
3. **Confiabilidade**: o registro é derivado do estado **persistido** (before lido do banco e after do resultado da gravação), nunca do que o navegador enviou.
4. **Consulta**: a tela de detalhes passa a apresentar o histórico de alterações cadastrais de forma legível (campo → de → para) e **separada** das movimentações patrimoniais (o usuário distingue visualmente "alteração cadastral" de "movimentação").
5. **Ausência de histórico**: quando não houver eventos, exibir estado vazio claro ("nenhuma alteração cadastral registrada") — sem erro e sem informação enganosa (o cadastro inicial não é uma alteração; ele já é representado pela movimentação `ENTRADA_AQUISICAO`).
6. **Movimentações geradas por edição** (mudança de condição) aparecem no fluxo de movimentações, como hoje, com o operador correto.
7. **Limite e transparência**: o histórico cadastral exibe os **50 eventos mais recentes** (mesmo teto da trilha atual); havendo mais, o sistema avisa que existem eventos anteriores não listados — sem truncamento silencioso (FR-016).

---

## 5. User Scenarios & Testing *(mandatory)*

### User Story 1 — Consulta detalhada do bem (Priority: P1)

Como usuário com `patrimonio.visualizar`, ao clicar em "Ver Detalhes" de um bem (na listagem, na busca ou lendo o QR Code da etiqueta), quero ver **todos** os dados cadastrais — inclusive os que não aparecem na listagem e os que não aparecem hoje na tela — para conferir a situação real do bem sem precisar consultar a API ou abrir o banco.

**Why this priority**: É a base do ciclo de manutenção cadastral e a única das três necessidades que já tem tela: entregar só isto já resolve "o usuário não consegue consultar os dados técnicos completos".

**Independent Test**: abrir `/assets/{id}` de um bem com marca, modelo, nº de série, especificações, observações e dados fiscais preenchidos e conferir todos os campos, sem qualquer edição.

**Acceptance Scenarios**:
1. **Given** um bem com marca, modelo, nº de série e especificações cadastrados, **When** o usuário abre o detalhe, **Then** todos esses valores aparecem corretamente, sem truncamento e sem inventar dado.
2. **Given** um bem com observações cadastradas, **When** o detalhe é aberto, **Then** as observações são exibidas.
3. **Given** um bem sem especificações (vazio), **When** o detalhe é aberto, **Then** o campo aparece como não informado/marcado como vazio, nunca com dado fictício.
4. **Given** um bem com localização e custodiante atuais, **When** o detalhe é aberto, **Then** localização (com unidade/departamento) e responsável são exibidos conforme o cadastro atual.
5. **Given** um usuário sem `patrimonio.visualizar`, **When** ele tenta `/assets/{id}`, **Then** recebe 403 (e o acesso é registrado na trilha).
6. **Given** um ID inexistente, **When** acessado, **Then** 404 amigável.

### User Story 2 — Edição controlada dos dados cadastrais (Priority: P2)

Como usuário com `patrimonio.editar` (ex.: Patrimônio / Gestor de TI), na tela de detalhes de um bem com um dado errado ou desatualizado, quero clicar em **"Editar bem"**, corrigir os campos permitidos e salvar, para manter o cadastro correto **sem recadastrar o bem** e **sem mexer** na localização, na custódia ou na situação (que têm fluxo próprio).

**Why this priority**: É a necessidade central do prompt e a lacuna registrada em `specs/001` §11 item 3; depende da consulta (US1) apenas como ponto de partida.

**Independent Test**: autenticado com `patrimonio.editar`, abrir `/assets/{id}/edit`, alterar nome/marca/modelo/nº de série/especificações, salvar e conferir o mesmo `id` (nenhum bem novo) com os valores atualizados no detalhe e na listagem.

**Acceptance Scenarios**:
1. **Given** um bem existente e usuário com `patrimonio.editar`, **When** ele altera nome, marca, modelo, nº de série e especificações e salva, **Then** o **mesmo registro** (mesmo `id` e mesmo tombamento) passa a exibir os novos valores e o bem **não é duplicado** (contagem de bens inalterada).
2. **Given** campos válidos, **When** o formulário é salvo, **Then** as validações existentes são aplicadas (nome obrigatório, nº de série único, limites de tamanho, valor não negativo).
3. **Given** um nº de série já usado por outro bem, **When** o usuário tenta salvar, **Then** recebe a mensagem de duplicidade e o registro **não** é alterado.
4. **Given** um usuário sem `patrimonio.editar`, **When** ele abre ou envia `/assets/{id}/edit`, **Then** 403 (interface e requisição direta) e nada é gravado.
5. **Given** uma requisição manipulada enviando `tag`, `status`, `location_id` e `custodian_id`, **When** processada, **Then** esses campos são ignorados e o tombamento/situação/local/custódia permanecem iguais.
6. **Given** uma edição que muda a `condition`, **When** salva, **Then** uma movimentação `ATUALIZACAO_ESTADO` é gerada com o **operador autenticado** e o cadastro atualizado.
7. **Given** um formulário aberto e sem alterações efetivas, **When** o usuário salva, **Then** o sistema informa que nada mudou e não grava auditoria nem movimentação.
8. **Given** falha de gravação simulada, **When** o salvamento falha, **Then** nenhum campo fica alterado e não há evento de auditoria correspondente.

### User Story 3 — Histórico de alterações cadastrais consultável (Priority: P3)

Como gestor/auditor, na tela de detalhes do bem, quero ver **quem alterou o quê, quando, de qual valor para qual valor** — separado das movimentações — para reconstituir a história cadastral do bem sem abrir a trilha de auditoria do sistema.

**Why this priority**: Fecha o ciclo de rastreabilidade (RNF do prompt) e reaproveita integralmente a trilha existente; agrega valor mesmo sem edição web (as alterações feitas por API/importação já aparecem).

**Independent Test**: alterar um campo pela edição (ou pela API), abrir o detalhe e conferir o evento com campo, valor anterior, valor novo, usuário e data.

**Acceptance Scenarios**:
1. **Given** um bem recém-cadastrado sem alterações, **When** o histórico é consultado, **Then** aparece o estado vazio "nenhuma alteração cadastral registrada" (sem erro).
2. **Given** uma alteração válida de `brand` de "Dell" para "Lenovo", **When** o histórico é consultado, **Then** o evento mostra campo, de "Dell", para "Lenovo", usuário e data/hora.
3. **Given** um bem com movimentações e alterações cadastrais, **When** o histórico é consultado, **Then** os dois tipos aparecem **distinguidos** (alteração cadastral × movimentação), na ordem cronológica decrescente.
4. **Given** uma alteração feita por outro usuário, **When** o histórico é consultado, **Then** o autor informado é o usuário autenticado que executou a operação (não "Sistema").

### Edge Cases

- **Tombamento manipulado no POST**: ignorado; valor anterior preservado (o campo não está no schema de edição).
- **Nº de série apagado (vazio)**: permitido (coluna nullable) — desde que não haja outro bem usando o mesmo valor.
- **Nº de série com espaços/caixa diferentes**: aplicado `strip`; a unicidade é **comparação exata após `strip` (case-sensitive)** — comportamento atual preservado por decisão desta feature; **não** se amplia para unicidade case-insensitive.
- **Nome só com espaços**: rejeitado como vazio.
- **Duas abas editando o mesmo bem**: a segunda gravação deve avisar conflito em vez de sobrescrever (P3 aprovada).
- **Bem `BAIXADO`**: edição **bloqueada** (P4 aprovada), sem gravação.
- **Bem com inventário aberto/encerrado**: a edição **não** altera itens, resultados ou lista esperada do inventário (somente leitura pelo inventário); o efeito sobre a ata segue a P5 aprovada (comportamento atual mantido; dívida M-003).
- **Bem com movimentações**: nenhuma movimentação histórica é editada ou apagada; apenas a condição pode gerar um **novo** evento.
- **Falha de JavaScript**: o formulário continua funcional (validação e gravação são do servidor).
- **Sem alterações**: mensagem informativa, sem gravação.
- **Valor de aquisição com vírgula decimal** (formulário brasileiro): interpretado corretamente ou rejeitado com mensagem clara (padrão atual do formulário de cadastro).

---

## 6. Requirements *(mandatory)*

### Functional Requirements

| Requisito (prompt) | FR | Descrição |
|---|---|---|
| RF01 | **FR-001** | A tela `/assets/{id}` MUST apresentar todos os dados cadastrais do bem em seções legíveis: identificação (tombamento, nome, categoria, situação, condição), ficha técnica (marca, modelo, nº de série, especificações), aquisição/fiscal (data, valor, NF, fornecedor, garantia), observações, localização/unidade/departamento, custodiante, depreciação e etiqueta/QR. |
| RF01 | **FR-002** | Campos vazios MUST ser exibidos como "não informado"/omitidos — o sistema MUST NOT apresentar valor inexistente como cadastrado. |
| RF01 | **FR-003** | A consulta detalhada MUST exigir `patrimonio.visualizar`; bem inexistente MUST responder 404 amigável. |
| RF02 | **FR-004** | A tela de detalhes MUST oferecer a ação "Editar bem" visível apenas com `can('patrimonio.editar')`, conduzindo a `/assets/{id}/edit`. |
| RF02 | **FR-005** | O acesso à edição (GET e POST) MUST ser autorizado no backend por `require_permission("patrimonio.editar")` (deny by default; 403 registrado na trilha; 404 para bem inexistente). |
| RF03 | **FR-006** | MUST ser possível editar: `name`, `category`, `brand`, `model`, `serial_number`, `specifications`, `purchase_date`, `purchase_value`, `invoice_number`, `supplier`, `warranty_expiry`, `condition` e `notes`, preservando obrigatoriedade, limites de tamanho e validações existentes. |
| RF03 | **FR-007** | O formulário de edição MUST reutilizar os componentes, o layout e as validações do formulário de cadastro existente (`assets/form.html`) e delegar a regra ao service — sem lógica de negócio no template/rota (Constitution II/III). |
| RF03 | **FR-008** | A edição MUST atualizar o registro existente: MUST NOT criar novo bem, MUST NOT alterar `id` nem gerar movimentação `ENTRADA_AQUISICAO` adicional. |
| RF04 | **FR-009** | O tombamento (`tag`) MUST permanecer imutável nesta feature: MUST NOT existir campo editável na interface, MUST NOT constar do schema de edição e requisições manipuladas com `tag` MUST ser ignoradas. |
| RF04 | **FR-010** | O sistema MUST NOT permitir duplicidade de tombamento (garantida pela restrição `UNIQUE` existente) nem de número de série (validação de unicidade existente no service, excluindo o próprio bem). |
| RF05 | **FR-011** | Situação (`status`), localização (`location_id`) e custódia (`custodian_id`) MUST NOT ser alteráveis pela edição cadastral; alterações dessas propriedades MUST continuar ocorrendo exclusivamente pelo motor de movimentações. |
| RF05 | **FR-012** | Se a edição alterar `condition`, o sistema MUST gerar a movimentação de `ATUALIZACAO_ESTADO` correspondente com o **operador autenticado** (não "Sistema") e a justificativa registrada — mantendo o padrão da feature 065. |
| RF06 | **FR-013** | Cada edição efetiva MUST registrar **um** evento na trilha `audit_logs` (ação `ALTERACAO`), reutilizando `write_change_audit`, com: bem (`resource_id` + `resource_ref`), usuário autenticado (id + username), data/hora, campos alterados e valores anterior/novo. |
| RF06 | **FR-014** | O registro de auditoria MUST derivar do estado persistido (before do banco, after do resultado gravado) — nunca de dados arbitrários enviados pelo navegador — e MUST NOT incluir credenciais. |
| RF06 | **FR-015** | A alteração do cadastro e o registro de auditoria MUST ser atômicos (mesma transação): falha em qualquer etapa MUST desfazer ambas, sem dado parcialmente atualizado nem trilha órfã. |
| RF07 | **FR-016** | A tela de detalhes MUST apresentar o histórico de alterações cadastrais de forma legível (campo, valor anterior, valor novo, usuário, data/hora), **distinguido** das movimentações patrimoniais, exibindo os **50 eventos mais recentes** e avisando explicitamente quando houver eventos anteriores não listados (nunca truncar em silêncio). |
| RF07 | **FR-017** | Sem eventos de alteração cadastral, MUST ser exibido estado vazio claro, sem erro e sem informação enganosa (o cadastro inicial não é alteração — é a `ENTRADA_AQUISICAO`). |
| RF08 | **FR-018** | Erros de obrigatoriedade, unicidade de série, limites de tamanho, valor negativo, ausência de permissão, bem inexistente, falha de gravação e conflito de edição concorrente MUST ser tratados com mensagem amigável, sem gravação parcial e sem expor detalhes internos. O conflito de edição concorrente é tratado no **fluxo web de edição** (P3); a API `PUT` preserva o contrato atual, sem parâmetro de versão. |
| RF08 | **FR-019** | Salvar sem alterações efetivas MUST informar o usuário e MUST NOT gravar auditoria nem movimentação; cancelar MUST voltar ao detalhe sem gravar. |
| RF09 | **FR-020** | Consulta e edição MUST seguir o padrão visual existente (Bootstrap 5, tema claro/escuro, `can()`, alertas, 403/404 amigáveis, central de ajuda) e MUST ser responsivas em telas estreitas, sem redesenho fora do escopo. |
| RF10 | **FR-021** | Edição cadastral MUST NOT alterar: cadastro de bens, listagens/buscas/filtros, movimentações e transferências, custódia e localização, inventários (itens, resultados e listas esperadas), relatórios contábeis/patrimoniais, exportações CSV/Excel, geração de documentos/termos, permissões e auditoria, importação de dados. |
| RF10 | **FR-022** | Documentos e históricos já emitidos MUST NOT ser alterados silenciosamente por uma edição cadastral: termos (snapshots de movimentação) e listas esperadas de inventário permanecem congelados; o efeito hoje existente sobre a ata (leitura viva de `tag`/`name`/`category`) MUST permanecer como hoje nesta feature (P5 aprovada), com a dívida (snapshots de `name`/`tag`/`category` no item de inventário) registrada para feature própria. |
| — | **FR-023** | A implementação MUST ser incremental e cirúrgica (Constitution I): alterar apenas template de detalhes, novo template de edição, router web de bens, service/schema de bens, testes, manifesto de rotas e documentação visível — sem refatorações não relacionadas. |
| — | **FR-024** | A suíte pytest existente MUST permanecer verde (nenhum teste removido, enfraquecido ou pulado) e novos testes MUST cobrir AC01–AC15 (Constitution VIII). |

### Key Entities

- **Bem patrimonial (`Asset`, tabela `assets`)**: entidade editada. Identidade patrimonial: `tag` (única, imutável nesta feature). Dados cadastrais editáveis: `name`, `category`, `brand`, `model`, `serial_number` (único quando informado), `specifications`, `purchase_date`, `purchase_value`, `invoice_number`, `supplier`, `warranty_expiry`, `condition`, `notes`. Propriedades protegidas: `status`, `location_id`, `custodian_id`. Metadados: `created_at`, `updated_at`.
- **Localização (`Location`)**: origem de `branch`/`department` exibidos no detalhe; só acessível para leitura por esta feature.
- **Custodiante (`Custodian`)**: responsável atual exibido no detalhe; só leitura por esta feature.
- **Movimentação (`Movement`)**: motor de alteração de localização/custódia/situação/condição; recebe um novo evento quando a edição muda `condition`. Imutável para esta feature.
- **Trilha de auditoria (`AuditLog`, tabela `audit_logs`)**: registro das alterações cadastrais (ação `ALTERACAO`), consultada no detalhe; somente leitura, sem escrita/exclusão.
- **Item de inventário (`InventarioItem`)**: consome os dados do bem (lista esperada + ata); MUST NOT ser alterado pela edição.
- **Relação com o objeto de autorização**: permissões existentes `patrimonio.visualizar` e `patrimonio.editar` (nenhuma permissão nova).

---

## 7. Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos campos cadastrais previstos no §4.1 ficam visíveis na tela de detalhes de um bem (verificado por teste de render com bem completo e com bem mínimo).
- **SC-002**: Uma correção cadastral completa pode ser feita pela interface **sem tocar em API/banco** e **sem criar registro novo** (contagem de bens inalterada antes/depois).
- **SC-003**: 100% das tentativas de edição sem `patrimonio.editar` — pela interface e por requisição direta ao endpoint — são negadas (403) e registradas na trilha; 0 registros alterados.
- **SC-004**: 100% das edições efetivas geram exatamente 1 evento de auditoria com valores anterior e novo; 0 alterações efetivadas sem evento correspondente (teste de falha simulada).
- **SC-005**: 100% das requisições manipuladas com `tag`, `status`, `location_id` ou `custodian_id` deixam esses campos inalterados.
- **SC-006**: Após qualquer edição cadastral, a contagem de movimentações `ENTRADA_AQUISICAO` e o conjunto de movimentações existentes permanecem idênticos (exceto o novo evento de condição, quando aplicável).
- **SC-007**: 0 alterações em `InventarioItem`, `Movement` (históricos) e documentos/termos já emitidos por efeito de edição cadastral.
- **SC-008**: Suíte pytest completa verde, com os novos testes da feature passando (sem enfraquecer testes existentes).
- **SC-009**: A consulta detalhada é servida **sem novas consultas N+1** (nenhuma consulta adicional além das de `AssetService.get_by_id`, que já usa `joinedload`) e responde em **< 1 s** no ambiente de referência — medido na verificação de T028.
- **SC-010**: A tela de detalhes e o formulário de edição permanecem utilizáveis de **360 px** (mobile) até desktop, nos breakpoints Bootstrap `sm`/`md`, sem sobreposição de conteúdo (verificado em T028).

---

## 8. Compatibilidade (requisitos derivados da análise)

- **API REST**: o contrato de `PUT /api/v1/assets/{id}` é **preservado** (mesmos campos de `AssetUpdate`, mesmas respostas). As correções previstas (validações e operador autenticado na movimentação de condição) são correções de comportamento interno, não mudança de contrato — as decisões P1/P2 aprovadas mantêm o schema `AssetUpdate` intacto (nenhum campo novo).
- **Autorização**: nenhuma permissão nova e nenhum perfil novo (Constitution VI). `patrimonio.visualizar` e `patrimonio.editar` já existem e já são concedidas a Administrador, Gestor de TI e Patrimônio.
- **Movimentações**: motor intocado; edição cadastral não cria atalho para localização/custódia/situação.
- **Inventário**: leitura pura; lista esperada e resultados intactos (Constitution V).
- **Auditoria**: trilha única reutilizada; sem segundo mecanismo (Constitution IX) e sem credenciais.
- **Banco**: **zero DDL, zero migração** (Constitution VII) — todos os campos já existem em `assets`.
- **Rotas**: a rota nova altera o inventário de rotas → `tests/route_manifest.json` MUST ser atualizado na mesma tarefa (feature 051 exige o manifesto como prova de não regressão).
- **Documentação**: `docs/ARQUITETURA_E_MANUTENCAO.md` e central de ajuda (`/ajuda`) MUST registrar a nova tela/editar bem (Constitution XI).
- **Multiplataforma**: compatível com MariaDB/MySQL e com os ambientes Windows/Linux do projeto — sem dependência nova, sem SQL específico de plataforma.

---

## 9. Alternativas avaliadas

| Alternativa | Descrição | Veredito |
|---|---|---|
| **A — Estender a tela de detalhes existente + formulário de edição web reutilizando `AssetService.update`/`AssetUpdate` + trilha atual** | Menor mudança que fecha as três lacunas (consulta incompleta, ausência de edição web, histórico pouco legível), sem nova permissão, sem DDL e sem mecanismo de auditoria paralelo | ✅ **ESCOLHIDA** |
| B — Criar tela de edição "do zero" (novo template, novas validações, novo service) | Duplicaria regras e validações existentes (viola Constitution II/III e I) | ❌ Descartada |
| C — Manter a edição só na API e apenas documentar | Não resolve a lacuna registrada em `specs/001` §11.3; usuário continuaria preso | ❌ Descartada |
| D — Fazer a edição dentro do próprio formulário de cadastro (`/assets/new` reaproveitado para editar) | Mistura criação e edição no mesmo fluxo, com risco de duplicação acidental e perda de clareza de permissão (`criar` × `editar`) | ❌ Descartada |
| E — Tabela própria de histórico cadastral (`asset_change_history`) | Duplicaria a trilha existente, com risco de divergência e mais DDL | ❌ Descartada (usar `audit_logs`) |
| F — Criar permissão nova (ex.: `patrimonio.editar_dados` ou `patrimonio.editar_tombamento`) | Não há necessidade demonstrada: `patrimonio.editar` já existe, já está descrita como "Editar dados cadastrais de bens" e já é concedida a perfis coerentes | ❌ Descartada (Constitution VI) |
| G — Permitir alteração de tombamento junto com a edição | Alteraria identificador patrimonial referenciado por etiquetas impressas, QR, importação (dedupe) e histórico; exige procedimento próprio | ❌ Descartada nesta feature (P1 aprovada: tombamento imutável) |

---

## 10. Critérios de aceitação

- **AC01 — Consulta completa**: um usuário autorizado consulta todos os dados cadastrais relevantes de um bem na tela de detalhes (incluindo marca, modelo, nº de série, especificações, observações e última atualização).
- **AC02 — Dados técnicos corretos**: os campos técnicos cadastrados são apresentados sem truncamento; campos vazios aparecem como não informados.
- **AC03 — Edição permitida**: um usuário com `patrimonio.editar` altera os campos do §4.3 e vê o resultado refletido no detalhe e na listagem.
- **AC04 — Validações aplicadas**: obrigatoriedade, unicidade de nº de série, limites de tamanho e valor não negativo são aplicados na edição (comportamento equivalente ao cadastro/API).
- **AC05 — Sem duplicação**: a edição atualiza o registro existente; a contagem de bens e o tombamento permanecem os mesmos.
- **AC06 — Tombamento protegido**: não há meio, pela interface ou por requisição direta, de alterar o tombamento de um bem; duplicidade de tombamento continua impossível.
- **AC07 — Autorização efetiva**: usuários sem `patrimonio.editar` não conseguem editar nem pela interface nem por requisição direta (403 + registro na trilha); usuários sem `patrimonio.visualizar` não consultam o detalhe.
- **AC08 — Auditoria gerada**: toda alteração válida gera evento de auditoria com usuário, data/hora, campos e valores anterior/novo, na mesma transação da alteração.
- **AC09 — Histórico correto**: o histórico exibe valores anteriores e novos corretamente e distingue alterações cadastrais de movimentações; sem eventos, exibe estado vazio claro.
- **AC10 — Histórico preservado**: a edição não modifica retroativamente movimentações, termos, itens/atas de inventário nem listas esperadas já geradas (P5 aprovada: ata/exportações seguem com leitura viva; snapshots são dívida M-003).
- **AC11 — Sem estado parcial**: falha de gravação não deixa dados parcialmente atualizados nem evento de auditoria órfão.
- **AC12 — Movimentação e custódia íntegras**: os fluxos de movimentação, transferência e custódia continuam funcionando; localização/custódia/situação não são alteráveis pela edição cadastral.
- **AC13 — Relatórios e exportações**: comportamentos e contratos de relatórios, CSVs, Excel e documentos permanecem os existentes (suíte de regressão verde).
- **AC14 — Responsividade**: detalhe e formulário de edição funcionam de **360 px** a desktop (`col-12 col-md-*`), verificados na T028.
- **AC15 — Não regressão**: os testes existentes continuam passando, incluindo `tests/test_route_inventory.py` com o manifesto atualizado.

---

## 11. Arquivos provavelmente envolvidos

| Arquivo | Alteração prevista (na implementação futura) |
|---|---|
| `app/web/templates/assets/detail.html` | **ALTERAR**: ação "Editar bem" condicionada; exibir `notes` e `updated_at`; seção/aba de histórico cadastral separada das movimentações |
| `app/web/templates/assets/list.html` | **ALTERAR (polimento opcional aprovado)**: ação "Editar" na linha, visível só com `can('patrimonio.editar')` e oculta para bem baixado (P4) — sem alterar filtros, busca ou paginação |
| `app/web/templates/assets/form.html` | **REUTILIZAR** como base visual/estrutural (não obrigatório alterar) |
| `app/web/templates/assets/edit.html` | **NOVO**: formulário de edição com os campos do §4.3, valores atuais preenchidos, campo oculto de versão e área de erro (T011) |
| `app/web/routers/assets.py` | **ALTERAR**: `GET /assets/{asset_id}/edit` (`patrimonio.editar`) e `POST /assets/{asset_id}/edit` (`patrimonio.editar`), delegando ao service + auditoria |
| `app/services/asset_service.py` | **ALTERAR**: `update` com validações (nome/limites/valor ≥ 0), operador autenticado na movimentação de condição e retorno do "nada mudou"; helper de leitura `get_cadastral_history` |
| `app/services/audit_service.py` | **ALTERAR (aditivo)**: parâmetro `commit: bool = True` em `write_audit`/`write_change_audit` — o default preserva todo comportamento atual (research R5, FR-015) |
| `app/schemas/asset.py` | **INTOCADO**: `AssetUpdate` permanece com os mesmos campos e **sem restrições novas** — as validações V1–V3 vivem no service (research R3, §8) |
| `app/services/movement_service.py` | **NÃO ALTERADO** (somente leitura): `get_timeline_for_asset` permanece como está para preservar o contrato de `GET /api/v1/assets/{id}/timeline` (research R6); o histórico cadastral usa leitura nova em `AssetService` |
| `app/api/assets_api.py` | **ALTERAR (mínimo, sem mudança de contrato)**: no `PUT /api/v1/assets/{asset_id}`, passar o **operador autenticado** a `AssetService.update` (research R4, FR-012), mantendo campos aceitos, resposta e códigos |
| `tests/route_manifest.json` | **ALTERAR**: registrar as novas rotas web (exigência de `tests/test_route_inventory.py`) |
| `tests/test_consulta_edicao_bens_067.py` | **NOVO**: AC01–AC15 da feature |
| `tests/test_assets.py` | **ESTENDER**: cobertura do operador autenticado/validações no service |
| `docs/ARQUITETURA_E_MANUTENCAO.md` | **ALTERAR**: seção de bens — detalhe e edição controlada (Constitution XI) |
| `app/services/help_service.py` (central de ajuda `/ajuda`) | **ALTERAR**: artigo de bens mencionando consulta detalhada e edição controlada (T022) |

**Intactos**: `app/schemas/asset.py` (sem campos/restrições novas), `app/models/asset.py`, `app/models/inventario.py`, `app/models/movement.py`, `app/services/movement_service.py` (motor de movimentação), `app/services/report_service.py`, `app/services/import_service.py`, `app/services/inventario_service.py`, `app/api/deps.py`, `app/services/permission_service.py` (nenhuma permissão nova), templates de movimentações/relatórios/inventário.

---

## 12. Plano mínimo de testes

**Regressão obrigatória (sem alterar asserções existentes)**: `test_assets.py` (**somente adição** de testes novos — T014), `test_api.py`, `test_rbac.py`, `test_route_inventory.py` (com manifesto atualizado), `test_import_asset_location.py`, `test_import_asset_movements.py`, `test_movements.py`, `test_localizacao_automatica_066.py`, `test_presentacao_trilha_063.py`, `test_fluxo_global_064.py`; **relatórios, exportações e documentos (AC13)**: `test_locations_export.py`, `test_report_print_smoke.py`, `test_inventario.py`, `test_datetime_flows.py` (ata CSV); + régua completa `python -m pytest`.

**Novos testes** (provável `tests/test_consulta_edicao_bens_067.py`, fixtures `client`/`db_session` de `tests/conftest.py`, SQLite in-memory):

| Teste | Protege |
|---|---|
| `test_detalhe_exibe_dados_completos` | AC01/AC02 (todos os campos, incluindo `notes` e `updated_at`) |
| `test_detalhe_omite_campos_vazios` | AC02 (nada de dado fictício) |
| `test_detalhe_404_bem_inexistente` / `test_detalhe_403_sem_permissao` | AC07/AC03 (FR-003) |
| `test_editar_bem_sem_permissao_nega_e_audita` | AC07 (interface e requisição direta; `ACESSO_NEGADO`) |
| `test_editar_bem_autorizado_atualiza_mesmo_registro` | AC03/AC05 (mesmo `id`, sem bem novo, contagem inalterada) |
| `test_edicao_serial_duplicado_rejeitada` | AC04/AC06 (unicidade) |
| `test_edicao_valida_limites_e_valor_negativo` | AC04 (limites de tamanho; valor ≥ 0) |
| `test_edicao_ignora_campos_protegidos_manipulados` | AC06/AC12 (`tag`/`status`/`location_id`/`custodian_id`) |
| `test_edicao_grava_auditoria_com_before_after` | AC08 (evento único com valores anterior/novo e autor) |
| `test_edicao_sem_alteracao_nao_grava` | AC11/RF-019 (sem auditoria vazia, sem movimentação) |
| `test_edicao_falha_nao_deixa_estado_parcial` | AC11 (transação única: rollback + ausência de trilha órfã) |
| `test_put_api_grava_operador_autenticado_na_condicao` | AC12/FR-012 no fluxo da **API** (`PUT /api/v1/assets/{id}` grava o operador autenticado na movimentação de condição) |

**Verificação de FR-020/SC-009/SC-010** (responsividade e desempenho): cenário manual `quickstart §2.18` em **360 px** e desktop + conferência das classes responsivas (`col-12 col-md-*`) nos templates alterados, e contagem de consultas do detalhe sem N+1 novo — registrada em `validacao.md` pela **T028**.
| `test_alteracao_de_condicao_gera_movimentacao_com_operador_autenticado` | AC12/FR-012 (padrão 065) |
| `test_historico_cadastral_separado_de_movimentacoes` | AC09/AC10 |
| `test_historico_vazio_sem_erro` | AC09 (estado vazio) |
| `test_put_api_mantem_contrato` | AC13 (API segue aceitando o payload atual) |

**Procedimento**: suíte em SQLite in-memory (padrão da casa); nenhuma escrita em banco real; validação manual opcional no ambiente com `DATABASE_URL` **apenas em leitura** (contagens antes/depois). `tests/test_route_inventory.py` MUST ser executado após atualizar o manifesto. Se o isolamento do banco de testes não estiver comprovado, nenhum teste destrutivo deve ser executado.

---

## 13. Riscos e medidas de mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Edição alterar documento histórico (ata lê `tag`/`name`/`category` ao vivo) | **Alto** (prova documental) | **P5 aprovada**: manter o comportamento atual nesta feature, com a limitação documentada e dívida M-003 registrada; testes que verificam integridade de `InventarioItem` e do conteúdo de movimentações (AC10) |
| Edição contornar o motor de movimentações (local/custódia/situação) | **Alto** (Constitution IV) | Campos fora do schema + teste de requisição manipulada (AC06/AC12) |
| Alteração sem auditoria (commit separado) | **Alto** (rastreabilidade) | FR-015: transação única + teste de falha simulada (AC08/AC11) |
| Usuário sem permissão editar por requisição direta | Alto | `require_permission("patrimonio.editar")` no backend + teste de 403 (AC07) |
| Regressão em movimentações, inventário, relatórios e exportações | Alto | Escopo cirúrgico (§11) + régua de regressão (§12); nenhum arquivo desses domínios alterado |
| `test_route_inventory.py` quebrar por rota nova | Médio | Atualização do `route_manifest.json` como tarefa explícita (AC15) |
| Perda de digitação/erro do usuário sobrescrevendo valor correto | Médio | Conflito de edição (P3) + confirmação do que muda + auditoria before/after legível |
| Validações novas quebrarem a API existente | Médio | Alterar apenas `AssetUpdate` com restrições compatíveis + teste de contrato da API (AC13) |
| Regra para bem `BAIXADO` **definida** (bloquear — P4 aprovada) | Médio | Coberta por T010/T012 (recusa com mensagem, sem gravação) |
| Escopo inflar (exclusão, edição de locais, redesign) | Médio | §3 "NÃO INCLUI" + tabela §11 fechada no diff final |
| Edição simultânea (duas abas) | Baixo/Médio | P3 aprovada: controle otimista por `updated_at` (T005/T010/T011) |

---

## 14. Pendências P1–P5 — decididas em 2026-10-10

- **P1 — Tombamento (`tag`)**: ✅ **APROVADA (2026-10-10): imutável** — a alteração do tombamento **fica fora desta feature**; a mudança exigirá procedimento próprio (rastreamento de etiquetas/QR impressos, reindexação da importação por tombamento, auditoria específica com valores anterior/novo e preservação do histórico). **Alternativa descartada**: permitir somente para `Administrador`, com trilha dedicada.
- **P2 — Condição (`condition`) no formulário de edição**: ✅ **APROVADA (2026-10-10): continua editável na ficha**, gerando a movimentação `ATUALIZACAO_ESTADO` **com o operador autenticado** e justificativa indicada; a alternativa de remover `condition` do formulário e exigir a movimentação de vistoria (fluxo próprio) foi descartada (ver Clarifications).
- **P3 — Conflito de edições concorrentes**: ✅ **APROVADA (2026-10-10): controle otimista** — o formulário carrega o `updated_at` e, se o registro mudou antes do salvamento, a gravação é recusada com aviso ("o bem foi alterado por outro usuário; recarregue e refaça a edição"), sem sobrescrita silenciosa (implementável sem DDL, pois `updated_at` já existe). **Alternativa descartada**: "last write wins" documentado (mais simples, porém perde a alteração alheia em silêncio).
- **P4 — Edição de bem `BAIXADO`**: ✅ **APROVADA (2026-10-10): bloquear** a edição de bem `BAIXADO` (coerente com a UI atual, que esconde Movimentar/Manutenção e com a noção de registro encerrado), com mensagem clara e possibilidade de correção por procedimento administrativo próprio (ver Clarifications).
- **P5 — Ata de inventário e exportações (leitura viva × snapshot)**: ✅ **APROVADA (2026-10-10): manter o comportamento atual nesta feature** (ata de inventário **já encerrado** reflete `tag`/`name`/`category` atuais, e o CSV de movimentações reflete o nome atual do bem), documentando a consequência; a alternativa (b) — congelar esses dados (snapshot de `name`/`tag`/`category` no `InventarioItem` e/ou nos documentos) — seria mudança de escopo com DDL aditivo e tarefa própria, **descartada nesta feature**. **Decisão aprovada (a)**: nesta feature — **sem alterar** a estrutura de inventário/relatórios — com o risco explicitamente registrado (AC10 e SC-007) e item (b) remetido a feature própria (ver Clarifications).

**Limitações desta execução**: apenas leitura — nenhum arquivo funcional foi alterado, nenhuma migração foi executada, nenhum teste foi escrito, nenhuma dependência foi instalada, nenhum commit/push foi feito. Nenhuma funcionalidade foi implementada: esta spec **não** cria rota, template, campo, tabela nem permissão; ela apenas delimita o que deverá ser feito após aprovação (Restrição do briefing: "Analise primeiro. Especifique depois. Não implemente."). As decisões **P1–P5** acima foram aprovadas pelo responsável e registradas em 2026-10-10 (ver Clarifications).

---

**Próximo passo**: aprovação final da spec e implementação pelo `tasks.md` (Setup → Foundational → US1 → US2 → US3 → Polish), dentro do escopo §11 e conforme as decisões P1–P5 registradas acima.
