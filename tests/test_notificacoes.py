"""
Testes da Notificação por E-mail de Movimentações (feature 030).

Cobre os cenários da spec Seção 14 com FAKE de provider (nunca SMTP real):
sucesso (assunto/conteúdo/registro/auditoria), falha de SMTP sem afetar a
movimentação, movimentação inválida sem e-mail, desativado (default),
destinatários, idempotência, segurança (sem credenciais), lote CSV e
tipos fora do alcance.
"""

import json

import pytest

from app.models.enums import AssetCategory, MovementType
from app.models.notification import Notification
from app.schemas.asset import AssetCreate
from app.schemas.custodian import CustodianCreate
from app.schemas.location import LocationCreate
from app.schemas.movement import MovementCreate
from app.services import notification_service as ns
from app.services.audit_service import (
    ACTION_NOTIFICACAO_ENVIADA,
    get_audit_logs,
)
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.email_config_service import save_config
from app.services.location_service import LocationService
from app.services.movement_service import MovementService

SUBJECT_PREFIX = "[SisPatrimônio Pro] Nova movimentação patrimonial - "


class FakeProvider:
    """Fake do EmailProvider: captura chamadas; opcionalmente levanta erro."""

    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def send(self, *, subject, body, recipients):
        self.calls.append(
            {"subject": subject, "body": body, "recipients": list(recipients)}
        )
        if self.error is not None:
            raise self.error


@pytest.fixture
def fake_provider(monkeypatch):
    """Injeta o fake como provider default do notification_service."""
    fake = FakeProvider()
    monkeypatch.setattr(ns, "SMTPEmailProvider", lambda: fake)
    return fake


@pytest.fixture
def notificacoes_ativas(db_session):
    """Ativa a notificação com um destinatário institucional de teste."""
    return save_config(
        db_session,
        enabled=True,
        recipients=["patrimonio@test.local"],
        user=None,
    )


def _base(db_session, tag="PAT-99001"):
    """Cria local, bem e colaborador (padrão test_movements)."""
    loc = LocationService.create(
        db_session,
        LocationCreate(name="TI Central", branch="Matriz", department="TI"),
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
            registration_code="MAT-5001",
            name="Rodrigo Santos",
            email="rodrigo@empresa.com",
            role="Dev",
            department="TI",
        ),
    )
    return loc, asset, cust


def _alocar(db_session, asset, cust, operator="Admin TI"):
    return MovementService.create_movement(
        db_session,
        MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.ALLOCATION,
            destination_custodian_id=cust.id,
            reason="Entrega de computador de trabalho",
            operator_name=operator,
        ),
    )


# ============================================================================
# US1 — Setor toma ciência (sucesso)
# ============================================================================

def test_us1_a_alocacao_ativa_envia_um_email_para_os_destinatarios(
    db_session, fake_provider, notificacoes_ativas
):
    """(a) ALOCAÇÃO com config ativada + fake → provider 1× com destinatários exatos."""
    loc, asset, cust = _base(db_session, tag="PAT-99001")

    movement = _alocar(db_session, asset, cust)

    assert len(fake_provider.calls) == 1
    call = fake_provider.calls[0]
    assert call["recipients"] == ["patrimonio@test.local"]

    # (d) registro Notification criado, SENT, vinculado à movimentação
    notif = db_session.query(Notification).filter_by(movement_id=movement.id).one()
    assert notif.status == "SENT"
    assert notif.attempt_count == 1
    assert notif.sent_at is not None
    # (US4/RN-008) campo reservado do link futuro permanece NULL
    assert notif.content_url is None
    assert json.loads(notif.recipients) == ["patrimonio@test.local"]


def test_us1_b_assunto_padronizado(db_session, fake_provider, notificacoes_ativas):
    """(b) assunto = [SisPatrimônio Pro] Nova movimentação patrimonial - <TAG> (RN-005)."""
    loc, asset, cust = _base(db_session, tag="PAT-99002")
    _alocar(db_session, asset, cust)
    assert fake_provider.calls[0]["subject"] == SUBJECT_PREFIX + "PAT-99002"


