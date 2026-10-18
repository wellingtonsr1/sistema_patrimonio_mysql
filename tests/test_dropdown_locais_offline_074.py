"""
Testes da feature 074 — Dropdown de locais na Conferência Offline.

Reusa o MESMO mecanismo de armazenamento local do inventário: o catálogo de
locais (`[{id, name}]`) entra no PACOTE offline (store `packages` do IndexedDB)
e a coleta passa a gravar `found_location_id`. O contrato de sync e o esquema
de banco NÃO mudam (contrato §3 inalterado; servidor já valida o id).

Cobertura por task (tasks.md):
- T002: contrato do pacote — campo `locations` completo e ordenado.
- T004: retrocompat — template trata pacote antigo (sem `locations`).
- T005: UI — `<select>` com label associado; sem input de texto livre.
- T006: estados — lista ausente vs vazia; registro bloqueado nos dois.
- T009: atualização — re-preparo consistente; pacote somente-leitura; falha
         de rede preserva pacote anterior (SC-005).
- T010: sync — `found_location_id` aceito; FR-009 asset.location_id inalterado.
- T011: integridade/retrocompat — id inválido preserva coleta; nome resolve.
"""

from pathlib import Path

import pytest

from app.models.enums import AssetCategory, AssetCondition, InventarioItemStatus
from app.models.movement import Movement
from app.schemas.asset import AssetCreate
from app.schemas.location import LocationCreate
from app.services.asset_service import AssetService
from app.services.inventario_offline_service import InventarioOfflineService
from app.services.inventario_service import InventarioService
from app.services.location_service import LocationService
from app.models.inventario import Inventario, InventarioItem
from app.models.inventario_offline import InventarioOfflineColeta
from app.models.enums import InventarioOfflineColetaStatus

API = "/api/v1/inventarios/{inv_id}/offline"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OFFLINE_HTML = PROJECT_ROOT / "app" / "web" / "templates" / "inventarios" / "offline.html"
OFFLINE_JS = PROJECT_ROOT / "app" / "web" / "static" / "js" / "inventario_offline.js"


# ============================================================================
# HELPERS
# ============================================================================

def _loc(db, name, branch="Matriz", department="TI"):
    return LocationService.create(db, LocationCreate(name=name, branch=branch, department=department))


def _asset(db, tag, location, name="Notebook Dell"):
    return AssetService.create(db, AssetCreate(
        tag=tag, name=name, category=AssetCategory.NOTEBOOK,
        purchase_value=3500.0, condition=AssetCondition.GOOD,
        initial_location_id=location.id,
    ))


def _inv(db, location, tag_prefix="LOC74", n_assets=1):
    for i in range(n_assets):
        _asset(db, f"{tag_prefix}-{i:04d}", location)
    return InventarioService.create_inventario(
        db, name="Inv 074", location_id=location.id, created_by_name="admin",
    )


def _op(op_id, item_id, asset_id, *, result="LOCAL_DIFERENTE", loc_id=None, loc_name=None):
    return {
        "client_operation_id": op_id, "operation": "CHECK",
        "asset_id": asset_id, "item_id": item_id, "result": result,
        "found_location_id": loc_id, "found_location_name": loc_name,
        "observation": None, "collected_at": "2026-10-18T10:00:00-03:00",
    }


def _sync(client, inv_id, snapshot, ops, device="device-074"):
    return client.post(
        API.format(inv_id=inv_id) + "/sync",
        json={"device_id": device, "snapshot_version": snapshot, "operations": ops},
    )


# ============================================================================
# Phase 2 — Foundational (T002 contrato; T004 retrocompat)
# ============================================================================

