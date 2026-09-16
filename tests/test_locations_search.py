"""Feature 007 — Pesquisa de Locais (tela /locations).

Testes organizados por user story da spec:
- US1: localizar local rapidamente pelo Nome / Identificação (mono-campo)
- US2: pesquisa tolerante (case-insensitive, multi-palavra, estados vazios, limpeza)
- US3: integridade da tela e dos dados existentes (não-regressão, read-only, retrocompatibilidade)

Fixtures `client` (sessão autenticada) e `db_session` vêm de tests/conftest.py.
Nenhum teste existente é editado (Constitution VIII).
"""
import re

from app.schemas.location import LocationCreate
from app.services.location_service import LocationService


def _criar_locais_base(db_session):
    """Massa de teste: locais com o formato real (sigla + descrição) + um de outra filial."""
    return {
        "controle": LocationService.create(db_session, LocationCreate(
            name="IPMJP – Acessoria de Controle Interno",
            branch="IPMJP",
            department="Controle Interno",
        )),
        "gabinete": LocationService.create(db_session, LocationCreate(
            name="IPMJP – Acessoria de Gabinete",
            branch="IPMJP",
            department="Gabinete",
        )),
        "patrimonio_sede": LocationService.create(db_session, LocationCreate(
            name="Almoxarifado Central",
            branch="SEDE",
            department="Logística",
            manager_name="Carla Mendes",
        )),
    }


# ---- US1: Localizar um local rapidamente pelo Nome / Identificação ----

def test_search_by_full_name_returns_the_location(client, db_session):
    """US1 (US1.1) — Nome completo: o local correspondente aparece."""
    locs = _criar_locais_base(db_session)

    resp = client.get("/locations", params={"search": "IPMJP – Acessoria de Controle Interno"})

    assert resp.status_code == 200
    assert locs["controle"].name in resp.text
    assert locs["patrimonio_sede"].name not in resp.text


def test_search_partial_match_by_name(client, db_session):
    """US1 (US1.2) — Parcial: 'Controle' encontra o local do Controle Interno."""
    locs = _criar_locais_base(db_session)

    resp = client.get("/locations", params={"search": "Controle"})

    assert resp.status_code == 200
    body = resp.text
    assert locs["controle"].name in body
    assert locs["gabinete"].name not in body
    assert locs["patrimonio_sede"].name not in body


def test_search_by_acronym_returns_all_matching(client, db_session):
    """US1 (US1.3) — Sigla 'IPMJP': todos os locais que a contêm no NOME."""
    locs = _criar_locais_base(db_session)

    resp = client.get("/locations", params={"search": "IPMJP"})

    assert resp.status_code == 200
    body = resp.text
    assert locs["controle"].name in body
    assert locs["gabinete"].name in body
    assert locs["patrimonio_sede"].name not in body   # SEDE — nome não contém


def test_search_field_is_repopulated_and_in_url(client, db_session):
    """US1 (US1.4/FR-009) — Campo reposto com o termo; GET preserva na URL."""
    _criar_locais_base(db_session)

    resp = client.get("/locations", params={"search": "Controle"})

    assert resp.status_code == 200
    assert 'value="Controle"' in resp.text


# ---- US2: Pesquisa tolerante e com feedback claro ----

def test_search_case_insensitive_equivalence(client, db_session):
    """US2 (US2.1) — CONTROLE / controle / Controle produzem resultados equivalentes."""
    locs = _criar_locais_base(db_session)

    bodies = []
    for termo in ("CONTROLE", "controle", "Controle"):
        resp = client.get("/locations", params={"search": termo})
        assert resp.status_code == 200
        bodies.append(resp.text)

    for body in bodies:
        assert locs["controle"].name in body
        assert locs["patrimonio_sede"].name not in body


def test_search_partial_any_position(client, db_session):
    """US2 (US2.2) — 'gabinete' minúsculo encontra o local do Gabinete (qualquer posição)."""
    locs = _criar_locais_base(db_session)

    resp = client.get("/locations", params={"search": "gabinete"})

    assert resp.status_code == 200
    assert locs["gabinete"].name in resp.text


