---

description: "Task list for feature implementation"
---

# Tasks: Backup Manual — Briefing Completo (Consolidação da 015)

**Input**: Design documents from `/specs/016-backup-manual-completo/`

**Prerequisites**: plan.md, spec.md (gap I1/I2/I3/T), research.md (R1–R9), data-model.md (BV-8..BV-11), contracts/service-contract.md, contracts/ui-contract.md, quickstart.md

**Tests**: Incluídos por exigência da spec (FR-010: testes A–J do §34). TDD: adaptar/escrever primeiro, garantir FALHA, depois implementar.

**Organization**: Por user story da spec. Foundation = constantes/regex/compat (bloqueia as stories); US1 = geração atômica v2 (gzip + SHA-256 + .part→renomear + log); US2 = falha literal (BACKUP_FALHA); US3 = listagem com Integridade/SHA-256; Polish = docs, escopo, relatório §39.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Projeto monolítico FastAPI existente: `app/services/`, `app/web/templates/`, `tests/` na raiz. Base: feature 015 em produção (suíte 385 passed).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline — nenhuma alteração de comportamento

- [x] T001 Rodar a suíte e registrar o baseline (`python3 -m pytest -q`): **385 passed + 1 falha pré-existente** `tests/test_rbac.py::test_lockout_after_failed_attempts` (fora do escopo — não corrigir, Princípio I). Confirmar os pontos da 015 que serão adaptados: `_BACKUP_NAME_RE` (linha 40), fluxo de `generate_backup`, fixture `_fake_dump`/`_clean_backup_dir` de `tests/test_backup_manual.py` (depends: none)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Constantes de auditoria + compatibilidade de formato — bloqueia TODAS as user stories

### Tests for Foundational (TDD — escrever primeiro, garantir FALHA)

- [x] T002 [P] Testes FALHANDO da compatibilidade em `tests/test_backup_manual.py`: regex/listagem aceita `.sql.gz` novo E `.sql` antigo (BV-10); `.part` NUNCA listado; `get_backup_path` serve ambos os sufixos e rejeita `.part` (research R7/R8) — cobre também a **US2b** (segurança de acesso/download) por regressão (remediação C1) (depends: T001)

### Implementation for Foundational

- [x] T003 [P] Adicionar em `app/services/audit_service.py`: `ACTION_BACKUP_FAILED = "BACKUP_FALHA"` + rótulo `"Backup Falhou"` em `ACTION_LABELS` — aditivo, eventos históricos intocados (research R5, I1)
- [x] T004 Atualizar `_BACKUP_NAME_RE` em `app/services/backup_service.py` para aceitar `\.sql(\.gz)?$` (grupos de data/hora/micros mantidos) — base da compatibilidade R7; `.part` segue fora do padrão (depends: T002)
- [x] T005 Checkpoint foundational: testes T002 verdes + suíte completa intacta (baseline RBAC exceto) (depends: T002, T003, T004)

**Checkpoint**: Foundation pronta — formato duplo reconhecido, constante de falha disponível

---

## Phase 3: User Story 1 — Geração atômica v2: gzip + SHA-256 + .part→renomear (Priority: P1) 🎯 MVP

**Goal**: Backup gerado em temporário único, comprimido (.sql.gz), íntegro (SHA-256), renomeado só após validação, com log técnico

**Independent Test**: `generate_backup` com executor fake → `backup_*.sql.gz` válido (gunzip legível), SHA-256 retornado/auditado, nenhum `.part` remanescente, nenhum momento com nome final incompleto

### Tests for User Story 1 (TDD — escrever primeiro, garantir FALHA)

