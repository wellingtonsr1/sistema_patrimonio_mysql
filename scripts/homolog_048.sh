#!/usr/bin/env bash
# Homologação da Feature 048 — servidor ISOLADO na porta 8001 com banco
# SQLite temporário (nada toca no MariaDB de produção).
set -e
cd "$(dirname "$0")/.."

export DATABASE_URL="sqlite:////tmp/homolog_048.db"
export AUTH_ADMIN_USERNAME="admin"
export AUTH_ADMIN_PASSWORD="homolog048"
export AUTH_PBKDF2_ITERATIONS="1000"
export AUTH_COOKIE_SECURE="false"
export BACKUP_AUTO_ENABLED="false"
export SCHEDULER_DISABLED="1"

rm -f /tmp/homolog_048.db

echo "=== Homologação 048 — http://localhost:8001 (admin / homolog048) ==="
echo "Pressione Ctrl+C para encerrar e o banco temporário será removido."
trap 'rm -f /tmp/homolog_048.db' EXIT
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
