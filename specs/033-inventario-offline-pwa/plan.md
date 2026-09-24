# Implementation Plan: Conferência de Inventário Offline — PWA + Service Worker + IndexedDB

**Branch**: `033-inventario-offline-pwa` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/033-inventario-offline-pwa/spec.md`

## Summary

Adicionar ao módulo de Inventário um modo de **coleta offline**: o usuário autorizado prepara, conectado, um pacote derivado do snapshot existente de bens esperados (`inventario_itens.expected_*`); sem conexão, realiza a conferência física (QR/tombamento) com os dados gravados no armazenamento local do navegador (IndexedDB) e uma fila de sincronização local; ao retornar à rede, as coletas são enviadas a novos endpoints em `/api/v1` que **revalidam tudo** e gravam **exclusivamente via `InventarioService.record_check` / `register_unlisted_asset`** (nenhum novo caminho de escrita patrimonial). Sincronização idempotente por `client_operation_id` gerado no dispositivo, parcial (reenvia só pendentes) e com conflitos preservados (nunca sobrescrita silenciosa) para reconciliação em área própria na tela do inventário. PWA mínimo (manifest + Service Worker com cache restrito e versionado) serve apenas a área de coleta offline. Decisões de spec aplicadas: C-1..C-5 e P-1..P-3.

## Technical Context

**Language/Version**: Python 3.10+ (backend); JavaScript vanilla ES2020+ no navegador (sem build step, padrão do projeto)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Pydantic v2 (backend); Jinja2 + Bootstrap 5 + QRCode.js (UI); **Service Worker + IndexedDB nativos do navegador** (sem biblioteca de banco local); BarcodeDetector API (leitura de QR, com fallback de digitação manual — ver research.md D1)

**Storage**: MariaDB (oficial, inalterado em semântica) + **1 tabela nova aditiva** (`inventario_offline_coletas` — registro de sync com idempotência/conflitos; o pacote é gerado on-demand do snapshot existente, sem tabela própria — research D9); IndexedDB no dispositivo (`sispatrimonio_offline`) como área temporária de coleta — **não é segunda base patrimonial**

**Testing**: pytest + TestClient (backend); testes JS offline validados por quickstart manual dirigido + testes de integração HTTP que simulam os fluxos (fila e persistência local testadas via cenários do quickstart; o pytest cobre todo o comportamento de servidor)

**Target Platform**: Linux server (Uvicorn atrás de Nginx, HTTPS externo); navegadores-alvo: Chrome/Edge atuais, inclusive Android (tablets de campo)

**Project Type**: web-application monolítica existente (FastAPI + Jinja2) — extensão incremental

**Performance Goals**: preparação de pacote ≤ 1 min para 1.000 bens (SC-001); coleta individual < 10 s offline (SC-002); sync de lote de 1.000 operações conclui com reenvio parcial correto (SC-005)

**Constraints**: nenhum cache de respostas sensíveis pelo Service Worker (FR-036); nenhuma credencial no IndexedDB (FR-031); coletas aceitas gravadas só pelos services existentes (FR-026/Princípios III e V); zero alteração em módulos não relacionados (FR-046/Princípio I); alterações de banco apenas aditivas idempotentes via `init_db` (Princípio VII)

**Scale/Scope**: 1 inventário até 1.000 itens por pacote; múltiplos dispositivos por inventário; ~10 arquivos novos + ~6 toques pontuais (ver Project Structure)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente / evolução incremental | ✅ PASS | Apenas extensão: 1 tabela nova, 1 router novo, 1 service novo, páginas novas; nenhum módulo existente reescrito; FR-046 lista os intocáveis |
| II | Arquitetura em camadas | ✅ PASS | Rotas novas autenticam/validam (Pydantic) e delegam ao service novo; service grava via services existentes |
| III | Regras de negócio nos services | ✅ PASS | Construção do pacote, validação de sync, idempotência e conflitos em `inventario_offline_service.py`; rotas não concentram regras |
| IV | Integridade patrimonial/movimentações | ✅ PASS | Nenhuma alteração de estado/local/custódia de bem: offline registra divergência, nunca movimenta; sem caminho que contorne o motor de movimentações (FR-013) |
| V | Integridade do Inventário | ✅ PASS | Gravação só via `record_check`/`register_unlisted_asset` (que já garantem "nunca altera Asset"); fechamento/ata inalterados; item não é marcado NAO_ENCONTRADO por omissão (FR-015) |
| VI | Segurança (auth, RBAC, AD) | ✅ PASS | `require_api_auth` (cookie de sessão — decisão C-1) + permissões `inventario.*` existentes (P-1); nada de credencial local (FR-031); IndexedDB sem segredos; Service Worker nunca cacheia respostas sensíveis (FR-036) |
| VII | MariaDB / alterações aditivas | ✅ PASS | 1 tabela nova + índices, criada pelo mecanismo `init_db`/migração idempotente existente; nenhuma coluna/remoção em tabelas existentes |
| VIII | Testes como não regressão | ✅ PASS | Novo `tests/test_inventario_offline.py` cobrindo os 19 cenários do SC-010; suíte existente intacta |
| IX | Auditoria | ✅ PASS | Eventos novos no `audit_service` existente (preparado/sync/conflito/rejeitado), sem credenciais (FR-044) |
| X | Interface consistente | ✅ PASS | Telas novas usam templates/Bootstrap/tema claro-escuro existentes; menu/navegação atuais não alterados além dos pontos previstos (botão "Preparar offline" na tela do inventário + seção "Conflitos offline") |
| XI | Documentação fiel | ✅ PASS | README + docs/INVENTARIO_TECNICO.md + artigo na central de ajuda atualizados na implementação (só o que for implementado) |
| XII | Fluxo por especificação | ✅ PASS | specify → clarify (C-1..C-5) → plan → tasks → implement |

**Gate: PASS** — sem violações; nada a registrar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/033-inventario-offline-pwa/
├── plan.md              # Este arquivo
├── research.md          # Phase 0: decisões (QR, SW, IDB, sync)
├── data-model.md        # Phase 1: entidades servidor + cliente
├── quickstart.md        # Phase 1: validação ponta a ponta
├── contracts/           # Phase 1: contratos da API offline
│   └── inventario-offline-contract.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── models/
│   └── inventario_offline.py            # NOVO: InventarioOfflineColeta (sync idempotente/conflitos)
├── database.py                          # TOQUE: registrar models (import)
├── services/
│   ├── inventario_offline_service.py    # NOVO: pacote, sync (idempotência/conflitos), reconciliação
│   └── audit_service.py                 # TOQUE: eventos INVENTARIO_OFFLINE_*
├── api/
│   ├── inventario_offline_api.py        # NOVO: router /api/v1/inventarios/{id}/offline/*
│   └── v1_router.py                     # TOQUE: include_router
├── web/
│   ├── routes.py                        # TOQUE: tela de coleta offline + seção Conflitos + botão Preparar
│   ├── templates/
│   │   ├── inventarios/offline.html     # NOVO: shell da coleta offline (cacheável)
│   │   ├── inventarios/view.html        # TOQUE: botão preparar + seção conflitos
│   │   └── base.html                    # TOQUE: registro do SW (páginas permitidas) + manifest link
│   └── static/
│       ├── js/inventario_offline.js     # NOVO: IndexedDB, fila, sync client
│       ├── js/qr_reader.js              # NOVO: leitor QR (BarcodeDetector + fallback manual)
│       ├── sw.js                        # NOVO: Service Worker (allowlist, cache versionado)
│       ├── manifest.webmanifest         # NOVO
│       └── icons/                       # NOVO: ícones PWA (identidade visual atual)
└── config.py                            # TOQUE: nada obrigatório (política de expiração é por estado, decisão P-2)

tests/
└── test_inventario_offline.py           # NOVO: 19 cenários + RBAC + auditoria + regressão local
```

**Structure Decision**: projeto único existente (padrão do repositório, `app/` em camadas); nenhuma nova top-level directory. Arquivos novos seguem as convenções vigentes (model por feature em `app/models/`, service por feature em `app/services/`, router por feature em `app/api/`, template + JS estático sem build).

## Complexity Tracking

> Sem violações de Constitution — seção vazia por decisão de gate PASS.
