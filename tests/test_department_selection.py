"""Feature 012 — Seleção de Departamento/Setor no Cadastro de Colaborador.

Testes organizados por user story da spec:
- Fase 2 (T003): DepartmentService — fonte oficial (RV-1) e validação/canonização (RV-2..RV-4)
- US1: cadastro com seleção oficial (AC-01, AC-02, AC-05; Cenários 1 e 4)
- US2: validação server-side (AC-03, AC-04; Cenários 2 e 3) + caracterização do caminho legado (RV-5)
- US3: edição com a mesma lista oficial (AC-06; Cenário 5) + exceção do valor vigente (FR-014/I2-b)
- US4: matrícula PROV-* (AC-07), histórico intocado (AC-08), Localização/Cargo intocados (AC-09/FR-011), existentes preservados (FR-014)

Regras do data-model (RV-1..RV-7): a fonte oficial é a lista derivada ao vivo dos
valores distintos de `locations.department` (ZERO DDL); a validação estrita aplica-se
somente ao caminho do formulário (marcador `department_source=official`).

Fixtures `client` (sessão autenticada) e `db_session` vêm de tests/conftest.py.
Nenhum teste existente é editado (Constitution VIII).
"""
import re

import pytest

from app.models.custodian import Custodian
from app.schemas.custodian import CustodianCreate
from app.schemas.location import LocationCreate
from app.services.custodian_service import CustodianService
from app.services.department_service import DepartmentService
from app.services.location_service import LocationService


# ============================================================================
# Helpers de massa (padrão de tests/test_custodians_search.py)
# ============================================================================

def _criar_local(db, nome, departamento, branch="Matriz"):
    return LocationService.create(db, LocationCreate(
        name=nome, branch=branch, department=departamento))


def _criar_colaborador(db, matricula, nome, email, departamento, role="Analista"):
    return CustodianService.create(db, CustodianCreate(
        registration_code=matricula,
        name=nome,
        email=email,
        role=role,
        department=departamento,
    ))


def _dados_form(**overrides):
    """Payload do formulário da nova UI (sempre envia o marcador oficial)."""
    dados = {
        "registration_code": "MAT-0120",
        "name": "Colaborador Oficial",
        "email": "oficial.012@empresa.local",
        "role": "Analista",
        "department": "Setor de Suporte",
        "department_source": "official",
    }
    dados.update(overrides)
    return dados


# ============================================================================
# Fase 2 (T003) — DepartmentService: fonte oficial e validação (RV-1..RV-4)
# ============================================================================

def test_list_official_returns_distinct_sorted_case_insensitive(db_session):
    """RV-1 — distintos de locations.department, ordenação case-insensitive."""
    _criar_local(db_session, "Local Z", "Zebra")
    _criar_local(db_session, "Local A", "apple")
    _criar_local(db_session, "Local B", "Banana")
    _criar_local(db_session, "Local Duplicado", "apple")  # repetido → uma ocorrência

    assert DepartmentService.list_official(db_session) == ["apple", "Banana", "Zebra"]


def test_list_official_excludes_null_and_blank(db_session):
    """RV-1 — sem nulos e sem valores só de espaços."""
    _criar_local(db_session, "Local Em Branco", "   ")
    _criar_local(db_session, "Local Ok", "TI")

    assert DepartmentService.list_official(db_session) == ["TI"]


def test_list_official_empty_without_locations(db_session):
    """RV-1 — banco sem locais → lista vazia (sem seed)."""
    assert DepartmentService.list_official(db_session) == []


