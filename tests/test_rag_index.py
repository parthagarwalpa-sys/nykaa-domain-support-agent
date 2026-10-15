"""Part 1 Task 3 — chunking, embeddings, and ChromaDB collection tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.rag import (
    COLLECTION_FIXED,
    COLLECTION_SENTENCE,
    FIXED_CHUNK_OVERLAP_CHARS,
    FIXED_CHUNK_SIZE_CHARS,
    build_text_chunks,
    get_chroma_client,
    get_embedder,
    load_policy_documents,
    query_collection,
    rebuild_collections,
    split_sentences,
    upsert_chunks_to_collection,
)
from knowledge_base.policy_loader import REQUIRED_POLICY_FILES


@pytest.fixture(scope="module")
def embedder():
    return get_embedder()


@pytest.fixture(scope="module")
def built_index(tmp_path_factory, embedder):
    persist = tmp_path_factory.mktemp("chroma_task3")
    stats = rebuild_collections(persist_dir=persist, embedder=embedder)
    client = get_chroma_client(persist)
    return {"persist": persist, "stats": stats, "client": client, "embedder": embedder}


def test_load_twelve_policy_documents():
    docs = load_policy_documents()
    assert len(docs) == 12
    filenames = {doc.source_file for doc in docs}
    assert filenames == set(REQUIRED_POLICY_FILES)
    for doc in docs:
        assert doc.document_id.startswith("KB-")
        assert doc.title
        assert doc.topic
        assert doc.policy_body.strip()


def test_fixed_and_sentence_chunking_non_empty_and_deterministic():
    docs = load_policy_documents()
    fixed_a = build_text_chunks(docs, "fixed")
    fixed_b = build_text_chunks(docs, "fixed")
    sentence_a = build_text_chunks(docs, "sentence")
    sentence_b = build_text_chunks(docs, "sentence")

    assert fixed_a and sentence_a
    assert fixed_a == fixed_b
    assert sentence_a == sentence_b

    for chunk in fixed_a + sentence_a:
        assert chunk.text.strip()
        assert chunk.document_id
        assert chunk.source_file
        assert chunk.chunk_strategy in ("fixed", "sentence")

    fixed_ids = [c.chunk_id for c in fixed_a]
    sentence_ids = [c.chunk_id for c in sentence_a]
    assert len(fixed_ids) == len(set(fixed_ids))
    assert len(sentence_ids) == len(set(sentence_ids))


def test_chunks_map_to_parent_documents():
    docs = load_policy_documents()
    doc_ids = {d.document_id for d in docs}
    for chunk in build_text_chunks(docs, "fixed") + build_text_chunks(docs, "sentence"):
        assert chunk.document_id in doc_ids


def test_sentence_splitter_preserves_whole_sentences():
    sample = "First sentence here. Second sentence follows! Third one?"
    parts = split_sentences(sample)
    assert len(parts) == 3
    assert parts[0].endswith(".")
    assert parts[1].endswith("!")


def test_upsert_is_used_during_rebuild(built_index):
    """Ensure Chroma upsert path is invoked (Masai requirement)."""
    with patch("app.rag.upsert_chunks_to_collection", wraps=upsert_chunks_to_collection) as spy:
        rebuild_collections(
            persist_dir=built_index["persist"],
            embedder=built_index["embedder"],
        )
    assert spy.call_count == 2


def test_two_separate_collections_with_expected_counts(built_index):
    stats = built_index["stats"]
    client = built_index["client"]

    fixed_col = client.get_collection(COLLECTION_FIXED)
    sentence_col = client.get_collection(COLLECTION_SENTENCE)

    assert fixed_col.count() == stats["fixed_chunk_count"]
    assert sentence_col.count() == stats["sentence_chunk_count"]
    assert fixed_col.name != sentence_col.name
    assert stats["fixed_chunk_count"] > 0
    assert stats["sentence_chunk_count"] > 0


def test_sample_retrieval_returns_parent_metadata(built_index):
    embedder = built_index["embedder"]
    client = built_index["client"]

    beauty_query = "return window for Beauty sealed products"
    fixed_col = client.get_collection(COLLECTION_FIXED)
    fixed_result = query_collection(fixed_col, beauty_query, embedder, n_results=3)

    assert fixed_result["ids"] and fixed_result["metadatas"]
    top_meta = fixed_result["metadatas"][0][0]
    assert top_meta["document_id"]
    assert top_meta["topic"]
    assert top_meta["source_file"]
    assert top_meta["chunk_strategy"] == "fixed"
    joined_fixed = " ".join(fixed_result["documents"][0]).lower()
    assert top_meta["document_id"] == "KB-001" or "beauty" in joined_fixed

    cod_query = "COD refund bank account timeline"
    sentence_col = client.get_collection(COLLECTION_SENTENCE)
    sentence_result = query_collection(sentence_col, cod_query, embedder, n_results=3)
    sent_meta = sentence_result["metadatas"][0][0]
    assert sent_meta["chunk_strategy"] == "sentence"
    assert sent_meta["document_id"].startswith("KB-")
    joined_sentence = " ".join(sentence_result["documents"][0]).lower()
    assert sent_meta["document_id"] == "KB-002" or "cod" in joined_sentence or "refund" in joined_sentence


def test_chunk_parameters_documented():
    assert FIXED_CHUNK_SIZE_CHARS == 220
    assert FIXED_CHUNK_OVERLAP_CHARS == 60
    assert FIXED_CHUNK_OVERLAP_CHARS < FIXED_CHUNK_SIZE_CHARS
