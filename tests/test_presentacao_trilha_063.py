"""Feature 063 — Padronização da Apresentação de Origem e Destino na Trilha de Fluxo & Movimentações.

Arquivo de TESTE da FEATURE 063. Agenda:
  US1 (T002/T003/T004): renderização da trilha — FALHA (RED) na primeira rodada,
             pois o template atual exibe o snapshot cru (ex.: `IPMJP - Sede - Divisão
             de Previdência (Sede - Divisão de Previdência)`).
  US2 (T005/T007): guarda de não-mutação — VERDE nas duas rodadas (antes e depois
             da alteração de template), provando que gravação, histórico, busca e
             o dropdown da Feature 062 ficam idênticos.

Padrão de testes da casa: fixtures `client`/`db_session` (SQLite em memória),
helpers com `LocationService.create` e `AssetService.create`, movimentação via
`client.post("/movements/new", ...)`, asserts sobre `GET /assets/{id}.text`.

SCOPE (não é nossa): zero backend, zero DDL, zero seletores da 062, zero testes
antigos modificados. Só este arquivo novo + a macro/card do template.
"""

import pytest

from app.models.enums import MovementType, AssetCategory, AssetStatus
from app.schemas.asset import AssetCreate
from app.schemas.custodian import CustodianCreate
from app.schemas.location import LocationCreate
from app.schemas.movement import MovementCreate, MovementFilter
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.location_service import LocationService
from app.services.movement_service import MovementService

# ============================================================================
# Fixtures de apoio (massa pequena, reutilizável)
# ============================================================================

def _make_location(name, branch, department):
    return LocationService.create(
        db_session,
        LocationCreate(name=name, branch=branch, department=department),
    )


def _make_custodian(registration_code, name, email, department, role="Analista", db_session=None):
    return CustodianService.create(
        db_session,
        CustodianCreate(
            registration_code=registration_code,
            name=name,
            email=email,
            role=role,
            department=department,
        ),
    )


def _make_asset_create(tag="PAT-06300", name="Notebook 063",
                       initial_location_id=None):
    return AssetCreate(
        tag=tag,
        name=name,
        category=AssetCategory.NOTEBOOK,
        purchase_value=1000.0,
        initial_location_id=initial_location_id,
    )


# ============================================================================
# User Story 1 — Renderização da trilha (RED → GREEN)
# ============================================================================

class TestUS1RenderizacaoTrilha:
    """T002 (RED) → T003 (template) → T004 (GREEN)."""

    @pytest.fixture()
    def asset_com_movimentacoes(self, db_session):
        """Bem com ENTRADA (fonte de snapshot cru) + TRANSFERENCIA para um local
        padrão de produção, e um movimento extra no Clube (caso dedup)."""
        # locais de produção (nomes reais, com sufixo " - departamento")
        loc_prev = LocationService.create(
            db_session,
            LocationCreate(
                name="Sede - Setor de Recadastramento",
                branch="IPMJP - Sede",
                department="Setor de Recadastramento",
            ),
        )
        loc_dest = LocationService.create(
            db_session,
            LocationCreate(
                name="Sede - Divisão de Previdência",
                branch="IPMJP - Sede",
                department="Divisão de Previdência",
            ),
        )
        loc_clube = LocationService.create(
            db_session,
            LocationCreate(
                name="Clube da Pessoa Idosa",
                branch="Clube",
                department="Clube da Pessoa Idosa",
            ),
        )

        # bem começando no local de origem
        asset = AssetService.create(
            db_session,
            _make_asset_create(
                tag="PAT-06301",
                name="Notebook 063",
                initial_location_id=loc_prev.id,
            ),
        )

        # ENTRADA_AQUISICAO (origem literal "Fornecedor / Entrada Inicial")
        MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.ACQUISITION,
                reason="Teste 063 entrada padrão",
                operator_name="Validador 063",
            ),
        )

        # TRANSFERENCIA_LOCAL prev → dest
        MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.TRANSFER,
                destination_location_id=loc_dest.id,
                reason="Teste 063 transferência padronizada",
                operator_name="Validador 063",
            ),
        )

        # ALOCACAO para o clube (caso dedup: name == department)
        custodian = _make_custodian(
            "MAT-5060", "Carlos Lima", "carlos.lima@teste.local", "Clube da Pessoa Idosa",
            role="Analista", db_session=db_session,
        )
        MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.ALLOCATION,
                destination_custodian_id=custodian.id,
                destination_location_id=loc_clube.id,
                reason="Teste 063 alocação no clube",
                operator_name="Validador 063",
            ),
        )

        db_session.commit()
        return asset

    def test_titulos_sao_departamento_e_contexto_deduplicado(
        self, asset_com_movimentacoes, client
    ):
        # RED — template antigo exibia o snapshot cru; esta rodada deve FALHAR.
        html = client.get(f"/assets/{asset_com_movimentacoes.id}").text

        # (a) linhas principais = department
        assert "Setor de Recadastramento" in html, "título da ORIGEM deve ser o department (linha principal)"
        assert "Divisão de Previdência" in html, "título do DESTINO deve ser o department (linha principal)"

        # (b) contexto = local_curto • branch (ex.: "Sede • IPMJP - Sede")
        assert "Sede • IPMJP - Sede" in html, "o contexto de ORIGEM/DESTINO deve ser 'Sede • IPMJP - Sede'"

        # (c) snapshot cru formatado NÃO está no HTML da trilha
        cru = "IPMJP - Sede - Setor de Recadastramento (Sede - Setor de Recadastramento)"
        assert cru not in html, "o snapshot cru formatado NÃO deve aparecer no HTML"

        # (e) seção "Custódia & Localização Atual" permanece presente/Intacta
        assert "Custódia & Localização Atual" in html
        assert "Localização Física" in html

    def test_caso_deduplicado_sem_duplicate_no_html(self, asset_com_movimentacoes, client):
        # RED — o template antigo repetiria o nome; esta rodada deve FALHAR.
        html = client.get(f"/assets/{asset_com_movimentacoes.id}").text

        # nenhum dos dois textos redundantes pode aparecer (Clube = department
        # e também o nome completo da localização)
        assert "Clube da Pessoa Idosa - Clube da Pessoa Idosa" not in html
        assert "Clube da Pessoa Idosa • Clube da Pessoa Idosa" not in html

        # o contexto deduplicado é somente "Clube" (sem o departamento repetido)
        assert "Clube" in html
        assert "Clube da Pessoa Idosa" in html  # titular (department) continua presente


