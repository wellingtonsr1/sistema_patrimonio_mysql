"""Feature 070 — Legibilidade dos eventos de alteração cadastral na trilha (detalhe do Equipamento).

Arquivo de TESTE da FEATURE 070 (`specs/070-legibilidade-trilha-auditoria/`).
Agenda (research R9):

  US1 (T003/T004/T005 → RED; T006–T008 → GREEN): resumo legível no cartão de
      auditoria da trilha — título contextual, rótulos amigáveis, antes → depois
      no padrão do painel "Alterações cadastrais", JSON completo fora do conteúdo
      principal, descrição suprimida quando há resumo e preservada no fallback.
  US2 (T009 → RED; T010 → GREEN): controle "<details> Ver detalhes técnicos"
      recolhido por padrão, JSON original Antes/Depois, wrap sem overflow,
      renderização segura de payload hostil, fallback de um único estado.
  US3 (T011 — verde-verde): guarda de não-mutação da trilha, payload da API
      idêntico (sem `audit_summary`), cartões de movimentação 063 e painel
      cadastrais 067 intactos.

Padrão da casa (063/064/067): fixtures `client`/`db_session` (SQLite em memória),
massa via `AssetService.create`, edição real via `POST /assets/{id}/edit`, e a
prova é o HTML renderizado / estado do banco — não detalhes de roteamento.

SCOPE (não é nosso): zero teste existente alterado, zero DDL, zero mudança em
`movement_service.py`, `audit_service.py` ou `app/api/` (contracts C1–C10).
"""

import json
import re
from datetime import datetime

from app.models.audit_log import AuditLog
from app.models.enums import AssetCategory, AssetCondition, MovementType
from app.schemas.asset import AssetCreate
from app.schemas.movement import MovementCreate
from app.services.asset_service import AssetService
from app.services.movement_service import MovementService


# ============================================================================
# Helpers de massa (espelham tests/test_consulta_edicao_bens_067.py)
# ============================================================================

def _make_asset(db_session, tag="PAT-07000", name="Notebook 070", **overrides) -> object:
    payload = {
        "tag": tag,
        "name": name,
        "category": AssetCategory.NOTEBOOK,
        "purchase_value": 0.0,
    }
    payload.update(overrides)
    return AssetService.create(db_session, AssetCreate(**payload))


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _form(asset, **overrides) -> dict:
    """Payload do POST `/assets/{id}/edit` com o formulário pré-preenchido."""
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
        "expected_updated_at": _iso(asset.updated_at),
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


def _bloco_painel_070(html: str) -> str:
    """Trecho do HTML a partir do painel `#historico-cadastral`.

    Hub necessário ao ajuste FR-010 (071): os asserts de legibilidade migraram
    da trilha para o painel "Alterações cadastrais" — seção exclusiva das
    alterações cadastrais a partir da 071.
    """
    return html.split('id="historico-cadastral"', 1)[1].split("Trilha de Fluxo", 1)[0]


def _area_visivel(bloco: str) -> str:
    """Remove os blocos <details>...</details> (detalhes técnicos recolhidos)."""
    return re.sub(r"<details\b.*?</details>", "", bloco, flags=re.S)


def _evento_audit(db_session, asset_id: int, descricao: str = None) -> AuditLog:
    db_session.expire_all()
    query = (
        db_session.query(AuditLog)
        .filter(AuditLog.resource == "Asset", AuditLog.resource_id == asset_id)
    )
    if descricao:
        query = query.filter(AuditLog.description == descricao)
    return query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).first()


def _gravar_evento(db_session, asset, *, previous_data, new_data,
                   description="Evento de teste 070",
                   action="ALTERACAO") -> AuditLog:
    """Insere um evento de auditoria diretamente (caminho de dados históricos).

    071 (T012): `action` parametrizável — eventos de alteração cadastral
    (ALTERACAO) migram para o painel; os plantados com ação atípica exercitam
    o cartão do fallback US3, que permanece na trilha.
    """
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
# User Story 1 — Resumo legível (T003/T004/T005 RED → T006–T008 GREEN)
# ============================================================================

