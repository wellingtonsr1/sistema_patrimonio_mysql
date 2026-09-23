"""
Testes da feature 029 — integração entre a importação CSV de equipamentos e o
histórico de Fluxo/Movimentações patrimoniais.

Cenários cobertos (spec 029-importacao-csv-fluxo, seção "Estratégia de Testes"):
A (novo bem com colaborador+local), B (sem colaborador), C (sem localização),
D (sem ambos), E (reimportação idêntica), F (mudança de colaborador),
G (mudança de localização), H (colaborador+local simultâneos),
I (estoque), J (usuário autenticado), K (falha transacional), L (Fluxo).
"""

import pytest

from app.models.asset import Asset
from app.models.custodian import Custodian
from app.models.location import Location
from app.models.movement import Movement
from app.models.enums import AssetStatus, MovementType
from app.services.import_service import parse_csv, execute_import
from app.services.movement_service import MovementService
from app.services.location_service import LocationService


# ---------------------------------------------------------------------------
# Helpers de apoio (padrão de tests/test_import_asset_location.py)
# ---------------------------------------------------------------------------

LOCAIS_BASE = [
    ("Sala de TI", "Matriz", "TI"),
    ("Divisão de Previdência", "Matriz", "Previdência"),
    ("Laboratório", "Matriz", "TI"),
]


def _criar_locais_base(db):
    """Garante as localizações usadas nos testes."""
    ids = {}
    for nome, branch, dept in LOCAIS_BASE:
        existing = LocationService.get_by_name(db, nome)
        if not existing:
            loc = Location(name=nome, branch=branch, department=dept)
            db.add(loc)
            db.flush()
            ids[nome] = loc.id
        else:
            ids[nome] = existing.id
    db.commit()
    return ids


def _criar_colaboradores_base(db):
    """Garante os colaboradores usados nos testes. Retorna dict nome → id."""
    nomes = ["Mariana Souto Soares", "Micael de Araújo Silva"]
    ids = {}
    for i, nome in enumerate(nomes):
        existing = db.query(Custodian).filter(Custodian.name == nome).first()
        if not existing:
            cust = Custodian(
                name=nome,
                registration_code=f"TEST-{i:05d}",
                email=f"{nome.split()[0].lower()}{i}@teste.local",
                role="Servidor",
                department="TI",
            )
            db.add(cust)
            db.flush()
            ids[nome] = cust.id
        else:
            ids[nome] = existing.id
    db.commit()
    return ids


def _csv(colaborador: str = "", localizacao: str = "", tombamento: str = "TEST029") -> str:
    """Monta um CSV de 1 linha com colunas reais de carga (custodiante + local)."""
    return (
        "tombamento;equipamento;categoria;Custodiante;localização\n"
        f"{tombamento};Computador;DESKTOP;{colaborador};{localizacao}\n"
    )


def _movements(db, asset_id):
    return (
        db.query(Movement)
        .filter(Movement.asset_id == asset_id)
        .order_by(Movement.id.asc())
        .all()
    )


def _asset(db, tag):
    return db.query(Asset).filter(Asset.tag == tag).first()


OPERADOR = "Wellington Teste"


# ---------------------------------------------------------------------------
# Cenário A + L — novo equipamento com colaborador + localização no Fluxo (US1)
# ---------------------------------------------------------------------------

