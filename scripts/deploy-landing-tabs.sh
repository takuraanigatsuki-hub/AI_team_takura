#!/bin/bash
set -e
ROOT=/root/AI_team_takura
CID=$(docker compose -f "$ROOT/docker-compose.yml" ps -q ai-team-room)
for f in static/landing.html static/css/landing.css static/js/landing.js; do
  docker cp "$ROOT/$f" "$CID:/app/$f"
done
docker restart "$CID"
echo OK
