"""Vendoring dos CDNs — Feature 059 (M6 da análise 2026-09-30).

Problema: base.html/login.html/setup.html carregavam Bootstrap, Icons,
Chart.js (SEM versão fixada!), QRCode.js e fonte Plus Jakarta Sans de
jsdelivr/googleapis — contradição com o PWA offline (033), falha total
de apresentação se o firewall bloquear os CDNs e risco latente de major
nova do Chart.js quebrar o dashboard sem mudança local.

Guard (FR-004): qualquer referência CDN nos templates FAILA a suíte.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = PROJECT_ROOT / "app" / "web" / "templates"
VENDOR = PROJECT_ROOT / "app" / "web" / "static" / "vendor"

CDN_PADRAO = r"cdn\.jsdelivr|fonts\.googleapis|fonts\.gstatic|googleapis\.com|gstatic\.com"


# ---------------------------------------------------------------------------
# FR-004 / SC-001 — guarda anti-CDN em TODOS os templates
# ---------------------------------------------------------------------------

def test_guard_nenhum_template_referencia_cdn():
    import re

    infratores: list[str] = []
    for tpl in TEMPLATES.rglob("*.html"):
        conteudo = tpl.read_text(encoding="utf-8")
        if re.search(CDN_PADRAO, conteudo):
            infratores.append(str(tpl.relative_to(PROJECT_ROOT)))
    assert not infratores, (
        f"Templates ainda referenciam CDN externo (use /static/vendor/): {infratores}"
    )


# ---------------------------------------------------------------------------
# FR-002 — vendors versionados presentes
# ---------------------------------------------------------------------------

def test_chartjs_vendored_umd_presente_e_com_versao():
    chart = VENDOR / "js" / "chart.umd.js"
    assert chart.is_file(), "chart.umd.js ausente em static/vendor/js/"
    conteudo = chart.read_text(encoding="utf-8", errors="ignore")[:400]
    assert "4.4" in conteudo, "Chart.js deve ser a série 4.4 fixada (FR-002)"


def test_qrcode_vendored_presente():
    qr = VENDOR / "js" / "qrcode.min.js"
    assert qr.is_file(), "qrcode.min.js ausente em static/vendor/js/"


def test_bootstrap_vendor_continua_presente():
    for nome in (
        "css/bootstrap.min.css",
        "css/bootstrap-icons.css",
        "css/fonts/bootstrap-icons.woff2",
        "js/bootstrap.bundle.min.js",
    ):
        assert (VENDOR / nome).is_file(), f"vendor Bootstrap ausente: {nome}"


# ---------------------------------------------------------------------------
# FR-003 — fonte Plus Jakarta Sans local
# ---------------------------------------------------------------------------

def test_fonte_local_css_e_arquivos_presentes():
    css = VENDOR / "fonts" / "plus-jakarta-sans.css"
    assert css.is_file(), "plus-jakarta-sans.css ausente"
    conteudo = css.read_text(encoding="utf-8")
    assert "@font-face" in conteudo and "Plus Jakarta Sans" in conteudo
    # cada url() do CSS deve apontar para arquivo existente
    import re

    for caminho in re.findall(r"url\(([^)]+)\)", conteudo):
        relativo = caminho.strip("'\" ").split("?")[0]
        assert (VENDOR / "fonts" / relativo).is_file(), f"fonte ausente: {relativo}"


# ---------------------------------------------------------------------------
# FR-005 — SW precache com os vendors e CACHE_VERSION bumpada
# ---------------------------------------------------------------------------

def test_sw_allowlist_inclui_vendors_novos():
    sw = (PROJECT_ROOT / "app" / "web" / "static" / "js" / "sw.js").read_text(
        encoding="utf-8"
    )
    for asset in (
        "/static/vendor/js/chart.umd.js",
        "/static/vendor/js/qrcode.min.js",
        "/static/vendor/fonts/plus-jakarta-sans.css",
    ):
        assert asset in sw, f"allowlist do SW sem {asset} (FR-005)"


def test_sw_cache_version_bumpada_v33():
    """A 059 bumpou para v33; bumps posteriores (v34+ da 060) são evolução
    legítima — o guard exige no mínimo v33."""
    sw = (PROJECT_ROOT / "app" / "web" / "static" / "js" / "sw.js").read_text(
        encoding="utf-8"
    )
    import re

    m = re.search(r'CACHE_VERSION = "inventario-offline-v(\d+)"', sw)
    assert m, "CACHE_VERSION não encontrada"
    assert int(m.group(1)) >= 33, (
        f"CACHE_VERSION deve ser >= v33 (propagar allowlist da 059); atual: v{m.group(1)}"
    )
