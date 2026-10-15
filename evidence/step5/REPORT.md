# Step 5 — Part 1 Task 4: Grounded generation and empirical fallback threshold



**Date:** 2026-10-14 (distance semantics corrected same day)  

**Verdict:** STEP_5_TASK_4_COMPLETE



## Collection (provisional for Task 4)



- **Chroma collection:** `nykaa_sentence_chunks` (sentence-based chunks from Task 3)

- **Note:** Task 5 will compare both collections; this choice is practical for Task 4 only, not the deployment recommendation.



## Retrieval and scoring



| Parameter | Value |

|-----------|--------|

| Top-k | 3 |

| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (`normalize_embeddings=True`) |

| Chroma metric | Default **`l2`** → **squared Euclidean** distance in `distances` |

| Cosine interpretation | `cosine_similarity = 1 - raw_chroma_l2_squared / 2` (unit-normalized vectors) |

| Fallback gate | Top-1 **raw squared-L2** ≤ `max_top1_l2_distance` (threshold **1.1129**) |

| Fallback message | `I don't know based on the available policy knowledge base.` |

| Threshold artifact | `app/data/retrieval_threshold.json` |



**Verification:** Chroma `distances[0][0]` matched manual `sum((q - d) ** 2)` on normalized query/doc embeddings (same vector → 0).



## Calibration (Phase A)



| Scope | Query topic | Top-1 parent | Raw L2² | Cosine (= 1 − raw/2) |

|-------|-------------|--------------|---------|----------------------|

| IN_SCOPE | Beauty returns | KB-001 | 0.2364 | 0.8818 |

| IN_SCOPE | COD refunds | KB-002 | 0.7852 | 0.6074 |

| IN_SCOPE | Order cancellation | KB-006 | 0.4880 | 0.7560 |

| OUT_OF_SCOPE | Weather | KB-003 | 1.4406 | 0.2797 |

| OUT_OF_SCOPE | Mathematics | KB-011 | 1.7785 | 0.1108 |



- **Observed in-scope top-1 raw L2² max:** 0.7852  

- **Observed out-of-scope top-1 raw L2² min:** 1.4406  

- **Selected threshold:** `max_top1_l2_distance = 1.1129` (midpoint on **raw** scores; unchanged after cosine fix)  

- **Rationale:** Clear separation on raw squared-L2; midpoint avoids preset constants such as 0.5/0.6/0.7.



Full JSON: [`threshold_calibration.json`](threshold_calibration.json)



## Demonstrations (Phase B)



Five in-scope + one out-of-scope: [`grounded_generation_examples.json`](grounded_generation_examples.json)



MOCK_LLM composer: deterministic string from retrieved chunk text only (`app/grounded_generation.py`).



## Commands



```powershell

python scripts/calibrate_retrieval_threshold.py

python scripts/run_grounded_generation_demo.py

python -m pytest tests/test_grounded_generation.py -v

```



## Test and regression evidence



| Command | Result |

|---------|--------|

| `pytest tests/test_grounded_generation.py -v` | 13 passed — see [`pytest_task4.txt`](pytest_task4.txt) |

| Combined regression (Task 4 + Tasks 1–3 + Step 1B) | 41 passed — see [`pytest_regression.txt`](pytest_regression.txt) |

| `python -m pip check` | No broken requirements — see [`pip_check.txt`](pip_check.txt) |



## Official brief



`docs/MASAI_OFFICIAL_BRIEF.md` — unchanged (SHA-256 verified at commit time).

