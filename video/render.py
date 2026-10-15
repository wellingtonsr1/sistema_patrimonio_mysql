#!/usr/bin/env python3
"""Renderiza uma gravação de terminal (JSON v2 estilo asciinema) para MP4.

Uso: python3 render.py <entrada.json> <saida.mp4> [--fps 15] [--speed 1.0]
"""
import json
import os
import subprocess
import sys

import pyte
from PIL import Image, ImageDraw, ImageFont

FONTS = {
    False: "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    True: "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
}
FONT_SIZE = 18
LINE_H = 22
PAD = 14
TITLE_H = 40

BG = (13, 17, 23)          # #0d1117
BG_TITLE = (22, 27, 34)    # #161b22
FG = (201, 209, 217)       # #c9d1d9
TITLE_FG = (139, 148, 158)

PALETTE = {
    "black": (33, 37, 41), "red": (255, 123, 114), "green": (63, 185, 80),
    "yellow": (210, 153, 34), "blue": (88, 166, 255), "magenta": (188, 140, 255),
    "cyan": (57, 197, 207), "white": (177, 186, 196),
    "brightblack": (72, 79, 88), "brightred": (255, 161, 152),
    "brightgreen": (86, 211, 100), "brightyellow": (227, 179, 65),
    "brightblue": (121, 192, 255), "brightmagenta": (210, 168, 255),
    "brightcyan": (86, 212, 221), "brightwhite": (240, 246, 252),
}


def parse_args(argv):
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    inp, out = argv[1], argv[2]
    fps, speed, gap_cap = 15, 1.0, 6.0
    i = 3
    while i < len(argv):
        if argv[i] == "--fps":
            fps = int(argv[i + 1]); i += 2
        elif argv[i] == "--speed":
            speed = float(argv[i + 1]); i += 2
        elif argv[i] == "--gap-cap":
            gap_cap = float(argv[i + 1]); i += 2
        else:
            i += 1
    return inp, out, fps, speed, gap_cap


def color(name, default):
    if not name or name in ("default", "g"):
        return default
    if name in PALETTE:
        return PALETTE[name]
    if len(name) == 6:
        try:
            return tuple(int(name[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            return default
    return default


def load_events(path):
    events = []
    with open(path, encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        for line in fh:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            if len(ev) == 3 and ev[1] == "o":
                events.append((float(ev[0]), ev[2]))
    return header, events


def build_timeline(events, speed, gap_cap):
    """Retorna eventos com tempos comprimidos (pausas longas encurtadas)."""
    out, last, acc = [], None, 0.0
    for t, data in events:
        if last is None:
            acc = 0.0
        else:
            gap = t - last
            acc += (gap / speed)
            if gap > gap_cap:
                # troca a pausa longa por uma pausa curta
                acc -= (gap - 1.2) / speed
        last = t
        out.append((acc, data))
    return out


def main():
    inp, out, fps, speed, gap_cap = parse_args(sys.argv)
    header, events = load_events(inp)
    cols = int(header.get("width", 132))
    rows = int(header.get("height", 36))
    # fundo/título vemem do cabeçalho do .cast (padrão = versão Linux)
    global BG
    if header.get("bg"):
        BG = tuple(int(header["bg"][i:i + 2], 16) for i in (1, 3, 5))
    titulo_cast = header.get("title")
    timeline = build_timeline(events, speed, gap_cap)
    duration = timeline[-1][0] + 2.0 if timeline else 1.0

    font = ImageFont.truetype(FONTS[False], FONT_SIZE)
    font_b = ImageFont.truetype(FONTS[True], FONT_SIZE)
    charw = font.getlength("M")

    term_w = int(round(cols * charw))
    term_h = rows * LINE_H
    W = int(term_w + 2 * PAD)
    W += W % 2
    H = int(TITLE_H + term_h + 2 * PAD)
    H += H % 2

    screen = pyte.Screen(cols, rows)
    try:
        stream = pyte.ByteStream(screen)
        feed = stream.feed
    except AttributeError:
        stream = pyte.Stream(screen)
        feed = lambda b: stream.feed(b.decode("utf-8", "replace"))

    exe = subprocess.check_output(
        [sys.executable, "-c",
         "import imageio_ffmpeg as f;print(f.get_ffmpeg_exe())"],
        text=True).strip()

    proc = subprocess.Popen(
        [exe, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-preset", "medium", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=open("/tmp/sispat-demo/ffmpeg.log", "w"))

    def render_frame():
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        # barra de título
        d.rectangle([0, 0, W, TITLE_H - 1], fill=BG_TITLE)
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            x = 16 + i * 20
            d.ellipse([x, 14, x + 12, 26], fill=c)
        titulo = titulo_cast or "root@sispat-prod — SisPatrimônio Pro · instalação nativa (install.sh)"
        tw = d.textlength(titulo, font=font)
        d.text(((W - tw) / 2, 11), titulo, font=font, fill=TITLE_FG)

        y = TITLE_H + PAD
        buffer = screen.buffer
        for row in range(rows):
            line = buffer[row]
            # agrupa células por estilo para desenhar poucos textos por linha
            runs = []  # [(texto, estilo)]
            for col in range(cols):
                ch = line[col]
                bold = bool(ch.bold)
                rev = bool(ch.reverse)
                fg = color(ch.fg, FG)
                bg = color(ch.bg, None)
                if rev:
                    fg, bg = (bg if bg is not None else BG), fg
                style = (bold, fg, bg)
                txt = ch.data if ch.data else " "
                if runs and runs[-1][1] == style:
                    runs[-1][0] += txt
                else:
                    runs.append([txt, style])

            x = PAD
            for txt, (bold, fg, bg) in runs:
                fnt = font_b if bold else font
                w = d.textlength(txt, font=fnt)
                if bg is not None:
                    d.rectangle([x, y, x + w, y + LINE_H], fill=bg)
                d.text((x, y), txt, font=fnt, fill=fg)
                x += w
            y += LINE_H

        # cursor
        try:
            hidden = screen.cursor.hidden
        except AttributeError:
            hidden = False
        if not hidden:
            cx = PAD + screen.cursor.x * charw
            cy = TITLE_H + PAD + screen.cursor.y * LINE_H
            d.rectangle([cx, cy + LINE_H - 3, cx + charw, cy + LINE_H - 1],
                        fill=FG)

        return img.tobytes()

    frame_dur = 1.0 / fps
    n_frames = int(duration * fps)
    idx, pos = 0, 0
    for f in range(n_frames):
        t = f * frame_dur
        while pos < len(timeline) and timeline[pos][0] <= t:
            feed(timeline[pos][1].encode("utf-8", "replace"))
            pos += 1
        try:
            proc.stdin.write(render_frame())
        except BrokenPipeError:
            print(open("/tmp/sispat-demo/ffmpeg.log").read()[-3000:],
                  file=sys.stderr)
            sys.exit(1)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        print(open("/tmp/sispat-demo/ffmpeg.log").read()[-3000:],
              file=sys.stderr)
        sys.exit(1)
    print(f"ok: {out} | {n_frames} frames | {W}x{H} | {duration:.1f}s | fps={fps}")


if __name__ == "__main__":
    main()
