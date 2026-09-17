# Feature Specification: Seleção de Departamento/Setor no Cadastro de Colaborador

**Feature Branch**: `012-selecao-departamento-colaborador`

**Created**: 2026-09-17

**Status**: Draft

**Input**: Substituir o campo de texto livre "Departamento / Setor *" do cadastro e da edição de Colaborador por uma seleção de registros oficiais existentes no banco de dados (nunca lista fixa no HTML), padronizando as grafias, mantendo o campo obrigatório e a validação no backend, sem alterar Localização de patrimônio, Cargo/Função nem qualquer outro módulo.

---

## 1. Contexto e análise do sistema atual (somente leitura, verificada nesta especificação)

Fatos confirmados no código — nenhum nome abaixo é presumido:

| # | Ponto investigado | Realidade atual verificada |
|---|---|---|
| 1 | Modelo do Colaborador | `app/models/custodian.py`: classe `Custodian` (tabela `custodians`) |
| 2 | Campo Departamento/Setor | Coluna `department` (`String(100)`, `nullable=False`), comentada no código como "Setor" |
| 3 | É texto livre? | **Sim** — sem FK, sem enum, sem validação contra lista; aceita qualquer texto |
| 4 | Como o colaborador é criado | `CustodianService.create`; web `POST /custodians/new` (`department: str = Form(...)`) e API REST `POST /api/v1/custodians` (`CustodianCreate.department: str`); auditoria via `write_change_audit` |
| 5 | Como o colaborador é editado | `CustodianService.update`; web `POST /custodians/{id}/edit` (`department: str = Form(...)`) e API REST `PUT /api/v1/custodians/{id}`; auditoria before/after |
| 6 | Formulário de cadastro | `app/web/templates/custodians/form.html`: `<input type="text" name="department" required>` — obrigatoriedade **apenas no navegador** |
| 7 | Formulário de edição | O **mesmo** `form.html` (flag `is_edit`), mesmo campo texto pré-preenchido |
| 8 | Entidade de Departamento | **Não existe** — nenhuma tabela/modelo de departamentos em `app/models/` |
| 9 | Entidade de Setor | **Não existe** como entidade própria; baseline registra: "Setor não é entidade: é campo `department` em `Location` e `Custodian`" (`specs/001-sistema-existente/spec.md`, `data-model.md`, `SPEC-KIT-SISTEMA-ATUAL.md`) |
| 10 | Estrutura organizacional existente | Apenas `Location.department` (`app/models/location.py`) — departamento do **local físico do patrimônio**, também texto livre, sem cadastro próprio |
| 11 | Cadastro oficial de Departamentos/Setores | **Não existe** nenhum |
| 12 | Serviço para consultar registros | **Não existe** serviço dedicado; o mais próximo são consultas ad hoc `db.query(Location.department).distinct()` em `app/web/routes.py` (filtros de bens e de inventário) |
| 13 | Endpoint/API para listar | **Não existe** endpoint de departamentos; `GET /api/v1/locations` e `GET /api/v1/custodians` retornam `department` como atributo dos registros, não como lista |
| 14 | Componente de seleção reutilizável | **Não existe** — sem `datalist`/select2/tom-select; `static/js/main.js` contém só tooltips, alertas, tema e contadores. Precedente do projeto: selects server-rendered (`assets/form.html`, `assets/list.html`, `inventarios/new.html`) |
| 15 | Telas que exibem o department do colaborador | `custodians/list.html` (badge), `custodians/detail.html` (cabeçalho), `assets/form.html` e `movements/new.html` (texto da opção de seleção de custodiante), `movements/term.html` (tabela do termo), `reports/custodians_report.html` (coluna "Setor"); a pesquisa de colaboradores (feature 006) também casa o termo com o departamento |
| 16 | Relatórios que utilizam a informação | `ReportService.generate_custodians_csv` (coluna de department) e o relatório web "Relação de Colaboradores" (`/reports/custodians`). O dashboard usa `Location.department` (localização — **não** do colaborador) |
| 17 | Testes existentes de Colaborador | `tests/test_custodian_provisional.py`, `test_custodians_search.py`, `test_custodian_import.py`, `test_api.py`, `test_rbac.py`, `test_ad.py` — todos exercitam `department` como texto livre ("TI", "D", "RH", "Comercial"…) |

**Consequências da análise** (refletidas nos requisitos):

