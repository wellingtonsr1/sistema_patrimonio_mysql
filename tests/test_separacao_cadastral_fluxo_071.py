"""Feature 071 — Separação entre Alterações Cadastrais e Trilha de Fluxo & Movimentações.

Arquivo de TESTE da FEATURE 071 (`specs/071-separar-cadastrais-fluxo/`).

Agenda:

  US1 (T008/T009/T010 GREEN): a trilha deixa de renderizar eventos `ALTERACAO`
      duplicados — as alterações cadastrais ficam EXCLUSIVAS no painel
      `#historico-cadastral`; movimentações permanecem na trilha.
  US2 (T012/T013/T014): preservação — `audit_logs` byte-a-byte, payload da API
      `/timeline` idêntico (C1/C2) e painel com teto 50 + aviso `truncado`.
  US3 (T015): fallback — eventos de auditoria NÃO cadastrais atípicos continuam
      renderizados na trilha com o aparato da 070; `ALTERACAO` é exclusivo do painel.

Padrão da casa (063/064/067/070): fixtures `client`/`db_session` (SQLite em
memória), massa via `AssetService.create`, edição real via `POST /assets/{id}/edit`,
e a prova é o HTML renderizado / estado do banco — não detalhes de roteamento.

SCOPE (não é nosso): zero mudança em `movement_service.py`, `audit_service.py`,
`app/api/` (contracts C1–C10), model ou migração.
"""

import json
import re
from datetime import datetime

from app.models.audit_log import AuditLog
from app.models.enums import AssetCategory, MovementType
from app.schemas.asset import AssetCreate
from app.schemas.movement import MovementCreate
from app.services.asset_service import AssetService
from app.services.movement_service import MovementService

# ============================================================================
# Helpers de massa
# ============================================================================

def _make_asset(db_session, tag="PAT-07100", name="Notebook 071", **overrides):
    """Cria um bem pelo serviço (fonte única do cadastro)."""
    payload = {
        "tag": tag,
        "name": name,
        "category": AssetCategory.NOTEBOOK,
        "purchase_value": 0.0,
    }
    payload.update(overrides)
    return AssetService.create(db_session, AssetCreate(**payload))


def _form(asset, **overrides):
    """Corpo do POST `/assets/{id}/edit` — padrão EXATO do formulário (067/070)."""
    data = {
        "name": asset.name,
        "category": asset.category.value,
        "brand": asset.brand or "",
        "model": asset.model or "",
        "serial_number": asset.serial_number or "",
        "specifications": asset.specifications or "",
        "purchase_date": asset.purchase_date.strftime("%Y-%m-%d") if asset.purchase_date else "",
        "purchase_value": f"{asset.purchase_value or 0.0:.2f}",
        "invoice_number": asset.invoice_number or "",
        "supplier": asset.supplier or "",
        "warranty_expiry": asset.warranty_expiry.strftime("%Y-%m-%d") if asset.warranty_expiry else "",
        "condition": asset.condition.value,
        "notes": asset.notes or "",
        "expected_updated_at": asset.updated_at.strftime("%Y-%m-%dT%H:%M:%S") if asset.updated_at else "",
    }
    data.update(overrides)
    return data


