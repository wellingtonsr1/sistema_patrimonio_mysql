"""Validação local da Feature 046 — renderiza / (dashboard) via TestClient e mede
as colunas da tabela "Fluxo Recente de Movimentações" com um layout engine real
(WeasyPrint) sobre o CSS real do app (bootstrap vendor local + style.css +
<style> embutido do template).

Somente leitura do app: nenhum arquivo do app é alterado. Sem screenshots
(headless): produz medições determinísticas (equivalente a getBoundingClientRect)
dos cenários V0 (pré-alteração) / V1 (pós-alteração) do quickstart.

Uso: .venv/bin/python specs/046-dashboard-larguras-colunas/validar_local.py [V0|V1] [larguras...]

O script compara ainda a tabela "Necessitam de atenção" (que NÃO é alvo) entre
as fases: suas medições devem permanecer idênticas V0 → V1 (fronteira de escopo,
R5 do plan).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BASE_CSS = ROOT / "app/web/static/css/style.css"
VENDOR_CSS = ROOT / "app/web/static/vendor/css/bootstrap.min.css"
OUT = Path(__file__).resolve().parent / "validacao_local.out.md"

# Fase: "V0" usa o HTML puro capturado; "V1" permite injetar marcações de classe
# (o próprio template alterado já traz a classe de escopo — nada a injetar).
PHASE = "V0"
if len(sys.argv) > 1 and sys.argv[1] in ("V0", "V1"):
    PHASE = sys.argv[1]
    sys.argv.pop(1)

COLS = ["Data", "Tombamento", "Equipamento", "Ação", "Destino", "Operador", "Ações"]
CLS = ["col-data", "col-tag", "col-equip", "col-acao", "col-destino", "col-operador", "col-acoes"]
OTHER_COLS = ["Tag", "Equipamento (outra)", "Observação"]
OTHER_CLS = ["o0", "o1", "o2"]


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
<style>@page {{ size: {viewport}px 6000px; margin: 0; }}</style>
</head><body>{body_html}</body></html>"""


def measure(html: str) -> dict:
    from weasyprint import HTML  # import tardio: mensagem de erro clara se ausente
    doc = HTML(string=html, base_url=str(ROOT)).render()
    page = doc.pages[0]
    out = {"page_width": float(page.width)}
    found = {}
    other_found = {}

    def walk(box):
        el = getattr(box, "element", None)
        if el is not None:
            classes = (el.get("class") or "").split()
            if el.tag == "col" and classes:
                if classes[0] in CLS and classes[0] not in found:
                    found[classes[0]] = box
                if classes[0] in OTHER_CLS and classes[0] not in other_found:
                    other_found[classes[0]] = box
            if "dash-table" in classes and "table" not in out:
                out["table"] = box
            if "attn-table" in classes and "other_table" not in out:
                out["other_table"] = box
        for child in getattr(box, "all_children", lambda: [])():
            walk(child)

    walk(page._page_box)
    # linhas de texto por tr da tabela-alvo (prova de linha única, SC-005)
    rows = []

    def _count_lines(bx):
        if bx.__class__.__name__ == "LineBox":
            return 1
        return sum(_count_lines(c) for c in getattr(bx, "all_children", lambda: [])())

    def _rows(bx):
        el = getattr(bx, "element", None)
        if el is not None and el.tag == "tr":
            rows.append(_count_lines(bx))
            return
        for c in getattr(bx, "all_children", lambda: [])():
            _rows(c)

    tb0 = out.get("table")
    if tb0 is not None:
        _rows(tb0)
    out["rows"] = rows
    cols = {}
    for name, cls in zip(COLS, CLS):
        b = found.get(cls)
        cols[name] = round(b.width, 1) if b is not None else None
    out["cols"] = cols
    ocols = {}
    for name, cls in zip(OTHER_COLS, OTHER_CLS):
        b = other_found.get(cls)
        ocols[name] = round(b.width, 1) if b is not None else None
    out["other_cols"] = ocols
    tb = out.get("table")
    out["table_width"] = round(tb.width, 1) if tb is not None else None
    otb = out.get("other_table")
    out["other_table_width"] = round(otb.width, 1) if otb is not None else None
    return out


