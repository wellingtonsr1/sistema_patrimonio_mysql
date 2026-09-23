"""Modelo da Integração 1Doc (feature 031 — data-model.md).

Registro UM-PARA-UM entre movimentação e integração com o 1Doc:
``movement_id`` é UNIQUE (``uq_onedoc_integrations_movement_id``) — garantia
estrutural de idempotência (SC-003): no máximo 1 comunicação por movimentação,
espelhando o precedente da feature 030 (``uq_notifications_movement_id``).

O modelo patrimonial (``Movement``) permanece puro: o número do processo 1Doc
vive APENAS aqui (plan D1/D2). ``content_url`` é reservado para o link futuro
de consulta (FR-017) e permanece NULL nesta versão.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import now_utc

STATUS_PENDING = "PENDING"
STATUS_SENT = "SENT"
STATUS_FAILED = "FAILED"


class OneDocIntegration(Base):
    __tablename__ = "onedoc_integrations"
    __table_args__ = (
        UniqueConstraint("movement_id", name="uq_onedoc_integrations_movement_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    movement_id = Column(
        Integer,
        ForeignKey("movements.id"),
        nullable=False,
        index=True,
    )
    movement = relationship("Movement", foreign_keys=[movement_id])

    # Número do processo 1Doc informado pelo operador (normalizado: trim).
    # Validação de formato: somente trim na v1 (analyze U1) — o formato real
    # do processo chega com C-2/C-4 do fornecedor.
    process_number = Column(String(60), nullable=False)

    # PENDING -> SENT | FAILED (data-model.md). SENT é terminal.
    status = Column(String(20), nullable=False, default=STATUS_PENDING, index=True)

    # Identificador da comunicação retornado pela API.
    # NULL/None = desconhecido (decisão Q3 — sucesso sem ID continua SENT).
    message_id = Column(String(100), nullable=True)

    attempt_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)

    # Erro técnico SANITIZADO (sem token/credenciais — Constitution VI), máx. 2000 chars.
    last_error = Column(Text, nullable=True)

    # Reservado para o link futuro de consulta da movimentação (FR-017).
    # NUNCA preenchido nesta versão.
    content_url = Column(String(500), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover — diagnóstico
        return (
            f"<OneDocIntegration(id={self.id}, movement_id={self.movement_id}, "
            f"status='{self.status}', process_number='{self.process_number}')>"
        )
