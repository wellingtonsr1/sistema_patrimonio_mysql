"""Configuração Jinja2 + injeção global de variáveis — Feature 051.

Módulo SEM dependência de domínios: pode ser importado por todos os
routers e pelo facade sem risco de import circular (FR-004: a
configuração ocorre exatamente UMA vez, aqui; o facade re-exporta
`templates` para os consumidores históricos — main.py, admin_routes,
help_routes).
"""
import logging
from datetime import datetime
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.config import APP_NAME, APP_VERSION, COMPANY_NAME
from app.utils.time_utils import utc_to_recife
from app.services.custodian_service import CustodianService
from app.services.audit_service import action_label
from app.services.permission_service import get_user_permission_names, get_user_role_names

# Configuração do Jinja2 Templates
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _inject_current_user(request: Request) -> dict:
    """
    Disponibiliza o usuário autenticado, seus perfis e suas permissões para
    todos os templates (menu dinâmico, botões condicionais via `can()`).

    As permissões/perfis são pré-computados pelas dependências de auth
    (request.state._permissions/_roles). O fallback abre uma sessão própria
    apenas se ainda não houver cache (defensivo, com tolerância a falhas).
    """
    user = getattr(request.state, "user", None)
    permissions = set(getattr(request.state, "_permissions", None) or set())
    roles = list(getattr(request.state, "_roles", None) or [])
    if user is not None and not getattr(request.state, "_permissions", None):
        try:
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                permissions = get_user_permission_names(db, user)
                roles = get_user_role_names(db, user)
            finally:
                db.close()
        except Exception:
            permissions, roles = set(), []
    return {
        "current_user": user,
        "user_permissions": permissions,
        "user_roles": roles,
        "can": lambda perm: perm in permissions,
        # Feature 010: delega ao serviço (fonte única: ^PROV-\d{6}$)
        "is_provisional": CustodianService.is_provisional,
    }


templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR),
    context_processors=[_inject_current_user],
)

logger = logging.getLogger("sispatrimonio.web")

# Injeta variáveis globais nos templates
templates.env.globals["app_name"] = APP_NAME
templates.env.globals["app_version"] = APP_VERSION
templates.env.globals["company_name"] = COMPANY_NAME
templates.env.globals["current_year"] = datetime.now().year
templates.env.globals["action_label"] = action_label
# Feature 004 — mecanismo central de apresentação (UTC -> America/Recife)
templates.env.filters["localtime"] = utc_to_recife
templates.env.globals["localtime"] = utc_to_recife