def _editar(client, asset, **overrides) -> None:
    """Edita o cadastro pelo fluxo real (grava ALTERACAO com before/after)."""
    resp = client.post(
        f"/assets/{asset.id}/edit",
        data=_form(asset, **overrides),
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    assert "updated=true" in resp.headers["location"], resp.headers["location"]


def _bloco_trilha(html: str) -> str:
    """Trecho do HTML a partir da seção da trilha (o painel cadastral fica acima)."""
    return html.split("Trilha de Fluxo & Movimentações", 1)[1]


def _bloco_painel(html: str) -> str:
    """Trecho do HTML a partir do painel `#historico-cadastral`."""
    return html.split('id="historico-cadastral"', 1)[1].split("Trilha de Fluxo", 1)[0]


def _gravar_evento(db_session, asset, *, previous_data, new_data,
                   description="Evento de teste 071", action="ALTERACAO") -> AuditLog:
    """Insere um evento de auditoria diretamente (caminho de dados históricos)."""
    entry = AuditLog(
        timestamp=datetime.utcnow(),
        username="admin",
        action=action,
        module="Patrimônio",
        resource="Asset",
        resource_id=asset.id,
        resource_ref=asset.tag,
        description=description,
        previous_data=json.dumps(previous_data) if previous_data is not None else None,
        new_data=json.dumps(new_data) if new_data is not None else None,
    )
    db_session.add(entry)
    db_session.commit()
    return entry


# ============================================================================
# US1 — Separar: ALTERACAO no painel, NUNCA na trilha (T008/T009/T010)
# ============================================================================

class TestUS1Separacao:
    """Spec §4 US1 / §3 R-C1, R-C3 — classificação pela ação, painel exclusivo."""

    def test_edicao_sai_da_trilha_e_fica_no_painel(self, client, db_session):
        """FR-001/FR-002 — a edição gravada como ALTERACAO some da trilha e
        permanece legível no painel (rótulo + antes → depois)."""
        asset = _make_asset(db_session, tag="PAT-07101", name="Scanner Fujitsu 6140Z")
        _editar(client, asset, name="Scanner Fujitsu 6140z")

        html = client.get(f"/assets/{asset.id}").text
        painel = _bloco_painel(html)
        trilha = _bloco_trilha(html)

        # Painel: alteração cadastral legível (padrão 067)
        assert "Nome do bem" in painel, "rótulo do campo ausente no painel"
        assert "Scanner Fujitsu 6140Z" in painel, "valor ANTERIOR ausente no painel"
        assert "Scanner Fujitsu 6140z" in painel, "valor POSTERIOR ausente no painel"
        assert "text-decoration-line-through" in painel, (
            "padrão visual do painel 067 (valor riscado) alterado"
        )

        # Trilha: ZERO cartões de alteração cadastral
        assert "Alteração cadastral" not in trilha, (
            "071 proíbe exibir ALTERACAO na trilha — o filtro da rota não foi aplicado"
        )
        assert "Campos alterados" not in trilha

    def test_varios_campos_painel_trilha_sem_cartoes(self, client, db_session):
        """FR-001/FR-002 — vários campos alterados: painel lista todos; trilha limpa."""
        asset = _make_asset(db_session, tag="PAT-07102", name="Notebook 071 II")
        _editar(client, asset, name="Notebook 071 III", brand="Dell", supplier="Dell Brasil")

        html = client.get(f"/assets/{asset.id}").text
        painel = _bloco_painel(html)
        trilha = _bloco_trilha(html)

        for rotulo, valor in (("Nome do bem", "Notebook 071 III"),
                              ("Marca", "Dell"),
                              ("Fornecedor", "Dell Brasil")):
            assert rotulo in painel, f"rótulo ausente no painel: {rotulo}"
            assert valor in painel, f"valor ausente no painel: {valor!r}"

        # R-C3: classificação pela ação — nada de cartão cadastral na trilha
        assert "Alteração cadastral" not in trilha

    def test_movimentacao_permanece_na_trilha(self, client, db_session):
        """AC02/AC06/AC07 — movimentação física segue exatamente como antes."""
        from app.schemas.location import LocationCreate
        from app.services.location_service import LocationService

        loc_a = LocationService.create(db_session, LocationCreate(
            name="Sala A 071", branch="Unidade A", department="Dept A"))
        loc_b = LocationService.create(db_session, LocationCreate(
            name="Sala B 071", branch="Unidade B", department="Dept B"))
        asset = _make_asset(db_session, tag="PAT-07103", name="Notebook 071 Fluxo",
                            initial_location_id=loc_a.id)
        _editar(client, asset, name="Notebook 071 Fluxo v2")
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id, movement_type=MovementType.TRANSFER,
            destination_location_id=loc_b.id,
            reason="Transferência 071", operator_name="Validador 071"))
        db_session.commit()

        trilha = _bloco_trilha(client.get(f"/assets/{asset.id}").text)

        # Movimentação 063/064 intocada
        assert "Origem" in trilha and "Destino" in trilha, "cartão de movimentação alterado"
        assert "Dept A" in trilha and "Dept B" in trilha
        assert "Transferência 071" in trilha
        assert "Validador 071" in trilha

        # E a edição cadastral NÃO voltou como cartão
        assert "Alteração cadastral" not in trilha

    def test_evento_misto_um_registro_por_secao(self, client, db_session):
        """AC08/FR-007 — edição que muda condição: ALTERACAO no painel E
        movimentação ATUALIZACAO_ESTADO na trilha; sem duplicação nem perda."""
        asset = _make_asset(db_session, tag="PAT-07104", name="Notebook 071 Misto")
        _editar(client, asset, condition="EXCELENTE")

        html = client.get(f"/assets/{asset.id}").text
        painel = _bloco_painel(html)
        trilha = _bloco_trilha(html)

        # Painel: a alteração cadastral (condição)
        assert "Estado de Conservação" in painel, "alteração de condição ausente no painel"
        assert "NOVO" in painel, "valor anterior da condição ausente no painel"
        assert "EXCELENTE" in painel, "valor posterior da condição ausente no painel"

        # Trilha: a movimentação de estado gerada pelo motor (V8/067);  o
        # registro cadastral equivalente NÃO aparece como cartão.
        assert "Atualização de Estado" in trilha, (
            "movimentação ATUALIZACAO_ESTADO ausente da trilha — eventos mistos não podem perder o lado físico"
        )
        assert "Alteração cadastral" not in trilha