- **Não existe hoje uma fonte oficial de Departamentos/Setores no banco.** A existência dessa fonte é **pré-condição** do comportamento desejado e a forma de provê-la (reutilizar estrutura existente, novo cadastro, carga de dados oficiais) é decisão do planejamento (`/speckit-plan`) — **nada é criado por esta especificação** (necessidade apenas documentada, conforme briefing).
- `Location.department` representa o departamento do **local físico do bem** (escopo de inventário, filtros de bens, dashboard) e é texto livre — reutilizá-la como fonte acopla o departamento funcional do colaborador ao domínio de localização física (colaborador sem local e local sem colaborador são situações válidas). **Decisão do `/speckit-plan` (research R1 revisada): a fonte oficial oficialmente adotada É o conjunto de valores distintos de `Location.department`, usado apenas em leitura (lista derivada ao vivo)** — consequências do acoplamento aceitas e documentadas em `research.md`; `Location` permanece estruturalmente intocada (FR-009/AC-09).
- A trilha patrimonial **não registra** o department do colaborador: `Movement` guarda snapshots textuais de **nome** (imutáveis — Princípio IV da Constitution) e FK por `id`; o termo lê `custodian.department` **vivo** no momento da emissão; o inventário guarda apenas `expected_custodian_name`. Alterar o departamento hoje **já não reescreve** nenhum registro histórico.
- O AD **apenas vincula** usuários a colaboradores existentes (`find_linked_custodian` por e-mail/matrícula) — nunca cria nem altera department.
- A **importação CSV de colaboradores** (`custodian_import_service.py`) também grava `department` como texto obrigatório (e atualiza em massa) — caminho de escrita **distinto e fora do escopo** desta feature (mantém-se como está; a potencial divergência de padronização fica registrada para o backlog).

---

## Clarifications

### Session 2026-09-17

- Q: Qual deve ser a fonte oficial dos registros de Departamento/Setores que alimentará a seleção no cadastro de colaborador? → A: C — Delegar ao `/speckit-plan`: a decisão da fonte oficial (reutilizar estrutura existente ou criar cadastro próprio) permanece inteiramente no planejamento; a spec registra a necessidade documentada e o requisito de não-duplicação (FR-010).
- Q: Como os registros de Departamento/Setores já gravados com grafias divergentes (ex.: "Setor de Suporte", "setor de suporte", "SUPORTE") devem ser tratados pela feature? → A: A — Existentes ficam como estão: somente novos cadastros e edições passam a usar a seleção oficial; a normalização em lote/migração de valores antigos fica para feature futura própria.
- Q: Quando um Departamento/Setor da lista oficial for inativado (ou se tornar inutilizável) depois que colaboradores já o utilizam, o que deve acontecer com esses colaboradores e com novos cadastros? → A: A — Bloquear: o cadastro/edição do colaborador cujo departamento atual estiver inativo fica impedido até que um registro ativo seja selecionado (regra válida somente se a fonte oficial definida no plan possuir conceito de ativo/inativo); registros inativos nunca aparecem para novas seleções.
- Q: A que caminho se aplica a validação estrita do valor oficial, dado que o plan revisou a fonte para `Location.department` (sem identificador por registro)? → A: Ao caminho da seleção oficial — o **formulário** de criação/edição (marcador `department_source=official`); os demais caminhos existentes (API REST, importação CSV, chamadas diretas ao service) permanecem como estão hoje, preservados pelo FR-012, com normalização progressiva registrada como feature futura (decisão do plan revisado — research R6/R7).
- Q: Na edição, se o valor vigente do colaborador não consta na lista oficial, o usuário deve re-selecioná-lo? → A: Não — a submissão idêntica ao valor vigente é aceita sem re-normalização (FR-014); a validação do valor oficial aplica-se apenas quando um valor **diferente** é submetido (remediação /speckit-analyze — I2, opção b).

### Session 2026-09-17 (implementação)

- Q: Qual o tipo de controle do campo "Departamento / Setor"? → A: **Campo de seleção (dropdown/`<select>` nativo)** com a lista oficial, opção vazia "— Selecione —" e valor vigente pré-selecionado na edição. **Sem lógica de pesquisa** (sem datalist, sem digitação/filtro): o Cenário 4 do briefing ("pesquisar parte do nome") fica suplantado — a lista completa é apresentada no dropdown e a criação por digitação é estruturalmente impossível. Decisão do usuário durante a implementação; supersede a opção datalist de `research.md` R5.

---

## 2. Problema e objetivo

