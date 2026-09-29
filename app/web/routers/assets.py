"""Router: BENS / EQUIPAMENTOS (ASSETS) — Feature 051.

Conteúdo movido LITERALMENTE de `app/web/routes.py` (L368–921).
`web_router` é incluído pelo facade na posição original (FR-005).
"""
from datetime import datetime
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.api.deps import _client_ip, require_permission
from app.models.asset import Asset
from app.models.enums import AssetCategory, AssetCondition, AssetStatus, InventarioStatus
from app.models.inventario import Inventario
from app.schemas.asset import AssetCreate
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.import_service import execute_import, parse_csv, preview_import  # noqa: F401 (parse/preview mantidos por compat)
from app.services.location_service import LocationService
from app.services.movement_service import MovementService
from app.services.audit_service import ACTION_CREATE, ACTION_IMPORT, write_audit, write_change_audit
from app.web.routers.templates_env import templates
from app.web.routers.shared import (
    _confirm_payload_rows,
    _dynamic_form,
    _read_csv_upload,
    _render_mapping_step,
    _render_smart_preview,
)
from app.web.routers.inventario import user_has_permission_for
from app.models.location import Location
from app.services.import_intelligence import analyze_columns

web_router = APIRouter(include_in_schema=False)


def _asset_audit_snapshot(asset) -> dict:
    """Snapshot serializável de um bem para a trilha de auditoria."""
    data = {
        "tag": asset.tag, "name": asset.name, "brand": asset.brand, "model": asset.model,
        "serial_number": asset.serial_number, "purchase_value": asset.purchase_value,
        "invoice_number": asset.invoice_number, "supplier": asset.supplier,
        "location_id": asset.location_id, "custodian_id": asset.custodian_id, "notes": asset.notes,
    }
    if asset.category is not None:
        data["category"] = asset.category.value
    if asset.condition is not None:
        data["condition"] = asset.condition.value
    if asset.status is not None:
        data["status"] = asset.status.value
    return data


