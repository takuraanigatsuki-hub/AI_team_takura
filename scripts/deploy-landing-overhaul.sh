#!/bin/bash
set -e
CID=$(docker compose -f /root/AI_team_takura/docker-compose.yml ps -q ai-team-room)
for f in app.py room/user_auth.py; do
  docker cp "/root/AI_team_takura/$f" "$CID:/app/$f"
done
for f in landing.html portal.html static/js/landing.js static/js/support-tickets.js static/js/auth-fields.js static/css/landing.css static/css/main.css; do
  docker cp "/root/AI_team_takura/static/${f#static/}" "$CID:/app/static/${f#static/}" 2>/dev/null || \
  docker cp "/root/AI_team_takura/$f" "$CID:/app/$f"
done
docker cp /root/AI_team_takura/app.py "$CID:/app/app.py"
docker cp /root/AI_team_takura/static/landing.html "$CID:/app/static/landing.html"
docker cp /root/AI_team_takura/static/js/landing.js "$CID:/app/static/js/landing.js"
docker cp /root/AI_team_takura/static/js/support-tickets.js "$CID:/app/static/js/support-tickets.js"
docker cp /root/AI_team_takura/static/css/landing.css "$CID:/app/static/css/landing.css"
docker restart "$CID"
echo deploy landing ok
