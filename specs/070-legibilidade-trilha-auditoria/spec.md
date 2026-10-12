# Feature Specification: Legibilidade dos Eventos de Alteração Cadastral na Trilha de Fluxo & Movimentações (detalhe do Equipamento)

**Feature Branch**: `070-legibilidade-trilha-auditoria`

**Created**: 2026-10-12

**Status**: Draft

**Input**: Melhorar a apresentação dos eventos de **alteração cadastral** na seção "Trilha de Fluxo & Movimentações" da tela de detalhes de um equipamento patrimonial do módulo **Equipamentos** do SisPatrimônio Pro: exibir de forma legível o que foi alterado (campo, valor anterior, valor posterior, responsável, data), sem exigir que o usuário compare manualmente dois objetos JSON completos. Mudança de **apresentação** com gravação, histórico, contrato de API e demais funcionalidades **intactos** (Constitution I/IV/IX). **Nesta etapa: somente especificação — nenhum arquivo funcional é modificado.**

---

## Clarifications

### Session 2026-10-12

- Q: Onde o resumo legível (campos alterados com rótulo, antes → depois) de cada evento de auditoria deve ser calculado, sem tocar em `get_timeline_for_asset` nem no contrato da API? (PD-1) → A: **Helper somente-leitura em service** (padrão aprovado pela Feature 067 — ex.: `AssetService`), chamado pela rota `view_asset_detail` para enriquecer os itens de auditoria; `MovementService.get_timeline_for_asset` e `GET /api/v1/assets/{id}/timeline` permanecem intocados. Consequência imediata para PD-2: com o helper no mesmo módulo do `_ASSET_FIELD_LABELS`, a fonte única de rótulos é reutilizada **no lugar** (sem exportação nem dicionário novo).
- Q: Qual padrão visual deve representar "valor anterior → valor posterior" em cada linha de campo alterado no cartão da trilha? (PD-3) → A: **Padrão do painel "Alterações cadastrais"** — valor anterior riscado + seta + valor posterior em destaque, reaproveitando os estilos já existentes (zero CSS novo, consistência na mesma tela).
- Q: Qual título o cartão de alteração cadastral deve usar no topo do resumo? → A: **Formato do pedido original** — um campo alterado → "Alteração cadastral — <rótulo do campo>" (ex.: "Alteração cadastral — Nome do bem"); vários campos → "Alteração cadastral — Dados do equipamento". Descartados: título fixo (A) e título com contagem de campos (C).
- Q: Como o resumo deve tratar a diferença entre "campo ausente" (chave não existe no snapshot) e "campo com valor nulo" (chave existe com `null`), dado que o diff desserializado atual não distingue os dois? (PD-4) → A: **Exibição neutra `—`** para ausente e nulo no resumo; a distinção real permanece disponível apenas no JSON original dos detalhes técnicos. Motivo: marcadores de "campo removido/adicionado" inventariam alterações artificiais quando a diferença for só de formato de snapshot (web × API × históricos, §1.7), violando FR-005. Descartadas: distinção por membership (B) e representação técnica crua (C).

---

## 1. Contexto e análise do sistema atual (somente leitura, verificada nesta especificação)

