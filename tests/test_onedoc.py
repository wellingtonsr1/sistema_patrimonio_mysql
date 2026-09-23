"""
Testes da Integração 1Doc (feature 031).

Cobre os cenários US1/US2/US3 da spec com FAKE de provider (nunca HTTP real):
comunicação automática com tabela fiel (US1), falha externa sem afetar a
movimentação (US2), reprocessamento + idempotência + RBAC (US3).
"""

import pytest

from app import config
from app.models.enums import AssetCategory, MovementType
from app.models.onedoc_integration import OneDocIntegration
from app.schemas.asset import AssetCreate
from app.schemas.custodian import CustodianCreate
from app.schemas.location import LocationCreate
from app.schemas.movement import MovementCreate
from app.services import onedoc_service as osvc
from app.services.audit_service import (
    ACTION_INTEGRACAO_1DOC_ENVIADA,
    ACTION_INTEGRACAO_1DOC_SOLICITADA,
    get_audit_logs,
)
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.location_service import LocationService
from app.services.movement_service import MovementService

SUBJECT_PREFIX_1DOC = "[SisPatrimônio Pro] Movimentação patrimonial - "


class FakeOneDocProvider:
    """Fake do OneDocProvider: captura chamadas; erros opcionais."""

    def __init__(self, send_error=None, find_process_result=None):
        self.calls = []
        self.send_error = send_error
        self.find_process_result = find_process_result  # bool | None (Q2)

    def find_process(self, process_number):
        return self.find_process_result

    def send_communication(self, process_number, *, subject, body_text, body_html):
        self.calls.append(
            {
                "process_number": process_number,
                "subject": subject,
                "body_text": body_text,
                "body_html": body_html,
            }
        )
        if self.send_error is not None:
            raise self.send_error
        return f"MSG-{len(self.calls):04d}"


@pytest.fixture
def fake_onedoc(monkeypatch):
    """Provider fake default do onedoc_service (envio e consulta Q2)."""
    fake = FakeOneDocProvider()
    monkeypatch.setattr(osvc, "OneDocHttpClient", lambda: fake)
    return fake


@pytest.fixture
def onedoc_ativa(monkeypatch):
    """Liga a integração via ambiente (default do sistema é false)."""
    monkeypatch.setattr(config, "ONEDOC_ENABLED", True)


def _base(db_session, tag="DOC-99001", loc_name="TI Central"):
    """Cria local, bem e colaborador (padrão test_movements/test_notificacoes)."""
    loc = LocationService.create(
        db_session,
        LocationCreate(name=loc_name, branch="Matriz", department="TI"),
    )
    asset = AssetService.create(
        db_session,
        AssetCreate(
            tag=tag,
            name="Dell Latitude 5440",
            category=AssetCategory.NOTEBOOK,
            initial_location_id=loc.id,
        ),
    )
    cust = CustodianService.create(
        db_session,
        CustodianCreate(
            registration_code=f"MAT-{tag[-5:]}",  # único por bem (tags distintos no teste)
            name="Rodrigo Santos",
            email=f"rodrigo.{tag[-5:]}@empresa.com",  # único por bem
            role="Dev",
            department="TI",
        ),
    )
    return loc, asset, cust


def _cautela(db_session, asset, cust, process_number=None, operator="Admin TI"):
    return MovementService.create_movement(
        db_session,
        MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.ALLOCATION,
            destination_custodian_id=cust.id,
            reason="Entrega de computador de trabalho",
            operator_name=operator,
        ),
        onedoc_process_number=process_number,
    )


def _integracao(db_session, movement_id):
    return (
        db_session.query(OneDocIntegration)
        .filter(OneDocIntegration.movement_id == movement_id)
        .one()
    )


# ============================================================================
# US1 — Comunicação automática no processo 1Doc (P1) — MVP
# ============================================================================


