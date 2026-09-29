"""Testes estruturais do Service Worker — Feature 053.

A suíte pytest não executa JavaScript; estes testes leem o arquivo
`app/web/static/js/sw.js` do disco e fazem asserts de estrutura para
guardar invariantes da feature 033 corrigidos pela 053:

1. FR-001 (053): o handler `fetch` chama `event.respondWith` no máximo
   UMA vez por evento — o sub-bloco da navegação offline (`OFFLINE_NAV_RE`)
   retorna imediatamente após o seu `respondWith` (a segunda chamada no
   mesmo evento lança InvalidStateError por spec Fetch).
2. FR-002 (053): `CACHE_VERSION >= inventario-offline-v32` — o bump garante
   que a ativação remova dos dispositivos os caches v31 possivelmente
   corrompidos (mecanismo FR-037 da 033).
3. FR-003 (053): allowlist de precache e regra network-only de `/api/*`
   permanecem intactas (nenhuma mudança além do escopo).
"""
from pathlib import Path

SW_PATH = Path(__file__).resolve().parent.parent / "app" / "web" / "static" / "js" / "sw.js"


def _sw_source() -> str:
    return SW_PATH.read_text(encoding="utf-8")


def _extract_brace_block(source: str, anchor: str) -> str:
    """Extrai o bloco `{...}` que segue `anchor`, balanceando chaves.

    Ignora chaves dentro de strings curtas ('...' ou "...") do próprio SW —
    suficiente para os blocos estruturais do arquivo (sem template literals).
    """
    idx = source.index(anchor)
    start = source.index("{", idx)
    depth = 0
    in_squote = in_dquote = False
    for i in range(start, len(source)):
        ch = source[i]
        if ch == "'" and not in_dquote:
            in_squote = not in_squote
        elif ch == '"' and not in_squote:
            in_dquote = not in_dquote
        elif not in_squote and not in_dquote:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return source[start : i + 1]
    raise AssertionError(f"Bloco de '{anchor}' não fechado no sw.js")


def test_respondwith_unico_na_navegacao_offline():
    """FR-001/SC-001: dentro do bloco de navegação, o sub-bloco OFFLINE_NAV_RE
    termina com `return;` logo após o respondWith — sem queda para o segundo
    respondWith (navegações gerais)."""
    source = _sw_source()
    navigate_block = _extract_brace_block(source, 'event.request.mode === "navigate"')
    offline_block = _extract_brace_block(navigate_block, "OFFLINE_NAV_RE.test(path)")

    # O sub-bloco offline contém exatamente 1 CHAMADA respondWith( ...
    # (contagem com parêntese para não pegar a palavra em comentários).
    assert offline_block.count("respondWith(") == 1, (
        "Sub-bloco OFFLINE_NAV_RE deve conter exatamente 1 respondWith"
    )
    # ...e deve encerrar com return; (senão a execução cai no respondWith
    # das demais navegações — segunda chamada = InvalidStateError).
    tail = offline_block.rsplit("}", 1)[0]  # conteúdo antes do fechamento final
    assert "return;" in tail, (
        "Sub-bloco OFFLINE_NAV_RE deve terminar com 'return;' após o respondWith "
        "(FR-001 da 053 — respondWith é único por evento)"
    )

    # O bloco de navegação como um todo contém 2 CHAMADAS respondWith(
    # (offline + demais navegações), em ramos mutuamente exclusivos garantidos
    # pelo return.
    assert navigate_block.count("respondWith(") == 2, (
        "Bloco de navegação deve manter os 2 respondWith (offline e demais "
        "navegações), agora mutuamente exclusivos"
    )


def test_cache_version_minima_v32():
    """FR-002/SC-002: a versão do cache avançou para v32 (ou além) — caches
    v31 dos dispositivos são removidos na ativação do SW atualizado."""
    source = _sw_source()
    assert 'var CACHE_VERSION = "inventario-offline-v32"' in source


def test_allowlist_precache_intacta():
    """FR-003/SC-004: as 14 entradas da allowlist permanecem."""
    source = _sw_source()
    allowlist = [
        "/static/css/style.css?v=20260924",
        "/static/vendor/css/bootstrap.min.css",
        "/static/vendor/css/bootstrap-icons.css",
        "/static/vendor/css/fonts/bootstrap-icons.woff2",
        "/static/vendor/css/fonts/bootstrap-icons.woff",
        "/static/vendor/js/bootstrap.bundle.min.js",
        "/static/js/inventario_offline.js",
        "/static/js/qr_reader.js",
        "/static/offline-start.html",
        "/static/manifest.webmanifest",
        "/static/icons/pwa-icon-192.png",
        "/static/icons/pwa-icon-512.png",
        "/static/img/Logo_IPMjp_2.png",
        "/static/img/favicon.ico",
    ]
    for url in allowlist:
        assert url in source, f"Allowlist perdeu a entrada {url}"
    # Contagem confinada ao array PRECACHE_URLS (a URL offline-start.html
    # também aparece no fallback de navegação — fora do array).
    precache_block = source.split("var PRECACHE_URLS = [", 1)[1].split("];", 1)[0]
    assert precache_block.count('"/static/') == 14


def test_api_network_only_preservada():
    """FR-036 da 033 preservado: /api/* é network-only (sem cache)."""
    source = _sw_source()
    assert 'if (path.startsWith("/api/")) return;' in source


def test_nenhuma_referencia_a_v31_no_codigo():
    """SC-002: nenhuma referência a inventario-offline-v31 no CÓDIGO runtime
    (app/). Menções em docs/specs são changelog/documentação histórica e não
    executam — o que importaria seria o runtime ainda fixar v31."""
    raiz = Path(__file__).resolve().parent.parent
    offenders = []
    for p in (raiz / "app").rglob("*"):
            if p.is_file() and p.suffix in {".js", ".py", ".md", ".html"}:
                try:
                    if "inventario-offline-v31" in p.read_text(encoding="utf-8", errors="ignore"):
                        offenders.append(str(p.relative_to(raiz)))
                except OSError:
                    pass
    assert not offenders, f"Referências a v31 encontradas em: {offenders}"