class TestPacoteCarregaCatalogo:
    def test_pacote_inclui_locations_completo_e_ordenado(self, client, db_session):
        """T002: pacote traz `locations` = todos os locais, ordem get_all, chaves {id,name}."""
        _loc(db_session, "Almoxarifado Central", branch="Matriz", department="Almox")
        _loc(db_session, "Sala dos Servidores", branch="Matriz", department="TI")
        base = _loc(db_session, "Recepcao", branch="Filial", department="Adm")
        inv = _inv(db_session, base, tag_prefix="PKG", n_assets=1)

        resp = client.post(API.format(inv_id=inv.id) + "/package")
        assert resp.status_code == 200, resp.text
        locs = resp.json()["locations"]

        # Mesma fonte/ordem exibida pela Conferência Online (LocationService.get_all)
        esperado = [l.name for l in LocationService.get_all(db_session)]
        assert [l["name"] for l in locs] == esperado
        assert len(locs) == 3, "todos os locais cadastrados devem vir no pacote"
        for l in locs:
            assert set(l.keys()) == {"id", "name"}
            assert isinstance(l["id"], int) and l["name"]

    def test_locations_reflete_cadastro_apos_novo_local(self, client, db_session):
        """T002/T009: novo local cadastrado aparece no pacote re-preparado."""
        base = _loc(db_session, "Base", branch="M", department="D")
        inv = _inv(db_session, base, tag_prefix="PKG2")
        _loc(db_session, "Novo Setor", branch="M", department="Z")

        body = client.post(API.format(inv_id=inv.id) + "/package").json()
        assert "Novo Setor" in [l["name"] for l in body["locations"]]


# ============================================================================
# Phase 3 — US1 (T004 retrocompat; T005 select; T006 estados)
# ============================================================================

class TestUIDropdown:
    def test_template_troca_input_texto_por_select(self, client):
        """T005: `<select id="mFoundLocationId">` com label; SEM input de texto livre."""
        html = OFFLINE_HTML.read_text(encoding="utf-8")
        assert 'id="mFoundLocationId"' in html
        assert 'for="mFoundLocationId"' in html
        assert "form-select" in html
        assert 'id="mFoundLocationName"' not in html, "input de texto livre deve ter sido removido"

    def test_template_trata_pacote_antigo_sem_locations(self, client):
        """T004: pacote antigo (sem `locations`) cai em estado de lista indisponível."""
        html = OFFLINE_HTML.read_text(encoding="utf-8")
        # Guarda que trata `locations` ausente (pacote legado) — nunca inventa opções
        assert "Array.isArray" in html and "locations" in html
        assert "prepare a coleta offline" in html, "orientação de re-preparar pacote antigo ausente"

    def test_template_distingue_lista_vazia_e_indisponivel(self, client):
        """T006: mensagens distintas para lista vazia (sem cadastro) vs indisponível."""
        html = OFFLINE_HTML.read_text(encoding="utf-8")
        assert "Nenhum local cadastrado" in html, "estado de lista vazia ausente"
        assert "prepare a coleta offline" in html, "estado de lista indisponível ausente"


# ============================================================================
# Phase 4 — US2 (T009 atualização/preservação)
# ============================================================================

class TestAtualizacaoPreservacao:
    def test_repreparo_pacote_e_consistente(self, client, db_session):
        """T009(a): re-preparo substitui o pacote e as locations seguem o cadastro."""
        base = _loc(db_session, "Base", branch="M", department="D")
        inv = _inv(db_session, base, tag_prefix="REP")
        api = API.format(inv_id=inv.id) + "/package"

        b1 = client.post(api).json()
        _loc(db_session, "Adicional", branch="M", department="E")
        b2 = client.post(api).json()

        assert set(l["name"] for l in b2["locations"]) >= set(l["name"] for l in b1["locations"])
        assert "Adicional" in [l["name"] for l in b2["locations"]]

    def test_pacote_somente_leitura_nao_altera_cadastro(self, client, db_session):
        """T009(b)/FR-005: gerar o pacote não escreve nem altera o cadastro de locais."""
        base = _loc(db_session, "Base RO", branch="M", department="D")
        inv = _inv(db_session, base, tag_prefix="RO")
        from app.models.location import Location
        before = db_session.query(Location).count()

        client.post(API.format(inv_id=inv.id) + "/package")
        after = db_session.query(Location).count()
        assert after == before, "preparação não pode criar/alterar locais"

    def test_js_persist_pacote_apos_resposta_ok(self, client):
        """T009(c)/SC-005: savePackage só roda no .then (resposta OK); erro → .catch sem persistir."""
        js = OFFLINE_JS.read_text(encoding="utf-8")
        # Fluxo prepareFromDetail: fetch → .then(valida status) → .then(pkg => savePackage) → .catch
        assert ".then(function (pkg) { return savePackage(pkg); })" in js
        assert js.index("return savePackage(pkg)") > js.index("if (resp.status === 409)")
        assert ".catch(function (err)" in js


