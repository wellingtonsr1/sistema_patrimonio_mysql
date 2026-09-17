"""
Testes de renderização do componente "Resultado da conferência" (feature 011).

Guarda de não-regressão da correção visual: as 4 opções do campo devem
renderizar com a classe `result-option` (borda com contraste nos dois temas
via token --c-border), com os valores e o cursor de clique intactos.

Cobre as DUAS telas que renderizam o campo (FR-008):
  - página dedicada: GET /inventarios/{inv_id}/conferir/{asset_id}
  - modal: GET /inventarios/{inv_id} (bloco do modal de conferência)

A cor da borda em si não é assertável sem navegador — a validação de
contraste é manual (quickstart §3 da feature).
"""
import pytest

from app.models.enums import AssetCategory, AssetCondition
from app.schemas.asset import AssetCreate
from app.schemas.location import LocationCreate
from app.services.asset_service import AssetService
from app.services.location_service import LocationService

RESULT_VALUES = ["ENCONTRADO", "LOCAL_DIFERENTE", "NAO_ENCONTRADO", "SEM_IDENTIFICACAO"]


def _setup_inventario_com_bem(client, db_session):
    """Cria local + bem + inventário aberto com 1 item pendente (padrão test_inventario)."""
    loc = LocationService.create(db_session, LocationCreate(
        name="Loc Visual 011", branch="Matriz", department="TI"))
    asset = AssetService.create(db_session, AssetCreate(
        tag="VIS-011-0001", name="Notebook Visual",
        category=AssetCategory.NOTEBOOK, purchase_value=1000.0,
        condition=AssetCondition.GOOD, initial_location_id=loc.id))
    resp = client.post("/inventarios/new", data={
        "name": "Inventário Visual 011", "location_id": str(loc.id),
    }, follow_redirects=False)
    assert resp.status_code == 303
    return asset


def _assert_result_options(html: str, context: str):
    """As 4 opções presentes com result-option, valores e cursor intactos."""
    assert html.count("result-option") >= 4, (
        f"{context}: esperadas 4 opções com result-option; "
        f"encontradas {html.count('result-option')}"
    )
    for value in RESULT_VALUES:
        assert f'value="{value}"' in html, f"{context}: valor {value} ausente"
    assert "cursor:pointer" in html, f"{context}: cursor de clique desapareceu"


def test_conference_page_renders_result_option(client, db_session):
    """Página dedicada de conferência: 4 opções com result-option (FR-008)."""
    asset = _setup_inventario_com_bem(client, db_session)
    from app.models.inventario import Inventario as Inv
    inv = db_session.query(Inv).first()
    resp = client.get(f"/inventarios/{inv.id}/conferir/{asset.id}")
    assert resp.status_code == 200
    _assert_result_options(resp.text, "página de conferência")


def test_inventory_detail_modal_renders_result_option(client, db_session):
    """Modal de conferência no detalhe do inventário: 4 opções com result-option (FR-008)."""
    _setup_inventario_com_bem(client, db_session)
    from app.models.inventario import Inventario as Inv
    inv = db_session.query(Inv).first()
    resp = client.get(f"/inventarios/{inv.id}")
    assert resp.status_code == 200
    _assert_result_options(resp.text, "modal do detalhe do inventário")