### Problema

O campo "Departamento / Setor *" aceita texto livre. Grafias diferentes para o mesmo setor conviveram no banco:

```text
Setor de Suporte
setor de suporte
Setor Suporte
SUPORTE
```

Isso fragmenta pesquisas (feature 006 casa o termo com o departamento), relatórios (Relação de Colaboradores, CSV) e qualquer agrupamento/comparação por setor, além de permitir erros de digitação silenciosos.

### Objetivo

No cadastro e na edição de Colaborador, o campo passa a ser uma **seleção de registros oficiais existentes no banco de dados**:

```text
Departamento / Setor *

[ — Selecione — ▼ ]
  IPMJP - DAF
  IPMJP - Setor de Suporte
  IPMJP - Setor de Atendimento
  IPMJP - Seção de Folha de Benefícios
  ...
```

O colaborador passa a apontar para o registro oficial — a padronização vem dos dados, não de lista fixa escrita no HTML.

---

## 3. Princípio fundamental — não confundir com Localização

**Departamento/Setor do Colaborador ≠ Localização física do patrimônio.**

- `Location.department` descreve o local do **bem** (movimentações, inventário, filtros de acervo, dashboard) e **não é alterado** por esta feature — embora, pelo plan revisado, seus valores distintos componham a lista oficial da seleção (derivação somente-leitura; o Departamento/Setor do Colaborador permanece um conceito distinto do local físico do bem).
- Nenhuma regra patrimonial (movimentações, inventário, termos, auditoria, RBAC) é tocada.
- O campo **Cargo / Função** (`role`) permanece texto livre — fora do escopo.

---

## 4. User Scenarios & Testing

### User Story 1 - Cadastrar colaborador selecionando um Departamento/Setor oficial (Priority: P1) 🎯 MVP

Um usuário com permissão de cadastro de colaboradores abre o formulário "Cadastrar Colaborador" e, no campo "Departamento / Setor *", seleciona um registro existente na lista oficial (**campo de seleção/dropdown**). O cadastro só é concluído com uma seleção válida, e o colaborador fica associado ao registro escolhido — nunca a um texto digitado livremente.

**Why this priority**: É o núcleo da padronização: sem seleção obrigatória da fonte oficial, o problema das grafias divergentes continua.

**Independent Test**: Abrir o cadastro, selecionar um Departamento/Setor da lista oficial e salvar → o colaborador é criado com exatamente o registro oficial associado; tentar salvar sem seleção → rejeitado.

**Acceptance Scenarios**:

1. **Given** o formulário de cadastro, **When** o usuário seleciona um Departamento/Setor existente na lista oficial e salva, **Then** o cadastro é realizado e o colaborador fica associado ao registro oficial selecionado (Cenário 1 do briefing; AC-01, AC-05).
2. **Given** o campo de seleção, **When** o usuário tenta informar uma denominação nova digitando texto livre, **Then** não é possível: o campo não aceita valores que não correspondam a um registro existente (AC-02).
3. **Given** o formulário preenchido sem seleção de Departamento/Setor, **When** o usuário tenta salvar, **Then** o cadastro é rejeitado (Cenário 2 do briefing; AC-03).
4. **Given** o campo de seleção, **When** o usuário o abre, **Then** todos os registros oficiais vigentes são apresentados como opções (sem campo de pesquisa própria — decisão de UX 2026-09-17; Cenário 4 do briefing original, de pesquisa parcial, fica suplantado: a lista completa é visível no dropdown e nada é criado por digitação).
5. **Given** o formulário, **When** o usuário abre o campo, **Then** a lista apresentada provém dos dados oficiais do banco (nenhuma lista fixa escrita diretamente no HTML).

### User Story 2 - Validação no backend (Priority: P1)

O servidor valida toda seleção recebida **no caminho da seleção oficial (formulário de criação e edição)**: valor oficial (correspondente à lista) é aceito e gravado na forma canônica; valor fora da lista/inexistente é rejeitado, com mensagem coerente com os padrões atuais do sistema. A obrigatoriedade também é garantida no servidor, não apenas no navegador. Os demais caminhos existentes são preservados pelo FR-012 (ver Clarificações).

**Why this priority**: Sem validação no servidor, o padrão é contornável e a padronização não é garantia real.

**Independent Test**: Enviar diretamente ao backend (caminho do formulário) uma criação/edição de colaborador com valor oficial fora da lista ou vazio → operação rejeitada; com valor oficial presente na lista → aceita.

