#!/usr/bin/env python3
"""Explora o SisPatrimônio Pro no browser e salva os screenshots crus.

Uso: python3 browser_shots.py [dir_destino] [base_url]
"""
import sys

from playwright.sync_api import sync_playwright

BASE = "https://10.20.30.10:8000"
VIEW = {"width": 1400, "height": 760}


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else "/tmp/shots"
    base = sys.argv[2] if len(sys.argv) > 2 else BASE
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEW, ignore_https_errors=True,
                                  device_scale_factor=1)
        page = ctx.new_page()

        page.goto(base + "/", wait_until="networkidle")
        print("GET / ->", page.url, "| title:", page.title())
        page.screenshot(path=f"{dest}/01-login.png")

        page.goto(base + "/setup", wait_until="networkidle")
        print("GET /setup ->", page.url, "| title:", page.title())
        page.screenshot(path=f"{dest}/02-setup.png")

        # cria o primeiro administrador (fluxo real de primeiro acesso)
        page.fill("#full_name", "Administrador")
        page.fill("#username", "admin")
        page.fill("#email", "admin@sispatrimonio.local")
        page.fill("#password", "Admin.Demo.2026")
        page.fill("#confirm_password", "Admin.Demo.2026")
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        print("apos setup ->", page.url, "| title:", page.title())
        page.screenshot(path=f"{dest}/03-apos-setup.png")

        # se caiu na tela de login, entra
        if "/login" in page.url or "login" in page.url.lower():
            try:
                page.fill("#username", "admin")
                page.fill("#password", "Admin.Demo.2026")
                page.click("button[type=submit]")
                page.wait_for_load_state("networkidle")
            except Exception as e:  # noqa: BLE001
                print("login auto falhou:", e)
        print("apos login ->", page.url, "| title:", page.title())
        page.screenshot(path=f"{dest}/04-pos-login.png")

        # tenta a home/logado
        page.goto(base + "/", wait_until="networkidle")
        print("GET / logado ->", page.url, "| title:", page.title())
        page.screenshot(path=f"{dest}/05-home.png")

        page.goto(base + "/docs", wait_until="networkidle")
        print("GET /docs ->", page.url, "| title:", page.title())
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{dest}/06-docs.png")

        browser.close()


if __name__ == "__main__":
    main()