| # | Ponto investigado | Realidade verificada |
|---|---|---|
| 1 | Rota da tela de detalhes do Equipamento | `view_asset_detail` — `GET /assets/{asset_id}` (`app/web/routers/assets.py` L478–519), permissão `patrimonio.visualizar`; passa `timeline = MovementService.get_timeline_for_asset(db, asset_id)` e `cadastral_history = AssetService.get_cadastral_history(db, asset_id)` ao template |
| 2 | Template da tela | `app/web/templates/assets/detail.html` (414 linhas). Duas seções distintas na coluna direita: **"Alterações cadastrais"** (painel `id="historico-cadastral"`, ~L228–263, Feature 067) e **"Trilha de Fluxo & Movimentações"** (~L265–400) |
| 3 | Cartão de evento de auditoria na trilha (problema) | `detail.html` L285–321: badges (rótulo da ação via `action_label`, módulo, `resource_ref`), data/hora, **"Descrição: Campos alterados: name"** e, em seguida, `Antes:` / `Depois:` com os objetos JSON **completos** via `{{ item.prev_data \| tojson(indent=0) }}` / `{{ item.new_data \| tojson(indent=0) }}` (L305–317) + "Registrado por" |
| 4 | Fonte dos eventos da trilha | `MovementService.get_timeline_for_asset` (`app/services/movement_service.py` L410–473): une `Movement` + `AuditLog` (`resource='Asset' AND resource_id=<asset_id>`, teto de 50 eventos, **exclui** `MOVIMENTACAO`/`MANUTENCAO`/`CRIACAO`), desserializa `previous_data`/`new_data` em `prev_data`/`new_data` (JSON inválido → `None`, tolerância atual) e ordena do mais recente para o mais antigo |
| 5 | Contrato congelado | O MESMO método alimenta `GET /api/v1/assets/{asset_id}/timeline` (`app/api/assets_api.py` L78–130) — Specs 029 e 067 declaram `get_timeline_for_asset` **NÃO alterado**; `tests/test_api.py` trava o payload (`prev_data`/`new_data` desserializados) |
| 6 | Gravação dos eventos | `write_change_audit` (`app/services/audit_service.py` L261–314) grava snapshots **completos** before/after em `previous_data`/`new_data` (JSON em TEXT) e monta a descrição `"Campos alterados: " + campos ordenados` via `changed_fields(before, after)` (L317–330) — o sistema **já calcula a diferença**, mas só a usa no texto da descrição |
| 7 | Formatos de snapshot divergentes | Edição web `_asset_audit_snapshot` (`app/web/routers/assets.py` L52–68: sem `specifications`/datas) × edição API `_asset_snapshot` (`app/api/assets_api.py` L24–40: 17 campos, datas `'%Y-%m-%d'`). Eventos históricos podem ter conjuntos de chaves diferentes — a apresentação deve tolerar a união das chaves |
| 8 | Rótulos amigáveis já existentes | `_ASSET_FIELD_LABELS` (`app/services/asset_service.py` L73–92: 17 rótulos, ex. `name → "Nome do bem"`, `location_id → "Localização"`) já usado por `AssetService.get_cadastral_history` (L97–149) para o painel "Alterações cadastrais" |
| 9 | Limitação comprovada do diff | `changed_fields` usa `before.get(key)`/`after.get(key)`: **chave ausente** e **valor `null` explícito** viram `None` idêntico — o diff desserializado **não distingue** ausente × nulo; a distinção só existe no JSON bruto armazenado |
| 10 | Ações que efetivamente chegam ao cartão de auditoria da trilha | Na prática, `ALTERACAO` (edição web `assets.py` L655–683 e API PUT `assets_api.py` L166–195 — ambas gravam `resource_id`). `CRIACAO`/`MOVIMENTACAO`/`MANUTENCAO` são excluídas pelo service; a importação CSV grava `resource_id=None` (fora do filtro). Eventos antigos/outros formatos continuam sendo exibidos com tolerância atual |
| 11 | Renderização e segurança | Jinja2 com autoescape ativo nos templates; `tojson` é seguro. Qualquer novo render DEVE manter os dados como dados (sem interpretação como HTML/JS) |
| 12 | Mecanismo de expansão já existente no projeto | `app/web/templates/admin/audit/list.html` L111–118 já usa `<details>` **nativo** para mostrar `ANTERIOR`/`POSTERIOR` — precedente reutilizável (sem JavaScript, recolhido por padrão, operável por teclado) |
| 13 | Ponto de registro de helpers de template | `app/web/routers/templates_env.py` (globals `action_label`, filtro `localtime`) — local estabelecido para expor helpers de apresentação aos templates |
| 14 | Testes existentes que tocam a área | `tests/test_presentacao_trilha_063.py` (asserts sobre o HTML da trilha), `tests/test_consulta_edicao_bens_067.py` (detalhe + painel cadastral + trilha + API), `tests/test_api.py` (payload da timeline), `tests/test_movements.py`, `tests/test_import_asset_movements.py`, `tests/test_departamento_destino_062.py`, `tests/test_assets.py`, `tests/test_datetime_flows.py` (datas na trilha). **Nenhum teste trava o JSON bruto como conteúdo principal do cartão** — a mudança não deve quebrar nenhum deles |
| 15 | Relação com specs anteriores | 063/064 padronizaram **Origem/Destino de movimentações** (intocados aqui); 067 criou o painel "Alterações cadastrais" e registrou como **lacuna (c)** o fato de o "Antes/Depois" da trilha aparecer como "JSON bruto (`tojson`), pouco legível" (`specs/067-consulta-edicao-bens/spec.md` L131) — a 067 **não alterou** o cartão da trilha (fora de seu escopo). Esta feature (070) fecha exatamente essa lacuna, sem sobrepor as demais |
| 16 | Documentação / ajuda | Nenhum artigo da central de ajuda descreve o formato atual dos cartões de auditoria da trilha (mesma verificação da 063) — nenhuma atualização obrigatória; reconfirmar na implementação (Constitution XI) |

**Consequências da análise** (refletidas nos requisitos):

