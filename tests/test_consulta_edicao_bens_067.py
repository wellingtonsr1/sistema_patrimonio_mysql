"""Feature 067 — Consulta Detalhada e Edição Controlada de Bens Patrimoniais.

Arquivo de TESTE da FEATURE 067 (`specs/067-consulta-edicao-bens/`). Cobre os
critérios de aceite AC01–AC15 (§12 da spec):

  US1 (T006/T007) — consulta detalhada: AC01/AC02 (todos os campos, incl.
      `notes` e `updated_at`; campos vazios como "não informado") e
      AC03/AC07 (403 sem `patrimonio.visualizar`, 404 para bem inexistente).
  US2/US3 (T010...) — edição controlada, auditoria, transação e histórico.

Padrão da casa (063/064/066): fixtures `client`/`db_session`/`unauth_client`
(SQLite em memória), massa via `AssetService.create`, e a prova é o **estado
do banco/HTML renderizado**, não detalhes internos de roteamento.

SCOPE desta feature: só este arquivo novo + templates/rotas/serviços da 067 —
zero teste existente alterado, zero DDL, zero migração (Constitution VII/VIII).
"""

from datetime import datetime

import pytest

from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.enums import AssetCategory, AssetCondition, AssetStatus, MovementType
from app.models.movement import Movement
from app.schemas.asset import AssetCreate
from app.services.asset_service import AssetService
from app.services.auth_service import create_user
from app.utils.time_utils import utc_to_recife

# tests/ não tem __init__.py: o pytest registra o conftest como módulo
# top-level `conftest` (mesma lição de tests/test_hermeticidade_suite.py).
# Importar `tests.conftest` reexecutaria o conftest como SEGUNDO módulo e
# sobrescreveria `app.main.SessionLocal`, quebrando a hermeticidade da suíte.
from conftest import TEST_PASSWORD


# ============================================================================
# Helpers de massa
# ============================================================================

def _make_asset(db_session, tag="PAT-06700", name="Notebook 067", **overrides) -> Asset:
    """Cria um bem pelo serviço (fonte única do cadastro)."""
    payload = {
        "tag": tag,
        "name": name,
        "category": AssetCategory.NOTEBOOK,
        "purchase_value": 0.0,
    }
    payload.update(overrides)
    return AssetService.create(db_session, AssetCreate(**payload))


