# Tasks: 053-correcao-respondwith-duplo-sw

**Input**: plan.md + spec.md de `specs/053-correcao-respondwith-duplo-sw/`

## Phase 1: TDD

- [x] T001 Criar `tests/test_sw_service_worker.py` com os testes estruturais D3 (respondWith único, v32, allowlist, /api/*, sem v31) e REGISTRAR a falha inicial (vermelho) dos testes 1–2
- [x] T002 Aplicar o fix em `app/web/static/js/sw.js`: `return;` após o `respondWith` do bloco `OFFLINE_NAV_RE` (FR-001) e `CACHE_VERSION` → `inventario-offline-v32` com changelog (FR-002)
- [x] T003 Rodar `tests/test_sw_service_worker.py` — verde (SC-001/SC-002)

## Phase 2: Validação

- [x] T004 Suíte completa vs. baseline (SC-003: apenas os 2 failures pré-existentes de `test_backup_externo.py` permitidos; patamar 861 passed)
- [x] T005 Grep de `inventario-offline-v31` no repositório = 0 ocorrências (SC-002); `git diff --stat` confinado a sw.js + teste novo + docs/spec (FR-004)
- [x] T006 Atualizar `docs/COLETA_OFFLINE.md` com nota da correção e da nova versão de cache
- [x] T007 Escrever `specs/053-correcao-respondwith-duplo-sw/validacao.md` (V1–V6) incluindo a pendência operacional de prova de campo (R2 da análise)
