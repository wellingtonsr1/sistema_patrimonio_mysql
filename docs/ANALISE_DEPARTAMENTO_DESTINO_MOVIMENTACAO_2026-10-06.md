# ANÁLISE DE VIABILIDADE — USO DE DEPARTAMENTO COMO DESTINO DE MOVIMENTAÇÃO

**Data**: 2026-10-06
**Natureza**: SOMENTE ANÁLISE (read-only). Nenhum código, banco, template, rota, model, migration ou teste foi alterado para produzir este documento.
**Método**: leitura de models/services/routers/templates/schemas + da spec da Feature 012 + consultas SELECT somente-leitura no banco real (MariaDB) para o levantamento de dados (§9 do briefing).
**Gatilho**: avaliar se o destino da movimentação patrimonial deve passar a usar o **Departamento/Setor** (campo do cadastro de Localização) como identificação principal, mantendo Localização e Unidade Administrativa como contexto — em vez das opções compostas atuais tipo `Sede - Divisão de Previdência (IPMJP - Sede - Divisão de Previdência)`.

---

## 1. Resumo executivo

A mudança **é viável e é recomendável — mas como alteração de APRESENTAÇÃO, não de modelo**.

O ponto decisivo é que o destino de uma movimentação **nunca foi gravado como texto**: o formulário "Novo Local / Departamento" envia o **id da Localização** (`destination_location_id`), e o texto composto que aparece na tela é apenas o **rótulo da opção**, montado no template a partir de `Location.name`, `Location.branch` e `Location.department`. O histórico é preservado por **snapshots de texto imutáveis** gravados no momento da movimentação (`destination_location_name` etc.), verificados em produção: 118 movimentações, 0 snapshots sem coerência com o cadastro, 0 FKs órfãs.

Portanto, a proposta "Departamento/Setor como identificação principal do destino" **não exige alterar banco, nem migration, nem backend**: basta reordenar o **texto** das opções do `<select>` (departamento primeiro, local/unidade como contexto), mantendo o `value="{{ loc.id }}"`. O histórico não é tocado, porque os snapshots antigos continuam gravados como estão.

Sobre os dois "Departamentos": **não são a mesma entidade** — são duas colunas de texto livre independentes (`Custodian.department` e `Location.department`, sem FK entre si e sem tabela de departamentos). Porém, desde a Feature 012 o sistema **já ponteou os dois conceitos deliberadamente**: a lista oficial de Departamento/Setor do colaborador é **derivada ao vivo dos valores distintos de `locations.department`** (`DepartmentService`). Conclusão: **C — parcialmente relacionados**, com unificação de vocabulário em uma direção e divergências reais de dados comprovadas (4 valores de colaborador fora da lista oficial, além de typos no cadastro de locais).

Recomendação: **Alternativa B** (rótulo departamento-primeiro, somente template, valor continua sendo o id da Localização), **sem** normalizar agora em entidade própria (Alternativa C), **sem** mudar o formato dos snapshots. Os typos encontrados (`Acessoria`, `Assist}ência`, `Superitendência`, branch `IPMJP – Sede` com travessão) são **higiene de dados cadastral**, registrados como observação — fora do escopo desta análise e sem qualquer efeito retroativo sobre o histórico.

---

## 2. Como funciona atualmente (fluxo real, verificado no código)

### 2.1 O campo "Novo Local / Departamento"

Existe em **um único lugar**: `app/web/templates/movements/new.html` (L102–106):

```html
<label class="form-label">Novo Local / Departamento</label>
<select name="destination_location_id" class="form-select">
    <option value="">-- Manter Local Atual --</option>
    {% for loc in locations %}
    <option value="{{ loc.id }}">{{ loc.name }} ({{ loc.branch }} - {{ loc.department }})</option>
    {% endfor %}
</select>
```

- **Texto exibido**: `{{ loc.name }} ({{ loc.branch }} - {{ loc.department }})` — ex.: `Sede - Divisão de Previdência (IPMJP - Sede - Divisão de Previdência)`.
- **Identificador enviado ao backend**: `loc.id` (PK de `locations`). **Nenhum texto de departamento é enviado.**
- A lista vem do backend (`form_new_movement` em `app/web/routers/movements.py`, ~L65–95) via `LocationService.get_all(db)` — ordenada por `branch, department, name` (`app/services/location_service.py` L22).
- **Sem JavaScript** envolvido na montagem (a lógica JS do form é só do campo 1Doc, Feature 031).

