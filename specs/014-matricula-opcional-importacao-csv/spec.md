# Feature Specification: Matrícula Opcional na Importação de Colaboradores via CSV

**Feature Branch**: `014-matricula-opcional-importacao-csv`

**Created**: 2026-09-17

**Status**: Draft

**Input**: Tornar a coluna `matricula` opcional na importação de colaboradores via CSV, aplicando a mesma regra já existente no cadastro individual (feature 010): matrícula informada → usada com as validações atuais; matrícula ausente/vazia/só espaços/coluna ausente → geração automática de matrícula provisória reutilizando EXATAMENTE a implementação existente. Nenhuma outra regra, validação, transação ou funcionalidade pode ser alterada.

---

## 1. Contexto e análise do sistema atual (somente leitura, verificada nesta especificação)

Fatos confirmados no código — nenhum nome abaixo é presumido:

| # | Ponto investigado | Realidade atual verificada |
|---|---|---|
| 1 | Regra da feature 010 (cadastro individual) | Implementada e funcionando: `CustodianService.create` (feature 010) aceita `registration_code` opcional; vazio/ausente → `_next_provisional_code(db)` gera `PROV-%06d`; `is_provisional()` verifica pelo prefixo `PROV-` (case-insensitive); anti-fabricação rejeita valores informados iniciados por `PROV-` |
| 2 | Mecanismo de geração | `CustodianService._next_provisional_code(db)` (estático, privado): maior `PROV-` BEM-FORMADO existente + 1 (precedente `InventarioService.next_code`); ignora prefixos malformados; constraint UNIQUE de `registration_code` como garantia final; loop curto de retentativa (5x) em caso de colisão concorrente |
| 3 | Unicidade/concorrência | Garantida por: consulta do maior sequencial + verificação de existência + UNIQUE constraint + retentativa — estratégia do cadastro individual, a ser REUTILIZADA (não reescrita) |
| 4 | Onde a importação assume obrigatoriedade | `app/services/custodian_import_service.py` — `_validate_row` linha ~120: `if not row.get("registration_code", "").strip(): errors.append("Linha N: matricula é obrigatória")` → linha sem matrícula nem entra nas rows válidas do preview/execução |
| 5 | Fluxo completo do importador | 3 estágios: `parse_custodian_csv(content)` → valida linhas (aqui está o erro de obrigatoriedade); `preview_custodian_import(rows, db)` → duplicatas por matrícula/e-mail (não valida obrigatoriedade); `execute_custodian_import(rows, db, skip_duplicates)` → cria/atualiza diretamente via modelo `Custodian` (**NÃO** passa por `CustodianService.create` — por isso não herda a geração de PROV) |
| 6 | Transporte entre estágios | Preview renderiza os rows e o formulário de confirmação serializa `csv_rows` como JSON num campo oculto (`csv_data`), reparseado em `confirm_import_custodians` — a matrícula (ou sua ausência) viaja textualmente entre os estágios |
| 7 | Regras existentes a preservar | Normalização `_normalize_registration_code` (trim + upper); duplicidade por matrícula/e-mail com regra `skip_duplicates` (pular) vs atualização in-place; e-mail duplicado → erro/skip; commit parcial com erros reportados — TODOS preservados |
| 8 | Documentação do fluxo | `app/web/templates/custodians/import.html` linha 247: "colunas `matricula`, `nome`, `email`, `cargo` e `setor` são **obrigatórias**"; tabela de colunas (linha ~261) marca `matricula` com badge "Sim" (vermelho); exemplo de CSV (linha ~308) começa com `matricula;...` |
| 9 | Testes existentes | `tests/test_custodian_import.py`: `test_parse_custodian_csv_reports_missing_required_fields` **asserta o erro atual** ("matricula é obrigatória") — precisará de ajuste pontual (única edição permitida em teste existente, cobre comportamento diretamente alterado pela especificação); demais testes (Cenários de criação, duplicatas, preview, API e web E2E) usam matrículas informadas e não devem ser tocados |
| 10 | Spec 010 | Registrou explicitamente a importação como "não incluído" (matrícula obrigatória mantida) — esta feature fecha essa lacuna de consistência |
| 11 | Documentação externa | `docs/doc_proviśorios/docs_para_testes/colaboradores.csv` (arquivo de teste do usuário) contém a coluna matricula; README/help não documentam as colunas do importador — documentação alvo é a tela de importação |

