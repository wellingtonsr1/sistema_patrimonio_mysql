# Feature Specification: Pesquisa de Colaboradores

**Feature Branch**: `006-pesquisa-colaboradores`
**Created**: 2026-09-16
**Status**: Draft

**Input**: "Adicionar um campo de pesquisa à tela existente de colaboradores/custodiantes, permitindo localizar rapidamente um colaborador sem percorrer manualmente a tabela. Pesquisa combinada (sem seleção de campo) por matrícula, nome, cargo, departamento e e-mail, com correspondência parcial e sem diferenciação de maiúsculas/minúsculas. Aproveitar a tabela e os dados já existentes; não criar nova tela, não alterar cadastro, colunas, links, contagem de bens, ações, permissões ou regras de negócio."

---

## 1. Contexto do Sistema Existente (análise verificada no código)

Esta feature **não é greenfield**. A análise do código confirmou os pontos que a spec manda identificar antes de alterar (Restrições §8) — todos verificados em 16/09/2026:

| Item exigido pela spec | Onde está | Evidência | Implicação para a feature |
|---|---|---|---|
| 1. Rota responsável pela tela | `app/web/routes.py` → `list_custodians_view` | `GET /custodians` com permissão `colaboradores.visualizar` (Constitution VI) | A pesquisa nasce dentro desta rota/desta permissão — nenhuma rota nova |
| 2. Template utilizado | `app/web/templates/custodians/list.html` | Tabela com colunas Matrícula, Nome, Cargo, Departamento, E-mail, Bens, Ações | O campo de pesquisa é acrescido acima da tabela existente; colunas intocadas |
| 3. Serviço/consulta da listagem | `app/services/custodian_service.py` → `get_all(db, active_only=False)` | Retorna a lista completa; a rota calcula `active_assets_count` por colaborador | Ponto único de consulta — **não criar segunda lógica** (RT-002) |
| 4. Mecanismo de paginação/filtro | **Não existe** — a tela carrega a lista completa, sem paginação server-side e sem filtro na tela | A rota itera `for c in custodians` sem `skip/limit`; o template não tem controle de busca | A pesquisa não precisa conviver com paginação existente (nenhuma há); o impacto de desempenho será avaliado durante o planejamento da implementação. |
| 5. Testes existentes da tela | **Não existe `tests/test_custodians.py`** — a cobertura de colaboradores está em `test_ad.py`, `test_rbac.py` e `test_custodian_import.py` | Verificado por grep em `tests/` (correção de referência feita durante o plan) | Devem continuar passando sem edição (Constitution VIII); nova cobertura em arquivo próprio |

**Conclusão da análise**: a pesquisa é uma **extensão de consulta** sobre a listagem existente — sem nova tela, sem nova entidade, sem alteração de modelo/banco, sem alteração de permissões. Como a tela hoje **carrega a lista completa sem paginação**, a solução deve seguir a arquitetura atual. Como a tela hoje carrega a lista completa sem paginação, o /speckit.plan deve avaliar o ponto adequado de execução do filtro (servidor ou cliente), considerando desempenho e crescimento da base. — nenhuma solução pode carregar desnecessariamente registros além do que a tela já carrega hoje.

**Padrão visual do sistema (Constitution X)**: outras telas do sistema já empregam campos de busca sobre tabelas com o texto orientativo no padrão "Pesquisar por..."; o campo deve seguir esse mesmo padrão visual (ícone de lupa, placeholder orientativo, mensagem de estado vazio).

---

## 2. User Scenarios & Testing

### User Story 1 - Localizar um colaborador rapidamente (Priority: P1)

Um operador do patrimônio precisa encontrar um colaborador específico na lista (ex.: para vincular um bem, conferir custódia ou acessar os detalhes). Hoje ele percorre a tabela com a barra de rolagem. Com a pesquisa, digita parte de qualquer dado exibido (matrícula, nome, cargo, departamento ou e-mail) e a tabela passa a mostrar somente os colaboradores correspondentes — sem escolher previamente em qual campo pesquisar.

