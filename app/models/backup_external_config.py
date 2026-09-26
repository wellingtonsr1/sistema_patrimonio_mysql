"""Configuração do destino externo de backups — SisPatrimônio Pro (feature 045).

Singleton id=1 (padrão BackupConfig/ADSettings): define se — e para onde —
cada backup local válido é copiado após a geração (feature 045).

- Tabela NOVA, criada por `Base.metadata.create_all` em `init_db()` —
  aditiva, idempotente, zero ALTER (Constitution VII; data-model 045).
- Nenhum campo contém segredo: o destino é uma pasta de rede/NAS já
  montada no SO (C-4 — a aplicação não manipula credenciais).
- O caminho é validado pelo serviço (`external_backup_service`) antes de
  qualquer uso; aqui há apenas persistência.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base
from app.utils.time_utils import now_utc


class BackupExternalConfig(Base):
    """Configuração do destino externo (singleton id=1)."""

    __tablename__ = "backup_external_config"

    id = Column(Integer, primary_key=True)  # singleton: sempre 1

    # Cópia externa ativa — default DESABILITADO (FR-004/SC-001): o
    # comportamento atual (somente local) é preservado byte-a-byte.
    enabled = Column(Boolean, default=False, nullable=False)

    # Único tipo nesta feature (FR-003); vocabulário controlado para
    # extensão futura (ex.: S3).
    dest_type = Column(String(20), default="PASTA_REDE", nullable=False)

    # Caminho montado no SO (ex.: /mnt/backup-sispatrimonio);
    # None/"" = não configurado.
    dest_path = Column(String(255), nullable=True)

    # Metadados de rastreio (padrão BackupConfig)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    updated_by = Column(String(100), nullable=True)

    def __repr__(self):
        return (
            f"<BackupExternalConfig(id={self.id}, enabled={self.enabled}, "
            f"dest_type={self.dest_type!r})>"
        )
