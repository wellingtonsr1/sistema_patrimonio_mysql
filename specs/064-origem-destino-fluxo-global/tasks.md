# Tasks: Padronização da Apresentação de Origem e Destino no Fluxo Global de Movimentações

**Input**: Design documents from `/specs/064-origem-destino-fluxo-global/`  
**Branch**: `064-origem-destino-fluxo-global`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-contract.md, quickstart.md

**Implementation scope**: only `app/web/templates/movements/list.html` (production) + new `tests/test_fluxo_global_064.py` (tests). Zero backend, zero DDL, zero new dependencies, zero edits to existing tests.

**Implementation strategy**: US1 first (renderização red→green), then US2 (guarda de não-mutação). Régua final inclusive suítes 062/063 inéditas.

---

## Phase 1: Setup (Baseline + Escopo do Projeto)

**Purpose**: Registrar régua atual e documentar o raio de alteração antes de qualquer código novo — seguindo o plano `064-origem-destino-fluxo-global/plan.md` §18.1 e a Constitution VIII.

- [ ] T001 Registrar régua atual da suíte (`python -m pytest`) — esperado baseline `948 passed / 2 skipped / 4 failed`; os 4 failures são ambientais e pré-existentes (`test_backup_config.py` ×1, `test_migrations_052.py` ×3; `ModuleNotFoundError` de `dotenv`/`alembic` num subprocesso). Regravar esse número no `tasks.md` ou no `validacao.md` quando executado; qualquer diferença de natais em produtividade nos failures aqui é sinal de ambiente, não de regressão.

---

## Phase 2: Foundational (Pré-requisitos não-bloqueantes para esta feature)

**Purpose**: Esta feature é de apresentação e não exige infraestrutura nova. Esta fase documenta apenas a leitura que evita regressions.

- [ ] T002 Confirmar leitura do template atual `app/web/templates/movements/list.html` linhas 128–137 (Origem/Destino com snapshots) e registrar que o `joinedload` existente em `app/services/movement_service.py` (L479–485) já entrega `origin_location`/`destination_location` completos — sem query nova, sem service novo. Não editar nada; apenas verificar antes de alterar.
- [ ] T003 Confirmar escopo de proteção no `app/web/templates/movements/list.html`: `<style>` escopado da Feature 039, larguras de coluna em px, classes `mov-fluxo`/`mov-sec`, cabeçalhos e botões (L20–115) permanecem intocados. A alteração é apenas o corpo das 2 `<td>` + macro no topo.

**Checkpoint**: Linha de base documentada, raio de alteração delimitado, sem código novo ainda.

---

## Phase 3: User Story — Apresentação padronizada sem redundância (US1) 🎯 MVP

**Goal**: Origem e Destino na tabela do Fluxo Global (`/movements`) exibem, quando a relação `Location` existe, `department` como linha principal + `local_curto • branch` deduplicado em `.mov-sec`, seguindo o contrato `contracts/ui-contract.md` §2–§4 e o padrão aprovado na Feature 063 (commit `0b3a329`). Quando a relação não existe, o snapshot cru é exibido byte-a-byte como hoje.

**Independent Test**: `tests/test_fluxo_global_064.py` renderiza `/movements` com locais de dados conhecidos e verifica ausência de redundância (`IPMJP - Sede - Assessoria de Gabinete (Sede - Assessoria de Gabinete)` não aparece), presença de `department` em destaque, contexto `Sede • IPMJP - Sede` e caso Clube sem `Clube • Clube`. Esse teste parte RED contra o template atual e vira GREEN após a macro + células.

### Redação antes da implementação — único arquivo de teste novo

> Nota: testes escritos antes da implementação (RED) segundo estratégia `spec.md` §19. Nenhum teste existente é editado.

- [ ] T004 [P] [US1] Criar `tests/test_fluxo_global_064.py` com fixture/setup espelhando `test_presentacao_trilha_063.py` e os helpers da casa (`client`, `db_session`, `LocationService`, `AssetService`, `MovementService`) — sem editar `conftest.py` nem fixtures existentes (somente novo arquivo).

### Renderização — implementação no único arquivo de produção