def test_ensure_official_returns_canonical_form(db_session):
    """RV-2 — casamento case-insensitive/trim devolve a forma canônica oficial."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")

    assert DepartmentService.ensure_official(db_session, "SETOR DE SUPORTE") == "Setor de Suporte"
    assert DepartmentService.ensure_official(db_session, "  setor de suporte  ") == "Setor de Suporte"
    assert DepartmentService.ensure_official(db_session, "Setor de Suporte") == "Setor de Suporte"


def test_ensure_official_canonical_from_official_written_uppercase(db_session):
    """RV-2 — oficial cadastrado em maiúsculas: variação de caixa grava a forma vigente."""
    _criar_local(db_session, "Local Caixa", "SUPORTE")

    assert DepartmentService.ensure_official(db_session, "suporte") == "SUPORTE"


def test_ensure_official_empty_raises_required_error(db_session):
    """RV-4 — vazio/só espaços → erro de obrigatoriedade (FR-003/AC-03)."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")

    with pytest.raises(ValueError, match="obrigatório"):
        DepartmentService.ensure_official(db_session, "")
    with pytest.raises(ValueError, match="obrigatório"):
        DepartmentService.ensure_official(db_session, "   ")


def test_ensure_official_unknown_value_raises_invalid_error(db_session):
    """RV-3 — sem correspondência → erro de seleção inválida (FR-004/AC-04)."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")

    with pytest.raises(ValueError, match="inválido"):
        DepartmentService.ensure_official(db_session, "Setor Inexistente XYZ")


def test_ensure_official_case_ambiguity_raises_error(db_session):
    """RV-3 — dois oficiais diferindo só por caixa: ambiguidade real → rejeita."""
    _criar_local(db_session, "Local Um", "Suporte")
    _criar_local(db_session, "Local Dois", "SUPORTE")

    with pytest.raises(ValueError, match="inválido"):
        DepartmentService.ensure_official(db_session, "suporte")


def test_ensure_official_exact_match_wins_over_ambiguity(db_session):
    """RV-2 — submissão idêntica (exata) a um oficial é aceita mesmo com ambiguidade alheia."""
    _criar_local(db_session, "Local Um", "Suporte")
    _criar_local(db_session, "Local Dois", "SUPORTE")

    assert DepartmentService.ensure_official(db_session, " Suporte ") == "Suporte"


# ============================================================================
# US1 (T007/T008) — Cadastrar colaborador selecionando um oficial
# (AC-01, AC-02, AC-05; Cenários 1 e 4; RV-1 derivação ao vivo)
# ============================================================================

def test_form_new_renders_official_selection(db_session, client):
    """US1 (AC-01/FR-001) — GET /custodians/new: marcador oculto, campo de
    seleção (dropdown <select>) e cada oficial vigente como <option>."""
    _criar_local(db_session, "Local DAF", "IPMJP - DAF")
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")

    body = client.get("/custodians/new").text

    assert 'name="department_source"' in body and 'value="official"' in body
    assert '<select name="department"' in body
    assert 'id="department-options"' not in body      # sem datalist/pesquisa
    assert "IPMJP - DAF" in body            # opções vêm do contexto (banco)
    assert "Setor de Suporte" in body
    assert 'name="department"' in body      # campo segue gravando em department


def test_form_new_options_come_from_database_not_hardcoded(db_session, client):
    """US1 (AC-01) — sem locais, nenhuma opção de departamento é renderizada
    (lista 100% derivada do banco; nada fixo no HTML)."""
    body = client.get("/custodians/new").text

    assert 'name="department_source"' in body
    assert "Engenharia de Software" not in body  # placeholder antigo removido


def test_web_create_with_marker_saves_canonical(client, db_session):
    """US1 (Cenário 1/AC-05/RV-2) — POST com marcador + variação de caixa de um
    oficial → 303 para /custodians e gravação da forma CANÔNICA."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")

    resp = client.post("/custodians/new", data=_dados_form(
        department="SETOR DE SUPORTE", email="caixa.012@empresa.local"),
        follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/custodians"
    gravado = db_session.query(Custodian).filter(
        Custodian.email == "caixa.012@empresa.local").first()
    assert gravado is not None
    assert gravado.department == "Setor de Suporte"   # canônico, não o digitado


def test_web_create_with_marker_exact_official(client, db_session):
    """US1 (AC-05) — submissão exata de um oficial grava o próprio valor."""
    _criar_local(db_session, "Local DAF", "IPMJP - DAF")

    resp = client.post("/custodians/new", data=_dados_form(
        department="IPMJP - DAF", email="daf.012@empresa.local"),
        follow_redirects=False)

    assert resp.status_code == 303
    gravado = db_session.query(Custodian).filter(
        Custodian.email == "daf.012@empresa.local").first()
    assert gravado.department == "IPMJP - DAF"


def test_official_list_reflects_location_changes_live(db_session, client):
    """US1 (RV-1/R8) — local novo cadastrado aparece na lista no próximo render
    (derivação ao vivo, sem seed)."""
    _criar_local(db_session, "Local Inicial", "Setor Inicial")
    assert "Setor Novo" not in client.get("/custodians/new").text

    _criar_local(db_session, "Local Novo", "Setor Novo")

    body = client.get("/custodians/new").text
    assert "Setor Inicial" in body
    assert "Setor Novo" in body


# ============================================================================
# US2 (T013–T015) — Validação no backend (AC-03/AC-04; Cenários 2 e 3) +
# caracterização do caminho legado (RV-5/api-contract §3)
# ============================================================================

def test_web_create_empty_department_rejected_server_side(client, db_session):
    """US2 (Cenário 2/AC-03/RV-4) — vazio com marcador → redirect com erro
    'obrigatório' e NENHUM colaborador gravado (independe do navegador)."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")

    resp = client.post("/custodians/new", data=_dados_form(
        department="   ", email="vazio.012@empresa.local"),
        follow_redirects=False)

    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]
    assert "obrigat%C3%B3rio" in resp.headers["location"]
    assert db_session.query(Custodian).filter(
        Custodian.email == "vazio.012@empresa.local").first() is None


def test_web_create_missing_department_rejected_server_side(client, db_session):
    """US2 (AC-03/RV-4) — campo ausente do payload com marcador: a requisição é
    rejeitada server-side (validação FastAPI 422; nada gravado). O caso 'vazio'
    submetido segue pelo guard do handler (redirect 'obrigatório')."""
    dados = _dados_form(email="ausente.012@empresa.local")
    del dados["department"]

    resp = client.post("/custodians/new", data=dados, follow_redirects=False)

    assert resp.status_code == 422
    assert db_session.query(Custodian).filter(
        Custodian.email == "ausente.012@empresa.local").first() is None


def test_web_create_unknown_department_rejected_server_side(client, db_session):
    """US2 (Cenário 3/AC-04/RV-3) — valor fora da lista com marcador → redirect
    com erro 'inválido' e NENHUM colaborador gravado."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")

    resp = client.post("/custodians/new", data=_dados_form(
        department="Setor Inexistente XYZ", email="invalido.012@empresa.local"),
        follow_redirects=False)

    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]
    assert "inv%C3%A1lido" in resp.headers["location"]
    assert db_session.query(Custodian).filter(
        Custodian.email == "invalido.012@empresa.local").first() is None


