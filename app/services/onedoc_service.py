"""Serviço de integração com o 1Doc (feature 031 — contracts §3).

Orquestra: elegibilidade (FR-006/Q1), idempotência (FR-009), montagem de
conteúdo (onedoc_message), envio via provedor (onedoc_client) e auditoria
(padão ACTION_* — research D11).

Contrato central: ``notify_movement`` NUNCA levanta exceção ao chamador —
qualquer falha é registrada (estado da integração + auditoria + log) e a
movimentação permanece intocada (FR-007), espelhando o contrato da 030.
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config
from app.models.asset import Asset
from app.models.enums import MovementType
from app.models.movement import Movement
from app.models.onedoc_integration import (
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_SENT,
    OneDocIntegration,
)
from app.services.audit_service import (
    ACTION_INTEGRACAO_1DOC_ENVIADA,
    ACTION_INTEGRACAO_1DOC_FALHOU,
    ACTION_INTEGRACAO_1DOC_REPROCESSADA,
    ACTION_INTEGRACAO_1DOC_SOLICITADA,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    write_audit,
)
from app.services.onedoc_client import OneDocHttpClient
from app.services.onedoc_message import build_body_html, build_body_text, build_subject
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)

# Tipos elegíveis (FR-006 / Clarifications Q1 2026-09-23): cautela e
# transferência de local. Devolução, manutenções, baixa, ajustes e aquisição
# NÃO geram comunicação no 1Doc.
NOTIFICABLE_TYPES = {
    MovementType.ALLOCATION,
    MovementType.TRANSFER,
}


def find_process_safe(process_number: str) -> Optional[bool]:
    """Consulta existência do processo (Q2) via provider default.

    - False = processo inexistente (bloqueia a movimentação ANTES de gravar);
    - True  = existe;
    - None  = API não suporta consulta (C-2/C-3) OU indisponibilidade —
      modo tolerante (nunca bloqueia por incapacidade de consultar; FR-007).
    Usa o símbolo do módulo (patchable nos testes — fake provider).
    """
    try:
        return OneDocHttpClient().find_process(process_number)
    except Exception:
        return None


def _sanitize_error_message(message: str) -> str:
    """Remove credenciais 1Doc do texto de erro (Constitution VI/SC-005).

    Remove: (1) ocorrências do segredo/URL reais do ambiente; (2) padrões
    ``token=...``/``Bearer ...`` que possam ecoar segredos vindos do próprio
    texto de erro da API (precedente de defesa em profundidade).
    """
    import re

    for secret in (config.ONEDOC_API_TOKEN, config.ONEDOC_API_URL):
        if secret and secret in message:
            message = message.replace(secret, "***")
    # padrões de segredo embutidos no texto (ex.: "token=ABC...", "Bearer ABC...")
    message = re.sub(r"(?i)(token\s*[=:]\s*)\S+", r"\1***", message)
    message = re.sub(r"(?i)(bearer\s+)\S+", r"\1***", message)
    return message


def _asset_info(db: Session, movement: Movement) -> Tuple[str, str]:
    """Tag e nome do bem (fonte: Asset — data-model, somente leitura)."""
    asset = db.query(Asset).filter(Asset.id == movement.asset_id).first()
    tag = (getattr(asset, "tag", None) or "-").strip() or "-"
    name = (getattr(asset, "name", None) or "-").strip() or "-"
    return tag, name


def _audit(
    db: Session,
    *,
    action: str,
    result: str,
    movement: Movement,
    process_number: Optional[str],
    description: str,
    ip_address: Optional[str],
    user=None,
    message_id: Optional[str] = None,
) -> None:
    """Evento de auditoria de integração (contracts §3 — sem segredos)."""
    try:
        tag, _ = _asset_info(db, movement)
        new_data = {"processo": process_number}
        if message_id:
            new_data["message_id"] = message_id
        write_audit(
            db,
            user=user,  # None = ator é o serviço (precedente 020/030)
            action=action,
            module="integracao_1doc",
            resource="movement",
            resource_id=movement.id,
            resource_ref=tag,
            ip_address=ip_address,
            result=result,
            description=description,
            new_data=new_data,
        )
    except Exception:
        logger.exception(
            "Falha ao auditar evento de integração 1Doc (movimentação %s) — operação preservada.",
            movement.id,
        )


def _send(db: Session, integration: OneDocIntegration, movement: Movement, provider) -> None:
    """Executa o envio e atualiza estado/auditoria (comum a enviar e reprocessar)."""
    integration.status = STATUS_PENDING
    integration.attempt_count = (integration.attempt_count or 0) + 1
    integration.last_attempt_at = now_utc()
    db.commit()

    try:
        tag, asset_name = _asset_info(db, movement)
        subject = build_subject(tag)
        body_text = build_body_text(
            asset_name=asset_name,
            asset_tag=tag,
            origin_name=movement.origin_location_name,
            destination_name=movement.destination_location_name,
        )
        body_html = build_body_html(
            asset_name=asset_name,
            asset_tag=tag,
            origin_name=movement.origin_location_name,
            destination_name=movement.destination_location_name,
        )

        message_id = provider.send_communication(
            integration.process_number,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

        integration.status = STATUS_SENT
        # Q3: sucesso sem id da mensagem continua SENT — None = desconhecido.
        integration.message_id = (message_id or None)
        integration.sent_at = now_utc()
        integration.last_error = None
        db.commit()

        _audit(
            db,
            action=ACTION_INTEGRACAO_1DOC_ENVIADA,
            result=RESULT_SUCCESS,
            movement=movement,
            process_number=integration.process_number,
            description="Comunicação da movimentação incluída no processo 1Doc.",
            ip_address=None,
            message_id=integration.message_id,
        )
    except Exception as exc:
        # Falha externa: movimentação permanece concluída (FR-007); registra
        # FAILED com erro sanitizado + auditoria, sem segredos (US2).
        sanitized = _sanitize_error_message(str(exc))[:2000]
        logger.warning(
            "Falha ao integrar movimentação %s com o 1Doc: %s",
            movement.id,
            type(exc).__name__,
        )
        try:
            integration.status = STATUS_FAILED
            integration.last_error = sanitized
            integration.last_error_at = now_utc()
            db.commit()
        except Exception:
            logger.exception(
                "Falha ao registrar estado FAILED da integração (movimentação %s).",
                movement.id,
            )
        _audit(
            db,
            action=ACTION_INTEGRACAO_1DOC_FALHOU,
            result=RESULT_FAILURE,
            movement=movement,
            process_number=integration.process_number,
            description=f"Falha na integração com o 1Doc: {sanitized}",
            ip_address=None,
        )


def notify_movement(
    db: Session,
    movement: Movement,
    process_number: Optional[str] = None,
    *,
    operator: Optional[str] = None,
    ip_address: Optional[str] = None,
    provider=None,
) -> None:
    """Dispara a integração da movimentação (best-effort — NUNCA levanta).

    Sequência (contracts §3): guardas → idempotência → registro PENDING →
    auditoria SOLICITADA → envio → estado final + auditoria.
    """
    try:
        if movement is None or movement.id is None:
            return

        # 1. Guarda: integração ativa (FR-002/desativada por padrão)
        if not config.ONEDOC_ENABLED:
            return

        # 2. Elegibilidade (FR-006/Q1) — dupla checagem em profundidade
        if movement.movement_type not in NOTIFICABLE_TYPES:
            return

        # 3. Processo informado (sem processo não há comunicação; a exigência
        #    de preenchimento é tratada na validação FR-002 do create_movement)
        process_number = (process_number or "").strip() or None
        if not process_number:
            return

        # 4. Idempotência (FR-009) — no máximo 1 integração por movimentação;
        #    SENT e PENDING existentes NÃO reenviam (FAILED é reprocessável
        #    manualmente — US3).
        existing = (
            db.query(OneDocIntegration)
            .filter(OneDocIntegration.movement_id == movement.id)
            .first()
        )
        if existing is not None:
            return

        integration = OneDocIntegration(
            movement_id=movement.id,
            process_number=process_number,
            status=STATUS_PENDING,
            attempt_count=0,
        )
        db.add(integration)
        try:
            db.commit()
        except IntegrityError:
            # Corrida teórica: outra conexão registrou entre a checagem e o
            # insert (UNIQUE movement_id) — tratar como "já registrado" (T019).
            db.rollback()
            return
        db.refresh(integration)

        _audit(
            db,
            action=ACTION_INTEGRACAO_1DOC_SOLICITADA,
            result=RESULT_SUCCESS,
            movement=movement,
            process_number=process_number,
            description="Integração da movimentação solicitada ao processo 1Doc.",
            ip_address=ip_address,
        )

        prov = provider if provider is not None else OneDocHttpClient()
        _send(db, integration, movement, prov)
    except Exception:
        # Última linha de defesa: NADA escapa ao chamador (FR-007/US2)
        logger.exception(
            "Erro inesperado no serviço de integração 1Doc (movimentação %s) — movimentação preservada.",
            getattr(movement, "id", None),
        )


def reprocess(
    db: Session,
    integration_id: int,
    *,
    user,
    ip_address: Optional[str] = None,
    provider=None,
) -> Tuple[bool, str]:
    """Reprocessa uma integração FAILED (US3/FR-011 — decisão Q4).

    - Exige registro existente; integração SENT NÃO reenvia (Q3/idempotência);
    - Mantém o MESMO registro (UNIQUE) e incrementa attempt_count;
    - Audita _REPROCESSADA com o usuário REAL (não None);
    - Nunca altera a movimentação original.
    """
    integration = (
        db.query(OneDocIntegration).filter(OneDocIntegration.id == integration_id).first()
    )
    if integration is None:
        return False, "Integração não encontrada."

    movement = (
        db.query(Movement).filter(Movement.id == integration.movement_id).first()
    )
    if movement is None:
        return False, "Movimentação da integração não encontrada."

    if integration.status == STATUS_SENT:
        # Idempotência: já enviada — nada a fazer (US3.2/D8)
        return False, "Integração já enviada anteriormente — nada a reprocessar."

    _audit(
        db,
        action=ACTION_INTEGRACAO_1DOC_REPROCESSADA,
        result=RESULT_SUCCESS,
        movement=movement,
        process_number=integration.process_number,
        description="Reprocessamento manual da integração 1Doc acionado.",
        ip_address=ip_address,
        user=user,
    )

    prov = provider if provider is not None else OneDocHttpClient()
    _send(db, integration, movement, prov)

    db.refresh(integration)
    if integration.status == STATUS_SENT:
        return True, "Integração reprocessada com sucesso."
    return False, integration.last_error or "Falha no reprocessamento."