def test_search_targets_name_field_only(client, db_session):
    """US2 (US2.6 / FR-002, contratesta mono-campo) — Termo que casa APENAS com
    Filial/Departamento/Gestor de um local (e não com o nome) NÃO retorna o registro."""
    locs = _criar_locais_base(db_session)

    # "SEDE" é a Filial, "Logística" o Departamento e "Carla Mendes" a Gestor —
    # nenhum desses termos aparece no NAME do local
    for termo in ("SEDE", "Logística", "Carla Mendes"):
        resp = client.get("/locations", params={"search": termo})
        assert resp.status_code == 200
        body = resp.text
        assert locs["patrimonio_sede"].name not in body
        assert "Nenhum local encontrado." in body


def test_search_trims_surrounding_spaces(client, db_session):
    """US2 (US2.3/FR-005) — Espaços nas extremidades são removidos do termo."""
    locs = _criar_locais_base(db_session)

    resp = client.get("/locations", params={"search": "  Controle  "})

    assert resp.status_code == 200
    body = resp.text
    assert locs["controle"].name in body
    assert locs["gabinete"].name not in body


def test_search_empty_or_blank_returns_full_list(client, db_session):
    """US2 (US2.4/FR-006) — Vazio ou só espaços: lista completa, sem estado de busca."""
    locs = _criar_locais_base(db_session)

    resp_empty = client.get("/locations", params={"search": ""})
    resp_blank = client.get("/locations", params={"search": "   "})
    resp_none = client.get("/locations")

    for resp in (resp_empty, resp_blank, resp_none):
        assert resp.status_code == 200
        body = resp.text
        assert locs["controle"].name in body
        assert locs["gabinete"].name in body
        assert locs["patrimonio_sede"].name in body
        assert "Nenhum local encontrado." not in body


def test_search_no_results_shows_exact_empty_state(client, db_session):
    """US2 (US2.5/FR-007) — Termo inexistente: 'Nenhum local encontrado.' exato, sem erro."""
    locs = _criar_locais_base(db_session)

    resp = client.get("/locations", params={"search": "zzz-inexistente-xyz"})

    assert resp.status_code == 200
    body = resp.text
    assert "Nenhum local encontrado." in body
    assert locs["controle"].name not in body
    assert "Nenhum local cadastrado" not in body   # há locais; estado distinto


def test_clearing_search_restores_full_list(client, db_session):
    """US2 (US2.6/FR-010) — Após pesquisa sem resultado, limpar restaura a lista completa."""
    locs = _criar_locais_base(db_session)

    first = client.get("/locations", params={"search": "zzz-inexistente-xyz"})
    assert "Nenhum local encontrado." in first.text

    second = client.get("/locations")
    assert second.status_code == 200
    body = second.text
    assert locs["controle"].name in body
    assert locs["gabinete"].name in body
    assert locs["patrimonio_sede"].name in body


def test_search_multiple_words_treated_as_single_text(client, db_session):
    """US2 (edge case multi-palavra, correção F1) — 'controle interno' encontra o local."""
    locs = _criar_locais_base(db_session)

    resp = client.get("/locations", params={"search": "controle interno"})

    assert resp.status_code == 200
    body = resp.text
    assert locs["controle"].name in body
    assert locs["gabinete"].name not in body


def test_search_with_special_characters_does_not_fail(client, db_session):
    """US2 (research R6) — Termo com '%' não gera erro na página."""
    _criar_locais_base(db_session)

    resp = client.get("/locations", params={"search": "100%"})

    assert resp.status_code == 200
    assert "Nenhum local encontrado." in resp.text


# ---- US3: Integridade da tela e dos dados existentes ----

