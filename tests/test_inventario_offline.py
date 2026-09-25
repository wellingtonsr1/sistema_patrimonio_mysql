"""
Testes da feature 033 — Conferência de Inventário Offline (PWA + SW + IndexedDB).

Cobertura do lado SERVIDOR (o comportamento exclusivo do navegador — fila
IndexedDB, persistência local, cache do Service Worker — é validado pelos
cenários manuais do quickstart C2/C4, conforme registrado na spec).

Cenários de origem cobertos (SC-010): preparação (1), permissão negada (2),
sincronização (10–15), conflito, múltiplos dispositivos, datas, auditoria e
segurança (17–19).

Regras-chave exercitadas ( Constitution/spec ):
- Princípio V/FR-026: gravação do item EXCLUSIVAMENTE via InventarioService.
- C-2/P-2: preparação só em PLANNED/IN_PROGRESS; encerrado → 409.
- C-5/FR-027: resultado igual → duplicated; diferente → CONFLICT preservado.
- FR-005/SC-007: preparação/sync NUNCA alteram o cadastro patrimonial.
- FR-044: auditoria INVENTARIO_OFFLINE_* sem credenciais.
"""

import pytest

from app.models.audit_log import AuditLog
from app.models.enums import (
    AssetCategory,
    AssetCondition,
    InventarioItemStatus,
    InventarioStatus,
)
from app.models.inventario_offline import InventarioOfflineColeta
from app.models.enums import InventarioOfflineColetaStatus
from app.schemas.asset import AssetCreate
from app.schemas.location import LocationCreate
from app.services.asset_service import AssetService
from app.services.audit_service import (
    ACTION_ACCESS_DENIED,
    ACTION_INVENTARIO_OFFLINE_CONFLITO,
    ACTION_INVENTARIO_OFFLINE_PREPARADO,
    ACTION_INVENTARIO_OFFLINE_REJEITADO,
    ACTION_INVENTARIO_OFFLINE_RECONCILED,
    ACTION_INVENTARIO_OFFLINE_SYNC,
)
from app.services.inventario_offline_service import (
    InventarioOfflineService,
    OfflinePackageError,
)
from app.services.inventario_service import InventarioService
from app.services.location_service import LocationService
from app.services.permission_service import (
    assign_role,
    create_role,
    ensure_default_roles,
    get_role_by_name,
)

API = "/api/v1/inventarios/{inv_id}/offline"


# ============================================================================
# HELPERS
# ============================================================================

def _make_location(db, name="Matriz - TI - Sala dos Servidores", department="Tecnologia da Informação"):
    return LocationService.create(db, LocationCreate(
        name=name, branch="Matriz", department=department,
    ))


def _make_asset(db, tag, location=None, name="Notebook Dell", serial=None):
    return AssetService.create(db, AssetCreate(
        tag=tag,
        name=name,
        category=AssetCategory.NOTEBOOK,
        purchase_value=3500.0,
        condition=AssetCondition.GOOD,
        serial_number=serial,
        initial_location_id=location.id if location else None,
    ))


def _make_inventario(db, location, n_assets=1, tag_prefix="OFF-TST"):
    for i in range(n_assets):
        _make_asset(db, f"{tag_prefix}-{i:04d}", location=location)
    return InventarioService.create_inventario(
        db, name="Inventário Offline", location_id=location.id, created_by_name="admin",
    )


def _close(db, inv):
    """Encerra marcando todos os itens como ENCONTRADO (fluxo online)."""
    for item in inv.itens:
        if item.status == InventarioItemStatus.PENDING and not item.nao_previsto:
            InventarioService.record_check(
                db, item=item, result=InventarioItemStatus.FOUND, username="closer",
            )
    InventarioService.close_inventario(db, inventario=inv, closed_by_name="closer")
    db.refresh(inv)
    return inv


def _user_with_perm(db, username, permission):
    """Usuário NÃO-admin com uma permissão específica (RBAC deny by default)."""
    ensure_default_roles(db)
    from app.services.auth_service import create_user
    user = create_user(db, username=username, password="senha@1234", is_admin=False)
    role = create_role(db, f"role-{username}")
    from app.models.permission import Permission
    perm = db.query(Permission).filter(Permission.name == permission).first()
    from app.models.role_permission import RolePermission
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()
    assign_role(db, user, role)
    return user


def _login(client, username, password="senha@1234"):
    resp = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp


