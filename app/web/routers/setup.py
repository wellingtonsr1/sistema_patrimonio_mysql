"""Router: PRIMEIRO ACESSO / CONFIGURAÇÃO INICIAL — Feature 051.

Conteúdo movido LITERALMENTE de `app/web/routes.py` (L1978–2167).
`web_router` é incluído pelo facade na posição original (FR-005).
`_claim_first_access` é re-exportado pelo facade (consumido por testes).
"""
import logging

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.config import AUTH_ADMIN_PASSWORD
from app.database import get_db
from app.api.deps import _client_ip
from app.models.setup_claim import SetupClaim
from app.models.user import User
from app.models.user_role import UserRole
from app.services.auth_service import create_user
from app.services.permission_service import (
    assign_role,
    ensure_default_roles,
    get_role_by_name,
)
from app.services.audit_service import (
    ACTION_CREATE,
    RESULT_SUCCESS,
    write_audit,
)
from app.web.routers.templates_env import templates

logger = logging.getLogger("sispatrimonio.web")

web_router = APIRouter(include_in_schema=False)

# Identificador do singleton de reivindicação do primeiro acesso.
SETUP_CLAIM_ID = 1


def _first_access_enabled(db: Session) -> bool:
    """
    O fluxo de primeiro acesso só é ativado quando:
    - AUTH_ADMIN_PASSWORD não está configurada (o bootstrap por variável de
      ambiente não será preparado), E
    - ainda não existe nenhum usuário no banco.

    Esta é apenas a verificação de exibição/prescrição: ela não é suficiente
    sozinha para autorizar a criação do administrador, pois duas requisições
    concorrentes poderiam vê-la verdadeira ao mesmo tempo. A exclusividade é
    garantida por `_claim_first_access`, que reivindica o bootstrap com uma
    escrita atômica antes de criar o usuário.
    """
    if AUTH_ADMIN_PASSWORD:
        return False
    return db.query(User).first() is None


def _claim_first_access(db: Session) -> bool:
    """
    Reivindica atomicamente o primeiro acesso.

    Insere o registro singleton (`setup_claims.id = 1`): a chave primária é a
    garantia de exclusividade, pois apenas uma requisição consegue inserir a
    linha. Quem chega primeiro segue para a criação do administrador no mesmo
    commit; as concorrentes caem em violação de unicidade (`IntegrityError`) ou
    em bloqueio de escrita (`OperationalError`) e recebem False.

    A reivindicação não é confirmada enquanto `db.commit()` não acontece: se a
    criação do administrador falhar, o `db.rollback()` libera o registro e o
    primeiro acesso volta a ficar disponível.
    """
    db.add(SetupClaim(id=SETUP_CLAIM_ID))
    try:
        db.flush()
    except (IntegrityError, OperationalError):
        db.rollback()
        return False
    return True


@web_router.get("/setup", response_class=HTMLResponse)
def first_access_page(
    request: Request, db: Session = Depends(get_db)
):
    """Tela de configuração inicial. Só visível em instalação nova."""
    if not _first_access_enabled(db):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="setup.html",
        context={"error": ""},
    )


@web_router.post("/setup", response_class=HTMLResponse)
def first_access_submit(
    request: Request,
    full_name: str = Form(""),
    username: str = Form(""),
    password: str = Form(...),
    confirm_password: str = Form(...),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    """Processa a criação do primeiro administrador."""
    ip = _client_ip(request)

    # Pré-checagem (barata): instalação nova e sem bootstrap por variável de
    # ambiente. NÃO é a garantia de exclusividade — ver _claim_first_access.
    if not _first_access_enabled(db):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    username = (username or "").strip()
    full_name = (full_name or "").strip()
    email = (email or "").strip()

    if not username:
        return templates.TemplateResponse(
            request=request,
            name="setup.html",
            context={"error": "O nome de usuário não pode ser vazio."},
        )
    if not password or len(password) < 8:
        return templates.TemplateResponse(
            request=request,
            name="setup.html",
            context={"error": "A senha deve ter no mínimo 8 caracteres."},
        )
    if password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="setup.html",
            context={"error": "As senhas não coincidem."},
        )

    # Reivindica o bootstrap de forma atômica ANTES de criar o usuário. A
    # partir daqui, a reivindicação só é confirmada junto com a criação do
    # administrador (mesmo commit); qualquer falha faz rollback e libera o
    # primeiro acesso.
    if not _claim_first_access(db):
        logger.warning(
            "Primeiro acesso já reivindicado/em andamento; requisição concorrente "
            "redirecionada ao login (ip=%s)",
            ip,
        )
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Defesa em profundidade: se algum usuário já existir (ex.: banco legado
    # com reivindicação inexistente), descarta a reivindicação na mesma
    # transação e volta para o login.
    if db.query(User).first() is not None:
        db.rollback()
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        admin = create_user(
            db,
            username=username,
            password=password,
            full_name=full_name or None,
            email=email or None,
            is_admin=True,
        )
    except ValueError as err:
        # Libera a reivindicação para que o primeiro acesso possa ser refeito.
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="setup.html",
            context={"error": str(err)},
        )
    except IntegrityError:
        # Outra requisição criou o primeiro usuário neste intervalo.
        db.rollback()
        logger.warning("Primeiro acesso concluído por outra requisição concorrente")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Garante catálogo de permissões e o perfil Administrador (idempotente)
    ensure_default_roles(db)

    # Vincula o perfil Administrador ao novo usuário, se ainda não estiver
    # vinculado (garante que o administrador tem as permissões esperadas).
    admin_role = get_role_by_name(db, "Administrador")
    if admin_role:
        role_assigned = (
            db.query(UserRole)
            .filter(UserRole.user_id == admin.id, UserRole.role_id == admin_role.id)
            .first()
        )
        if not role_assigned:
            assign_role(db, admin, admin_role)

    # Auditoria de criação — NUNCA registra senha, hash ou credencial.
    write_audit(
        db,
        user=admin,
        action=ACTION_CREATE,
        module="Usuários",
        resource="User",
        resource_ref=admin.username,
        resource_id=admin.id,
        ip_address=ip,
        result=RESULT_SUCCESS,
        description="Primeiro administrador criado no primeiro acesso",
        new_data={
            "username": admin.username,
            "full_name": admin.full_name,
            "email": admin.email,
            "is_admin": True,
        },
    )

    logger.info(
        "Primeiro administrador criado via setup: username=%s, ip=%s",
        admin.username,
        ip,
    )

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
