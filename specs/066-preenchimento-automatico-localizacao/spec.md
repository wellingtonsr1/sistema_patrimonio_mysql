# Feature Specification: Preenchimento Automático do Campo Localização

**Feature Branch**: `066-preenchimento-automatico-localizacao`

**Created**: 2026-10-09

**Status**: **APROVADA (2026-10-09)** — todas as pendências resolvidas: P1 e P2 aprovadas pelo responsável; P3 e P4 resolvidas via `/speckit-clarify` (ver Clarifications e §14). Pronta para implementação (`tasks.md` completo).

**Input**: User description: "Fazer com que o campo obrigatório 'Localização' do cadastro de localizações seja preenchido automaticamente pela combinação de 'Unidade Administrativa' + 'Departamento / Setor' (formato `Unidade - Departamento`), padronizando os nomes, reduzindo erros de digitação e mantendo compatibilidade com cadastros, movimentações, relatórios e importações existentes. Etapa de análise em modo somente leitura antes de qualquer alteração de código."

---

## Clarifications

### Session 2026-10-09

- Q: Quando duas localizações tiverem a mesma Unidade Administrativa e o mesmo Departamento/Setor — gerando o mesmo nome automático — o que o sistema deve fazer com o segundo cadastro? (P3) → A: **Bloquear** com a mensagem de duplicidade já existente ("Já existe um local cadastrado com este nome"); sem sufixo manual nem composição com prédio/andar/sala nesta feature — comportamento atual confirmado como desejado e dívida registrada para feature própria.
- Q: Escopo de documentação a atualizar junto com a mudança (placeholder do campo e central de ajuda)? (P4) → A: **Tudo na mesma implementação** — placeholder do campo, artigo `cadastrar-locais` da central de ajuda e `docs/ARQUITETURA_E_MANUTENCAO.md` (Constitution XI).

---

## 1. Diagnóstico do comportamento atual (Fase 1 — somente leitura, verificado 2026-10-09)

### 1.1 Formulário e interface

| # | Ponto investigado | Realidade verificada |
|---|---|---|
| 1 | Template da tela "Cadastrar Localização ou Departamento" | `app/web/templates/locations/form.html` — `<form method="post" action="/locations/new">` (L25) com campos **livres**: `name` (label "Localização", `required`, placeholder "Ex: Matriz SP - TI - Data Center" ~L27–29), `branch` (label "Unidade Administrativa", `required` ~L31–33), `department` (label "Departamento / Setor", `required` ~L35–37), além de `manager_name`, `building`, `floor`, `room`, `description` |
| 2 | JavaScript associado | **Nenhum** — o template não possui bloco `<script>`; não há sincronização entre os campos |
| 3 | Validação | Apenas HTML5 `required` nos três campos; sem máscara, sem composição, sem verificação de unicidade no cliente |
| 4 | Padrão visual | Bootstrap 5 no padrão da casa; erro exibido via `?error=` (alert `alert-danger` no topo do template) |
| 5 | Viabilidade de cálculo no navegador | **Confirmada**: composição de dois `input[type=text]` com atualização em `input`/`change` não conflita com validação, acessibilidade (`readonly` + label permanece) nem com o envio do formulário |

### 1.2 Backend e banco de dados

