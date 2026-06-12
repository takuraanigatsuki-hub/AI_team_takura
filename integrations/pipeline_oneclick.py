"""Figma → React → Deploy one-click pipeline."""

async def run_full_pipeline(room_manager, figma_url: str = None) -> dict:
    import config as cfg
    steps = []

    url = figma_url or cfg.config.get("figma_default_url", "")
    if url:
        frontend = room_manager.agents.get("frontend")
        if frontend:
            await room_manager.handle_user_message({
                "type": "task",
                "text": f"Импортируй Figma и создай React UI: {url}",
                "target": "frontend",
            })
            steps.append({"step": "figma_import", "ok": True})

    await room_manager.handle_user_message({
        "type": "task",
        "text": "Доработай React Preview до production-ready UI",
        "target": "frontend",
    })
    steps.append({"step": "react_polish", "ok": True})

    from integrations.deploy_export import create_deploy_bundle
    bundle = create_deploy_bundle()
    steps.append({"step": "deploy_bundle", "ok": True, "url": bundle.get("download_url")})

    if room_manager:
        await room_manager.broadcast_work({
            "type": "pipeline_update",
            "message": "🚀 Pipeline: Figma → React → Deploy ZIP готов",
            "download_url": bundle.get("download_url"),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

    return {"ok": True, "steps": steps, "bundle": bundle}
