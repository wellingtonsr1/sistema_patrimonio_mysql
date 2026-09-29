# Tasks: 055-fix-testes-backup-externo-plataforma

**Input**: spec.md + plan.md de `specs/055-fix-testes-backup-externo-plataforma/`

## Phase 1: Diagnóstico

- [x] T001 Tracebacks completos dos 2 failures + leitura do service (etapa 6 da cópia mapeia PermissionError → REASON_SEM_PERMISSAO) + prova empírica da premissa POSIX no Windows
- [x] T002 Classificação: premissa de teste desatualizada — nenhum bug de produção (FR-002)

## Phase 2: Implementação

- [x] T003 Helper `_bloquear_escrita(dest) -> liberar()` cross-platform (D1) + imports
- [x] T004 Aplicar nos 2 pontos de uso (test_destino_sem_permissao e bloco F de test_zero_segredos_em_logs) sem tocar assertions (D2)

## Phase 3: Validação

- [x] T005 SC-001: `pytest tests/test_backup_externo.py` → 20 passed (0 failed)
- [x] T006 SC-002: suíte completa → 0 failed (889 passed)
- [x] T007 SC-003/SC-004: `git diff --stat` confinado; assertions intactas
- [x] T008 README: nota da 045 atualizada (fim das falhas conhecidas)
- [x] T009 Escrever `validacao.md`
