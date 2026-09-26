"""Validação local da Feature 043 — renderiza /admin/users via TestClient e
mede as colunas da tabela com um layout engine real (WeasyPrint) sobre o CSS real
do app (bootstrap vendor local + style.css + <style> embutido do template).

Somente leitura do app: nenhum arquivo do app é alterado. Apenas media=screen
(tela não-relatório — R10: sem bloco de impressão nesta feature).

Uso: .venv/bin/python specs/043-usuarios-larguras-colunas/validar_local.py [larguras...]
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

COLS = ["Usuário", "E-mail", "Origem", "Perfis", "Status", "Último Acesso", "Ações"]
CLS = ["c1", "c2", "c3", "c4", "c5", "c6", "c7"]
TBL = "usr-lista-table"


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
    """Semeia usuários cobrindo os edge cases do quickstart (se ainda não houver)."""
    from app.models.user import User
    if db.query(User).filter(User.username == "val043").count() > 0:
        return
    casos = [
        # username, full_name, email, provider, is_admin, ativo, ultimo_login
        ("val043.admin", "Validador Quarenta e Três Administrador do Sistema Patrimonial",
         "validador.quarenta.tres.administrador@ipmjp.pb.gov.br", "local", True, True, True),
        ("val043.ad", "Maria Fernanda Oliveira Santos e Silva",
         "maria.fernanda.oliveira.santos.e.silva@municipio.gov.br", "ad", False, True, True),
        ("val043.semperfil", None, "sem.perfil@ipmjp.pb.gov.br", "local", False, True, True),
        ("val043.bloqueado", "Usuário Bloqueado de Exemplo", "bloqueado@ipmjp.pb.gov.br",
         "local", False, False, None),
    ]
    for username, full_name, email, provider, is_admin, ativo, login in casos:
        db.add(User(username=username, full_name=full_name, email=email,
                    auth_provider=provider, is_admin=is_admin, is_active=ativo,
                    last_login=(datetime.datetime(2026, 9, 25, 18, 30) if login else None),
                    password_hash="x"))
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
        create_user(db, username="val043.owner", password="Val043!senha",
                    full_name="Dono da Validação Quarenta e Três", is_admin=True)
        _seed_dados(db)
    finally:
        db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        client.post("/api/v1/auth/login",
                    data={"username": "val043.owner", "password": "Val043!senha"})
        resp = client.get("/admin/users")
        assert resp.status_code == 200, resp.status_code
        body = resp.text
    app.dependency_overrides.clear()

    # Extrai o card da tabela + <style> embutido (bloco content do template)
    m = re.search(r"(<style>.*?</style>)", body, re.S)
    inline_style = m.group(1) if m else ""
    i_ini = body.find('class="card"')
    i_ini = body.rfind("<div", 0, i_ini) if i_ini > 0 else 0
    table_html = body[i_ini:]

    lines = ["# validacao local 043 — medições WeasyPrint (screen)", ""]
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
