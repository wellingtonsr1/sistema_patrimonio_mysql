from datetime import datetime

from app.utils.time_utils import now_utc
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.database import Base


class BackupConfig(Base):
    """
    Configuração operacional do Backup Automático e da Retenção (feature 021).

    Singleton id=1 (padrão ADSettings): armazena as 8 configurações operacionais
    administráveis pela tela Administração → Backups → Configurações de Backup.

    Campos None = "não definido": a configuração EFETIVA (backup_config_service.
    get_effective_config) resolve por campo  persistido → env (config.py) →
    default da Feature 020. Nenhum campo contém segredo, caminho de arquivo ou
    parâmetro técnico (MYSQLDUMP_PATH/BACKUP_DIR/BACKUP_IMPORT_TIMEOUT/DATABASE_URL
    permanecem configuração de ambiente — spec FR-005).
    """

    __tablename__ = "backup_config"

    id = Column(Integer, primary_key=True)  # singleton: sempre 1

    # --- Agendamento (semântica idêntica à Feature 020) ---
    auto_enabled = Column(Boolean, default=False, nullable=False)  # default desativado (FR-009)
    schedule = Column(String(10), nullable=True)    # daily | weekly
    time = Column(String(5), nullable=True)         # HH:MM em America/Recife
    weekday = Column(Integer, nullable=True)        # 0=domingo … 6=sábado (schedule=weekly)

    # --- Retenção (parâmetros; a política GFS vive no backup_scheduler) ---
    retention_daily_days = Column(Integer, nullable=True)     # ≥ 1
    retention_weekly_weeks = Column(Integer, nullable=True)   # ≥ 1
    retention_monthly_months = Column(Integer, nullable=True) # ≥ 1
    keep_pre_restore = Column(Integer, nullable=True)         # ≥ 0 (0 = preservar todos)

    # --- Metadados de rastreio ---
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    updated_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<BackupConfig(id={self.id}, auto_enabled={self.auto_enabled}, schedule='{self.schedule}')>"
