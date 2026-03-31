"""
embed_service.py
----------------
Text embedding service using the sentence-transformers library.

The SentenceTransformer model is loaded once at import time so it is shared
across the entire application lifetime, avoiding redundant loading overhead.
"""

from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Module-level model loading — happens once when the module is first imported.
# ---------------------------------------------------------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Embedding model loaded: all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    """Embed a single string and return a plain Python list of floats.

    Parameters
    ----------
    text:
        The input string to embed.

    Returns
    -------
    list[float]
        A 1-D list of floats representing the embedding vector.
    """
    return model.encode(text).tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings and return a list of embedding vectors.

    Encoding the full batch at once is significantly more efficient than
    calling :func:`embed_text` in a loop because the model can process
    multiple sentences in parallel on the same hardware.

    Parameters
    ----------
    texts:
        A list of input strings to embed.

    Returns
    -------
    list[list[float]]
        A list where each element is a 1-D list of floats representing the
        embedding vector for the corresponding input string.
    """
    return model.encode(texts).tolist()
