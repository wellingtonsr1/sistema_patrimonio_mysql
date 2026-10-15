#!/usr/bin/env python3
"""Gera a abertura (vinheta) do vídeo de demonstração + capa.

Estética "terminal de produção": prompt digitado → limpeza da tela →
título, subtítulo, barra de acento e tag, com fade final para o fundo
do vídeo principal (junção invisível).

Uso:
  python3 make_intro.py <intro.mp4> [capa.png] [titulo] [subtitulo] [tag]
                     [prompt] [comando] [rodape_dir] [bg_hex]

Exemplo (Windows): prompt "PS C:\\Users\\Administrador> ", comando
"powershell -ExecutionPolicy Bypass -File .\\install.ps1", bg "#012456".
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1460, 860
FPS = 15
DUR = 6.6

BG = (13, 17, 23)          # mesmo fundo do terminal do vídeo principal
FG = (201, 209, 217)
GREEN = (63, 185, 80)
BLUE = (88, 166, 255)
GRAY = (139, 148, 158)
DIM = (48, 55, 62)

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

PROMPT = "root@sispat-prod:~# "
COMANDO = "bash install.sh"
RODAPE_DIR = "v1.0.0 · install.sh"

T_CMD_IN = 0.45            # início da digitação
T_CMD_STEP = 0.055         # atraso por tecla
T_ENTER = T_CMD_IN + len(COMANDO) * T_CMD_STEP + 0.35
T_WIPE = T_ENTER + 0.30    # limpa a linha digitada
T_WIPE_END = T_WIPE + 0.30
T_TITLE = T_WIPE_END + 0.05
T_SUB = T_TITLE + 0.55
T_BAR = T_TITLE + 0.70
T_TAG = T_TITLE + 1.15
T_FADE = DUR - 0.75        # fade para BG no final


def calcular_tempos():
    """Recalcula a linha do tempo (comandos longos estendem a duração)."""
    global DUR, T_ENTER, T_WIPE, T_WIPE_END, T_TITLE, T_SUB, T_BAR, T_TAG, T_FADE
    T_ENTER = T_CMD_IN + len(COMANDO) * T_CMD_STEP + 0.35
    T_WIPE = T_ENTER + 0.30
    T_WIPE_END = T_WIPE + 0.30
    T_TITLE = T_WIPE_END + 0.05
    T_SUB = T_TITLE + 0.55
    T_BAR = T_TITLE + 0.70
    T_TAG = T_TITLE + 1.15
    # mínimo 6,6 s preserva a vinheta Linux original; senão, garante ~1,2 s
    # de tag visível antes do fade
    DUR = max(6.6, T_TAG + 1.95)
    T_FADE = DUR - 0.75


def segmentos_prompt():
    """Trechos do prompt com cores (Linux: host/dir; Windows: PS/caminho)."""
    if PROMPT.startswith("root@"):
        return [("root@sispat-prod", GREEN), (":", FG), ("~", BLUE), ("# ", FG)]
    fim = PROMPT.rfind("> ")
    caminho = PROMPT[3:fim] if fim > 3 else PROMPT[3:]
    return [("PS ", GRAY), (caminho, BLUE), (PROMPT[3 + len(caminho):], FG)]


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def norm(t, t0, t1):
    if t1 <= t0:
        return 1.0 if t >= t0 else 0.0
    return max(0.0, min(1.0, (t - t0) / (t1 - t0)))


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    global PROMPT, COMANDO, RODAPE_DIR, BG
    out = sys.argv[1]
    capa = sys.argv[2] if len(sys.argv) > 2 else None
    if len(sys.argv) > 6 and sys.argv[6]:
        PROMPT = sys.argv[6]
    if len(sys.argv) > 7 and sys.argv[7]:
        COMANDO = sys.argv[7]
    if len(sys.argv) > 8 and sys.argv[8]:
        RODAPE_DIR = sys.argv[8]
    if len(sys.argv) > 9 and sys.argv[9]:
        h = sys.argv[9].lstrip("#")
        BG = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    calcular_tempos()
    t_capa = T_TAG + 0.9

    f_cmd = ImageFont.truetype(MONO, 30)
    f_cmd_b = ImageFont.truetype(MONO_B, 30)
    f_title = ImageFont.truetype(MONO_B, 76)
    f_sub = ImageFont.truetype(MONO, 28)
    f_tag = ImageFont.truetype(MONO_B, 20)
    f_small = ImageFont.truetype(MONO, 18)

    # linha digitada centralizada estaticamente (não "pula" durante a digitação)
    largura_prompt = d_len = None
    full = PROMPT + COMANDO
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    largura_full = tmp.textlength(full, font=f_cmd)
    x_linha = (W - largura_full) / 2
    y_linha = H / 2 - 18

    titulo = (sys.argv[3] if len(sys.argv) > 3 and sys.argv[3]
              else "SisPatrimônio Pro")
    subtitulo = (sys.argv[4] if len(sys.argv) > 4 and sys.argv[4]
                 else "Instalação nativa · install.sh  (systemd + MariaDB)")
    tag = (sys.argv[5] if len(sys.argv) > 5 and sys.argv[5]
           else "DEMONSTRAÇÃO REAL · Ubuntu 22.04 · execução completa em 58 s")
    rodape = "github.com/wellingtonsr1/SisPatrimonioPro"
    w_titulo = tmp.textlength(titulo, font=f_title)
    w_sub = tmp.textlength(subtitulo, font=f_sub)
    w_tag = tmp.textlength(tag, font=f_tag)
    w_rod = tmp.textlength(rodape, font=f_small)

    exe = subprocess.check_output(
        [sys.executable, "-c", "import imageio_ffmpeg as f;print(f.get_ffmpeg_exe())"],
        text=True).strip()

    proc = subprocess.Popen(
        [exe, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-preset", "medium", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=open("/tmp/intro-ffmpeg.log", "w"))

    n_frames = int(DUR * FPS)
    for i in range(n_frames):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)

        # ---- 1. prompt + comando digitado -------------------------------
        if t < T_WIPE_END:
            n_chars = max(0, int((t - T_CMD_IN) / T_CMD_STEP))
            n_chars = min(n_chars, len(COMANDO))
            parcial = PROMPT + COMANDO[:n_chars]

            # prompt colorido (Linux: host verde/dir azul; Windows: PS/caminho)
            x = x_linha
            for texto, cor in segmentos_prompt():
                d.text((x, y_linha), texto, font=f_cmd, fill=cor)
                x += d.textlength(texto, font=f_cmd)

            if n_chars:
                d.text((x, y_linha), COMANDO[:n_chars], font=f_cmd, fill=FG)
                x += d.textlength(COMANDO[:n_chars], font=f_cmd)

            # cursor em bloco
            piscando = int(t * 3) % 2 == 0 if t < T_ENTER else True
            if piscando:
                h_cur = 30
                d.rectangle([x + 2, y_linha + 4, x + 2 + 17, y_linha + 4 + h_cur - 6],
                            fill=GREEN if t < T_ENTER else FG)

            # fade da linha digitada ao "enter"
            a = 1 - ease_out(norm(t, T_ENTER, T_WIPE_END))
            if a < 1:
                overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay)
                od.rectangle([0, 0, W, H], fill=BG + (int((1 - a) * 255),))
                img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
                d = ImageDraw.Draw(img)

        # ---- 2. título --------------------------------------------------
        p_title = ease_out(norm(t, T_TITLE, T_TITLE + 0.55))
        if p_title > 0:
            dy = int((1 - p_title) * 34)
            y_t = H / 2 - 90 + dy
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.text(((W - w_titulo) / 2, y_t), titulo, font=f_title,
                    fill=FG + (int(255 * p_title),))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            d = ImageDraw.Draw(img)

        # ---- 3. subtítulo ------------------------------------------------
        p_sub = ease_out(norm(t, T_SUB, T_SUB + 0.45))
        if p_sub > 0:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.text(((W - w_sub) / 2, H / 2 + 12 + int((1 - p_sub) * 18)),
                    subtitulo, font=f_sub, fill=GRAY + (int(255 * p_sub),))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            d = ImageDraw.Draw(img)

        # ---- 4. barra de acento -----------------------------------------
        p_bar = ease_out(norm(t, T_BAR, T_BAR + 0.6))
        if p_bar > 0:
            larg = 520 * p_bar
            y_b = H / 2 - 8
            d.rectangle([(W - larg) / 2, y_b, (W + larg) / 2, y_b + 4], fill=GREEN)
            if p_bar > 0.5:  # pequeno trecho azul no fim da barra
                lz = 90 * min(1.0, (p_bar - 0.5) * 2)
                d.rectangle([(W + larg) / 2 - lz, y_b, (W + larg) / 2, y_b + 4],
                            fill=BLUE)

        # ---- 5. tag e rodapé --------------------------------------------
        p_tag = ease_out(norm(t, T_TAG, T_TAG + 0.4))
        if p_tag > 0:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            al = int(255 * p_tag)
            od.text(((W - w_tag) / 2, H / 2 + 74 + int((1 - p_tag) * 12)),
                    tag, font=f_tag, fill=BLUE + (al,))
            od.text((40, H - 46), rodape, font=f_small, fill=GRAY + (al,))
            od.text((W - 40 - d.textlength(RODAPE_DIR, font=f_small),
                     H - 46), RODAPE_DIR, font=f_small,
                    fill=GRAY + (al,))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            d = ImageDraw.Draw(img)

        # ---- 6. fade final para o fundo do vídeo principal ---------------
        p_fade = norm(t, T_FADE, DUR)
        if p_fade > 0:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.rectangle([0, 0, W, H], fill=BG + (int(255 * p_fade),))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        if capa and abs(t - t_capa) < (1 / FPS / 2):
            img.save(capa)

        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        print(open("/tmp/intro-ffmpeg.log").read()[-2000:], file=sys.stderr)
        sys.exit(1)
    print(f"intro: {out} | {n_frames} frames | {W}x{H} | "
          f"{n_frames / FPS:.3f}s @ {FPS}fps (duração prevista {DUR}s)"
          + (f" | capa: {capa}" if capa else ""))


if __name__ == "__main__":
    main()
