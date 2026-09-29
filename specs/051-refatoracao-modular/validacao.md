# Registro de Validação — Feature 051 (Constituição XII / T019)

**Data**: 2026-09-28 · **Feature**: Refatoração Modular — Rotas Web e Backup Service
**Método**: movimentação literal (MOVER, NÃO REESCREVER) + inventário de rotas como prova de não-regressão + suíte completa por fase.

## Baseline (T001)

- **Suíte completa pré-refatoração: 863 passed / 0 failed** (97s, SQLite in-memory).
- Nota: as 2 falhas pré-existentes de `test_backup_externo.py` citadas no plan não se verificam no repo atual — baseline é 100% verde.

## T002 — Manifesto de rotas

- `tests/test_route_inventory.py` + `tests/route_manifest.json` gerados do código PRÉ-refatoração.
- **140 rotas** (path + methods + endpoint name).
- Adaptação técnica: nesta versão do FastAPI, `include_router` registra `_IncludedRouter` lazy — o walker desce recursivamente por `original_router.routes`.

## Execução por fase

| Fase | Conteúdo | Resultado |
|---|---|---|
| F1 | `routers/shared.py` (helpers 048) + núcleo do facade | ✅ |
| F2 | `routers/auth.py` + `routers/setup.py` | ✅ |
| F3 | `routers/dashboard.py` + `routers/reports.py` | ✅ |
| F4 | `routers/movements.py` | ✅ |
| F5 | `routers/custodians.py` | ✅ |
| F6 | `routers/locations.py` | ✅ |
| F7 | `routers/maintenances.py` | ✅ |
| F8 | `routers/inventario.py` | ✅ |
| F9 | `routers/assets.py` | ✅ |
| B1 | backup_service — **Amendment A1**: módulo único + mapa de navegação | ✅ |

## Achados do implement (documentados na spec/plan)

### 1. Import circular resolvido com `routers/templates_env.py`

A primeira versão do facade importava os domínios, que importavam `templates` do facade → ciclo. Solução: configuração Jinja2 + injeção global movida para `routers/templates_env.py` (sem dependência de domínios); facade e routers importam de lá. FR-004 preservado: configuração ocorre exatamente uma vez.

### 2. Amendment A1 — decomposição física do backup_service REJEITADA (evidência)

Levantamento antes de mover: **42 pontos** de `monkeypatch.setattr(backup_service, ...)`/leitura direta nos testes (`SessionLocal`, `DATABASE_URL`, `BACKUP_DIR`, `MYSQLDUMP_PATH`, `BACKUP_IMPORT_TIMEOUT`, `drain_engine`, `maintenance_mode`, `_RESTORE_IN_PROGRESS`, `_run_mysqldump`, `_run_mysql_import`, `write_audit`, `subprocess`, `shutil`, `_BACKUP_NAME_RE`, `_RESTORE_LOCK`, `_maintenance_set`, `_import_with_deadline`, `_sanitize_stderr`). Funções resolvem globais no módulo onde são definidas: o split faria os patches deixarem de ser vistos, quebrando ~40 testes (NR-002) ou exigindo reescrita interna (viola movimentação literal/FR-009). **Decisão (Constituição I)**: módulo único, mapa de navegação por seções no docstring (+27 linhas, zero código alterado). Spec FR-007/SC-003 ajustados; decomposição física registrada como spec futura condicionada.

### 3. Assertion de inspeção da 050 ajustada (NR-002 — import apenas)

`tests/test_location_nomenclatura_050.py::test_048_rotas_e_execute_intocados` inspeciona o FONTE de `routes` e exige os decoradores de `/locations/import`. Com a movimentação para `routers/locations.py`, a assertion foi ajustada para concatenar o fonte do módulo do domínio — as strings verificadas (`'@web_router.post("/locations/import"'`) permanecem idênticas. Único teste existente editado; nenhum assertion de comportamento alterado.

### 4. `locais.csv` de docs revertido

Alteração pré-existente na working tree (arquivo de dados do usuário, fora do escopo da 051) revertida com `git checkout --`.

## Provas finais

| Prova | Resultado |
|---|---|
| SC-001 — inventário de rotas | **140/140 idênticos** ao manifesto pré-refatoração |
| SC-002 — suíte final | **879 passed / 0 failed** (baseline 863 + 16 testes novos da 051) |
| SC-003 — limites | `routes.py` **86 linhas** (≤200); maior módulo novo: `routers/inventario.py` 529 (≤800, FR-011); backup_service módulo único por A1 |
| SC-004 — consumidores intocados | `git diff --stat` em `main.py`, `admin_routes.py`, `help_routes.py`: **0 alterações** |
| SC-005 — ciclo sensível backup/restore | `test_backup_restore.py` 46 passed; suíte de backup completa verde (inclui TestClient 019) |
| T013 — RBAC | `test_rbac.py` **30 passed** (decorators de permissão sobreviveram à movimentação) |
| T020 — canário de imports | `test_routers_structure.py` 15 módulos importados isoladamente — verde |
| T021 — varredura de consumidores | Todos os `from app.web.routes import` resolvem via facade; nenhum consumidor editado |

## Novos arquivos

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `app/web/routers/__init__.py` | 6 | Pacote |
| `app/web/routers/templates_env.py` | 74 | Config Jinja2 única (FR-004) |
| `app/web/routers/shared.py` | 324 | Helpers 048 (movidos) |
| `app/web/routers/auth.py` | 173 | Login/logout + `_safe_next_url` |
| `app/web/routers/dashboard.py` | 24 | Dashboard |
| `app/web/routers/setup.py` | 220 | Primeiro acesso |
| `app/web/routers/assets.py` | 502 | Bens + etiquetas + importação |
| `app/web/routers/movements.py` | 182 | Movimentações |
| `app/web/routers/custodians.py` | 381 | Colaboradores |
| `app/web/routers/locations.py` | 243 | Locais |
| `app/web/routers/maintenances.py` | 122 | Manutenções |
| `app/web/routers/reports.py` | 112 | Relatórios |
| `app/web/routers/inventario.py` | 529 | Inventário + sw.js + offline |
| `tests/test_route_inventory.py` | 74 | Prova de não-regressão de rotas |
| `tests/route_manifest.json` | — | Manifesto 140 rotas |
| `tests/test_routers_structure.py` | 36 | Canário de imports circulares |

`app/web/routes.py`: 2.668 → **86 linhas**. `backup_service.py`: 1.381 → 1.408 (só docstring/mapa A1).