class TestCenarioA_NovoComColaboradorELocalizacao:
    def test_a_importacao_cria_bem_e_movimentacoes_no_fluxo(self, db_session):
        locs = _criar_locais_base(db_session)
        custs = _criar_colaboradores_base(db_session)

        rows, errs = parse_csv(
            _csv(colaborador="Mariana Souto Soares", localizacao="Sala de TI")
        )
        assert errs == []

        result = execute_import(
            rows, db_session, skip_duplicates=False, operator_name=OPERADOR
        )
        assert result["imported"] == 1, result["errors"]
        assert result["errors"] == []

        asset = _asset(db_session, "TEST029")
        assert asset is not None
        # Estado atual: alocado ao colaborador e à localização do CSV
        assert asset.custodian_id == custs["Mariana Souto Soares"]
        assert asset.location_id == locs["Sala de TI"]
        assert asset.status == AssetStatus.IN_USE

        movs = _movements(db_session, asset.id)
        # (A) ENTRADA_AQUISICAO com snapshots reais + ALOCACAO_CAUTELA via motor
        assert len(movs) == 2
        entrada, alocacao = movs

        assert entrada.movement_type == MovementType.ACQUISITION
        assert entrada.origin_location_name == "Fornecedor / Entrada Inicial"
        assert entrada.origin_custodian_name == "Almoxarifado Geral"
        # Snapshot do destino no formato canônico do motor (filial - departamento (nome))
        assert entrada.destination_location_name == "Matriz - TI (Sala de TI)"
        assert entrada.operator_name == OPERADOR
        assert entrada.new_status == AssetStatus.AVAILABLE
        # Sem snapshots fabricados (D1): nada de "Importação CSV"/"Sistema" como origem
        assert entrada.origin_location_name != "Importação CSV"
        assert entrada.origin_custodian_name != "Sistema"
        # Termo da entrada segue o padrão do cadastro manual — nunca "TR-CSV-"
        assert entrada.term_code and entrada.term_code.startswith("TR-INIC-")
        assert not entrada.term_code.startswith("TR-CSV-")

        assert alocacao.movement_type == MovementType.ALLOCACAO if hasattr(
            MovementType, "ALLOCACAO"
        ) else alocacao.movement_type == MovementType.ALLOCATION
        assert alocacao.destination_custodian_id == custs["Mariana Souto Soares"]
        assert alocacao.destination_location_id == locs["Sala de TI"]
        assert alocacao.operator_name == OPERADOR
        assert alocacao.new_status == AssetStatus.IN_USE
        # Termo sequencial padrão do sistema (FR-007): TR-{ano}-{seq:05d}
        assert alocacao.term_code is not None
        assert alocacao.term_code.startswith(f"TR-{alocacao.timestamp.year}-")
        assert len(alocacao.term_code.split("-")[-1]) == 5
        assert not alocacao.term_code.startswith("TR-CSV-")

        # (L) O Fluxo recupera as movimentações pela consulta existente
        timeline = MovementService.get_timeline_for_asset(db_session, asset.id)
        movs_timeline = [item for item in timeline if item["type"] == "movement"]
        assert {m["data"].id for m in movs_timeline} == {entrada.id, alocacao.id}


# ---------------------------------------------------------------------------
# Cenários B, C, D, I — ausências combinadas não inventam dados (US2)
# ---------------------------------------------------------------------------

