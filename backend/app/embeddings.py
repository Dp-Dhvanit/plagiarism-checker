"""
Local sentence-embedding model for the similarity pipeline (Feature 1).

Uses sentence-transformers/all-MiniLM-L6-v2, per the project spec's
fallback choice — runs fully locally (no external API, no per-request
cost or rate limit), which is what "similarity via embeddings, not an
LLM call" means in practice. Mirrors the lazy-singleton pattern already
used for the local scorer in app/scoring.py.
"""
from __future__ import annotations

import os
import threading

import numpy as np
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2's output dimension

_model = None
_load_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        # Guards against concurrent first requests each loading their own
        # copy of the model (same race as app/scoring.py's TextScorer.load).
        with _load_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Returns an (N, EMBEDDING_DIM) float32 array of L2-normalized embeddings."""
    if not texts:
        return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return vectors.astype(np.float32)


def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity between every row of `a` and every row of `b`.

    Both inputs are expected already L2-normalized (as embed_texts()
    produces), so this is a plain dot product.
    """
    if a.size == 0 or b.size == 0:
        return np.zeros((a.shape[0], b.shape[0]), dtype=np.float32)
    return a @ b.T
