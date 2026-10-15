"""One-off helper to regenerate evidence/step3/KNOWLEDGE_BASE_FINAL_REVIEW.md."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from knowledge_base.policy_loader import load_all_policy_drafts
OUT = ROOT / "evidence" / "step3" / "KNOWLEDGE_BASE_FINAL_REVIEW.md"

HEADER = """# Knowledge Base — Final Review (Part 1, Task 2)

**Fictional capstone policies:** These documents are original assignment content and are **not** representations of Nykaa commercial policies.

## Approved human edits (2026-10-14)

1. **KB-001:** Wrong-item returns explicitly allowed for all five categories within each category window.
2. **KB-007:** Seven-day points pending explained as initial return/cancellation adjustments, not full return-window coverage.
3. **KB-010:** Concealed damage after 48h clarified with reasonable evidence (photos or unboxing video).

## Cross-policy consistency

- KB-001 (15-day Apparel/Footwear returns) vs KB-009 (10-day size exchange): exchange remains stricter; consistent.
- KB-001 Beauty sealed returns vs KB-010 transit-documented broken-seal exception: compatible.
- KB-002 COD (7 business days) vs KB-006 prepaid cancel (5 business days): separate flows; unchanged.
- KB-007 no longer claims 7-day pending covers all category return windows.
- KB-012 unchanged; escalation INR thresholds remain fictional support rules.

## Validation

- `pytest tests/test_knowledge_base_drafts.py -v`: 5 passed
- `pytest tests/test_dataset.py -v`: 9 passed
- `pytest tests/test_step1b_smoke.py -v`: 6 passed
- `pip check`: No broken requirements found

See `evidence/step3/validation_all.txt`.

---

"""


def main() -> None:
    lines = [HEADER]
    for draft in load_all_policy_drafts():
        lines.extend(
            [
                f"## {draft['document_id']} — {draft['title']}",
                "",
                f"**Topic:** {draft['topic']}  ",
                f"**Sentence count:** {draft['sentence_count']}",
                "",
                "### Policy body",
                "",
                draft["policy_body"],
                "",
                "---",
                "",
            ]
        )
    lines.append("**STATUS: TASK_2_FINALIZED**")
    OUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
