"""Rebuild ChromaDB indexes for Part 1 Task 3 and print a summary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag import (  # noqa: E402
    COLLECTION_FIXED,
    COLLECTION_SENTENCE,
    get_chroma_client,
    get_embedder,
    query_collection,
    rebuild_collections,
)

SAMPLE_QUERIES = {
    COLLECTION_FIXED: "What is the return window for Beauty products?",
    COLLECTION_SENTENCE: "How are cash on delivery refunds processed?",
}


def main() -> None:
    stats = rebuild_collections()
    embedder = get_embedder()
    client = get_chroma_client()

    retrieval: dict[str, object] = {}
    for collection_name, query in SAMPLE_QUERIES.items():
        col = client.get_collection(collection_name)
        result = query_collection(col, query, embedder, n_results=2)
        retrieval[collection_name] = {
            "query": query,
            "ids": result.get("ids"),
            "documents": result.get("documents"),
            "metadatas": result.get("metadatas"),
            "distances": result.get("distances"),
        }

    payload = {"build": stats, "sample_retrieval": retrieval}
    print(json.dumps(payload, indent=2))

    evidence_dir = ROOT / "evidence" / "step4"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "index_build.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