def _op_check(op_id, item_id, asset_id, *, result="ENCONTRADO", loc_id=None, cust_id=None, obs=None):
    return {
        "client_operation_id": op_id,
        "operation": "CHECK",
        "asset_id": asset_id,
        "item_id": item_id,
        "result": result,
        "found_location_id": loc_id,
        "found_custodian_id": cust_id,
        "observation": obs,
        "collected_at": "2026-09-24T09:12:00-03:00",
    }


def _sync(client, inv_id, pkg_version, ops, device_id="device-test-0001"):
    return client.post(
        API.format(inv_id=inv_id) + "/sync",
        json={"device_id": device_id, "snapshot_version": pkg_version, "operations": ops},
    )


# ============================================================================
# US1 — Preparação do pacote offline (T007)
# ============================================================================

class TestUS1Preparacao:
    def test_401_sem_sessao(self, unauth_client, db_session):
        loc = _make_location(db_session)
        inv = _make_inventario(db_session, loc)
        resp = unauth_client.post(API.format(inv_id=inv.id) + "/package")
        assert resp.status_code == 401

    def test_403_sem_permissao_e_auditado(self, client, db_session):
        _user_with_perm(db_session, "semperm", "inventario.visualizar")
        _login(client, "semperm")
        loc = _make_location(db_session)
        inv = _make_inventario(db_session, loc)
        resp = client.post(API.format(inv_id=inv.id) + "/package")
        assert resp.status_code == 403
        evt = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == ACTION_ACCESS_DENIED)
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert evt is not None

    def test_pacote_com_campos_minimos_apenas(self, client, db_session):
        """FR-003/SC-008: somente os dados mínimos; nada administrativo/credencial."""
        loc = _make_location(db_session)
        _make_asset(db_session, "OFF-TST-9001", location=loc, serial="SN-9A2C")
        inv = InventarioService.create_inventario(db_session, name="Pacote", location_id=loc.id)

        resp = client.post(API.format(inv_id=inv.id) + "/package")
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["inventory_id"] == inv.id
        assert body["inventory_code"] == inv.code
        assert body["snapshot_version"] and len(body["snapshot_version"]) == 64  # SHA-256
        assert body["expires_when"] == "inventory_closed_or_reprepared"
        assert len(body["items"]) == 1

        item = body["items"][0]
        # Feature 034 (H-3/D4): pacote não contém chaves de custodiante para nenhum inventário
        assert set(item.keys()) == {
            "asset_id", "item_id", "tag", "serial_number", "description",
            "expected_location_id", "expected_location_name", "qr_url",
        }
        assert item["serial_number"] == "SN-9A2C"
        assert item["qr_url"].endswith(f"/assets/{item['asset_id']}")
        # Nada de credenciais/dados administrativos em qualquer ponto do payload
        text = str(body).lower()
        for forbidden in ("password", "senha", "token", "hash", "permission"):
            assert forbidden not in text

    def test_pacote_sem_chaves_de_custodiante_mesmo_legado(self, client, db_session):
        """Feature 034 (H-3/D4): pacote não contém expected_custodian_id/name — nem p/ item legado."""
        loc = _make_location(db_session)
        _make_asset(db_session, "OFF-TST-9101", location=loc)
        inv = InventarioService.create_inventario(db_session, name="Pacote Legado 034", location_id=loc.id)
        item = inv.itens[0]
        item.expected_custodian_name = "Maria Legado"  # simula inventário legado (gravação direta)
        db_session.commit()

        resp = client.post(API.format(inv_id=inv.id) + "/package")
        assert resp.status_code == 200, resp.text
        item_payload = resp.json()["items"][0]
        assert "expected_custodian_id" not in item_payload
        assert "expected_custodian_name" not in item_payload
        assert "Maria Legado" not in str(item_payload)

    def test_409_inventario_encerrado(self, client, db_session):
        loc = _make_location(db_session)
        inv = _close(db_session, _make_inventario(db_session, loc))
        resp = client.post(API.format(inv_id=inv.id) + "/package")
        assert resp.status_code == 409
        assert "encerrado" in resp.json()["detail"].lower()

    def test_422_sem_itens(self, client, db_session):
        loc = _make_location(db_session)
        inv = InventarioService.create_inventario(db_session, name="Vazio", location_id=loc.id)
        # remove os itens esperados (nenhum bem no escopo: cria e esvazia)
        for item in list(inv.itens):
            db_session.delete(item)
        db_session.commit()
        resp = client.post(API.format(inv_id=inv.id) + "/package")
        assert resp.status_code == 422

    def test_422_acima_de_mil_itens(self, client, db_session):
        loc = _make_location(db_session)
        # 1.001 bens no escopo → snapshot acima do limite (criação direta, rápida)
        from app.models.asset import Asset
        assets = [
            Asset(tag=f"VOL-{i:05d}", name="Vol", category=AssetCategory.NOTEBOOK,
                  purchase_value=1.0, status=None, condition=AssetCondition.GOOD,
                  location_id=loc.id)
            for i in range(1001)
        ]
        db_session.add_all(assets)
        db_session.commit()
        inv = InventarioService.create_inventario(db_session, name="Volume", location_id=loc.id)
        assert len(inv.itens) > 1000
        resp = client.post(API.format(inv_id=inv.id) + "/package")
        assert resp.status_code == 422

    def test_preparacao_nao_altera_dados_oficiais(self, client, db_session):
        """FR-005/SC-007: zero write no cadastro decorrente da preparação."""
        loc = _make_location(db_session)
        asset = _make_asset(db_session, "OFF-TST-9002", location=loc)
        inv = InventarioService.create_inventario(db_session, name="NoWrite", location_id=loc.id)
        before = (asset.location_id, asset.status, asset.updated_at if hasattr(asset, "updated_at") else None)

        resp = client.post(API.format(inv_id=inv.id) + "/package")
        assert resp.status_code == 200

        db_session.refresh(asset)
        assert (asset.location_id, asset.status) == before[:2]
        # snapshot do pacote = snapshot do item (mesma fonte, sem mutação)
        item = inv.itens[0]
        assert item.status == InventarioItemStatus.PENDING

    def test_snapshot_version_deterministico(self, client, db_session):
        """FR-004: mesmo snapshot → mesma versão; itens novos → versão nova."""
        loc = _make_location(db_session)
        _make_asset(db_session, "OFF-TST-9003", location=loc)
        inv = InventarioService.create_inventario(db_session, name="Determin.", location_id=loc.id)

        v1 = client.post(API.format(inv_id=inv.id) + "/package").json()["snapshot_version"]
        v2 = client.post(API.format(inv_id=inv.id) + "/package").json()["snapshot_version"]
        assert v1 == v2

        # Bem novo no cadastro NÃO altera a base (snapshot imune — Princípio V).
        _make_asset(db_session, "OFF-TST-9004", location=loc)
        db_session.expire_all()
        v3 = client.post(API.format(inv_id=inv.id) + "/package").json()["snapshot_version"]
        assert v3 == v1

        # A versão identifica a BASE de coleta (conjunto de itens do snapshot —
        # D9 ajustado no tasks.md): conferência online altera o STATUS por
        # design (C-3/C-5) e NÃO invalida o pacote; adicionar item ao snapshot
        # (não previsto → previsto não é possível; novo inventário sim) mudaria.
        item = inv.itens[0]
        InventarioService.record_check(
            db_session, item=item, result=InventarioItemStatus.FOUND, username="conf"
        )
        v4 = client.post(API.format(inv_id=inv.id) + "/package").json()["snapshot_version"]
        assert v4 == v1  # base inalterada: pacote continua válido (C-5 idempotente)

    def test_auditoria_preparado_sem_credenciais(self, client, db_session):
        loc = _make_location(db_session)
        _make_asset(db_session, "OFF-TST-9005", location=loc)
        inv = InventarioService.create_inventario(db_session, name="Audit", location_id=loc.id)

        client.post(API.format(inv_id=inv.id) + "/package")

        evt = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == ACTION_INVENTARIO_OFFLINE_PREPARADO)
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert evt is not None
        text = f"{evt.description or ''}{evt.new_data or ''}".lower()
        for forbidden in ("password", "senha", "token", "cookie"):
            assert forbidden not in text


