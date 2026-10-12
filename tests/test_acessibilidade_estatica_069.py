"""
Feature 069 — Acessibilidade U3/U4 (login e inventário): verificação ESTÁTICA.

TDD: os testes abaixo foram escritos ANTES dos fixes nos templates (RED com
as contagens de hoje, GREEN após cada fix). A suíte não executa JavaScript:
as verificações são feitas sobre o HTML servido (TestClient), com parser
`html.parser` da stdlib — zero dependência nova (R5 do research.md).

Cobertura (contract §3 da spec):
  - todo input/select/textarea visível tem nome acessível
    (label[for] / label ancestral / aria-label / aria-labelledby)
  - todo botão só-ícone tem aria-label (ou texto/texto oculto)
  - grupo de rádios "Resultado da conferência" envolto em fieldset/legend
  - alertas de erro dos fluxos com role="alert"
  - nenhum id duplicado por página

Limites declarados (R5/R9): não mede contraste, não executa JS/leitor de
tela — verificação manual continua no quickstart §4; axe-core com browser
fica no backlog (docs/Melhorias_SisPatrimonio_Pro.md).
"""
import re
from html.parser import HTMLParser

import pytest

from app.models.enums import AssetCategory, AssetCondition
from app.schemas.asset import AssetCreate
from app.schemas.location import LocationCreate
from app.services.asset_service import AssetService
from app.services.location_service import LocationService

# Input/select/textarea que REPRESENTAM controles visíveis (o hidden do
# formulário de login não precisa de nome acessível; aria-hidden também não).
VISIBLE_INPUT_TYPES = {
    "text", "password", "email", "number", "date", "time", "search", "tel",
    "url", "checkbox", "radio", "range", "file", "color", "month", "week",
}
VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                 "link", "meta", "param", "source", "track", "wbr"}