class TestUS1ResumoLegivel:
    """AC01–AC04/AC12 — o cartão de alteração cadastral é legível sem JSON."""

    def test_campo_unico_titulo_rrotulo_antes_depois(self, client, db_session):
        """T003/AC01/AC04 — um campo alterado: rótulo + antes → depois legíveis.

        071 (FR-010 §6, Constitution VIII): a alteração cadastral deixou de ser
        renderizada na trilha e é exclusiva do painel "Alterações cadastrais"
        (mesmo aparato legível da 070). Asserts migrados da trilha para o
        painel — nenhum assert enfraquecido.
        """
        asset = _make_asset(db_session, tag="PAT-07001",
                            name="Scaners Fujitsu mod. 6140Z")
        _editar(client, asset, name="Scaners Fujitsu mod. 6140z")

        html = client.get(f"/assets/{asset.id}").text
        painel = _bloco_painel_070(html)
        trilha = _bloco_trilha(html)

        # Painel é a seção exclusiva e identificada das alterações cadastrais
        assert "Alterações cadastrais" in painel, (
            "a legibilidade das alterações cadastrais deve viver no painel (071 FR-002)"
        )

        # Rótulo amigável + antes riscado + depois em destaque (padrão do painel)
        assert "Nome do bem" in painel
        assert "Scaners Fujitsu mod. 6140Z" in painel, "valor ANTERIOR ausente"
        assert "Scaners Fujitsu mod. 6140z" in painel, "valor POSTERIOR ausente"

        # 071 — o evento não vira cartão na trilha (FR-001)
        assert "Alteração cadastral" not in trilha, (
            "ALTERACAO não pode voltar à trilha (071 FR-001)"
        )
        visivel = _area_visivel(trilha)
        assert '"tag"' not in visivel, (
            "o snapshot JSON não pode aparecer fora dos detalhes técnicos"
        )

    def test_varios_campos_todos_listados_inalterados_ausentes(self, client, db_session):
        """T004/AC02/AC03 — vários campos listados; campos inalterados fora.

        071 (FR-010): asserts migrados para o painel "Alterações cadastrais",
        que lista TODAS as alterações do evento (fonte única das mudanças).
        """
        asset = _make_asset(db_session, tag="PAT-07002", name="Notebook 070 II")
        _editar(client, asset,
                name="Notebook 070 III", brand="Dell", supplier="Dell Brasil")

        painel = _bloco_painel_070(client.get(f"/assets/{asset.id}").text)

        assert "Alterações cadastrais" in painel
        for rotulo, valores in (
            ("Nome do bem", ("Notebook 070 II", "Notebook 070 III")),
            ("Marca", ("Dell",)),
            ("Fornecedor", ("Dell Brasil",)),
        ):
            assert rotulo in painel, f"rótulo ausente do painel: {rotulo}"
            for valor in valores:
                assert valor in painel, f"valor ausente do painel: {valor!r}"

        # Campo NÃO alterado não ocupa espaço no painel ( Categoria nunca mudou )
        assert "Categoria" not in painel, (
            "campo inalterado não pode aparecer na apresentação resumida"
        )

    def test_campo_desconhecido_e_fallbacks(self, client, db_session):
        """T005/AC04/AC08/AC12 — campo fora do mapeamento exibido pelo nome
        técnico; evento sem diff preserva a descrição atual; descrição é
        suprimida quando existe resumo (M4).

        071 (FR-010): os eventos de suporte são plantados com ação atípica para
        exercitar o cartão do fallback na trilha (o ALTERACAO real mora no
        painel; a parte (c) cobre o fluxo real de edição). O aparato e os
        asserts não mudam.
        """
        asset = _make_asset(db_session, tag="PAT-07003", name="Notebook 070 IV")

        # (a) evento histórico com chave desconhecida → nome técnico, sem quebra
        _gravar_evento(
            db_session, asset,
            previous_data={"campo_futuro": "x"}, new_data={"campo_futuro": "y"},
            description="Campos alterados: campo_futuro",
            action="HISTORICO_ATIPO",
        )
        # (b) evento sem dados de estado → descrição atual preservada
        _gravar_evento(
            db_session, asset, previous_data=None, new_data=None,
            description="Evento legado sem estados registrados",
            action="HISTORICO_ATIPO",
        )

        resp = client.get(f"/assets/{asset.id}")
        assert resp.status_code == 200, resp.text
        bloco = _bloco_trilha(resp.text)

        assert "campo_futuro" in bloco, "campo desconhecido deve ser exibido pelo nome técnico"
        assert "admin" in bloco or "Evento legado sem estados registrados" in bloco, (
            "nenhum evento pode ficar órfão — os registros (mesmo sem diff) continuam acessíveis"
        )

        # (c) fluxo real de edição (071 FR-010): a alteração cadastral mora no
        # painel, listando os campos alterados; a linha 'Campos alterados: ...'
        # (mensagem técnica) não pode coexistir com a lista legível (M4).
        asset_b = _make_asset(db_session, tag="PAT-07004", name="Notebook 070 V")
        _editar(client, asset_b, name="Notebook 070 VI")
        html_b = client.get(f"/assets/{asset_b.id}").text
        painel_b = _bloco_painel_070(html_b)
        trilha_b = _bloco_trilha(html_b)
        assert "Nome do bem" in painel_b
        assert "Notebook 070 VI" in painel_b
        assert "Campos alterados" not in painel_b, (
            "a descrição técnica não pode aparecer junto da lista legível do painel"
        )
        assert "Alteração cadastral" not in trilha_b, (
            "071 FR-001 — a edição não pode voltar à trilha"
        )


