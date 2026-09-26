"""Validação local da Feature 044 — renderiza /assets/labels via TestClient e
mede as colunas da tabela de seleção com um layout engine real (WeasyPrint) sobre
o CSS real do app (bootstrap vendor local + style.css + <style> embutido do template).

Somente leitura do app: nenhum arquivo do app é alterado. Apenas media=screen
(tela não-relatório — R10: sem bloco de impressão nesta feature; a folha de
etiquetas #labels-print-area não é medida nem alterada).

Uso: .venv/bin/python specs/044-etiquetas-larguras-colunas/validar_local.py [larguras...]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BASE_CSS = ROOT / "app/web/static/css/style.css"
VENDOR_CSS = ROOT / "app/web/static/vendor/css/bootstrap.min.css"
OUT = Path(__file__).resolve().parent / "validacao_local.out.md"

COLS = ["Checkbox", "Tombamento", "Equipamento", "Setor", "Localização"]
CLS = ["c0", "c1", "c2", "c3", "c4"]
TBL = "etiq-table"


def build_html(body_html: str, viewport: int, dark: bool) -> str:
    """Recria o shell do base.html com os assets reais (vendor local)."""
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


def measure(html: str) -> dict:
    from weasyprint import HTML  # import tardio: mensagem de erro clara se ausente
    doc = HTML(string=html, base_url=str(ROOT), media_type="screen").render()
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
    """Semeia equipamentos cobrindo os edge cases do quickstart (se ainda não houver)."""
    from app.models.asset import Asset
    from app.models.location import Location
    from app.models.enums import AssetStatus
    if db.query(Asset).filter(Asset.tag == "IMPJP1456VAL").count() > 0:
        return
    locs = {
        "fundo": Location(name="IPMJP - Fundo Municipal de Previdência", branch="IPMJP",
                          department="Setor de Análise de Benefícios"),
        "anali": Location(name="IPMJP - Setor de Análise de Benefícios", branch="IPMJP",
                          department="Gabinete da Superintendência"),
        "jurid": Location(name="IPMJP - Assessoria Jurídica", branch="IPMJP",
                          department="Assessoria Jurídica"),
        "super": Location(name="IPMJP - Superintendência Adjunta", branch="IPMJP",
                          department="Setor de Contabilidade"),
    }
    for loc in locs.values():
        db.add(loc)
    db.flush()
    casos = [
        # tag, nome, marca, modelo, local
        ("IMPJP679450VAL", "Computador Lenovo ThinkCentre M720q Tiny i7", "Dell", "OptiPlex 7090 Micro", locs["fundo"]),
        ("IMPJP1456VAL", "Computador Dell OptiPlex 7090", "Dell", "OptiPlex 7090", locs["anali"]),
        ("IMPJP777VAL", "Impressora Multifuncional Laser Colorida Epson EcoTank", None, None, locs["anali"]),
        ("IMPJP888VAL", "Notebook", None, None, None),
        ("IMPJP999VAL", "Ar Condicionado Split Hi-Wall Inverter 12000 BTUs Quente e Frio", "LG", "Dual Inverter Voice", locs["jurid"]),
        ("IMPJP101VAL", "Cadeira", None, None, locs["super"]),
        ("IMPJP102VAL", "Servidor Rack Dell PowerEdge R750 Dual Xeon Silver 4310 128GB", "Dell", "PowerEdge R750", locs["fundo"]),
    ]
    for tag, nome, marca, modelo, loc in casos:
        db.add(Asset(tag=tag, name=nome, brand=marca, model=modelo, location=loc,
                     status=AssetStatus.AVAILABLE))
    db.commit()


def main():
    widths = [int(a) for a in sys.argv[1:]] or [1440, 1152, 1024, 768, 375]
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import Base, get_db
    from tests.conftest import engine, TestingSessionLocal, _override_get_db
    from app.services.auth_service import create_user

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        create_user(db, username="val044.owner", password="Val044!senha",
                    full_name="Dono da Validação Quarenta e Quatro", is_admin=True)
        _seed_dados(db)
    finally:
        db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        client.post("/api/v1/auth/login",
                    data={"username": "val044.owner", "password": "Val044!senha"})
        resp = client.get("/assets/labels")
        assert resp.status_code == 200, resp.status_code
        body = resp.text
    app.dependency_overrides.clear()

    # Extrai o card da tabela + <style> embutido (bloco content do template)
    m = re.search(r"(<style>.*?</style>)", body, re.S)
    inline_style = m.group(1) if m else ""
    i_ini = body.find('class="card no-print"')
    i_ini = body.rfind("<div", 0, i_ini) if i_ini > 0 else 0
    table_html = body[i_ini:]

    lines = ["# validacao local 044 — medições WeasyPrint (screen)", ""]
    for vp in widths:
        for dark in (False, True):
            html = build_html(inline_style + table_html, vp, dark)
            r = measure(html)
            total = sum(v for v in r["cols"].values() if v)
            lines.append(f"## viewport {vp}px {'dark' if dark else 'light'}")
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
