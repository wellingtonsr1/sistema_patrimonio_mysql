# Tasks: Pesquisa de Colaboradores

**Input**: Design documents from `/specs/006-pesquisa-colaboradores/`

**Prerequisites**: plan.md (✅), spec.md (✅), research.md (✅ R1–R6), data-model.md (✅), contracts/web-search-contract.md (✅), quickstart.md (✅)

**Tests**: **Testes são requisito desta feature** (spec FR-015; Constitution VIII). Novo arquivo `tests/test_custodians_search.py`, escrito **antes** da implementação de cada story (TDD), usando as fixtures existentes de `tests/conftest.py` (`client` autenticado e `db_session`) — nenhum teste existente é editado, nenhuma infraestrutura de teste é criada ou adaptada.

**Organization**: Tarefas agrupadas por user story do spec — US1 localizar colaborador rapidamente (P1), US2 pesquisa tolerante e com feedback claro (P2), US3 integridade da tela existente (P3). A regra de filtragem vive na camada de serviço (`CustodianService.get_all`, plan §1/R2); a rota só repassa o parâmetro; o template só renderiza — nenhuma duplicação (RT-002/FR-014).

**Feature Branch**: `006-pesquisa-colaboradores`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: User story da spec a que a tarefa pertence (US1, US2, US3)
- Todas as descrições incluem caminhos exatos de arquivo

## Path Conventions

- Projeto single-root: código em `app/`, testes em `tests/`, artifacts desta feature em `specs/006-pesquisa-colaboradores/`. Arquivos de código modificados: `app/services/custodian_service.py`, `app/web/routes.py` (apenas `list_custodians_view`), `app/web/templates/custodians/list.html` (plan §9); **NÃO são tocados**: `app/api/**`, `app/models/**`, `app/schemas/**`, demais rotas/templates, permissões/RBAC, `tests/conftest.py` e testes existentes (plan §10).

---

## Phase 1: Setup (Contexto da Feature)

**Purpose**: Confirmar contexto e estado limpo antes de qualquer mudança

- [x] T001 [P] Verificar que os artifacts de design existem em `specs/006-pesquisa-colaboradores/` (spec.md, plan.md, research.md, data-model.md, contracts/web-search-contract.md, quickstart.md) e que `git status` não mostra modificações pendentes nos arquivos-alvo do plan §9 (`app/services/custodian_service.py`, `app/web/routes.py`, `app/web/templates/custodians/list.html`, `tests/`)

**Checkpoint**: Contexto confirmado — nenhum arquivo-alvo está modificado.

---

## Phase 2: Foundational (Baseline e Verificação de Reuso — Bloqueia as Stories)

**Purpose**: Registrar o estado de regressão antes de qualquer mudança e confirmar que os mecanismos a reutilizar estão exatamente como o plan assume

**⚠️ CRITICAL**: Nenhuma tarefa de user story pode começar antes desta fase

- [x] T002 [P] Registrar a baseline de regressão: executar `pytest -q` na raiz e anotar o resultado atual (estado conhecido: 230 passed, 1 failed — `test_lockout_after_failed_attempts`, falha defasada conhecida) — referência para comparação na Phase 6 (quickstart §1)
- [x] T003 [P] Verificar no código os mecanismos de reuso contra o plan §2: `app/services/custodian_service.py` → `get_all(db, active_only=False)` (L11–15) e `count_assigned_assets`; `app/web/routes.py` → `list_custodians_view` (L872–888, permissão `colaboradores.visualizar`); precedente do padrão de filtro: `app/services/asset_service.py` (`get_all` com `or_` + `ilike`) e `app/web/templates/assets/list.html` (input-group + `bi-search` L47–48); `app/web/templates/custodians/list.html` → bloco `empty-state` atual ("Nenhum colaborador cadastrado", L64–72) a preservar — se qualquer assinatura divergir, PARAR e reportar antes de implementar

**Checkpoint**: Baseline registrada; mecanismos de reuso confirmados — stories podem começar.

---

## Phase 3: User Story 1 — Localizar um colaborador rapidamente (Priority: P1) 🎯 MVP

**Goal**: Um campo de pesquisa acima da tabela filtra por matrícula, nome, cargo, departamento e e-mail (combinado, parcial, case-insensitive), mostrando somente os correspondentes

**Independent Test**: com colaboradores cadastrados, submeter `?search=Amanda` → somente "Amanda Silva Nunes" e "Amanda Teixeira Rodrigues" aparecem, com todos os dados/ações existentes; submeter `?search=MAT-1036` → o colaborador da matrícula aparece

### Tests for User Story 1 (escritas primeiro — devem falhar antes da implementação) ⚠️

