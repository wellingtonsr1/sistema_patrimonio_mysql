import pytest
from app.models.enums import AssetStatus, AssetCondition, AssetCategory, MovementType
from app.models.movement import Movement
from app.schemas.asset import AssetCreate
from app.schemas.custodian import CustodianCreate
from app.schemas.location import LocationCreate
from app.schemas.movement import MovementCreate
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.location_service import LocationService
from app.services.movement_service import MovementService


def test_asset_creation_registers_initial_movement(db_session):
    """Verifica se ao criar um equipamento o primeiro fluxo (ENTRADA_AQUISICAO) é gravado automaticamente"""
    loc = LocationService.create(db_session, LocationCreate(
        name="TI Central", branch="Matriz", department="TI"
    ))
    
    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-99001",
        name="Dell Latitude 5440",
        category=AssetCategory.NOTEBOOK,
        purchase_value=5500.0,
        initial_location_id=loc.id
    ))

    assert asset.id is not None
    assert asset.status == AssetStatus.AVAILABLE

    # Verifica se o primeiro movimento foi gerado
    # (a timeline retorna dicts: {'type': 'movement'|'audit', 'data': Movement|AuditLog, ...})
    timeline = MovementService.get_timeline_for_asset(db_session, asset.id)
    assert len(timeline) == 1
    assert timeline[0]["type"] == "movement"
    assert timeline[0]["data"].movement_type == MovementType.ACQUISITION
    assert timeline[0]["data"].destination_location_id == loc.id
    assert "Tombamento inicial" in timeline[0]["data"].reason


def test_allocation_and_custody_flow(db_session):
    """Testa o fluxo completo de alocação de equipamento a um colaborador e geração do termo"""
    loc = LocationService.create(db_session, LocationCreate(name="TI", branch="SP", department="TI"))
    cust = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-5001",
        name="Rodrigo Santos",
        email="rodrigo@empresa.com",
        role="Dev",
        department="TI"
    ))

    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-99002",
        name="MacBook Air M2",
        category=AssetCategory.NOTEBOOK,
        initial_location_id=loc.id
    ))

    # Executa Alocação
    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.ALLOCATION,
        destination_custodian_id=cust.id,
        reason="Entrega de computador de trabalho",
        operator_name="Admin TI"
    ))

    assert movement.new_status == AssetStatus.IN_USE
    assert movement.term_code is not None
    assert "TR-" in movement.term_code

    # Verifica atualização no ativo
    db_session.refresh(asset)
    assert asset.status == AssetStatus.IN_USE
    assert asset.custodian_id == cust.id

    # Verifica histórico completo do fluxo
    # (a timeline retorna dicts: {'type': 'movement'|'audit', 'data': Movement|AuditLog, ...})
    timeline = MovementService.get_timeline_for_asset(db_session, asset.id)
    assert len(timeline) == 2
    assert timeline[0]["type"] == "movement"
    assert timeline[0]["data"].movement_type == MovementType.ALLOCATION
    assert timeline[1]["data"].movement_type == MovementType.ACQUISITION


def test_return_to_stock_flow(db_session):
    """Testa o fluxo de devolução do equipamento ao estoque"""
    loc = LocationService.create(db_session, LocationCreate(name="TI", branch="SP", department="TI"))
    cust = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-5002",
        name="Fernanda Lima",
        email="fernanda@empresa.com",
        role="Designer",
        department="UX"
    ))

    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-99003",
        name="Monitor 27 Pol",
        category=AssetCategory.MONITOR,
        initial_location_id=loc.id,
        initial_custodian_id=cust.id
    ))

    assert asset.status == AssetStatus.IN_USE

    # Executa Devolução ao Estoque
    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.RETURN_STOCK,
        destination_location_id=loc.id,
        reason="Devolução de monitor por migração para home office",
        operator_name="Admin TI"
    ))

    db_session.refresh(asset)
    assert asset.status == AssetStatus.AVAILABLE
    assert asset.custodian_id is None
    assert movement.movement_type == MovementType.RETURN_STOCK


def test_cannot_move_written_off_asset(db_session):
    """Garante que equipamentos descartados/baixados não possam ser movimentados"""
    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-99004",
        name="Nobreak Antigo",
        category=AssetCategory.EQUIPMENT
    ))

    # Baixa o equipamento
    MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.WRITE_OFF,
        reason="Sucata sem conserto",
        operator_name="Admin"
    ))

    db_session.refresh(asset)
    assert asset.status == AssetStatus.WRITTEN_OFF

    # Tenta movimentar novamente
    with pytest.raises(ValueError, match="já foi baixado"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            reason="Tentativa inválida de transferir sucata",
            operator_name="Admin"
        ))


