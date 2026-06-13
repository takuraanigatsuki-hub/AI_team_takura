#!/usr/bin/env bash
# Полная установка на чистом Ubuntu (REG.RU / VPS)
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/takuraanigatsuki-hub/AI_team_takura.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/AI_team_takura}"
USE_PROD="${USE_PROD:-0}"

echo "==> System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl ca-certificates

echo "==> Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
if ! docker compose version >/dev/null 2>&1; then
  apt-get install -y -qq docker-compose-plugin 2>/dev/null || true
fi

echo "==> Repository"
if [ -d "$INSTALL_DIR/.git" ]; then
  cd "$INSTALL_DIR"
  git fetch origin main
  git reset --hard origin/main
else
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

mkdir -p data output knowledge backups

if [ -f /tmp/ai-team.env ]; then
  cp /tmp/ai-team.env "$INSTALL_DIR/.env"
  chmod 600 "$INSTALL_DIR/.env"
  echo "    .env installed from upload"
elif [ ! -f "$INSTALL_DIR/.env" ]; then
  cp .env.production.example .env 2>/dev/null || cp .env.example .env
  echo "    WARNING: edit .env manually"
fi

echo "==> Start containers"
if [ "$USE_PROD" = "1" ]; then
  docker compose -f docker-compose.prod.yml build --pull
  docker compose -f docker-compose.prod.yml up -d
  COMPOSE="docker compose -f docker-compose.prod.yml"
else
  docker compose build --pull
  docker compose up -d
  COMPOSE="docker compose"
fi

echo "==> Wait for health"
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "    health OK"
    break
  fi
  sleep 3
done

if [ -n "${OWNER_EMAIL:-}" ] && [ -n "${OWNER_PASSWORD:-}" ]; then
  echo "==> Create owner"
  $COMPOSE exec -T ai-team-room python scripts/create_owner.py \
    --email "$OWNER_EMAIL" --password "$OWNER_PASSWORD" --name "${OWNER_NAME:-Owner}" || true
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo ""
echo "=== DONE ==="
$COMPOSE ps
echo ""
echo "Open: http://${IP}:8000/app"
if [ -f .env ] && grep -q '^APP_DOMAIN=' .env; then
  DOM="$(grep '^APP_DOMAIN=' .env | cut -d= -f2- | tr -d '\r')"
  if [ "$DOM" != "localhost" ] && [ -n "$DOM" ]; then
    echo "Or:   https://${DOM}/app"
  fi
fi