**Acceptance Scenarios**:

1. **Given** uma requisição de criação (caminho do formulário) com valor de Departamento/Setor **fora da lista oficial**, **When** processada pelo backend, **Then** a operação é rejeitada (Cenário 3 do briefing; AC-04).
2. **Given** uma requisição com valor que não corresponde a nenhum oficial (incluída a ambiguidade — dois oficiais diferindo só por caixa), **When** processada, **Then** a operação é rejeitada (AC-04).
3. **Given** uma requisição sem Departamento/Setor (vazio), **When** processada pelo servidor, **Then** é rejeitada — a obrigatoriedade não depende do navegador (AC-03).
4. **Given** uma requisição válida com identificador existente, **When** processada, **Then** o Departamento/Setor é corretamente associado ao colaborador (AC-05).

### User Story 3 - Editar colaborador usando a mesma lista oficial (Priority: P2)

No formulário de edição, o campo "Departamento / Setor" mostra o setor atual e permite selecionar outro registro válido da mesma fonte oficial usada no cadastro. A alteração nunca cria denominação nova.

**Why this priority**: Fecha o ciclo cadastral; depende da fonte oficial (US1), mas a jornada de edição é verificável por si só.

**Independent Test**: Editar um colaborador existente, trocar o Departamento/Setor por outro registro oficial e salvar → o novo registro é associado; nenhum texto arbitrário é criado.

**Acceptance Scenarios**:

1. **Given** um colaborador existente, **When** o usuário edita e seleciona outro Departamento/Setor da lista oficial, **Then** o novo registro válido é associado (Cenário 5 do briefing; AC-06).
2. **Given** o formulário de edição, **When** aberto, **Then** apresenta o setor atual pré-selecionado e a mesma lista oficial do cadastro (AC-06).
3. **Given** a edição, **When** o usuário tenta salvar com valor inválido ou vazio, **Then** aplica-se a mesma validação do cadastro (US2).

### User Story 4 - Compatibilidade com matrícula provisória e integridade do histórico (Priority: P2)

Colaboradores com matrícula provisória `PROV-*` (feature 010) utilizam o campo normalmente, sem qualquer restrição adicional. Alterar o Departamento/Setor de um colaborador não altera retroativamente movimentações, termos, inventários, auditoria ou registros históricos. A Localização de patrimônio permanece intocada.

**Why this priority**: Garante não-regressão e coexistência com a feature 010; verificável de forma independente das USs 1–3.

**Independent Test**: Cadastrar colaborador com matrícula `PROV-*` e um Departamento/Setor oficial → cadastro permitido normalmente; em seguida alterar o Departamento/Setor desse colaborador (com movimentações anteriores) → histórico e snapshots permanecem exatamente como estavam.

**Acceptance Scenarios**:

1. **Given** o cadastro com matrícula `PROV-000001` (ou qualquer `PROV-*`) e um Departamento/Setor existente selecionado, **When** salvo, **Then** o cadastro é permitido normalmente, sem bloqueio atribuível à matrícula provisória (Cenário 6 do briefing; AC-07).
2. **Given** um colaborador com movimentações/termos anteriores, **When** seu Departamento/Setor é alterado, **Then** movimentações, termos, inventários, auditoria e registros históricos permanecem exatamente como gravados (nenhuma reescrita retroativa) (AC-08).
3. **Given** qualquer operação desta feature, **When** executada, **Then** a Localização de patrimônio (`Location` e seu departamento), os bens, movimentações, inventário, termos, autenticação, AD, RBAC e permissões não apresentam alteração de comportamento (AC-09).

### Edge Cases