def test_term_page_qr_code_points_to_term_route(client, db_session):
    """O QR Code de validação do termo deve apontar para a rota web do termo"""
    cust = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-7100",
        name="Teste QR",
        email="qr@empresa.com",
        role="Dev",
        department="TI"
    ))
    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-99010",
        name="Notebook Teste",
        category=AssetCategory.NOTEBOOK
    ))
    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.ALLOCATION,
        destination_custodian_id=cust.id,
        reason="Teste do QR code do termo",
        operator_name="Admin"
    ))
    assert movement.term_code is not None

    response = client.get(f"/movements/{movement.id}/term")
    assert response.status_code == 200
    # O QR deve validar na página do termo, não numa rota inexistente
    assert f"/movements/{movement.id}/term" in response.text


# ============================================================================
# Feature 005 — Matriz de Movimentação (Local x Responsável)
# ============================================================================

def _setup_bem_com_responsavel(db_session, tag, loc_suffix, cust_suffix):
    """Cria local + colaborador + bem alocado (IN_USE) — base dos cenários da matriz."""
    loc = LocationService.create(db_session, LocationCreate(
        name=f"Local {loc_suffix}", branch="Matriz", department=f"Dep {loc_suffix}"
    ))
    cust = CustodianService.create(db_session, CustodianCreate(
        registration_code=f"MAT-{cust_suffix}",
        name=f"Colaborador {cust_suffix}",
        email=f"colab{cust_suffix}@empresa.com",
        role="Analista",
        department=f"Dep {loc_suffix}"
    ))
    asset = AssetService.create(db_session, AssetCreate(
        tag=tag,
        name="Notebook de Teste",
        category=AssetCategory.NOTEBOOK,
        initial_location_id=loc.id,
        initial_custodian_id=cust.id
    ))
    return loc, cust, asset


# ---- US1: Bloqueio de movimentações sem alteração efetiva ----

def test_allocation_same_location_and_same_custodian_is_blocked(db_session):
    """US1 (T009) — ALLOCATION com mesmo local e mesmo responsável deve ser bloqueada."""
    loc, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00501", "US1a", "5001")
    movements_before = db_session.query(Movement).filter(Movement.asset_id == asset.id).count()
    snapshot = (asset.status, asset.location_id, asset.custodian_id)

    with pytest.raises(ValueError, match="Nenhuma alteração efetiva"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.ALLOCATION,
            destination_location_id=loc.id,       # mesmo local
            destination_custodian_id=cust.id,     # mesmo responsável
            reason="Tentativa sem alteração efetiva",
            operator_name="Auditor"
        ))

    db_session.refresh(asset)
    assert (asset.status, asset.location_id, asset.custodian_id) == snapshot
    assert db_session.query(Movement).filter(Movement.asset_id == asset.id).count() == movements_before


def test_transfer_same_location_and_same_custodian_is_blocked(db_session):
    """US1 (T010) — TRANSFER sem mudança de local e sem mudança de responsável é bloqueada."""
    loc, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00502", "US1b", "5002")
    movements_before = db_session.query(Movement).filter(Movement.asset_id == asset.id).count()

    with pytest.raises(ValueError, match="Nenhuma alteração efetiva"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            destination_location_id=loc.id,       # mesmo local
            destination_custodian_id=cust.id,     # mesmo responsável
            reason="Tentativa sem alteração efetiva",
            operator_name="Auditor"
        ))

    assert db_session.query(Movement).filter(Movement.asset_id == asset.id).count() == movements_before


def test_blocked_operation_generates_no_term_or_asset_change(db_session):
    """US1 (T011) — Operação bloqueada não gera Movement, termo ou alteração patrimonial."""
    loc, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00503", "US1c", "5003")
    movements_before = db_session.query(Movement).filter(Movement.asset_id == asset.id).count()
    terms_before = db_session.query(Movement).filter(Movement.term_code.isnot(None)).count()

    with pytest.raises(ValueError, match="Nenhuma alteração efetiva"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.ALLOCATION,
            destination_location_id=loc.id,
            destination_custodian_id=cust.id,
            reason="Bloqueio sem efeitos colaterais",
            operator_name="Auditor"
        ))

    assert db_session.query(Movement).filter(Movement.asset_id == asset.id).count() == movements_before
    assert db_session.query(Movement).filter(Movement.term_code.isnot(None)).count() == terms_before
    db_session.refresh(asset)
    assert asset.status == AssetStatus.IN_USE
    assert asset.custodian_id == cust.id
    assert asset.location_id == loc.id


