import os
import sys
from pathlib import Path

# Garante que o diretório raiz do projeto está no PYTHONPATH
# (necessário quando pytest é executado diretamente, sem instalacao do pacote)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configurações de autenticação para os testes (devem vir antes dos imports do app)
os.environ.setdefault("AUTH_PBKDF2_ITERATIONS", "1000")   # hash rápido nos testes
os.environ.setdefault("AUTH_COOKIE_SECURE", "false")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.services.auth_service import create_user

# Banco de dados de teste pode ser SQLite em memória (padrão) ou MariaDB se
# DATABASE_URL_TEST for configurado. Isso mantém a compatibilidade com a suite
# existente (106 testes) sem depender de um serviço MariaDB rodando.
_TEST_DATABASE_URL = os.getenv("DATABASE_URL_TEST", "sqlite:///:memory:")

if _TEST_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        _TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    engine = create_engine(
        _TEST_DATABASE_URL,
        poolclass=StaticPool,
        pool_pre_ping=True,
    )

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============================================================================
# Feature 054 (achado M1 da análise de 2026-09-29): HERMETICIDADE da suíte.
#
# O lifespan do TestClient (app/main.py) executava init_db() → engine do
# banco REAL do .env e ensure_admin_user/ensure_default_roles via
# SessionLocal real — com o MariaDB parado a suíte inteira quebrava (ERROR
# at setup) e cada rodada escrevia no banco de produção como efeito
# colateral. Aqui a fonte de dados do bootstrap aponta para o banco de
# TESTE e o bootstrap vira no-op: o estado visível dos testes é idêntico
# (dados vêm exclusivamente dos fixtures — como já era de fato).
#
# Cobertura dupla: `app.main.SessionLocal` é o nome que o lifespan usa;
# `app.database.SessionLocal` cobre importadores tardios dentro de funções
# (padrão existente: templates_env, health_check).
# ============================================================================
import app.main as _app_main  # noqa: E402
import app.database as _app_database  # noqa: E402

_app_main.SessionLocal = TestingSessionLocal
_app_database.SessionLocal = TestingSessionLocal
_app_main.init_db = lambda: None  # create_all é feito pelo fixture db_session
_app_main.ensure_admin_user = lambda *a, **k: None
_app_main.ensure_default_roles = lambda *a, **k: None

TEST_USERNAME = "testuser"
TEST_PASSWORD = "teste@1234"


@pytest.fixture(scope="function")
def db_session():
    """Cria as tabelas no banco de teste antes de cada teste e limpa ao final"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _scheduler_session_isolation(db_session, monkeypatch):
    """Feature 021: o agendador lê a configuração efetiva com sessão PRÓPRIA.

    Sem este isolamento, caminhos de teste que tocam scheduler_status/_eff()
    abririam a SessionLocal de PRODUÇÃO (banco real do deploy). Aqui a sessão
    do scheduler é sempre o banco de teste e o snapshot começa limpo por teste.

    A thread real NÃO é iniciada nos testes: o lifespan (TestClient) dispara
    start_scheduler(), cujo primeiro tick abre sessão na conexão compartilhada
    (StaticPool) e quebra a transação do fixture. Em 020 a thread era inofensiva
    quando desativada; em 021 ela toca o banco imediatamente. Nenhum teste
    depende da thread — todos exercitam o loop/funções de forma síncrona.
    """
    from sqlalchemy.orm import sessionmaker as _sessionmaker

    import app.services.backup_scheduler as _bs

    SchedulerSM = _sessionmaker(
        autocommit=False, autoflush=False, bind=db_session.get_bind()
    )
    monkeypatch.setattr(_bs, "SessionLocal", SchedulerSM)
    monkeypatch.setattr(_bs, "_current_effective", None)
    monkeypatch.setattr(_bs, "start_scheduler", lambda *a, **k: None)
    monkeypatch.setattr(_bs, "stop_scheduler", lambda *a, **k: None)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_test_user():
    """Cria o usuário de teste usado pelo fixture `client`."""
    db = TestingSessionLocal()
    try:
        return create_user(
            db,
            username=TEST_USERNAME,
            password=TEST_PASSWORD,
            full_name="Usuário de Teste",
            is_admin=True,
        )
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente autenticado (sessão válida) para os testes que exercitam o fluxo normal."""
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        _create_test_user()
        login = test_client.post(
            "/api/v1/auth/login",
            data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        )
        assert login.status_code == 200, login.text
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def unauth_client(db_session):
    """Cliente SEM sessão, para testar bloqueio de acesso não autenticado."""
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()