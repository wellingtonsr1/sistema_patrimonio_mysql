import pytest
from app.models.enums import AssetStatus, AssetCategory, MovementType
from app.schemas.asset import AssetCreate
from app.schemas.custodian import CustodianCreate
from app.schemas.location import LocationCreate
from app.schemas.movement import MovementCreate, MovementFilter
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.location_service import LocationService
from app.services.movement_service import MovementService


@pytest.fixture
def sample_movements(db_session):
    """Cria conjunto diversificado de movimentações para validação da pesquisa."""
    loc_ti = LocationService.create(db_session, LocationCreate(
        name="TI Central", branch="Matriz", department="TI"
    ))
    loc_almox = LocationService.create(db_session, LocationCreate(
        name="Almoxarifado Geral", branch="Matriz", department="Logística"
    ))
    loc_rh = LocationService.create(db_session, LocationCreate(
        name="Recursos Humanos", branch="Filial 1", department="RH"
    ))

    cust_rodrigo = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-5001",
        name="Rodrigo Santos",
        email="rodrigo.santos@empresa.com",
        role="Desenvolvedor",
        department="TI"
    ))
    cust_amanda = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-5002",
        name="Amanda Silva",
        email="amanda.silva@empresa.com",
        role="Analista",
        department="RH"
    ))

    # Bem 1: Notebook Dell
    asset1 = AssetService.create(db_session, AssetCreate(
        tag="PAT-99001",
        name="Dell Latitude 5440",
        category=AssetCategory.NOTEBOOK,
        purchase_value=5500.0,
        initial_location_id=loc_almox.id
    ))
    # Aloca para Rodrigo
    mov1 = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset1.id,
        movement_type=MovementType.ALLOCATION,
        destination_location_id=loc_ti.id,
        destination_custodian_id=cust_rodrigo.id,
        reason="Entrega para desenvolvedor",
        operator_name="Carlos Operador",
        term_code="TR-2026-00042"
    ))

    # Bem 2: Monitor LG
    asset2 = AssetService.create(db_session, AssetCreate(
        tag="PAT-99002",
        name="Monitor LG Ultrawide 29",
        category=AssetCategory.MONITOR,
        purchase_value=1200.0,
        initial_location_id=loc_almox.id
    ))
    # Transfere para RH
    mov2 = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset2.id,
        movement_type=MovementType.TRANSFER,
        destination_location_id=loc_rh.id,
        reason="Transferência para nova sala de RH",
        operator_name="Maria Supervisora",
        term_code="TR-2026-00099"
    ))

    # Bem 3: Impressora HP
    asset3 = AssetService.create(db_session, AssetCreate(
        tag="PAT-99003",
        name="Impressora HP LaserJet Pro",
        category=AssetCategory.PRINTER,
        purchase_value=2500.0,
        initial_location_id=loc_almox.id
    ))

    return {
        "loc_ti": loc_ti,
        "loc_almox": loc_almox,
        "loc_rh": loc_rh,
        "cust_rodrigo": cust_rodrigo,
        "cust_amanda": cust_amanda,
        "asset1": asset1,
        "asset2": asset2,
        "asset3": asset3,
        "mov1": mov1,
        "mov2": mov2,
    }


# ==============================================================================
# USER STORY 1: LOCALIZAR MOVIMENTAÇÕES POR TEXTO SIMPLES E PARCIAL (P1 🎯 MVP)
# ==============================================================================

def test_search_by_tag(db_session, sample_movements):
    """Teste A: pesquisa por tombamento exato e parcial."""
    # Busca por tombamento PAT-99001
    f = MovementFilter(search="PAT-99001")
    items, total = MovementService.get_all_movements(db_session, filters=f)
    assert total >= 1
    assert all("PAT-99001" in m.asset.tag for m in items)

    # Busca parcial 99002
    f2 = MovementFilter(search="99002")
    items2, total2 = MovementService.get_all_movements(db_session, filters=f2)
    assert total2 >= 1
    assert all("PAT-99002" in m.asset.tag for m in items2)


