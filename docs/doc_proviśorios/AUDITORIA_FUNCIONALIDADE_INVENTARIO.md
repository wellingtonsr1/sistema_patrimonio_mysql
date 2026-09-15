# RELATÓRIO DE AUDITORIA TÉCNICA — FUNCIONALIDADE "INVENTÁRIO"

**Sistema:** SisPatrimônio Pro
**Modo da análise:** exclusivamente leitura (nenhuma alteração foi realizada no sistema)
**Data da análise:** 14/09/2026
**Método:** inspeção estática do código-fonte, templates, serviços, modelos, rotas, permissões, testes e configurações.

---

## 1. Resumo executivo

O Inventário é um módulo formal e comprobatório de conferência física do acervo. Um inventário é criado com escopo opcional (local/setor) e **gera imediatamente um snapshot imutável de bens esperados** (`inventario_itens`), que captura local e custodiante cadastrados no momento da geração. A conferência em campo registra, por item, um resultado (`Encontrado`, `Local Diferente`, `Não Encontrado`, `Sem Identificação`), local encontrado, observação, conferente e data/hora — **sem nunca alterar o cadastro do patrimônio** (regra garantida no service e coberta por testes de regressão). O encerramento exige zero pendentes e trava as conferências. O fluxo móvel existe via QR Code **gerado** (QRCode.js) que aponta para a ficha do bem `/assets/{id}`, de onde um dropdown "Inventário" leva à página de conferência; **não há leitor de câmera embutido nem RFID**. Foram encontrados **1 problema ALTO** (formulário "Registrar bem não previsto" do painel lateral quebra com erro 422) e nenhum CRÍTICO.

---

## 2. Arquivos envolvidos

| Arquivo | Responsabilidade | Relação com Inventário |
| ------- | ---------------- | ---------------------- |
| `app/models/inventario.py` | Modelos `Inventario` e `InventarioItem` (tabelas `inventarios` e `inventario_itens`) | Núcleo: entidade, snapshot esperado, resultado da conferência |
| `app/models/enums.py` | `InventarioStatus` (PLANEJADO/EM_ANDAMENTO/ENCERRADO) e `InventarioItemStatus` (PENDENTE/ENCONTRADO/LOCAL_DIFERENTE/NAO_ENCONTRADO/SEM_IDENTIFICACAO) com rótulos | Define todos os status do módulo |
| `app/services/inventario_service.py` | Toda a lógica: geração de código, escopo, snapshot de itens, conferência (`record_check`), não previsto (`register_unlisted_asset`), resumo (`summary`), encerramento (`close_inventario`) | Núcleo; encapsula a regra "nunca altera o Asset" |
| `app/web/routes.py` (linhas ~1750–2164) | 8 rotas web: listar, form/criar, detalhe, buscar, iniciar, página de conferência, registrar conferência, não previsto, encerrar; helpers `user_has_permission_for` e integração de inventário aberto na ficha (linhas 686–703) | Interface e orquestração HTTP |
| `app/web/templates/inventarios/list.html` | Lista de inventários com filtros e progresso | Entrada do módulo (menu) |
| `app/web/templates/inventarios/new.html` | Formulário de criação com escopo | Criação do snapshot |
| `app/web/templates/inventarios/detail.html` | Detalhe: consolidação, busca por tombamento, iniciar, lista de esperados, **1 modal de conferência por item**, painel de não previstos, comprovação, modal de encerramento | Tela principal operacional |
| `app/web/templates/inventarios/conferir.html` | Página de conferência de um bem específico (destino do fluxo QR) e registro de não previsto com `asset_id` oculto | Fluxo de campo |
| `app/services/audit_service.py` | `write_audit`, `ACTION_INVENTARIO`, rótulos | Trilha de auditoria do módulo |
| `app/services/permission_service.py` | Permissões `inventario.visualizar/criar/conferir/encerrar` e perfis padrão | RBAC |
| `app/services/report_service.py` | `_inventario_rows`, `generate_inventario_csv/pdf/excel` — ata comprobatória | Exportação (via `app/api/reports_api.py` linhas 163–205) |
| `app/web/templates/assets/detail.html` | Ficha do bem: QR Code (`origin + /assets/{id}`), flash `inventario=ok/erro` (código morto), dropdown "Inventário" com inventários abertos | Destino do QR e ponto de partida alternativo |
| `app/web/templates/assets/labels.html` | Etiquetas em lote com o mesmo QR | Impressão de etiquetas para campo |
| `app/api/assets_api.py` (linha 166) | `PUT /api/v1/assets/{asset_id}` — única via de edição de cadastro (API REST) | Contexto da seção 8 (conferência × edição) |
| `app/api/deps.py` | `require_web_auth`, `require_permission` (403 + auditoria de negação) | Segurança de todas as rotas |
| `tests/test_inventario.py` | 18 testes: serviço, fluxo web, RBAC, auditoria, exportação | Especificação executável do comportamento |

