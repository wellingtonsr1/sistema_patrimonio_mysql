"""Router: INVENTÁRIO PATRIMONIAL COMPLETO E COMPROBATÓRIO — Feature 051.

Conteúdo movido LITERALMENTE de `app/web/routes.py` (L2168–2668).
`web_router` é incluído pelo facade na posição original (FR-005).
"""
from datetime import datetime
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import _client_ip, get_current_user, require_permission
from app.models.asset import Asset
from app.models.enums import (
    InventarioItemStatus,
    InventarioOfflineColetaStatus,
    InventarioStatus,
)
from app.models.inventario import Inventario
from app.models.location import Location
from app.services.asset_service import AssetService
from app.services.inventario_service import InventarioService
from app.services.location_service import LocationService
from app.services.audit_service import ACTION_INVENTARIO, RESULT_SUCCESS, write_audit
from app.web.routers.templates_env import templates

web_router = APIRouter(include_in_schema=False)


def user_has_permission_for(request: Request, db: Session, permission: str) -> bool:
    """Verifica permissão do usuário da request (helper do módulo de inventário)."""
    from app.services.permission_service import user_has_permission
    user = getattr(request.state, "user", None)
    if user is None:
        user = get_current_user(request, db)
    return user_has_permission(db, user, permission)


@web_router.get("/inventarios", response_class=HTMLResponse, dependencies=[Depends(require_permission("inventario.visualizar"))])
def list_inventarios(
    request: Request,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    status_enum = (
        InventarioStatus(status_filter)
        if status_filter and status_filter in [e.value for e in InventarioStatus]
        else None
    )
    inventarios = InventarioService.get_all(db, search=search, status=status_enum)
    summaries = {inv.id: InventarioService.summary(db, inv.id) for inv in inventarios}
    return templates.TemplateResponse(
        request=request,
        name="inventarios/list.html",
        context={
            "inventarios": inventarios,
            "summaries": summaries,
            "search": search or "",
            "selected_status": status_filter or "",
            "statuses": InventarioStatus,
            "active_tab": "inventarios",
        },
    )


@web_router.get("/inventarios/new", response_class=HTMLResponse, dependencies=[Depends(require_permission("inventario.criar"))])
def form_new_inventario(request: Request, db: Session = Depends(get_db)):
    locations = LocationService.get_all(db)
    departments = (
        db.query(Location.department).distinct().filter(Location.department != None).all()  # noqa: E711
    )
    departments = sorted(d[0] for d in departments if d[0])
    return templates.TemplateResponse(
        request=request,
        name="inventarios/new.html",
        context={
            "locations": locations,
            "departments": departments,
            "active_tab": "inventarios",
        },
    )


@web_router.post("/inventarios/new", dependencies=[Depends(require_permission("inventario.criar"))])
def create_inventario_form(
    request: Request,
    name: str = Form(...),
    location_id: Optional[int] = Form(None),
    department: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    user = request.state.user
    try:
        inv = InventarioService.create_inventario(
            db,
            name=name,
            location_id=location_id if location_id and location_id > 0 else None,
            department=department or None,
            notes=notes or None,
            created_by_id=user.id,
            created_by_name=user.username,
        )
    except ValueError as err:
        return RedirectResponse(
            url=f"/inventarios/new?error={quote(str(err))}", status_code=status.HTTP_303_SEE_OTHER
        )

    total = len(inv.itens) if inv.itens else 0
    write_audit(
        db,
        user=user,
        action=ACTION_INVENTARIO,
        module="Inventário",
        resource="Inventario",
        resource_id=inv.id,
        resource_ref=inv.code,
        ip_address=_client_ip(request),
        result=RESULT_SUCCESS,
        description=f"Inventário '{inv.name}' criado com {total} bem(ns) esperado(s). Escopo: {inv.scope_filters}",
        new_data={
            "code": inv.code,
            "name": inv.name,
            "escopo": inv.scope_filters,
            "bens_esperados": total,
        },
    )
    return RedirectResponse(url=f"/inventarios/{inv.id}", status_code=status.HTTP_303_SEE_OTHER)


@web_router.get("/inventarios/{inventario_id}", response_class=HTMLResponse, dependencies=[Depends(require_permission("inventario.visualizar"))])
def view_inventario(
    request: Request,
    inventario_id: int,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    inv = InventarioService.get_by_id(db, inventario_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventário não encontrado")

    itens = list(inv.itens)

    # Filtros da lista de conferência
    if search:
        term = f"%{search.strip()}%"
        filtered = [
            i for i in itens
            if (i.asset and (i.asset.tag.lower().find(term.strip("%").lower()) >= 0
                             or i.asset.name.lower().find(term.strip("%").lower()) >= 0))
        ]
        itens = filtered
    if status_filter and status_filter in [e.value for e in InventarioItemStatus]:
        status_enum = InventarioItemStatus(status_filter)
        itens = [i for i in itens if i.status == status_enum]

    # Consolidação e proveniência dos itens não previstos
    unlisted = [i for i in itens if i.nao_previsto]
    expected_itens = [i for i in itens if not i.nao_previsto]
    can_conferir = user_has_permission_for(request, db, "inventario.conferir")
    can_encerrar = user_has_permission_for(request, db, "inventario.encerrar")

    # Feature 033: coletas offline (rastreabilidade por dispositivo — US4) e
    # conflitos preservados (P-3/FR-027) — leitura via service (Princípio III).
    # ATENÇÃO: o valor do enum é o rótulo ("OFFLINE_CONFLITO"), não o nome.
    from app.services.inventario_offline_service import InventarioOfflineService
    offline = InventarioOfflineService.list_coletas(db, inventory_id=inv.id)
    offline_conflitos = [
        c for c in offline["coletas"]
        if c["status"] == InventarioOfflineColetaStatus.CONFLICT.value
    ]

    return templates.TemplateResponse(
        request=request,
        name="inventarios/detail.html",
        context={
            "inv": inv,
            "expected_itens": expected_itens,
            "unlisted_itens": unlisted,
            "summary": InventarioService.summary(db, inv.id),
            "all_locations": LocationService.get_all(db),
            "search": search or "",
            "selected_status": status_filter or "",
            "item_statuses": InventarioItemStatus,
            "can_conferir": can_conferir,
            "can_encerrar": can_encerrar,
            "offline_coletas": offline["coletas"],
            "offline_conflitos": offline_conflitos,
            "error": error,
            "active_tab": "inventarios",
        },
    )


@web_router.post("/inventarios/{inventario_id}/buscar", dependencies=[Depends(require_permission("inventario.conferir"))])
def buscar_bem_inventario(
    request: Request,
    inventario_id: int,
    tag: str = Form(...),
    db: Session = Depends(get_db),
):
    """Localiza um item pelo tombamento (fluxo de campo: digitar/escanear o QR)."""
    tag_clean = (tag or "").strip()
    asset = db.query(Asset).filter(Asset.tag.ilike(tag_clean)).first()
    if not asset:
        error_msg = f'Nenhum bem com o tombamento "{tag_clean}" foi encontrado no cadastro.'
        return RedirectResponse(
            url=f"/inventarios/{inventario_id}?error={quote(error_msg)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    item = InventarioService.get_item_for_conference(db, inventario_id, asset.id)
    if item:
        # Bem esperado (ou ocorrência já registrada): abre o modal de conferência
        return RedirectResponse(
            url=f"/inventarios/{inventario_id}?search={quote(asset.tag)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    # Bem existe no cadastro, mas não está na lista: registra como não previsto
    error_msg = f"O bem {asset.tag} não está na lista de esperados. Registre-o como não previsto no painel lateral."
    return RedirectResponse(
        url=f"/inventarios/{inventario_id}?search={quote(asset.tag)}&error={quote(error_msg)}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@web_router.post("/inventarios/{inventario_id}/iniciar", dependencies=[Depends(require_permission("inventario.conferir"))])
def iniciar_inventario(
    request: Request,
    inventario_id: int,
    db: Session = Depends(get_db),
):
    """Inicia formalmente a conferência (marca started_at e status EM_ANDAMENTO)."""
    user = request.state.user
    inv = InventarioService.get_by_id(db, inventario_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventário não encontrado")
    if inv.status == InventarioStatus.CLOSED:
        return RedirectResponse(
            url=f"/inventarios/{inventario_id}?error={quote('Este inventário já está encerrado.')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if inv.started_at is None:
        inv.started_at = datetime.utcnow()
        if inv.status == InventarioStatus.PLANNED:
            inv.status = InventarioStatus.IN_PROGRESS
        db.commit()
        write_audit(
            db,
            user=user,
            action=ACTION_INVENTARIO,
            module="Inventário",
            resource="Inventario",
            resource_id=inv.id,
            resource_ref=inv.code,
            ip_address=_client_ip(request),
            result=RESULT_SUCCESS,
            description=f"Inventário {inv.code} iniciado formalmente",
        )
    return RedirectResponse(url=f"/inventarios/{inventario_id}", status_code=status.HTTP_303_SEE_OTHER)


@web_router.get("/inventarios/{inventario_id}/conferir/{asset_id}", response_class=HTMLResponse, dependencies=[Depends(require_permission("inventario.conferir"))])
def conferir_asset_page(
    request: Request,
    inventario_id: int,
    asset_id: int,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Página de conferência em campo de um bem (fluxo QR: ficha → conferir)."""
    asset = AssetService.get_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    inv = InventarioService.get_by_id(db, inventario_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventário não encontrado")

    item = InventarioService.get_item_for_conference(db, inventario_id, asset_id)
    all_locations = LocationService.get_all(db)

    return templates.TemplateResponse(
        request=request,
        name="inventarios/conferir.html",
        context={
            "asset": asset,
            "inv": inv,
            "item": item,
            "all_locations": all_locations,
            "error": error,
            "active_tab": "inventarios",
        },
    )


@web_router.post("/inventarios/{inventario_id}/conferir/{item_id}", dependencies=[Depends(require_permission("inventario.conferir"))])
def confer_item(
    request: Request,
    inventario_id: int,
    item_id: int,
    result: str = Form(...),
    found_location_id: Optional[int] = Form(None),
    observation: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    user = request.state.user
    item = InventarioService.get_item(db, item_id)
    if not item or item.inventario_id != inventario_id:
        raise HTTPException(status_code=404, detail="Item de inventário não encontrado")

    valid = {e.value for e in InventarioItemStatus} - {InventarioItemStatus.PENDING.value}
    if result not in valid:
        return RedirectResponse(
            url=f"/inventarios/{inventario_id}?error={quote('Resultado de conferência inválido.')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        InventarioService.record_check(
            db,
            item=item,
            result=InventarioItemStatus(result),
            found_location_id=found_location_id if found_location_id and found_location_id > 0 else None,
            observation=observation or None,
            user_id=user.id,
            username=user.username,
        )
    except ValueError as err:
        return RedirectResponse(
            url=f"/inventarios/{inventario_id}?error={quote(str(err))}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    write_audit(
        db,
        user=user,
        action=ACTION_INVENTARIO,
        module="Inventário",
        resource="InventarioItem",
        resource_id=item.id,
        resource_ref=item.asset.tag if item.asset else str(item.asset_id),
        ip_address=_client_ip(request),
        result=RESULT_SUCCESS,
        description=(
            f"Conferência registrada no inventário {item.inventario.code}: "
            f"bem {item.asset.tag if item.asset else item.asset_id} => "
            f"{item.status.label}"
            + (f"; local encontrado: {item.found_location_name}" if item.found_location_name else "")
        ),
        new_data={
            "inventario": item.inventario.code,
            "bem": item.asset.tag if item.asset else item.asset_id,
            "resultado": item.status.value,
            "local_encontrado": item.found_location_name,
            "observacao": item.observation,
        },
    )
    return RedirectResponse(url=f"/inventarios/{inventario_id}", status_code=status.HTTP_303_SEE_OTHER)


@web_router.post("/inventarios/{inventario_id}/nao-previsto", dependencies=[Depends(require_permission("inventario.conferir"))])
def register_unlisted_asset(
    request: Request,
    inventario_id: int,
    asset_id: int = Form(...),
    found_location_id: Optional[int] = Form(None),
    observation: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    user = request.state.user
    inv = InventarioService.get_by_id(db, inventario_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventário não encontrado")

    created = False
    tag = None
    try:
        item, created = InventarioService.register_unlisted_asset(
            db,
            inventario=inv,
            asset_id=asset_id,
            found_location_id=found_location_id if found_location_id and found_location_id > 0 else None,
            observation=observation or None,
            user_id=user.id,
            username=user.username,
        )
        tag = item.asset.tag if item.asset else str(asset_id)
    except ValueError as err:
        return RedirectResponse(
            url=f"/inventarios/{inventario_id}?error={quote(str(err))}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if created:
        write_audit(
            db,
            user=user,
            action=ACTION_INVENTARIO,
            module="Inventário",
            resource="InventarioItem",
            resource_id=item.id,
            resource_ref=tag,
            ip_address=_client_ip(request),
            result=RESULT_SUCCESS,
            description=(
                f"Bem não previsto {tag} encontrado em campo durante o inventário "
                f"{inv.code} (ocorrência registrada; cadastro não alterado)"
            ),
            new_data={
                "inventario": inv.code,
                "bem": tag,
                "nao_previsto": True,
                "local_encontrado": item.found_location_name,
                "observacao": item.observation,
            },
        )
    return RedirectResponse(url=f"/inventarios/{inventario_id}", status_code=status.HTTP_303_SEE_OTHER)


@web_router.post("/inventarios/{inventario_id}/offline/coletas/{coleta_id}/reconciliar",
    dependencies=[Depends(require_permission("inventario.conferir"))])
def reconciliar_coleta_offline(
    request: Request,
    inventario_id: int,
    coleta_id: int,
    action: str = Form(...),
    db: Session = Depends(get_db),
):
    """Reconcilia conflito offline pela tela do inventário (P-3/D8): KEEP ou APPLY."""
    from app.services.inventario_offline_service import (
        InventarioOfflineService,
        OfflinePackageError,
    )
    user = request.state.user
    try:
        InventarioOfflineService.reconcile(db, coleta_id=coleta_id, action=action, user=user)
    except OfflinePackageError as err:
        return RedirectResponse(
            url=f"/inventarios/{inventario_id}?error={quote(str(err.detail))}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url=f"/inventarios/{inventario_id}", status_code=status.HTTP_303_SEE_OTHER)


@web_router.get("/sw.js", include_in_schema=False)
def service_worker_js():
    """Serve o Service Worker na raiz (escopo '/' — D4) para que a navegação
    em `/inventarios/{id}/offline` seja cache-first (FR-035). Nenhuma rota de
    API é interceptada (FR-036).
    """
    from pathlib import Path
    from fastapi.responses import FileResponse

    sw_path = Path(__file__).resolve().parent.parent / "static" / "js" / "sw.js"
    return FileResponse(sw_path, media_type="application/javascript")


@web_router.get("/inventarios/{inventario_id}/offline", response_class=HTMLResponse, dependencies=[Depends(require_permission("inventario.visualizar"))])
def view_inventario_offline(
    request: Request,
    inventario_id: int,
    db: Session = Depends(get_db),
):
    """Shell da coleta offline (feature 033; servida cache-first pelo SW apenas nesta rota).

    Nada administrativo é renderizado (FR-030); a coleta em si acontece no client
    (IndexedDB) — esta página é o casco HTML cacheável com indicadores (FR-041).
    """
    inv = InventarioService.get_by_id(db, inventario_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventário não encontrado")
    return templates.TemplateResponse(
        request=request,
        name="inventarios/offline.html",
        context={
            "inv": inv,
            "active_tab": "inventarios",
        },
    )


@web_router.post("/inventarios/{inventario_id}/encerrar", dependencies=[Depends(require_permission("inventario.encerrar"))])
def close_inventario(
    request: Request,
    inventario_id: int,
    closure_notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    user = request.state.user
    inv = InventarioService.get_by_id(db, inventario_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventário não encontrado")

    try:
        InventarioService.close_inventario(
            db,
            inventario=inv,
            closed_by_name=user.username,
            closure_notes=closure_notes or None,
        )
    except ValueError as err:
        return RedirectResponse(
            url=f"/inventarios/{inventario_id}?error={quote(str(err))}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    write_audit(
        db,
        user=user,
        action=ACTION_INVENTARIO,
        module="Inventário",
        resource="Inventario",
        resource_id=inv.id,
        resource_ref=inv.code,
        ip_address=_client_ip(request),
        result=RESULT_SUCCESS,
        description=f"Inventário {inv.code} encerrado e resultados consolidados",
        new_data={
            "code": inv.code,
            "encerrado_em": inv.closed_at.isoformat() if inv.closed_at else None,
            "encerrado_por": inv.closed_by_name,
            "notas_encerramento": inv.closure_notes,
        },
    )
    return RedirectResponse(url=f"/inventarios/{inventario_id}", status_code=status.HTTP_303_SEE_OTHER)
