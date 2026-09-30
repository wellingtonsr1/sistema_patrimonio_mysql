"""
Configuração centralizada de logs técnicos do SisPatrimônio Pro.

Separação preservada:
- Auditoria → ações dos usuários e eventos de negócio (tabela audit_log).
- Logs técnicos → erros, exceções, falhas de infraestrutura e diagnóstico
  (este módulo). Nunca se misturam.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import DATA_DIR

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_APP_LOG = str(LOG_DIR / "app.log")
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB
_BACKUP_COUNT = 5


class _SingleLevelFilter(logging.Filter):
    """Permite somente registros abaixo de um determinado nível."""

    def __init__(self, max_level: int) -> None:
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - infrastructure
        return record.levelno <= self.max_level


class _AsyncioNoiseFilter(logging.Filter):
    """Suprime ruído de desconexão benigna do logger `asyncio` (feature 058, M-N3).

    No Windows (Proactor), cada cliente que derruba a conexão abruptamente
    (celular dormindo, keep-alive cortado) gera um callback
    `_call_connection_lost` que loga um traceback de ~15 linhas com
    ConnectionResetError [WinError 10054] — poluindo o app.error.log e
    podendo esconder erros reais.

    Escopo (FR-003): APENAS registros emitidos pelo logger `asyncio` cuja
    exceção seja ConnectionResetError/ConnectionAbortedError/BrokenPipeError
    (desconexão iniciada pelo cliente). Erros de aplicação e outros erros do
    event loop passam íntegros (FR-004).
    """

    _BENIGNAS = (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "asyncio":
            return True
        exc = record.exc_info[1] if record.exc_info else None
        return not isinstance(exc, self._BENIGNAS)


def _build_formatter() -> logging.Formatter:
    """Formato consistente: data/hora | nível | logger | mensagem."""
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-5s | %(name)-35s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def configure_logging() -> None:
    """Configura handlers de logs técnicos de forma centralizada e idempotente."""
    root_logger = logging.getLogger()
    app_log_handler_exists = any(
        getattr(h, "baseFilename", "") == _APP_LOG for h in root_logger.handlers
    )

    if not app_log_handler_exists:
        file_handler = RotatingFileHandler(
            filename=_APP_LOG,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(_build_formatter())
        file_handler.addFilter(_SingleLevelFilter(logging.INFO))
        root_logger.addHandler(file_handler)

        file_err_handler = RotatingFileHandler(
            filename=str(LOG_DIR / "app.error.log"),
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_err_handler.setLevel(logging.WARNING)
        file_err_handler.setFormatter(_build_formatter())
        root_logger.addHandler(file_err_handler)

    console_handler_exists = any(
        isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout
        for h in root_logger.handlers
    )

    if not console_handler_exists:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(_build_formatter())
        root_logger.addHandler(console_handler)

    root_logger.setLevel(logging.INFO)

    if not getattr(root_logger, "_sispatrimonio_logging_configured", False):
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logger_asyncio = logging.getLogger("asyncio")
        if not any(
            isinstance(f, _AsyncioNoiseFilter) for f in logger_asyncio.filters
        ):
            logger_asyncio.addFilter(_AsyncioNoiseFilter())
        root_logger._sispatrimonio_logging_configured = True  # type: ignore[attr-defined]
