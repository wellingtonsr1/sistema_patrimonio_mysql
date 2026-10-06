# Feature Specification: Seleção de Destino por Departamento/Setor na Movimentação (apresentação Departamento-primeiro)

**Feature Branch**: `062-selecao-departamento-destino`

**Created**: 2026-10-06

**Status**: Draft

**Input**: Apresentar o Departamento/Setor como identificação principal do destino de movimentação patrimonial — e do select de Localização do equipamento — mantendo a Unidade Administrativa como contexto, com agrupamento por unidade. Mudança de APRESENTAÇÃO (somente templates): o identificador enviado continua sendo o id da Localização, zero alteração de banco/backend, com teste de não-mutação dos snapshots do histórico. Escopo mínimo da §10 da análise `docs/ANALISE_DEPARTAMENTO_DESTINO_MOVIMENTACAO_2026-10-06.md`.

---

## 1. Contexto e análise do sistema atual (somente leitura, verificada nesta especificação)

| # | Ponto investigado | Realidade verificada |
|---|---|---|
| 1 | Campo "Novo Local / Departamento" | Única ocorrência: `app/web/templates/movements/new.html` L102–106 (`<select name="destination_location_id">`) |
| 2 | Texto atual da opção | `{{ loc.name }} ({{ loc.branch }} - {{ loc.department }})` — ex.: `Sede - Divisão de Previdência (IPMJP - Sede - Divisão de Previdência)` |
| 3 | Identificador realmente enviado | `loc.id` (PK de `locations`) — nenhum texto de departamento é enviado ao backend |
| 4 | Fonte da lista | `form_new_movement` (`app/web/routers/movements.py` ~L65–95) via `LocationService.get_all(db)`, ordenada por `branch, department, name` (`location_service.py` L22) |
| 5 | O que grava o destino | `MovementService.create_movement`: `destination_location_id` (FK) + snapshot `destination_location_name = f"{branch} - {department} ({name})"` (`movement_service.py` L136/L148) |
| 6 | Histórico | snapshots imutáveis; leitores: `movements/list.html` L129/133, `assets/detail.html` L258/266, `dashboard.html` L287, `reports/movements_report.html` L92/96, busca 049 (`movement_service.py` L513+), termo (`get_term_details` usa o snapshot do local) |
| 7 | Formato do snapshot já travado por teste | `tests/test_import_asset_movements.py` L134: `destination_location_name == "Matriz - TI (Sala de TI)"` (formato `Unidade - Departamento (Nome)`) |
| 8 | Mesmo padrão de select no form de equipamento | `app/web/templates/assets/form.html` L109–111 (select de Localização do bem, opção vazia `-- Estoque Central / Almoxarifado --`); fonte idêntica `LocationService.get_all(db)` (`form_new_asset`, `routers/assets.py` L391+) |
| 9 | Departamento no cadastro | `Location.department` (`String(100)`, NOT NULL, texto livre) — sem entidade de departamentos; é a fonte oficial da lista de Departamento/Setor dos colaboradores (Feature 012, `DepartmentService`) |
| 10 | Dados de produção (SELECT read-only, 2026-10-06) | 36 localizações; cada `department` em exatamente 1 local (equivalência 1:1 **por acidente de dados** — sem constraint de unicidade); 35 com branch `IPMJP - Sede` + `Clube` + `Shoping` |
| 11 | Testes existentes | NENHUM teste trava o TEXTO atual da opção; os testes de movimentação enviam `destination_location_id` (`test_movements.py`) e travam o FORMATO do snapshot (item 7) |
| 12 | Ajuda central | o artigo "movimentar-equipamento" não menciona o rótulo nem o formato das opções (sem ocorrência de "Novo Local" em `help_service.py` — nenhuma atualização obrigatória de ajuda) |

**Consequências da análise** (refletidas nos requisitos):

- O destino de uma movimentação **nunca foi gravado como texto**: o formulário envia o id da Localização e o texto composto é apenas o rótulo da opção, montado no template. Mudar o rótulo **não altera** o que é gravado.
- Portanto a proposta é realizável como **alteração de apresentação**: templates + testes, **zero DDL, zero backend, zero migração** (Princípio I da Constitution — evolução incremental mínima).
- O histórico é protegido por **snapshots imutáveis** (Princípio IV da Constitution). A guarda desta feature é **não introduzir novo formato de snapshot** e comprovar por teste que o formato gravado permanece idêntico ao atual (item 7).
- Os typos e divergências de dados (`Acessoria`, `Assist}ência Social`, branch `IPMJP – Sede` com travessão, drift de `custodians.department`) estão registrados na análise (§12) como **higiene de dados fora do escopo** — feature própria.