O mesmo padrão de option (`name (branch - department)`, value = id) se repete no formulário de equipamento: `app/web/templates/assets/form.html` L111.

### 2.2 O que acontece ao gravar

`POST /movements/new` (`app/web/routers/movements.py` ~L100–160) recebe `destination_location_id: Optional[int]` → monta `MovementCreate` (`app/schemas/movement.py`) → `MovementService.create_movement` (`app/services/movement_service.py`):

1. **Snapshot da origem** (L136): `f"{asset.location.branch} - {asset.location.department} ({asset.location.name})"` → `origin_location_name`.
2. **Snapshot do destino** (L148): resolve a `Location` pelo id e grava `f"{new_location.branch} - {new_location.department} ({new_location.name})"` → `destination_location_name`.
3. **Matriz de Movimentação** (Feature 005, L167+): resolve destino efetivo, valida VAL-002/003/004/005 (transferência exige local; alocação exige colaborador; bloqueio de "nenhuma alteração efetiva").
4. Atualiza `asset.location_id` (e `custodian_id` conforme o tipo) e grava a `Movement` com **FK + snapshot** de origem e destino.

O mesmo formato composto de snapshot é usado na criação de bem (`app/services/asset_service.py` L167) e na importação CSV (`app/services/import_service.py` L482 e L629, com fallback literal `"Estoque Central"` quando não há local). Os **relatórios** usam variante mais curta `f"{branch} - {department}"` (`app/services/report_service.py` L111, L205, L335).

### 2.3 Onde o texto composto aparece / não aparece

| Tela | O que exibe | Fonte |
|---|---|---|
| Movimentação — nova | option `name (branch - department)` | template, ao vivo do cadastro |
| Movimentação — lista | origem/destino **snapshots** | `m.origin/destination_location_name` (movements/list.html L129/133) |
| Bem — detalhe (timeline) | **snapshots** por movimentação | assets/detail.html L258/266 |
| Bem — detalhe (localização ATUAL) | `branch • department` **ao vivo** | assets/detail.html L114 (segue FK) |
| Bem — lista | `a.location.name` **ao vivo** (ou "Estoque Central") | assets/list.html L226 (segue FK) |
| Dashboard — recentes | **snapshot** de destino | dashboard.html L287 |
| Dashboard — distribuição por departamento | `Location.department` **ao vivo**, agrupado | dashboard_service.py L38–44 |
| Relatório de movimentações | **snapshots** | reports/movements_report.html L92/96 |
| Termo (get_term_details) | local = **snapshot**; colaborador = **vivo** | movement_service.py L588–615 (L608 lê `custodian.department` atual) |
| Busca de movimentações (049) | casa **snapshots** com `ilike` | movement_service.py L513+ |
| Inventário — local esperado | `asset.location.name` (só nome) na **criação** do item | inventario_service.py L128 |

**Ponto-chave**: tudo que é **histórico** (lista de movimentações, timeline, termo, relatório, busca) lê **snapshot**; tudo que é **estado atual** (detalhe/lista do bem, filtros, dashboard, escopo de inventário) segue a **FK ao vivo**. Essa separação é exatamente o que protege o histórico (§8).

---

## 3. Modelo atual

### 3.1 Entidades e campos (verificados nos models)

```
Colaborador (Custodian, tabela custodians)
  └─ department : String(100), NOT NULL, TEXTO LIVRE  ← "Departamento" do colaborador
  └─ (sem FK para nenhuma entidade de departamento — ela não existe)

Localização (Location, tabela locations)
  └─ name      : String(100), UNIQUE  ← ex.: "Sede - Divisão de Previdência"
  └─ branch    : String(100)          ← Unidade Administrativa, ex.: "IPMJP - Sede"
  └─ department: String(100), NOT NULL, TEXTO LIVRE  ← "Departamento / Setor" da localização
  └─ building / floor / room / manager_name / description
  └─ (sem FK para nenhuma entidade de departamento — ela não existe)

Usuário (User, tabela users)
  └─ NÃO possui campo de departamento (qualquer relação é via vinculação AD a um Custodian)

Patrimônio (Asset, tabela assets)
  └─ location_id : FK → locations.id   ← localização FÍSICA atual
  └─ custodian_id: FK → custodians.id  ← responsável atual
  └─ (não existe coluna de departamento no Asset)

Movimentação (Movement, tabela movements) — "Gravação imutável" (docstring do model)
  └─ origin_location_id      : FK → locations.id      ┐
  └─ origin_location_name    : String(150) SNAPSHOT   │ origem
  └─ origin_custodian_id / origin_custodian_name       ┘
  └─ destination_location_id : FK → locations.id      ┐
  └─ destination_location_name : String(150) SNAPSHOT │ destino
  └─ destination_custodian_id / destination_custodian_name ┘
  └─ (NÃO existe snapshot de departamento — o department entra DENTRO do texto do snapshot de local)
```

