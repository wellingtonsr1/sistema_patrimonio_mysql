#!/usr/bin/env python3
"""Gera a gravação (JSON v2 estilo asciinema) da INSTALAÇÃO MANUAL no Linux.

Segue o "Fluxo manual (alternativa)" do README (10 passos), com os literais
reais do projeto: saída do `python run.py`, `/health` e do CLI `create-user`.
A saída de ferramentas externas (apt, pip, venv) é omitida — o vídeo pula
com uma pausa no lugar, sem inventar linhas. A senha do banco nunca aparece
ecoada: `read -s` e `${SENHA}` evitam mostrá-la (mesma política do vídeo do
instalador).

Uso: python3 make_manual_session.py <saida.cast>
"""
import json
import sys

COLS, ROWS = 132, 36

RESET = "\x1b[0m"
GREEN, CYAN = "\x1b[32m", "\x1b[36m"
HOST = f"\x1b[1;32mroot@sispat-prod{RESET}"


def ps1(diretorio="~", venv=False):
    pre = f"{GREEN}(.venv){RESET} " if venv else ""
    return f"{pre}{HOST}:\x1b[1;34m{diretorio}{RESET}# "


class Sessao:
    def __init__(self):
        self.eventos = []
        self.t = 0.0
        self.ps1 = ps1()

    def out(self, texto, pausa=0.0):
        if texto:
            self.eventos.append([round(self.t, 4), "o", texto])
        self.t += pausa

    def pausa(self, seg):
        self.t += seg

    def digita(self, texto, passo=0.045):
        for ch in texto:
            self.eventos.append([round(self.t, 4), "o", ch])
            self.t += passo

    def cmd(self, texto, pausa_enter=0.45):
        """Prompt + comando digitado + Enter (bash)."""
        self.out(self.ps1)
        self.digita(texto)
        self.out("\r\n", pausa_enter)

    def branco(self, texto, pausa=0.04):
        self.out(f"{texto}{RESET}\r\n", pausa)

    def etapa(self, n, nome):
        self.out("\r\n", 0.10)
        self.branco(f"── [{n}/10] {nome}", 0.14)