- [ ] T005 [US1] Adicionar macro `_local_curto(name, department)` no topo de `app/web/templates/movements/list.html`, logo após o `{% extends %}` e antes dos blocos — idêntica em lógica à macro da Feature 063 (`assets/detail.html`): remove o sufixo ` - {department}` do `name` via `endswith`/`rsplit` quando presente, senão devolve o `name` intacto. Esta macro NÃO é importada compartilhada — replica documentada da spec §11 e regra de dívida consciente.
- [ ] T006 [US1] Alterar a célula Origem em `app/web/templates/movements/list.html` (a `<td class="small mov-fluxo">`, L128–130): quando `m.origin_location` existe, exibir `m.origin_location.department` como linha principal + contexto composto pela regra de §4 do contrato (join ` • `, deduplicado — sem `Clube • Clube` e sem `Clube da Pessoa Idosa - Clube da Pessoa Idosa`); quando não existe, manter `{{ m.origin_location_name or '-' }}` (snapshot cru byte-a-byte: `Fornecedor / Entrada Inicial`, `Não definido`, formatos antigos). Preservar ícone `bi-geo-alt`, classes `small mov-fluxo` e colaborador `m.origin_custodian_name or '-'` na linha seguinte.
- [ ] T007 [US1] Alterar a célula Destino em `app/web/templates/movements/list.html` (a `<td>`, L131–135): quando `m.destination_location` existe, exibir `m.destination_location.department` como linha principal (estilo `fw-semibold` com `color:var(--c-primary-text);` e ícone `bi-geo-alt-fill`, conforme contrato §3) + contexto `.mov-sec` composto pela mesma regra de deduplicação + colaborador `m.destination_custodian_name or '-'` com ícone `bi-person-fill`. Quando não existe, manter `{{ m.destination_location_name or '-' }}` (snapshot cru byte-a-byte).
- [ ] T008 [US1] Validar que o contexto nunca produz separador órfão (` • ` no início/fim) e que uma `partes` vazia não renderiza linha em branco — implementar no Jinja seguindo §4 do contrato: só append de `curto` quando `curto and curto != loc.department`; só append de `branch` quando `loc.branch and loc.branch not in partes and loc.branch != loc.department`; join ` • ` e renderização condicional da linha de contexto quando `partes` não vazia.

**Checkpoint**: `tests/test_fluxo_global_064.py::test_fluxo_global_titulos_sao_departamento_e_contexto_deduplicado` e `test_fluxo_global_caso_deduplicado_clube` GREEN, sem redundância e sem quebra para registros sem FK.

---

## Phase 4: User Story — Guarda de não-mutação (US2)

**Goal**: A mudança visual não altera gravação, busca, CSV, termo, dashboard, relatório, dropdown 062 ou trilha 063. Backup do snapshot permanece byte-a-byte no banco, no CSV (`/api/reports/movements/csv`) e na busca 049. (Constitution IV, VII, VIII; AC08–AC13.)

**Independent Test**: `tests/test_fluxo_global_064.py` grava uma movimentação com snapshot no formato atual, busca por `"Dept B"` no Fluxo Global e confirma que o CSV endpoint (`/api/reports/movements/csv`) continua com o snapshot cru e idêntico antes/depois da mudança de template (mesmo banco).

### Guarda — testes no arquivo novo (continuação)

- [ ] T009 [P] [US2] Adicionar `test_fluxo_global_fallbacks_snapshot_e_literais` em `tests/test_fluxo_global_064.py`: verificar registros sem FK e literais especiais (`Não definido`, `Nenhum / Estoque`, `Fornecedor / Entrada Inicial`) exibidos byte-a-byte como hoje — sem inventar estrutura.
- [ ] T010 [P] [US2] Adicionar `test_fluxo_global_nao_muda_gravacao_nem_busca_nem_csv` em `tests/test_fluxo_global_064.py`: gravar transferência com snapshot `Unidade B - Dept B (Sala B)`, confirmar que busca por `"Dept B"` no Fluxo Global encontra o registro, confirmar conteúdo do colaborador correto e confirmar CSV byte-a-byte (gerar CSV sobre o mesmo banco antes e depois da mudança de template e comparar as strings).

### Guarda — execução de sentinela (sem editar testes existentes)

- [ ] T011 Executar subconjunto de regressão sem editar arquivos: `tests/test_movements.py`, `tests/test_movements_search.py`, `tests/test_import_asset_movements.py`, `tests/test_departamento_destino_062.py`, `tests/test_presentacao_trilha_063.py` em `--quiet` — esperado 100% passed e nenhum teste editado (protege AC12/AC13 e a trilha 063).
- [ ] T012 Executar régua completa (`python -m pytest`): esperado `~953 passed / 2 skipped / 4 failed` (os 4 failures ambientais idênticos ao baseline). Exit code 1 é aceitável **somente** por esses 4 failures ambientais conhecidos; qualquer novo failure é regressão a investigar antes de avançar.

**Checkpoint**: US2 verde, CSV idêntico, busca intacta, suítes 062/063 verdes sem edição, régua final dentro do esperado.

---

## Phase 5: Polish & Validação Manual

**Purpose**: Smoke visual e registro de validação.

