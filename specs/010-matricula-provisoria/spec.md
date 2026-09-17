# Feature Specification: Identificador Provisório de Colaborador (PROV-*)

**Feature Branch**: `010-matricula-provisoria`

**Created**: 2026-09-17

**Status**: Draft

**Input**: Permitir o cadastro e uso patrimonial de um colaborador que ainda não possui (ou não informou) a matrícula funcional oficial, usando um identificador provisório gerado automaticamente pelo sistema no formato `PROV-000001`, claramente distinguível de uma matrícula real, com substituição posterior pela matrícula oficial preservando o colaborador, os vínculos e o histórico.

---

## 1. Análise do sistema atual (somente leitura, verificada nesta especificação)

Fatos confirmados no código que delimitam esta feature — nenhum nome abaixo é presumido:

| # | Ponto investigado | Realidade atual verificada |
|---|---|---|
| 1 | Modelagem do colaborador | `app/models/custodian.py`: classe `Custodian` (tabela `custodians`) |
| 2 | Onde a matrícula vive | Coluna `registration_code` (`String(50)`, `nullable=False`, `unique=True`, `index=True`), comentada no código como "Matrícula" |
| 3 | Restrição de unicidade | `UNIQUE` no banco + validação no service (`"Matrícula já cadastrada"`) |
| 4 | Cadastro | `CustodianService.create` (service); rotas web `POST /custodians/new` (form `Form(...)`) e API REST — **a matrícula é obrigatória hoje** (schema `CustodianCreate.registration_code: str`) |
| 5 | Pesquisa | `CustodianService.get_all(search=...)` (feature 006): termo combinado incluindo a matrícula |
| 6 | Interface | Formulário `custodians/form.html` (campo "Matrícula / Código Funcional" **obrigatório**; em edição o campo é **readonly**), listagem `custodians/list.html`, detalhes `custodians/detail.html`, `assets/detail.html`, `assets/form.html`, `assets/list.html`, `movements/new.html`, importação `custodians/import.html` |
| 7 | Movimentações | `Movement` referencia o colaborador por **FK (`origin_custodian_id`/`destination_custodian_id`) + snapshot textual** (`origin_custodian_name`/`destination_custodian_name`), gravado no formato `"Nome (MAT-xxxx)"` em `movement_service.py` — a trilha é **imutável** (Princípio IV da Constitution) |
| 8 | Termos | `movements/term.html` exibe a matrícula **viva** do colaborador (`term.custodian.registration_code`) na tabela do documento |
| 9 | Vínculo com bens | `Asset.custodian_id` → FK para `custodians.id` |
| 10 | Vínculo com movimentações | Mesmo modelo de #7 (FK por `id` + snapshot textual) |
| 11 | Inventário | `InventarioItem` guarda apenas **snapshot de nome** (`expected_custodian_name`) — não usa matrícula |
| 12 | Autenticação | `User` (tabela `users`) é entidade **separada** de `Custodian` (login por `username`, hash PBKDF2) |
| 13 | Matrícula × login | **Nenhuma relação**: `username` do login não deriva da matrícula |
| 14 | Usuário local × colaborador | **Sem vínculo estrutural** (não existe FK users→custodians) |
| 15 | Usuário AD × colaborador | `ad_service.py` vincula por **e-mail/matrícula**: casa `Custodian.registration_code == username do AD` (L213) e e-mail — provisionamento exige correspondência |
| 16 | Serviços que criam/alteram | `CustodianService.create/update`; importação CSV de colaboradores (`custodian_import_service.py`, matrícula **obrigatória** na importação); API REST (`custodians_api.py`, com auditoria `write_audit`/`write_change_audit`); AD provisiona/atualiza colaborador |
| 17 | Testes existentes | `test_movements.py`, `test_rbac.py`, `test_custodian_import.py`, `test_custodians_search.py`, `test_ad.py`, `test_api.py` usam matrículas do tipo `MAT-xxxx` e exercitam duplicidade/validações atuais |

**Consequências da análise** (refletidas nos requisitos):

