#!/bin/bash
# Полный hot-deploy на VPS (без git на сервере)
set -euo pipefail
ROOT="/root/AI_team_takura"
cd "$ROOT"
CID=$(docker compose -f docker-compose.yml ps -q ai-team-room)
if [ -z "$CID" ]; then
  echo "Container ai-team-room not found"
  exit 1
fi

copy() {
  local src="$1"
  local dest="${2:-$1}"
  if [ -f "$src" ] || [ -d "$src" ]; then
    docker cp "$ROOT/$src" "$CID:/app/$dest"
  fi
}

copy app.py
copy config.py
copy knowledge_store.py
copy room
copy integrations
copy agents
copy tests
copy static
copy android-companion
copy scripts

mkdir -p "$ROOT/dist"
copy dist/AI_Team_Room_Setup.exe dist/AI_Team_Room_Setup.exe
copy dist/AI_Team_Room.exe dist/AI_Team_Room.exe
if [ -f "$ROOT/dist/AI_Team_Room.apk" ]; then
  copy dist/AI_Team_Room.apk dist/AI_Team_Room.apk
fi

docker restart "$CID"
sleep 20

echo "==> health"
curl -sf "http://127.0.0.1/api/health" | head -c 200 || true
echo ""
curl -s -o /dev/null -w "landing:%{http_code} " "http://127.0.0.1/"
curl -s -o /dev/null -w "mobile:%{http_code} " "http://127.0.0.1/mobile"
curl -s -o /dev/null -w "downloads:%{http_code} " "http://127.0.0.1/api/downloads/info"
curl -s -o /dev/null -w "setup:%{http_code} " "http://127.0.0.1/api/downloads/desktop/win/setup"
if [ -f "$ROOT/dist/AI_Team_Room.apk" ]; then
  curl -s -o /dev/null -w "apk:%{http_code} " "http://127.0.0.1/api/downloads/android/apk"
fi
echo ""
echo "OK deploy-full"
