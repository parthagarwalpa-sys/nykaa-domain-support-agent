"""Generate Task 13 evaluation evidence under evidence/step14/."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation_runner import (
    EVALUATION_QUERIES_PATH,
    format_evaluation_report,
    run_evaluation_suite,
)

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step14"


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EVALUATION_QUERIES_PATH, EVIDENCE_DIR / "evaluation_queries.json")

    suite = run_evaluation_suite()
    (EVIDENCE_DIR / "evaluation_results.json").write_text(
        json.dumps(suite, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "evaluation_report.md").write_text(
        format_evaluation_report(suite),
        encoding="utf-8",
    )
    rubric_src = EVIDENCE_DIR / "judge_rubric.md"
    if not rubric_src.is_file():
        pass
    print("Averages:", suite["averages"])
    print(f"Wrote Task 13 evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