- **Volume de registros**: a quantidade atual de Departamentos/Setores não é determinável pelo código (são dados de produção); a interface deve comportar tanto poucos registros quanto muitos (dropdown nativo do navegador, conforme decisão de UX 2026-09-17 — sem campo de pesquisa próprio). Premissa registrada na Seção 12.
- **Fonte oficial inexistente no momento da implementação**: **RESOLVIDA pelo plan revisado** — valores distintos de `Location.department` (Seção 10).
- **Registro da lista removido/inativado depois de usado por colaboradores**: o registro não aparece para novas seleções; e, se a fonte oficial definida no plan possuir conceito de ativo/inativo, o **cadastro/edição do colaborador cujo departamento vigente estiver inativo fica bloqueado** (clarificação Sessão 2026-09-17) até que outro registro ativo seja selecionado — força correção imediata, sem excluir o colaborador nem reescrever histórico (o valor gravado permanece visível enquanto o bloqueio persiste, para orientar a correção).
- **Inativação**: **não existe** hoje conceito de ativo/inativo/arquivado para Departamentos/Setores (não há entidade). Esta feature **não cria** mecanismo de inativação; se a fonte definida no plan introduzir registros inutilizáveis, eles não devem ser apresentados para novos cadastros.
- **Importação CSV de colaboradores**: continua gravando `department` como texto, como hoje — fora do escopo (divergência registrada para o backlog, Seção 1).
- **Colaboradores já cadastrados com grafias divergentes**: permanecem inalterados (clarificação Sessão 2026-09-17 — FR-014); a padronização do acervo existente não ocorre nem gradualmente (a edição não obriga re-normalização além do uso da seleção oficial no novo valor) nem em lote. **Na edição, a submissão idêntica ao valor vigente (mesmo fora da lista) é aceita sem re-normalização**; a validação oficial aplica-se apenas a valor submetido **diferente** (remediação /speckit-analyze — I2).
- **API REST de colaboradores**: permanece como está hoje (texto obrigatório) — a validação da seleção oficial aplica-se somente ao caminho do formulário (FR-004; plan revisado, research R6/R7); o caminho da API é preservado pelo FR-012 e sua normalização é feature futura.
- **Termos já emitidos**: exibem o department vigente **no momento da emissão** (comportamento atual) — não são reemitidos nem reescritos.
- **Espaços/case no valor recebido**: correspondência case-insensitive/trim com a lista oficial, gravando-se a forma canônica oficial — a padronização elimina a comparação por texto livre.

---

## 5. Requirements

### Functional Requirements

- **FR-001**: O cadastro de colaborador DEVE apresentar o campo "Departamento / Setor" como **seleção de registros oficiais existentes no banco de dados**; a lista DEVE provir de dados (nunca de lista fixa escrita diretamente no HTML) (AC-01).
- **FR-002**: O usuário NÃO DEVE conseguir criar uma nova denominação no campo — o controle é um **campo de seleção (dropdown)** que só oferece registros existentes (a criação por digitação é estruturalmente impossível) (AC-02).
- **FR-003**: O campo DEVE continuar **obrigatório**, com a obrigatoriedade garantida **no backend** (e não somente no navegador) (AC-03).
- **FR-004**: O backend DEVE validar a seleção recebida **no caminho da seleção oficial (formulário de criação e edição)**: valor oficial (correspondência com a lista oficial, case-insensitive/trim, gravando-se a forma canônica oficial) → aceitar; valor fora da lista/inexistente → rejeitar (AC-04), reutilizando os serviços/regras existentes quando possível. Os demais caminhos de criação/edição existentes (API REST, importação CSV, chamadas diretas ao service) permanecem como estão hoje (FR-012), com normalização progressiva desses caminhos registrada como feature futura.
- **FR-015**: Quando a fonte oficial possuir conceito de ativo/inativo, um colaborador cujo Departamento/Setor vigente esteja inativo DEVE ter o cadastro/edição bloqueado (rejeitado no backend, com orientação de re-seleção) até que um registro ativo seja escolhido; o registro inativo NÃO DEVE aparecer nas listas de seleção (novos cadastros e edições de outros colaboradores).
- **FR-005**: O Departamento/Setor selecionado DEVE ser corretamente associado ao colaborador e persistido (AC-05).
- **FR-006**: A edição de colaborador DEVE utilizar a **mesma fonte oficial** do cadastro, com o setor atual pré-selecionado, permitindo trocar por outro registro válido sem criar texto arbitrário (AC-06).
- **FR-007**: Colaboradores com matrícula provisória `PROV-*` DEVEM utilizar o campo normalmente; NENHUMA restrição baseada em matrícula provisória ou oficial pode ser criada (AC-07).
- **FR-008**: A alteração do Departamento/Setor NÃO DEVE modificar retroativamente movimentações patrimoniais, termos, inventários, auditoria ou registros históricos (AC-08).
- **FR-009**: A solução NÃO DEVE alterar a Localização de patrimônio (`Location` e seu departamento) nem nenhum fluxo que a utilize (AC-09).
- **FR-010**: A solução NÃO DEVE introduzir estruturas duplicadas caso seja confirmada, no planejamento, uma estrutura adequada existente para Departamento/Setor (AC-10); a escolha da fonte oficial é pré-condição documentada na Seção 12 e decidida no `/speckit-plan`.
- **FR-011**: O campo **Cargo / Função** permanece texto livre e inalterado (fora do escopo).
- **FR-014**: Colaboradores JÁ CADASTRADOS mantêm seus valores atuais de `department` (mesmo com grafias divergentes): esta feature NÃO normaliza, corrige ou migra registros existentes — a padronização aplica-se exclusivamente a novos cadastros e a edições subsequentes; normalização do acervo existente é feature futura própria (fora do escopo da Seção 8).
- **FR-012**: Nenhum comportamento existente DEVE regredir: cadastro/edição por todos os caminhos atuais, pesquisa de colaboradores (006), matrícula provisória (010), importação CSV (texto, inalterada), vinculação AD (apenas vincula), auditoria e RBAC permanecem como estão.
- **FR-013**: Toda operação de criação/edição continua auditada pelo mecanismo existente (sem mudanças na trilha).