- O problema é de **apresentação**: os dados necessários (campos alterados, valores antes/depois, usuário, data, ação) **já existem** no evento e chegam à template (`prev_data`/`new_data` desserializados + `AuditLog` completo).
- A função `changed_fields` e o mapeamento `_ASSET_FIELD_LABELS` **já existem** e são usados pelo painel "Alterações cadastrais" — a solução pode reutilizá-los sem criar mecanismo novo.
- A solução é realizável como **transformação de leitura para apresentação**: template (+ eventual helper de apresentação registrado no ponto já estabelecido), **zero DDL, zero mudança de gravação, zero mudança de service de timeline** (contrato da API `/timeline` preservado — Constitution I/IV/VII).
- A distinção técnica "chave ausente × valor nulo" **não é recuperável** do diff desserializado (item 9); ela permanece acessível no JSON original via "Ver detalhes técnicos" (comportamento de fallback documentado em FR-006).

---

## 2. Problema e Objetivo

### Problema

Na "Trilha de Fluxo & Movimentações", um evento de alteração cadastral exibe `Descrição: Campos alterados: name` e, logo abaixo, os **objetos JSON completos** dos estados anterior e posterior — incluindo todos os atributos que **não** mudaram. Exemplo real representativo:

**Antes:** `{"brand": null, "category": "OUTROS", "condition": "NOVO", "location_id": 9, "name": "Scaners Fujitsu mod. 6140Z", "status": "DISPONIVEL", "tag": "IPMJP0212"}`

**Depois:** `{"brand": null, "category": "OUTROS", "condition": "NOVO", "location_id": 9, "name": "Scaners Fujitsu mod. 6140z", "status": "DISPONIVEL", "tag": "IPMJP0212"}`

A única alteração é `Z → z` no campo `name`, mas o usuário precisa comparar os dois objetos manualmente para encontrá-la. Isso gera: excesso de informação visual; dificuldade de identificar o que mudou; exibição desnecessária de atributos inalterados; redundância com o painel "Alterações cadastrais"; dificuldade de leitura para usuários não técnicos; menor eficiência na conferência de auditoria.

### Objetivo

Apresentar cada evento de alteração cadastral da trilha com **descrição amigável e estruturada**, exibindo apenas os campos efetivamente alterados com seus rótulos compreensíveis, valor anterior e valor posterior — mantendo os **dados técnicos completos** (estados originais) disponíveis mediante expansão discreta, preservando integralmente registros, rastreabilidade e o restante do sistema.

---

## 3. User Scenarios & Testing

### User Story 1 - Cartão de alteração cadastral legível na trilha (Priority: P1) 🎯 MVP

Um servidor do Patrimônio, gestor ou auditor abre a ficha de um equipamento e lê, na "Trilha de Fluxo & Movimentações", cada evento de alteração cadastral com o **resumo do que mudou**: campo (em rótulo compreensível), valor anterior, valor posterior — sem precisar decifrar JSON. Campos que não mudaram não aparecem. Data, responsável, tipo de evento e identificação do bem continuam visíveis, como hoje.

**Why this priority**: é o núcleo do pedido — identificar em segundos o que foi alterado, quem alterou e quando.

**Independent Test**: registrar uma edição cadastral de um campo (ex.: nome) via `/assets/{id}/edit`, abrir `/assets/{id}` e verificar que o cartão do evento na trilha exibe o rótulo do campo com antes → depois, sem que o JSON completo seja o conteúdo principal.

**Acceptance Scenarios**:

1. **Given** um evento com alteração de um único campo, **When** a trilha é exibida, **Then** o cartão apresenta campo (rótulo amigável), valor anterior e valor posterior — sem exigir comparação de JSON.
2. **Given** um evento com alterações em vários campos, **When** o cartão é exibido, **Then** todos os campos alterados aparecem, cada um com seu antes/depois.
3. **Given** um evento em que campos permaneceram iguais, **When** o cartão é exibido, **Then** os campos inalterados **não** ocupam espaço no resumo.
4. **Given** um campo cadastrado no sistema (ex.: `name`, `brand`, `serial_number`, `location_id`), **When** ele é exibido, **Then** o rótulo é compreensível (mesma terminologia do painel "Alterações cadastrais" e dos formulários).
5. **Given** um campo desconhecido ou adicionado no futuro, **When** ele aparece em um evento, **Then** ele é exibido pelo seu nome técnico, sem quebrar o cartão.

---

### User Story 2 - Detalhes técnicos expansíveis (Priority: P2)

Quando o usuário (auditor, suporte técnico) precisa inspecionar o estado original completo do evento, ele aciona um controle discreto **"Ver detalhes técnicos"** no cartão — que expande os dados JSON originais (Antes e Depois, claramente separados) e recolhe de volta, sem sair da tela e sem alterar nada.

**Why this priority**: garante que a legibilidade não custe rastreabilidade — o dado técnico continua integralmente disponível para investigação.

**Independent Test**: com um evento exibido na trilha, expandir "Ver detalhes técnicos" e verificar que o JSON completo de antes e depois aparece; recolher e verificar que o cartão volta ao tamanho normal.

**Acceptance Scenarios**:

1. **Given** um evento com dados técnicos disponíveis, **When** a página é aberta, **Then** os detalhes estão **recolhidos** por padrão e o cartão não cresce desnecessariamente.
2. **Given** o controle "Ver detalhes técnicos", **When** o usuário ativa-o (clique ou teclado), **Then** os estados original anterior e posterior aparecem, distinguíveis entre si, sem quebrar o layout (objetos extensos quebram linha adequadamente).
3. **Given** um valor contendo HTML/JavaScript, acentuação, aspas ou quebras de linha, **When** os detalhes são exibidos, **Then** o conteúdo aparece como **dado** (texto), nunca interpretado ou executado.
4. **Given** um evento cujo um dos estados está ausente ou com JSON inválido, **When** os detalhes são exibidos, **Then** o controle funciona e mostra o que existe, sem erro de renderização.

---

### User Story 3 - Preservação integral: demais eventos, painel cadastral e histórico (Priority: P1)

Qualquer usuário continua vendo a trilha completa e confiável: movimentações, manutenções e demais categorias de evento com suas informações específicas exatamente como hoje; o painel "Alterações cadastrais" permanece intacto; registros de auditoria no banco permanecem byte-a-byte idênticos; e a API de timeline entrega o mesmo payload.

**Why this priority**: é a guarda da feature (Constitution IV/VIII/IX) — condição para que a US1 seja segura e sem regressões.

**Independent Test**: após a mudança, comparar o conteúdo de `audit_logs` antes/depois (idêntico), o payload de `GET /api/v1/assets/{id}/timeline` (idêntico) e o render de um equipamento com movimentações (idêntico ao atual para aí de movimentação).

**Acceptance Scenarios**:

1. **Given** um equipamento com movimentações e eventos não-cadastrais, **When** a trilha é exibida, **Then** esses cartões mantêm suas informações específicas (origem/destino 063/064, motivo, operador, termo) sem qualquer mudança.
2. **Given** o painel "Alterações cadastrais", **When** a tela é exibida, **Then** seu conteúdo e comportamento são idênticos aos atuais (067 intacta).
3. **Given** eventos de auditoria já gravados, **When** a página é renderizada, **Then** nenhum registro é alterado, regravado ou excluído (leitura pura).
4. **Given** a API `GET /api/v1/assets/{id}/timeline`, **When** ela é consultada após a mudança, **Then** o payload é idêntico ao atual (mesmas chaves e valores).

---

### Edge Cases

- **Evento com "Nenhuma alteração de campo registrada"** (descrição já gravada pelo sistema): o cartão não inventa diff — exibe a descrição como está, sem lista de campos.
- **Evento com apenas um dos estados** (só `previous_data` ou só `new_data`, inclusive gravações históricas): o resumo exibe o estado disponível claramente identificado (ex.: "Valor anterior: X" sem par "Depois"); os detalhes técnicos mostram o que existe.
- **JSON inválido / não-dicionário** em `previous_data`/`new_data` (tolerância atual do service converte para `None`): o cartão não quebra — cai no comportamento atual descritivo (descrição + estado legível, quando houver).
- **Conjuntos de chaves diferentes entre antes e depois** (snapshot web × API × históricos): o resumo considera a **união** das chaves; campo só presente em um dos lados é tratado como alteração com o outro lado vazio (`—`), sem inventar valores.
- **Ausente × nulo**: o diff desserializado não distingue (limitação verificada §1.9); ambos aparecem como `—` no resumo; a distinção permanece no JSON original dos detalhes técnicos (limitação documentada, não mascarada).
- **Valores nulos, strings vazias, números, booleanos, datas e enums** (`DISPONIVEL`, `OUTROS`…): exibidos conforme seu significado real — sem rotulá-los como alteração quando o formato do evento não permite concluir.
- **Valores longos** (ex.: `notes`, `specifications`): quebra de linha adequada, sem rolagem horizontal da página; sem truncamento que impeça a consulta no resumo (o resumo valoriza a diferença; o texto integral permanece nos detalhes técnicos).
- **Caracteres especiais/acentuação/aspas/quebras de linha** (nomes como `Assist}ência`, valores com `"`): preservados e exibidos corretamente, escapados.
- **Conteúdo hostil** (`<script>` em `notes`): exibido como texto, nunca executado.
- **Vários eventos de alteração do mesmo bem** (edições repetidas): cada cartão resume o **seu** evento; ordem cronológica (mais recente no topo) inalterada.
- **Evento sem `prev_data`/`new_data`** (demais ações de auditoria que por qualquer motivo casem no filtro): comportamento de hoje preservado (descrição + identificação), sem tentativa artificial de diff.

---

## 4. Requirements

### Functional Requirements

