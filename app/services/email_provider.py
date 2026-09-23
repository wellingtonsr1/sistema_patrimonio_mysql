"""Provedor de envio de e-mail (feature 030 — research.md D1/D2).

Único ponto do sistema que conhece SMTP (stdlib ``smtplib`` — zero
dependências novas). Isolado atrás do protocolo ``EmailProvider`` para:

- mock/fake trivial na suíte de testes (nunca SMTP real — spec Seção 14);
- futura substituição por outro canal (fila/worker, provedor transacional)
  sem tocar o domínio de movimentações (NFR-004).

Erros SMTP propagam **sanitizados**: a mensagem de exceção NUNCA contém
senha ou credenciais (Constitution VI). Exceções ``smtplib.SMTP*`` nativas
não incluem a senha — mas a sanitização aqui garante o contrato mesmo se
uma subclasse de erro incluir dados do servidor/usuário.
"""

import logging
import smtplib
from email.message import EmailMessage
from typing import List, Protocol

from app import config

logger = logging.getLogger(__name__)


class EmailProvider(Protocol):
    """Contrato mínimo de envio (contracts §3)."""

    def send(self, *, subject: str, body: str, recipients: List[str]) -> None:
        """Envia o e-mail; levanta exceção em falha (quem trata é o caller)."""
        ...


def _sanitize_error(exc: Exception) -> Exception:
    """Re-levanta a exceção com mensagem sem credenciais.

    Remove da mensagem qualquer ocorrência da senha/usuário SMTP (o texto de
    erros de protocolo pode ecoar comandos do diálogo SMTP com AUTH).
    """
    msg = str(exc)
    secrets = [config.SMTP_PASSWORD, config.SMTP_USERNAME, config.SMTP_FROM]
    for s in secrets:
        if s and s in msg:
            msg = msg.replace(s, "***")
    if msg != str(exc):
        exc.args = (msg,)
    return exc


class SMTPEmailProvider:
    """Implementação SMTP via stdlib (contracts §3)."""

    def send(self, *, subject: str, body: str, recipients: List[str]) -> None:
        if not recipients:
            raise ValueError("Nenhum destinatário informado para o envio.")
        if not config.SMTP_HOST:
            raise RuntimeError(
                "SMTP não configurado no ambiente (SMTP_HOST ausente). "
                "A notificação permanece inoperante."
            )

        sender = config.SMTP_FROM or config.SMTP_USERNAME
        if not sender:
            raise RuntimeError(
                "Remetente não configurado (SMTP_FROM ou SMTP_USERNAME ausente)."
            )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message.set_content(body, charset="utf-8")

        try:
            with smtplib.SMTP(
                config.SMTP_HOST, config.SMTP_PORT, timeout=config.SMTP_SEND_TIMEOUT
            ) as smtp:
                if config.SMTP_USE_TLS:
                    smtp.starttls()
                if config.SMTP_USERNAME and config.SMTP_PASSWORD:
                    smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError, ValueError, RuntimeError) as exc:
            logger.warning("Falha de envio SMTP: %s", type(exc).__name__)
            raise _sanitize_error(exc) from exc
