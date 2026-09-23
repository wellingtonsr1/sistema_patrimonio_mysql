"""Configuração administrável da Notificação por E-mail (feature 030).

Fonte ÚNICA de verdade em runtime para ativação/destinatários, seguindo o
precedente da feature 021 (backup_config_service — singleton + precedência
persistido → env → default). Aqui, contudo:

- ``enabled``:   persistido → **default False** (sem fallback env — a
                 ativação é decisão administrativa da tela; nada em .env
                 liga a notificação — RN-006/FR-006).
- ``recipients``: persistido → **vazio** (sem fallback env — destinatário é
                 a configuração oficial do sistema, RN-004).

Os parâmetros de ENVIO (SMTP_HOST/PORT/USERNAME/PASSWORD/FROM/USE_TLS/
SEND_TIMEOUT) vivem exclusivamente no ambiente (app/config.py SMTP_*) —
nenhum segredo no banco (Constitution VI).

Service ESPECÍFICO de e-mail: não é um serviço genérico de configuração.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config
from app.models.notification import EmailConfig
from app.services.audit_service import (
    ACTION_NOTIFICACAO_CONFIG,
    RESULT_SUCCESS,
    write_change_audit,
)
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)

# Cota conservadora de destinatários (decisão de plano — data-model.md §1)
_MAX_RECIPIENTS = 10

# Validação de formato de e-mail (institucional, suficiente para a tela;
# o envio real depende do SMTP aceitar ou não o endereço)
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


@dataclass(frozen=True)
class EffectiveEmailConfig:
    """Snapshot imutável da configuração efetiva (consumo pelo service)."""

    enabled: bool
    recipients: List[str]
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


def get_email_config(db: Session, create: bool = True) -> EmailConfig:
    """Retorna a linha singleton id=1, criando-a (lazy) se ausente.

    Com ``create=False`` é LEITURA PURA (precedente 022): se a linha não
    existe, retorna um objeto NÃO persistido — nunca add/commit/flush
    (GETs somente-leitura sem efeito colateral de escrita).
    """
    settings = db.query(EmailConfig).filter(EmailConfig.id == 1).first()
    if settings is None:
        if not create:
            return EmailConfig(id=1, notifications_enabled=False)
        settings = EmailConfig(id=1, notifications_enabled=False)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def normalize_recipients(raw: str) -> List[str]:
    """Normaliza a entrada bruta da tela em lista de e-mails.

    Aceita separação por linha ou vírgula; faz trim; deduplica preservando
    ordem. NÃO valida formato (ver ``validate_recipients``).
    """
    if not raw:
        return []
    parts = [p.strip().lower() for p in raw.replace(",", "\n").split("\n")]
    seen = set()
    result: List[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            result.append(p)
    return result


def validate_recipients(recipients: List[str]) -> List[str]:
    """Valida formato dos destinatários; levanta ValueError amigável.

    Regras (data-model.md §1): obrigatório quando ativado; formato válido;
    máx. 10 destinatários.
    """
    for r in recipients:
        if not _EMAIL_RE.match(r):
            raise ValueError(f"E-mail inválido: {r!r}. Corrija a lista de destinatários.")
    if len(recipients) > _MAX_RECIPIENTS:
        raise ValueError(
            f"Máximo de {_MAX_RECIPIENTS} destinatários permitido "
            f"(recebido {len(recipients)})."
        )
    return recipients


def get_effective_config(db: Session, create: bool = False) -> EffectiveEmailConfig:
    """Resolve a configuração efetiva (precedência documentada no módulo).

    Default ``create=False`` (leitura pura) — o fluxo de notificação nunca
    cria a linha singleton como efeito colateral de leitura.
    """
    row = get_email_config(db, create=create)

    recipients: List[str] = []
    if row.recipients:
        try:
            loaded = json.loads(row.recipients)
            if isinstance(loaded, list):
                recipients = [str(r).strip() for r in loaded if str(r).strip()]
        except (ValueError, TypeError):
            logger.warning("email_config.recipients inválido — tratado como vazio.")
            recipients = []

    return EffectiveEmailConfig(
        enabled=bool(row.notifications_enabled),
        recipients=recipients,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )


def save_config(
    db: Session,
    *,
    enabled: bool,
    recipients: List[str],
    user=None,
) -> EffectiveEmailConfig:
    """Valida, persiste e audita a configuração de notificação (contracts §4).

    - Ativado exige >= 1 destinatário válido (ValueError amigável);
    - Normaliza (trim/lowercase), deduplica, valida formato e cota (máx. 10);
    - Grava write_change_audit(ACTION_NOTIFICACAO_CONFIG) com before/after
      (sem segredos — não há segredo nesta configuração);
    - Retorna o snapshot efetivo salvo.
    """
    before = get_effective_config(db, create=False)

    normalized = normalize_recipients(
        "\n".join(recipients) if isinstance(recipients, list) else str(recipients or "")
    )

    if enabled and not normalized:
        raise ValueError(
            "Para ativar as notificações, informe pelo menos um e-mail de destinatário."
        )
    validate_recipients(normalized)

    row = get_email_config(db, create=True)  # POST pode criar o singleton
    before_enabled = row.notifications_enabled
    before_recipients = row.recipients

    row.notifications_enabled = bool(enabled)
    row.recipients = json.dumps(normalized, ensure_ascii=False) if normalized else None
    row.updated_at = now_utc()
    row.updated_by = user.username if user is not None else None

    db.commit()
    db.refresh(row)

    # Auditoria de configuração (before/after — padrão write_change_audit)
    try:
        write_change_audit(
            db,
            user=user,
            action=ACTION_NOTIFICACAO_CONFIG,
            module="notificacoes",
            resource="email_config",
            resource_id=row.id,
            before={
                "notifications_enabled": bool(before_enabled),
                "recipients": json.loads(before_recipients) if before_recipients else [],
            },
            after={
                "notifications_enabled": bool(enabled),
                "recipients": normalized,
            },
        )
    except Exception:
        logger.exception("Falha ao auditar ALTERACAO_CONFIG_NOTIFICACAO (não bloqueia a operação).")

    return EffectiveEmailConfig(
        enabled=bool(enabled),
        recipients=normalized,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )
