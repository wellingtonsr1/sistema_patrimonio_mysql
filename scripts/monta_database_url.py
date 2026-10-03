"""Monta a DATABASE_URL com percent-encoding programático — feature 061 (T032, FR-010).

FONTE ÚNICA de montagem da URL de conexão: usada pelos instaladores nativos
(install.sh e install.ps1). Nenhum outro ponto monta a URL manualmente —
corrige a duplicação apontada no diagnóstico (lista-arquivos.md §Banco, B-1/B-3).

Entrada exclusivamente por VARIÁVEIS DE AMBIENTE (nunca argv — SR-001: a senha
não pode aparecer em `ps aux`/`/proc/<pid>/cmdline` nem em logs):

- SP_DBSCHEME  scheme do SQLAlchemy: 'mariadb+pymysql' (MariaDB) ou
               'mysql+pymysql' (MySQL Oracle) — FR-009, nada além disso.
- SP_DBUSER    usuário do banco (obrigatório)
- SP_DBPASS    senha do banco (pode ser vazia)
- SP_DBHOST    host (obrigatório)
- SP_DBPORT    porta (obrigatória)
- SP_DBNAME    nome do banco (obrigatório)

Saída: a URL pronta na stdout (capturada pelo chamador — NUNCA impressa em
log pelo instalador, pois contém a senha).

`quote(..., safe='')` e NÃO quote_plus: espaço vira '%20' (quote_plus usaria
'+' — que o parse de URL do SQLAlchemy NÃO decodifica como espaço, corrompendo
a senha e causando Access denied); '@' → %40, '#' → %23 etc. ficam corretos.

Stdlib pura (sem dependências): roda com o python3 do sistema no Linux e com
o venv no Windows — a montagem acontece depois do ensure_venv, mas o script
não precisa de nada além da stdlib.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import quote

SCHEMES_PERMITIDOS = ("mariadb+pymysql", "mysql+pymysql")


def monta_database_url(
    scheme: str, user: str, password: str, host: str, port: str, database: str
) -> str:
    """Monta a URL com percent-encoding de usuário e senha (safe='')."""
    if scheme not in SCHEMES_PERMITIDOS:
        raise SystemExit(
            f"ERRO: scheme nao suportado: '{scheme}' "
            f"(use {' ou '.join(SCHEMES_PERMITIDOS)})"
        )
    if not user:
        raise SystemExit("ERRO: SP_DBUSER ausente/vazio.")
    if not host:
        raise SystemExit("ERRO: SP_DBHOST ausente/vazio.")
    if not port:
        raise SystemExit("ERRO: SP_DBPORT ausente/vazio.")
    if not database:
        raise SystemExit("ERRO: SP_DBNAME ausente/vazio.")
    return (
        f"{scheme}://{quote(user, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/{database}"
    )


def main() -> None:
    print(
        monta_database_url(
            os.environ.get("SP_DBSCHEME", ""),
            os.environ.get("SP_DBUSER", ""),
            os.environ.get("SP_DBPASS", ""),
            os.environ.get("SP_DBHOST", ""),
            os.environ.get("SP_DBPORT", ""),
            os.environ.get("SP_DBNAME", ""),
        )
    )


if __name__ == "__main__":
    sys.exit(main())