| # | Ponto investigado | Realidade verificada |
|---|---|---|
| 1 | Rota web de criação | `GET/POST /locations/new` → `form_new_location` / `create_location_form` (`app/web/routers/locations.py` L195–243), permissão `locais.criar`. O POST recebe `name`, `branch`, `department` como `Form(...)` obrigatórios, monta `LocationCreate` e delega a `LocationService.create` |
| 2 | Rota web de edição | **NÃO EXISTE** edição web de local (varredura de rotas + `route_manifest.json` só mostra `/locations/new` e import). Edição só pela API |
| 3 | API REST | `POST /api/v1/locations` (`locais.criar`) e `PUT /api/v1/locations/{id}` (`locais.editar`) em `app/api/locations_api.py` (L46/L68) — recebem `name` explícito no payload (`LocationCreate`/`LocationUpdate` de `app/schemas/location.py`) |
| 4 | Service | `app/services/location_service.py` — `create` valida unicidade por nome (`get_by_name`, L34 → `ValueError("Já existe um local cadastrado com este nome")`); `update` idem com `exclude_unset` (L53–70); `get_all` ordena por `branch, department, name` |
| 5 | Modelo | `app/models/location.py` — `name` **String(100) NOT NULL UNIQUE index** (L12), `branch` NOT NULL, `department` NOT NULL, `building`/`floor`/`room`/`manager_name` opcionais |
| 6 | Relacionamentos | `Asset.location_id` (FK → `locations.id`); `Movement.origin_location_id`/`destination_location_id` (FK) **+ snapshots de texto** `origin/destination_location_name` (String 150) gravados no formato `f"{branch} - {department} ({name})"` (`app/services/movement_service.py` L136/L148) |
| 7 | Identificador da localização | **Ambos**: internamente o `id` (FKs, seletores de formulário enviam `value="{{ loc.id }}"`); no nível de negócio o **nome é chave natural** — unicidade no modelo e resolução por nome em importações e inventário offline (ver §1.3) |
| 8 | Importação de locais (CSV) | `app/services/location_import_service.py` — coluna **"Localização" (nome) é obrigatória e separada** de "Unidade Administrativa" e "Departamento"; duplicidade detectada por nome; importação **só cria**, nunca atualiza |
| 9 | Exclusão | Não há rota de exclusão de local (web ou API) |
| 10 | Departamento/Setor | Confirmado no código e no banco: `Location.department` é texto NOT NULL; é a **fonte da lista oficial** usada pelo colaborador (spec 012) e rótulo no dropdown de destino da movimentação (spec 062). `Custodian.department` é coluna distinta, sem FK |

### 1.3 Uso atual do nome da localização (maior risco de compatibilidade)

| Área | Uso de `Location.name` | Referência |
|---|---|---|
| Cadastro/edição | Chave de unicidade (`ValueError` em duplicidade) | `location_service.py` L34/L59 |
| **Importação de bens (CSV)** | **Resolução do local pelo nome** — `LocationService.get_by_name(db, loc_raw)`; nome não encontrado = erro/NAO_ENCONTRADO | `import_service.py` L494; `import_intelligence.py` L362 |
| **Importação de locais (CSV)** | Nome é obrigatório; duplicata = skip/erro | `location_import_service.py` L123, L169 |
| **Inventário offline (PWA)** | Casamento exato `Location.name == found_location_name.strip()` | `inventario_offline_service.py` L292 |
| Movimentações | Seleção por **id**; exibição/CSV/relatório usam o **snapshot texto** gravado no evento, não o cadastro atual | `movements/list.html` L137/148, `report_service.py` L518–520 |
| Busca (spec 007) | Filtro mono-campo `Location.name.ilike` | `location_service.py` L21 |
| Telas e documentos | Exibição direta (`loc.name`) em listagem de locais, bens, etiquetas, inventário, termo, relatórios, dashboard | `locations/list.html` L67, `assets/list.html` L77, `movements/term.html` L97 etc. |
| Exportações | CSV de locais exporta `name, branch, department, ...` como colunas separadas | `report_service.generate_locations_csv` (spec 008) |
| Testes e demo | Dezenas de fixtures criam locais com nome arbitrário (ex.: `name="TI", branch="SP"`) via `LocationService.create` | `tests/test_movements.py` L43/L88, `seed_demo.py` |

**Conclusão da Fase 1**: o nome é usado como identificador **apenas em fluxos de resolução por texto** (importações e inventário offline); o fluxo de movimentação usa `id` + snapshot imutável. Como a proposta **não muda o padrão existente dos dados** (ver §1.4), esses fluxos não são afetados.

### 1.4 Verificação dos dados existentes (somente leitura — MariaDB real `sispatrimoniopro_db`, 2026-10-09)

| Verificação | Resultado |
|---|---|
| Total de localizações | **37** |
| Nomes no padrão `branch - department` exato (`CONCAT(TRIM(branch),' - ',TRIM(department))`) | **37/37 (100%)** |
| Nomes divergentes/incompletos | **0** |
| Localizações sem unidade ou sem departamento | **0** |
| Nomes duplicados (case-insensitive) | **0** |
| Mesmo `department` em `branch`s diferentes | **0** |
| Mesmo par `branch+department` (colisão futura do nome automático) | **0** |
| Nomes acima de 100 caracteres (limite da coluna) | **0** (máx.: branch 16, department 35, soma+separador 50) |
| Espaços sobrando em `name`/`branch`/`department` | **0** |
| Locais com prédio/andar/sala preenchidos | **0** (todos NULL — o nome atual não carrega esses dados) |
| Bens com local vinculado / movimentações gravadas | 310 de 313 bens; **352 movimentações** |

