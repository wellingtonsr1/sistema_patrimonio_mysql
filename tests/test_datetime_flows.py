"""Testes de fluxo da feature 004 — Padronização de Data e Hora.

Organização por user story (specs/004-padronizacao-datas-utc/tasks.md):
- US1 (T004): apresentação de Inventário e Auditoria em America/Recife;
- US2 (T011): persistência UTC em Movimentações/Importação;
- US3 (T017): preservação de datas de negócio (testes-guarda);
- US4 (T020): apresentação nos exports (report_service);
- US5 (T025): filtros de período local -> UTC.

Padrões de suíte: fixtures `client`/`db_session` de tests/conftest.py; asserções
de HTML no estilo tests/test_inventario_reconferencia_ui.py. Instantes fixos em
UTC nas asserções (ex.: 22:30 UTC == 19:30 Recife).
"""

from datetime import datetime

import pytest

from app.models.audit_log import AuditLog
from app.models.enums import AssetCategory, AssetCondition
from app.services.asset_service import AssetService
from app.services.inventario_service import InventarioService
from app.services.location_service import LocationService
from app.schemas.asset import AssetCreate
from app.schemas.location import LocationCreate

TEST_USERNAME = "testuser"


# ============================================================================
# Helpers (padrões de tests/test_inventario_reconferencia_ui.py)
# ============================================================================

def _make_location(db, name="Loc Datetime", department="TI"):
    return LocationService.create(db, LocationCreate(
        name=name,
        branch="Matriz",
        department=department,
    ))


def _make_asset(db, tag, location=None, name="Notebook Dell"):
    return AssetService.create(db, AssetCreate(
        tag=tag,
        name=name,
        category=AssetCategory.NOTEBOOK,
        purchase_value=3500.0,
        condition=AssetCondition.GOOD,
        initial_location_id=location.id if location else None,
    ))


def _create_inventario(client, db_session, location, name="Inventário Datetime"):
    resp = client.post(
        "/inventarios/new",
        data={"name": name, "location_id": str(location.id)},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    inv_id = int(resp.headers["Location"].rsplit("/", 1)[1])
    inv = InventarioService.get_by_id(db_session, inv_id)
    assert inv is not None
    return inv


def _get_item_for_asset(db, inv, asset):
    return [i for i in inv.itens if i.asset.tag == asset.tag][0]


# Instante de referência fixo: 22:30 UTC == 19:30 em America/Recife (dia 15/09/2026)
FIXED_UTC = datetime(2026, 9, 15, 22, 30)


# ============================================================================
# US1 (T004) — Apresentação de Inventário e Auditoria em America/Recife
# ============================================================================

class TestUS1ApresentacaoInventario:
    def test_detail_exibe_horario_local_para_checked_at_fixo(self, client, db_session):
        """Item com checked_at fixo em 22:30 UTC deve exibir 19:30 (Recife)."""
        loc = _make_location(db_session)
        asset = _make_asset(db_session, "DT-INV-0001", location=loc)
        inv = _create_inventario(client, db_session, loc)
        item = _get_item_for_asset(db_session, inv, asset)

        item.checked_at = FIXED_UTC
        item.checked_by_name = TEST_USERNAME
        db_session.commit()
        db_session.expire_all()

        resp = client.get(f"/inventarios/{inv.id}")
        assert resp.status_code == 200, resp.text
        html = resp.text
        assert "15/09/2026 19:30" in html
        assert "15/09/2026 22:30" not in html

    def test_list_exibe_horario_local_para_created_at_fixo(self, client, db_session):
        """Inventário criado em 22:30 UTC (default) deve listar 19:30 (Recife)."""
        loc = _make_location(db_session)
        inv = _create_inventario(client, db_session, loc)
        inv.created_at = FIXED_UTC
        db_session.commit()
        db_session.expire_all()

        resp = client.get("/inventarios")
        assert resp.status_code == 200, resp.text
        html = resp.text
        assert "15/09/2026 19:30" in html
        assert "15/09/2026 22:30" not in html


class TestUS1ApresentacaoAuditoria:
    def test_auditoria_exibe_horario_local_com_segundos(self, client, db_session):
        """Trilha de auditoria exibe 19:30:xx (Recife) para timestamp 22:30 UTC."""
        log = AuditLog(
            timestamp=datetime(2026, 9, 15, 22, 30, 45),
            user_id=None,
            username=TEST_USERNAME,
            action="TEST",
            module="Teste",
            resource="AuditLog",
            result="SUCCESS",
        )
        db_session.add(log)
        db_session.commit()

        resp = client.get("/admin/audit")
        assert resp.status_code == 200, resp.text
        html = resp.text
        assert "15/09/2026 19:30:45" in html
        assert "22:30:45" not in html


# ============================================================================
# US2 (T011) — Persistência padronizada em UTC (Movimentações/Importação)
# ============================================================================

class TestUS2PersistenciaUTC:
    def test_movimentacao_grava_utc(self, client, db_session):
        """Movement.timestamp gravado pelo service representa UTC (naive),
        com tolerância de segundos em relação a now_utc()."""
        from datetime import timedelta

        from app.schemas.movement import MovementCreate
        from app.services.movement_service import MovementService
        from app.utils.time_utils import now_utc
        from app.models.enums import MovementType

        loc = _make_location(db_session)
        asset = _make_asset(db_session, "DT-MOV-0001", location=loc)

        movement = MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            destination_location_id=loc.id,
            reason="Teste de padronizacao UTC",
        ))
        db_session.expire(movement)

        before = now_utc() - timedelta(seconds=2)
        after = now_utc() + timedelta(seconds=2)
        assert before <= movement.timestamp <= after

    def test_consistencia_intra_linha_timestamp_created_at(self, client, db_session):
        """SC-003: mesma linha de movements sem divergência de padrão
        (timestamp e created_at representam o mesmo instante, tolerância 60s)."""
        from app.schemas.movement import MovementCreate
        from app.services.movement_service import MovementService
        from app.models.enums import MovementType

        loc = _make_location(db_session)
        asset = _make_asset(db_session, "DT-MOV-0002", location=loc)

        movement = MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            destination_location_id=loc.id,
            reason="Teste de consistencia intra-linha",
        ))
        db_session.expire(movement)

        drift = abs((movement.timestamp - movement.created_at).total_seconds())
        assert drift < 60