---

## 3. Fluxo completo (passo a passo)

1. **Acesso**: menu lateral/barra superior "Inventários" (`base.html` linhas 65–67 e 183–185), visível apenas com `can('inventario.visualizar')` → `GET /inventarios`.
2. **Rota**: `list_inventarios` (`routes.py` 1750) — dependência `require_permission("inventario.visualizar")`.
3. **Serviço/consultas**: `InventarioService.get_all` (busca por nome/código, filtro de status) + `InventarioService.summary` por inventário (2 consultas agregadas em `inventario_itens` por inventário — N+1 na listagem).
4. **Criação**: `GET/POST /inventarios/new` (`inventario.criar`). O POST chama `create_inventario`, que gera código `INV-AAAA-NNNN` (`next_code`), grava escopo textual (`scope_filters`) e chama `generate_items`.
5. **Seleção dos patrimônios**: `_scope_query` = todos os `assets` com `status != BAIXADO`, filtrados por `location_id` e/ou `Location.department`; para cada bem cria `InventarioItem` com **snapshot**: `expected_location_id/name` e `expected_custodian_name` (prova imune a movimentações futuras — testado por `test_scope_snapshot_survives_later_asset_move`). Idempotente.
6. **Responsável**: determinado **no snapshot** a partir de `Asset.custodian.name` (não há escolha de responsável na conferência).
7. **Início da conferência**: botão "Iniciar" → `POST /inventarios/{id}/iniciar` marca `started_at` e status EM_ANDAMENTO (auditoria). O início também ocorre **implicitamente** na primeira conferência ou registro de não previsto (`record_check`/`register_unlisted_asset`).
8. **Identificação de um patrimônio**: (a) `POST /inventarios/{id}/buscar` com a tag (digitada ou scanner externo) — resolve por `Asset.tag.ilike(tag)`; (b) QR Code da etiqueta → `/assets/{id}` → dropdown "Inventário" → `GET /inventarios/{id}/conferir/{asset_id}`; (c) clique no ícone de conferir na lista.
9. **Registro da conferência**: modal por item ou página `conferir.html` → `POST /inventarios/{id}/conferir/{item_id}` → `InventarioService.record_check` grava `status`, `found_location_id/name`, `observation`, `checked_by_id/name`, `checked_at`; primeira conferência define `started_at`/EM_ANDAMENTO; `write_audit` por item.
10. **Não encontrado**: resultado `NAO_ENCONTRADO` (`found_location_id = None`).
11. **Local diferente**: `LOCAL_DIFERENTE` exige `found_location_id` **diferente** do esperado (validação no service rejeita local igual ou ausente).
12. **Bem não previsto**: existe no cadastro mas fora da lista → `register_unlisted_asset` cria item `nao_previsto=True`, status `SEM_IDENTIFICACAO`, com local encontrado e observação; guard contra duplicidade. (Ver problema A-1 na seção 13.)
13. **Encerramento**: `POST /inventarios/{id}/encerrar` (`inventario.encerrar`) → `close_inventario` **exige 0 pendentes** entre os esperados; grava `closed_at`, `closed_by_name`, `closure_notes`; status ENCERRADO trava conferências (service e templates).
14. **Registros permanentes no banco**: linhas em `inventarios` (metadados e comprovação), `inventario_itens` (snapshot + resultado + conferente), `audit_logs` (criação, início, cada conferência, cada não previsto novo, encerramento). **Nada em `assets`/`movements` é alterado.**

