"""HTTPS nativo (uvicorn SSL) — Feature 056 (achado da prova de campo da 053).

Prova do problema: em origin de IP puro (`http://10.39.0.16:8000`),
`navigator.serviceWorker` é undefined (não secure context) — o PWA/coleta
offline (033) não funciona na rede via IP sem HTTPS.

Correção: SSL nativo no uvicorn via env vars `APP_SSL_CERTFILE`/
`APP_SSL_KEYFILE` (opt-in — sem elas, comportamento HTTP atual intocado) e
gerador de CA+certificado local com SAN do IP da LAN.

Testes estruturais (padrão 053/054): leitura de config/código, sem banco.
"""
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_defaults_sem_env_sao_none(monkeypatch):
    """FR-001/FR-006: sem envs, os defaults são None — HTTP puro (comportamento
    atual preservado; suíte intocada)."""
    import importlib

    import app.config as config

    monkeypatch.delenv("APP_SSL_CERTFILE", raising=False)
    monkeypatch.delenv("APP_SSL_KEYFILE", raising=False)
    importlib.reload(config)
    try:
        assert config.APP_SSL_CERTFILE is None
        assert config.APP_SSL_KEYFILE is None
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_run_py_passa_ssl_condicional():
    """FR-002: run.py lê as envs de config e passa ssl_certfile/ssl_keyfile ao
    uvicorn APENAS quando ambos definidos; prints com esquema dinâmico."""
    run_py = (RAIZ / "run.py").read_text(encoding="utf-8", errors="ignore")
    assert "APP_SSL_CERTFILE" in run_py
    assert "APP_SSL_KEYFILE" in run_py
    assert "ssl_certfile" in run_py and "ssl_keyfile" in run_py
    assert '"https" if' in run_py or "'https' if" in run_py


def test_gera_cert_dev_existe_com_san():
    """FR-003: script gerador presente, com SAN do IP + localhost + domínio
    local, idempotente (--force)."""
    script = RAIZ / "scripts" / "gera_cert_dev.py"
    assert script.is_file()
    conteudo = script.read_text(encoding="utf-8", errors="ignore")
    for token in ("subjectAltName", "IP:", "DNS:localhost", "DNS:sispatrimoniopro.local", "--force"):
        assert token in conteudo, f"gera_cert_dev.py sem '{token}'"


def test_gitignore_cobre_data_ssl():
    """FR-004/SC-005: chave privada nunca versionada — .gitignore cobre data/ssl/."""
    gitignore = (RAIZ / ".gitignore").read_text(encoding="utf-8", errors="ignore")
    assert "data/ssl/" in gitignore or "data\\ssl" in gitignore
