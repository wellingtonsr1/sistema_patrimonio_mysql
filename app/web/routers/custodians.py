"""Router: COLABORADORES (CUSTODIANS) — Feature 051.

Conteúdo movido LITERALMENTE de `app/web/routes.py` (L1072–1422).
`web_router` é incluído pelo facade na posição original (FR-005).
"""
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import _client_ip, require_permission
from app.schemas.custodian import CustodianCreate, CustodianUpdate
from app.services.custodian_service import CustodianService
from app.services.department_service import DepartmentService
from app.services.custodian_import_service import (
    execute_custodian_import,
    parse_custodian_csv,
    preview_custodian_import,
)
from app.services.audit_service import ACTION_CREATE, ACTION_IMPORT, ACTION_UPDATE, write_audit, write_change_audit
from app.web.routers.templates_env import templates
from app.web.routers.shared import (
    _confirm_payload_rows,
    _dynamic_form,
    _read_csv_upload,
    _render_mapping_step,
    _render_smart_preview,
)

web_router = APIRouter(include_in_schema=False)


def _custodian_audit_snapshot(c) -> dict:
    return {
        "registration_code": c.registration_code,
        "name": c.name,
        "email": c.email,
        "cpf": c.cpf,
        "role": c.role,
        "department": c.department,
        "is_active": c.is_active,
    }


@web_router.get("/custodians", response_class=HTMLResponse, dependencies=[Depends(require_permission("colaboradores.visualizar"))])
def list_custodians_view(request: Request, search: Optional[str] = None, db: Session = Depends(get_db)):
    custodians = CustodianService.get_all(db, search=search)
    for c in custodians:
        c.active_assets_count = CustodianService.count_assigned_assets(db, c.id)

    return templates.TemplateResponse(
        request=request,
        name="custodians/list.html",
        context={"custodians": custodians, "search": search or "", "active_tab": "custodians"}
    )


@web_router.get("/custodians/new", response_class=HTMLResponse, dependencies=[Depends(require_permission("colaboradores.criar"))])
def form_new_custodian(request: Request, error: Optional[str] = None, db: Session = Depends(get_db)):
    # Feature 012: lista oficial de Departamentos/Setores derivada ao vivo dos locais.
    return templates.TemplateResponse(
        request=request,
        name="custodians/form.html",
        context={"error": error or "", "departments": DepartmentService.list_official(db), "active_tab": "custodians"}
    )


