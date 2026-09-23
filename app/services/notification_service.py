"""Serviço de notificação por e-mail de movimentações (feature 030).

Orquestra: elegibilidade (RN-002), idempotência (RN-007), configuração
(email_config_service), montagem de assunto (RN-005) e corpo (FR-008),
envio via provedor (email_provider) e auditoria (padrão ACTION_*).

Contrato central (contracts §2): ``notify_movement`` NUNCA levanta exceção
ao chamador — qualquer falha é registrada (estado da Notification + auditoria
+ log) e a movimentação permanece intocada (RN-001).
"""

import json
import logging
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.enums import MovementType
from app.models.movement import Movement
from app.models.notification import Notification
from app.services.audit_service import (
    ACTION_NOTIFICACAO_ENVIADA,
    ACTION_NOTIFICACAO_FALHOU,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    write_audit,
)
from app.services.email_config_service import get_effective_config
from app.services.email_provider import SMTPEmailProvider
from app.utils.time_utils import format_local, now_utc

logger = logging.getLogger(__name__)

# Tipos notificados (RN-002 / Clarifications Q1 2026-09-23): apenas os 3
# tipos principais concluídos por fluxos manuais (web/API).
NOTIFICABLE_TYPES = {
    MovementType.ALLOCATION,
    MovementType.TRANSFER,
    MovementType.RETURN_STOCK,
}

STATUS_PENDING = "PENDING"
STATUS_SENT = "SENT"
STATUS_FAILED = "FAILED"


def _sanitize_error_message(message: str) -> str:
    """Remove credenciais SMTP do texto de erro (Constitution VI/SC-005)."""
    from app import config

    for secret in (config.SMTP_PASSWORD, config.SMTP_USERNAME, config.SMTP_FROM):
        if secret and secret in message:
            message = message.replace(secret, "***")
    return message


def _asset_info(db: Session, movement: Movement) -> Tuple[str, str]:
    """Tag e identificação do bem da movimentação (fonte: Asset — F1/F6)."""
    asset = db.query(Asset).filter(Asset.id == movement.asset_id).first()
    tag = (getattr(asset, "tag", None) or "-").strip() or "-"
    name = (getattr(asset, "name", None) or "-").strip() or "-"
    return tag, name


def build_subject(tag: str) -> str:
    """Assunto institucional único (RN-005) — nenhum outro ponto monta assunto."""
    return f"[SisPatrimônio Pro] Nova movimentação patrimonial - {tag}"


def build_body(db: Session, movement: Movement) -> str:
    """Corpo institucional (FR-008/RN-009/RN-010) — text/plain, sem link (RN-008).

    Operador exibido = usuário autenticado que concluiu a operação, exatamente
    o ``operator_name`` já gravado na movimentação (RN-010 — web ou API).
    """
    tag, asset_name = _asset_info(db, movement)
    lines = [
        "Notificação de Movimentação Patrimonial",
        "",
        f"Bem: {asset_name}",
        f"Tombamento: {tag}",
        f"Tipo de movimentação: {movement.movement_type.label}",
        f"Local de origem: {movement.origin_location_name or '-'}",
        f"Local de destino: {movement.destination_location_name or '-'}",
        f"Responsável anterior: {movement.origin_custodian_name or '-'}",
        f"Responsável atual: {movement.destination_custodian_name or '-'}",
        f"Data e hora: {format_local(movement.timestamp)} (America/Recife)",
        f"Realizada por: {movement.operator_name or '-'}",
    ]
    if movement.reason:
        lines.append(f"Motivo: {movement.reason}")
    if movement.term_code:
        lines.append(f"Termo de responsabilidade: {movement.term_code}")
    lines += [
        "",
        "Este é um aviso automático do SisPatrimônio Pro para ciência do setor de Patrimônio.",
        "Mensagem gerada automaticamente — não responda.",
    ]
    return "\n".join(lines)


def _audit(
    db: Session,
    *,
    action: str,
    result: str,
    movement: Movement,
    recipients: List[str],
    description: str,
    ip_address: Optional[str],
) -> None:
    """Evento de auditoria de notificação (contracts §2 — user=None, sem segredos)."""
    try:
        tag, _ = _asset_info(db, movement)
        write_audit(
            db,
            user=None,  # ator = o serviço (precedente dos eventos automáticos de backup — 020)
            action=action,
            module="notificacoes",
            resource="movement",
            resource_id=movement.id,
            resource_ref=tag,
            ip_address=ip_address,
            result=result,
            description=description,
            new_data={"destinatarios": recipients},
        )
    except Exception:
        logger.exception(
            "Falha ao auditar evento de notificação (movimentação %s) — operação preservada.",
            movement.id,
        )