# ============================================================================
# US2 — Área de coleta offline: shell web + validações (T015)
# ============================================================================

class TestUS2ShellEColeta:
    def test_shell_exige_login(self, unauth_client, db_session):
        loc = _make_location(db_session)
        inv = _make_inventario(db_session, loc)
        resp = unauth_client.get(f"/inventarios/{inv.id}/offline", follow_redirects=False)
        assert resp.status_code in (303, 401)  # redirect p/ login ou 401 API

    def test_shell_exige_permissao_visualizar(self, client, db_session):
        _user_with_perm(db_session, "sinv", "inventario.conferir")  # sem visualizar
        _login(client, "sinv")
        loc = _make_location(db_session)
        inv = _make_inventario(db_session, loc)
        resp = client.get(f"/inventarios/{inv.id}/offline")
        assert resp.status_code == 403

    def test_shell_renderiza_sem_dados_administrativos(self, client, db_session):
        loc = _make_location(db_session)
        inv = _make_inventario(db_session, loc)
        resp = client.get(f"/inventarios/{inv.id}/offline")
        assert resp.status_code == 200
        html = resp.text.lower()
        assert "coleta offline" in html
        for forbidden in ("admin/users", "admin/roles", "admin/audit"):
            assert forbidden not in html

    def test_deriva_local_diferente_como_online(self, db_session):
        """C-3: mesma regra de derivação do fluxo online (record_check)."""
        from app.models.asset import Asset
        loc = _make_location(db_session)
        loc2 = _make_location(db_session, name="Outro Local", department="RH")
        asset = _make_asset(db_session, "OFF-TST-9500", location=loc)
        inv = InventarioService.create_inventario(db_session, name="C3", location_id=loc.id)
        item = inv.itens[0]

        InventarioService.record_check(
            db_session, item=item, result=InventarioItemStatus.FOUND_WRONG_LOCATION,
            found_location_id=loc2.id, username="coletor",
        )
        db_session.refresh(item)
        assert item.status == InventarioItemStatus.FOUND_WRONG_LOCATION
        assert item.found_location_id == loc2.id
        # FR-013/SC-007: cadastro NUNCA alterado pela coleta
        db_session.refresh(asset)
        assert asset.location_id == loc.id

    def test_operacao_unlisted_aceita_validacao(self, db_session):
        """FR-014: bem fora do snapshot é ocorrência via register_unlisted_asset."""
        loc = _make_location(db_session)
        inv = InventarioService.create_inventario(db_session, name="Unlisted", location_id=loc.id)
        # bem criado DEPOIS do inventário → fora do snapshot (nao_previsto)
        asset_fora = _make_asset(db_session, "OFF-TST-9600", location=loc)
        item, created = InventarioService.register_unlisted_asset(
            db_session, inventario=inv, asset_id=asset_fora.id,
            found_location_id=loc.id, observation="bem não previsto",
            username="coletor",
        )
        assert created is True
        assert item.nao_previsto is True

    def test_service_rejeita_unlisted_de_asset_inexistente(self, db_session):
        loc = _make_location(db_session)
        inv = InventarioService.create_inventario(db_session, name="404", location_id=loc.id)
        with pytest.raises(ValueError):
            InventarioService.register_unlisted_asset(
                db_session, inventario=inv, asset_id=999999, username="coletor",
            )


