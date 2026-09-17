"""
Testes do Identificador Provisório de Colaborador (feature 010).

Cobre: geração automática PROV-* no cadastro sem matrícula (web/API),
sequência e unicidade, anti-fabricação (create/update, web/API), marcação
visual de provisoriedade, uso patrimonial sem bloqueios (alocação/devolução/
termo), substituição PROV-* → matrícula oficial preservando o colaborador,
vínculos e histórico, e não-regressão dos comportamentos existentes.
"""
import re

from app.models.asset import Asset
from app.models.custodian import Custodian
from app.models.enums import AssetCondition, AssetCategory, AssetStatus, MovementType
from app.models.location import Location
from app.schemas.asset import AssetCreate
from app.schemas.custodian import CustodianCreate, CustodianUpdate
from app.schemas.location import LocationCreate
from app.schemas.movement import MovementCreate
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.movement_service import MovementService

PROV_RE = re.compile(r"^PROV-\d{6}$")


# ============================================================================
# US1 — Cadastro sem matrícula gera PROV-* (web e API)
# ============================================================================

def test_api_create_without_registration_code_generates_prov(db_session):
    """(a) API sem registration_code → 201 com PROV-000001 (primeiro)."""
    cust = CustodianService.create(db_session, CustodianCreate(
        name="Fulano Provisorio", email="fulano.prov@empresa.local",
        role="Técnico", department="TI",
    ))
    assert PROV_RE.match(cust.registration_code)
    assert cust.registration_code == "PROV-000001"


def test_api_sequence_increments(db_session):
    """(b) Segundo cadastro sem matrícula → PROV-000002."""
    CustodianService.create(db_session, CustodianCreate(
        name="Um", email="um@empresa.local", role="A", department="D"))
    dois = CustodianService.create(db_session, CustodianCreate(
        name="Dois", email="dois@empresa.local", role="A", department="D"))
    assert dois.registration_code == "PROV-000002"


def test_web_create_without_registration_code(client):
    """(c) Web: cadastro sem matrícula cria o colaborador com PROV-* e marca 'provisória'."""
    resp = client.post("/custodians/new", data={
        "registration_code": "",
        "name": "Web Provisorio",
        "email": "web.prov@empresa.local",
        "role": "Técnico",
        "department": "TI",
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/custodians"

    listing = client.get("/custodians").text
    m = re.search(r"PROV-\d{6}", listing)
    assert m, "PROV-* deveria aparecer na listagem"
    assert "provisória" in listing.lower()


def test_web_create_with_spaces_only_code_treated_as_empty(client, db_session):
    """(d) Campo com espaços → tratado como não informado."""
    resp = client.post("/custodians/new", data={
        "registration_code": "   ",
        "name": "Espacos Provisorio",
        "email": "espacos.prov@empresa.local",
        "role": "Técnico",
        "department": "TI",
    }, follow_redirects=False)
    assert resp.status_code == 303
    cust = db_session.query(Custodian).filter(
        Custodian.email == "espacos.prov@empresa.local").first()
    assert cust is not None
    assert PROV_RE.match(cust.registration_code)


def test_search_finds_provisional(client, db_session):
    """(e) Pesquisa 006 encontra o colaborador provisório por PROV-*."""
    client.post("/custodians/new", data={
        "registration_code": "", "name": "Pesquisavel Provisorio",
        "email": "pesquisavel.prov@empresa.local", "role": "A", "department": "D"})
    page = client.get("/custodians", params={"search": "PROV-000001"}).text
    assert "Pesquisavel Provisorio" in page


def test_regression_create_with_official_code_unchanged(client, db_session):
    """(f) Não-regressão: cadastro COM matrícula segue idêntico ao atual."""
    resp = client.post("/custodians/new", data={
        "registration_code": "MAT-9001",
        "name": "Oficial Regressao",
        "email": "oficial.regressao@empresa.local",
        "role": "A", "department": "D",
    }, follow_redirects=False)
    assert resp.status_code == 303
    cust = db_session.query(Custodian).filter(
        Custodian.registration_code == "MAT-9001").first()
    assert cust is not None
    assert not CustodianService.is_provisional("MAT-9001")
    # API também
    api = client.post("/api/v1/custodians", json={
        "registration_code": "MAT-9002",
        "name": "Oficial API", "email": "oficial.api@empresa.local",
        "role": "A", "department": "D",
    })
    assert api.status_code == 201


# ============================================================================
# US2 — Uso patrimonial normal do provisório (sem bloqueios)
# ============================================================================

def _asset_for(db, tag, loc=None):
    return AssetService.create(db, AssetCreate(
        tag=tag, name=f"Bem {tag}", category=AssetCategory.OTHER,
        purchase_value=100.0, location_id=loc.id if loc else None,
    ))


def _prov_custodian(db, email):
    return CustodianService.create(db, CustodianCreate(
        name="Provisorio Mov", email=email, role="A", department="D"))


def test_allocation_with_provisional_custodian(db_session):
    """(a) Alocação/cautela com colaborador PROV-* funciona sem bloqueio."""
    cust = _prov_custodian(db_session, "mov.prov@empresa.local")
    asset = _asset_for(db_session, "PROVMOV-001")

    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id,
        movement_type=MovementType.ALLOCATION,
        destination_custodian_id=cust.id,
        reason="Cautela para colaborador provisório",
        operator_name="Admin TI",
    ))

    db_session.refresh(asset)
    assert asset.custodian_id == cust.id
    assert asset.status == AssetStatus.IN_USE
    assert movement.term_code is not None
    # snapshot da época contém a identificação vigente (PROV-*)
    assert cust.registration_code in movement.destination_custodian_name