**Why this priority**: é o valor central — eliminar a busca manual por rolagem.

**Independent Test**: com colaboradores cadastrados, informar um termo (parcial ou completo, em qualquer combinação de maiúsculas/minúsculas) e verificar que a tabela exibe somente os correspondentes, com todos os dados e ações existentes preservados.

**Acceptance Scenarios**:

1. **Given** colaboradores chamados "Amanda Silva Nunes" e "Amanda Teixeira Rodrigues", **When** o operador pesquisa `Amanda`, **Then** ambos aparecem nos resultados (e somente eles).

2. **Given** um colaborador com matrícula `MAT-1036`, **When** o operador pesquisa `MAT-1036` (ou parte dela), **Then** o colaborador correspondente é apresentado.

3. **Given** colaboradores com e-mails contendo `amanda.nunes36`, **When** o operador pesquisa esse trecho do e-mail, **Then** o colaborador correspondente é apresentado.

4. **Given** um colaborador no departamento "Comercial" e outro com cargo "Gerente de Contas", **When** o operador pesquisa `Comercial` e depois `Gerente`, **Then** cada pesquisa retorna os colaboradores correspondentes.

---

### User Story 2 - Pesquisa tolerante e com feedback claro (Priority: P2)

A pesquisa deve se comportar de forma previsível: não diferencia maiúsculas de minúsculas, aceita correspondência parcial e, quando nada corresponde, informa claramente que nenhum colaborador foi encontrado — sem erro na aplicação. Ao limpar o campo, a lista completa retorna.

**Why this priority**: qualidade da interação — evita frustração ("achei que não tinha cadastro") e garante recuperabilidade do estado.

**Independent Test**: pesquisar o mesmo termo em variações de caixa (`AMANDA`, `Amanda`, `amanda`) e verificar resultados equivalentes; pesquisar termo inexistente e verificar a mensagem "Nenhum colaborador encontrado."; limpar o campo e verificar o retorno da lista completa.

**Acceptance Scenarios**:

1. **Given** um colaborador chamado "Amanda Silva Nunes", **When** o operador pesquisa `AMANDA`, `Amanda` ou `amanda`, **Then** os resultados são equivalentes.

2. **Given** um colaborador chamado "Alexandre Carvalho Gomes", **When** o operador pesquisa `Alex`, **Then** o colaborador é encontrado (correspondência parcial).

3. **Given** nenhum colaborador correspondente ao termo, **When** a pesquisa é submetida, **Then** a tela apresenta claramente a mensagem "Nenhum colaborador encontrado." e a aplicação não apresenta erro.

4. **Given** uma pesquisa ativa, **When** o operador limpa o campo de pesquisa, **Then** a tabela volta a apresentar a lista completa de colaboradores.

---

### User Story 3 - Integridade da tela existente (Priority: P3)

A pesquisa é exclusivamente uma operação de consulta: nada é criado, alterado ou excluído. Todos os elementos existentes da tela permanecem funcionando exatamente como antes — links dos nomes para os detalhes, contagem de bens, ações disponíveis, colunas — e o acesso à pesquisa respeita a mesma permissão da tela (`colaboradores.visualizar`): ninguém encontra, pela pesquisa, um colaborador que não poderia visualizar.

**Why this priority**: proteção de não-regressão — a feature não pode custar nada ao que já funciona.

**Independent Test**: com a pesquisa implementada, exercitar os fluxos existentes da tela (abrir detalhes pelo nome, verificar contagem de bens, usar as ações) e comparar com o comportamento anterior; tentar pesquisar sem a permissão da tela e verificar o bloqueio existente.

**Acceptance Scenarios**:

1. **Given** um colaborador nos resultados da pesquisa, **When** o operador clica no nome, **Then** os detalhes do colaborador abrem normalmente, como antes.

2. **Given** um colaborador com bens vinculados, **When** ele aparece nos resultados, **Then** a contagem de bens exibida é a mesma de antes da feature.

