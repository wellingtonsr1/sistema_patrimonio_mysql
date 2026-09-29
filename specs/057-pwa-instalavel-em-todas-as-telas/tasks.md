# Tasks: 057-pwa-instalavel-em-todas-as-telas

**Input**: spec.md + plan.md de `specs/057-pwa-instalavel-em-todas-as-telas/`

## Phase 1: TDD

- [x] T001 RED: `tests/test_pwa_instalavel_057.py` (manifest no login; registro incondicional no base.html) — 2 failed registrados
- [x] T002 Diagnóstico documentado: DOM do login sem `<link rel="manifest">` (evidência da causa do "não é possível instalar")

## Phase 2: Implementação

- [x] T003 D1: `<link rel="manifest">` no `login.html`
- [x] T004 D2: registro incondicional do SW no `base.html`
- [x] T005 Nota no `docs/COLETA_OFFLINE.md` (instalação a partir de qualquer tela)

## Phase 3: Validação

- [x] T006 GREEN: arquivo novo 2/2; guardas 053 verdes (7/7 com test_sw)
- [x] T007 SC-003: suíte completa 893 passed / 0 failed
- [x] T008 SC-004: prova no navegador — login com manifest linkado + SW ativado (instalável)
- [x] T009 `validacao.md`
