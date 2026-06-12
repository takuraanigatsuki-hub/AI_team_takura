"""Figma REST API — импорт макетов и design tokens."""

import json
import os
import re
from typing import Optional
from urllib.parse import unquote, urlparse, parse_qs

import httpx

from integrations.figma_rate_limit import (
    FigmaRateLimitError,
    is_in_cooldown,
    parse_retry_after,
    set_cooldown,
    throttle,
)

FIGMA_URL_RE = re.compile(
    r"figma\.com/(?:design|file|site|proto|board|deck|slides|community/file)/([a-zA-Z0-9]+)(?:/[^?]*)?",
    re.IGNORECASE,
)

# Типы ссылок, которые REST API Figma не открывает как /v1/files/{key}
UNSUPPORTED_API_TYPES = frozenset({"site", "proto", "board", "deck", "slides"})
SUPPORTED_API_TYPES = frozenset({"design", "file", "community"})


def parse_figma_url(url: str) -> Optional[dict]:
    """Извлекает file_key и node_id из ссылки Figma."""
    if not url or "figma.com" not in url:
        return None
    m = FIGMA_URL_RE.search(url)
    if not m:
        return None
    file_key = m.group(1)
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) >= 2 and path_parts[0] == "community" and path_parts[1] == "file":
        file_type = "community"
    elif path_parts:
        file_type = path_parts[0].lower()
    else:
        file_type = "design"
    node_raw = qs.get("node-id", [""])[0]
    node_id = unquote(node_raw).replace("-", ":") if node_raw else None
    return {
        "file_key": file_key,
        "node_id": node_id,
        "url": url,
        "file_type": file_type,
        "api_supported": file_type in SUPPORTED_API_TYPES,
    }


def is_figma_api_url(url: str) -> bool:
    parsed = parse_figma_url(url)
    return bool(parsed and parsed.get("api_supported"))


