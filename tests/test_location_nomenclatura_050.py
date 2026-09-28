# Feature 050 — Contrato de nomenclatura da importação/exportação de localizações.
# Cenários do FR-022 da spec (oficial, compatibilidade, duplicidades, round-trip).
import pytest

from app.services.location_import_service import (
    _normalize_column_name,
    parse_locations_csv,
)


# ============================================================================
# HELPERS (padrão da suíte — login via API define cookie de sessão)
# ============================================================================

PASSWORD = "senha@1234"

CSV_OFICIAL = "Localização;Unidade Administrativa;Departamento\nSala da TI;IPMJP - Sede;Divisão de Tecnologia da Informação\n"
CSV_LEGADO = "Nome;Filial;Departamento\nSala da TI;IPMJP - Sede;Divisão de Tecnologia da Informação\n"


def _mapping_oficial(content: str) -> str:
    """Mapeamento coluna→campo como o passo de mapeamento da 048 o produz
    (confirm do fluxo real: servidor reclassifica com o mapping confirmado)."""
    import json
    from app.services.import_intelligence import analyze_columns
    analysis = analyze_columns(content, "locations")
    mapping = {s["column"]: s["field"] for s in analysis["suggestions"] if s.get("field")}
    return json.dumps(mapping, ensure_ascii=False)


def _make_user(db, username="admin_050"):
    from app.services.auth_service import create_user
    return create_user(db, username=username, password=PASSWORD,
                       full_name="Admin 050", is_admin=True)


def _login(client, username="admin_050", password=PASSWORD):
    resp = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text[:300]
    return resp


@pytest.fixture()
def admin_client(client, db_session):
    _make_user(db_session)
    _login(client)
    return client


# ============================================================================
# US1 — Contrato oficial (cenários 1–2 do FR-022)
# ============================================================================

def test_cenario1_csv_oficial_importa_ponta_a_ponta(admin_client, db_session):
    """CSV oficial Localização;Unidade Administrativa;Departamento importa e grava
    name/branch/department corretos (FR-001/002/003/004 — hoje falha)."""
    from app.models.location import Location

    mapping = _mapping_oficial(CSV_OFICIAL)
    resp = admin_client.post(
        "/locations/import",
        data={"csv_content": CSV_OFICIAL, "skip_duplicates": "false",
              "step": "analyze", "mapping": mapping},
        follow_redirects=False,
    )
    assert resp.status_code == 200, resp.text[:300]
    # mapeamento sugerido correto (FR-004): os 3 cabeçalhos oficiais reconhecidos
    assert "Unidade Administrativa" in resp.text

    confirm = admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": CSV_OFICIAL, "mapping": mapping, "skip_duplicates": "false"},
        follow_redirects=False,
    )
    assert confirm.status_code == 200, confirm.text[:300]

    loc = db_session.query(Location).filter_by(name="Sala da TI").first()
    assert loc is not None
    assert loc.branch == "IPMJP - Sede"
    assert loc.department == "Divisão de Tecnologia da Informação"


def test_cenario2_ordem_espacos_caixa_acentos(admin_client, db_session):
    """Ordem das colunas livre (FR-005); espaços/caixa/acentos normalizados
    pelo mecanismo existente (cenário 2 do FR-022)."""
    from app.models.location import Location

    csv_variado = (
        "departamento;   Unidade Administrativa ;localizacao\n"
        "Divisão de TI;IPMJP - Sede;Sala de Rede\n"
    )
    mapping = _mapping_oficial(csv_variado)
    resp = admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": csv_variado, "mapping": mapping, "skip_duplicates": "false"},
        follow_redirects=False,
    )
    assert resp.status_code == 200, resp.text[:300]

    loc = db_session.query(Location).filter_by(name="Sala de Rede").first()
    assert loc is not None
    assert loc.branch == "IPMJP - Sede"
    assert loc.department == "Divisão de TI"


def test_normalizacao_cabecalho_oficial():
    """Unidade Administrativa → branch (FR-002); Localização → name (FR-001)."""
    assert _normalize_column_name("Unidade Administrativa") == "branch"
    assert _normalize_column_name("unidade administrativa") == "branch"
    assert _normalize_column_name("Localização") == "name"
    assert _normalize_column_name("Departamento") == "department"


def test_parse_csv_oficial_sem_erro():
    """parse_locations_csv aceita o CSV oficial sem erro de campo obrigatório (FR-004)."""
    rows, errors = parse_locations_csv(CSV_OFICIAL)
    assert errors == []
    assert len(rows) == 1
    assert rows[0]["name"] == "Sala da TI"
    assert rows[0]["branch"] == "IPMJP - Sede"


# ============================================================================
# US2 — Compatibilidade controlada (cenários 3–6 do FR-022)
# ============================================================================

def test_cenario3_cabecalhos_legados_aceitos(db_session):
    """CSV legado Nome;Filial;Departamento continua importando (FR-006)."""
    rows, errors = parse_locations_csv(CSV_LEGADO)
    assert errors == []
    assert rows[0]["name"] == "Sala da TI"
    assert rows[0]["branch"] == "IPMJP - Sede"