## Clarifications

### Session 2026-10-06

- Q1: Incluir também o select de Localização do formulário de Equipamentos (`assets/form.html`) nesta feature? → **A: Sim — como User Story P2** (mesma apresentação, testável independentemente da história da movimentação).
- Q2: Agrupar as opções por Unidade Administrativa (optgroup)? → **A: Sim — optgroups por unidade** (ex.: grupo `IPMJP - Sede` com seus ~34 setores, grupos `Clube` e `Shoping`), imitando o raciocínio unidade → setor.
- Q3: Qual deve ser o texto da opção de destino? → **A: "Departamento (Unidade)"** — ex.: `Divisão de Previdência (IPMJP - Sede)`. O nome do local sai do texto da opção (continua no banco, único, e visível nas demais telas). Com optgroups, a unidade aparece no cabeçalho do grupo **e** no contexto da opção — **deliberado**: a opção permanece autocontida (rótulo completo mesmo se exibida fora do grupo).

---

## 2. User Scenarios & Testing

### User Story 1 - Escolher o destino da movimentação pelo Departamento/Setor (Priority: P1) 🎯 MVP

Um operador com permissão de movimentação abre o formulário "Registrar Fluxo de Movimentação" e, no campo de destino, vê as opções **organizadas por Unidade Administrativa** (ex.: `IPMJP - Sede`, `Clube`, `Shoping`) e, dentro de cada grupo, as opções identificadas **primeiro pelo Departamento/Setor** com a unidade como contexto — ex.: `Divisão de Previdência (IPMJP - Sede)`. O operador localiza o setor de destino lendo o começo da opção, seleciona e conclui a movimentação normalmente; o comportamento de gravação é exatamente o atual.

**Why this priority**: É o núcleo do pedido — o operador pensa "para qual setor vou entregar?" e a lista agora começa pelo setor. Responde diretamente à dor registrada na análise de 2026-10-06 (rótulo verboso e redundante).

**Independent Test**: Renderizar o formulário de movimentação com locais de duas unidades → cada unidade aparece como grupo e cada opção começa pelo departamento; submeter uma transferência escolhendo uma opção → grava exatamente como hoje (id + snapshot no formato atual).

**Acceptance Scenarios**:

1. **Given** o formulário de movimentação com localizações de mais de uma unidade, **When** o operador abre o campo "Novo Local / Departamento", **Then** as opções estão agrupadas por Unidade Administrativa (cabeçalho do grupo = unidade).
2. **Given** o mesmo campo, **When** o operador lê uma opção, **Then** o texto começa pelo Departamento/Setor e traz a unidade como contexto — ex.: `Divisão de Previdência (IPMJP - Sede)` — e não mais `Sede - Divisão de Previdência (IPMJP - Sede - Divisão de Previdência)`.
3. **Given** o campo vazio, **When** o operador não seleciona local, **Then** a opção vazia `-- Manter Local Atual --` permanece como primeira opção (comportamento atual preservado).
4. **Given** uma transferência concluída escolhendo uma opção da nova lista, **When** o sistema grava a movimentação, **Then** o destino é registrado com o mesmo identificador e o mesmo formato de snapshot de hoje (nenhuma mudança de gravação).
5. **Given** localizações com o mesmo Departamento/Setor em unidades diferentes (cenário futuro — hoje não ocorre nos dados), **When** o operador lê as opções, **Then** cada opção continua distinguível pela unidade no contexto.

### User Story 2 - Mesma apresentação no cadastro de Equipamento (Priority: P2)

Um operador com permissão de cadastro de patrimônio abre o formulário de Equipamento e, no select de Localização, encontra as opções com a mesma apresentação da movimentação: agrupadas por unidade, texto iniciando pelo Departamento/Setor com a unidade como contexto, mantida o valor vazio atual (`-- Estoque Central / Almoxarifado --`, que representa bem sem local).

