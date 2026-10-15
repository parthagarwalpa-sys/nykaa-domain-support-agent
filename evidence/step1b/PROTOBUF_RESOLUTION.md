# Protobuf dependency resolution (Step 1B follow-up)

**Date:** 2026-10-13  
**Primary `.venv`:** repaired 2026-10-13 (`protobuf==5.29.6`, `googleapis-common-protos==1.75.0`, `pip check` clean)  
**Verification env:** `.venv-disposable-protobuf` (gitignored, used for initial proof)  
**Verdict:** `DEPENDENCY_RESOLVED` → applied to primary env; Step 1B closed

## Root cause

Two packages in the CrewAI/ChromaDB stack require **incompatible** protobuf ranges when the resolver picks the newest transitive wheels:

| Package | Protobuf constraint |
|---------|---------------------|
| `autogen-core==0.7.5` | `protobuf~=5.29.3` (5.29.x only) |
| `googleapis-common-protos==1.75.5` | `protobuf>=6.33.5,<8.0.0` |
| `googleapis-common-protos==1.75.0` | `protobuf>=4.25.8,<8.0.0` (compatible with 5.29.x) |
| `opentelemetry-proto==1.45.1` | `protobuf>=5.0,<8.0` |
| `onnxruntime==1.31.0` (chromadb) | `protobuf>=4.25.8` |

The primary environment installed all frameworks, then **manually upgraded** protobuf to `7.36.2` so CrewAI could import ChromaDB after `googleapis-common-protos 1.75.5` had already been pulled. That satisfied runtime imports but violated `autogen-core` metadata (`pip check` failure).

The conflict is not CrewAI vs AutoGen directly; it is **`autogen-core`’s 5.29.x pin vs `googleapis-common-protos>=1.75.5`’s 6.33.5+ floor**, pulled via `chromadb` → OpenTelemetry OTLP gRPC exporters.

## Is protobuf 5.29.x compatible with the required packages?

**Yes**, when pip is allowed to resolve with an explicit `protobuf==5.29.6` pin. The resolver selects **`googleapis-common-protos==1.75.0`** (not 1.75.5). All six Step 1B smoke tests pass; `import crewai`, `chromadb`, and `autogen_agentchat` succeed.

**No** for a single environment that must keep **`protobuf>=6.33.5`** and **`autogen-core==0.7.5`** together without violating metadata—those ranges do not overlap.

## Fresh installation result

```powershell
python -m venv .venv-disposable-protobuf
.\.venv-disposable-protobuf\Scripts\pip install -r evidence\step1b\protobuf_test_requirements.in
```

- **Result:** Success (no `--no-deps`, no overrides).
- Installed: `protobuf==5.29.6`, `googleapis-common-protos==1.75.0`, `autogen-core==0.7.5`, full Step 1B stack.

Duplicate probe (protobuf pin only, same package list): identical resolution (`1.75.0` + `5.29.6`).

## `pip check` result (disposable env)

```
No broken requirements found.
```

Evidence: `evidence/step1b/protobuf_disposable_pip_check.txt`

## Smoke tests (disposable env)

```powershell
.\.venv-disposable-protobuf\Scripts\python.exe -m pytest tests/test_step1b_smoke.py -v
```

**6/6 PASSED** (CrewAI tool kickoff + both AutoGen review cases + import smoke).

## Recommended minimal dependency changes (not applied to primary `.venv` yet)

**`requirements.in`** — add one pin and remove the manual protobuf upgrade note:

```text
protobuf==5.29.6
```

Optional hardening (only if reproducibility needs extra guard against a future `googleapis-common-protos` bump):

```text
googleapis-common-protos==1.75.0
```

Not required when `protobuf==5.29.6` is pinned; pip already avoids `1.75.5`.

**`requirements.txt`** — regenerate from a clean venv after adopting the pin:

```powershell
pip install -r requirements.in
pip freeze > requirements.txt
```

**Primary `.venv` repair (operator action, not run automatically):**

```powershell
pip install "protobuf==5.29.6"
pip install "googleapis-common-protos==1.75.0"
pip check
pytest tests/test_step1b_smoke.py -v
```

## Final verdict

**`DEPENDENCY_RESOLVED`**
