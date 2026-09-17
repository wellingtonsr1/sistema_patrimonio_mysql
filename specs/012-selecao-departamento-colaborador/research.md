# Research: Seleção de Departamento/Setor no Cadastro de Colaborador

**Feature**: 012-selecao-departamento-colaborador | **Data**: 2026-09-17
**Entrada**: spec.md (com clarificações da Sessão 2026-09-17) + análise de código verificada

> **Revisão 2026-09-17 (pós-feedback do usuário, antes de /speckit-tasks)**: as decisões **R1 e R2 foram revistas** — o usuário optou por **reutilizar `Location.department`** como fonte oficial (alternativa originalmente rejeitada), o que torna a **validação por texto** a única combinação coerente (não existe id de departamento para uma FK). Esta revisão substitui integralmente as decisões R1/R2 originais (tabela `departments` + coluna `department_id`), que permanecem documentadas como alternativa rejeitada. R3/R6/R7/R8/R9 foram rederivadas em cascata. Todas as consequências materiais estão quantificadas em cada decisão.

> Todas as decisões abaixo foram verificadas contra o código real (arquivos e linhas citados). Nenhuma biblioteca ou mecanismo novo é introduzido sem precedente no projeto.

---

## R1. Fonte oficial de Departamentos/Setores — REVISADA: reutilizar `Location.department`

- **Decision (revisada)**: A fonte oficial é a **lista dos valores distintos** de `Location.department` (`app/models/location.py` linha 18) — o departamento já cadastrado nos locais físicos do patrimônio. **Nenhuma tabela nova** é criada; a lista é derivada ao vivo (`SELECT DISTINCT department FROM locations`, precedentes: `app/web/routes.py` linhas 342, 406, 1806).
- **Rationale**: Decisão do usuário na revisão pós-plan. Vantagens: **zero estrutura nova** (concretiza AC-10 no limite — nada duplicado); **zero DDL** (Constitution VII no máximo); unifica o vocabulário do colaborador com o domínio que o **inventário já usa** como escopo (`InventarioService._scope_query` compara com `Location.department` — `app/services/inventario_service.py` linhas 94–101) e que os filtros de bens e o dashboard já exibem — pesquisa/filtro por setor passa a ser coerente entre colaboradores, bens e inventários.
- **Consequências aceitas (trade-offs honestos)**:
  1. **Grafias herdadas**: `Location.department` também é texto livre; a lista oficial herda eventuais duplicatas de grafia ("Setor de Suporte" × "setor de suporte"). A padronização dos **colaboradores** fica relativa aos valores de local (o objetivo central — impedir grafia livre no colaborador — é atendido; a limpeza das grafias dos **locais** é feature futura própria, backlog).
  2. **Ovo-galinha**: banco sem nenhum local cadastrado → lista vazia → formulário não tem opções (colaborador ainda pode ser criado pelos caminhos legados — R6). Registrado no quickstart como pré-condição operacional.
  3. **Sem conceito de ativo/inativo** em `Location` → a regra da clarificação Q3 (FR-015, bloqueio) fica **inoperante** nesta feature — a spec a tornou condicional à existência do conceito ("regra válida somente se a fonte oficial possuir conceito de ativo/inativo"). Documentado em R9.
- **Alternatives considered**:
  - *Tabela `departments` nova + carga idempotente* (decisão original R1) — **rejeitada nesta revisão** por opção do usuário; permanece como alternativa documentada caso os trade-offs 1–3 se revelem inaceitáveis na prática (feature futura pode introduzir o cadastro próprio sem retrabalho da UI — a camada `DepartmentService` isola a fonte).
  - *Lista fixa no HTML* — rejeitada: proibida pela spec (FR-001).
  - *Seed a partir de lista hard-coded* — rejeitada: FR-001 veta lista fixa; valores devem vir dos dados.

## R2. Vínculo do colaborador com a fonte oficial — REVISADA: validação por texto, sem coluna/FK nova