- [x] T006 [P] [US1] Testes FALHANDO da geração v2 em `tests/test_backup_manual.py` (contract §1, data-model BV-8/9/11): (a) sucesso → arquivo final é gzip legível (blocos verificáveis), nome `.sql.gz`, retorno com `sha256`; recomputar SHA-256 do arquivo == retornado (Teste I); (b) **atomicidade**: o **executor fake captura o estado do diretório (`listdir` de `BACKUP_DIR`) dentro do callback** — durante a geração nenhum arquivo casa o regex final — e ao final nenhum `.part` existe (Teste G parcial; **remediação U1**: mecanismo de observação explícito); (c) auditoria `BACKUP_CRIADO` com `new_data.sha256`; (d) log técnico: caplog contém início/conclusão e não contém `MYSQL_PWD`/senha (Teste G/I — research R6) (depends: T005)
- [x] T007 [P] [US1] Testes FALHANDO web (Teste H literal) em `tests/test_backup_manual.py`: 2 POSTs `/admin/backups/gerar` (executor fake via monkeypatch de `_run_mysqldump`) → 2 arquivos `.sql.gz` distintos, listagem com os 2, nenhum sobrescreveu; download de um `.sql.gz` serve bytes íntegros (Testes A/C adaptados) (depends: T005)

### Implementation for User Story 1

- [x] T008 [US1] Implementar o fluxo v2 em `generate_backup` (`app/services/backup_service.py`, contract §1): temporário `<base>.part` → executor → compressão streaming `gzip.open` (blocos 1 MB) → validação (existe, tamanho > 0, gzip legível) → SHA-256 streaming → **renomear** para `.sql.gz` → `BACKUP_CRIADO` com `new_data.sha256`; logger de módulo (início/conclusão/falha — sem segredos); limpeza de `.part*` em qualquer falha (research R1/R2/R3/R6, I2+I3) (depends: T004, T006)
- [x] T009 [US1] Checkpoint US1 (MVP v2): testes T006/T007 verdes; suíte completa intacta (depends: T008)

**Checkpoint**: Geração v2 funcional — atômica, comprimida, íntegra, auditada e logada

---

## Phase 4: User Story 2 — Falha literal: BACKUP_FALHA sem falso sucesso (Priority: P1)

**Goal**: Qualquer falha grava `BACKUP_FALHA`/FALHA, mensagem segura, sem parcial, com diagnóstico no log

**Independent Test**: Executor falha → `BACKUP_FALHA` na trilha, `.part*` removido, nada listado, log com a exceção controlada

### Tests for User Story 2 (TDD — escrever primeiro, garantir FALHA)

- [x] T010 [P] [US2] Testes FALHANDO da falha literal em `tests/test_backup_manual.py` (Teste G do §34, contract §1): executor lança erro → evento `BACKUP_FALHA` (resultado FALHA) — não mais `BACKUP_CRIADO`/FAILURE; descrição segura; nenhum `.part*` nem arquivo final listado; log de erro presente sem segredos; segunda falha no meio da compressão (fake que grava gzip inválido) → idem (depends: T009)

### Implementation for User Story 2

- [x] T011 [US2] Alterar o ramo de falha de `generate_backup` (`app/services/backup_service.py`): evento `ACTION_BACKUP_FAILED` (I1) — limpeza `.part*` e mensagem segura já existentes são preservadas; diagnóstico via logger (depends: T008, T010)
- [x] T012 [US2] Checkpoint US2: testes T010 verdes; eventos antigos da 015 intocados na trilha (depends: T011)

**Checkpoint**: US1 + US2 — ciclo completo v2 com sucesso e falha literais

---

## Phase 5: User Story 3 — Listagem com Integridade e SHA-256 (Priority: P2)

**Goal**: Tela exibe Integridade (OK/—/CORROMPIDO) e SHA-256 por backup; compatibilidade `.sql` visível

**Independent Test**: Listagem com 1 `.sql` antigo + 1 `.sql.gz` novo → Integridade "—" e OK respectivamente; SHA-256 exibido apenas para o novo

### Tests for User Story 3 (TDD — escrever primeiro, garantir FALHA)