### Regras (síntese operacional)

- R1 — Obrigatório no servidor (R/FR-003).
- R2 — Somente registros existentes; sem criação por digitação; sem lista fixa no HTML (FR-001/FR-002).
- R3 — Validação de negócio concentrada em service (`DepartmentService.ensure_official`), consumida pelo caminho da seleção oficial (formulário); caminhos legados preservados (FR-004 + FR-012; Princípio III da Constitution).
- R4 — Sem restrição por tipo de matrícula (FR-007).
- R5 — Histórico intocável; snapshots imutáveis (FR-008; Princípio IV).
- R6 — Localização de patrimônio e Cargo/Função fora do escopo (FR-009/FR-011).

### Key Entities

- **`Custodian` (existente)**: o campo `department` (texto) passa a ser **preenchido apenas com o valor do registro oficial selecionado**. Esta especificação não define nem cria novas entidades, tabelas ou colunas — a representação estrutural do Departamento/Setor (inclusive a eventual relação entre colaborador e a fonte oficial) é decisão do `/speckit-plan` (confirmado na clarificação da Sessão 2026-09-17), a partir da necessidade documentada na Seção 1.
- **`Location` (existente, estruturalmente intocada)**: departamento do local físico do patrimônio; pelo plan revisado, seus valores distintos (somente-leitura) **são a fonte oficial** da seleção desta feature (FR-009/AC-09 preservados — nenhuma alteração estrutural nem de fluxos).
- **`Movement`, `InventarioItem`, termos, `audit_logs` (existentes, intocados)**: consumidores/histórico — permanecem imutáveis.

---

## 6. Critérios de Aceitação (rastreabilidade)

| AC | Enunciado | Coberto por |
|---|---|---|
| AC-01 | Cadastro apresenta Departamento/Setor como seleção de registros existentes | US1/AS1, AS5; FR-001 |
| AC-02 | Não é possível criar denominação digitando texto livre | US1/AS2; FR-002 |
| AC-03 | O campo continua obrigatório | US1/AS3, US2/AS3; FR-003 |
| AC-04 | O backend valida existência/validade da seleção (caminho da seleção oficial — formulário) | US2/AS1, AS2; FR-004 |
| AC-05 | O registro selecionado é corretamente associado ao colaborador | US1/AS1, US2/AS4; FR-005 |
| AC-06 | Edição usa a mesma lista oficial e permite trocar o registro | US3; FR-006 |
| AC-07 | Colaborador `PROV-*` utiliza o campo normalmente | US4/AS1; FR-007 |
| AC-08 | Alterar o Departamento/Setor não altera histórico retroativamente | US4/AS2; FR-008 |
| AC-09 | A solução não altera a Localização de patrimônio | US4/AS3; FR-009 |
| AC-10 | Não são introduzidas estruturas duplicadas se já existir estrutura adequada | FR-010 (decisão no plan a partir da Seção 1) |

### Cenários de validação do briefing (mapa)

| Cenário | Descrição | Esperado | Onde |
|---|---|---|---|
| 1 | Cadastro selecionando registro existente | Cadastro realizado corretamente | US1/AS1 |
| 2 | Salvar sem seleção | Cadastro rejeitado | US1/AS3 |
| 3 | Valor fora da lista oficial enviado direto ao backend (caminho do formulário) | Operação rejeitada | US2/AS1 |
| 4 | ~~Pesquisar parte do nome~~ (suplantado pela decisão de UX 2026-09-17 — dropdown sem pesquisa) | Lista completa apresentada no dropdown | US1/AS4 |
| 5 | Editar e trocar o Departamento/Setor | Novo registro válido associado | US3/AS1 |
| 6 | Cadastrar com matrícula `PROV-000001` + registro existente | Cadastro permitido normalmente | US4/AS1 |