def test_legacy_web_without_marker_accepts_free_text(client, db_session):
    """US2 (RV-5/FR-012) — POST web SEM marcador: comportamento atual integral
    (texto livre gravado; teste de caracterização da não-mudança)."""
    dados = _dados_form(department="Texto Livre Qualquer", email="legado.012@empresa.local")
    del dados["department_source"]

    resp = client.post("/custodians/new", data=dados, follow_redirects=False)

    assert resp.status_code == 303
    gravado = db_session.query(Custodian).filter(
        Custodian.email == "legado.012@empresa.local").first()
    assert gravado is not None
    assert gravado.department == "Texto Livre Qualquer"


def test_legacy_api_accepts_free_text_unchanged(client, db_session):
    """US2 (RV-5/api-contract §3/FR-012) — API REST: texto livre → 201,
    contrato inalterado (caracterização)."""
    resp = client.post("/api/v1/custodians", json={
        "registration_code": "MAT-0121",
        "name": "API Legado",
        "email": "api.legado.012@empresa.local",
        "role": "Analista",
        "department": "TI",
    })

    assert resp.status_code == 201
    gravado = db_session.query(Custodian).filter(
        Custodian.email == "api.legado.012@empresa.local").first()
    assert gravado.department == "TI"


# ============================================================================
# US3 (T018/T019) — Editar colaborador usando a mesma lista oficial
# (AC-06; Cenário 5; exceção do valor vigente — FR-014/remediação I2-b)
# ============================================================================

