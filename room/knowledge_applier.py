"""Применение изученных знаний — чтобы агенты не повторяли один шаблон."""

from typing import Optional


def get_learned_hints(agent_id: str, task_text: str, agent_topics: list | None = None) -> dict:
    """Собрать подсказки из базы агента + Design Lab для UI/таблиц."""
    hints = {"topics": [], "colors": [], "summary_lines": [], "prompt_extra": ""}
    topics = agent_topics or []

    relevant = _score_topics(task_text, topics)[:3]
    for item in relevant:
        title = item.get("title") or item.get("topic", "")
        summary = (item.get("summary") or "")[:200]
        if title:
            hints["topics"].append(title)
        if summary:
            hints["summary_lines"].append(f"{title}: {summary}" if title else summary)

    if agent_id in ("frontend", "presenter", "doc_writer"):
        try:
            from integrations.figma_learning import load_patterns
            patterns = load_patterns() or {}
            colors = (patterns.get("colors") or [])[:6]
            if colors:
                hints["colors"] = colors
                hints["summary_lines"].append(
                    f"Палитра из Design Lab: {', '.join(colors[:4])}"
                )
        except Exception:
            pass

    if hints["summary_lines"]:
        hints["prompt_extra"] = (
            "Учитывай изученное ранее (не копируй шаблон буквально):\n"
            + "\n".join(f"- {line}" for line in hints["summary_lines"][:4])
        )

    try:
        from integrations.rag.retrieve import retrieve_context_text
        rag_ctx = retrieve_context_text(agent_id, task_text, limit=5)
        if rag_ctx:
            hints["rag_context"] = rag_ctx
            hints["prompt_extra"] = (
                (hints.get("prompt_extra") or "")
                + "\n\nБаза знаний (RAG):\n"
                + rag_ctx
            ).strip()
    except Exception:
        pass

    return hints


def _score_topics(task_text: str, topics: list) -> list:
    import re
    words = set(re.findall(r"[a-zA-Zа-яА-Я0-9]{3,}", (task_text or "").lower()))
    if not words or not topics:
        return []
    scored = []
    for item in topics:
        blob = " ".join([
            item.get("topic", ""),
            item.get("title", ""),
            item.get("summary", ""),
            " ".join(item.get("keywords") or []),
        ]).lower()
        item_words = set(re.findall(r"[a-zA-Zа-яА-Я0-9]{3,}", blob))
        overlap = len(words & item_words)
        if overlap > 0:
            scored.append((overlap, item))
    scored.sort(key=lambda x: (-x[0], x[1].get("timestamp", "")))
    return [item for _, item in scored]


def vary_seed(task_text: str) -> int:
    """Детерминированное разнообразие по тексту задачи."""
    return sum(ord(c) for c in (task_text or "")) % 997
