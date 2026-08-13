#!/bin/bash
# ====================
# Server Heartbeat Cron Job
# ====================
# This script sends a heartbeat ping to the server every 10 minutes.
# Usage: Add this line to your crontab:
#   */10 * * * * /path/to/heartbeat.sh >> /var/log/heartbeat.log 2>&1

HEARTBEAT_URL="http://localhost:8000/api/health"
PROJECT_DIR="/path/to/cnpi_api"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Sending heartbeat to: $HEARTBEAT_URL"

cd "$PROJECT_DIR"
python manage.py heartbeat -t "$HEARTBEAT_URL" > /dev/null 2>&1

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Heartbeat completed."