def test_form_edit_renders_official_selection(db_session, client):
    """US3 (AC-06) — GET /custodians/{id}/edit: marcador, dropdown com a lista
    oficial e o valor vigente pré-selecionado (mesmo fora da lista)."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")
    _criar_local(db_session, "Local Logística", "Logística")
    colab = _criar_colaborador(db_session, "MAT-0130", "Colaborador Edicao",
                               "edicao.012@empresa.local", "Grafia Antiga")

    body = client.get(f"/custodians/{colab.id}/edit").text

    assert resp_ok(body)
    assert 'name="department_source"' in body and 'value="official"' in body
    assert '<select name="department"' in body
    assert 'id="department-options"' not in body      # sem datalist/pesquisa
    assert "Setor de Suporte" in body          # mesma lista oficial do cadastro
    assert "Logística" in body
    assert 'value="Grafia Antiga"' in body     # valor vigente pré-selecionado


def test_edit_to_another_official_saves_canonical(db_session, client):
    """US3 (Cenário 5/AC-06/RV-2) — trocar por outro oficial grava o canônico."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")
    _criar_local(db_session, "Local Logística", "Logística")
    colab = _criar_colaborador(db_session, "MAT-0131", "Colaborador Troca",
                               "troca.012@empresa.local", "Logística")

    resp = client.post(f"/custodians/{colab.id}/edit", data={
        "name": "Colaborador Troca",
        "email": "troca.012@empresa.local",
        "role": "Analista",
        "department": "SETOR DE SUPORTE",
        "department_source": "official",
    }, follow_redirects=False)

    assert resp.status_code == 303
    db_session.refresh(colab)
    assert colab.department == "Setor de Suporte"   # canônico


def test_edit_unchanged_value_outside_list_accepted_without_renormalization(db_session, client):
    """US3 (FR-014/remediação I2-b) — submissão idêntica ao valor vigente
    (grafia herdada fora da lista) é aceita sem re-normalização."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")
    colab = _criar_colaborador(db_session, "MAT-0132", "Colaborador Herdado",
                               "herdado.012@empresa.local", "Grafia Antiga")

    resp = client.post(f"/custodians/{colab.id}/edit", data={
        "name": "Colaborador Herdado",
        "email": "herdado.012@empresa.local",
        "role": "Analista",
        "department": "Grafia Antiga",
        "department_source": "official",
    }, follow_redirects=False)

    assert resp.status_code == 303
    db_session.refresh(colab)
    assert colab.department == "Grafia Antiga"   # mantido, sem exigir re-seleção


def test_edit_different_invalid_value_rejected_and_unchanged(db_session, client):
    """US3 (US2 aplica-se à edição/RV-3) — valor DIFERENTE e fora da lista →
    redirect com erro e colaborador inalterado."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")
    colab = _criar_colaborador(db_session, "MAT-0133", "Colaborador Invalido",
                               "invalido.edit.012@empresa.local", "Grafia Antiga")

    resp = client.post(f"/custodians/{colab.id}/edit", data={
        "name": "Colaborador Invalido",
        "email": "invalido.edit.012@empresa.local",
        "role": "Analista",
        "department": "Setor Inexistente XYZ",
        "department_source": "official",
    }, follow_redirects=False)

    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]
    db_session.refresh(colab)
    assert colab.department == "Grafia Antiga"   # nada gravado


def resp_ok(body):
    """Auxiliar trivial de leitura (mantém os asserts acima declarativos)."""
    return body is not None and len(body) > 0


