"""Servidor de homologação isolado da Feature 048 (porta 8001).

Substitui o engine do app.database por um SQLite temporário ANTES de importar
app.main — o lifespan (init_db) roda contra o SQLite; as migrações aditivas
de MariaDB são dispensadas (no SQLite o create_all já cria todas as colunas
novas, pois as tabelas nascem do zero).

Uso: .venv/bin/python scripts/homolog_048_serve.py
Admin: admin / homolog048 · Encerrar: Ctrl+C (banco temporário é removido).
"""
import os
import sys
import atexit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = "/tmp/homolog_048.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["AUTH_ADMIN_USERNAME"] = "admin"
os.environ["AUTH_ADMIN_PASSWORD"] = "homolog048"
os.environ["AUTH_PBKDF2_ITERATIONS"] = "1000"
os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ["BACKUP_AUTO_ENABLED"] = "false"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

eng = create_engine(
    f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False}
)

import app.database as db  # noqa: E402

db.engine = eng
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng)
# No SQLite as tabelas nascem completas via create_all; migrações aditivas de
# MariaDB (ALTER ... IF NOT EXISTS) são desnecessárias aqui.
db._ensure_schema_migrations = lambda: None

from app.main import app  # noqa: E402

atexit.register(lambda: os.path.exists(DB_PATH) and os.remove(DB_PATH))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
