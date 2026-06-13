#!/usr/bin/env bash
# Восстановление из backups/ai-team-backup-*.tar.gz
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 backups/ai-team-backup-YYYYMMDD-HHMMSS.tar.gz"
  exit 1
fi

ARCHIVE="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f "$ARCHIVE" ]; then
  echo "File not found: $ARCHIVE"
  exit 1
fi

read -r -p "Перезаписать data/, output/, knowledge/? [y/N] " ans
if [ "$ans" != "y" ] && [ "$ans" != "Y" ]; then
  echo "Cancelled"
  exit 0
fi

echo "==> Pre-backup current state"
bash "$ROOT/scripts/backup-data.sh" || true

echo "==> Extract $ARCHIVE"
tar -xzf "$ARCHIVE" -C "$ROOT"
echo "OK — перезапустите: bash scripts/deploy-vps.sh"