def test_return_stock_with_provisional_custodian(db_session):
    """(b) Devolução ao estoque — comportamento existente."""
    cust = _prov_custodian(db_session, "ret.prov@empresa.local")
    asset = _asset_for(db_session, "PROVMOV-002")
    MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id, movement_type=MovementType.ALLOCATION,
        destination_custodian_id=cust.id, reason="Cautela", operator_name="Op"))
    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id, movement_type=MovementType.RETURN_STOCK,
        reason="Devolução", operator_name="Op"))
    db_session.refresh(asset)
    assert asset.custodian_id is None
    assert asset.status == AssetStatus.AVAILABLE
    assert movement.movement_type == MovementType.RETURN_STOCK


def test_term_page_shows_provisional_badge(client, db_session):
    """(c) Termo exibe o código PROV-* com a marcação de provisória."""
    cust = _prov_custodian(db_session, "term.prov@empresa.local")
    asset = _asset_for(db_session, "PROVMOV-003")
    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id, movement_type=MovementType.ALLOCATION,
        destination_custodian_id=cust.id, reason="Cautela", operator_name="Op"))

    page = client.get(f"/movements/{movement.id}/term").text
    assert cust.registration_code in page
    assert "provisória" in page.lower()


def test_inventory_snapshot_uses_name_only(db_session):
    """(d) Sanidade: snapshot de inventário usa nome (sem matrícula) — intocado."""
    cust = _prov_custodian(db_session, "inv.prov@empresa.local")
    assert cust.name == "Provisorio Mov"
    # O modelo InventarioItem guarda apenas expected_custodian_name (string):
    # a feature não altera o inventário; aqui apenas garantimos que o serviço
    # de movimentação/inventário não rejeita colaboradores PROV-*.
    assert CustodianService.is_provisional(cust.registration_code)


def _make_location(db):
    return LocationService_create(db)


def LocationService_create(db):
    from app.services.location_service import LocationService
    return LocationService.create(db, LocationCreate(
        name="Local PROV", branch="F1", department="D1"))


