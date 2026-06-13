#!/usr/bin/env bash
# Резервная копия data/, output/, knowledge/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${BACKUP_DIR:-$ROOT/backups}"
ARCHIVE="$OUT_DIR/ai-team-backup-$STAMP.tar.gz"
KEEP="${BACKUP_KEEP:-14}"

mkdir -p "$OUT_DIR"

echo "==> Backup -> $ARCHIVE"
tar -czf "$ARCHIVE" \
  --exclude='data/rag/*.db-journal' \
  data output knowledge 2>/dev/null || tar -czf "$ARCHIVE" data output knowledge

SIZE="$(du -h "$ARCHIVE" | cut -f1)"
echo "    size: $SIZE"

# Ротация
if [ "$KEEP" -gt 0 ]; then
  ls -1t "$OUT_DIR"/ai-team-backup-*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
fi

# Опционально: rclone в облако
if [ -n "${RCLONE_REMOTE:-}" ] && command -v rclone >/dev/null 2>&1; then
  echo "==> rclone copy -> $RCLONE_REMOTE"
  rclone copy "$ARCHIVE" "$RCLONE_REMOTE" --progress
fi

echo "OK"