def test_search_by_equipment_name_partial_and_case_insensitive(db_session, sample_movements):
    """Teste B: pesquisa parcial por nome do equipamento (case-insensitive)."""
    # Minúsculas
    f = MovementFilter(search="latitude")
    items, total = MovementService.get_all_movements(db_session, filters=f)
    assert total >= 1
    assert all("Dell Latitude" in m.asset.name for m in items)

    # Maiúsculas
    f2 = MovementFilter(search="DELL")
    items2, total2 = MovementService.get_all_movements(db_session, filters=f2)
    assert total2 >= 1
    assert all("Dell" in m.asset.name for m in items2)


def test_search_by_custodian_name_and_matricula(db_session, sample_movements):
    """Teste C: pesquisa por colaborador (nome ou matrícula na origem/destino)."""
    # Nome do colaborador
    f1 = MovementFilter(search="Rodrigo")
    items1, total1 = MovementService.get_all_movements(db_session, filters=f1)
    assert total1 >= 1
    assert any(
        (m.destination_custodian_name and "Rodrigo" in m.destination_custodian_name) or
        (m.origin_custodian_name and "Rodrigo" in m.origin_custodian_name) or
        (m.destination_custodian and "Rodrigo" in m.destination_custodian.name)
        for m in items1
    )

    # Matrícula
    f2 = MovementFilter(search="MAT-5001")
    items2, total2 = MovementService.get_all_movements(db_session, filters=f2)
    assert total2 >= 1
    assert any(
        (m.destination_custodian and m.destination_custodian.registration_code == "MAT-5001") or
        (m.origin_custodian and m.origin_custodian.registration_code == "MAT-5001")
        for m in items2
    )


def test_search_by_location(db_session, sample_movements):
    """Teste D: pesquisa por local (origem ou destino)."""
    f = MovementFilter(search="TI Central")
    items, total = MovementService.get_all_movements(db_session, filters=f)
    assert total >= 1
    assert any(
        (m.destination_location_name and "TI Central" in m.destination_location_name) or
        (m.origin_location_name and "TI Central" in m.origin_location_name)
        for m in items
    )


def test_search_by_operator_and_term_code(db_session, sample_movements):
    """Pesquisa por operador e identificador do termo."""
    f_op = MovementFilter(search="Carlos Operador")
    items_op, total_op = MovementService.get_all_movements(db_session, filters=f_op)
    assert total_op >= 1
    assert all("Carlos Operador" in m.operator_name for m in items_op)

    real_term = sample_movements["mov1"].term_code
    assert real_term is not None
    f_term = MovementFilter(search=real_term)
    items_term, total_term = MovementService.get_all_movements(db_session, filters=f_term)
    assert total_term >= 1
    assert any(m.term_code == real_term for m in items_term)


def test_search_by_movement_type_label_or_enum(db_session, sample_movements):
    """Pesquisa por tipo de movimentação via rótulo em português ou nome do enum."""
    f_label = MovementFilter(search="Transferência")
    items_label, total_label = MovementService.get_all_movements(db_session, filters=f_label)
    assert total_label >= 1
    assert all(m.movement_type == MovementType.TRANSFER for m in items_label)


def test_search_web_route_integration(client, sample_movements):
    """Verifica chamada HTTP GET /movements?search=... na rota web."""
    response = client.get("/movements?search=Latitude")
    assert response.status_code == 200
    assert "Dell Latitude 5440" in response.text
    assert "Monitor LG" not in response.text
    assert 'value="Latitude"' in response.text


# ==============================================================================
# USER STORY 2: INTEGRAÇÃO COM FILTROS EXISTENTES E LIMPEZA (P2)
# ==============================================================================