**Why this priority**: Consistência entre os dois selects de localização do sistema (mesma fonte, mesmo padrão de opção hoje); sem ela, o operador vê dois formatos diferentes para a mesma escolha.

**Independent Test**: Renderizar o formulário de equipamento → mesmas regras de grupo e rótulo da US1, com a opção vazia preservada.

**Acceptance Scenarios**:

1. **Given** o formulário de Equipamento, **When** o operador abre o select de Localização, **Then** as opções estão agrupadas por unidade e começam pelo Departamento/Setor com a unidade como contexto.
2. **Given** o mesmo select, **When** o operador não seleciona local, **Then** a opção vazia atual (`-- Estoque Central / Almoxarifado --`) permanece como primeira opção.
3. **Given** um equipamento salvo com uma localização escolhida na nova apresentação, **When** o cadastro é gravado, **Then** o bem fica vinculado à Localização escolhida exatamente como hoje (nenhuma mudança de gravação).

### User Story 3 - Integridade do histórico e não-mutação da gravação (Priority: P1)

Qualquer usuário do sistema — inclusive auditoria — continua vendo o histórico de movimentações exatamente como hoje: registros antigos mantêm seus textos de origem/destino originais, a busca de movimentações continua encontrando pelos mesmos termos, e movimentações novas gravam o destino no formato atual. A mudança de apresentação **não altera nenhum dado gravado**, passado ou futuro.

**Why this priority**: É a guarda da feature (Princípio IV da Constitution — trilha imutável) e condição para a US1 ser segura; sem esse teste de não-mutação, a mudança de rótulo não pode ser aprovada.

**Independent Test**: Gravar uma movimentação após a mudança e comparar, campo a campo, com o formato gravado antes: identificador, snapshot de destino e exibição no histórico/termo/relatório idênticos ao comportamento atual; registros anteriores intocados.

**Acceptance Scenarios**:

1. **Given** movimentações já existentes no sistema, **When** qualquer tela de histórico, termo, relatório, dashboard ou busca é exibida, **Then** os textos de origem/destino exibidos são exatamente os mesmos de antes da feature (snapshots não são regravados nem reformatados).
2. **Given** uma movimentação nova registrada após a feature, **When** seu destino é gravado, **Then** o formato do snapshot gravado é idêntico ao formato atual (mesmo padrão já travado pelos testes existentes de movimentação/importação).
3. **Given** a busca de movimentações, **When** o usuário pesquisa por um termo que casava antes (departamento, unidade, nome do local dentro do snapshot), **Then** o mesmo registro continua sendo encontrado.

### Edge Cases

- **Departamento homônimo em unidades diferentes (futuro)**: hoje os dados têm equivalência 1:1 por acidente (sem constraint de unicidade); se vier a ocorrer, a opção permanece distinguível pela unidade no contexto (deliberado na clarificação Q3 — rótulo autocontido).
- **Nome da unidade com caracteres especiais** (ex.: travessão em `IPMJP – Sede` vs hífen): a apresentação não interpreta nem normaliza o valor — exibe o texto do cadastro como está (higiene de dados é feature própria).
- **Departamento vazio ou só espaços**: impossível nos dados atuais (`department` é NOT NULL e o formulário de local exige preenchimento); a apresentação não cria regra nova — exibe o que existe.
- **Lista vazia (nenhuma localização)**: o campo exibe apenas a opção vazia atual, sem grupos — comportamento atual preservado.
- **Uma única unidade**: um único grupo com cabeçalho da unidade; nada muda na usabilidade.
- **Value do option**: permanece o identificador numérico da Localização em TODOS os casos; nenhum teste ou integração que envie o identificador é afetado.

## 3. Requirements

### Functional Requirements

