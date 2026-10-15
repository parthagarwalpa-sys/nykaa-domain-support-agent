# Step 4 — Part 1 Task 3 (chunking, embeddings, ChromaDB)

**Date:** 2026-10-14  
**Verdict:** `STEP_4_TASK_3_COMPLETE`

## Embedding model

- `sentence-transformers/all-MiniLM-L6-v2` (local SentenceTransformers; no external embedding API)

## Chunking

| Strategy | Parameters | Chunk count |
|----------|------------|-------------|
| Fixed-size with overlap | 220 characters, 60 overlap | **39** |
| Sentence-based | Regex split on `.!?` boundaries | **49** |

**Rationale for 220/60:** Approved policies are short (2–5 sentences, ~400–900 characters). A 220-character window with 60-character overlap produces 1–4 reproducible chunks per document without oversized embedding inputs, while still splitting longer policies for retrieval granularity.

## ChromaDB

| Collection | Records | Persist path |
|------------|---------|--------------|
| `nykaa_fixed_chunks` | 39 | `chroma_data/` (gitignored) |
| `nykaa_sentence_chunks` | 49 | `chroma_data/` (gitignored) |

Ingestion uses `collection.upsert()` with embeddings and metadata: `document_id`, `title`, `topic`, `source_file`, `chunk_strategy`.

## Sample retrieval (verification only)

**Fixed collection** — query: *What is the return window for Beauty products?*  
Top hit: `KB-001-fixed-001` → parent `KB-001`, topic *return window by product category*.

**Sentence collection** — query: *How are cash on delivery refunds processed?*  
Top hit: `KB-002-sentence-000` → parent `KB-002`, topic *COD refund timelines*.

Full JSON: `index_build.json`, `index_build_console.txt`.

## Commands

```powershell
python scripts/rebuild_kb_index.py
python -m pytest tests/test_rag_index.py -v
```

## Validation summary

| Check | Result |
|-------|--------|
| `tests/test_rag_index.py` | 8 passed |
| `tests/test_dataset.py` | 9 passed |
| `tests/test_knowledge_base_drafts.py` | 5 passed |
| `tests/test_step1b_smoke.py` | 6 passed |
| `pip check` | No broken requirements found |

See `pytest_all.txt`, `pip_check.txt`.

## Out of scope (not implemented)

- Grounded generation, fallback threshold (Task 4)
- Precision/recall comparison (Task 5)