def _login_sem_perfil(unauth_client, db_session, username="semperfil067"):
    """Sessão autenticada SEM perfil algum (deny by default — FR-003/AC07)."""
    create_user(db_session, username=username, password=TEST_PASSWORD)
    resp = unauth_client.post(
        "/login",
        data={"username": username, "password": TEST_PASSWORD, "next": "/assets"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text


def _login_com_perfil(unauth_client, db_session, username="editor067", role="Gestor de TI"):
    """Sessão autenticada com perfil que possui `patrimonio.editar`."""
    from app.services.permission_service import (
        assign_role, ensure_default_roles, get_role_by_name,
    )

    ensure_default_roles(db_session)
    user = create_user(
        db_session,
        username=username,
        password=TEST_PASSWORD,
        full_name="Editor da Silva",
    )
    assign_role(db_session, user, get_role_by_name(db_session, role))
    resp = unauth_client.post(
        "/login",
        data={"username": username, "password": TEST_PASSWORD, "next": "/assets"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    return user


def _form(**overrides) -> dict:
    """Corpo do POST `/assets/{id}/edit` com todos os campos editáveis (§4.3).

    O envio completo é intencional: prova que a lista fechada de campos é
    aplicada no backend e que campos vazios não sobrescrevem nada por engano.
    """
    data = {
        "name": "Notebook 067",
        "category": AssetCategory.NOTEBOOK.value,
        "brand": "",
        "model": "",
        "serial_number": "",
        "specifications": "",
        "purchase_date": "",
        "purchase_value": "0.0",
        "invoice_number": "",
        "supplier": "",
        "warranty_expiry": "",
        "condition": AssetCondition.NEW.value,
        "notes": "",
        "expected_updated_at": "",
    }
    data.update(overrides)
    return data


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _form_preenchido(asset: Asset, **overrides) -> dict:
    """Payload EXATO que o navegador envia no formulário pré-preenchido.

    Espelha o que `assets/edit.html` renderiza nos `value`/`selected` — é a
    base honesta para provar V9 ("salvar sem alterações não grava nada").
    """
    data = _form(
        name=asset.name,
        category=asset.category.value,
        brand=asset.brand or "",
        model=asset.model or "",
        serial_number=asset.serial_number or "",
        specifications=asset.specifications or "",
        purchase_date=asset.purchase_date.strftime("%Y-%m-%d") if asset.purchase_date else "",
        purchase_value=f"{asset.purchase_value or 0.0:.2f}",
        invoice_number=asset.invoice_number or "",
        supplier=asset.supplier or "",
        warranty_expiry=asset.warranty_expiry.strftime("%Y-%m-%d") if asset.warranty_expiry else "",
        condition=asset.condition.value,
        notes=asset.notes or "",
        expected_updated_at=_iso(asset.updated_at),
    )
    data.update(overrides)
    return data


def _eventos_alteracao(db_session, asset_id: int):
    """Eventos de auditoria de ALTERACAO cadastral do bem (FR-006/AC06)."""
    db_session.expire_all()
    return (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "ALTERACAO", AuditLog.resource_id == asset_id)
        .all()
    )


def _movimentos_estado(db_session, asset_id: int):
    db_session.expire_all()
    return (
        db_session.query(Movement)
        .filter(
            Movement.asset_id == asset_id,
            Movement.movement_type == MovementType.STATUS_UPDATE,
        )
        .all()
    )


# ============================================================================
# User Story 1 — Consulta detalhada do bem (T006/T007 → RED antes da T008)
# ============================================================================

class TestUS1ConsultaDetalhada:
    """AC01/AC02/AC03/AC07 — tela `/assets/{id}` apresenta todo o cadastro."""

    def test_detalhe_exibe_dados_completos(self, client, db_session):
        """AC01/AC02 — bem completo: todos os campos, incl. `notes` e `updated_at`."""
        notes = "Usado pela equipe de TI; bateria a trocar em 2027."
        asset = _make_asset(
            db_session,
            tag="PAT-06701",
            name="Notebook Dell Latitude 5440",
            brand="Dell",
            model="Latitude 5440",
            serial_number="SN-067-0001",
            specifications="Intel Core i7 / 16 GB / SSD 512 GB",
            purchase_date=datetime(2024, 3, 10, 9, 0, 0),
            purchase_value=7500.5,
            invoice_number="NF-1234/2024",
            supplier="Dell Brasil",
            warranty_expiry=datetime(2027, 3, 10, 9, 0, 0),
            condition=AssetCondition.GOOD,
            notes=notes,
        )

        resp = client.get(f"/assets/{asset.id}")
        assert resp.status_code == 200, resp.text
        html = resp.text

        # Identificação (já existente — guarda de não-regressão da tela)
        for value in (
            "PAT-06701", "Notebook Dell Latitude 5440",
            asset.category.label, asset.status.label, asset.condition.label,
        ):
            assert value in html, f"campo ausente no detalhe: {value!r}"

        # Ficha técnica + fiscal (AC02 — sem truncamento)
        for value in (
            "Dell", "Latitude 5440", "SN-067-0001",
            "Intel Core i7 / 16 GB / SSD 512 GB",
            "NF-1234/2024", "Dell Brasil",
            "10/03/2024", "10/03/2027", "7.500,50",
        ):
            assert value in html, f"campo ausente no detalhe: {value!r}"

        # AC01 — observações e última atualização cadastral aparecem
        assert "Observações" in html, "seção de observações ausente"
        assert notes in html, "conteúdo das observações ausente"
        assert "Última atualização" in html, "última atualização cadastral ausente"
        esperado = utc_to_recife(asset.updated_at).strftime("%d/%m/%Y %H:%M")
        assert esperado in html, f"data de atualização {esperado!r} ausente"

    def test_detalhe_omite_campos_vazios(self, client, db_session):
        """AC02 — bem mínimo: nada exibido como se estivesse cadastrado."""
        asset = _make_asset(db_session, tag="PAT-06702", name="Monitor 067")

        resp = client.get(f"/assets/{asset.id}")
        assert resp.status_code == 200, resp.text
        html = resp.text

        # Nenhum dado fictício/representação interna vaza para a tela
        assert "None" not in html, "valor `None` exposto no detalhe"
        assert "PAT-06702" in html and "Monitor 067" in html

        # Campos vazios marcados como não informados (nunca preenchidos por engano)
        assert "Não informado" in html
        assert "- / -" in html  # marca/modelo vazios
        # Observações vazias não criam seção
        assert "Observações" not in html, "seção de observações exibida sem conteúdo"

    def test_detalhe_404_bem_inexistente(self, client):
        """FR-003 — id inexistente → 404 (sem gravação)."""
        resp = client.get("/assets/999067")
        assert resp.status_code == 404

    def test_detalhe_403_sem_permissao(self, unauth_client, db_session):
        """AC07 — sem `patrimonio.visualizar` → 403 na tela de detalhes."""
        asset = _make_asset(db_session, tag="PAT-06703", name="Impressora 067")
        _login_sem_perfil(unauth_client, db_session)

        resp = unauth_client.get(f"/assets/{asset.id}")
        assert resp.status_code == 403, resp.text


# ============================================================================
# User Story 2 — Edição controlada dos dados cadastrais (T010 → RED)
# ============================================================================

class TestUS2EdicaoControlada:
    """AC03–AC08/AC11/AC12 — `/assets/{id}/edit` com RBAC, validação e trilha."""

    def test_editar_bem_sem_permissao_nega_e_audita(self, unauth_client, db_session):
        """AC07 — sem `patrimonio.editar`: 403 em GET e POST, nada gravado."""
        asset = _make_asset(db_session, tag="PAT-06710", name="Original 067")
        _login_sem_perfil(unauth_client, db_session, username="semperfil067b")

        assert unauth_client.get(f"/assets/{asset.id}/edit").status_code == 403
        resp = unauth_client.post(
            f"/assets/{asset.id}/edit", data=_form(name="Invadido")
        )
        assert resp.status_code == 403, resp.text

        db_session.expire_all()
        assert db_session.query(Asset).filter_by(id=asset.id).one().name == "Original 067"
        assert _eventos_alteracao(db_session, asset.id) == []
        negados = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.action == "ACESSO_NEGADO",
                AuditLog.resource == "patrimonio.editar",
            )
            .count()
        )
        assert negados >= 2, "tentativas negadas não foram registradas na trilha"

    def test_editar_formulario_pre_preenchido_sem_campos_protegidos(self, client, db_session):
        """§4.3 — o formulário traz os valores atuais e NÃO expõe campos protegidos."""
        asset = _make_asset(
            db_session, tag="PAT-06711", name="Notebook 067", brand="Dell",
            serial_number="SN-067-2001", notes="Observação existente.",
        )
        resp = client.get(f"/assets/{asset.id}/edit")
        assert resp.status_code == 200, resp.text
        html = resp.text
        assert "Notebook 067" in html and "Dell" in html and "SN-067-2001" in html
        assert "Observação existente." in html
        assert 'name="expected_updated_at"' in html  # P3 aprovada
        assert _iso(asset.updated_at) in html
        for proibido in ('name="tag"', 'name="status"', 'name="location_id"', 'name="custodian_id"'):
            assert proibido not in html, f"campo protegido exposto no formulário: {proibido}"

    def test_editar_bem_autorizado_atualiza_mesmo_registro(self, client, db_session):
        """AC03/AC05 — atualiza o MESMO registro (sem criar bem novo)."""
        asset = _make_asset(db_session, tag="PAT-06712", name="Notebook 067")
        total = db_session.query(Asset).count()

        resp = client.post(
            f"/assets/{asset.id}/edit",
            data=_form(
                name="Notebook 067 Renomeado",
                brand="Dell",
                model="Latitude 5440",
                serial_number="SN-067-1001",
                specifications="Intel i7 / 16 GB",
                supplier="Dell Brasil",
                purchase_value="7500.50",
                notes="Atualizado na vistoria.",
                expected_updated_at=_iso(asset.updated_at),
            ),
            follow_redirects=False,
        )
        assert resp.status_code == 303, resp.text
        assert resp.headers["location"] == f"/assets/{asset.id}?updated=true"

        db_session.expire_all()
        atual = db_session.query(Asset).filter_by(id=asset.id).one()
        assert atual.tag == "PAT-06712"  # tombamento imutável (P1)
        assert atual.name == "Notebook 067 Renomeado"
        assert atual.brand == "Dell" and atual.model == "Latitude 5440"
        assert atual.serial_number == "SN-067-1001"
        assert atual.specifications == "Intel i7 / 16 GB"
        assert atual.supplier == "Dell Brasil"
        assert atual.purchase_value == 7500.50
        assert atual.notes == "Atualizado na vistoria."
        assert db_session.query(Asset).count() == total

    def test_editar_bem_autorizado_com_perfil_nao_admin(self, unauth_client, db_session):
        """AC03/AC07 — o caminho real de RBAC (perfil com `patrimonio.editar`)."""
        asset = _make_asset(db_session, tag="PAT-06713", name="Notebook 067")
        _login_com_perfil(unauth_client, db_session, username="editor067")

        resp = unauth_client.post(
            f"/assets/{asset.id}/edit",
            data=_form(brand="Lenovo", expected_updated_at=_iso(asset.updated_at)),
            follow_redirects=False,
        )
        assert resp.status_code == 303, resp.text
        assert resp.headers["location"] == f"/assets/{asset.id}?updated=true"

        db_session.expire_all()
        assert db_session.query(Asset).filter_by(id=asset.id).one().brand == "Lenovo"
        eventos = _eventos_alteracao(db_session, asset.id)
        assert len(eventos) == 1
        assert eventos[0].username == "editor067"

    def test_edicao_serial_duplicado_rejeitada(self, client, db_session):
        """§4.4 — nº de série já usado por outro bem: rejeitar, nada gravado."""
        _make_asset(db_session, tag="PAT-06714", name="A", serial_number="SN-067-DUP")
        b = _make_asset(db_session, tag="PAT-06715", name="B")

        resp = client.post(
            f"/assets/{b.id}/edit",
            data=_form(serial_number="SN-067-DUP", expected_updated_at=_iso(b.updated_at)),
            follow_redirects=False,
        )
        assert resp.status_code == 303, resp.text
        assert resp.headers["location"].startswith(f"/assets/{b.id}/edit?error=")

        db_session.expire_all()
        assert db_session.query(Asset).filter_by(id=b.id).one().serial_number is None
        assert _eventos_alteracao(db_session, b.id) == []

    def test_edicao_valida_limites_e_valor_negativo(self, client, db_session):
        """§4.4 — nome vazio, texto acima do limite e valor negativo: nada gravado."""
        asset = _make_asset(db_session, tag="PAT-06716", name="Notebook 067")
        casos = (
            {"name": "   "},
            {"name": "x" * 151},
            {"brand": "b" * 101},
            {"purchase_value": "-1"},
        )
        for caso in casos:
            resp = client.post(
                f"/assets/{asset.id}/edit",
                data=_form(expected_updated_at=_iso(asset.updated_at), **caso),
                follow_redirects=False,
            )
            assert resp.status_code == 303, (caso, resp.text)
            assert resp.headers["location"].startswith(f"/assets/{asset.id}/edit?error="), caso

        db_session.expire_all()
        atual = db_session.query(Asset).filter_by(id=asset.id).one()
        assert atual.name == "Notebook 067"
        assert atual.brand is None
        assert atual.purchase_value == 0.0
        assert _eventos_alteracao(db_session, asset.id) == []

    def test_edicao_ignora_campos_protegidos_manipulados(self, client, db_session):
        """V5/V6 — `tag`/`status`/`location_id`/`custodian_id` enviados são ignorados."""
        asset = _make_asset(db_session, tag="PAT-06717", name="Notebook 067")
        status_antes, loc_antes, cust_antes = asset.status, asset.location_id, asset.custodian_id

        resp = client.post(
            f"/assets/{asset.id}/edit",
            data=_form(
                name="Notebook 067 Editado",
                tag="HACKEADO-001",
                status=AssetStatus.WRITTEN_OFF.value,
                location_id="987",
                custodian_id="654",
                expected_updated_at=_iso(asset.updated_at),
            ),
            follow_redirects=False,
        )
        assert resp.status_code == 303, resp.text

        db_session.expire_all()
        atual = db_session.query(Asset).filter_by(id=asset.id).one()
        assert atual.name == "Notebook 067 Editado"  # campo autorizado aplicado
        assert atual.tag == "PAT-06717"
        assert atual.status == status_antes
        assert atual.location_id == loc_antes
        assert atual.custodian_id == cust_antes

    def test_edicao_grava_auditoria_com_before_after(self, client, db_session):
        """AC06/FR-006 — 1 evento, autor autenticado e campos de/para."""
        asset = _make_asset(db_session, tag="PAT-06718", name="Notebook 067", brand="Dell")

        resp = client.post(
            f"/assets/{asset.id}/edit",
            data=_form(brand="Lenovo", expected_updated_at=_iso(asset.updated_at)),
            follow_redirects=False,
        )
        assert resp.status_code == 303, resp.text

        eventos = _eventos_alteracao(db_session, asset.id)
        assert len(eventos) == 1
        evento = eventos[0]
        assert evento.resource_ref == "PAT-06718"
        assert evento.username == "testuser"
        assert evento.user_id is not None
        assert "Dell" in (evento.previous_data or "")
        assert "Lenovo" in (evento.new_data or "")

    def test_edicao_sem_alteracao_nao_grava(self, client, db_session):
        """V9 — salvar sem mudanças: sem auditoria vazia e sem movimentação."""
        asset = _make_asset(db_session, tag="PAT-06719", name="Notebook 067")
        movimentos_antes = len(_movimentos_estado(db_session, asset.id))

        resp = client.post(
            f"/assets/{asset.id}/edit",
            data=_form_preenchido(asset),
            follow_redirects=False,
        )
        assert resp.status_code == 303, resp.text
        assert resp.headers["location"] == f"/assets/{asset.id}?unchanged=true"
        assert _eventos_alteracao(db_session, asset.id) == []
        assert len(_movimentos_estado(db_session, asset.id)) == movimentos_antes

    def test_edicao_falha_nao_deixa_estado_parcial(self, client, db_session, monkeypatch):
        """AC11 — falha na trilha desfaz a alteração (transação única)."""
        import app.web.routers.assets as assets_router

        asset = _make_asset(db_session, tag="PAT-06720", name="Notebook 067")

        def _falha(*_args, **_kwargs):
            raise RuntimeError("banco indisponível")

        monkeypatch.setattr(assets_router, "write_change_audit", _falha)

        resp = client.post(
            f"/assets/{asset.id}/edit",
            data=_form(name="Nome Parcial", expected_updated_at=_iso(asset.updated_at)),
            follow_redirects=False,
        )
        assert resp.status_code == 303, resp.text
        local = resp.headers["location"]
        assert local.startswith(f"/assets/{asset.id}/edit?error=")
        assert "RuntimeError" not in local and "banco indisponível" not in local

        db_session.expire_all()
        assert db_session.query(Asset).filter_by(id=asset.id).one().name == "Notebook 067"
        assert _eventos_alteracao(db_session, asset.id) == []

    def test_alteracao_de_condicao_gera_movimentacao_com_operador_autenticado(self, client, db_session):
        """V8/FR-012 — mudar condição gera movimentação com o operador da sessão."""
        asset = _make_asset(db_session, tag="PAT-06721", name="Notebook 067")

        resp = client.post(
            f"/assets/{asset.id}/edit",
            data=_form(
                condition=AssetCondition.GOOD.value,
                expected_updated_at=_iso(asset.updated_at),
            ),
            follow_redirects=False,
        )
        assert resp.status_code == 303, resp.text

        movs = _movimentos_estado(db_session, asset.id)
        assert len(movs) == 1
        assert movs[0].new_condition == AssetCondition.GOOD
        assert movs[0].operator_name == "Usuário de Teste"  # full_name da sessão
        assert movs[0].operator_name != "Sistema"

    def test_edicao_de_bem_baixado_recusada(self, client, db_session):
        """P4 aprovada — bem `BAIXADO`: bloqueado em GET e POST, nada gravado."""
        asset = _make_asset(db_session, tag="PAT-06722", name="Notebook 067")
        asset.status = AssetStatus.WRITTEN_OFF
        db_session.commit()
        esperado = _iso(asset.updated_at)

        get_resp = client.get(f"/assets/{asset.id}/edit", follow_redirects=False)
        assert get_resp.status_code == 303, get_resp.text
        assert get_resp.headers["location"].startswith(f"/assets/{asset.id}?error=")

        post_resp = client.post(
            f"/assets/{asset.id}/edit",
            data=_form(name="Editado", expected_updated_at=esperado),
            follow_redirects=False,
        )
        assert post_resp.status_code == 303, post_resp.text
        assert post_resp.headers["location"].startswith(f"/assets/{asset.id}?error=")

        db_session.expire_all()
        assert db_session.query(Asset).filter_by(id=asset.id).one().name == "Notebook 067"
        assert _eventos_alteracao(db_session, asset.id) == []

    def test_edicao_conflito_de_versao_recusada(self, client, db_session):
        """P3 aprovada — edição concorrente: recusa sem sobrescrita silenciosa."""
        asset = _make_asset(db_session, tag="PAT-06723", name="Notebook 067")

        resp = client.post(
            f"/assets/{asset.id}/edit",
            data=_form(name="Nome Novo", expected_updated_at="2020-01-01T12:00:00"),
            follow_redirects=False,
        )
        assert resp.status_code == 303, resp.text
        assert resp.headers["location"].startswith(f"/assets/{asset.id}/edit?error=")

        db_session.expire_all()
        assert db_session.query(Asset).filter_by(id=asset.id).one().name == "Notebook 067"
        assert _eventos_alteracao(db_session, asset.id) == []

    def test_put_api_grava_operador_autenticado_na_condicao(self, client, db_session):
        """FR-012 também na API — `PUT /api/v1/assets/{id}` com operador da sessão."""
        asset = _make_asset(db_session, tag="PAT-06724", name="Notebook 067")

        resp = client.put(
            f"/api/v1/assets/{asset.id}",
            json={"condition": AssetCondition.FAIR.value},
        )
        assert resp.status_code == 200, resp.text

        movs = _movimentos_estado(db_session, asset.id)
        assert len(movs) == 1
        assert movs[0].new_condition == AssetCondition.FAIR
        assert movs[0].operator_name == "Usuário de Teste"
        assert movs[0].operator_name != "Sistema"


# ============================================================================
# User Story 3 — Histórico de alterações cadastrais consultável (T016 → RED)
# ============================================================================

def _bloco_historico(html: str) -> str:
    """Recorta a seção de histórico cadastral do HTML (marcadores do template)."""
    inicio = html.find('id="historico-cadastral"')
    fim = html.find("<!-- fim do histórico cadastral -->")
    assert inicio != -1, "seção de histórico cadastral ausente no detalhe"
    assert fim != -1, "marcador de fim do histórico cadastral ausente"
    assert fim > inicio
    return html[inicio:fim]


class TestUS3HistoricoCadastral:
    """AC09/AC10/FR-016/FR-017 — histórico separado, legível e com estado vazio."""

    def test_historico_cadastral_separado_de_movimentacoes(self, client, db_session):
        """Após uma edição: campo + de → para + autor, sem misturar movimentações."""
        asset = _make_asset(db_session, tag="PAT-06730", name="Notebook 067", brand="Dell")

        resp = client.post(
            f"/assets/{asset.id}/edit",
            data=_form(brand="Lenovo", expected_updated_at=_iso(asset.updated_at)),
            follow_redirects=False,
        )
        assert resp.status_code == 303, resp.text

        detalhe = client.get(f"/assets/{asset.id}")
        assert detalhe.status_code == 200, detalhe.text
        bloco = _bloco_historico(detalhe.text)

        # AC09 — legível: campo reconhecível, valor anterior e novo, autor e data
        assert "Marca" in bloco
        assert "Dell" in bloco and "Lenovo" in bloco
        # FR-006 — o autor é o snapshot de usuário gravado na trilha
        assert "testuser" in bloco

        # FR-017 — o histórico cadastral NÃO é misturado com a trilha de movimentação
        assert "Origem" not in bloco and "Destino" not in bloco
        assert "Trilha de Fluxo" not in bloco
        # ... e a trilha de movimentação continua na tela, separada
        assert "Trilha de Fluxo" in detalhe.text
        assert "Nenhuma alteração cadastral registrada" not in bloco

    def test_historico_vazio_sem_erro(self, client, db_session):
        """FR-017 — bem sem alterações cadastrais: estado vazio claro, HTTP 200."""
        asset = _make_asset(db_session, tag="PAT-06731", name="Notebook 067")

        resp = client.get(f"/assets/{asset.id}")
        assert resp.status_code == 200, resp.text
        bloco = _bloco_historico(resp.text)
        assert "Nenhuma alteração cadastral registrada" in bloco
        assert "Dell" not in bloco  # nada de dado inventado


def test_historico_limite_e_aviso_de_truncamento(db_session):
    """FR-016 — teto de eventos com aviso explícito (sem truncamento silencioso)."""
    from app.services.audit_service import write_change_audit

    asset = _make_asset(db_session, tag="PAT-06732", name="Notebook 067")
    for i in range(3):
        write_change_audit(
            db_session,
            user=None,
            action="ALTERACAO",
            module="Patrimônio",
            resource="Asset",
            resource_ref="PAT-06732",
            resource_id=asset.id,
            before={"notes": f"nota {i}"},
            after={"notes": f"nota {i + 1}"},
        )

    historico = AssetService.get_cadastral_history(db_session, asset.id, limit=2)
    assert len(historico["eventos"]) == 2
    assert historico["total"] == 3
    assert historico["truncado"] is True

    # Leitura legível: rótulo de negócio + valores anterior/novo (AC09)
    alteracoes = historico["eventos"][0]["changes"]
    assert alteracoes[0]["label"] == "Observações"
    assert alteracoes[0]["before"].startswith("nota ")
    assert alteracoes[0]["after"].startswith("nota ")

    # Sem eventos além do teto → sem aviso
    historico_completo = AssetService.get_cadastral_history(db_session, asset.id, limit=50)
    assert historico_completo["truncado"] is False
    assert len(historico_completo["eventos"]) == 3