**Consequências da análise** (refletidas nos requisitos): a inconsistência está localizada em **um único ponto de validação** (`_validate_row`) e na criação direta por modelo em `execute_custodian_import` (que contorna o service). A correção mínima remove a obrigatoriedade da validação e delega a geração da provisória ao mecanismo existente (`_next_provisional_code`), sem tocar cadastro individual, AD ou demais fluxos; o endpoint REST de importação (`POST /api/v1/custodians/import/csv`, verificado em `app/api/custodians_api.py`) consome os mesmos services e herda a nova regra sem alteração de código.

---

## 2. Problema e objetivo

### Problema

A importação CSV de colaboradores exige `matricula`, enquanto o cadastro individual (feature 010) a tornou opcional com geração automática de `PROV-*`. O mesmo dado cadastral tem regras diferentes conforme o canal de entrada — linhas sem matrícula são rejeitadas na importação mesmo sendo válidas no cadastro individual.

### Objetivo

Na importação CSV de colaboradores, `matricula` passa a ser opcional (informada, vazia, só espaços ou coluna inteiramente ausente), gerando matrícula provisória automaticamente — pela mesma implementação do cadastro individual — para os casos de ausência, preservando integralmente todas as demais regras do importador.

---

## 3. Princípio fundamental — reutilizar, não duplicar

- A geração de matrícula provisória é **uma só** no sistema: a do cadastro individual (feature 010). A importação passa a consumi-la — **nada de segunda implementação**, contagem paralela ou formato divergente.
- A regra é **por linha**: cada colaborador da mesma importação é tratado independentemente (informada → usada; ausente → provisória).
- **Zero mudança nas regras para matrículas informadas**: normalização, validação, unicidade, duplicidade, mensagens, transação e rollback permanecem como estão.

---

## 4. User Scenarios & Testing

### User Story 1 — Importar colaborador sem matrícula e receber matrícula provisória (Priority: P1) 🎯 MVP

Um usuário prepara um CSV onde algumas linhas não têm matrícula (célula vazia, só espaços ou coluna ausente) e importa normalmente — o sistema gera a provisória de cada linha ausente com a mesma regra do cadastro individual.

**Why this priority**: É a correção central da inconsistência entre os dois canais.

**Independent Test**: CSV com matrícula vazia → importação sem erro de matrícula; colaborador criado com `PROV-` gerado; CSV com coluna ausente → todos recebem `PROV-`.

**Acceptance Scenarios**:

1. **Given** um CSV com célula de matrícula vazia, **When** importado, **Then** o colaborador é criado com matrícula provisória e a importação NÃO reporta erro de matrícula ausente (Teste 2 do briefing).
2. **Given** um CSV com matrícula contendo somente espaços, **When** importado, **Then** é tratado como não informada — provisória gerada (Teste 3).
3. **Given** um CSV **sem a coluna `matricula`**, **When** importado, **Then** a importação continua válida e todos os colaboradores recebem matrícula provisória (Teste 4; exemplo do briefing "Nome,Departamento,Setor").
4. **Given** um CSV com matrículas informadas e ausentes **na mesma importação**, **When** importado, **Then** informadas mantêm o valor e ausentes recebem provisórias — todos os registros válidos importados (importação mista, Teste 5).

### User Story 2 — Regras de matrícula informada preservadas (Priority: P1)

**Independent Test**: CSV com matrícula válida, duplicada e inválida → comportamentos idênticos aos atuais (Testes 1, 6).

**Acceptance Scenarios**:

1. **Given** matrícula informada e válida, **When** importada, **Then** é utilizada como está (normalização atual: trim + upper) e NÃO é gerada provisória (Teste 1).
2. **Given** matrícula informada que já existe no banco, **When** importada, **Then** aplica-se EXATAMENTE a regra atual de duplicidade (skip ou atualização conforme `skip_duplicates`) — nunca substituição silenciosa por provisória (Teste 6).
3. **Given** matrícula informada inválida (ex.: iniciada por `PROV-`), **When** importada, **Then** aplica-se a regra atual de validação existente para esse caso (sem nova regra nesta feature — ver Edge Cases).

### User Story 3 — Unicidade das provisórias na mesma importação (Priority: P1)

**Independent Test**: CSV com várias linhas sem matrícula → cada colaborador recebe uma `PROV-` distinta (Teste 7).

**Acceptance Scenarios**:

1. **Given** várias linhas sem matrícula na mesma importação, **When** executada, **Then** cada colaborador recebe sua própria provisória sequencial única — nenhuma duplicada.
2. **Given** a geração concorrente (dois processos simultâneos), **When** colidir, **Then** vale o mecanismo já existente no cadastro individual (constraint UNIQUE + retentativa) — reutilizado sem reescrita (ver Edge Cases sobre concorrência).