class TestCenarioBCDI_AusenciasNaoInventam:
    def test_b_com_local_sem_colaborador(self, db_session):
        locs = _criar_locais_base(db_session)
        rows, errs = parse_csv(_csv(localizacao="Sala de TI", tombamento="TEST029B"))
        assert errs == []
        result = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert result["errors"] == [], result["errors"]

        asset = _asset(db_session, "TEST029B")
        assert asset is not None
        assert asset.custodian_id is None
        assert asset.location_id == locs["Sala de TI"]
        assert asset.status == AssetStatus.AVAILABLE
        # Nenhuma movimentação de custódia (apenas a entrada)
        movs = _movements(db_session, asset.id)
        assert [m.movement_type for m in movs] == [MovementType.ACQUISITION]

    def test_c_com_colaborador_sem_local(self, db_session):
        custs = _criar_colaboradores_base(db_session)
        rows, errs = parse_csv(
            _csv(colaborador="Micael de Araújo Silva", tombamento="TEST029C")
        )
        assert errs == []
        result = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert result["errors"] == [], result["errors"]

        asset = _asset(db_session, "TEST029C")
        assert asset is not None
        assert asset.custodian_id == custs["Micael de Araújo Silva"]
        assert asset.status == AssetStatus.IN_USE
        movs = _movements(db_session, asset.id)
        tipos = [m.movement_type for m in movs]
        assert MovementType.ACQUISITION in tipos
        assert MovementType.ALLOCATION in tipos

    def test_d_sem_colaborador_sem_localizacao(self, db_session):
        rows, errs = parse_csv(_csv(tombamento="TEST029D"))
        assert errs == []
        result = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert result["errors"] == [], result["errors"]

        asset = _asset(db_session, "TEST029D")
        assert asset is not None
        assert asset.custodian_id is None
        assert asset.location_id is None
        assert asset.status == AssetStatus.AVAILABLE
        # (D) nenhuma movimentação artificial — apenas a entrada
        movs = _movements(db_session, asset.id)
        assert [m.movement_type for m in movs] == [MovementType.ACQUISITION]
        assert movs[0].destination_location_name == "Estoque Central"
        assert movs[0].destination_custodian_id is None

    def test_i_estoque_nao_recebe_colaborador(self, db_session):
        rows, errs = parse_csv(_csv(tombamento="TEST029I"))
        assert errs == []
        result = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert result["errors"] == [], result["errors"]
        asset = _asset(db_session, "TEST029I")
        assert asset.status == AssetStatus.AVAILABLE
        assert asset.custodian_id is None

    def test_celula_com_espacos_e_ausencia(self, db_session):
        # célula só com espaços = ausência (CSV real tem " ")
        rows, errs = parse_csv(_csv(colaborador="   ", localizacao="  ", tombamento="TEST029S"))
        assert errs == []
        result = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert result["errors"] == [], result["errors"]
        asset = _asset(db_session, "TEST029S")
        assert asset is not None
        assert asset.custodian_id is None
        assert asset.location_id is None


# ---------------------------------------------------------------------------
# Erros de linha — colaborador inexistente (FR-012) e regressão FR-013 (US2)
# ---------------------------------------------------------------------------

class TestErrosDeLinha:
    def test_colaborador_inexistente_erro_de_linha(self, db_session):
        _criar_locais_base(db_session)
        rows, errs = parse_csv(
            _csv(colaborador="Fulano Inexistente", localizacao="Sala de TI",
                 tombamento="TEST029ERR")
        )
        assert errs == []
        result = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        # (FR-012) erro na linha, bem não criado, sem movimentação
        assert result["imported"] == 0
        assert len(result["errors"]) == 1
        assert "Fulano Inexistente" in result["errors"][0]
        assert "colaborador" in result["errors"][0].lower()
        assert _asset(db_session, "TEST029ERR") is None

    def test_local_inexistente_erro_de_linha_regressao_fr013(self, db_session):
        """Regressão passiva da FR-013 (cobertura duplicada no arquivo novo por
        rastreabilidade; o teste original permanece em test_import_asset_location.py)."""
        _criar_locais_base(db_session)
        _criar_colaboradores_base(db_session)
        rows, errs = parse_csv(
            _csv(colaborador="Mariana Souto Soares", localizacao="Local_Fantasma",
                 tombamento="TEST029ERR2")
        )
        assert errs == []
        result = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert result["imported"] == 0
        assert len(result["errors"]) == 1
        assert "Local_Fantasma" in result["errors"][0]
        assert _asset(db_session, "TEST029ERR2") is None

    def test_nome_duplicado_resolucao_deterministica(self, db_session):
        """(Remediação C1) nomes duplicados no cadastro: primeira ocorrência
        determinística (menor id) quando não há matrícula no CSV."""
        locs = _criar_locais_base(db_session)
        ids = []
        for i in range(2):
            cust = Custodian(
                name="Nome Duplicado Teste",
                registration_code=f"DUP-{i:04d}",
                email=f"dup{i}@teste.local",
                role="Servidor",
                department="TI",
            )
            db_session.add(cust)
            db_session.flush()
            ids.append(cust.id)
        db_session.commit()

        rows, errs = parse_csv(
            _csv(colaborador="Nome Duplicado Teste", localizacao="Sala de TI",
                 tombamento="TEST029DUP")
        )
        assert errs == []
        result = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert result["errors"] == [], result["errors"]
        asset = _asset(db_session, "TEST029DUP")
        assert asset.custodian_id == min(ids)
        assert asset.location_id == locs["Sala de TI"]