- O **snapshot textual** das movimentações congela a matrícula da época — por design, registros históricos **não mudam** quando a matrícula oficial substitui a provisória (a trilha histórica é imutável e a FK por `id` preserva o vínculo). Termos futuros exibirão a matrícula atual.
- A substituição da matrícula **existe parcialmente hoje**: o service aceita `registration_code` no update, mas a **interface web bloqueia** (campo readonly) e o **AD usa a matrícula como chave de casamento** — os impactos estão listados na Seção "Impacto esperado".
- Existe **precedente interno** para numeração sequencial com prefixo: `InventarioService.next_code` gera `INV-YYYY-NNNN` consultando o maior código existente + 1, apoiado na constraint `UNIQUE` — o mesmo padrão de abordagem se aplica ao `PROV-`.

---

## 2. Princípio fundamental

O identificador `PROV-000123` é um **identificador temporário do colaborador**, não uma matrícula funcional falsa. Ele existe para permitir o cadastro patrimonial antes de a matrícula oficial existir. A existência de uma identificação provisória **não impede, por si só, nenhuma operação patrimonial** do colaborador.

### Separação identificação × autenticação (regra explícita)

- **Identificação patrimonial**: `PROV-000123` vive em `custodians.registration_code`.
- **Autenticação**: mecanismos existentes (usuário local por `username`/senha; AD por bind LDAP). `User` e `Custodian` são entidades separadas, sem FK entre si.
- O identificador provisório **NÃO pode** ser usado como senha, nome de usuário de login, substituto de username AD, CPF, telefone ou qualquer dado pessoal; e **NÃO pode** ser fabricado a partir de dado pessoal (CPF, telefone, nome, username AD, e-mail, data de nascimento ou qualquer outro dado pessoal). É sempre um número sequencial gerado pelo sistema.

---

## 3. User Scenarios & Testing

### User Story 1 - Cadastrar colaborador sem matrícula oficial (Priority: P1) 🎯 MVP

Um usuário com permissão de cadastro de colaboradores precisa alocar um bem a uma pessoa recém-contratada cuja matrícula funcional ainda não foi emitida/informada. Hoje isso é impossível (a matrícula é obrigatória no cadastro). Ao deixar o campo de matrícula em branco, o sistema gera automaticamente um identificador `PROV-*` e o cadastro segue normal, com o caráter provisório visível em todas as telas.

**Why this priority**: É a lacuna central da feature — sem ela, ou o colaborador não existe no sistema, ou recebe uma matrícula falsa que depois precisa ser "gambiarreada".

**Independent Test**: Cadastrar um colaborador preenchendo nome/e-mail/cargo/departamento e deixando a matrícula vazia → o registro é criado com identificador `PROV-000001` (ou o próximo sequencial), único, marcado como provisório na interface; o colaborador aparece na pesquisa e na listagem normalmente.

**Acceptance Scenarios**:

1. **Given** o formulário de cadastro de colaborador, **When** o usuário preenche os campos obrigatórios existentes deixando a matrícula em branco e salva, **Then** o colaborador é criado com identificador `PROV-` + número sequencial gerado automaticamente (formato `PROV-000001`, 6 dígitos), e a tela confirma a criação.
2. **Given** um colaborador com identificador `PROV-000001`, **When** outro colaborador é cadastrado também sem matrícula, **Then** recebe `PROV-000002` (sem repetição, sem interferência do usuário).
3. **Given** a listagem e os detalhes do colaborador provisório, **When** a matrícula é exibida, **Then** aparece de forma inequivocamente provisória (ex.: `PROV-000001 (provisória)`), sem poder ser confundida com matrícula oficial.
4. **Given** um colaborador provisório na pesquisa (006), **When** o usuário busca por `PROV-000001` (ou parte), **Then** o colaborador é encontrado normalmente.

### User Story 2 - Usar o colaborador provisório normalmente nas operações patrimoniais (Priority: P1)

O colaborador com identificador provisório participa de todas as operações patrimoniais que um colaborador normal participa — a condição provisória **não é motivo de bloqueio**. Nenhuma regra nova de restrição é criada; as regras existentes de cada operação continuam valendo.

**Why this priority**: O valor da feature é justamente não travar o patrimônio à espera de papelada de RH.

**Independent Test**: Com um colaborador `PROV-*` cadastrado, executar as operações típicas (alocação/cautela de bem, devolução, transferência, emissão de termo, conferência de inventário) → todas seguem o comportamento existente, sem erro ou bloqueio atribuível ao caráter provisório.

**Acceptance Scenarios**:

1. **Given** um colaborador provisório cadastrado, **When** um bem é alocado a ele (Alocação/Cautela), **Then** a movimentação é registrada normalmente e o histórico exibe o colaborador com sua identificação provisória.
2. **Given** um colaborador provisório custodiando bens, **When** um termo de responsabilidade/cautela é emitido, **Then** o termo é gerado normalmente exibindo a identificação atual do colaborador (incluindo a marcação de provisória quando aplicável).
3. **Given** um inventário em andamento, **When** um bem é conferido com o colaborador provisório como custodiante esperado/encontrado, **Then** o registro segue o comportamento existente (que usa nome do colaborador em snapshot).
4. **Given** qualquer operação patrimonial existente, **When** executada com colaborador provisório, **Then** nenhuma validação nova impede a operação apenas por causa do caráter provisório (o colaborador inativo, por exemplo, segue sujeito às regras que já existem).

### User Story 3 - Substituir o identificador provisório pela matrícula oficial (Priority: P2)

Chegada a matrícula funcional oficial (ex.: `123456`), o usuário autorizado informa-a no cadastro do colaborador. O sistema substitui o `PROV-*` pela matrícula oficial **mantendo o mesmo colaborador**: mesmo `id`, mesmos vínculos de bens, movimentações e termos, histórico e auditoria preservados — nenhuma "segunda pessoa" é criada.

**Why this priority**: Fecha o ciclo da feature; depende da US1 para existir, mas é o requisito de correção cadastral.

**Independent Test**: Cadastrar colaborador `PROV-*`, alocar um bem a ele, depois informar a matrícula oficial → o colaborador permanece o mesmo registro (mesmo `id`), o bem continua vinculado, o histórico da movimentação continua válido, e a partir de então a matrícula oficial é exibida.

**Acceptance Scenarios**:

1. **Given** um colaborador com identificador `PROV-000123` e um bem alocado, **When** um usuário autorizado informa a matrícula oficial `123456`, **Then** o mesmo colaborador passa a exibir `123456`, marcado como oficial; nenhum novo colaborador é criado.
2. **Given** a substituição efetivada, **When** o histórico de movimentações anteriores é consultado, **Then** os snapshots antigos permanecem como foram gravados na época (com a identificação da época) — nada é reescrito retroativamente, e o vínculo por FK permanece íntegro.
3. **Given** a substituição efetivada, **When** um novo termo é emitido para o colaborador, **Then** o termo exibe a matrícula oficial (os termos são documentos emitidos com a identificação vigente).
4. **Given** a trilha de auditoria, **When** a substituição ocorre, **Then** a alteração é registrada (antes/depois) conforme o mecanismo existente de auditoria de alterações de colaborador, sem qualquer dado sensível.
5. **Given** um colaborador que **já possui** matrícula oficial (não `PROV-*`), **When** tenta-se substituir a matrícula pela interface, **Then** o comportamento permanece o atual (bloqueio existente da interface para matrícula oficial é preservado; a substituição permitida é exclusivamente a de identificador `PROV-*` → matrícula oficial).

### User Story 4 - Segurança e integridade da numeração (Priority: P2)

O sistema garante que a numeração `PROV-*` é controlada pelo sistema: única, sequencial, imune a colisão em cadastros simultâneos, e não fabricável pelo usuário.

**Why this priority**: Protege a integridade do mecanismo; não tem valor sozinha, mas é pré-condição de confiabilidade.

**Independent Test**: Criar colaboradores simultâneos sem matrícula → todos recebem identificadores distintos e sequenciais; tentar informar manualmente um valor `PROV-*` no cadastro → rejeitado.

**Acceptance Scenarios**:

1. **Given** dois usuários cadastrando colaboradores sem matrícula ao mesmo tempo, **When** ambos salvam, **Then** cada colaborador recebe um identificador `PROV-*` **distinto** (ex.: `PROV-000125` e `PROV-000126`) — nunca o mesmo.
2. **Given** o formulário de cadastro, **When** o usuário tenta informar manualmente um valor no campo de matrícula que siga o padrão `PROV-*`, **Then** a tentativa é rejeitada (o usuário não fabrica identificadores provisórios; valores oficiais digitados continuam sujeitos às validações existentes).
3. **Given** a base de dados, **When** consultada, **Then** não existem dois colaboradores com o mesmo identificador (regra de unicidade válida para todos os registros, oficiais e provisórios — a coluna já é `UNIQUE`).

---