def test_us1_a_cautela_com_processo_gera_comunicacao(
    db_session, fake_onedoc, onedoc_ativa
):
    """(a) cautela com processo → SENT + message_id + auditoria SOLICITADA/ENVIADA."""
    loc, asset, cust = _base(db_session, tag="DOC-99001")
    movement = _cautela(db_session, asset, cust, process_number="2026/000123")

    notif = _integracao(db_session, movement.id)
    assert notif.status == "SENT"
    assert notif.process_number == "2026/000123"
    assert notif.message_id == "MSG-0001"
    assert notif.sent_at is not None
    assert notif.attempt_count == 1
    # FR-017: campo reservado do link futuro permanece NULL
    assert notif.content_url is None

    logs = get_audit_logs(db_session, module="integracao_1doc")
    actions = {l.action for l in logs}
    assert ACTION_INTEGRACAO_1DOC_SOLICITADA in actions
    assert ACTION_INTEGRACAO_1DOC_ENVIADA in actions
    # eventos automáticos: ator = serviço (precedente 020/030)
    assert all(l.user_id is None for l in logs if l.action != "INTEGRACAO_1DOC_REPROCESSADA")


def test_us1_b_conteudo_fiel_ao_modelo_do_setor(db_session, fake_onedoc, onedoc_ativa):
    """(b) saudação + tabela 4 colunas com dados oficiais; sem link (FR-017)."""
    loc, asset, cust = _base(db_session, tag="DOC-99002")
    _cautela(db_session, asset, cust, process_number="2026/000124")

    body = fake_onedoc.calls[0]["body_text"]
    assert fake_onedoc.calls[0]["subject"] == SUBJECT_PREFIX_1DOC + "DOC-99002"
    assert ("Bom dia!" in body) or ("Boa tarde!" in body) or ("Boa noite!" in body)
    assert "Descrição do Material" in body
    assert "Tombamento" in body
    assert "Origem" in body
    assert "Destino" in body
    assert "Dell Latitude 5440" in body          # Descrição do Material
    assert "DOC-99002" in body                   # Tombamento
    assert "TI Central" in body                  # Origem == Destino local inicial
    assert "http" not in body.lower()            # FR-017: sem link nesta versão
    # HTML também gerado (escolha do client conforme C-4)
    assert "<table" in fake_onedoc.calls[0]["body_html"]


def test_us1_c_processo_obrigatorio_quando_ativa(db_session, fake_onedoc, onedoc_ativa):
    """(c) integração ativa + cautela SEM processo → ValueError, nada gravado (FR-002)."""
    loc, asset, cust = _base(db_session, tag="DOC-99003")
    total_antes = db_session.query(OneDocIntegration).count()

    with pytest.raises(ValueError, match="processo 1Doc"):
        _cautela(db_session, asset, cust, process_number=None)

    assert len(fake_onedoc.calls) == 0
    assert db_session.query(OneDocIntegration).count() == total_antes


def test_us1_d_processo_inexistente_bloqueia(db_session, fake_onedoc, onedoc_ativa):
    """(d) find_process→False → ValueError; movimentação NÃO gravada (US1.3/Q2)."""
    loc, asset, cust = _base(db_session, tag="DOC-99004")
    fake_onedoc.find_process_result = False

    with pytest.raises(ValueError, match="não foi encontrado"):
        _cautela(db_session, asset, cust, process_number="2026/999999")

    assert len(fake_onedoc.calls) == 0
    assert db_session.query(OneDocIntegration).count() == 0


def test_us1_e_api_sem_consulta_modo_tolerante(db_session, fake_onedoc, onedoc_ativa):
    """(e) find_process→None → modo tolerante: grava e envia (US1.4/Q2)."""
    loc, asset, cust = _base(db_session, tag="DOC-99005")
    fake_onedoc.find_process_result = None

    movement = _cautela(db_session, asset, cust, process_number="2026/000125")
    notif = _integracao(db_session, movement.id)
    assert notif.status == "SENT"
    assert len(fake_onedoc.calls) == 1