**Conclusão da Fase 1.4**: o banco **já segue 100% o padrão proposto** (`Unidade Administrativa - Departamento / Setor`). A feature é a **formalização e automatização** de uma convenção já verdadeira nos dados — não é uma migração de nomenclatura. Nenhuma consulta retornou resultado que exija renomear registros.

---

## 2. Problema e motivação

O campo "Localização" é digitado livremente pelo usuário, embora na prática seja a composição de "Unidade Administrativa" + "Departamento / Setor". Isso gera: (a) risco de divergência entre os três campos (nome que não bate com a unidade/setor informados ao lado); (b) erros de digitação e espaços acidentais; (c) dependência do disciplínio do usuário para manter um padrão que o sistema já espera como chave de unicidade e de resolução em importações. Como 100% dos dados reais já seguem o padrão, automatizar a composição elimina a causa do problema sem necessidade de migração.

## 3. Objetivo e escopo

**Objetivo**: no formulário web de cadastro de localização, o campo "Localização" passa a ser gerado automaticamente a partir de `Unidade Administrativa` + `Departamento / Setor`, no formato `Unidade - Departamento`, com validação definitiva no servidor.

**INCLUI (escopo)**:
- Composição automática (sincronizada em tempo real) do campo `name` no template `locations/form.html`.
- Regra de composição centralizada no service (fonte única) e aplicada de forma autoritativa no `POST /locations/new`.
- Tratamento de duplicidade, limite de tamanho e campos incompletos na tela de cadastro.
- Testes automatizados novos de geração, falsificação, duplicidade e regressão.

**NÃO INCLUI (fora do escopo)**:
- Alterar nomes, registros ou snapshots existentes (nenhuma migração de dados).
- Alterar o esquema do banco (zero DDL — Constitution VII).
- Alterar a API REST (`POST/PUT /api/v1/locations`), a importação CSV de locais, a importação de bens ou o inventário offline — contratos preservados (ver §8 e Pendência P1).
- Criar tela de edição web de local (não existe hoje; feature própria).
- Incluir prédio/andar/sala na composição do nome (recomendação do responsável confirmada: permanecem campos separados).
- Alterar snapshots de movimentações, relatórios, CSV, termos ou dashboard.

## 4. Comportamento funcional esperado

### 4.1 Regras de geração do nome (regra definitiva)

1. **Formato**: `TRIM(branch) + " - " + TRIM(department)` — ex.: `IPMJP - Sede - Divisão de Previdência`.
2. **Sem espaços excedentes**: cada componente é aparado (`strip`) antes da junção; um único separador ` - ` entre eles; nenhum separador fantasma se um componente vier vazio (não ocorre — ambos são obrigatórios).
3. **Fonte única**: a função de composição vive no service (`LocationService`), usada pela rota web e pelo cliente (mesmo resultado nos dois lados).
4. **Autoridade do servidor**: no `POST /locations/new`, o valor do campo `name` enviado pelo navegador é **ignorado** e recomposto a partir de `branch`/`department` recebidos — requisição manipulada não persiste nome divergente (AC05).
5. **Tamanho**: o nome composto deve caber em 100 caracteres (coluna `locations.name`); se exceder, o servidor rejeita com mensagem clara (sem truncamento silencioso).
6. **Nada de prédio/andar/sala** na composição; esses campos continuam independentes e opcionais.

### 4.2 Comportamento no preenchimento (sincronização dinâmica)

| Estado dos campos de origem | Campo "Localização" |
|---|---|
| Nenhum preenchido | Vazio |
| Só `branch` | Vazio |
| Só `department` | Vazio |
| Ambos preenchidos | Exibe `branch - department` atualizado a cada tecla (`input`/`change`) |

- O campo é `readonly` (não digitar, mas **enviado** no form — `disabled` seria omitido e quebraria o `required` atual).
- **Não é permitido salvar incompleto**: `branch` e `department` continuam `required` (HTML + servidor); enquanto um estiver vazio, o nome permanece vazio e o submit é bloqueado pela validação nativa do navegador — nenhum registro inválido é criado para acomodar a geração automática.
- Sem JavaScript, o servidor continua recompondo o nome a partir dos dois campos enviados: o valor do campo `name` é dispensável (FR-003), de modo que a falha de script não produz registro errado.

