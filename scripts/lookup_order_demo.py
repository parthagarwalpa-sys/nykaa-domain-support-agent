"""Print a sample Task 6 order lookup as JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.order_status import check_order_status  # noqa: E402


def main() -> int:
    record_id = sys.argv[1] if len(sys.argv) > 1 else "NYK-20261013-0001"
    print(json.dumps(check_order_status(record_id), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