- **Decision (revisada)**: **Nenhuma coluna nova** em `Custodian`. A coluna textual `department` (String(100), NOT NULL) permanece como o único armazenamento, e a integridade é garantida por **validação do texto contra a lista oficial** no caminho do formulário (R7). **Model `Custodian` e schemas não mudam estruturalmente.**
- **Rationale**: Com a fonte derivada de `Location.department` (R1), não existe identificador estável para FK (o "registro oficial" é um valor, não uma linha endereçável). A padronização vem do **contrato da UI** (o campo só oferece valores oficiais) + **validação backend do valor selecionado** (FR-004 no caminho da seleção — R7). A coluna `department` já alimenta todos os consumidores (pesquisa 006 `CustodianService.get_all` ilike; `report_service.py` linha 439; `custodians/list.html`, `detail.html`, `reports/custodians_report.html`, `movements/term.html`, `assets/form.html`, `movements/new.html`) — zero alteração neles.
- **Consequências aceitas**: sem FK, um valor oficial pode "perder a referência" se TODOS os locais daquele departamento forem removidos/renomeados (o colaborador mantém o texto gravado — histórico intacto; a edição com submissão idêntica ao valor vigente é aceita sem re-normalização — remediação I2, opção b — e a re-seleção só é exigida se o usuário submeter valor diferente). Integridade é **de validação**, não **referencial** — weaker que a alternativa original; aceito pela decisão de revisão.
- **Alternatives considered**:
  - *FK `department_id` → tabela `departments`* (decisão original R2) — incoerente com R1 revista (não há tabela); rejeitada em cascata.
  - *FK para `locations`* — sem sentido de domínio (colaborador não aponta para um local).
  - *Validar por id de local* — não representaria departamento (vários locais compartilham o mesmo valor).

## R3. Migração de schema — REVISADA: ZERO DDL

- **Decision (revisada)**: **Nenhuma alteração de schema**. Nenhuma tabela nova, nenhuma coluna nova, nenhum `ALTER`. `app/database.py` e `tests/conftest.py` não são tocados.
- **Rationale**: Com R1/R2 revisadas, não há estrutura a criar. Constitution VII fica satisfeita no grau máximo (nenhuma alteração estrutural, nem mesmo aditiva) e o risco de migração desaparece (nada a migrar, nada a reverter).
- **Alternatives considered**: as da R1/R2 originais (`create_all` para tabela, `ADD COLUMN IF NOT EXISTS` para coluna) — obsoletas sob a revisão.

## R4. Superfície de acesso à lista oficial — server-side (inalterada da versão original)

- **Decision**: A lista oficial chega ao formulário **embutida server-side** no render de `/custodians/new` e `/custodians/{id}/edit` (`form_new_custodian`/`form_edit_custodian` consultam `DepartmentService.list_official` e injetam no template). **Nenhum endpoint/rota nova**.
- **Rationale**: Igual à versão original: herda as permissões das páginas (`colaboradores.criar` linha 887 / `colaboradores.editar` linha 937 — Constitution VI) sem superfície de acesso nova; volume (dezenas/centenas de valores distintos) é compatível com server-side rendering; precedentes de selects server-rendered (`assets/form.html`, `inventarios/new.html`).
- **Alternatives considered**: endpoint REST novo e permissão nova — rejeitados (mesmos motivos da versão original: escopo/RBAC).

## R5. UX da seleção — campo de seleção (dropdown) nativo (**REVISADA em 2026-09-17**)

- **Decision (revisada — decisão do usuário durante a implementação)**: **`<select class="form-select">` nativo** com a lista oficial, option vazia "— Selecione —" e valor vigente pré-selecionado na edição. **Sem datalist, sem campo de pesquisa, sem digitação** — o Cenário 4 do briefing ("pesquisar parte do nome") fica suplantado: a lista completa é apresentada no dropdown. Sem dependência externa (Princípio X).
- **Supersede**: a opção `<input list>` + `<datalist>` da versão original desta decisão **não é implementada**; a lista é fixa no controle e a criação por digitação é estruturalmente impossível (FR-002 reforçado).
- **Alternatives considered**: datalist com filtro de digitação — rejeitada pelo usuário (complexidade desnecessária para o caso de uso); bibliotecas externas (Select2/TomSelect) — vetadas desde a versão original.
- **Rationale**: idêntica à versão original (spec FR-002, Constitution X, precedentes). Com fonte derivada (R1), o conjunto de opções tende a ser pequeno/médio → `<select>` nativo simples provavelmente basta; a tasks decidirá pela contagem real.

