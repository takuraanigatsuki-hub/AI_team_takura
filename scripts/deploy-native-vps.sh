#!/bin/bash
set -e
cd /root/AI_team_takura
CID=$(docker compose ps -q ai-team-room)
docker cp dist/AI_Team_Room.exe "$CID:/app/dist/AI_Team_Room.exe"
docker cp dist/AI_Team_Room_Setup.exe "$CID:/app/dist/AI_Team_Room_Setup.exe"
docker cp app.py "$CID:/app/app.py"
docker cp room/client_access.py "$CID:/app/room/client_access.py"
docker cp static/landing.html "$CID:/app/static/landing.html"
docker cp static/download.html "$CID:/app/static/download.html"
docker cp static/desktop.html "$CID:/app/static/desktop.html"
docker cp static/js/landing.js "$CID:/app/static/js/landing.js"
docker cp static/js/desktop-app.js "$CID:/app/static/js/desktop-app.js"
docker cp static/js/download-page.js "$CID:/app/static/js/download-page.js"
docker restart "$CID"
sleep 25
curl -sf http://127.0.0.1/api/health
echo
curl -s -o /dev/null -w "setup:%{http_code} " http://127.0.0.1/api/downloads/desktop/win/setup
curl -s -o /dev/null -w "ws-browser:%{http_code} " http://127.0.0.1/workspace
curl -s -o /dev/null -w "ws-app:%{http_code} " -H "User-Agent: AITeamRoomDesktop/1.1" http://127.0.0.1/workspace
curl -s -o /dev/null -w "portal:%{http_code}" http://127.0.0.1/portal
echo