### 3.2 Os dois "Departamentos" lado a lado

| | **Departamento do colaborador** | **Departamento / Setor da localização** |
|---|---|---|
| Coluna | `custodians.department` | `locations.department` |
| Armazenamento | texto livre `String(100)` | texto livre `String(100)` |
| Finalidade | setor onde a pessoa trabalha (exibição, busca de colaboradores, termo) | setor do local físico do bem (filtros, dashboard, inventário, rótulos) |
| Entidade própria | **Não existe** (confirmado na spec 012, §1 item 8–13) | **Não existe** |
| FK / relacionamento | nenhum | nenhum |
| Padronização | desde a Feature 012: seleção obrigatória de lista oficial no formulário web (marcador `department_source=official`) — lista **derivada ao vivo** de `locations.department` | criado/alterado pelo cadastro de Localização (e importação CSV de locais) — **fonte** da lista oficial |
| Caminhos sem padronização | API REST de colaboradores e importação CSV continuam texto livre (FR-012/FR-014 da 012) | — |
| Usos atuais | `custodians/list.html` (badge), `custodians/detail.html`, texto da option de colaborador em `movements/new.html` L97 e `assets/form.html` L121, **termo** (`get_term_details` lê vivo, L608; `term.html` L66), relatório de colaboradores (`reports/custodians_report.html` L51 + CSV), busca de colaboradores (`custodian_service.py` L155) | dashboard (distribuição), filtros de equipamentos web+API+relatórios (`asset_service.py` L87–88, `routers/assets.py` L98/162, `report_service`), filtro/escopo de inventário (`routers/inventario.py` L73–76, `inventario_service.py` L99–101), rótulos compostos (movimentação/entrada/relatórios), `locations/list.html` L73, etiquetas (`assets/labels.html` L163) |

### 3.3 Conclusão do modelo

```
Departamento do colaborador ──(ponte UNIDIRECIONAL via DepartmentService, Feature 012)──▶ valores de locations.department
```

O colaborador aponta para um **texto** que deve pertencer ao vocabulário da localização; não há chave estrangeira, não há tabela, não há integridade estrutural — a integridade é **convencional** (validação apenas no caminho do formulário web).

---

## 4. Onde o código implementa isso (mapa completo)

### 4.1 Composição do rótulo "Localização - Departamento" — no BACKEND (services)

| Arquivo | Linha | Código |
|---|---|---|
| `app/services/movement_service.py` | L136 | `prev_location_name = f"{asset.location.branch} - {asset.location.department} ({asset.location.name})"` |
| `app/services/movement_service.py` | L148 | `new_location_name = f"{new_location.branch} - {new_location.department} ({new_location.name})"` |
| `app/services/asset_service.py` | L167 | mesmo formato (entrada de bem) |
| `app/services/asset_service.py` | L178–186 | ⚠ formato DIFERENTE: `STATUS_UPDATE` grava snapshot só com `asset.location.name` (sem branch/department) — observação, §12 |
| `app/services/import_service.py` | L482, L629 | mesmo formato composto; fallback `"Estoque Central"` |
| `app/services/report_service.py` | L111, L205, L335 | `f"{asset.location.branch} - {asset.location.department}"` (sem `name`) |

### 4.2 Composição das opções do formulário — no TEMPLATE (não no JS)

| Arquivo | Linha | Ponto |
|---|---|---|
| `app/web/templates/movements/new.html` | L102–106 | campo **"Novo Local / Departamento"** (única ocorrência do rótulo) |
| `app/web/templates/assets/form.html` | L109–111 | select de localização do bem (mesmo padrão de option) |
| `app/web/routers/movements.py` | ~L65–95 (`form_new_movement`) | fornece `locations`/`custodians` ao template |
| `app/web/routers/movements.py` | ~L100–160 (`create_movement_form`) | recebe `destination_location_id` (int) |

### 4.3 Preservação do histórico (snapshots)