# ============================================================================
# User Story 2 — Detalhes técnicos expansíveis (T009 RED → T010 GREEN)
# ============================================================================

class TestUS2DetalhesTecnicos:
    """AC05/AC06/AC09/AC10 — <details> recolhido, JSON original, renderização segura."""

    def test_details_recolhido_por_padrao_com_json_completo(self, client, db_session):
        """T009/AC05/AC06 — controle recolhido (sem `open`) com Antes/Depois.

        071 (FR-010 §6): a apresentação 070 permanece VIVA na trilha para os
        eventos NÃO cadastrais atípicos (fallback US3). O evento de suporte passa
        a ser plantado com ação atípica — o assert e o aparato testado não mudam
        (o resumo 070 depende dos dados de estado, não da ação).
        """
        asset = _make_asset(db_session, tag="PAT-07005", name="Notebook 070 Detalhe")
        _gravar_evento(
            db_session, asset,
            previous_data={"name": "Notebook 070 Detalhe"},
            new_data={"name": "Notebook 070 Detalhe v2"},
            description="Campos alterados: name",
            action="HISTORICO_ATIPO",
        )

        bloco = _bloco_trilha(client.get(f"/assets/{asset.id}").text)

        # Recolhido por padrão: <details SEM atributo open (M5)
        detalhes = re.findall(r"<details\b[^>]*>.*?</details>", bloco, flags=re.S)
        assert detalhes, "o cartão deve oferecer o controle <details> de detalhes técnicos"
        for bloco_detalhe in detalhes:
            assert "open" not in _bloco_detalhes_open_attr(bloco_detalhe), (
                "detalhes devem permanecer recolhidos por padrão"
            )
        assert "Ver detalhes técnicos" in bloco, "nome acessível do controle ausente"

        # Estados originais completos e distinguíveis dentro do <details> (M6)
        conteudo = detalhes[0]
        assert "Antes:" in conteudo and "Depois:" in conteudo
        assert '"name": "Notebook 070 Detalhe"' in conteudo, "JSON original ANTES ausente"
        assert '"name": "Notebook 070 Detalhe v2"' in conteudo, "JSON original DEPOIS ausente"

    def test_wrap_sem_overflow_e_estilos(self, client, db_session):
        """T009/AC14/AC09 — <pre> com wrap para objetos extensos (M7).

        071 (FR-010): evento plantado atípico para exercitar o cartão do fallback.
        """
        asset = _make_asset(db_session, tag="PAT-07006", name="Notebook 070 Wrap")
        _gravar_evento(
            db_session, asset,
            previous_data={"name": "Notebook 070 Wrap", "notes": "limpo"},
            new_data={"name": "Notebook 070 Wrap", "notes": "Nota com " + ("texto longo " * 50)},
            description="Campos alterados: notes",
            action="HISTORICO_ATIPO",
        )

        bloco = _bloco_trilha(client.get(f"/assets/{asset.id}").text)
        assert "white-space:pre-wrap" in bloco, "JSON extenso deve quebrar linha (M7)"
        assert "word-break:break-word" in bloco

    def test_payload_hostil_exibido_como_dado(self, client, db_session):
        """T009/AC10 — HTML/JavaScript em valores nunca é executado (M6).

        071 (FR-010): evento plantado atípico — o cartão do fallback mantém o
        mesmo escape.
        """
        asset = _make_asset(db_session, tag="PAT-07007", name="Notebook 070 Seguro")
        hostil = "<script>alert(1)</script>"
        _gravar_evento(
            db_session, asset,
            previous_data={"name": "Notebook 070 Seguro", "notes": "limpo"},
            new_data={"name": "Notebook 070 Seguro", "notes": hostil},
            description="Campos alterados: notes",
            action="HISTORICO_ATIPO",
        )

        html = client.get(f"/assets/{asset.id}").text
        assert "<script>alert(1)</script>" not in html, (
            "o dado hostil não pode chegar ao HTML como script executável"
        )
        assert "\\u003cscript" in html or "&lt;script&gt;" in html, (
            "o dado hostil deve aparecer ESCAPADO (texto/dado)"
        )

    def test_um_estado_solo_fallback(self, client, db_session):
        """T009/AC08/R6.2 — apenas um estado: sem resumo, detalhes com o lado
        disponível e descrição preservada.

        071 (FR-010): evento plantado atípico — o solo-state é comportamento do
        fallback, que permanece na trilha.
        """
        asset = _make_asset(db_session, tag="PAT-07008", name="Notebook 070 Parcial")
        _gravar_evento(
            db_session, asset, previous_data=None,
            new_data={"name": "Notebook 070 Parcial", "brand": "Lenovo"},
            description="Evento histórico com estado parcial",
            action="HISTORICO_ATIPO",
        )

        bloco = _bloco_trilha(client.get(f"/assets/{asset.id}").text)

        assert "Evento histórico com estado parcial" in bloco, "descrição deve ser preservada"
        assert "Alteração cadastral —" not in bloco, (
            "sem diff utilizável não pode haver título de resumo"
        )
        detalhe = re.search(r"<details\b[^>]*>.*?</details>", bloco, flags=re.S)
        assert detalhe, "os detalhes técnicos devem funcionar com um único estado"
        assert "Depois:" in detalhe.group(0)
        assert "Antes:" not in detalhe.group(0), "sem estado anterior não pode haver rótulo"