def test_us1_c_conteudo_do_email(db_session, fake_provider, notificacoes_ativas):
    """(c) corpo contém os dados da movimentação e NÃO contém link (FR-008/RN-008/RN-010)."""
    loc, asset, cust = _base(db_session, tag="PAT-99003")
    _alocar(db_session, asset, cust, operator="Admin TI")

    body = fake_provider.calls[0]["body"]
    assert "PAT-99003" in body                       # tombamento
    assert "Dell Latitude 5440" in body              # identificação do bem
    assert "Alocação / Cautela" in body              # rótulo do tipo (.label)
    assert "TI Central" in body                      # local (origem/destino)
    assert "Rodrigo Santos" in body                  # custodiante atual
    assert "Admin TI" in body                        # operador (RN-010)
    assert "Data e hora" in body                     # data/hora apresentada
    assert "http" not in body.lower()                # RN-008: sem link nesta versão


def test_us1_e_auditoria_do_envio(db_session, fake_provider, notificacoes_ativas):
    """(e) auditoria NOTIFICACAO_ENVIADA, SUCCESS, sem credenciais."""
    loc, asset, cust = _base(db_session, tag="PAT-99004")
    movement = _alocar(db_session, asset, cust)

    logs = get_audit_logs(db_session, module="notificacoes")
    enviados = [l for l in logs if l.action == ACTION_NOTIFICACAO_ENVIADA]
    assert len(enviados) == 1
    evento = enviados[0]
    assert evento.result == "SUCCESS"
    assert evento.resource == "movement"
    assert evento.resource_id == movement.id
    assert evento.resource_ref == "PAT-99004"
    # sem credenciais/segredos no evento (SC-005)
    serializado = f"{evento.description or ''}{evento.new_data or ''}".lower()
    assert "smtp_password" not in serializado
    assert "senha" not in serializado


def test_us1_f_transferencia_e_devolucao_tambem_notificam(
    db_session, fake_provider, notificacoes_ativas
):
    """(f) TRANSFERENCIA_LOCAL e DEVOLUCAO_ESTOQUE geram e-mail (RN-002/Q1)."""
    loc, asset, cust = _base(db_session, tag="PAT-99005")

    # aloca (1º e-mail)
    _alocar(db_session, asset, cust)
    assert len(fake_provider.calls) == 1

    # transferência de local com custódia preservada (2º e-mail)
    loc2 = LocationService.create(
        db_session,
        LocationCreate(name="Filial Sul", branch="Filial", department="Administração"),
    )
    MovementService.create_movement(
        db_session,
        MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.TRANSFER,
            destination_location_id=loc2.id,
            reason="Mudança de setor",
            operator_name="Admin TI",
        ),
    )
    assert len(fake_provider.calls) == 2

    # devolução ao estoque (3º e-mail)
    MovementService.create_movement(
        db_session,
        MovementCreate(
            asset_id=asset.id,
            movement_type=MovementType.RETURN_STOCK,
            destination_location_id=loc.id,
            reason="Devolução por troca de equipamento",
            operator_name="Admin TI",
        ),
    )
    assert len(fake_provider.calls) == 3
    assert "Transferência de Local" in fake_provider.calls[1]["body"]
    assert "Devolução ao Estoque" in fake_provider.calls[2]["body"]


def test_us1_g_tipo_fora_do_alcance_nao_notifica(
    db_session, fake_provider, notificacoes_ativas
):
    """(g) ENTRADA_AQUISICAO (fora do alcance) → nenhum e-mail, nenhum registro (RN-002/Q1)."""
    _base(db_session, tag="PAT-99006")  # criação do bem gera ENTRADA_AQUISICAO

    assert len(fake_provider.calls) == 0
    assert db_session.query(Notification).count() == 0


def test_us1_h_movimentacao_invalida_nao_notifica(
    db_session, fake_provider, notificacoes_ativas
):
    """(h) validação falha (VAL-002) → ValueError propagado, NENHUM e-mail/registro (FR-002)."""
    loc, asset, cust = _base(db_session, tag="PAT-99007")
    _alocar(db_session, asset, cust)  # 1º e-mail (válido)
    assert len(fake_provider.calls) == 1
    total_antes = db_session.query(Notification).count()

    # alocação redundante: mesmo custodiante e mesmo local → VAL-002
    with pytest.raises(ValueError):
        MovementService.create_movement(
            db_session,
            MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType.ALLOCATION,
                destination_custodian_id=cust.id,
                reason="Tentativa sem alteração efetiva",
                operator_name="Admin TI",
            ),
        )

    assert len(fake_provider.calls) == 1  # nenhum e-mail novo
    assert db_session.query(Notification).count() == total_antes  # nenhum registro


