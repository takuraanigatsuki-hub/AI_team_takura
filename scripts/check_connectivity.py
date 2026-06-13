"""Проверка доступа к внешним сервисам (LLM, embeddings)."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main() -> int:
    from integrations.http_client import describe_outbound
    from integrations.llm_client import chat, is_configured
    from integrations.rag.embeddings import embed_query, is_configured as emb_ok

    print(f"Outbound: {describe_outbound()}")
    ok = True

    if is_configured():
        try:
            reply = await chat([{"role": "user", "content": "ping"}], max_tokens=5)
            print(f"LLM: OK — {reply[:60]!r}")
        except Exception as e:
            print(f"LLM: FAIL — {e}")
            ok = False
    else:
        print("LLM: skip (OPENAI_API_KEY not set)")

    if emb_ok():
        try:
            vec = await embed_query("test")
            print(f"Embeddings: OK — dim={len(vec or [])}")
        except Exception as e:
            print(f"Embeddings: FAIL — {e}")
            ok = False
    else:
        print("Embeddings: skip")

    if not ok:
        print("\nПодсказка: включите VPN и укажите в .env:")
        print("  OUTBOUND_PROXY_MODE=proxy")
        print("  OUTBOUND_PROXY=http://127.0.0.1:7890")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
