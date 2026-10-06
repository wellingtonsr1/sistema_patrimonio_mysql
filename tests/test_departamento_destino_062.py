"""Feature 062 — Seleção de destino por Departamento/Setor (apresentação).

Testes de:
- US1: renderização do select de destino em /movements/new (ui-contract §1):
  opções agrupadas por Unidade Administrativa (optgroup) e rótulo
  "Departamento (Unidade)", value = id da Location, opção vazia primeira.
- US2: mesma apresentação em /assets/new (ui-contract §2), preservando a
  opção vazia "Estoque Central" e o select de COLABORADOR (intocado).
- US3: guarda de NÃO-MUTAÇÃO (ui-contract §5; FR-006/FR-007): a mudança de
  apresentação não altera gravação (id + snapshot no formato atual),
  histórico anterior (nada regravado) nem a busca por snapshot (Feature 049).

US1/US2 são TDD red→green (escritos ANTES da alteração dos templates).
US3 é guarda verde-verde: passa antes E depois da mudança.
"""
import pytest

from app.models.enums import AssetCategory, MovementType
from app.models.movement import Movement
from app.schemas.asset import AssetCreate
from app.schemas.custodian import CustodianCreate
from app.schemas.location import LocationCreate
from app.schemas.movement import MovementFilter
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.location_service import LocationService
from app.services.movement_service import MovementService


def _criar_locais_062(db_session):
    """Dados fixos da feature (T002 remediada): 1 local no Clube, 2 na Sede."""
    prev = LocationService.create(db_session, LocationCreate(
        name="Sede - Divisão de Previdência",
        branch="IPMJP - Sede",
        department="Divisão de Previdência",
    ))
    arq = LocationService.create(db_session, LocationCreate(
        name="Sede - Setor de Arquivo",
        branch="IPMJP - Sede",
        department="Setor de Arquivo",
    ))
    clube = LocationService.create(db_session, LocationCreate(
        name="Clube da Pessoa Idosa",
        branch="Clube",
        department="Clube da Pessoa Idosa",
    ))
    return {"prev": prev, "arq": arq, "clube": clube}


def _grupo_do_html(html: str, branch: str) -> str:
    """Trecho entre <optgroup label="BRANCH"> e seu </optgroup> (ui-contract §1)."""
    marcador = f'<optgroup label="{branch}">'
    assert marcador in html, f"optgroup da unidade {branch!r} ausente"
    return html.split(marcador, 1)[1].split("</optgroup>", 1)[0]


# ============================================================================
# US1 — Movimentação: destino agrupado por unidade, departamento primeiro
# ============================================================================

def test_movements_new_groups_by_branch_with_department_first(client, db_session):
    locs = _criar_locais_062(db_session)
    html = client.get("/movements/new").text

    # (a) opção vazia primeira e FORA de qualquer grupo
    assert html.index("-- Manter Local Atual --") < html.index("<optgroup")

    # (b) grupos por Unidade Administrativa
    assert '<optgroup label="Clube">' in html
    assert '<optgroup label="IPMJP - Sede">' in html

    # (c) rótulo "Departamento (Unidade)" com o value correto DENTRO do grupo certo
    grupo_sede = _grupo_do_html(html, "IPMJP - Sede")
    grupo_clube = _grupo_do_html(html, "Clube")
    assert f'<option value="{locs["prev"].id}">Divisão de Previdência (IPMJP - Sede)</option>' in grupo_sede
    assert f'<option value="{locs["arq"].id}">Setor de Arquivo (IPMJP - Sede)</option>' in grupo_sede
    assert f'<option value="{locs["clube"].id}">Clube da Pessoa Idosa (Clube)</option>' in grupo_clube

    # (c2) ordem intra-grupo (FR-008): ordem da fonte — departamento → nome
    assert grupo_sede.index("Divisão de Previdência (IPMJP - Sede)") < grupo_sede.index("Setor de Arquivo (IPMJP - Sede)")

    # (d) sem o formato antigo redundante (Sede - X (IPMJP - Sede - X))
    assert "Divisão de Previdência (IPMJP - Sede - Divisão de Previdência)" not in html
    assert "Setor de Arquivo (IPMJP - Sede - Setor de Arquivo)" not in html


# ============================================================================
# US2 — Equipamento: mesma apresentação; select de colaborador intocado
# ============================================================================

