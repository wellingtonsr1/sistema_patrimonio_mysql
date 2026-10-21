"""Cabeçalhos Cache-Control — propagação de deploy do PWA (033) e dos assets.

Sem Cache-Control explícito, o navegador usa a heurística de frescor e pode
guardar `/sw.js` e CSS por dias. O sintoma em produção: Ctrl+F5 conserte o
tema (ignora cache), mas a navegação normal volta ao problema (SW antigo
continua ativo e serve shell/CSS antigos cache-first). O middleware
`cache_control_middleware` (app/main.py) garante `no-cache` em `/sw.js`,
`/static/*` e HTML dinâmico.
"""
from pathlib import Path

MAIN_PY = Path(__file__).resolve().parent.parent / "app" / "main.py"


def test_middleware_cache_control_existe_no_main():
    """Guard estrutural: o middleware continua declarado e cobre os 3 alvos."""
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "cache_control_middleware" in src
    assert 'path == "/sw.js"' in src
    assert 'path.startswith("/static/")' in src
    assert '"text/html" in content_type' in src


def test_sw_js_responde_no_cache(client):
    """/sw.js DEVE revalidar a cada visita — é o que permite o navegador
    detectar um CACHE_VERSION novo na primeira navegação pós-deploy."""
    resp = client.get("/sw.js")
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("cache-control") == "no-cache"


def test_static_css_responde_no_cache(client):
    """CSS estático revalida (304 barato) — o buste `?v=` dos templates só
    funciona se a resposta antiga não ficar 'fresca' sem revalidação."""
    resp = client.get("/static/css/style.css")
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("cache-control") == "no-cache"


def test_html_dinamico_responde_no_cache(client):
    """Páginas HTML dinâmicas também revalidam — nunca heurística."""
    resp = client.get("/")
    assert resp.status_code == 200, resp.text
    assert "text/html" in resp.headers.get("content-type", "")
    assert resp.headers.get("cache-control") == "no-cache"