# ============================================================================
# US2 — Falha de e-mail nunca afeta a movimentação
# ============================================================================

class _SMTPUnavailable(RuntimeError):
    pass


def test_us2_a_smtp_caido_movimentacao_persiste(
    db_session, monkeypatch, notificacoes_ativas
):
    """(a) SMTP indisponível → movimentação persistida e concluída (RN-001)."""
    fake = FakeProvider(error=_SMTPUnavailable("Connection refused"))
    monkeypatch.setattr(ns, "SMTPEmailProvider", lambda: fake)

    loc, asset, cust = _base(db_session, tag="PAT-99008")
    movement = _alocar(db_session, asset, cust)

    # movimentação persistida normalmente + estado do bem atualizado
    assert movement.id is not None
    db_session.refresh(asset)
    from app.models.enums import AssetStatus
    assert asset.status == AssetStatus.IN_USE
    assert asset.custodian_id == cust.id


def test_us2_b_registro_failed_sem_segredos(
    db_session, monkeypatch, notificacoes_ativas
):
    """(b) Notification FAILED, attempt_count=1, erro sanitizado (FR-010).

    As credenciais reais do ambiente (config SMTP_*) nunca aparecem no
    error_message, mesmo quando a exceção as ecoa.
    """
    from app import config as app_config

    monkeypatch.setattr(app_config, "SMTP_USERNAME", "secret-user")
    monkeypatch.setattr(app_config, "SMTP_PASSWORD", "secret-pass")
    fake = FakeProvider(error=RuntimeError("AUTH 535 failed for secret-user/secret-pass"))
    monkeypatch.setattr(ns, "SMTPEmailProvider", lambda: fake)

    loc, asset, cust = _base(db_session, tag="PAT-99009")
    _alocar(db_session, asset, cust)

    notif = db_session.query(Notification).one()
    assert notif.status == "FAILED"
    assert notif.attempt_count == 1
    assert notif.last_attempt_at is not None
    assert notif.error_message  # registrada
    assert "secret-pass" not in notif.error_message
    assert "secret-user" not in notif.error_message


def test_us2_c_auditoria_da_falha_sanitizada(
    db_session, monkeypatch, notificacoes_ativas
):
    """(c) auditoria NOTIFICACAO_FALHOU, FAILURE, descrição sem segredos."""
    from app import config as app_config
    from app.services.audit_service import ACTION_NOTIFICACAO_FALHOU

    monkeypatch.setattr(app_config, "SMTP_PASSWORD", "super-senha-123")
    fake = FakeProvider(error=RuntimeError("SMTP down (credencial: super-senha-123)"))
    monkeypatch.setattr(ns, "SMTPEmailProvider", lambda: fake)

    loc, asset, cust = _base(db_session, tag="PAT-99010")
    _alocar(db_session, asset, cust)

    logs = get_audit_logs(db_session, module="notificacoes")
    falhas = [l for l in logs if l.action == ACTION_NOTIFICACAO_FALHOU]
    assert len(falhas) == 1
    assert falhas[0].result == "FAILURE"
    desc = (falhas[0].description or "").lower()
    assert "super-senha-123" not in desc