# ============================================================================
# Phase 5 — US3 (T010 sync id + FR-009; T011 integridade/retrocompat)
# ============================================================================

class TestSyncPorId:
    def test_sync_local_diferente_por_id_e_nao_altera_cadastro(self, client, db_session):
        """T010 + FR-009: sync aceita found_location_id; asset.location_id INALTERADO (Constitution IV)."""
        base = _loc(db_session, "Base Sync", branch="M", department="D")
        destino = _loc(db_session, "Outro Setor", branch="M", department="Z")
        inv = _inv(db_session, base, tag_prefix="SYN")
        item = inv.itens[0]
        snapshot = InventarioOfflineService.compute_snapshot_version(db_session, inv.id)
        asset_id, item_id = item.asset_id, item.id
        mov_before = db_session.query(Movement).count()

        resp = _sync(client, inv.id, snapshot, [
            _op("op-sync-001", item_id, asset_id, loc_id=destino.id),
        ])
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["accepted"]) == 1, resp.text

        db_session.expire_all()
        item2 = db_session.get(InventarioItem, item_id)
        assert item2.found_location_id == destino.id
        # FR-009 / Constitution IV: a localização cadastral NÃO muda
        asset2 = db_session.get(type(item.asset), asset_id)
        assert asset2.location_id == base.id, "conferência não altera cadastro patrimonial"
        assert db_session.query(Movement).count() == mov_before, "nenhuma movimentação criada"


class TestIntegridadeERetrocompat:
    def test_id_inexistente_rejeita_preserva_coleta(self, client, db_session):
        """T011(a)/FR-011: found_location_id inválido → rejeição estável; coleta PRESERVADA."""
        base = _loc(db_session, "Base RI", branch="M", department="D")
        inv = _inv(db_session, base, tag_prefix="RID")
        item = inv.itens[0]
        snapshot = InventarioOfflineService.compute_snapshot_version(db_session, inv.id)

        resp = _sync(client, inv.id, snapshot, [
            _op("op-ri-001", item.id, item.asset_id, loc_id=999999),
        ])
        out = resp.json()
        assert len(out["rejected"]) == 1 and out["rejected"][0]["reason"] == "local_inexistente"
        row = db_session.query(InventarioOfflineColeta).filter_by(client_operation_id="op-ri-001").first()
        assert row is not None and row.status == InventarioOfflineColetaStatus.REJECTED, "coleta não pode ser descartada"

    def test_nome_legado_ainda_resolve(self, client, db_session):
        """T011(b)/FR-012: coleta antiga só com found_location_name (nome único) é aceita."""
        base = _loc(db_session, "Base Legado", branch="M", department="D")
        destino = _loc(db_session, "Destino Legado", branch="M", department="Z")
        inv = _inv(db_session, base, tag_prefix="LEG")
        item = inv.itens[0]
        snapshot = InventarioOfflineService.compute_snapshot_version(db_session, inv.id)

        resp = _sync(client, inv.id, snapshot, [
            _op("op-leg-001", item.id, item.asset_id, loc_name="Destino Legado"),
        ])
        assert len(resp.json()["accepted"]) == 1, resp.text
        db_session.expire_all()
        assert db_session.get(InventarioItem, item.id).found_location_id == destino.id

    def test_local_diferente_sem_local_rejeita(self, client, db_session):
        """T011(c)/FR-011: LOCAL_DIFERENTE sem id/nome → rejeição; nada atribuído automaticamente."""
        base = _loc(db_session, "Base SemLocal", branch="M", department="D")
        inv = _inv(db_session, base, tag_prefix="NOL")
        item = inv.itens[0]
        snapshot = InventarioOfflineService.compute_snapshot_version(db_session, inv.id)

        resp = _sync(client, inv.id, snapshot, [
            _op("op-nol-001", item.id, item.asset_id),
        ])
        out = resp.json()
        assert len(out["rejected"]) == 1 and out["rejected"][0]["reason"] == "local_nao_resolvido"
        db_session.expire_all()
        assert db_session.get(InventarioItem, item.id).found_location_id is None
