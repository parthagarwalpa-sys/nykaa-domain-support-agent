"""Part 1 Task 3 — chunking, local embeddings, and dual ChromaDB collections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import chromadb
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

from knowledge_base.policy_loader import load_all_policy_drafts

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHROMA_DIR = PROJECT_ROOT / "chroma_data"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_FIXED = "nykaa_fixed_chunks"
COLLECTION_SENTENCE = "nykaa_sentence_chunks"

# Character-based fixed windows: policies are 2–5 sentences (~400–900 chars).
# 220/60 yields 1–4 stable chunks per document without oversized embedding inputs.
FIXED_CHUNK_SIZE_CHARS = 220
FIXED_CHUNK_OVERLAP_CHARS = 60

ChunkStrategy = Literal["fixed", "sentence"]
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_embedder: SentenceTransformer | None = None


@dataclass(frozen=True)
class PolicyDocument:
    document_id: str
    title: str
    topic: str
    source_file: str
    policy_body: str


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    text: str
    document_id: str
    title: str
    topic: str
    source_file: str
    chunk_strategy: ChunkStrategy


def load_policy_documents() -> list[PolicyDocument]:
    rows = load_all_policy_drafts()
    return [
        PolicyDocument(
            document_id=row["document_id"],
            title=row["title"],
            topic=row["topic"],
            source_file=row["filename"],
            policy_body=row["policy_body"],
        )
        for row in rows
    ]


def split_sentences(text: str) -> list[str]:
    cleaned = " ".join(line.strip() for line in text.strip().splitlines() if line.strip())
    if not cleaned:
        return []
    return [part.strip() for part in _SENTENCE_SPLIT.split(cleaned) if part.strip()]


def chunk_fixed_size(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(0, end - overlap)
    return chunks


def build_text_chunks(
    documents: list[PolicyDocument],
    strategy: ChunkStrategy,
    *,
    chunk_size: int = FIXED_CHUNK_SIZE_CHARS,
    overlap: int = FIXED_CHUNK_OVERLAP_CHARS,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for doc in documents:
        if strategy == "fixed":
            parts = chunk_fixed_size(doc.policy_body, chunk_size, overlap)
            id_prefix = f"{doc.document_id}-fixed"
        else:
            parts = split_sentences(doc.policy_body)
            id_prefix = f"{doc.document_id}-sentence"

        if not parts:
            raise ValueError(f"No chunks produced for {doc.document_id} ({strategy})")

        for index, part in enumerate(parts):
            chunks.append(
                TextChunk(
                    chunk_id=f"{id_prefix}-{index:03d}",
                    text=part,
                    document_id=doc.document_id,
                    title=doc.title,
                    topic=doc.topic,
                    source_file=doc.source_file,
                    chunk_strategy=strategy,
                )
            )
    return chunks


def get_embedder(model_name: str = EMBEDDING_MODEL_NAME) -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(model_name)
    return _embedder


def reset_embedder_cache() -> None:
    global _embedder
    _embedder = None


def _chunk_to_metadata(chunk: TextChunk) -> dict[str, str]:
    return {
        "document_id": chunk.document_id,
        "title": chunk.title,
        "topic": chunk.topic,
        "source_file": chunk.source_file,
        "chunk_strategy": chunk.chunk_strategy,
    }


def upsert_chunks_to_collection(
    collection: Collection,
    chunks: list[TextChunk],
    embedder: SentenceTransformer,
) -> int:
    if not chunks:
        return 0
    texts = [chunk.text for chunk in chunks]
    embeddings = embedder.encode(texts, normalize_embeddings=True).tolist()
    collection.upsert(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[_chunk_to_metadata(chunk) for chunk in chunks],
    )
    return len(chunks)


def get_chroma_client(persist_dir: Path | str = DEFAULT_CHROMA_DIR) -> chromadb.ClientAPI:
    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


def rebuild_collections(
    persist_dir: Path | str = DEFAULT_CHROMA_DIR,
    *,
    embedder: SentenceTransformer | None = None,
) -> dict[str, Any]:
    """Build or refresh both Chroma collections from approved KB policies."""
    documents = load_policy_documents()
    fixed_chunks = build_text_chunks(documents, "fixed")
    sentence_chunks = build_text_chunks(documents, "sentence")

    model = embedder or get_embedder()
    client = get_chroma_client(persist_dir)

    fixed_col = client.get_or_create_collection(name=COLLECTION_FIXED)
    sentence_col = client.get_or_create_collection(name=COLLECTION_SENTENCE)

    fixed_count = upsert_chunks_to_collection(fixed_col, fixed_chunks, model)
    sentence_count = upsert_chunks_to_collection(sentence_col, sentence_chunks, model)

    return {
        "embedding_model": EMBEDDING_MODEL_NAME,
        "document_count": len(documents),
        "fixed_chunk_count": fixed_count,
        "sentence_chunk_count": sentence_count,
        "collections": {
            COLLECTION_FIXED: fixed_count,
            COLLECTION_SENTENCE: sentence_count,
        },
        "fixed_chunk_size": FIXED_CHUNK_SIZE_CHARS,
        "fixed_overlap": FIXED_CHUNK_OVERLAP_CHARS,
        "persist_dir": str(Path(persist_dir).resolve()),
    }


def query_collection(
    collection: Collection,
    query_text: str,
    embedder: SentenceTransformer,
    n_results: int = 3,
) -> dict[str, Any]:
    query_embedding = embedder.encode([query_text], normalize_embeddings=True).tolist()
    return collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