- [x] T013 [P] [US3] Testes FALHANDO da listagem v2 em `tests/test_backup_manual.py` (contract §3, ui-contract §1): `list_backups()` retorna `sha256` e `integrity` (`OK` para gzip válido; `—` para `.sql`; `CORROMPIDO` para gzip com trailer inválido — fixture grava bytes truncados); template renderiza as colunas Integridade/SHA-256 com os estados (depends: T009)

### Implementation for User Story 3

- [x] T014 [US3] Implementar a listagem v2 em `list_backups()` (`app/services/backup_service.py`, contract §3): campos aditivos `sha256` (streaming on-demand) e `integrity` (OK/—/CORROMPIDO por leitura/trailer gzip) + colunas no `app/web/templates/admin/backups.html` (ui-contract: badges e `title` com hash completo — nenhuma outra alteração visual) (depends: T013, T008)
- [x] T015 [US3] Checkpoint US3: testes T013 verdes; todas as stories (1–3) funcionais (depends: T014)

**Checkpoint**: Todas as user stories concluídas — backup v2 completo e visível

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentação, escopo, relatório §39 e validação final

- [x] T016 [P] Atualizar documentação (Princípio XI, quickstart DoD): README §💾 (backup comprimido `.sql.gz`, SHA-256, conteúdo do backup = dump do banco com inclusões/exclusões da Seção 1 da spec, compatibilidade `.sql` antigos) + central de ajuda em `app/services/help_service.py` (coerente com a tela v2)
- [x] T017 [P] Verificação estática de escopo via `git diff` (quickstart DoD; cobre **US2b** — remediação C1): alterações restritas a `backup_service.py`, `audit_service.py` (+2 linhas), `admin/backups.html` (colunas), `tests/test_backup_manual.py`, `README.md`, `help_service.py` — **rotas web, permissão, RBAC, models e demais módulos intocados**; `grep` garantindo nenhuma credencial em código/logs/eventos (Princípio VI)
- [x] T018 Validação final: executar o quickstart (§1 suíte; §2 testes A–J; §3 validação manual no MariaDB — com o usuário; §4 **Relatório Final Obrigatório §39** com as declarações explícitas RESTORE/AGENDAMENTO/RETENÇÃO/BANCO); re-verificar a Constitution (checklist do plan.md); marcar todas as tarefas `[X]` em `tasks.md` e reportar (depends: T015, T016, T017)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: imediato
- **Foundational (Phase 2)**: **BLOQUEIA as stories** (constante + regex dupla)
- **US1 (Phase 3)**: núcleo v2 (geração atômica)
- **US2 (Phase 4)**: depende de US1 (altera o ramo de falha do fluxo v2)
- **US3 (Phase 5)**: depende de US1 (listagem v2 dos arquivos gerados)
- **Polish (Phase 6)**: depende de todas

### Parallel Opportunities

- T002 (testes) e T003 (constante) — arquivos distintos
- T006/T007 (US1) — mesmo módulo de testes: sequencial na prática
- T016/T017 (polish) paralelos

## Implementation Strategy

### MVP First (Foundation + US1)

1. Phases 1–2: Setup + Foundation
2. Phase 3: US1 — geração v2 completa (atômica + gzip + SHA-256 + log)
3. **STOP and VALIDATE**: quickstart §3 (backup real no MariaDB com `.sql.gz` e checksum)

### Incremental Delivery

1. Foundation + US1 → geração v2 (MVP)
2. US2 → falha literal BACKUP_FALHA
3. US3 → listagem com Integridade/SHA-256
4. Polish → docs, escopo, relatório §39, DoD

### Notes

- TDD: cada bloco de testes escrito e FALHANDO antes da respectiva implementação
- Base da 015 preservada: rotas/permissão/RBAC/download intocados; `.sql` antigos continuam funcionando (R7)
- O relatório final (§39 do briefing) é entregável do T018 — não opcional
- Commit após cada checkpoint
