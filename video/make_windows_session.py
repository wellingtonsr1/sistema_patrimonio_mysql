#!/usr/bin/env python3
"""Gera a gravação (JSON v2 estilo asciinema) da sessão do instalador Windows.

As mensagens são LITERAIS do `install no windows/nativa/install.ps1`
(banner, [INFO ]/[OK   ]/[AVISO], cabeçalhos `-- [n/16]`, prompts de
Read-Host e o Print-Summary). A saída de ferramentas externas (winget,
pip, python) é omitida — o vídeo pula com uma pausa no lugar, sem inventar
linhas.

Uso: python3 make_windows_session.py <saida.cast>
"""
import json
import sys

COLS, ROWS = 132, 36
PS1 = "PS C:\\Users\\Administrador> "
CMD = "powershell -ExecutionPolicy Bypass -File .\\install.ps1"

RESET = "\x1b[0m"
GREEN, YELLOW, CYAN, RED, WHITE = "\x1b[32m", "\x1b[33m", "\x1b[36m", "\x1b[31m", "\x1b[97m"

BANNER_TITULO = ("SisPatrimonio Pro - Instalador WINDOWS (nativo) "
                 "v1.2.0-win (2026-10-16 09:41:07)")
LINHAS = "=" * 62


class Sessao:
    def __init__(self):
        self.eventos = []
        self.t = 0.0

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

    def log(self, nivel, msg, cor, pausa=0.06):
        self.out(f"{cor}[{nivel:<5}] {msg}{RESET}\r\n", pausa)

    def ok(self, msg, pausa=0.06):
        self.log("OK", msg, GREEN, pausa)

    def info(self, msg, pausa=0.06):
        self.log("INFO", msg, CYAN, pausa)

    def aviso(self, msg, pausa=0.06):
        self.log("AVISO", msg, YELLOW, pausa)

    def branco(self, texto, pausa=0.04):
        self.out(f"{WHITE}{texto}{RESET}\r\n", pausa)

    def etapa(self, n, nome):
        self.out("\r\n", 0.10)
        self.branco(f"-- [{n}/16] {nome}", 0.14)