# ============================================================================
# US2 — Acessibilidade do histórico cadastral garantida (T012/T013/T014)
# ============================================================================

class TestUS2Preservacao:
    """AC09/AC12 — zero bytes em `audit_logs`; API idêntica; painel 50 + truncado."""

    def test_nao_mutacao_audit_logs(self, client, db_session):
        """C4 — a renderização não altera nenhum registro de auditoria."""
        asset = _make_asset(db_session, tag="PAT-07105", name="Notebook 071 Guarda")
        _editar(client, asset, name="Notebook 071 Guarda v2")

        def snapshot():
            db_session.expire_all()
            return [
                (e.id, e.description, e.previous_data, e.new_data)
                for e in db_session.query(AuditLog)
                .filter(AuditLog.resource_id == asset.id)
                .order_by(AuditLog.id).all()
            ]

        antes = snapshot()
        assert client.get(f"/assets/{asset.id}").status_code == 200
        assert snapshot() == antes, "a renderização alterou registros de auditoria"

    def test_payload_api_timeline_identico(self, client, db_session):
        """C1/C2 — API /timeline continua entregando movimentações E eventos de
        auditoria (incl. ALTERACAO); `audit_summary` NUNCA vaza; chaves intactas."""
        asset = _make_asset(db_session, tag="PAT-07106", name="Notebook 071 API")
        _editar(client, asset, name="Notebook 071 API v2")

        resp = client.get(f"/api/v1/assets/{asset.id}/timeline")
        assert resp.status_code == 200, resp.text
        assert "audit_summary" not in resp.text

        eventos = [i for i in resp.json() if i["type"] == "audit"]
        assert eventos, "o payload da API deve continuar entregando os eventos de auditoria"
        assert any(i["data"]["action"] == "ALTERACAO" for i in eventos), (
            "o service (fonte única) não pode perder os eventos ALTERACAO — só a TELA os filtra"
        )

        chaves_esperadas = {
            "id", "action", "module", "resource", "resource_id", "resource_ref",
            "username", "result", "description", "previous_data", "new_data",
        }
        for item in eventos:
            assert "audit_summary" not in item
            assert set(item["data"].keys()) == chaves_esperadas, (
                "o contrato de chaves do payload da API mudou (C2)"
            )

    def test_painel_teto_50_com_aviso_truncado(self, client, db_session):
        """SC-005/AC09 — bem com mais de 50 edições: painel exibe as 50 mais
        recentes + aviso `truncado`; histórico completo segue em /admin/audit."""
        asset = _make_asset(db_session, tag="PAT-07107", name="Notebook 071 Muitos")
        for i in range(55):
            db_session.expire_all()  # o objeto precisa do updated_at fresco (otimismo P3)
            _editar(client, asset, name=f"Notebook 071 Muitos v{i}")

        painel = _bloco_painel(client.get(f"/assets/{asset.id}").text)

        assert "Notebook 071 Muitos v54" in painel, "edição mais recente ausente do painel"
        assert "Notebook 071 Muitos v0" not in painel, (
            "edições além do teto 50 não podem aparecer no painel"
        )
        assert "Existem alterações anteriores não listadas" in painel and "50" in painel, (
            "aviso de truncamento do painel ausente"
        )

    def test_sem_cadastral_a_trilha_fica_vazia_de_auditoria(self, client, db_session):
        """Consequência SC-001 — bem sem movimentações e só com edições: a trilha
        não exibe NENHUM cartão de auditoria (e não quebra o estado vazio)."""
        asset = _make_asset(db_session, tag="PAT-07108", name="Notebook 071 Sozinho")
        _editar(client, asset, name="Notebook 071 Sozinho v2")

        html = client.get(f"/assets/{asset.id}").text
        trilha = _bloco_trilha(html)

        assert "Alteração cadastral" not in trilha
        assert client.get(f"/assets/{asset.id}").status_code == 200


