"""Внешние интеграции: Telegram, Jira, Linear, Notion, Vercel."""

import os
from typing import Optional


def _cfg(key: str, env: str) -> str:
    import config as cfg_module
    return (os.environ.get(env) or cfg_module.config.get(key) or "").strip()


def integration_status() -> dict:
    return {
        "telegram": bool(_cfg("telegram_bot_token", "TELEGRAM_BOT_TOKEN")),
        "jira": bool(_cfg("jira_url", "JIRA_URL") and _cfg("jira_token", "JIRA_TOKEN")),
        "linear": bool(_cfg("linear_api_key", "LINEAR_API_KEY")),
        "notion": bool(_cfg("notion_token", "NOTION_TOKEN")),
        "vercel": bool(_cfg("vercel_token", "VERCEL_TOKEN")),
    }


async def send_telegram(text: str, chat_id: str = None) -> Optional[dict]:
    token = _cfg("telegram_bot_token", "TELEGRAM_BOT_TOKEN")
    if not token:
        return None
    from integrations.telegram_bot import send_message, _default_chat_id, _load_chats
    cid = chat_id or _default_chat_id()
    if not cid:
        chats = _load_chats()
        cid = chats[0]["chat_id"] if chats else ""
    if not cid:
        return None
    result = await send_message(cid, text, parse_mode="Markdown")
    if not result.get("ok"):
        result = await send_message(cid, text)
    return result


async def create_jira_issue(summary: str, description: str) -> Optional[dict]:
    url = _cfg("jira_url", "JIRA_URL")
    token = _cfg("jira_token", "JIRA_TOKEN")
    email = _cfg("jira_email", "JIRA_EMAIL")
    project = _cfg("jira_project", "JIRA_PROJECT") or "PROJ"
    if not url or not token:
        return None
    import httpx
    import base64
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{url.rstrip('/')}/rest/api/3/issue",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json={"fields": {"project": {"key": project}, "summary": summary[:255],
                             "description": {"type": "doc", "version": 1,
                                               "content": [{"type": "paragraph",
                                                              "content": [{"type": "text", "text": description[:2000]}]}]},
                             "issuetype": {"name": "Task"}}},
        )
        if r.status_code in (200, 201):
            data = r.json()
            return {"key": data.get("key"), "url": f"{url}/browse/{data.get('key')}"}
        return {"error": r.text[:300]}


async def create_linear_issue(title: str, description: str) -> Optional[dict]:
    key = _cfg("linear_api_key", "LINEAR_API_KEY")
    team_id = _cfg("linear_team_id", "LINEAR_TEAM_ID")
    if not key or not team_id:
        return None
    import httpx
    query = """
    mutation($title: String!, $desc: String!, $teamId: String!) {
      issueCreate(input: { title: $title, description: $desc, teamId: $teamId }) {
        success issue { id url identifier }
      }
    }"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": key, "Content-Type": "application/json"},
            json={"query": query, "variables": {"title": title[:200], "desc": description[:2000], "teamId": team_id}},
        )
        data = r.json()
        issue = data.get("data", {}).get("issueCreate", {}).get("issue")
        return issue


async def export_notion_page(title: str, content: str) -> Optional[dict]:
    token = _cfg("notion_token", "NOTION_TOKEN")
    parent = _cfg("notion_parent_page_id", "NOTION_PARENT_PAGE_ID")
    if not token or not parent:
        return None
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.notion.com/v1/pages",
            headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28",
                       "Content-Type": "application/json"},
            json={
                "parent": {"page_id": parent},
                "properties": {"title": {"title": [{"text": {"content": title[:200]}}]}},
                "children": [{"object": "block", "type": "paragraph",
                              "paragraph": {"rich_text": [{"type": "text", "text": {"content": content[:2000]}}]}}],
            },
        )
        if r.status_code == 200:
            d = r.json()
            return {"url": d.get("url"), "id": d.get("id")}
        return {"error": r.text[:300]}


async def deploy_vercel(project_name: str = "ai-team-preview") -> Optional[dict]:
    token = _cfg("vercel_token", "VERCEL_TOKEN")
    if not token:
        return None
    from integrations.deploy_export import create_deploy_bundle
    create_deploy_bundle()
    import httpx
    zip_path = os.path.join(os.path.dirname(__file__), "..", "output", "deploy", "latest.zip")
    if not os.path.exists(zip_path):
        return {"error": "No deploy bundle"}
    return {
        "ok": True,
        "message": "Vercel: загрузите ZIP через vercel.com/new или `npx vercel deploy`",
        "bundle": "/api/deploy/download",
        "docs": "https://vercel.com/docs/cli/deploy",
    }