### 4.3 Duplicidades

- A combinação pode gerar nome já cadastrado: a unicidade **já existente** (`name` UNIQUE + `get_by_name` em `create`) intercepta e exibe a mensagem atual "Já existe um local cadastrado com este nome" via `?error=` — compreensível e sem registro indevido.
- **Nenhum nome existente é alterado** para contornar conflito. Hoje não há colisão possível (0 pares `branch+department` repetidos — §1.4).
- **Colisão branch+department no futuro** (duas salas do mesmo setor na mesma unidade): a composição geraria nome idêntico e o **segundo cadastro é bloqueado** pela mesma regra de unicidade, com a mensagem atual — decisão aprovada em Clarifications 2026-10-09 (P3). Sem sufixo manual e sem incluir prédio/andar/sala nesta feature; o tratamento dessa exceção é dívida registrada para feature própria.

### 4.4 Cadastro × edição

- **Cadastro (em escopo)**: nova localização nasce com o nome composto.
- **Edição**: não existe edição web; a `PUT /api/v1/locations/{id}` permanece intocada (contrato). Como o service usa `exclude_unset`, atualizações parciais que não enviam `name` **não renomeiam** — abrir/editar registros antigos não provoca renomeações inesperadas (AC08).
- Registros antigos mantêm seus nomes; como 37/37 já são do padrão, não há "fora do padrão" a conviver.

## 5. User Scenarios & Testing *(mandatory)*

### User Story 1 — Geração automática no formulário de cadastro (Priority: P1)

Como operador com permissão `locais.criar`,
ao preencher "Unidade Administrativa" e "Departamento / Setor" no formulário `/locations/new`,
quero ver o campo "Localização" ser preenchido automaticamente com `Unidade - Departamento`,
para que o nome nasça padronizado sem digitação manual.

**Why this priority**: É o objetivo central da funcionalidade.

**Independent Test**: Abrir `/locations/new`, digitar branch e department e observar o campo Localização refletir a composição em tempo real; submeter e conferir o registro criado.

**Acceptance Scenarios**:
1. **Given** formulário vazio, **When** usuário digita `IPMJP - Sede` em Unidade e `Divisão de Previdência` em Departamento, **Then** Localização exibe `IPMJP - Sede - Divisão de Previdência` sem submeter.
2. **Given** ambos os campos preenchidos, **When** o usuário corrige o departamento, **Then** o nome gerado é atualizado imediatamente.
3. **Given** só a Unidade preenchida, **When** o formulário está parado, **Then** Localização permanece vazia.
4. **Given** dados válidos, **When** o formulário é enviado, **Then** o registro é criado com `name` exatamente igual à composição e redireciona para `/locations`.

### User Story 2 — Validação autoritativa no servidor (Priority: P2)

Como administrador e auditor de integridade,
quero que o servidor ignore o valor do campo Localização enviado pelo navegador e o recomponha a partir dos campos de origem,
para que requisições manipuladas não persistam nomes fora do padrão.

**Why this priority**: Garante que a padronização não dependa do cliente (validação em backend — Constitution VI).

**Independent Test**: Enviar POST a `/locations/new` com `name="Nome Falsificado"` e branch/department válidos; o registro criado deve trazer o nome recomposto.

**Acceptance Scenarios**:
1. **Given** um POST manipulado com `name="Hackeado"`, `branch="IPMJP - Sede"`, `department="TI"`, **When** processado, **Then** persiste `IPMJP - Sede - TI`.
2. **Given** um POST com composição que atinge nome já cadastrado, **When** processado, **Then** nenhum registro é criado e a mensagem de duplicidade é exibida.
3. **Given** um POST cujo nome composto exceder 100 caracteres, **When** processado, **Then** a criação é rejeitada com mensagem clara, sem gravação truncada.

### User Story 3 — Compatibilidade com fluxos existentes (Priority: P3)

Como usuário do sistema,
quero que importações, movimentações, relatórios, inventário e históricos continuem funcionando exatamente como antes,
para que a mudança não provoque regressão.

**Why this priority**: A feature só cria valor se não quebra nada do que já funciona.

**Independent Test**: Rodar a suíte de regressão (locais, movimentações, importações, inventário) e validar os fluxos de leitura após o cadastro de um local novo.