- **FR-001**: O cartão de um evento de **alteração cadastral** na "Trilha de Fluxo & Movimentações" DEVE apresentar um resumo legível contendo, conforme os dados existentes no evento: tipo de evento (rótulo da ação), identificação do bem (`resource_ref`/tombamento), data/hora, responsável (`Registrado por`), e — para cada campo alterado — rótulo amigável, valor anterior e valor posterior exibidos no **padrão visual já aceito do painel "Alterações cadastrais"** (valor anterior riscado + seta + valor posterior em destaque — decisão PD-3, clarify 2026-10-12). O JSON completo NÃO deve ser o conteúdo principal do cartão. **Título do cartão** (decisão clarify 2026-10-12): um campo alterado → "Alteração cadastral — <rótulo do campo>" (ex.: "Alteração cadastral — Nome do bem"); vários campos → "Alteração cadastral — Dados do equipamento"; sem diff utilizável → sem título de campo (comportamento atual preservado, FR-005).
- **FR-002**: O resumo DEVE conter **apenas** os campos efetivamente alterados; campos inalterados NÃO ocupam espaço na apresentação resumida. Todos os campos alterados de um evento DEVEM ser exibidos.
- **FR-003**: Os rótulos dos campos DEVEM corresponder à terminologia já usada para o cadastro de equipamentos (mesma fonte de rótulos do painel "Alterações cadastrais"); campo sem rótulo conhecido DEVE ser exibido pelo nome técnico, sem falhar a renderização.
- **FR-004**: O cartão DEVE disponibilizar um controle discreto **"Ver detalhes técnicos"**, recolhido por padrão, que expande/recolhe na própria página os dados técnicos completos do evento, preservando a distinção entre o estado anterior e o estado posterior, com renderização segura (dados como texto, nunca HTML/JS executável) e sem quebrar o layout com objetos extensos.
- **FR-005**: Quando o diff não puder ser calculado (JSON inválido, estrutura não-dict, um dos estados ausente, evento sem par antes/depois), o sistema DEVE exibir o que existe disponível, mantendo o comportamento tolerante atual — sem erro de renderização e sem inventar informação.
- **FR-006**: Valores nulos, strings vazias, números, booleanos, datas, enums e textos longos DEVEM ser apresentados de acordo com seus significados reais. A limitação histórica de que "chave ausente" e "valor nulo" são indistinguíveis no diff desserializado DEVE ser tratada com exibição neutra (`—`) no resumo, preservando-se a distinção no JSON original dos detalhes técnicos. **Decisão PD-4 (clarify 2026-10-12)**: `—` neutro para ausente e para nulo explícito no resumo; a spec optou deliberadamente por NÃO sinalizar "chave ausente" com marcador próprio, para não exibir artefatos de formato de snapshot como alterações reais.
- **FR-007**: A melhoria DEVE limitar-se aos cartões de eventos de alteração cadastral na trilha do detalhe do Equipamento. Os demais tipos de eventos da trilha (movimentações, manutenções e demais ações de auditoria) e o painel "Alterações cadastrais" permanecem inalterados; a distinção entre as duas seções é preservada e nenhum evento é exibido "duas vezes em formato detalhado" — o painel continua com seu resumo cadastral e a trilha com seu cartão resumido + detalhes técnicos sob demanda.
- **FR-008**: É PROIBIDO, como consequência desta feature: alterar `MovementService.get_timeline_for_asset` ou o payload de `GET /api/v1/assets/{asset_id}/timeline`; alterar a gravação de auditoria (`write_audit`/`write_change_audit`/`changed_fields`); alterar o esquema do banco ou os registros históricos; executar migrações; alterar rotas, permissões, autenticação, LDAP, importação/exportação ou relatórios; introduzir dependências novas.
- **FR-009**: Data, responsável, tipo de evento e vínculo com o equipamento DEVEM continuar corretos; a ordem cronológica e os critérios atuais de ordenação e limite da trilha permanecem inalterados; não pode existir edição ou exclusão de eventos; a visualização continua sujeita à mesma permissão atual (`patrimonio.visualizar`).
- **FR-010**: A implementação DEVE vir acompanhada de testes novos nos padrões existentes da suíte (arquivo novo, fixtures `client`/`db_session`, guarda de não-mutação) e a suíte completa DEVE permanecer verde, sem enfraquecer nenhum teste existente (Constitution VIII).
- **FR-011**: A apresentação DEVE seguir o padrão visual atual (Jinja2 + Bootstrap 5, tema claro/escuro), com contraste adequado, diferenciação dos valores sem depender exclusivamente de cores, quebra adequada de textos longos, sem rolagem horizontal desnecessária, e controle de expansão operável por teclado com estado acessível (sem animações novas nem elementos decorativos).

### Key Entities