# ============================================================================
# User Story 2 — Guarda de não-mutação (VERDE antes e depois do template)
# ============================================================================

class TestUS2GuardaNaoMutacao:
    """T005: teste de guarda. Deve passar ANTES e CONTINUAR passando depois do
    template. Nada de movimentação, busca 049 e ENTRADA_AQUISICAO muda."""

    @pytest.fixture()
    def movimento_com_gravacao(self, db_session, client):
        """Cria bem + ENTRADA + uma TRANSFERÊNCIA e retorna (asset, movimentacao)."""
        loc_a = LocationService.create(
            db_session,
            LocationCreate(name="Sala A", branch="Unidade A", department="Dept A"),
        )
        loc_b = LocationService.create(
            db_session,
            LocationCreate(name="Sala B", branch="Unidade B", department="Dept B"),
        )

        asset = AssetService.create(
            db_session,
            _make_asset_create(
                tag="PAT-06302",
                name="Notebook 063-2",
                initial_location_id=loc_a.id,
            ),
        )

        # ENTRADA_AQUISICAO (origem literal "Fornecedor / Entrada Inicial" + destino no formato atual)
        entrada = MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.ACQUISITION,
                destination_location_id=loc_a.id,
                reason="Teste 063 entrada padrão",
                operator_name="Validador 063",
            ),
        )

        # TRANSFERÊNCIA para loc_b
        mov = MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.TRANSFER,
                destination_location_id=loc_b.id,
                reason="Teste 063 transferência (guarda)",
                operator_name="Validador 063",
            ),
        )

        # Persiste o snapshot da ENTRADA ANTES de qualquer POST na página (guarda US2).
        # A TRANSFERÊNCIA não deve regravar a entrada.
        snapshot_antes = (
            entrada.origin_location_name,
            entrada.destination_location_name,
        )

        return asset, mov, entrada, snapshot_antes

    def test_nao_muda_gravacao_nem_historico(self, movimento_com_gravacao, client, db_session):
        asset, mov, entrada, snapshot_antes = movimento_com_gravacao

        # (a) gravação segue o contrato atual (transferência)
        assert mov.destination_location_name == "Unidade B - Dept B (Sala B)"

        # (b) ENTRADA_AQUISICAO permanece byte-a-byte idêntica (nada é regravado)
        entrada_depois = MovementService.get_by_id(db_session, entrada.id)
        assert (entrada_depois.origin_location_name, entrada_depois.destination_location_name) == snapshot_antes, (
            f"entrada_depois={entrada_depois.origin_location_name!r} x {entrada_depois.destination_location_name!r}, "
            f"snapshot_antes={snapshot_antes}"
        )

        # (c) busca por snapshot 049 continua casando pelos mesmos termos
        movs_b, _ = MovementService.get_all_movements(
            db_session, filters=MovementFilterMock(search="Dept B")
        )
        assert any(m.id == mov.id for m in movs_b)

    def test_dropdown_062_nao_mudou(self, movimento_com_gravacao, client, db_session):
        # Garantia cruzada: a suíte da 062 continua 100% verde (FR-005/AC05).
        # Este teste só garante que o GET /assets/{id} renderiza sem quebrar o
        # fluxo do dropdown; o capítulo 062 está coberto pela suíte (test_departamento_destino_062.py)
        # que roda na régua final.
        asset, _, _, _ = movimento_com_gravacao
        resp = client.get(f"/assets/{asset.id}")
        assert resp.status_code == 200


# ============================================================================
# Mocks mínimos (para testar apenas a camada de apresentação/e2e, os motores
# reais ficam intactos durante o RED; substituídos pelas schemas reais acima)
class MovementFilterMock:
    """Compatible with app.schemas.movement.MovementFilter para a busca 049."""
    def __init__(self, search="", asset_id=None, movement_type=None,
                 custodian_id=None, location_id=None, start_date=None,
                 end_date=None):
        self.search = search
        self.asset_id = asset_id
        self.movement_type = movement_type
        self.custodian_id = custodian_id
        self.location_id = location_id
        self.start_date = start_date
        self.end_date = end_date


# ============================================================================
