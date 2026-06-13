#!/bin/bash
set -e
CID=$(docker compose -f /root/AI_team_takura/docker-compose.yml ps -q ai-team-room)
docker cp /root/AI_team_takura/app.py "$CID:/app/app.py"
docker cp /root/AI_team_takura/room/user_auth.py "$CID:/app/room/user_auth.py"
docker cp /root/AI_team_takura/static/landing.html "$CID:/app/static/landing.html"
docker cp /root/AI_team_takura/static/desktop.html "$CID:/app/static/desktop.html"
docker cp /root/AI_team_takura/static/portal.html "$CID:/app/static/portal.html"
docker cp /root/AI_team_takura/static/js/landing.js "$CID:/app/static/js/landing.js"
docker cp /root/AI_team_takura/static/js/desktop-app.js "$CID:/app/static/js/desktop-app.js"
docker cp /root/AI_team_takura/static/js/profile.js "$CID:/app/static/js/profile.js"
docker cp /root/AI_team_takura/static/js/auth-fields.js "$CID:/app/static/js/auth-fields.js"
docker cp /root/AI_team_takura/static/css/landing.css "$CID:/app/static/css/landing.css"
docker cp /root/AI_team_takura/static/css/desktop.css "$CID:/app/static/css/desktop.css"
docker cp /root/AI_team_takura/static/css/main.css "$CID:/app/static/css/main.css"
docker restart "$CID"
echo "deploy ok"
