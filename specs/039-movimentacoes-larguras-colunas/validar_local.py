"""Validação local da Feature 039 — renderiza /movements via TestClient e mede
as colunas da tabela com um layout engine real (WeasyPrint) sobre o CSS real do
app (bootstrap vendor local + style.css + <style> embutido do template).

Somente leitura do app: nenhum arquivo do app é alterado. Sem screenshots
(headless): produz medições determinísticas (equivalente a getBoundingClientRect)
dos cenários V0/V1/V2/V3/V4 do quickstart.

Uso: .venv/bin/python specs/039-movimentacoes-larguras-colunas/validar_local.py [larguras...]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BASE_CSS = ROOT / "app/web/static/css/style.css"
VENDOR_CSS = ROOT / "app/web/static/vendor/css/bootstrap.min.css"
OUT = Path(__file__).resolve().parent / "validacao_local.out.md"

COLS = ["Data/Hora", "Tombamento", "Equipamento", "Tipo", "Origem",
        "Destino", "Motivo", "Operador", "Ações"]
CLS = ["col-dh", "col-tag", "col-equip", "col-tipo", "col-origem",
       "col-destino", "col-motivo", "col-operador", "col-acoes"]


def build_html(body_html: str, viewport: int, dark: bool) -> str:
    """Recria o shell do base.html com os assets reais (vendor local)."""
    css = VENDOR_CSS.read_text(encoding="utf-8") + "\n" + BASE_CSS.read_text(encoding="utf-8")
    bg = "#111418" if dark else "#ffffff"
    color = "#e7eaee" if dark else "#1c2330"
    # @page por ÚLTIMO (vence o @page { size: Auto } do style.css @media print)
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
    doc = HTML(string=html, base_url=str(ROOT)).render()
    page = doc.pages[0]
    out = {"page_width": float(page.width)}
    found = {}

    def walk(box):
        el = getattr(box, "element", None)
        if el is not None:
            classes = (el.get("class") or "").split()
            if el.tag == "col" and classes and classes[0] in CLS and classes[0] not in found:
                found[classes[0]] = box
            if "mov-lista-table" in classes and "table" not in out:
                out["table"] = box
        for child in getattr(box, "all_children", lambda: [])():
            walk(child)

    walk(page._page_box)
    cols = {}
    for name, cls in zip(COLS, CLS):
        b = found.get(cls)
        cols[name] = round(b.width, 1) if b is not None else None
    out["cols"] = cols
    tb = out.get("table")
    out["table_width"] = round(tb.width, 1) if tb is not None else None
    return out


def _seed_dados(db):
    """Semeia dados cobrindo os edge cases do quickstart (se ainda não houver)."""
    from app.models.user import User
    from app.models.asset import Asset
    from app.models.movement import Movement
    if db.query(Movement).count() > 0:
        return
    u = db.query(User).filter_by(username="val039").first()
    casos = [
        # (tag, nome, tipo, origem_loc, origem_cust, destino_loc, destino_cust, motivo, termo)
        ("TMB-2026-9999", "Notebook Dell Latitude 5440 com fonte dedicada para validação de layout de tabela",
         "ALOCACAO_CAUTELA", None, None,
         "Secretaria Municipal de Educação - Almoxarifado Central Setor Norte",
         "Maria Fernanda Oliveira Santos e Silva",
         "Alocação para uso administrativo no setor de estatística e monitoramento de indicadores educacionais do município",
         True),
        ("TMB-2026-8888", "Impressora Multifuncional Epson L395",
         "ENVIO_MANUTENCAO", "Almoxarifado Central", "João da Silva Sauro",
         "Assistência Técnica Autorizada Teknikão Manutenção e Comércio de Pestras LTDA",
         None,
         "Cabeçote de impressão entupido após troca de tinta; aguardando diagnóstico da assistência e orçamento de reparo aprovado pela supervisão",
         False),
        ("TMB-2026-7777", "Monitor LG UltraWide 29\"",
         "ATUALIZACAO_ESTADO", "Sala de Reuniões 2", "Ana Paula Ferreira",
         "Sala de Reuniões 2", "Ana Paula Ferreira",
         "Vistoria trimestral: risquinhos na tela, estado mudado de ÓTIMO para BOM",
         False),
    ]
    for tag, nome, tipo, ol, oc, dl, dc, motivo, termo in casos:
        a = Asset(tag=tag, name=nome, status="EM_USO", condition="BOM", category="NOTEBOOK")
        db.add(a)
        db.flush()
        db.add(Movement(asset_id=a.id, movement_type=tipo,
                        origin_location_name=ol, origin_custodian_name=oc,
                        destination_location_name=dl, destination_custodian_name=dc,
                        previous_status=None, new_status="EM_USO",
                        reason=motivo, operator_name="Validador Trinta e Nove",
                        term_code=("TR-2026-0439" if termo else None)))
    db.commit()


def main():
    widths = [int(a) for a in sys.argv[1:]] or [1440, 1152, 1024, 700, 375, 2880]
    # Renderiza /movements autenticado contra o banco de teste (SQLite em memória,
    # mesmo mecanismo da suíte — Constitution VII)
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import Base, get_db
    from tests.conftest import engine, TestingSessionLocal, _override_get_db
    from app.services.auth_service import create_user

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        create_user(db, username="val039", password="Val039!senha",
                    full_name="Validador Trinta e Nove", is_admin=True)
        _seed_dados(db)
    finally:
        db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        client.post("/api/v1/auth/login",
                    data={"username": "val039", "password": "Val039!senha"})
        resp = client.get("/movements")
        assert resp.status_code == 200, resp.status_code
        body = resp.text
    app.dependency_overrides.clear()

    # Extrai o card da tabela + <style> embutido (bloco content do template)
    m = re.search(r"(<style>.*?</style>)", body, re.S)
    inline_style = m.group(1) if m else ""
    i_ini = body.find("<!-- Table -->")
    i_fim = body.find("{% endblock", i_ini)
    i_fim2 = body.find("</div>\n{% endblock", i_ini)
    fim = i_fim if i_fim >= 0 else (i_fim2 if i_fim2 >= 0 else len(body))
    table_html = body[i_ini:fim] if i_ini >= 0 else body

    lines = ["# validacao local 039 — medições WeasyPrint", ""]
    for vp in widths:
        for dark in (False, True):
            html = build_html(inline_style + table_html, vp, dark)
            r = measure(html)
            total = sum(v for v in r["cols"].values() if v)
            lines.append(f"## viewport {vp}px {'dark' if dark else 'light'}")
            lines.append(f"- page: {r['page_width']}px · tabela: {r['table_width']}px · soma cols: {round(total,1)}px")
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
