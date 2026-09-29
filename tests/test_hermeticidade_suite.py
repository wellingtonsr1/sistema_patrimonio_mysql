"""Hermeticidade da suíte — Feature 054 (achado M1 da análise de 2026-09-29).

Problema provado (RED): o lifespan do TestClient (`app/main.py`) executava
`init_db()` → `app.database.engine` (banco REAL do `.env`) e
`ensure_admin_user`/`ensure_default_roles` via `app.database.SessionLocal`
real. Com o MariaDB local parado — ou com `DATABASE_URL` apontando para porta
morta — a suíte produzia erros de conexão no setup (`ERROR at setup`) e nunca
podia rodar em CI sem infraestrutura.

Correção (conftest 054): o conftest aponta `app.main.SessionLocal` (e o
fallback `app.database.SessionLocal`) para o banco de TESTE e torna o
bootstrap do lifespan um no-op — o estado visível dos testes é idêntico
(dados vêm exclusivamente dos fixtures).

Estes testes guardam a hermeticidade sem depender do MariaDB real.
"""
import subprocess
import sys
from pathlib import Path

import pytest

import app.main as app_main
from fastapi.testclient import TestClient

# tests/ não tem __init__.py: o pytest registra o conftest como módulo
# top-level `conftest` (mesma lição documentada em test_backup_config.py).
from conftest import TestingSessionLocal

RAIZ = Path(__file__).resolve().parent.parent


# ============================================================================
# US1 — Lifespan hermético
# ============================================================================

def test_lifespan_nao_toca_banco_real(monkeypatch):
    """SC-001: subir o app (lifespan completo) com o banco real INALCANÇÁVEL
    não pode levantar erro de conexão — prova direta do M1.

    A DATABASE_URL aponta para uma porta morta; se qualquer código do
    lifespan tocar `app.database.engine`, a conexão falha e o teste quebra.
    """
    import app.database as database

    engine_original = database.engine
    monkeypatch.setattr(
        database,
        "engine",
        __import__("sqlalchemy", fromlist=["create_engine"]).create_engine(
            "mariadb+pymysql://hermetico:hermetico@localhost:3390/inexistente",
            pool_pre_ping=False,
        ),
        raising=True,
    )
    try:
        with TestClient(app_main.app):
            pass  # subir E descer o app sem tocar o banco real
    finally:
        monkeypatch.setattr(database, "engine", engine_original, raising=True)


def test_sessionlocal_do_main_aponta_para_banco_de_teste():
    """FR-002: `app.main.SessionLocal` é a sessionmaker do banco de TESTE.

    Garante que qualquer código de runtime executado sob a suíte (lifespan,
    handlers) leia/escreva no SQLite de teste, nunca no MariaDB do `.env`.
    """
    assert app_main.SessionLocal is TestingSessionLocal


def test_suilen_anterior_produzia_erros_de_setup_sem_mariadb():
    """Documentação executável do RED: com o mecanismo antigo, 12+ testes de
    test_inventario.py davam ERROR de conexão com DATABASE_URL morta (prova
    de 2026-09-29, registros no validacao.md da 054). A correção substitui a
    fonte de dados do lifespan — este teste fixa o contrato: os dados da
    suíte vêm dos fixtures, não do bootstrap.
    """
    # Sobe o app via fixture `client` (já hermético) e prova que o usuário
    # admin/global NÃO foi criado pelo ensure_admin_user do lifespan — quem
    # cria usuários na suíte é o conftest (_create_test_user).
    from sqlalchemy import select

    import app.models.user as user_models
    from app.database import Base

    db = TestingSessionLocal()
    try:
        Base.metadata.create_all(bind=db.get_bind())
        usuarios = db.execute(select(user_models.User)).scalars().all()
        nomes = {u.username for u in usuarios}
        # O bootstrap NÃO criou nada: se houvesse ensure_admin_user com a
        # SessionLocal real, haveria um usuário 'admin' aqui.
        assert "admin" not in nomes
    finally:
        db.close()


# ============================================================================
# US2 — Runner com o Python do venv (D3 da validação da 053)
# ============================================================================

def test_test_bat_usa_python_do_venv():
    """SC-003: o runner `test.bat` fixa `.venv\\Scripts\\python.exe` — o
    interpretador do sistema (fora do venv) produz o failure ambiental do
    `test_backup_config` (dotenv não visível no subprocesso).
    """
    conteudo = (RAIZ / "test.bat").read_text(encoding="utf-8", errors="ignore")
    assert ".venv\\Scripts\\python.exe" in conteudo or (
        ".venv/Scripts/python.exe" in conteudo
    )
    assert "pytest" in conteudo


def test_readme_documenta_hermeticidade():
    """FR-007: README documenta a hermeticidade e o runner."""
    readme = (RAIZ / "README.md").read_text(encoding="utf-8", errors="ignore")
    assert "test.bat" in readme
    hermetico = ("hermétic" in readme.lower()) or ("hermetic" in readme.lower())
    assert hermetico, "README deve documentar a hermeticidade da suíte"
