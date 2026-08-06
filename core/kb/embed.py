"""Embedding model access.

The model is loaded once and reused. Loading takes several seconds, which is
tolerable at build time and not tolerable per turn of a phone call.

Embeddings are normalized on output so that a dot product is a cosine
similarity. This matters for the retrieval threshold: scores are then comparable
across queries and a fixed cut-off means the same thing every time.
"""

from __future__ import annotations

import os
from functools import lru_cache

import numpy as np


@lru_cache(maxsize=2)
def _load(model_name: str, device: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device=device)


def model_name(multilingual: bool = False) -> str:
    """The embedding model for a corpus.

    The Philippine and Indonesian corpus uses a multilingual model rather than the
    English one, and it is a separate index rather than a shared one. Similarity
    scales differ between the two models, so a single abstention threshold cannot
    serve both; each corpus is calibrated on its own queries.
    """
    if multilingual:
        return os.getenv(
            "EMBED_MODEL_MULTILINGUAL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
    return os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")


def device() -> str:
    requested = os.getenv("EMBED_DEVICE", "cpu")
    if requested == "cuda":
        try:
            import torch

            if not torch.cuda.is_available():
                return "cpu"
        except Exception:  # noqa: BLE001 - fall back rather than fail a build
            return "cpu"
    return requested


def dimension(multilingual: bool = False) -> int:
    model = _load(model_name(multilingual), device())
    # The accessor was renamed; support both so a library upgrade does not break
    # the build.
    getter = getattr(model, "get_embedding_dimension", None) or getattr(
        model, "get_sentence_embedding_dimension"
    )
    return getter()


def encode(texts: list[str], multilingual: bool = False, batch_size: int = 32) -> np.ndarray:
    """Embed documents. Returns a float32 array of shape (len(texts), dim)."""
    model = _load(model_name(multilingual), device())
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 200,
        convert_to_numpy=True,
    )
    return np.asarray(vectors, dtype="float32")


def encode_query(text: str, multilingual: bool = False) -> np.ndarray:
    """Embed a single query.

    The bge family is trained with an instruction prefix on the query side only.
    Applying it lifts retrieval measurably, and applying it to documents as well
    would undo the benefit.
    """
    name = model_name(multilingual)
    if "bge" in name and "bge-m3" not in name:
        text = f"Represent this sentence for searching relevant passages: {text}"
    return encode([text], multilingual=multilingual)[0]
