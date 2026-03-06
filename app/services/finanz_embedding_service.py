# -*- coding: utf-8 -*-
"""
Finanzberatung Document Embedding Service

Embeds document text into vector space for similarity search:
- Chunking with tiktoken (4000 tokens, 200 overlap)
- Embedding via sentence-transformers multilingual model
- Storage in ChromaDB collection per session
- Similarity search for finding related documents/contracts

Gracefully degrades if ML dependencies are not installed.
"""

import logging
from typing import Optional

from app.config.base import Config, FinanzConfig as finanz_config
from app.models import get_db_session
from app.models.finanzberatung import FinanzDocument, DocumentStatus

logger = logging.getLogger(__name__)

# Optional ML imports
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


class FinanzEmbeddingService:
    """Embeds financial document text for semantic search."""

    def __init__(self):
        self._model = None
        self._chroma_client = None

    @property
    def is_available(self) -> bool:
        """Check if all ML dependencies are available."""
        return HAS_TIKTOKEN and HAS_SENTENCE_TRANSFORMERS and HAS_CHROMADB

    def _get_model(self):
        """Lazy-load the sentence transformer model."""
        if self._model is None and HAS_SENTENCE_TRANSFORMERS:
            model_name = finanz_config.FINANZ_EMBEDDING_MODEL
            self._model = SentenceTransformer(model_name)
        return self._model

    def _get_chroma_client(self):
        """Lazy-load ChromaDB client."""
        if self._chroma_client is None and HAS_CHROMADB:
            import os
            chroma_path = finanz_config.get_chromadb_path()
            os.makedirs(chroma_path, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=chroma_path)
        return self._chroma_client

    def _get_collection(self, session_id: int):
        """Get or create a ChromaDB collection for a session."""
        client = self._get_chroma_client()
        if client is None:
            return None
        return client.get_or_create_collection(
            name=f"finanz_session_{session_id}",
            metadata={"hnsw:space": "cosine"},
        )

    def chunk_text(self, text: str, chunk_size: int = 4000, overlap: int = 200) -> list[str]:
        """
        Split text into chunks using tiktoken token counting.

        Falls back to character-based chunking if tiktoken unavailable.
        """
        if not text or not text.strip():
            return []

        if not HAS_TIKTOKEN:
            # Character-based fallback
            chunks = []
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunks.append(text[start:end])
                start = end - overlap
            return chunks

        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)

        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = enc.decode(chunk_tokens)
            chunks.append(chunk_text)
            start = end - overlap

        return chunks

    def embed_document(self, document_id: int) -> dict:
        """
        Embed a document's text into the session's ChromaDB collection.

        Args:
            document_id: ID of the FinanzDocument

        Returns:
            Dict with 'chunk_count', 'collection_name'
        """
        if not self.is_available:
            logger.info("Embedding dependencies not available — skipping doc %s", document_id)
            return {"chunk_count": 0, "collection_name": None, "skipped": True}

        db = get_db_session()
        try:
            doc = db.query(FinanzDocument).filter(
                FinanzDocument.id == document_id
            ).first()
            if doc is None:
                raise ValueError(f"Document {document_id} not found")

            # Update status to EMBEDDING
            doc.status = DocumentStatus.EMBEDDING
            db.commit()

            text = doc.extracted_text or ""
            if not text.strip():
                logger.warning("Document %s has no extracted text — skipping embedding", document_id)
                doc.status = DocumentStatus.EMBEDDED
                db.commit()
                return {"chunk_count": 0, "collection_name": None, "skipped": True}

            # Chunk text
            chunk_size = finanz_config.FINANZ_CHUNK_SIZE
            chunk_overlap = finanz_config.FINANZ_CHUNK_OVERLAP

            chunks = self.chunk_text(text, chunk_size, chunk_overlap)
            if not chunks:
                return {"chunk_count": 0, "collection_name": None, "skipped": True}

            # Embed chunks
            model = self._get_model()
            embeddings = model.encode(chunks, show_progress_bar=False).tolist()

            # Store in ChromaDB
            collection = self._get_collection(doc.session_id)
            if collection is None:
                return {"chunk_count": 0, "collection_name": None, "skipped": True}

            ids = [f"doc{document_id}_chunk{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "document_id": str(document_id),
                    "chunk_index": i,
                    "filename": doc.original_filename,
                    "document_type": doc.document_type or "unknown",
                }
                for i in range(len(chunks))
            ]

            # Upsert (handles re-embedding)
            collection.upsert(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            # Update status to EMBEDDED
            doc.status = DocumentStatus.EMBEDDED
            db.commit()

            collection_name = f"finanz_session_{doc.session_id}"
            logger.info(
                "Document %s embedded: %d chunks in collection '%s'",
                document_id, len(chunks), collection_name,
            )
            return {
                "chunk_count": len(chunks),
                "collection_name": collection_name,
                "skipped": False,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error("Embedding error for doc %s: %s", document_id, e, exc_info=True)
            raise
        finally:
            db.close()

    def search_similar(
        self, session_id: int, query: str, n_results: int = 5
    ) -> list[dict]:
        """
        Search for similar text chunks within a session's documents.

        Args:
            session_id: Session to search in
            query: Search query text
            n_results: Number of results to return

        Returns:
            List of dicts with 'text', 'document_id', 'filename', 'distance'
        """
        if not self.is_available:
            return []

        try:
            model = self._get_model()
            collection = self._get_collection(session_id)
            if collection is None:
                return []

            query_embedding = model.encode([query], show_progress_bar=False).tolist()

            results = collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
            )

            output = []
            if results and results.get("documents"):
                for i, doc_text in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                    dist = results["distances"][0][i] if results.get("distances") else None
                    output.append({
                        "text": doc_text,
                        "document_id": meta.get("document_id"),
                        "filename": meta.get("filename"),
                        "document_type": meta.get("document_type"),
                        "distance": dist,
                    })

            return output

        except Exception as e:
            logger.error("Similarity search error for session %s: %s", session_id, e, exc_info=True)
            return []
