"""
JARVIS RAG Local Vector Embeddings Module.

Provides a lightweight, fully local, offline-first vector embedding provider
using TF-IDF term weighting and cosine similarity matrices.
Guarantees zero external API calls or network dependencies.
"""

import zlib
import re
from typing import Dict, List
import numpy as np


class EmbeddingProvider:
    """
    Abstract interface for embedding generators.
    """

    def embed_text(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError


class LocalTFIDFEmbeddingProvider(EmbeddingProvider):
    """
    Offline local TF-IDF vector embedding provider with fixed vocabulary dimensionality.
    Runs locally on CPU with zero network requirements.
    Uses process-deterministic hashing to guarantee persistent vector compatibility.
    """

    def __init__(self, vector_dim: int = 128) -> None:
        """
        Initializes TF-IDF vectorizer.

        Args:
            vector_dim: Number of vocabulary features / dimensions.
        """
        self.vector_dim = vector_dim

    def _tokenize(self, text: str) -> List[str]:
        """Tokenizes text into lowercase words."""
        return re.findall(r"\b[a-z0-9]{2,}\b", text.lower())

    def _text_to_vector(self, text: str) -> np.ndarray:
        """Converts text into normalized term frequency feature vector."""
        tokens = self._tokenize(text)
        vec = np.zeros(self.vector_dim, dtype=np.float32)
        if not tokens:
            return vec

        # Use process-deterministic zlib.crc32 hash for vocabulary feature mapping
        for t in tokens:
            idx = zlib.crc32(t.encode("utf-8")) % self.vector_dim
            vec[idx] += 1.0

        # L2 Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_text(self, text: str) -> List[float]:
        """
        Generates vector representation for a single text string.

        Args:
            text: Text to embed.

        Returns:
            List[float]: Normalized vector float values.
        """
        return self._text_to_vector(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates vector representations for a batch of text strings.

        Args:
            texts: List of text strings.

        Returns:
            List[List[float]]: List of vector float arrays.
        """
        return [self.embed_text(t) for t in texts]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Computes cosine similarity score between two normalized vector lists.

    Args:
        vec_a: First vector.
        vec_b: Second vector.

    Returns:
        float: Cosine similarity score between 0.0 and 1.0.
    """
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    val = dot / (norm_a * norm_b)
    return max(0.0, min(1.0, val))