@web_router.post("/custodians/new", dependencies=[Depends(require_permission("colaboradores.criar"))])
def create_custodian_form(
    request: Request,
    registration_code: Optional[str] = Form(None),
    name: str = Form(...),
    email: str = Form(...),
    cpf: Optional[str] = Form(None),
    role: str = Form(...),
    department: str = Form(...),
    department_source: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Feature 010: matrícula opcional — deixada em branco, o service gera
    automaticamente um identificador provisório PROV-*.
    Feature 012: com o marcador department_source=official (formulário da
    seleção oficial), o Departamento/Setor é validado/canonizado contra a
    lista oficial (derivada de locations.department) antes de gravar; sem o
    marcador, o comportamento atual é preservado integralmente."""
    if department_source == "official":
        try:
            department = DepartmentService.ensure_official(db, department)
        except ValueError as err:
            return RedirectResponse(url=f"/custodians/new?error={quote(str(err))}", status_code=status.HTTP_303_SEE_OTHER)
    custodian_data = CustodianCreate(
        registration_code=(registration_code or None),
        name=name,
        email=email,
        cpf=cpf or None,
        role=role,
        department=department,
        is_active=True
    )
    try:
        custodian = CustodianService.create(db, custodian_data)
    except ValueError as err:
        return RedirectResponse(url=f"/custodians/new?error={quote(str(err))}", status_code=status.HTTP_303_SEE_OTHER)
    write_change_audit(
        db,
        user=request.state.user,
        action=ACTION_CREATE,
        module="Colaboradores",
        resource="Custodian",
        resource_ref=custodian.registration_code,
        resource_id=custodian.id,
        ip_address=_client_ip(request),
        after=_custodian_audit_snapshot(custodian),
        description=f"Cadastro do colaborador {custodian.name} ({custodian.registration_code})",
    )
    return RedirectResponse(url="/custodians", status_code=status.HTTP_303_SEE_OTHER)


@web_router.get("/custodians/{custodian_id}/edit", response_class=HTMLResponse, dependencies=[Depends(require_permission("colaboradores.editar"))])
def form_edit_custodian(request: Request, custodian_id: int, error: Optional[str] = None, success: Optional[str] = None, db: Session = Depends(get_db)):
    """Exibe o formulário de edição de um colaborador existente.

    A matrícula (registration_code) é o identificador do colaborador e é
    exibida somente para leitura: ela não pode ser alterada pela interface
    de edição, preservando o vínculo dos bens custodiados.
    """
    custodian = CustodianService.get_by_id(db, custodian_id)
    if not custodian:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado")
    # Feature 012: mesma lista oficial do cadastro (derivada de locations.department).
    return templates.TemplateResponse(
        request=request,
        name="custodians/form.html",
        context={
            "custodian": custodian,
            "departments": DepartmentService.list_official(db),
            "error": error or "",
            "success": success or "",
            "active_tab": "custodians"
        }
    )


@web_router.post("/custodians/{custodian_id}/edit", dependencies=[Depends(require_permission("colaboradores.editar"))])
def update_custodian_form(
    request: Request,
    custodian_id: int,
    name: str = Form(...),
    email: str = Form(...),
    cpf: Optional[str] = Form(None),
    role: str = Form(...),
    department: str = Form(...),
    department_source: Optional[str] = Form(None),
    registration_code: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Salva a edição de um colaborador existente.

    Recebe os campos editáveis (nome, e-mail, CPF, cargo e departamento).
    Feature 010: a matrícula é aceita do formulário SOMENTE quando a atual é
    um identificador provisório PROV-* (substituição pela matrícula oficial,
    preservando o mesmo colaborador e os vínculos por FK). Colaboradores com
    matrícula oficial continuam com a matrícula inalterável pela interface.
    A atualização é feita in-place pelo ID, preservando os relacionamentos
    de custódia dos bens.
    """
    before_c = CustodianService.get_by_id(db, custodian_id)
    if not before_c:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado")
    before = _custodian_audit_snapshot(before_c)
    new_code: Optional[str] = None
    # Guard da feature 010: só aplica matrícula informada quando a atual é PROV-*.
    if CustodianService.is_provisional(before_c.registration_code):
        candidate = (registration_code or "").strip()
        if candidate and candidate != before_c.registration_code:
            new_code = candidate
    # Feature 012: validação oficial apenas para valor DIFERENTE do vigente —
    # a submissão idêntica ao valor atual (mesmo fora da lista) é aceita sem
    # re-normalização (FR-014; remediação I2 opção b).
    if department_source == "official" and (department or "").strip() != (before_c.department or "").strip():
        try:
            department = DepartmentService.ensure_official(db, department)
        except ValueError as err:
            return RedirectResponse(url=f"/custodians/{custodian_id}/edit?error={quote(str(err))}", status_code=status.HTTP_303_SEE_OTHER)
    update_data = CustodianUpdate(
        registration_code=new_code,
        name=name,
        email=email,
        cpf=cpf or None,
        role=role,
        department=department,
    )
    try:
        custodian = CustodianService.update(db, custodian_id, update_data)
    except ValueError as err:
        return RedirectResponse(url=f"/custodians/{custodian_id}/edit?error={quote(str(err))}", status_code=status.HTTP_303_SEE_OTHER)
    if not custodian:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado")
    write_change_audit(
        db,
        user=request.state.user,
        action=ACTION_UPDATE,
        module="Colaboradores",
        resource="Custodian",
        resource_ref=custodian.registration_code,
        resource_id=custodian.id,
        ip_address=_client_ip(request),
        before=before,
        after=_custodian_audit_snapshot(custodian),
        description=f"Edição do colaborador {custodian.name} ({custodian.registration_code})",
    )
    return RedirectResponse(url=f"/custodians/{custodian_id}/edit?success={quote('Colaborador atualizado com sucesso.')}", status_code=status.HTTP_303_SEE_OTHER)


@web_router.get("/custodians/import", response_class=HTMLResponse, dependencies=[Depends(require_permission("colaboradores.criar"))])
def form_import_custodians(request: Request):
    """Exibe o formulário de importação CSV de colaboradores"""
    return templates.TemplateResponse(
        request=request,
        name="custodians/import.html",
        context={"active_tab": "custodians"}
    )


@web_router.post("/custodians/import", response_class=HTMLResponse, dependencies=[Depends(require_permission("colaboradores.criar"))])
def process_import_custodians(
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
                name="custodians/import.html",
                context={
                    "active_tab": "custodians",
                    "error": "Dados do mapeamento ausentes. Envie o arquivo novamente.",
                }
            )
        return _render_smart_preview(
            request=request,
            template_name="custodians/import.html",
            kind="custodians",
            content=csv_content,
            mapping_raw=mapping,
            dynamic_form=_dynamic_form(request),
            filtro=filtro,
            filename=filename or "",
            skip_duplicates=skip_duplicates,
            active_tab="custodians",
            form_action="/custodians/import",
            confirm_action="/custodians/import/confirm",
            back_url="/custodians/import",
            db=db,
        )

    content, error_response = _read_csv_upload(request, file, "custodians/import.html", "custodians")
    if error_response is not None:
        return error_response

    return _render_mapping_step(
        request=request,
        template_name="custodians/import.html",
        kind="custodians",
        content=content,
        filename=file.filename or "",
        skip_duplicates=skip_duplicates,
        active_tab="custodians",
        form_action="/custodians/import",
        back_url="/custodians/import",
    )


@web_router.post("/custodians/import/confirm", dependencies=[Depends(require_permission("colaboradores.criar"))])
def confirm_import_custodians(
    request: Request,
    csv_data: Optional[str] = Form(None),
    csv_content: Optional[str] = Form(None),
    mapping: Optional[str] = Form(None),
    skip_duplicates: bool = Form(True),
    resolutions: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Confirma e executa a importação de colaboradores (Feature 048)"""
    rows, class_counts, parse_err = _confirm_payload_rows(
        csv_data, resolutions, db, _dynamic_form(request),
        csv_content=csv_content, mapping_raw=mapping, kind="custodians",
    )
    if parse_err is not None:
        return templates.TemplateResponse(
            request=request,
            name="custodians/import.html",
            context={
                "active_tab": "custodians",
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
        result = execute_custodian_import(rows, db, skip_duplicates=skip_duplicates)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="custodians/import.html",
            context={
                "active_tab": "custodians",
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
        module="Colaboradores",
        resource="Custodian",
        resource_ref="importacao-csv",
        ip_address=_client_ip(request),
        description=f"Importação CSV de colaboradores: {result.get('imported', 0)} importados, "
                    f"{result.get('skipped', 0)} ignorados, {len(result.get('errors', []))} erros"
                    f"{_counts_desc}",
        new_data={"imported": result.get("imported", 0), "skipped": result.get("skipped", 0)},
    )

    return templates.TemplateResponse(
        request=request,
        name="custodians/import.html",
        context={
            "active_tab": "custodians",
            "show_result": True,
            "result": result,
        }
    )


@web_router.get("/custodians/{custodian_id}", response_class=HTMLResponse, dependencies=[Depends(require_permission("colaboradores.visualizar"))])
def view_custodian_detail(request: Request, custodian_id: int, db: Session = Depends(get_db)):
    custodian = CustodianService.get_by_id(db, custodian_id)
    if not custodian:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado")

    assigned_assets = CustodianService.get_assigned_assets(db, custodian_id)

    return templates.TemplateResponse(
        request=request,
        name="custodians/detail.html",
        context={
            "custodian": custodian,
            "assets": assigned_assets,
            "active_tab": "custodians"
        }
    )
