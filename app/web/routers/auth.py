"""Router: AUTENTICAÇÃO (páginas de login/logout) — Feature 051.

Conteúdo movido LITERALMENTE de `app/web/routes.py` (L214–354).
`web_router` é incluído pelo facade na posição original (FR-005).
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import AUTH_COOKIE_NAME
from app.database import get_db
from app.api.deps import _client_ip, get_current_user
from app.services.ad_service import (
    ADAuthenticationError,
    ADNoProfileError,
    ADUnavailableError,
)
from app.services.auth_provider import resolve_authentication
from app.services.auth_service import AccountLockedError
from app.services.audit_service import (
    ACTION_LOGIN,
    ACTION_LOGIN_FAILED,
    ACTION_LOGIN_LOCKED,
    ACTION_LOGOUT,
    RESULT_FAILURE,
    RESULT_LOCKED,
    RESULT_SUCCESS,
    write_audit,
)
from app.services.session_service import (
    clear_session_cookie,
    create_session,
    revoke_session,
    set_session_cookie,
)
from app.web.routers.templates_env import templates

logger = logging.getLogger("sispatrimonio.web")

web_router = APIRouter(include_in_schema=False)


def _safe_next_url(value: str) -> str:
    """Permite apenas redirecionamentos internos (evita open redirect)."""
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"


@web_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "", db: Session = Depends(get_db)):
    """Exibe a tela de login. Se já autenticado, redireciona para a home."""
    if get_current_user(request, db):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"next": next, "error": ""},
    )


@web_router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
    db: Session = Depends(get_db),
):
    """Processa o login via formulário e estabelece a sessão."""
    ip = _client_ip(request)
    ad_error_message = None
    try:
        user = resolve_authentication(db, username, password)
    except (ADUnavailableError, ADAuthenticationError, ADNoProfileError) as ad_exc:
        # Erros específicos da integração AD: mensagem clara e genérica ao
        # usuário; detalhes técnicos ficam apenas no log do servidor.
        user = None
        ad_error_message = str(ad_exc)
        logger.warning("Falha de login AD para '%s': %s", username, type(ad_exc).__name__)
    except AccountLockedError:
        write_audit(
            db,
            user=None,
            username=username,
            action=ACTION_LOGIN_LOCKED,
            module="Autenticação",
            resource="Login",
            resource_ref=username,
            ip_address=ip,
            result=RESULT_LOCKED,
            description="Login bloqueado por excesso de tentativas",
        )
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "next": next,
                "error": "Conta temporariamente bloqueada por excesso de tentativas de login. Tente novamente mais tarde.",
            },
        )

    if not user:
        if ad_error_message:
            # Falha específica do AD (indisponibilidade, credencial ou perfil):
            # mensagem já amigável; a auditoria específica foi registrada no
            # serviço da integração. Não duplica LOGIN_FALHA local.
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"next": next, "error": ad_error_message},
            )
        write_audit(
            db,
            user=None,
            username=username,
            action=ACTION_LOGIN_FAILED,
            module="Autenticação",
            resource="Login",
            resource_ref=username,
            ip_address=ip,
            result=RESULT_FAILURE,
            description="Tentativa de login com credenciais inválidas",
        )
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"next": next, "error": "Usuário ou senha inválidos"},
        )

    write_audit(
        db,
        user=user,
        action=ACTION_LOGIN,
        module="Autenticação",
        resource="Login",
        resource_ref=user.username,
        ip_address=ip,
        result=RESULT_SUCCESS,
        description="Login realizado com sucesso",
    )

    token = create_session(db, user.id)
    response = RedirectResponse(
        url=_safe_next_url(next), status_code=status.HTTP_303_SEE_OTHER
    )
    set_session_cookie(response, token)
    return response


@web_router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    """Revoga a sessão no servidor e remove o cookie."""
    user = get_current_user(request, db)
    write_audit(
        db,
        user=user,
        action=ACTION_LOGOUT,
        module="Autenticação",
        resource="Logout",
        resource_ref=user.username if user else None,
        ip_address=_client_ip(request),
        result=RESULT_SUCCESS,
        description="Logout realizado",
    )
    token = request.cookies.get(AUTH_COOKIE_NAME)
    revoke_session(db, token)
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookie(response)
    return response
