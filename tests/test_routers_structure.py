"""Feature 051 — Canário de imports circulares dos módulos decompostos (T020).

Importa CADA módulo de `app/web/routers/` isoladamente: qualquer import
circular introduzido pela decomposição do routes.py quebra aqui em segundos
(antes da suíte completa). Complementa SC-005 da spec 051.
"""
import importlib

import pytest

MODULES = [
    "app.web.routers",
    "app.web.routers.templates_env",
    "app.web.routers.shared",
    "app.web.routers.auth",
    "app.web.routers.dashboard",
    "app.web.routers.setup",
    "app.web.routers.assets",
    "app.web.routers.movements",
    "app.web.routers.custodians",
    "app.web.routers.locations",
    "app.web.routers.maintenances",
    "app.web.routers.reports",
    "app.web.routers.inventario",
    "app.web.routes",
    "app.services.backup_service",
]


@pytest.mark.parametrize("module_path", MODULES)
def test_module_imports_cleanly(module_path):
    mod = importlib.import_module(module_path)
    assert mod is not None