- [ ] T013 Verificar o diff de produção: `git diff main -- app/` deve mostrar somente `app/web/templates/movements/list.html` (macro + 2 células). Qualquer outro arquivo de produção é violação do AC14/AC15/FR-007.
- [ ] T014 (manual — smoke visual) Subir a app local (`python run.py`), abrir `/movements` com usuário `movimentacao.visualizar` e conferir: linha principal = departamento, contexto = `Sede • IPMJP - Sede` em fonte menor; caso Clube com contexto apenas `Clube`; entrada inicial `Fornecedor / Entrada Inicial` como está; registro sem origem `Não definido` + `Nenhum / Estoque` como está; layout fixo da Feature 039 preservado (larguras e quebras inalteradas). Registro de prints em `specs/064-origem-destino-fluxo-global/validacao.md` quando concluído.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: sem dependências — executar primeiro para registrar baseline.
- **Phase 2**: leituras somente — não bloqueia, mas deve ser confirmado antes de T005/T006/T007.
- **Phase 3 (US1)**: depende de T002/T003 confirmados; T004 (teste) deve ser escrito antes de T005/T006/T007 (RED→GREEN).
- **Phase 4 (US2)**: depende da implementação da Phase 3 estar GREEN; T011/T012 são sentinela após T009/T010.
- **Phase 5**: depende de US2 verde.

### User Story Dependencies

- **US1** e **US2** compartilham o único arquivo de teste (`tests/test_fluxo_global_064.py`) e o único arquivo de produção alterado (`app/web/templates/movements/list.html`). US2 não pode ser validado com a mudança de template separada de US1 sem reverter o template — por isso são implementadas em sequência, não em paralelo, mesmo usando o mesmo arquivo de teste.

### Within Each User Story

- Teste escrito e falhando (RED) antes da implementação (T004 antes de T005–T008).
- Macro antes das células, mas na mesma `movements/list.html` (T005 antes de T006/T007 na ordem de leitura, sem arquivo separado).
- Guarda de CSV byte-a-byte (T010) é o teste mais forte de escopo — rodar sempre que o template for alterado.

### Parallel Opportunities

- T004 (criação do arquivo de teste) é independente dos detalhes da implementação e pode ser iniciado em paralelo à revisão de T002/T003, mas o teste só pode virar GREEN após T005/T006/T007.
- T009 e T010 são adicionados ao mesmo arquivo novo e podem ser desenvolvidos em sequência; não há arquivo separado para cada.
- Não há paralelismo entre arquivos de produção porque há um único arquivo alterado (`movements/list.html`).

---

## Parallel Example: Escrever o teste de US1 antes da implementação

```bash
# Passo 1 — escrever o teste novo (RED) em paralelo com a leitura de T002/T003
Task: T004 [P] [US1] Criar tests/test_fluxo_global_064.py

# Passo 2 — implementação sequencial no mesmo template
Task: T005 [US1] Macro _local_curto em app/web/templates/movements/list.html
Task: T006 [US1] Célula Origem em app/web/templates/movements/list.html
Task: T007 [US1] Célula Destino em app/web/templates/movements/list.html
Task: T008 [US1] Validar sem separador órfão / linha em branco em app/web/templates/movements/list.html
```

---

## Implementation Strategy

### MVP First (US1 Only — mas com teste de guarda integrado)

1. Completar Phase 1 — registrar baseline.
2. Completar leituras de Phase 2 (T002/T003) sem editar.
3. Escrever T004 (teste novo RED) — deve falhar contra o template atual.
4. Completar T005/T006/T007/T008 (macro + 2 células) → US1 GREEN.
5. **STOP and VALIDATE**: T004 + T009 + T010 GREEN; subconjunto 062/063 intacto.

### Guarda antes de considerar entregue

6. Completar T011 (subconjunto de regressão sem edição) e T012 (régua completa).
7. Completar T013 (diff de produção) e T014 (smoke visual manual + validacao.md).

### Escopo mínimo (Constitution I)

- Somente `app/web/templates/movements/list.html` (macro + 2 células).
- Somente `tests/test_fluxo_global_064.py` (novo).
- Zero backend, zero DDL, zero novo serviço, zero nova rota, zero novo modelo, zero nova dependência.
- Macro replicada (não compartilhada) — dívida registrada na spec §11 para feature futura (Alternativa B).

---

## Notes

- **[P]** = arquivo diferente, sem dependência de tarefa incompleta.
- **[US1]/[US2]** = rastreabilidade ao story do spec.md (testes e implementação da apresentação + guarda).
- **Zero DDL** é requisito do plano (`data-model.md`) e da Constitution VII — confirmado antes e depois da implementação.
- **CSV byte-a-byte** é prova do AC11 (teste T010); o CSV usa somente snapshots brutos via `ReportService.generate_movements_csv` — fora do template.
- **Nenhum teste existente é editado** — même a régua final pode ter os 4 failures ambientais pré-existentes; isso não é regressão.
- **Reuso das fixtures da casa** (`client`, `db_session`, services em `tests/conftest.py`) — não tocar em `conftest.py`.