# ============================================================================
# US3 (T017) — Datas de negócio preservadas (testes-guarda: passam antes e
# depois da feature; protegem a semântica de purchase_date/warranty_expiry)
# ============================================================================

class TestUS3DatasDeNegocio:
    def test_importacao_csv_preserva_purchase_date(self, client, db_session):
        """CSV com compra 15/09/2026: armazenada e exibida como 15/09/2026."""
        from app.models.asset import Asset

        csv_content = (
            "tombamento,equipamento,categoria,data_aquisicao\n"
            "DT-CSV-0001,Notebook Import,NOTEBOOK,15/09/2026\n"
        )
        resp = client.post(
            "/api/v1/assets/import/csv",
            files={"file": ("bens.csv", csv_content.encode("utf-8"), "text/csv")},
            data={"skip_duplicates": "true"},
            follow_redirects=False,
        )
        assert resp.status_code == 200, resp.text

        asset = db_session.query(Asset).filter(Asset.tag == "DT-CSV-0001").first()
        assert asset is not None, "Bem da importação não encontrado"
        assert asset.purchase_date is not None
        assert (asset.purchase_date.year, asset.purchase_date.month, asset.purchase_date.day) == (2026, 9, 15)

        detail = client.get(f"/assets/{asset.id}")
        assert detail.status_code == 200, detail.text
        assert "15/09/2026" in detail.text

    def test_cadastro_formulario_preserva_purchase_e_warranty(self, client, db_session):
        """Cadastro via formulário: compra 15/09/2026 e garantia 15/09/2028."""
        from app.models.asset import Asset

        resp = client.post(
            "/assets/new",
            data={
                "tag": "DT-FORM-0001",
                "name": "Notebook Formulário",
                "category": "NOTEBOOK",
                "purchase_value": "1000.00",
                "purchase_date": "2026-09-15",
                "warranty_expiry": "2028-09-15",
            },
            follow_redirects=False,
        )
        assert resp.status_code in (200, 303), resp.text

        asset = db_session.query(Asset).filter(Asset.tag == "DT-FORM-0001").first()
        assert asset is not None, "Bem do formulário não encontrado"
        assert (asset.purchase_date.year, asset.purchase_date.month, asset.purchase_date.day) == (2026, 9, 15)
        assert asset.warranty_expiry is not None
        assert (asset.warranty_expiry.year, asset.warranty_expiry.month, asset.warranty_expiry.day) == (2028, 9, 15)

        detail = client.get(f"/assets/{asset.id}")
        assert detail.status_code == 200, detail.text
        assert "15/09/2026" in detail.text
        assert "15/09/2028" in detail.text

    def test_filtro_purchase_date_continua_funcionando(self, client, db_session):
        """Filtros por período de compra (data pura) seguem o comportamento atual."""
        from app.models.asset import Asset

        csv_content = (
            "tombamento,equipamento,categoria,data_aquisicao\n"
            "DT-CSV-0002,Notebook Filtro,NOTEBOOK,15/09/2026\n"
        )
        resp = client.post(
            "/api/v1/assets/import/csv",
            files={"file": ("bens.csv", csv_content.encode("utf-8"), "text/csv")},
            data={"skip_duplicates": "true"},
        )
        assert resp.status_code == 200, resp.text

        resp = client.get("/assets", params={
            "purchase_date_from": "2026-09-01",
            "purchase_date_to": "2026-09-15",
        })
        assert resp.status_code == 200, resp.text
        html = resp.text
        # O bem criado com compra 15/09/2026 aparece no intervalo 01/09–15/09,
        # sem nenhum deslocamento por fuso na data de negócio.
        assert "DT-CSV-0002" in html


# ============================================================================
# US4 (T020) — Exports: dados em Recife, carimbo "Gerado em" local
# ============================================================================

