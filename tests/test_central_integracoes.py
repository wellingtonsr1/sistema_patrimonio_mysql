"""Testes da Central de Integrações (feature 032 — spec §22).

Fakes SEMPRE — nenhum serviço externo real (SMTP/HTTP/AD) na suíte.
Cenários: RBAC (US2), painel/status (US1), segredos mascarados (US2),
teste de conexão (US3), histórico/diagnóstico (US4), propagação (US5),
condução administrativa (US6), idempotência/extensibilidade (SC-007/SC-008).
"""

import pytest

from app import config
from app.models.ad_settings import ADSettings
from app.models.integration_execution import (
    OP_CONNECTION_TEST,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    IntegrationExecution,
)
from app.models.notification import EmailConfig, Notification
from app.models.onedoc_integration import OneDocIntegration
from app.services import integration_center_service as ics


# ============================================================================
# Helpers / fixtures
# ============================================================================

def _make_user(db, username="admin_central", is_admin=False):
    from app.models.user import User
    from app.services.auth_service import hash_password

    user = db.query(User).filter(User.username == username).first()
    if user:
        return user
    user = User(
        username=username,
        full_name="Admin Central",
        email=f"{username}@test.local",
        is_active=True,
        is_admin=is_admin,
        password_hash=hash_password("SenhaForte!123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _grant(db, user, perm_name):
    from app.models.permission import Permission
    from app.models.role import Role
    from app.models.role_permission import RolePermission
    from app.models.user_role import UserRole

    role = db.query(Role).filter(Role.name == "_central_test").first()
    if not role:
        role = Role(name="_central_test", description="perfil de teste", is_system=False)
        db.add(role)
        db.commit()
        db.refresh(role)
    perm = db.query(Permission).filter(Permission.name == perm_name).first()
    if not perm:
        perm = Permission(name=perm_name, module="Integrações", label=perm_name)
        db.add(perm)
        db.commit()
        db.refresh(perm)
    if not db.query(RolePermission).filter_by(role_id=role.id, permission_id=perm.id).first():
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        db.commit()
    if not db.query(UserRole).filter_by(user_id=user.id, role_id=role.id).first():
        db.add(UserRole(user_id=user.id, role_id=role.id, assigned_by="local"))
        db.commit()


def _login(client, db, user):
    """Loga via endpoint de autenticação (padrão test_onedoc.py) — cookie
    de sessão real criado pelo fluxo HTTP com o usuário já no banco."""
    client.cookies.clear()
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": user.username, "password": "SenhaForte!123"},
    )
    assert resp.status_code == 200, f"login falhou para {user.username}: {resp.text}"


def _seed_email_enabled(db):
    row = db.query(EmailConfig).filter(EmailConfig.id == 1).first()
    if row:
        row.notifications_enabled = True
    else:
        db.add(EmailConfig(id=1, notifications_enabled=True, recipients='["a@t.local"]'))
    db.commit()


@pytest.fixture
def db(db_session):
    """Alias para o fixture `db_session` do conftest (convenção 030/031)."""
    return db_session


@pytest.fixture
def admin_user(db):
    return _make_user(db, "admin_central", is_admin=False)


# ============================================================================
# US2 — RBAC: todas as rotas negam a não autorizados
# ============================================================================

class TestRBAC:
    ROTAS = [
        ("get", "/admin/integracoes"),
        ("get", "/admin/integracoes/email"),
        ("get", "/admin/integracoes/email/historico"),
        ("get", "/admin/integracoes/movimentacao/1"),
    ]

    def test_sem_permissao_negado(self, client, db, admin_user):
        _login(client, db, admin_user)  # sem integracoes.visualizar
        for method, url in self.ROTAS:
            resp = getattr(client, method)(url)
            assert resp.status_code == 403, url

    def test_post_testar_sem_permissao_negado(self, client, db, admin_user):
        _login(client, db, admin_user)
        resp = client.post("/admin/integracoes/email/testar")
        assert resp.status_code == 403

    def test_com_visualizar_acessa_painel(self, client, db, admin_user):
        _grant(db, admin_user, "integracoes.visualizar")
        _login(client, db, admin_user)
        resp = client.get("/admin/integracoes")
        assert resp.status_code == 200

    def test_testar_exige_testar(self, client, db, admin_user):
        _grant(db, admin_user, "integracoes.visualizar")  # sem integracoes.testar
        _login(client, db, admin_user)
        resp = client.post("/admin/integracoes/email/testar")
        assert resp.status_code == 403

    def test_nao_autenticado_redirect_login(self, unauth_client):
        resp = unauth_client.get("/admin/integracoes", follow_redirects=False)
        assert resp.status_code in (303, 307)


# ============================================================================
# US1 — Painel: status padronizado por integração (derivação spec §7)
# ============================================================================

class TestStatusDerivation:
    def test_email_sem_smtp_nao_configurada(self, db, monkeypatch):
        monkeypatch.setattr(config, "SMTP_HOST", "")
        assert ics._email_status_fn(db)["status"] == ics.STATUS_NAO_CONFIGURADA

    def test_email_desabilitada(self, db, monkeypatch):
        monkeypatch.setattr(config, "SMTP_HOST", "smtp.t.local")
        # email_config ausente → default desativado (RN-006/FR-006)
        assert ics._email_status_fn(db)["status"] == ics.STATUS_DESABILITADA

    def test_email_ativa_com_sucesso(self, db, monkeypatch):
        monkeypatch.setattr(config, "SMTP_HOST", "smtp.t.local")
        _seed_email_enabled(db)
        db.add(IntegrationExecution(integration_key="email", operation="SEND_EMAIL", result=RESULT_SUCCESS))
        db.commit()
        assert ics._email_status_fn(db)["status"] == ics.STATUS_ATIVA

    def test_email_com_erro(self, db, monkeypatch):
        monkeypatch.setattr(config, "SMTP_HOST", "smtp.t.local")
        _seed_email_enabled(db)
        db.add(IntegrationExecution(integration_key="email", operation="SEND_EMAIL", result=RESULT_FAILURE, detail="Falha de autenticação"))
        db.commit()
        assert ics._email_status_fn(db)["status"] == ics.STATUS_COM_ERRO

    def test_email_indisponivel(self, db, monkeypatch):
        monkeypatch.setattr(config, "SMTP_HOST", "smtp.t.local")
        _seed_email_enabled(db)
        db.add(IntegrationExecution(integration_key="email", operation=OP_CONNECTION_TEST, result=RESULT_FAILURE, detail="Serviço de e-mail indisponível (OSError)."))
        db.commit()
        assert ics._email_status_fn(db)["status"] == ics.STATUS_INDISPONIVEL

    def test_email_inativa_sem_execucoes(self, db, monkeypatch):
        monkeypatch.setattr(config, "SMTP_HOST", "smtp.t.local")
        _seed_email_enabled(db)
        assert ics._email_status_fn(db)["status"] == ics.STATUS_INATIVA

    def test_onedoc_pendente_por_fornecedor(self, db, monkeypatch):
        monkeypatch.setattr(config, "ONEDOC_ENABLED", False)
        assert ics._onedoc_status_fn(db)["status"] == ics.STATUS_PENDENTE

    def test_onedoc_pendente_tem_precedencia(self, db, monkeypatch):
        # PENDENTE (fornecedor) vence DESABILITADA — integração nunca operou
        monkeypatch.setattr(config, "ONEDOC_ENABLED", False)
        card = next(c for c in ics.get_panel(db) if c["key"] == "onedoc")
        assert card["status"] == ics.STATUS_PENDENTE

    def test_ad_desabilitada(self, db, monkeypatch):
        monkeypatch.setattr(config, "AD_SERVER", "")
        monkeypatch.setattr(config, "AD_BASE_DN", "")
        assert ics._ad_status_fn(db)["status"] == ics.STATUS_DESABILITADA

    def test_ad_nao_configurada_sem_servidor(self, db, monkeypatch):
        monkeypatch.setattr(config, "AD_SERVER", "")
        monkeypatch.setattr(config, "AD_BASE_DN", "")
        db.add(ADSettings(id=1, enabled=True, server="", base_dn=""))
        db.commit()
        assert ics._ad_status_fn(db)["status"] == ics.STATUS_NAO_CONFIGURADA

    def test_glpi_nao_configurada_fixa(self, db):
        assert ics._glpi_status_fn(db)["status"] == ics.STATUS_NAO_CONFIGURADA


class TestPainel:
    def test_quatro_cards_com_campos(self, client, db, admin_user, monkeypatch):
        monkeypatch.setattr(config, "SMTP_HOST", "")
        monkeypatch.setattr(config, "ONEDOC_ENABLED", False)
        monkeypatch.setattr(config, "AD_SERVER", "")
        _grant(db, admin_user, "integracoes.visualizar")
        _login(client, db, admin_user)

        resp = client.get("/admin/integracoes")
        html = resp.text
        assert resp.status_code == 200
        for nome in ("E-mail", "1Doc", "GLPI", "Active Directory"):
            assert nome in html
        assert "Falhas recentes (24h)" in html  # janela explícita (P-4)
        assert "Pendente" in html               # 1Doc aguardando fornecedor
        assert "Não Configurada" in html        # GLPI prevista

    def test_menu_item_unico_central(self, client, db, admin_user, monkeypatch):
        """Menu: apenas 'Central de Integrações' — os cards do painel (AD, 1Doc,
        GLPI, E-mail) são a segunda camada, sem submenu no menu lateral."""
        monkeypatch.setattr(config, "SMTP_HOST", "")
        _grant(db, admin_user, "integracoes.visualizar")
        _login(client, db, admin_user)
        page = client.get("/admin/integracoes").text
        assert "Central de Integrações" in page
        assert "sidebar-subnav" not in page  # sem submenu no menu
        # O painel exibe as 4 integrações (segunda camada)
        for nome in ("E-mail", "1Doc", "GLPI", "Active Directory"):
            assert nome in page
        # Sem itens soltos com rótulo antigo no menu
        assert "> Integração AD<" not in page
        assert "> Integração 1Doc<" not in page

    def test_extensibilidade_stub_aparece_no_painel(self, db, monkeypatch):
        """SC-007/C1: nova integração = nova entrada no catálogo, sem mudança estrutural."""
        def _stub_status(db):
            return {"status": ics.STATUS_INATIVA, "detail": {}}

        monkeypatch.setitem(
            ics.INTEGRATIONS.__class__ and ics.__dict__, "_orig", None
        ) if False else None
        ics.INTEGRATIONS.append(
            {
                "key": "webhook_exemplo",
                "name": "Webhook Exemplo",
                "description": "stub",
                "purpose": "stub",
                "supports_test": False,
                "supports_reprocess": False,
                "supports_enable_disable": False,
                "config_route": None,
                "config_permission": None,
                "status_fn": _stub_status,
            }
        )
        try:
            cards = ics.get_panel(db)
            keys = [c["key"] for c in cards]
            assert "webhook_exemplo" in keys
            card = next(c for c in cards if c["key"] == "webhook_exemplo")
            assert card["status_label"] == "Inativa"
        finally:
            ics.INTEGRATIONS.pop()

    def test_janela_falhas_24h(self, db, monkeypatch):
        """P-4: contagem limitada à janela de 24h (execução antiga não conta)."""
        from datetime import timedelta

        from app.utils.time_utils import now_utc

        monkeypatch.setattr(config, "SMTP_HOST", "")
        old = IntegrationExecution(
            integration_key="email",
            operation="SEND_EMAIL",
            result=RESULT_FAILURE,
            created_at=now_utc() - timedelta(hours=48),
        )
        db.add(old)
        db.commit()
        counters = ics._execution_counters(db, "email")
        assert counters["failures"] >= 1
        assert counters["failures_24h"] == 0


# ============================================================================
# US2 — Segredos nunca expostos (SC-003)
# ============================================================================

class TestSegredos:
    def test_mask_secret(self):
        """FR-016/FR-017: indicação de presença; últimos 4 chars só em valores
        longos (exemplo da spec: '************ABCD'); valor curto = só asteriscos."""
        assert ics.mask_secret("") == ""
        assert ics.mask_secret(None) == ""
        assert ics.mask_secret("curta") == "************"          # < 8 chars: nada revelável
        assert ics.mask_secret("senhasecreta-ABCD") == "************ABCD"  # padrão da spec

    def test_superficie_sem_credenciais(self, client, db, admin_user, monkeypatch):
        """SC-003: varredura de painel/detalhe/histórico/propagação."""
        segredo_smtp = "SENHA-SMTP-SECRETA-XYZ"
        segredo_onedoc = "TOKEN-1DOC-SECRETO-QRS"
        monkeypatch.setattr(config, "SMTP_HOST", "smtp.t.local")
        monkeypatch.setattr(config, "SMTP_PASSWORD", segredo_smtp)
        monkeypatch.setattr(config, "ONEDOC_API_URL", "https://api.1doc.t.local")
        monkeypatch.setattr(config, "ONEDOC_API_TOKEN", segredo_onedoc)
        _seed_email_enabled(db)

        _grant(db, admin_user, "integracoes.visualizar")
        _login(client, db, admin_user)

        for url in (
            "/admin/integracoes",
            "/admin/integracoes/email",
            "/admin/integracoes/onedoc",
            "/admin/integracoes/email/historico",
            "/admin/integracoes/movimentacao/999",
        ):
            html = client.get(url).text
            assert segredo_smtp not in html, url
            assert segredo_onedoc not in html, url

    def test_detail_saneado_na_execucao(self, db):
        """NFR-002: erro que ecoa a senha é sanitizado antes de gravar."""
        from app.services.audit_service import write_audit  # noqa: F401

        segredo = "SENHA-VAZADA-NO-ERRO"
        ics.record_execution(db, "email", "SEND_EMAIL", RESULT_FAILURE, detail=f"SMTP auth falhou: senha={segredo}")
        row = db.query(IntegrationExecution).order_by(IntegrationExecution.id.desc()).first()
        assert segredo not in (row.detail or "")
        assert "***" in (row.detail or "")

    def test_record_execution_nunca_levanta(self, db, monkeypatch):
        """Plan D6: falha de gravação nunca afeta a integração."""
        def boom_commit(self):
            raise RuntimeError("db quebrado")

        monkeypatch.setattr(type(db), "commit", boom_commit)
        # não deve levantar
        ics.record_execution(db, "email", "SEND_EMAIL", RESULT_SUCCESS)


# ============================================================================
# US3 — Teste de conexão (fake; idempotência SC-008/C3)
# ============================================================================

class FakeEmailProvider:
    @staticmethod
    def fake_check(ok=True, message="ok"):
        def _inner():
            return ok, message, 42 if ok else None
        return _inner


class TestRunTest:
    def test_email_sucesso_registra(self, client, db, admin_user, monkeypatch):
        _grant(db, admin_user, "integracoes.visualizar")
        _grant(db, admin_user, "integracoes.testar")
        _login(client, db, admin_user)
        monkeypatch.setattr(
            "app.services.email_provider.check_connection",
            FakeEmailProvider.fake_check(True, "Conexão e autenticação SMTP verificadas com sucesso."),
        )
        resp = client.post("/admin/integracoes/email/testar", follow_redirects=False)
        assert resp.status_code == 303
        assert "success" in resp.headers["location"]
        rows = db.query(IntegrationExecution).filter_by(integration_key="email", operation=OP_CONNECTION_TEST).all()
        assert len(rows) == 1
        assert rows[0].result == RESULT_SUCCESS

    def test_email_timeout_classifica_indisponivel(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.email_provider.check_connection",
            FakeEmailProvider.fake_check(False, "Serviço de e-mail indisponível (OSError)."),
        )
        ok, msg = ics.run_test(db, "email")
        assert ok is False
        assert "indisponível" in msg.lower()

    def test_email_auth_invalida_classifica_autenticacao(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.email_provider.check_connection",
            FakeEmailProvider.fake_check(False, "Falha de autenticação na integração com o e-mail (SMTP)."),
        )
        ok, msg = ics.run_test(db, "email")
        assert "autenticação" in msg.lower()

    def test_onedoc_interno_sem_http(self, db, monkeypatch):
        """P-3/D8: verificação INTERNA — nenhuma chamada externa enquanto [PENDING C-*]."""
        chamadas = []
        monkeypatch.setattr("app.services.onedoc_client.OneDocHttpClient.find_process", lambda self, n: chamadas.append(n) or True)
        monkeypatch.setattr(config, "ONEDOC_API_URL", "https://api.1doc.t.local")
        monkeypatch.setattr(config, "ONEDOC_API_TOKEN", "tok")
        ok, msg = ics.run_test(db, "onedoc")
        assert ok is True
        assert chamadas == []  # nenhuma chamada HTTP
        row = db.query(IntegrationExecution).filter_by(integration_key="onedoc", operation="INTERNAL_CHECK").first()
        assert row is not None

    def test_teste_duas_vezes_duas_execucoes(self, client, db, admin_user, monkeypatch):
        """SC-008/C3: cada teste grava exatamente 1 execução — nada duplicado além do esperado."""
        _grant(db, admin_user, "integracoes.visualizar")
        _grant(db, admin_user, "integracoes.testar")
        _login(client, db, admin_user)
        monkeypatch.setattr(
            "app.services.email_provider.check_connection",
            FakeEmailProvider.fake_check(True, "ok"),
        )
        client.post("/admin/integracoes/email/testar")
        client.post("/admin/integracoes/email/testar")
        n = db.query(IntegrationExecution).filter_by(integration_key="email", operation=OP_CONNECTION_TEST).count()
        assert n == 2

    def test_glpi_sem_teste(self, client, db, admin_user):
        _grant(db, admin_user, "integracoes.visualizar")
        _grant(db, admin_user, "integracoes.testar")
        _login(client, db, admin_user)
        resp = client.post("/admin/integracoes/glpi/testar", follow_redirects=False)
        assert resp.status_code == 404

    def test_auditoria_do_teste(self, db, monkeypatch, admin_user):
        from app.services.audit_service import get_audit_logs

        monkeypatch.setattr(
            "app.services.email_provider.check_connection",
            FakeEmailProvider.fake_check(True, "ok"),
        )
        ics.run_test(db, "email", user=admin_user, ip_address="127.0.0.1")
        logs = get_audit_logs(db, limit=10)
        assert any(l.action in ("TESTE_INTEGRACAO_SUCESSO", "TESTE_INTEGRACAO_FALHA") for l in logs)


# ============================================================================
# US4 — Detalhe e histórico (filtros, paginação, sanitização)
# ============================================================================

class TestDetalheHistorico:
    def _seed(self, db):
        db.add(IntegrationExecution(integration_key="email", operation="SEND_EMAIL", result=RESULT_SUCCESS, username="op1"))
        db.add(IntegrationExecution(integration_key="email", operation="SEND_EMAIL", result=RESULT_FAILURE, username="op2", detail="Falha de autenticação SMTP"))
        db.commit()

    def test_contadores_no_detalhe(self, client, db, admin_user):
        self._seed(db)
        _grant(db, admin_user, "integracoes.visualizar")
        _login(client, db, admin_user)
        html = client.get("/admin/integracoes/email").text
        assert "Falha de autenticação SMTP" in html
        assert "2" in html  # total de execuções

    def test_filtro_por_usuario(self, db):
        """FR-019/C2: filtro opcional por usuário."""
        self._seed(db)
        result = ics.get_history(db, "email", user="op1")
        assert result["total"] == 1
        assert result["rows"][0].username == "op1"

    def test_filtro_status(self, db):
        self._seed(db)
        result = ics.get_history(db, "email", status=RESULT_FAILURE)
        assert result["total"] == 1

    def test_paginacao(self, db):
        for i in range(25):
            db.add(IntegrationExecution(integration_key="onedoc", operation="SEND_COMMUNICATION", result=RESULT_SUCCESS))
        db.commit()
        page1 = ics.get_history(db, "onedoc", page=1, page_size=20)
        page2 = ics.get_history(db, "onedoc", page=2, page_size=20)
        assert page1["total"] == 25
        assert len(page1["rows"]) == 20
        assert len(page2["rows"]) == 5
        assert page1["rows"][0].created_at >= page2["rows"][0].created_at  # desc

    def test_historico_vazio_amigavel(self, client, db, admin_user):
        _grant(db, admin_user, "integracoes.visualizar")
        _login(client, db, admin_user)
        resp = client.get("/admin/integracoes/onedoc/historico")
        assert resp.status_code == 200

    def test_key_invalida_404(self, client, db, admin_user):
        _grant(db, admin_user, "integracoes.visualizar")
        _login(client, db, admin_user)
        assert client.get("/admin/integracoes/inexistente").status_code == 404


# ============================================================================
# US5 — Propagação por movimentação (somente leitura; idempotência SC-008)
# ============================================================================

class TestPropagacao:
    def _movement(self, db):
        from app.models.asset import Asset
        from app.models.enums import AssetStatus, MovementType
        from app.models.movement import Movement

        asset = db.query(Asset).first()
        if not asset:
            asset = Asset(tag="T-PROP-01", name="Bem Propagação")
            db.add(asset)
            db.commit()
            db.refresh(asset)
        mv = Movement(
            asset_id=asset.id,
            movement_type=MovementType.ALLOCATION,
            new_status=AssetStatus.IN_USE,
            reason="Teste de propagação",
            operator_name="op",
        )
        db.add(mv)
        db.commit()
        db.refresh(mv)
        return mv

    def test_estados_por_integracao(self, client, db, admin_user):
        mv = self._movement(db)
        db.add(Notification(movement_id=mv.id, status="SENT"))
        db.add(OneDocIntegration(movement_id=mv.id, process_number="2026/1", status="PENDING"))
        db.commit()
        _grant(db, admin_user, "integracoes.visualizar")
        _login(client, db, admin_user)

        prop = ics.get_movement_propagation(db, mv.id)
        assert prop["email"]["status"] == "SENT"
        assert prop["onedoc"]["status"] == "PENDING"
        assert prop["glpi"] is None  # não aplicável

        html = client.get(f"/admin/integracoes/movimentacao/{mv.id}").text
        assert "T-PROP-01" in html or str(mv.id) in html

    def test_movimentacao_sem_registros(self, db):
        mv = self._movement(db)
        prop = ics.get_movement_propagation(db, mv.id)
        assert prop["email"]["status"] is None
        assert prop["onedoc"]["status"] is None

    def test_reprocesso_nao_duplica_registro(self, db, monkeypatch, admin_user):
        """SC-008/C3: reprocess com sucesso mantém exatamente 1 registro (UNIQUE)."""
        mv = self._movement(db)
        integration = OneDocIntegration(movement_id=mv.id, process_number="2026/9", status="FAILED")
        db.add(integration)
        db.commit()
        db.refresh(integration)

        class FakeProvider:
            def send_communication(self, *a, **k):
                return "msg-1"

        monkeypatch.setattr(config, "ONEDOC_ENABLED", True)
        from app.services import onedoc_service

        ok, msg = onedoc_service.reprocess(db, integration.id, user=admin_user, provider=FakeProvider())
        assert ok is True
        n = db.query(OneDocIntegration).filter_by(movement_id=mv.id).count()
        assert n == 1
        db.refresh(integration)
        assert integration.status == "SENT"


# ============================================================================
# US6 — Condução administrativa (guardas de destino; sem interruptor novo)
# ============================================================================

class TestConducao:
    def test_tela_notificacoes_mantem_guarda(self, client, db, admin_user):
        """Acesso direto à tela de destino SEM a permissão dela → negado (a
        Central não concede o que a tela não concederia — FR-013/P-3)."""
        _grant(db, admin_user, "integracoes.visualizar")
        _grant(db, admin_user, "integracoes.testar")
        # SEM notificacoes.gerenciar
        _login(client, db, admin_user)
        resp = client.get("/admin/notificacoes")
        assert resp.status_code == 403

    def test_tela_1doc_mantem_guarda(self, client, db, admin_user):
        _grant(db, admin_user, "integracoes.visualizar")  # sem integracao1doc.reprocessar
        _login(client, db, admin_user)
        resp = client.get("/admin/integracao-1doc")
        assert resp.status_code == 403
