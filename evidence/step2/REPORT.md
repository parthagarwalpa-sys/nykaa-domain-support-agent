# Step 2 — Part 1 Task 1 (dataset) evidence

**Date:** 2026-10-13  
**Verdict:** `STEP_2_PASS` (Task 1 only)

## Commands

```powershell
python dataset.py
python -m pytest tests/test_dataset.py -v
python -m pytest tests/test_step1b_smoke.py -v
python -m pip check
```

## Artifacts

| File | Description |
|------|-------------|
| `dataset_report.txt` | Console summary from `dataset.py` |
| `dataset_summary.json` | Structured counts |
| `pytest_dataset.txt` | T01 unit tests |
| `pytest_step1b_regression.txt` | Step 1B regression |
| `pip_check.txt` | Dependency integrity |

## Design parameters

See `README.md` and `dataset.py` module constants.