3. **Given** um usuário sem a permissão de visualizar colaboradores, **When** ele tenta acessar a tela/pesquisa, **Then** o bloqueio existente continua valendo (a pesquisa não expõe nada além do que a tela já expõe).

4. **Given** a pesquisa em uso, **When** o operador realiza qualquer ação disponível na tabela, **Then** o comportamento existente é preservado (nenhuma ação nova ou removida).

---

## Edge Cases

* **Termo vazio ou só espaços**: equivale a sem pesquisa — lista completa (RF-011), sem mensagem de erro.

* **Termo com espaços nas extremidades**: tratado sem afetar o resultado (ex.: ` amanda ` encontra "Amanda Silva Nunes").

* **Colaborador ativo × inativo na pesquisa**: a lista atual da tela já reflete a regra existente de exibição de colaboradores; a pesquisa filtra sobre essa mesma lista — não amplia nem reduz o universo visível (RN-002).

* **Termo que corresponde a campos diferentes de colaboradores distintos** (ex.: "Silva" no nome de um, "silva" no departamento de outro): ambos aparecem — a pesquisa é combinada (RF-007).

* **Caracteres especiais no termo** (ex.: `%`, `_`, aspas): tratados como texto comum, sem provocar erro nem comportamento inesperado na consulta.

* **Muitos colaboradores**: a pesquisa continua utilizável com a base atual e crescente de colaboradores; o plano deve avaliar o ponto de execução do filtro (servidor ou cliente), considerando o desempenho e o crescimento da quantidade de colaboradores. (sem carregar mais dados no navegador do que a tela já carrega hoje).

---

## Requirements

### Functional Requirements

* **FR-001**: A tela de colaboradores DEVE apresentar um campo de pesquisa acima da tabela existente, com texto orientativo no formato "Pesquisar por matrícula, nome, cargo, departamento ou e-mail...".

* **FR-002**: A pesquisa DEVE localizar colaboradores pela **matrícula** (total ou parcial).

* **FR-003**: A pesquisa DEVE localizar colaboradores pelo **nome** (total ou parcial), incluindo nomes compostos (ex.: `Amanda` encontra "Amanda Silva Nunes" e "Amanda Teixeira Rodrigues").

* **FR-004**: A pesquisa DEVE localizar colaboradores pelo **cargo** (ex.: `Gerente` encontra "Gerente de Contas").

* **FR-005**: A pesquisa DEVE localizar colaboradores pelo **departamento** (ex.: `Comercial`).

* **FR-006**: A pesquisa DEVE localizar colaboradores pelo **e-mail** (total ou parcial, ex.: `amanda.nunes36`).

* **FR-007**: A pesquisa DEVE ser **combinada**: o termo é verificado em matrícula, nome, cargo, departamento e e-mail, sem que o usuário precise selecionar previamente o campo.

* **FR-008**: A pesquisa DEVE aceitar **correspondência parcial** (ex.: `Alex` encontra "Alexandre Carvalho Gomes").

* **FR-009**: A pesquisa NÃO DEVE diferenciar **maiúsculas de minúsculas** (`amanda`, `Amanda` e `AMANDA` produzem o mesmo resultado).

* **FR-010**: Quando nenhuma correspondência existir, a tela DEVE informar claramente "Nenhum colaborador encontrado." — sem erro na aplicação.

* **FR-011**: Ao **limpar** o campo de pesquisa, a tabela DEVE voltar a apresentar a lista completa de colaboradores (não há paginação existente na tela; caso o plano introduza algum filtro/paginação já existente, a limpeza deve retornar a esse estado-base).

* **FR-012**: Os resultados da pesquisa DEVEM apresentar **exatamente** os dados, colunas, links e ações já existentes na tabela — a pesquisa não modifica dados de colaboradores.

* **FR-013**: A pesquisa DEVE respeitar a mesma permissão da tela (`colaboradores.visualizar`) e o universo de colaboradores já visível ao usuário — não pode expor colaborador que o usuário não poderia ver (RN-002).

