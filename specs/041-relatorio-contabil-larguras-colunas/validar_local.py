"""Validação local da Feature 041 — renderiza /reports/inventory via TestClient e
mede as colunas da tabela com um layout engine real (WeasyPrint) sobre o CSS real
do app (bootstrap vendor local + style.css + <style> embutido do template).

Somente leitura do app: nenhum arquivo do app é alterado. Duas passadas por
cenário: media=screen (layout de tela — V0–V4) e media=print (prova de que o
papel não herda min-width/table-layout da tela — V6; os blocos @media print
C1–C10 do style.css + a regra de segurança da 041 ficam ativos).

Uso: .venv/bin/python specs/041-relatorio-contabil-larguras-colunas/validar_local.py [larguras...]
"""
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BASE_CSS = ROOT / "app/web/static/css/style.css"
VENDOR_CSS = ROOT / "app/web/static/vendor/css/bootstrap.min.css"
OUT = Path(__file__).resolve().parent / "validacao_local.out.md"

COLS = ["Tombamento", "Descrição", "Categoria", "Status", "Localização", "Responsável",
        "Data Compra", "Valor Aquisição", "Depreciação", "Valor Atual"]
CLS = ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10"]
TBL = "invrep-table"


def build_html(body_html: str, viewport: int, dark: bool) -> str:
    """Recria o shell do base.html com os assets reais (vendor local).
    @page por ÚLTIMO (vence o @page size:Auto do @media print do style.css)."""
    css = VENDOR_CSS.read_text(encoding="utf-8") + "\n" + BASE_CSS.read_text(encoding="utf-8")
    bg = "#111418" if dark else "#ffffff"
    color = "#e7eaee" if dark else "#1c2330"
    return f"""<!DOCTYPE html>
<html data-theme="{'dark' if dark else 'light'}"><head><meta charset="utf-8">
<style>{css}</style>
<style>
  html, body {{ margin: 0; padding: 0; width: {viewport}px; background: {bg}; color: {color}; }}
  body {{ font-family: sans-serif; }}
</style>
<style>@page {{ size: {viewport}px 4000px; margin: 0; }}</style>
</head><body>{body_html}</body></html>"""


def measure(html: str, media: str) -> dict:
    from weasyprint import HTML  # import tardio: mensagem de erro clara se ausente
    doc = HTML(string=html, base_url=str(ROOT), media_type=media).render()
    page = doc.pages[0]
    out = {"page_width": float(page.width)}
    found = {}
    state = {"table": None}

    def walk(box):
        el = getattr(box, "element", None)
        if el is not None:
            classes = (el.get("class") or "").split()
            if el.tag == "col" and classes and classes[0] in CLS and classes[0] not in found:
                found[classes[0]] = box
            if el.tag == "table" and state["table"] is None:
                state["table"] = box
            if TBL in classes and "table" not in out:
                out["table"] = box
        for child in getattr(box, "all_children", lambda: [])():
            walk(child)

    walk(page._page_box)
    cols = {}
    if found:
        for name, cls in zip(COLS, CLS):
            b = found.get(cls)
            cols[name] = round(b.width, 1) if b is not None else None
    else:
        # Fallback "antes" (V0): sem <colgroup>/classes — mede as células da
        # 1ª linha (distribuição real do layout automático).
        row = _first_row(state["table"])
        cells = [c for c in getattr(row, "all_children", lambda: [])()
                 if getattr(getattr(c, "element", None), "tag", None) in ("td", "th")] if row else []
        for i, name in enumerate(COLS):
            cols[name] = round(cells[i].width, 1) if i < len(cells) else None
    out["cols"] = cols
    tb = out.get("table") or state["table"]
    out["table_width"] = round(tb.width, 1) if tb is not None else None
    return out


def _first_row(table_box):
    """Primeira <tr> da árvore de boxes da tabela (ou None)."""
    if table_box is None:
        return None
    stack = [table_box]
    while stack:
        b = stack.pop(0)
        el = getattr(b, "element", None)
        if el is not None and el.tag == "tr":
            return b
        stack.extend(getattr(b, "all_children", lambda: [])())
    return None


