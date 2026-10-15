#!/usr/bin/env python3
"""Grava screenshots REAIS do SisPatrimônio Pro rodando localmente.

Usado pelo vídeo de demonstração (sem instalação): loga no sistema e percorre
as telas principais, salvando screenshots crus 1400x760 que a cena do
navegador consome.

Uso: python3 demo_shots.py <dir_destino> <base_url> <usuario> <senha>
"""
import sys

from playwright.sync_api import sync_playwright

VIEW = {"width": 1400, "height": 760}


def main():
    dest, base, user, pw = sys.argv[1:5]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEW, ignore_https_errors=True,
                                  device_scale_factor=1)
        page = ctx.new_page()

        # ---- login (tela vazia -> preenchida) --------------------------------
        page.goto(base + "/login", wait_until="networkidle")
        print("GET /login ->", page.url, "|", page.title())
        page.screenshot(path=f"{dest}/01-login.png")
        page.fill("#username", user)
        page.fill("#password", pw)
        page.screenshot(path=f"{dest}/02-login-preenchido.png")
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        print("apos login ->", page.url, "|", page.title())
        page.wait_for_timeout(600)
        page.screenshot(path=f"{dest}/03-dashboard.png")

        # ---- equipamentos (lista) --------------------------------------------
        page.goto(base + "/assets", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{dest}/04-assets.png")

        # ---- ficha de um bem (linha do tempo do fluxo) -------------------------
        link = page.query_selector("table a[href^='/assets/']")
        if link:
            link.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
            print("ficha ->", page.url)
            page.screenshot(path=f"{dest}/05-asset-detalhe.png")
        else:
            page.goto(base + "/assets", wait_until="networkidle")
            page.screenshot(path=f"{dest}/05-asset-detalhe.png")

        # ---- movimentações ------------------------------------------------------
        page.goto(base + "/movements", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{dest}/06-movements.png")

        # ---- inventário ----------------------------------------------------------
        page.goto(base + "/inventarios", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{dest}/07-inventarios.png")

        # ---- etiquetas QR ----------------------------------------------------------
        page.goto(base + "/assets/labels", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{dest}/08-labels.png")

        # ---- administração → auditoria --------------------------------------------
        page.goto(base + "/admin/audit", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{dest}/09-audit.png")

        # ---- central de ajuda --------------------------------------------------------
        page.goto(base + "/ajuda", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{dest}/10-ajuda.png")

        browser.close()
    print("screenshots em", dest)


if __name__ == "__main__":
    main()