def _seed_dados(db):
    """Semeia dados cobrindo os edge cases da spec 046 (se ainda não houver).

    Movimentações COM e SEM term_code (par vs. botão único nas Ações),
    destino por colaborador E por local/"Estoque" (os dois ramos do if/else)
    e equipamento com nome longo.
    """
    from app.models.user import User
    from app.models.asset import Asset
    from app.models.movement import Movement
    if db.query(Movement).count() > 0:
        return
    casos = [
        # (tag, nome, tipo, destino_loc, destino_cust, termo)
        ("TMB-2026-4601", "Computador Dell OptiPlex 7090 Desktop Mini com processador Intel Core i7 de décima primeira geração, memória de dezesseis gigabytes e unidade de estado sólido de quinhentos e doze gigabytes",
         "ALOCACAO_CAUTELA", None,
         "Maria Fernanda Oliveira Santos e Silva", "TR-2026-0461"),
        ("TMB-2026-4602", "Impressora Multifuncional Epson L395",
         "ENVIO_MANUTENCAO", "Assistência Técnica Autorizada Teknikão Manutenção e Comércio de Peças LTDA",
         None, None),
        ("TMB-2026-4603", "Monitor LG UltraWide 29 polegadas",
         "TRANSFERENCIA_LOCAL", "IPMJP - Fundo Municipal de Previdência - Setor de Análise de Benefícios e Atendimento ao Público",
         None, None),
        ("TMB-2026-4604", "Notebook Dell Latitude 5440",
         "DEVOLUCAO_ESTOQUE", "Estoque", None, None),
        ("TMB-2026-4605", "Projetor Epson PowerLite X49 para sala de treinamento",
         "ALOCACAO_CAUTELA", None,
         "Ana Paula Ferreira", "TR-2026-0462"),
        ("TMB-2026-4606", "Roteador Wi-Fi 6 TP-Link Archer AX23",
         "ENTRADA_AQUISICAO", "IPMJP - Superintendência Adjunta de Tecnologia da Informação", None, None),
    ]
    for tag, nome, tipo, dl, dc, termo in casos:
        a = Asset(tag=tag, name=nome, status="EM_USO", condition="BOM", category="NOTEBOOK")
        db.add(a)
        db.flush()
        db.add(Movement(asset_id=a.id, movement_type=tipo,
                        origin_location_name=None, origin_custodian_name=None,
                        destination_location_name=dl, destination_custodian_name=dc,
                        previous_status=None, new_status="EM_USO",
                        reason="Seed de validação de layout (feature 046).",
                        operator_name="Validador Quarenta e Seis",
                        term_code=termo))
    # Bem sem localização/custodiante = inconsistência → garante que a OUTRA
    # tabela ("Necessitam de atenção", L182–200) renderize, para a prova de
    # escopo (R5): suas medições devem permanecer idênticas V0 → V1.
    db.add(Asset(tag="TMB-2026-4699",
                 name="Equipamento sem localizacao para prova de escopo 046",
                 status="DISPONIVEL", condition="BOM", category="OUTROS"))
    db.commit()