# ============================================================================
# US4 (T024–T026) — Matrícula provisória, histórico intocado e escopo preservado
# (AC-07, AC-08, AC-09; Cenário 6; FR-011/FR-014) — somente testes
# ============================================================================

def test_web_create_provisional_registration_with_official_department(client, db_session):
    """US4 (Cenário 6/AC-07/FR-007) — matrícula vazia + seleção oficial:
    PROV-* gerado E department canônico; nenhuma regra nova por matrícula."""
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")

    resp = client.post("/custodians/new", data=_dados_form(
        registration_code="", email="prov.012@empresa.local"),
        follow_redirects=False)

    assert resp.status_code == 303
    gravado = db_session.query(Custodian).filter(
        Custodian.email == "prov.012@empresa.local").first()
    assert gravado is not None
    assert re.match(r"^PROV-\d{6}$", gravado.registration_code)
    assert gravado.department == "Setor de Suporte"   # seleção oficial normal


def test_edit_department_does_not_rewrite_history(db_session, client):
    """US4 (AC-08/FR-008/RV-6) — colaborador com movimentação anterior: trocar
    o departamento pelo formulário deixa movements e a trilha pré-existente de
    audit_logs exatamente como estavam (nenhuma reescrita retroativa)."""
    from app.models.audit_log import AuditLog
    from app.models.enums import AssetCategory, MovementType
    from app.models.movement import Movement
    from app.schemas.asset import AssetCreate
    from app.schemas.movement import MovementCreate
    from app.services.asset_service import AssetService
    from app.services.movement_service import MovementService

    _criar_local(db_session, "Local Origem", "Logística")
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")
    colab = _criar_colaborador(db_session, "MAT-0140", "Colaborador Historico",
                               "historico.012@empresa.local", "Logística")
    loc = LocationService.get_by_name(db_session, "Local Origem")
    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-01240", name="Notebook Histórico",
        category=AssetCategory.NOTEBOOK, initial_location_id=loc.id))
    movement = MovementService.create_movement(db_session, MovementCreate(
        asset_id=asset.id, movement_type=MovementType.ALLOCATION,
        destination_custodian_id=colab.id,
        reason="Cautela antes da troca de setor", operator_name="Admin TI"))
    db_session.commit()

    movement_snapshot = (
        movement.movement_uuid, movement.movement_type, str(movement.timestamp),
        movement.origin_location_id, movement.origin_location_name,
        movement.origin_custodian_id, movement.origin_custodian_name,
        movement.destination_location_id, movement.destination_location_name,
        movement.destination_custodian_id, movement.destination_custodian_name,
        movement.previous_status, movement.new_status, movement.reason,
        movement.operator_name, movement.term_code,
    )
    audit_before = db_session.query(AuditLog).order_by(AuditLog.id).all()
    audit_snapshot = {
        a.id: (a.timestamp, a.user_id, a.username, a.action, a.module, a.resource,
               a.resource_id, a.resource_ref, a.ip_address, a.result,
               a.description, a.previous_data, a.new_data)
        for a in audit_before
    }
    # Contagem pré-edição inclui a movimentação de aquisição criada por AssetService.create.
    movement_count_before = db_session.query(Movement).filter(
        Movement.asset_id == asset.id).count()

    resp = client.post(f"/custodians/{colab.id}/edit", data={
        "name": "Colaborador Historico",
        "email": "historico.012@empresa.local",
        "role": "Analista",
        "department": "Setor de Suporte",
        "department_source": "official",
    }, follow_redirects=False)

    assert resp.status_code == 303
    db_session.refresh(colab)
    assert colab.department == "Setor de Suporte"   # a edição ocorreu

    # Nenhuma movimentação nova: contagem igual à pré-edição e a existente
    # byte-a-byte igual (snapshots imutáveis — Constitution IV).
    assert db_session.query(Movement).filter(Movement.asset_id == asset.id).count() == movement_count_before
    db_session.refresh(movement)
    assert (
        movement.movement_uuid, movement.movement_type, str(movement.timestamp),
        movement.origin_location_id, movement.origin_location_name,
        movement.origin_custodian_id, movement.origin_custodian_name,
        movement.destination_location_id, movement.destination_location_name,
        movement.destination_custodian_id, movement.destination_custodian_name,
        movement.previous_status, movement.new_status, movement.reason,
        movement.operator_name, movement.term_code,
    ) == movement_snapshot

    # Trilha pré-existente imutável (apensável — somente eventos novos se somam).
    audit_after = db_session.query(AuditLog).order_by(AuditLog.id).all()
    assert len(audit_after) >= len(audit_snapshot)
    for a in audit_after:
        if a.id in audit_snapshot:
            assert (a.timestamp, a.user_id, a.username, a.action, a.module,
                    a.resource, a.resource_id, a.resource_ref, a.ip_address,
                    a.result, a.description, a.previous_data, a.new_data) == audit_snapshot[a.id]


