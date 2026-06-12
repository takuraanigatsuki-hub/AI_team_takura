"""Diff между версиями артефактов."""

import difflib
from typing import Optional


def diff_text(old: str, new: str, label_old: str = "v1", label_new: str = "v2") -> dict:
    old_lines = (old or "").splitlines()
    new_lines = (new or "").splitlines()
    unified = list(difflib.unified_diff(old_lines, new_lines, fromfile=label_old, tofile=label_new, lineterm=""))
    html_parts = []
    for line in unified:
        cls = "diff-ctx"
        if line.startswith("+") and not line.startswith("+++"):
            cls = "diff-add"
        elif line.startswith("-") and not line.startswith("---"):
            cls = "diff-del"
        elif line.startswith("@@"):
            cls = "diff-hunk"
        html_parts.append(f'<div class="{cls}">{_esc(line)}</div>')
    return {
        "unified": "\n".join(unified),
        "html": "".join(html_parts) if html_parts else "<div class='muted'>Нет изменений</div>",
        "added": sum(1 for l in unified if l.startswith("+") and not l.startswith("+++")),
        "removed": sum(1 for l in unified if l.startswith("-") and not l.startswith("---")),
    }


def diff_artifacts(art_a: dict, art_b: dict) -> dict:
    content_a = art_a.get("content") or art_a.get("description") or ""
    content_b = art_b.get("content") or art_b.get("description") or ""
    return {
        "from": {"id": art_a.get("id"), "title": art_a.get("title"), "created_at": art_a.get("created_at")},
        "to": {"id": art_b.get("id"), "title": art_b.get("title"), "created_at": art_b.get("created_at")},
        "content_diff": diff_text(content_a, content_b, art_a.get("title", "A"), art_b.get("title", "B")),
    }


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
