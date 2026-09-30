"""Higiene de template e de logs — Feature 058 (M5 + M-N3 da análise 2026-09-30).

M5: atributo `style` quebrado no botão do menu do usuário (base.html) —
    aspas órfãs fechavam o atributo cedo e `;border-color:...` virava
    atributo inválido (renderiza por tolerância do navegador).
M-N3: ruído `ConnectionResetError [WinError 10054]` (e primos 10053/10038)
    do logger `asyncio` poluindo app.error.log com tracebacks de ~15 linhas
    a cada desconexão abrupta de cliente (celular dormindo, keep-alive
    cortado), podendo esconder erros reais.
"""

from __future__ import annotations

import logging
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "app" / "web" / "templates" / "base.html"


# ---------------------------------------------------------------------------
# M5 — style íntegro no menu do usuário
# ---------------------------------------------------------------------------

def test_m5_base_html_sem_aspas_orfas_no_style_do_menu():
    """O padrão quebrado (`";border-color:` fora do atributo) não existe mais."""
    conteudo = BASE.read_text(encoding="utf-8")
    assert '";border-color:rgba(255,255,255,.15);"' not in conteudo, (
        "base.html ainda contém o atributo style quebrado no menu do usuário"
    )


def test_m5_base_html_style_integro_com_color_e_border_color():
    """color e border-color estão no MESMO atributo style do botão."""
    conteudo = BASE.read_text(encoding="utf-8")
    assert (
        'style="color:var(--color-primary);border-color:rgba(255,255,255,.15);"'
        in conteudo
    ), "botão do menu do usuário deve ter style íntegro (color + border-color)"


# ---------------------------------------------------------------------------
# M-N3 — filtro de ruído de desconexão no logger asyncio
# ---------------------------------------------------------------------------

def _record(
    logger_name: str,
    exc: BaseException | None = None,
) -> logging.LogRecord:
    exc_info = (type(exc), exc, exc.__traceback__) if exc else None
    return logging.LogRecord(
        name=logger_name,
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Exception in callback %s",
        args=(),
        exc_info=exc_info,
    )


def test_m3_filtro_suprime_connection_reset_do_logger_asyncio():
    from app.logging_config import _AsyncioNoiseFilter

    filtro = _AsyncioNoiseFilter()
    rec = _record("asyncio", ConnectionResetError(10054, "conexão cancelada pelo host"))
    assert filtro.filter(rec) is False  # suprimido


def test_m3_filtro_suprime_connection_aborted_e_broken_pipe_no_asyncio():
    from app.logging_config import _AsyncioNoiseFilter

    filtro = _AsyncioNoiseFilter()
    assert filtro.filter(_record("asyncio", ConnectionAbortedError(10053, "abortada"))) is False
    assert filtro.filter(_record("asyncio", BrokenPipeError(32, "pipe quebrado"))) is False


def test_m3_filtro_passa_erro_real_do_asyncio():
    """Erro que NÃO é desconexão benigna segue íntegro (FR-004)."""
    from app.logging_config import _AsyncioNoiseFilter

    filtro = _AsyncioNoiseFilter()
    assert filtro.filter(_record("asyncio", ValueError("bug real no callback"))) is True


def test_m3_filtro_passa_connection_reset_de_logger_de_aplicacao():
    """O escopo é APENAS o logger asyncio (FR-003): o mesmo erro vindo de um
    service de aplicação nunca pode ser suprimido."""
    from app.logging_config import _AsyncioNoiseFilter

    filtro = _AsyncioNoiseFilter()
    rec = _record(
        "app.services.backup_service",
        ConnectionResetError(10054, "conexão cancelada"),
    )
    assert filtro.filter(rec) is True


def test_m3_filtro_passa_registro_sem_excecao():
    from app.logging_config import _AsyncioNoiseFilter

    filtro = _AsyncioNoiseFilter()
    assert filtro.filter(_record("asyncio")) is True


def test_m3_configure_logging_instala_filtro_uma_vez_so():
    """Instalação idempotente: chamar configure_logging() duas vezes não
    duplica o filtro no logger asyncio."""
    from app.logging_config import configure_logging

    configure_logging()
    configure_logging()

    logger_asyncio = logging.getLogger("asyncio")
    filtros = [f for f in logger_asyncio.filters if type(f).__name__ == "_AsyncioNoiseFilter"]
    assert len(filtros) == 1, f"esperado 1 filtro de ruído, encontrados {len(filtros)}"
