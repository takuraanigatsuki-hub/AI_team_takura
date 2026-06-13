#!/usr/bin/env bash
# Обновление и перезапуск на VPS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_BEFORE="${BACKUP_BEFORE:-1}"

mkdir -p data output knowledge backups

if [ "$BACKUP_BEFORE" = "1" ] && [ -d data ] && [ "$(ls -A data 2>/dev/null || true)" ]; then
  bash "$ROOT/scripts/backup-data.sh" || echo "Backup skipped (non-fatal)"
fi

echo "==> git pull"
git fetch origin main
git pull origin main

echo "==> docker compose up ($COMPOSE_FILE)"
docker compose -f "$COMPOSE_FILE" build --pull
docker compose -f "$COMPOSE_FILE" up -d

echo "==> status"
docker compose -f "$COMPOSE_FILE" ps

DOMAIN="${APP_DOMAIN:-}"
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a && source .env && set +a
  DOMAIN="${APP_DOMAIN:-localhost}"
fi

echo ""
echo "OK — приложение запущено."
if [ "$DOMAIN" != "localhost" ] && [ -n "$DOMAIN" ]; then
  echo "    https://${DOMAIN}/app"
else
  echo "    http://$(hostname -I 2>/dev/null | awk '{print $1}'):80/app"
  echo "    (задайте APP_DOMAIN в .env для HTTPS)"
fi
