"""Run Task 4 grounded-generation demonstrations (5 in-scope + 1 out-of-scope)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.grounded_generation import (  # noqa: E402
    get_embedder,
    get_task4_collection,
    run_demonstration_suite,
)

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step5"


def main() -> int:
    embedder = get_embedder()
    collection = get_task4_collection()
    examples = run_demonstration_suite(collection=collection, embedder=embedder)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVIDENCE_DIR / "grounded_generation_examples.json"
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(examples, handle, indent=2)
        handle.write("\n")
    print(f"Wrote {len(examples)} demonstrations to {out_path}")
    for row in examples:
        flag = "FALLBACK" if row["fallback_fired"] else "GROUNDED"
        print(f"[{flag}] {row['query'][:70]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