def main():
    widths = [int(a) for a in sys.argv[1:]] or [1440, 1152, 1024, 700, 375, 2880]
    # Renderiza / autenticado contra o banco de teste (SQLite em memória,
    # mesmo mecanismo da suíte — Constitution VII)
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import Base, get_db
    from tests.conftest import engine, TestingSessionLocal, _override_get_db
    from app.services.auth_service import create_user

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        create_user(db, username="val046", password="Val046!senha",
                    full_name="Validador Quarenta e Seis", is_admin=True)
        _seed_dados(db)
    finally:
        db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        client.post("/api/v1/auth/login",
                    data={"username": "val046", "password": "Val046!senha"})
        resp = client.get("/")
        assert resp.status_code == 200, resp.status_code
        body = resp.text
    app.dependency_overrides.clear()

    # Marcação de MEDIÇÃO (somente no HTML capturado — o template real não é
    # tocado): ambas as tabelas recebem classes de referência e um colgroup
    # NEUTRO (sem larguras), para que os mesmos seletores (cN/dash-table/
    # attn-table) existam em V0 e V1 e a comparação reflita apenas o CSS da fase.
    m = re.search(r"(<style>.*?</style>)", body, re.S)
    inline_style = m.group(1) if m else ""
    # 1) Tabela "Necessitam de atenção" (se renderizada): classes de referência.
    #    O corte precisa começar na TAG <table ...>: se começar no atributo
    #    class=, o fragmento fica com a tag de abertura cortada, o parser
    #    descarta table/colgroup e a medição de escopo sai None.
    o_attr = body.find('class="table align-middle table-sm"')
    o_ini = body.rfind("<table", 0, o_attr) if o_attr >= 0 else -1
    if o_ini >= 0:
        o_end = body.find("</table>", o_attr) + len("</table>")
        attn = body[o_ini:o_end]
        attn_marked = attn.replace('class="table align-middle table-sm"',
                                   'class="table align-middle table-sm attn-table"')
        attn_marked = attn_marked.replace("<th>Tag</th>", '<th class="o0">Tag</th>')
        attn_marked = attn_marked.replace("<th>Equipamento</th>", '<th class="o1">Equipamento</th>')
        attn_marked = attn_marked.replace("<th>Observação</th>", '<th class="o2">Observação</th>')
        if "<colgroup>" not in attn_marked:
            attn_marked = attn_marked.replace(
                "<thead>",
                '<colgroup><col class="o0"><col class="o1"><col class="o2"></colgroup><thead>',
                1,
            )
        body = body[:o_ini] + attn_marked + body[o_end:]

    # 2) Tabela-alvo: em V0 injeta a classe de escopo + colgroup NEUTRO (sem
    #    larguras) para medição comparável; em V1 o template já traz a classe
    #    e o colgroup reais — nada a injetar.
    if 'class="table align-middle dash-table"' not in body:
        body = body.replace('class="table align-middle"',
                            'class="table align-middle dash-table"', 1)
    d_attr = body.find('class="table align-middle dash-table"')
    d_ini = body.rfind("<table", 0, d_attr) if d_attr >= 0 else -1
    if d_ini >= 0:
        d_tag_end = body.find(">", d_ini) + 1
        if "<colgroup>" not in body[d_tag_end:d_tag_end + 500]:
            neutral = ('<colgroup>'
                       + "".join(f'<col class="{c}">' for c in CLS)
                       + "</colgroup>")
            body = body[:d_tag_end] + neutral + body[d_tag_end:]

    # Corpo medido: da outra tabela (já marcada, precede a tabela-alvo) até o
    # fim do bloco da tabela-alvo — AMBAS no mesmo HTML (prova de escopo R5).
    # idem acima: recuar até a tag <table de cada tabela marcada
    o2_attr = body.find("attn-table")
    o2_ini = body.rfind("<table", 0, o2_attr) if o2_attr >= 0 else -1
    d2_attr = body.find('class="table align-middle dash-table"')
    d2_ini = body.rfind("<table", 0, d2_attr) if d2_attr >= 0 else -1
    if o2_ini >= 0 and d2_ini > o2_ini:
        measured_body = body[o2_ini:]
    else:
        measured_body = body[d2_ini:] if d2_ini >= 0 else body

    # Corpo de referência de escopo: a OUTRA tabela sozinha (medição independente,
    # robusta a diferenças de parsing do layout engine entre as duas tabelas).
    o3_attr = body.find("attn-table")
    o3_ini = body.rfind("<table", 0, o3_attr) if o3_attr >= 0 else -1
    if o3_ini >= 0:
        o3_fim = body.find("<!-- Recent Movements -->", o3_attr)
        other_body = body[o3_ini:o3_fim if o3_fim >= 0 else len(body)]
    else:
        other_body = ""

    spans_ellip = re.findall(r"<span[^>]*dash-ellip[^>]*>", measured_body)
    n_title = sum(1 for s in spans_ellip if "title=" in s)
    lines = [f"# validação local 046 — medições WeasyPrint (fase {PHASE})", "",
             f"- spans dash-ellip: {len(spans_ellip)} · com tooltip (title): {n_title}", ""]
    for vp in widths:
        for dark in (False, True):
            html = build_html(inline_style + measured_body, vp, dark)
            r = measure(html)
            total = sum(v for v in r["cols"].values() if v)
            lines.append(f"## viewport {vp}px {'dark' if dark else 'light'} ({PHASE})")
            lines.append(f"- page: {r['page_width']}px · tabela-alvo: {r['table_width']}px · soma cols: {round(total,1)}px")
            for name in COLS:
                w = r["cols"][name]
                pct = round(100 * w / r["table_width"], 1) if (w and r["table_width"]) else "?"
                lines.append(f"  - {name}: {w}px ({pct}%)")
            rows = r.get("rows") or []
            lines.append("  - trs (thead+tbody, linhas de texto por tr): "
                         + ("/".join(str(x) for x in rows) if rows else "-"))
            ot = r.get("other_table_width")
            ototal = sum(v for v in r["other_cols"].values() if v)
            if other_body:
                r2 = measure(build_html(inline_style + other_body, vp, dark))
                ot2 = r2.get("other_table_width")
                oc2 = {n: r2["other_cols"][n] for n in OTHER_COLS}
            else:
                ot2, oc2 = ot, {n: r["other_cols"][n] for n in OTHER_COLS}
            ot2_total = sum(v for v in oc2.values() if v)
            lines.append(f"- [escopo] outra tabela: {ot2}px · soma: {round(ot2_total, 1)}px · cols: "
                         + ", ".join(f"{n}={oc2[n]}" for n in OTHER_COLS))
            lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSalvo em {OUT}")


if __name__ == "__main__":
    main()