### User Story 4 — Preview e documentação coerentes (Priority: P2)

**Independent Test**: Linha sem matrícula no preview não aparece como erro; documentação da tela de importação marca `matricula` como opcional com a nova regra.

**Acceptance Scenarios**:

1. **Given** o preview da importação, **When** uma linha não tem matrícula, **Then** NÃO aparece como erro de obrigatoriedade; o preview PODE indicar que será gerada provisória (sinalização permissiva — remediação I1) — sem inventar antecipadamente um número diferente do que será efetivamente criado.
2. **Given** a tela de importação, **When** o usuário consulta a documentação das colunas, **Then** `matricula` aparece como opcional: "Se informada, será utilizada. Quando não informada, o sistema gerará automaticamente uma matrícula provisória, seguindo a mesma regra do cadastro individual."

### Edge Cases

- **Matrícula informada com prefixo `PROV-`** (anti-fabricação): o cadastro individual rejeita valores informados iniciados por `PROV-`. Na importação, o comportamento atual para esse caso NÃO possui validação específica — esta feature não cria nova regra de validação além da geração por ausência; qualquer lacuna existente é documentada na análise (Seção 1) para avaliação futura, sem expandir o escopo.
- **Concorrência/unicidade**: a geração reutiliza o mecanismo do cadastro individual (sequencial + UNIQUE + retentativa). Caso a implementação atual apresente vulnerabilidade de concorrência, esta feature NÃO a corrige — documenta e mantém o escopo controlado (diretriz do briefing).
- **Colunas extras no CSV**: continuam ignoradas, como hoje.
- **Duplicidade de e-mail**: regra atual (erro/skip conforme `skip_duplicates`) preservada — a geração de provisória não altera o tratamento de e-mail.
- **Linhas com outros erros** (nome/e-mail/cargo/setor inválidos): continuam rejeitadas como hoje — a ausência de matrícula deixou de ser erro, as demais validações permanecem.

---

## 5. Requirements

### Functional Requirements

- **FR-001**: A coluna `matricula` do CSV DEVE deixar de ser obrigatória: a ausência (célula vazia, somente espaços ou coluna inexistente) NÃO DEVE gerar erro nem rejeitar a linha (AC-01, AC-02, AC-03).
- **FR-002**: Para cada linha sem matrícula, o sistema DEVE gerar automaticamente uma matrícula provisória REUTILIZANDO a mesma implementação (serviço/função/mecanismo) do cadastro individual — é PROIBIDO criar segunda implementação, contagem paralela ou formato divergente (AC-05).
- **FR-003**: Matrícula informada e válida DEVE ser utilizada normalmente (normalização e validações atuais), sem geração de provisória (AC-04).
- **FR-004**: Matrícula informada duplicada DEVE continuar obedecendo EXATAMENTE à regra atual de duplicidade do importador (skip/atualização conforme `skip_duplicates`), nunca substituída silenciosamente por provisória (AC-06).
- **FR-005**: A mesma importação DEVE aceitar linhas com e sem matrícula (importação mista), tratando cada linha individualmente (AC-07).
- **FR-006**: Cada colaborador sem matrícula DEVE receber uma matrícula provisória ÚNICA — nenhuma provisória duplicada dentro da mesma importação (AC-08).
- **FR-007**: O preview/validação NÃO DEVE tratar matrícula ausente como erro; se exibir informação de matrícula, PODE indicar que será gerada provisória (o briefing diz "poderá indicar" — remediação I1: obrigatoriedade revertida para permissiva), sem fabricar antecipadamente um número diferente do efetivamente criado (AC-09).
- **FR-008**: Nenhuma validação existente para matrículas informadas DEVE ser eliminada: válida → aceitar; duplicada → regra atual; inválida → regra atual; a única mudança de regra é "ausência deixou de ser erro" (AC-06).
- **FR-009**: Nenhum DDL/migração/modelo DEVE ser alterado — a infraestrutura atual já suporta matrícula provisória (feature 010 em produção).
- **FR-010**: O comportamento do cadastro individual, a regra de matrícula provisória existente, outros importadores e demais módulos NÃO DEVEM ser alterados (AC-11).
- **FR-011**: A documentação do fluxo de importação (tela `custodians/import.html` e afins) DEVE ser atualizada: `matricula` opcional — "Se informada, será utilizada. Quando não informada, o sistema gerará automaticamente uma matrícula provisória, seguindo a mesma regra do cadastro individual." (AC-10).
- **FR-012**: Os testes dos 8 cenários do briefing DEVEM existir e passar; os testes existentes relacionados a colaboradores/importação DEVEM continuar passando (com o ajuste pontual do teste que asserta o erro hoje existente — comportamento diretamente alterado por esta especificação) (AC-10, AC-11).

