from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database import Base
from app.utils.time_utils import now_utc


class EmailConfig(Base):
    """
    Configuração da Notificação por E-mail de Movimentações (feature 030).

    Singleton id=1 (padrão BackupConfig/ADSettings): armazena APENAS os
    parâmetros administráveis pela tela Administração → Notificações —
    ativação e destinatários. Nenhum campo contém segredo: as credenciais
    SMTP vivem exclusivamente no ambiente (app/config.py SMTP_* —
    Constitution VI, precedente AD_BIND_PASSWORD).

    Default conservador: notifications_enabled=False — sem configuração
    explícita do administrador, o comportamento do sistema é idêntico ao
    anterior à feature (RN-006/FR-006).
    """

    __tablename__ = "email_config"

    id = Column(Integer, primary_key=True)  # singleton: sempre 1

    notifications_enabled = Column(Boolean, default=False, nullable=False)  # default desativado (FR-006)
    recipients = Column(Text, nullable=True)  # JSON array de e-mails válidos (normalizados pelo service)

    # --- Metadados de rastreio ---
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    updated_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<EmailConfig(id={self.id}, notifications_enabled={self.notifications_enabled})>"


class Notification(Base):
    """
    Registro de notificação por e-mail vinculada a uma movimentação (030).

    Vínculo UM-PARA-UM com a movimentação (UNIQUE em movement_id): garantia
    estrutural da idempotência (RN-007) — uma movimentação nunca gera mais de
    um e-mail, mesmo em reprocesso.

    ``content_url`` fica SEMPRE NULL nesta versão (RN-008): campo reservado
    para o futuro link de consulta à movimentação — a inclusão do link será
    mudança apenas de template + preenchimento deste campo, sem reestruturar
    o serviço.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("movement_id", name="uq_notifications_movement_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    movement_id = Column(
        Integer,
        ForeignKey("movements.id"),
        nullable=False,
        unique=True,  # 1:1 — idempotência estrutural
    )
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING | SENT | FAILED

    # Snapshot do que foi efetivamente usado no envio
    recipients = Column(Text, nullable=True)   # JSON array
    subject = Column(String(255), nullable=True)

    # Controle de tentativas (FR-010; prepara retry futuro — P-1, sem mudança de modelo)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    # Erro técnico sanitizado (sem credenciais — Constitution VI)
    error_message = Column(Text, nullable=True)

    # Reservado para o link futuro (RN-008) — NULL nesta versão
    content_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    def __repr__(self):
        return f"<Notification(id={self.id}, movement_id={self.movement_id}, status='{self.status}')>"
