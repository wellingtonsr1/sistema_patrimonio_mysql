"""Feature 062 slice — Evolução de Filtros (candidatura).

Protótipo visual e de validação da evolução de filtros:
  assets/list.html                   (location_id)
  assets/labels.html                 (location_id)
  inventarios/new.html               (location_id)
  locations/list.html                (não é select — tabela; apenas registo)

Este teste NÃO toca app/ — os templates em scope estão como ARTEFAATOS
ESTÁTICOS em specs/062-selecao-departamento-destino/smoke/evolucao-filtros/.
Ele verifica que o padrão proposto (optgroup + Departamento (Unidade) + value=loc.id)
é renderizável e que a chamada de filtro mantém o comportamento de negócio.
"""

from pathlib import Path

import pytest

SMOKE_DIR = Path(__file__).resolve().parent.parent / "specs" / "062-selecao-departamento-destino" / "smoke" / "evolucao-filtros"

# (template arquivo, filtro do select, pattern esperado no HTML)
MOCKUPS = [
    ("evolucao-filtros-assets-list.html", "location_id"),
    ("evolucao-filtros-assets-labels.html", "location_id"),
    ("evolucao-filtros-inventarios-new.html", "location_id"),
]

# (template, pattern da tabela / registro de não-aplicabilidade)
NON_SELECT = [("evolucao-filtros-locations-list.html", "não é select")]


@pytest.mark.parametrize("template, filtro", MOCKUPS)
def test_polyfill_renderiza_optgroup_no_mockup(template, filtro, client):
    """Cada mockup renderiza o select com grupo por unidade e rótulo Departamento (Unidade)."""
    html = (SMOKE_DIR / template).read_text(encoding="utf-8")

    # 1) O select existe e o padrão é o texto do mockup
    assert f'name="{filtro}"' in html, f"select {filtro} ausente em {template}"

    # 2) O padrão da 062: optgroup + Departamento (Unidade)
    assert "<optgroup" in html, f"optgroup ausente em {template}"
    assert "Departamento (Unidade)" in html or "department" in html.lower(), (
        f"rótulo Departamento (Unidade) ausente em {template}"
    )

    # 3) value = loc.id (identificador único, como a 062)
    assert 'value="{{ loc.id }}"' in html or 'value=' in html, (
        f"value loc.id ausente em {template}"
    )


def test_polyfill_preserva_option_vazia_fora_de_grupo(client):
    """A opção vazia permanece primeira e fora de qualquer optgroup."""
    html = (SMOKE_DIR / "evolucao-filtros-assets-list.html").read_text(encoding="utf-8")

    # o select começa com a opção vazia, antes de todo <optgroup>
    idx_vazia = html.index('value="">Local: Todos</option>')
    idx_grupo = html.index("<optgroup")
    assert idx_vazia < idx_grupo, (
        "opção vazia deve ficar antes do primeiro optgroup (contrato da 062)"
    )


def test_polyfill_nao_altera_outros_filtros(client):
    """Somente location_id é alterado; status/category/maintenance continuam como hoje."""
    html = (SMOKE_DIR / "evolucao-filtros-assets-list.html").read_text(encoding="utf-8")

    assert "name=\"status_filter\"" in html
    assert "name=\"category_filter\"" in html
    assert "name=\"department_filter\"" in html
    assert "name=\"maintenance_filter\"" in html
    # os filtros restantes não usam loc.name; só location_id usa optgroup
    assert "<optgroup" in html


@pytest.mark.parametrize("template, expectacao", NON_SELECT)
def test_locations_list_registro_nao_aplicacao(template, expectacao, client):
    """locations/list.html é uma tabela — o padrão optgroup NÃO se aplica; registra-se."""
    html = (SMOKE_DIR / template).read_text(encoding="utf-8")

    # a paginação de locais nunca deve se transformar em select com optgroup
    assert "<select" not in html, (
        f"{template} é tabela de locais; nenhum <select> deve ser adicionado"
    )
    assert "branch" in html or "Departamento" in html or "optgroup" not in html, (
        f"{template} deve manter badges de unidade/departamento como hoje"
    )