### Regras (síntese operacional)

- R1 — Ausência de matrícula ≠ erro → provisória (FR-001/FR-002).
- R2 — Informada → usada com todas as regras atuais (FR-003/FR-004/FR-008).
- R3 — Uma só implementação de geração de provisória no sistema (FR-002).
- R4 — Zero mudança fora do importador de colaboradores (FR-009/FR-010).

### Key Entities

- **`app/services/custodian_import_service.py`**: único service alterado — `_validate_row` (remove a obrigatoriedade de `registration_code`), `execute_custodian_import` (linha sem matrícula → geração via mecanismo existente antes de criar), `preview_custodian_import` (linha sem matrícula permanece listada, sem busca por matrícula vazia, com a flag `will_generate_provisional` disponível como sinalização — sem mudança visual obrigatória; remediação I1).
- **`CustodianService._next_provisional_code`** (existente, feature 010): REUTILIZADO como gerador único — torná-lo consumível pelo importador (ex.: método público de fachada ou chamada direta ao estático) é a extensão mínima permitida; sua lógica interna NÃO muda.
- **`app/web/templates/custodians/import.html`**: documentação da tela (badge obrigatória → opcional + regra; exemplo de CSV).
- **`tests/test_custodian_import.py`**: ajuste pontual do teste que asserta "matricula é obrigatória" (comportamento alterado) + novos testes dos cenários do briefing.
- **`CustodianService.create`/`update`, API REST, AD, modelos, migrations**: INTOCADOS (o endpoint REST de importação existente herda a regra pelos services compartilhados — zero alteração de código).

---

## 6. Critérios de Aceitação (rastreabilidade)

| AC | Enunciado (checklist do briefing) | Coberto por |
|---|---|---|
| AC-01 | `matricula` não é mais obrigatória no CSV | US1/AS1; FR-001 |
| AC-02 | CSV sem a coluna `matricula` pode ser importado | US1/AS3; FR-001 |
| AC-03 | Célula vazia/espaços tratados como ausência | US1/AS1, AS2; FR-001 |
| AC-04 | Matrícula informada funciona normalmente | US2/AS1; FR-003 |
| AC-05 | Provisórias geradas pela mesma lógica do cadastro individual | US1/AS1; FR-002 |
| AC-06 | Duplicadas obedecem à regra atual (e demais validações preservadas) | US2/AS2; FR-004/FR-008 |
| AC-07 | Importação mista (com/sem matrícula) funciona | US1/AS4; FR-005 |
| AC-08 | Cada sem-matrícula recebe provisória única | US3/AS1; FR-006 |
| AC-09 | Preview não trata ausência como erro; sinalização de provisória permissiva, sem fabricar número (remediação I1) | US4/AS1; FR-007 |
| AC-10 | Testes criados/ajustados e existentes passando; documentação atualizada | US4/AS2; FR-011/FR-012 |
| AC-11 | Nenhuma funcionalidade fora do escopo alterada | US4; FR-010 |

### Cenários de teste do briefing (mapa)

| Teste | Cenário | Onde |
|---|---|---|
| 1 | Matrícula informada → usada, não provisória | US2/AS1 |
| 2 | Vazia → provisória, sem erro | US1/AS1 |
| 3 | Só espaços → provisória | US1/AS2 |
| 4 | Coluna ausente → importação válida, todos com provisória | US1/AS3 |
| 5 | Mista → informadas + provisórias juntos | US1/AS4 |
| 6 | Duplicada informada → regra atual, sem substituição | US2/AS2 |
| 7 | Várias sem matrícula → provisórias únicas | US3/AS1 |
| 8 | Regressão da suíte existente | FR-012 / Polish |

---

## 7. Success Criteria

- **SC-001**: 100% dos 8 cenários de teste do briefing cobertos por testes e passando.
- **SC-002**: Zero erro de "matricula é obrigatória" na importação — a ausência gera provisória em todos os caminhos (parse/preview/execução, web e API).
- **SC-003**: Toda provisória gerada pela importação segue o formato e o mecanismo do cadastro individual (mesma função geradora; zero contagem paralela no código).
- **SC-004**: Comportamento das matrículas informadas byte-a-byte igual ao atual (duplicidade, normalização, validações).
- **SC-005**: Suíte existente verde (única edição permitida: o teste que asserta o erro removido — comportamento alterado pela spec).
- **SC-006**: `git diff` restrito a: `custodian_import_service.py`, fachada mínima de `custodian_service.py` (se necessária para expor o gerador), `import.html` (documentação) e testes.

