"""Feature 006 — Pesquisa de Colaboradores (tela /custodians).

Testes organizados por user story da spec:
- US1: localizar colaborador rapidamente (combinada, parcial, 5 campos)
- US2: pesquisa tolerante (case-insensitive, estados vazios, limpeza)
- US3: integridade da tela existente (não-regressão, read-only)

Fixtures `client` (sessão autenticada) e `db_session` vêm de tests/conftest.py.
Nenhum teste existente é editado (Constitution VIII).
"""
import pytest

from app.schemas.custodian import CustodianCreate
from app.services.custodian_service import CustodianService


def _criar_colaboradores_base(db_session):
    """Massa de teste: 3 colaboradores com campos distintos (US1/US2/US3)."""
    return {
        "amanda_silva": CustodianService.create(db_session, CustodianCreate(
            registration_code="MAT-1036",
            name="Amanda Silva Nunes",
            email="amanda.nunes36@empresa.com",
            role="Gerente de Contas",
            department="Comercial",
        )),
        "amanda_teixeira": CustodianService.create(db_session, CustodianCreate(
            registration_code="MAT-1037",
            name="Amanda Teixeira Rodrigues",
            email="amanda.teixeira@empresa.com",
            role="Analista de Vendas",
            department="Comercial",
        )),
        "bruno": CustodianService.create(db_session, CustodianCreate(
            registration_code="MAT-2001",
            name="Bruno Cardoso",
            email="bruno.cardoso@empresa.com",
            role="Auxiliar de Logística",
            department="Logística",
        )),
    }


# ---- US1: Localizar um colaborador rapidamente ----

def test_search_by_name_returns_only_matches(client, db_session):
    """US1 (CA-002) — Busca por nome: somente os correspondentes aparecem."""
    c = _criar_colaboradores_base(db_session)

    resp = client.get("/custodians", params={"search": "Amanda"})

    assert resp.status_code == 200
    body = resp.text
    assert c["amanda_silva"].name in body
    assert c["amanda_teixeira"].name in body
    assert c["bruno"].name not in body          # fora do resultado


def test_search_by_registration_code(client, db_session):
    """US1 (CA-003) — Busca por matrícula completa e parcial."""
    c = _criar_colaboradores_base(db_session)

    resp_full = client.get("/custodians", params={"search": "MAT-1036"})
    assert resp_full.status_code == 200
    assert c["amanda_silva"].name in resp_full.text
    assert c["amanda_teixeira"].name not in resp_full.text

    resp_partial = client.get("/custodians", params={"search": "1036"})
    assert resp_partial.status_code == 200
    assert c["amanda_silva"].name in resp_partial.text
    assert c["bruno"].name not in resp_partial.text


def test_search_by_department(client, db_session):
    """US1 (CA-004) — Busca por departamento: os dois do Comercial aparecem."""
    c = _criar_colaboradores_base(db_session)

    resp = client.get("/custodians", params={"search": "Comercial"})

    assert resp.status_code == 200
    assert c["amanda_silva"].name in resp.text
    assert c["amanda_teixeira"].name in resp.text
    assert c["bruno"].name not in resp.text


def test_search_by_role(client, db_session):
    """US1 (CA-005) — Busca por cargo: 'Gerente' encontra 'Gerente de Contas'."""
    c = _criar_colaboradores_base(db_session)

    resp = client.get("/custodians", params={"search": "Gerente"})

    assert resp.status_code == 200
    assert c["amanda_silva"].name in resp.text
    assert c["amanda_teixeira"].name not in resp.text
    assert c["bruno"].name not in resp.text


def test_search_by_email_partial(client, db_session):
    """US1 (CA-006) — Busca por trecho do e-mail."""
    c = _criar_colaboradores_base(db_session)

    resp = client.get("/custodians", params={"search": "amanda.nunes36"})

    assert resp.status_code == 200
    assert c["amanda_silva"].name in resp.text
    assert c["amanda_teixeira"].name not in resp.text


# ---- US2: Pesquisa tolerante e com feedback claro ----

def test_search_case_insensitive_equivalence(client, db_session):
    """US2 (CA-007) — AMANDA / Amanda / amanda produzem resultados equivalentes."""
    c = _criar_colaboradores_base(db_session)

    bodies = []
    for termo in ("AMANDA", "Amanda", "amanda"):
        resp = client.get("/custodians", params={"search": termo})
        assert resp.status_code == 200
        bodies.append(resp.text)

    for body in bodies:
        assert c["amanda_silva"].name in body
        assert c["amanda_teixeira"].name in body
        assert c["bruno"].name not in body


def test_search_partial_match(client, db_session):
    """US2 (FR-008) — Parcial: 'Bruno' encontra 'Bruno Cardoso' (e vice-versa, parte do nome)."""
    c = _criar_colaboradores_base(db_session)

    resp = client.get("/custodians", params={"search": "Cardos"})

    assert resp.status_code == 200
    assert c["bruno"].name in resp.text
    assert c["amanda_silva"].name not in resp.text


