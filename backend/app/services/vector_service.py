"""
ChromaDB vector store service.

RBAC is enforced at the database query level inside ``query_documents``.
The ``allowed_sources`` list — derived from the caller's role via
``rbac_service.get_allowed_sources`` — is passed directly as a ChromaDB
``where`` filter.  This means the similarity search never even sees
documents from unauthorised departments; the restriction is structural,
not a post-retrieval filter that could be accidentally bypassed.

Typical data flow
-----------------
1. Ingestion script calls ``add_documents`` with ``metadata={"department": "<dept>", ...}``.
2. At query time, the router resolves the caller's role → allowed_sources.
3. ``query_documents`` issues a single Chroma query::

       where={"department": {"$in": allowed_sources}}

   Chroma applies this filter before ANN search, so no cross-department
   vectors are ever ranked or returned.
"""

import logging
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level client and collection cache — created once on first use.
_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None

COLLECTION_NAME = "finsolve_docs"
DISTANCE_THRESHOLD = 0.8  # Cosine distance; lower = more similar. 0 = identical, 2 = opposite.


def _get_client() -> chromadb.PersistentClient:
    """Return the shared ChromaDB persistent client, creating it if needed."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info("ChromaDB client initialised at '%s'", settings.CHROMA_PERSIST_DIR)
    return _client


def get_or_create_collection() -> chromadb.Collection:
    """Return the shared Chroma collection, creating it with cosine metric if absent.

    The collection is created with ``hnsw:space=cosine`` so that distances
    are in the range [0, 2], where 0 is identical and 2 is maximally dissimilar.
    The ``DISTANCE_THRESHOLD`` of 0.8 therefore keeps only meaningfully
    relevant chunks.

    Returns:
        The ``finsolve_docs`` ChromaDB ``Collection`` object.
    """
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Collection '%s' ready (%d documents).",
            COLLECTION_NAME,
            _collection.count(),
        )
    return _collection


def add_documents(
    texts: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict],
    ids: List[str],
) -> None:
    """Upsert document chunks into the vector store.

    Uses ``upsert`` so that re-running the ingestion script is idempotent —
    existing chunks are overwritten rather than duplicated.

    Args:
        texts:      Raw text of each chunk (stored as the Chroma ``document``).
        embeddings: Pre-computed embedding vectors, one per chunk.
        metadatas:  Metadata dicts for each chunk.  **Every dict must include
                    a ``"department"`` key** (e.g. ``{"department": "finance",
                    "source": "financial_summary.md", "chunk_index": 0}``).
                    The ``department`` value is used by the RBAC ``where``
                    filter at query time.
        ids:        Stable, unique string IDs for each chunk.  Recommended
                    format: ``"<source_filename>_chunk_<index>"``.

    Raises:
        ValueError: If the four lists have mismatched lengths.
    """
    if not (len(texts) == len(embeddings) == len(metadatas) == len(ids)):
        raise ValueError(
            f"All input lists must be the same length. Got: texts={len(texts)}, "
            f"embeddings={len(embeddings)}, metadatas={len(metadatas)}, ids={len(ids)}"
        )

    collection = get_or_create_collection()
    collection.upsert(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )
    logger.info("Upserted %d chunks into '%s'.", len(ids), COLLECTION_NAME)


def query_documents(
    query_embedding: List[float],
    allowed_sources: List[str],
    k: int = 5,
) -> List[Dict]:
    """Retrieve the top-k relevant chunks the caller is permitted to see.

    RBAC is enforced here via the ``where`` filter passed to ChromaDB.
    The filter is evaluated **before** the approximate-nearest-neighbour
    search, so documents from unauthorised departments are structurally
    excluded — they are never ranked, scored, or visible to the caller.

    Args:
        query_embedding:  The embedding vector of the user's question.
        allowed_sources:  Department names the caller may access, as returned
                          by ``rbac_service.get_allowed_sources(role)``.
                          Example: ``["employee_handbook", "finance"]``.
        k:                Maximum number of chunks to return (default 5).

    Returns:
        A list of dicts, each containing:

        - ``text``     (str):   The raw chunk text.
        - ``metadata`` (dict):  Stored metadata including ``department`` and ``source``.
        - ``distance`` (float): Cosine distance from the query (lower = more relevant).

        Only chunks with ``distance <= DISTANCE_THRESHOLD`` (0.8) are included.
        Returns an empty list if the collection is empty or no chunks pass
        the relevance threshold.
    """
    collection = get_or_create_collection()

    if collection.count() == 0:
        logger.warning("Collection '%s' is empty — no documents ingested yet.", COLLECTION_NAME)
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(k, collection.count()),
        where={"department": {"$in": allowed_sources}},
        include=["documents", "metadatas", "distances"],
    )

    chunks: List[Dict] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for text, metadata, distance in zip(documents, metadatas, distances):
        if distance <= DISTANCE_THRESHOLD:
            chunks.append({"text": text, "metadata": metadata, "distance": distance})

    logger.debug(
        "Query returned %d/%d chunks within threshold (allowed_sources=%s).",
        len(chunks),
        len(documents),
        allowed_sources,
    )
    return chunks


def get_collection_count() -> int:
    """Return the total number of chunks currently stored in the collection.

    Returns:
        Integer document count.  Returns 0 if the collection does not yet exist.
    """
    collection = get_or_create_collection()
    return collection.count()