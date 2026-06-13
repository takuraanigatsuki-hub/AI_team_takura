#!/bin/bash
CID=$(docker compose -f /root/AI_team_takura/docker-compose.yml ps -q ai-team-room)
docker cp /root/AI_team_takura/static/landing.html "$CID:/app/static/landing.html"
docker cp /root/AI_team_takura/static/css/landing.css "$CID:/app/static/css/landing.css"
docker cp /root/AI_team_takura/static/js/landing.js "$CID:/app/static/js/landing.js"
echo OK