Funções inexistentes (explícito): não há edição do inventário após criado, não há cancelamento/eliminação de inventário, não há reabertura de encerrado, não há API REST de operação de inventário (só exportação de ata), não há paginação da lista de itens, não há "próximo bem" automático.

---

## 4. Fluxo mobile

A interface é responsiva (Bootstrap 5; col-12, tabelas `table-responsive`, sidebar mobile em `main.js`), mas **não existe um modo "campo" dedicado**. O fluxo real pelo celular é:

```text
Câmera do celular lê o QR da etiqueta
      ↓
Abre https://.../assets/{id}  (ficha do bem; exige login + patrimonio.visualizar)
      ↓
Dropdown "Inventário" com inventários abertos (limite 10; só se status ≠ BAIXADO)
      ↓
GET /inventarios/{id}/conferir/{asset_id}  (conferir.html: ficha resumo somente-leitura
                                            + esperado + formulário de resultado)
      ↓
Escolhe resultado (+ local se LOCAL_DIFERENTE) + observação
      ↓
POST /inventarios/{id}/conferir/{item_id}  → registro + auditoria
      ↓
Redirect para /inventarios/{id}  (topo da lista — sem navegação p/ o próximo bem)
```

Alternativa pelo celular: dentro do detalhe do inventário, **digitar manualmente** o tombamento no campo "Tombamento / QR do bem" (tem `autofocus`, o que ajuda a digitar/escanear o próximo). Observações exatas:

- **Leitura de QR por câmera dentro do app**: **não existe** (nenhum `getUserMedia`/`BarcodeDetector` no projeto). O QR é lido pela câmera do próprio celular como URL.
- **RFID**: **não existe** (zero ocorrências no código).
- **Pesquisa manual / por número patrimonial**: existe (`/buscar` e filtro da lista).
- **Abertura do patrimônio após leitura**: sim, a ficha resumo em `conferir.html`.
- **Confirmação de conferência**: sim, botão "Registrar conferência"/"Registrar resultado".
- **Registro de divergência**: sim, no mesmo formulário.
- **Navegação para o próximo patrimônio**: **não existe**; o redirect vai ao topo do detalhe do inventário (o `autofocus` do campo de busca é o único atalho).
- O fluxo alternativo descrito no texto do template ("leva à ficha dele, onde há atalho de conferência") **confirma** que o fluxo atual é o do diagrama acima — ele não é "Escanear → Exibir → Conferir" dentro de uma única tela.

---

## 5. QR Code / RFID

- **Geração**: biblioteca **QRCode.js via CDN** (`base.html` linha 32), na ficha (`assets/detail.html` linhas 306–315) e nas etiquetas em lote (`assets/labels.html`). Conteúdo: `window.location.origin + "/assets/{asset.id}"` — ou seja, o QR aponta para a **ficha do bem**, não diretamente para a conferência.
- **Leitura**: nenhuma integrada. O texto da interface instrui "Aponte a câmera para a etiqueta QR do bem", o que na prática significa usar a câmera do celular para abrir a URL.
- **RFID**: **não há nenhuma evidência de implementação ou menção a RFID** em código, templates ou dependências.

---

## 6. Conferência de patrimônio (o que é "conferido")

O conceito de conferido é representado **exclusivamente no item de inventário** (nunca no patrimônio):

```text
inventarios (Inventario: status PLANEJADO→EM_ANDAMENTO→ENCERRADO, started_at)
      ↓ 1:N
inventario_itens (InventarioItem)
   ├─ snapshot do esperado: expected_location_id/name, expected_custodian_name
   ├─ resultado: status (PENDENTE/ENCONTRADO/LOCAL_DIFERENTE/NAO_ENCONTRADO/SEM_IDENTIFICACAO)
   ├─ local encontrado: found_location_id/name  (+ observation)
   ├─ quem/quando: checked_by_id, checked_by_name (snapshot), checked_at
   └─ flag: nao_previsto (bem encontrado em campo fora da lista)
```