- [x] T004 [P] [US1] Criar `tests/test_custodians_search.py` com os casos US1 (fixtures `client` e `db_session` de `tests/conftest.py`; colaboradores criados via `CustodianService.create`): (a) busca por nome — `?search=Amanda` retorna Amanda Silva Nunes e Amanda Teixeira Rodrigues e não retorna outros (CA-002); (b) busca por matrícula completa `MAT-1036` e parcial `1036` (CA-003); (c) busca por departamento `Comercial` (CA-004); (d) busca por cargo `Gerente` encontra "Gerente de Contas" (CA-005); (e) busca por trecho de e-mail `amanda.nunes36` (CA-006); (f) **verificação TDD**: os testes (a)–(e) devem falhar antes da implementação (a rota atual ignora `search` e renderiza a lista completa) — executar e registrar o vermelho

### Implementation for User Story 1 (sequenciais — service → rota → template)

- [x] T005 [US1] Estender `CustodianService.get_all` em `app/services/custodian_service.py`: novo parâmetro **aditivo** `search: Optional[str] = None` (R2 — chamadores existentes intocados); com termo após `strip()`, aplicar `or_` de 5 `ilike("%termo%")` sobre `registration_code`, `name`, `role`, `department`, `email` (R3/FR-002..FR-009); importar `or_` de `sqlalchemy`; sem termo → consulta atual sem filtro (retrocompatibilidade do contrato, regra 2)
- [x] T006 [US1] Estender `list_custodians_view` em `app/web/routes.py`: novo parâmetro `search: Optional[str] = None`; repassar `search` ao `get_all` e incluir `"search": search or ""` no contexto do template (contrato: campo repopulado); **manter** `require_permission("colaboradores.visualizar")` intacto (FR-013/RN-002)
- [x] T007 [US1] Acrescentar em `app/web/templates/custodians/list.html` o formulário GET de pesquisa **acima** da tabela (padrão visual de `assets/list.html` L47–48: `input-group` com ícone `bi-search` + `input name="search"` com placeholder "Pesquisar por matrícula, nome, cargo, departamento ou e-mail..." e `value="{{ search }}"`), dentro do card, preservando o bloco atual da tabela; a tabela passa a renderizar os resultados filtrados sem qualquer alteração de colunas/linhas/links (FR-001, FR-012)
- [x] T008 [US1] Executar `pytest tests/test_custodians_search.py -q` até US1 verde e confirmar que os testes existentes de colaboradores (`pytest tests/test_ad.py tests/test_rbac.py tests/test_custodian_import.py -q`) permanecem no estado da baseline (serviço retrocompatível)

**Checkpoint**: US1 funcional e testável isoladamente — MVP entregue (pesquisa combinada completa).

---

## Phase 4: User Story 2 — Pesquisa tolerante e com feedback claro (Priority: P2)

**Goal**: Case-insensibilidade, correspondência parcial e estados claros: mensagem de nenhum resultado sem erro, e limpeza do campo restaura a lista completa

**Independent Test**: `?search=AMANDA`/`Amanda`/`amanda` → resultados equivalentes; `?search=zzz-inexistente` → HTTP 200 com "Nenhum colaborador encontrado."; `?search=` (vazio) → lista completa

### Tests for User Story 2 (extensão do mesmo arquivo — sequenciais entre si)

- [x] T009 [P] [US2] Estender `tests/test_custodians_search.py` com os casos US2: (a) case-insensitive — `AMANDA`, `Amanda` e `amanda` produzem resultados equivalentes (CA-007); (b) correspondência parcial — `Alex` encontra "Alexandre Carvalho Gomes" (FR-008); (c) **pesquisa combinada entre campos** (FR-007) — com um colaborador cujo departamento é "Logística" e outro chamado "Logística Silva", a busca por `Logística` retorna **ambos** (o termo casa em campos diferentes de colaboradores distintos — edge case da spec); (d) termo inexistente → status 200, corpo contém "Nenhum colaborador encontrado." e **não** contém linhas `<tr>` de colaboradores (CA-008/FR-010); (e) campo repopulado — o HTML contém `value="<termo>"` no input de busca (contrato); (f) `?search=` vazio/só espaços → lista completa, sem a mensagem de busca vazia (CA-009/FR-011); executar e registrar o vermelho dos casos novos antes da implementação

### Implementation for User Story 2 (extensões pontuais)

- [x] T010 [US2] Completar em `app/web/templates/custodians/list.html` os estados vazios (R4): reestruturar o condicional para (1) tabela com resultados; (2) `{% elif search %}` → bloco `empty-state` com "Nenhum colaborador encontrado." (FR-010); (3) `{% else %}` → "Nenhum colaborador cadastrado" **preservado como está** (estado atual da tela); `search` já chega do contexto como string (T006)
- [x] T011 [US2] Comprovar via teste a normalização do termo na **camada de serviço** (o caso (f) de T009 — `?search=` só espaços → lista completa — já exercita `strip()` + vazio = sem filtro); se o teste evidenciar lacuna, ajustar `CustodianService.get_all` em `app/services/custodian_service.py`; executar `pytest tests/test_custodians_search.py -q` até US1+US2 verdes

