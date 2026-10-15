#!/usr/bin/env python3
"""Adiciona legendas/rótulos de etapa sobrepostos ao vídeo final.

Formato das legendas de etapa: sempre SINGULAR — "Etapa 1/16",
"Etapa 2/16", … "Etapa 16/16" (sem intervalos tipo "Etapas 4–13/16").

Tempos reais vêm do .cast (primeira ocorrência de cada cabeçalho
`── [n/16]`). Como algumas etapas duram milissegundos, cada chip tem
duração mínima de 0,18 s; o arrasto acumulado é auto-corretivo (uma
etapa longa volta a alinhar o chip com a tela). Chips com menos de 0,9 s
mostram só o número ("Etapa 7/16") para serem lidos em tempo real.

O instalador imprime um 17º cabeçalho "[17/16]" (off-by-one do script);
ele é dobrado no 16º para a sequência terminar em 16/16.

Uso: python3 add_labels.py <video_entrada.mp4> <video_saida.mp4>
"""
import json
import re
import subprocess
import sys

import imageio_ffmpeg as iff
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1460, 860, 15
CAST_PADRAO = "instalacao-nativa-linux.cast"
OFFSET_PADRAO = 6.6      # duração da abertura (a gravação começa depois dela)
SCENE_LINUX = 65.47      # início da cena do navegador no vídeo Linux
URL_LINUX = "https://10.20.30.10:8000"

VERDE = (63, 185, 80)
AZUL = (88, 166, 255)
CHIP_BG = (16, 20, 26, 225)
TEXTO = (240, 246, 252, 255)

F_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FADE = 0.28           # fade máximo (reduzido em chips curtos)
MIN_DUR = 0.18        # duração mínima de um chip de etapa
NOME_COMPLETO = 0.9   # abaixo disso, chip mostra só "Etapa N/16"
TOTAL_ETAPAS = 16

FOLDS = {(16, 17): "Auditoria e firewall"}


def marcos_do_cast(cast):
    """Momentos de cada etapa do instalador, extraídos do .cast."""
    linhas = open(cast, encoding="utf-8").read().splitlines()
    ev = [(json.loads(l)[0], json.loads(l)[2]) for l in linhas[1:]]

    t_senha = t_verif = None
    passos, buf, vistos = [], "", set()
    for tt, s in ev:
        buf += s
        if t_senha is None and re.search(r"Senha do banco \(m[íi]n\. 12 caracteres", buf):
            t_senha = tt
        if t_verif is None and re.search(
                r"(systemctl is-active sispatrimoniopro|Get-ScheduledTask -TaskName)", buf):
            t_verif = tt
        # cada cabeçalho tem texto único: guarda o PRIMEIRO instante em que aparece
        for m in re.finditer(r"(?:──|--) \[\d+/16\] [^\r\n\x1b]+", buf):
            txt = m.group(0)
            if txt not in vistos:
                vistos.add(txt)
                passos.append((txt, tt))
    return t_senha, t_verif, ev[-1][0], passos


def monta_legendas(cast, offset, scene_start=None, url_navegador=URL_LINUX):
    t_senha, t_verif, t_end, bruto = marcos_do_cast(cast)
    t_senha = t_senha if t_senha is not None else 5.42
    t_verif = t_verif if t_verif is not None else 54.06

    passos = []
    for i, (txt, tt) in enumerate(bruto):
        m = re.match(r"(?:──|--) \[(\d+)/16\] (.*)", txt)
        num, nome = int(m.group(1)), m.group(2).strip()
        fim = bruto[i + 1][1] if i + 1 < len(bruto) else t_verif
        passos.append([num, nome, tt, fim])

    # dobra cabeçalhos acima de 16 no anterior (sequência termina em 16/16)
    while passos and passos[-1][0] > TOTAL_ETAPAS:
        ultimo = passos.pop()
        if passos:
            prev = passos[-1]
            prev[3] = ultimo[3]
            prev[1] = FOLDS.get((prev[0], ultimo[0]),
                                f"{prev[1]} e {ultimo[1]}")

    # layout sequencial com duração mínima (arrasto auto-corretivo)
    chips, fim_anterior = [], None
    for num, nome, t0, t1 in passos:
        inicio = max(t0, fim_anterior) if fim_anterior else t0
        fim = max(t1, inicio + MIN_DUR)
        chips.append((inicio, fim, num, nome))
        fim_anterior = fim

    rotulos = [
        (1.0 + offset, t_senha + offset,
         "Pré-requisitos · root, Ubuntu, systemd, apt"
         if "linux" in cast else "Pré-requisitos · Administrador, Python, Git, winget",
         VERDE),
        (t_senha + offset, passos[0][2] + offset,
         "Credenciais · senha digitada sem eco", VERDE),
    ]
    for inicio, fim, num, nome in chips:
        titulo = (f"Etapa {num}/{TOTAL_ETAPAS}" if fim - inicio < NOME_COMPLETO
                  else f"Etapa {num}/{TOTAL_ETAPAS} · {nome}")
        rotulos.append((inicio + offset, fim + offset, titulo, VERDE))

    rotulos.append((max(t_verif, fim_anterior) + offset, t_end + offset,
                    "Resumo final e verificação · health + tarefa/serviço", VERDE))

    # cena do navegador (deslocamentos relativos ao início da cena)
    if scene_start is not None:
        cenas = [
            (0.13, 2.40, f"Acesso pelo navegador · {url_navegador}"),
            (2.40, 4.60, "Tela de login · primeiro acesso"),
            (4.60, 8.60, "Primeiro administrador · /setup"),
            (8.60, 10.70, "Autenticação com o novo usuário"),
            (10.70, 13.70, "Dashboard autenticado"),
            (13.70, 17.60, "API · Swagger UI em /docs"),
        ]
        for a, b, txt in cenas:
            rotulos.append((scene_start + a, scene_start + b, txt, AZUL))

    rotulos = sorted(r for r in rotulos if r[1] > r[0] + 0.05)
    for p, n in zip(rotulos, rotulos[1:]):
        if n[0] < p[1] - 1e-6:
            print(f"AVISO: sobreposição {p[2]!r} x {n[2]!r}", file=sys.stderr)
    return rotulos