- **Não existe** flag/status de "inventariado" na tabela `assets` — o patrimônio permanece intocado (regra do service: "NUNCA altera Asset.location_id / custodian_id / status"; testes `test_record_check_found_starts_inventory` e `test_record_check_wrong_location_requires_different_location` verificam isso).
- Histórico de **re-conferências** não é versionado no item (sobrescreve `checked_*`), mas cada gravação gera uma linha de auditoria.

---

## 7. Divergências

| Caso | Situação | Tratamento no código |
| ---- | -------- | -------------------- |
| **A. Encontrado no local correto** | esperado = encontrado | Resultado `ENCONTRADO`; se o usuário não informar local, o service assume o `expected_location_id`. Registra conferente/data/auditoria. |
| **B. Encontrado em local diferente** | esperado ≠ encontrado | Resultado `LOCAL_DIFERENTE`; **obriga** informar `found_location_id` **e** rejeita se for igual ao esperado (`ValueError` no `record_check`). Não altera o cadastro do bem — apenas registra (para tratamento posterior por movimentação/edição). |
| **C. Cadastrado, mas não localizado** | esperado, não achado | Resultado `NAO_ENCONTRADO` (`found_location_id=None`). Não gera pendência automática além do próprio status; o encerramento só é possível com todos os esperados conferidos (inclui os NAO_ENCONTRADO). |
| **D. Bem físico sem cadastro** | existe no chão, não existe no sistema | **Sem tratamento.** Tanto `/buscar` quanto `register_unlisted_asset` exigem que o `Asset` exista (`"Patrimônio não encontrado no cadastro"`). Não há criação de bem a partir do inventário. |
| **E. Sem identificação/etiqueta** | presente, tombo ilegível | Resultado `SEM_IDENTIFICACAO` disponível no modal/página para itens esperados. Para bem **não cadastrado** (sem tombamento), cai no caso D — sem tratamento. **Observação**: `register_unlisted_asset` reutiliza `SEM_IDENTIFICACAO` como status de bem não previsto (sobrecarga semântica — ver M-6). |

Em B, C e E o sistema **registra, solicita confirmação via formulário e audita**; não altera automaticamente nada; não gera pendências formais nem tarefas de correção.

---

## 8. Edição durante o inventário

**Resposta direta: NÃO. O usuário não consegue editar nenhum dado patrimonial durante a conferência — nem por acidente, nem intencionalmente pela interface de Inventário.**

- **Não existe botão "Editar" nem link de edição** em nenhuma das 4 telas de inventário, nem na ficha do bem (`assets/detail.html`). Não há rota web `GET/POST /assets/{id}/edit` — a única edição de cadastro no sistema é a **API REST** `PUT /api/v1/assets/{id}` (`assets_api.py` linha 166, permissão `patrimonio.editar`), e seu schema `AssetUpdate` **nem sequer aceita `location_id`, `custodian_id` ou `status`** (mudança de local/responsável só por movimentação).
- A tela de conferência (`conferir.html`) reutiliza apenas **dados** da ficha (tag, nome, local, custodiante, status) em formato somente-leitura; não reutiliza o formulário de edição (que não existe na web).
- Campos alteráveis durante a conferência: **somente** resultado, local encontrado e observação — todos gravados em `inventario_itens`.
- Alteração é imediata (POST direto), com confirmação implícita pelo botão "Registrar resultado" e modal com botão Cancelar; re-conferência é permitida enquanto o inventário estiver aberto.
- **Separação conferir × editar**: total e arquitetural. O service de inventário não importa `AssetService.update` e não escreve em `Asset`.

---

## 9. Banco de dados

Banco: **MariaDB/MySQL** exclusivamente (`config.py` — sem fallback SQLite). Tabelas diretamente envolvidas:

### `inventarios`
- **Finalidade**: cabeçalho do inventário e comprovação formal.
- **PK**: `id`. **FKs**: `location_id → locations.id`, `created_by_id → users.id (SET NULL)`.
- **Campos importantes**: `code` (único, `INV-AAAA-NNNN`), `name`, `status` (Enum PLANEJADO/EM_ANDAMENTO/ENCERRADO, indexado), `department`, `scope_filters` (snapshot textual), `notes`, `created_by_name` (snapshot), `created_at`, `started_at`, `closed_at`, `closed_by_name`, `closure_notes`.
- **Datas**: criação, início, encerramento (todas `datetime.utcnow` naive). **Usuário**: criador (id+nome) e encerrador (nome).

