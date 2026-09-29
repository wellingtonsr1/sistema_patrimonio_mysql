"""Feature 051 — Inventário de rotas como prova de não-regressão (FR-006/T002).

Captura (path, methods, endpoint_name) de todas as rotas HTTP do app FastAPI
e compara contra o manifesto `tests/route_manifest.json` — capturado do código
PRÉ-refatoração. Qualquer diferença de path, método ou nome de endpoint após a
decomposição de app/web/routes.py quebra este teste.

Nota: nesta versão do FastAPI, `include_router` registra um `_IncludedRouter`
lazy — as rotas reais vivem em `original_router.routes`. O walker desce
recursivamente por esses wrappers.
"""
import json
from pathlib import Path

from app.main import app

MANIFEST_PATH = Path(__file__).parent / "route_manifest.json"

METHOD_ORDER = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def _method_key(method: str) -> int:
    try:
        return METHOD_ORDER.index(method)
    except ValueError:
        return len(METHOD_ORDER)


def route_inventory():
    """Inventário ordenado (path, methods, endpoint) de todas as rotas HTTP."""
    items = []

    def walk(routes):
        for route in routes:
            kind = type(route).__name__
            if kind == "_IncludedRouter":
                walk(route.original_router.routes)
                continue
            methods = getattr(route, "methods", None)
            if not methods:
                continue  # Mount e afins não são rotas HTTP
            methods = sorted((m for m in methods if m != "HEAD"), key=_method_key)
            if not methods:
                continue
            items.append(
                {
                    "path": route.path,
                    "methods": methods,
                    "endpoint": getattr(route, "name", "") or "",
                }
            )

    walk(app.router.routes)
    items.sort(key=lambda r: (r["path"], r["methods"], r["endpoint"]))
    return items


def test_route_inventory_matches_manifest():
    assert MANIFEST_PATH.exists(), (
        "manifesto ausente — gere com: "
        "python -c \"import json; from tests.test_route_inventory import route_inventory; "
        "from pathlib import Path; "
        "Path('tests/route_manifest.json').write_text(json.dumps(route_inventory(), indent=2, ensure_ascii=False), encoding='utf-8')\""
    )
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    atual = route_inventory()
    assert atual == manifest, (
        "Inventário de rotas divergiu do manifesto pré-refatoração (FR-006 da 051). "
        "Se a mudança for intencional, regenere o manifesto e registre no validacao.md."
    )
