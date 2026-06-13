#!/usr/bin/env python3
"""Индексация knowledge packs в RAG (SQLite FTS5)."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge packs into RAG")
    parser.add_argument("--replace", action="store_true", help="Clear index before ingest")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    args = parser.parse_args()

    from integrations.rag.ingest import ingest_all_packs, get_index_stats

    if args.stats:
        print(json.dumps(get_index_stats(), indent=2, ensure_ascii=False))
        return

    result = ingest_all_packs(replace=args.replace)
    stats = get_index_stats()
    print(f"Ingested {result['total']} entries across {len(result['agents'])} agents")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