### `inventario_itens`
- **Finalidade**: expectativa (snapshot) + ata de conferência de cada bem.
- **PK**: `id`. **FKs**: `inventario_id → inventarios.id (CASCADE)`, `asset_id → assets.id (CASCADE)`, `expected_location_id` e `found_location_id → locations.id`, `checked_by_id → users.id (SET NULL)`.
- **Restrição**: `UNIQUE (inventario_id, asset_id)` — impede duplicidade de bem por inventário.
- **Campos importantes**: `status` (Enum dos 5, indexado), `nao_previsto` (Boolean), `expected_*` (snapshot), `found_location_id/name`, `observation`, `checked_by_id/name`, `checked_at`, `created_at`.

### Tabelas de apoio (somente leitura pelo módulo)
- `assets` — fonte dos bens (`tag` único, `name`, `status`, `location_id`, `custodian_id`); **nunca escrita pelo inventário**.
- `locations` — locais (com `department` usado no escopo).
- `custodians` — fonte do `expected_custodian_name`.
- `users` — conferente/criador.
- `audit_logs` — trilha (seção 11).

Relacionamentos resumidos: `Inventario 1—N InventarioItem N—1 Asset`; `InventarioItem N—1 Location (2x: esperado/encontrado)`; `InventarioItem N—1 User (conferente)`.

---

## 10. Permissões e segurança

- **Permissões** (catálogo canônico, deny-by-default): `inventario.visualizar`, `inventario.criar`, `inventario.conferir`, `inventario.encerrar`.
- **Perfis padrão**: **Administrador** (todas + bypass `is_admin` auditado) e **Patrimônio** (as 4 de inventário) têm acesso pleno; **Auditor** tem apenas `inventario.visualizar` (leitura + exportação se tiver `relatorios.exportar`); Gestor de TI, Técnico de TI, Almoxarifado e Consulta **não têm nenhuma** permissão de inventário.
- **Aplicação**: backend real — `require_permission(...)` como dependência em **todas** as rotas (403 auditado com `ACESSO_NEGADO`); autenticação por sessão cookie (`require_web_auth` em todo o roteador web). Os botões/affordances da UI (`can_conferir`, `can_encerrar`, `can(...)`) são apenas cosméticos — a validação é no servidor. Teste `test_rbac_deny_and_grant_inventario` confirma 403/200.
- **Restrições por setor/localização/unidade**: **não existem**. Qualquer usuário com `inventario.conferir` confere qualquer inventário, de qualquer local. O escopo é uma decisão do criador, não do RBAC.
- **Exportação da ata**: exige `inventario.visualizar` **e** `relatorios.exportar` simultaneamente (`reports_api.py`).
- **Nuance**: o fluxo QR exige `patrimonio.visualizar` (ficha) + `inventario.conferir`; um perfil hipotético "só conferente" sem `patrimonio.visualizar` não conseguiria usar a via da ficha.
- **CSRF**: os POSTs de formulários não têm token (mitigado por cookie `SameSite=Lax`; lacuna já documentada em `docs/`, vale para os POSTs do inventário também).

---

## 11. Auditoria e rastreabilidade

Ação `ACTION_INVENTARIO = "INVENTARIO"`, módulo "Inventário", gravada em `audit_logs` com usuário (id + username snapshot), IP, `previous_data`/`new_data` (JSON), resultado.