- **FR-001**: O campo de destino da movimentação "Novo Local / Departamento" DEVE apresentar as opções agrupadas por **Unidade Administrativa**, com o cabeçalho de cada grupo sendo o valor da unidade da localização (Princípio X da Constitution — interface consistente).
- **FR-002**: O texto de cada opção DEVE iniciar pelo **Departamento/Setor** e apresentar a Unidade Administrativa como contexto, no formato `Departamento (Unidade)` — ex.: `Divisão de Previdência (IPMJP - Sede)` — eliminando a redundância atual em que o departamento e a unidade aparecem duas vezes no mesmo rótulo.
- **FR-003**: O identificador enviado pelo formulário DEVE permanecer o **id da Localização** em todos os casos; NENHUM texto de departamento é enviado, gravado ou interpretado pelo backend (nenhuma mudança de contrato).
- **FR-004**: A opção vazia atual `-- Manter Local Atual --` DEVE permanecer como primeira opção do campo de destino (comportamento preservado).
- **FR-005**: O select de Localização do formulário de Equipamento DEVE adotar a mesma apresentação (agrupamento por unidade + rótulo `Departamento (Unidade)`), preservando sua opção vazia atual (`-- Estoque Central / Almoxarifado --`) e o identificador enviado.
- **FR-006**: O sistema NÃO DEVE alterar o formato dos snapshots de local gravados nas movimentações — origem e destino continuam gravados no formato atual (`Unidade - Departamento (Nome)`), já travado pelos testes existentes (US3).
- **FR-007**: O sistema NÃO DEVE regravar, reescrever ou reformatar snapshots de movimentações já existentes; histórico, termo, relatórios, dashboard e busca exibem os textos originais (Princípio IV da Constitution).
- **FR-008**: A lista de opções DEVE continuar provinda do cadastro de Localizações (fonte única), na mesma ordenação atual por unidade → departamento → nome — nada de lista fixa no HTML.
- **FR-009**: O sistema NÃO DEVE alterar banco de dados (zero DDL), rotas, permissões (`movimentacao.criar`, `patrimonio.criar`), schemas, services, API REST, termo, relatórios ou integrações (1Doc, AD, SMTP) como consequência desta feature.
- **FR-010**: Toda alteração desta feature DEVE vir acompanhada de testes nos padrões existentes, incluindo o teste de não-mutação da gravação (US3) e a suíte completa verde (Princípio VIII).
- **FR-011**: A apresentação DEVE preservar a acessibilidade/semântica atual dos selects (a unidade presente tanto no cabeçalho do grupo quanto no contexto da opção é decisão deliberada — ver Clarifications Q3).

### Regras (síntese operacional)

- R1 — Somente apresentação: mudam os rótulos das opções e o agrupamento; NADA muda em values, nomes de campos, contratos, banco e histórico (FR-003/FR-006/FR-007/FR-009).
- R2 — Fonte única: lista derivada ao vivo do cadastro de Localizações, ordenação atual preservada (FR-008).
- R3 — Rótulo único e autocontido: `Departamento (Unidade)` dentro do grupo da unidade (FR-002; Q3).
- R4 — Não-mutação comprovada: teste específico prova que gravação, snapshots, histórico e busca permanecem idênticos (US3; FR-006/FR-007).

### Key Entities

- **`Location` (existente, estruturalmente intocada)**: fonte das opções — `branch` (Unidade Administrativa) dá o grupo; `department` (Departamento/Setor) dá o início do rótulo; `name` permanece no banco e nas demais telas.
- **`Movement` (existente, intocada)**: destino continua referenciado por `destination_location_id` (FK) + snapshot de texto imutável no formato atual.
- **`Asset` (existente, intocado)**: `location_id` continua sendo o vínculo de localização do bem.

## 4. Success Criteria

### Measurable Outcomes

- **SC-001**: 100% das opções dos dois selects afetados iniciam pelo Departamento/Setor, com a unidade como contexto no próprio rótulo (verificável por inspeção da página renderizada e por teste).
- **SC-002**: 100% das opções estão dentro do grupo da sua unidade; nenhuma opção fora de grupo (exceto a opção vazia pré-existente de cada select).
- **SC-003**: Zero alteração no comportamento de gravação: identificador enviado, snapshot gravado, histórico, termo, relatórios, dashboard e busca produzem resultados idênticos aos atuais (comprovado pelo teste de não-mutação).
- **SC-004**: Zero mudança de permissões, rotas, banco e integrações; suíte completa verde no patamar atual (923 passed / 1 skipped / 0 failed).
- **SC-005**: Operador identifica o setor de destino lendo o início da opção — validação com o usuário em smoke visual (print antes/depois do formulário).

## 5. Assumptions e Premissas

