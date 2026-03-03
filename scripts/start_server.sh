#!/bin/bash
set -e

echo "[start_server] Starting Sandstone backend..."

# Create systemd service if it doesn't exist
if [ ! -f /etc/systemd/system/sandstone.service ]; then
    sudo tee /etc/systemd/system/sandstone.service > /dev/null << 'EOF'
[Unit]
Description=Sandstone Flask API
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/sandstone
EnvironmentFile=/opt/sandstone/.env
ExecStart=/opt/sandstone/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile /var/log/sandstone/access.log \
    --error-logfile /var/log/sandstone/error.log \
    app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    sudo mkdir -p /var/log/sandstone
    sudo chown ubuntu:ubuntu /var/log/sandstone
    sudo systemctl daemon-reload
    sudo systemctl enable sandstone
    echo "[start_server] Created systemd service"
fi

sudo systemctl start sandstone
echo "[start_server] Sandstone is running"