# ============================================================================
# US3 — Sincronização (T027): idempotência, conflitos, revalidação, auditoria
# ============================================================================

class TestUS3Sincronizacao:
    def _prep(self, db_session, client, n=2):
        loc = _make_location(db_session)
        loc2 = _make_location(db_session, name="Local Alternativo", department="RH")
        for i in range(n):
            _make_asset(db_session, f"SYN-TST-{i:04d}", location=loc)
        inv = InventarioService.create_inventario(db_session, name="Sync", location_id=loc.id)
        pkg = client.post(API.format(inv_id=inv.id) + "/package").json()
        return inv, pkg, loc, loc2

    def test_sync_estruturado_e_grava_via_record_check(self, client, db_session):
        inv, pkg, loc, loc2 = self._prep(db_session, client)
        item = inv.itens[0]
        resp = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-sync-0001", item.id, item.asset_id, result="ENCONTRADO"),
        ])
        assert resp.status_code == 200
        body = resp.json()
        assert body["accepted"][0]["client_operation_id"] == "op-sync-0001"
        assert body["accepted"][0]["item_status"] == "ENCONTRADO"
        assert body["duplicated"] == [] and body["conflicts"] == [] and body["rejected"] == []
        db_session.refresh(item)
        assert item.status == InventarioItemStatus.FOUND  # via record_check (FR-026)

    def test_idempotencia_reenvio_e_resultado_igual_duplicated(self, client, db_session):
        """SC-004/C-5: reenvio e resultado igual → duplicated, sem segunda gravação."""
        inv, pkg, loc, loc2 = self._prep(db_session, client)
        item = inv.itens[0]
        op = _op_check("op-dupl-0001", item.id, item.asset_id)
        r1 = _sync(client, inv.id, pkg["snapshot_version"], [op])
        assert len(r1.json()["accepted"]) == 1
        # reenvio do MESMO client_operation_id → duplicated (UNIQUE)
        r2 = _sync(client, inv.id, pkg["snapshot_version"], [op])
        assert len(r2.json()["duplicated"]) == 1
        # mesma coleta de OUTRO dispositivo, resultado IGUAL ao estado do item → duplicated
        op2 = _op_check("op-dupl-0002", item.id, item.asset_id)
        r3 = _sync(client, inv.id, pkg["snapshot_version"], [op2], device_id="device-2")
        assert len(r3.json()["duplicated"]) == 1
        assert db_session.query(InventarioOfflineColeta).filter(
            InventarioOfflineColeta.inventory_id == inv.id
        ).count() == 2  # apenas 2 linhas gravadas (sem duplicar o efeito no item)

    def test_resultado_diferente_conflito_preservado(self, client, db_session):
        """C-5/FR-027/SC-006: divergente → CONFLICT com payload íntegro; nunca sobrescreve."""
        inv, pkg, loc, loc2 = self._prep(db_session, client)
        item = inv.itens[0]
        # fluxo online conferiu ENCONTRADO
        InventarioService.record_check(db_session, item=item, result=InventarioItemStatus.FOUND, username="online")
        # coleta offline divergente (LOCAL_DIFERENTE para outro local)
        r = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-conf-0001", item.id, item.asset_id, result="LOCAL_DIFERENTE", loc_id=loc2.id),
        ])
        body = r.json()
        assert len(body["conflicts"]) == 1
        assert body["conflicts"][0]["reason"] == "result_diverges"
        coleta_id = body["conflicts"][0]["coleta_id"]
        row = db_session.get(InventarioOfflineColeta, coleta_id)
        assert row.status == InventarioOfflineColetaStatus.CONFLICT
        assert row.client_payload is not None  # preservado para reconciliação
        db_session.refresh(item)
        assert item.status == InventarioItemStatus.FOUND  # item NÃO sobrescrito

    def test_inventario_encerrado_rejeita_com_motivo(self, client, db_session):
        """C-2/FR-025: encerrado → todas as operações rejeitadas com motivo claro."""
        inv, pkg, loc, loc2 = self._prep(db_session, client)
        _close(db_session, inv)
        item = inv.itens[0]
        r = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-clos-0001", item.id, item.asset_id),
        ])
        body = r.json()
        assert len(body["rejected"]) == 1
        assert body["rejected"][0]["reason"] == "inventario_encerrado"

    def test_snapshot_mismatch_rejeitado(self, client, db_session):
        """FR-004/D9: coleta sobre base diferente → snapshot_mismatch."""
        inv, pkg, loc, loc2 = self._prep(db_session, client)
        item = inv.itens[0]
        r = _sync(client, inv.id, "0" * 64, [
            _op_check("op-snap-0001", item.id, item.asset_id),
        ])
        body = r.json()
        assert body["rejected"][0]["reason"] == "snapshot_mismatch"

    def test_asset_fora_do_snapshot_rejeitado(self, client, db_session):
        inv, pkg, loc, loc2 = self._prep(db_session, client)
        asset_fora = _make_asset(db_session, "SYN-TST-9000", location=loc)  # depois do pacote
        r = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-outs-0001", None, asset_fora.id, result="ENCONTRADO"),
        ])
        body = r.json()
        assert body["rejected"][0]["reason"] == "asset_fora_do_snapshot"

    def test_unlisted_aceito_e_local_inexistente_rejeitado(self, client, db_session):
        inv, pkg, loc, loc2 = self._prep(db_session, client)
        asset_fora = _make_asset(db_session, "SYN-TST-9001", location=loc)
        r1 = _sync(client, inv.id, pkg["snapshot_version"], [
            {"client_operation_id": "op-unl-0001", "operation": "UNLISTED",
             "asset_id": asset_fora.id, "found_location_id": loc.id,
             "observation": "não previsto", "collected_at": "2026-09-24T09:20:00-03:00"},
        ])
        assert len(r1.json()["accepted"]) == 1
        r2 = _sync(client, inv.id, pkg["snapshot_version"], [
            {"client_operation_id": "op-unl-0002", "operation": "UNLISTED",
             "asset_id": asset_fora.id, "found_location_id": 999999,
             "collected_at": "2026-09-24T09:21:00-03:00"},
        ])
        assert r2.json()["rejected"][0]["reason"] == "local_inexistente"

    def test_resultado_invalido_rejeitado(self, client, db_session):
        inv, pkg, loc, loc2 = self._prep(db_session, client)
        item = inv.itens[0]
        r = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-badr-0001", item.id, item.asset_id, result="STATUS_INVENTADO"),
        ])
        assert r.json()["rejected"][0]["reason"] == "resultado_invalido"

    def test_sync_parcial_por_operacao(self, client, db_session):
        """FR-022/SC-005: processamento por operação; aceitas permanecem em queda."""
        inv, pkg, loc, loc2 = self._prep(db_session, client, n=3)
        itens = inv.itens
        ops = [
            _op_check("op-par-0001", itens[0].id, itens[0].asset_id),
            _op_check("op-par-0002", itens[1].id, itens[1].asset_id),
            _op_check("op-par-0003", None, 999999),  # inválida: não aborta o lote
        ]
        r = _sync(client, inv.id, pkg["snapshot_version"], ops)
        body = r.json()
        assert len(body["accepted"]) == 2 and len(body["rejected"]) == 1

    def test_datas_collected_preservada_received_oficial(self, client, db_session):
        """FR-045: collected_at preservado; received_at é a referência oficial (UTC)."""
        from datetime import datetime, timezone
        inv, pkg, loc, loc2 = self._prep(db_session, client, n=1)
        item = inv.itens[0]
        r = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-date-0001", item.id, item.asset_id),
        ])
        row = db_session.query(InventarioOfflineColeta).filter(
            InventarioOfflineColeta.client_operation_id == "op-date-0001"
        ).first()
        assert row is not None
        assert row.collected_at is not None and row.received_at is not None
        # SQLite pode armazenar naive; o valor deve ser o UTC do servidor (agora)
        delta = abs((row.received_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds())
        assert delta < 60  # received_at = momento do recebimento (FR-045)

    def test_auditoria_sync_conflito_rejeitado_sem_credenciais(self, client, db_session):
        inv, pkg, loc, loc2 = self._prep(db_session, client)
        item = inv.itens[0]
        InventarioService.record_check(db_session, item=item, result=InventarioItemStatus.FOUND, username="online")
        _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-aud-0001", item.id, item.asset_id),
            _op_check("op-aud-0002", item.id, item.asset_id, result="LOCAL_DIFERENTE", loc_id=loc2.id),
            _op_check("op-aud-0003", None, 999999),
        ])
        actions = {a for (a,) in db_session.query(AuditLog.action).filter(
            AuditLog.action.in_([
                ACTION_INVENTARIO_OFFLINE_SYNC,
                ACTION_INVENTARIO_OFFLINE_CONFLITO,
                ACTION_INVENTARIO_OFFLINE_REJEITADO,
            ])
        ).all()}
        assert ACTION_INVENTARIO_OFFLINE_SYNC in actions
        assert ACTION_INVENTARIO_OFFLINE_CONFLITO in actions
        assert ACTION_INVENTARIO_OFFLINE_REJEITADO in actions
        for evt in db_session.query(AuditLog).filter(
            AuditLog.action.in_([ACTION_INVENTARIO_OFFLINE_SYNC, ACTION_INVENTARIO_OFFLINE_CONFLITO, ACTION_INVENTARIO_OFFLINE_REJEITADO])
        ).all():
            text = f"{evt.description or ''}{evt.new_data or ''}".lower()
            for forbidden in ("password", "senha", "token", "cookie"):
                assert forbidden not in text

    def test_card_conflitos_renderiza_na_tela_do_inventario(self, client, db_session):
        """Regressão: o card 'Conflitos offline' deve aparecer na tela do inventário.

        Bug: a rota comparava c['status'] == 'CONFLICT', mas o valor do enum é o
        rótulo ('OFFLINE_CONFLITO') — o card nunca renderizava com conflito real.
        """
        inv, pkg, loc, loc2 = self._prep(db_session, client)
        item = inv.itens[0]
        InventarioService.record_check(
            db_session, item=item, result=InventarioItemStatus.NOT_FOUND, username="online"
        )
        _sync(client, inv.id, pkg["snapshot_version"], [
            # offline diz ENCONTRADO para item NAO_ENCONTRADO → divergente → CONFLICT
            _op_check("op-card-0001", item.id, item.asset_id),
        ])

        page = client.get(f"/inventarios/{inv.id}")
        assert page.status_code == 200
        assert "Conflitos offline (1)" in page.text
        assert "Aplicar coleta" in page.text
        assert "Manter registrado" in page.text

    def test_sync_403_sem_permissao(self, client, db_session):
        loc = _make_location(db_session)
        inv = _make_inventario(db_session, loc)
        # prepara com usuário autorizado ANTES de trocar a sessão
        pkg = client.post(API.format(inv_id=inv.id) + "/package").json()
        _user_with_perm(db_session, "nosync", "inventario.visualizar")
        _login(client, "nosync")  # sem inventario.conferir
        r = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-perm-0001", inv.itens[0].id, inv.itens[0].asset_id),
        ])
        assert r.status_code == 403


