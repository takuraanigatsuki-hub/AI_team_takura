"""One-click deploy — экспорт preview как standalone bundle."""

import json
import os
import shutil
import zipfile
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "deploy")
LATEST_ZIP = os.path.join(OUTPUT_DIR, "latest.zip")
MANIFEST = os.path.join(OUTPUT_DIR, "manifest.json")


def _read_latest_site() -> tuple[str, str]:
    latest = os.path.join(os.path.dirname(__file__), "..", "output", "sites", "latest.html")
    if os.path.exists(latest):
        with open(latest, "r", encoding="utf-8") as f:
            return f.read(), "index.html"
    return _default_landing(), "index.html"


def _default_landing() -> str:
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><title>AI Team Preview</title>
<style>body{font-family:system-ui;display:flex;align-items:center;justify-content:center;min-height:100vh;background:#1a1d2e;color:#fff;margin:0}
.card{text-align:center;padding:40px}.btn{display:inline-block;margin-top:16px;padding:12px 24px;background:#6c63ff;color:#fff;border-radius:8px;text-decoration:none}</style></head>
<body><div class="card"><h1>🤖 AI Team Room</h1><p>Deploy preview — дайте Соне задачу с UI</p>
<a class="btn" href="/">← Вернуться в студию</a></div></body></html>"""


def create_deploy_bundle(title: str = "AI Team Preview", include_readme: bool = True) -> dict:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    html, _ = _read_latest_site()

    staging = os.path.join(OUTPUT_DIR, "_staging")
    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    with open(os.path.join(staging, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    if include_readme:
        readme = f"""# {title}

Exported from AI Team Room · {datetime.now().isoformat()}

## Deploy

- **GitHub Pages**: push `index.html` to `gh-pages` branch
- **Netlify**: drag & drop this folder
- **Vercel**: `vercel --prod` in this directory

Live preview: `/api/sites/latest`
"""
        with open(os.path.join(staging, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme)

    if os.path.exists(LATEST_ZIP):
        os.remove(LATEST_ZIP)
    with zipfile.ZipFile(LATEST_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(staging):
            for name in files:
                path = os.path.join(root, name)
                zf.write(path, os.path.relpath(path, staging))

    shutil.rmtree(staging)

    info = {
        "ok": True,
        "title": title,
        "created_at": datetime.now().isoformat(),
        "download_url": "/api/deploy/download",
        "preview_url": "/api/sites/latest",
        "size_bytes": os.path.getsize(LATEST_ZIP),
        "instructions": [
            "Скачайте ZIP и загрузите на Netlify Drop или Vercel",
            "Или откройте /api/sites/latest для локального preview",
            "GitHub Pages: push index.html в gh-pages",
        ],
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    return info