def test_base_route_renders_current_table_structure(client, db_session):
    """US3 (US3.1) — Sem search: as 7 colunas atuais e todos os locais na ordenação."""
    locs = _criar_locais_base(db_session)

    resp = client.get("/locations")

    assert resp.status_code == 200
    body = resp.text
    for header in ("Nome / Identificação", "Filial", "Departamento",
                   "Prédio / Andar / Sala", "Gestor", "Bens", "Ações"):
        assert header in body
    assert locs["controle"].name in body
    assert locs["gabinete"].name in body
    assert locs["patrimonio_sede"].name in body
    assert "Nenhum local encontrado." not in body


def test_results_preserve_see_assets_link(client, db_session):
    """US3 (US3.2) — Link 'Ver Bens' dos resultados mantém o location_id correto."""
    locs = _criar_locais_base(db_session)

    resp = client.get("/locations", params={"search": "Controle"})

    assert resp.status_code == 200
    assert f'href="/assets?location_id={locs["controle"].id}"' in resp.text
    assert f'href="/assets?location_id={locs["gabinete"].id}"' not in resp.text


def test_results_preserve_asset_count(client, db_session):
    """US3 (US3.3) — Contagem de bens idêntica com e sem pesquisa (badge)."""
    from app.models.enums import AssetCategory, AssetStatus
    from app.schemas.asset import AssetCreate
    from app.services.asset_service import AssetService

    locs = _criar_locais_base(db_session)
    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-00701",
        name="Impressora do Controle",
        category=AssetCategory.PRINTER,
        initial_location_id=locs["controle"].id,
    ))
    db_session.expire(asset)
    assert asset.status == AssetStatus.AVAILABLE   # bem vinculado ao local

    resp_search = client.get("/locations", params={"search": "Controle"})
    resp_full = client.get("/locations")

    assert resp_search.status_code == 200
    assert resp_full.status_code == 200
    # contagem = 1 bem no badge do local (mesma com e sem filtro)
    for body in (resp_search.text, resp_full.text):
        assert re.search(r"badge rounded-pill[^>]*>\s*1\s*<", body)


def test_service_get_all_without_search_is_backward_compatible(db_session):
    """US3 (FR-011/contrato regra 2) — get_all sem search: comportamento original."""
    locs = _criar_locais_base(db_session)

    all_no_arg = LocationService.get_all(db_session)
    all_none = LocationService.get_all(db_session, search=None)
    all_blank = LocationService.get_all(db_session, search="   ")

    assert {x.id for x in all_no_arg} == {x.id for x in all_none} == {x.id for x in all_blank}
    assert len(all_no_arg) == 3
    # ordenação atual preservada: branch, department, name
    expected = sorted(all_no_arg, key=lambda x: (x.branch, x.department, x.name))
    assert [x.id for x in all_no_arg] == [x.id for x in expected]


def test_api_rest_locations_unchanged(client, db_session):
    """US3 (contrato regra 3) — API REST /api/v1/locations inalterada (sem search exposto)."""
    locs = _criar_locais_base(db_session)

    resp = client.get("/api/v1/locations")

    assert resp.status_code == 200
    data = resp.json()
    ids = {item["id"] for item in data}
    assert {locs["controle"].id, locs["gabinete"].id, locs["patrimonio_sede"].id} <= ids
    # sem termo, a API não é filtrada mesmo recebendo o parâmetro não-documentado
    resp_ignored = client.get("/api/v1/locations", params={"search": "IPMJP"})
    assert len(resp_ignored.json()) == len(data)


def test_search_is_read_only(client, db_session):
    """US3 (spec RN/FR-012) — A pesquisa não cria, altera ou exclui locais."""
    locs = _criar_locais_base(db_session)
    snapshot = {
        x.id: (x.name, x.branch, x.department, x.building, x.floor, x.room, x.manager_name)
        for x in LocationService.get_all(db_session)
    }

    client.get("/locations", params={"search": "Controle"})
    client.get("/locations", params={"search": "zzz-inexistente"})
    client.get("/locations")

    all_after = LocationService.get_all(db_session)
    assert len(all_after) == len(snapshot)
    for x in all_after:
        assert (x.name, x.branch, x.department, x.building, x.floor, x.room, x.manager_name) == snapshot[x.id]