def test_us1_f_desativada_byte_identico(db_session, fake_onedoc):
    """(f) integração desativada (default) → nenhum campo exigido, nenhum registro."""
    loc, asset, cust = _base(db_session, tag="DOC-99006")
    assert config.ONEDOC_ENABLED is False  # default do sistema

    movement = _cautela(db_session, asset, cust, process_number=None)
    assert movement.id is not None
    assert db_session.query(OneDocIntegration).count() == 0
    assert len(fake_onedoc.calls) == 0


def test_us1_g_tipos_fora_do_alcance(db_session, fake_onedoc, onedoc_ativa):
    """(g) devolução (de bem em uso) e manutenção não interagem com o 1Doc (Q1)."""
    loc, asset, cust = _base(db_session, tag="DOC-99007")
    # aloca primeiro (cautela válida SEM processo — enforce desligado apenas
    # para o setup; o objetivo do teste são os tipos fora do alcance)
    MovementService.create_movement(
        db_session,
        MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.ALLOCATION,
            destination_custodian_id=cust.id,
            reason="Setup do cenário",
            operator_name="Setup",
        ),
        onedoc_enforce=False,
    )

    # devolução ao estoque mesmo COM processo informado: fora do alcance (Q1)
    MovementService.create_movement(
        db_session,
        MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.RETURN_STOCK,
            reason="Devolução de teste",
            operator_name="Admin TI",
        ),
        onedoc_process_number="2026/000126",
    )
    # apenas a cautela do setup teria integrado SE tivesse processo — como não
    # tinha, nenhum registro existe; e a devolução não gerou nada:
    assert db_session.query(OneDocIntegration).count() == 0
    assert len(fake_onedoc.calls) == 0

    # envio para manutenção também fora do alcance
    MovementService.create_movement(
        db_session,
        MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.MAINTENANCE_OUT,
            reason="Envio para conserto",
            operator_name="Admin TI",
        ),
        onedoc_process_number="2026/000127",
    )
    assert db_session.query(OneDocIntegration).count() == 0
    assert len(fake_onedoc.calls) == 0


def test_us1_h_movimentacao_invalida_nao_notifica(db_session, fake_onedoc, onedoc_ativa):
    """(h) validação VAL falha → ValueError propagado, provider não chamado."""
    loc, asset, cust = _base(db_session, tag="DOC-99009")
    _cautela(db_session, asset, cust, process_number="2026/000127")  # 1ª válida
    total_antes = db_session.query(OneDocIntegration).count()

    with pytest.raises(ValueError):
        _cautela(db_session, asset, cust, process_number="2026/000128")  # VAL-002: sem alteração efetiva

    assert len(fake_onedoc.calls) == 1  # só a 1ª
    assert db_session.query(OneDocIntegration).count() == total_antes


def test_us1_i_lote_csv_fora_do_alcance(db_session, fake_onedoc, onedoc_ativa):
    """(i) import CSV: onedoc_enforce=False — sem exigência, sem registro (F6)."""
    loc, asset, cust = _base(db_session, tag="DOC-99010")
    # simula a chamada do lote (import_service): enforce desligado, SEM processo
    movement = MovementService.create_movement(
        db_session,
        MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.ALLOCATION,
            destination_custodian_id=cust.id,
            reason="Alocação via carga CSV",
            operator_name="Importação",
        ),
        onedoc_enforce=False,
    )
    assert movement.id is not None
    assert db_session.query(OneDocIntegration).count() == 0
    assert len(fake_onedoc.calls) == 0


# ============================================================================
# US2 — Falha do 1Doc nunca afeta a movimentação (P1)
# ============================================================================


class _SecretError(Exception):
    """Erro que ecoa o token (simula vazamento de credencial em mensagem)."""


