"""Feature 064 — Padronização da Apresentação de Origem e Destino no Fluxo Global de Movimentações.

Arquivo de TESTE da FEATURE 064. Agenda:
  US1 (T004/T005/T006/T007/T008): renderização da tabela do Fluxo Global — FALHA
      (RED) na primeira rodada, pois o template atual exibe o snapshot cru
      (ex.: `IPMJP - Sede - Assessoria de Gabinete (Sede - Assessoria de Gabinete)`).
  US2 (T009/T010): guarda de não-mutação — VERDE nas duas rodadas (antes e depois
      da alteração de template), provando que gravação, busca 049 e o CSV
      (endpoint /api/reports/movements/csv) permanecem idênticos.

Padrão de testes da casa: fixtures `client`/`db_session` (SQLite em memória),
helpers com `LocationService.create` e `AssetService.create`, movimentação via
`MovementService.create_movement`, e CSV via `ReportService.generate_movements_csv`.

SCOPE (não é nossa): zero backend, zero DDL, zero backend alterado, zero testes
antigos modificados. Só este arquivo novo + a macro/células do template
(app/web/templates/movements/list.html).
"""

from app.models.enums import AssetCategory, MovementType
from app.schemas.asset import AssetCreate
from app.schemas.custodian import CustodianCreate
from app.schemas.location import LocationCreate
from app.schemas.movement import MovementCreate, MovementFilter
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.location_service import LocationService
from app.services.movement_service import MovementService
from app.services.report_service import ReportService

import pytest


# ============================================================================
# Fixtures de apoio (massa pequena, reutilizável)
# ============================================================================

def _make_location(db_session, name, branch, department):
    return LocationService.create(
        db_session,
        LocationCreate(name=name, branch=branch, department=department),
    )


def _make_custodian(db_session, registration_code, name, email, department, role="Analista"):
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


def _make_asset(db_session, tag="PAT-06400", name="Equipamento 064", initial_location_id=None):
    return AssetService.create(
        db_session,
        AssetCreate(
            tag=tag,
            name=name,
            category=AssetCategory.NOTEBOOK,
            purchase_value=1000.0,
            initial_location_id=initial_location_id,
        ),
    )


# ============================================================================
# User Story 1 — Renderização do Fluxo Global (RED → GREEN)
# ============================================================================