# ============================================================================
# US4 — Múltiplos dispositivos (T035)
# ============================================================================

class TestUS4MultiDispositivo:
    def test_consolida_dois_dispositivos_com_rastreabilidade(self, client, db_session):
        loc = _make_location(db_session)
        for i in range(2):
            _make_asset(db_session, "MULT-TST-000" + str(i), location=loc)
        inv = InventarioService.create_inventario(db_session, name="Multi", location_id=loc.id)
        pkg = client.post(API.format(inv_id=inv.id) + "/package").json()
        i1, i2 = inv.itens[0], inv.itens[1]
        r1 = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-multi-0001", i1.id, i1.asset_id),
        ], device_id="tablet-01")
        r2 = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-multi-0002", i2.id, i2.asset_id),
        ], device_id="tablet-02")
        assert len(r1.json()["accepted"]) == 1 and len(r2.json()["accepted"]) == 1

        consulta = client.get(API.format(inv_id=inv.id) + "/coletas").json()
        assert consulta["total"] == 2
        devices = {c["device_id"] for c in consulta["coletas"]}
        assert devices == {"tablet-01", "tablet-02"}
        users = {c["username"] for c in consulta["coletas"]}
        assert users == {"testuser"}  # sessão de teste (rastreabilidade de origem)

    def test_conflito_entre_dispositivos(self, client, db_session):
        loc = _make_location(db_session)
        loc2 = _make_location(db_session, name="MultConf Local B", department="RH")
        _make_asset(db_session, "MULT-TST-0009", location=loc)
        inv = InventarioService.create_inventario(db_session, name="MultiConf", location_id=loc.id)
        pkg = client.post(API.format(inv_id=inv.id) + "/package").json()
        item = inv.itens[0]
        r1 = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-mc-0001", item.id, item.asset_id, result="ENCONTRADO"),
        ], device_id="tablet-01")
        r2 = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-mc-0002", item.id, item.asset_id, result="LOCAL_DIFERENTE", loc_id=loc2.id),
        ], device_id="tablet-02")
        assert len(r1.json()["accepted"]) == 1
        assert len(r2.json()["conflicts"]) == 1  # nunca sobrescreve silenciosamente (C-5)