**Checkpoint**: US1 e US2 completas — pesquisa tolerante, com feedback claro e recuperável.

---

## Phase 5: User Story 3 — Integridade da tela existente (Priority: P3)

**Goal**: Operação read-only: dados, links, contagem de bens, ações, permissão e demais chamadores do service permanecem exatamente como antes

**Independent Test**: resultados da busca mantêm link `/custodians/{id}`, contagem de bens e ações; `GET /custodians` sem busca renderiza a tela atual; `get_all` sem `search` retorna todos (API REST intocada)

### Tests for User Story 3 (extensão do mesmo arquivo)

- [x] T012 [P] [US3] Estender `tests/test_custodians_search.py` com os casos US3: (a) não-regressão dos resultados — para um colaborador com bens vinculados, os resultados contêm `href="/custodians/{id}"`, o valor da contagem de bens (`active_assets_count` calculado pela rota) e o link "Ver Bens" (CA-010/RN-003); (b) retrocompatibilidade do serviço — `CustodianService.get_all(db)` e `get_all(db, active_only=True)` sem `search` retornam o mesmo que antes (contrato, regra 2; FR-014); (c) estado base — `GET /custodians` sem `search` renderiza a listagem completa com todas as linhas e **sem** a mensagem "Nenhum colaborador encontrado." (CA-011); (d) operação read-only — após a busca, `db_session.query(Custodian).count()` e os atributos dos colaboradores permanecem inalterados (RN-001); executar e registrar o vermelho dos casos novos antes da implementação

### Implementation for User Story 3

- [x] T013 [US3] Conformidade do template em `app/web/templates/custodians/list.html`: verificar que o loop dos resultados e as ações (`{% if can('colaboradores.editar') %}` e "Ver Bens") estão **fora** do caminho novo e intactos — nenhuma alteração permitida aqui além do formulário de busca e do estado vazio (T007/T010); ajustar apenas se a verificação evidenciar quebra
- [x] T014 [US3] Executar `pytest tests/test_custodians_search.py -q` até verde (US1+US2+US3) e a suíte de regressão direta `pytest tests/test_ad.py tests/test_rbac.py tests/test_custodian_import.py -q` no estado da baseline

**Checkpoint**: Todas as user stories implementadas — pesquisa completa sem custo ao que já existe.

---

## Phase 6: Polish & Cross-Cutting (Regressão, Documentação e Validação)

**Purpose**: Garantir não-regressão integral, documentação fiel (Constitution XI) e validação executável

- [x] T015 Executar a suíte completa `pytest -q`: todos os testes existentes no estado registrado em T002 + todos os testes novos verdes (quickstart §1; nenhuma edição em testes existentes — Constitution VIII)
- [x] T016 [P] Atualizar `app/services/help_service.py` — artigo "cadastrar-colaboradores" (L537): mencionar o campo de pesquisa na tela de colaboradores (o que pesquisa: matrícula, nome, cargo, departamento, e-mail; parcial e sem diferenciar maiúsculas/minúsculas)
- [x] T017 [P] Atualizar `docs/ARQUITETURA_E_MANUTENCAO.md` — §12.4 Colaboradores & Locais: uma linha sobre a pesquisa server-side via `CustodianService.get_all(search=...)` (padrão da pesquisa de bens)
- [ ] T018 Executar o procedimento manual de `specs/006-pesquisa-colaboradores/quickstart.md` §2–§3 no ambiente (navegador, usuário com `colaboradores.visualizar`): cenários 2.1–2.11 e spot-checks (tela de bens intacta, API REST intacta, permissão intacta); registrar os resultados
- [x] T019 Completar o checklist de conformidade da Constitution (quickstart §4), verificar os SC-001..SC-006 do spec e confirmar via `git status` que apenas `app/services/custodian_service.py`, `app/web/routes.py`, `app/web/templates/custodians/list.html`, `tests/test_custodians_search.py`, os 2 alvos de documentação e `specs/006-pesquisa-colaboradores/**` foram alterados/criados

**Checkpoint**: Feature entregue — validada por suíte, validação manual e checklist.

---

## Validation Results

> Preenchido por T018/T019. Automação executada em 16/09/2026; validação manual pendente do operador.

