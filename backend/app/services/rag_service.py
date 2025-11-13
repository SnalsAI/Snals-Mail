"""
RAG Service per generare risposte usando documenti rilevanti.

FASE 9: RAG System
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models.documento import Documento, TipoDocumento
from app.integrations.vector_store import VectorStoreClient
from app.integrations.llm_client import LLMClient
from app.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


class RAGService:
    """Servizio RAG per generare risposte informate."""

    def __init__(self, db: Session):
        """
        Inizializza RAG service.

        Args:
            db: Sessione database
        """
        self.db = db
        self.vector_store = VectorStoreClient()
        self.llm_client = LLMClient()
        self.doc_processor = DocumentProcessor()

    def embed_documento(self, documento_id: int) -> bool:
        """
        Embedda un documento nel vector store.

        Args:
            documento_id: ID documento

        Returns:
            bool: True se successo
        """
        documento = self.db.query(Documento).filter(Documento.id == documento_id).first()

        if not documento:
            logger.error(f"Documento {documento_id} non trovato")
            return False

        if not documento.embedding_abilitato:
            logger.info(f"Embedding non abilitato per documento {documento_id}")
            return False

        try:
            # Processa documento
            chunks, metadatas, ids = self.doc_processor.process_document_for_embedding(
                documento.file_path,
                documento.id,
                {
                    'tipo': documento.tipo.value,
                    'titolo': documento.titolo,
                    'data_documento': documento.data_documento.isoformat() if documento.data_documento else None,
                    'priorita': documento.priorita
                }
            )

            if not chunks:
                logger.warning(f"Nessun chunk generato per documento {documento_id}")
                return False

            # Aggiungi al vector store
            success = self.vector_store.add_documents(chunks, metadatas, ids)

            if success:
                documento.stato = "embeddato"
                documento.num_chunks = len(chunks)
                documento.vector_store_id = f"doc_{documento.id}"
                from datetime import datetime
                documento.embeddato_at = datetime.now()
                self.db.commit()

                logger.info(f"✅ Documento {documento_id} embeddato: {len(chunks)} chunks")
                return True
            else:
                documento.stato = "errore"
                documento.errore_messaggio = "Errore aggiunta vector store"
                self.db.commit()
                return False

        except Exception as e:
            logger.error(f"❌ Errore embedding documento {documento_id}: {e}")
            documento.stato = "errore"
            documento.errore_messaggio = str(e)
            self.db.commit()
            return False

    def retrieve_relevant_documents(
        self,
        query: str,
        n_results: int = 5,
        tipo_filter: Optional[List[TipoDocumento]] = None
    ) -> List[Dict]:
        """
        Recupera documenti rilevanti per una query.

        Args:
            query: Query di ricerca
            n_results: Numero risultati
            tipo_filter: Filtra per tipo documento

        Returns:
            List[Dict]: Documenti rilevanti con score
        """
        try:
            # Prepara filtri
            filter_metadata = None
            if tipo_filter:
                filter_metadata = {"tipo": {"$in": [t.value for t in tipo_filter]}}

            # Cerca nel vector store
            results = self.vector_store.search(
                query=query,
                n_results=n_results,
                filter_metadata=filter_metadata
            )

            # Formatta risultati
            relevant_docs = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'],
                results['metadatas'],
                results['distances']
            )):
                relevant_docs.append({
                    'content': doc,
                    'metadata': metadata,
                    'score': 1 - distance,  # Converti distance in similarity score
                    'rank': i + 1
                })

            logger.info(f"✅ Trovati {len(relevant_docs)} documenti rilevanti per query")
            return relevant_docs

        except Exception as e:
            logger.error(f"❌ Errore retrieve documenti: {e}")
            return []

    def generate_rag_response(
        self,
        query: str,
        context: Optional[str] = None,
        tipo_filter: Optional[List[TipoDocumento]] = None,
        n_docs: int = 3
    ) -> Dict:
        """
        Genera risposta usando RAG.

        Args:
            query: Domanda/query
            context: Contesto aggiuntivo (es. email originale)
            tipo_filter: Filtra documenti per tipo
            n_docs: Numero documenti da usare

        Returns:
            Dict: {response, sources, confidence}
        """
        try:
            # Retrieve documenti rilevanti
            relevant_docs = self.retrieve_relevant_documents(
                query=query,
                n_results=n_docs,
                tipo_filter=tipo_filter
            )

            if not relevant_docs:
                logger.warning("Nessun documento rilevante trovato, uso LLM senza RAG")
                response = self.llm_client.generate(query, model_type="generation")
                return {
                    'response': response,
                    'sources': [],
                    'confidence': 0.5,
                    'rag_used': False
                }

            # Costruisci contesto da documenti
            context_parts = []
            sources = []

            for doc in relevant_docs:
                context_parts.append(f"[Documento: {doc['metadata']['titolo']}]\n{doc['content']}\n")
                sources.append({
                    'titolo': doc['metadata']['titolo'],
                    'tipo': doc['metadata']['tipo'],
                    'chunk_index': doc['metadata']['chunk_index'],
                    'score': doc['score']
                })

            rag_context = "\n---\n".join(context_parts)

            # Costruisci prompt RAG
            prompt = self._build_rag_prompt(query, rag_context, context)

            # Genera risposta
            response = self.llm_client.generate(prompt, model_type="generation")

            # Calcola confidence basata su score documenti
            avg_score = sum(d['score'] for d in relevant_docs) / len(relevant_docs)

            logger.info(f"✅ Risposta RAG generata (confidence: {avg_score:.2f})")

            return {
                'response': response,
                'sources': sources,
                'confidence': avg_score,
                'rag_used': True,
                'num_sources': len(sources)
            }

        except Exception as e:
            logger.error(f"❌ Errore generazione RAG: {e}")
            # Fallback a LLM senza RAG
            response = self.llm_client.generate(query, model_type="generation")
            return {
                'response': response,
                'sources': [],
                'confidence': 0.3,
                'rag_used': False,
                'error': str(e)
            }

    def _build_rag_prompt(self, query: str, context: str, additional_context: Optional[str] = None) -> str:
        """
        Costruisce prompt per RAG.

        Args:
            query: Domanda
            context: Contesto da documenti
            additional_context: Contesto aggiuntivo

        Returns:
            str: Prompt completo
        """
        prompt = f"""Sei un assistente esperto di SNALS (sindacato scuola).

Usa SOLO le informazioni nei documenti forniti per rispondere alla domanda.
Se i documenti non contengono informazioni sufficienti, dillo chiaramente.

DOCUMENTI DI RIFERIMENTO:
{context}

"""

        if additional_context:
            prompt += f"""CONTESTO AGGIUNTIVO:
{additional_context}

"""

        prompt += f"""DOMANDA:
{query}

ISTRUZIONI:
1. Rispondi in modo preciso basandoti sui documenti
2. Cita il nome del documento quando possibile
3. Se i documenti non contengono la risposta, spiega cosa manca
4. Usa un tono professionale e cortese
5. Formatta la risposta in modo chiaro

RISPOSTA:"""

        return prompt

    def update_document_usage(self, documento_id: int):
        """
        Aggiorna statistiche utilizzo documento.

        Args:
            documento_id: ID documento
        """
        try:
            documento = self.db.query(Documento).filter(Documento.id == documento_id).first()

            if documento:
                from datetime import datetime
                documento.num_utilizzi += 1
                documento.ultimo_accesso = datetime.now()
                self.db.commit()

        except Exception as e:
            logger.error(f"Errore aggiornamento usage: {e}")
