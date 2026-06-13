#!/bin/bash
set -e
ROOT=/root/AI_team_takura
CID=$(docker compose -f "$ROOT/docker-compose.yml" ps -q ai-team-room)
for f in \
  static/portal.html static/index.html \
  static/css/shell-nav.css static/css/premium-theme.css \
  static/js/sidebar-nav.js
do
  docker cp "$ROOT/$f" "$CID:/app/$f"
done
docker restart "$CID"
echo OK
