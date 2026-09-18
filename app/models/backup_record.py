"""Metadados determinísticos de backups — SisPatrimônio Pro (feature 020).

Um registro por tentativa de geração (sucesso ou falha) de qualquer fluxo
(manual, automático, pré-restauração). A identificação do tipo NÃO depende
do nome do arquivo (spec FR-013); o padrão de nome físico permanece o da
015/016 e é validado contra `_BACKUP_NAME_RE` pelo serviço antes de gravar.

- Tabela NOVA, criada por `Base.metadata.create_all` em `init_db()` —
  aditiva, idempotente, zero ALTER (Constitution VII; data-model BV-1).
- `timestamp` em UTC naive (`now_utc()` — política da feature 004).
- Em FAILURE, `filename` é o nome FINAL projetado `{base}.sql.gz` (casa com
  a regex do serviço; NÃO indica arquivo disponível — listagem/elegibilidade
  sempre cruzam registro com arquivo presente no disco; data-model BV-4).
- `removed_at` é preenchido EXCLUSIVAMENTE pelo ciclo de retenção da 020
  (data-model: a remoção física não remove o registro — §20/§33 do briefing).
"""

from sqlalchemy import Column, DateTime, Index, Integer, String

from app.database import Base
from app.utils.time_utils import now_utc


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True, index=True)
    # NOT NULL UNIQUE — 1 registro por arquivo; FAILURE usa o nome final
    # projetado (sem colisão: a geração falhou antes do rename; data-model §1).
    filename = Column(String(120), nullable=False, unique=True, index=True)
    # MANUAL | AUTOMATICO | PRE_RESTAURACAO (vocabulário controlado no serviço)
    backup_type = Column(String(20), nullable=False)
    # SUCCESS | FAILURE
    status = Column(String(10), nullable=False)
    # Início da geração — UTC naive (feature 004)
    timestamp = Column(DateTime, default=now_utc, nullable=False, index=True)
    size_bytes = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=True)
    # Motivo da falha controlado (nunca segredos — Princípio VI)
    error_description = Column(String(255), nullable=True)
    # Preenchidos EXCLUSIVAMENTE pela retenção (020)
    removed_at = Column(DateTime, nullable=True)
    removed_reason = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=now_utc)

    def __repr__(self):
        return (
            f"<BackupRecord(id={self.id}, filename={self.filename!r}, "
            f"backup_type={self.backup_type!r}, status={self.status!r}, "
            f"removed_at={self.removed_at!r})>"
        )


# Índice composto para as consultas de monitoramento/elegibilidade
# (por tipo+status; data-model §1).
Index("ix_backup_records_type_status", BackupRecord.backup_type, BackupRecord.status)