def _bloco_detalhes_open_attr(bloco_detalhe: str) -> str:
    """Atributos da tag <details> (para verificar ausência de `open`)."""
    return re.match(r"<details\b[^>]*>", bloco_detalhe).group(0)


# ============================================================================
# User Story 3 — Preservação integral (T011 — verde-verde: as guardas passam
# ANTES e CONTINUAM passando depois da feature — contracts C1–C6)
# ============================================================================

class TestUS3Preservacao:
    """AC07/AC11/AC15/AC16 — nada além da apresentação mudou."""

    def test_nao_mutacao_audit_logs(self, client, db_session):
        """AC07/C4 — a renderização não altera nenhum registro de auditoria."""
        asset = _make_asset(db_session, tag="PAT-07009", name="Notebook 070 Guarda")
        _editar(client, asset, name="Notebook 070 Guarda v2")

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
        """AC16/C2 — a API entrega o payload atual; `audit_summary` NUNCA vaza."""
        asset = _make_asset(db_session, tag="PAT-07010", name="Notebook 070 API")
        _editar(client, asset, name="Notebook 070 API v2")

        resp = client.get(f"/api/v1/assets/{asset.id}/timeline")
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert "audit_summary" not in resp.text

        chaves_esperadas = {
            "id", "action", "module", "resource", "resource_id", "resource_ref",
            "username", "result", "description", "previous_data", "new_data",
        }
        eventos = [item for item in payload if item["type"] == "audit"]
        assert eventos, "o payload deve continuar entregando os eventos de auditoria"
        for item in eventos:
            assert "audit_summary" not in item
            assert set(item["data"].keys()) == chaves_esperadas, (
                "o contrato de chaves do payload da API mudou (C2)"
            )

        # Os estados desserializados batem com o service (fonte única intacta)
        service = MovementService.get_timeline_for_asset(db_session, asset.id)
        api_novo = next(i for i in eventos if i["data"]["action"] == "ALTERACAO")
        svc_novo = next(i for i in service if i["type"] == "audit")
        assert api_novo["data"]["new_data"] == svc_novo["new_data"]
        assert api_novo["data"]["previous_data"] == svc_novo["prev_data"]

    def test_cartao_movimentacao_intacto_063(self, client, db_session):
        """AC11/C6 — cartões de movimentação no padrão 063 permanecem intactos."""
        from app.schemas.location import LocationCreate
        from app.services.location_service import LocationService

        loc_a = LocationService.create(
            db_session, LocationCreate(name="Sala A", branch="Unidade A", department="Dept A"))
        loc_b = LocationService.create(
            db_session, LocationCreate(name="Sala B", branch="Unidade B", department="Dept B"))
        asset = _make_asset(db_session, tag="PAT-07011", name="Notebook 070 Fluxo",
                            initial_location_id=loc_a.id)
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id, movement_type=MovementType.ACQUISITION,
            reason="Entrada 070", operator_name="Validador 070"))
        MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id, movement_type=MovementType.TRANSFER,
            destination_location_id=loc_b.id,
            reason="Transferência 070", operator_name="Validador 070"))
        db_session.commit()

        bloco = _bloco_trilha(client.get(f"/assets/{asset.id}").text)
        assert "Origem" in bloco and "Destino" in bloco, "cartão de movimentação alterado"
        assert "Dept A" in bloco and "Dept B" in bloco, (
            "títulos de localização no padrão 063 (department) alterados"
        )

    def test_painel_alteracoes_cadastrais_intacto_067(self, client, db_session):
        """AC11/C5 — o painel superior 067 permanece idêntico e separado."""
        asset = _make_asset(db_session, tag="PAT-07012", name="Notebook 070 Painel")
        _editar(client, asset, name="Notebook 070 Painel v2")

        html = client.get(f"/assets/{asset.id}").text
        painel = html.split('id="historico-cadastral"', 1)[1].split("Trilha de Fluxo", 1)[0]
        assert "Alterações cadastrais" in painel, "painel 067 desapareceu"
        assert "Nome do bem" in painel, "resumo do painel 067 alterado"
        assert "text-decoration-line-through" in painel, (
            "padrão visual do painel 067 (valor riscado) alterado"
        )
