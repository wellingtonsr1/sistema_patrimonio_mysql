"""Documentação de cenários de rede — Feature 060.

Situação real: usuário desligou a rede da máquina servidora, viu a página
"Você está offline" e concluiu que o sistema "não funciona sem internet".
Confusão entre internet (operadora) × rede local (LAN) × servidor.

- FR-001: offline-start.html traz a dica do https://localhost:8000.
- FR-002/003: artigo na Central de Ajuda, indexável pela pesquisa.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OFFLINE_HTML = PROJECT_ROOT / "app" / "web" / "static" / "offline-start.html"


def test_offline_start_traz_dica_do_localhost():
    conteudo = OFFLINE_HTML.read_text(encoding="utf-8")
    assert "localhost:8000" in conteudo, (
        "offline-start.html deve indicar que no próprio servidor o acesso é "
        "https://localhost:8000 (sem rede alguma)"
    )
    assert "servidor" in conteudo.lower()


def test_ajuda_tem_artigo_de_cenarios_de_rede():
    from app.services import help_service

    article = help_service.get_article("internet-rede-servidor")
    assert article, "artigo 'internet-rede-servidor' ausente na Central de Ajuda"
    texto = (
        article.get("summary", "")
        + " ".join(
            (s.get("body", "") or "") + " ".join(s.get("steps", []) or [])
            for s in article.get("sections", [])
        )
    ).lower()
    for termo in ("internet", "rede local", "servidor", "localhost", "coleta offline"):
        assert termo in texto, f"artigo sem explicar '{termo}'"


def test_artigo_rede_listado_na_categoria_primeiros_passos():
    """O artigo aparece na Central de Ajuda (categoria Primeiros Passos)."""
    from app.services import help_service

    cat = next(c for c in help_service.get_categories() if c["key"] == "primeiros-passos")
    assert "internet-rede-servidor" in cat["article_ids"]


def test_artigo_rede_indexavel_na_pesquisa():
    """FR-003: o artigo está no índice de pesquisa e os termos-chave estão
    pesquisáveis (o índice serializa title+summary+keywords no campo `text`)."""
    from app.services import help_service

    indice = help_service.serialize_search_index()
    ids = {a.get("id") for a in indice}
    assert "internet-rede-servidor" in ids, "artigo fora do índice de pesquisa"
    art = next(a for a in indice if a.get("id") == "internet-rede-servidor")
    texto = ((art.get("text") or "") + " " + (art.get("summary") or "")).lower()
    for termo in ("internet", "offline", "rede", "servidor", "localhost"):
        assert termo in texto, f"termo '{termo}' não pesquisável (FR-003)"
    # e o artigo declara suas keywords (fonte do índice)
    artigo = help_service.get_article("internet-rede-servidor")
    kw = " ".join(artigo.get("keywords", [])).lower()
    assert all(t in kw for t in ("internet", "offline", "rede", "servidor", "localhost"))