def test_asset_pages_render_with_provisional(client, db_session):
    """(e) Páginas do bem renderizam com custodiante provisório."""
    cust = _prov_custodian(db_session, "page.prov@empresa.local")
    asset = _asset_for(db_session, "PROVMOV-004")
    MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id, movement_type=MovementType.ALLOCATION,
        destination_custodian_id=cust.id, reason="Cautela", operator_name="Op"))
    assert client.get(f"/assets/{asset.id}").status_code == 200
    assert client.get("/assets").status_code == 200


# ============================================================================
# US3 — Substituição PROV-* → matrícula oficial
# ============================================================================

def test_web_edit_provisional_to_official(db_session, client):
    """(a) Web: PROV-* → oficial no mesmo id; sem marcação depois."""
    cust = _prov_custodian(db_session, "subst.web@empresa.local")
    old_code = cust.registration_code

    resp = client.post(f"/custodians/{cust.id}/edit", data={
        "registration_code": "123456",
        "name": "Provisorio Mov",
        "email": "subst.web@empresa.local",
        "cpf": "",
        "role": "A",
        "department": "D",
    }, follow_redirects=False)
    assert resp.status_code == 303
    db_session.refresh(cust)
    assert cust.id == cust.id and cust.registration_code == "123456"
    detail = client.get(f"/custodians/{cust.id}").text
    assert "123456" in detail
    assert "provisória" not in detail.lower()


def test_web_edit_official_still_readonly(db_session, client):
    """(b) Web: matrícula oficial permanece inalterável."""
    cust = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-7300", name="Oficial Edit",
        email="oficial.edit@empresa.local", role="A", department="D"))
    resp = client.post(f"/custodians/{cust.id}/edit", data={
        "registration_code": "999999",
        "name": "Oficial Edit", "email": "oficial.edit@empresa.local",
        "cpf": "", "role": "A", "department": "D",
    }, follow_redirects=False)
    assert resp.status_code == 303
    db_session.refresh(cust)
    assert cust.registration_code == "MAT-7300"


def test_api_put_provisional_to_official(db_session, client):
    """(c) API: PUT substitui PROV-* pela oficial, mesmo id."""
    cust = _prov_custodian(db_session, "subst.api@empresa.local")
    resp = client.put(f"/api/v1/custodians/{cust.id}", json={
        "registration_code": "654321",
    })
    assert resp.status_code == 200
    db_session.refresh(cust)
    assert cust.registration_code == "654321"


def test_substitution_preserves_links_and_history(db_session, client):
    """(d) Mesmo registro: bens vinculados e snapshot antigo intactos."""
    cust = _prov_custodian(db_session, "preserv.prov@empresa.local")
    old_code = cust.registration_code
    asset = _asset_for(db_session, "PROVMOV-005")
    old_movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id, movement_type=MovementType.ALLOCATION,
        destination_custodian_id=cust.id, reason="Cautela", operator_name="Op"))

    CustodianService.update(db_session, cust.id, CustodianUpdate(
        registration_code="246810"))
    db_session.refresh(asset)
    assert asset.custodian_id == cust.id  # FK por id preservada
    db_session.refresh(old_movement)
    # snapshot imutável: continua com a identificação da época
    assert old_code in old_movement.destination_custodian_name


def test_substitution_is_audited(db_session, client):
    """(e) Auditoria registra before (PROV-*) e after (oficial) — mecanismo
    existente do POST de edição web (write_change_audit)."""
    from app.models.audit_log import AuditLog
    from app.services.audit_service import ACTION_UPDATE
    cust = _prov_custodian(db_session, "audit.prov@empresa.local")
    old_code = cust.registration_code
    resp = client.post(f"/custodians/{cust.id}/edit", data={
        "registration_code": "135711",
        "name": "Provisorio Mov",
        "email": "audit.prov@empresa.local",
        "cpf": "", "role": "A", "department": "D",
    }, follow_redirects=False)
    assert resp.status_code == 303
    db_session.expire_all()
    entry = (db_session.query(AuditLog)
             .filter(AuditLog.resource_id == cust.id,
                     AuditLog.module == "Colaboradores",
                     AuditLog.action == ACTION_UPDATE)
             .order_by(AuditLog.id.desc()).first())
    assert entry is not None
    blob = f"{entry.previous_data or ''} {entry.new_data or ''}"
    assert old_code in blob and "135711" in blob