```text
Evento: Criação do inventário
Onde: POST /inventarios/new → write_audit (resource=Inventario, ref=code)
Usuário/Data/IP: sim / sim / sim | Patrimônio: não (registrado nº de bens e escopo)
Extras: new_data com code, nome, escopo, bens esperados

Evento: Início formal da conferência
Onde: POST /inventarios/{id}/iniciar → write_audit ("iniciado formalmente")
Observação: só quando started_at era None; o início implícito pela 1ª conferência NÃO gera evento próprio

Evento: Conferência registrada (por item, incluindo divergências B/C/E)
Onde: POST /inventarios/{id}/conferir/{item_id} → write_audit (resource=InventarioItem, ref=tag)
Extras: new_data = inventário, bem, resultado, local encontrado, observação

Evento: Bem não previsto registrado (apenas quando criado; duplicata não audita)
Onde: POST /inventarios/{id}/nao-previsto → write_audit
Extras: new_data = inventário, bem, nao_previsto, local, observação

Evento: Encerramento
Onde: POST /inventarios/{id}/encerrar → write_audit
Extras: new_data = encerrado_em, encerrado_por, notas

Evento: Cancelamento do inventário
Não existe — não há como cancelar.

Evento: Tentativa FALHA (ex.: encerrar com pendentes, LOCAL_DIFERENTE com local igual, buscar tag inexistente)
Não foi encontrada evidência de registro de auditoria para estas operações — erros resultam em redirect com mensagem e nada é gravado (apenas acessos negados 403 são auditados, via require_permission).

Evento: Consultas (listagem, detalhe, busca de bem)
Não foi encontrada evidência de registro de auditoria para estas operações.
```

Rastreabilidade adicional: cada item exibe conferente/data/hora na própria linha (e nas atas exportadas); a ficha do bem incorpora a trilha de auditoria na sua timeline (`assets/detail.html`), então as conferências aparecem no histórico do patrimônio.

---

## 12. Fluxograma técnico real

```text
Usuário autenticado
  ↓
Menu "Inventários" (base.html, can inventario.visualizar)
  ↓
GET /inventarios → list_inventarios → InventarioService.get_all + summary×N
  ↓
GET /inventarios/new → form_new_inventario (locais + departamentos)
  ↓
POST /inventarios/new → create_inventario_form
      → InventarioService.create_inventario
          → next_code (INV-AAAA-NNNN) → INSERT inventarios
          → generate_items → _scope_query (assets ≠ BAIXADO [+ local/setor])
          → INSERT inventario_itens (snapshot expected_*)
      → write_audit (criação) → redirect GET /inventarios/{id}
  ↓
view_inventario (detail.html: summary, lista esperados, painel não previstos)
  ↓ (opcional) POST /inventarios/{id}/iniciar → started_at + EM_ANDAMENTO + audit
  ↓
Identificação do bem:
  [a] POST /inventarios/{id}/buscar (tag) → achou na lista? redirect ?search=tag
                                          → não está na lista? mensagem + painel
  [b] QR etiqueta → GET /assets/{id} → dropdown "Inventário"
        → GET /inventarios/{id}/conferir/{asset_id} (conferir.html)
  [c] ícone conferir da linha → modal (#modalConferir{item.id})
  ↓
POST /inventarios/{id}/conferir/{item_id} → confer_item
      → InventarioService.record_check (valida: encerrado, resultado, LOCAL_DIFERENTE)
      → UPDATE inventario_itens (status, found_*, observation, checked_*)
      → started_at/EM_ANDAMENTO implícito (se 1ª)
      → write_audit (por item) → redirect GET /inventarios/{id}
  ↓ (bem fora da lista)
POST /inventarios/{id}/nao-previsto → register_unlisted_asset
      → INSERT inventario_itens (nao_previsto=True, SEM_IDENTIFICACAO) + audit
  ↓
POST /inventarios/{id}/encerrar (can inventario.encerrar)
      → close_inventario (exige 0 PENDENTE) → ENCERRADO + audit
  ↓
Exportação da ata: GET /api/v1/reports/inventarios/{id}/csv|pdf|excel
      (inventario.visualizar + relatorios.exportar → ReportService.generate_inventario_*)
```

---

## 13. Problemas encontrados