class FigmaClient:
    def __init__(self, access_token: str = "", auth_type: str = "pat"):
        self.access_token = access_token
        self.auth_type = auth_type  # "oauth" | "pat"
        self.base = "https://api.figma.com/v1"

    @property
    def configured(self) -> bool:
        return bool(self.access_token)

    def _headers(self) -> dict:
        headers = {"User-Agent": "AI-Team-Room/1.0"}
        if not self.access_token:
            return headers
        if self.auth_type == "oauth":
            headers["Authorization"] = f"Bearer {self.access_token}"
        else:
            headers["X-Figma-Token"] = self.access_token
        return headers

    async def _request(self, method: str, url: str, *, retries: int = 3, **kwargs) -> httpx.Response:
        last_resp = None
        for attempt in range(retries):
            if is_in_cooldown():
                from integrations.figma_rate_limit import cooldown_remaining
                raise FigmaRateLimitError(cooldown_remaining())
            await throttle()
            async with httpx.AsyncClient(timeout=kwargs.pop("timeout", 30.0)) as client:
                resp = await client.request(method, url, headers=self._headers(), **kwargs)
            last_resp = resp
            if resp.status_code == 429:
                wait = parse_retry_after(resp)
                set_cooldown(wait)
                if attempt < retries - 1:
                    import asyncio
                    await asyncio.sleep(min(wait, 30))
                    continue
                raise FigmaRateLimitError(wait, f"Figma API 429: {resp.text[:200]}")
            return resp
        return last_resp

    async def get_file(self, file_key: str, node_ids: Optional[str] = None, depth: Optional[int] = None) -> dict:
        params = {}
        if node_ids:
            params["ids"] = node_ids
        if depth is not None:
            params["depth"] = depth
        resp = await self._request("GET", f"{self.base}/files/{file_key}", params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"Figma API {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def get_file_meta(self, file_key: str, depth: int = 1) -> dict:
        resp = await self._request(
            "GET", f"{self.base}/files/{file_key}", params={"depth": depth}, timeout=20.0
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Figma API {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def get_me(self) -> dict:
        resp = await self._request("GET", f"{self.base}/me", timeout=15.0)
        if resp.status_code != 200:
            raise RuntimeError(f"Figma API {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def get_team_projects(self, team_id: str) -> dict:
        resp = await self._request("GET", f"{self.base}/teams/{team_id}/projects", timeout=20.0)
        if resp.status_code != 200:
            raise RuntimeError(f"Figma API {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def get_project_files(self, project_id: str) -> dict:
        resp = await self._request("GET", f"{self.base}/projects/{project_id}/files", timeout=20.0)
        if resp.status_code != 200:
            raise RuntimeError(f"Figma API {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def get_local_variables(self, file_key: str) -> dict:
        resp = await self._request(
            "GET", f"{self.base}/files/{file_key}/variables/local", timeout=20.0
        )
        if resp.status_code == 404:
            return {"variables": {}, "message": "Variables API недоступен для этого файла"}
        if resp.status_code != 200:
            raise RuntimeError(f"Figma API {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def export_images(self, file_key: str, node_ids: str, fmt: str = "png", scale: int = 2) -> dict:
        resp = await self._request(
            "GET",
            f"{self.base}/images/{file_key}",
            params={"ids": node_ids, "format": fmt, "scale": scale},
            timeout=30.0,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Figma export {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def extract_design_summary(self, file_data: dict, node_id: Optional[str] = None) -> dict:
        """Сводка макета: цвета, шрифты, размеры фрейма."""
        colors = set()
        fonts = set()
        frames = []

        def walk(node, depth=0):
            if depth > 12:
                return
            ntype = node.get("type", "")
            name = node.get("name", "")
            if ntype in ("FRAME", "COMPONENT", "INSTANCE", "GROUP"):
                box = node.get("absoluteBoundingBox") or {}
                frames.append({
                    "name": name,
                    "type": ntype,
                    "width": box.get("width"),
                    "height": box.get("height"),
                    "id": node.get("id"),
                })
            fills = node.get("fills") or []
            for fill in fills:
                if fill.get("type") == "SOLID" and fill.get("color"):
                    c = fill["color"]
                    r = int(c.get("r", 0) * 255)
                    g = int(c.get("g", 0) * 255)
                    b = int(c.get("b", 0) * 255)
                    colors.add(f"#{r:02x}{g:02x}{b:02x}")
            style = node.get("style") or {}
            if style.get("fontFamily"):
                fonts.add(f"{style['fontFamily']} {style.get('fontWeight', 400)}")
            for child in node.get("children") or []:
                walk(child, depth + 1)

        doc = file_data.get("document") or {}
        if node_id:
            target = self._find_node(doc, node_id)
            if target:
                walk(target)
            else:
                walk(doc)
        else:
            walk(doc)

        return {
            "file_name": file_data.get("name", "Figma"),
            "last_modified": file_data.get("lastModified", ""),
            "colors": sorted(colors)[:24],
            "fonts": sorted(fonts)[:12],
            "frames": frames[:20],
        }

    def _find_node(self, node: dict, node_id: str) -> Optional[dict]:
        if node.get("id") == node_id:
            return node
        for child in node.get("children") or []:
            found = self._find_node(child, node_id)
            if found:
                return found
        return None

    def tokens_to_css(self, summary: dict) -> str:
        lines = [":root {"]
        for i, color in enumerate(summary.get("colors", [])[:8]):
            name = ["--accent", "--surface", "--text", "--border", "--green", "--purple", "--red", "--muted"]
            if i < len(name):
                lines.append(f"    {name[i]}: {color};")
        lines.append("}")
        return "\n".join(lines)

    async def import_design(self, url: str, *, lightweight: bool = False) -> dict:
        parsed = parse_figma_url(url)
        if not parsed:
            raise ValueError("Некорректная ссылка Figma")
        if not parsed.get("api_supported"):
            ftype = parsed.get("file_type", "unknown")
            raise ValueError(
                f"Ссылка figma.com/{ftype}/ не поддерживается Figma REST API. "
                "Используйте figma.com/design/… или figma.com/file/…"
            )
        if not self.configured:
            raise ValueError("Figma не подключена — OAuth или FIGMA_ACCESS_TOKEN в .env")

        file_key = parsed["file_key"]
        node_id = parsed.get("node_id")

        if lightweight:
            file_data = await self.get_file_meta(file_key, depth=2)
        elif node_id:
            file_data = await self.get_file(file_key, node_ids=node_id)
        else:
            file_data = await self.get_file_meta(file_key, depth=2)

        summary = self.extract_design_summary(file_data, node_id)

        preview_url = None
        if not lightweight and node_id:
            try:
                img = await self.export_images(file_key, node_id)
                preview_url = (img.get("images") or {}).get(node_id)
            except FigmaRateLimitError:
                raise
            except Exception:
                pass

        variables = {}
        if not lightweight:
            try:
                variables = await self.get_local_variables(file_key)
            except FigmaRateLimitError:
                pass
            except Exception:
                pass

        return {
            "file_key": file_key,
            "node_id": node_id,
            "url": url,
            "file_type": parsed.get("file_type", "design"),
            "summary": summary,
            "css_tokens": self.tokens_to_css(summary),
            "preview_url": preview_url,
            "variables": variables,
        }


def get_client() -> FigmaClient:
    from config import config

    store_path = os.path.join(os.path.dirname(__file__), "..", "data", "figma_oauth.json")
    try:
        with open(store_path, "r", encoding="utf-8") as f:
            store = json.load(f)
        if store.get("access_token"):
            return FigmaClient(access_token=store["access_token"], auth_type="oauth")
    except Exception:
        pass
    token = config.get("figma_access_token", "")
    return FigmaClient(access_token=token, auth_type="pat")


async def get_client_async() -> FigmaClient:
    from integrations.figma_oauth import ensure_valid_oauth_token
    from config import config

    oauth_token = await ensure_valid_oauth_token()
    if oauth_token:
        return FigmaClient(access_token=oauth_token, auth_type="oauth")
    token = config.get("figma_access_token", "")
    return FigmaClient(access_token=token, auth_type="pat")
