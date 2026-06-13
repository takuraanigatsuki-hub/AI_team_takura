"""OpenAI embeddings для hybrid RAG."""

from __future__ import annotations

import json
import math
import os
from typing import Optional

import httpx


def is_configured() -> bool:
    import config as cfg
    key = os.environ.get("OPENAI_API_KEY") or cfg.config.get("openai_api_key", "")
    return bool(key.strip())


def _settings() -> dict:
    import config as cfg
    return {
        "api_key": os.environ.get("OPENAI_API_KEY") or cfg.config.get("openai_api_key", ""),
        "base_url": (os.environ.get("OPENAI_BASE_URL") or cfg.config.get("openai_base_url")
                     or "https://api.openai.com/v1").rstrip("/"),
        "model": os.environ.get("EMBEDDING_MODEL") or cfg.config.get("embedding_model") or "text-embedding-3-small",
    }


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts or not is_configured():
        return []
    cfg = _settings()
    # OpenAI accepts batch input
    clean = [(t or "")[:8000] for t in texts]
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{cfg['base_url']}/embeddings",
            headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
            json={"model": cfg["model"], "input": clean},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Embeddings {resp.status_code}: {resp.text[:300]}")
        data = resp.json().get("data") or []
        data.sort(key=lambda x: x.get("index", 0))
        return [item["embedding"] for item in data]


async def embed_query(text: str) -> Optional[list[float]]:
    vecs = await embed_texts([text])
    return vecs[0] if vecs else None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embedding_to_blob(vec: list[float]) -> bytes:
    return json.dumps(vec).encode("utf-8")


def blob_to_embedding(blob: bytes) -> list[float]:
    return json.loads(blob.decode("utf-8"))