* **FR-014**: A solução DEVE reutilizar o serviço/consulta existente da listagem (`CustodianService`), sem criar segunda lógica de consulta de colaboradores (RT-002); a regra de filtragem, quando aplicada no servidor, concentra-se na camada de serviço (Constitution III).

* **FR-015**: A funcionalidade DEVE vir acompanhada de testes cobrindo, no mínimo: matrícula, nome, nome parcial, cargo, departamento, e-mail, case-insensibilidade, pesquisa combinada entre campos, nenhum resultado, limpeza da pesquisa, não-regressão da tela (links, contagem de bens, ações) e caracteres especiais no termo (sem erro); a preservação de permissões é verificada pela suíte RBAC existente e pelo spot-check manual do quickstart (nenhum gate novo é criado); os testes existentes de colaboradores DEVEM continuar passando sem modificações.

### Success Criteria

* **SC-001**: Um operador localiza qualquer colaborador da lista atual em menos de 10 segundos, digitando no máximo 1 termo — sem uso da barra de rolagem.

* **SC-002**: 100% das pesquisas por cada um dos 5 campos (matrícula, nome, cargo, departamento, e-mail) retornam o colaborador correspondente, nos formatos completo, parcial e com variação de caixa.

* **SC-003**: 100% das pesquisas sem correspondência exibem a mensagem "Nenhum colaborador encontrado." — zero erros de aplicação.

* **SC-004**: 100% dos elementos existentes da tela (links, contagem de bens, ações, colunas) funcionam após a pesquisa exatamente como antes (verificação por testes de não-regressão).

* **SC-005**: A permissão `colaboradores.visualizar` permanece o único requisito de acesso à tela com pesquisa — nenhum dado novo fica exposto sem a devida permissão.

* **SC-006**: A suíte de testes existente relacionada a colaboradores permanece 100% aprovada, sem modificações, e os novos testes da pesquisa são aprovados.

---

## Key Entities

* **Colaborador/Custodiante (Custodian)**: pessoa a quem a guarda de bens é atribuída. Atributos pesquisáveis: matrícula (`registration_code`), nome (`name`), cargo (`role`), departamento (`department`), e-mail (`email`). É a única entidade envolvida — nenhum atributo novo é criado e nenhum dado é modificado pela pesquisa.

* **Contagem de bens por colaborador**: valor exibido na tabela (`active_assets_count`), calculado pelo serviço existente; a pesquisa apenas preserva esse valor nos resultados.

---

## Assumptions

1. Não existe paginação server-side na tela hoje (verificado no código); caso o plano avalie introduzi-la por desempenho, isso será decisão documentada do `/speckit-plan`, não desta spec.

2. O universo de colaboradores pesquisáveis é o mesmo da listagem atual (a regra existente de exibição — ativos/inativos — permanece; a pesquisa não altera o universo visível).

3. Acentos: o comportamento de correspondência segue o mecanismo padrão do sistema; não é exigida normalização de acentos nesta feature (ex.: pesquisa por "Joao" encontrar "João" seria melhoria futura, registrada como tal).

4. A pesquisa não substitui nem duplica qualquer filtro de outros módulos; é específica da tela de colaboradores.

5. Documentação (central de ajuda, quando aplicável) será atualizada na mesma tarefa de implementação, conforme regra do projeto (Constitution XI).

6. Os testes novos seguirão os padrões existentes da suíte pytest do projeto.

---

## Out of Scope (não serão tratados nesta feature)

* Criar nova tela de colaboradores ou alterar o cadastro (criar/editar/excluir).

* Paginação server-side da tabela (avaliada no plano apenas se RT-003 comprovar necessidade; não é requisito desta feature).

* Normalização de acentos na comparação (ex.: "Joao" → "João").

* Pesquisa por atributos não exibidos na tabela (ex.: telefone, CPF, vínculo com usuário do sistema).

* Alteração de colunas, links, contagem de bens, ações, permissões, regras de negócio, detalhes do colaborador ou outras telas.

* Exportação/importação de dados.