# ---------------------------------------------------------------------------
# Cenário E — reimportação idêntica não duplica movimentações (US3)
# ---------------------------------------------------------------------------

class TestCenarioE_ReimportacaoIdentica:
    def test_e_reimportacao_identica_nao_duplica(self, db_session):
        locs = _criar_locais_base(db_session)
        custs = _criar_colaboradores_base(db_session)
        csv_texto = _csv(
            colaborador="Mariana Souto Soares", localizacao="Sala de TI",
            tombamento="TEST029E",
        )

        rows, errs = parse_csv(csv_texto)
        assert errs == []
        r1 = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert r1["imported"] == 1 and r1["errors"] == []

        asset = _asset(db_session, "TEST029E")
        movs_antes = _movements(db_session, asset.id)
        assert len(movs_antes) == 2

        # Reimportação idêntica (skip_duplicates=False = ramo de atualização)
        rows2, errs2 = parse_csv(csv_texto)
        assert errs2 == []
        r2 = execute_import(rows2, db_session, skip_duplicates=False, operator_name=OPERADOR)
        # Sem erro falso de VAL-002 ao operador (cenário E da spec)
        assert r2["errors"] == [], r2["errors"]

        movs_depois = _movements(db_session, asset.id)
        # (E) nenhuma movimentação nova; histórico anterior intacto
        assert len(movs_depois) == len(movs_antes)
        assert [m.id for m in movs_depois] == [m.id for m in movs_antes]
        assert asset.custodian_id == custs["Mariana Souto Soares"]
        assert asset.location_id == locs["Sala de TI"]

    def test_e_reimportacao_com_skip_duplicates_conta_skipped(self, db_session):
        locs = _criar_locais_base(db_session)
        custs = _criar_colaboradores_base(db_session)
        csv_texto = _csv(
            colaborador="Mariana Souto Soares", localizacao="Sala de TI",
            tombamento="TEST029E2",
        )
        rows, _ = parse_csv(csv_texto)
        execute_import(rows, db_session, skip_duplicates=True, operator_name=OPERADOR)
        rows2, _ = parse_csv(csv_texto)
        r2 = execute_import(rows2, db_session, skip_duplicates=True, operator_name=OPERADOR)
        assert r2["skipped"] == 1
        asset = _asset(db_session, "TEST029E2")
        assert asset.custodian_id == custs["Mariana Souto Soares"]
        assert asset.location_id == locs["Sala de TI"]
        assert len(_movements(db_session, asset.id)) == 2


# ---------------------------------------------------------------------------
# Cenários F, G, H — reimportação com mudança real usa a matriz (US4)
# ---------------------------------------------------------------------------