- Model: `app/models/movement.py` — colunas `origin/destination_location_name`, `origin/destination_custodian_name` + FKs; docstring "Gravação imutável... incluindo snapshots de origem e destino".
- Leitores dos snapshots: `movements/list.html` L129/133, `assets/detail.html` L258/266, `dashboard.html` L287, `reports/movements_report.html` L92/96, busca 049 (`movement_service.py` L513+), termo (`get_term_details` — local por snapshot).
- Assemblies de entrada também fabricam snapshots literais: origem `"Fornecedor / Entrada Inicial"` / `"Almoxarifado Geral"` e destino `"Estoque Central"` (`asset_service.py` L183, `import_service.py` L629) — sem FK, por definição.

### 4.4 Feature 012 — a ponte já existente entre os dois conceitos

- `app/services/department_service.py`: `list_official(db)` = valores distintos de `locations.department` (trim, não nulos, ordenados case-insensitive; **derivada ao vivo, zero DDL, sem cache/seed**); `ensure_official(db, department)` = canonização case-insensitive no caminho do formulário.
- `app/web/routers/custodians.py` L67/L89–91/L133/L183–185: só aplica `ensure_official` quando o form envia `department_source=official`; API REST e CSV ficam de fora (FR-012/FR-014).
- `specs/012-selecao-departamento-colaborador/spec.md` §3: doutrina oficial — **"Departamento/Setor do Colaborador ≠ Localização física do patrimônio"**, com reuso de vocabulário aceito e documentado no plan (research R1/R8).

---

## 5. Conflito ou relação entre os dois conceitos de Departamento

### 5.1 Resposta com evidência de código (não presumida)

1. **Não existe entidade de departamentos**: nenhuma tabela/model em `app/models/`; confirmado também pela spec 012 (baseline: "Setor não é entidade: é campo `department` em `Location` e `Custodian`").
2. **Ambos são texto livre `String(100)`**: `Custodian.department` (app/models/custodian.py L18) e `Location.department` (app/models/location.py L18). Sem FK entre si, sem FK a terceiros.
3. **Existe uma ponte DELIBERADA em uma direção** (Feature 012): a lista oficial de Departamento/Setor do **colaborador** é derivada **ao vivo** de `locations.department` (`DepartmentService.list_official`), com canonização (`ensure_official`) apenas no caminho do formulário web. Ou seja: o sistema **já trata o `Location.department` como o vocabulário canônico** para o setor do colaborador.
4. **A ponte é frouxa por decisão documentada**: API REST e importação CSV de colaboradores continuam texto livre; valores antigos não foram normalizados (FR-012/FR-014); `CustodianService` não valida.

### 5.2 Evidência dos DADOS reais (SELECT read-only, 2026-10-06)

Base: **36 localizações, 77 colaboradores, 118 movimentações**.

**a) Valores de `custodians.department` FORA da lista oficial (distintos de `locations.department`): 4 de 22**

| Valor gravado no colaborador | Colaboradores | Situação |
|---|---|---|
| `Divisão Previdenciária` | 8 | diverge do oficial `Divisão de Previdência` (texto diferente, não só caixa) |
| `Assessoria de Gabinete` | 4 | diverge do oficial — que está mal grafado: `Acessoria de Gabinete` |
| `Assessoria de Controle Interno` | 4 | diverge do oficial — mal grafado: `Acessoria de Controle Interno` |
| `Setor de Serviços Gerais` | 1 | **não existe em nenhuma localização** |

- Há também variação de caixa: `Seção de desenvolvimento` (2 colaboradores) vs oficial `Seção de Desenvolvimento` — seria canonizada numa próxima edição pelo `ensure_official`.

**b) Higiene do cadastro de localizações (o lado "fonte")**

| Problema | Registro(s) |
|---|---|
| Typos no `department` | `Acessoria de Controle Interno`, `Acessoria de Gabinete`, `Assist}ência Social` (chave estranha no meio), `Superitendência Adjunta`, `Shoping 4400` |
| Branch com travessão | `Sede - Data Center` usa branch `IPMJP – Sede` (EN DASH) enquanto as outras 35 usam `IPMJP - Sede` (hífen) — invisível a olho nu e quebra agrupamentos/filtros por branch |
| Espaços duplos no `name` | `Sede -  Assistência Social`, `Sede -  Sala de Reunião`, `Sede -  Data Center` |
| Nomes não institucionais | `Shoping 4400` (branch `Shoping`) |

**c) Departamento ≡ Localização? Hoje é 1:1 — mas por acidente de dados**