| Severidade | Problema | Local | Evidência no código | Impacto |
| ---------- | -------- | ----- | ------------------- | ------- |
| **ALTO** | Formulário "Registrar bem não previsto" do painel lateral envia `tag` (texto), mas a rota exige `asset_id: int = Form(...)` e não resolve tag→bem. Sempre responde **422** (JSON cru) — fluxo D/"não previsto" quebrado na tela principal | `detail.html` (form com `name="tag"`) × `routes.py` `register_unlisted_asset` (`asset_id: int = Form(...)`) | `detail.html` linha do form `/nao-previsto` usa `name="tag"`; `conferir.html` usa corretamente `hidden name="asset_id"`; nenhum JS converte o campo; nenhum teste HTTP cobre `/nao-previsto` | Operador em campo não consegue registrar não previsto pelo painel; o caminho de `/buscar` ("Registre-o como não previsto no painel lateral") leva a um erro. Só funciona via página QR `conferir.html` |
| MÉDIO | Sem paginação e 1 modal por item renderizado no detalhe | `view_inventario` + `detail.html` | `get_by_id` carrega **todos** os itens; template faz `{% for item in expected_itens %}` duas vezes (tabela + modais) | Inventários grandes (milhares de bens) tornam a página pesada/lenta, sobretudo no celular |
| MÉDIO | Operações falhas não são auditadas (resultado FAILURE) | `routes.py` (todos os `except ValueError` → redirect) | Apenas sucesso grava `write_audit`; tentativa de encerrar com pendentes, LOCAL_DIFERENTE inválido, tag inexistente — nada registrado | Fragiliza a prova em campo (não se sabe quem tentou o quê e quando falhou) |
| MÉDIO | Sem token CSRF nos POSTs do módulo (condição sistêmica, já documentada em `docs/`) | Todos os forms de `list/new/detail/conferir.html` | Ausência de campo CSRF; `docs/AUDITORIA_TECNICA_RELATORIO.md` registra a lacuna | Mitigado por `SameSite=Lax`; risco residual de POST forjado |
| MÉDIO | Sem restrição de escopo por local/setor/unidade no RBAC | `permission_service.py` + rotas | Permissões só por ação; nenhum filtro por localização do usuário | Qualquer conferente confere qualquer unidade — aceitável em org pequenas, risco em multi-unidade |
| MÉDIO | Inventário não pode ser cancelado nem reaberto após encerramento; não há confirmação extra além do modal | `routes.py`/`inventario_service.py` | Não existe rota de cancelar/reabrir; `close_inventario` é irreversível | Encerramento por engano exige intervenção manual no banco |
| BAIXO | Status do bem não previsto reutiliza `SEM_IDENTIFICACAO` | `inventario_service.py` `register_unlisted_asset` | `status=InventarioItemStatus.UNIDENTIFIED` para `nao_previsto=True` | Atas mostram "Sem Identificação" como resultado de bens não previstos, mesmo tombados — ambiguidade semântica |
| BAIXO | Código morto: flashes `inventario=ok/erro` sem rota produtora | `assets/detail.html` linhas 18–29 | Nenhuma rota redireciona com esses parâmetros (POST `/conferir` redireciona para `/inventarios/{id}`) | Sugere fluxo antigo descontinuado; confunde manutenção |
| BAIXO | Condição de corrida na geração de código `INV-AAAA-NNNN` | `next_code` | `max`-like + `int+1` sem lock; há `UNIQUE` em `code` | Dois usuários criando em simultâneo → 500 para um deles (raro) |
| BAIXO | Entrada do `/buscar` não escapa metacaracteres LIKE (`%`, `_`) | `routes.py` `buscar_bem_inventario` | `Asset.tag.ilike(tag_clean)` com texto bruto do usuário | Digitando `%` o usuário obtém casamento difuso e pode cair no item errado |
| BAIXO | Dropdown de inventários na ficha limitado a 10 e oculto para bens BAIXADO | `view_asset_detail` (`limit(10)`) + `detail.html` | `.limit(10)`; bloco dentro de `status != 'BAIXADO'` | Com >10 inventários abertos alguns ficam inacessíveis pela ficha; baixados não são conferíveis pela ficha (mas são pela lista) |
| INFORMATIVO | Snapshot: bens cadastrados **após** a criação não entram na lista esperada | `generate_items` (executa só na criação) | Comportamento documentado no docstring e no aviso de `new.html` | Esses bens só aparecem como "não previsto" |
| INFORMATIVO | Re-conferência permitida enquanto aberto (sobrescreve resultado) | `record_check` + aviso em `conferir.html` | "pode ser atualizado abaixo enquanto o inventário estiver aberto" | Intencional; histórico só via auditoria |
| INFORMATIVO | Sem API REST de operação de inventário (apenas exportação) | `app/api/` | Nenhum endpoint `/inventarios` na API de negócio | Integrações externas limitadas |
| INFORMATIVO | Timestamps `utcnow` naive; `Movement` usa `datetime.now()` | Models do inventário × `asset_service.update` | Mistura de convenções no projeto | Possível defasagem horária em relatórios |

