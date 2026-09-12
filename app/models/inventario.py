"""
Módulo de Inventário Patrimonial Completo e Comprobatório.

Entidades isoladas que REFERENCIAM o patrimônio existente (assets, locations)
sem jamais alterá-los: uma divergência apontada pelo inventário é apenas
registrada para tratamento posterior pelos fluxos próprios (movimentação,
edição de cadastro), nunca aplicada automaticamente.

Cada `InventarioItem` é simultaneamente a expectativa (snapshot da
localização cadastrada no momento da geração da lista) e a ata de
conferência (resultado, conferente, data/hora, observação).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import InventarioStatus, InventarioItemStatus


class Inventario(Base):
    """
    Inventário patrimonial: uma conferência física formal do acervo.

    - Escopo: filtros (opcional location_id/department) aplicados no momento
      da criação; o snapshot dos bens esperados vive em `itens`.
    - Snapshot textual de filtros (`scope_filters`) preserva a prova de como
      a lista foi gerada, mesmo que os filtros mudem depois.
    - Encerramento trava os itens (nenhuma conferência nova é aceita).
    """
    __tablename__ = "inventarios"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)  # ex: INV-2026-0001
    name = Column(String(150), nullable=False)                          # ex: "Inventário Anual 2026 - Sede"
    status = Column(Enum(InventarioStatus), nullable=False, default=InventarioStatus.PLANNED, index=True)

    # Escopo (filtros opcionais; vazios = todo o acervo)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    department = Column(String(100), nullable=True)
    scope_filters = Column(String(255), nullable=True)  # snapshot textual p/ comprovação

    # Metadados / comprovação
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_name = Column(String(100), nullable=True)   # snapshot do username
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)           # primeiro registro de conferência
    closed_at = Column(DateTime, nullable=True)            # encerramento
    closed_by_name = Column(String(100), nullable=True)    # snapshot do username que encerrou
    closure_notes = Column(Text, nullable=True)

    # Relacionamentos
    location = relationship("Location")
    created_by = relationship("User")
    itens = relationship(
        "InventarioItem",
        back_populates="inventario",
        cascade="all, delete-orphan",
        order_by="InventarioItem.id",
    )

    def __repr__(self):
        return f"<Inventario(id={self.id}, code='{self.code}', status='{self.status}')>"


class InventarioItem(Base):
    """
    Bem esperado em um inventário + ata da sua conferência.

    - `expected_*`: snapshot do cadastro no momento da geração da lista
      (prova do que era esperado, imune a edições posteriores do cadastro).
    - `found_*`: preenchidos na conferência. O cadastro do bem NUNCA é
      alterado por causa do resultado da conferência.
    - Bem não previsto: item com `asset_id` apontando para um bem real que
      NÃO estava na lista esperada (encontrado em campo via QR/busca),
      `nao_previsto=True`.
    """
    __tablename__ = "inventario_itens"
    __table_args__ = (
        UniqueConstraint("inventario_id", "asset_id", name="uq_inventario_item_asset"),
    )

    id = Column(Integer, primary_key=True, index=True)
    inventario_id = Column(Integer, ForeignKey("inventarios.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)

    # Snapshot da expectativa (geração da lista)
    expected_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    expected_location_name = Column(String(150), nullable=True)
    expected_custodian_name = Column(String(150), nullable=True)

    # Resultado da conferência
    status = Column(Enum(InventarioItemStatus), nullable=False, default=InventarioItemStatus.PENDING, index=True)
    nao_previsto = Column(Boolean, default=False, nullable=False)
    found_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    found_location_name = Column(String(150), nullable=True)
    observation = Column(Text, nullable=True)

    # Comprovação: quem conferiu e quando
    checked_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    checked_by_name = Column(String(100), nullable=True)
    checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    inventario = relationship("Inventario", back_populates="itens")
    asset = relationship("Asset")
    expected_location = relationship("Location", foreign_keys=[expected_location_id])
    found_location = relationship("Location", foreign_keys=[found_location_id])
    checked_by = relationship("User", foreign_keys=[checked_by_id])

    def __repr__(self):
        return f"<InventarioItem(id={self.id}, inventario_id={self.inventario_id}, asset_id={self.asset_id}, status='{self.status}')>"
