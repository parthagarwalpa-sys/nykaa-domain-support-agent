# Final submission checklist (manual gates)

Use this after [`FINAL_SUBMISSION_AUDIT.md`](FINAL_SUBMISSION_AUDIT.md). Mark items only when **you** have verified them; do not assume completion from Cursor.

## In-repository (verified 2026-10-15 audit)

- [x] Masai Tasks 1–16 implemented with tests and evidence paths  
- [x] Full pytest: **208 passed** (fresh venv + primary venv)  
- [x] `python -m pip check` clean on fresh install  
- [x] `docs/MASAI_OFFICIAL_BRIEF.md` unchanged  
- [x] README states **Nykaa (E-commerce & Retail)** track and reproducible dataset design  
- [x] No `.env` with secrets committed (`.env` gitignored; `.env.example` safe)  
- [x] No slides/screenshots/PDF/video deliverables required or present  

## External / manual (not done in audit workspace)

- [ ] **Git initialized** in project root (`git init` or clone from remote)  
- [ ] **All intended files staged** (exclude `.venv*`, `chroma_data/`, `logs/`, `.env`)  
- [ ] **No secrets** in staged diff (`git diff`, search for keys/tokens)  
- [ ] **Repository pushed** to GitHub (or approved host)  
- [ ] **Repository visibility: public**  
- [ ] **README renders** on GitHub (track line, setup, MOCK_LLM, telemetry)  
- [ ] **GitHub URL verified** in browser (clone URL matches submission link)  
- [ ] **Clean-clone test** on another path: `pip install -r requirements.in` → `rebuild_kb_index.py` → `pytest`  
- [ ] **Final GitHub link** copied for Masai submission portal  
- [ ] **Deadline** confirmed with Masai  

## Post-push smoke (recommended)

```powershell
git clone <your-public-repo-url> nykaa-capstone-clean
cd nykaa-capstone-clean
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.in
$env:CREWAI_DISABLE_TELEMETRY="true"
$env:OTEL_SDK_DISABLED="true"
$env:MOCK_LLM="true"
python scripts/rebuild_kb_index.py
python -m pytest -q
python -m pip check
```

When every **External / manual** box is checked, treat the project as **`SUBMISSION_READY`** for the Masai link step.