## 4. Edge Cases

- **Campo de matrícula preenchido com espaços em branco** → tratado como não informado (gera `PROV-*`), coerente com a normalização já usada nas pesquisas do sistema.
- **Esgotamento/colisão na geração** (ex.: falha transiente de banco durante a geração) → a operação falha com mensagem de erro padrão do sistema, sem gravar colaborador parcial; nova tentativa gera o próximo número (a geração é idempotente em relação ao estado do banco — consulta o maior existente + 1, e a constraint `UNIQUE` é a última linha de defesa).
- **Conflito de concorrência real** (dois cadastros simultâneos) → a solução deve se apoiar no comportamento do MariaDB/MySQL em produção e na estratégia dos testes (SQLite em memória), sem inventar mecanismo novo: se a colisão ocorrer, o registro não é gravado com identificador duplicado e a operação pode ser repetida com segurança.
- **Colaborador provisório inativado** (ex.: desligado antes de receber matrícula) → segue o comportamento existente de colaboradores inativos; seu `PROV-*` não é reutilizado (a unicidade é permanente na coluna).
- **Importação CSV de colaboradores** → o comportamento da importação **não muda** nesta feature (matrícula obrigatória, como hoje). Registrado como não incluído para manter o escopo mínimo (ver §7).
- **Vinculação AD** → o casamento `registration_code == username AD` continua funcionando com matrícula oficial; um `PROV-*` não corresponde a nenhum username AD real (prefixo + zeros não é username de domínio), portanto o comportamento atual de provisionamento não é alterado. Se um usuário do AD tiver username que case com um `PROV-*` (hipótese remota), o comportamento atual de casamento por e-mail/matrícula prevalece — sem regra nova.
- **Colaborador já possui matrícula oficial** → não pode receber identificador provisório (só se aplica quando a matrícula não é informada) e não pode ter sua matrícula oficial trocada pela interface (comportamento atual preservado).
- **Tentativa de gravar manualmente `PROV-*` via API** → rejeitada com o mesmo princípio da interface (ver FR correspondente), respeitando o padrão atual de resposta de erro da API.
- **Termo emitido na época provisória e consultado depois da substituição** → documentos e snapshots já emitidos permanecem como foram gerados (imutabilidade); apenas emissões novas exibem a matrícula oficial.

---

## 5. Requirements

### Functional Requirements

- **FR-001**: O cadastro de colaborador DEVE aceitar a matrícula **não informada** (campo vazio) — na interface web e nos demais caminhos de criação existentes — gerando automaticamente um identificador provisório no formato `PROV-` + 6 dígitos (ex.: `PROV-000001`).
- **FR-002**: O número após `PROV-` DEVE ser gerado automaticamente pelo sistema, sequencial (proximo número disponível), sem escolha do usuário; o formato é fixo e o prefixo é obrigatoriamente `PROV-` (nenhum outro prefixo, sem espaços, sem variação).
- **FR-003**: O identificador provisório DEVE ser **único** na base (nunca dois colaboradores com o mesmo identificador), valendo a constraint `UNIQUE` existente na coluna de matrícula — nenhuma alteração de schema para unicidade é necessária.
- **FR-004**: A geração NÃO DEVE derivar de dados pessoais (CPF, telefone, nome, username AD, e-mail, data de nascimento ou qualquer outro dado pessoal) — exclusivamente numeração sequencial própria do sistema.
- **FR-005**: O usuário NÃO DEVE poder fabricar um identificador provisório: valores digitados que sigam o padrão `PROV-*` são rejeitados nos caminhos de criação (interface e API), com mensagem consistente com os padrões atuais.
- **FR-006**: Quando o colaborador possuir identificador provisório, a interface DEVE marcá-lo claramente como provisória em todas as exibições relevantes (listagem, detalhes do colaborador, formulário, seleção de colaborador em movimentação, detalhes do bem, termo) — apresentação inequívoca, que não permita confundir com matrícula oficial.
- **FR-007**: A condição provisória NÃO DEVE criar nenhum bloqueio novo de operações patrimoniais: cadastro, alocação/cautela, transferência, devolução, envio/retorno de manutenção, inventário, emissão de termos, consultas e histórico seguem as regras existentes de cada operação.
- **FR-008**: DEVE ser possível informar posteriormente a matrícula funcional oficial substituindo o identificador `PROV-*`, **mantendo o mesmo colaborador** (mesmo registro/`id`): bens vinculados, movimentações, termos e histórico permanecem íntegros (relacionamentos por FK por `id`), sem criar segunda pessoa.
- **FR-009**: A substituição DEVE seguir as validações existentes (unicidade da matrícula oficial — "Matrícula já cadastrada"), exigir permissão de edição de colaboradores (a que já existe) e ser registrada na auditoria conforme o mecanismo atual de alterações.
- **FR-010**: A substituição pela interface é permitida **apenas** quando o identificador atual for `PROV-*`; colaboradores com matrícula oficial mantêm o bloqueio atual de edição de matrícula (comportamento existente preservado — sem nova regra de troca de matrícula oficial).
- **FR-011**: Snapshots históricos e documentos já gravados (movimentações, termos emitidos, ata de inventário) NÃO são reescritos pela substituição (imutabilidade da trilha — Princípio IV); emissões futuras usam a identificação vigente.
- **FR-012**: O identificador provisório NÃO DEVE ser usado como senha, login, CPF ou qualquer dado pessoal de autenticação; nenhuma relação nova entre `User` e `Custodian` é criada.
- **FR-013**: A pesquisa de colaboradores (feature 006) DEVE continuar funcionando com identificadores `PROV-*` (o campo de matrícula já é um dos alvos da pesquisa combinada).
- **FR-014**: A geração DEVE evitar duplicidade em cadastros simultâneos, com comportamento compatível com MariaDB/MySQL (produção) e com a estratégia da suíte de testes; a constraint `UNIQUE` da coluna é a garantia final.
- **FR-015**: Nenhum comportamento existente DEVE regredir: cadastro com matrícula informada (web/API/CSV), validações de duplicidade atuais, pesquisas, importação CSV (matrícula obrigatória, inalterada), vinculação AD (casamento por e-mail/matrícula), movimentações, inventário, termos, auditoria e RBAC permanecem como estão.

