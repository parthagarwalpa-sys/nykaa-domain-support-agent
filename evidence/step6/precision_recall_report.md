# Task 5 — Document-level precision and recall

- **Embedding model:** sentence-transformers/all-MiniLM-L6-v2
- **Top-k:** 3
- **Ground truth:** C:\Users\Parth\Projects\MASAI_NYKAA_CAPSTONE\app\data\retrieval_ground_truth.json

## Recommendation

**Recommended strategy:** `fixed` (`nykaa_fixed_chunks`)

Mean precision and recall both tied at 0.6667 / 1.0000; fixed-size indexing is preferred for fewer chunks (39 vs 49) and simpler overlap handling.

## Aggregate — fixed (`nykaa_fixed_chunks`)

- Mean precision: **0.6667**
- Mean recall: **1.0000**
- Mean F1 (supplemental): **0.7667**

## Aggregate — sentence (`nykaa_sentence_chunks`)

- Mean precision: **0.6667**
- Mean recall: **1.0000**
- Mean F1 (supplemental): **0.7667**

### Beauty return eligibility — `eval_01_beauty_return`

**Query:** What is the return eligibility for unused sealed Beauty products?

**Relevant docs:** `{'KB-001'}`

#### Fixed (`nykaa_fixed_chunks`)

- Retrieved chunks: `['KB-001-fixed-001', 'KB-005-fixed-001', 'KB-010-fixed-002']`
- Retrieved parent docs (deduped): `{'KB-010', 'KB-005', 'KB-001'}`
- TP = 1, FP = 2, FN = 0
- precision = TP / (TP + FP) = 1 / (1 + 2) = 1/3 = 0.3333
- recall = TP / (TP + FN) = 1 / (1 + 0) = 1/1 = 1.0000

#### Sentence (`nykaa_sentence_chunks`)

- Retrieved chunks: `['KB-001-sentence-002', 'KB-005-sentence-001', 'KB-010-sentence-003']`
- Retrieved parent docs (deduped): `{'KB-010', 'KB-005', 'KB-001'}`
- TP = 1, FP = 2, FN = 0
- precision = TP / (TP + FP) = 1 / (1 + 2) = 1/3 = 0.3333
- recall = TP / (TP + FN) = 1 / (1 + 0) = 1/1 = 1.0000

### COD refund timeline — `eval_02_cod_refund`

**Query:** What is the timeline for COD refunds to a bank account?

**Relevant docs:** `{'KB-002'}`

#### Fixed (`nykaa_fixed_chunks`)

- Retrieved chunks: `['KB-002-fixed-000', 'KB-002-fixed-001', 'KB-006-fixed-002']`
- Retrieved parent docs (deduped): `{'KB-006', 'KB-002'}`
- TP = 1, FP = 1, FN = 0
- precision = TP / (TP + FP) = 1 / (1 + 1) = 1/2 = 0.5000
- recall = TP / (TP + FN) = 1 / (1 + 0) = 1/1 = 1.0000

#### Sentence (`nykaa_sentence_chunks`)

- Retrieved chunks: `['KB-002-sentence-001', 'KB-002-sentence-002', 'KB-006-sentence-003']`
- Retrieved parent docs (deduped): `{'KB-006', 'KB-002'}`
- TP = 1, FP = 1, FN = 0
- precision = TP / (TP + FP) = 1 / (1 + 1) = 1/2 = 0.5000
- recall = TP / (TP + FN) = 1 / (1 + 0) = 1/1 = 1.0000

### Express delivery SLA — `eval_03_delivery_sla`

**Query:** What is the express delivery SLA for metro tier-1 cities?

**Relevant docs:** `{'KB-003'}`

#### Fixed (`nykaa_fixed_chunks`)

- Retrieved chunks: `['KB-003-fixed-001', 'KB-003-fixed-000', 'KB-011-fixed-000']`
- Retrieved parent docs (deduped): `{'KB-003', 'KB-011'}`
- TP = 1, FP = 1, FN = 0
- precision = TP / (TP + FP) = 1 / (1 + 1) = 1/2 = 0.5000
- recall = TP / (TP + FN) = 1 / (1 + 0) = 1/1 = 1.0000

#### Sentence (`nykaa_sentence_chunks`)

- Retrieved chunks: `['KB-003-sentence-001', 'KB-011-sentence-000', 'KB-003-sentence-002']`
- Retrieved parent docs (deduped): `{'KB-003', 'KB-011'}`
- TP = 1, FP = 1, FN = 0
- precision = TP / (TP + FP) = 1 / (1 + 1) = 1/2 = 0.5000
- recall = TP / (TP + FN) = 1 / (1 + 0) = 1/1 = 1.0000

### Order cancellation while Placed — `eval_04_cancellation_placed`

**Query:** What is the cancellation policy for orders still in Placed status?

**Relevant docs:** `{'KB-006'}`

#### Fixed (`nykaa_fixed_chunks`)

- Retrieved chunks: `['KB-006-fixed-000', 'KB-006-fixed-001', 'KB-006-fixed-002']`
- Retrieved parent docs (deduped): `{'KB-006'}`
- TP = 1, FP = 0, FN = 0
- precision = TP / (TP + FP) = 1 / (1 + 0) = 1/1 = 1.0000
- recall = TP / (TP + FN) = 1 / (1 + 0) = 1/1 = 1.0000

#### Sentence (`nykaa_sentence_chunks`)

- Retrieved chunks: `['KB-006-sentence-002', 'KB-006-sentence-000', 'KB-006-sentence-001']`
- Retrieved parent docs (deduped): `{'KB-006'}`
- TP = 1, FP = 0, FN = 0
- precision = TP / (TP + FP) = 1 / (1 + 0) = 1/1 = 1.0000
- recall = TP / (TP + FN) = 1 / (1 + 0) = 1/1 = 1.0000

### Apparel/Footwear size exchange — `eval_05_size_exchange`

**Query:** How does size exchange work for Apparel and Footwear?

**Relevant docs:** `{'KB-009'}`

#### Fixed (`nykaa_fixed_chunks`)

- Retrieved chunks: `['KB-009-fixed-000', 'KB-009-fixed-001', 'KB-009-fixed-002']`
- Retrieved parent docs (deduped): `{'KB-009'}`
- TP = 1, FP = 0, FN = 0
- precision = TP / (TP + FP) = 1 / (1 + 0) = 1/1 = 1.0000
- recall = TP / (TP + FN) = 1 / (1 + 0) = 1/1 = 1.0000

#### Sentence (`nykaa_sentence_chunks`)

- Retrieved chunks: `['KB-009-sentence-000', 'KB-009-sentence-002', 'KB-009-sentence-001']`
- Retrieved parent docs (deduped): `{'KB-009'}`
- TP = 1, FP = 0, FN = 0
- precision = TP / (TP + FP) = 1 / (1 + 0) = 1/1 = 1.0000
- recall = TP / (TP + FN) = 1 / (1 + 0) = 1/1 = 1.0000