def _seed_dados(db):
    """Semeia dados cobrindo os edge cases do quickstart (se ainda não houver)."""
    from app.models.user import User
    from app.models.asset import Asset
    from app.models.location import Location
    from app.models.custodian import Custodian
    from app.models.enums import AssetStatus, AssetCategory, AssetCondition
    if db.query(Asset).filter(Asset.tag == "TMB-2026-0439").count() > 0:
        return
    loc = Location(
        name="Secretaria Municipal de Educação - Almoxarifado Central Setor Norte",
        branch="Sede", department="Educação")
    cust = Custodian(
        registration_code="MAT-2026-0439",
        name="Maria Fernanda Oliveira Santos e Silva",
        email="maria.fernanda.oliveira.santos.e.silva@municipio.gov.br",
        role="Assessora Técnica Administrativa Pedagógica",
        department="Departamento de Estatística e Monitoramento de Indicadores Educacionais")
    db.add(loc)
    db.add(cust)
    db.flush()
    casos = [
        # tag, name, category, status, serial, com_local, com_cust, data, valor
        ("TMB-2026-0439", "Notebook Dell Latitude 5440 com fonte dedicada para validação de layout de tabela",
         AssetCategory.NOTEBOOK, AssetStatus.IN_USE, "SN-XYZ-123456789", True, True,
         datetime.datetime(2024, 1, 10), 12500.00),
        ("TMB-2026-0438", "Impressora Multifuncional Epson L395",
         AssetCategory.EQUIPMENT, AssetStatus.AVAILABLE, None, False, False, None, 15890.50),
        ("TMB-2026-0437", 'Monitor LG UltraWide 29"',
         AssetCategory.MONITOR, AssetStatus.IN_MAINTENANCE, None, True, True,
         datetime.datetime(2023, 7, 25), 120000.00),
    ]
    for tag, name, cat, st, serial, com_loc, com_cust, dt, val in casos:
        db.add(Asset(tag=tag, name=name, category=cat, status=st,
                     condition=AssetCondition.GOOD, serial_number=serial,
                     location_id=loc.id if com_loc else None,
                     custodian_id=cust.id if com_cust else None,
                     purchase_date=dt, purchase_value=val))
    db.commit()


def main():
    widths = [int(a) for a in sys.argv[1:]] or [1440, 1152, 1024, 768, 375, 2880]
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import Base, get_db
    from tests.conftest import engine, TestingSessionLocal, _override_get_db
    from app.services.auth_service import create_user

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        create_user(db, username="val041", password="Val041!senha",
                    full_name="Validador Quarenta e Um", is_admin=True)
        _seed_dados(db)
    finally:
        db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        client.post("/api/v1/auth/login",
                    data={"username": "val041", "password": "Val041!senha"})
        resp = client.get("/reports/inventory")
        assert resp.status_code == 200, resp.status_code
        body = resp.text
    app.dependency_overrides.clear()

    # Extrai o card do relatório + <style> embutido (bloco content do template)
    m = re.search(r"(<style>.*?</style>)", body, re.S)
    inline_style = m.group(1) if m else ""
    i_ini = body.find('class="page-header no-print"')
    i_ini = body.rfind("<div", 0, i_ini) if i_ini > 0 else 0
    table_html = body[i_ini:]

    lines = ["# validacao local 041 — medições WeasyPrint (screen = V0–V4 · print = V6)", ""]
    for vp in widths:
        for dark in (False, True):
            for media in ("screen", "print"):
                html = build_html(inline_style + table_html, vp, dark)
                r = measure(html, media)
                total = sum(v for v in r["cols"].values() if v)
                lines.append(f"## viewport {vp}px {'dark' if dark else 'light'} · {media}")
                lines.append(f"- page: {r['page_width']}px · tabela: {r['table_width']}px · soma cols: {round(total, 1)}px")
                for name in COLS:
                    w = r["cols"][name]
                    pct = round(100 * w / r["table_width"], 1) if (w and r["table_width"]) else "?"
                    lines.append(f"  - {name}: {w}px ({pct}%)")
                lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSalvo em {OUT}")


if __name__ == "__main__":
    main()
