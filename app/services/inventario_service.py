"""
Serviço do módulo de Inventário Patrimonial Completo e Comprobatório.

Regras de ouro (spec §10 e §18):
- O inventário NUNCA altera o cadastro do patrimônio (assets, movements,
  locations). Uma divergência é apenas REGISTRADA para tratamento posterior
  pelos fluxos próprios (movimentação, edição de cadastro).
- Referencia os bens existentes (asset_id) e faz snapshot textual da
  expectativa — sem duplicar dados cadastrais.
- Encerramento trava as conferências (itens passam a ser imutáveis).
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.asset import Asset
from app.models.location import Location
from app.models.custodian import Custodian
from app.models.enums import AssetStatus, InventarioStatus, InventarioItemStatus
from app.models.inventario import Inventario, InventarioItem


class InventarioService:
    # ------------------------------------------------------------------
    # Criação e escopo
    # ------------------------------------------------------------------

    @staticmethod
    def next_code(db: Session) -> str:
        """Gera o próximo código sequencial INV-YYYY-NNNN."""
        year = datetime.utcnow().year
        prefix = f"INV-{year}-"
        last = (
            db.query(Inventario.code)
            .filter(Inventario.code.like(f"{prefix}%"))
            .order_by(Inventario.code.desc())
            .first()
        )
        seq = int(last[0].rsplit("-", 1)[1]) + 1 if last else 1
        return f"{prefix}{seq:04d}"

    @staticmethod
    def _scope_description(location: Optional[Location], department: Optional[str]) -> str:
        parts = []
        if location:
            parts.append(f"Local: {location.name}")
        if department:
            parts.append(f"Setor: {department}")
        return "; ".join(parts) if parts else "Todo o acervo (todos os locais e setores)"

    @staticmethod
    def create_inventario(
        db: Session,
        *,
        name: str,
        location_id: Optional[int] = None,
        department: Optional[str] = None,
        notes: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_name: Optional[str] = None,
    ) -> Inventario:
        """Cria o inventário e gera imediatamente a lista de bens esperados (snapshot)."""
        name = (name or "").strip()
        if not name:
            raise ValueError("O nome do inventário é obrigatório.")

        location = db.get(Location, location_id) if location_id else None
        if location_id and not location:
            raise ValueError("Local informado no escopo não existe.")

        inv = Inventario(
            code=InventarioService.next_code(db),
            name=name,
            status=InventarioStatus.PLANNED,
            location_id=location.id if location else None,
            department=(department or "").strip() or None,
            scope_filters=InventarioService._scope_description(location, department),
            notes=notes or None,
            created_by_id=created_by_id,
            created_by_name=created_by_name,
        )
        db.add(inv)
        db.flush()  # garante inv.id para os itens

        InventarioService.generate_items(db, inv)
        db.commit()
        db.refresh(inv)
        return inv

    @staticmethod
    def _scope_query(db: Session, *, location_id: Optional[int], department: Optional[str]):
        """Bens esperados no escopo: todos os não baixados, filtrados por local/setor."""
        query = db.query(Asset).filter(Asset.status != AssetStatus.WRITTEN_OFF)
        if location_id:
            query = query.filter(Asset.location_id == location_id)
        if department:
            query = query.join(Location, Asset.location_id == Location.id).filter(
                Location.department == department
            )
        return query

    @staticmethod
    def generate_items(db: Session, inv: Inventario) -> int:
        """
        Gera os itens esperados (snapshot da localização/colaborador atuais).
        Idempotente: ignora bens que já estejam na lista (evita duplicidade
        se chamado novamente). Retorna quantos itens foram adicionados.
        """
        existing = {i.asset_id for i in db.query(InventarioItem.asset_id).filter(
            InventarioItem.inventario_id == inv.id
        ).all()}
        added = 0
        assets = InventarioService._scope_query(
            db, location_id=inv.location_id, department=inv.department
        ).options(joinedload(Asset.custodian)).all()
        for asset in assets:
            if asset.id in existing:
                continue
            db.add(InventarioItem(
                inventario_id=inv.id,
                asset_id=asset.id,
                expected_location_id=asset.location_id,
                expected_location_name=asset.location.name if asset.location else None,
                expected_custodian_name=asset.custodian.name if asset.custodian else None,
            ))
            added += 1
        return added

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    @staticmethod
    def get_all(db: Session, search: Optional[str] = None, status: Optional[InventarioStatus] = None) -> List[Inventario]:
        query = db.query(Inventario).options(joinedload(Inventario.location))
        if search:
            term = f"%{search.strip()}%"
            query = query.filter((Inventario.name.ilike(term)) | (Inventario.code.ilike(term)))
        if status:
            query = query.filter(Inventario.status == status)
        return query.order_by(Inventario.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, inventario_id: int) -> Optional[Inventario]:
        return (
            db.query(Inventario)
            .options(joinedload(Inventario.itens).joinedload(InventarioItem.asset))
            .filter(Inventario.id == inventario_id)
            .first()
        )

    @staticmethod
    def get_item(db: Session, item_id: int) -> Optional[InventarioItem]:
        return (
            db.query(InventarioItem)
            .options(joinedload(InventarioItem.asset).joinedload(Asset.location))
            .filter(InventarioItem.id == item_id)
            .first()
        )

    @staticmethod
    def get_item_for_conference(db: Session, inventario_id: int, asset_id: int) -> Optional[InventarioItem]:
        """Localiza o item de um bem dentro do inventário (fluxo QR/busca)."""
        return (
            db.query(InventarioItem)
            .filter(
                InventarioItem.inventario_id == inventario_id,
                InventarioItem.asset_id == asset_id,
            )
            .first()
        )

    @staticmethod
    def summary(db: Session, inventario_id: int) -> dict:
        """Consolidação dos resultados (comprobatória)."""
        rows = (
            db.query(InventarioItem.status, func.count(InventarioItem.id))
            .filter(
                InventarioItem.inventario_id == inventario_id,
                InventarioItem.nao_previsto == False,  # noqa: E712
            )
            .group_by(InventarioItem.status)
            .all()
        )
        counts = {status: count for status, count in rows}
        unlisted = (
            db.query(func.count(InventarioItem.id))
            .filter(
                InventarioItem.inventario_id == inventario_id,
                InventarioItem.nao_previsto == True,  # noqa: E712
            )
            .scalar()
        ) or 0
        expected = sum(counts.values())
        checked = sum(
            count for status, count in counts.items() if status != InventarioItemStatus.PENDING
        )
        return {
            "expected": expected,
            "checked": checked,
            "pending": counts.get(InventarioItemStatus.PENDING, 0),
            "found": counts.get(InventarioItemStatus.FOUND, 0),
            "wrong_location": counts.get(InventarioItemStatus.FOUND_WRONG_LOCATION, 0),
            "not_found": counts.get(InventarioItemStatus.NOT_FOUND, 0),
            "unidentified": counts.get(InventarioItemStatus.UNIDENTIFIED, 0),
            "unlisted": unlisted,
        }

    # ------------------------------------------------------------------
    # Conferência
    # ------------------------------------------------------------------

    @staticmethod
    def record_check(
        db: Session,
        *,
        item: InventarioItem,
        result: InventarioItemStatus,
        found_location_id: Optional[int] = None,
        observation: Optional[str] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
    ) -> InventarioItem:
        """
        Registra o resultado da conferência física de um item.

        Regras:
        - Inventário encerrado → ValueError (itens travados).
        - Item não previsto não aceita ENCONTRADO/LOCAL_DIFERENTE/NÃO_ENCONTRADO
          (o próprio registro dele já é a ocorrência) — apenas observação.
        - LOCAL_DIFERENTE exige found_location_id diverso do esperado.
        - found_location_name é snapshot textual do local informado.
        - NUNCA altera Asset.location_id / custodian_id / status.
        """
        inv = item.inventario or db.get(Inventario, item.inventario_id)
        if inv is None:
            raise ValueError("Inventário do item não encontrado.")
        if inv.status == InventarioStatus.CLOSED:
            raise ValueError("Este inventário está encerrado; as conferências estão travadas.")
        if result == InventarioItemStatus.PENDING:
            raise ValueError("Resultado inválido para conferência.")

        if item.nao_previsto:
            # Ocorrência de bem não previsto: apenas observação complementar.
            item.observation = observation or item.observation
            item.checked_by_id = user_id
            item.checked_by_name = username
            item.checked_at = datetime.utcnow()
        else:
            if result == InventarioItemStatus.FOUND_WRONG_LOCATION:
                if not found_location_id:
                    raise ValueError("Informe o local onde o bem foi encontrado.")
                if found_location_id == item.expected_location_id:
                    raise ValueError(
                        "O local informado é igual ao cadastrado; "
                        "se o bem está no local correto, registre como 'Encontrado'."
                    )
            elif result in (InventarioItemStatus.FOUND, InventarioItemStatus.UNIDENTIFIED):
                found_location_id = found_location_id or item.expected_location_id
            elif result == InventarioItemStatus.NOT_FOUND:
                found_location_id = None

            found_name = None
            if found_location_id:
                loc = db.get(Location, found_location_id)
                if not loc:
                    raise ValueError("Local informado não existe.")
                found_name = loc.name

            item.status = result
            item.found_location_id = found_location_id
            item.found_location_name = found_name
            item.observation = observation or None
            item.checked_by_id = user_id
            item.checked_by_name = username
            item.checked_at = datetime.utcnow()

        # Primeira conferência efetiva inicia formalmente o inventário
        if inv.started_at is None and (item.nao_previsto or item.status != InventarioItemStatus.PENDING):
            inv.started_at = datetime.utcnow()
            if inv.status == InventarioStatus.PLANNED:
                inv.status = InventarioStatus.IN_PROGRESS

        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def register_unlisted_asset(
        db: Session,
        *,
        inventario: Inventario,
        asset_id: int,
        found_location_id: Optional[int] = None,
        observation: Optional[str] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
    ) -> Tuple[InventarioItem, bool]:
        """
        Registra um bem NÃO PREVISTO encontrado em campo (spec §3 ⚠️).
        O bem deve existir no cadastro (identificado via QR/busca). A ocorrência
        fica no inventário; o cadastro do bem não é alterado.
        Retorna (item, created).
        """
        if inventario.status == InventarioStatus.CLOSED:
            raise ValueError("Este inventário está encerrado; novas ocorrências estão travadas.")

        asset = db.get(Asset, asset_id)
        if not asset:
            raise ValueError("Patrimônio não encontrado no cadastro.")

        existing = InventarioService.get_item_for_conference(db, inventario.id, asset.id)
        if existing:
            return existing, False  # já esperado (ou já registrado): não duplica

        item = InventarioItem(
            inventario_id=inventario.id,
            asset_id=asset.id,
            nao_previsto=True,
            status=InventarioItemStatus.UNIDENTIFIED,
            found_location_id=found_location_id or asset.location_id,
            observation=observation,
            checked_by_id=user_id,
            checked_by_name=username,
            checked_at=datetime.utcnow(),
        )
        db.add(item)

        # Snapshot textual do local onde foi encontrado
        loc_id = found_location_id or asset.location_id
        if loc_id:
            loc = db.get(Location, loc_id)
            item.found_location_name = loc.name if loc else None

        if inventario.started_at is None:
            inventario.started_at = datetime.utcnow()
            if inventario.status == InventarioStatus.PLANNED:
                inventario.status = InventarioStatus.IN_PROGRESS

        db.commit()
        db.refresh(item)
        return item, True

    # ------------------------------------------------------------------
    # Encerramento
    # ------------------------------------------------------------------

    @staticmethod
    def close_inventario(
        db: Session,
        *,
        inventario: Inventario,
        closed_by_name: Optional[str] = None,
        closure_notes: Optional[str] = None,
    ) -> Inventario:
        """
        Encerra o inventário: trava conferências e consolida resultados.
        Exige que todos os itens esperados estejam conferidos (nenhum PENDENTE).
        """
        if inventario.status == InventarioStatus.CLOSED:
            raise ValueError("Este inventário já está encerrado.")
        pending = (
            db.query(func.count(InventarioItem.id))
            .filter(
                InventarioItem.inventario_id == inventario.id,
                InventarioItem.nao_previsto == False,  # noqa: E712
                InventarioItem.status == InventarioItemStatus.PENDING,
            )
            .scalar()
        ) or 0
        if pending:
            raise ValueError(
                f"Não é possível encerrar: {pending} item(ns) aguardam conferência."
            )
        inventario.status = InventarioStatus.CLOSED
        inventario.closed_at = datetime.utcnow()
        inventario.closed_by_name = closed_by_name
        inventario.closure_notes = closure_notes or None
        db.commit()
        db.refresh(inventario)
        return inventario