**Acceptance Scenarios**:
1. **Given** localizações antigas no banco, **When** consultadas em listas, movimentações, relatórios e CSV, **Then** permanecem byte-a-byte inalteradas.
2. **Given** um local novo criado com nome composto, **When** um CSV de bens referencia esse nome em importação, **Then** a resolução `get_by_name` encontra o local normalmente.
3. **Given** a API REST `POST/PUT /api/v1/locations`, **When** chamada com `name` explícito, **Then** o contrato é presetado como hoje (sem imposição da composição).

### Edge Cases

- Branch ou department apenas com espaços: tratados como vazios (`strip`) → nome fica vazio e `required` bloqueia o submit.
- Nome composto com acentuação/literals longos: válidos (UTF-8), limitados a 100 caracteres.
- Colisão de nome com registro existente: mensagem atual de duplicidade, sem criação.
- Nomes legados fora do padrão: nenhum existe hoje (37/37); se surgirem por importação/API, permanecem intactos — a regra vale para o fluxo web de cadastro.
- Falha de JavaScript: servidor recompose o nome — sem dependência exclusiva do cliente.

## 6. Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O formulário `/locations/new` MUST exibir o campo "Localização" preenchido automaticamente com `TRIM(branch) + " - " + TRIM(department)` sempre que ambos os campos de origem tiverem valor, mantendo-se sincronizado a cada alteração.
- **FR-002**: O campo "Localização" MUST ser `readonly` (visível e enviado no formulário), com label e indicação de preenchimento automático; `branch` e `department` permanecem `required`.
- **FR-003**: No `POST /locations/new`, o servidor MUST ignorar o valor de `name` enviado pelo cliente e recompor o nome a partir de `branch`/`department`, usando a função de composição do service (fonte única da regra — Constitution II/III).
- **FR-004**: O nome composto MUST respeitar o limite de 100 caracteres; excedeu → rejeição com mensagem amigável (sem truncamento silencioso).
- **FR-005**: Enquanto um dos campos de origem estiver ausente, o sistema MUST manter a Localização vazia e impedir o salvamento (validação nativa + servidor), nunca criando registro incompleto.
- **FR-006**: Duplicidade MUST continuar sendo detectada pelas regras de unicidade existentes (`name` UNIQUE + `get_by_name`), com a mensagem atual — nenhum registro existente é renomeado.
- **FR-007**: A API REST, a importação CSV de locais, a importação de bens e o inventário offline NÃO devem sofrer alteração de contrato nesta feature (ver Pendência P1).
- **FR-008**: Nenhum registro existente, snapshot de movimentação, documento ou histórico pode ser alterado (zero migração de dados; zero DDL).
- **FR-009**: A regra de composição MUST ficar centralizada no service (`LocationService`), sem duplicação de lógica entre template e rota além da chamada ao helper compartilhado.
- **FR-010**: A implementação MUST ser cirúrgica: apenas template, rota web de criação, service (helper), testes e documentação visível correspondente.

### Key Entities

- **Localização (`Location`)**: unidade física/departamental; atributos relevantes: `name` (chave natural, UNIQUE 100), `branch` (obrigatório), `department` (obrigatório), opcionais prédio/andar/sala/gestor/descrição; referenciada por `Asset.location_id` e por FKs+snapshots em `Movement`.

## 7. Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos novos locais criados pela tela web nascem com `name == branch - department`, sem intervenção de digitação no campo.
- **SC-002**: 100% das requisições manipuladas no campo `name` do formulário web são neutralizadas (nome recomposto no servidor).
- **SC-003**: 0 registros históricos alterados; banco permanece com os mesmos 37 nomes (quando não houver cadastro novo).
- **SC-004**: Suíte pytest existente permanece verde (sem testes removidos ou enfraquecidos) + novos testes da feature passando.
- **SC-005**: Nenhuma quebra em importação de bens/locais, movimentações, relatórios, CSV e inventário (regressão executada e registrada).

## 8. Compatibilidade (requisitos derivados da análise)

- **Identificação por nome**: preservada — o padrão dos nomes novos é idêntico ao dos existentes (37/37), então `get_by_name` (importação de bens, importação de locais, inventário offline) segue resolvendo normalmente.
- **Movimentações**: usa `id` + snapshots imutáveis; nada muda em origem/destino, busca (049), CSV, termo, dashboard, trilha 063 e Fluxo Global 064.
- **Exportações**: CSV de locais continua com colunas separadas `nome;filial;departamento;...`.
- **Contratos de API/importação**: intactos (FR-007) — a regra vale para o fluxo web; registros criados por API/CSV com nome explícito não são reescritos.
- **Banco**: zero DDL, zero migração, zero UPDATE (AC11).

