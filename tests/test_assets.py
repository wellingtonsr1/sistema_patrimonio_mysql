import pytest
from datetime import datetime, timedelta
from app.models.enums import AssetStatus, AssetCondition, AssetCategory
from app.schemas.asset import AssetCreate, AssetUpdate
from app.services.asset_service import AssetService


def test_asset_crud_and_depreciation(db_session):
    """Testa cadastro, atualização e cálculo contábil de depreciação"""
    purchase_dt = datetime.utcnow() - timedelta(days=365)  # 1 ano atrás
    
    asset = AssetService.create(db_session, AssetCreate(
        tag="PAT-88001",
        name="Servidor Web NGINX",
        category=AssetCategory.SERVER,
        brand="Dell",
        model="PowerEdge",
        serial_number="SV-88001",
        purchase_date=purchase_dt,
        purchase_value=10000.00,
        condition=AssetCondition.NEW
    ))

    assert asset.id is not None
    assert asset.tag == "PAT-88001"
    assert asset.purchase_value == 10000.00

    # Testa cálculo de depreciação linear (20% ao ano = 20% em 1 ano)
    deprec = AssetService.calculate_depreciation(asset, annual_rate=0.20)
    assert deprec["initial_value"] == 10000.00
    assert 1800.0 <= deprec["depreciated_amount"] <= 2200.0  # Aproximadamente 20%
    assert 7800.0 <= deprec["current_value"] <= 8200.0

    # Atualização de cadastro
    updated = AssetService.update(db_session, asset.id, AssetUpdate(
        notes="Atualizado com 64GB de memória adicional",
        condition=AssetCondition.GOOD
    ))

    assert updated.notes == "Atualizado com 64GB de memória adicional"
    assert updated.condition == AssetCondition.GOOD


# ============================================================================
# Feature 067 — régua de serviço da edição cadastral (T014)
#
# Cobertura NOVA, sem alterar nenhum teste existente: operador autenticado e
# motivo na movimentação de condição, validações V1–V3 do serviço e o
# `commit=False` que permite ao chamador fechar cadastro + trilha numa única
# transação (Constitution VIII).
# ============================================================================

def _asset_067(db_session, tag="PAT-06730", **overrides):
    payload = {
        "tag": tag,
        "name": "Notebook 067 (serviço)",
        "category": AssetCategory.NOTEBOOK,
        "purchase_value": 0.0,
    }
    payload.update(overrides)
    return AssetService.create(db_session, AssetCreate(**payload))


def test_067_update_registra_operador_e_motivo_na_movimentacao_de_condicao(db_session):
    """V8/FR-012 — quem mudou a condição vai para a movimentação (não 'Sistema')."""
    from app.models.enums import MovementType
    from app.models.movement import Movement

    asset = _asset_067(db_session, tag="PAT-06731")

    AssetService.update(
        db_session,
        asset.id,
        AssetUpdate(condition=AssetCondition.GOOD),
        operator_name="maria.silva",
        change_reason="Vistoria anual 2026",
    )

    movimento = (
        db_session.query(Movement)
        .filter(
            Movement.asset_id == asset.id,
            Movement.movement_type == MovementType.STATUS_UPDATE,
        )
        .one()
    )
    assert movimento.operator_name == "maria.silva"
    assert movimento.reason == "Vistoria anual 2026"
    assert movimento.previous_condition == AssetCondition.NEW
    assert movimento.new_condition == AssetCondition.GOOD


def test_067_update_sem_operador_preserva_fallback_do_sistema(db_session):
    """Compatibilidade — sem os novos parâmetros o comportamento anterior é mantido."""
    from app.models.enums import MovementType
    from app.models.movement import Movement

    asset = _asset_067(db_session, tag="PAT-06732")

    AssetService.update(db_session, asset.id, AssetUpdate(condition=AssetCondition.FAIR))

    movimento = (
        db_session.query(Movement)
        .filter(
            Movement.asset_id == asset.id,
            Movement.movement_type == MovementType.STATUS_UPDATE,
        )
        .one()
    )
    assert movimento.operator_name == "Sistema"
    assert movimento.reason == "Vistoria técnica / Atualização de estado de conservação"


def test_067_update_valida_nome_limites_e_valor_negativo(db_session):
    """V1–V3 — a regra vive no serviço (fonte única para web e API)."""
    asset = _asset_067(db_session, tag="PAT-06733")

    for invalido in (
        AssetUpdate(name="   "),
        AssetUpdate(name="x" * 151),
        AssetUpdate(brand="b" * 101),
        AssetUpdate(invoice_number="n" * 101),
        AssetUpdate(supplier="s" * 151),
        AssetUpdate(purchase_value=-0.01),
    ):
        with pytest.raises(ValueError):
            AssetService.update(db_session, asset.id, invalido)
        db_session.rollback()

    # Limites exatos continuam aceitos (nada de truncamento silencioso)
    atualizado = AssetService.update(
        db_session, asset.id, AssetUpdate(brand="b" * 100, name="n" * 150)
    )
    assert atualizado.brand == "b" * 100
    assert atualizado.name == "n" * 150


def test_067_update_commit_false_nao_persiste_antes_do_commit_do_chamador(db_session):
    """FR-015 — `commit=False` deixa o commit para o chamador (rollback desfaz)."""
    from app.models.asset import Asset

    asset = _asset_067(db_session, tag="PAT-06734")

    AssetService.update(db_session, asset.id, AssetUpdate(notes="rascunho"), commit=False)
    assert db_session.query(Asset).filter_by(id=asset.id).one().notes == "rascunho"

    db_session.rollback()
    db_session.expire_all()
    assert db_session.query(Asset).filter_by(id=asset.id).one().notes is None


def test_067_write_change_audit_commit_false_fica_na_transacao(db_session):
    """FR-015 — a trilha acompanha a mesma transação quando `commit=False`."""
    from app.models.audit_log import AuditLog
    from app.services import audit_service

    audit_service.write_change_audit(
        db_session,
        user=None,
        action="ALTERACAO",
        module="Patrimônio",
        resource="Asset",
        resource_id=1,
        before={"brand": "A"},
        after={"brand": "B"},
        commit=False,
    )
    assert db_session.query(AuditLog).count() == 1

    db_session.rollback()
    db_session.expire_all()
    assert db_session.query(AuditLog).count() == 0