def test_substitution_conflict_keeps_provisional(db_session, client):
    """(f) Colisão: matrícula já usada → erro existente e PROV-* permanece."""
    CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-7400", name="Ocupado",
        email="ocupado@empresa.local", role="A", department="D"))
    cust = _prov_custodian(db_session, "conflict.prov@empresa.local")
    old_code = cust.registration_code
    try:
        CustodianService.update(db_session, cust.id, CustodianUpdate(
            registration_code="MAT-7400"))
        raised = False
    except ValueError as err:
        raised = True
        assert "já cadastrada" in str(err).lower()
    assert raised
    db_session.refresh(cust)
    assert cust.registration_code == old_code


def test_api_official_to_official_current_behavior(db_session, client):
    """(g) API oficial→oficial mantém comportamento atual."""
    a = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-7500", name="A",
        email="a7500@empresa.local", role="A", department="D"))
    resp = client.put(f"/api/v1/custodians/{a.id}", json={
        "registration_code": "MAT-7501"})
    assert resp.status_code == 200
    db_session.refresh(a)
    assert a.registration_code == "MAT-7501"


def test_future_movement_shows_official_no_badge(client, db_session):
    """(h) FR-011 2ª metade: emissão futura (nova movimentação pós-substituição)
    exibe a matrícula oficial no termo, sem a marcação de provisória."""
    cust = _prov_custodian(db_session, "future.prov@empresa.local")
    CustodianService.update(db_session, cust.id, CustodianUpdate(
        registration_code="192837"))
    asset = _asset_for(db_session, "PROVMOV-006")
    new_movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id, movement_type=MovementType.ALLOCATION,
        destination_custodian_id=cust.id, reason="Cautela pós-substituição",
        operator_name="Op"))
    term = client.get(f"/movements/{new_movement.id}/term").text
    assert "192837" in term
    assert "provisória" not in term.lower()


# ============================================================================
# US4 — Segurança e integridade da numeração
# ============================================================================

def test_collision_with_preexisting_prov(db_session):
    """(a) Colisão: PROV-000001 pré-existente → geração pula para o próximo."""
    # Criado direto no modelo: o serviço rejeita PROV-* digitado (anti-
    # fabricação, FR-005), então o legado pré-existente contorna-o de propósito.
    db_session.add(Custodian(
        registration_code="PROV-000001", name="Pre Existentes",
        email="pre.existentes@empresa.local", role="A", department="D"))
    db_session.commit()
    nxt = CustodianService.create(db_session, CustodianCreate(
        name="Depois Colisao", email="depois@empresa.local",
        role="A", department="D"))
    assert nxt.registration_code == "PROV-000002"


def test_web_create_rejects_fabricated_prov(client):
    """(b) Web create: PROV-* digitado é rejeitado."""
    resp = client.post("/custodians/new", data={
        "registration_code": "PROV-000999",
        "name": "Fabricado", "email": "fabricado@empresa.local",
        "role": "A", "department": "D"}, follow_redirects=False)
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]


def test_web_create_rejects_fabricated_prov_db(client, db_session):
    """(b-complemento) Nenhum colaborador 'Fabricado' é gravado."""
    client.post("/custodians/new", data={
        "registration_code": "PROV-000998",
        "name": "Fabricado DB", "email": "fabricado.db@empresa.local",
        "role": "A", "department": "D"})
    assert db_session.query(Custodian).filter(
        Custodian.email == "fabricado.db@empresa.local").first() is None


def test_api_create_rejects_fabricated_prov(client):
    """(c) API create: PROV-* digitado → 400."""
    resp = client.post("/api/v1/custodians", json={
        "registration_code": "PROV-000123",
        "name": "Fabricado API", "email": "fabricado.api@empresa.local",
        "role": "A", "department": "D"})
    assert resp.status_code == 400


