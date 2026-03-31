"""
Document ingestion pipeline for FinSolve RAG Chatbot.

Reads all source documents from the data/ folder, chunks them, embeds them
with the local sentence-transformer model, and upserts them into ChromaDB
with role-access metadata so the RBAC ``where`` filter works at query time.

Usage (run from the backend/ directory)::

    python scripts/ingest.py

The script always performs a full re-ingest: the existing ChromaDB collection
is deleted and recreated so stale chunks from renamed or removed files cannot
accumulate.
"""

import sys
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — allows importing from app/ when run as a plain script
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent  # .../backend/
sys.path.insert(0, str(_BACKEND_DIR))

from langchain.text_splitter import RecursiveCharacterTextSplitter          # noqa: E402
from langchain_community.document_loaders import CSVLoader, TextLoader      # noqa: E402
from langchain_community.document_loaders import UnstructuredMarkdownLoader  # noqa: E402

from app.core.config import settings                                          # noqa: E402
from app.services.embed_service import embed_texts                           # noqa: E402
from app.services.vector_service import add_documents, get_or_create_collection  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DATA_DIR = _BACKEND_DIR.parent / "data"

# Single source of truth for what gets ingested and which department tag it receives.
# IMPORTANT: department names here MUST exactly match ROLE_PERMISSIONS in rbac_service.py.
# employee_handbook → accessible to ALL roles.
# hr               → accessible to hr and c_level only.
DEPARTMENT_CONFIG = [
    {
        "files": ["data/engineering/engineering_master_doc.md"],
        "department": "engineering",
    },
    {
        "files": [
            "data/finance/financial_summary.md",
            "data/finance/quarterly_financial_report.md",
        ],
        "department": "finance",
    },
    {
        "files": ["data/hr/hr_data.csv"],
        "department": "hr",
    },
    {
        "files": ["data/hr/employee_handbook.md"],
        "department": "employee_handbook",
    },
    {
        "files": [
            "data/marketing/marketing_report_2024.md",
            "data/marketing/marketing_report_q1_2024.md",
            "data/marketing/marketing_report_q2_2024.md",
            "data/marketing/marketing_report_q3_2024.md",
            "data/marketing/market_report_q4_2024.md",
        ],
        "department": "marketing",
    },
]

SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n", "\n", " ", ""],
)


# ---------------------------------------------------------------------------
# Loader helpers
# ---------------------------------------------------------------------------


def _load_file(path: Path) -> list:
    """Load a single file and return a list of LangChain ``Document`` objects.

    Supports ``.md``, ``.txt``, ``.csv``, and ``.docx`` files.
    Unrecognised extensions are skipped with a warning.

    Args:
        path: Absolute path to the file to load.

    Returns:
        A (possibly empty) list of ``Document`` objects.
    """
    suffix = path.suffix.lower()
    try:
        if suffix in (".md", ".txt"):
            try:
                loader = UnstructuredMarkdownLoader(str(path))
                docs = loader.load()
                if not docs:
                    raise ValueError("UnstructuredMarkdownLoader returned empty — fallback")
            except Exception:
                # Graceful fallback if unstructured is not fully installed.
                loader = TextLoader(str(path), encoding="utf-8")
                docs = loader.load()
        elif suffix == ".csv":
            loader = CSVLoader(str(path), encoding="utf-8")
            docs = loader.load()
        elif suffix == ".docx":
            from langchain_community.document_loaders import Docx2txtLoader  # noqa: PLC0415
            loader = Docx2txtLoader(str(path))
            docs = loader.load()
        else:
            print(f"  ⚠️  Skipping unsupported file type: {path.name}")
            return []
    except Exception as exc:
        print(f"  ❌  Failed to load {path.name}: {exc}")
        return []

    return docs


# ---------------------------------------------------------------------------
# Main ingestion entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full ingestion pipeline."""
    print("\n" + "=" * 60)
    print("  FinSolve Document Ingestion Pipeline")
    print("=" * 60)

    # 1. Clear existing collection for a clean re-ingest.
    print("\n🗑️  Clearing existing ChromaDB collection...")
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    client = chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection("finsolve_docs")
        print("   Collection deleted.")
    except Exception:
        print("   No existing collection found — starting fresh.")

    # Force vector_service to recreate its cached collection reference.
    import app.services.vector_service as vs
    vs._collection = None  # noqa: SLF001

    get_or_create_collection()
    print("   New collection created.\n")

    # 2. Collect all chunks across all entries in DEPARTMENT_CONFIG.
    all_texts:     list[str]  = []
    all_metadatas: list[dict] = []
    all_ids:       list[str]  = []

    # Root of the repo (one level above backend/)
    _REPO_DIR = _BACKEND_DIR.parent

    for entry in DEPARTMENT_CONFIG:
        department: str = entry["department"]
        file_paths: list[str] = entry["files"]
        print(f"\n📂  department='{department}'")

        for rel_path in file_paths:
            abs_path = _REPO_DIR / rel_path

            if not abs_path.exists():
                print(f"  ⚠️  File not found, skipping: {abs_path}")
                continue

            docs = _load_file(abs_path)
            if not docs:
                continue

            chunks = SPLITTER.split_documents(docs)
            print(f"    📄  {abs_path.name}: {len(docs)} doc(s) → {len(chunks)} chunks")

            for chunk_index, chunk in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                all_texts.append(chunk.page_content)
                all_metadatas.append({
                    "department": department,
                    "source": abs_path.name,
                    "chunk_index": chunk_index,
                })
                all_ids.append(chunk_id)

    if not all_texts:
        print("\n❌  No documents found. Aborting.")
        sys.exit(1)

    print(f"\n📊  Total chunks to embed: {len(all_texts)}")

    # 3. Embed all chunks in one batched call.
    print("\n🔢  Generating embeddings...")
    embeddings = embed_texts(all_texts)
    print(f"   Embedded {len(embeddings)} chunks.")

    # 4. Upsert into ChromaDB.
    print("\n💾  Storing in ChromaDB...")
    add_documents(
        texts=all_texts,
        embeddings=embeddings,
        metadatas=all_metadatas,
        ids=all_ids,
    )

    # 5. Verify final count.
    from app.services.vector_service import get_collection_count
    final_count = get_collection_count()
    print(f"\n✅  Ingestion complete — {final_count} chunks stored in ChromaDB.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