Cada valor de `department` aparece em **exatamente 1** localização; nenhum par `(branch, department)` se repete. Em 2 casos o departamento é uma cópia do nome (`Clube da Pessoa Idosa`, `Shoping 4400`). **Não há constraint de unicidade** — nada impede que amanhã exista `Setor de Atendimento` na Sede e no Shoping. Ou seja: escolher destino "por departamento" hoje é não-ambíguo **por sorte dos dados**, não por garantia estrutural.

### 5.3 Veredito (alternativas do briefing)

**C — parcialmente relacionados.** São conceitos de negócio distintos (a própria spec 012 chancela: "Departamento/Setor do Colaborador ≠ Localização física"), porém o sistema já os unificou **de facto no vocabulário** (a fonte oficial do colaborador É a lista de `locations.department`). Não é "A" (não há entidade compartilhada) nem "B" puro (não são independentes — a 012 os ponteou). Não é "D": não há mistura acidental de conceitos — a ponte é intencional e documentada. O risco semântico real não é a homonímia em si, e sim o **drift de dados** observado (valores do lado colaborador fora do vocabulário canônico + typos do lado canônico).

### 5.4 Risco de conflito semântico ao usar "Departamento" como destino

Baixo. O campo de movimentação escolhe **localização** (id); "Departamento" só apareceria como rótulo. O colaborador não entra no destino da movimentação (o destino de custódia é o campo separado "Novo Colaborador"). Os dois conceitos só se encontram no **texto das opções**, e a 012 já os alinhou. A única exigência: se o rótulo passar a liderar com o departamento, o **contexto (branch/local) deve permanecer visível na opção** para desambiguar quando (se) houver departamento repetido entre unidades.

---

## 6. Impacto da mudança proposta (Departamento/Setor como identificação principal)

Premissa: com o menor alteração segura (ver §8/§9), **o value continua sendo `loc.id`** — nada muda no backend, no banco e no histórico. O impacto se concentra na **apresentação das opções**.

| Área | Impacto | Detalhe |
|---|---|---|
| Movimentação — form | **SIM (alvo)** | `movements/new.html` L102–106: reordenar texto da option |
| Equipamentos — form | OPCIONAL | `assets/form.html` L111 usa o mesmo padrão — recomenda-se mudar junto por consistência |
| Movimentação — lista/histórico | **NENHUM** | lê snapshots gravados (`origin/destination_location_name`) — textos antigos permanecem |
| Bem — timeline | **NENHUM** | snapshots |
| Termo de responsabilidade | **NENHUM** (local) | `get_term_details` usa snapshot do local; recomenda-se **manter o formato do snapshot** para não fragmentar a busca |
| Busca de movimentações (049) | **NENHUM** | casa snapshots; formato inalterado = compatibilidade total |
| Equipamentos — lista/detalhe (estado atual) | NENHUM | segue FK (`a.location.*`) — continua ao vivo |
| Dashboard | NENHUM | distribuição por `Location.department` (ao vivo) e recentes por snapshot — intocados |
| Relatórios | NENHUM | `report_service` usa `branch - department` do cadastro vigente e snapshots de movimentação — intocados |
| Inventário | NENHUM | escopo filtra por `location_id`/`department` (texto do cadastro vigente); `expected_location_name` é snapshot do **nome** na criação do item |
| Importação/exportação (CSV) | NENHUM | importadores resolvem local por nome/id; snapshots gerados mantêm formato |
| API REST | NENHUM | `MovementCreate`/`MovementRead` já operam com `destination_location_id` |
| Banco / migration | **NENHUM** | zero DDL, zero migração de dados |
| Permissões / RBAC / auditoria | NENHUM | mesmas rotas, mesmas permissões `movimentacao.criar` |
| Integrações (1Doc, AD, SMTP) | NENHUM | não tocam rótulos de opção |
| Risco novo introduzido | 1, mitigável | **ambiguidade futura** se o mesmo `department` existir em duas localizações (hoje 1:1): mitigar exibindo branch/unidade na própria opção (ou optgroups por unidade) |

---

## 7. Riscos

