"""Backup / restore комнаты."""

import json
import os
import zipfile
from datetime import datetime
from io import BytesIO

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIRS = ["data", "knowledge", "output"]
SKIP_FILES = {".env"}


def create_backup() -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        meta = {"created_at": datetime.now().isoformat(), "version": "1.0"}
        zf.writestr("backup_meta.json", json.dumps(meta, indent=2))
        for folder in BACKUP_DIRS:
            base = os.path.join(PROJECT_ROOT, folder)
            if not os.path.isdir(base):
                continue
            for root, _, files in os.walk(base):
                for fn in files:
                    if fn in SKIP_FILES:
                        continue
                    full = os.path.join(root, fn)
                    arc = os.path.relpath(full, PROJECT_ROOT)
                    zf.write(full, arc)
    buf.seek(0)
    return buf.read()
