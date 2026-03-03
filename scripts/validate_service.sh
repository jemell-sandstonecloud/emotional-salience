#!/bin/bash
set -e
echo "[validate] Checking Sandstone health..."

MAX_RETRIES=10
RETRY_INTERVAL=3

for i in $(seq 1 $MAX_RETRIES); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "[validate] Health check passed (attempt $i)"
        exit 0
    fi
    echo "[validate] Attempt $i/$MAX_RETRIES - HTTP $HTTP_CODE, retrying in ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

echo "[validate] FAILED - service did not become healthy"
exit 1
