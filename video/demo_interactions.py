#!/usr/bin/env python3
"""Grava VÍDEO das interações reais do SisPatrimônio Pro (demonstração).

Duas gravações separadas (contexto/auth próprios), no viewport 1400x760 dos
demais screenshots:

- segA: lista de equipamentos -> digitar busca -> clicar em Filtrar;
- segB: sidebar -> Relatórios -> Movimentações (trilha de auditoria) ->
  rolagem pela tabela.

O vídeo webm sai em <dir>/segA/page.webm e <dir>/segB/page.webm; a extração
de frames e o corte até o estado estável são feitos por make_demo_scene.py.

Uso: python3 demo_interactions.py <dir_base> <base_url> <usuario> <senha> [segA|segB]
"""
import os
import sys

from playwright.sync_api import sync_playwright

VIEW = {"width": 1400, "height": 760}


def contexto(browser, base, user, pw, gravar_dir=None):
    kwargs = dict(viewport=VIEW, ignore_https_errors=True, device_scale_factor=1)
    if gravar_dir:
        kwargs.update(record_video_dir=gravar_dir,
                      record_video_size=VIEW)
    ctx = browser.new_context(**kwargs)
    pg = ctx.new_page()
    pg.goto(base + "/login", wait_until="networkidle")
    pg.fill("#username", user)
    pg.fill("#password", pw)
    pg.click("button[type=submit]")
    pg.wait_for_load_state("networkidle")
    return ctx, pg


def main():
    base_dir, base, user, pw = sys.argv[1:5]
    apenas = sys.argv[5] if len(sys.argv) > 5 else ""
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---- sessão para autenticar; gravações reusam o estado ----
        ctx_auth, _ = contexto(browser, base, user, pw)
        state = ctx_auth.storage_state()

        def nova_ctx(nome):
            ctx = browser.new_context(
                viewport=VIEW, ignore_https_errors=True, device_scale_factor=1,
                storage_state=state,
                record_video_dir=os.path.join(base_dir, nome),
                record_video_size=VIEW)
            return ctx, ctx.new_page()

        # ---- segA: busca + Filtrar na lista de equipamentos ----
        if apenas != "segB":
            ctx, pg = nova_ctx("segA")
            pg.goto(base + "/assets", wait_until="networkidle")
            pg.wait_for_timeout(1000)
            pg.click("input[name='search']")
            pg.type("input[name='search']", "nobreak", delay=95)
            pg.wait_for_timeout(700)
            pg.click("form.assets-filters button[type=submit]")
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(2000)
            print("segA fim | url:", pg.url, "| titulo:", pg.title())
            ctx.close()   # salva o webm

        # ---- segB: Exportar CSV -> Trilha de Auditoria + rolagem ----
        if apenas != "segA":
            ctx, pg = nova_ctx("segB")
            pg.goto(base + "/movements", wait_until="networkidle")
            pg.wait_for_timeout(1200)
            # botao visivel "Exportar CSV" da tela de movimentacoes leva ao
            # relatorio /reports/movements (os itens "Trilha de Auditoria"
            # sao de dropdowns fechados e ficariam invisiveis)
            pg.click("a.btn-ghost[href='/reports/movements']")
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(1600)
            for _ in range(6):          # rolagem suave pela tabela
                pg.mouse.wheel(0, 90)
                pg.wait_for_timeout(160)
            pg.wait_for_timeout(1800)
            print("segB fim | url:", pg.url, "| titulo:", pg.title())
            ctx.close()

        ctx_auth.close()
        browser.close()
    print("gravacoes em", base_dir)


if __name__ == "__main__":
    main()
