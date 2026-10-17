"""COR-06 (`specs/072-pentest-auditoria-adversarial`) — SEC-006.

Página amigável de indisponibilidade: exceção NÃO-HTTP → 500 com HTML
amigável na web (mesmo layout de 403/404) e 500 JSON genérico em /api/*,
sem senha/DSN/SQL no corpo (ficha §3; propriedades provadas pelo TC-45).

Nota de harness: em Starlette 1.6 o handler catch-all (`Exception`) vive no
`ServerErrorMiddleware`, que entrega a resposta amigável e relança a exceção
ao servidor (para o uvicorn logar). O `TestClient` com
`raise_server_exceptions=True` (default) levanta a exceção no teste EM VEZ de
devolvê-la — por isso estes testes constroem o cliente com
`raise_server_exceptions=False` (mesma sessão do fixture).

Nenhum teste existente é alterado (FR-039/Constitution VIII).
"""

from fastapi.testclient import TestClient

REMESSA_HOSTIL = (
    "RuntimeError de teste: senha=sintetico "
    "DATABASE_URL=mysql+pymysql://root:secreta@127.0.0.1:3307/sispatrimonio_test"
)


def _levantar(_):
    def _raise(*args, **kwargs):
        raise RuntimeError(REMESSA_HOSTIL)
    return _raise


def _cliente_sem_reraise(client) -> TestClient:
    """Mesmo app, mesma sessão logada, sem relançar exceção no teste."""
    from app.main import app
    c = TestClient(app, raise_server_exceptions=False)
    c.cookies.update(client.cookies)
    return c


def test_excecao_nao_http_na_web_recebe_pagina_amigavel(client, monkeypatch):
    """Exceção de dependência em rota web → HTML amigável com status 500,
    sem a exceção (nem senha/DSN) no corpo."""
    from app.services.asset_service import AssetService

    monkeypatch.setattr(AssetService, "get_all", _levantar(None))
    resp = _cliente_sem_reraise(client).get("/assets", follow_redirects=False)
    assert resp.status_code == 500
    corpo = resp.text
    assert "Indisponível no momento" in corpo
    assert "text/html" in resp.headers.get("content-type", "")
    assert REMESSA_HOSTIL not in corpo
    assert "DATABASE_URL" not in corpo and "root:secreta" not in corpo
    assert "Traceback" not in corpo
    # layout base (mesma família dos templates 403/404)
    assert "Voltar ao Início" in corpo


def test_excecao_nao_http_na_api_recebe_json_generico(client, monkeypatch):
    """Exceção de dependência em /api/* → 500 JSON genérico (detail curto),
    sem DSN/senha/traceback no corpo."""
    from app.services.asset_service import AssetService

    monkeypatch.setattr(AssetService, "get_all", _levantar(None))
    resp = _cliente_sem_reraise(client).get("/api/v1/assets", follow_redirects=False)
    assert resp.status_code == 500
    corpo = resp.text
    assert resp.headers["content-type"].startswith("application/json")
    assert "Erro interno do servidor" in corpo
    assert REMESSA_HOSTIL not in corpo
    assert "DATABASE_URL" not in corpo and "root:" not in corpo
    assert "Traceback" not in corpo
