"""
Testes da feature 008 — Exportação CSV de Locais.

Cobre:
- US1: botão "Exportar CSV" na tela de Locais (gate `relatorios.exportar`) e
  download direto via GET /api/v1/reports/locations/csv no padrão dos exports
  existentes (conjunto completo, tela intacta).
- US2: formato do CSV fixado no contrato (cabeçalho exato, ordenação da
  listagem, escapamento, vazios como "", sem colunas de interface).
- US3: proteção RBAC (botão oculto + 403/401), operação read-only e
  não-regressão das exportações existentes.

Padrões: fixtures `client` (admin), `unauth_client` (sem sessão) e
`db_session` de tests/conftest.py; perfil "Técnico de TI" (sem
`relatorios.exportar`) conforme tests/test_rbac.py.
"""

import csv
import io

from app.models.location import Location
from app.services.auth_service import create_user
from app.services.permission_service import (
    assign_role,
    ensure_default_roles,
    get_role_by_name,
)
from app.services.report_service import ReportService

PASSWORD = "senha@1234"

EXPORT_URL = "/api/v1/reports/locations/csv"
LOCATION_CSV_HEADER = "nome;filial;departamento;predio;andar;sala;gestor"


# ============================================================================
# HELPERS
# ============================================================================

def _make_location(db, name, branch="Matriz SP", department="TI",
                   building=None, floor=None, room=None, manager_name=None):
    """Cria um local diretamente via model (feature read-only; sem regras novas)."""
    loc = Location(
        name=name,
        branch=branch,
        department=department,
        building=building,
        floor=floor,
        room=room,
        manager_name=manager_name,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def _parse_csv(body):
    """Re-parseia o corpo do CSV com o mesmo mecanismo do sistema (`;`)."""
    return [row for row in csv.reader(io.StringIO(body), delimiter=";") if row]


def _make_user(db, username, role_names=None):
    """Cria usuário com perfis (mesmo padrão de tests/test_rbac.py)."""
    ensure_default_roles(db)
    user = create_user(db, username=username, password=PASSWORD, is_admin=False)
    for rn in role_names or []:
        role = get_role_by_name(db, rn)
        if role:
            assign_role(db, user, role)
    return user


def _login(client, username):
    resp = client.post(
        "/api/v1/auth/login", data={"username": username, "password": PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    return resp


# ============================================================================
# US1 — Botão na tela, download no padrão do sistema, conjunto completo
# ============================================================================

def test_export_button_visible_with_permission(client):
    """FR-001: botão "Exportar CSV" visível no cabeçalho da tela de Locais,
    com o markup padrão dos 3 botões de exportação existentes."""
    resp = client.get("/locations")
    assert resp.status_code == 200
    html = resp.text
    assert 'href="/api/v1/reports/locations/csv"' in html
    assert "Exportar CSV" in html
    assert 'class="btn btn-ghost"' in html
    assert 'bi bi-upload me-1' in html


def test_locations_csv_download_headers(client):
    """FR-002/FR-005: download direto com content-type, disposition e nome
    de arquivo no padrão das exportações existentes."""
    resp = client.get(EXPORT_URL)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "charset=utf-8-sig" in resp.headers["content-type"]
    assert resp.headers["content-disposition"] == "attachment; filename=locais.csv"


def test_locations_csv_contains_all_created_locations(client, db_session):
    """FR-006: o CSV contém todos os locais criados (e somente eles)."""
    _make_location(db_session, "Sede Central")
    _make_location(db_session, "Filial Norte", branch="Filial Norte",
                   department="Almoxarifado")
    _make_location(db_session, "Depósito Zona Sul", department="Logística")

    resp = client.get(EXPORT_URL)
    assert resp.status_code == 200
    rows = _parse_csv(resp.text)
    names = [r[0] for r in rows[1:]]
    assert len(names) == 3
    assert set(names) == {"Sede Central", "Filial Norte", "Depósito Zona Sul"}


def test_export_ignores_active_search_filter(client, db_session):
    """FR-006/FR-010: com filtro de pesquisa ativo na chamada da tela, a
    exportação mantém o conjunto completo, não o filtrado."""
    _make_location(db_session, "Almoxarifado Central")
    _make_location(db_session, "Sala dos Servidores", department="Suporte")

    # Tela com filtro ativo (feature 007): lista filtrada, sem erro
    screen = client.get("/locations", params={"search": "Almoxarifado"})
    assert screen.status_code == 200
    assert "Almoxarifado Central" in screen.text
    assert "Sala dos Servidores" not in screen.text

    # A exportação NÃO é afetada pelo filtro da tela
    resp = client.get(EXPORT_URL)
    assert resp.status_code == 200
    rows = _parse_csv(resp.text)
    names = [r[0] for r in rows[1:]]
    assert set(names) == {"Almoxarifado Central", "Sala dos Servidores"}


def test_locations_screen_intact_after_export(client, db_session):
    """FR-009: após a exportação, a tela de Locais segue 200 e íntegra
    (pesquisa 007, tabela e colunas no lugar)."""
    _make_location(db_session, "Local Pós-Export")

    first = client.get("/locations")
    assert first.status_code == 200

    export = client.get(EXPORT_URL)
    assert export.status_code == 200

    after = client.get("/locations")
    assert after.status_code == 200
    assert "Local Pós-Export" in after.text
    assert "Nome / Identificação" in after.text
    assert 'name="search"' in after.text


# ============================================================================
# US2 — Conteúdo fiel e no padrão do sistema (contrato §3)
# ============================================================================

def test_csv_header_exact(client, db_session):
    """US2a: primeira linha EXATAMENTE o cabeçalho fixado no contrato."""
    _make_location(db_session, "Qualquer Local")

    resp = client.get(EXPORT_URL)
    first_line = resp.text.splitlines()[0]
    assert first_line == LOCATION_CSV_HEADER


def test_csv_one_row_per_location_in_listing_order(client, db_session):
    """US2b: uma linha por local, na ordenação da listagem
    (filial → departamento → nome), com massa fora da ordem de inserção."""
    _make_location(db_session, "C-TI-B", branch="Matriz SP", department="TI")
    _make_location(db_session, "A-ALM-Z", branch="Filial NORTE", department="Almoxarifado")
    _make_location(db_session, "B-TI-A", branch="Matriz SP", department="TI")
    _make_location(db_session, "A-ALM-A", branch="Filial NORTE", department="Almoxarifado")

    resp = client.get(EXPORT_URL)
    rows = _parse_csv(resp.text)
    names = [r[0] for r in rows[1:]]
    assert names == ["A-ALM-A", "A-ALM-Z", "B-TI-A", "C-TI-B"]


def test_csv_escaping_semicolon_quotes_accents_newline(client, db_session):
    """US2c: valores com `;`, aspas, acentos e quebra de linha escapados
    pelo mecanismo padrão — re-parse rende célula única íntegra."""
    _make_location(db_session, "Sala; especial \"A\" çãõ")
    _make_location(db_session, "Local\ncom quebra", department="RH")

    resp = client.get(EXPORT_URL)
    rows = _parse_csv(resp.text)
    data_rows = rows[1:]
    assert len(data_rows) == 2
    names = {r[0] for r in data_rows}
    assert names == {"Sala; especial \"A\" çãõ", "Local\ncom quebra"}
    # Célula com `;` permanece única (não quebrou a linha em colunas extras)
    for r in data_rows:
        assert len(r) == 7


def test_csv_optional_null_fields_as_empty(client, db_session):
    """US2d: campos opcionais nulos → vazios (""), nunca "None"."""
    _make_location(db_session, "Local Mínimo")

    resp = client.get(EXPORT_URL)
    rows = _parse_csv(resp.text)
    assert rows[1] == ["Local Mínimo", "Matriz SP", "TI", "", "", "", ""]
    assert "None" not in resp.text


def test_csv_has_no_interface_columns(client, db_session):
    """US2e: sem colunas de interface — sem "Ações"/"Ver Bens" e sem
    contagem de bens no corpo (precedente estrito do CSV de colaboradores)."""
    _make_location(db_session, "Local Sem Interface")

    resp = client.get(EXPORT_URL)
    body = resp.text
    rows = _parse_csv(body)
    assert rows[0] == LOCATION_CSV_HEADER.split(";")
    for forbidden in ("Ações", "Ver Bens", "bens", "count_assets"):
        assert forbidden not in body
    assert all(len(r) == 7 for r in rows)


def test_service_direct_call_matches_endpoint(client, db_session):
    """US2f: `ReportService.generate_locations_csv(db)` direto (sem argumento)
    gera o mesmo conteúdo do endpoint — reuso R1 do research."""
    _make_location(db_session, "Local Reuso R1")

    direct = ReportService.generate_locations_csv(db_session)
    via_endpoint = client.get(EXPORT_URL).text
    assert direct == via_endpoint


# ============================================================================
# US3 — Proteção e preservação (RBAC, read-only, não-regressão)
# ============================================================================

def test_button_hidden_and_endpoint_403_without_export_permission(db_session, unauth_client):
    """US3a: autenticado com `locais.visualizar` mas SEM `relatorios.exportar`
    (perfil Almoxarifado, padrão test_rbac.py): botão AUSENTE na tela e
    endpoint com 403."""
    _make_user(db_session, "almox1", role_names=["Almoxarifado"])
    _login(unauth_client, "almox1")

    screen = unauth_client.get("/locations")
    assert screen.status_code == 200  # vê a tela, mas não o botão
    assert "Exportar CSV" not in screen.text
    assert "/api/v1/reports/locations/csv" not in screen.text

    assert unauth_client.get(EXPORT_URL).status_code == 403


def test_endpoint_requires_authentication(unauth_client):
    """US3b: chamada sem sessão → 401 pelo mecanismo da API."""
    assert unauth_client.get(EXPORT_URL).status_code == 401


def test_export_is_read_only(client, db_session):
    """US3c: snapshot de Location (contagem + campos) antes/depois de
    exportações repetidas é idêntico (operação exclusivamente read-only)."""
    _make_location(db_session, "Read Only A", building="Ed. 1", floor="2º",
                   room="201", manager_name="Gestor A")
    _make_location(db_session, "Read Only B", branch="Filial Sul", department="RH")

    def snapshot():
        rows = db_session.query(Location).order_by(Location.id).all()
        return [(r.id, r.name, r.branch, r.department, r.building,
                 r.floor, r.room, r.manager_name) for r in rows]

    before = snapshot()
    for _ in range(3):
        assert client.get(EXPORT_URL).status_code == 200
    db_session.expire_all()
    assert snapshot() == before
    assert len(before) == 2


def test_empty_database_returns_header_only(client, db_session):
    """US3d: zero locais → 200 com APENAS a linha de cabeçalho (sem 500)."""
    resp = client.get(EXPORT_URL)
    assert resp.status_code == 200
    lines = [l for l in resp.text.splitlines() if l.strip()]
    assert lines == [LOCATION_CSV_HEADER]


def test_existing_exports_unchanged(client):
    """US3e: exportações existentes intocadas — custodians segue 200 com
    `filename=colaboradores.csv` e inventory/csv segue 200 no mesmo gate."""
    cust = client.get("/api/v1/reports/custodians/csv")
    assert cust.status_code == 200
    assert cust.headers["content-disposition"] == "attachment; filename=colaboradores.csv"

    inv = client.get("/api/v1/reports/inventory/csv")
    assert inv.status_code == 200
    assert inv.headers["content-type"].startswith("text/csv")


def test_screen_without_export_permission_search_and_table_intact(db_session, unauth_client):
    """US3f: para usuário sem o gate de exportação, a tela mantém a pesquisa
    (007) e a tabela íntegras — o botão é a única adição da feature."""
    _make_user(db_session, "almox2", role_names=["Almoxarifado"])
    _make_location(db_session, "Almoxarifado Central")
    _make_location(db_session, "Sala de Reuniões", department="Diretoria")
    _login(unauth_client, "almox2")

    resp = unauth_client.get("/locations", params={"search": "Almoxarifado"})
    assert resp.status_code == 200
    body = resp.text
    assert "Almoxarifado Central" in body
    assert "Sala de Reuniões" not in body
    assert 'name="search"' in body
    for header in ("Nome / Identificação", "Filial", "Departamento",
                   "Prédio / Andar / Sala", "Gestor", "Bens", "Ações"):
        assert header in body
    assert "Exportar CSV" not in body
