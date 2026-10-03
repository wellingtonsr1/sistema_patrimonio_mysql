"""DATABASE_URL — percent-encoding único e paridade MariaDB×MySQL (Feature 061, US5/T034).

Cobertura (lista-arquivos.md §Banco, B-5):
- (a) Unitários de `scripts/monta_database_url.py` (fonte única de montagem,
      FR-010): senha com caracteres especiais percent-encodada com
      `quote(safe='')` — espaço vira %20 e NUNCA '+' (quote_plus corromperia
      a senha: SQLAlchemy não decodifica '+' como espaço → Access denied);
      scheme restrito a mariadb+pymysql/mysql+pymysql (FR-009); campos
      obrigatórios; senha vazia permitida; round-trip via `sqlalchemy.make_url`.
- (b) Contrato estrutural: o `install.sh` chama o helper e não contém mais
      one-liner de montagem duplicado (a prova do `install.ps1` vive no repo
      de instalação — fora da dev).
- (c) Condicional (padrão `MIGRATIONS_TEST_URL` — Princípio VIII, zero DDL na
      suíte padrão): com `PARIDADE_DB_TEST_URL` (`mariadb+pymysql://` ou
      `mysql+pymysql://`), conecta e valida `SELECT 1` + versão coerente com o
      scheme (SC-006) — prova MariaDB no Linux; MySQL na VM Windows.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import make_url, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HELPER = PROJECT_ROOT / "scripts" / "monta_database_url.py"
INSTALL_SH = PROJECT_ROOT / "install.sh"

# senha deliberadamente hostil: @ : / ? # & = % + espaço aspa
SENHA_HOSTIL = "p@ss w:rd/?#&=%+'~!"


def _helper():
    spec = importlib.util.spec_from_file_location("monta_database_url", HELPER)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# ---------------------------------------------------------------------------
# (a) Unitários do helper
# ---------------------------------------------------------------------------

def test_unit_senha_hostil_fica_totalmente_percent_encoded():
    url = _helper().monta_database_url(
        "mariadb+pymysql", "usuario", SENHA_HOSTIL, "127.0.0.1", "3306", "banco"
    )
    # nenhum caractere especial cru sobrevive fora do scheme e do @host:porta
    credenciais = url.split("://", 1)[1].split("@")[0]
    assert SENHA_HOSTIL not in url
    for bruto in ("@", " ", ":", "/", "?", "#", "&", "=", "%", "+", "'", "!"):
        par = f"{bruto}".replace("%", "%25")  # % é o prefixo do encoding
        if bruto == "%":
            continue  # % sempre aparece COMO prefixo de escape
        assert f"{bruto}" not in credenciais.split(":", 1)[1], (
            f"'{bruto}' cru vazou na senha: {credenciais}"
        )


def test_unit_espaco_vira_p20_e_nunca_mais():
    url = _helper().monta_database_url(
        "mariadb+pymysql", "usuario", "sen ha", "h", "3306", "b"
    )
    assert "%20" in url
    assert "+" not in url.split("://", 1)[1].split("@")[0].split(":", 1)[1]


def test_unit_round_trip_sqlalchemy_componentes_preservados():
    url = _helper().monta_database_url(
        "mysql+pymysql", "u@ser", SENHA_HOSTIL, "db.host", "3307", "banco/db"
    )
    parsed = make_url(url)
    assert parsed.drivername == "mysql+pymysql"
    assert parsed.username == "u@ser"
    assert parsed.password == SENHA_HOSTIL
    assert parsed.host == "db.host"
    assert parsed.port == 3307
    assert parsed.database == "banco/db"


def test_unit_scheme_invalido_rejeitado():
    with pytest.raises(SystemExit):
        _helper().monta_database_url("sqlite://", "u", "s", "h", "1", "b")
    with pytest.raises(SystemExit):
        # mysql:// a seco NÃO é permitido: o driver é sempre pymysql (FR-009)
        _helper().monta_database_url("mysql://", "u", "s", "h", "1", "b")


def test_unit_senha_vazia_permitida_e_campos_obrigatorios():
    h = _helper()
    assert h.monta_database_url("mariadb+pymysql", "u", "", "h", "1", "b").endswith(":@h:1/b")
    for campo, args in (
        ("SP_DBUSER", ("", "s", "h", "1", "b")),
        ("SP_DBHOST", ("u", "s", "", "1", "b")),
        ("SP_DBPORT", ("u", "s", "h", "", "b")),
        ("SP_DBNAME", ("u", "s", "h", "1", "")),
    ):
        with pytest.raises(SystemExit):
            h.monta_database_url("mariadb+pymysql", *args)


def test_unit_cli_por_ambiente_igual_a_funcao():
    env = {
        **os.environ,
        "SP_DBSCHEME": "mariadb+pymysql",
        "SP_DBUSER": "usuario",
        "SP_DBPASS": SENHA_HOSTIL,
        "SP_DBHOST": "127.0.0.1",
        "SP_DBPORT": "3306",
        "SP_DBNAME": "banco",
    }
    resultado = subprocess.run(
        [sys.executable, str(HELPER)], env=env, capture_output=True, text=True, check=True
    )
    assert resultado.stdout.strip() == _helper().monta_database_url(
        "mariadb+pymysql", "usuario", SENHA_HOSTIL, "127.0.0.1", "3306", "banco"
    )


# ---------------------------------------------------------------------------
# (b) Contrato estrutural: fim da duplicação nos instaladores
# ---------------------------------------------------------------------------

def test_contrato_install_sh_chama_helper_sem_one_liner_duplicado():
    fonte = INSTALL_SH.read_text(encoding="utf-8")
    assert "monta_database_url.py" in fonte, "install.sh deve chamar a fonte única"
    assert 'print(f"mariadb+pymysql://' not in fonte, (
        "one-liner de montagem duplicado ainda presente no install.sh"
    )
    # credencial vai por ambiente, nunca por argv
    assert "SP_DBUSER=\"$DB_USER\"" in fonte and "SP_DBPASS=\"$DB_PASSWORD\"" in fonte


# ---------------------------------------------------------------------------
# (c) Condicional — conexão real APENAS por configuração (skip na suíte padrão)
# ---------------------------------------------------------------------------

def test_condicional_conexao_real_por_configuracao():
    """SC-006/FR-027: mesma base de código contra MariaDB (Linux) e MySQL
    (Windows) apenas via env. Sem PARIDADE_DB_TEST_URL: skip explícito."""
    url = os.getenv("PARIDADE_DB_TEST_URL", "")
    if not url:
        pytest.skip("PARIDADE_DB_TEST_URL não definida — validação real em Fase 4 (VM Windows)")
    from sqlalchemy import create_engine

    eh_mariadb = url.startswith("mariadb+pymysql")
    eh_mysql = url.startswith("mysql+pymysql")
    assert eh_mariadb or eh_mysql, "PARIDADE_DB_TEST_URL deve usar mysql+pymysql ou mariadb+pymysql"
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
        versao = str(conn.execute(text("SELECT VERSION()")).scalar())
    assert ("MariaDB" in versao) == eh_mariadb, (
        f"versão/scheme incoerentes: versão='{versao}' scheme={'mariadb' if eh_mariadb else 'mysql'}"
    )
