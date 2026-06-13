#!/bin/bash
CID=$(docker compose -f /root/AI_team_takura/docker-compose.yml ps -q ai-team-room)
docker cp /root/AI_team_takura/middleware/security.py "$CID:/app/middleware/security.py"
docker cp /root/AI_team_takura/static/js/auth-device.js "$CID:/app/static/js/auth-device.js"
docker cp /root/AI_team_takura/static/js/desktop-app.js "$CID:/app/static/js/desktop-app.js"
docker cp /root/AI_team_takura/static/auth-device.html "$CID:/app/static/auth-device.html"
docker cp /root/AI_team_takura/static/desktop.html "$CID:/app/static/desktop.html"
docker restart "$CID"
sleep 20
curl -sf -X POST http://127.0.0.1/api/auth/device/start | head -c 120
echo