def notify_movement(
    db: Session,
    movement: Movement,
    *,
    operator: Optional[str] = None,
    ip_address: Optional[str] = None,
    provider=None,
) -> None:
    """Dispara a notificação da movimentação (best-effort — nunca levanta).

    Sequência (contracts §2): elegibilidade → config → idempotência →
    registro PENDING → envio → estado final + auditoria. Qualquer exceção é
    capturada aqui; nada escapa ao chamador (FR-003).
    """
    try:
        if movement is None or movement.id is None:
            return

        # 1. Elegibilidade (RN-002) — dupla checagem (defesa em profundidade;
        #    o hook já filtra, mas o service também é seguro isoladamente)
        if movement.movement_type not in NOTIFICABLE_TYPES:
            return

        # 2. Configuração (leitura pura — nunca cria o singleton)
        effective = get_effective_config(db, create=False)
        if not effective.enabled:
            return  # default desativado — comportamento idêntico ao anterior
        if not effective.recipients:
            # Ativada sem destinatário válido: nenhum envio, nenhum erro
            # visível; registra evento de falha de configuração (spec Seção 11)
            _audit(
                db,
                action=ACTION_NOTIFICACAO_FALHOU,
                result=RESULT_FAILURE,
                movement=movement,
                recipients=[],
                description="Notificação não enviada: configuração ativada sem destinatários válidos.",
                ip_address=ip_address,
            )
            return

        # 3. Idempotência (RN-007) — no máximo 1 notificação por movimentação
        existing = db.query(Notification).filter(Notification.movement_id == movement.id).first()
        if existing is not None:
            return

        recipients: List[str] = list(effective.recipients)
        notif = Notification(
            movement_id=movement.id,
            status=STATUS_PENDING,
            recipients=json.dumps(recipients, ensure_ascii=False),
            attempt_count=0,
        )
        db.add(notif)
        try:
            db.commit()
        except IntegrityError:
            # Corrida teórica: outra conexão registrou a notificação entre a
            # checagem e o insert (UNIQUE movement_id) — tratar como "já
            # notificado" e sair sem reenviar (RN-007; T019)
            db.rollback()
            return
        db.refresh(notif)

        # 4. Montagem + envio (timeout curto no provider — FR-016)
        try:
            tag, _ = _asset_info(db, movement)
            subject = build_subject(tag)
            body = build_body(db, movement)

            notif.subject = subject[:255]
            notif.attempt_count = 1
            notif.last_attempt_at = now_utc()

            prov = provider if provider is not None else SMTPEmailProvider()
            prov.send(subject=subject, body=body, recipients=recipients)

            notif.status = STATUS_SENT
            notif.sent_at = now_utc()
            db.commit()

            _audit(
                db,
                action=ACTION_NOTIFICACAO_ENVIADA,
                result=RESULT_SUCCESS,
                movement=movement,
                recipients=recipients,
                description="Notificação de movimentação enviada por e-mail.",
                ip_address=ip_address,
            )
        except Exception as exc:
            # Falha de envio/montagem: movimentação permanece concluída (RN-001);
            # registra estado FAILED + auditoria de falha, sem segredos
            sanitized = _sanitize_error_message(str(exc))
            logger.warning(
                "Falha ao notificar movimentação %s: %s", movement.id, type(exc).__name__
            )
            try:
                notif.status = STATUS_FAILED
                notif.error_message = sanitized[:2000]
                db.commit()
            except Exception:
                logger.exception(
                    "Falha ao registrar estado FAILED da notificação (movimentação %s).",
                    movement.id,
                )
            _audit(
                db,
                action=ACTION_NOTIFICACAO_FALHOU,
                result=RESULT_FAILURE,
                movement=movement,
                recipients=recipients,
                description=f"Falha no envio da notificação: {sanitized}",
                ip_address=ip_address,
            )
    except Exception:
        # Última linha de defesa: NADA escapa ao chamador (FR-003/Seção 11)
        logger.exception(
            "Erro inesperado no serviço de notificação (movimentação %s) — operação preservada.",
            getattr(movement, "id", None),
        )
