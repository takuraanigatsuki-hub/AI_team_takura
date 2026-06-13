"""Diff и экспорт handoff для Sonya Design Studio."""

import difflib
import io
import json
import zipfile
from typing import Optional

from integrations.sonya_studio import _find_project, _load_store, get_project


def _get_version_raw(p: dict, version_ref: str) -> Optional[dict]:
    """version_ref — id (ver-...) или номер версии (1, 2, ...)."""
    versions = p.get("versions") or []
    if not versions:
        return None
    if str(version_ref).startswith("ver-"):
        return next((v for v in versions if v.get("id") == version_ref), None)
    try:
        num = int(version_ref)
        return next((v for v in versions if v.get("version_num") == num), None)
    except (TypeError, ValueError):
        return None


def compare_versions(project_id: str, from_ref: str, to_ref: str) -> Optional[dict]:
    store = _load_store()
    p = _find_project(store, project_id)
    if not p:
        return None

    v_from = _get_version_raw(p, from_ref)
    v_to = _get_version_raw(p, to_ref)
    if not v_from or not v_to:
        return None

    code_from = (v_from.get("react_code") or "").splitlines()
    code_to = (v_to.get("react_code") or "").splitlines()
    diff_lines = list(difflib.unified_diff(
        code_from, code_to,
        fromfile=f"v{v_from.get('version_num')}",
        tofile=f"v{v_to.get('version_num')}",
        lineterm="",
    ))

    colors_from = set(v_from.get("colors") or [])
    colors_to = set(v_to.get("colors") or [])

    task_from = v_from.get("task") or ""
    task_to = v_to.get("task") or ""
    task_changed = task_from.strip() != task_to.strip()

    return {
        "project_id": project_id,
        "from": {
            "id": v_from.get("id"),
            "version_num": v_from.get("version_num"),
            "title": v_from.get("title"),
        },
        "to": {
            "id": v_to.get("id"),
            "version_num": v_to.get("version_num"),
            "title": v_to.get("title"),
        },
        "summary": {
            "lines_added": sum(1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++")),
            "lines_removed": sum(1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---")),
            "colors_added": sorted(colors_to - colors_from),
            "colors_removed": sorted(colors_from - colors_to),
            "task_changed": task_changed,
        },
        "task_from": task_from,
        "task_to": task_to,
        "diff": "\n".join(diff_lines[:400]),
        "diff_truncated": len(diff_lines) > 400,
    }


def build_handoff_package(project_id: str) -> Optional[dict]:
    project = get_project(project_id)
    if not project:
        return None
    current = project.get("current_version") or {}
    handoff = project.get("figma_handoff") or {}

    return {
        "schema": "sonya-studio-handoff/v1",
        "project_id": project_id,
        "title": project.get("title"),
        "status": project.get("status"),
        "version_num": current.get("version_num"),
        "version_id": current.get("id"),
        "preview_title": current.get("title"),
        "task": current.get("task"),
        "colors": current.get("colors") or project.get("colors", []),
        "css_tokens": handoff.get("css_tokens") or _css_from_colors(current.get("colors") or []),
        "react_code": current.get("react_code", ""),
        "published_at": handoff.get("published_at") or project.get("published_at"),
        "figma_url": handoff.get("figma_url"),
        "studio_url": f"/workspace?view=sonya-studio&project={project_id}",
        "figma_import_steps": [
            "1. Скачайте handoff.zip (tokens.css + App.jsx + README)",
            "2. В Figma создайте файл или откройте шаблон",
            "3. Импортируйте цвета из tokens.css в Variables / Styles",
            "4. Сверьте UI со скриншотом превью в Studio",
            "5. React-код — для разработчиков (Dev Mode / код)",
        ],
        "comments_resolved": sum(1 for c in project.get("comments", []) if c.get("status") == "resolved"),
        "comments_total": len(project.get("comments", [])),
    }


def _css_from_colors(colors: list) -> str:
    names = ["--accent", "--surface", "--text", "--border", "--green", "--purple", "--muted", "--yellow"]
    lines = [":root {"]
    for i, c in enumerate(colors[:8]):
        if i < len(names):
            lines.append(f"  {names[i]}: {c};")
    lines.append("}")
    return "\n".join(lines)


def build_handoff_zip(project_id: str) -> Optional[tuple[str, bytes]]:
    pkg = build_handoff_package(project_id)
    if not pkg:
        return None

    title_safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in pkg["title"])[:40].strip()
    filename = f"sonya-handoff-{title_safe or project_id}-v{pkg.get('version_num', 1)}.zip"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("handoff.json", json.dumps(pkg, ensure_ascii=False, indent=2))
        zf.writestr("tokens.css", pkg.get("css_tokens", ""))
        zf.writestr("App.jsx", pkg.get("react_code", ""))
        zf.writestr(
            "README.txt",
            "\n".join([
                f"Sonya Design Studio — {pkg.get('title')}",
                f"Version: v{pkg.get('version_num')}",
                "",
                "Файлы:",
                "  tokens.css  — design tokens для Figma/CSS",
                "  App.jsx     — React компонент",
                "  handoff.json — метаданные",
                "",
                "Studio:",
                f"  {pkg.get('studio_url')}",
                "",
                "Шаги Figma:",
                *[f"  {s}" for s in pkg.get("figma_import_steps", [])],
            ]),
        )
    return filename, buf.getvalue()
