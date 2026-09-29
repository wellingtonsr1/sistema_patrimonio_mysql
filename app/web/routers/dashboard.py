"""Router: DASHBOARD — Feature 051.

Conteúdo movido LITERALMENTE de `app/web/routes.py` (L355–367).
`web_router` é incluído pelo facade na posição original (FR-005).
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dashboard_service import DashboardService
from app.web.routers.templates_env import templates

web_router = APIRouter(include_in_schema=False)


@web_router.get("/", response_class=HTMLResponse)
def view_dashboard(request: Request, db: Session = Depends(get_db)):
    stats = DashboardService.get_stats(db)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"stats": stats, "active_tab": "dashboard"}
    )
