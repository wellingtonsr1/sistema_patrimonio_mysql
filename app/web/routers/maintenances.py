"""Router: MANUTENÇÕES (MAINTENANCES) — Feature 051.

Conteúdo movido LITERALMENTE de `app/web/routes.py` (L1779–1882).
`web_router` é incluído pelo facade na posição original (FR-005).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import _client_ip, require_permission
from app.models.enums import AssetStatus, MaintenanceType
from app.schemas.maintenance import MaintenanceCreate, MaintenanceUpdate
from app.services.asset_service import AssetService
from app.services.maintenance_service import MaintenanceService
from app.services.audit_service import ACTION_MAINTENANCE, write_audit
from app.web.routers.templates_env import templates

web_router = APIRouter(include_in_schema=False)


@web_router.get("/maintenances", response_class=HTMLResponse, dependencies=[Depends(require_permission("manutencao.visualizar"))])
def list_maintenances_view(request: Request, db: Session = Depends(get_db)):
    maintenances = MaintenanceService.get_all(db)
    return templates.TemplateResponse(
        request=request,
        name="maintenances/list.html",
        context={"maintenances": maintenances, "active_tab": "maintenances"}
    )


@web_router.get("/maintenances/new", response_class=HTMLResponse, dependencies=[Depends(require_permission("manutencao.criar"))])
def form_new_maintenance(request: Request, asset_id: Optional[int] = None, db: Session = Depends(get_db)):
    assets, _ = AssetService.get_all(db, limit=500)
    active_assets = [a for a in assets if a.status != AssetStatus.WRITTEN_OFF]
    selected_asset = AssetService.get_by_id(db, asset_id) if asset_id else None

    return templates.TemplateResponse(
        request=request,
        name="maintenances/new.html",
        context={
            "assets": active_assets,
            "selected_asset": selected_asset,
            "maintenance_types": MaintenanceType,
            "active_tab": "maintenances"
        }
    )


@web_router.post("/maintenances/new", dependencies=[Depends(require_permission("manutencao.criar"))])
def create_maintenance_form(
    request: Request,
    asset_id: int = Form(...),
    maintenance_type: str = Form(...),
    provider_name: Optional[str] = Form(None),
    description: str = Form(...),
    cost: float = Form(0.0),
    operator_name: str = Form("Técnico"),
    db: Session = Depends(get_db)
):
    maint_data = MaintenanceCreate(
        asset_id=asset_id,
        maintenance_type=MaintenanceType(maintenance_type),
        provider_name=provider_name or None,
        description=description,
        cost=cost
    )
    maint = MaintenanceService.create(db, maint_data, operator=operator_name)
    asset_tag = maint.asset.tag if maint.asset else None
    write_audit(
        db,
        user=request.state.user,
        action=ACTION_MAINTENANCE,
        module="Manutenção",
        resource="Maintenance",
        resource_ref=asset_tag,
        resource_id=maint.id,
        ip_address=_client_ip(request),
        new_data={
            "tipo": maint.maintenance_type.value,
            "status": maint.status.value,
            "descricao": maint.description,
            "custo": maint.cost,
        },
        description=f"Abertura de ordem de serviço {maint.maintenance_type.label} para o bem {asset_tag or asset_id}",
    )
    return RedirectResponse(url=f"/assets/{asset_id}?maintenance_started=true", status_code=status.HTTP_303_SEE_OTHER)


@web_router.post("/maintenances/{maintenance_id}/complete", dependencies=[Depends(require_permission("manutencao.finalizar"))])
def complete_maintenance_form(
    request: Request,
    maintenance_id: int,
    solution: str = Form(...),
    cost: float = Form(0.0),
    operator_name: str = Form("Técnico"),
    db: Session = Depends(get_db)
):
    update_data = MaintenanceUpdate(
        solution=solution,
        cost=cost
    )
    maint = MaintenanceService.complete_maintenance(db, maintenance_id, update_data, operator=operator_name)
    asset_id = maint.asset_id if maint else ""
    if maint:
        asset_tag = maint.asset.tag if maint.asset else None
        write_audit(
            db,
            user=request.state.user,
            action=ACTION_MAINTENANCE,
            module="Manutenção",
            resource="Maintenance",
            resource_ref=asset_tag,
            resource_id=maint.id,
            ip_address=_client_ip(request),
            before={"status": "EM_ANDAMENTO", "custo": maint.cost},
            after={"status": maint.status.value, "custo": maint.cost, "solucao": maint.solution},
            description=f"Finalização da ordem de serviço {maint.id} do bem {asset_tag or asset_id}",
        )
    return RedirectResponse(url=f"/assets/{asset_id}?maintenance_completed=true", status_code=status.HTTP_303_SEE_OTHER)
