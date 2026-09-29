"""PWA instalável de qualquer tela — Feature 057.

Causa do "não é possível instalar o app" (diagnóstico 2026-09-29):
a página de login é template separado e não declarava o manifest
(`<link rel="manifest">`), e o Service Worker só registrava em telas de
inventário — partindo do login, o Chrome não encontra os pré-requisitos
de instalabilidade (manifest na página + página sob controle do SW).

Guardas estruturais (padrão 053/056): leitura dos templates, sem banco.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOGIN = RAIZ / "app" / "web" / "templates" / "login.html"
BASE = RAIZ / "app" / "web" / "templates" / "base.html"


def test_login_declara_manifest():
    """SC-001: o login declara o manifest — sem isso o Chrome recusa a
    instalação partindo da tela onde o usuário naturalmente tenta."""
    conteudo = LOGIN.read_text(encoding="utf-8", errors="ignore")
    assert 'rel="manifest"' in conteudo
    assert "/static/manifest.webmanifest" in conteudo


def test_base_registra_sw_incondicionalmente():
    """SC-002: o registro do SW não depende mais de `active_tab == 'inventarios'`
    — qualquer página estendendo base.html é instalável/gerenciada pelo SW.
    (FR-036 da 033 preservado: o SW é network-only fora da allowlist.)"""
    conteudo = BASE.read_text(encoding="utf-8", errors="ignore")
    assert "serviceWorker.register('/sw.js')" in conteudo
    # A condição antiga NÃO pode mais existir entre o bloco de scripts e o fim
    bloco = conteudo.split("{% block scripts %}", 1)[1]
    assert "active_tab == 'inventarios'" not in bloco, (
        "O registro do SW deve ser incondicional (feature 057)"
    )
