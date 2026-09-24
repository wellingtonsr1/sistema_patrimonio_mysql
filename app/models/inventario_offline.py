"""
Model da coleta offline de inventário (feature 033 — aditivo).

Registro no SERVIDOR de cada coleta feita em campo sem conexão e recebida na
sincronização. É a âncora da idempotência (UNIQUE inventory_id +
client_operation_id), da rastreabilidade de origem (dispositivo/usuário) e da
preservação de conflitos (nenhuma sobrescrita silenciosa entre canais
online/offline — decisão C-5).

Princípios preservados:
- Princípio V: a gravação no item acontece EXCLUSIVAMENTE via
  `InventarioService.record_check` / `register_unlisted_asset` (FR-026).
- Princípio VII: tabela nova aditiva, criada pelo mecanismo `init_db`
  existente; nenhuma tabela/coluna existente é alterada.
- O coletador NUNCA é fonte de verdade: o servidor revalida tudo (FR-025).
"""

from datetime import datetime

from app.utils.time_utils import now_utc
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import InventarioOfflineColetaStatus


class InventarioOfflineColeta(Base):
    """Coleta offline de inventário recebida pelo servidor (feature 033)."""

    __tablename__ = "inventario_offline_coletas"
    __table_args__ = (
        UniqueConstraint(
            "inventory_id",
            "client_operation_id",
            name="uq_inventario_offline_coleta_operation",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(
        Integer,
        ForeignKey("inventarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Identificador único da operação gerado NO DISPOSITIVO (FR-020)
    client_operation_id = Column(String(64), nullable=False, index=True)

    status = Column(
        Enum(InventarioOfflineColetaStatus),
        nullable=False,
        default=InventarioOfflineColetaStatus.ACCEPTED,
        index=True,
    )

    # Bem conferido (null permitido? NÃO: toda coleta refere um bem do cadastro,
    # previsto (CHECK) ou não previsto (UNLISTED) — ver data-model.md)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    # Item do snapshot (null para operações UNLISTED — bem fora do pacote)
    inventario_item_id = Column(
        Integer, ForeignKey("inventario_itens.id"), nullable=True, index=True
    )

    operation = Column(String(20), nullable=False)  # CHECK | UNLISTED
    # Resultado declarado (snapshot textual — não é FK do enum do item)
    result = Column(String(30), nullable=True)
    found_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    # Responsável encontrado: registrado SOMENTE na coleta (decisão da análise
    # de consistência — nunca aplicado ao item; record_check não grava custódia)
    found_custodian_id = Column(Integer, ForeignKey("custodians.id"), nullable=True)
    observation = Column(Text, nullable=True)

    # Rastreabilidade de origem (FR-028)
    device_id = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(100), nullable=True)  # snapshot do username no sync

    # Datas: coleta preserva o declarado; servidor é a referência oficial (FR-045)
    collected_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    synced_at = Column(DateTime(timezone=True), nullable=True)  # aceitação/gravação

    # Reconciliação de conflitos (D8)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    reconciled_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reconcile_action = Column(String(20), nullable=True)  # KEEP | APPLY

    # Payload original preservado (conflitos/rejeições — C-5/FR-019)
    client_payload = Column(Text, nullable=True)
    reject_reason = Column(String(255), nullable=True)

    # Relacionamentos (leitura mínima; escrita no item só via services oficiais)
    inventario = relationship("Inventario")
    asset = relationship("Asset")
    inventario_item = relationship("InventarioItem")
    found_location = relationship("Location")
    found_custodian = relationship("Custodian")
    user = relationship("User", foreign_keys=[user_id])
    reconciled_by = relationship("User", foreign_keys=[reconciled_by_id])

    def __repr__(self):
        return (
            f"<InventarioOfflineColeta(id={self.id}, inventory_id={self.inventory_id}, "
            f"client_operation_id='{self.client_operation_id}', status='{self.status}')>"
        )
