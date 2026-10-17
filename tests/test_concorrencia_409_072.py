"""COR-05 (`specs/072-pentest-auditoria-adversarial`) — SEC-004/COR-05.

Lock de concorrência (MariaDB 1020/1213) mapeado para 409 (`Retry-After: 1`)
no handler central de `app/main.py` — reproduz a observação do TC-24/EV-027
(500 cru sob colisão) invertida em nível unitário com monkeypatch (ficha §3).

Nenhum teste existente é alterado (FR-039/Constitution VIII).
"""

import pytest
from sqlalchemy.exc import OperationalError

LOCKS_CONCORRENCIA = (1020, 1213)
_codes = pytest.mark.parametrize("codigo_mariadb", LOCKS_CONCORRENCIA)


def _operational_error_tb(codigo_mariadb: int) -> OperationalError:
    """OperationalError com `orig` no formato do pymysql/MariaDB real."""
    return OperationalError(
        "UPDATE assets SET ... WHERE id = %s",
        None,
        Exception(codigo_mariadb, "Record has changed since last read"),
    )


def _cria_bem(client) -> int:
    resp = client.post("/api/v1/assets", json={
        "tag": "COR5-0001",
        "name": "Bem da concorrência COR-05",
        "category": "NOTEBOOK",
        "purchase_value": 1.0,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@_codes
def test_lock_concorrencia_na_mutacao_responde_409_com_retry_after(
    client, monkeypatch, codigo_mariadb, db_session
):
    """PUT de bem sob OperationalError(1020/1213) → 409 amigável, sem 500,
    sem DSN/SQL do driver no corpo (ficha COR-05, criterio de reteste)."""
    asset_id = _cria_bem(client)

    from sqlalchemy.orm import Session

    def commit_sob_lock(self):
        raise _operational_error_tb(codigo_mariadb)

    monkeypatch.setattr(Session, "commit", commit_sob_lock)
    try:
        resp = client.put(
            f"/api/v1/assets/{asset_id}",
            json={"name": "Edição sob colisão"},
        )
    finally:
        monkeypatch.undo()  # restaura ANTES de qualquer commit de teardown
    assert resp.status_code == 409, resp.text
    assert resp.headers.get("retry-after") == "1"
    corpo = resp.text.lower()
    assert "conflito" in corpo and "tente novamente" in corpo
    assert "mariadb" not in corpo or codigo_mariadb not in corpo
    for vazamento in ("127.0.0.1:3307", "mysql+pymysql", "root@", "traceback",
                      "syntax error", "select 1 from", "info_schema"):
        assert vazamento.lower() not in corpo, vazamento


def test_operationalerror_fora_do_mapa_e_relancado(client, monkeypatch):
    """OperationalError com outra causa (ex.: 2006 server gone) NÃO é engolido:
    o handler relança — nenhum erro do driver é silenciado (FR-039)."""
    from sqlalchemy.orm import Session
    asset_id = _cria_bem(client)

    def commit_server_gone(self):
        raise _operational_error_tb(2006)

    monkeypatch.setattr(Session, "commit", commit_server_gone)
    with pytest.raises(OperationalError):
        client.put(
            f"/api/v1/assets/{asset_id}",
            json={"name": "Edição sob falha de conexão"},
        )
