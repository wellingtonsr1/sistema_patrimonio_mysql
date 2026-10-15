#!/usr/bin/env python3
"""Compõe a cena do vídeo de DEMONSTRAÇÃO (sem instalação) do navegador.

Reusa a geometria e as cores do browser_scene.py (paridade visual com os
demais vídeos) e acrescenta o que a cena de demonstração precisa:

- bloco "troca": crossfade curto entre telas (ex.: login passando de vazio
  a preenchido), sem barra de carregamento;
- bloco "filma": sequência REAL de frames de uma interação gravada com
  Playwright (demo_interactions.py), 15 fps, encaixada na timeline;
- chips de rótulo por tela (mesmo lower-third do add_labels.py).

Uso: python3 make_demo_scene.py <pasta_shots> <saida.mp4> [host] [bg_hex]
                                [dir_segA] [dir_segB]
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

import browser_scene as bs

W, H, FPS = bs.W, bs.H, bs.FPS
WX0, WY0 = bs.WX0, bs.WY0
VW, VH = bs.VW, bs.VH
TAB_H, ADDR_H, PROG_H = bs.TAB_H, bs.ADDR_H, bs.PROG_H
VY0, WX1, WY1 = bs.VY0, bs.WX1, bs.WY1
CHROME, FIELD, BORDER = bs.CHROME, bs.FIELD, bs.BORDER
FG, GRAY, BLUE, GREEN = bs.FG, bs.GRAY, bs.BLUE, bs.GREEN
F_TAB, F_TAB_B = bs.F_TAB, bs.F_TAB_B
DEFAULT_HOST = bs.DEFAULT_HOST
ease, norm = bs.ease, bs.norm

LOG = bs.LOG.replace("sispat-scene", "sispat-demo-scene")

CHIP_BG = (16, 20, 26, 225)
F_CHIP = ImageFont.truetype(F_TAB_B, 21)
FADE = 0.28


def timeline(host, dir_sega=None, dir_segb=None):
    """Linha do tempo: login -> telas principais + interações reais.

    Os blocos são declarados (duração, spec) e os tempos absolutos são
    acumulados — inserir/durar um bloco não desalinha os demais.
    """
    u = host
    specs = [
        (0.4, ("janela",)),
        (2.0, ("digita", f"https://{u}")),
        (0.4, ("carrega",)),
        (3.5, ("pagina", "01-login", "Entrar | SisPatrimônio Pro",
               f"{u}/login", "Autenticação · login local ou Active Directory")),
        (0.8, ("troca", "02-login-preenchido")),
        (3.2, ("pagina", "02-login-preenchido", "Entrar | SisPatrimônio Pro",
               f"{u}/login", "Acesso · usuário e senha (senhas nunca exibidas)")),
        (0.5, ("carrega",)),
        (7.2, ("pagina", "03-dashboard", "SisPatrimônio - Dashboard",
               f"{u}/", "Dashboard · KPIs do acervo e gráficos")),
        (0.4, ("carrega",)),
        (6.6, ("pagina", "04-assets", "SisPatrimônio - Equipamentos",
               f"{u}/assets",
               "Equipamentos · busca, filtros e tombamento")),
    ]
    if dir_sega:
        n = len(os.listdir(dir_sega))
        specs.append((n / FPS, ("filma", dir_sega, f"{u}/assets",
                                "SisPatrimônio - Equipamentos",
                                "Filtro em ação · digitando a busca e clicando em Filtrar")))
    specs += [
        (0.4, ("carrega",)),
        (7.6, ("pagina", "05-asset-detalhe",
               "SisPatrimônio - IPMJP1247 - Impressora | SisPatrimônio Pro",
               f"{u}/assets/300",
               "Ficha do bem · dados, QR Code e linha do tempo do fluxo")),
        (0.4, ("carrega",)),
        (6.6, ("pagina", "06-movements",
               "SisPatrimônio - Histórico de Movimentações", f"{u}/movements",
               "Movimentações · histórico auditável origem → destino")),
    ]
    if dir_segb:
        n = len(os.listdir(dir_segb))
        specs.append((n / FPS, ("filma", dir_segb, f"{u}/reports/movements",
                                "SisPatrimônio - Relatório de Auditoria de Movimentações",
                                "Relatório · Trilha de Auditoria e Fluxo, com exportação")))
    specs += [
        (0.4, ("carrega",)),
        (6.6, ("pagina", "07-inventarios",
               "SisPatrimônio - Inventários | SisPatrimônio Pro",
               f"{u}/inventarios",
               "Inventário · conferência física com QR Code")),
        (0.4, ("carrega",)),
        (6.6, ("pagina", "08-labels",
               "SisPatrimônio - Etiquetas de Patrimônio", f"{u}/assets/labels",
               "Etiquetas patrimoniais · QR Code em folha A4")),
        (0.4, ("carrega",)),
        (6.6, ("pagina", "09-audit",
               "SisPatrimônio - Auditoria | SisPatrimônio Pro",
               f"{u}/admin/audit",
               "Auditoria · trilha administrativa completa")),
        (0.4, ("carrega",)),
        (6.6, ("pagina", "10-ajuda",
               "SisPatrimônio - Ajuda e Manual | SisPatrimônio Pro",
               f"{u}/ajuda", "Central de ajuda integrada ao sistema")),
        (0.8, ("sai",)),
    ]
    tl, t = [], 0.0
    for dur, spec in specs:
        bloco = (spec[0], t, t + dur) + tuple(spec[1:])
        tl.append(bloco)
        t += dur
    return tl


def estado_em(tl, t):
    for i, blk in enumerate(tl):
        if blk[1] <= t < blk[2]:
            return i, (t - blk[1]) / (blk[2] - blk[1])
    return len(tl) - 1, 1.0


def pagina_ate(tl, idx):
    atual = None
    for blk in tl[:idx]:
        if blk[0] in ("pagina", "troca"):
            atual = blk[3]
    return atual


def chip(img, texto, alpha):
    """Lower-third no canto inferior esquerdo (estilo add_labels.py)."""
    if alpha <= 0:
        return img
    a = int(255 * alpha)
    x0, y0, h = 40, H - 98, 54
    d = ImageDraw.Draw(img)
    w = 6 + 22 + d.textlength(texto, font=F_CHIP) + 26
    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(camada)
    cd.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=12,
                         fill=CHIP_BG[:3] + (int(CHIP_BG[3] * alpha),))
    cd.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=12,
                         outline=GREEN + (int(200 * alpha),), width=2)
    img = Image.alpha_composite(img.convert("RGBA"), camada).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle([x0 + 2, y0 + 2, x0 + 8, y0 + h - 2], fill=GREEN + (a,))
    d.text((x0 + 22, y0 + h / 2), texto, font=F_CHIP,
           fill=(240, 246, 252, a), anchor="lm")
    return img


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    shots_dir, out = sys.argv[1], sys.argv[2]
    host = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else DEFAULT_HOST
    bg = (13, 17, 23)
    if len(sys.argv) > 4 and sys.argv[4]:
        h = sys.argv[4].lstrip("#")
        bg = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    dir_sega = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None
    dir_segb = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else None

    tl = timeline(host, dir_sega, dir_segb)
    dur = tl[-1][2]
    titulos = {b[3]: b[4] for b in tl if b[0] == "pagina"}

    f_tab = ImageFont.truetype(F_TAB, 15)
    f_url = ImageFont.truetype(F_TAB, 17)
    f_fav = ImageFont.truetype(F_TAB_B, 11)

    imgs = {}
    for bloco in tl:
        if bloco[0] == "pagina":
            nome = bloco[3]
        elif bloco[0] == "troca":
            nome = bloco[3]
        else:
            continue
        if nome in imgs:
            continue
        im = Image.open(os.path.join(shots_dir, nome + ".png")).convert("RGB")
        if im.size != (VW, VH):
            im = im.resize((VW, VH), Image.LANCZOS)
        imgs[nome] = im

    filmes = {}
    for bloco in tl:
        if bloco[0] == "filma":
            d = bloco[3]
            filmes[d] = [os.path.join(d, f)
                         for f in sorted(os.listdir(d))]

    exe = subprocess.check_output(
        [sys.executable, "-c",
         "import imageio_ffmpeg as f;print(f.get_ffmpeg_exe())"],
        text=True).strip()
    proc = subprocess.Popen(
        [exe, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-preset", "medium", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=open(LOG, "w"))

    for fi in range(int(dur * FPS)):
        t = fi / FPS
        idx, p = estado_em(tl, t)
        blk = tl[idx]
        img = Image.new("RGB", (W, H), bg)

        url_txt, tab_txt, caret = "", "Nova aba", False
        carregando, progresso = False, 0.0
        page_key, veil, rotulo = None, 0.0, None
        troca_de, troca_para = None, None
        filme, filme_i = None, 0

        if blk[0] == "digita":
            alvo = blk[3]
            n = int(ease(p) * len(alvo) + 1e-9)
            url_txt, caret = alvo[:max(0, n)], True
            ant = pagina_ate(tl, idx)
            tab_txt = titulos.get(ant, "Nova aba")
            page_key = ant
        elif blk[0] == "carrega":
            seg = tl[idx + 1] if idx + 1 < len(tl) else None
            url_txt = seg[5] if (seg and seg[0] == "pagina") else ""
            tab_txt = "Carregando…"
            carregando, progresso = True, p
            page_key = pagina_ate(tl, idx)
            veil = 0.85 * ease(p)
        elif blk[0] == "pagina":
            url_txt, tab_txt, page_key = blk[5], blk[4], blk[3]
            rotulo = blk[6]
            veil = 0.85 * (1 - ease(norm(t, blk[1], blk[1] + 0.30)))
        elif blk[0] == "troca":
            troca_de, troca_para = pagina_ate(tl, idx), blk[3]
            seg = tl[idx + 1]
            url_txt, tab_txt, page_key = seg[5], seg[4], seg[3]
            rotulo = seg[6]
        elif blk[0] == "filma":
            filme = filmes[blk[3]]
            filme_i = min(int((t - blk[1]) * FPS), len(filme) - 1)
            url_txt, tab_txt, rotulo = blk[4], blk[5], blk[6]
        elif blk[0] in ("janela", "sai"):
            page_key = None

        # ---------- viewport ----------
        vp = Image.new("RGB", (VW, VH), (245, 246, 248))
        if filme is not None:
            vp = Image.open(filme[filme_i]).convert("RGB")
            if vp.size != (VW, VH):
                vp = vp.resize((VW, VH), Image.LANCZOS)
        elif blk[0] == "troca":
            vp = imgs[troca_de].copy()
            vp = Image.blend(vp, imgs[troca_para], ease(p))
        elif page_key:
            vp = imgs[page_key].copy()
        if veil > 0:
            branco = Image.new("RGB", (VW, VH), (255, 255, 255))
            vp = Image.blend(vp, branco, min(1.0, veil))
        img.paste(vp, (WX0, VY0))

        d = ImageDraw.Draw(img)

        # ---------- chrome do navegador ----------
        d.rectangle([WX0, WY0, WX1, WY0 + TAB_H + ADDR_H + PROG_H], fill=CHROME)
        d.rectangle([WX0, WY0, WX1, WY1], outline=BORDER, width=1)
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            x = 46 + i * 20
            cy = WY0 + TAB_H // 2
            d.ellipse([x - 6, cy - 6, x + 6, cy + 6], fill=c)
        tx0, tx1, ty0, ty1 = 116, 520, WY0 + 4, WY0 + TAB_H - 2
        d.rounded_rectangle([tx0, ty0, tx1, ty1], radius=8, fill=FIELD)
        fx0, fy0 = tx0 + 12, (ty0 + ty1) // 2 - 8
        d.rounded_rectangle([fx0, fy0, fx0 + 16, fy0 + 16], radius=4, fill=BLUE)
        d.text((fx0 + 3.4, fy0 + 2), "S", font=f_fav, fill=(255, 255, 255))
        titulo = tab_txt
        while d.textlength(titulo, font=f_tab) > (tx1 - tx0 - 44) and titulo:
            titulo = titulo[:-2] + "…"
        d.text((tx0 + 38, (ty0 + ty1) // 2 - 10), titulo, font=f_tab, fill=FG)
        fy0, fy1 = WY0 + TAB_H + 7, WY0 + TAB_H + ADDR_H - 7
        d.rounded_rectangle([WX0 + 10, fy0, WX1 - 10, fy1], radius=9, fill=FIELD)
        cx, cy = WX0 + 30, (fy0 + fy1) // 2
        d.rounded_rectangle([cx - 6, cy - 2, cx + 6, cy + 9], radius=2, fill=GREEN)
        d.arc([cx - 5, cy - 11, cx + 5, cy - 1], 180, 360, fill=GREEN, width=3)
        if url_txt:
            d.text((WX0 + 46, (fy0 + fy1) // 2 - 11), url_txt,
                   font=f_url, fill=FG)
        elif blk[0] == "janela":
            d.text((WX0 + 46, (fy0 + fy1) // 2 - 11),
                   "Pesquisar ou digitar endereço", font=f_url, fill=GRAY)
        if caret:
            bx = WX0 + 46 + d.textlength(url_txt, font=f_url) + 2
            if int(t * 3) % 2 == 0:
                d.rectangle([bx, fy0 + 5, bx + 2, fy1 - 5], fill=FG)
        rx, ry = WX1 - 32, (fy0 + fy1) // 2
        if carregando:
            a0 = (t * 420) % 360
            d.arc([rx - 9, ry - 9, rx + 9, ry + 9], a0, a0 + 110, fill=BLUE, width=3)
        else:
            d.arc([rx - 9, ry - 9, rx + 9, ry + 9], 40, 320, fill=GRAY, width=3)
            d.polygon([(rx + 7, ry - 8), (rx + 12, ry - 3), (rx + 4, ry - 3)],
                      fill=GRAY)
        if carregando:
            w = VW * min(1.0, 0.08 + 0.92 * (progresso ** 0.45))
            d.rectangle([WX0, WY0 + TAB_H + ADDR_H, WX0 + w,
                         WY0 + TAB_H + ADDR_H + PROG_H], fill=BLUE)

        # ---------- chip de rótulo ----------
        if rotulo:
            a_in = min(1.0, (t - blk[1]) / FADE)
            a_out = min(1.0, (blk[2] - t) / FADE)
            img = chip(img, rotulo, max(0.0, min(a_in, a_out)))

        # ---------- transições de abertura/fechamento ----------
        if blk[0] == "janela":
            al = ease(p)
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.rectangle([0, 0, W, H], fill=bg + (int(255 * (1 - al)),))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            if al < 1:
                base = Image.new("RGB", (W, H), bg)
                base.paste(img, (0, int((1 - al) * 26)))
                img = base
        elif blk[0] == "sai":
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.rectangle([0, 0, W, H], fill=bg + (int(255 * ease(p)),))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        print(open(LOG).read()[-2000:], file=sys.stderr)
        sys.exit(1)
    print(f"cena de demonstração: {out} | {int(dur * FPS)} frames | "
          f"{W}x{H} | {dur:.2f}s @ {FPS}fps")


if __name__ == "__main__":
    main()
