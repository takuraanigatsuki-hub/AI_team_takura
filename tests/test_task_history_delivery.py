"""Task history — delivery metadata для презентаций и файлов."""

from task_history import TaskHistory


def test_parent_inherits_pptx_from_presenter_child():
    th = TaskHistory()
    th.tasks = []

    parent_id = th.add_submitted("Мне нужно сделать презентацию на тему школа", "all")
    child_id = th.add_queued(
        "Создать презентацию", "presenter", "Ника", "📽️", parent_id=parent_id,
    )
    th.mark_awaiting_approval(
        child_id,
        "Готово",
        agent_name="Ника",
        agent_emoji="📽️",
        artifact_id="abc123",
        preview_url="/api/projects/abc123/preview",
        download_url="/api/projects/abc123/file/presentation.pptx",
        artifact_type="presentation",
        task_kind="presentation",
    )

    parent = th._find(parent_id)
    assert parent["status"] == "awaiting_approval"
    assert parent.get("download_url") == "/api/projects/abc123/file/presentation.pptx"
    assert parent.get("task_kind") == "presentation"

    enriched = th.enrich_for_ui([parent])[0]
    assert enriched.get("download_url") == "/api/projects/abc123/file/presentation.pptx"