| # | Risco | Avaliação | Mitigação |
|---|---|---|---|
| 1 | **Perda/alteração de histórico** (movimentações antigas mudarem de significado) | **MÍNIMO** — histórico é snapshot imutável gravado na emissão; mudança proposta não reescreve nada | Manter snapshots como estão; NUNCA reescrever `destination_location_name` de registros antigos; testes de não-rewrita na spec |
| 2 | **Duplicidade/ambiguidade de departamento** entre localizações | **BAIXO hoje** (dados 1:1), cresce se duas unidades tiverem setor homônimo (não há constraint) | Exibir branch/unidade como contexto na option; optgroups por unidade; se a instituição crescer, aí sim avaliar Alternativa C |
| 3 | **Inconsistência de dados** (typos/drift) ganhar protagonismo | **REAL e COMPROVADO** (`Acessoria`, `Assist}ência`, `Divisão Previdenciária` × `Divisão de Previdência`, branch com travessão) — se o rótulo lidera com o departamento, o erro fica mais visível | Correção cadastral dos typos (ação administrativa normal, não quebra histórico — snapshots antigos mantêm a grafia da época, o que é correto); eventual feature de higiene própria |
| 4 | **Mudança de significado dos dados** | NENHUMA com a abordagem B — `destination_location_id` continua sendo a chave; o que muda é só o texto exibido | — |
| 5 | **Incompatibilidade com registros existentes** | NENHUMA — nada é regravado; busca continua casando os formatos antigos | Não alterar o formato dos snapshots novos (manter `branch - department (name)`) para não criar dois formatos convivendo na busca |
| 6 | **Fragmentação de formato de snapshot** (se alguém aproveitar e mudar também o snapshot) | Risco de *scope creep* | Escopo da futura SPEC deve proibir explicitamente mudança de snapshot na v1 |
| 7 | Termo exibir dados desatualizados | Já existe hoje e é assimétrico: local = snapshot (correto), **colaborador = vivo** (`get_term_details` L608) — re-render do termo reflete mudanças posteriores de `custodian.department` | Observação (§12); fora do escopo desta análise |

## 8. Alternativas

### Alternativa A — manter Localização como identificação principal (status quo)

- **Vantagens**: zero esforço; zero risco; comportamento provado em produção.
- **Desvantagens**: rótulo verboso e redundante (`Sede - Divisão de Previdência (IPMJP - Sede - Divisão de Previdência)` — o departamento aparece 2× e o nome do local já é quase todo o rótulo); operador pensa "para qual setor vou entregar?" e o campo começa pelo prédio.
- Complexidade 0 · Risco 0 · Banco: nada · Backend: nada · Frontend: nada · Dados: nada · Histórico: nada.
- **Recomendação**: não resolve a dor relatada.

### Alternativa B — Departamento/Setor como identificação principal, Localização/Unidade como contexto ⭐

- **O quê**: nas opções do `select`, o texto passa a liderar com o departamento, com contexto na sequência — ex.: `Divisão de Previdência — Sede (IPMJP - Sede)` ou, fiel ao exemplo do briefing, `Divisão de Previdência` com subtexto `Sede • IPMJP - Sede`. **O `value` continua `loc.id`.**
- **Vantagens**: atende exatamente à proposta; alinhado ao vocabulário que o operador já usa (o colaborador já é escolhido por setor — `c.name (matrícula - department)`); **zero DDL, zero migration, zero backend**; histórico imune (snapshots intocados); compatível com busca e relatórios existentes.
- **Desvantagens**: ganho é de UX — não cria integridade estrutural; se aparecerem departamentos homônimos entre unidades, o contexto na opção é obrigatório (e é exatamente o que se mantém).
- Complexidade **mínima** · Risco **mínimo** · Banco: **nada** · Backend: **nada** · Frontend: 1–2 templates · Dados: **nenhuma migração** · Histórico: **intocado**.
- **Variante B+**: agrupar opções por unidade com `<optgroup label="{{ loc.branch }}">` — melhora ainda mais a varredura visual; ainda só template.
- **Recomendação**: **SIM** — é a menor alteração segura que entrega o objetivo.

### Alternativa C — criar/normalizar entidade única de Departamento/Setor ligada a colaboradores e localizações

- **O quê**: tabela `departments`, FKs em `custodians.department_id` e `locations.department_id`, migração e limpeza do drift (unificar `Divisão Previdenciária`→`Divisão de Previdência`, corrigir typos, caixa, etc.).
- **Vantagens**: integridade real (FK), sem drift, habilitaria permissões/relatórios por departamento e departamentos multi-unidade.
- **Desvantagens**: DDL + migration + reescrita de `DepartmentService` + ajuste em formulários, API, CSV de colaboradores e locais, filtros, relatórios, dashboard, busca; **migração de dados obrigatória** com decisão de unificação (ex.: 8 colaboradores de `Divisão Previdenciária`); a Feature 012 deliberadamente escolheu zero DDL; quebra o princípio da casa de mudança mínima sem necessidade comprovada hoje.
- Complexidade **alta** · Risco **médio** (migração + regressão ampla) · Banco: **DDL + migração** · Backend: amplo · Frontend: amplo · Dados: **sim, migração** · Histórico: preservável, mas snapshots antigos ficariam com grafias pré-unificação (correto, porém visível).
- **Recomendação**: **NÃO agora**. Só se nascer requisito real: departamentos servindo a mais de uma unidade, permissões por departamento, ou integração com RH/AD onde o setor é chave estrutural.

