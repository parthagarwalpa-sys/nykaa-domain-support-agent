# Final acceptance audit — reproducibility (fresh venv)

**Date:** 2026-10-15  
**Venv:** `.venv-audit-fresh/` (created during audit; not the primary `.venv`)

## Commands

```powershell
python -m venv .venv-audit-fresh
.\.venv-audit-fresh\Scripts\python.exe -m pip install -r requirements.in
$env:CREWAI_DISABLE_TELEMETRY="true"; $env:OTEL_SDK_DISABLED="true"; $env:MOCK_LLM="true"
.\.venv-audit-fresh\Scripts\python.exe -m pip check
.\.venv-audit-fresh\Scripts\python.exe scripts/rebuild_kb_index.py
.\.venv-audit-fresh\Scripts\python.exe -m pytest -v
```

## Results

| Step | Result |
|------|--------|
| `pip check` | Clean (`pip_check_fresh_venv.txt`) |
| Chroma rebuild | Success (`rebuild_kb_index_fresh_venv.txt`) |
| Full pytest | **208 passed**, 0 failed, 0 skipped, 2944 warnings (`pytest_full_fresh_venv.txt`) |

## Notes

- First install may download Hugging Face model weights for `all-MiniLM-L6-v2` if not cached.
- Graded runtime uses MOCK_LLM; no OpenAI/API keys required for the test suite.
