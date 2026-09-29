"""Gera CA local + certificado de servidor para HTTPS nativo (feature 056).

Objetivo (achado da prova de campo da 053): o PWA/coleta offline (033) só
funciona em secure context — via IP puro (http://10.39.x.x:8000) o Service
Worker não registra. Este script cria, com o openssl CLI (sem dependências
Python novas):

  data/ssl/ca.crt       — CA local a importar nos aparelhos (uma vez)
  data/ssl/ca.key       — chave da CA (local, NUNCA versionada)
  data/ssl/server.crt   — certificado do servidor com SAN do IP da LAN
  data/ssl/server.key   — chave do servidor (local, NUNCA versionada)

SAN gerado: IP:<ip-lan>, DNS:localhost, DNS:<hostname>,
DNS:sispatrimoniopro.local (o CN legado do cert DER commitado).

Uso:
    python scripts/gera_cert_dev.py              # detecta o IP da LAN
    python scripts/gera_cert_dev.py --ip 10.39.0.16
    python scripts/gera_cert_dev.py --force      # regera (apaga os existentes)

Validação no aparelho: importar data/ssl/ca.crt como CA confiável e acessar
https://<ip>:8000 com APP_SSL_CERTFILE/APP_SSL_KEYFILE no .env (run.py cuida
do resto). Ver docs/HTTPS_LOCAL.md (seção Windows nativo).
"""
import argparse
import socket
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SSL_DIR = RAIZ / "data" / "ssl"

VALIDADE_CA_DIAS = "3650"   # ~10 anos
VALIDADE_SERVER_DIAS = "825"  # limite prudente p/ cert de servidor em CA privada


def ip_lan() -> str:
    """IP da LAN sem enviar pacotes: socket UDP 'conectado' a um endpoint
    de rota padrão e leitura do getsockname() (não há tráfego real)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    finally:
        s.close()
    if ip.startswith(("127.", "169.254.")):
        raise SystemExit(
            f"IP detectado ({ip}) é loopback/link-local — informe --ip <ip-da-lan>."
        )
    return ip


def rodar(cmd: list, descricao: str) -> None:
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        print(f"[ERRO] {descricao}:\n{resultado.stderr}")
        sys.exit(1)
    print(f"[OK] {descricao}")


def main() -> None:
    parser = argparse.ArgumentParser(description="CA local + cert com SAN do IP (056)")
    parser.add_argument("--ip", help="IP da LAN (default: detectado automaticamente)")
    parser.add_argument("--force", action="store_true", help="regera mesmo se existir")
    args = parser.parse_args()

    openssl = "openssl"
    ip = args.ip or ip_lan()
    hostname = socket.gethostname()
    SSL_DIR.mkdir(parents=True, exist_ok=True)

    ca_key, ca_crt = SSL_DIR / "ca.key", SSL_DIR / "ca.crt"
    srv_key, srv_csr, srv_crt = SSL_DIR / "server.key", SSL_DIR / "server.csr", SSL_DIR / "server.crt"

    existentes = [p for p in (ca_key, ca_crt, srv_key, srv_crt) if p.exists()]
    if existentes and not args.force:
        raise SystemExit(
            "Certificados já existem em data/ssl/ "
            f"({', '.join(p.name for p in existentes)}). Use --force para regerar."
        )
    for p in existentes:
        p.unlink()

    print(f"-> IP da LAN: {ip} (hostname: {hostname})")

    # 1) CA local (self-signed, subject padrão da CA)
    rodar(
        [openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(ca_key), "-out", str(ca_crt),
         "-days", VALIDADE_CA_DIAS,
         "-subj", "/CN=SisPatrimonio Pro - CA local (dev)/O=IPMjp"],
        "CA local criada (ca.crt / ca.key)",
    )

    # 2) Chave + CSR do servidor
    rodar(
        [openssl, "req", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(srv_key), "-out", str(srv_csr),
         "-subj", f"/CN={ip}/O=IPMjp"],
        "chave e CSR do servidor geradas",
    )

    # 3) Extensões: SAN (IP + DNS) + usos de servidor
    extfile = SSL_DIR / "_ext.cnf"
    extfile.write_text(
        "subjectAltName = "
        f"IP:{ip},DNS:localhost,DNS:{hostname},DNS:sispatrimoniopro.local\n"
        "basicConstraints = CA:FALSE\n"
        "keyUsage = digitalSignature, keyEncipherment\n"
        "extendedKeyUsage = serverAuth\n",
        encoding="ascii",
    )
    rodar(
        [openssl, "x509", "-req", "-in", str(srv_csr),
         "-CA", str(ca_crt), "-CAkey", str(ca_key), "-CAcreateserial",
         "-out", str(srv_crt),
         "-days", VALIDADE_SERVER_DIAS, "-extfile", str(extfile)],
        "certificado do servidor assinado pela CA (SAN: "
        f"IP:{ip}, localhost, {hostname}, sispatrimoniopro.local)",
    )
    extfile.unlink()
    srv_csr.unlink(missing_ok=True)

    print("=" * 60)
    print("[>>] Pronto em data/ssl/:")
    print("     ca.crt     -> importe como CA confiável nos aparelhos (1x)")
    print("     server.crt -> APP_SSL_CERTFILE")
    print("     server.key -> APP_SSL_KEYFILE  (NUNCA versionar/compartilhar)")
    print(f"[>>] Depois: https://{ip}:{APP_PORT_DICA()}")


def APP_PORT_DICA() -> str:
    try:
        from app.config import APP_PORT
        return str(APP_PORT)
    except Exception:
        return "8000"


if __name__ == "__main__":
    main()