def test_us2_a_falha_registra_failed_sanitizado(db_session, fake_onedoc, onedoc_ativa):
    """(a) provider lança erro com o token → movimentação válida, FAILED com ***, auditoria FALHOU."""
    loc, asset, cust = _base(db_session, tag="DOC-99011")
    fake_onedoc.send_error = _SecretError("conexao recusada token=ONEDOC-SEGREDO-123")

    movement = _cautela(db_session, asset, cust, process_number="2026/000130")
    assert movement.id is not None  # movimentação PERMANECE concluída (FR-007)

    notif = _integracao(db_session, movement.id)
    assert notif.status == "FAILED"
    assert notif.last_error is not None
    assert "ONEDOC-SEGREDO-123" not in notif.last_error   # sanitizado (SC-005)
    assert "***" in notif.last_error
    assert notif.last_error_at is not None

    logs = get_audit_logs(db_session, module="integracao_1doc")
    falhas = [l for l in logs if l.action == "INTEGRACAO_1DOC_FALHOU"]
    assert len(falhas) == 1
    assert falhas[0].result == "FAILURE"
    serializado = f"{falhas[0].description or ''}{falhas[0].new_data or ''}"
    assert "ONEDOC-SEGREDO-123" not in serializado


def test_us2_b_timeout_nao_presa_o_usuario(db_session, onedoc_ativa, monkeypatch):
    """(b) provider lento além do timeout → integração FAILED, resposta não presa (SC-004)."""
    import time
    from app.models.onedoc_integration import STATUS_FAILED as FAILED

    class SlowProvider:
        def find_process(self, process_number):
            return None
        def send_communication(self, process_number, **kw):
            time.sleep(0.5)  # fake do timeout (o real é do client/requests)
            raise TimeoutError("simulou timeout de leitura")

    monkeypatch.setattr(osvc, "OneDocHttpClient", lambda: SlowProvider())

    loc, asset, cust = _base(db_session, tag="DOC-99012")
    start = time.time()
    movement = _cautela(db_session, asset, cust, process_number="2026/000131")
    elapsed = time.time() - start

    # movimentação concluída mesmo com provider lento; hook captura a exceção
    assert movement.id is not None
    assert elapsed < 30  # não fica preso indefinidamente
    notif = _integracao(db_session, movement.id)
    assert notif.status == FAILED
    assert notif.attempt_count == 1


def test_us2_c_erro_permanente_sem_retry_automatico(db_session, fake_onedoc, onedoc_ativa):
    """(c) erro permanente (4xx) → FAILED; nenhuma nova tentativa automática (FR-010)."""
    loc, asset, cust = _base(db_session, tag="DOC-99013")
    fake_onedoc.send_error = Exception("HTTP 403 — credencial recusada")

    movement = _cautela(db_session, asset, cust, process_number="2026/000132")
    notif = _integracao(db_session, movement.id)
    assert notif.status == "FAILED"
    assert notif.attempt_count == 1  # single-shot: sem loop de retry (P-5)
    assert len(fake_onedoc.calls) == 1


def test_us2_d_email_e_1doc_independentes(db_session, fake_onedoc, onedoc_ativa, monkeypatch):
    """(d) 1Doc falha com e-mail ativo → e-mail SENT e 1Doc FAILED (FR-015)."""
    from app.services import notification_service as ns
    from app.models.notification import Notification

    class FakeEmailProvider:
        def __init__(self):
            self.calls = []
        def send(self, *, subject, body, recipients):
            self.calls.append({"subject": subject})
    fake_email = FakeEmailProvider()
    monkeypatch.setattr(ns, "SMTPEmailProvider", lambda: fake_email)

    # ativa notificação em banco (padrão 030)
    from app.services.email_config_service import save_config
    save_config(db_session, enabled=True, recipients=["patrimonio@test.local"], user=None)

    loc, asset, cust = _base(db_session, tag="DOC-99014")
    fake_onedoc.send_error = Exception("1Doc indisponível")

    movement = _cautela(db_session, asset, cust, process_number="2026/000133")

    email_row = db_session.query(Notification).filter_by(movement_id=movement.id).one()
    assert email_row.status == "SENT"
    assert len(fake_email.calls) == 1

    onedoc_row = _integracao(db_session, movement.id)
    assert onedoc_row.status == "FAILED"   # independente do e-mail (FR-015)