### Alternativa D — seleção em duas etapas (Departamento → Local) com resolução automática

- **O quê**: operador escolhe o departamento; se houver um único local com aquele departamento (hoje: sempre), o sistema resolve o local sozinho; se houver mais de um, pergunta o local.
- **Vantagens**: experiência mais próxima do pedido; preparada para multi-unidade.
- **Desvantagens**: exige JS/backend novo (endpoint de resolução ou JS sobre os dados já renderizados), mais superfície de teste, benefício marginal **hoje** porque a relação é 1:1.
- Complexidade **média** · Risco **baixo-médio** · Banco: nada · Backend: pequeno · Frontend: médio · Dados: nada · Histórico: nada.
- **Recomendação**: **NÃO agora**; registrar como evolução natural caso a B+ (optgroups) não baste quando a instituição crescer.

---

## 9. Recomendação técnica

**Alternativa B (com variante B+ optgroups), como SPEC de escopo mínimo — apresentação-pura:**

1. **`app/web/templates/movements/new.html`** (obrigatório): rótulo da opção com o departamento em primeiro lugar e local/unidade como contexto; `value="{{ loc.id }}"` **inalterado**; sugestão de formato: `{{ loc.department }} — {{ loc.name }} ({{ loc.branch }})` → `Divisão de Previdência — Sede - Divisão de Previdência (IPMJP - Sede)`, ou apenas `{{ loc.department }} ({{ loc.branch }})` se o nome do local for suprimido (decisão da spec; hoje o `name` já contém branch+department, então suprimi-lo elimina a redundância do exemplo do briefing).
2. **`app/web/templates/assets/form.html`** L111 (recomendável junto): mesmo padrão, por consistência entre os dois selects de localização.
3. **Optgroups por unidade** (B+, opcional): `<optgroup label="{{ loc.branch }}">` agrupando os locais — resolve visualmente o caso "escolher o setor dentro da unidade".
4. **NÃO alterar** o formato dos snapshots (`movement_service.py` L136/L148 etc.), **NÃO alterar** backend/banco, **NÃO reescrever** registros existentes.
5. Higiene de dados (typos, branch com travessão, `Divisão Previdenciária`): **ação cadastral separada** (tela de Localizações/Colaboradores), fora da SPEC de apresentação; é segura porque o histórico preserva os snapshots da época.

## 10. Escopo sugerido para FUTURA SPEC (proposta — NÃO implementar nesta etapa)

- **Arquivos provavelmente afetados**: `app/web/templates/movements/new.html`; opcionalmente `app/web/templates/assets/form.html`; **nenhum arquivo** em `app/models/`, `app/services/`, `app/schemas/`, `app/api/`, migrations.
- **Tabelas provavelmente afetadas**: **nenhuma** (zero DDL).
- **Necessidade de migration**: **não**.
- **Necessidade de ajustes no backend**: **nenhuma** (a rota e o service já operam com `destination_location_id`).
- **Necessidade de ajustes no frontend**: reordenar/agrupar o texto das opções; nenhum JS obrigatório (optgroup é server-side).
- **Necessidade de migração de dados**: **nenhuma**.
- **Testes necessários** (padrão da casa, TDD red→green): renderização do form contendo o departamento no início do texto da opção **e** o `value` idêntico ao id do local; opção vazia `-- Manter Local Atual --` preservada; fluxo completo de transferência gravando `destination_location_id` e snapshot **exatamente como hoje** (teste de não-mutação de formato); busca de movimentações por snapshot continua casando; suíte completa verde (régua atual: 923 passed / 1 skipped).
- **Critérios de aceitação sugeridos**: (1) operador identifica o setor de destino lendo o começo da opção; (2) unidade/local permanece visível como contexto; (3) value enviado = id da Location; (4) histórico, termo, relatórios e busca de movimentações exibem exatamente os mesmos textos de antes para registros antigos; (5) zero alteração em movimentações/termos/audit_logs; (6) permissões e rotas inalteradas.
- **Decisões que a SPEC deve tomar**: incluir ou não `assets/form.html`; adotar ou não optgroups; suprimir ou manter o `name` do local no rótulo; rótulo do campo (sugestão: manter "Novo Local / Departamento" ou evoluir para "Novo Departamento / Setor — local de destino").

