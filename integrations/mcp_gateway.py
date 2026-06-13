"""MCP-style gateway — единая точка вызова tools агентов."""

from __future__ import annotations

from typing import Any, Optional


async def invoke_tool(agent_id: str, tool_name: str, arguments: dict = None) -> dict:
    arguments = arguments or {}
    tool_name = (tool_name or "").strip().lower()

    if tool_name == "rag_search":
        from integrations.rag.retrieve import retrieve_for_agent
        q = arguments.get("query") or arguments.get("task") or ""
        hits = await retrieve_for_agent(agent_id, q, limit=int(arguments.get("limit", 6)))
        return {"ok": True, "tool": tool_name, "results": hits}

    if tool_name == "project_memory":
        from room.project_memory import get_memory
        return {"ok": True, "tool": tool_name, "memory": get_memory()}

    if tool_name == "figma_import":
        url = arguments.get("url", "")
        if not url:
            return {"ok": False, "error": "url required"}
        from integrations.figma_client import get_client
        client = get_client()
        if not client.configured:
            return {"ok": False, "error": "Figma not configured"}
        result = await client.import_design(url, lightweight=True)
        return {"ok": True, "tool": tool_name, "summary": result.get("summary")}

    if tool_name == "create_pptx":
        from integrations.pptx_builder import build_pptx_bytes
        task = arguments.get("task") or arguments.get("query") or ""
        content = arguments.get("content") or ""
        data = build_pptx_bytes(task, content)
        return {"ok": True, "tool": tool_name, "bytes": len(data), "filename": "presentation.pptx"}

    if tool_name == "evaluate_artifact":
        from room.evaluator_gate import evaluate_artifact
        return await evaluate_artifact(
            task_text=arguments.get("task", ""),
            agent_id=arguments.get("agent_id") or agent_id,
            agent_name=arguments.get("agent_name", agent_id),
            response=arguments.get("response", ""),
            artifact=arguments.get("artifact"),
        )

    if tool_name == "cursor_run":
        from integrations.cursor_client import get_client
        client = get_client()
        prompt = arguments.get("prompt") or arguments.get("task") or ""
        if not client.configured:
            return {"ok": False, "error": "Cursor not configured"}
        run = await client.run_agent(prompt, repo_url=arguments.get("repo_url"))
        return {"ok": True, "tool": tool_name, "run": run}

    if tool_name == "web_fetch":
        import httpx
        url = arguments.get("url", "")
        if not url:
            return {"ok": False, "error": "url required"}
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(url)
            text = r.text[:8000]
        return {"ok": True, "tool": tool_name, "status": r.status_code, "text": text}

    if tool_name in ("sandbox_run", "run_python", "code_exec"):
        from integrations.sandbox.docker_runner import run_python
        code = arguments.get("code") or arguments.get("python") or ""
        timeout = int(arguments.get("timeout") or 30)
        return {"ok": True, "tool": tool_name, **await run_python(code, timeout=timeout)}

    if tool_name in ("playwright_snapshot", "browser_snapshot", "browser_test"):
        from integrations.playwright_runner import browser_snapshot, run_smoke_test, playwright_installed
        url = arguments.get("url") or arguments.get("target") or "http://localhost:8000"
        if tool_name == "browser_test":
            checks = arguments.get("checks") or arguments.get("contains") or []
            if isinstance(checks, str):
                checks = [checks]
            result = await run_smoke_test(url, checks=checks)
        else:
            result = await browser_snapshot(url)
        result["playwright_installed"] = playwright_installed()
        return {"ok": True, "tool": tool_name, **result}

    return {"ok": False, "error": f"Unknown tool: {tool_name}", "agent_id": agent_id}


async def list_tools(agent_id: str) -> list[dict]:
    from integrations.agent_tools import tools_for
    return tools_for(agent_id)