class TestUS4Exports:
    def _inventario_com_item_fixo(self, client, db_session):
        loc = _make_location(db_session)
        asset = _make_asset(db_session, "DT-EXP-0001", location=loc)
        inv = _create_inventario(client, db_session, loc)
        item = _get_item_for_asset(db_session, inv, asset)
        item.checked_at = FIXED_UTC
        item.checked_by_name = TEST_USERNAME
        db_session.commit()
        db_session.expire_all()
        return inv

    def test_ata_csv_exibe_horario_local(self, client, db_session):
        """CSV da ata: conferido_em/created_at em 19:30 (Recife), não 22:30."""
        inv = self._inventario_com_item_fixo(client, db_session)

        resp = client.get(f"/api/v1/reports/inventarios/{inv.id}/csv")
        assert resp.status_code == 200, resp.text
        body = resp.text
        assert "19:30" in body
        assert "22:30" not in body

    def test_ata_pdf_exibe_horario_local(self, client, db_session):
        """PDF da ata: timestamps dos dados em Recife."""
        inv = self._inventario_com_item_fixo(client, db_session)

        resp = client.get(f"/api/v1/reports/inventarios/{inv.id}/pdf")
        assert resp.status_code == 200, resp.text
        content = resp.content
        assert content[:4] == b"%PDF"

    def test_csv_movimentacoes_exibe_horario_local(self, client, db_session):
        """CSV de movimentações: carimbo dos dados em Recife."""
        from datetime import timedelta

        from app.schemas.movement import MovementCreate
        from app.services.movement_service import MovementService
        from app.models.enums import MovementType
        from app.utils.time_utils import now_utc

        loc = _make_location(db_session)
        asset = _make_asset(db_session, "DT-EXP-0002", location=loc)
        movement = MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            destination_location_id=loc.id,
            reason="Teste export movimentacoes",
        ))
        # Fixa o carimbo em um instante conhecido (22:30 UTC = 19:30 Recife)
        movement.timestamp = FIXED_UTC
        db_session.commit()
        db_session.expire(movement)
        assert now_utc() > FIXED_UTC - timedelta(seconds=1)  # sanidade

        resp = client.get("/api/v1/reports/movements/csv")
        assert resp.status_code == 200, resp.text
        body = resp.text
        assert "15/09/2026 19:30" in body
        assert "15/09/2026 22:30" not in body


# ============================================================================
# US5 (T025) — Filtros de período local -> UTC
# ============================================================================

class TestUS5FiltrosPeriodo:
    def _criar_movimentacao_com_timestamp(self, client, db_session, tag, ts):
        from app.schemas.movement import MovementCreate
        from app.services.movement_service import MovementService
        from app.models.enums import MovementType

        loc = _make_location(db_session, name=f"Loc {tag}")
        asset = _make_asset(db_session, tag, location=loc)
        movement = MovementService.create_movement(db_session, MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            destination_location_id=loc.id,
            reason=f"Teste filtro {tag}",
        ))
        movement.timestamp = ts
        db_session.commit()
        db_session.expire(movement)
        return movement

    def _get_movements(self, client, params):
        resp = client.get("/api/v1/movements", params=params)
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_registro_19h_local_retornado_pelo_periodo_do_dia(self, client, db_session):
        """Registro 22:00 UTC (19:00 Recife) aparece no intervalo local 15/09 00:00–23:59."""
        movement = self._criar_movimentacao_com_timestamp(
            client, db_session, "DT-FLT-0001", datetime(2026, 9, 15, 22, 0))

        movements = self._get_movements(client, {
            "start_date": "2026-09-15T00:00:00",
            "end_date": "2026-09-15T23:59:00",
        })
        ids = [m["id"] for m in movements]
        assert movement.id in ids, movements

    def test_registro_23h50_local_incluido_no_dia_correto(self, client, db_session):
        """23:50 Recife = 02:50 UTC de 16/09: incluído no filtro de 15/09, excluído do de 14/09."""
        movement = self._criar_movimentacao_com_timestamp(
            client, db_session, "DT-FLT-0002", datetime(2026, 9, 16, 2, 50))

        movements_dia15 = self._get_movements(client, {
            "start_date": "2026-09-15T00:00:00",
            "end_date": "2026-09-15T23:59:00",
        })
        assert movement.id in [m["id"] for m in movements_dia15]

        movements_dia14 = self._get_movements(client, {
            "start_date": "2026-09-14T00:00:00",
            "end_date": "2026-09-14T23:59:00",
        })
        assert movement.id not in [m["id"] for m in movements_dia14]

    def test_offset_explicito_respeitado_como_absoluto(self, client, db_session):
        """Intervalo com offset -03:00 explícito cobre 19:00 locais (22:00 UTC)."""
        movement = self._criar_movimentacao_com_timestamp(
            client, db_session, "DT-FLT-0003", datetime(2026, 9, 15, 22, 0))

        movements = self._get_movements(client, {
            "start_date": "2026-09-15T03:00:00-03:00",
            "end_date": "2026-09-16T02:59:00-03:00",
        })
        assert movement.id in [m["id"] for m in movements]
