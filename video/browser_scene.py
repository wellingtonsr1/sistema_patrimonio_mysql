#!/usr/bin/env python3
"""Compõe a cena final do vídeo: um navegador acessando o sistema.

Recebe os screenshots crus (1400x760) e desenha o chrome do navegador
(aba, barra de endereço com digitação, cadeado, barra de carregamento)
em volta deles, gerando um MP4 no mesmo padrão dos demais.

Uso: python3 browser_scene.py <pasta_shots> <saida.mp4> [host] [bg_hex]

bg_hex define o fundo/margens (padrão #0d1117 = vídeo Linux; use #012456
para costurar com o terminal PowerShell do vídeo Windows).
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1460, 860
FPS = 15

# geometria da janela (viewport 1400x760 centralizado)
WX0, WY0 = 30, 4
VW, VH = 1400, 760
TAB_H, ADDR_H, PROG_H = 44, 45, 3
VY0 = WY0 + TAB_H + ADDR_H + PROG_H            # 96
WX1, WY1 = WX0 + VW, VY0 + VH                  # 1430, 856

CHROME = (31, 35, 41)       # #1f2329
FIELD = (43, 48, 54)        # #2b3036
BORDER = (48, 54, 61)
FG = (201, 209, 217)
GRAY = (139, 148, 158)
BLUE = (88, 166, 255)
GREEN = (63, 185, 80)
BG = (13, 17, 23)

F_TAB = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F_TAB_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

DEFAULT_HOST = "10.20.30.10:8000"


def monta_timeline(host):
    """Linha do tempo da cena do navegador para um host:porta qualquer."""
    base = f"https://{host}"
    # (tipo, t0, t1, ...)
    return [
        ("janela", 0.0, 0.40),
        ("digita", 0.40, 2.00, base),
        ("carrega", 2.00, 2.40),
        ("pagina", 2.40, 4.60, "01-login", "Entrar | SisPatrimônio Pro",
         f"{host}/login?next=/"),
        ("digita", 4.60, 5.60, f"{host}/setup"),
        ("carrega", 5.60, 6.00),
        ("pagina", 6.00, 8.60, "02-setup",
         "Configuração Inicial | SisPatrimônio Pro", f"{host}/setup"),
        ("carrega", 8.60, 9.00),
        ("pagina", 9.00, 10.20, "03-apos-setup", "Entrar | SisPatrimônio Pro",
         f"{host}/login"),
        ("carrega", 10.20, 10.70),
        ("pagina", 10.70, 13.70, "05-home", "SisPatrimônio - Dashboard",
         f"{host}/"),
        ("digita", 13.70, 14.60, f"{host}/docs"),
        ("carrega", 14.60, 15.00),
        ("pagina", 15.00, 17.60, "06-docs", "SisPatrimônio Pro - Swagger UI",
         f"{host}/docs"),
        ("sai", 17.60, 18.40),
    ]


TIMELINE = monta_timeline(DEFAULT_HOST)
DUR = TIMELINE[-1][2]


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def norm(t, a, b):
    if b <= a:
        return 1.0 if t >= a else 0.0
    return max(0.0, min(1.0, (t - a) / (b - a)))


def estado_em(t):
    """Retorna (indice_do_bloco, progresso_dentro_do_bloco)."""
    for i, blk in enumerate(TIMELINE):
        if blk[1] <= t < blk[2]:
            return i, (t - blk[1]) / (blk[2] - blk[1])
    return len(TIMELINE) - 1, 1.0


def pagina_anterior_ate(idx):
    """Screenshot visível antes/até o bloco `idx` (None se ainda não houve)."""
    atual = None
    for blk in TIMELINE[:idx]:
        if blk[0] == "pagina":
            atual = blk[3]
    return atual


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    shots_dir, out = sys.argv[1], sys.argv[2]
    host = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_HOST
    global TIMELINE, DUR, BG
    if len(sys.argv) > 4 and sys.argv[4]:
        h = sys.argv[4].lstrip("#")
        BG = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    TIMELINE = monta_timeline(host)
    DUR = TIMELINE[-1][2]

    f_tab = ImageFont.truetype(F_TAB, 15)
    f_tab_b = ImageFont.truetype(F_TAB_B, 15)
    f_url = ImageFont.truetype(F_TAB, 17)
    f_fav = ImageFont.truetype(F_TAB_B, 11)

    imgs = {}
    for nome in ("01-login", "02-setup", "03-apos-setup", "05-home", "06-docs"):
        p = os.path.join(shots_dir, nome + ".png")
        im = Image.open(p).convert("RGB")
        if im.size != (VW, VH):
            im = im.resize((VW, VH), Image.LANCZOS)
        imgs[nome] = im

    # título da aba por screenshot (derivado da própria timeline)
    TITULOS = {b[3]: b[4] for b in TIMELINE if b[0] == "pagina"}

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
        stderr=open("/tmp/scene-ffmpeg.log", "w"))

    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        idx, p = estado_em(t)
        blk = TIMELINE[idx]
        img = Image.new("RGB", (W, H), BG)

        # ---------- estado da barra de endereço / aba ----------
        url_txt, tab_txt, caret = "", "Nova aba", False
        progresso = 0.0
        carregando = False
        page_key, veil = None, 0.0

        if blk[0] == "digita":
            alvo = blk[3]
            n = int(ease(p) * len(alvo) + 1e-9)
            url_txt, caret = alvo[:max(0, n)], True
            page_key = pagina_anterior_ate(idx)
            # o navegador mantém a aba anterior enquanto se edita o endereço
            tab_txt = TITULOS.get(page_key, "Nova aba")
        elif blk[0] == "carrega":
            seguinte = TIMELINE[idx + 1] if idx + 1 < len(TIMELINE) else None
            url_txt = seguinte[5] if (seguinte and seguinte[0] == "pagina") else ""
            tab_txt = "Carregando…"
            carregando, progresso = True, p
            page_key = pagina_anterior_ate(idx)
            veil = 0.85 * ease(p)
        elif blk[0] == "pagina":
            url_txt, tab_txt = blk[5], blk[4]
            page_key = blk[3]
            veil = 0.85 * (1 - ease(norm(t, blk[1], blk[1] + 0.30)))
        elif blk[0] in ("janela", "sai"):
            url_txt, tab_txt = "", "Nova aba"
            page_key = None

        # ---------- viewport ----------
        vp = Image.new("RGB", (VW, VH), (245, 246, 248))
        if page_key:
            vp = imgs[page_key].copy()
        if veil > 0:
            v = Image.new("RGB", (VW, VH), (255, 255, 255))
            vp = Image.blend(vp, v, min(1.0, veil))
        img.paste(vp, (WX0, VY0))

        d = ImageDraw.Draw(img)

        # ---------- chrome ----------
        d.rectangle([WX0, WY0, WX1, WY0 + TAB_H + ADDR_H + PROG_H],
                    fill=CHROME)
        d.rectangle([WX0, WY0, WX1, WY1], outline=BORDER, width=1)

        # semáforo
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            x = 46 + i * 20
            cy = WY0 + TAB_H // 2
            d.ellipse([x - 6, cy - 6, x + 6, cy + 6], fill=c)

        # aba ativa
        tx0, tx1, ty0, ty1 = 116, 520, WY0 + 4, WY0 + TAB_H - 2
        d.rounded_rectangle([tx0, ty0, tx1, ty1], radius=8, fill=FIELD)
        # favicon
        fx0, fy0 = tx0 + 12, (ty0 + ty1) // 2 - 8
        d.rounded_rectangle([fx0, fy0, fx0 + 16, fy0 + 16], radius=4, fill=BLUE)
        d.text((fx0 + 3.4, fy0 + 2), "S", font=f_fav, fill=(255, 255, 255))
        # título da aba (truncado)
        titulo = tab_txt
        while d.textlength(titulo, font=f_tab) > (tx1 - tx0 - 44) and titulo:
            titulo = titulo[:-2] + "…"
        d.text((tx0 + 38, (ty0 + ty1) // 2 - 10), titulo, font=f_tab, fill=FG)

        # campo de endereço
        fy0, fy1 = WY0 + TAB_H + 7, WY0 + TAB_H + ADDR_H - 7
        d.rounded_rectangle([WX0 + 10, fy0, WX1 - 10, fy1], radius=9, fill=FIELD)
        # cadeado
        cx, cy = WX0 + 30, (fy0 + fy1) // 2
        d.rounded_rectangle([cx - 6, cy - 2, cx + 6, cy + 9], radius=2, fill=GREEN)
        d.arc([cx - 5, cy - 11, cx + 5, cy - 1], 180, 360, fill=GREEN, width=3)
        # texto do endereço
        if url_txt:
            d.text((WX0 + 46, (fy0 + fy1) // 2 - 11), url_txt,
                   font=f_url, fill=FG)
        elif blk[0] == "janela":
            d.text((WX0 + 46, (fy0 + fy1) // 2 - 11), "Pesquisar ou digitar endereço",
                   font=f_url, fill=GRAY)
        if caret:
            wpx = d.textlength(url_txt, font=f_url)
            bx = WX0 + 46 + wpx + 2
            if int(t * 3) % 2 == 0:
                d.rectangle([bx, fy0 + 5, bx + 2, fy1 - 5], fill=FG)

        # recarregar / spinner
        rx, ry = WX1 - 32, (fy0 + fy1) // 2
        if carregando:
            a0 = (t * 420) % 360
            d.arc([rx - 9, ry - 9, rx + 9, ry + 9], a0, a0 + 110,
                  fill=BLUE, width=3)
        else:
            d.arc([rx - 9, ry - 9, rx + 9, ry + 9], 40, 320, fill=GRAY, width=3)
            d.polygon([(rx + 7, ry - 8), (rx + 12, ry - 3), (rx + 4, ry - 3)],
                      fill=GRAY)

        # barra de progresso
        if carregando:
            w = VW * min(1.0, 0.08 + 0.92 * (progresso ** 0.45))
            d.rectangle([WX0, WY0 + TAB_H + ADDR_H, WX0 + w,
                         WY0 + TAB_H + ADDR_H + PROG_H], fill=BLUE)

        # ---------- transições ----------
        if blk[0] == "janela":
            al = ease(p)
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.rectangle([0, 0, W, H], fill=BG + (int(255 * (1 - al)),))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            # leve subida da janela
            if al < 1:
                desl = int((1 - al) * 26)
                base = Image.new("RGB", (W, H), BG)
                base.paste(img, (0, desl))
                img = base
        elif blk[0] == "sai":
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.rectangle([0, 0, W, H], fill=BG + (int(255 * ease(p)),))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        print(open("/tmp/scene-ffmpeg.log").read()[-2000:], file=sys.stderr)
        sys.exit(1)
    print(f"cena do navegador: {out} | {int(DUR * FPS)} frames | "
          f"{W}x{H} | {DUR}s @ {FPS}fps")


if __name__ == "__main__":
    main()