# ---- US2: Alocação no mesmo local / tipos corretos ----

def test_allocation_same_location_new_custodian_succeeds(db_session):
    """US2 (T014/T015) — Alocação a novo colaborador mantendo o local: sucesso, termo, local preservado."""
    loc, cust_old, asset = _setup_bem_com_responsavel(db_session, "PAT-00504", "US2a", "5004")
    cust_new = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-5010",
        name="Mariana Costa",
        email="mariana@empresa.com",
        role="Analista",
        department="Dep US2a"
    ))

    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.ALLOCATION,
        destination_custodian_id=cust_new.id,   # responsável diferente, local não informado (= atual)
        reason="Troca de colaborador no mesmo setor",
        operator_name="Gestor"
    ))

    db_session.refresh(asset)
    assert asset.custodian_id == cust_new.id
    assert asset.location_id == loc.id                 # local preservado
    assert asset.status == AssetStatus.IN_USE
    assert movement.term_code is not None              # termo gerado
    assert movement.destination_custodian_id == cust_new.id


def test_transfer_same_location_is_blocked(db_session):
    """US2 (T016) — TRANSFER mantendo o local atual é bloqueada (mesmo mudando o responsável)."""
    loc, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00505", "US2b", "5005")
    cust_new = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-5011",
        name="Mario Torres",
        email="mario@empresa.com",
        role="Analista",
        department="Dep US2b"
    ))

    with pytest.raises(ValueError, match="local de destino diferente"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            destination_location_id=loc.id,        # mesmo local
            destination_custodian_id=cust_new.id,  # responsável diferente
            reason="Tentativa de transferência no mesmo local",
            operator_name="Auditor"
        ))


def test_allocation_without_custodian_is_blocked(db_session):
    """US2 (T017) — Alocação exige responsável de destino válido (VAL-003, reforço da matriz)."""
    loc, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00506", "US2c", "5006")

    with pytest.raises(ValueError, match="obrigatório selecionar o colaborador"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.ALLOCATION,
            destination_location_id=loc.id,
            # sem destination_custodian_id
            reason="Alocação sem responsável",
            operator_name="Auditor"
        ))


# ---- US3: Transferência de local mantendo o responsável ----

def test_transfer_new_location_same_custodian_succeeds(db_session):
    """US3 (T021/T022) — Transferência para novo local mantendo o responsável: local atualizado, custodiante preservado."""
    loc_a, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00507", "US3a", "5007")
    loc_b = LocationService.create(db_session, LocationCreate(
        name="Local US3b", branch="Filial", department="Dep US3b"
    ))

    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.TRANSFER,
        destination_location_id=loc_b.id,   # local diferente
        # destination_custodian_id omitido → preserva o atual
        reason="Mudança de filial mantendo o colaborador",
        operator_name="Gestor"
    ))

    db_session.refresh(asset)
    assert asset.location_id == loc_b.id
    assert asset.custodian_id == cust.id                # preservado
    assert movement.destination_custodian_id == cust.id  # T028: registro histórico fiel
    assert movement.destination_custodian_name == f"Colaborador 5007 (MAT-5007)"

    # status: bem alocado continua em uso
    assert asset.status == AssetStatus.IN_USE


def test_transfer_between_stock_locations_without_custodian(db_session):
    """US3 (T023) — Transferência entre locais de estoque sem responsável: mantém None e disponível."""
    loc_a = LocationService.create(db_session, LocationCreate(
        name="Almoxarifado A", branch="Matriz", department="Estoque"
    ))
    loc_b = LocationService.create(db_session, LocationCreate(
        name="Depósito B", branch="Filial", department="Estoque"
    ))
    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-00508",
        name="Cadeira de Estoque",
        category=AssetCategory.EQUIPMENT,
        initial_location_id=loc_a.id   # sem custodian_id → estoque
    ))

    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.TRANSFER,
        destination_location_id=loc_b.id,
        reason="Reorganização de estoque",
        operator_name="Almoxarife"
    ))

    db_session.refresh(asset)
    assert asset.location_id == loc_b.id
    assert asset.custodian_id is None
    assert asset.status == AssetStatus.AVAILABLE
    assert movement.destination_custodian_id is None


