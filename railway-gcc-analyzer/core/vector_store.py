"""
core/vector_store.py

ChromaDB vector store management for the Railway GCC Contract Risk Analyzer.
Embeds GCC rule texts using the sentence-transformers model 'all-MiniLM-L6-v2'
and stores them in a persistent local ChromaDB collection for semantic retrieval.
"""

import logging
from typing import List, Dict, Any

import chromadb
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class GCCVectorStore:
    """
    Manages a ChromaDB persistent vector collection of Railway GCC rules.

    On construction, initialises the sentence-transformers embedding model
    (all-MiniLM-L6-v2) and connects to (or creates) the 'gcc_rules'
    ChromaDB collection stored at `persist_dir`.

    The embedding model is loaded at startup so that the first user query
    does not incur a cold-start delay.
    """

    COLLECTION_NAME = "gcc_rules"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, persist_dir: str = "./chroma_db") -> None:
        """
        Initialise the GCCVectorStore.

        Args:
            persist_dir: Path to the directory where ChromaDB will persist
                         its data. Must be writable. On Hugging Face Spaces
                         use a path inside the Space's persistent storage.
        """
        logger.info("Loading sentence-transformers model: %s", self.EMBEDDING_MODEL)
        self.model = SentenceTransformer(self.EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully.")

        logger.info("Connecting to ChromaDB at: %s", persist_dir)
        self.client: PersistentClient = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB collection '%s' ready. Documents: %d",
            self.COLLECTION_NAME,
            self.collection.count(),
        )

    def is_populated(self) -> bool:
        """
        Check whether the ChromaDB collection already contains documents.

        Returns:
            True if the collection has at least one document, False otherwise.
        """
        return self.collection.count() > 0

    def populate(self, gcc_rules: List[Dict[str, Any]]) -> None:
        """
        Embed and upsert all GCC rules into the ChromaDB collection.

        This method is idempotent — it checks `is_populated()` first and
        does nothing if the collection already has data, preventing duplicate
        insertions on Space restarts.

        Args:
            gcc_rules: The list of GCC rule dicts from data/gcc_rules.py.
                       Each dict must have keys: clause_id, clause_title,
                       clause_text, risk_category, keywords.
        """
        if self.is_populated():
            logger.info(
                "ChromaDB collection already populated (%d docs). Skipping.",
                self.collection.count(),
            )
            return

        logger.info("Populating ChromaDB with %d GCC rules...", len(gcc_rules))

        ids: List[str] = []
        embeddings: List[List[float]] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for rule in gcc_rules:
            clause_id: str = rule["clause_id"]
            clause_text: str = rule["clause_text"]
            keywords: List[str] = rule.get("keywords", [])

            # Compute embedding for the clause text
            embedding = self.model.encode(clause_text, convert_to_numpy=True).tolist()

            ids.append(clause_id)
            embeddings.append(embedding)
            documents.append(clause_text)
            metadatas.append({
                "clause_id": clause_id,
                "clause_title": rule["clause_title"],
                "risk_category": rule["risk_category"],
                "keywords": ", ".join(keywords),
            })

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(
            "ChromaDB populated: %d rules upserted. Collection size: %d",
            len(gcc_rules),
            self.collection.count(),
        )

    def query(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Perform a semantic similarity search against the GCC rules collection.

        Args:
            query_text: The extracted contract clause text to search for.
            n_results:  Maximum number of matching GCC rules to return.

        Returns:
            A list of metadata dicts for the top matching GCC rules, each with:
            clause_id, clause_title, risk_category, keywords.
            Returns an empty list if the collection is empty or the query fails.
        """
        if not self.is_populated():
            logger.warning("ChromaDB collection is empty. Cannot query.")
            return []

        if not query_text or not query_text.strip():
            return []

        try:
            query_embedding = self.model.encode(query_text, convert_to_numpy=True).tolist()

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count()),
                include=["metadatas", "distances"],
            )

            matched_metadatas: List[Dict[str, Any]] = []
            if results and results.get("metadatas"):
                for meta in results["metadatas"][0]:
                    matched_metadatas.append(dict(meta))

            return matched_metadatas

        except Exception as exc:
            logger.error("ChromaDB query failed: %s", exc)
            return []
