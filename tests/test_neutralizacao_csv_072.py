"""COR-03 (`specs/072-pentest-auditoria-adversarial`) — SEC-003, CWE-1236.

Neutralização de fórmula nas exportações CSV do `ReportService` (fidcha COR-03
de `achados/plano-correcao.md`). Reproduz os vetores do TC-27 (EV-030) em nível
unitário e no caminho real de exportação do inventário, e preserva o invariante
de números negativos legítimos (`-150` intacto).

Nenhum teste existente é alterado (FR-039/Constitution VIII).
"""

import csv
import io

from app.services.report_service import ReportService

# Células que NÃO podem avaliar como fórmula (saiem prefixadas com apóstrofo)
VEICULOS_FORMULA = [
    "=cmd|' /C calc'!A0",       # payload exato do TC-27 (EV-030)
    "+1+1",
    "-2+3",
    "@SUM(1+1)*cmd",
    "\t=SUM(1,1)",              # variante com tab inicial (ficha COR-03)
    " \r=1",                    # variante com espaço/CRLF inicial
]

# Números negativos legítimos do relatório — permanecem SEM prefixo
NUMEROS_LEGITIMOS = ["-150", "-150.00", "-150,50", "-42"]


def _celulas_leitura(linha_csv: str) -> list:
    """Lê uma linha CSV emitida pelo serviço como uma planilha faria."""
    return [c for c in next(csv.reader(io.StringIO(linha_csv), delimiter=";"))]


def _prefixado(celula: str) -> bool:
    """A célula saiu como texto (prefixo apóstrofo), não como fórmula."""
    return celula.startswith("'")


# ============================================================================
# Unitário — ponto único de neutralização
# ============================================================================

def test_vetores_formula_sao_prefixados_na_saida():
    """Vetor CSV Injection → célula emitida com apóstrofo (nunca como fórmula)."""
    for vetor in VEICULOS_FORMULA:
        linha = ReportService._csv_line([vetor])
        celulas = _celulas_leitura(linha)
        assert len(celulas) == 1, vetor
        assert _prefixado(celulas[0]), f"vetor {vetor!r} saiu cru: {celulas[0]!r}"


def test_numeros_negativos_legitimos_permanecem_intactos():
    """`-150` (e variantes) é número e deve continuar sem prefixo (FR-038)."""
    for numero in NUMEROS_LEGITIMOS:
        linha = ReportService._csv_line([numero])
        celulas = _celulas_leitura(linha)
        assert celulas[0] == numero, f"número mutado: {celulas[0]!r} ≠ {numero!r}"


def test_linha_mista_do_inventario_prefixa_so_a_formula():
    """Linha com mistura: só as células fórmula são tocadas — as demais intactas."""
    valores = ["T-001", "=1+1", "1234.56", "-0.10", "Nota fiscal comum", "+2+3"]
    saida = ReportService._csv_line(valores)
    celulas = _celulas_leitura(saida)
    esperado = [
        "T-001", "'=1+1", "1234.56", "-0.10", "Nota fiscal comum", "'+2+3",
    ]
    assert celulas == esperado


def test_valor_nao_texto_passa_intacto():
    """Ints/floats (campos numéricos emitidos como número) não são mutados."""
    assert ReportService._csv_line([150]) == "150\r\n"
    assert ReportService._csv_line([-150]) == "-150\r\n"


# ============================================================================
# Caminho real — exportação do inventário com campos de fórmula (TC-27)
# ============================================================================

def test_export_inventario_csv_com_formula_e_neutralizado(db_session):
    """Bem com jornadas de fórmula nos campos (payload do TC-27) → nenhuma
    célula do CSV emitido inicia com caractere de fórmula; `-` numérico intacto."""
    from app.models.asset import Asset
    from app.models.enums import AssetCategory

    db_session.add(Asset(
        tag="COR3-0001",
        name="=cmd|' /C calc'!A0",
        category=AssetCategory.NOTEBOOK,
        brand="+1+1",
        model="-2+3",
        serial_number="COR3-SER-0001",
        notes="@SUM(1+1)*cmd",
        purchase_value=1.0,
    ))
    db_session.commit()

    corpo = ReportService.generate_inventory_csv(db_session)

    formula_na_saida = []
    for celulas in csv.reader(io.StringIO(corpo), delimiter=";"):
        for celula in celulas:
            # célula CRUA de fórmula = começa com =/+/@ ou `-` não-numérico
            bruto = celula.lstrip(" \t\r\n")
            if (
                bruto[:1] in ("=", "+", "@")
                or (bruto[:1] == "-" and not bruto.lstrip("-").replace(".", "").replace(",", "").isdigit())
            ):
                formula_na_saida.append(celula)
    assert formula_na_saida == [], f"células de fórmula cruas na saída: {formula_na_saida}"

    linha_bem = [l for l in corpo.splitlines() if "COR3-0001" in l]
    assert len(linha_bem) == 1
    assert "'=cmd" in linha_bem[0] and "'+1+1" in linha_bem[0] and "'-2+3" in linha_bem[0]
