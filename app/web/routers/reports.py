"""Router: RELATÓRIOS — Feature 051.

Conteúdo movido LITERALMENTE de `app/web/routes.py` (L1883–1977).
`web_router` é incluído pelo facade na posição original (FR-005).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import require_permission
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.movement_service import MovementService
from app.web.routers.templates_env import templates

web_router = APIRouter(include_in_schema=False)


@web_router.get("/reports/inventory", response_class=HTMLResponse, dependencies=[Depends(require_permission("relatorios.visualizar"))])
def view_inventory_report(
    request: Request,
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    custodian_id: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    maintenance_status: Optional[str] = Query(None),
    purchase_date_from: Optional[str] = Query(None),
    purchase_date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    # Converter parâmetros (location_id e custodian_id já são string, não precisam converter)
    loc_id = int(location_id) if location_id and location_id.strip().isdigit() else None
    cust_id = int(custodian_id) if custodian_id and custodian_id.strip().isdigit() else None

    from app.models.enums import AssetStatus as AS, AssetCategory as AC
    status_enum = AS(status) if status and status in [e.value for e in AS] else None
    category_enum = AC(category) if category and category in [e.value for e in AC] else None

    # Converter datas
    date_from = datetime.strptime(purchase_date_from, "%Y-%m-%d") if purchase_date_from else None
    date_to = datetime.strptime(purchase_date_to, "%Y-%m-%d") if purchase_date_to else None

    assets, total = AssetService.get_all(
        db, search=search, status=status_enum, category=category_enum,
        location_id=loc_id, custodian_id=cust_id,
        brand=brand, model=model, department=department,
        maintenance_status=maintenance_status,
        purchase_date_from=date_from, purchase_date_to=date_to,
        limit=1000
    )
    for a in assets:
        a.deprec_info = AssetService.calculate_depreciation(a)

    return templates.TemplateResponse(
        request=request,
        name="reports/inventory.html",
        context={
            "assets": assets,
            "total": total,
            "active_tab": "reports",
            "search": search or "",
            "selected_status": status or "",
            "selected_category": category or "",
            "selected_location": loc_id or "",
            "selected_custodian": cust_id or "",
            "selected_brand": brand or "",
            "selected_model": model or "",
            "selected_department": department or "",
            "selected_maintenance": maintenance_status or "",
            "selected_date_from": purchase_date_from or "",
            "selected_date_to": purchase_date_to or ""
        }
    )


@web_router.get("/reports/movements", response_class=HTMLResponse, dependencies=[Depends(require_permission("relatorios.visualizar"))])
def view_movements_report(request: Request, db: Session = Depends(get_db)):
    movements, total = MovementService.get_all_movements(db, limit=1000)
    return templates.TemplateResponse(
        request=request,
        name="reports/movements_report.html",
        context={
            "movements": movements,
            "total": total,
            "active_tab": "reports"
        }
    )


@web_router.get("/reports/custodians", response_class=HTMLResponse, dependencies=[Depends(require_permission("relatorios.visualizar"))])
def view_custodians_report(request: Request, db: Session = Depends(get_db)):
    custodians = CustodianService.get_all(db)
    for c in custodians:
        c.active_assets_count = CustodianService.count_assigned_assets(db, c.id)

    return templates.TemplateResponse(
        request=request,
        name="reports/custodians_report.html",
        context={
            "custodians": custodians,
            "total": len(custodians),
            "active_tab": "reports"
        }
    )