- **`AuditLog` (existente, intocada)**: fonte única dos eventos — `timestamp`, `username` (snapshot), `action`, `module`, `resource`, `resource_id`, `resource_ref`, `result`, `description`, `previous_data`/`new_data` (JSON em TEXT). Trilha imutável e somente-leitura (Constitution IV/IX).
- **Item da timeline (estrutura existente)**: dicionário `{type: 'audit', timestamp, data: AuditLog, prev_data, new_data}` produzido hoje por `get_timeline_for_asset` — consumido pelo template (esta feature) e pela API (intocada).
- **`Asset` (existente, intocado)**: contexto da página; rótulos amigáveis dos campos derivam do cadastro real de equipamentos já mapeado em `_ASSET_FIELD_LABELS`.

---

## 5. Success Criteria

### Measurable Outcomes

- **SC-001**: 100% dos cartões de alteração cadastral da trilha exibem o resumo com campo, valor anterior e valor posterior; em eventos de campo único, o usuário identifica a alteração sem ler JSON (verificável por inspeção do HTML renderizado e por teste).
- **SC-002**: Nenhum campo inalterado aparece na apresentação resumida; todos os campos alterados de um evento aparecem (100% de cobertura do diff do evento).
- **SC-003**: Os dados técnicos completos permanecem consultáveis mediante expansão e recolhidos por padrão em 100% dos cartões com dados disponíveis.
- **SC-004**: Zero alteração no conteúdo de `audit_logs` (comparação antes/depois byte-a-byte) e payload idêntico em `GET /api/v1/assets/{id}/timeline` (comprovado por testes de guarda).
- **SC-005**: Eventos históricos com formatos diferentes, JSON inválido ou estados ausentes continuam sendo exibidos (100% dos eventos que a tela exibia antes continuam visíveis; nenhum erro de renderização).
- **SC-006**: Conteúdos com HTML/JavaScript em valores exibem-se como texto em 100% dos casos testados (nenhuma execução).
- **SC-007**: Cartões de movimentações, demais eventos de auditoria e o painel "Alterações cadastrais" permanecem idênticos aos atuais (testes das Specs 063/064/067 verdes sem edição).
- **SC-008**: Suíte de testes 100% verde no patamar atual, acrescida dos testes novos da feature (Constitution VIII).
- **SC-009**: Em smoke visual com dados reais, o operador identifica o que mudou, quem mudou e quando em cada cartão, em segundos, sem comparar JSON (validação com o usuário — print antes/depois).

---

## 6. Assumptions

- A fonte de rótulos amigáveis é o mapeamento **já existente** para o cadastro de equipamentos (`_ASSET_FIELD_LABELS`, 17 campos) usado pelo painel "Alterações cadastrais" — a feature **não cria** novo vocabulário nem tradução própria; campos futuros caem no nome técnico (FR-003).
- O cálculo da diferença é **transformação de leitura**: reutiliza a função já existente `changed_fields` (ou equivalente comportamento) sobre os `prev_data`/`new_data` já desserializados — nenhum dado novo é criado nem inferido além do que o evento registra.
- O controle de expansão aproveita mecanismo **já usado no projeto** para o mesmo fim (`<details>` nativo em `admin/audit/list.html`), salvo decisão em contrário no plan — sem JavaScript novo obrigatório.
- A duplicação de contexto entre o painel "Alterações cadastrais" (resumo) e a trilha (cartão resumido + detalhes técnicos) é **aceita e deliberada**: as seções têm papéis distintos (leitura rápida × histórico cronológico completo com rastreabilidade), conforme §7.
- Eventos de auditoria por bem alcançam a trilha hoje essencialmente como `ALTERACAO`; a solução é **genérica por ação** — não depende de ser específica de uma ação ou de um campo (FR-001).
- Documentação: nenhum artigo da central de ajuda descreve o formato atual dos cartões de auditoria da trilha (verificação análoga da Spec 063) — nenhuma atualização obrigatória; reconfirmar na implementação (Constitution XI).
- Escopo exclusivo: módulo **Equipamentos**, tela `/assets/{id}`. Nenhuma outra tela de auditoria (`/admin/audit`), cadastro, movimentação, manutenção, inventário, relatório ou exportação é afetada.

---

## 7. Integração com o painel "Alterações cadastrais" e preservação dos demais eventos

**Alterações cadastrais** (painel superior, Feature 067): permanece exatamente como está — resumo cadastral com estilos próprios, teto de 50 eventos e aviso de truncamento. Nenhuma mudança em sua lógica de dados.

**Trilha de Fluxo & Movimentações**: continua apresentando os eventos em ordem cronológica (mais recente no topo) com responsável, data, identificação e informações específicas por categoria. A mudança atinge **somente o ramo de renderização dos eventos de alteração cadastral** (`item.type == 'audit'` com diff disponível):

- **Alterações cadastrais** → resumo legível (novo) + "Ver detalhes técnicos" (novo, recolhido).
- **Movimentações** (ENTRADA, ALOCAÇÃO, TRANSFERÊNCIA, MANUTENÇÃO etc.) → cartão com Origem/Destino no padrão das Specs 063/064, motivo, operador e termo — **intocado**.
- **Demais eventos de auditoria** que apareçam na trilha (sem diff utilizável) → descrição + identificação atuais preservados (FR-005).

