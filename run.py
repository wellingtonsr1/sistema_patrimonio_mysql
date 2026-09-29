"""
Script de inicialização do SisPatrimônio Pro.
Executa o servidor FastAPI com Uvicorn.
"""

import uvicorn
import logging

from app.config import APP_HOST, APP_PORT, APP_NAME
from app.database import init_db

if __name__ == "__main__":
    print(f"-> Inicializando banco de dados do {APP_NAME}...")
    init_db()
    
    # Configura logs técnicos centralizados com rotação
    from app.logging_config import configure_logging
    configure_logging()
    
    # HTTPS nativo (feature 056): TLS terminado no próprio uvicorn quando os
    # caminhos do certificado/chave estiverem definidos no ambiente
    # (APP_SSL_CERTFILE + APP_SSL_KEYFILE). Sem eles, HTTP puro — nada muda.
    # O PWA/coleta offline (033) exige secure context: em origens por IP só há
    # Service Worker sobre HTTPS (prova de campo da 053).
    from app.config import APP_SSL_CERTFILE, APP_SSL_KEYFILE

    ssl_args = {}
    if APP_SSL_CERTFILE and APP_SSL_KEYFILE:
        ssl_args = {"ssl_certfile": APP_SSL_CERTFILE, "ssl_keyfile": APP_SSL_KEYFILE}
    esquema = "https" if ssl_args else "http"
    
    print("=" * 60)
    print(f"[OK] {APP_NAME} iniciado com sucesso!")
    print(f"[>>] Interface Web: {esquema}://{APP_HOST}:{APP_PORT}")
    print(f"[>>] Swagger API Docs: {esquema}://{APP_HOST}:{APP_PORT}/docs")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=False,
        **ssl_args,
    )