class TestCenarioFGH_ReimportacaoComMudanca:
    def _importar_inicial(self, db, tag, colaborador, local):
        _criar_locais_base(db)
        _criar_colaboradores_base(db)
        rows, errs = parse_csv(_csv(colaborador=colaborador, localizacao=local, tombamento=tag))
        assert errs == []
        r = execute_import(rows, db, skip_duplicates=False, operator_name=OPERADOR)
        assert r["errors"] == [], r["errors"]
        return _asset(db, tag)

    def test_f_mudanca_de_colaborador(self, db_session):
        locs = _criar_locais_base(db_session)
        custs = _criar_colaboradores_base(db_session)
        asset = self._importar_inicial(db_session, "TEST029F", "Mariana Souto Soares", "Sala de TI")
        movs_antes = _movements(db_session, asset.id)

        rows, _ = parse_csv(
            _csv(colaborador="Micael de Araújo Silva", localizacao="Sala de TI",
                 tombamento="TEST029F")
        )
        r = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert r["errors"] == [], r["errors"]

        db_session.refresh(asset)
        assert asset.custodian_id == custs["Micael de Araújo Silva"]
        assert asset.status == AssetStatus.IN_USE
        movs_depois = _movements(db_session, asset.id)
        # Nova ALOCACAO_CAUTELA; movimentações anteriores preservadas
        assert len(movs_depois) == len(movs_antes) + 1
        nova = movs_depois[-1]
        assert nova.movement_type == MovementType.ALLOCATION
        assert nova.destination_custodian_id == custs["Micael de Araújo Silva"]
        assert nova.destination_location_id == locs["Sala de TI"]
        assert nova.operator_name == OPERADOR
        assert movs_antes == movs_depois[:-1]

    def test_g_mudanca_de_local_mesmo_colaborador(self, db_session):
        locs = _criar_locais_base(db_session)
        custs = _criar_colaboradores_base(db_session)
        asset = self._importar_inicial(db_session, "TEST029G", "Mariana Souto Soares", "Sala de TI")
        movs_antes = _movements(db_session, asset.id)

        rows, _ = parse_csv(
            _csv(colaborador="Mariana Souto Soares", localizacao="Laboratório",
                 tombamento="TEST029G")
        )
        r = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert r["errors"] == [], r["errors"]

        db_session.refresh(asset)
        assert asset.custodian_id == custs["Mariana Souto Soares"]
        assert asset.location_id == locs["Laboratório"]
        movs_depois = _movements(db_session, asset.id)
        assert len(movs_depois) == len(movs_antes) + 1
        nova = movs_depois[-1]
        # (G) mudança só de local com mesmo responsável → TRANSFERENCIA_LOCAL
        assert nova.movement_type == MovementType.TRANSFER
        assert nova.destination_location_id == locs["Laboratório"]
        assert nova.destination_custodian_id == custs["Mariana Souto Soares"]
        assert movs_antes == movs_depois[:-1]

    def test_h_mudanca_de_colaborador_e_local_simultanea(self, db_session):
        locs = _criar_locais_base(db_session)
        custs = _criar_colaboradores_base(db_session)
        asset = self._importar_inicial(db_session, "TEST029H", "Mariana Souto Soares", "Sala de TI")
        movs_antes = _movements(db_session, asset.id)

        rows, _ = parse_csv(
            _csv(colaborador="Micael de Araújo Silva", localizacao="Divisão de Previdência",
                 tombamento="TEST029H")
        )
        r = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert r["errors"] == [], r["errors"]

        db_session.refresh(asset)
        assert asset.custodian_id == custs["Micael de Araújo Silva"]
        assert asset.location_id == locs["Divisão de Previdência"]
        movs_depois = _movements(db_session, asset.id)
        assert len(movs_depois) == len(movs_antes) + 1
        nova = movs_depois[-1]
        # (H) entrega a novo colaborador → ALOCACAO_CAUTELA com termo (VAL-007)
        assert nova.movement_type == MovementType.ALLOCATION
        assert nova.term_code is not None
        assert nova.term_code.startswith(f"TR-{nova.timestamp.year}-")
        assert movs_antes == movs_depois[:-1]

    def test_reimportacao_sem_colaborador_mantem_custodia_atual(self, db_session):
        """(R4) carga parcial sem custodiante NÃO desaloca o bem."""
        custs = _criar_colaboradores_base(db_session)
        asset = self._importar_inicial(db_session, "TEST029R4", "Mariana Souto Soares", "Sala de TI")
        movs_antes = _movements(db_session, asset.id)

        rows, _ = parse_csv(_csv(tombamento="TEST029R4"))
        r = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        assert r["errors"] == [], r["errors"]

        db_session.refresh(asset)
        assert asset.custodian_id == custs["Mariana Souto Soares"]
        assert len(_movements(db_session, asset.id)) == len(movs_antes)