def construir():
    s = Sessao()

    # ---- atualiza índices do apt (pré-passo) --------------------------------
    s.cmd("apt-get update", 0.6)
    s.pausa(4.0)                       # saída do apt omitida

    # ---- [1/10] Python -----------------------------------------------------
    s.etapa(1, "Pré-requisitos · Python 3.10+")
    s.cmd("apt-get install -y python3 python3-venv python3-pip", 0.5)
    s.pausa(4.4)
    s.cmd("python3 --version")
    s.out("Python 3.12.3\r\n", 0.4)

    # ---- [2/10] Git --------------------------------------------------------
    s.etapa(2, "Pré-requisitos · Git")
    s.cmd("apt-get install -y git", 0.4)
    s.pausa(2.3)
    s.cmd("git --version")
    s.out("git version 2.43.0 (Ubuntu 2.43.0-1ubuntu7)\r\n", 0.4)

    # ---- [3/10] MariaDB/MySQL ----------------------------------------------
    s.etapa(3, "Pré-requisitos · MariaDB/MySQL")
    s.cmd("apt-get install -y mariadb-server", 0.4)
    s.pausa(4.6)
    s.cmd("systemctl enable --now mariadb", 0.4)
    s.pausa(1.4)
    s.cmd("mariadb --version")
    s.out("mariadb  Ver 15.1 Distrib 11.4.5-MariaDB, "
          "for debian-linux-gnu (x86_64)\r\n", 0.5)

    # ---- [4/10] Clone -------------------------------------------------------
    s.etapa(4, "Código-fonte (git clone)")
    s.cmd("git clone https://github.com/wellingtonsr1/SisPatrimonioPro.git", 0.5)
    s.pausa(0.6)
    s.out("Cloning into 'SisPatrimonioPro'...\r\n", 2.4)
    s.cmd("cd SisPatrimonioPro")
    s.ps1 = ps1("~/SisPatrimonioPro")

    # ---- [5/10] venv --------------------------------------------------------
    s.etapa(5, "Ambiente virtual (.venv)")
    s.cmd("python3 -m venv .venv", 0.4)
    s.pausa(1.9)
    s.cmd("source .venv/bin/activate")
    s.ps1 = ps1("~/SisPatrimonioPro", venv=True)

    # ---- [6/10] Dependências ------------------------------------------------
    s.etapa(6, "Dependências (requirements.txt)")
    s.cmd("pip install -r requirements.txt", 0.4)
    s.pausa(5.2)                       # saída do pip omitida

    # ---- [7/10] Banco e usuário ----------------------------------------------
    s.etapa(7, "Banco de dados e usuário")
    s.cmd('read -s -p "Senha do banco (min. 12 caracteres): " SENHA; echo', 0.5)
    s.out("Senha do banco (min. 12 caracteres): ")
    s.pausa(1.5)                       # senha digitada sem eco
    s.out("\r\n", 0.4)
    s.cmd("mysql -u root -p", 0.5)
    s.out("Enter password: ")
    s.pausa(1.2)
    s.out("\r\n", 0.3)
    # --- monitor MariaDB (prompt próprio, sem prompt do bash) ---
    def sql(comando, resultado, pausa=0.4):
        s.out("MariaDB [(none)]> ")
        s.digita(comando)
        s.out("\r\n", pausa)
        s.out(resultado + "\r\n", 0.4)

    sql("CREATE DATABASE sispatrimoniopro CHARACTER SET utf8mb4 "
        "COLLATE utf8mb4_unicode_ci;", "Query OK, 1 row affected (0.01 sec)")
    sql("CREATE USER 'sispat'@'%' IDENTIFIED BY '${SENHA}';",
        "Query OK, 0 rows affected (0.00 sec)")
    sql("GRANT ALL PRIVILEGES ON sispatrimoniopro.* TO 'sispat'@'%';",
        "Query OK, 0 rows affected (0.00 sec)")
    sql("FLUSH PRIVILEGES;", "Query OK, 0 rows affected (0.00 sec)")
    s.out("MariaDB [(none)]> ")
    s.digita("exit")
    s.out("\r\n", 0.3)
    s.out("Bye\r\n", 0.6)

    # ---- [8/10] DATABASE_URL -------------------------------------------------
    s.etapa(8, "Configuração do DATABASE_URL (.env)")
    s.cmd("cp .env.example .env", 0.4)
    s.cmd('echo "DATABASE_URL=mariadb+pymysql://sispat:${SENHA}'
          '@127.0.0.1:3306/sispatrimoniopro" >> .env', 0.5)
    s.cmd("chmod 600 .env", 0.4)

    # ---- [9/10] Inicialização -------------------------------------------------
    s.etapa(9, "Inicialização (python run.py)")
    s.cmd("nohup python run.py > /var/log/sispatrimonio.log 2>&1 &", 0.9)
    s.out("[1] 1847\r\n", 0.4)
    s.cmd("tail -n 8 /var/log/sispatrimonio.log", 0.8)
    s.out("-> Inicializando banco de dados do SisPatrimônio Pro...\r\n", 0.12)
    s.out("=" * 60 + "\r\n", 0.12)
    s.out(f"{GREEN}[OK]{RESET} SisPatrimônio Pro iniciado com sucesso!\r\n", 0.12)
    s.out(f"{CYAN}[>>]{RESET} Interface Web: http://0.0.0.0:8000\r\n", 0.12)
    s.out(f"{CYAN}[>>]{RESET} Swagger API Docs: http://0.0.0.0:8000/docs\r\n", 0.12)
    s.out("=" * 60 + "\r\n", 0.12)
    s.out("INFO:     Started server process [1847]\r\n", 0.12)
    s.out("INFO:     Uvicorn running on http://0.0.0.0:8000 "
          "(Press CTRL+C to quit)\r\n", 1.2)

    # ---- [10/10] Primeiro administrador + verificação ---------------------------
    s.etapa(10, "Primeiro administrador (CLI)")
    s.cmd('python -m app.cli create-user --username admin '
          '--name "Administrador" --admin', 0.6)
    s.out("Senha: ")
    s.pausa(1.3)                       # senha digitada sem eco
    s.out("\r\n", 0.2)
    s.out("Confirme a senha: ")
    s.pausa(1.1)
    s.out("\r\n", 0.3)
    s.out("Sucesso: usuário 'admin' criado!\r\n", 0.9)
    s.cmd("curl -s http://127.0.0.1:8000/health", 0.7)
    s.out('{"status":"healthy","application":"ok","database":"ok",'
          '"ad":"not_applicable"}\r\n', 1.1)
    s.cmd("systemctl is-active mariadb", 0.5)
    s.out("active\r\n", 0.7)
    s.cmd("curl -sI http://127.0.0.1:8000/docs | head -1", 0.6)
    s.out("HTTP/1.1 200 OK\r\n", 1.3)
    s.out(s.ps1, 0.4)
    return s


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    saida = sys.argv[1]
    sessao = construir()
    with open(saida, "w", encoding="utf-8") as fh:
        json.dump({
            "version": 2,
            "width": COLS,
            "height": ROWS,
            "timestamp": 1792000000,
            "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"},
            "title": "root@sispat-prod — SisPatrimônio Pro · "
                     "instalação manual (README)",
        }, fh, ensure_ascii=False)
        fh.write("\n")
        for ev in sessao.eventos:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"sessao: {saida} | {len(sessao.eventos)} eventos | "
          f"{sessao.t:.1f}s de relogio")


if __name__ == "__main__":
    main()