@web_router.get("/assets", response_class=HTMLResponse, dependencies=[Depends(require_permission("patrimonio.visualizar"))])
def list_assets(
    request: Request,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    location_id: Optional[str] = Query(None),
    custodian_id: Optional[str] = Query(None),
    brand_filter: Optional[str] = Query(None),
    model_filter: Optional[str] = Query(None),
    department_filter: Optional[str] = Query(None),
    maintenance_filter: Optional[str] = Query(None),
    purchase_date_from: Optional[str] = Query(None),
    purchase_date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    # Converter parâmetros de string para int (ou None se vazio/inválido)
    loc_id = int(location_id) if location_id and location_id.strip().isdigit() else None
    cust_id = int(custodian_id) if custodian_id and custodian_id.strip().isdigit() else None

    status_enum = AssetStatus(status_filter) if status_filter and status_filter in [e.value for e in AssetStatus] else None
    cat_enum = AssetCategory(category_filter) if category_filter and category_filter in [e.value for e in AssetCategory] else None

    # Converter datas
    from datetime import datetime as dt
    date_from = dt.strptime(purchase_date_from, "%Y-%m-%d") if purchase_date_from else None
    date_to = dt.strptime(purchase_date_to, "%Y-%m-%d") if purchase_date_to else None

    assets, total = AssetService.get_all(
        db, search=search, status=status_enum, category=cat_enum,
        location_id=loc_id, custodian_id=cust_id,
        brand=brand_filter, model=model_filter,
        department=department_filter, maintenance_status=maintenance_filter,
        purchase_date_from=date_from, purchase_date_to=date_to,
        limit=200
    )
    locations = LocationService.get_all(db)
    custodians = CustodianService.get_all(db, active_only=True)

    # Obter lista única de departamentos para o filtro
    departments = db.query(Location.department).distinct().filter(Location.department != None).all()
    departments = [d[0] for d in departments if d[0]]

    return templates.TemplateResponse(
        request=request,
        name="assets/list.html",
        context={
            "assets": assets,
            "total": total,
            "search": search or "",
            "selected_status": status_filter or "",
            "selected_category": category_filter or "",
            "selected_location": loc_id or "",
            "selected_custodian": cust_id or "",
            "selected_brand": brand_filter or "",
            "selected_model": model_filter or "",
            "selected_department": department_filter or "",
            "selected_maintenance": maintenance_filter or "",
            "selected_date_from": purchase_date_from or "",
            "selected_date_to": purchase_date_to or "",
            "locations": locations,
            "custodians": custodians,
            "departments": departments,
            "categories": AssetCategory,
            "statuses": AssetStatus,
            "active_tab": "assets"
        }
    )


@web_router.get("/assets/labels", response_class=HTMLResponse, dependencies=[Depends(require_permission("patrimonio.visualizar"))])
def assets_labels(
    request: Request,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    location_id: Optional[str] = Query(None),
    custodian_id: Optional[str] = Query(None),
    brand_filter: Optional[str] = Query(None),
    model_filter: Optional[str] = Query(None),
    department_filter: Optional[str] = Query(None),
    selected: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Página de seleção e impressão de etiquetas patrimoniais em lote.

    Somente leitura: não altera registros patrimoniais. O QR Code reutiliza a
    mesma biblioteca e o mesmo conteúdo da ficha do bem (/assets/{id}).
    """
    loc_id = int(location_id) if location_id and location_id.strip().isdigit() else None
    cust_id = int(custodian_id) if custodian_id and custodian_id.strip().isdigit() else None
    status_enum = AssetStatus(status_filter) if status_filter and status_filter in [e.value for e in AssetStatus] else None
    cat_enum = AssetCategory(category_filter) if category_filter and category_filter in [e.value for e in AssetCategory] else None

    assets, total = AssetService.get_all(
        db, search=search, status=status_enum, category=cat_enum,
        location_id=loc_id, custodian_id=cust_id,
        brand=brand_filter, model=model_filter,
        department=department_filter,
        limit=200
    )
    locations = LocationService.get_all(db)
    custodians = CustodianService.get_all(db, active_only=True)

    departments = db.query(Location.department).distinct().filter(Location.department != None).all()
    departments = [d[0] for d in departments if d[0]]

    # Seleção em lote (somente leitura — ids validados e ordenados como escolhidos)
    selected_ids: list = []
    if selected:
        for part in selected.split(","):
            part = part.strip()
            if part.isdigit():
                val = int(part)
                if val not in selected_ids:
                    selected_ids.append(val)
    selected_assets: list = []
    if selected_ids:
        selected_assets = db.query(Asset).options(joinedload(Asset.location)).filter(Asset.id.in_(selected_ids)).all()
        selected_assets.sort(key=lambda a: selected_ids.index(a.id))

    # Dados para atualização ao vivo da folha de etiquetas (sem recarregar a página)
    payload_assets = {a.id: a for a in assets}
    for a in selected_assets:
        payload_assets.setdefault(a.id, a)
    selected_payload = {
        str(a.id): {
            "id": a.id,
            "tag": a.tag,
            "name": a.name,
            "department": a.location.department if a.location else None,
            "location_name": a.location.name if a.location else None,
        }
        for a in payload_assets.values()
    }

    return templates.TemplateResponse(
        request=request,
        name="assets/labels.html",
        context={
            "assets": assets,
            "total": total,
            "search": search or "",
            "selected_status": status_filter or "",
            "selected_category": category_filter or "",
            "selected_location": loc_id or "",
            "selected_custodian": cust_id or "",
            "selected_brand": brand_filter or "",
            "selected_model": model_filter or "",
            "selected_department": department_filter or "",
            "locations": locations,
            "custodians": custodians,
            "departments": departments,
            "categories": AssetCategory,
            "statuses": AssetStatus,
            "selected": selected or "",
            "selected_list": [str(v) for v in selected_ids],
            "selected_assets": selected_assets,
            "selected_payload": selected_payload,
            "page_ids": [a.id for a in assets],
            "active_tab": "labels"
        }
    )


@web_router.get("/assets/import", response_class=HTMLResponse, dependencies=[Depends(require_permission("patrimonio.criar"))])
def form_import_assets(request: Request):
    """Exibe o formulário de importação CSV"""
    return templates.TemplateResponse(
        request=request,
        name="assets/import.html",
        context={"active_tab": "assets"}
    )


@web_router.post("/assets/import", response_class=HTMLResponse, dependencies=[Depends(require_permission("patrimonio.criar"))])
def process_import_assets(
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
        # Fase 2: mapeamento confirmado → classificação por registro
        # mapping individual por coluna (mapping_<coluna>) ou JSON único
        if not csv_content:
            return templates.TemplateResponse(
                request=request,
                name="assets/import.html",
                context={
                    "active_tab": "assets",
                    "error": "Dados do mapeamento ausentes. Envie o arquivo novamente.",
                }
            )
        return _render_smart_preview(
            request=request,
            template_name="assets/import.html",
            kind="assets",
            content=csv_content,
            mapping_raw=mapping,
            dynamic_form=_dynamic_form(request),
            filtro=filtro,
            filename=filename or "",
            skip_duplicates=skip_duplicates,
            active_tab="assets",
            form_action="/assets/import",
            confirm_action="/assets/import/confirm",
            back_url="/assets/import",
            db=db,
        )

    # Fase 1: upload do arquivo → passo de mapeamento
    content, error_response = _read_csv_upload(request, file, "assets/import.html", "assets")
    if error_response is not None:
        return error_response

    # Guarda R6: vazio/só BOM → erro puro (sem o cartão de mapeamento)
    _analysis = analyze_columns(content, "assets")
    if _analysis["parse_errors"] and _analysis["total_rows"] == 0 and not _analysis["header"]:
        return templates.TemplateResponse(
            request=request,
            name="assets/import.html",
            context={
                "active_tab": "assets",
                "error": "Não foi possível analisar o arquivo:",
                "parse_errors": _analysis["parse_errors"],
            }
        )

    return _render_mapping_step(
        request=request,
        template_name="assets/import.html",
        kind="assets",
        content=content,
        filename=file.filename or "",
        skip_duplicates=skip_duplicates,
        active_tab="assets",
        form_action="/assets/import",
        back_url="/assets/import",
    )


@web_router.post("/assets/import/confirm", dependencies=[Depends(require_permission("patrimonio.criar"))])
def confirm_import_assets(
    request: Request,
    csv_data: Optional[str] = Form(None),
    csv_content: Optional[str] = Form(None),
    mapping: Optional[str] = Form(None),
    skip_duplicates: bool = Form(True),
    resolutions: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Confirma e executa a importação (Feature 048: payload classificado ou
    lista canônica legada — mesma URL, mesmo execute_import)"""
    rows, class_counts, parse_err = _confirm_payload_rows(
        csv_data, resolutions, db, _dynamic_form(request),
        csv_content=csv_content, mapping_raw=mapping, kind="assets",
    )
    if parse_err is not None:
        return templates.TemplateResponse(
            request=request,
            name="assets/import.html",
            context={
                "active_tab": "assets",
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
        # Feature 029 — o operador das movimentações é o usuário autenticado
        _user = getattr(request.state, "user", None)
        _operator = (_user.full_name or _user.username) if _user else None
        result = execute_import(rows, db, skip_duplicates=skip_duplicates, operator_name=_operator)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="assets/import.html",
            context={
                "active_tab": "assets",
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
        module="Patrimônio",
        resource="Asset",
        resource_ref="importacao-csv",
        ip_address=_client_ip(request),
        description=f"Importação CSV de bens: {result.get('imported', 0)} importados, "
                    f"{result.get('skipped', 0)} ignorados, {len(result.get('errors', []))} erros"
                    f"{_counts_desc}",
        new_data={"imported": result.get("imported", 0), "skipped": result.get("skipped", 0)},
    )

    return templates.TemplateResponse(
        request=request,
        name="assets/import.html",
        context={
            "active_tab": "assets",
            "show_result": True,
            "result": result,
        }
    )


@web_router.get("/assets/new", response_class=HTMLResponse, dependencies=[Depends(require_permission("patrimonio.criar"))])
def form_new_asset(request: Request, error: Optional[str] = None, db: Session = Depends(get_db)):
    locations = LocationService.get_all(db)
    custodians = CustodianService.get_all(db, active_only=True)
    return templates.TemplateResponse(
        request=request,
        name="assets/form.html",
        context={
            "locations": locations,
            "custodians": custodians,
            "categories": AssetCategory,
            "conditions": AssetCondition,
            "error": error or "",
            "active_tab": "assets"
        }
    )


@web_router.post("/assets/new", dependencies=[Depends(require_permission("patrimonio.criar"))])
def create_asset_form(
    request: Request,
    tag: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    brand: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    serial_number: Optional[str] = Form(None),
    specifications: Optional[str] = Form(None),
    purchase_date: Optional[str] = Form(None),
    purchase_value: float = Form(0.0),
    invoice_number: Optional[str] = Form(None),
    supplier: Optional[str] = Form(None),
    warranty_expiry: Optional[str] = Form(None),
    condition: str = Form(AssetCondition.NEW.value),
    location_id: Optional[int] = Form(None),
    custodian_id: Optional[int] = Form(None),
    operator_name: str = Form("Operador"),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    dt_purchase = datetime.strptime(purchase_date, "%Y-%m-%d") if purchase_date else None
    dt_warranty = datetime.strptime(warranty_expiry, "%Y-%m-%d") if warranty_expiry else None

    create_data = AssetCreate(
        tag=tag,
        name=name,
        category=AssetCategory(category),
        brand=brand or None,
        model=model or None,
        serial_number=serial_number or None,
        specifications=specifications or None,
        purchase_date=dt_purchase,
        purchase_value=purchase_value,
        invoice_number=invoice_number or None,
        supplier=supplier or None,
        warranty_expiry=dt_warranty,
        condition=AssetCondition(condition),
        initial_location_id=location_id if location_id and location_id > 0 else None,
        initial_custodian_id=custodian_id if custodian_id and custodian_id > 0 else None,
        initial_operator=operator_name,
        notes=notes or None
    )

    try:
        asset = AssetService.create(db, create_data)
    except ValueError as err:
        return RedirectResponse(url=f"/assets/new?error={quote(str(err))}", status_code=status.HTTP_303_SEE_OTHER)
    write_change_audit(
        db,
        user=request.state.user,
        action=ACTION_CREATE,
        module="Patrimônio",
        resource="Asset",
        resource_ref=asset.tag,
        resource_id=asset.id,
        ip_address=_client_ip(request),
        after=_asset_audit_snapshot(asset),
        description=f"Cadastro do bem {asset.tag} - {asset.name}",
    )
    return RedirectResponse(url=f"/assets/{asset.id}?created=true", status_code=status.HTTP_303_SEE_OTHER)


@web_router.get("/assets/{asset_id}", response_class=HTMLResponse, dependencies=[Depends(require_permission("patrimonio.visualizar"))])
def view_asset_detail(request: Request, asset_id: int, db: Session = Depends(get_db)):
    asset = AssetService.get_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")

    timeline = MovementService.get_timeline_for_asset(db, asset_id)
    deprec = AssetService.calculate_depreciation(asset)

    # Inventário: inventários abertos (não encerrados) para conferência via QR
    open_inventarios = []
    if user_has_permission_for(request, db, "inventario.conferir"):
        open_inventarios = (
            db.query(Inventario)
            .filter(Inventario.status != InventarioStatus.CLOSED)
            .order_by(Inventario.created_at.desc())
            .limit(10)
            .all()
        )

    return templates.TemplateResponse(
        request=request,
        name="assets/detail.html",
        context={
            "asset": asset,
            "timeline": timeline,
            "depreciation": deprec,
            "open_inventarios": open_inventarios,
            "active_tab": "assets"
        }
    )