# ---------------------------------------------------------------------------
# Cenário K — falha transacional não deixa estado parcial (US5)
# ---------------------------------------------------------------------------

class TestCenarioK_FalhaTransacional:
    def test_k_falha_na_movimentacao_nao_deixa_estado_parcial(self, db_session, monkeypatch):
        locs = _criar_locais_base(db_session)
        _criar_colaboradores_base(db_session)

        rows, errs = parse_csv(
            _csv(colaborador="Mariana Souto Soares", localizacao="Sala de TI",
                 tombamento="TEST029K")
        )
        assert errs == []

        original = MovementService.create_movement

        # Assinatura compatível com a 030 (parâmetros aditivos notify/operator/ip_address)
        def _falha(db, data, *args, **kwargs):
            raise ValueError("Falha simulada na movimentação")

        monkeypatch.setattr(MovementService, "create_movement", _falha)
        result = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        monkeypatch.setattr(MovementService, "create_movement", original)

        # Linha reportada como erro
        assert result["imported"] == 0
        assert any("Falha simulada" in e for e in result["errors"])

        # Sem estado parcial: a unidade da linha é rollback por inteiro —
        # o bem não fica alocado (nem entra pela metade) sem a movimentação
        asset = _asset(db_session, "TEST029K")
        if asset is not None:
            assert asset.custodian_id is None
            assert asset.status != AssetStatus.IN_USE
            movs = _movements(db_session, asset.id)
            assert all(m.movement_type == MovementType.ACQUISITION for m in movs)
            assert asset.location_id is None or asset.location_id == locs["Sala de TI"]

    def test_k_falha_em_uma_linha_nao_impede_as_demasias(self, db_session, monkeypatch):
        _criar_locais_base(db_session)
        _criar_colaboradores_base(db_session)
        csv_texto = (
            "tombamento;equipamento;categoria;Custodiante;localização\n"
            "TEST029K1;Computador;DESKTOP;Mariana Souto Soares;Sala de TI\n"
            "TEST029K2;Monitor;MONITOR;;Sala de TI\n"
        )
        rows, _ = parse_csv(csv_texto)

        chamadas = {"n": 0}
        original = MovementService.create_movement

        # Assinatura compatível com a 030 (parâmetros aditivos notify/operator/ip_address)
        def _falha_apos_primeira(db, data, *args, **kwargs):
            chamadas["n"] += 1
            if chamadas["n"] > 1:
                raise ValueError("Falha simulada na movimentação")
            return original(db, data, *args, **kwargs)

        monkeypatch.setattr(MovementService, "create_movement", _falha_apos_primeira)
        result = execute_import(rows, db_session, skip_duplicates=False, operator_name=OPERADOR)
        monkeypatch.setattr(MovementService, "create_movement", original)

        # 1ª linha OK (com custódia), 2ª linha sem custódia não passa pelo motor
        assert _asset(db_session, "TEST029K1") is not None
        k2 = _asset(db_session, "TEST029K2")
        assert k2 is not None
        assert k2.custodian_id is None


# ---------------------------------------------------------------------------
# Matriz — MovementService.resolve_movement_type (Foundational)
# ---------------------------------------------------------------------------

