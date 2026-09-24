"""Modelo do histórico unificado de execuções de integração (feature 032).

Tabela `integration_executions` — histórico APPEND-ONLY da Central de
Integrações (plan D2, decisão P-1): registra OCORRÊNCIAS (envios, testes,
verificações internas), sem substituir a fonte de verdade do ESTADO das
integrações, que permanece em `notifications`, `onedoc_integrations`,
`ad_settings` e `email_config` (data-model.md).

- Nenhuma rota/edit cria, altera ou exclui registros (somente o service
  `integration_center_service.record_execution` grava — best-effort);
- `detail` contém erro/informação SANITIZADA (Constitution VI) — máx. 2000
  chars (padrão OneDocIntegration.last_error);
- `movement_id` é referência FRACA (sem FK/UNIQUE): o vínculo 1:1 entre
  movimentação e integração permanece garantido nas tabelas de integração
  (uq_notifications_movement_id / uq_onedoc_integrations_movement_id);
- Credenciais NUNCA são gravadas aqui (SC-003).
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base
from app.utils.time_utils import now_utc

# Chaves do catálogo de integrações (plan D1 — integration_center_service)
KEY_EMAIL = "email"
KEY_ONEDOC = "onedoc"
KEY_AD = "ad"
KEY_GLPI = "glpi"

# Tipos de operação (data-model.md)
OP_SEND_EMAIL = "SEND_EMAIL"
OP_SEND_COMMUNICATION = "SEND_COMMUNICATION"
OP_CONNECTION_TEST = "CONNECTION_TEST"
OP_INTERNAL_CHECK = "INTERNAL_CHECK"

# Resultados (padrão RESULT_* do audit_service)
RESULT_SUCCESS = "SUCCESS"
RESULT_FAILURE = "FAILURE"


class IntegrationExecution(Base):
    __tablename__ = "integration_executions"
    __table_args__ = (
        Index("ix_integration_executions_key_created", "integration_key", "created_at"),
        Index(
            "ix_integration_executions_key_result_created",
            "integration_key",
            "result",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Chave da integração no catálogo (email | onedoc | ad | glpi | futuras)
    integration_key = Column(String(30), nullable=False, index=True)

    # Tipo de operação: SEND_EMAIL | SEND_COMMUNICATION | CONNECTION_TEST | INTERNAL_CHECK
    operation = Column(String(40), nullable=False)

    # SUCCESS | FAILURE
    result = Column(String(20), nullable=False, index=True)

    # Duração da execução/teste em milissegundos (NULL = não medido)
    duration_ms = Column(Integer, nullable=True)

    # Ator humano (teste/reprocesso); NULL = ator é o serviço (precedente 030/031)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Snapshot do username (sobrevive à exclusão do usuário — padrão AuditLog)
    username = Column(String(100), nullable=True)

    # Referência fraca à movimentação quando aplicável (sem FK/UNIQUE — ver docstring)
    movement_id = Column(Integer, nullable=True, index=True)

    # Erro/informação SANITIZADA (sem credenciais — Constitution VI), máx. 2000 chars
    detail = Column(Text, nullable=True)

    created_at = Column(DateTime, default=now_utc, nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover — diagnóstico
        return (
            f"<IntegrationExecution(id={self.id}, key='{self.integration_key}', "
            f"op='{self.operation}', result='{self.result}')>"
        )
