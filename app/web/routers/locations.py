"""Router: LOCAIS E DEPARTAMENTOS (LOCATIONS) — Feature 051.

Conteúdo movido LITERALMENTE de `app/web/routes.py` (L1423–1778).
`web_router` é incluído pelo facade na posição original (FR-005).
"""
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import _client_ip, require_permission
from app.schemas.location import LocationCreate
from app.services.location_service import LocationService
from app.services.location_import_service import (
    execute_locations_import,
    parse_locations_csv,
    preview_locations_import,
)
from app.services.audit_service import ACTION_CREATE, ACTION_IMPORT, write_audit, write_change_audit
from app.web.routers.templates_env import templates
from app.web.routers.shared import (
    _confirm_payload_rows,
    _dynamic_form,
    _read_csv_upload,
    _render_mapping_step,
    _render_smart_preview,
)

web_router = APIRouter(include_in_schema=False)


@web_router.get("/locations", response_class=HTMLResponse, dependencies=[Depends(require_permission("locais.visualizar"))])
def list_locations_view(request: Request, search: Optional[str] = None, db: Session = Depends(get_db)):
    locations = LocationService.get_all(db, search=search)
    for loc in locations:
        loc.assets_count = LocationService.count_assets(db, loc.id)

    return templates.TemplateResponse(
        request=request,
        name="locations/list.html",
        context={"locations": locations, "search": (search or "").strip(), "active_tab": "locations"}
    )


@web_router.get("/locations/import", response_class=HTMLResponse, dependencies=[Depends(require_permission("locais.criar"))])
def form_import_locations(request: Request):
    """Exibe o formulário de importação CSV de locais"""
    return templates.TemplateResponse(
        request=request,
        name="locations/import.html",
        context={"active_tab": "locations"},
    )


@web_router.post("/locations/import", response_class=HTMLResponse, dependencies=[Depends(require_permission("locais.criar"))])
def process_import_locations(
    request: Request,
    step: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    csv_content: Optional[str] = Form(None),
    mapping: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    filtro: Optional[str] = Form(None),
    skip_duplicates: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Processa o upload e exibe o passo de mapeamento (Feature 048 — R5);
    com step=analyze, reexecuta a análise server-side e classifica os registros
    (pré-visualização — nada gravado, SC-001)."""
    if step == "analyze":
        if not csv_content:
            return templates.TemplateResponse(
                request=request,
                name="locations/import.html",
                context={
                    "active_tab": "locations",
                    "error": "Dados do mapeamento ausentes. Envie o arquivo novamente.",
                }
            )
        return _render_smart_preview(
            request=request,
            template_name="locations/import.html",
            kind="locations",
            content=csv_content,
            mapping_raw=mapping,
            dynamic_form=_dynamic_form(request),
            filtro=filtro,
            filename=filename or "",
            skip_duplicates=skip_duplicates,
            active_tab="locations",
            form_action="/locations/import",
            confirm_action="/locations/import/confirm",
            back_url="/locations/import",
            db=db,
        )

    content, error_response = _read_csv_upload(request, file, "locations/import.html", "locations")
    if error_response is not None:
        return error_response

    return _render_mapping_step(
        request=request,
        template_name="locations/import.html",
        kind="locations",
        content=content,
        filename=file.filename or "",
        skip_duplicates=skip_duplicates,
        active_tab="locations",
        form_action="/locations/import",
        back_url="/locations/import",
    )


@web_router.post("/locations/import/confirm", dependencies=[Depends(require_permission("locais.criar"))])
def confirm_import_locations(
    request: Request,
    csv_data: Optional[str] = Form(None),
    csv_content: Optional[str] = Form(None),
    mapping: Optional[str] = Form(None),
    skip_duplicates: bool = Form(True),
    resolutions: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Confirma e executa a importação de locais (Feature 048)"""
    rows, class_counts, parse_err = _confirm_payload_rows(
        csv_data, resolutions, db, _dynamic_form(request),
        csv_content=csv_content, mapping_raw=mapping, kind="locations",
    )
    if parse_err is not None:
        return templates.TemplateResponse(
            request=request,
            name="locations/import.html",
            context={
                "active_tab": "locations",
                "show_result": True,
                "result": {
                    "imported": 0,
                    "skipped": 0,
                    "errors": [f"Erro ao processar dados: {parse_err}"],
                    "total_processed": 0,
                },
            }
        )

    try:
        result = execute_locations_import(rows, db, skip_duplicates=skip_duplicates)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="locations/import.html",
            context={
                "active_tab": "locations",
                "show_result": True,
                "result": {
                    "imported": 0,
                    "skipped": 0,
                    "errors": [f"Erro na importação: {str(e)}"],
                    "total_processed": 0,
                },
            }
        )

    _counts_desc = ""
    if class_counts:
        _counts_desc = ", ".join(f"{k}: {v}" for k, v in sorted(class_counts.items()))
        _counts_desc = f"; classificações da pré-visualização [{_counts_desc}]"
    write_audit(
        db,
        user=request.state.user,
        action=ACTION_IMPORT,
        module="Locais",
        resource="Location",
        resource_ref="importacao-csv",
        ip_address=_client_ip(request),
        description=f"Importação CSV de locais: {result.get('imported', 0)} criados, "
                    f"{result.get('skipped', 0)} ignorados, {len(result.get('errors', []))} erros"
                    f"{_counts_desc}",
        new_data={"imported": result.get("imported", 0), "skipped": result.get("skipped", 0)},
    )

    return templates.TemplateResponse(
        request=request,
        name="locations/import.html",
        context={
            "active_tab": "locations",
            "show_result": True,
            "result": result,
        }
    )


@web_router.get("/locations/new", response_class=HTMLResponse, dependencies=[Depends(require_permission("locais.criar"))])
def form_new_location(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(
        request=request,
        name="locations/form.html",
        context={"error": error or "", "active_tab": "locations"}
    )


@web_router.post("/locations/new", dependencies=[Depends(require_permission("locais.criar"))])
def create_location_form(
    request: Request,
    name: str = Form(...),
    branch: str = Form(...),
    building: Optional[str] = Form(None),
    floor: Optional[str] = Form(None),
    room: Optional[str] = Form(None),
    department: str = Form(...),
    manager_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    loc_data = LocationCreate(
        name=name,
        branch=branch,
        building=building or None,
        floor=floor or None,
        room=room or None,
        department=department,
        manager_name=manager_name or None,
        description=description or None
    )
    try:
        loc = LocationService.create(db, loc_data)
    except ValueError as err:
        return RedirectResponse(url=f"/locations/new?error={quote(str(err))}", status_code=status.HTTP_303_SEE_OTHER)
    write_change_audit(
        db,
        user=request.state.user,
        action=ACTION_CREATE,
        module="Locais",
        resource="Location",
        resource_ref=loc.name,
        resource_id=loc.id,
        ip_address=_client_ip(request),
        after={"name": loc.name, "branch": loc.branch, "department": loc.department},
        description=f"Cadastro do local {loc.name}",
    )
    return RedirectResponse(url="/locations", status_code=status.HTTP_303_SEE_OTHER)