- A ordenação atual da fonte (`unidade → departamento → nome`) permanece adequada para os optgroups (dentro de cada grupo as opções ficam ordenadas por departamento — o agrupamento já nasce naturalmente da fonte).
- O agrupamento por unidade não altera a contagem nem a disponibilidade de opções — apenas sua organização visual.
- A `location` do bem e o destino da movimentação continuam sendo conceitos vinculados à Localização (id), não ao departamento — nada nesta feature cria novo vínculo patrimonial por departamento.
- Higiene de dados (typos de `locations.department`/`branch`, drift de `custodians.department`) é feature própria, registrada na análise de 2026-10-06 §12 — fora do escopo.
- Se no futuro a instituição criar departamentos multi-unidade, esta apresentação continua válida (contexto da unidade no rótulo); a evolução estrutural (entidade de departamentos) é a Alternativa C da análise, não recomendada para agora.

## 6. Impacto esperado (componentes confirmados pela análise — nada inventado)

| Componente | Alteração esperada |
|---|---|
| `app/web/templates/movements/new.html` (L102–106) | **SIM** — agrupar por unidade (optgroup) e rótulo `Departamento (Unidade)`; value inalterado |
| `app/web/templates/assets/form.html` (L109–111) | **SIM** — mesma apresentação no select de Localização do bem; option vazia preservada |
| Backend (routers, services, schemas) | **NENHUM** — a fonte já entrega a lista ordenada por unidade → departamento → nome |
| Banco / migrations | **NENHUM** (zero DDL) |
| Histórico / termo / relatórios / dashboard / busca | **NENHUM** (snapshots imutáveis, formato preservado — FR-006/FR-007) |
| API REST / integrações (1Doc, AD, SMTP) / permissões | **NENHUM** |
| Testes | **NOVOS** — renderização dos dois forms (grupos + rótulos + values) e não-mutação da gravação; suíte existente intacta |
| Documentação | **NÃO REQUERIDA** — nenhum artigo da ajuda central menciona o formato atual das opções (verificado); comportamento de gravação não muda |

## 7. Critérios de Aceitação (rastreabilidade)

| AC | Enunciado | Coberto por |
|---|---|---|
| AC-01 | Opções do destino da movimentação agrupadas por unidade | US1/AS1; FR-001 |
| AC-02 | Rótulo `Departamento (Unidade)` no destino da movimentação | US1/AS2; FR-002 |
| AC-03 | `-- Manter Local Atual --` preservada como primeira opção | US1/AS3; FR-004 |
| AC-04 | Gravação idêntica à atual (id + formato de snapshot) | US1/AS4, US3/AS2; FR-003/FR-006 |
| AC-05 | Histórico/termo/relatórios/busca exibem textos originais | US3/AS1, AS3; FR-007 |
| AC-06 | Mesma apresentação no form de Equipamento, com opção vazia preservada | US2/AS1, AS2; FR-005 |
| AC-07 | Zero DDL, zero mudança de rota/permissão/API | FR-009 |
| AC-08 | Suíte verde + testes novos da feature | FR-010 |

## 8. Escopo

### Incluído

- Apresentação do select de destino na **movimentação** (grupos por unidade + rótulo `Departamento (Unidade)`);
- Mesma apresentação no select de Localização do **equipamento**;
- Preservação explícita das opções vazias atuais de cada select;
- Testes de renderização e de não-mutação da gravação.

### Não incluído (limites de escopo)

- Qualquer alteração de banco, backend, API, permissões, migração ou integrações (FR-009);
- Alteração do formato dos snapshots de movimentação (presente ou passado) (FR-006/FR-007);
- Higiene/normalização de dados (`Acessoria`, `Assist}ência`, travessão no branch, drift de colaboradores) — feature própria;
- Entidade de departamentos / FK de departamento (Alternativa C da análise) — não recomendada nesta etapa;
- Outros selects que exibem departamento (colaborador em `movements/new.html` L97 e `assets/form.html` L121) — permanecem como estão;
- Edição do rótulo do campo ("Novo Local / Departamento") — permanece como está.

> **Nota de escopo**: o valor enviado por cada opção continua sendo o id da Localização — inclusive os nomes dos campos (`destination_location_id` e `location_id`) permanecem inalterados.

*Esta especificação descreve SOMENTE o comportamento desejado e a análise verificada do código atual. Nada foi implementado, e nenhum model, tabela, rota, template, API ou teste foi alterado na elaboração deste documento. Detalhes de implementação ficam para o `/speckit-plan`.*
