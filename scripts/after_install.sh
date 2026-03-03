#!/bin/bash
set -e
echo "[after_install] Installing dependencies..."
cd /opt/sandstone

# Create virtual environment if it doesn't exist
if [ ! -d venv ]; then
    python3 -m venv venv
    echo "[after_install] Created virtual environment"
fi

# Activate and install
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database schema using env vars from .env
echo "[after_install] Running schema migrations..."
set -a
source .env
set +a

if [ -n "$DB_HOST" ] && [ -n "$DB_PASSWORD" ]; then
    export PGPASSWORD="$DB_PASSWORD"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f db/schema.sql 2>/dev/null || true
    unset PGPASSWORD
    echo "[after_install] Schema applied"
else
    echo "[after_install] Skipping schema - DB_HOST or DB_PASSWORD not set"
fi

echo "[after_install] Done"
