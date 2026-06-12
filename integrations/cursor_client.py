"""Клиент Cursor Cloud Agents API + локальный cursor-sdk (если установлен)."""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Any, Callable, Optional

import httpx

API_BASE = "https://api.cursor.com"

cursor_runs: dict[str, dict] = {}


class CursorClient:
    def __init__(self, api_key: str = "", model: str = "composer-2.5"):
        self.api_key = api_key
        self.model = model
        self._auth = (api_key, "") if api_key else None

    def _headers(self) -> dict:
        return {"Content-Type": "application/json", "User-Agent": "AI-Team-Room/1.0"}

    async def verify_key(self) -> dict:
        if not self.api_key:
            return {"ok": False, "error": "API ключ не задан"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{API_BASE}/v0/me",
                    auth=self._auth,
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {"ok": True, "user": data}
                return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def list_repositories(self) -> list:
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{API_BASE}/v0/repositories",
                    auth=self._auth,
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data if isinstance(data, list) else data.get("repositories", [])
        except Exception:
            pass
        return []

    async def create_cloud_agent(
        self,
        prompt: str,
        repo_url: str,
        ref: str = "main",
        auto_create_pr: bool = True,
    ) -> dict:
        if not self.api_key:
            raise ValueError("Cursor API ключ не настроен")
        payload = {
            "prompt": {"text": prompt},
            "model": self.model,
            "source": {"repository": repo_url, "ref": ref},
            "target": {"autoCreatePr": auto_create_pr},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{API_BASE}/v0/agents",
                auth=self._auth,
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Cursor API {resp.status_code}: {resp.text[:400]}")
            return resp.json()

    async def get_agent(self, agent_id: str) -> dict:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{API_BASE}/v0/agents/{agent_id}",
                auth=self._auth,
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Cursor API {resp.status_code}: {resp.text[:300]}")
            return resp.json()

    def _run_local_sync(self, prompt: str, cwd: str) -> str:
        from cursor_sdk import Agent, LocalAgentOptions

        with Agent.create(
            model=self.model,
            api_key=self.api_key,
            local=LocalAgentOptions(cwd=cwd),
        ) as agent:
            return agent.send(prompt).text()

    async def run_local(
        self,
        prompt: str,
        cwd: Optional[str] = None,
        on_progress: Optional[Callable[[str], Any]] = None,
    ) -> dict:
        if not self.api_key:
            raise ValueError("Cursor API ключ не настроен")
        root = cwd or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if on_progress:
            await _maybe_await(on_progress("🔄 Запуск локального Cursor Agent…"))

        try:
            text = await asyncio.to_thread(self._run_local_sync, prompt, root)
            return {"mode": "local", "status": "completed", "text": text}
        except ImportError:
            return {
                "mode": "local",
                "status": "unavailable",
                "text": (
                    "Пакет `cursor-sdk` не установлен.\n"
                    "Укажите GitHub repo в настройках для Cloud Agent."
                ),
            }
        except Exception as e:
            return {"mode": "local", "status": "error", "text": str(e)}

    async def run_task(
        self,
        prompt: str,
        repo_url: str = "",
        ref: str = "main",
        cwd: Optional[str] = None,
        auto_create_pr: bool = True,
        on_progress: Optional[Callable[[str], Any]] = None,
        force_cloud: bool = False,
    ) -> dict:
        from config import config

        run_id = str(uuid.uuid4())[:8]
        run_record = {
            "id": run_id,
            "prompt": prompt,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "result": None,
            "mode": None,
            "repo_url": repo_url,
        }
        cursor_runs[run_id] = run_record

        use_cloud = bool(repo_url) and (
            force_cloud
            or config.get("cursor_cloud_mode", True)
            or config.get("cursor_github_sync", False)
        )

        try:
            if use_cloud:
                if on_progress:
                    await _maybe_await(on_progress(
                        f"☁️ Cloud Agent → GitHub\n`{repo_url}` (ветка `{ref}`)"
                    ))
                data = await self.create_cloud_agent(
                    prompt, repo_url, ref, auto_create_pr=auto_create_pr
                )
                agent_id = data.get("id") or data.get("agent", {}).get("id", "")
                run_record.update({
                    "mode": "cloud",
                    "agent_id": agent_id,
                    "status": "running",
                    "result": data,
                    "auto_create_pr": auto_create_pr,
                })

                dashboard = f"https://cursor.com/agents/{agent_id}" if agent_id else ""
                summary = (
                    f"☁️ **Cloud Agent** запущен на GitHub\n\n"
                    f"• Repo: `{repo_url}`\n"
                    f"• Agent ID: `{agent_id}`\n"
                )
                if auto_create_pr:
                    summary += "• PR будет создан автоматически\n"
                if dashboard:
                    summary += f"• [Cursor Dashboard]({dashboard})\n"

                if agent_id:
                    try:
                        status = await self.get_agent(agent_id)
                        run_record["agent_status"] = status
                        st = status.get("status", "")
                        if st:
                            summary += f"• Статус: **{st}**"
                    except Exception:
                        pass

                run_record["text"] = summary
                run_record["status"] = "running"
                return run_record

            result = await self.run_local(prompt, cwd, on_progress)
            run_record.update(result)
            run_record["status"] = result.get("status", "completed")
            run_record["text"] = result.get("text", "")
            return run_record
        except Exception as e:
            run_record["status"] = "error"
            run_record["text"] = str(e)
            return run_record
        finally:
            run_record["finished_at"] = datetime.now().isoformat()


async def _maybe_await(value):
    if asyncio.iscoroutine(value):
        await value


def get_client() -> CursorClient:
    from config import config

    return CursorClient(
        api_key=config.get("cursor_api_key", ""),
        model=config.get("cursor_model", "composer-2.5"),
    )
