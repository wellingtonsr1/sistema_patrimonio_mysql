"""Router: FLUXO DE MOVIMENTAÇÃO (MOVEMENTS) — Feature 051.

Conteúdo movido LITERALMENTE de `app/web/routes.py` (L922–1071).
`web_router` é incluído pelo facade na posição original (FR-005).
"""
import logging
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import _client_ip, require_permission
from app.models.enums import AssetCondition, AssetStatus, MovementType
from app.schemas.movement import MovementCreate, MovementFilter
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.location_service import LocationService
from app.services.movement_service import MovementService
from app.services.audit_service import ACTION_MOVEMENT, write_change_audit
from app.web.routers.templates_env import templates

logger = logging.getLogger("sispatrimonio.web")

web_router = APIRouter(include_in_schema=False)


def _onedoc_enabled() -> bool:
    """Feature 031: flag de integração 1Doc para o template (Q5 — campo só
    aparece nos formulários elegíveis quando a integração está ativa)."""
    from app import config as _config

    return bool(_config.ONEDOC_ENABLED)


@web_router.get("/movements", response_class=HTMLResponse, dependencies=[Depends(require_permission("movimentacao.visualizar"))])
def list_movements_view(
    request: Request,
    movement_type: Optional[str] = None,
    asset_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    m_type_enum = MovementType(movement_type) if movement_type and movement_type in [e.value for e in MovementType] else None
    clean_search = search.strip() if search and search.strip() else None
    filters = MovementFilter(movement_type=m_type_enum, asset_id=asset_id, search=clean_search)
    movements, total = MovementService.get_all_movements(db, filters=filters, limit=200)

    return templates.TemplateResponse(
        request=request,
        name="movements/list.html",
        context={
            "movements": movements,
            "total": total,
            "selected_type": movement_type or "",
            "search": clean_search or "",
            "movement_types": MovementType,
            "active_tab": "movements"
        }
    )


@web_router.get("/movements/new", response_class=HTMLResponse, dependencies=[Depends(require_permission("movimentacao.criar"))])
def form_new_movement(
    request: Request,
    asset_id: Optional[int] = None,
    m_type: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    assets, _ = AssetService.get_all(db, limit=500)
    # Filtra apenas ativos não baixados para nova movimentação
    active_assets = [a for a in assets if a.status != AssetStatus.WRITTEN_OFF]
    locations = LocationService.get_all(db)
    custodians = CustodianService.get_all(db, active_only=True)

    selected_asset = AssetService.get_by_id(db, asset_id) if asset_id else None

    return templates.TemplateResponse(
        request=request,
        name="movements/new.html",
        context={
            "assets": active_assets,
            "selected_asset": selected_asset,
            "locations": locations,
            "custodians": custodians,
            "movement_types": MovementType,
            "conditions": AssetCondition,
            "prefill_type": m_type or "",
            "error": error or "",
            "onedoc_enabled": _onedoc_enabled(),
            "active_tab": "movements"
        }
    )


@web_router.post("/movements/new", dependencies=[Depends(require_permission("movimentacao.criar"))])
def create_movement_form(
    request: Request,
    asset_id: int = Form(...),
    movement_type: str = Form(...),
    destination_location_id: Optional[int] = Form(None),
    destination_custodian_id: Optional[int] = Form(None),
    new_condition: Optional[str] = Form(None),
    reason: str = Form(...),
    operator_name: str = Form("Operador"),
    notes: Optional[str] = Form(None),
    onedoc_process_number: Optional[str] = Form(None),  # 031: processo 1Doc (só tipos elegíveis — Q5)
    db: Session = Depends(get_db)
):
    cond_enum = AssetCondition(new_condition) if new_condition and new_condition in [e.value for e in AssetCondition] else None

    # Feature 065 — o operador das movimentações é obrigatoriamente o usuário autenticado no servidor
    auth_user = getattr(request.state, "user", None)
    actual_operator = ((auth_user.full_name or auth_user.username)[:100]) if auth_user else operator_name

    movement_data = MovementCreate(
        asset_id=asset_id,
        movement_type=MovementType(movement_type),
        destination_location_id=destination_location_id if destination_location_id and destination_location_id > 0 else None,
        destination_custodian_id=destination_custodian_id if destination_custodian_id and destination_custodian_id > 0 else None,
        new_condition=cond_enum,
        reason=reason,
        operator_name=actual_operator,
        notes=notes or None,
        generate_term=True,
        onedoc_process_number=onedoc_process_number,  # 031: processo 1Doc (validação no service — FR-002)
    )

    try:
        movement = MovementService.create_movement(db, movement_data)
    except ValueError as err:
        # Repassa o bem e o tipo escolhidos para repovoar o formulário com o aviso
        return RedirectResponse(
            url=f"/movements/new?asset_id={asset_id}&m_type={movement_type}&error={quote(str(err))}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    asset_tag = movement.asset.tag if movement.asset else None
    write_change_audit(
        db,
        user=request.state.user,
        action=ACTION_MOVEMENT,
        module="Movimentação",
        resource="Movement",
        resource_ref=asset_tag,
        resource_id=movement.id,
        ip_address=_client_ip(request),
        before={
            "status": movement.previous_status.value if movement.previous_status else None,
            "condition": movement.previous_condition.value if movement.previous_condition else None,
        },
        after={
            "status": movement.new_status.value,
            "condition": movement.new_condition.value if movement.new_condition else None,
            "tipo": movement.movement_type.value,
            "motivo": movement.reason,
            "termo": movement.term_code,
        },
        description=f"Movimentação {movement.movement_type.label} do bem {asset_tag or movement.asset_id}",
    )

    # Se for alocação ou devolução, redireciona para o termo gerado
    if movement.movement_type in [MovementType.ALLOCATION, MovementType.RETURN_STOCK]:
        return RedirectResponse(url=f"/movements/{movement.id}/term", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url=f"/assets/{asset_id}?moved=true", status_code=status.HTTP_303_SEE_OTHER)


@web_router.get("/movements/{movement_id}/term", response_class=HTMLResponse, dependencies=[Depends(require_permission("movimentacao.visualizar"))])
def view_movement_term(request: Request, movement_id: int, db: Session = Depends(get_db)):
    """Renderiza a página para visualização e impressão do Termo de Responsabilidade/Cautela"""
    term_data = MovementService.get_term_details(db, movement_id)
    if not term_data:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")

    return templates.TemplateResponse(
        request=request,
        name="movements/term.html",
        context={
            "term": term_data,
            "movement_id": movement_id
        }
    )