### Key Entities

- **`Custodian`** (existente): a coluna `registration_code` (`String(50)`, `unique`, `not null`) passa a abrigar também identificadores `PROV-*`. **Nenhuma nova coluna é criada** para distinguir provisória de oficial — o **prefixo `PROV-` é o marcador** (identificador autoevidente, evita migração, coluna nova e sincronização de estado). Nenhuma alteração de schema nesta feature (a coluna atual já suporta o formato — `String(50)`).
- **`Asset`, `Movement`, `Termo/term.html`, `InventarioItem`**: consumidores existentes — vinculam por FK/`id` ou exibem a matrícula corrente/snapshot; seu comportamento não muda (apenas a apresentação ganha a marcação de provisória onde a matrícula é exibida viva).
- **`User` / autenticação / AD**: intocados (separação identificação × autenticação).

---

## 6. Success Criteria

- **SC-001**: 100% dos cadastros sem matrícula oficial resultam em identificador `PROV-*` único, sequencial e não escolhível — comprovado por testes (incluindo cadastros simultâneos sem colisão).
- **SC-002**: 100% das operações patrimoniais testadas com colaborador provisório seguem o comportamento existente, sem qualquer bloqueio novo atribuível ao caráter provisório (alocação, devolução, transferência, termo, inventário, consultas).
- **SC-003**: A substituição `PROV-*` → matrícula oficial preserva o mesmo colaborador (mesmo `id`), os vínculos (bens, movimentações, termos) e o histórico — comprovado por testes de não-perda.
- **SC-004**: Zero apresentação de `PROV-*` como matrícula oficial nas telas (marcação "provisória" presente em todas as exibições da matrícula viva de colaborador provisório).
- **SC-005**: Zero uso de `PROV-*` como credencial ou derivação de dado pessoal — e tentativa de fabricação manual (`PROV-*` digitado) rejeitada em interface e API.
- **SC-006**: A suíte existente permanece no patamar atual (nenhum teste regressa); novos testes cobrem os cenários desta spec seguindo os padrões existentes (`tests/test_*.py`).
- **SC-007**: Nenhuma alteração de schema de banco (nenhuma migration) — a feature opera sobre a estrutura existente.

---

## 7. Escopo

### Incluído

