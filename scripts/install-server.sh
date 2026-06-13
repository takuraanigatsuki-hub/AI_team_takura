#!/usr/bin/env bash
# Первичная установка на чистый VPS (Ubuntu/Debian)
# Запуск: curl -fsSL ... | bash   или   bash scripts/install-server.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/takuraanigatsuki-hub/AI_team_takura.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/AI_team_takura}"

echo "==> Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" 2>/dev/null || true
  echo "    Перелогиньтесь или выполните: newgrp docker"
fi

echo "==> Git"
if ! command -v git >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y git
fi

echo "==> Клонирование $REPO_URL"
if [ -d "$INSTALL_DIR/.git" ]; then
  cd "$INSTALL_DIR"
  git pull origin main || true
else
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

mkdir -p data output knowledge backups

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "!!! Отредактируйте .env: nano $INSTALL_DIR/.env"
  echo "    Обязательно: OPENAI_API_KEY, APP_DOMAIN, POSTGRES_PASSWORD"
fi

echo "==> Готово. Дальше:"
echo "    cd $INSTALL_DIR"
echo "    nano .env"
echo "    bash scripts/deploy-vps.sh"
