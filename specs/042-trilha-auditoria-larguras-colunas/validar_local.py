"""Validação local da Feature 042 — renderiza /reports/movements via TestClient e
mede as colunas da tabela com um layout engine real (WeasyPrint) sobre o CSS real
do app (bootstrap vendor local + style.css + <style> embutido do template).

Somente leitura do app: nenhum arquivo do app é alterado. Duas passadas por
cenário: media=screen (layout de tela — V0–V4) e media=print (prova de que o
papel não herda min-width/table-layout/ellipsis da tela — V6; os blocos
@media print C1–C10 do style.css + a regra de segurança da 042 ficam ativos).

Uso: .venv/bin/python specs/042-trilha-auditoria-larguras-colunas/validar_local.py [larguras...]
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

COLS = ["Data/Hora", "Tombamento", "Equipamento", "Tipo", "Origem", "Destino",
        "Status", "Motivo", "Operador", "Termo"]
CLS = ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10"]
TBL = "movrep-table"


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
    """Semeia movimentações cobrindo os edge cases do quickstart (se ainda não houver)."""
    from app.models.user import User
    from app.models.asset import Asset
    from app.models.movement import Movement
    from app.models.enums import AssetStatus, MovementType, AssetCategory, AssetCondition
    if db.query(Movement).count() > 0:
        return
    casos_asset = [
        ("TMB-2026-0539", "Notebook Dell Latitude 5440 com fonte dedicada para validação de layout de tabela",
         AssetCategory.NOTEBOOK, AssetStatus.IN_USE),
        ("TMB-2026-0538", "Impressora Multifuncional Epson L395",
         AssetCategory.EQUIPMENT, AssetStatus.AVAILABLE),
        ("TMB-2026-0537", 'Monitor LG UltraWide 29"',
         AssetCategory.MONITOR, AssetStatus.IN_MAINTENANCE),
        ("TMB-2026-0536", "Servidor Dell PowerEdge R750 com dois processadores e redundância de energia",
         AssetCategory.SERVER, AssetStatus.IN_USE),
    ]
    assets = []
    for tag, name, cat, st in casos_asset:
        a = Asset(tag=tag, name=name, category=cat, status=st,
                  condition=AssetCondition.GOOD, purchase_value=120000.00)
        db.add(a)
        assets.append(a)
    db.flush()

    origem_longa = "Secretaria Municipal de Educação - Almoxarifado Central Setor Norte"
    destino_longo = "IPMJP - Setor de Contabilidade e Patrimônio do Órgão Central"
    custodiana = "Maria Fernanda Oliveira Santos e Silva"
    operador = "Validador Quarenta e Dois"
    casos_mov = [
        # asset, tipo, origem_loc, origem_cust, destino_loc, destino_cust, status, motivo, termo
        (assets[0], MovementType.ALLOCATION, origem_longa, custodiana, destino_longo, custodiana,
         AssetStatus.IN_USE,
         "Transferência para alocação no setor de estatística e monitoramento de indicadores "
         "educacionais do município após aprovação da supervisão responsável pelo patrimônio",
         "TR-2026-0539"),
        (assets[1], MovementType.MAINTENANCE_OUT, origem_longa, None, destino_longo, custodiana,
         AssetStatus.IN_MAINTENANCE,
         "Cabeçote de impressão entupido após troca de tinta; aguardando diagnóstico da assistência",
         None),
        (assets[2], MovementType.ACQUISITION, None, None, None, None,
         AssetStatus.AVAILABLE,
         "Entrada por aquisição direta conforme processo administrativo e nota fiscal correspondente",
         None),
        (assets[3], MovementType.STATUS_UPDATE, "Almoxarifado Central", "João da Silva",
         "Almoxarifado Central", "João da Silva",
         AssetStatus.IN_USE,
         "Vistoria trimestral de conservação com atualização de estado",
         "TR-2026-0536"),
    ]
    for a, tipo, ol, oc, dl, dc, st, motivo, termo in casos_mov:
        db.add(Movement(asset_id=a.id, movement_type=tipo,
                        origin_location_name=ol, origin_custodian_name=oc,
                        destination_location_name=dl, destination_custodian_name=dc,
                        previous_status=None, new_status=st,
                        reason=motivo, operator_name=operador, term_code=termo))
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
        create_user(db, username="val042", password="Val042!senha",
                    full_name="Validador Quarenta e Dois", is_admin=True)
        _seed_dados(db)
    finally:
        db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        client.post("/api/v1/auth/login",
                    data={"username": "val042", "password": "Val042!senha"})
        resp = client.get("/reports/movements")
        assert resp.status_code == 200, resp.status_code
        body = resp.text
    app.dependency_overrides.clear()

    # Extrai o card do relatório + <style> embutido (bloco content do template)
    m = re.search(r"(<style>.*?</style>)", body, re.S)
    inline_style = m.group(1) if m else ""
    i_ini = body.find('class="page-header no-print"')
    i_ini = body.rfind("<div", 0, i_ini) if i_ini > 0 else 0
    table_html = body[i_ini:]

    lines = ["# validacao local 042 — medições WeasyPrint (screen = V0–V4 · print = V6)", ""]
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
