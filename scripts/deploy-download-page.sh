#!/bin/bash
CID=$(docker compose -f /root/AI_team_takura/docker-compose.yml ps -q ai-team-room)
docker cp /root/AI_team_takura/static/download.html "$CID:/app/static/download.html"
docker cp /root/AI_team_takura/static/js/download-page.js "$CID:/app/static/js/download-page.js"
docker cp /root/AI_team_takura/static/css/desktop.css "$CID:/app/static/css/desktop.css"
echo OK
