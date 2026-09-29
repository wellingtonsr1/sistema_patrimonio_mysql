"""FACADE da Interface Web — Feature 051 (Refatoração Modular).

Antes da 051 este arquivo concentrava TODAS as rotas web (2.668 linhas,
10 domínios). Agora ele é o ponto de agregação e de compatibilidade:

1. `templates` (configuração Jinja2 + injeção global) é configurado UMA
   única vez em `app/web/routers/templates_env.py` (FR-004) e re-exportado
   aqui — consumidores históricos (`app.main`, `admin_routes`,
   `help_routes`) continuam importando `templates` e `web_router` deste
   módulo, sem edição.

2. `web_router` agrega os routers de domínio de `app/web/routers/` NA
   MESMA ORDEM das seções originais do arquivo (FR-005): o matching de
   rotas do FastAPI é ordenado e a ordem original é preservada.

3. Re-exports de compatibilidade (NR-002): símbolos que testes e outros
   módulos importavam daqui continuam resolvidos via facade.

As rotas em si vivem em `app/web/routers/<dominio>.py`, movidas
LITERALMENTE do conteúdo original (MOVER, NÃO REESCREVER).
"""
from fastapi import APIRouter

# Configuração única do Jinja2 (FR-004) — re-exportada abaixo.
from app.web.routers.templates_env import (  # noqa: F401
    TEMPLATES_DIR,
    logger,
    templates,
)

# Routers de domínio (Feature 051)
from app.web.routers import (  # noqa: E402
    assets,
    auth,
    custodians,
    dashboard,
    inventario,
    locations,
    maintenances,
    movements,
    reports,
    setup,
    shared,
)

web_router = APIRouter(include_in_schema=False)

# ============================================================================
# Ordem de inclusão = ordem original das seções do routes.py (FR-005):
# AUTENTICAÇÃO → DASHBOARD → BENS → MOVIMENTAÇÃO → COLABORADORES → LOCAIS →
# MANUTENÇÕES → RELATÓRIOS → PRIMEIRO ACESSO → INVENTÁRIO
# ============================================================================
web_router.include_router(auth.web_router)
web_router.include_router(dashboard.web_router)
web_router.include_router(assets.web_router)
web_router.include_router(movements.web_router)
web_router.include_router(custodians.web_router)
web_router.include_router(locations.web_router)
web_router.include_router(maintenances.web_router)
web_router.include_router(reports.web_router)
web_router.include_router(setup.web_router)
web_router.include_router(inventario.web_router)

# ============================================================================
# Re-exports de compatibilidade (NR-002) — símbolos consumidos de fora
# ============================================================================

# Primeiro acesso: `tests/test_setup_first_access.py` importa daqui.
from app.web.routers.setup import SETUP_CLAIM_ID, _claim_first_access, _first_access_enabled  # noqa: E402,F401

# Helpers 048 compartilhados: expostos pelo facade por compatibilidade.
from app.web.routers.shared import (  # noqa: E402,F401
    _apply_mapping_to_rows,
    _confirm_payload_rows,
    _dynamic_form,
    _mapping_samples,
    _read_csv_upload,
    _render_mapping_step,
    _render_smart_preview,
)

# Helpers de domínio reutilizados entre módulos (assets ↔ inventário).
from app.web.routers.auth import _safe_next_url  # noqa: E402,F401
from app.web.routers.inventario import user_has_permission_for  # noqa: E402,F401
from app.web.routers.assets import _asset_audit_snapshot  # noqa: E402,F401
from app.web.routers.custodians import _custodian_audit_snapshot  # noqa: E402,F401
