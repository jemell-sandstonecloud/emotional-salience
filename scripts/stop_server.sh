#!/bin/bash
echo "[stop_server] Stopping Sandstone backend..."
if systemctl is-active --quiet sandstone; then
    sudo systemctl stop sandstone
    echo "[stop_server] Sandstone stopped"
else
    echo "[stop_server] Sandstone was not running"
fi
exit 0