## 11. Respostas objetivas às 10 perguntas

1. **É viável?** Sim. O destino já é e continua sendo o id da Localização; o departamento é só rótulo.
2. **É recomendável?** Sim, como melhoria de apresentação (Alternativa B). Não como re-modelagem (C) — não há requisito que a justifique hoje.
3. **O Departamento do colaborador e o Departamento/Setor da localização são o mesmo conceito?** Não são a mesma entidade (duas colunas de texto livre, sem FK, sem tabela de departamentos), mas desde a Feature 012 compartilham o **mesmo vocabulário canônico** (`locations.department` é a fonte oficial da seleção do colaborador). Conclusão: **C — parcialmente relacionados**, com drift real de dados (4 valores de colaborador fora da lista + typos no lado canônico).
4. **Devem compartilhar a mesma estrutura?** Já compartilham o vocabulário (ponte unidirecional, zero DDL). Compartilhar **estrutura** (entidade/FK) só se surgir necessidade real (departamento multi-unidade, permissões por setor, integração RH/AD). Não recomendo agora.
5. **O campo "Novo Local / Departamento" deve mudar?** Sim — o **texto** da opção (departamento primeiro, local/unidade como contexto). O **value** (`loc.id`) e o nome do campo (`destination_location_id`) não devem mudar.
6. **Menor alteração segura?** Reordenar o rótulo das opções em `movements/new.html` (e opcionalmente `assets/form.html`): 1–2 templates, zero backend, zero banco.
7. **É necessário alterar banco?** Não. Zero DDL, zero migration.
8. **É necessário migrar dados?** Não. (Correção de typos/grafias é higiene cadastral opcional, feita pelas telas — não é migração e não toca histórico.)
9. **Risco de quebrar movimentações e histórico?** Praticamente nulo com a abordagem B: histórico é snapshot imutável (verificado: 118 movimentações, 0 FK sem snapshot, 0 FK órfã, snapshots 100% coerentes com o cadastro vigente). Risco residual controlado: não mudar o formato dos snapshots novos (evita dois formatos na busca).
10. **Próximo passo para a SPEC?** Executar `/speckit-specify` com escopo da §10 (apresentação-pura), decidindo: incluir `assets/form.html`? optgroups? suprimir o `name` do local no rótulo? Depois `/speckit-plan` → `/speckit-tasks` com TDD e teste de não-mutação de snapshots.

## 12. Observações (problemas não relacionados — apenas registro, §12 do briefing: nada corrigido)

1. **Formato de snapshot divergente**: a movimentação `STATUS_UPDATE` (`asset_service.update`) grava `origin/destination_location_name` apenas com `location.name`, sem o formato composto `branch - department (name)` usado no resto do sistema — os dois formatos já convivem.
2. **Assimetria do termo**: `get_term_details` exibe o local pelo **snapshot**, mas o departamento do colaborador **vivo** (`custodian.department`, L608) — re-render de um termo antigo reflete mudanças posteriores do cadastro do colaborador (o PDF impresso é estático).
3. **Dados com typos** (lado canônico): `Acessoria de Controle Interno`, `Acessoria de Gabinete`, `Assist}ência Social`, `Superitendência Adjunta`, `Shoping 4400`, espaços duplos em 3 nomes.
4. **Branch com EN DASH**: `Sede - Data Center` usa `IPMJP – Sede` (travessão) vs `IPMJP - Sede` nas demais 35 — invisível a olho nu e quebra agrupamentos por unidade.
5. **`department` sem unicidade**: a equivalência 1:1 departamento↔localização é acidente dos dados atuais (36 locais), não garantia estrutural — qualquer solução "por departamento" deve sempre manter o contexto de unidade/local visível.
6. **Drift colaborador × lista oficial**: `Divisão Previdenciária` (8), `Assessoria de Gabinete` (4), `Assessoria de Controle Interno` (4), `Setor de Serviços Gerais` (1), `Seção de desenvolvimento` (caixa) — consequência esperada dos caminhos fora da 012 (API/CSV) e da não-normalização do acervo (FR-014).

---

*Fim da análise. Nenhuma implementação foi realizada; este documento é apenas a base de decisão para a eventual SPEC.*
