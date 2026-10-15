"""Validation for Part 1 Task 2 knowledge-base policy drafts (structure only)."""

from __future__ import annotations

from knowledge_base.policy_loader import (
    POLICIES_DIR,
    REQUIRED_POLICY_FILES,
    REQUIRED_TOPICS,
    load_all_policy_drafts,
)


def test_exactly_twelve_required_files_exist():
    present = sorted(p.name for p in POLICIES_DIR.glob("KB-*.md"))
    assert present == sorted(REQUIRED_POLICY_FILES)
    assert len(present) == 12


def test_all_topics_represented_once():
    drafts = load_all_policy_drafts()
    topics = [d["topic"] for d in drafts]
    assert len(topics) == len(set(topics))
    assert set(topics) == set(REQUIRED_TOPICS)


def test_document_ids_unique_and_match_filenames():
    drafts = load_all_policy_drafts()
    ids = [d["document_id"] for d in drafts]
    assert len(ids) == len(set(ids))
    for draft in drafts:
        assert draft["document_id"]
        assert draft["document_id"] in draft["filename"]


def test_metadata_and_policy_body_present():
    drafts = load_all_policy_drafts()
    for draft in drafts:
        assert draft["title"]
        assert draft["topic"]
        assert draft["policy_body"].strip()


def test_policy_body_sentence_counts():
    drafts = load_all_policy_drafts()
    for draft in drafts:
        count = int(draft["sentence_count"])
        assert 2 <= count <= 5, (
            f"{draft['document_id']} has {count} policy-body sentences (expected 2–5)"
        )
