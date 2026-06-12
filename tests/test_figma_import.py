"""Тесты импорта Figma и генерации React UI."""

import asyncio

import pytest

FIGMA_URL = "https://www.figma.com/site/uYRfrETGR8pcwChwLtJ6Ua/Untitled?t=S7zOAy3vHRn3HWqR-0"
FILE_KEY = "uYRfrETGR8pcwChwLtJ6Ua"


def test_parse_figma_site_url():
    from integrations.figma_client import parse_figma_url

    parsed = parse_figma_url(FIGMA_URL)
    assert parsed is not None
    assert parsed["file_key"] == FILE_KEY
    assert parsed["file_type"] == "site"


def test_fixture_loads():
    from integrations.figma_fixtures import get_fixture

    data = get_fixture(FILE_KEY)
    assert data is not None
    assert data["summary"]["file_name"] == "Untitled"
    assert len(data["summary"]["colors"]) >= 5
    assert len(data["summary"]["frames"]) >= 4


def test_import_design_uses_fixture_without_token():
    from integrations.figma_client import FigmaClient

    client = FigmaClient(access_token="")

    async def run():
        return await client.import_design(FIGMA_URL)

    result = asyncio.run(run())
    assert result["file_key"] == FILE_KEY
    assert result["file_type"] == "site"
    assert result["summary"]["file_name"] == "Untitled"


def test_generate_react_from_figma():
    from agents.react_preview import generate_react_from_figma
    from integrations.figma_fixtures import get_fixture

    figma = get_fixture(FILE_KEY)
    preview = generate_react_from_figma(figma, f"Импортируй Figma и создай React UI: {FIGMA_URL}")

    assert preview["figma_imported"] is True
    assert preview.get("is_site") is True
    assert "Figma · Untitled" in preview["title"]
    assert "function App()" in preview["code"]
    assert "figmaTokens" in preview["code"]
    assert "#7f56d9" in preview["code"]
    assert "Header" in preview["code"] or "Hero" in preview["code"]


def test_figma_import_api(client):
    r = client.post("/api/figma/import", json={"url": FIGMA_URL})
    assert r.status_code == 200
    data = r.json()
    assert data["file_key"] == FILE_KEY
    assert data["summary"]["file_name"] == "Untitled"