def test_cenario3_variacoes_legadas_de_branch(db_session):
    """unidade/empresa/sede/setor/area continuam reconhecidos (FR-006)."""
    assert _normalize_column_name("unidade") == "branch"
    assert _normalize_column_name("empresa") == "branch"
    assert _normalize_column_name("sede") == "branch"
    assert _normalize_column_name("setor") == "department"
    assert _normalize_column_name("área") == "department"
    assert _normalize_column_name("divisão") == "department"


def test_cenario4_cabecalho_desconhecido_nao_utilizada():
    """Matriz/Filial nunca reconhecido permanece coluna desconhecida (FR-008) —
    analyze_columns marca como sem campo (não utilizada), não grava."""
    from app.services.import_intelligence import analyze_columns
    csv_desc = "Matriz/Filial;Departamento\nX;Y\n"
    analysis = analyze_columns(csv_desc, "locations")
    matriz = [s for s in analysis["suggestions"] if s["column"] == "Matriz/Filial"]
    assert matriz, "coluna deveria aparecer na análise"
    assert matriz[0]["field"] is None or matriz[0]["confidence"] == "desconhecida"


def test_cenario5_coluna_obrigatoria_ausente_detectada():
    """CSV sem a coluna Unidade Administrativa → erro de campo obrigatório
    com a mensagem oficial (FR-012 — cobre também o cenário 7)."""
    rows, errors = parse_locations_csv("Localização;Departamento\nSala X;TI\n")
    assert rows == []
    assert any("Unidade Administrativa" in e and "obrigat" in e for e in errors)


def test_cenario6_valores_originais_preservados():
    """Normalização só para comparação — espaços/caixa dos VALORES preservados
    (FR-019 da 048)."""
    rows, errors = parse_locations_csv(
        "Localização;Unidade Administrativa;Departamento\n"
        "  Sala  do  Servidores ;  IPMJP - Sede ;Tecnologia da Informação  \n"
    )
    assert errors == []
    # strip() vigente nos services; espaços internos e caixa originais preservados
    assert rows[0]["name"] == "Sala  do  Servidores"
    assert rows[0]["branch"] == "IPMJP - Sede"


# ============================================================================
# US4 — Semântica/dados (cenários 9–12 do FR-022)
# ============================================================================

def test_cenario9_localizacao_existente_duplicado(admin_client, db_session):
    """Localização existente → DUPLICADO, nenhum registro novo (FR-018/SC-004).
    Mesmo conteúdo em formato legado e oficial → mesmos registros."""
    from app.models.location import Location

    mapping = _mapping_oficial(CSV_OFICIAL)
    first = admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": CSV_OFICIAL, "mapping": mapping, "skip_duplicates": "false"},
        follow_redirects=False,
    )
    assert first.status_code == 200
    total_1 = db_session.query(Location).count()

    # Reenvio do mesmo arquivo (reanálise — FR-018 da 048): duplicados, nada duplicado
    second = admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": CSV_OFICIAL, "mapping": mapping, "skip_duplicates": "false"},
        follow_redirects=False,
    )
    assert second.status_code == 200
    total_2 = db_session.query(Location).count()
    assert total_1 == total_2 == 1  # SC-004: 0 duplicidades pela nomenclatura


def test_cenario10_reanalise_legado_vs_oficial_mesmos_registros(admin_client, db_session):
    """O mesmo conteúdo nos formatos legado e oficial identifica a MESMA
    localização existente (duplicidade por name — imune a rótulos, FR-018)."""
    from app.models.location import Location

    m_of = _mapping_oficial(CSV_OFICIAL)
    m_leg = _mapping_oficial(CSV_LEGADO)
    r1 = admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": CSV_OFICIAL, "mapping": m_of, "skip_duplicates": "true"},
        follow_redirects=False,
    )
    assert r1.status_code == 200
    # mesmo registro em formato legado → duplicado, não cria novo
    r2 = admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": CSV_LEGADO, "mapping": m_leg, "skip_duplicates": "true"},
        follow_redirects=False,
    )
    assert r2.status_code == 200
    assert db_session.query(Location).filter_by(name="Sala da TI").count() == 1


def test_cenario11_rollback_linha_com_erro(admin_client, db_session):
    """Linha com erro sofre rollback e não impede as demais (commit por linha da
    029 — estratégia transacional vigente, FR-015/FR-019)."""
    from app.models.location import Location

    csv_misto = (
        "Localização;Unidade Administrativa;Departamento\n"
        "Sala Boa;IPMJP - Sede;TI\n"
        ";Unidade sem Localização;TI\n"  # linha 3 inválida
        "Sala Boa 2;IPMJP - Sede;TI\n"
    )
    mapping = _mapping_oficial(csv_misto)
    resp = admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": csv_misto, "mapping": mapping, "skip_duplicates": "false"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    names = {l.name for l in db_session.query(Location).all()}
    assert "Sala Boa" in names and "Sala Boa 2" in names  # válidas gravadas
    assert not any("sem Localização" in n for n in names)  # inválida não gravou


