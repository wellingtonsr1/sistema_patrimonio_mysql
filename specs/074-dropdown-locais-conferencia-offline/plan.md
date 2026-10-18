# Implementation Plan: Dropdown de Locais Cadastrados na Conferência Offline

**Branch**: `074-dropdown-locais-conferencia-offline` | **Date**: 2026-10-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/074-dropdown-locais-conferencia-offline/spec.md`

## Summary

Substituir o campo de texto livre "Local onde foi encontrado" da Conferência Offline (`app/web/templates/inventarios/offline.html`) por um `<select>` com os locais cadastrados, **reutilizando o mecanismo de armazenamento local do inventário**: o catálogo de locais (`id` + `name`) passa a ser incluído no **pacote offline** gerado por `InventarioOfflineService.generate_package` e persistido, junto com o restante do pacote, no IndexedDB `sispatrimonio_offline` (store `packages`) via `savePackage()`/`getPackage()` — sem novo banco local, sem novo store, sem nova rotina de sincronização.

A coleta offline passa a gravar `found_location_id` (campo **já suportado** pelo contrato de sync: `InventarioOfflineService.process_sync` valida `db.get(Location, id)` e o cliente já envia o campo). **Nenhuma mudança no contrato de sync, no esquema do banco, na Conferência Online ou no fluxo do inventário.**

Diagnóstico completo (FR-013): ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.10+ (FastAPI, SQLAlchemy 2, Pydantic v2, Jinja2) + JavaScript vanilla ES2020+ (sem build step)

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2, PyMySQL (MariaDB), Jinja2 + Bootstrap 5 (`form-select`), Service Worker nativo

**Storage**: Servidor: MariaDB/MySQL (produção) / SQLite em testes. Dispositivo: IndexedDB `sispatrimonio_offline` **v1** com stores `packages` (keyPath `inventory_id`), `coletas`, `sync_queue`, `device_info` — **schema intocado**; o catálogo de locais vive como campo adicional do registro de pacote existente

**Testing**: pytest (+ TestClient do FastAPI); testes estáticos de template/acessibilidade já existentes

**Target Platform**: Navegadores desktop/móveis (PWA, HTTPS); funciona 100% offline após preparação do pacote

**Project Type**: Web application (server-rendered + PWA offline)

**Performance Goals**: catálogo de locais carregado junto do pacote (1 requisição existente); renderização nativa do `<select>` — sem índice, sem biblioteca

**Constraints**: offline-capable sem novas requisições durante a coleta; sem novas dependências; contrato de sync e esquema de banco intocados; re-preparo do pacote limitado a `MAX_PACKAGE_ITEMS` (1000) itens — inalterado

**Scale/Scope**: base existente de locais (`locations`), ordem de dezenas/centenas (mesmo `LocationService.get_all` usado pela Conferência Online); alterações restritas a **5 arquivos de código + 1 suíte de testes**

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio (Constitution) | Status | Evidência |
|---|---|---|
| I — Preservação e evolução incremental | ✅ PASS | Extensão **aditiva** do payload do pacote offline; escopo fechado de arquivos (ver Project Structure); nenhuma refatoração alheia; Conferência Online e inventário intocados |
| II — Arquitetura em camadas | ✅ PASS | A mudança de dado acontece no **service** (`InventarioOfflineService.generate_package`); a rota `POST .../offline/package` continua apenas delegando; a UI consome via cliente JS |
| III — Regras de negócio nos services | ✅ PASS | Validação do local permanece no servidor (`process_sync` → `InventarioService.record_check`); nenhum código de negócio novo em rota/template |
| IV — Integridade patrimonial e movimentações | ✅ PASS | Conferência continua apenas **registrando** divergência; cadastro/localização cadastral não é alterado; gravação segue o caminho oficial `record_check` |
| V — Integridade do inventário | ✅ PASS | Inventário não altera cadastro; snapshot do inventário permanece imune; validações de item/status inalteradas |
| VI — Segurança (authN/RBAC) | ✅ PASS | Nenhuma rota nova; endpoints existentes mantêm `require_permission("inventario.conferir"/"inventario.visualizar")`; catálogo de locais já é dado servido ao mesmo perfil; nenhuma credencial envolvida |
| VII — Banco de dados | ✅ PASS | **Zero** alteração de schema MariaDB; nada de migração |
| VIII — Testes | ✅ PASS | Suíte verde obrigatória; novos testes para pacote + dropdown + sync (ver quickstart.md) |
| IX — Auditoria | ✅ PASS | Sem operação de escrita nova: preparação do pacote continua auditada (`ACTION_INVENTARIO_OFFLINE_PREPARADO`); sync mantém auditoria existente |
| X — Interface consistente | ✅ PASS | Mesmo `form-select`/ Bootstrap 5 da Conferência Online; `label[for]`/`id` conforme acessibilidade (spec 069); temas claro/escuro preservados |
| XI — Documentação fiel | ✅ PASS | Central de ajuda (`help_service.py`) atualizada: "informe o local" → "selecione o local no dropdown" |
| XII — Desenvolvimento por spec | ✅ PASS | Fluxo specify → clarify → plan; este plano precede qualquer código |

**Gates: PASS — 0 violações.** Nenhuma justificativa pendente (Complexity Tracking vazio).

## Project Structure

### Documentation (this feature)

```text
specs/074-dropdown-locais-conferencia-offline/
├── plan.md              # Este arquivo
├── research.md          # Phase 0 — diagnóstico técnico (FR-013) + decisões
├── data-model.md        # Phase 1 — entidades e formatos
├── quickstart.md        # Phase 1 — guia de validação
├── contracts/           # Phase 1 — extensão do contrato do pacote offline
│   └── offline-package-locations-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado pelo /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── services/
│   └── inventario_offline_service.py   # ALTERADO: generate_package inclui "locations" [{id, name}]
├── web/
│   ├── templates/inventarios/
│   │   └── offline.html                # ALTERADO: input de texto → <select> + estados de lista indisponível/vazia
│   └── static/
│       ├── js/
│       │   └── sw.js                   # ALTERADO: bump CACHE_VERSION → inventario-offline-v35
│       └── ...                         # inventario_offline.js: NÃO alterado (já persiste/grava/envia found_location_id)
└── services/
    └── help_service.py                 # ALTERADO: texto da ajuda da conferência (dropdown)

tests/
└── test_dropdown_locais_offline_074.py # NOVO: contrato do pacote, UI do select, sync por id, retrocompat, estados

# Arquivos que NÃO mudam (confirmado por inspeção):
#   app/api/inventario_offline_api.py      — endpoints intactos
#   app/services/inventario_service.py     — record_check intacto
#   app/web/routers/inventario.py          — rotas intactas (online e shell offline)
#   app/web/static/js/inventario_offline.js— savePackage/getPackage/registrarColeta/sincronizar já suportam found_location_id
#   app/models/* e migrations/*            — zero alteração de schema
#   app/web/templates/inventarios/detail.html, conferir.html — Conferência Online intocada
```

**Structure Decision**: projeto único (web app server-rendered + PWA). As alterações seguem as camadas existentes: **service** (fonte do catálogo) → **pacote offline** (transporte + persistência reutilizadas) → **template offline** (dropdown). O núcleo cliente `inventario_offline.js` não precisa de mudança: `savePackage` persiste o pacote inteiro (novos campos incluídos), `registrarColeta` já aceita `foundLocationId` e `sincronizar` já envia `found_location_id`/`found_location_name`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nenhuma violação | — | — |
