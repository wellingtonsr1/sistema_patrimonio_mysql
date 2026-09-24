"""
Service da coleta offline de inventário (feature 033).

Regras de negócio do modo offline (Princípio III — nada de regra em rotas):

- Pacote: gerado ON-DEMAND a partir do snapshot `inventario_itens` (D9), com
  `snapshot_version` determinístico (SHA-256 do conjunto ordenado
  asset_id:item_id:status) e SOMENTE os campos mínimos do FR-003. Nenhum write
  no cadastro (FR-005/Princípio V).
- Estados preparáveis: PLANNED/IN_PROGRESS; encerrado → recusado (C-2/P-2).
- Limite: 1.000 itens por pacote (D9/SC-001); inventário sem itens → recusa.

O coletador NUNCA é fonte de verdade: a sincronização revalida tudo no
servidor (FR-025) e grava EXCLUSIVAMENTE via `InventarioService.record_check`
/ `register_unlisted_asset` (FR-026/Princípios III e V).
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.enums import InventarioItemStatus, InventarioStatus
from app.models.inventario import Inventario, InventarioItem
from app.utils.time_utils import now_utc

# Limite de volume por pacote/lote (D9; SC-001 assume 1.000)
MAX_PACKAGE_ITEMS = 1_000
MAX_SYNC_OPERATIONS = 1_000

# Estados que permitem preparação/sync (C-2/P-2)
PREPARABLE_STATUSES = (InventarioStatus.PLANNED, InventarioStatus.IN_PROGRESS)

SNAPSHOT_SCHEMA_VERSION = "1"  # versão do schema do pacote (entra no hash)


class OfflinePackageError(Exception):
    """Erro de regra de negócio do modo offline (com status HTTP sugerido)."""

    def __init__(self, detail: str, status_code: int = 422):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class InventarioOfflineService:
    """Pacote offline, sincronização idempotente e reconciliação de conflitos."""

    # ------------------------------------------------------------------
    # Pacote offline (US1)
    # ------------------------------------------------------------------

    @staticmethod
    def compute_snapshot_version(db: Session, inventory_id: int) -> str:
        """Versão determinística da base de coleta (D9/FR-004).

        SHA-256 do conjunto ordenado (asset_id, item_id) do snapshot + versão
        do schema. O STATUS não compõe a versão (ajuste registrado no
        tasks.md/Notes): conferências online e coletas aceitas alteram o
        status durante o inventário válido por design (C-3/C-5) — incluir o
        status invalidaria o pacote na própria sincronização. A versão
        identifica a BASE de coleta (quais itens eram esperados).
        """
        rows = (
            db.query(
                InventarioItem.asset_id,
                InventarioItem.id,
            )
            .filter(
                InventarioItem.inventario_id == inventory_id,
                InventarioItem.nao_previsto.is_(False),
            )
            .order_by(InventarioItem.asset_id, InventarioItem.id)
            .all()
        )
        material = ";".join(f"{asset_id}:{item_id}" for asset_id, item_id in rows)
        return hashlib.sha256(
            f"v{SNAPSHOT_SCHEMA_VERSION}|{material}".encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _load_open_inventario(db: Session, inventory_id: int) -> Inventario:
        inv = (
            db.query(Inventario)
            .options(joinedload(Inventario.itens).joinedload(InventarioItem.asset))
            .filter(Inventario.id == inventory_id)
            .first()
        )
        if inv is None:
            raise OfflinePackageError("Inventário não encontrado.", status_code=404)
        if inv.status not in PREPARABLE_STATUSES:
            raise OfflinePackageError(
                "Este inventário está encerrado; não pode ser preparado para coleta offline.",
                status_code=409,
            )
        return inv

    @staticmethod
    def generate_package(db: Session, *, inventory_id: int, base_origin: str) -> Dict[str, Any]:
        """Gera o pacote offline on-demand (contrato §2; D9).

        Somente leitura: nenhum write no cadastro ou no snapshot (FR-005).
        """
        inv = InventarioOfflineService._load_open_inventario(db, inventory_id)

        items = [i for i in inv.itens if not i.nao_previsto]
        if not items:
            raise OfflinePackageError(
                "Inventário sem itens gerados; nada a preparar para coleta offline.",
                status_code=422,
            )
        if len(items) > MAX_PACKAGE_ITEMS:
            raise OfflinePackageError(
                f"Snapshot acima do limite de {MAX_PACKAGE_ITEMS} itens por pacote offline.",
                status_code=422,
            )

        origin = base_origin.rstrip("/")
        package_items: List[Dict[str, Any]] = []
        for item in sorted(items, key=lambda i: i.id):
            asset = item.asset
            package_items.append(
                {
                    "asset_id": item.asset_id,
                    "item_id": item.id,
                    "tag": asset.tag if asset else None,
                    "serial_number": asset.serial_number if asset else None,
                    "description": asset.name if asset else None,
                    "expected_location_id": item.expected_location_id,
                    "expected_location_name": item.expected_location_name,
                    # Fato do repositório: o snapshot não tem expected_custodian_id
                    # (apenas o nome textual); mantém contrato sem inventar dado.
                    "expected_custodian_id": None,
                    "expected_custodian_name": item.expected_custodian_name,
                    "qr_url": f"{origin}/assets/{item.asset_id}",  # D2
                }
            )

        return {
            "inventory_id": inv.id,
            "inventory_code": inv.code,
            "inventory_status": inv.status.value,
            "snapshot_version": InventarioOfflineService.compute_snapshot_version(
                db, inv.id
            ),
            "generated_at": now_utc().isoformat(),
            "expires_when": "inventory_closed_or_reprepared",  # P-2
            "items": package_items,
        }

    # ------------------------------------------------------------------
    # Sincronização (US3) — revalida tudo (FR-025); grava EXCLUSIVAMENTE via
    # InventarioService (FR-026); idempotente (UNIQUE + C-5); conflitos
    # preservados sem sobrescrita silenciosa (C-5/FR-027).
    # ------------------------------------------------------------------

    @staticmethod
    def process_sync(
        db: Session,
        *,
        inventory_id: int,
        device_id: str,
        snapshot_version: str,
        operations: List[Dict[str, Any]],
        user,
    ) -> Dict[str, Any]:
        """Processa um lote de operações offline (contrato §3).

        Processamento POR OPERAÇÃO (FR-022/SC-005): uma operação inválida não
        aborta o lote; aceitas permanecem gravadas mesmo em queda posterior.
        """
        from app.models.asset import Asset
        from app.models.location import Location
        from app.services.audit_service import (
            ACTION_INVENTARIO_OFFLINE_CONFLITO,
            ACTION_INVENTARIO_OFFLINE_REJEITADO,
            ACTION_INVENTARIO_OFFLINE_SYNC,
            write_audit,
        )
        from app.services.inventario_service import InventarioService
        from app.models.inventario_offline import InventarioOfflineColeta
        from app.models.enums import InventarioOfflineColetaStatus as Status

        valid_results = {
            InventarioItemStatus.FOUND.value,
            InventarioItemStatus.FOUND_WRONG_LOCATION.value,
            InventarioItemStatus.NOT_FOUND.value,
            InventarioItemStatus.UNIDENTIFIED.value,
        }
        results: Dict[str, List[Dict[str, Any]]] = {
            "accepted": [], "duplicated": [], "conflicts": [], "rejected": [],
        }

        inv = db.get(Inventario, inventory_id)
        if inv is None:
            raise OfflinePackageError("Inventário não encontrado.", status_code=404)

        current_snapshot = InventarioOfflineService.compute_snapshot_version(
            db, inventory_id
        )
        inventory_open = inv.status in PREPARABLE_STATUSES

        def _coleta_row(op: Dict[str, Any], status: Status, reason: Optional[str] = None):
            collected_at = op.get("collected_at")
            if isinstance(collected_at, str):
                try:
                    collected_at = datetime.fromisoformat(collected_at)
                except ValueError:
                    collected_at = now_utc()
            return InventarioOfflineColeta(
                inventory_id=inventory_id,
                client_operation_id=op["client_operation_id"],
                status=status,
                asset_id=op.get("asset_id") or 0,
                inventario_item_id=op.get("item_id"),
                operation=op.get("operation", "CHECK"),
                result=op.get("result"),
                found_location_id=op.get("found_location_id"),
                found_custodian_id=op.get("found_custodian_id"),
                observation=op.get("observation"),
                device_id=device_id,
                user_id=user.id if user else None,
                username=user.username if user else None,
                collected_at=collected_at or now_utc(),
                received_at=now_utc(),
                client_payload=json.dumps(op, default=str),
                reject_reason=reason,
            )

        def _reject(op: Dict[str, Any], reason: str, detail: str):
            db.add(_coleta_row(op, Status.REJECTED, reason))
            db.commit()
            results["rejected"].append(
                {"client_operation_id": op["client_operation_id"], "reason": reason, "detail": detail}
            )
            write_audit(
                db,
                user=user,
                action=ACTION_INVENTARIO_OFFLINE_REJEITADO,
                module="Inventário",
                resource="inventario_offline_coleta",
                resource_id=inventory_id,
                resource_ref=f"/inventarios/{inventory_id}",
                description=f"Coleta offline rejeitada ({reason}): {op['client_operation_id'][:16]}…",
            )

        for op in operations:
            op_id = op["client_operation_id"]

            # 1) Idempotência forte: (inventory_id, client_operation_id) já recebido
            existing = (
                db.query(InventarioOfflineColeta)
                .filter(
                    InventarioOfflineColeta.inventory_id == inventory_id,
                    InventarioOfflineColeta.client_operation_id == op_id,
                )
                .first()
            )
            if existing is not None:
                results["duplicated"].append(
                    {"client_operation_id": op_id, "reason": "already_received"}
                )
                continue

            # 2) Inventário encerrado → todas as operações rejeitadas (C-2/FR-025)
            if not inventory_open:
                _reject(op, "inventario_encerrado",
                        "Inventário encerrado; coleta tardia não pode ser aplicada.")
                continue

            # 3) Coleta sobre base diferente → snapshot_mismatch (FR-004/D9)
            if snapshot_version != current_snapshot:
                _reject(op, "snapshot_mismatch",
                        "Coleta feita sobre um snapshot diferente do atual; re-prepare o pacote.")
                continue

            # 4) Validações de referência (servidor é a autoridade — FR-025)
            result = op.get("result")
            if op.get("operation") == "CHECK" and result not in valid_results:
                _reject(op, "resultado_invalido", "Resultado declarado não é válido.")
                continue
            found_location_id = op.get("found_location_id")
            found_location_name = op.get("found_location_name")
            if found_location_id is None and found_location_name:
                # Coleta offline divergente: o cliente pode conhecer o local
                # apenas pelo NOME (o pacote não carrega catálogo de locais —
                # FR-003). O servidor resolve o id por nome exato (único);
                # sem match → rejeição estável preservando a coleta.
                match = (
                    db.query(Location)
                    .filter(Location.name == found_location_name.strip())
                    .all()
                )
                if len(match) == 1:
                    found_location_id = match[0].id
            if found_location_id is not None and not db.get(Location, found_location_id):
                _reject(op, "local_inexistente", "Local encontrado não existe no cadastro.")
                continue
            if op.get("found_custodian_id") is not None:
                from app.models.custodian import Custodian
                if not db.get(Custodian, op["found_custodian_id"]):
                    _reject(op, "responsavel_inexistente", "Responsável encontrado não existe no cadastro.")
                    continue

            try:
                if op.get("operation") == "CHECK":
                    item = db.get(InventarioItem, op.get("item_id") or 0)
                    if (
                        item is None
                        or item.inventario_id != inventory_id
                        or item.nao_previsto
                        or item.asset_id != op.get("asset_id")
                    ):
                        _reject(op, "asset_fora_do_snapshot",
                                "Bem/item não pertence ao snapshot deste inventário.")
                        continue

                    item_status = InventarioItemStatus(result)
                    if item.status != InventarioItemStatus.PENDING:
                        if item.status.value == result:
                            # C-5: resultado igual ao já registrado → idempotente
                            db.add(_coleta_row(op, Status.DUPLICATED))
                            db.commit()
                            results["duplicated"].append(
                                {"client_operation_id": op_id, "reason": "already_processed"}
                            )
                            continue
                        # C-5/FR-027: divergente → CONFLICT preservado, NUNCA sobrescreve
                        row = _coleta_row(op, Status.CONFLICT)
                        db.add(row)
                        db.commit()
                        db.refresh(row)
                        results["conflicts"].append(
                            {"client_operation_id": op_id, "item_id": item.id,
                             "coleta_id": row.id, "reason": "result_diverges"}
                        )
                        write_audit(
                            db,
                            user=user,
                            action=ACTION_INVENTARIO_OFFLINE_CONFLITO,
                            module="Inventário",
                            resource="inventario_offline_coleta",
                            resource_id=row.id,
                            resource_ref=f"/inventarios/{inventory_id}",
                            description=(
                                f"Conflito offline no item {item.id}: coleta {op_id[:16]}… "
                                f"declara '{result}'; item está '{item.status.value}'."
                            ),
                        )
                        continue

                    # Caminho oficial ÚNICO de gravação (FR-026/Princípios III e V)
                    if item_status == InventarioItemStatus.FOUND_WRONG_LOCATION and not found_location_id:
                        _reject(op, "local_nao_resolvido",
                                "Local encontrado não pôde ser identificado pelo servidor.")
                        continue
                    record = InventarioService.record_check(
                        db,
                        item=item,
                        result=item_status,
                        found_location_id=found_location_id,
                        observation=op.get("observation"),
                        user_id=user.id if user else None,
                        username=user.username if user else None,
                    )
                    row = _coleta_row(op, Status.ACCEPTED)
                    row.synced_at = now_utc()
                    db.add(row)
                    db.commit()
                    results["accepted"].append(
                        {"client_operation_id": op_id, "item_id": record.id,
                         "item_status": record.status.value}
                    )
                else:  # UNLISTED
                    asset = db.get(Asset, op.get("asset_id") or 0)
                    if not asset:
                        _reject(op, "asset_inexistente", "Patrimônio não encontrado no cadastro.")
                        continue
                    unlisted_item, created = InventarioService.register_unlisted_asset(
                        db,
                        inventario=inv,
                        asset_id=asset.id,
                        found_location_id=found_location_id,
                        observation=op.get("observation"),
                        user_id=user.id if user else None,
                        username=user.username if user else None,
                    )
                    status = Status.ACCEPTED if created else Status.DUPLICATED
                    row = _coleta_row(op, status)
                    row.synced_at = now_utc()
                    db.add(row)
                    db.commit()
                    bucket = "accepted" if created else "duplicated"
                    entry: Dict[str, Any] = {"client_operation_id": op_id}
                    if bucket == "accepted":
                        entry["item_id"] = unlisted_item.id
                        entry["item_status"] = unlisted_item.status.value
                    else:
                        entry["reason"] = "already_registered"
                    results[bucket].append(entry)
            except ValueError as err:
                db.rollback()
                _reject(op, "validacao_falhou", str(err))

        # Auditoria consolidada do lote (sem credenciais — FR-044)
        write_audit(
            db,
            user=user,
            action=ACTION_INVENTARIO_OFFLINE_SYNC,
            module="Inventário",
            resource="inventario_offline_sync",
            resource_id=inventory_id,
            resource_ref=f"/inventarios/{inventory_id}",
            description=(
                f"Sync offline (dispositivo {device_id[:16]}…): "
                f"{len(results['accepted'])} aceitas, {len(results['duplicated'])} duplicadas, "
                f"{len(results['conflicts'])} conflitos, {len(results['rejected'])} rejeitadas."
            ),
        )

        return {
            "inventory_id": inventory_id,
            "inventory_status": inv.status.value,
            "server_time": now_utc().isoformat(),
            **results,
        }

    # ------------------------------------------------------------------
    # Consulta de coletas (§4) e reconciliação de conflitos (§5/D8)
    # ------------------------------------------------------------------

    @staticmethod
    def list_coletas(
        db: Session,
        *,
        inventory_id: int,
        status: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        from app.models.inventario_offline import InventarioOfflineColeta
        from app.models.enums import InventarioOfflineColetaStatus as Status

        q = db.query(InventarioOfflineColeta).filter(
            InventarioOfflineColeta.inventory_id == inventory_id
        )
        if status:
            try:
                q = q.filter(InventarioOfflineColeta.status == Status(status))
            except ValueError:
                raise OfflinePackageError("Status inválido para consulta.", status_code=422)
        if device_id:
            q = q.filter(InventarioOfflineColeta.device_id == device_id)
        rows = q.order_by(InventarioOfflineColeta.id).all()
        return {
            "inventory_id": inventory_id,
            "total": len(rows),
            "coletas": [
                {
                    "id": r.id,
                    "client_operation_id": r.client_operation_id,
                    "operation": r.operation,
                    "status": r.status.value,
                    "asset_id": r.asset_id,
                    "item_id": r.inventario_item_id,
                    "device_id": r.device_id,
                    "username": r.username,
                    "result": r.result,
                    "collected_at": r.collected_at.isoformat() if r.collected_at else None,
                    "received_at": r.received_at.isoformat() if r.received_at else None,
                    "reject_reason": r.reject_reason,
                    "reconcile_action": r.reconcile_action,
                }
                for r in rows
            ],
        }

    @staticmethod
    def reconcile(
        db: Session,
        *,
        coleta_id: int,
        action: str,
        user,
    ) -> Dict[str, Any]:
        """Reconcilia um conflito (D8): KEEP mantém o item; APPLY grava via record_check."""
        from app.services.audit_service import (
            ACTION_INVENTARIO_OFFLINE_RECONCILED,
            write_audit,
        )
        from app.services.inventario_service import InventarioService
        from app.models.inventario_offline import InventarioOfflineColeta
        from app.models.enums import InventarioOfflineColetaStatus as Status

        if action not in ("KEEP", "APPLY"):
            raise OfflinePackageError("Ação de reconciliação inválida (use KEEP ou APPLY).", 422)
        row = db.get(InventarioOfflineColeta, coleta_id)
        if row is None:
            raise OfflinePackageError("Coleta offline não encontrada.", status_code=404)
        if row.status != Status.CONFLICT:
            raise OfflinePackageError(
                "Somente coletas em CONFLITO podem ser reconciliadas.", status_code=409
            )

        item = db.get(InventarioItem, row.inventario_item_id) if row.inventario_item_id else None
        if action == "APPLY":
            if item is None or not row.result:
                raise OfflinePackageError("Coleta sem item/resultado aplicável.", status_code=422)
            inv = db.get(Inventario, row.inventory_id)
            if inv is None or inv.status not in PREPARABLE_STATUSES:
                raise OfflinePackageError(
                    "Inventário encerrado; a coleta não pode ser aplicada.", status_code=409
                )
            try:
                item = InventarioService.record_check(
                    db,
                    item=item,
                    result=InventarioItemStatus(row.result),
                    found_location_id=row.found_location_id,
                    observation=row.observation,
                    user_id=user.id if user else None,
                    username=user.username if user else None,
                )
            except ValueError as err:
                raise OfflinePackageError(str(err), status_code=409)

        row.status = Status.RECONCILED
        row.reconciled_at = now_utc()
        row.reconciled_by_id = user.id if user else None
        row.reconcile_action = action
        db.commit()

        write_audit(
            db,
            user=user,
            action=ACTION_INVENTARIO_OFFLINE_RECONCILED,
            module="Inventário",
            resource="inventario_offline_coleta",
            resource_id=row.id,
            resource_ref=f"/inventarios/{row.inventory_id}",
            description=f"Conflito offline {row.client_operation_id[:16]}… reconciliado com '{action}'.",
        )
        return {
            "coleta_id": row.id,
            "status": row.status.value,
            "action": action,
            "item_id": item.id if item else None,
            "item_status": item.status.value if item else None,
        }
