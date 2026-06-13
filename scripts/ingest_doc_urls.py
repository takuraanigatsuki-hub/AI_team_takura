"""CLI: ingest public doc URLs into RAG."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from integrations.rag.url_ingest import ingest_default_docs  # noqa: E402


async def main() -> None:
    result = await ingest_default_docs()
    out = ROOT / "data" / "rag" / "url_ingest_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ingested={len(result.get('ingested', []))} errors={len(result.get('errors', []))}")
    print(f"total_chunks={result.get('index', {}).get('total_chunks', '?')}")
    print(f"report: {out}")


if __name__ == "__main__":
    asyncio.run(main())