## 9. Alternativas avaliadas

| Alternativa | Descrição | Veredito |
|---|---|---|
| **A — Composição web + autoridade no servidor da rota web** (helper no service; API/importação intocadas) | Menor mudança que atinge o fluxo onde o problema existe (digitação manual) | ✅ **ESCOLHIDA** |
| B — Imposição em `LocationService.create` (todas as origens) | Quebraria API REST, `seed_demo`, CLI e dezenas de testes que criam locais com nome arbitrário (`name="TI", branch="SP"`) | ❌ Descartada — violaria FR-007/Constitution I |
| C — Apenas JavaScript no cliente (sem servidor) | Barato, mas aceita requisição manipulada (AC05 falharia) | ❌ Descartada |
| D — Campo oculto em vez de `readonly` | Perde transparência/validação visual do usuário | ❌ Descartada (usar `readonly` visível) |

## 10. Critérios de aceitação

- **AC01 — Geração automática**: o campo Localização é preenchido a partir de Unidade Administrativa e Departamento / Setor.
- **AC02 — Atualização dinâmica**: alterações nos campos de origem atualizam o nome gerado durante o preenchimento.
- **AC03 — Padronização**: o resultado segue `Unidade - Departamento`, sem espaços excedentes nem separadores duplicados.
- **AC04 — Somente leitura**: o usuário não digita o nome gerado (`readonly` visível), conforme viabilidade confirmada (§1.1 item 5).
- **AC05 — Validação no servidor**: requisição manipulada no campo `name` não persiste valor divergente do par `branch`/`department`.
- **AC06 — Campos incompletos**: com um ou ambos os campos de origem vazios, a Localização fica vazia e o salvamento é impedido; nenhum registro inválido é criado.
- **AC07 — Duplicidade**: conflito de nome é identificado pelas regras de unicidade existentes, com mensagem compreensível e sem criação indevida; nada é renomeado.
- **AC08 — Edição segura**: registros antigos não são renomeados (API PUT intocada; `exclude_unset` preservado; nenhum UPDATE de dados).
- **AC09 — Compatibilidade**: patrimônio, movimentações, relatórios, documentos, importações e exportações continuam funcionando (suíte verde).
- **AC10 — Histórico preservado**: snapshots, documentos e dados anteriores permanecem inalterados.
- **AC11 — Banco preservado**: zero DDL, zero migração, zero alteração de dados.
- **AC12 — Testes de regressão**: suítes existentes identificadas no plano §12 e novos testes cobrindo AC01–AC06.

## 11. Arquivos provavelmente envolvidos

| Arquivo | Alteração justificada |
|---|---|
| `app/web/templates/locations/form.html` | Tornar `name` `readonly` + label "preenchido automaticamente"; adicionar JS de sincronização (listener nos 2 campos, `strip` + junção ` - `); ajustar placeholder do campo para refletir o padrão |
| `app/web/routers/locations.py` | No `create_location_form`: tornar `name` opcional no form e **recompor** via helper do service antes de criar (ignora valor do cliente) |
| `app/services/location_service.py` | Adicionar helper puro de composição (fonte única), sem alterar `create`/`update`/`get_all` |
| `tests/test_localizacao_automatica_066.py` | **Novo**: geração, sincronização, AC05 (falsificação), duplicidade, tamanho, incompletos, regressão |
| `docs/ARQUITETURA_E_MANUTENCAO.md` | Nota na seção de Locais sobre a composição automática (Constitution XI — mudança de comportamento visível) |

**Intactos**: `app/models/location.py`, `app/schemas/location.py`, `app/api/locations_api.py`, `location_import_service.py`, `import_service.py`, `inventario_offline_service.py`, `movement_service.py`, templates de movimentações/relatórios, demais testes.

## 12. Plano mínimo de testes

**Regressão executada sem edição** (padrão da casa): `test_locations_search.py`, `test_movements.py`, `test_department_selection.py`, `test_import_asset_location.py`, `test_import_asset_movements.py`, `test_departamento_destino_062.py`, `test_presentacao_trilha_063.py`, `test_fluxo_global_064.py` + régua completa `python -m pytest`.