def test_scope_untouched_locations_roles_and_existing_custodians(db_session, client):
    """US4 (AC-09/FR-009/FR-011; Q2/FR-014/RV-6) — snapshot comparativo:
    locations (incl. department), Cargo/Função e colaboradores não editados
    permanecem idênticos após os fluxos da feature."""
    _criar_local(db_session, "Local A", "Departamento A", branch="Matriz")
    _criar_local(db_session, "Local B", "Departamento B", branch="Filial")
    _criar_local(db_session, "Local Suporte", "Setor de Suporte")
    editado = _criar_colaborador(db_session, "MAT-0150", "Colaborador Editado",
                                 "editado.015@empresa.local", "Departamento A",
                                 role="Cargo Original")
    intocado = _criar_colaborador(db_session, "MAT-0151", "Colaborador Intocado",
                                  "intocado.015@empresa.local", "SUPORTE",
                                  role="Cargo Antigo")

    def _locais_snapshot():
        from app.models.location import Location
        return {
            l.id: (l.name, l.branch, l.building, l.floor, l.room, l.department,
                   l.manager_name, l.description)
            for l in db_session.query(Location).order_by(Location.id).all()
        }

    def _colaboradores_snapshot():
        return {
            c.id: (c.registration_code, c.name, c.email, c.cpf, c.role,
                   c.department, c.is_active)
            for c in db_session.query(Custodian).order_by(Custodian.id).all()
        }

    locais_antes = _locais_snapshot()
    colab_antes = _colaboradores_snapshot()

    # Fluxos da feature: cadastro via seleção oficial + edição do colaborador-alvo.
    assert client.post("/custodians/new", data=_dados_form(
        department="Setor de Suporte", email="novo.015@empresa.local"),
        follow_redirects=False).status_code == 303
    assert client.post(f"/custodians/{editado.id}/edit", data={
        "name": "Colaborador Editado",
        "email": "editado.015@empresa.local",
        "role": "Cargo Original",
        "department": "Setor de Suporte",
        "department_source": "official",
    }, follow_redirects=False).status_code == 303

    # Localização de patrimônio intocada (FR-009/AC-09).
    assert _locais_snapshot() == locais_antes
    # Cargo/Função permanece texto livre e inalterado (FR-011).
    db_session.refresh(editado)
    assert editado.role == "Cargo Original"
    # Colaborador pré-existente sem edição permanece com valores originais (Q2/FR-014).
    db_session.refresh(intocado)
    assert (intocado.registration_code, intocado.name, intocado.email, intocado.cpf,
            intocado.role, intocado.department, intocado.is_active) == colab_antes[intocado.id]
    # O colaborador criado/editado difere apenas nos campos previstos pela spec.
    depois = _colaboradores_snapshot()
    assert depois[intocado.id] == colab_antes[intocado.id]
    assert depois[editado.id][5] == "Setor de Suporte"          # department alterado (previsto)
    assert depois[editado.id][:5] == colab_antes[editado.id][:5]  # cargo/demais campos intactos