def test_web_form_blocked_movement_shows_error_banner(client, db_session):
    """Feature 005 — O formulário web exibe o banner de erro quando a matriz
    bloqueia a movimentação (POST → redirect 303 → GET com ?error= renderiza alerta)."""
    loc, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00518", "US7a", "5019")

    resp = client.post(
        "/movements/new",
        data={
            "asset_id": str(asset.id),
            "movement_type": "TRANSFERENCIA_LOCAL",
            "destination_location_id": str(loc.id),      # mesmo local
            "destination_custodian_id": str(cust.id),    # mesmo responsável
            "reason": "Tentativa sem alteração efetiva via formulário",
            "operator_name": "Auditor",
        },
        follow_redirects=True,   # segue o 303 → GET /movements/new?error=...
    )

    assert resp.status_code == 200
    body = resp.text
    assert "alert-danger" in body                      # banner renderizado
    assert "Nenhuma altera&ccedil;&atilde;o efetiva" in body or "Nenhuma alteração efetiva" in body
    assert f'value="{asset.id}" selected' in body       # bem repovoado
    assert 'value="TRANSFERENCIA_LOCAL" checked' in body  # tipo repovoado


def test_api_movements_returns_400_with_matrix_message(client, db_session):
    """US1-US4 (T047) — As validações da matriz chegam à API REST como HTTP 400
    com a mensagem exata, pelo mecanismo genérico existente."""
    loc, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00517", "US6a", "5018")

    resp = client.post("/api/v1/movements", json={
        "asset_id": asset.id,
        "movement_type": "TRANSFERENCIA_LOCAL",
        "destination_location_id": loc.id,      # mesmo local
        "destination_custodian_id": cust.id,    # mesmo responsável
        "reason": "Operação sem alteração efetiva via API",
        "operator_name": "Auditor",
    })

    assert resp.status_code == 400
    assert "Nenhuma alteração efetiva" in resp.json()["detail"]


def test_transfer_without_destination_location_is_rejected(db_session):
    """US3 (T024) — Transferência exige local de destino válido (VAL-005)."""
    loc, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00509", "US3c", "5009")

    with pytest.raises(ValueError, match="obrigatório selecionar o local de destino"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            # sem destination_location_id
            reason="Transferência sem local",
            operator_name="Auditor"
        ))


def test_allocation_same_custodian_new_location_is_rejected(db_session):
    """US3 (T025) — Alocação com o mesmo responsável e só mudança de local deve ser rejeitada (VAL-004)."""
    loc_a, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00510", "US3d", "5010")
    loc_b = LocationService.create(db_session, LocationCreate(
        name="Local US3d-destino", branch="Filial", department="Dep US3d"
    ))

    with pytest.raises(ValueError, match="já é o responsável atual"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.ALLOCATION,
            destination_location_id=loc_b.id,     # local diferente + mesmo responsável → é transferência
            destination_custodian_id=cust.id,     # mesmo responsável
            reason="Mudança de local registrada como alocação",
            operator_name="Auditor"
        ))


# ---- US4: Mudança simultânea de local e responsável ----

def test_allocation_new_location_new_custodian_atomic(db_session):
    """US4 (T029/T030/T031) — Alocação com local e responsável novos: atualização atômica, termo, EM_USO."""
    loc_a, cust_old, asset = _setup_bem_com_responsavel(db_session, "PAT-00511", "US4a", "5011")
    loc_b = LocationService.create(db_session, LocationCreate(
        name="Local US4b", branch="Filial Santos", department="Operações"
    ))
    cust_new = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-5012",
        name="Fernanda Rocha",
        email="fernanda.r@empresa.com",
        role="Vendedora",
        department="Operações"
    ))

    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.ALLOCATION,
        destination_location_id=loc_b.id,
        destination_custodian_id=cust_new.id,
        reason="Entrega a nova colaboradora em outra filial",
        operator_name="Gestor"
    ))

    db_session.refresh(asset)
    assert asset.location_id == loc_b.id
    assert asset.custodian_id == cust_new.id
    assert asset.status == AssetStatus.IN_USE
    assert movement.term_code is not None
    assert movement.destination_location_id == loc_b.id
    assert movement.destination_custodian_id == cust_new.id


def test_allocation_from_stock_to_custodian_in_new_location(db_session):
    """US4 (T029 variante estoque→colaborador) — Saída do estoque com mudança de local: Alocação, termo, EM_USO."""
    loc_stock = LocationService.create(db_session, LocationCreate(
        name="Estoque Geral", branch="Matriz", department="Estoque"
    ))
    loc_dest = LocationService.create(db_session, LocationCreate(
        name="Filial Curitiba", branch="Filial", department="Vendas"
    ))
    cust = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-5013",
        name="Marcos Dias",
        email="marcos@empresa.com",
        role="Vendedor",
        department="Vendas"
    ))
    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-00512",
        name="Impressora Multifuncional",
        category=AssetCategory.EQUIPMENT,
        initial_location_id=loc_stock.id   # estoque, sem custodiante
    ))

    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.ALLOCATION,
        destination_location_id=loc_dest.id,
        destination_custodian_id=cust.id,
        reason="Entrega de impressora a colaborador na filial",
        operator_name="Gestor"
    ))

    db_session.refresh(asset)
    assert asset.location_id == loc_dest.id
    assert asset.custodian_id == cust.id
    assert asset.status == AssetStatus.IN_USE
    assert movement.term_code is not None