def construir():
    s = Sessao()

    # ---- shell -----------------------------------------------------------
    s.out(PS1, 0.5)
    s.digita(CMD)
    s.out("\r\n", 0.9)

    # ---- gates + banner (ordem real do Main) -----------------------------
    s.ok("Executando com privilegios de administrador.", 0.45)
    s.out(f"\r\n{LINHAS}\r\n", 0.05)
    s.info(BANNER_TITULO, 0.05)
    s.out(f"{WHITE}{LINHAS}{RESET}\r\n\r\n", 0.35)

    # ---- Detect-Host ------------------------------------------------------
    s.ok("Python 3.12 detectado.")
    s.ok("Git detectado.")
    s.aviso("Nenhum servidor MariaDB/MySQL detectado (sera instalado MariaDB - decisao D3).")
    s.aviso("Cliente mysql/mariadb nao encontrado - sera provido com o servidor.")
    s.pausa(0.9)

    # ---- Collect-Secrets (sem eco) ---------------------------------------
    s.out("\r\nSenha do banco (min. 12 caracteres; ENTER vazio nas duas = gerar automaticamente): ")
    s.pausa(1.7)
    s.out("\r\nConfirme a senha (vazio nas duas = tentar senha vazia): ")
    s.pausa(1.3)
    s.out("\r\n", 0.5)

    # ---- Confirm-Plan ------------------------------------------------------
    s.out("\r\n", 0.1)
    s.branco("  RESUMO DA INSTALACAO")
    s.out("    Diretorio    : C:\\SisPatrimonioPro\r\n", 0.04)
    s.out("    Repositorio  : https://github.com/wellingtonsr1/SisPatrimonioPro.git (branch main)\r\n", 0.04)
    s.out("    Banco        : sispatrimoniopro_db (usuario sispat em 127.0.0.1:3306)\r\n", 0.04)
    s.out("    Aplicacao    : 0.0.0.0:8000\r\n", 0.04)
    s.out("    Tarefa       : sispatrimoniopro (roda como SYSTEM)\r\n", 0.04)
    s.out("\r\n", 0.6)
    s.out("  Confirmar e iniciar a instalacao? (s/N): ")
    s.pausa(1.1)
    s.digita("s\r\n", 0.09)
    s.ok("Confirmado.", 0.55)

    # ---- [1/16] Pacotes -----------------------------------------------------
    s.etapa(1, "Pacotes do sistema (Python, Git, MariaDB)")
    s.info("Instalando MariaDB Server via winget (MariaDB.Server; pode levar alguns minutos)...")
    s.pausa(2.4)                      # saída do winget omitida
    s.ok("Python 3.12 atende ao requisito (>= 3.10).")
    s.ok("Git disponivel.")
    s.info("Iniciando o servico do banco (MariaDB)...")
    s.pausa(1.2)
    s.ok("Servico de banco ativo: MariaDB")
    s.ok("Cliente de banco: C:\\Program Files\\MariaDB 11.4\\bin\\mysql.exe", 0.35)

    # ---- [2/16] Conectividade ----------------------------------------------
    s.etapa(2, "Verificacao de conectividade")
    s.ok("Repositorio acessivel e branch 'main' existe.", 0.35)

    # ---- [3/16] Clone --------------------------------------------------------
    s.etapa(3, "Codigo-fonte (clone)")
    s.ok("Repositorio clonado (branch main) em C:\\SisPatrimonioPro.", 0.35)

    # ---- [4/16] venv ---------------------------------------------------------
    s.etapa(4, "Ambiente virtual e dependencias")
    s.info("Instalando requirements.txt (do repositorio recem-clonado; leva alguns minutos)...")
    s.pausa(2.2)                      # pip omitido
    s.info("Garantindo cryptography e tzdata (autenticacao MySQL 8 / Timezone Windows)...")
    s.pausa(1.1)
    s.ok("Dependencias instaladas e validadas (imports OK).", 0.3)

    # ---- [5/16] URL ----------------------------------------------------------
    s.etapa(5, "Montagem da URL do banco")
    s.ok("DATABASE_URL montado com percent-encoding (senha nunca em argv/log).", 0.3)

    # ---- [6/16] Banco --------------------------------------------------------
    s.etapa(6, "Banco de dados (criacao/validacao)")
    s.ok("Acesso administrativo via root validado.", 0.5)
    s.ok("Banco 'sispatrimoniopro_db' pronto (criado ou ja existente; utf8mb4/utf8mb4_unicode_ci).")
    s.ok("Usuario 'sispat' (localhost e 127.0.0.1) garantido.")
    s.ok("Privilegios garantidos apenas em 'sispatrimoniopro_db'.* (sem privilegios globais - SR-003).", 0.35)

    # ---- [7/16] SSL ----------------------------------------------------------
    s.etapa(7, "Certificados SSL (HTTPS local)")
    s.info("IP da LAN para o SAN: 192.168.0.15", 0.6)
    s.ok("Certificados SSL gerados em data\\ssl - a aplicacao subira em HTTPS.", 0.35)

    # ---- [8/16] .env ---------------------------------------------------------
    s.etapa(8, "Arquivo de configuracao .env")
    s.ok(".env gerado com ACL restrita (equivalente 0600 - SR-002).", 0.35)

    # ---- [9/16] Conexao ------------------------------------------------------
    s.etapa(9, "Teste de conexao com o banco")
    s.ok("Conexao validada via DATABASE_URL (esquema mysql+pymysql).", 0.35)

    # ---- [10/16] Tarefa agendada --------------------------------------------
    s.etapa(10, "Tarefa agendada (servico)")
    s.ok("Tarefa agendada 'sispatrimoniopro' instalada (dispara no boot; reinicia ate 3x em falha).", 0.4)

    # ---- [11/16] Sanity ------------------------------------------------------
    s.etapa(11, "Sanity pre-start")
    s.ok("Arquivos do servico presentes (.env, venv, run.py).", 0.35)

    # ---- [12/16] Parada ------------------------------------------------------
    s.etapa(12, "Parada da tarefa de rodada anterior")
    s.ok("Tarefa sispatrimoniopro instalada, mas inativa - nada a parar.", 0.35)

    # ---- [13/16] init_db -----------------------------------------------------
    s.etapa(13, "Inicializacao do schema (init_db)")
    s.info("Executando init_db() do projeto (create_all + migracoes leves)...")
    s.pausa(1.6)
    s.ok("Schema verificado/criado via init_db() do projeto.", 0.3)

    # ---- [14/16] Start + health ---------------------------------------------
    s.etapa(14, "Start + health check")
    s.info("Aguardando /health (ate 120s)...")
    s.pausa(2.0)
    s.ok("Aplicacao saudavel: /health -> healthy", 0.4)

    # ---- [15/16] Bateria -----------------------------------------------------
    s.etapa(15, "Bateria pos-instalacao")
    s.ok("Python >= 3.10: OK", 0.05)
    s.ok("venv + dependencias: OK", 0.05)
    s.ok("Banco ativo (MariaDB): OK", 0.05)
    s.ok("Conexao com o banco: OK", 0.05)
    s.ok("Tabela base (users) existente: OK", 0.05)
    s.ok("Tarefa sispatrimoniopro ativa: OK", 0.05)
    s.ok("https://127.0.0.1:8000/health: OK", 0.05)
    s.ok("Bateria completa: todas as verificacoes passaram.", 0.4)

    # ---- [16/16] Auditoria ----------------------------------------------------
    s.etapa(16, "Auditoria de seguranca")
    s.ok("Auto-check: nenhuma credencial no log (SR-001).", 0.05)
    s.ok(".env com ACL restrita (equivalente 0600 - SR-002).", 0.05)
    s.ok("Usuario do banco sem privilegios globais (SR-003) - grants aplicados somente no banco da aplicacao.", 0.5)

    # ---- firewall (fora das 16 etapas, como no script) -----------------------
    s.ok("Regra de firewall de entrada criada para a porta 8000 (acesso via rede).", 0.6)

    # ---- Print-Summary (literal) ---------------------------------------------
    s.out("\r\n", 0.1)
    s.branco("  " + LINHAS, 0.12)
    s.ok("SisPatrimonio Pro instalado com sucesso (WINDOWS nativo)!", 0.12)
    s.branco("  " + LINHAS, 0.5)
    s.out("\r\n", 0.1)
    s.branco("  ACESSO")
    s.out("    Aplicacao    : https://192.168.0.15:8000\r\n", 0.03)
    s.out("    Swagger API  : https://192.168.0.15:8000/docs\r\n", 0.03)
    s.out("    Health check : https://192.168.0.15:8000/health\r\n", 0.03)
    s.out("    HTTPS        : importe C:\\SisPatrimonioPro\\data\\ssl\\ca.crt como CA confiavel nos aparelhos (1x).\r\n", 0.03)
    s.out("\r\n", 0.1)
    s.branco("  INSTALACAO")
    s.out("    Diretorio    : C:\\SisPatrimonioPro\r\n", 0.03)
    s.out("    Configuracao : C:\\SisPatrimonioPro\\.env (ACL restrita - contem credenciais)\r\n", 0.03)
    s.out("    Tarefa       : sispatrimoniopro (roda como SYSTEM no boot)\r\n", 0.03)
    s.out("    Log          : C:\\ProgramData\\sispatrimonio-install.log\r\n", 0.03)
    s.out("    Logs/Backups : C:\\SisPatrimonioPro\\data\\logs | C:\\SisPatrimonioPro\\data\\backups\r\n", 0.03)
    s.out("\r\n", 0.1)
    s.branco("  GERENCIAR O SERVICO")
    s.out("    Get-ScheduledTask -TaskName sispatrimoniopro        # estado\r\n", 0.03)
    s.out("    Start-ScheduledTask -TaskName sispatrimoniopro      # iniciar\r\n", 0.03)
    s.out("    Stop-ScheduledTask -TaskName sispatrimoniopro       # parar\r\n", 0.03)
    s.out("    Unregister-ScheduledTask -TaskName sispatrimoniopro # remover (o desinstalador faz isso)\r\n", 0.03)
    s.out("\r\n", 0.1)
    s.branco("  PRIMEIRO ADMINISTRADOR (escolha um caminho - nunca exibimos senhas)")
    s.out("    A) CLI (recomendado):\r\n", 0.03)
    s.out('       cd "C:\\SisPatrimonioPro"\r\n', 0.03)
    s.out('       .venv\\Scripts\\python.exe -m app.cli create-user --username admin --name "Administrador" --admin\r\n', 0.03)
    s.out("       (a senha e solicitada de forma oculta; minimo 8 caracteres)\r\n", 0.03)
    s.out("    B) Primeiro acesso: abra a aplicacao e use a pagina /setup\r\n", 0.03)
    s.out("       (disponivel enquanto nao existir nenhum usuario)\r\n", 0.03)
    s.out("    C) Variaveis de ambiente: AUTH_ADMIN_USERNAME/AUTH_ADMIN_PASSWORD\r\n", 0.03)
    s.out("       no .env antes do primeiro start (remova apos o primeiro login)\r\n", 0.03)
    s.out("\r\n", 0.1)
    s.out("  A senha do banco NAO aparece neste resumo nem no log - esta apenas\r\n", 0.03)
    s.out("  no .env (DATABASE_URL), com ACL restrita.\r\n", 0.03)
    s.branco("  " + LINHAS, 0.5)
    s.ok("Concluido.", 1.2)

    # ---- verificacao ao vivo ---------------------------------------------------
    s.out(PS1, 0.35)
    s.digita("Get-ScheduledTask -TaskName sispatrimoniopro | Select-Object TaskName,State")
    s.out("\r\n", 0.9)
    s.out("TaskName          State\r\n", 0.05)
    s.out("--------          -----\r\n", 0.05)
    s.out("sispatrimoniopro  Ready\r\n", 0.9)
    s.out(PS1, 0.3)
    s.digita("curl.exe -sk https://localhost:8000/health")
    s.out("\r\n", 1.0)
    s.out('{"status":"healthy","application":"ok","database":"ok","ad":"not_applicable"}\r\n', 1.1)
    s.out(PS1, 0.4)
    s.digita("exit", 0.07)
    s.out("\r\n", 0.5)
    return s


def main():
    if len(sys.argv) < 2:
        print("uso: make_windows_session.py <saida.cast>", file=sys.stderr)
        sys.exit(2)
    saida = sys.argv[1]
    sessao = construir()
    with open(saida, "w", encoding="utf-8") as fh:
        json.dump({
            "version": 2,
            "width": COLS,
            "height": ROWS,
            "timestamp": 1792000000,
            "env": {"TERM": "xterm-256color", "SHELL": "powershell"},
            "title": "Windows PowerShell - SisPatrimonio Pro (instalacao nativa install.ps1)",
            "bg": "#012456",
        }, fh, ensure_ascii=False)
        fh.write("\n")
        for ev in sessao.eventos:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"sessao: {saida} | {len(sessao.eventos)} eventos | "
          f"{sessao.t:.1f}s de relogio")


if __name__ == "__main__":
    main()