Não há conversão de movimentações ou ações operacionais em "alteração cadastral", nem remoção de informações específicas de nenhuma categoria.

---

## 8. Critérios de Aceitação (rastreabilidade)

| AC | Enunciado | Coberto por |
|---|---|---|
| AC01 | Evento de um único campo: o cartão apresenta campo, valor anterior e valor posterior sem usar o JSON completo como conteúdo principal | US1/AS1; FR-001; SC-001 |
| AC02 | Evento de vários campos: todos os campos alterados aparecem com seus antes/depois | US1/AS2; FR-002; SC-002 |
| AC03 | Campos inalterados não ocupam espaço na apresentação resumida | US1/AS3; FR-002; SC-002 |
| AC04 | Rótulos amigáveis conforme o mapeamento real do cadastro; campo desconhecido exibido pelo nome técnico sem quebra | US1/AS4–AS5; FR-003 |
| AC05 | Detalhes técnicos expansíveis com os estados originais anterior e posterior | US2/AS2; FR-004; SC-003 |
| AC06 | Detalhes técnicos recolhidos por padrão (cartão não cresce) | US2/AS1; FR-004; SC-003 |
| AC07 | A renderização não altera conteúdo de eventos armazenados (byte-a-byte) | US3/AS3; FR-008; SC-004 |
| AC08 | Eventos anteriores, incompletos ou em formatos diferentes continuam exibidos (fallback) | Edge Cases; FR-005; SC-005 |
| AC09 | Nulos, vazios, números, booleanos, datas, enums, textos longos e caracteres especiais exibidos conforme seus significados reais | Edge Cases; FR-006 |
| AC10 | HTML/JavaScript em valores exibido como dado, sem execução | US2/AS3; FR-004; SC-006 |
| AC11 | Movimentações, manutenções e demais categorias de eventos inalterados | US3/AS1; FR-007; SC-007 |
| AC12 | Data, responsável, tipo de evento e vínculo com o equipamento corretos; ordem cronológica inalterada | FR-001; FR-009 |
| AC13 | Controle de expansão utilizável por teclado, com estado acessível | US2/AS2; FR-011 |
| AC14 | Conteúdo legível nas resoluções suportadas, sem quebras indevidas de layout nem rolagem horizontal | Edge Cases; FR-011 |
| AC15 | Suíte existente (Equipamentos, detalhe, auditoria, movimentações, Specs 063/064/067) permanece verde sem edição de testes | FR-010; SC-008 |
| AC16 | Nenhum comportamento de outras telas/módulos que usem a auditoria muda; payload da API de timeline idêntico | US3/AS4; FR-008; SC-004 |
| AC17 | Nenhuma mudança de esquema de banco ou de estrutura dos registros históricos | FR-008; SC-004 |

---

## 9. Impacto esperado (arquivos candidatos — fundamentado na análise)

| Componente | Alteração esperada |
|---|---|
| `app/web/templates/assets/detail.html` (ramo `item.type == 'audit'`, L285–321) | **SIM** — resumo legível + controle "Ver detalhes técnicos"; restante do template intocado (cartões de movimentação 063/064, "Custódia", ficha, QR) |
| Helper de apresentação (somente leitura em `app/services/asset_service.py` — padrão 067; chamado pela rota `view_asset_detail` para enriquecer os itens de auditoria) | **SIM** (decisão PD-1/PD-2 — clarify 2026-10-12) — reutiliza `changed_fields` + `_ASSET_FIELD_LABELS` no mesmo módulo, sem duplicar lógica (Constitution II/III); `templates_env.py` fica fora do escopo |
| `app/services/movement_service.py` (`get_timeline_for_asset`) | **NENHUM** (contrato da API congelado — Specs 029/067) |
| `app/services/audit_service.py` (gravação, `write_change_audit`, `changed_fields`) | **NENHUM** (somente reutilização dos existentes) |
| `app/web/routers/assets.py` / `app/api/assets_api.py` | **NENHUM** |
| Banco de dados / `migrations/` | **NENHUM** (zero DDL) |
| `admin/audit/list.html`, demais telas, relatórios, importação/exportação, permissões/LDAP | **NENHUM** |
| Testes | **NOVOS** — ex.: `tests/test_legibilidade_trilha_070.py` (renderização RED→GREEN + guarda de não-mutação e contrato da API); nenhum teste existente modificado |
| Documentação / ajuda central | **NÃO REQUERIDA** (reconfirmar na implementação — Constitution XI) |

---

## 10. Riscos e mitigações