def test_cenario12_dados_preexistentes_intactos(admin_client, db_session):
    """Dados já cadastrados não são apagados/recriados pela importação (FR-017)."""
    from app.models.location import Location

    pre = Location(name="Pré-existente 050", branch="Unidade X", department="RH")
    db_session.add(pre)
    db_session.commit()
    pre_id = pre.id

    mapping = _mapping_oficial(CSV_OFICIAL)
    resp = admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": CSV_OFICIAL, "mapping": mapping, "skip_duplicates": "false"},
        follow_redirects=False,
    )
    assert resp.status_code == 200

    db_session.expire_all()
    still = db_session.get(Location, pre_id)
    assert still is not None
    assert still.name == "Pré-existente 050"
    assert still.branch == "Unidade X"


# ============================================================================
# US5 — Preservação da 048 (FR-019/020/021)
# ============================================================================

def test_048_passo_mapeamento_ponta_a_ponta_com_oficial(admin_client, db_session):
    """Fluxo completo da 048 com CSV oficial: upload → passo de mapeamento
    (rótulos oficiais, sugestão auto) → prévia classificada → confirmação.
    Auditoria write_audit registrada (FR-025)."""
    from app.models.audit_log import AuditLog

    # passo de mapeamento (rótulos oficiais presentes) — upload multipart padrão da suíte
    import io
    resp_map = admin_client.post(
        "/locations/import",
        files={"file": ("locais_oficial.csv", io.BytesIO(CSV_OFICIAL.encode("utf-8")), "text/csv")},
        data={"skip_duplicates": "false"},
        follow_redirects=False,
    )
    assert resp_map.status_code == 200
    body = resp_map.text
    assert "Localização" in body and "Unidade Administrativa" in body
    assert "Nome do local" not in body  # rótulo legado ausente (FR-010)

    # prévia classificada (analyze reexecuta server-side)
    mapping = _mapping_oficial(CSV_OFICIAL)
    resp_prev = admin_client.post(
        "/locations/import",
        data={"csv_content": CSV_OFICIAL, "mapping": mapping, "skip_duplicates": "false",
              "step": "analyze"},
        follow_redirects=False,
    )
    assert resp_prev.status_code == 200

    # confirmação grava e audita
    resp_conf = admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": CSV_OFICIAL, "mapping": mapping, "skip_duplicates": "false"},
        follow_redirects=False,
    )
    assert resp_conf.status_code == 200
    logs = (db_session.query(AuditLog)
            .order_by(AuditLog.id.desc()).limit(5).all()) if AuditLog is not None else []
    import_names = [getattr(l, "action", "") or getattr(l, "event_type", "") for l in logs]
    assert any("IMPORT" in (n or "") for n in import_names), import_names


def test_048_rotas_e_execute_intocados():
    """Rotas/URLs e execute_locations_import preservados (FR-020) — o mecanismo
    de gravação é o existente; a 050 só estende aliases/rótulos/mensagens."""
    import inspect
    from app.web import routes
    from app.services import location_import_service as lis

    src = inspect.getsource(routes)
    assert '@web_router.post("/locations/import"' in src
    assert '@web_router.post("/locations/import/confirm"' in src
    # execute continua expondo a assinatura atual (skip_duplicates)
    sig = inspect.signature(lis.execute_locations_import)
    assert "skip_duplicates" in sig.parameters


# ============================================================================
# US6 — Export oficial + round-trip (FR-026/027)
# ============================================================================

def test_export_locais_header_oficial_e_round_trip(admin_client, db_session):
    """Export usa cabeçalhos oficiais (FR-026) e o arquivo exportado é
    reimportado sem ajustes — duplicados, nada novo (FR-027/SC-004)."""
    from app.models.location import Location

    # grava 1 local via importação oficial
    mapping = _mapping_oficial(CSV_OFICIAL)
    admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": CSV_OFICIAL, "mapping": mapping, "skip_duplicates": "false"},
        follow_redirects=False,
    )

    # export com header oficial
    export = admin_client.get("/api/v1/reports/locations/csv")
    assert export.status_code == 200
    first_line = export.text.splitlines()[0]
    assert first_line == "Localização;Unidade Administrativa;Departamento;Prédio;Andar;Sala;Gestor"
    assert "Sala da TI" in export.text

    # round-trip: reimportar o exportado (header oficial já reconhecido)
    mapping_rt = _mapping_oficial(export.text)
    assert mapping_rt  # cabeçalhos oficiais do export reconhecidos pelo importador
    rt = admin_client.post(
        "/locations/import/confirm",
        data={"csv_content": export.text, "mapping": mapping_rt, "skip_duplicates": "true"},
        follow_redirects=False,
    )
    assert rt.status_code == 200
    assert db_session.query(Location).filter_by(name="Sala da TI").count() == 1