- **Baseline (T002)**: ☑ registrada — 230 passed, 1 failed (`test_lockout_after_failed_attempts`, falha defasada conhecida)
- **Suíte completa (T015)**: ☑ executada · ☑ estado existente confirmado (230 passed + mesma única falha defasada) · ☑ novos testes verdes (**15/15** em `tests/test_custodians_search.py`)
- **TDD**: ☑ vermelho confirmado antes da implementação — T004: 5/5 falhando (rota ignorava `search`); T009/T012 verdes na 1ª execução (caminhos já implementados na US1, cada caso exercita o branch real)
- **Validação manual (T018)**: ☐ cenários 2.1–2.11 · ☐ spot-checks §3 — **PENDENTE: executar pelo operador no ambiente**
- **Constitution checklist (T019)**: ☑ completo — escopo plan §9/§10 respeitado (`git status` confere: apenas os 5 arquivos previstos + artifacts), comportamento preservado (245 passed), nenhum DDL, permissão intacta, documentação na mesma tarefa (T016–T017)
- **SC-001..SC-006**: ☑ SC-002 (5 campos × completo/parcial/caixa — casos US1+US2) · ☑ SC-003 (nenhum resultado com mensagem, zero erros) · ☑ SC-004 (elementos da tela intactos — caso US3 com link/contagem/ação) · ☑ SC-005 (permissão intacta — rota sem mudança de gate; suíte RBAC verde) · ☑ SC-006 (suíte existente 100% + novos verdes) · ☐ SC-001 (localizar <10s sem rolagem — critério UX, confere na validação manual T018)
- **Observações**: mudanças da feature 005 e de `app/config.py` não constam mais no `git status` (aparentemente commitadas fora desta sessão); alteração pré-existente em `docs/doc_proviśorios/docs_para_testes/Coisas a corrigir ou melhorar.md` não é desta feature

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — imediata
- **Foundational (Phase 2)**: depende da Phase 1 — BLOQUEIA as stories (baseline + confirmação dos mecanismos de reuso)
- **User Stories (Phases 3–5)**: dependem da Phase 2; **devem ser implementadas em ordem** (US1 → US2 → US3) porque todas tocam o mesmo trio service/rota/template e o mesmo arquivo de testes — a independência entre stories é preservada no nível de **teste** (cada story tem casos próprios executáveis isoladamente)
- **Polish (Phase 6)**: T015 depende de todas as stories; T016–T017 em paralelo após T014; T018 depende de T015; T019 fecha a entrega

### User Story Dependencies

- **US1 (P1)**: núcleo — cria o parâmetro `search` no service, o repasse na rota e o campo no template
- **US2 (P2)**: complementa o template com os estados vazios e confirma a normalização do termo (usa o esqueleto da US1)
- **US3 (P3)**: proteção de não-regressão (usa tudo o que existe; implementa por verificação/conformidade, com mudanças só se a verificação evidenciar quebra)

### Within Each User Story

- Testes primeiro, como **requisito TDD obrigatório**: a tarefa de testes é escrita E executada (verificando que falha) **antes** da implementação correspondente — nunca em paralelo com ela → implementação → execução dos testes até verde → regressão direta
- As tarefas de implementação são sequenciais entre si (service → rota → template; mesmo fluxo de arquivos)

### Parallel Opportunities

- T001/T002/T003 (Setup/Foundational) em paralelo
- T016–T017 (documentação, arquivos distintos) em paralelo
- **Testes NÃO são paralelizáveis com a implementação**: dentro de cada User Story, a tarefa de testes é requisito TDD e deve estar escrita e executada (falhando) **antes** do início da implementação correspondente — o marcador [P] nas tarefas de testes indica apenas independência de arquivo, não execução concorrente com a implementação

---

## Parallel Example: Phase 6 Documentation

```bash
# Os 2 alvos de documentação são arquivos distintos — podem ser editados em paralelo:
Task: "Atualizar app/services/help_service.py (artigo de ajuda)"      # T016
Task: "Atualizar docs/ARQUITETURA_E_MANUTENCAO.md (§12.4)"            # T017
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 + 2 → contexto, baseline e mecanismos confirmados
2. US1 → pesquisa combinada funcional (matrícula/nome/cargo/departamento/e-mail, parcial, case-insensitive)
3. **STOP and VALIDATE**: `pytest tests/test_custodians_search.py -q` verde nos casos US1 + testes existentes intactos
4. O MVP já entrega o valor central (localizar sem rolagem)

### Incremental Delivery

1. US1 → pesquisa funcional (MVP)
2. US2 → tolerância e feedback (case, parcial, estados vazios, limpeza)
3. US3 → proteção de não-regressão (links, contagem, ações, permissão, read-only)
4. Phase 6 → regressão integral + documentação + validação manual + checklist

### Notes

- **Nenhuma tarefa cria ou adapta infraestrutura de banco**: zero DDL (data-model §3); a suíte usa os fixtures existentes
- **Nenhuma tarefa altera** `app/api/**`, models, schemas, permissões, demais rotas/templates ou testes existentes (plan §10)
- Evitar: tarefas vagas, editar testes existentes, tocar arquivos do plan §10