| # | Risco | Mitigação |
|---|---|---|
| 1 | Alterar `get_timeline_for_asset` e quebrar o contrato de `GET /api/v1/assets/{id}/timeline` ( Specs 029/067, `test_api.py`) | FR-008 proíbe; guarda de payload idêntico nos testes novos |
| 2 | Editar o mesmo bloco do template e afetar os cartões de movimentação (063/064) ou o painel cadastral (067) | Diff restrito ao ramo `item.type == 'audit'`; suítes 063/064/067 como régua de regressão (AC15/SC-007) |
| 3 | Inventar informação ao interpretar snapshots históricos com formatos divergentes | FR-005/FR-006: fallback para exibição do que existe; união de chaves; sem decomposição que crie valor |
| 4 | Duplicar a lógica de diff/rótulos já existente (duas fontes de verdade) | Reutilização obrigatória de `changed_fields` + fonte única de rótulos (PD-2); revisão de escopo |
| 5 | Expor dados técnicos além das permissões atuais | O controle expande **apenas** os dados já entregues hoje ao template da mesma página (mesma permissão `patrimonio.visualizar`); nenhum dado novo é buscado |
| 6 | Interpretação acidental de dados históricos como HTML/JS | Autoescape preservado + conteúdo dentro de `pre`/texto escapado; teste com payload hostil (AC10) |
| 7 | Interpretar "chave ausente" como alteração ou mascarar a limitação | FR-006 documenta o fallback `—` e mantém a distinção no JSON original |
| 8 | Regressão de datas exibidas (feature 004 — `localtime`) | Reutilizar o filtro `localtime` existente no cartão; teste `test_datetime_flows.py` na régua |

---

## 11. Escopo

### Incluído

- Apresentação resumida (campos alterados com rótulo, antes → depois) nos cartões de **alteração cadastral** da "Trilha de Fluxo & Movimentações" do detalhe do Equipamento (`/assets/{id}`);
- Controle discreto "Ver detalhes técnicos" (recolhido por padrão) com os estados originais Antes/Depois;
- Helper de apresentação reutilizável (decidido no plan) que expõe diff + rótulos já existentes, sem duplicar lógica;
- Testes novos de renderização, casos especiais e guarda de não-mutação/contrato.

### Não incluído (limites de escopo)

- Alterações em gravação de auditoria, `MovementService`, API, rotas, permissões, autenticação, LDAP, banco ou migrações (FR-008);
- O painel "Alterações cadastrais" (Feature 067) e os cartões de movimentação (Features 063/064) — intocados;
- Tela `/admin/audit` e demais consumidores da trilha (relatórios, exportações, dashboard) — fora do escopo, com formatação própria aprovada;
- Importação/exportação de equipamentos e relatórios CSV/Excel/PDF;
- Higiene de dados cadastrais ou refatorações não relacionadas (Constitution I);
- Novas dependências, novos elementos decorativos ou animações.

---

## 12. Decisões técnicas (todas fechadas no clarify de 2026-10-12 — contexto para `/speckit-plan`)

| # | Pendência | Alternativas registradas |
|---|---|---|
| ~~PD-1~~ | **RESOLVIDA (clarify 2026-10-12)** — helper somente-leitura em service (padrão 067), chamado pela rota `view_asset_detail`. Descartadas: filtro global Jinja (diff fora do service) e pós-processamento só na rota (lógica de apresentação espalhada fora do service). Ver `## Clarifications` | Ver `## Clarifications` |
| ~~PD-2~~ | **RESOLVIDA por consequência (clarify 2026-10-12)** — o helper vive no mesmo módulo do `_ASSET_FIELD_LABELS` (`asset_service.py`) e reutiliza o dicionário no lugar; nenhuma exportação, módulo compartilhado ou duplicação | Ver `## Clarifications` |
| ~~PD-3~~ | **RESOLVIDA (clarify 2026-10-12)** — opção A: padrão do painel "Alterações cadastrais" (`rótulo: ~~anterior~~ → **posterior**`), estilos reaproveitados, zero CSS novo. Descartadas: rótulos explícitos em linhas separadas (B) e híbrido com rótulos ocultos (C) | Ver `## Clarifications` |
| ~~PD-4~~ | **RESOLVIDA (clarify 2026-10-12)** — opção A: `—` neutro para ausente e nulo no resumo; distinção preservada apenas nos detalhes técnicos (JSON original). Descartadas: distinção por membership (B, risco de artefatos web×API) e representação crua (C) | Ver `## Clarifications` |

---

> **Nota de etapa**: esta especificação descreve SOMENTE o comportamento desejado e a análise verificada do código atual. **Nada foi implementado** — nenhum template, service, rota, modelo ou teste foi alterado na elaboração deste documento; nenhum commit foi realizado. O plano de implementação (ordem de tarefas, TDD red→green, checkpoints) segue o padrão da casa em etapa própria (`/speckit-plan` → `/speckit-tasks`) — as pendências técnicas PD-1…PD-4 foram **fechadas no clarify de 2026-10-12** (ver `## Clarifications`).