- Geração automática de identificador `PROV-*` no cadastro de colaborador sem matrícula (web e caminhos de criação existentes);
- Marcação visual "provisória" nas exibições da matrícula viva;
- Substituição `PROV-*` → matrícula oficial no caminho de edição (mesmo colaborador, vínculos preservados);
- Proteções contra fabricação manual de `PROV-*` (interface e API);
- Testes dos cenários desta spec.

### Não incluído

- Importação CSV de colaboradores sem matrícula (a importação mantém a matrícula obrigatória, como hoje);
- Criação de coluna/tabela nova ou migration (o prefixo é o marcador da condição provisória);
- Qualquer mudança em autenticação, AD (regras de casamento), RBAC, permissões, tipos de movimentação, regras de movimentação, inventário, termos (estrutura), relatórios (estrutura), API (contratos além do mínimo para o comportamento novo);
- Reescrita de histórico/snapshots existentes;
- Conversão em lote de `PROV-*` → oficial (a substituição é colaborador a colaborador, no fluxo de edição existente);
- Numeração provisória para bens/locais (a feature é sobre colaboradores).

---

## 8. Casos de erro (comportamento definido)

| Situação | Comportamento |
|---|---|
| Tentativa de cadastrar com matrícula `PROV-*` digitada pelo usuário | Rejeitada — o usuário não fabrica identificador provisório (mensagem consistente com os padrões atuais do sistema; não definimos texto exato aqui, deixado para o plan alinhar com os erros existentes) |
| Matrícula oficial duplicada (existente) | Mantém-se o erro atual "Matrícula já cadastrada" |
| Colisão na geração do `PROV-*` (concorrência) | O registro não é gravado duplicado (constraint `UNIQUE`); a operação pode ser repetida e receberá o próximo número disponível |
| Falha durante a geração (ex.: banco indisponível) | Operação falha com erro padrão do sistema, sem gravar colaborador parcial; sem exposição de detalhe técnico sensível |
| Tentativa de substituir matrícula oficial por outro valor | Bloqueada como hoje (interface readonly para oficial; API segue as validações atuais) |
| Substituição com matrícula oficial já usada por outro colaborador | Erro existente "Matrícula já cadastrada" — sem perda de dados |
| Colaborador já com matrícula oficial recebe tentativa de provisório | Não aplicável — provisório só é gerado quando a matrícula não é informada |
| Informação de matrícula com espaços | Normalizada (trim) antes das validações |

---

## 9. Impacto esperado (componentes realmente afetados, pela análise)

| Componente | Alteração esperada |
|---|---|
| `app/services/custodian_service.py` | Geração do `PROV-*` no `create` quando a matrícula não é informada (padrão de geração inspirado no precedente `InventarioService.next_code`); validação anti-fabricação; substituição `PROV-*` → oficial no `update` já suportada pelo service |
| `app/schemas/custodian.py` | `registration_code` passa a aceitar ausência na criação (optional com default adequado) — apenas o caminho de criação |
| `app/web/routes.py` | Formulário web: matrícula opcional no cadastro (`Form(None)`); permitir a edição de matrícula **somente** quando for `PROV-*` (hoje é readonly sempre); auditoria já existente no caminho |
| `app/web/templates/custodians/form.html` | Campo de matrícula opcional (dica "deixe em branco para gerar identificador provisório"); em edição: editável apenas se `PROV-*` |
| Templates de exibição (list/detail de colaboradores, seleção em `movements/new.html`, `assets/*`, `movements/term.html`) | Marcação visual "provisória" onde a matrícula viva de colaborador provisório é exibida |
| `tests/` (arquivo novo) | Testes dos cenários das US1–US4 (geração, unicidade, concorrência, uso patrimonial, substituição com preservação de vínculos, anti-fabricação, não-regressão) |

**Não alterar** (explicitamente fora do impacto): models (zero DDL), `movement_service.py` (snapshots continuam sendo gravados como hoje — com o valor vigente no momento da operação), `inventario_service.py`, `ad_service.py`, `custodian_import_service.py`, API de relatórios, autenticação, RBAC, configuração.

*(Nenhuma decisão pendente que exija escolha do usuário foi identificada: o formato `PROV-000001` e a regra "prefixo como marcador, sem coluna nova" foram definidos pelo próprio input; a análise confirmou viabilidade sem DDL.)*

---

**FIM — Nesta etapa, somente esta `spec.md` foi criada. Nenhum código, teste, template, rota, schema de banco ou outro arquivo foi alterado.**