def test_us2_e_crash_apos_insert_nao_quebra_proximas(db_session, fake_onedoc, onedoc_ativa):
    """(e) PENDING órfão (crash entre insert e envio) não quebra movimentações seguintes."""
    loc, asset, cust = _base(db_session, tag="DOC-99015", loc_name="TI Central A")
    # cria registro PENDING órfão manualmente (simula crash)
    movement1 = _cautela(db_session, asset, cust, process_number="2026/000134")
    orphan = _integracao(db_session, movement1.id)
    orphan.status = "PENDING"
    db_session.commit()
    fake_onedoc.calls.clear()

    # nova movimentação do mesmo bem (devolução não integra; usar outro bem)
    loc2, asset2, cust2 = _base(db_session, tag="DOC-99016", loc_name="TI Central B")
    movement2 = _cautela(db_session, asset2, cust2, process_number="2026/000135")
    assert movement2.id is not None
    row2 = _integracao(db_session, movement2.id)
    assert row2.status == "SENT"  # fluxo seguinte íntegro


# ============================================================================
# US3 — Ciência, reprocessamento e idempotência (P2)
# ============================================================================


def _make_user_com_permissao(db, permission_name, username="oper_1doc"):
    """Cria usuário com perfil contendo UMA permissão (padrão test_rbac/030)."""
    from app.models.permission import Permission
    from app.models.role import Role
    from app.models.role_permission import RolePermission
    from app.models.user_role import UserRole
    from app.services.auth_service import create_user
    from app.services.permission_service import ensure_default_roles

    ensure_default_roles(db)
    user = create_user(
        db,
        username=username,
        password="teste@1234",
        full_name=f"Operador {username}",
        is_admin=False,
    )
    perm = db.query(Permission).filter(Permission.name == permission_name).one()
    role = Role(name=f"Role {permission_name}", is_system=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return user


def _login(client, username="oper_1doc", password="teste@1234"):
    resp = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp


def test_us3_a_reprocessa_failed_para_sent(db_session, fake_onedoc, onedoc_ativa):
    """(a) FAILED + reprocess (permissão) → SENT, mesmo registro, auditoria com user real."""
    user = _make_user_com_permissao(db_session, "integracao1doc.reprocessar")
    loc, asset, cust = _base(db_session, tag="DOC-99017")

    fake_onedoc.send_error = Exception("1Doc indisponível")
    movement = _cautela(db_session, asset, cust, process_number="2026/000140")
    row = _integracao(db_session, movement.id)
    assert row.status == "FAILED"
    integration_id = row.id  # MESMO registro (UNIQUE)

    fake_onedoc.send_error = None  # 1Doc recuperado
    ok, msg = osvc.reprocess(db_session, integration_id, user=user, provider=fake_onedoc)

    assert ok is True, msg
    db_session.expire(row)
    assert row.status == "SENT"
    assert row.id == integration_id        # mesmo registro — nunca duplica
    assert row.attempt_count == 2          # 1ª falha + reprocessamento

    logs = get_audit_logs(db_session, module="integracao_1doc")
    reproc = [l for l in logs if l.action == "INTEGRACAO_1DOC_REPROCESSADA"]
    assert len(reproc) == 1
    assert reproc[0].user_id == user.id    # usuário REAL no reprocessamento (Q4)


def test_us3_b_reprocess_sent_nao_reenvia(db_session, fake_onedoc, onedoc_ativa):
    """(b) reprocessar integração SENT → nada reenviado (Q3/D8)."""
    user = _make_user_com_permissao(db_session, "integracao1doc.reprocessar")
    loc, asset, cust = _base(db_session, tag="DOC-99018")
    movement = _cautela(db_session, asset, cust, process_number="2026/000141")
    row = _integracao(db_session, movement.id)
    assert row.status == "SENT"
    assert len(fake_onedoc.calls) == 1

    ok, msg = osvc.reprocess(db_session, row.id, user=user, provider=fake_onedoc)
    assert ok is False
    assert "já enviada" in msg
    assert len(fake_onedoc.calls) == 1     # nenhuma segunda comunicação (SC-003)


def test_us3_c_idempotencia_unica_por_movimentacao(db_session, fake_onedoc, onedoc_ativa):
    """(c) chamar notify_movement 2× (retry/requisição repetida) → 1 registro apenas."""
    loc, asset, cust = _base(db_session, tag="DOC-99019")
    movement = _cautela(db_session, asset, cust, process_number="2026/000142")
    assert db_session.query(OneDocIntegration).count() == 1

    # repetição explícita do disparo (ex.: requisição reenviada)
    osvc.notify_movement(db_session, movement, "2026/000142", provider=fake_onedoc)
    assert db_session.query(OneDocIntegration).count() == 1
    assert len(fake_onedoc.calls) == 1


def _setup_rota(db_session, permission_name):
    """Cria usuário c/ permissão + registra client web (padrão 030 US3)."""
    user = _make_user_com_permissao(db_session, permission_name)
    return user


def test_us3_d_rota_sem_permissao_403(db_session, unauth_client):
    """(d) rota reprocessar sem permissão dedicada → 403 (deny by default, Q4)."""
    from app.services.auth_service import create_user
    from app.services.permission_service import ensure_default_roles

    ensure_default_roles(db_session)
    create_user(
        db_session,
        username="oper_sem_perm",
        password="teste@1234",
        full_name="Sem Permissão",
        is_admin=False,
    )
    _login(unauth_client, username="oper_sem_perm")
    resp = unauth_client.post("/admin/integracao-1doc/1/reprocessar")
    assert resp.status_code == 403

    resp = unauth_client.get("/admin/integracao-1doc")
    assert resp.status_code == 403


def test_us3_e_rota_lista_com_permissao(db_session, unauth_client, fake_onedoc, onedoc_ativa):
    """(e) GET com permissão → 200 listando integrações; POST reprocessa FAILED."""
    _setup_rota(db_session, "integracao1doc.reprocessar")
    _login(unauth_client)

    loc, asset, cust = _base(db_session, tag="DOC-99020")
    fake_onedoc.send_error = Exception("1Doc fora do ar")
    movement = _cautela(db_session, asset, cust, process_number="2026/000143")
    row = _integracao(db_session, movement.id)
    assert row.status == "FAILED"

    resp = unauth_client.get("/admin/integracao-1doc")
    assert resp.status_code == 200
    assert "2026/000143" in resp.text       # processo listado

    fake_onedoc.send_error = None
    resp = unauth_client.post(f"/admin/integracao-1doc/{row.id}/reprocessar")
    assert resp.status_code in (200, 303)   # flash + redirect (padrão web)
    db_session.expire(row)
    assert row.status == "SENT"


def test_us3_f_content_url_permanece_null(db_session, fake_onedoc, onedoc_ativa):
    """(f) após todos os fluxos, content_url permanece NULL (FR-017)."""
    user = _make_user_com_permissao(db_session, "integracao1doc.reprocessar")
    loc, asset, cust = _base(db_session, tag="DOC-99021")
    movement = _cautela(db_session, asset, cust, process_number="2026/000144")
    row = _integracao(db_session, movement.id)
    assert row.content_url is None
    osvc.reprocess(db_session, row.id, user=user, provider=fake_onedoc)
    assert row.content_url is None
