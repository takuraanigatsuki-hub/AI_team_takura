#!/usr/bin/env python3
"""Синхронизация Snow Dashboard темы из Figma → data/figma-snow-theme.json + static/css/figma-theme.generated.css"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from integrations.figma_theme import sync_from_figma, ensure_theme_files, save_theme, merge_figma_colors

    try:
        theme = await sync_from_figma()
        print("sync ok — source:", theme.get("source"))
    except Exception as e:
        print("sync failed:", e)
        print("using cached / official fallback…")
        theme = ensure_theme_files()
        if "light" not in theme:
            theme = merge_figma_colors(theme if isinstance(theme, dict) else {"sources": []})
            save_theme(theme)
    print("accent light:", theme["light"]["accent"])
    print("bg light:", theme["light"]["bg"])


if __name__ == "__main__":
    asyncio.run(main())
