"""Run Task 5 document-level precision/recall evaluation for both chunk collections."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.retrieval_evaluation import (  # noqa: E402
    GROUND_TRUTH_PATH,
    load_ground_truth,
    render_markdown_report,
    run_full_evaluation,
)

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step6"


def main() -> int:
    evaluation = run_full_evaluation()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    gt_copy = EVIDENCE_DIR / "retrieval_ground_truth.json"
    shutil.copy2(GROUND_TRUTH_PATH, gt_copy)

    results_path = EVIDENCE_DIR / "precision_recall_results.json"
    with results_path.open("w", encoding="utf-8") as handle:
        json.dump(evaluation, handle, indent=2)
        handle.write("\n")

    report_md = render_markdown_report(evaluation)
    report_path = EVIDENCE_DIR / "precision_recall_report.md"
    report_path.write_text(report_md + "\n", encoding="utf-8")

    rec = evaluation["recommendation"]
    print(f"Wrote {results_path}")
    print(f"Wrote {report_path}")
    print(f"Recommended: {rec['recommended_strategy']} ({rec['recommended_collection']})")
    print(rec["rationale_sentences"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
