"""Resultado externo FINAL por backup — SisPatrimônio Pro (feature 045).

Um único registro por `filename` (resultado final — retry não duplica,
clarificação C-16/Teste H): a linha é escrita uma única vez, ao fim do
ciclo de cópia, pelo `external_backup_service`. Nenhuma rotina edita ou
apaga registros (histórico imutável) e nenhuma rotina toca o destino
(C-12 — sem retenção externa).

- Tabela NOVA, criada por `Base.metadata.create_all` em `init_db()` —
  aditiva, idempotente, zero ALTER (Constitution VII; data-model 045).
- Vínculo lógico por `filename` com `backup_records.filename` (mesmo
  padrão de desacoplamento da 020; sem FK física). A cópia externa só
  ocorre para SUCCESS local, então o vínculo sempre existe.
- `copied_at` em UTC naive (`now_utc()` — política da feature 004);
  representa o momento do resultado final (última cópia/tentativa
  exibida na tela — §23).
- `error_description` contém APENAS motivo controlado (nunca segredos —
  Princípio VI/C-14).
"""

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base
from app.utils.time_utils import now_utc


class BackupExternalRecord(Base):
    """Resultado externo final de um backup (por filename)."""

    __tablename__ = "backup_external_records"

    id = Column(Integer, primary_key=True, index=True)
    # NOT NULL UNIQUE — mesmo nome do backup local (C-15); casa
    # `_BACKUP_NAME_RE`. Retry nunca duplica (resultado final único).
    filename = Column(String(120), nullable=False, unique=True, index=True)
    # MANUAL | AUTOMATICO | PRE_RESTAURACAO (cópia do tipo original)
    backup_type = Column(String(20), nullable=False)
    # SUCCESS | FAILURE (vocabulário de BackupRecord)
    status = Column(String(10), nullable=False)
    # Momento do resultado final — UTC naive (feature 004)
    copied_at = Column(DateTime, default=now_utc, nullable=False, index=True)
    # Preenchidos apenas em SUCCESS (tamanho/hash validados no destino)
    size_bytes = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=True)
    # Motivo controlado (FAILURE) — nunca segredos (Princípio VI)
    error_description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=now_utc)

    def __repr__(self):
        return (
            f"<BackupExternalRecord(id={self.id}, filename={self.filename!r}, "
            f"status={self.status!r}, copied_at={self.copied_at!r})>"
        )