# ============================================================================
# US3 — Fallback: eventos NÃO cadastrais atípicos permanecem na trilha (T015)
# ============================================================================

class TestUS3Fallback:
    """AC11/FR-006/R-C2 — nada de evento desconhecido é engolido pela separação."""

    def test_evento_atipico_sem_estado_permanece_na_trilha(self, client, db_session):
        """Evento histórico atípico (não ALTERACAO) com apenas descrição:
        cartão segue na trilha com a descrição preservada (fallback 070)."""
        asset = _make_asset(db_session, tag="PAT-07109", name="Notebook 071 Legacy")
        _gravar_evento(db_session, asset, previous_data=None, new_data=None,
                       description="Evento histórico sem estados registrados",
                       action="HISTORICO_ATIPO")

        trilha = _bloco_trilha(client.get(f"/assets/{asset.id}").text)

        assert "Evento histórico sem estados registrados" in trilha, (
            "evento não cadastral desapareceu da trilha — fallback R-C2 violado"
        )
        assert "Historico Atipo" in trilha, (
            "ação atípica deve renderizar com o rótulo de fallback do action_label"
        )

    def test_evento_atipico_com_estado_parcial_usa_fallback_solo_070(self, client, db_session):
        """Evento histórico atípico COM apenas UM estado: o aparato 070 permanece
        vivo no fallback — descrição preservada, SEM título de resumo (sem diff
        utilizável) e <details> com o lado disponível (padrão do solo-state 070)."""
        asset = _make_asset(db_session, tag="PAT-07110", name="Notebook 071 Parcial")
        _gravar_evento(db_session, asset, previous_data=None,
                       new_data={"name": "Notebook 071 Parcial", "brand": "Lenovo"},
                       description="Evento histórico com estado parcial",
                       action="HISTORICO_ATIPO")

        bloco = _bloco_trilha(client.get(f"/assets/{asset.id}").text)

        assert "Evento histórico com estado parcial" in bloco, "descrição deve ser preservada"
        detalhes = re.findall(r"<details\b[^>]*>.*?</details>", bloco, flags=re.S)
        assert detalhes, "detalhes técnicos 070 ausentes no cartão de fallback"
        assert "Depois:" in detalhes[0]
        assert "Antes:" not in detalhes[0], "sem estado anterior não pode haver rótulo"
        assert "Lenovo" in bloco, "estado parcial deve continuar visível (dados, não executável)"

    def test_edicao_que_angaria_fallback_nao_gera_atipico_falso(self, client, db_session):
        """R-C3 — a classificação usa a AÇÃO; a edição real (ALTERACAO) nunca
        pode reaparecer na trilha sob qualquer apresentação."""
        asset = _make_asset(db_session, tag="PAT-07111", name="Notebook 071 Regra")
        _editar(client, asset, name="Notebook 071 Regra v2")

        html = client.get(f"/assets/{asset.id}").text
        painel = _bloco_painel(html)
        trilha = _bloco_trilha(html)

        assert "Nome do bem" in painel and "Notebook 071 Regra v2" in painel
        assert "Alteração cadastral" not in trilha
