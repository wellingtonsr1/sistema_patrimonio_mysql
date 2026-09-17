"""Feature 013 — Smoke test da âncora de impressão dos relatórios.

Verifica (via pytest) que os 3 templates de relatório renderizam o container
com a classe de escopo `report-print` — a âncora obrigatória do novo bloco
`@media print` (css-contract §1; research R9; remediação U1 do /speckit-analyze:
admin tem bypass em `require_permission`, confirmado em app/api/deps.py:110).

A validação de LAYOUT de impressão é manual/visual (quickstart §2) — pytest
não renderiza CSS; este teste é apenas o guarda da âncora de marcação.

Fixtures `client` (sessão autenticada admin) e `db_session` vêm de tests/conftest.py.
Nenhum teste existente é editado (Constitution VIII).
"""

import pytest

ROTAS_RELATORIOS = [
    "/reports/movements",
    "/reports/custodians",
    "/reports/inventory",
]


@pytest.mark.parametrize("rota", ROTAS_RELATORIOS)
def test_report_renders_print_scope_anchor(client, rota):
    """US1–US3 — cada relatório renderiza o container com a âncora `report-print`."""
    resp = client.get(rota)

    assert resp.status_code == 200, f"{rota} → {resp.status_code}"
    assert 'class="card p-4 report-print"' in resp.text, (
        f"{rota}: container do relatório sem a âncora de impressão `report-print`"
    )
