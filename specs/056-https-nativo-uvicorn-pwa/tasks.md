# Tasks: 056-https-nativo-uvicorn-pwa

**Input**: spec.md + plan.md de `specs/056-https-nativo-uvicorn-pwa/`

## Phase 1: TDD

- [x] T001 RED: `tests/test_https_config_056.py` com os 4 testes estruturais (D4) — registrar falha inicial

## Phase 2: Implementação

- [x] T002 D1: env vars `APP_SSL_CERTFILE`/`APP_SSL_KEYFILE` em `app/config.py`
- [x] T003 D2: passagem condicional SSL no `run.py` + prints com esquema dinâmico
- [x] T004 D3: `scripts/gera_cert_dev.py` (CA + server cert com SAN do IP; idempotente; `--force`)
- [x] T005 D4/FR-004: `.gitignore` com `data/ssl/`
- [x] T006 FR-005: `docs/HTTPS_LOCAL.md` — seção "Windows nativo (uvicorn SSL)"

## Phase 3: Validação

- [x] T007 GREEN: arquivo de teste 4/4
- [x] T008 SC-003: gerar cert real; `openssl x509 -text` mostra SAN do IP; cadeia valida
- [x] T009 SC-001: instância HTTPS na 8443 → `curl -k https://localhost:8443/health` 200; 8000 segue HTTP idêntico
- [x] T010 SC-002: navegador em `https://localhost:8443` → `navigator.serviceWorker` definido + SW registra
- [x] T011 SC-004/SC-005: suíte 889/0; `git status` limpo com cert gerado
- [x] T012 `validacao.md`
