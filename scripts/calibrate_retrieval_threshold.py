"""Calibrate Task 4 retrieval fallback threshold and write app/data/retrieval_threshold.json."""

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
    run_threshold_calibration,
    write_threshold_artifact,
)

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step5"


def main() -> int:
    embedder = get_embedder()
    collection = get_task4_collection()
    calibration = run_threshold_calibration(collection=collection, embedder=embedder)
    artifact_path = write_threshold_artifact(calibration)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = EVIDENCE_DIR / "threshold_calibration.json"
    with evidence_path.open("w", encoding="utf-8") as handle:
        json.dump(calibration, handle, indent=2)
        handle.write("\n")
    print(f"Wrote threshold artifact: {artifact_path}")
    print(f"Wrote calibration evidence: {evidence_path}")
    print(json.dumps(calibration["selected_threshold"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
