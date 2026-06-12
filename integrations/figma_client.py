"""Figma REST API — импорт макетов и design tokens."""

import re
from typing import Optional
from urllib.parse import unquote, urlparse, parse_qs

import httpx

FIGMA_URL_RE = re.compile(
    r"figma\.com/(?:design|file|site|proto|board|deck|slides)/([a-zA-Z0-9]+)(?:/[^?]*)?",
    re.IGNORECASE,
)


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
    path_parts = parsed.path.strip("/").split("/")
    file_type = path_parts[1] if len(path_parts) >= 2 else "design"
    node_raw = qs.get("node-id", [""])[0]
    node_id = unquote(node_raw).replace("-", ":") if node_raw else None
    return {
        "file_key": file_key,
        "node_id": node_id,
        "url": url,
        "file_type": file_type,
    }


class FigmaClient:
    def __init__(self, access_token: str = ""):
        self.access_token = access_token
        self.base = "https://api.figma.com/v1"

    @property
    def configured(self) -> bool:
        return bool(self.access_token)

    def _headers(self) -> dict:
        return {"X-Figma-Token": self.access_token, "User-Agent": "AI-Team-Room/1.0"}

    async def get_file(self, file_key: str, node_ids: Optional[str] = None) -> dict:
        params = {}
        if node_ids:
            params["ids"] = node_ids
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base}/files/{file_key}",
                headers=self._headers(),
                params=params,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Figma API {resp.status_code}: {resp.text[:300]}")
            return resp.json()

    async def get_file_meta(self, file_key: str) -> dict:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{self.base}/files/{file_key}",
                headers=self._headers(),
                params={"depth": "1"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Figma API {resp.status_code}: {resp.text[:300]}")
            return resp.json()

    async def get_local_variables(self, file_key: str) -> dict:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{self.base}/files/{file_key}/variables/local",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return {"variables": {}, "message": "Variables API недоступен для этого файла"}
            if resp.status_code != 200:
                raise RuntimeError(f"Figma API {resp.status_code}: {resp.text[:300]}")
            return resp.json()

    async def export_images(self, file_key: str, node_ids: str, fmt: str = "png", scale: int = 2) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base}/images/{file_key}",
                headers=self._headers(),
                params={"ids": node_ids, "format": fmt, "scale": scale},
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

    async def import_design(self, url: str) -> dict:
        parsed = parse_figma_url(url)
        if not parsed:
            raise ValueError("Некорректная ссылка Figma")
        if not self.configured:
            raise ValueError("FIGMA_ACCESS_TOKEN не задан в .env")

        file_key = parsed["file_key"]
        node_id = parsed.get("node_id")
        file_data = await self.get_file(file_key, node_ids=node_id) if node_id else await self.get_file_meta(file_key)
        summary = self.extract_design_summary(file_data, node_id)

        preview_url = None
        if node_id:
            try:
                img = await self.export_images(file_key, node_id)
                preview_url = (img.get("images") or {}).get(node_id)
            except Exception:
                pass

        variables = {}
        try:
            variables = await self.get_local_variables(file_key)
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

    return FigmaClient(access_token=config.get("figma_access_token", ""))