def test_search_combined_with_movement_type(db_session, sample_movements):
    """Teste E: pesquisa combinada cumulativa com filtro de tipo de movimentação."""
    # Dell com tipo ALLOCATION -> deve encontrar
    f_match = MovementFilter(search="Dell", movement_type=MovementType.ALLOCATION)
    items_match, total_match = MovementService.get_all_movements(db_session, filters=f_match)
    assert total_match == 1
    assert items_match[0].asset.tag == "PAT-99001"
    assert items_match[0].movement_type == MovementType.ALLOCATION

    # Dell com tipo TRANSFER -> deve retornar zero (Dell foi alocado, não transferido)
    f_nomatch = MovementFilter(search="Dell", movement_type=MovementType.TRANSFER)
    items_nomatch, total_nomatch = MovementService.get_all_movements(db_session, filters=f_nomatch)
    assert total_nomatch == 0
    assert len(items_nomatch) == 0


def test_search_empty_or_whitespace_returns_all(db_session, sample_movements):
    """Teste G: pesquisa vazia ou somente com espaços retorna listagem padrão inalterada."""
    items_all, total_all = MovementService.get_all_movements(db_session)

    f_empty = MovementFilter(search="")
    items_empty, total_empty = MovementService.get_all_movements(db_session, filters=f_empty)
    assert total_empty == total_all
    assert len(items_empty) == len(items_all)

    f_spaces = MovementFilter(search="    ")
    items_spaces, total_spaces = MovementService.get_all_movements(db_session, filters=f_spaces)
    assert total_spaces == total_all
    assert len(items_spaces) == len(items_all)


def test_search_web_clear_link_and_repopulation(client, sample_movements):
    """Verifica repopulação de campos e presença do botão Limpar."""
    response = client.get("/movements?search=Latitude&movement_type=ALOCACAO_CAUTELA")
    assert response.status_code == 200
    assert 'value="Latitude"' in response.text
    assert 'selected>Alocação / Cautela' in response.text
    assert 'href="/movements"' in response.text
    assert "Limpar" in response.text


# ==============================================================================
# USER STORY 3: ESTADO VAZIO, RESPONSIVIDADE E PRESERVAÇÃO DE SEGURANÇA (P3)
# ==============================================================================

def test_search_no_results_empty_state_feedback(client, sample_movements):
    """Teste F: busca sem resultados exibe mensagem clara e atalho para limpar pesquisa."""
    response = client.get("/movements?search=TERMO_INEXISTENTE_XYZ")
    assert response.status_code == 200
    assert "Nenhuma movimentação encontrada para a pesquisa informada" in response.text
    assert "Limpar Pesquisa" in response.text


def test_search_respects_backend_limit(db_session, sample_movements):
    """Teste H: respeita limite de paginação/registros sem carregar tudo em memória."""
    f = MovementFilter(search="PAT-99")
    items, total = MovementService.get_all_movements(db_session, filters=f, limit=1)
    assert total >= 2
    assert len(items) == 1


def test_search_requires_permission_rbac(unauth_client, sample_movements, db_session):
    """Teste I: usuário sem permissão movimentacao.visualizar recebe 403."""
    from app.services.auth_service import create_user
    from app.services.permission_service import ensure_default_roles

    ensure_default_roles(db_session)
    create_user(db_session, username="sem_perm", password="pwd@1234User", full_name="Sem Permissao")

    login_resp = unauth_client.post(
        "/api/v1/auth/login", data={"username": "sem_perm", "password": "pwd@1234User"}
    )
    assert login_resp.status_code == 200

    # Tenta acessar rota de movimentações com busca
    res = unauth_client.get("/movements?search=Dell")
    assert res.status_code == 403


def test_search_is_strictly_read_only(db_session, sample_movements):
    """Verifica que a operação de busca não muta registros, tabelas ou históricos."""
    from app.models.movement import Movement
    from app.models.asset import Asset

    count_mov_before = db_session.query(Movement).count()
    count_assets_before = db_session.query(Asset).count()

    f = MovementFilter(search="PAT-99001")
    MovementService.get_all_movements(db_session, filters=f)

    assert db_session.query(Movement).count() == count_mov_before
    assert db_session.query(Asset).count() == count_assets_before
