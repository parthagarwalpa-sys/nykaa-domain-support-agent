"""Generate Task 8 LangChain session memory evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.support_session import run_fresh_session_demo, run_same_session_demo  # noqa: E402

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step9"


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    same = run_same_session_demo()
    fresh = run_fresh_session_demo()

    (EVIDENCE_DIR / "transcript_same_session.json").write_text(
        json.dumps(same, indent=2) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "transcript_fresh_session.json").write_text(
        json.dumps(fresh, indent=2) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "memory_store_summary.json").write_text(
        json.dumps(
            {
                "same_session": same["session_store_summary"],
                "fresh_session": fresh["session_store_summary"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote evidence to {EVIDENCE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
