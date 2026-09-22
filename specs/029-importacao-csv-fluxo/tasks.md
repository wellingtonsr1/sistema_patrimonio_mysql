---

description: "Task list for feature 029-importacao-csv-fluxo implementation"
---

# Tasks: Registrar no Fluxo as movimentações da importação CSV de equipamentos

**Input**: Design documents from `/specs/029-importacao-csv-fluxo/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/service-contract.md, quickstart.md

**Tests**: Testes são OBRIGATÓRIOS nesta feature — a spec exige os cenários A–L ("TESTES OBRIGATÓRIOS") e a Constitution VIII exige cobertura nova. Cada fase de User Story começa pelos testes (devem FALHAR antes da implementação — TDD).

**Organization**: Tasks agrupadas por User Story (US1–US5 da spec.md). Todas as stories tocam `app/services/import_service.py` em pontos diferentes — as tarefas de implementação dessa file são sequenciais (nenhuma marcada [P] conflita no mesmo arquivo); os testes são escritos antes de cada slice.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- Projeto único existente (FastAPI): `app/` (services, web, api), `tests/` na raiz
- Arquivos-alvo (fechados no plan.md): `app/services/import_service.py`, `app/services/movement_service.py`, `app/web/routes.py`, `app/api/assets_api.py`, `tests/test_import_asset_movements.py` (novo). NENHUM teste existente é modificado — `tests/test_import_asset_location.py` permanece integral (o comportamento de erro para local inexistente já é o exigido pela FR-013, ver D10 do research)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verificação do ambiente e scaffolding de testes antes de qualquer alteração

- [X] T001 [P] Verificar baseline da suíte antes de qualquer alteração: `python -m pytest tests/ -q` → esperado 565 passed / 0 failed (instalar `httpx2` no venv se o TestClient reclamar — dependência de ambiente, não do projeto); registrar o resultado como patamar de não regressão (Princípio VIII)
- [X] T002 [P] Criar scaffolding de testes em tests/test_import_asset_movements.py: helpers de apoio seguindo o padrão de tests/test_import_asset_location.py (`_criar_locais_base` estendido com colaboradores de apoio via modelo Custodian — ex.: "Mariana Souto Soares", "Micael de Araújo Silva"; construtores de CSV com colunas `tombamento;equipamento;categoria;Custodiante;localização`; import de `parse_csv`, `execute_import`, `MovementService`, `Movement`, `Asset`, `Custodian`) — sem cenários ainda

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Base compartilhada por TODAS as user stories: matriz consultável + coluna de custodiante parseada

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase (US1/US3/US4 dependem de `resolve_movement_type`; todas dependem da coluna `Custodiante` ser reconhecida pelo parser)

- [X] T003 [P] Escrever testes unitários da matriz em tests/test_import_asset_movements.py para `MovementService.resolve_movement_type` cobrindo TODAS as linhas da tabela de decisão do contrato C3 (specs/research R5): igual×igual → None; igual local + custodiante diferente → ALOCACAO_CAUTELA; local diferente + mesmo custodiante → TRANSFERENCIA_LOCAL; ambos diferentes → ALOCACAO_CAUTELA; estoque (None) → custodiante → ALOCACAO_CAUTELA; método é puro (não consulta DB, não muta nada). Executar e confirmar que FALHAM (função não existe)
- [X] T004 Implementar método estático puro `resolve_movement_type(current_location_id, current_custodian_id, dest_location_id, dest_custodian_id) -> Optional[MovementType]` em app/services/movement_service.py conforme contrato C3 — `create_movement` INTOCADO (nenhuma mudança de assinatura/validações VAL-002..VAL-008/termo/commit); documentar docstring com a tabela de decisão e a nota de que devolução (custodiante → estoque) está fora de escopo do CSV (R4)
- [X] T005 [P] Escrever teste de parse em tests/test_import_asset_movements.py: CSV com coluna `Custodiante` (e variações `colaborador`, `responsavel`, `custodian`) produz `row["custodiante"]` com o valor limpo; célula com só espaços (ex.: `" "`) vira string vazia — executar e confirmar FALHA (alias não existe)
- [X] T006 Adicionar entradas da coluna de custodiante em COLUMN_ALIASES em app/services/import_service.py: normalizadas para a chave canônica `custodiante` — `custodiante`, `custodian`, `colaborador`, `responsavel`, `responsável` (o normalizador existente trata espaços→underscore e acentos; reusar o mecanismo, sem lógica nova) — contrato C1

**Checkpoint**: Matriz consultável e coluna de custodiante parseada — user stories podem começar

---

## Phase 3: User Story 1 — Equipamento importado com colaborador e localização aparece no Fluxo (Priority: P1) 🎯 MVP

**Goal**: Bem novo importado com colaborador + localização fica `EM USO` com histórico correto no Fluxo: entrada real (sem snapshots fabricados) + ALOCACAO_CAUTELA via motor, termo sequencial padrão, operador = usuário autenticado

**Independent Test**: importar 1 linha com colaborador + localização e consultar o Fluxo do bem criado (service + timeline) — entrega valor isolado

### Tests for User Story 1 ⚠️ (escrever primeiro, confirmar FALHA)

- [X] T007 [P] [US1] Testes dos cenários A e L em tests/test_import_asset_movements.py: (A) `execute_import` de linha com colaborador+localização cria o bem com status IN_USE, custodian_id e location_id corretos; existem exatamente 2 movimentações — ENTRADA_AQUISICAO com snapshots reais (origem "Fornecedor / Entrada Inicial"/"Almoxarifado Geral", destino = local do CSV, operator_name do parâmetro, termo padrão TR-INIC) e ALOCACAO_CAUTELA com destination_custodian/location corretos, termo sequencial TR-{ano}-NNNNN (NUNCA "TR-CSV-"), operador = operator_name informado; (L) ambas recuperáveis via `MovementService.get_timeline_for_asset` (type 'movement', tipos corretos) sem alteração na consulta

### Implementation for User Story 1

- [X] T008 [US1] Reescrever o ramo de criação de bem novo em execute_import em app/services/import_service.py: (1) assinatura ganha `operator_name: Optional[str] = None` com fallback de compatibilidade `"Importação CSV"` (rotas sempre passam usuário autenticado — T010); (2) Asset criado com `status=AVAILABLE` e SEM custodian_id; (3) substituir a movimentação fabricada (D1: origem "Importação CSV"/"Sistema", TR-CSV) pela entrada padrão do cadastro manual (R1/contrato C2.3): `MovementType.ACQUISITION`, `origin_location_name="Fornecedor / Entrada Inicial"`, `origin_custodian_name="Almoxarifado Geral"`, destino = local resolvido do CSV ou "Estoque Central", `new_status=AVAILABLE`, `operator_name=operator_name`, termo `TR-INIC-{ano}-{asset.id:04d}`, reason patrimonial clara mencionando importação CSV; manter `db.flush()`
- [X] T009 [US1] Aplicar a custódia de bem novo via motor em execute_import em app/services/import_service.py (após T008): se o CSV informar custodiante resolvido → `MovementService.create_movement(db, MovementCreate(asset_id=..., movement_type=resolve_movement_type(None, None, location_id, custodian_id), destination_location_id=..., destination_custodian_id=..., reason=..., operator_name=operator_name, generate_term=True))` → status IN_USE + termo sequencial (R6/contrato C2.3); bem novo sem custodiante não gera movimentação de custódia
- [X] T010 [US1] Repasse do operador autenticado nas rotas (R8/contrato C4): em app/web/routes.py `confirm_import_assets` e em app/api/assets_api.py `import_csv_api` chamar `execute_import(rows, db, skip_duplicates=..., operator_name=(request.state.user.full_name or request.state.user.username))`; nenhuma outra mudança nas rotas — auditoria `write_audit(ACTION_IMPORT, ...)` permanece como está, APÓS execute_import
- [X] T011 [US1] Teste de integração do cenário J em tests/test_import_asset_movements.py (TestClient, padrão tests/test_api.py): usuário autenticado com permissão patrimonio.criar importa CSV via `POST /api/v1/assets/import/csv` → a ALOCACAO_CAUTELA gerada tem `operator_name == full_name (ou username)` do usuário logado; evento ACTION_IMPORT presente na auditoria; confirmar suíte parcial verde (T007–T010 passam)

**Checkpoint**: US1 completa e testável isoladamente — MVP validável (importar bem com custódia → Fluxo reconstrói a atribuição)

---

## Phase 4: User Story 2 — Importação sem colaborador/localização não inventa dados nem movimentações (Priority: P1)

**Goal**: Ausências combinadas produzem estado fiel ao CSV, sem falsa alocação/transferência, sem inventar colaborador/local; colaborador inexistente = erro de linha; comportamento de local inexistente verificado como já conforme à FR-013 (nenhum teste existente modificado)

**Independent Test**: importar linhas com ausências combinadas e verificar estado do bem + ausência de movimentações artificiais — independente de US1

### Tests for User Story 2 ⚠️ (escrever primeiro, confirmar FALHA onde aplicável)

- [X] T012 [P] [US2] Testes dos cenários B, C, D e I em tests/test_import_asset_movements.py: (B) linha com localização e sem custodiante → bem AVAILABLE com local, sem custodiante, NENHUMA ALOCACAO_CAUTELA/TRANSFERENCIA (apenas a ENTRADA); (C) linha com custodiante e sem localização → alocação acontece sem local de destino (o bem herda o local da entrada/estoque) e o motor valida; (D) linha sem custodiante e sem localização → apenas ENTRADA_AQUISICAO (destino "Estoque Central"), nada artificial; (I) bem importado como estoque/disponível não recebe custodiante indevido; células vazias e só-espaços tratadas como ausência; incluir caso de nome de colaborador duplicado no cadastro: resolução determinística pela menor id (order_by(Custodian.id) — remediação C1) quando matrícula não é informada
- [X] T013 [US2] Testes de erro de linha em tests/test_import_asset_movements.py (arquivo novo; NENHUM teste existente é modificado — remediação I1 do analyze: o comportamento de local inexistente já é o exigido pela FR-013 e já está coberto por `test_import_localizacao_valida_nao_importa_com_local_inexistente` em tests/test_import_asset_location.py, que permanece verde sem alteração): (FR-012) CSV com colaborador inexistente → erro "Linha {i}: colaborador 'X' não encontrado no cadastro de colaboradores", bem NÃO criado, sem movimentação; (FR-013) regressão passiva: coluna de localização reconhecida com valor inexistente continua gerando erro de linha e bem não criado (assercão duplicada no arquivo novo por rastreabilidade, sem tocar o arquivo existente)

### Implementation for User Story 2

- [X] T014 [US2] Implementar resolução do custodiante em execute_import em app/services/import_service.py: ler `row.get("custodiante")` (strip; vazio = ausente); resolução pelo cadastro existente — precedência por `registration_code` quando o CSV informar matrícula (identificador oficial, único); senão `Custodian.name` com match exato (ilike) **com `order_by(Custodian.id)`** para primeira ocorrência determinística entre bancos em caso de nomes duplicados (R2/contrato C2.1, remediação C1 do analyze); não encontrado → `errors.append(f"Linha {i}: colaborador '{x}' não encontrado no cadastro de colaboradores")` + pular linha (sem criar bem); NUNCA criar colaborador (FR-001/FR-012)
- [X] T015 [US2] Verificar coerência do comportamento de local em execute_import em app/services/import_service.py (remediação I1: o erro/pulo da linha para local não resolvido já existe e atende à FR-013 — manter sem modificação semântica): garantir que a entrada com local ausente usa destino "Estoque Central" apenas quando o CSV NÃO informa local (coerência com T008/T012 — sem caminho duplo conflitante); garantir que nenhuma linha sem custodiante gera movimentação de custódia (cobre T012/T013)

**Checkpoint**: US1+US2 completas — importação fiel ao CSV, sem dados falsos, Fluxo correto nos dois sentidos (com/sem custódia)

---

## Phase 5: User Story 3 — Reimportação idêntica não duplica movimentações (Priority: P1)

**Goal**: Reprocessar a mesma linha (mesmo colaborador, mesma localização) não cria movimentação nova; histórico intacto; sem erro falso ao operador

**Independent Test**: importar a mesma linha 2× e contar movimentações do bem — independente das demais stories

### Tests for User Story 3 ⚠️ (escrever primeiro, confirmar FALHA)

- [X] T016 [P] [US3] Testes do cenário E em tests/test_import_asset_movements.py: importar linha com colaborador+localização, depois reimportar a MESMA linha com `skip_duplicates=False` → contagem de movimentações do bem inalterada (1 ENTRADA + 1 ALOCACAO), `result["errors"] == []` (sem VAL-002 vazando como erro falso), histórico anterior intacto (mesmos ids/tipos); com `skip_duplicates=True` → linha contada em `skipped` e nenhuma movimentação

### Implementation for User Story 3

- [X] T017 [US3] Implementar verificação de mudança efetiva no ramo de atualização de execute_import em app/services/import_service.py: comparar `asset.location_id`/`asset.custodian_id` atuais × destino do CSV via `MovementService.resolve_movement_type`; `None` → NENHUMA movimentação e nenhum erro (FR-015/R7); destino sem custodiante na reimportação = manter custódia atual (R4 — nunca chamar o motor para devolução via CSV)

**Checkpoint**: US1–US3 completas — reimportação segura (idempotente em histórico)

---

## Phase 6: User Story 4 — Reimportação com mudança real gera o histórico correto (Priority: P2)

**Goal**: Mudança real de colaborador/localização na reimportação aplica a matriz existente e preserva o histórico anterior

**Independent Test**: importar linha, reimportar com outro colaborador/local e conferir a sequência do histórico — independente das stories 1–3

### Tests for User Story 4 ⚠️ (escrever primeiro, confirmar FALHA)

- [X] T018 [P] [US4] Testes dos cenários F, G e H em tests/test_import_asset_movements.py: (F) mudança de colaborador → nova ALOCACAO_CAUTELA para o novo colaborador (termo sequencial), movimentação anterior PRESERVADA no histórico, status IN_USE; (G) mudança só de local com mesmo custodiante → TRANSFERENCIA_LOCAL, local atualizado, histórico intacto; (H) mudança de colaborador e localização simultânea → matriz entrega ALOCACAO_CAUTELA (VAL-007, com termo); em todos: operador = usuário da reimportação, sem duplicação indevida

### Implementation for User Story 4

- [X] T019 [US4] Implementar aplicação da custódia na reimportação em execute_import em app/services/import_service.py (após T017): se `resolve_movement_type` devolver tipo → `MovementService.create_movement(...)` com o tipo resolvido, destino do CSV, reason clara (mudança via importação CSV), operator_name do usuário, `generate_term=True` para ALOCACAO_CAUTELA (R7/contrato C2.4); `None` → nada (T017); histórico anterior intacto por construção (append-only)

**Checkpoint**: US1–US4 completas — ciclo de vida completo via CSV com histórico fiel

---

## Phase 7: User Story 5 — Consistência transacional entre cadastro e histórico (Priority: P2)

**Goal**: Falha na criação da movimentação não deixa estado parcial; linha reportada como erro; demais linhas seguem o comportamento do lote

**Independent Test**: forçar falha em create_movement e verificar que o bem não fica alocado sem movimentação — independente das demais stories

### Tests for User Story 5 ⚠️ (escrever primeiro, confirmar FALHA)

- [X] T020 [P] [US5] Testes do cenário K em tests/test_import_asset_movements.py: monkeypatch de `MovementService.create_movement` para levantar `ValueError` (falha simulada na movimentação) → resultado da importação reporta a linha em `errors`, o bem da linha NÃO fica com custodian_id/location_id/status alterados sem a movimentação (sem alocação órfã), as demais linhas do lote são processadas normalmente (contrato do resultado preservado)

### Implementation for User Story 5

- [X] T021 [US5] Implementar unidade transacional por linha em execute_import em app/services/import_service.py (R3/contrato C2): `db.commit()` após cada linha processada com sucesso (fecha a unidade bem+entrada+custódia; `create_movement` já comita a movimentação — D4); em qualquer erro da linha (resolução, exceção do motor) → `db.rollback()` + `errors.append("Linha {i}: {msg}")` + `continue`; comportamento do lote preservado (linhas boas não são perdidas por linha ruim); remover o commit único de fim de lote, mantendo a captura de erro de commit do lote na rota/service onde ainda aplicável (verificar chamadas em tests/ existentes)

**Checkpoint**: Todas as 5 user stories completas — correção estrutural integral com consistência garantida

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validação final, documentação e conformidade

- [X] T022 Executar a suíte completa `python -m pytest tests/ -q`: esperado baseline 565 + novos testes verdes, ZERO falhas (nenhum teste existente é modificado ou enfraquecido — remediação I1: `tests/test_import_asset_location.py` permanece integral, 13 testes); conferir que `tests/test_import_asset_location.py`, `tests/test_movements.py`, `tests/test_api.py`, `tests/test_rbac.py` etc. seguem verdes
- [X] T023 [P] Atualizar documentação na mesma tarefa (Constitution XI): README.md e docs/ARQUITETURA_E_MANUTENCAO.md — seção de importação CSV de equipamentos: coluna `Custodiante`/`colaborador` suportada (resolução pelo cadastro, erro se inexistente), histórico patrimonial gerado no Fluxo (entrada + alocação/cautela via motor), termo sequencial padrão, operador = usuário autenticado, reimportação idêntica não duplica histórico; marcar como verificado no código (nada de comportamento não implementado)
- [X] T024 Executar a validação ponta a ponta do quickstart.md (specs/029-importacao-csv-fluxo/quickstart.md): gate da suíte (§1) + cenário manual 2.1–2.3 (4 bens TESTE029A–D, termo TR-2026-XXXXX, reimportação idêntica e com mudança, erro de colaborador inexistente, auditoria ACTION_IMPORT, timeline via API) + checklist de não regressão visual (§3); registrar resultados
- [X] T025 Verificação final de conformidade: mapear critérios de aceite SC-001..SC-007 e FR-001..FR-024 da spec.md aos testes implementados (cenários A–L); rodar o checklist da Constitution (Princípios I–XII) — escopo, regras nos services, movimentações pelo motor, zero credenciais, banco intocado, testes verdes, documentação fiel; registrar no relatório de conclusão

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — T001/T002 imediatos e paralelos
- **Foundational (Phase 2)**: depende de T002 (scaffolding de testes); T003→T004 (matriz), T005→T006 (alias) podem intercalar; BLOQUEIA todas as stories
- **US1 (Phase 3)**: depende da Phase 2 completa; ordem interna T007 → T008 → T009 → T010 → T011
- **US2 (Phase 4)**: depende de US1 (T014/T015 modificam o mesmo ramo já reescrito por T008/T009); T012/T013 antes de T014/T015
- **US3 (Phase 5)**: depende de US2 (o ramo de atualização é tocado depois do de criação); T016 → T017
- **US4 (Phase 6)**: depende de US3 (T019 estende a verificação de T017); T018 → T019
- **US5 (Phase 7)**: depende de US1–US4 (fecha a unidade transacional sobre o fluxo completo); T020 → T021
- **Polish (Phase 8)**: depende de todas as stories (T022 → T023/T024 → T025)

### User Story Dependencies

- **US1 (P1)**: foundational → implementação própria; nenhuma dependência de outras stories
- **US2 (P1)**: estende o ramo de criação de US1 com regras de ausência/erro; testes independentes dos de US1
- **US3 (P1)**: independente em comportamento (ramo de atualização), sequencial em arquivo com US1/US2
- **US4 (P2)**: estende US3 (mesma verificação, saída com movimentação)
- **US5 (P2)**: fecha a transacionalidade sobre todos os caminhos anteriores

### Within Each User Story

- Testes PRIMEIRO (confirmar FALHA), depois implementação, depois teste de integração (quando houver)
- Services antes das rotas (T008/T009 antes de T010)
- Story completa antes da próxima prioridade

### Parallel Opportunities

- T001 ∥ T002 (setup)
- T003→T004 ∥ T005→T006 (foundational: arquivos/aspectos diferentes — tests/movement_service vs tests/import_service aliases)
- T007 ∥ T012/T016/T018/T020 são testes de stories diferentes — MAS compartilham tests/test_import_asset_movements.py: escrevê-los em sequência (mesmo arquivo); o [P] indica ausência de dependência lógica, não de arquivo
- T023 ∥ T024 (polish, arquivos diferentes)
- Implementação de import_service.py é ESTRITAMENTE sequencial (T008→T009→T014/T015→T017→T019→T021) — evitar conflitos de merge

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) + Phase 2 (Foundational)
2. Phase 3 (US1) — T007..T011
3. **STOP and VALIDATE**: importar CSV com colaborador+localização e conferir Fluxo/termo/operador (quickstart §2.2 passos 1–5)
4. MVP entrega o cerne da inconsistência corrigida

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → validar (Fluxo reconstrói atribuição)
3. US2 → validar (nada inventado; erros de linha claros)
4. US3 → validar (reimportação idempotente)
5. US4 → validar (mudanças reais via matriz)
6. US5 → validar (falha sem estado parcial)
7. Polish → suíte verde + docs + quickstart completo

### Notes

- `create_movement` é INTOCADO em todas as tarefas (contrato C3) — qualquer necessidade de alterá-lo é sinal de desvio do plano e deve ser escalada
- Nenhum DDL; nenhuma rota nova; nenhuma permissão nova
- Commit sugerido por tarefa ou grupo lógico (Constitution XII: validação antes de declarar concluída)