def chip(img, texto, cor, alpha, dx):
    """Lower-third no canto inferior esquerdo, com fade e deslize."""
    if alpha <= 0:
        return
    a = int(255 * alpha)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(F_BOLD, 21)
    x0, y0 = 40 + dx, H - 98
    w = 6 + 22 + d.textlength(texto, font=f) + 26
    h = 54

    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(camada)
    cd.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=12,
                         fill=CHIP_BG[:3] + (int(CHIP_BG[3] * alpha),))
    cd.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=12,
                         outline=cor + (int(200 * alpha),), width=2)
    img.alpha_composite(camada)

    d.rectangle([x0 + 2, y0 + 2, x0 + 8, y0 + h - 2], fill=cor + (a,))
    d.text((x0 + 22, y0 + h / 2), texto, font=f, fill=TEXTO[:3] + (a,),
           anchor="lm")


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    entrada, saida = sys.argv[1], sys.argv[2]

    cast, offset = CAST_PADRAO, OFFSET_PADRAO
    scene_start, url_nav = SCENE_LINUX, URL_LINUX
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--cast":
            cast = args[i + 1]; i += 2
        elif args[i] == "--offset":
            offset = float(args[i + 1]); i += 2
        elif args[i] == "--scene-start":
            scene_start = float(args[i + 1]); i += 2
        elif args[i] == "--url":
            url_nav = args[i + 1]; i += 2
        elif args[i] == "--sem-navegador":
            scene_start = None; i += 1
        else:
            i += 1

    rotulos = monta_legendas(cast, offset, scene_start, url_nav)
    for r in rotulos:
        print(f"  {r[0]:6.2f} → {r[1]:6.2f}  {r[2]}")

    nframes, dur = iff.count_frames_and_secs(entrada)
    print(f"entrada: {nframes} frames · {dur:.2f}s")

    proc = subprocess.Popen(
        [iff.get_ffmpeg_exe(), "-y", "-i", entrada,
         "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-",
         "-filter_complex",
         "[0:v]format=rgba[b];[b][1:v]overlay[v];[v]format=yuv420p[o]",
         "-map", "[o]","-c:v", "libx264", "-crf", "20", "-preset", "medium",
         "-movflags", "+faststart", saida],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=open("/tmp/labels-ffmpeg.log", "w"))

    vazio = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bytes_vazios = vazio.tobytes()
    escritos = 0
    try:
        for i in range(nframes):
            t = i / FPS
            ativos = [r for r in rotulos if r[0] <= t < r[1]]
            if not ativos:
                proc.stdin.write(bytes_vazios)
            else:
                img = vazio.copy()
                for t0, t1, texto, cor in ativos:
                    # fade proporcional à duração: chip curto atinge alpha cheio
                    fade = min(FADE, (t1 - t0) * 0.3)
                    a_in = min(1.0, (t - t0) / fade)
                    a_out = min(1.0, (t1 - t) / fade)
                    a = max(0.0, min(a_in, a_out))
                    chip(img, texto, cor, a, int((1 - a_in) * -16))
                proc.stdin.write(img.tobytes())
            escritos += 1
    except BrokenPipeError:
        print("ffmpeg encerrou a leitura antes do fim (ok)", file=sys.stderr)
    finally:
        try:
            proc.stdin.close()
        except BrokenPipeError:
            pass
        proc.wait()

    if proc.returncode != 0:
        print(open("/tmp/labels-ffmpeg.log").read()[-2500:], file=sys.stderr)
        sys.exit(1)
    print(f"legendas aplicadas: {saida} | {escritos} frames | "
          f"{len(rotulos)} rótulos")


if __name__ == "__main__":
    main()
