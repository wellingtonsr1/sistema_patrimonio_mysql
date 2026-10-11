"""Testes unitários do helper de paginação — feature 068 (T004).

Contrato: specs/068-paginacao-listas-e-relatorios-integros/contracts/
web-list-pagination-contract.md (FR-002 normalização de `page`).

Somente puro (sem banco/client): roda em < 0,1 s e não depende de fixtures.
"""

from app.utils.pagination import DEFAULT_PAGE_SIZE, offset_for, page_meta, parse_page


def test_parse_page_normaliza_valores_invalidos_para_1():
    """FR-002: ausente/vazio/não numérico/negativo -> página 1 (nunca 4xx)."""
    assert parse_page(None) == 1
    assert parse_page("") == 1
    assert parse_page("   ") == 1
    assert parse_page("abc") == 1
    assert parse_page("1.5") == 1
    assert parse_page("0") == 1
    assert parse_page("-1") == 1
    assert parse_page(True) == 1  # bool não é página
    assert parse_page([1]) == 1


def test_parse_page_aceita_inteiro_e_string_numerica():
    assert parse_page(3) == 3
    assert parse_page("3") == 3
    assert parse_page(" 7 ") == 7
    assert parse_page("007") == 7


def test_offset_for_usa_page_size_padrao_e_normaliza():
    assert offset_for(1) == 0
    assert offset_for(2) == 200
    assert offset_for(3, 50) == 100
    assert offset_for("2") == 200
    assert offset_for("abc") == 0
    assert offset_for(0) == 0
    assert offset_for(1, 0) == 0  # page_size inválido cai no padrão
    assert offset_for(2, DEFAULT_PAGE_SIZE) == 200


def test_page_meta_calcula_intervalo_e_bandeiras():
    meta = page_meta(250, 1, 200)
    assert meta == {
        "page": 1,
        "page_size": 200,
        "pages": 2,
        "total": 250,
        "start": 1,
        "end": 200,
        "has_prev": False,
        "has_next": True,
    }
    meta2 = page_meta(250, 2, 200)
    assert meta2["start"] == 201
    assert meta2["end"] == 250
    assert meta2["has_prev"] is True
    assert meta2["has_next"] is False


def test_page_meta_recorta_pagina_alem_do_fim():
    """FR-002: página 99999 -> última válida com dados (SC-002)."""
    meta = page_meta(450, 99999, 200)
    assert meta["page"] == 3
    assert meta["start"] == 401
    assert meta["end"] == 450
    assert meta["has_next"] is False
    assert meta["has_prev"] is True


def test_page_meta_estado_vazio_sem_controle_de_pagina():
    """FR-006: total 0 -> pages 1 (macro renderiza nada)."""
    meta = page_meta(0, 5, 200)
    assert meta["pages"] == 1
    assert meta["start"] == 0
    assert meta["end"] == 0
    assert meta["has_prev"] is False
    assert meta["has_next"] is False


def test_page_meta_total_negativo_ou_none_vira_zero():
    assert page_meta(-10, 1, 200)["total"] == 0
    assert page_meta(None, 1, 200)["total"] == 0


def test_page_meta_page_size_invalido_cai_no_padrao():
    assert page_meta(250, 1, 0)["page_size"] == DEFAULT_PAGE_SIZE
    assert page_meta(250, 1, -5)["page_size"] == DEFAULT_PAGE_SIZE
    assert page_meta(250, 1, "x")["page_size"] == DEFAULT_PAGE_SIZE


# ---------------------------------------------------------------------------
# T005 — macro `macros/pagination.html` (renderização isolada, sem app/banco)
# ---------------------------------------------------------------------------

def _render_pager(page, pages, total, start, end, query="status=EM_USO"):
    """Renderiza a macro isoladamente (Jinja puro + request stub)."""
    from types import SimpleNamespace

    from jinja2 import Environment, FileSystemLoader
    from starlette.datastructures import QueryParams

    env = Environment(loader=FileSystemLoader("app/web/templates"))
    tpl = env.from_string(
        "{% from 'macros/pagination.html' import pager %}"
        "{{ pager(page, pages, total, start, end, request) }}"
    )
    request = SimpleNamespace(
        query_params=QueryParams(query), url=SimpleNamespace(path="/assets")
    )
    return tpl.render(request=request, page=page, pages=pages, total=total, start=start, end=end)


def test_macro_pager_oculto_quando_cabe_em_uma_pagina():
    """FR-006/SC-004: pages <= 1 -> nada é renderizado (sem ruído visual)."""
    assert _render_pager(1, 1, 50, 1, 50).strip() == ""
    assert _render_pager(1, 1, 0, 0, 0).strip() == ""


def test_macro_pager_renderiza_indicador_e_links_preservando_filtros():
    """FR-004/FR-007/FR-022: indicador X–Y de Z, Anterior/Próxima com filtros."""
    html = _render_pager(2, 3, 450, 201, 400)
    assert 'data-testid="pager"' in html  # marcador do AC15
    assert "Mostrando 201–400 de 450" in html
    assert "Página 2 de 3" in html
    assert 'rel="prev"' in html and 'rel="next"' in html
    assert "status=EM_USO" in html  # FR-007: filtro sobrevive à troca de página
    assert "page=1" in html and "page=3" in html
    assert "flex-sm-row" in html  # FR-022: responsivo (360 px -> desktop)


def test_macro_pager_desabilita_botoes_nos_extremos():
    """Borda inferior/superior: botão correspondente fica `disabled` (sem link)."""
    first = _render_pager(1, 3, 450, 1, 200)
    assert 'rel="prev"' not in first and 'rel="next"' in first
    last = _render_pager(3, 3, 450, 401, 450)
    assert 'rel="next"' not in last and 'rel="prev"' in last
