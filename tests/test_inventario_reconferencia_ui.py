"""
Testes de UI da re-conferência de inventário (feature 003 — aviso de sobrescrita).

Cobre a camada de apresentação APENAS: alerta da conferência anterior nos modais
de `detail.html`, confirmação (`confirm()`) no envio para itens já conferidos e
complemento do alerta existente em `conferir.html`.

Nenhuma alteração de backend é exigida ou testada aqui: a rota
`POST /inventarios/{id}/conferir/{item_id}` e o `InventarioService.record_check`
permanecem os mesmos (regressão coberta por tests/test_inventario.py).

Cenários de referência: specs/003-aviso-reconferencia/quickstart.md (A–F) e
critérios CA-01..CA-09 da spec.
"""

import pytest

from app.models.enums import AssetCategory, AssetCondition, InventarioItemStatus
from app.services.asset_service import AssetService
from app.services.inventario_service import InventarioService
from app.services.location_service import LocationService
from app.schemas.asset import AssetCreate
from app.schemas.location import LocationCreate

TEST_USERNAME = "testuser"


# ============================================================================
# Helpers compartilhados (padrões de tests/test_inventario.py)
# ============================================================================

def _make_location(db, name="Loc Reconferencia", department="TI"):
    return LocationService.create(db, LocationCreate(
        name=name,
        branch="Matriz",
        department=department,
    ))


def _make_asset(db, tag, location=None, name="Notebook Dell"):
    return AssetService.create(db, AssetCreate(
        tag=tag,
        name=name,
        category=AssetCategory.NOTEBOOK,
        purchase_value=3500.0,
        condition=AssetCondition.GOOD,
        initial_location_id=location.id if location else None,
    ))