## R6. Compatibilidade da suíte de testes — REVISADA: caminho legado preservado + modo estrito opt-in do formulário

- **Decision (revisada)**: A validação contra a lista oficial aplica-se **apenas ao caminho do formulário** (que passa a enviar o marcador `department_source=official` — hidden input da nova UI, contract UI §4). Todos os demais caminhos (API create, importação CSV, chamadas diretas ao service) **mantêm o comportamento atual**: texto livre obrigatório não vazio, sem consulta à lista.
- **Rationale (quantificado)**: A suíte existente cria colaboradores com textos arbitrários em **28 chamadas** a `CustodianService.create` (`test_custodian_import.py`, `test_custodian_provisional.py`, `test_custodians_search.py`, `test_movements.py`), **10 POSTs** de API (`test_api.py` ×5, `test_custodian_import.py` ×1, `test_custodian_provisional.py` ×2, `test_rbac.py` ×2) e **6 POSTs web** (`test_custodian_provisional.py`) — com `"TI"`, `"D"`, `"RH"`, `"R"`, `"Comercial"`, `"UX"` etc. e **sem** local de departamento correspondente no banco por-teste (fixture `db_session` é function-scoped: `create_all`/`drop_all` por teste). Validação estrita em todos os caminhos **quebraria dezenas de testes** (Constitution VIII veda editá-los). O modo estrito opt-in resolve: testes antigos (sem marcador) seguem no caminho legado; os testes **novos** da feature exercitam o caminho do formulário com marcador.
- **Consequência aceita (residual risk — registrado)**: AC-04 é garantido **no caminho da seleção** (formulário — o alvo da feature). Uma chamada forjada à API/serviço sem o marcador ainda grava texto arbitrário — o que **já é o comportamento vigente** desses caminhos (preservado por FR-012 e pela Seção 8 da spec: importação CSV fora do escopo). O briefing mira o formulário ("usuário não consegue criar denomininação digitando"); a API permanece como está hoje.
- **Alternatives considered**:
  - *Validação estrita universal (API+CSV+service)* — rejeitada: quebra ~44 call sites de teste existentes (Constitution VIII) e muda contratos vigentes (FR-012).
  - *Editar os testes existentes para criar locais antes* — rejeitada: Constitution VIII.

## R7. Validação no backend — REVISADA: regra no service, invocada pelo caminho do formulário

- **Decision (revisada)**: `DepartmentService.ensure_official(db, department: str) -> str` — normaliza (trim) e verifica se o valor **consta na lista oficial** (`Location.department` distintos, comparação case-insensitive para rejeitar "setor de suporte" quando só existe "Setor de Suporte"? **Não** — a comparação é case-insensitive e aceita variações de caixa que correspondam a um único valor oficial, gravando a forma canônica oficial; se o texto não corresponder a nenhum valor oficial → `ValueError("Departamento/Setor inválido — selecione um registro da lista oficial")`). As rotas web `create_custodian_form`/`update_custodian_form` chamam `ensure_official` **quando `department_source == "official"`** e passam o valor canônico ao `CustodianService` (que permanece **intocado**).
- **Rationale**: A regra vive em service (Constitution III — a rota delega a validação, não a implementa); `CustodianService` e todos os seus consumidores ficam intocados (R6); obrigatoriedade FR-003: o formulário exige seleção e `department` vazio é rejeitado pelo `Form(...)` obrigatório + validação existente do service (`CustodianCreate.department: str` — Pydantic 422 no legado; no formulário, empty string cai no erro do service "obrigatório" já verificável). Normalização para a forma canônica oficial elimina divergências de caixa ("SUPORTE" → grava "Setor de Suporte" oficial).
- **Alternatives considered**: validação dentro de `CustodianService.create` — rejeitada: aplicaria a regra a CSV/API/legado (R6); duplicaria a regra com flag extra no service.