---

## 7. Success Criteria

- **SC-001**: 100% dos novos cadastros de colaborador (via formulário) registram um Departamento/Setor da lista oficial — zero novas grafias livres.
- **SC-002**: 100% das tentativas de salvar sem seleção, com valor fora da lista oficial ou não utilizável são **rejeitadas no servidor** no caminho da seleção oficial — formulário (comprovado por testes diretos ao backend, sem depender do navegador).
- **SC-003**: Zero criação de denominação nova por digitação (o campo não produz valores fora da fonte oficial).
- **SC-004**: 100% das edições de Departamento/Setor utilizam a mesma fonte oficial do cadastro.
- **SC-005**: Zero alteração retroativa em movimentações, termos, inventários, auditoria e histórico após mudanças de Departamento/Setor (comprovado por testes de não-rewrita).
- **SC-006**: Zero mudança de comportamento em Localização de patrimônio, bens, movimentações, inventário, termos, autenticação, AD, RBAC e Cargo/Função.
- **SC-007**: A suíte existente permanece no patamar atual (nenhum teste regressa); novos testes cobrem os cenários desta spec seguindo os padrões existentes (`tests/test_*.py`).

---

## 8. Escopo

### Incluído

- Campo "Departamento / Setor" do **cadastro** de Colaborador como seleção de registros oficiais;
- Campo "Departamento / Setor" da **edição** de Colaborador com a mesma fonte oficial;
- Campo "Departamento / Setor" como **campo de seleção (dropdown)** da lista oficial (sem campo de pesquisa próprio — decisão de UX 2026-09-17);
- Obrigatoriedade e validação no backend para os caminhos de criação/edição de colaborador;
- Fornecimento da lista oficial à interface a partir do banco;
- Testes dos cenários desta spec.

### Não incluído (limites de escopo)

- **Localização de patrimônio** (`Location`, seu departamento, filtros de bens, escopo de inventário, dashboard);
- **Assets, Movimentações, Inventário, Termos** (estrutura e regras);
- **Autenticação, AD, RBAC, permissões, auditoria** (mecanismos existentes);
- **Campo Cargo / Função** (permanece texto livre);
- **Importação CSV de colaboradores** (mantém `department` textual — divergência registrada para o backlog);
- **Normalização/migração em lote dos valores já gravados** de colaboradores existentes (clarificação Sessão 2026-09-17 — FR-014: existentes ficam como estão; feature futura própria);
- **Criação automática** de tabela/modelo/entidade de Departamentos/Setores (**decisão do plan: zero DDL** — nenhuma estrutura criada nesta feature);
- **Mecanismo de inativação/arquivamento** de Departamentos/Setores (não existe hoje; não criado aqui) — mas o comportamento de bloqueio frente a registros inativados JÁ FICA DEFINIDO (clarificação Sessão 2026-09-17 — FR-015), aplicável assim que a fonte oficial do plan introduzir o conceito;
- **Histórico de alterações de Departamento/Setor do colaborador** (não existe mecanismo específico hoje — documentado na análise, sem criar mecanismo novo);
- Reescrita de qualquer registro histórico existente.

---

## 9. Casos de erro (comportamento definido)

| Situação | Comportamento |
|---|---|
| Salvar sem selecionar Departamento/Setor | Rejeitado no servidor (obrigatoriedade), com mensagem coerente com os padrões atuais |
| Edição enviando o valor vigente do colaborador (mesmo fora da lista) | Aceito sem re-normalização (FR-014 — remediação I2); validação oficial aplica-se só a valor diferente |
| Valor oficial fora da lista/inexistente enviado ao backend (caminho do formulário) | Operação rejeitada (criação e edição) |
| Valor sem correspondência com nenhum oficial (incl. ambiguidade de grafias) | Operação rejeitada (fonte oficial: valores distintos de `Location.department` — plan revisado) |
| Colaborador cujo departamento vigente está inativo (quando o conceito existir) | Cadastro/edição bloqueado no backend (FR-015) — re-seleção de registro ativo obrigatória; histórico e valor gravado não são alterados |
| Valor com espaços/variações de case | Correspondência case-insensitive/trim com o oficial; grava-se a **forma canônica oficial** (sem erro por caixa) |
| Colaborador `PROV-*` | Nenhuma restrição adicional (nenhum erro novo atribuível à matrícula) |
| Fonte oficial indisponível/vazia no momento do cadastro | Pré-condição da implementação — comportamento (bloquear cadastro vs. permitir) definido no plan junto com a fonte |