def _create_inventario(client, db_session, location, name="Inventário Reconferência"):
    """Cria inventário com escopo por local (padrão test_full_inventory_flow_via_web)."""
    resp = client.post(
        "/inventarios/new",
        data={"name": name, "location_id": str(location.id)},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    inv_id = int(resp.headers["Location"].rsplit("/", 1)[1])
    inv = InventarioService.get_by_id(db_session, inv_id)
    assert inv is not None
    return inv


def _get_item_for_asset(db_session, inv, asset):
    return [i for i in inv.itens if i.asset.tag == asset.tag][0]


def _conferir_item(client, inv_id, item_id, result="ENCONTRADO", observation="Conferido", found_location_id=None):
    """Registra uma conferência pela rota web existente (service intacto)."""
    data = {"result": result, "observation": observation}
    if found_location_id is not None:
        data["found_location_id"] = str(found_location_id)
    resp = client.post(
        f"/inventarios/{inv_id}/conferir/{item_id}",
        data=data,
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    return resp


def _detail_page(client, inv_id):
    resp = client.get(f"/inventarios/{inv_id}")
    assert resp.status_code == 200, resp.text
    return resp.text


# ============================================================================
# US1 — Alerta da conferência anterior nos modais (T004–T006)
# ============================================================================

def test_modal_pendente_sem_alerta(client, db_session):
    """CA-01: item PENDENTE abre modal sem alerta de sobrescrita."""
    loc = _make_location(db_session)
    asset = _make_asset(db_session, "INV-REC-0001", location=loc)
    inv = _create_inventario(client, db_session, loc)
    item = _get_item_for_asset(db_session, inv, asset)
    assert item.status == InventarioItemStatus.PENDING

    html = _detail_page(client, inv.id)

    assert f'id="modalConferir{item.id}"' in html
    assert "Resultado anterior" not in html
    assert "substituirá" not in html
    assert "Já conferido" not in html


def test_modal_conferido_exibe_alerta_com_dados(client, db_session):
    """CA-02/CA-03: modal de item conferido mostra quem, quando e resultado anterior."""
    from datetime import datetime

    loc = _make_location(db_session)
    asset = _make_asset(db_session, "INV-REC-0002", location=loc)
    inv = _create_inventario(client, db_session, loc)
    item = _get_item_for_asset(db_session, inv, asset)

    _conferir_item(client, inv.id, item.id, result="ENCONTRADO")
    db_session.expire_all()

    # Re-carrega o inventário e os itens com a sessão local (pós-conferência)
    inv = InventarioService.get_by_id(db_session, inv.id)
    item = _get_item_for_asset(db_session, inv, asset)
    assert item.status == InventarioItemStatus.FOUND

    html = _detail_page(client, inv.id)

    assert "Já conferido por testuser" in html
    # Data/hora no formato %d/%m/%Y %H:%M (usa o checked_at recém-gravado)
    assert item.checked_at is not None
    assert item.checked_at.strftime("%d/%m/%Y %H:%M") in html
    assert "Resultado anterior: Encontrado" in html
    assert "substituirá" in html


def test_modal_alerta_sem_dados_historicos_nao_inventa(client, db_session):
    """CA-08: sem checked_by_name/checked_at, o alerta omite os trechos — nada inventado."""
    loc = _make_location(db_session)
    asset = _make_asset(db_session, "INV-REC-0003", location=loc)
    inv = _create_inventario(client, db_session, loc)
    item = _get_item_for_asset(db_session, inv, asset)

    _conferir_item(client, inv.id, item.id, result="NAO_ENCONTRADO")
    db_session.expire_all()

    # Re-carrega com a sessão local e simula ondelete="SET NULL":
    # histórico de conferência indisponível
    inv = InventarioService.get_by_id(db_session, inv.id)
    item = _get_item_for_asset(db_session, inv, asset)
    item.checked_by_name = None
    item.checked_at = None
    db_session.commit()

    html = _detail_page(client, inv.id)

    assert "Já conferido por" not in html
    assert f"Resultado anterior: {InventarioItemStatus.NOT_FOUND.label}" in html
    assert "substituirá" in html


# ============================================================================
# US2 — Confirmação explícita no envio (T009–T010)
# ============================================================================

CONFIRM_TEXT = (
    "onsubmit=\"return confirm('Este item já foi conferido. "
    "Registrar um novo resultado vai substituir o anterior. Continuar?')\""
)


def test_onsubmit_condicional_por_status(client, db_session):
    """CA-01/CA-04: onsubmit de confirmação só em itens conferidos; pendentes sem o atributo."""
    loc = _make_location(db_session)
    asset1 = _make_asset(db_session, "INV-REC-0004", location=loc)
    asset2 = _make_asset(db_session, "INV-REC-0005", location=loc)
    inv = _create_inventario(client, db_session, loc)
    item1 = _get_item_for_asset(db_session, inv, asset1)
    item2 = _get_item_for_asset(db_session, inv, asset2)

    # Confere apenas o primeiro item
    _conferir_item(client, inv.id, item1.id, result="ENCONTRADO")
    db_session.expire_all()

    html = _detail_page(client, inv.id)

    assert CONFIRM_TEXT in html            # item conferido tem o diálogo
    assert html.count(CONFIRM_TEXT) == 1   # apenas 1 dos 2 modais o tem
    # O form do modal pendente não tem onsubmit
    item2_modal_start = html.find(f'id="modalConferir{item2.id}"')
    assert item2_modal_start > 0
    form_seg = html[item2_modal_start:item2_modal_start + 300]
    assert "<form method=\"post\"" in form_seg
    assert "onsubmit" not in form_seg


def test_reconferencia_continua_gravando_pela_rota_existente(client, db_session):
    """CA-06: re-conferência via rota existente grava normalmente (regressão)."""
    loc = _make_location(db_session)
    other_loc = _make_location(db_session, name="Loc Divergente", department="RH")
    asset = _make_asset(db_session, "INV-REC-0006", location=loc)
    inv = _create_inventario(client, db_session, loc)
    item = _get_item_for_asset(db_session, inv, asset)

    _conferir_item(client, inv.id, item.id, result="ENCONTRADO")
    _conferir_item(
        client, inv.id, item.id,
        result="LOCAL_DIFERENTE", observation="Achou na sala ao lado",
        found_location_id=other_loc.id,
    )
    db_session.expire_all()

    inv = InventarioService.get_by_id(db_session, inv.id)
    item = _get_item_for_asset(db_session, inv, asset)
    assert item.status == InventarioItemStatus.FOUND_WRONG_LOCATION
    assert item.observation == "Achou na sala ao lado"
    assert item.checked_by_name == TEST_USERNAME


# ============================================================================
# US3 — Página de conferência em campo (T013)
# ============================================================================

def test_conferir_page_alerta_complementado_e_pendente_sem_alerta(client, db_session):
    """US3: alerta existente preservado + complemento (conferente/data); pendente sem alerta."""
    loc = _make_location(db_session)
    asset1 = _make_asset(db_session, "INV-REC-0007", location=loc)
    asset2 = _make_asset(db_session, "INV-REC-0008", location=loc)
    inv = _create_inventario(client, db_session, loc)
    item1 = _get_item_for_asset(db_session, inv, asset1)
    item2 = _get_item_for_asset(db_session, inv, asset2)

    _conferir_item(client, inv.id, item1.id, result="ENCONTRADO")
    db_session.expire_all()

    # Item conferido: alerta existente mantido + complemento
    resp = client.get(f"/inventarios/{inv.id}/conferir/{asset1.id}")
    assert resp.status_code == 200, resp.text
    html = resp.text
    assert "Resultado já registrado:" in html
    assert "pode ser atualizado abaixo" in html
    assert "Conferido por testuser" in html
    inv = InventarioService.get_by_id(db_session, inv.id)
    item1 = _get_item_for_asset(db_session, inv, asset1)
    assert item1.checked_at is not None
    assert item1.checked_at.strftime("%d/%m/%Y %H:%M") in html

    # Item pendente: apresentação atual, sem alerta de resultado registrado
    resp = client.get(f"/inventarios/{inv.id}/conferir/{asset2.id}")
    assert resp.status_code == 200, resp.text
    html2 = resp.text
    assert "Pendente de conferência" in html2
    assert "Resultado já registrado" not in html2
    assert "Conferido por" not in html2