class TestResolveMovementType:
    def test_nenhuma_alteracao_retorna_none(self):
        assert MovementService.resolve_movement_type(1, 2, 1, 2) is None
        assert MovementService.resolve_movement_type(None, None, None, None) is None

    def test_mesmo_local_custodiante_diferente_alocacao(self):
        assert (
            MovementService.resolve_movement_type(1, 2, 1, 3)
            == MovementType.ALLOCATION
        )

    def test_local_diferente_mesmo_custodiante_transferencia(self):
        assert (
            MovementService.resolve_movement_type(1, 2, 2, 2)
            == MovementType.TRANSFER
        )

    def test_local_e_custodiante_diferentes_alocacao_com_termo(self):
        assert (
            MovementService.resolve_movement_type(1, 2, 3, 4)
            == MovementType.ALLOCATION
        )

    def test_estoque_para_colaborador_alocacao(self):
        assert (
            MovementService.resolve_movement_type(1, None, 1, 5)
            == MovementType.ALLOCATION
        )
        assert (
            MovementService.resolve_movement_type(None, None, 7, 5)
            == MovementType.ALLOCATION
        )

    def test_e_puro_sem_db(self):
        """Método puro: não toca DB nem muta estado (contrato C3)."""
        import inspect
        sig = inspect.signature(MovementService.resolve_movement_type)
        assert len(sig.parameters) == 4
        # chamadas repetidas com mesmos argumentos → mesmo resultado (determinístico)
        r1 = MovementService.resolve_movement_type(1, None, 2, 3)
        r2 = MovementService.resolve_movement_type(1, None, 2, 3)
        assert r1 == r2 == MovementType.ALLOCATION


# ---------------------------------------------------------------------------
# Parser — coluna de custodiante entra pelos aliases (Foundational)
# ---------------------------------------------------------------------------

class TestParseCustodiante:
    @pytest.mark.parametrize("coluna", ["Custodiante", "custodiante", "colaborador",
                                        "responsavel", "custodian"])
    def test_alias_custodiante(self, coluna):
        csv_texto = (
            f"tombamento;equipamento;categoria;{coluna}\n"
            "TEST029P;Computador;DESKTOP;Mariana Souto Soares\n"
        )
        rows, errs = parse_csv(csv_texto)
        assert errs == []
        assert rows[0]["custodiante"] == "Mariana Souto Soares"

    def test_celula_com_espacos_vira_vazio(self):
        rows, errs = parse_csv(
            "tombamento;equipamento;categoria;Custodiante\n"
            "TEST029P2;Computador;DESKTOP;   \n"
        )
        assert errs == []
        assert rows[0]["custodiante"] == ""


# ---------------------------------------------------------------------------
# Cenário J — usuário autenticado como operador (US1, integração via API)
# ---------------------------------------------------------------------------

class TestCenarioJ_UsuarioAutenticado:
    def test_j_import_api_registra_operador_autenticado(self, client, db_session):
        """A movimentação gerada pela importação via API usa como operador o
        nome de exibição do usuário autenticado (não 'Sistema' nem o
        colaborador do CSV), e a auditoria ACTION_IMPORT é registrada."""
        from io import BytesIO

        from app.models.audit_log import AuditLog
        from app.services.audit_service import ACTION_IMPORT

        _criar_locais_base(db_session)
        _criar_colaboradores_base(db_session)

        csv_content = _csv(
            colaborador="Mariana Souto Soares", localizacao="Sala de TI",
            tombamento="TEST029J",
        ).encode("utf-8")

        response = client.post(
            "/api/v1/assets/import/csv",
            files={"file": ("equipamentos.csv", BytesIO(csv_content), "text/csv")},
            data={"skip_duplicates": "false"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["imported"] == 1, body.get("errors")

        asset = _asset(db_session, "TEST029J")
        assert asset is not None
        alocacao = (
            db_session.query(Movement)
            .filter(
                Movement.asset_id == asset.id,
                Movement.movement_type == MovementType.ALLOCATION,
            )
            .first()
        )
        assert alocacao is not None
        # Operador = nome de exibição do usuário autenticado (conftest:
        # full_name="Usuário de Teste")
        assert alocacao.operator_name == "Usuário de Teste"

        # Auditoria da importação permanece registrada (FR-018)
        audit = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == ACTION_IMPORT, AuditLog.resource == "Asset")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert audit is not None