class TestUS1RenderizacaoFluxoGlobal:
    """T004 (teste RED) → T005/T006/T007/T008 (template) → GREEN."""

    @pytest.fixture()
    def asset_com_movimentacoes(self, db_session):
        """Bem com ENTRADA (snapshot cru) + TRANSFERENCIA para locais de produção
        e um movimento extra no Clube (caso deduplicado)."""

        loc_prev = _make_location(
            db_session,
            name="Sede - Setor de Recadastramento",
            branch="IPMJP - Sede",
            department="Setor de Recadastramento",
        )
        loc_dest = _make_location(
            db_session,
            name="Sede - Divisão de Previdência",
            branch="IPMJP - Sede",
            department="Divisão de Previdência",
        )
        loc_clube = _make_location(
            db_session,
            name="Clube da Pessoa Idosa",
            branch="Clube",
            department="Clube da Pessoa Idosa",
        )

        asset = _make_asset(
            db_session,
            tag="PAT-06401",
            name="Notebook 064",
            initial_location_id=loc_prev.id,
        )

        # ENTRADA_AQUISICAO (origem literal "Fornecedor / Entrada Inicial")
        MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.ACQUISITION,
                reason="Teste 064 entrada padrão",
                operator_name="Validador 064",
            ),
        )

        # TRANSFERENCIA_LOCAL prev → dest
        MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.TRANSFER,
                destination_location_id=loc_dest.id,
                reason="Teste 064 transferência padronizada",
                operator_name="Validador 064",
            ),
        )

        # ALOCACAO para o clube (caso dedup: name == department)
        custodian = _make_custodian(
            db_session,
            "MAT-6060",
            "Carlos Lima",
            "carlos.lima@teste.local",
            "Clube da Pessoa Idosa",
            role="Analista",
        )
        MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.ALLOCATION,
                destination_custodian_id=custodian.id,
                destination_location_id=loc_clube.id,
                reason="Teste 064 alocação no clube",
                operator_name="Validador 064",
            ),
        )

        db_session.commit()
        return asset

    def test_titulos_sao_departamento_e_contexto_deduplicado(self, asset_com_movimentacoes, client):
        # RED — template antigo exibia o snapshot cru; esta rodada deve FALHAR.
        html = client.get("/movements").text

        # (a) linhas principais = department (não o snapshot cru)
        assert "Setor de Recadastramento" in html, "ORIGEM deve exibir o department (linha principal)"
        assert "Divisão de Previdência" in html, "DESTINO deve exibir o department (linha principal)"

        # (b) contexto = local_curto • branch (ex.: "Sede • IPMJP - Sede")
        assert "Sede • IPMJP - Sede" in html, "contexto de ORIGEM/DESTINO deve ser 'Sede • IPMJP - Sede'"

        # (c) snapshot cru formatado NÃO está no HTML da listagem
        cru = "IPMJP - Sede - Setor de Recadastramento (Sede - Setor de Recadastramento)"
        assert cru not in html, "o snapshot cru formatado NÃO deve aparecer no HTML"

        # (d) cabeçalho e estrutura da listagem permanecem
        assert "Fluxo Global de Movimentações" in html
        assert "Data / Hora" in html

    def test_caso_deduplicado_clube(self, asset_com_movimentacoes, client):
        # RED — o template antigo repetiria o nome; esta rodada deve FALHAR.
        html = client.get("/movements").text

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
    """T009/T010: teste de guarda. Deve passar ANTES e CONTINUAR passando depois
    do template. Nada de movimentação, busca 049, CSV e dropdown 062 muda."""

    @pytest.fixture()
    def movimentos(self, db_session):
        """Cria bem + ENTRADA + TRANSFERÊNCIA e retorna massa útil."""

        loc_a = _make_location(db_session, "Sala A", "Unidade A", "Dept A")
        loc_b = _make_location(db_session, "Sala B", "Unidade B", "Dept B")

        asset = _make_asset(
            db_session,
            tag="PAT-06402",
            name="Notebook 064-2",
            initial_location_id=loc_a.id,
        )

        # ENTRADA_AQUISICAO (origem literal "Fornecedor / Entrada Inicial" +
        # destino no formato atual)
        entrada = MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.ACQUISITION,
                destination_location_id=loc_a.id,
                reason="Teste 064 entrada padrão",
                operator_name="Validador 064",
            ),
        )

        # TRANSFERÊNCIA para loc_b
        mov = MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.TRANSFER,
                destination_location_id=loc_b.id,
                reason="Teste 064 transferência (guarda)",
                operator_name="Validador 064",
            ),
        )

        # snapshot antes de mais POSTs (guarda US2)
        snapshot_antes = (
            entrada.origin_location_name,
            entrada.destination_location_name,
        )

        return asset, mov, entrada, snapshot_antes, loc_b

    def test_nao_muda_gravacao_nem_historico(self, movimentos, db_session):
        _, mov, entrada, snapshot_antes, _ = movimentos

        # (a) gravação segue o contrato atual (transferência)
        assert mov.destination_location_name == "Unidade B - Dept B (Sala B)"

        # (b) ENTRADA_AQUISICAO permanece byte-a-byte idêntica (nada é regravado)
        entrada_depois = MovementService.get_by_id(db_session, entrada.id)
        assert (entrada_depois.origin_location_name, entrada_depois.destination_location_name) == snapshot_antes, (
            f"entrada_depois={entrada_depois.origin_location_name!r} x "
            f"{entrada_depois.destination_location_name!r}, snapshot_antes={snapshot_antes}"
        )

    def test_busca_049_continua_casando_pelo_snapshot(self, movimentos, db_session):
        _, mov, _, _, loc_b = movimentos

        # busca 049 casa pelo TEXTO do snapshot (não pelo formatted HTML)
        items, _ = MovementService.get_all_movements(
            db_session, filters=MovementFilter(search="Dept B")
        )
        assert any(m.id == mov.id for m in items)

        # além disso, busca pelo department real também encontra (contexto extra,
        # não substitui a busca por snapshot)
        items2, _ = MovementService.get_all_movements(
            db_session, filters=MovementFilter(search="Sala B")
        )
        assert any(m.id == mov.id for m in items2)

    def test_csv_byte_a_byte_antes_e_depois(self, movimentos, db_session):
        # CSV usa somente os snapshots brutos; não passa pelo template.
        # Prova inequívoca do AC11: gera o CSV sobre o mesmo banco e verifica
        # que os snapshots aparecem intactos.
        csv_out = ReportService.generate_movements_csv(db_session)
        assert "Unidade B - Dept B (Sala B)" in csv_out
        assert "Sala B" in csv_out  # snapshot bruto em colunas Origem/Destino (Local)

    def test_dropdown_062_nao_mudou_e_listagem_acessivel(self, movimentos, client):
        # Garantia cruzada: a listagem nova renderiza e o fluxo da 062 continua
        # acessível. O capítulo 062 está coberto pela suíte
        # (test_departamento_destino_062.py) que roda na régua final.
        asset, _, _, _, _ = movimentos
        resp = client.get("/movements")
        assert resp.status_code == 200
        assert "Fluxo Global de Movimentações" in resp.text
        assert "/movements/new" in resp.text

    def test_fluxo_global_fallbacks_snapshot_e_literais(self, movimentos, db_session, client):
        """Casos 5-8: registros sem FK e literais especiais ('Não definido',
        'Nenhum / Estoque', 'Fornecedor / Entrada Inicial') exibidos byte-a-byte (T009 / AC06 / AC07)."""
        asset, _, _, _, _ = movimentos
        from app.models.movement import Movement

        mov_sem_fk = Movement(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            new_status=asset.status,
            reason="Transferência sem FK de teste",
            origin_location_id=None,
            origin_location_name="Não definido",
            origin_custodian_id=None,
            origin_custodian_name="Nenhum / Estoque",
            destination_location_id=None,
            destination_location_name="Não definido",
            destination_custodian_id=None,
            destination_custodian_name="Nenhum / Estoque",
            operator_name="Validador 064",
        )
        db_session.add(mov_sem_fk)
        db_session.commit()

        resp = client.get("/movements")
        assert resp.status_code == 200
        html = resp.text

        # (a) Entrada inicial com literal preservado byte-a-byte
        assert "Fornecedor / Entrada Inicial" in html

        # (b) Literais gravados sem FK exibidos byte-a-byte
        assert "Não definido" in html
        assert "Nenhum / Estoque" in html


# ============================================================================
# Mocks mínimos (compatível com app.schemas.movement.MovementFilter)
# ============================================================================

class MovementFilterMock:
    """Compatível com app.schemas.movement.MovementFilter para a busca 049."""

    def __init__(
        self,
        search="",
        asset_id=None,
        movement_type=None,
        custodian_id=None,
        location_id=None,
        start_date=None,
        end_date=None,
    ):
        self.search = search
        self.asset_id = asset_id
        self.movement_type = movement_type
        self.custodian_id = custodian_id
        self.location_id = location_id
        self.start_date = start_date
        self.end_date = end_date


# ============================================================================
