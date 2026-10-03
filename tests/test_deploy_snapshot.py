"""Contrato do snapshot de produção — Feature 061, US4/T028 (contrato C1).

deploy.sh (Linux) e deploy.bat (Windows) publicam snapshots EQUIVALENTES para
a mesma dev — tudo que a produção precisa e nada indevido (SC-007):

- (a) keep-list de diretórios idêntica nos dois scripts e entre os filtros
      de publicar e rollback de cada script (D-1: hoje o .sh apagaria
      scripts/ e migrations/ do PRO — degradaria a produção);
- (b) keep-list de arquivos idêntica idem (SPEC-KIT-SISTEMA-ATUAL.md fora);
- (c) line endings determinísticos: git archive com core.autocrlf=false e
      core.eol=lf nos DOIS pontos de cada script (publicar + rollback);
- (d) nada indevido nos keep-lists (.env, specs/, tests/, .venv, backups…)
      e .gitignore da dev cobrindo data/ssl/ e .env (T018);
- (e) essenciais presentes: nos keep-lists E na dev real (app/, run.py,
      requirements.txt, README.md, scripts/gera_cert_dev.py, migrations/);
- (f) guard D-2: nenhum residual (*~, *.un~, *-old) rastreado na dev e o
      guard de aborta-com-lista presente nos dois scripts.

Estrutural (Princípio VIII): analisa o TEXTO dos scripts e a árvore rastreada
da dev — nunca publica nada, nunca toca produção.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_SH = PROJECT_ROOT / "deploy.sh"
DEPLOY_BAT = PROJECT_ROOT / "deploy.bat"
GITIGNORE = PROJECT_ROOT / ".gitignore"

# Whitelist canônica aprovada (lista-arquivos.md §Deploy / DE-1, DE-2)
DIRS_ESPERADOS = {"app", "data", "docs", "scripts", "migrations"}
ARQUIVOS_ESPERADOS = {
    ".gitignore",
    "README.md",
    "requirements.txt",
    "run.py",
    "seed_demo.py",
    "sistema_patrimonio.png",
}
PROIBIDOS = {".env", ".env.example", "specs", "tests", ".venv", "SPEC-KIT-SISTEMA-ATUAL.md"}

RESIDUAL_RE = re.compile(r"(~$|\.un~$|-old$)")


# ---------------------------------------------------------------------------
# (a)/(b) keep-lists dos dois scripts, publicar e rollback
# ---------------------------------------------------------------------------

def _blocos_sh(fonte: str) -> list[set[str]]:
    """Keep-lists do deploy.sh: um bloco por comando `find "$TMPDIR"`."""
    blocos = []
    for trecho in fonte.split('find "$TMPDIR"')[1:]:
        corpo = trecho.split("-exec rm -rf {} +")[0]
        nomes = set(re.findall(r"! -name (\S+)", corpo))
        if nomes:
            blocos.append(nomes)
    return blocos


def _blocos_bat(fonte: str) -> list[set[str]]:
    """Keep-lists do deploy.bat: para cada filtro, dirs (rmdir) + arquivos (del).

    Em cada seção o bloco de diretórios (`rmdir /s /q "%%D"`) é seguido pelo
    de arquivos (`del /q "%%F"`) — pareados pela ORDEM de aparição.
    """
    dirs_em_ordem = [
        set(re.findall(r'"%%~nxD"=="([^"]+)"', linha))
        for linha in fonte.splitlines()
        if 'rmdir /s /q "%%D"' in linha and '"%%~nxD"==' in linha
    ]
    arqs_em_ordem = [
        set(re.findall(r'"%%~nxF"=="([^"]+)"', linha))
        for linha in fonte.splitlines()
        if 'del /q "%%F"' in linha and '"%%~nxF"==' in linha
    ]
    return [d | a for d, a in zip(dirs_em_ordem, arqs_em_ordem)]


def test_contrato_scripts_de_deploy_existem():
    assert DEPLOY_SH.is_file(), "deploy.sh ausente na raiz da dev"
    assert DEPLOY_BAT.is_file(), "deploy.bat ausente na raiz da dev"


def test_contrato_dois_blocos_por_script_publicar_e_rollback():
    sh = _blocos_sh(DEPLOY_SH.read_text(encoding="utf-8"))
    bat = _blocos_bat(DEPLOY_BAT.read_text(encoding="utf-8"))
    assert len(sh) == 2, f"deploy.sh deve ter 2 filtros (publicar+rollback); há {len(sh)}"
    assert len(bat) == 2, f"deploy.bat deve ter 2 filtros (publicar+rollback); há {len(bat)}"
    assert sh[0] == sh[1], "publicar e rollback divergem no deploy.sh"
    assert bat[0] == bat[1], "publicar e rollback divergem no deploy.bat"


def test_contrato_keep_list_sh_equivalente_ao_bat():
    sh = _blocos_sh(DEPLOY_SH.read_text(encoding="utf-8"))
    bat = _blocos_bat(DEPLOY_BAT.read_text(encoding="utf-8"))
    assert sh[0] == bat[0], (
        f"whitelists divergentes (D-1): sh={sorted(sh[0])} bat={sorted(bat[0])}"
    )


def test_contrato_keep_list_conteudo_canonico():
    sh = _blocos_sh(DEPLOY_SH.read_text(encoding="utf-8"))[0]
    # separa dirs de arquivos no .sh via keep-list canônica
    assert DIRS_ESPERADOS | ARQUIVOS_ESPERADOS == sh, (
        f"keep-list inesperada: extras={sorted(sh - (DIRS_ESPERADOS | ARQUIVOS_ESPERADOS))}, "
        f"ausentes={sorted((DIRS_ESPERADOS | ARQUIVOS_ESPERADOS) - sh)}"
    )
    bat = _blocos_bat(DEPLOY_BAT.read_text(encoding="utf-8"))[0]
    assert bat == sh
    for proibido in PROIBIDOS:
        assert proibido not in sh, f"'{proibido}' não pode estar na whitelist do snapshot"


def test_contrato_line_endings_deterministicos():
    for arquivo in (DEPLOY_SH, DEPLOY_BAT):
        fonte = arquivo.read_text(encoding="utf-8")
        n = fonte.count("git -c core.autocrlf=false -c core.eol=lf archive")
        assert n == 2, (
            f"{arquivo.name}: esperados 2 `git archive` com EOL determinístico "
            f"(publicar + rollback); há {n}"
        )


# ---------------------------------------------------------------------------
# (d) nada indevido: .gitignore cobre material sensível (T018)
# ---------------------------------------------------------------------------

def test_contrato_gitignore_cobre_ssl_e_env():
    fonte = GITIGNORE.read_text(encoding="utf-8")
    assert "data/ssl/" in fonte, "data/ssl/ precisa seguir fora do versionamento"
    assert re.search(r"^\.env$", fonte, re.MULTILINE), ".env fora do versionamento"


# ---------------------------------------------------------------------------
# (e) essenciais presentes na dev real
# ---------------------------------------------------------------------------

def test_contrato_essenciais_presentes_na_dev():
    for caminho in (
        "app",
        "app/database.py",
        "run.py",
        "requirements.txt",
        "README.md",
        "scripts/gera_cert_dev.py",  # pré-requisito do contrato C2 (HTTPS no PRO)
        "migrations/env.py",         # versionamento de schema (052)
        "migrations/versions/0002_migracoes_legadas_idempotentes.py",
    ):
        assert (PROJECT_ROOT / caminho).exists(), f"essencial ausente na dev: {caminho}"


# ---------------------------------------------------------------------------
# (f) guard D-2: residuais zerados na origem + guard presente nos scripts
# ---------------------------------------------------------------------------

def test_contrato_dev_sem_residuais_rastreados():
    rastreados = subprocess.run(
        ["git", "ls-files"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    residuais = [r for r in rastreados if RESIDUAL_RE.search(r)]
    assert residuais == [], f"residuais (lixeira de editor) rastreados na dev: {residuais}"


def test_contrato_guard_de_residuais_presente_nos_dois_scripts():
    sh = DEPLOY_SH.read_text(encoding="utf-8")
    bat = DEPLOY_BAT.read_text(encoding="utf-8")
    assert "~$|\\.un~$|-old$" in sh, "deploy.sh sem o guard D-2 de residuais"
    assert '/c:"~$"' in bat and "/c:\"-old$\"" in bat, "deploy.bat sem o guard D-2 de residuais"