def test_us2_d_erro_de_montagem_registra_falha(
    db_session, monkeypatch, notificacoes_ativas
):
    """(d) exceção na montagem do conteúdo → falha registrada, nada propaga."""
    fake = FakeProvider()
    monkeypatch.setattr(ns, "SMTPEmailProvider", lambda: fake)
    monkeypatch.setattr(ns, "build_body", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom-template")))

    loc, asset, cust = _base(db_session, tag="PAT-99011")
    movement = _alocar(db_session, asset, cust)  # NÃO pode levantar

    assert movement.id is not None
    notif = db_session.query(Notification).filter_by(movement_id=movement.id).one()
    assert notif.status == "FAILED"
    assert "boom-template" in (notif.error_message or "")


def test_us2_e_sem_excecao_ao_chamador(db_session, monkeypatch, notificacoes_ativas):
    """(e) nenhuma exceção escapa do fluxo em cenário de falha (FR-003)."""
    class _ExplodingProvider:
        def send(self, **kw):
            raise RuntimeError("catastrophic smtp failure")

    monkeypatch.setattr(ns, "SMTPEmailProvider", lambda: _ExplodingProvider())

    loc, asset, cust = _base(db_session, tag="PAT-99012")
    # se alguma exceção escapasse, a própria chamada abaixo levantaria
    movement = _alocar(db_session, asset, cust)
    assert movement.id is not None


def _override_get_db_test():
    """Override do get_db apontando para o banco de teste (padrão conftest)."""
    from tests.conftest import TestingSessionLocal as TSL
    db = TSL()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# US3 — Administrador configura a notificação
# ============================================================================

def _make_user_com_permissao(db, permission_name):
    """Cria usuário com um perfil contendo UMA permissão (padrão test_rbac)."""
    from app.models.permission import Permission
    from app.models.role import Role
    from app.models.role_permission import RolePermission
    from app.models.user_role import UserRole
    from app.services.auth_service import create_user
    from app.services.permission_service import ensure_default_roles

    ensure_default_roles(db)
    user = create_user(
        db,
        username="oper_notif",
        password="teste@1234",
        full_name="Operador Notif",
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


def _login(client, username="oper_notif", password="teste@1234"):
    resp = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp


def test_us3_a_get_formulario_com_permissao(db_session, unauth_client):
    """(a) GET /admin/notificacoes com permissão → 200 e estado atual (leitura pura)."""
    _make_user_com_permissao(db_session, "notificacoes.gerenciar")
    _login(unauth_client)
    resp = unauth_client.get("/admin/notificacoes")
    assert resp.status_code == 200
    assert "Notifica" in resp.text
    # leitura pura: GET não cria a linha singleton se ausente
    from app.models.notification import EmailConfig
    row = db_session.query(EmailConfig).filter(EmailConfig.id == 1).first()
    assert row is None or bool(row.notifications_enabled) is False


def test_us3_b_post_ativado_sem_destinatario_rejeitado(db_session, unauth_client):
    """(b) POST ativado sem destinatários → erro amigável, nada persistido."""
    _make_user_com_permissao(db_session, "notificacoes.gerenciar")
    _login(unauth_client)
    resp = unauth_client.post(
        "/admin/notificacoes",
        data={"notifications_enabled": "on", "recipients": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]
    from app.models.notification import EmailConfig
    assert db_session.query(EmailConfig).count() == 0


def test_us3_c_post_email_invalido_rejeitado(db_session, unauth_client):
    """(c) POST com e-mail inválido → rejeitado."""
    _make_user_com_permissao(db_session, "notificacoes.gerenciar")
    _login(unauth_client)
    resp = unauth_client.post(
        "/admin/notificacoes",
        data={"notifications_enabled": "on", "recipients": "invalido@@sem-tld"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]


def test_us3_d_post_valido_persiste_e_audita(db_session, unauth_client):
    """(d) POST válido → persistido, flash de sucesso, auditoria de configuração."""
    from app.services.audit_service import ACTION_NOTIFICACAO_CONFIG, get_audit_logs

    _make_user_com_permissao(db_session, "notificacoes.gerenciar")
    _login(unauth_client)
    resp = unauth_client.post(
        "/admin/notificacoes",
        data={"notifications_enabled": "on", "recipients": "patrimonio@test.local"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "success=" in resp.headers["location"]

    from app.models.notification import EmailConfig
    row = db_session.query(EmailConfig).filter(EmailConfig.id == 1).one()
    assert row.notifications_enabled is True
    assert json.loads(row.recipients) == ["patrimonio@test.local"]

    logs = get_audit_logs(db_session, action=ACTION_NOTIFICACAO_CONFIG)
    assert len(logs) == 1
    assert logs[0].result == "SUCCESS"


def test_us3_e_desativado_nenhum_email(db_session, fake_provider):
    """(e) notificações desativadas (default) → nenhum e-mail, nenhum registro."""
    loc, asset, cust = _base(db_session, tag="PAT-99013")
    movement = _alocar(db_session, asset, cust)
    assert movement.id is not None
    assert len(fake_provider.calls) == 0
    assert db_session.query(Notification).count() == 0


def test_us3_f_sem_permissao_acesso_negado(db_session, unauth_client):
    """(f) usuário sem notificacoes.gerenciar → GET/POST negados (403)."""
    _make_user_com_permissao(db_session, "patrimonio.visualizar")  # permissão qualquer, não a exigida
    _login(unauth_client)
    assert unauth_client.get("/admin/notificacoes").status_code == 403
    assert unauth_client.post("/admin/notificacoes", data={}).status_code == 403


# ============================================================================
# US4 — Trazibilidade e não duplicidade
# ============================================================================

def test_us4_a_segunda_chamada_nao_reenvia(
    db_session, fake_provider, notificacoes_ativas
):
    """(a) reprocesso: notify_movement 2× para a mesma movimentação → 1 e-mail (RN-007)."""
    loc, asset, cust = _base(db_session, tag="PAT-99014")
    movement = _alocar(db_session, asset, cust)
    assert len(fake_provider.calls) == 1

    from app.services.notification_service import notify_movement
    notify_movement(db_session, movement)  # 2ª chamada (reprocesso futuro)

    assert len(fake_provider.calls) == 1  # nenhum reenvio
    assert db_session.query(Notification).filter_by(movement_id=movement.id).count() == 1


def test_us4_b_unico_registro_por_movimentacao(
    db_session, notificacoes_ativas
):
    """(b) banco rejeita 2ª Notification para o mesmo movement_id (UNIQUE)."""
    from sqlalchemy.exc import IntegrityError

    loc, asset, cust = _base(db_session, tag="PAT-99015")
    movement = _alocar(db_session, asset, cust)

    dup = Notification(movement_id=movement.id, status="PENDING")
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_us4_c_trilha_sem_segredos(db_session, fake_provider, notificacoes_ativas, monkeypatch):
    """(c) eventos de notificação contêm destinatários/resultado e nenhum segredo."""
    from app import config as app_config
    from app.services.audit_service import (
        ACTION_NOTIFICACAO_ENVIADA,
        ACTION_NOTIFICACAO_FALHOU,
    )

    monkeypatch_pass = "senh4-sup3r-s3cr3t4"
    monkeypatch.setattr(app_config, "SMTP_PASSWORD", monkeypatch_pass)
    loc, asset, cust = _base(db_session, tag="PAT-99016")
    _alocar(db_session, asset, cust)  # sucesso

    logs = get_audit_logs(db_session, module="notificacoes")
    acoes = {l.action for l in logs}
    assert ACTION_NOTIFICACAO_ENVIADA in acoes
    assert ACTION_NOTIFICACAO_FALHOU not in acoes or all(
        "senh4" not in (l.description or "").lower() for l in logs if l.action == ACTION_NOTIFICACAO_FALHOU
    )
    for l in logs:
        texto = f"{l.description or ''}{l.new_data or ''}".lower()
        assert "senh4-sup3r-s3cr3t4" not in texto
        assert "smtp_password" not in texto


def test_us4_d_content_url_null_na_v1(db_session, fake_provider, notificacoes_ativas):
    """(d) content_url é NULL na v1 — link futuro sem reestruturar (RN-008)."""
    loc, asset, cust = _base(db_session, tag="PAT-99017")
    movement = _alocar(db_session, asset, cust)
    notif = db_session.query(Notification).filter_by(movement_id=movement.id).one()
    assert notif.content_url is None


def test_us4_e_lote_csv_sem_notificacao(db_session, fake_provider, notificacoes_ativas):
    """(e) lote da importação CSV não notifica por linha (RN-002/Q2)."""
    from app.services.import_service import execute_import

    # config ativada; linha de CSV com bem novo + custodiante cria
    # ENTRADA_AQUISICAO e ALOCACAO_CAUTELA (lote) — nenhuma notifica
    # (nomes canônicos de coluna — saída de parse_csv)
    csv_rows = [{
        "tombamento": "PAT-CSV-001",
        "equipamento": "Notebook CSV",
        "categoria": "NOTEBOOK",
        "local_filial": "Matriz",
        "local_departamento": "TI",
        "local_nome": "TI Central",
        "custodiante_matricula": "MAT-9001",
        "custodiante_nome": "Colab CSV",
        "custodiante_email": "colab@empresa.com",
        "custodiante_cargo": "Dev",
        "custodiante_departamento": "TI",
    }]
    result = execute_import(csv_rows, db_session, operator_name="Importador")
    assert result.get("imported", 0) >= 1
    assert db_session.query(Notification).count() == 0
    assert len(fake_provider.calls) == 0