def test_transfer_with_new_custodian_is_rejected(db_session):
    """US4 (T032) — TRANSFER com novo colaborador (mudança de custódia) deve ser rejeitada (VAL-007)."""
    loc_a, cust_old, asset = _setup_bem_com_responsavel(db_session, "PAT-00513", "US4c", "5014")
    loc_b = LocationService.create(db_session, LocationCreate(
        name="Local US4c-destino", branch="Filial", department="Dep US4c"
    ))
    cust_new = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-5015",
        name="Paula Neves",
        email="paula@empresa.com",
        role="Analista",
        department="Dep US4c"
    ))

    with pytest.raises(ValueError, match="deve ser registrada como Alocação"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            destination_location_id=loc_b.id,
            destination_custodian_id=cust_new.id,   # novo responsável → é entrega → Alocação
            reason="Entrega registrada como transferência",
            operator_name="Auditor"
        ))


# ---- US5: Estoque e regras específicas ----

def test_return_stock_redundant_is_blocked(db_session):
    """US5 (T039) — Devolução redundante: bem já disponível no estoque, sem responsável e sem mudança de local."""
    loc = LocationService.create(db_session, LocationCreate(
        name="Almoxarifado US5", branch="Matriz", department="Estoque"
    ))
    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-00514",
        name="Teclado USB",
        category=AssetCategory.EQUIPMENT,
        initial_location_id=loc.id   # estoque, sem custodiante
    ))
    movements_before = db_session.query(Movement).filter(Movement.asset_id == asset.id).count()

    with pytest.raises(ValueError, match="já se encontra no estoque"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.RETURN_STOCK,
            destination_location_id=loc.id,   # mesmo local
            reason="Devolução redundante",
            operator_name="Auditor"
        ))

    assert db_session.query(Movement).filter(Movement.asset_id == asset.id).count() == movements_before


def test_return_stock_from_in_use_succeeds(db_session):
    """US5 (T037/T038) — Devolução válida: remove responsável, status DISPONIVEL, termo de devolução."""
    loc, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00515", "US5b", "5016")

    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.RETURN_STOCK,
        destination_location_id=loc.id,
        reason="Devolução por troca de equipamento",
        operator_name="Gestor"
    ))

    db_session.refresh(asset)
    assert asset.custodian_id is None
    assert asset.status == AssetStatus.AVAILABLE
    assert movement.term_code is not None                      # termo de devolução
    assert movement.destination_custodian_id is None
    assert movement.destination_custodian_name == "Almoxarifado / Estoque"


def test_maintenance_and_writeoff_flows_unaffected(db_session):
    """US5 (T042) — Manutenção e baixa preservam suas regras próprias fora da matriz."""
    loc, cust, asset = _setup_bem_com_responsavel(db_session, "PAT-00516", "US5c", "5017")

    # Envio para manutenção não é bloqueado pela matriz
    mv_maint = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.MAINTENANCE_OUT,
        reason="Envio para assistência técnica",
        operator_name="TI"
    ))
    db_session.refresh(asset)
    assert asset.status == AssetStatus.IN_MAINTENANCE
    assert asset.custodian_id == cust.id   # manutenção não altera custódia

    # Retorno de manutenção restaura disponibilidade (sem custodiante → AVAILABLE)
    mv_ret = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.MAINTENANCE_IN,
        reason="Retorno da assistência técnica",
        operator_name="TI"
    ))
    db_session.refresh(asset)
    assert asset.status == AssetStatus.AVAILABLE

    # Baixa/descarte preserva seu fluxo terminal
    mv_wo = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.WRITE_OFF,
        reason="Equipamento inservível após vistoria",
        operator_name="Gestor"
    ))
    db_session.refresh(asset)
    assert asset.status == AssetStatus.WRITTEN_OFF
    assert asset.custodian_id is None

    # E bem baixado permanece bloqueado (VAL-001, regra existente)
    with pytest.raises(ValueError, match="já foi baixado"):
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            destination_location_id=loc.id,
            reason="Tentativa após baixa",
            operator_name="Auditor"
        ))
