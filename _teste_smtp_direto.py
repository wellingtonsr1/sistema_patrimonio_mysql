"""Teste direto do SMTP configurado — feature 030 (utilitário de diagnóstico).

Reutiliza o MESMO provedor usado pelo sistema (app.services.email_provider),
então o resultado reflete exatamente o comportamento do SisPatrimônio:
- lê SMTP_* do .env (via app.config / dotenv);
- usa o mesmo login, TLS e timeout;
- mesma sanitização de erros (nunca ecoa senha).

NÃO cria movimentação, NÃO grava Notification, NÃO grava auditoria —
é apenas uma sonda de envio.

Uso (PowerShell, na raiz do projeto):
    python _teste_smtp_direto.py                    # envia p/ SMTP_FROM
    python _teste_smtp_direto.py outro@dominio.br   # envia p/ outro destino
"""

import sys

from app.services.email_provider import SMTPEmailProvider

TAG = "[SisPatrimônio Pro] Teste SMTP"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from app import config

    print("=== Configuração carregada do .env ===")
    print(f"  host      : {config.SMTP_HOST or '(vazio)'}")
    print(f"  porta     : {config.SMTP_PORT}")
    print(f"  TLS       : {config.SMTP_USE_TLS}")
    print(f"  usuario   : {config.SMTP_USERNAME or '(vazio — envio anônimo)'}")
    print(f"  senha     : {'<definida>' if config.SMTP_PASSWORD else '(vazia)'}")
    print(f"  remetente : {config.SMTP_FROM or '(vazio)'}")
    print(f"  timeout   : {config.SMTP_SEND_TIMEOUT}s")

    destino = sys.argv[1] if len(sys.argv) > 1 else (
        config.SMTP_FROM or config.SMTP_USERNAME
    )
    if not destino:
        print("\nERRO: sem destinatário (informe como argumento ou defina SMTP_FROM).")
        return 2

    corpo = (
        "Este é um teste de envio SMTP do SisPatrimônio Pro (feature 030).\n"
        "Se você recebeu este e-mail, o relay institucional está aceitando\n"
        "as credenciais configuradas no .env do servidor.\n\n"
        "Nenhuma movimentação foi criada; nenhum registro foi gravado.\n"
    )

    print(f"\nEnviando para: {destino} ...")
    try:
        SMTPEmailProvider().send(
            subject=f"{TAG} — {destino}",
            body=corpo,
            recipients=[destino],
        )
    except Exception as exc:  # mensagem já vem sanitizada do provider
        print(f"\n❌ FALHA no envio: {exc}")
        print("\nPistas comuns:")
        print("  • 535/554 Auth...  → usuário/senha recusados (confira SMTP_USERNAME —")
        print("    alguns Postfix exigem só a parte antes do @)")
        print("  • 554 Access denied sem AUTH → relay recusa o IP (precisa de conta ou")
        print("    de whitelist do IP na TI)")
        print("  • Timeout/Connection refused → host/porta/bloqueio de rede")
        return 1

    print("\n✅ E-MAIL ENVIADO — verifique a caixa de entrada (e o spam).")
    print("   O relay aceitou a mensagem; entrega final depende do servidor de destino.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
