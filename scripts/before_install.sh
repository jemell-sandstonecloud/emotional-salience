#!/bin/bash
set -e

echo "[before_install] Preparing for deployment..."

if systemctl is-active --quiet sandstone; then
    systemctl stop sandstone
    echo "[before_install] Stopped sandstone service"
fi

if [ -d /opt/sandstone ]; then
    find /opt/sandstone -mindepth 1 -not -name .env -not -path "*/venv/*" -not -name venv -delete 2>/dev/null || true
    echo "[before_install] Cleaned old deployment"
fi

echo "[before_install] Done"