## R8. Gestão dos registros oficiais — REVISADA: lista derivada ao vivo, sem seed

- **Decision (revisada)**: **Não há rotina de seed** nem cadastro de departamentos. A lista oficial é **derivada ao vivo** dos valores distintos de `locations.department` a cada render do formulário (consulta barata, precedente nas linhas 342/406/1806 de `routes.py`). Novos valores oficiais surgem naturalmente ao cadastrar/editar **locais** (fluxo existente, permissão `locais.criar`) — nenhum mecanismo novo é criado.
- **Rationale**: Fonte derivada não precisa de carga (R1); CRUD administrativo de departamentos segue fora do escopo (spec Seção 8); o "cadastro oficial" de um departamento novo passa a ser o cadastro/edição de um local — processo já existente e permissionado.
- **Alternatives considered**: seed idempotente de `departments` (versão original R8) — obsoleta sob R1 revista.

## R9. Regra de inativos (clarificação Q3) — REVISADA: inoperante nesta fonte

- **Decision (revisada)**: Nada é implementado para inativação: `Location` não possui conceito ativo/inativo/arquivado, e a spec tornou FR-015 **condicional** ("regra válida somente se a fonte oficial possuir conceito de ativo/inativo"). Com a fonte revista (R1), a condição não se verifica → **a regra de bloqueio não existe nesta feature**. A lista oficial exibe todos os valores distintos vigentes; registros "inutilizáveis" (R2: valor sem nenhum local correspondente) simplesmente não aparecem na lista — colaboradores que os carregam mantêm o texto gravado; a edição aceita a submissão do valor vigente sem re-normalização (remediação I2, opção b), exigindo re-seleção apenas para valor diferente.
- **Rationale**: Fidelidade à clarificação Q3 (que previa a condicional) e à Constitution I (não inventar mecanismo fora do escopo). Se a feature futura de limpeza/padronização de locais introduzir ativo/inativo, a regra Q3 poderá ser ativada numa camada própria.
- **Alternatives considered**: criar `is_active` em `Location` — rejeitado: altera Localização (FR-009 veda) e amplia escopo.

## R10. O que NÃO é tocado (verificação de escopo — reforçada pela revisão)

- **Decision**: Intocados nesta feature: `app/models/` **inteiro** (zero DDL — R3), `app/database.py`, `location_service.py`, `location_import_service.py`, `movement_service.py`, `inventario_service.py`, `ad_service.py`, `custodian_import_service.py`, `custodian_service.py` (R7 — service do colaborador permanece igual!), relatórios (estrutura), autenticação/RBAC/sessões, `static/js/main.js` (filtro JS opcional), API de colaboradores (R6 — contratos inalterados).
- **Rationale**: Sob a revisão, o raio de arquivos alterados **encolhe**: templates `custodians/form.html`, rotas web (4 handlers: 2 GET injetam lista; 2 POST validam com marcador), `department_service.py` (novo, leitura/validação), testes novos. Nenhum model, schema, API ou service existente é alterado.
- **Alternatives considered**: n/a — delimitação de escopo.

---

## Comparativo da decisão de revisão (transparência)

| Critério | Original (tabela `departments` + `department_id`) | **Revisado (reusar `Location.department`)** |
|---|---|---|
| DDL | Tabela nova + coluna nova | **Zero** |
| Integridade | Referencial (FK) | De validação (texto no caminho do formulário) |
| Grafias duplicadas na lista | Eliminadas pela carga canônica | **Herdadas dos locais** (limpeza é feature futura) |
| Q3 (inativos) | Operacional (`is_active` novo) | Inoperante (fonte sem conceito) |
| Suíte existente | Verde (caminho legado) | Verde (caminho legado) |
| Coerência com inventário/bens | Indireta | **Direta** (mesmo vocabulário de `Location.department`) |
| AC-10 (não duplicar estrutura) | Com ressalva (nova entidade) | **Máximo** (reutiliza a existente) |
