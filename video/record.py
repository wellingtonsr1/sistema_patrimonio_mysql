#!/usr/bin/env python3
"""Grava uma sessão de terminal real (docker exec + pty) e salva em JSON v2
(no formato do asciinema): [[tempo, "o", texto], ...]

Uso: python3 record.py <saida.json>
"""
import fcntl
import json
import os
import pty
import re
import select
import struct
import subprocess
import sys
import termios
import time

COLS = 132
ROWS = 36
CONTAINER = "sispat-demo"
INSTALLER = "/demo/install no linux/nativa/install.sh"
PS1 = (
    "\\[\\033[1;32m\\]root@sispat-prod"
    "\\[\\033[0m\\]:\\[\\033[1;34m\\]~\\[\\033[0m\\]# "
)
SENHA = "Demo.Instalacao.2026"
TIPO_MS = 0.045
MAX_DURACAO = 40 * 60

REGRAS = [
    (r"Senha do banco \(m[íi]n\. 12 caracteres", SENHA + "\n"),
    (r"Confirme a senha \(vazio nas duas", SENHA + "\n"),
    (r"Confirmar e .*instala[çc][ãa]o\? \(s/N\):", "s\n"),
]

COMANDO = 'bash "' + INSTALLER + '"; rc=$?; echo; echo ">>> instalador finalizado (exit $rc)"\n'
POS_INSTALL = (
    "systemctl is-active sispatrimoniopro; "
    "curl -sk https://10.20.30.10:8000/health; echo\n"
)
SAIDA = "exit\n"

RE_PROMPT = r"root@sispat-prod.*# $"


def set_winsize(fd, rows, cols):
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def set_raw(fd):
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[3] = attrs[3] & ~(termios.ECHO | termios.ICANON | termios.ISIG |
                            termios.IEXTEN)
    attrs[6][termios.VMIN] = 1
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def main():
    if len(sys.argv) < 2:
        print("uso: record.py <saida.json>", file=sys.stderr)
        sys.exit(2)
    out_path = sys.argv[1]

    master, slave = pty.openpty()
    set_winsize(slave, ROWS, COLS)
    set_raw(slave)

    cmd = [
        "docker", "exec", "-i", "-t",
        "-e", "TERM=xterm-256color",
        "-e", "PS1=" + PS1,
        "-e", "LANG=C.UTF-8",
        "-e", "DEBIAN_FRONTEND=noninteractive",
        CONTAINER,
        "bash", "--norc", "--noprofile",
    ]

    fh = open(out_path, "w", encoding="utf-8")
    json.dump({
        "version": 2,
        "width": COLS,
        "height": ROWS,
        "timestamp": int(time.time()),
        "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"},
        "title": "SisPatrimonio Pro — instalação nativa (install.sh)",
    }, fh, ensure_ascii=False)
    fh.write("\n")
    fh.flush()

    t0 = time.time()
    last_out = time.time()
    buf = ""
    regras_feitas = [False] * len(REGRAS)
    pendentes = []
    fase = "prompt"
    fase_t = time.time()

    proc = subprocess.Popen(cmd, stdin=slave, stdout=slave, stderr=slave,
                            start_new_session=True)
    os.close(slave)

    def emit(data: str):
        nonlocal last_out
        last_out = time.time()
        ev = [round(time.time() - t0, 4), "o", data]
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        fh.flush()

    def log(msg):
        print(f"[{time.time() - t0:6.1f}s] {msg}", file=sys.stderr, flush=True)

    def enviar(texto, passo=TIPO_MS):
        agora = time.time()
        for i, ch in enumerate(texto):
            pendentes.append((agora + i * passo, ch))

    def flush_pendentes():
        while pendentes and pendentes[0][0] <= time.time():
            os.write(master, pendentes.pop(0)[1].encode())

    def transita(nova, limpar=True):
        nonlocal fase, fase_t, buf
        log(f"fase {fase} -> {nova}")
        fase, fase_t = nova, time.time()
        if limpar:
            buf = ""

    try:
        while True:
            if time.time() - t0 > MAX_DURACAO:
                emit("\r\n[gravador] tempo esgotado\r\n")
                break

            flush_pendentes()

            if time.time() - last_out > 45:
                log(f"SEM SAIDA HA {time.time() - last_out:.0f}s | fase={fase} | "
                    f"tail={buf[-260:]!r}")
                last_out = time.time()

            r, _, _ = select.select([master], [], [], 0.05)
            if r:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                texto = chunk.decode("utf-8", "replace")
                buf += texto
                emit(texto)

            if pendentes:
                continue

            if fase == "prompt" and re.search(RE_PROMPT, buf) \
                    and time.time() - fase_t > 1.0:
                enviar(COMANDO, passo=0.035)
                transita("instalando")

            elif fase == "instalando":
                # "exit <n>" (o eco do comando digitado tem "exit $rc")
                if re.search(r"instalador finalizado \(exit \d+\)", buf):
                    # não limpa o buf: o prompt do shell já veio no mesmo lote
                    transita("pos", limpar=False)
                else:
                    for i, (rx, teclas) in enumerate(REGRAS):
                        if regras_feitas[i]:
                            continue
                        if re.search(rx, buf):
                            regras_feitas[i] = True
                            log(f"regra {i} casou -> respondendo")
                            enviar(teclas, passo=0.05)
                            buf = ""
                            break

            elif fase == "pos" and re.search(RE_PROMPT, buf) \
                    and time.time() - fase_t > 0.8:
                enviar(POS_INSTALL, passo=0.04)
                transita("verificando")

            elif fase == "verificando" and re.search(RE_PROMPT, buf) \
                    and time.time() - fase_t > 3.0:
                enviar(SAIDA, passo=0.06)
                transita("fim", limpar=False)

            if fase == "fim" and proc.poll() is not None:
                time.sleep(0.3)
                r, _, _ = select.select([master], [], [], 0.2)
                if r:
                    try:
                        d = os.read(master, 65536)
                        if d:
                            emit(d.decode("utf-8", "replace"))
                    except OSError:
                        pass
                break
            if proc.poll() is not None and fase != "fim":
                # shell morreu antes do esperado: drena e encerra
                time.sleep(0.3)
                break
    finally:
        dur = time.time() - t0
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        os.close(master)
        fh.close()
        print(f"gravado: {out_path} | {dur:.1f}s | "
              f"regras={sum(regras_feitas)}/{len(REGRAS)} | fase_final={fase}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