---

## 8. Escopo

### Incluído

- Opcionalidade de `matricula` no importador CSV (validação, preview e execução);
- Geração de provisória reutilizando o mecanismo existente do cadastro individual;
- Unicidade das provisórias dentro da mesma importação;
- Sinalização de provisória no preview, quando presente (flag `will_generate_provisional` disponível; sem fabricar número) — remediação I1;
- Documentação da tela de importação;
- Testes dos 8 cenários + ajuste pontual do teste do erro removido.

### Não incluído (limites de escopo)

- Cadastro individual, API REST de colaboradores, AD, regra de matrícula provisória existente (somente reutilizada);
- Outros importadores (equipamentos, locais), demais módulos (patrimônio, inventário, usuários, RBAC, departamentos/setores/cargos);
- DDL, migrations, alterações de modelo;
- Correção de eventuais vulnerabilidades de concorrência do gerador atual (documentadas, não corrigidas — diretriz do briefing);
- Refatoração geral do importador ou do service.

---

## 9. Casos de erro (comportamento definido)

| Situação | Comportamento |
|---|---|
| Matrícula vazia/espaços/ausente | Gera provisória (mesma lógica do cadastro individual) — sem erro |
| Matrícula informada duplicada | Regra atual do importador (skip ou atualização conforme `skip_duplicates`) |
| Matrícula informada inválida | Regra atual de validação existente (sem nova regra nesta feature) |
| E-mail duplicado | Regra atual (erro/skip) — inalterada |
| Linha com outros campos obrigatórios ausentes | Continua rejeitada (nome/e-mail/cargo/setor seguem obrigatórios) |
| Duas linhas sem matrícula na mesma importação | Cada uma recebe provisória única (sequencial do mecanismo existente) |

---

## 10. Premissas e dependências

- A feature 010 está em produção e seu mecanismo de geração é estável (o importador o consome como caixa-preta).
- A coluna `matricula` continua aceita (opcional ≠ removida); CSVs atuais com matrícula continuam importando identicamente.
- A sinalização no preview, quando presente, é textual ("Será gerada matrícula provisória") — o número só existe na execução, evitando fabricar valor divergente; a flag `will_generate_provisional` fica disponível no dict de preview para uso de UI, presente ou futuro (remediação I1).

---

## 11. Impacto esperado (componentes confirmados pela análise — nada inventado)

| Arquivo | Alteração esperada |
|---|---|
| `app/services/custodian_import_service.py` | `_validate_row`: remover a regra de obrigatoriedade de `registration_code`; `preview_custodian_import`: indicar provisória quando ausente; `execute_custodian_import`: quando ausente, gerar via mecanismo existente antes de criar |
| `app/services/custodian_service.py` | Somente se necessário: fachada pública mínima para o importador consumir `_next_provisional_code` (lógica interna intocada) |
| `app/web/templates/custodians/import.html` | Documentação: `matricula` opcional + regra de geração; ajuste do exemplo de CSV |
| `tests/test_custodian_import.py` | Ajuste do teste que asserta "matricula é obrigatória" (comportamento alterado) + novos testes dos 8 cenários |
| Cadastro individual, API, AD, modelos, migrations, outros importadores | **NÃO alterados** |

**Causa da inconsistência (resumo)**: a feature 010 tornou a matrícula opcional apenas no `CustodianService.create` (web/API), mas o importador CSV valida a obrigatoriedade em `_validate_row` e cria colaboradores diretamente pelo modelo (sem passar pelo service) — dois pontos que perpetuam a regra antiga no canal CSV.

---

## 12. Premissas registradas

- O formato `PROV-%06d` e a regra de unicidade atuais são mantidos como estão (inclusive eventuais limitações de concorrência — documentadas, não corrigidas aqui).
- "Matrícula válida" quando informada segue as validações já existentes no importador (normalização trim+upper e unicidade) — nenhuma validação nova é adicionada nesta feature.

---

*Esta especificação documenta a análise somente-leitura exigida pelo PROCEDIMENTO DE IMPLEMENTAÇÃO do briefing (arquivos envolvidos, causa da inconsistência e solução proposta) antes de qualquer alteração. Nada foi implementado nesta etapa; a implementação ocorrerá no fluxo seguinte (/speckit-plan → /speckit-tasks → /speckit-implement), restrita aos arquivos listados na Seção 11.*