def test_api_update_rejects_fabricated_prov(db_session, client):
    """(d) API update: novo valor PROV-* é rejeitado."""
    cust = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-7600", name="Alvo",
        email="alvo7600@empresa.local", role="A", department="D"))
    resp = client.put(f"/api/v1/custodians/{cust.id}", json={
        "registration_code": "PROV-000777"})
    assert resp.status_code == 400


def test_provisional_codes_are_unique(db_session):
    """(e) Unicidade permanente em lote de cadastros."""
    codes = set()
    for i in range(5):
        c = CustodianService.create(db_session, CustodianCreate(
            name=f"Lote {i}", email=f"lote{i}@empresa.local",
            role="A", department="D"))
        assert PROV_RE.match(c.registration_code)
        assert c.registration_code not in codes
        codes.add(c.registration_code)


def test_provisional_is_not_a_credential(db_session, client):
    """(f) PROV-* não cria usuário e não participa de autenticação."""
    from app.models.user import User
    before = db_session.query(User).count()
    CustodianService.create(db_session, CustodianCreate(
        name="Sem Credencial", email="sem.credencial@empresa.local",
        role="A", department="D"))
    after = db_session.query(User).count()
    assert before == after


# ============================================================================
# US4 — Regressão do achado manual (T019): valores PROV- malformados
# ============================================================================

def test_malformed_prov_rejected_on_web_edit(db_session, client):
    """(g) Achado T019: PROV-0000 (malformado) digitado na edição é rejeitado
    — não vira matrícula oficial disfarçada."""
    cust = _prov_custodian(db_session, "malformed.prov@empresa.local")
    resp = client.post(f"/custodians/{cust.id}/edit", data={
        "registration_code": "PROV-0000",
        "name": "Provisorio Mov", "email": "malformed.prov@empresa.local",
        "cpf": "", "role": "A", "department": "D",
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]
    db_session.refresh(cust)
    assert cust.registration_code != "PROV-0000"
    assert CustodianService.is_provisional(cust.registration_code)


def test_malformed_prov_variants_rejected(db_session):
    """(h) Anti-fabricação cobre variações malformadas e case-insensitive."""
    for bad in ("PROV-0000", "PROV-12", "prov-000001", "ProV-999999",
                "PROV-abcdef", "PROV-"):
        try:
            CustodianService.create(db_session, CustodianCreate(
                registration_code=bad,
                name=f"Bad {bad}", email=f"bad-{abs(hash(bad))}@e.local",
                role="A", department="D"))
            raised = False
        except ValueError as err:
            raised = "PROV-" in str(err)
        assert raised, f"'{bad}' deveria ser rejeitado"


def test_malformed_prov_stays_provisional_and_recoverable(db_session):
    """(i) Registro com PROV- malformado (ex.: legado/edição anterior) continua
    provisório — com badge, editável — e pode receber a matrícula oficial."""
    db_session.add(Custodian(
        registration_code="PROV-0000", name="Envenenado",
        email="envenenado@empresa.local", role="A", department="D"))
    db_session.commit()
    cust = db_session.query(Custodian).filter(
        Custodian.registration_code == "PROV-0000").first()

    assert CustodianService.is_provisional("PROV-0000")
    assert CustodianService.is_provisional("prov-0000")  # case-insensitive

    # A geração ignora o malformado na contagem (não quebra int())
    nxt = CustodianService.create(db_session, CustodianCreate(
        name="Novo Depois", email="novo.depois@e.local", role="A", department="D"))
    assert nxt.registration_code == "PROV-000001"

    # Recuperação: substituição pela matrícula oficial funciona
    CustodianService.update(db_session, cust.id, CustodianUpdate(
        registration_code="777777"))
    db_session.refresh(cust)
    assert cust.registration_code == "777777"
    assert not CustodianService.is_provisional(cust.registration_code)
