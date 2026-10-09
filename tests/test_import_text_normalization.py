"""Regressão: normalização de texto na importação (travessão de autocorreção
de planilhas, NBSP e espaços múltiplos) — parse_csv e _apply_mapping_to_rows."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.import_service import _normalize_text, parse_csv


def test_normalize_text_travessao_nbsp_espacos():
    assert _normalize_text("IPMJP \u2013 Sede \u2013 X") == "IPMJP - Sede - X"
    assert _normalize_text("IPMJP \u2014 Sede") == "IPMJP - Sede"
    assert _normalize_text("IPMJP\u00a0-\u00a0Se\u00e7\u00e3o") == "IPMJP - Se\u00e7\u00e3o"
    assert _normalize_text("A  B\t C") == "A B C"
    assert _normalize_text("") == ""


def test_parse_csv_normaliza_local_com_travessao():
    content = (
        "tombamento,equipamento,categoria,locations\n"
        "IPMJP9999,Notebook,Notebook,IPMJP \u2013 Sede \u2013 Superintend\u00eancia Adjunta\n"
    )
    rows, errors = parse_csv(content)
    assert errors == []
    assert rows[0]["localizacao"] == "IPMJP - Sede - Superintend\u00eancia Adjunta"


def test_parse_csv_normaliza_nbsp_e_espacos_duplos():
    content = (
        "tombamento,equipamento,categoria,locations\n"
        "IPMJP9999,Notebook,Notebook,IPMJP\u00a0-\u00a0Sede\u00a0-  Se\u00e7\u00e3o  de  Suporte\n"
    )
    rows, errors = parse_csv(content)
    assert errors == []
    assert rows[0]["localizacao"] == "IPMJP - Sede - Se\u00e7\u00e3o de Suporte"


def test_parse_csv_preserva_acentos_e_conteudo():
    content = (
        "tombamento,equipamento,categoria,locations\n"
        "IPMJP9999,Cafeteira,Equipamento,IPMJP - Sede - Ouvidoria\n"
    )
    rows, errors = parse_csv(content)
    assert errors == []
    assert rows[0]["equipamento"] == "Cafeteira"
    assert rows[0]["localizacao"] == "IPMJP - Sede - Ouvidoria"


def test_apply_mapping_to_rows_normaliza():
    from app.web.routers.shared import _apply_mapping_to_rows

    mapping = {
        "tombamento": "tombamento",
        "equipamento": "equipamento",
        "categoria": "categoria",
        "locations": "localizacao",
    }
    content = (
        "tombamento,equipamento,categoria,locations\n"
        "IPMJP9999,Notebook,Notebook,IPMJP \u2013 Sede \u2013 Superintend\u00eancia Adjunta\n"
    )
    rows = _apply_mapping_to_rows(content, mapping, kind="assets")
    assert rows[0]["resolved"]["localizacao"] == (
        "IPMJP - Sede - Superintend\u00eancia Adjunta"
    )