class _FormAudit(HTMLParser):
    """Coleta controles, buttons, labels, fieldsets, alerts e ids do HTML.

    Modelo de nomes acessíveis simplificado e voluntariamente conservador:
    conta como "com nome" o controle que tenha qualquer um dos mecanismos
    aceitos pela casa (label[for], label ancestral, aria-label,
    aria-labelledby, title em button âncora-ícone). Não tenta interpretar
    CSS/spring ARIA completo — o que o axe real cobre fica no backlog.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []            # elementos abertos (tag, attrs, ancestral de label?)
        self.controls = []         # dict: {tag, type, named, id, hidden, in_label, line}
        self.buttons = []          # dict: {text_pending, aria_label, line, hidden}
        self.labels_ids = []       # ids apontados por label[for]
        self.fieldset_depth = []   # se estamos dentro de algum <fieldset>
        self.radio_no_fieldset = []
        self.alert_danger = []     # dict {has_role_alert, line} para divs alert-danger
        self.alert_div_stack = []  # refs para divs .alert-danger abertas
        self.ids = []              # (id, line) de todos os elementos com id
        self._button_text = None   # buffer de texto do button corrente
        self._in_button = False

    # --- helpers -----------------------------------------------------------
    @staticmethod
    def _attrs_dict(attrs):
        return {k: (v or "") for k, v in attrs}

    def _named(self, d):
        if d.get("aria_label") or d.get("aria_labelledby") or d.get("title"):
            return True
        if d.get("id") is not None:
            return d["id"] in self.labels_ids
        if d.get("in_label"):
            return True
        return False

    # --- handlers ----------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = self._attrs_dict(attrs)
        in_label = any(t == "label" for t, _, _ in self.stack)
        self.ids.append((a.get("id"), self.getpos()[0])) if a.get("id") else None

        if tag == "label" and a.get("for"):
            self.labels_ids.append(a["for"])

        if tag in ("fieldset",):
            self.fieldset_depth.append(True)

        in_fieldset = bool(self.fieldset_depth)

        if tag == "button":
            self._in_button = True
            self._button_text = []
            self.buttons.append({
                "text_when_closed": None,  # preenchido no close
                "aria_label": a.get("aria-label", ""),
                "title": a.get("title", ""),
                "line": self.getpos()[0],
                "closed": False,
            })
        elif tag == "input" and a.get("type") in VISIBLE_INPUT_TYPES:
            ctl = {
                "tag": "input", "type": a.get("type"),
                "id": a.get("id"),
                "in_label": in_label,
                "in_fieldset": in_fieldset,
                "aria_label": a.get("aria-label", ""),
                "aria_labelledby": a.get("aria-labelledby", ""),
                "title": a.get("title", ""),
                "line": self.getpos()[0],
            }
            self.controls.append(ctl)
        elif tag in ("select", "textarea"):
            self.controls.append({
                "tag": tag, "id": a.get("id"),
                "in_label": in_label,
                "in_fieldset": in_fieldset,
                "aria_label": a.get("aria-label", ""),
                "aria_labelledby": a.get("aria-labelledby", ""),
                "title": a.get("title", ""),
                "line": self.getpos()[0],
            })

        is_alert_danger = tag == "div" and "alert-danger" in a.get("class", "")
        if is_alert_danger:
            self.alert_div_stack.append({"has_role_alert": a.get("role") == "alert",
                                         "line": self.getpos()[0]})

        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, a, in_label))

    def handle_data(self, data):
        if self._in_button and self._button_text is not None:
            self._button_text.append(data)

    def handle_endtag(self, tag):
        if tag == "button" and self._in_button:
            self.buttons[-1]["text_when_closed"] = "".join(self._button_text or []).strip()
            self.buttons[-1]["closed"] = True
            self._in_button = False
            self._button_text = None
        if tag == "fieldset" and self.fieldset_depth:
            self.fieldset_depth.pop()
        if tag == "div" and self.alert_div_stack:
            self.alert_danger.append(self.alert_div_stack.pop())
        # fecha todos os elementos acima do fechado inclusive — html.parser não
        # informa o contexto, então fechar um tag interrompe qualquer ancestral
        # aberto antes dele com o mesmo nome (Jinja bem formado, ok na prática)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def _audit(html: str) -> _FormAudit:
    p = _FormAudit()
    p.feed(html)
    p.close()
    return p


def _unnamed_controls(audit: _FormAudit):
    """Controles visíveis sem nenhum mecanismo de nome acessível."""
    out = []
    for ctl in audit.controls:
        if ctl.get("type") == "hidden":
            continue
        if not audit._named(ctl):
            out.append(ctl)
    return out


def _icon_only_buttons_without_name(audit: _FormAudit, html: str):
    """Buttons sem texto visível E sem aria-label/title.

    Heurística da casa: button cujo texto não-alnum está vazio é candidato a
    só-ícone; classe `btn-close` do Bootstrap já dá nome via implementação
    (o HTML dos nossos templates sempre traz aria-label="Fechar" neles).
    """
    out = []
    for b in audit.buttons:
        if b["text_when_closed"] is None and not b.get("closed"):
            continue  # button nunca fechado (aninhamento quebrado): ignora
        text = re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", b["text_when_closed"] or "")
        if not text and not (b["aria_label"] or b["title"]):
            out.append(b)
    return out


# ============================================================================
# Seeds (padrão da casa, conforme test_conferencia_visual.py)
# ============================================================================

def _setup_inventario_com_bem(client, db_session):
    loc = LocationService.create(db_session, LocationCreate(
        name="Loc 069", branch="Matriz", department="TI"))
    asset = AssetService.create(db_session, AssetCreate(
        tag="ACE-069-0001", name="Notebook A11y",
        category=AssetCategory.NOTEBOOK, purchase_value=1000.0,
        condition=AssetCondition.GOOD, initial_location_id=loc.id))
    resp = client.post("/inventarios/new", data={
        "name": "Inventário 069", "location_id": str(loc.id),
    }, follow_redirects=False)
    assert resp.status_code == 303
    return asset


@pytest.fixture()
def inv_ids(client, db_session):
    asset = _setup_inventario_com_bem(client, db_session)
    from app.models.inventario import Inventario as Inv
    inv = db_session.query(Inv).first()
    return {"inv": inv.id, "asset": asset.id}


# ============================================================================
# Regra 1 — controles com nome acessível (contract §3 / RN-1..RN-3)
# ============================================================================

def test_login_sem_controle_sem_nome(unauth_client):
    # igual ao teste de botões: o /login validado é o não autenticado (standalone)
    a = _audit(unauth_client.get("/login").text)
    unnamed = _unnamed_controls(a)
    assert not unnamed, f"/login: controles sem nome: {unnamed}"


def test_setup_sem_controle_sem_nome(client, db_session):
    # /setup só é servido quando não há usuário (ou 409/redireciona se já há) —
    # exercitamos o template direto via rota: existindo usuário, a casa 062
    # redireciona para /login; nesse caso consideramos o fluxo coberto pelo
    # test de login e pulamos com registro.
    r = client.get("/setup", follow_redirects=False)
    if r.status_code in (303, 307):
        pytest.skip("setup indisponível (usuário já existe) — fluxo coberto por /login")
    a = _audit(r.text)
    unnamed = _unnamed_controls(a)
    assert not unnamed, f"/setup: controles sem nome: {unnamed}"


def test_inventarios_list_sem_controle_sem_nome(client):
    a = _audit(client.get("/inventarios").text)
    unnamed = _unnamed_controls(a)
    assert not unnamed, f"/inventarios: controles sem nome: {unnamed}"


def test_inventarios_new_sem_controle_sem_nome(client):
    a = _audit(client.get("/inventarios/new").text)
    unnamed = _unnamed_controls(a)
    assert not unnamed, f"/inventarios/new: controles sem nome: {unnamed}"


def test_inventarios_detail_sem_controle_sem_nome(client, inv_ids):
    a = _audit(client.get(f"/inventarios/{inv_ids['inv']}").text)
    unnamed = _unnamed_controls(a)
    assert not unnamed, f"/inventarios/{{id}}: controles sem nome: {unnamed}"


def test_conferir_sem_controle_sem_nome(client, inv_ids):
    r = client.get(f"/inventarios/{inv_ids['inv']}/conferir/{inv_ids['asset']}")
    assert r.status_code == 200
    a = _audit(r.text)
    unnamed = _unnamed_controls(a)
    assert not unnamed, f"/conferir: controles sem nome: {unnamed}"


def test_offline_sem_controle_sem_nome(client, inv_ids):
    a = _audit(client.get(f"/inventarios/{inv_ids['inv']}/offline").text)
    unnamed = _unnamed_controls(a)
    assert not unnamed, f"/offline: controles sem nome: {unnamed}"


# ============================================================================
# Regra 2 — botões só-ícone com nome (RN-4)
# ============================================================================

def test_login_sem_botao_sonico_sem_nome(unauth_client):
    # /login sem sessão rende o layout standalone (o autenticado injeta o header
    # do base.html — redirecionado na prática, não é o estado a validar aqui)
    html = unauth_client.get("/login").text
    a = _audit(html)
    bad = _icon_only_buttons_without_name(a, "")
    assert not bad, f"/login: botões só-ícone sem nome: {bad}"


def test_inventarios_e_conferir_sem_botao_sonico_sem_nome(client, inv_ids):
    for path in (f"/inventarios/{inv_ids['inv']}",
                 f"/inventarios/{inv_ids['inv']}/conferir/{inv_ids['asset']}",
                 "/inventarios/new"):
        a = _audit(client.get(path).text)
        bad = _icon_only_buttons_without_name(a, path)
        assert not bad, f"{path}: botões só-ícone sem nome: {bad}"


# ============================================================================
# Regra 3 — grupo de rádios com fieldset/legend (RN-5)
# ============================================================================

@pytest.mark.parametrize("path_fn", [
    lambda ids: f"/inventarios/{ids['inv']}/conferir/{ids['asset']}",
    lambda ids: f"/inventarios/{ids['inv']}",
    lambda ids: f"/inventarios/{ids['inv']}/offline",
])
def test_resultado_da_conferencia_tem_fieldset(client, inv_ids, path_fn):
    r = client.get(path_fn(inv_ids))
    assert r.status_code == 200
    html = r.text
    # todas as 4 radios de resultado devem estar dentro de <fieldset>
    # e o grupo deve ter <legend> com o título do campo
    a = _audit(html)
    radios = [c for c in a.controls if c.get("type") == "radio"]
    assert len(radios) >= 4, "grupo de resultado com menos de 4 radios"
    for r0 in radios:
        assert r0["in_fieldset"], f"radio value={r0.get('id')} fora de fieldset"
    assert re.search(r"<legend[^>]*>\s*Resultado da conferência", html), \
        "legend 'Resultado da conferência' ausente"


# ============================================================================
# Regra 4 — alertas de erro com role="alert" (RN-6)
# ============================================================================

def test_login_alert_erro_tem_role(client):
    html = client.post("/login", data={
        "username": "nope", "password": "wrong", "next": "",
    }, follow_redirects=False).text
    a = _audit(html)
    assert a.alert_danger, "nenhum alert-danger renderizado no login com erro"
    assert all(d["has_role_alert"] for d in a.alert_danger), \
        f"alert-danger sem role=alert: {a.alert_danger}"


def test_conferir_alert_erro_tem_role(client, inv_ids):
    # o alerta de erro da conferência é ?error= na query string (padrão da casa)
    body = client.get(
        f"/inventarios/{inv_ids['inv']}/conferir/{inv_ids['asset']}"
        f"?error=Resultado+obrigatório").text
    a = _audit(body)
    assert a.alert_danger, "nenhum alert-danger na página de conferência"
    assert all(d["has_role_alert"] for d in a.alert_danger), \
        "alert-danger de conferir.html sem role=alert"


# ============================================================================
# Regra 5 — ids únicos por página (RN-7)
# ============================================================================

@pytest.mark.parametrize("path_fn", [
    lambda: "/login",
    lambda ids: f"/inventarios/{ids['inv']}",
    lambda ids: f"/inventarios/{ids['inv']}/conferir/{ids['asset']}",
    lambda ids: f"/inventarios/{ids['inv']}/offline",
])
def test_ids_unicos(client, inv_ids, path_fn):
    html = client.get(path_fn(inv_ids) if "ids" in path_fn.__code__.co_varnames
                      else path_fn()).text
    a = _audit(html)
    seen = {}
    dups = []
    for id_, line in a.ids:
        if id_ in seen:
            dups.append((id_, seen[id_], line))
        seen[id_] = line
    assert not dups, f"ids duplicados: {dups}"