---

## 14. Pontos positivos

- **Integridade patrimonial**: a regra "inventário nunca altera o cadastro" é reforçada em docstrings, service, templates e testes de regressão explícitos.
- **Snapshot comprobatório** (`expected_*` + `scope_filters`) que sobrevive a movimentações posteriores — evidência jurídico-administrativa sólida.
- **Validações de divergência no backend**: LOCAL_DIFERENTE exige local diferente do cadastrado; encerramento exige zero pendentes; inventário encerrado trava tudo.
- **RBAC granular** (4 permissões) aplicado no servidor em todas as rotas, com auditoria de negações e testes.
- **Auditoria rica** nas operações de escrita, com `before/after` JSON, IP e snapshots de username.
- **Atas exportáveis** em CSV/PDF/Excel com bloco de comprovação (quem criou, iniciou, encerrou) — bem cobertas por testes.
- **Dupla via de identificação** (busca por tombamento e QR via ficha) e proteção contra duplicidade (`UNIQUE` + guard no service).
- Boa cobertura de testes do módulo (serviço, HTTP, RBAC, auditoria, exportação).

## 15. Pontos que merecem atenção

1. Corrigir o fluxo "não previsto" do painel (ALTO) — hoje só funciona pela via da ficha/QR.
2. Desempenho/mobile do detalhe com inventários grandes (paginação + modal único).
3. Fluxo de campo dedicado: leitor de câmera embutido, navegação "próximo bem", fila de conferência.
4. Auditoria de falhas (result=FAILURE) e do início implícito.
5. Decisão de produto para caso D (bem físico sem cadastro) — hoje não há tratamento.
6. CSRF nos formulários (sistêmico) e restrição de escopo por unidade no RBAC.
7. Política de ciclo de vida: cancelamento/reabertura de inventário.
8. Reconciliar `patrimonio.editar` (permissão sem UI web; edição só via API REST).

---

## 16. Conclusão

1. **A lógica atual de Inventário está coerente?** Sim. Snapshot → conferência → consolidação → travamento é consistente e bem separada das demais camadas; a exceção operacional é o fluxo "não previsto" quebrado no painel.
2. **O fluxo de conferência está separado da edição patrimonial?** Sim, completamente — não existe edição patrimonial na UI de inventário (nem na web como um todo); a mudança de cadastro passa por movimentação/API dedicada.
3. **O uso pelo celular está adequado?** Parcialmente. Funciona (responsivo, QR→ficha→conferência), mas sem leitor embutido, sem navegação "próximo bem" e com página de detalhe pesada em acervos grandes.
4. **O registro da conferência é confiável?** Sim para o banco (quem/quando/resultado/local/observação no item + auditoria por gravação); a confiança total é limitada pela ausência de auditoria de falhas e pela re-conferência sobrescrever sem versionamento.
5. **As divergências são tratadas adequadamente?** A/B/C/E sim (com registro e bloqueio de erros); D (bem sem cadastro) e a pendência pós-divergência (nenhuma fila de tratamento) não têm tratamento.
6. **Existe rastreabilidade suficiente?** Boa (audit_logs + snapshots + atas), com lacunas: falhas não auditadas e consultas sem registro.
7. **Há risco de alteração indevida dos dados durante o inventário?** Não pelo inventário — o service não toca em `assets`. O risco residual é sistêmico (CSRF nos POSTs, mitigado por SameSite=Lax).
8. **Pontos prioritários para melhoria**: corrigir o formulário de não previsto; auditoria de falhas; desempenho/paginação; fluxo mobile dedicado com "próximo bem"; tratamento do bem sem cadastro; CSRF e escopo por unidade.

---

> **"Análise concluída em modo somente leitura. Nenhuma alteração foi realizada no sistema."**