---

## 10. Premissas e dependências

- **Pré-condição crítica (dependência) — RESOLVIDA no plan revisado**: **não existia hoje fonte oficial de Departamentos/Setores no banco** (Seção 1, itens 8–13). O `/speckit-plan` definiu a fonte como **valores distintos de `Location.department`** (derivação somente-leitura ao vivo; zero DDL — research R1/R3 revisadas). Pré-condição operacional: pelo menos um local cadastrado para a lista ter opções (lista vazia → formulário exibe apenas a opção vazia e o salvamento é rejeitado como obrigatório, sem fallback para texto livre).
- **Volume de registros**: desconhecido pelo código (dados de produção); **decisão de UX 2026-09-17: campo de seleção (dropdown/select nativo) em qualquer volume, sem campo de pesquisa próprio** — evita complexidade desnecessária (Princípio X da Constitution).
- **Interface**: segue os padrões visuais/funcionais existentes (Bootstrap 5, selects server-rendered como precedente; sem introdução de biblioteca externa sem previsão no plan — Princípio X da Constitution).
- **Usuários-alvo**: operadores com as permissões existentes `colaboradores.criar` / `colaboradores.editar` — nenhuma permissão nova.

---

## 11. Impacto esperado (componentes confirmados pela análise — nada inventado)

| Componente | Alteração esperada (atualizada pelo plan revisado) |
|---|---|
| **Fonte oficial de Departamentos/Setores** | Valores distintos de `Location.department` (derivação somente-leitura — plan revisado, research R1; zero DDL) |
| `app/web/templates/custodians/form.html` | Substituir o input de texto do campo "Departamento / Setor" por seleção a partir da lista oficial (o mesmo template atende cadastro e edição) |
| `app/web/routes.py` (`form_new_custodian`/`form_edit_custodian`, `create_custodian_form`, `update_custodian_form`) | Fornecer a lista oficial ao template; validar o valor submetido via `DepartmentService.ensure_official` quando o marcador da seleção oficial estiver presente (validação em service — Princípio III); sem marcador, comportamento atual |
| `app/services/department_service.py` | **Novo service** (leitura da fonte oficial + validação/canonização do valor) |
| `app/services/custodian_service.py` | **Intocado** (o valor chega já validado/canônico pela rota) |
| `app/api/custodians_api.py` | **Intocado** (caminho legado preservado — FR-012; ver api-contract) |
| `tests/` (arquivo novo, padrão `test_custodian_*.py`/`test_department_selection.py`) | Cenários das US1–US4, AC-01..AC-10, casos de erro e não-regressão (suíte existente intacta — Princípio VIII) |

**Não alterar** (fora do impacto confirmado): `app/models/` (**zero DDL confirmado pelo plan**), `app/database.py`, `app/schemas/`, `app/api/` (caminho legado), `location_service.py`/`location_import_service.py`, `movement_service.py`, `inventario_service.py`, `ad_service.py`, `custodian_import_service.py` (escopo), relatórios (estrutura), autenticação/RBAC, `static/js/main.js` (a menos que o plan preveja componente de pesquisa — decisão de UX lá registrada).

> **Nota pós-plan (2026-09-17)**: a decisão da fonte oficial e do mecanismo de validação foi tomada em `plan.md`/`research.md` (REVISADO): reuso de `Location.department` com validação por texto no caminho do formulário — raio de alteração reduzido (sem DDL; `custodian_service.py` e API intocados). Esta Seção 11 foi atualizada para refletir o impacto real; o potencial original permanece registrado no histórico do documento. Remediações `/speckit-analyze` (I1, I2, I3) aplicadas nesta revisão.

---

*Esta especificação descreve SOMENTE o comportamento desejado e a análise do código atual. Nada foi implementado, e nenhum modelo, tabela, rota, template, API ou teste foi alterado na elaboração deste documento (conforme briefing). A fonte oficial e os detalhes de implementação foram decididos em `plan.md`/`research.md` (revisado) e as remediações do `/speckit-analyze` (I1, I2, I3) estão aplicadas nesta versão.*