def test_assets_new_groups_by_branch_preserving_custodian_select(client, db_session):
    locs = _criar_locais_062(db_session)
    CustodianService.create(db_session, CustodianCreate(
        name="Colaborador 062",
        email="col062@test.local",
        role="Agente",
        department="Divisão de Previdência",
    ))  # sem matrícula → gera PROV-* (Feature 010)
    html = client.get("/assets/new").text

    # (a) opção vazia atual primeira e FORA de qualquer grupo
    assert html.index("-- Estoque Central / Almoxarifado --") < html.index("<optgroup")

    # (b) grupos por unidade
    assert '<optgroup label="Clube">' in html
    assert '<optgroup label="IPMJP - Sede">' in html

    # (c) rótulo + value dentro do grupo correto
    grupo_sede = _grupo_do_html(html, "IPMJP - Sede")
    grupo_clube = _grupo_do_html(html, "Clube")
    assert f'<option value="{locs["prev"].id}">Divisão de Previdência (IPMJP - Sede)</option>' in grupo_sede
    assert f'<option value="{locs["clube"].id}">Clube da Pessoa Idosa (Clube)</option>' in grupo_clube

    # (d) guarda: select de COLABORADOR continua com o rótulo atual
    #     "Nome (Matrícula - Departamento)" — imune à mudança
    assert "Colaborador 062 (" in html
    assert " - Divisão de Previdência)" in html


# ============================================================================
# US3 — Guarda de não-mutação (verde ANTES e DEPOIS da mudança de template)
# ============================================================================

def test_transferencia_nao_muda_gravacao_nem_historico(client, db_session):
    loc_a = LocationService.create(db_session, LocationCreate(
        name="Sala A", branch="Unidade A", department="Dept A"))
    loc_b = LocationService.create(db_session, LocationCreate(
        name="Sala B", branch="Unidade B", department="Dept B"))

    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-06201",
        name="Notebook 062",
        category=AssetCategory.NOTEBOOK,
        purchase_value=1000.0,
        initial_location_id=loc_a.id,
    ))

    # snapshot da ENTRADA_AQUISICAO antes do POST (para provar que nada é regravado)
    mov_entrada_antes = [
        t["data"] for t in MovementService.get_timeline_for_asset(db_session, asset.id)
        if t["type"] == "movement" and t["data"].movement_type == MovementType.ACQUISITION
    ][0]
    antes = (mov_entrada_antes.origin_location_name, mov_entrada_antes.destination_location_name)
    # origem literal da entrada (Feature 029) + destino no formato atual (FR-006)
    assert antes == ("Fornecedor / Entrada Inicial", "Unidade A - Dept A (Sala A)")

    resp = client.post("/movements/new", data={
        "asset_id": str(asset.id),
        "movement_type": "TRANSFERENCIA_LOCAL",
        "destination_location_id": str(loc_b.id),
        "reason": "Teste 062 nao-mutacao",
        "operator_name": "Auditor 062",
    })
    # TestClient segue o redirect (303) por padrão → resposta final 200;
    # o sucesso é provado pela movimentação gravada no banco, logo abaixo

    db_session.expire_all()
    transferencia = db_session.query(Movement).filter(
        Movement.asset_id == asset.id,
        Movement.movement_type == MovementType.TRANSFER,
    ).first()
    assert transferencia is not None

    # (a) gravação idêntica à atual: FK + snapshot no formato atual
    assert transferencia.destination_location_id == loc_b.id
    assert transferencia.destination_location_name == "Unidade B - Dept B (Sala B)"

    # (b) a ENTRADA permanece byte-a-byte idêntica (nada é regravado)
    mov_entrada_depois = [
        t["data"] for t in MovementService.get_timeline_for_asset(db_session, asset.id)
        if t["type"] == "movement" and t["data"].movement_type == MovementType.ACQUISITION
    ][0]
    assert (mov_entrada_depois.origin_location_name, mov_entrada_depois.destination_location_name) == antes

    # (c) busca por snapshot (Feature 049) continua encontrando pelos mesmos termos
    movs_b, _ = MovementService.get_all_movements(db_session, filters=MovementFilter(search="Dept B"))
    assert any(m.id == transferencia.id for m in movs_b)
    movs_a, _ = MovementService.get_all_movements(db_session, filters=MovementFilter(search="Dept A"))
    assert any(m.id == mov_entrada_depois.id for m in movs_a)