**Novos testes** (`tests/test_localizacao_automatica_066.py`):

| Teste | Protege |
|---|---|
| `test_localizacao_gerada_no_template` | AC01/AC02/AC03 (JS reflete composição; readonly) |
| `test_post_web_recompoe_nome_ignorando_cliente` | AC05 (POST com `name` adulterado grava a composição) |
| `test_campos_incompletos_nao_criam_registro` | AC06 (branch ou department vazio → sem criação) |
| `test_duplicidade_por_nome_composto` | AC07 (mensagem atual; nenhum registro indevido) |
| `test_nome_composto_acima_de_100_chars_rejeitado` | FR-004 (sem truncamento silencioso) |
| `test_dados_existentes_intocados_e_regressao` | AC08/AC10/AC11 (contagem e nomes do banco de teste inalterados; API PUT segue aceitando payload atual) |

Procedimento de validação com dados de teste: suíte em SQLite in-memory (`tests/conftest.py`, padrão da casa) + verificação manual opcional no ambiente com `DATABASE_URL` (contagem de 37 locais antes/depois sem escrita).

## 13. Riscos e medidas de mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Rejeição do usuário por não poder acrescentar detalhe (ex.: " - Data Center") ao nome | Médio | Pendência P2 — dados mostram 0 usos (locais com prédio/andar/sala estão vazios); descrição/prédio continuam como campos próprios |
| Colisão futura de `branch+department` (dois locais no mesmo setor) | Baixo | **Decidido (P3):** bloqueio com a mensagem de duplicidade existente; 0 colisões hoje; exceção (sufixo manual) registrada como dívida para feature própria |
| Name > 100 chars em nomes futuros longos | Baixo | Validação servidor + limite 50 chars observado nos dados |
| Quebra de importação/inventário por mudança de identificador | Alto se ocorresse | **Não ocorre**: padrão dos nomes novos = padrão existente (37/37); contratos de API/CSV intocados; regressão em `test_import_asset_*` |
| Dependência de JavaScript | Baixo | Servidor recompose o nome (FR-003) — sem script não há registro errado |
| Regressão de telas que exibem `loc.name` | Baixo | Mesmo formato de antes; suítes 062/063/064 na régua final |
| Violação de escopo/refatoração incidente | Médio | Tabela §11 é fechada; diff final limitada a esses arquivos |

## 14. Pendências que exigem decisão ou aprovação

- **P1 — Abrangência da validação no servidor**: ~~**Confirmar**~~ → **APROVADA (2026-10-09): validação vale apenas no fluxo web (`/locations/new`)**, preservando API REST e importação CSV (contratos). *Alternativa de impor em `LocationService.create` permanece descartada por quebrar API, seed, CLI e testes (§9-B).*
- **P2 — Perda da digitação livre do nome**: ~~**Confirmar aceitação**~~ → **APROVADA (2026-10-09): campo `readonly` confirmado** — o usuário não digita o nome; detalhes adicionais (ex.: sufixo de sala) ficam nos campos próprios (Prédio/Andar/Sala/Descrição). AC04 mantido integralmente.
- **P3 — Colisão branch+departamento no futuro**: ~~**Registrar**~~ → **RESOLVIDA (2026-10-09, opção A)**: segundo cadastro com o mesmo par é **bloqueado** com a mensagem de duplicidade existente; sem sufixo manual nesta feature. Tratamento de exceção (ex.: sufixo) fica para feature própria, registrada como dívida.
- **P4 — Placeholders e ajuda**: ~~**Confirmar**~~ → **RESOLVIDA (2026-10-09, opção A)**: atualizar placeholder do campo (em T005), artigo `cadastrar-locais` da central de ajuda (tarefa nova no Polish) e `docs/ARQUITETURA_E_MANUTENCAO.md` (T013) — tudo na mesma tarefa.

**Limitações desta execução**: somente leitura — nenhum arquivo de produção foi modificado, nenhuma migração ou escrita foi executada no banco; consultas ao MariaDB real foram apenas `SELECT`/agregações (§1.4). A implementação não começa sem aprovação explícita (Restrição 12 do briefing).

---

**Próximo passo** (após aprovação): `/speckit-plan` → `/speckit-tasks` → implementação dentro do escopo §11.
