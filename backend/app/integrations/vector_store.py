"""
Vector Store client usando ChromaDB per RAG.

FASE 9: RAG System
"""
import logging
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class VectorStoreClient:
    """Client per vector database ChromaDB."""

    def __init__(self):
        """Inizializza ChromaDB client."""
        self.client = None
        self.collection = None
        self.embedding_function = None
        self._initialize()

    def _initialize(self):
        """Inizializza connessione e collection."""
        try:
            # ChromaDB client
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_PATH,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Embedding function
            if settings.EMBEDDING_PROVIDER == "openai":
                self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=settings.OPENAI_API_KEY,
                    model_name=settings.EMBEDDING_MODEL
                )
            else:
                # Sentence Transformers (locale)
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=settings.EMBEDDING_MODEL
                )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="snals_documents",
                embedding_function=self.embedding_function,
                metadata={"description": "SNALS documents for RAG"}
            )

            logger.info(f"✅ ChromaDB inizializzato: {self.collection.count()} documenti")

        except Exception as e:
            logger.error(f"❌ Errore inizializzazione ChromaDB: {e}")
            raise

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> bool:
        """
        Aggiunge documenti al vector store.

        Args:
            documents: Lista testi da embeddare
            metadatas: Lista metadata per ogni documento
            ids: Lista ID univoci

        Returns:
            bool: True se successo
        """
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"✅ Aggiunti {len(documents)} documenti al vector store")
            return True

        except Exception as e:
            logger.error(f"❌ Errore aggiunta documenti: {e}")
            return False

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Cerca documenti simili alla query.

        Args:
            query: Testo query
            n_results: Numero risultati da restituire
            filter_metadata: Filtri sui metadata

        Returns:
            Dict con results
        """
        try:
            where = filter_metadata if filter_metadata else None

            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            logger.info(f"✅ Trovati {len(results['documents'][0])} documenti rilevanti")
            return {
                'documents': results['documents'][0],
                'metadatas': results['metadatas'][0],
                'distances': results['distances'][0]
            }

        except Exception as e:
            logger.error(f"❌ Errore ricerca: {e}")
            return {'documents': [], 'metadatas': [], 'distances': []}

    def delete_documents(self, ids: List[str]) -> bool:
        """
        Elimina documenti dal vector store.

        Args:
            ids: Lista ID da eliminare

        Returns:
            bool: True se successo
        """
        try:
            self.collection.delete(ids=ids)
            logger.info(f"✅ Eliminati {len(ids)} documenti")
            return True

        except Exception as e:
            logger.error(f"❌ Errore eliminazione: {e}")
            return False

    def update_document(
        self,
        id: str,
        document: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Aggiorna un documento esistente.

        Args:
            id: ID documento
            document: Nuovo testo
            metadata: Nuovi metadata

        Returns:
            bool: True se successo
        """
        try:
            self.collection.update(
                ids=[id],
                documents=[document],
                metadatas=[metadata]
            )
            logger.info(f"✅ Documento {id} aggiornato")
            return True

        except Exception as e:
            logger.error(f"❌ Errore aggiornamento: {e}")
            return False

    def get_stats(self) -> Dict:
        """
        Statistiche vector store.

        Returns:
            Dict con statistiche
        """
        try:
            count = self.collection.count()

            # Peek alcuni documenti per metadata
            peek = self.collection.peek(limit=10)

            return {
                'total_documents': count,
                'collection_name': self.collection.name,
                'embedding_function': settings.EMBEDDING_MODEL,
                'sample_metadata': peek['metadatas'][:3] if peek['metadatas'] else []
            }

        except Exception as e:
            logger.error(f"❌ Errore stats: {e}")
            return {}

    def reset(self) -> bool:
        """
        Reset completo del vector store (ATTENZIONE!).

        Returns:
            bool: True se successo
        """
        try:
            self.client.delete_collection(name="snals_documents")
            self._initialize()
            logger.warning("⚠️ Vector store resettato!")
            return True

        except Exception as e:
            logger.error(f"❌ Errore reset: {e}")
            return False
