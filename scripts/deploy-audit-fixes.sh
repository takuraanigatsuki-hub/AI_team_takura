#!/bin/bash
set -e
ROOT=/root/AI_team_takura
CID=$(docker compose -f "$ROOT/docker-compose.yml" ps -q ai-team-room)

for f in app.py room/client_access.py room/desktop_auth.py; do
  docker cp "$ROOT/$f" "$CID:/app/$f"
done

for f in \
  static/portal.html static/index.html static/landing.html static/desktop.html \
  static/js/ui-core.js static/js/app.js static/js/landing.js \
  static/js/desktop-app.js static/js/download-page.js static/js/auth-device.js
do
  docker cp "$ROOT/$f" "$CID:/app/$f"
done

docker restart "$CID"
sleep 22
curl -sf -X POST http://127.0.0.1/api/auth/device/start | head -c 160
echo
curl -sf -o /dev/null -w "backup=%{http_code}\n" http://127.0.0.1/api/backup/download
echo OK