def test_search_combined_across_fields(client, db_session):
    """US2 (FR-007, correção C1) — Termo que casa em campos diferentes de
    colaboradores distintos: departamento 'Logística' de um, nome de outra."""
    logistica_bem = CustodianService.create(db_session, CustodianCreate(
        registration_code="MAT-2002",
        name="Logística Silva",
        email="logistica.silva@empresa.com",
        role="Coordenadora",
        department="Comercial",
    ))
    _criar_colaboradores_base(db_session)

    resp = client.get("/custodians", params={"search": "Logística"})

    assert resp.status_code == 200
    body = resp.text
    assert "Bruno Cardoso" in body           # casa no DEPARTAMENTO de Bruno
    assert logistica_bem.name in body        # casa no NOME dela
    assert c_amarilho_not_in(body)


def c_amarilho_not_in(body):
    """Auxiliar do caso combinado: Amarelas de outra área não aparecem."""
    return "Amanda Silva Nunes" not in body and "Amanda Teixeira Rodrigues" not in body


def test_search_no_results_shows_empty_state(client, db_session):
    """US2 (CA-008/FR-010) — Termo inexistente: mensagem clara, sem linhas, sem erro."""
    _criar_colaboradores_base(db_session)

    resp = client.get("/custodians", params={"search": "zzz-inexistente-xyz"})

    assert resp.status_code == 200
    body = resp.text
    assert "Nenhum colaborador encontrado." in body
    assert "MAT-1036" not in body            # nenhuma linha de colaborador


def test_search_field_is_repopulated(client, db_session):
    """US2 (contrato) — O input volta preenchido com o termo pesquisado."""
    _criar_colaboradores_base(db_session)

    resp = client.get("/custodians", params={"search": "Amanda"})

    assert resp.status_code == 200
    assert 'value="Amanda"' in resp.text


def test_search_empty_or_blank_returns_full_list(client, db_session):
    """US2 (CA-009/FR-011) — search vazio ou só espaços: lista completa, sem estado de busca."""
    c = _criar_colaboradores_base(db_session)

    resp_empty = client.get("/custodians", params={"search": ""})
    resp_blank = client.get("/custodians", params={"search": "   "})
    resp_none = client.get("/custodians")

    for resp in (resp_empty, resp_blank, resp_none):
        assert resp.status_code == 200
        assert c["amanda_silva"].name in resp.text
        assert c["bruno"].name in resp.text
        assert "Nenhum colaborador encontrado." not in resp.text


# ---- US3: Integridade da tela existente ----

def test_results_preserve_links_actions_and_asset_count(client, db_session):
    """US3 (CA-010/RN-003) — Resultados mantêm link do nome, contagem de bens e ações."""
    from app.models.asset import Asset
    from app.models.enums import AssetCategory, AssetStatus
    from app.schemas.asset import AssetCreate
    from app.services.asset_service import AssetService

    c = _criar_colaboradores_base(db_session)
    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-00601",
        name="Notebook da Amanda",
        category=AssetCategory.NOTEBOOK,
        initial_custodian_id=c["amanda_silva"].id,
    ))
    db_session.expire(asset)
    assert asset.status == AssetStatus.IN_USE   # bem vinculado → contagem 1

    resp = client.get("/custodians", params={"search": "Amanda"})

    assert resp.status_code == 200
    body = resp.text
    assert f'href="/custodians/{c["amanda_silva"].id}"' in body   # link do nome intacto
    assert "Ver Bens" in body                                     # ação intacta
    # contagem = 1 bem (badge com espaçamento próprio do template)
    import re as _re
    assert _re.search(r"badge rounded-pill[^>]*>\s*1\s*<", body)


def test_service_get_all_without_search_is_backward_compatible(db_session):
    """US3 (FR-014/contrato regra 2) — get_all sem search: comportamento original."""
    c = _criar_colaboradores_base(db_session)

    all_no_arg = CustodianService.get_all(db_session)
    all_none = CustodianService.get_all(db_session, search=None)
    all_blank = CustodianService.get_all(db_session, search="   ")
    active_only = CustodianService.get_all(db_session, active_only=True)

    assert {x.id for x in all_no_arg} == {x.id for x in all_none} == {x.id for x in all_blank}
    assert len(all_no_arg) == 3
    assert len(active_only) == 3   # todos ativos na massa


def test_base_route_without_search_renders_current_screen(client, db_session):
    """US3 (CA-011) — GET /custodians sem search: tela atual, lista completa, sem estado de busca."""
    c = _criar_colaboradores_base(db_session)

    resp = client.get("/custodians")

    assert resp.status_code == 200
    body = resp.text
    assert c["amanda_silva"].name in body
    assert c["amanda_teixeira"].name in body
    assert c["bruno"].name in body
    assert "Nenhum colaborador encontrado." not in body
    assert "Nenhum colaborador cadastrado" not in body   # há colaboradores


def test_search_is_read_only(client, db_session):
    """US3 (RN-001) — A pesquisa não cria, altera ou exclui colaboradores."""
    c = _criar_colaboradores_base(db_session)
    snapshot = {
        x.id: (x.registration_code, x.name, x.email, x.role, x.department)
        for x in CustodianService.get_all(db_session)
    }

    client.get("/custodians", params={"search": "Amanda"})
    client.get("/custodians", params={"search": "zzz-inexistente"})
    client.get("/custodians")

    assert CustodianService.get_all(db_session).__len__() == len(snapshot)
    for x in CustodianService.get_all(db_session):
        assert (x.registration_code, x.name, x.email, x.role, x.department) == snapshot[x.id]
