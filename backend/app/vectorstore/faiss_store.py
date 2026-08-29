"""
MediRAG AI – FAISS Vector Store (Optional)

Alternative to ChromaDB for pure in-memory or disk-based ANN search.
Activated when VECTOR_STORE_TYPE=faiss in .env.
"""

import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LCDocument

from app.config import settings
from app.embeddings.embedding_service import get_embedding_service
from app.utils.logger import logger


class FAISSVectorStore:
    """
    Persistent FAISS vector store backed by disk serialization.
    Loads an existing index from disk on first use; creates a new one
    when the first batch of documents is added.
    """

    def __init__(self):
        self._store: Optional[FAISS] = None
        self._embedding_service = get_embedding_service()
        self._index_path = settings.faiss_index_path
        Path(self._index_path).mkdir(parents=True, exist_ok=True)

    def _load_or_create(self, texts: List[str], metadatas: List[Dict]) -> FAISS:
        """Load existing index or bootstrap from first batch."""
        index_file = os.path.join(self._index_path, "index.faiss")
        if os.path.exists(index_file):
            logger.info("Loading existing FAISS index from disk.")
            return FAISS.load_local(
                self._index_path,
                self._embedding_service.model,
                allow_dangerous_deserialization=True,
            )
        logger.info("Creating new FAISS index.")
        return FAISS.from_texts(
            texts=texts,
            embedding=self._embedding_service.model,
            metadatas=metadatas,
        )

    def _save(self) -> None:
        if self._store:
            self._store.save_local(self._index_path)

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        if not texts:
            return []

        if self._store is None:
            self._store = self._load_or_create(texts, metadatas)
            added = list(self._store.index_to_docstore_id.values())
        else:
            added = self._store.add_texts(texts=texts, metadatas=metadatas)

        self._save()
        logger.debug(f"FAISS: added {len(added)} vectors.")
        return added

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[LCDocument, float]]:
        if self._store is None:
            index_file = os.path.join(self._index_path, "index.faiss")
            if os.path.exists(index_file):
                self._store = FAISS.load_local(
                    self._index_path,
                    self._embedding_service.model,
                    allow_dangerous_deserialization=True,
                )
            else:
                logger.warning("FAISS index not yet initialised.")
                return []

        return self._store.similarity_search_with_relevance_scores(query=query, k=k)

    def delete_by_document_id(self, document_id: str) -> None:
        """
        FAISS does not natively support selective deletion.
        Rebuild the index minus the target document's vectors.
        """
        if self._store is None:
            return

        # Filter out entries belonging to this document_id
        docstore = self._store.docstore._dict  # type: ignore[attr-defined]
        ids_to_keep = [
            idx for idx, doc in docstore.items()
            if doc.metadata.get("document_id") != document_id
        ]
        if not ids_to_keep:
            # Nothing left – reset
            self._store = None
            for f in Path(self._index_path).glob("*"):
                f.unlink()
            return

        # Reconstruct from surviving documents
        surviving_texts = [docstore[i].page_content for i in ids_to_keep]
        surviving_metas = [docstore[i].metadata for i in ids_to_keep]
        self._store = FAISS.from_texts(
            texts=surviving_texts,
            embedding=self._embedding_service.model,
            metadatas=surviving_metas,
        )
        self._save()
        logger.info(f"FAISS: rebuilt index after removing document {document_id}")

    def get_collection_stats(self) -> Dict[str, Any]:
        if self._store is None:
            return {"type": "faiss", "vector_count": 0}
        return {
            "type": "faiss",
            "vector_count": self._store.index.ntotal,  # type: ignore[attr-defined]
        }
