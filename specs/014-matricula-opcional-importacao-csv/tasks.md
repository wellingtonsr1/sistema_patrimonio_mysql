---

description: "Task list for feature implementation"
---

# Tasks: Matrícula Opcional na Importação de Colaboradores via CSV

**Input**: Design documents from `/specs/014-matricula-opcional-importacao-csv/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R11), data-model.md (RV-1..RV-7), contracts/service-contract.md, quickstart.md

**Tests**: Incluídos por exigência da spec (FR-012: 8 cenários obrigatórios do briefing). TDD: escrever primeiro, garantir que FALHAM, depois implementar.

**Organization**: Por user story. A mudança central é compartilhada (foundational: `_validate_row` + fachada do gerador único); US1–US3 cobrem a execução, US4 cobre preview + documentação.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Projeto monolítico FastAPI existente: `app/services/`, `app/web/templates/`, `tests/` na raiz.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline e padrões — nenhuma alteração de comportamento

- [x] T001 Rodar a suíte completa e registrar o baseline (`python3 -m pytest -q`): **341 passed + 1 falha pré-existente** `tests/test_rbac.py::test_lockout_after_failed_attempts` (fora do escopo — não corrigir, Princípio I). Ler `tests/test_custodian_import.py` para capturar os padrões de fixture (db/session, construção de CSV) a serem reutilizados nos novos testes (depends: none)
- [x] T002 Criar o módulo de testes da feature `tests/test_custodian_import_optional_matricula.py` com imports e helpers (construtores de CSV com `;`, criação de colaboradores existentes) seguindo os padrões capturados em T001 — arquivo inicia vazio de testes, apenas infraestrutura (depends: T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Remover a obrigatoriedade (parse) e expor o gerador único — bloqueia TODAS as user stories

**⚠️ CRITICAL**: Nenhuma linha sem matrícula chega ao preview/execução antes desta fase

### Tests for Foundational (TDD — escrever primeiro, garantir FALHA)

- [x] T003 [P] Testes FALHANDO do parse sem obrigatoriedade em `tests/test_custodian_import_optional_matricula.py`: (a) CSV com célula vazia → linha em `rows` sem erro de matrícula; (b) célula `"   "` (só espaços) → idem; (c) CSV sem a coluna `matricula` → linhas válidas em `rows` (chave pode estar ausente); (d) demais erros preservados (sem nome/email/cargo/setor → erros como hoje). Ajustar o teste existente que asserta o erro removido: `tests/test_custodian_import.py::test_parse_custodian_csv_reports_missing_required_fields` — matrícula vazia sai da lista de erros esperados (comportamento alterado pela spec; única edição autorizada em teste existente, research R10 / Constitution VIII) (depends: T002)
- [x] T004 [P] Testes FALHANDO da fachada em `tests/test_custodian_import_optional_matricula.py`: `CustodianService.generate_available_provisional_code(db)` retorna `PROV-\d{6}`; retorna o próximo sequencial com `PROV-000005` pré-existente; retorna código disponível quando `PROV-000006` já existe (pula para 000007) — contrato §1, research R1 (depends: T002)

### Implementation for Foundational

- [x] T005 Implementar a fachada pública `generate_available_provisional_code(db) -> str` em `app/services/custodian_service.py`: delega a `_next_provisional_code(db)` (lógica interna **INTOCADA**) e repete enquanto `get_by_registration_code(db, code)` retornar registro — replica a verificação pré-inserção do `create`; sem persistir nada (depends: T004)
- [x] T006 Remover SOMENTE o bloco de obrigatoriedade de matrícula em `_validate_row` (`app/services/custodian_import_service.py` ~linha 120): excluir `if not row.get("registration_code","").strip(): errors.append("... matricula é obrigatória")` — validações de nome/email/cargo/setor/ativo byte-a-byte intactas (research R4, FR-001/FR-008) (depends: none [P])
- [x] T007 Checkpoint foundational: `python3 -m pytest tests/test_custodian_import.py tests/test_custodian_import_optional_matricula.py -q` → parse verde (linhas sem matrícula válidas) + fachada verde + suíte do importador existente verde (exceto ajuste R10) (depends: T003, T004, T005, T006)

**Checkpoint**: Foundation pronta — linhas sem matrícula chegam ao preview/execução e o gerador único está acessível

---

## Phase 3: User Story 1 — Importar sem matrícula → provisória (Priority: P1) 🎯 MVP

**Goal**: Linha com matrícula ausente (vazia, só espaços ou coluna ausente) é importada com `PROV-%06d` gerada pelo mecanismo único do cadastro individual

**Independent Test**: `execute_custodian_import` com CSV de 1 linha sem matrícula → colaborador criado com `PROV-*`, sem erro (quickstart §2 T2/T3/T4)

### Tests for User Story 1 (TDD — escrever primeiro, garantir FALHA)

- [x] T008 [P] [US1] Testes FALHANDO da execução em `tests/test_custodian_import_optional_matricula.py` (service-level, quickstart T2/T3/T4/T5): (a) célula vazia → criado com `registration_code` casando `PROV-\d{6}` e sem erro; (b) `"   "` → idem; (c) CSV sem coluna (chave ausente) → criado com `PROV-*`; (d) importação mista (informada + vazias na mesma execução) → informados mantêm valor, ausentes recebem `PROV-*`, `imported` conta todos (depends: T007)

### Implementation for User Story 1

- [x] T009 [US1] Implementar a geração no ramo de criação nova em `execute_custodian_import` (`app/services/custodian_import_service.py`): quando `(row.get("registration_code","") or "").strip()` for vazio → `reg_code = CustodianService.generate_available_provisional_code(db)` imediatamente antes do `Custodian(...)`/`db.add` (import do service no topo do módulo); ramo de atualização (duplicata) intocado; transação/erros/commit parcial idênticos aos atuais (research R2/R11, data-model RV-1/RV-2) (depends: T005, T008)
- [x] T010 [US1] Checkpoint US1 (MVP): `python3 -m pytest tests/test_custodian_import_optional_matricula.py -q` verde; suíte completa `python3 -m pytest -q` sem novas falhas além do baseline RBAC (depends: T009)

**Checkpoint**: US1 funcional e testável independentemente — CSV sem matrícula importa com provisória

---

## Phase 4: User Story 2 — Regras de matrícula informada preservadas (Priority: P1)

**Goal**: Matrículas informadas continuam byte-a-byte iguais (normalização, duplicidade, sem substituição por provisória)

**Independent Test**: CSV com `MAT-1045` nova, duplicada e normalizável → usada como está; duplicada segue skip/update conforme `skip_duplicates` (quickstart §2 T1/T6)

### Tests for User Story 2 (TDD — caracterização, devem PASSAR após US1)

- [x] T011 [P] [US2] Testes de caracterização em `tests/test_custodian_import_optional_matricula.py` (quickstart T1/T6, contract §2.4): (a) `MAT-1045` informada → criado com o valor, sem provisória; (b) normalização atual: `mat-1045` → `MAT-1045` (trim+upper de `_normalize_registration_code`); (c) matrícula duplicada no banco com `skip_duplicates=True` → `skipped` incrementado, registro intocado; (d) com `skip_duplicates=False` → atualização in-place mantendo a matrícula original; (e) em nenhum cenário a matrícula informada é substituída por `PROV-*` (data-model RV-5, FR-003/FR-004) (depends: T010)
- [x] T012 [US2] Checkpoint US2: testes de caracterização verdes — se algum falhar, a implementação de T009 vazou para o ramo de informadas: corrigir T009 (nunca relaxar o teste) (depends: T011)

**Checkpoint**: US1 + US2 independentes e verdes — ausência gera provisória, informada preservada

---

## Phase 5: User Story 3 — Unicidade das provisórias na mesma importação (Priority: P1)

**Goal**: Cada colaborador sem matrícula recebe `PROV-*` distinta dentro da mesma execução (RV-3)

**Independent Test**: CSV com 3 linhas sem matrícula → 3 provisórias duas a duas distintas (quickstart §2 T7)

### Tests for User Story 3 (testes de guarda — devem PASSAR com a implementação correta de T009; se falharem, revisar T009 — remediação C1)

- [x] T013 [P] [US3] Teste de unicidade em `tests/test_custodian_import_optional_matricula.py` (quickstart T7, contract §5): CSV com 3 linhas sem matrícula → `imported == 3` e `registration_code` duas a duas distintos, todos casando `PROV-\d{6}`; validação via `len(set(codes)) == 3` (data-model RV-3, research R6) (depends: T010)
- [x] T014 [US3] Checkpoint US3: teste verde com a implementação de T009 (flush por linha torna cada provisória visível à seguinte); se houver duplicata, revisar a ordem geração→add→flush em T009 (depends: T013)

**Checkpoint**: Todas as USs P1 (1–3) verdes — o MVP funcional está completo

---

## Phase 6: User Story 4 — Preview e documentação coerentes (Priority: P2)

**Goal**: Preview não trata ausência como erro nem fabrica número; documentação da tela marca `matricula` como opcional com a regra

**Independent Test**: `preview_custodian_import` com linha sem matrícula → sem duplicata por matrícula vazia, flag `will_generate_provisional=True`, `registration_code=""`; tela de importação documenta a opcionalidade (quickstart §3)

### Tests for User Story 4 (TDD — escrever primeiro, garantir FALHA)

- [x] T015 [P] [US4] Testes FALHANDO do preview em `tests/test_custodian_import_optional_matricula.py` (contract §2.3): (a) linha sem matrícula → preview presente com `registration_code=""`, `will_generate_provisional=True`, `is_duplicate=False` (sem e-mail duplicado); (b) linha sem matrícula e com e-mail já cadastrado → `is_duplicate=True` (duplicata por e-mail preservada); (c) linha com matrícula informada duplicada → `is_duplicate=True` como hoje; (d) nenhum preview fabrica número (`registration_code` permanece `""` — FR-007) (depends: T007)

### Implementation for User Story 4

- [x] T016 [US4] Implementar no `preview_custodian_import` (`app/services/custodian_import_service.py`): `will_generate_provisional = not reg_code` no dict de preview; suprimir a busca por matrícula quando vazia (`existing = _find_by_registration_code(db, reg_code) if reg_code else None` → `or _find_by_email(db, email)`) — pesquisa por `""` é inócua (research R3); shape existente inalterado (campo aditivo) (depends: T015)
- [x] T017 [US4] Atualizar a documentação em `app/web/templates/custodians/import.html` (research R9, FR-011): (a) parágrafo ~linha 247 — `matricula` sai da lista de obrigatórias ("As colunas `nome`, `email`, `cargo` e `setor` são obrigatórias."); (b) tabela de colunas ~linha 261 — badge `Sim`→`Não` (bg-danger→bg-secondary) e observação: "Se informada, será utilizada. Quando não informada, o sistema gerará automaticamente uma matrícula provisória, seguindo a mesma regra do cadastro individual."; (c) exemplo de CSV ~linha 308 — incluir linha sem matrícula (importação mista); (d) espelhar a regra no docstring do módulo `app/services/custodian_import_service.py` (cabeçalho "Colunas esperadas") (depends: none [P])
- [x] T018 [US4] Checkpoint US4: testes do preview verdes; suíte do importador verde; template sem regressão de sintaxe (renderização coberta pelos testes web E2E existentes em `tests/test_custodian_import.py`) (depends: T016, T017)

**Checkpoint**: Todas as user stories (1–4) funcionais

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Regressão, escopo e validação final

- [x] T019 [P] Regressão completa (quickstart T8): `python3 -m pytest -q` → suíte verde exceto a falha pré-existente do baseline RBAC; confirmar explicitamente que `tests/test_custodian_provisional.py` (feature 010) e os testes web/API de colaboradores permanecem verdes (depends: T018)
- [x] T020 [P] Verificação estática de escopo via `git diff --stat` + `git diff` (quickstart DoD): alterações restritas a `app/services/custodian_import_service.py`, `app/services/custodian_service.py` (apenas a fachada — `_next_provisional_code`/`create`/`update` sem dif), `app/web/templates/custodians/import.html`, `tests/test_custodian_import.py` (só o ajuste R10) e `tests/test_custodian_import_optional_matricula.py` (novo) — **zero** dif em rotas, models, schemas, migrations, API, AD, outros importadores (FR-009/FR-010, AC-11) (depends: T018)
- [x] T021 Validação final: executar o roteiro do `specs/014-matricula-opcional-importacao-csv/quickstart.md` (§1 suíte; §3.3–3.9 observações documentais do CSV de exemplo; §4 não-regressão do cadastro individual/outros importadores) e conferir a Definition of Done; re-verificar a Constitution (checklist do plan.md) e marcar todas as tarefas `[X]` em `tasks.md` (depends: T019, T020)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — imediato
- **Foundational (Phase 2)**: depende do Setup; **BLOQUEIA todas as user stories** (sem `_validate_row` corrigido e sem a fachada, nenhuma linha sem matrícula chega ao fluxo)
- **US1 (Phase 3)**: primeira story — MVP
- **US2 (Phase 4)**: depende de US1 (caracterização sobre a execução implementada)
- **US3 (Phase 5)**: depende de US1 (valida a unicidade da implementação de T009)
- **US4 (Phase 6)**: depende apenas da Foundation (preview/doc) — poderia paralelizar com US1 se houver capacidade
- **Polish (Phase 7)**: depende de todas as stories

### User Story Dependencies

- **US1 → US2/US3**: US2 e US3 caracterizam/guardam o comportamento criado em US1 (mesmo service, mesmas linhas)
- **US4 independente** de US1–US3 no código (função `preview` + template), dependente da Foundation

### Parallel Opportunities

- T003/T004 (testes foundational) e T006 (remoção da regra) — arquivos/testes distintos
- T008, T011, T013, T015 — todos em `tests/test_custodian_import_optional_matricula.py` mas independentes entre si (executar em sequência para evitar conflito de edição no mesmo arquivo; marcados [P] por não dependerem de implementação cruzada)
- T017 (template) paralelo a tudo da camada service

## Parallel Example: Foundation

```bash
# Testes primeiro (arquivo único, executar sequencialmente na prática):
Task: "T003 testes FALHANDO do parse"
Task: "T004 testes FALHANDO da fachada"

# Implementação:
Task: "T005 fachada em custodian_service.py"   # depende T004
Task: "T006 _validate_row em custodian_import_service.py"  # independente
```

---

## Implementation Strategy

### MVP First (Foundational + US1)

1. Phase 1–2: Setup + Foundation (parse sem obrigatoriedade + fachada do gerador único)
2. Phase 3: US1 — execução gera provisória
3. **STOP and VALIDATE**: CSV sem matrícula importa com `PROV-*` (quickstart §2 T2/T3/T4)

### Incremental Delivery

1. Foundation + US1 → correção central entregue (MVP)
2. US2 → guardas de caracterização das matrículas informadas
3. US3 → guardas de unicidade intra-importação
4. US4 → preview coerente + documentação da tela
5. Polish → regressão total, auditoria de escopo, DoD

### Notes

- TDD: cada bloco de testes escrito e FALHANDO antes da respectiva implementação
- Única edição autorizada em teste existente: `test_parse_custodian_csv_reports_missing_required_fields` (asserta o erro removido pela spec — research R10, Constitution VIII)
- Nenhuma mudança fora: `custodian_import_service.py`, fachada em `custodian_service.py`, `import.html` (documentação), testes
- Commit após cada checkpoint