# ============================================================================
# US5 — Ciclo de vida (T038): expiração por estado do inventário (P-2)
# ============================================================================

class TestUS5CicloDeVida:
    def test_encerramento_expira_pacote_bloqueia_coleta_e_sync(self, client, db_session):
        """C-2/P-2: encerrado → package 409 E sync rejeitado com motivo claro."""
        loc = _make_location(db_session)
        _make_asset(db_session, "VID-TST-0001", location=loc)
        inv = InventarioService.create_inventario(db_session, name="Vida", location_id=loc.id)
        pkg = client.post(API.format(inv_id=inv.id) + "/package").json()
        assert pkg["expires_when"] == "inventory_closed_or_reprepared"

        _close(db_session, inv)

        # nova preparação recusada (409)
        assert client.post(API.format(inv_id=inv.id) + "/package").status_code == 409
        # coletas tardias do pacote ainda ativo no dispositivo → rejeitadas
        item = inv.itens[0]
        body = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-vida-0001", item.id, item.asset_id),
        ]).json()
        assert body["rejected"][0]["reason"] == "inventario_encerrado"
        # ping indica não-preparável (client usa isso para bloquear a coleta — T039)
        ping = client.get(API.format(inv_id=inv.id) + "/ping").json()
        assert ping["preparable"] is False

    def test_reconciliacao_keep_e_apply(self, client, db_session):
        """D8/T032: KEEP mantém item; APPLY grava via record_check (inventário aberto)."""
        loc = _make_location(db_session)
        loc2 = _make_location(db_session, name="Local Reconcilia", department="RH")
        _make_asset(db_session, "REC-TST-0001", location=loc)
        _make_asset(db_session, "REC-TST-0002", location=loc)
        inv = InventarioService.create_inventario(db_session, name="Reconcilia", location_id=loc.id)
        pkg = client.post(API.format(inv_id=inv.id) + "/package").json()
        i1, i2 = inv.itens[0], inv.itens[1]
        # dois conflitos
        InventarioService.record_check(db_session, item=i1, result=InventarioItemStatus.FOUND, username="online")
        InventarioService.record_check(db_session, item=i2, result=InventarioItemStatus.FOUND, username="online")
        c1 = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-rec-0001", i1.id, i1.asset_id, result="LOCAL_DIFERENTE", loc_id=loc2.id),
        ]).json()["conflicts"][0]["coleta_id"]
        c2 = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-rec-0002", i2.id, i2.asset_id, result="LOCAL_DIFERENTE", loc_id=loc2.id),
        ]).json()["conflicts"][0]["coleta_id"]

        # KEEP: item mantém ENCONTRADO
        r_keep = client.post(API.format(inv_id=inv.id) + f"/coletas/{c1}/reconcile", json={"action": "KEEP"})
        assert r_keep.status_code == 200
        assert r_keep.json()["item_status"] == "ENCONTRADO"
        db_session.refresh(i1)
        assert i1.status == InventarioItemStatus.FOUND

        # APPLY: item passa para o resultado da coleta offline
        r_apply = client.post(API.format(inv_id=inv.id) + f"/coletas/{c2}/reconcile", json={"action": "APPLY"})
        assert r_apply.status_code == 200
        assert r_apply.json()["item_status"] == "LOCAL_DIFERENTE"
        db_session.refresh(i2)
        assert i2.status == InventarioItemStatus.FOUND_WRONG_LOCATION
        assert i2.found_location_id == loc2.id

        evt = db_session.query(AuditLog).filter(
            AuditLog.action == ACTION_INVENTARIO_OFFLINE_RECONCILED
        ).count()
        assert evt == 2

    def test_reconciliacao_409_coleta_nao_conflito(self, client, db_session):
        loc = _make_location(db_session)
        _make_asset(db_session, "REC-TST-0009", location=loc)
        inv = InventarioService.create_inventario(db_session, name="Rec409", location_id=loc.id)
        pkg = client.post(API.format(inv_id=inv.id) + "/package").json()
        item = inv.itens[0]
        _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-rec-0009", item.id, item.asset_id),
        ])
        coleta = db_session.query(InventarioOfflineColeta).filter(
            InventarioOfflineColeta.client_operation_id == "op-rec-0009"
        ).first()
        r = client.post(API.format(inv_id=inv.id) + f"/coletas/{coleta.id}/reconcile", json={"action": "KEEP"})
        assert r.status_code == 409  # só CONFLICT é reconciliável

    def test_reconciliacao_apply_inventario_encerrado_409(self, client, db_session):
        loc = _make_location(db_session)
        loc2 = _make_location(db_session, name="Local RecClosed", department="RH")
        _make_asset(db_session, "REC-TST-0010", location=loc)
        inv = InventarioService.create_inventario(db_session, name="RecClosed", location_id=loc.id)
        pkg = client.post(API.format(inv_id=inv.id) + "/package").json()
        item = inv.itens[0]
        InventarioService.record_check(db_session, item=item, result=InventarioItemStatus.FOUND, username="online")
        c = _sync(client, inv.id, pkg["snapshot_version"], [
            _op_check("op-rec-0010", item.id, item.asset_id, result="LOCAL_DIFERENTE", loc_id=loc2.id),
        ]).json()["conflicts"][0]["coleta_id"]
        _close(db_session, inv)
        r = client.post(API.format(inv_id=inv.id) + f"/coletas/{c}/reconcile", json={"action": "APPLY"})
        assert r.status_code == 409
