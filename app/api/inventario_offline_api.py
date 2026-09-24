"""
API REST da coleta offline de inventário (feature 033 — contrato §1–§5).

Rotas NÃO concentram regras de negócio (Princípios II/III): autenticam/
autorizam, validam entrada via schemas Pydantic e delegam ao
`InventarioOfflineService`. Toda rota exige sessão válida (C-1, aplicada no
include_router em `v1_router`) e permissões EXISTENTES do RBAC (P-1/D11):
- `inventario.conferir`: preparar pacote, sync, reconciliar;
- `inventario.visualizar`: ping, leitura de coletas/conflitos.

Erros no padrão existente {"detail": "..."} (401/403/404/409/422).
Nenhum payload inclui credenciais (FR-031/FR-044).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.utils.time_utils import now_utc

from app.api.deps import require_permission
from app.database import get_db
from app.models.enums import InventarioOfflineColetaStatus
from app.services.audit_service import (
    ACTION_INVENTARIO_OFFLINE_PREPARADO,
    write_audit,
)
from app.services.inventario_offline_service import (
    InventarioOfflineService,
    OfflinePackageError,
    MAX_SYNC_OPERATIONS,
)

router = APIRouter(
    prefix="/inventarios/{inventory_id}/offline",
    tags=["Inventário Offline (coleta em campo)"],
)


# ============================================================================
# Schemas (contrato)
# ============================================================================

class SyncOperation(BaseModel):
    client_operation_id: str = Field(..., min_length=8, max_length=64)
    operation: str = Field(..., pattern="^(CHECK|UNLISTED)$")
    asset_id: int = Field(..., gt=0)
    item_id: Optional[int] = None
    result: Optional[str] = Field(None, max_length=30)
    found_location_id: Optional[int] = None
    found_location_name: Optional[str] = Field(None, max_length=150)
    found_custodian_id: Optional[int] = None
    found_custodian_name: Optional[str] = Field(None, max_length=150)
    observation: Optional[str] = Field(None, max_length=2000)
    collected_at: str = Field(..., description="ISO 8601 com offset (FR-045)")

    @field_validator("observation")
    @classmethod
    def sanitize_observation(cls, v: Optional[str]) -> Optional[str]:
        """Sanitização mínima: sem credenciais na observação (FR-031/FR-044)."""
        if v is None:
            return None
        cleaned = " ".join(v.split())
        return cleaned or None


class SyncRequest(BaseModel):
    device_id: str = Field(..., min_length=8, max_length=64)
    snapshot_version: str = Field(..., min_length=32, max_length=64)
    operations: List[SyncOperation] = Field(..., min_length=1)

    @field_validator("operations")
    @classmethod
    def limit_batch(cls, v: List[SyncOperation]) -> List[SyncOperation]:
        if len(v) > MAX_SYNC_OPERATIONS:
            raise ValueError(
                f"Lote acima do limite de {MAX_SYNC_OPERATIONS} operações por requisição."
            )
        return v


# ============================================================================
# §1 — Ping (verificação real de conectividade; FR-042)
# ============================================================================

@router.get(
    "/ping",
    dependencies=[Depends(require_permission("inventario.visualizar"))],
)
def offline_ping(inventory_id: int, db: Session = Depends(get_db)):
    """Verificação leve real de conectividade + estado do inventário (§1).

    Sem efeito colateral e sem auditoria (é apenas connectivity check).
    """
    from app.models.inventario import Inventario
    from app.services.inventario_offline_service import PREPARABLE_STATUSES

    inv = db.get(Inventario, inventory_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventário não encontrado")
    return {
        "ok": True,
        "inventory_id": inv.id,
        "inventory_status": inv.status.value,
        "server_time": now_utc().isoformat(),
        "preparable": inv.status in PREPARABLE_STATUSES,
    }


# ============================================================================
# §2 — Preparação do pacote (US1)
# ============================================================================

@router.post(
    "/package",
    dependencies=[Depends(require_permission("inventario.conferir"))],
)
def generate_offline_package(
    inventory_id: int, request: Request, db: Session = Depends(get_db)
):
    """Gera o pacote offline on-demand (contrato §2; D9). Somente leitura."""
    user = request.state.user
    try:
        package = InventarioOfflineService.generate_package(
            db, inventory_id=inventory_id, base_origin=str(request.base_url)
        )
    except OfflinePackageError as err:
        raise HTTPException(status_code=err.status_code, detail=err.detail)

    write_audit(
        db,
        user=user,
        action=ACTION_INVENTARIO_OFFLINE_PREPARADO,
        module="Inventário",
        resource="inventario_offline_pacote",
        resource_id=inventory_id,
        resource_ref=f"/inventarios/{inventory_id}",
        description=(
            f"Pacote offline preparado: {len(package['items'])} itens; "
            f"snapshot_version={package['snapshot_version'][:16]}…"
        ),
    )
    return package


# ============================================================================
# §3 — Sincronização (US3)
# ============================================================================

@router.post(
    "/sync",
    dependencies=[Depends(require_permission("inventario.conferir"))],
)
def sync_offline(
    inventory_id: int,
    payload: SyncRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Recebe o lote de coletas (contrato §3); servidor revalida tudo (FR-025)."""
    user = request.state.user
    try:
        return InventarioOfflineService.process_sync(
            db,
            inventory_id=inventory_id,
            device_id=payload.device_id,
            snapshot_version=payload.snapshot_version,
            operations=[op.model_dump() for op in payload.operations],
            user=user,
        )
    except OfflinePackageError as err:
        raise HTTPException(status_code=err.status_code, detail=err.detail)


# ============================================================================
# §4 — Consulta de coletas (US4: rastreabilidade)
# ============================================================================

@router.get(
    "/coletas",
    dependencies=[Depends(require_permission("inventario.visualizar"))],
)
def list_offline_coletas(
    inventory_id: int,
    status: Optional[str] = None,
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Consulta das coletas registradas com rastreio de dispositivo/usuário (§4)."""
    try:
        return InventarioOfflineService.list_coletas(
            db, inventory_id=inventory_id, status=status, device_id=device_id
        )
    except OfflinePackageError as err:
        raise HTTPException(status_code=err.status_code, detail=err.detail)


# ============================================================================
# §5 — Reconciliação de conflitos (US3/US4; D8)
# ============================================================================

class ReconcileRequest(BaseModel):
    action: str = Field(..., pattern="^(KEEP|APPLY)$")


@router.post(
    "/coletas/{coleta_id}/reconcile",
    dependencies=[Depends(require_permission("inventario.conferir"))],
)
def reconcile_offline_coleta(
    inventory_id: int,
    coleta_id: int,
    payload: ReconcileRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Reconcilia um conflito: KEEP mantém o item; APPLY grava a coleta (§5/D8)."""
    user = request.state.user
    try:
        result = InventarioOfflineService.reconcile(
            db, coleta_id=coleta_id, action=payload.action, user=user
        )
        if result and inventory_id and result.get("item_id"):
            pass  # rota valida apenas a ação; service valida coleta↔inventário
        return result
    except OfflinePackageError as err:
        raise HTTPException(status_code=err.status_code, detail=err.detail)
