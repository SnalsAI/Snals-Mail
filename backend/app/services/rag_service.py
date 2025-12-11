"""
Servizio RAG (Retrieval-Augmented Generation) per indicizzazione e ricerca documenti
"""
import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from sqlalchemy.orm import Session

from app.models.email import Email
from app.models.knowledge_document import KnowledgeDocument
from app.services.attachment_extractor import get_attachment_extractor

logger = logging.getLogger(__name__)


class RAGService:
    """
    Servizio per indicizzazione e ricerca documenti con RAG.

    Indicizza automaticamente:
    - Documenti da info@snals.it (comunicazioni SNALS centrale)
    - Documenti da USR/USP (comunicazioni uffici scolastici)

    Mantiene metadati:
    - categoria: categoria principale email
    - sottocategoria: categorizzazione di secondo livello
    - mittente: indirizzo mittente
    - data: data ricezione email
    - email_id: ID email di origine
    - filename: nome file allegato
    """

    def __init__(self, persist_directory: str = "storage/chroma_db"):
        """
        Inizializza il servizio RAG.

        Args:
            persist_directory: Directory per persistenza ChromaDB
        """
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # Inizializza ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Usa sentence-transformers per embeddings multilingua (supporta italiano)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )

        # Crea o recupera collection
        self.collection = self.client.get_or_create_collection(
            name="snals_documents",
            embedding_function=self.embedding_function,
            metadata={"description": "Documenti SNALS da info@snals.it e USR/USP"}
        )

        logger.info(f"📚 RAG Service inizializzato - {self.collection.count()} documenti indicizzati")

    def should_index_email(self, email: Email) -> bool:
        """
        Determina se un'email deve essere indicizzata nel RAG.

        Criteri:
        - Email da info@snals.it (comunicazioni SNALS centrale)
        - Email da USR/USP (comunicazione_ust_usr)
        - Email con allegati

        Args:
            email: Email da valutare

        Returns:
            bool: True se deve essere indicizzata
        """
        # Controlla mittente info@snals.it
        if email.mittente and 'info@snals.it' in email.mittente.lower():
            return True

        # Controlla categoria UST/USR
        if email.categoria and email.get_categoria_value() == 'comunicazione_ust_usr':
            return True

        return False

    def index_email(self, email: Email, db: Session) -> Dict[str, Any]:
        """
        Indicizza un'email e i suoi allegati nel RAG.

        Args:
            email: Email da indicizzare
            db: Sessione database

        Returns:
            Dict con statistiche indicizzazione
        """
        if not self.should_index_email(email):
            logger.info(f"Email {email.id} non richiede indicizzazione RAG")
            return {
                'indexed': False,
                'reason': 'Email non da fonte RAG (info@snals.it o UST/USR)'
            }

        if not email.allegati or len(email.allegati) == 0:
            logger.info(f"Email {email.id} non ha allegati da indicizzare")
            return {
                'indexed': False,
                'reason': 'Nessun allegato'
            }

        logger.info(f"📥 Indicizzazione email {email.id} nel RAG...")

        extractor = get_attachment_extractor()
        documents_indexed = 0
        errors = []

        # Prepara metadati base
        base_metadata = {
            'email_id': str(email.id),
            'categoria': email.get_categoria_value() or 'unknown',
            'sottocategoria': email.sottocategoria or 'non_specificata',
            'mittente': email.mittente or 'unknown',
            'data_ricezione': email.data_ricezione.isoformat() if email.data_ricezione else datetime.now().isoformat(),
            'oggetto': email.oggetto[:200] if email.oggetto else '',
        }

        # Estrai interpretazione se disponibile
        if email.interpretazione and email.interpretazione.interpretazione_json:
            interp = email.interpretazione.interpretazione_json

            # Aggiungi dati interpretati ai metadati
            if 'migliorato' in interp:
                migliorato = interp['migliorato']
                if isinstance(migliorato, dict):
                    base_metadata['argomento'] = migliorato.get('argomento', '')
                    base_metadata['scuola'] = migliorato.get('scuola', '')

        # Indicizza allegati
        for allegato in email.allegati:
            try:
                filename = allegato.get('filename', 'unknown')
                filepath = allegato.get('path')

                if not filepath:
                    logger.warning(f"Path mancante per: {filename}")
                    errors.append(f"Path mancante: {filename}")
                    continue

                # Converti path relativo in assoluto se necessario
                if not os.path.isabs(filepath):
                    filepath = os.path.join('/app', filepath)

                if not os.path.exists(filepath):
                    logger.warning(f"File non trovato: {filepath}")
                    errors.append(f"File non trovato: {filename}")
                    continue

                # Estrai solo documenti testuali (PDF, Word, TXT)
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ['.pdf', '.doc', '.docx', '.txt', '.eml']:
                    logger.debug(f"Skip allegato {filename}: tipo non supportato")
                    continue

                # Estrai testo
                text = None
                if ext == '.eml':
                    # Per EML, estrai tutto il contenuto
                    eml_data = extractor.parse_eml_complete(filepath)
                    if eml_data:
                        text = f"{eml_data['subject']}\n\n{eml_data['body']}"
                else:
                    # Per altri, estrai testo
                    text = extractor.extract_text(filepath)

                if not text or len(text.strip()) < 50:
                    logger.warning(f"Testo insufficiente in {filename}: {len(text) if text else 0} caratteri")
                    errors.append(f"Testo insufficiente: {filename}")
                    continue

                # Crea metadati specifici documento
                doc_metadata = base_metadata.copy()
                doc_metadata['filename'] = filename
                doc_metadata['file_extension'] = ext
                doc_metadata['text_length'] = len(text)

                # Crea ID univoco documento
                doc_id = f"email_{email.id}_{filename}_{hash(filepath)}"

                # Indicizza nel vector store
                self.collection.add(
                    documents=[text],
                    metadatas=[doc_metadata],
                    ids=[doc_id]
                )

                documents_indexed += 1
                logger.info(f"✅ Indicizzato: {filename} ({len(text)} caratteri)")

            except Exception as e:
                logger.error(f"Errore indicizzazione {filename}: {e}")
                errors.append(f"{filename}: {str(e)}")

        result = {
            'indexed': True,
            'email_id': email.id,
            'documents_indexed': documents_indexed,
            'total_documents': self.collection.count(),
            'errors': errors
        }

        if documents_indexed > 0:
            logger.info(f"✅ Email {email.id}: {documents_indexed} documenti indicizzati nel RAG")
        else:
            logger.warning(f"⚠️ Email {email.id}: nessun documento indicizzato")

        return result

    def index_knowledge_document(self, documento: KnowledgeDocument) -> Dict[str, Any]:
        """
        Indicizza un documento knowledge nel RAG.

        Args:
            documento: KnowledgeDocument da indicizzare

        Returns:
            Dict con statistiche indicizzazione
        """
        logger.info(f"📥 Indicizzazione documento knowledge {documento.id}: {documento.titolo}")

        if not documento.testo_estratto or len(documento.testo_estratto.strip()) < 50:
            logger.warning(f"Documento {documento.id} ha testo insufficiente: {len(documento.testo_estratto) if documento.testo_estratto else 0} caratteri")
            return {
                'indexed': False,
                'reason': 'Testo insufficiente',
                'documento_id': documento.id
            }

        try:
            # Prepara metadati
            metadata = {
                'source': 'knowledge_base',
                'documento_id': str(documento.id),
                'tipo_documento': documento.tipo_documento.value if documento.tipo_documento else 'unknown',
                'titolo': documento.titolo[:200] if documento.titolo else '',
                'categoria_email': documento.categoria_email or 'non_specificata',
                'tags': ','.join(documento.tags) if documento.tags else '',
                'ente_emittente': documento.ente_emittente or '',
                'data_emissione': documento.data_emissione.isoformat() if documento.data_emissione else '',
                'numero_protocollo': documento.numero_protocollo or '',
                'anno_riferimento': documento.anno_riferimento or '',
                'file_name': documento.file_name or '',
                'created_at': documento.created_at.isoformat() if documento.created_at else datetime.now().isoformat()
            }

            # Chunking del testo (max 1000 caratteri per chunk con overlap 200)
            text = documento.testo_estratto
            chunk_size = 1000
            chunk_overlap = 200
            chunks = []
            document_ids = []

            # Se il testo è piccolo, indicizza tutto insieme
            if len(text) <= chunk_size:
                chunks = [text]
            else:
                # Split in chunks con overlap
                start = 0
                while start < len(text):
                    end = min(start + chunk_size, len(text))
                    chunk = text[start:end]
                    chunks.append(chunk)
                    start = end - chunk_overlap if end < len(text) else end

            # Indicizza ogni chunk
            for i, chunk in enumerate(chunks):
                # Crea metadati specifici chunk
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = i
                chunk_metadata['total_chunks'] = len(chunks)
                chunk_metadata['chunk_length'] = len(chunk)

                # ID univoco chunk
                doc_id = f"knowledge_{documento.id}_chunk_{i}"
                document_ids.append(doc_id)

                # Indicizza nel vector store
                self.collection.add(
                    documents=[chunk],
                    metadatas=[chunk_metadata],
                    ids=[doc_id]
                )

                logger.debug(f"✅ Chunk {i+1}/{len(chunks)} indicizzato: {len(chunk)} caratteri")

            logger.info(f"✅ Documento knowledge {documento.id} indicizzato: {len(chunks)} chunks, {len(text)} caratteri totali")

            return {
                'indexed': True,
                'documento_id': documento.id,
                'document_ids': document_ids,
                'chunks_created': len(chunks),
                'total_characters': len(text),
                'total_documents': self.collection.count()
            }

        except Exception as e:
            logger.error(f"❌ Errore indicizzazione documento knowledge {documento.id}: {e}", exc_info=True)
            return {
                'indexed': False,
                'reason': str(e),
                'documento_id': documento.id
            }

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Esegue query sul RAG.

        Args:
            query_text: Testo della query
            n_results: Numero risultati da restituire
            filter_metadata: Filtri metadati (es. {"categoria": "comunicazione_ust_usr"})

        Returns:
            Dict con risultati query
        """
        logger.info(f"🔍 Query RAG: '{query_text[:50]}...' (top {n_results})")

        # Esegui query
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filter_metadata
        )

        # Formatta risultati
        documents = []
        if results and results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results['distances'] else None

                # Calcola similarità: ChromaDB usa distanza coseno (0-2) o L2
                # Per coseno: 0 = identico, 2 = opposto
                # Convertiamo in percentuale 0-100%
                if distance is not None:
                    # Normalizza: distanza 0 = 100%, distanza 2 = 0%
                    similarity = max(0, min(100, (1 - distance / 2) * 100))
                else:
                    similarity = None

                documents.append({
                    'text': doc[:500] + '...' if len(doc) > 500 else doc,  # Troncato per preview
                    'full_text': doc,
                    'metadata': metadata,
                    'similarity_score': similarity,  # Percentuale 0-100%
                    'rank': i + 1
                })

        logger.info(f"✅ Query completata: {len(documents)} documenti trovati")

        return {
            'query': query_text,
            'results_count': len(documents),
            'documents': documents
        }

    def list_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        filter_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Lista tutti i documenti nel RAG con paginazione.

        Args:
            limit: Numero massimo documenti da restituire
            offset: Offset per paginazione
            filter_metadata: Filtri opzionali per metadati

        Returns:
            Dict con lista documenti e metadati
        """
        logger.info(f"📋 Lista documenti RAG: limit={limit}, offset={offset}")

        try:
            # ChromaDB non supporta offset direttamente, prendiamo tutti e facciamo slice
            all_results = self.collection.get(
                where=filter_metadata,
                include=['documents', 'metadatas']
            )

            total_count = len(all_results['ids']) if all_results['ids'] else 0

            # Paginazione manuale
            start = offset
            end = offset + limit

            documents = []
            if all_results and all_results['ids']:
                ids_slice = all_results['ids'][start:end]
                docs_slice = all_results['documents'][start:end] if all_results['documents'] else []
                metas_slice = all_results['metadatas'][start:end] if all_results['metadatas'] else []

                for i, doc_id in enumerate(ids_slice):
                    doc_text = docs_slice[i] if i < len(docs_slice) else ""
                    metadata = metas_slice[i] if i < len(metas_slice) else {}

                    documents.append({
                        'id': doc_id,
                        'summary': doc_text[:300] + '...' if len(doc_text) > 300 else doc_text,
                        'full_text': doc_text,
                        'metadata': metadata,
                        'text_length': len(doc_text)
                    })

            logger.info(f"✅ Restituiti {len(documents)}/{total_count} documenti")

            return {
                'documents': documents,
                'total': total_count,
                'limit': limit,
                'offset': offset
            }

        except Exception as e:
            logger.error(f"Errore lista documenti: {e}")
            return {
                'documents': [],
                'total': 0,
                'limit': limit,
                'offset': offset,
                'error': str(e)
            }

    def update_document_metadata(self, document_id: str, new_metadata: Dict) -> bool:
        """
        Aggiorna i metadati di un documento.

        Args:
            document_id: ID del documento
            new_metadata: Nuovi metadati

        Returns:
            bool: True se aggiornamento riuscito
        """
        logger.info(f"✏️ Aggiornamento metadati documento {document_id}")

        try:
            # Verifica che il documento esista
            existing = self.collection.get(ids=[document_id])

            if not existing or not existing['ids']:
                logger.warning(f"Documento {document_id} non trovato")
                return False

            # Aggiorna metadati
            self.collection.update(
                ids=[document_id],
                metadatas=[new_metadata]
            )

            logger.info(f"✅ Metadati aggiornati per documento {document_id}")
            return True

        except Exception as e:
            logger.error(f"Errore aggiornamento metadati: {e}")
            return False

    def delete_document(self, document_id: str) -> bool:
        """
        Elimina un singolo documento dal RAG.

        Args:
            document_id: ID del documento

        Returns:
            bool: True se eliminazione riuscita
        """
        logger.info(f"🗑️ Eliminazione documento {document_id}")

        try:
            self.collection.delete(ids=[document_id])
            logger.info(f"✅ Documento {document_id} eliminato")
            return True

        except Exception as e:
            logger.error(f"Errore eliminazione documento: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Restituisce statistiche sul RAG.

        Returns:
            Dict con statistiche
        """
        total_docs = self.collection.count()

        # Query per categoria (non supportato direttamente, usiamo get)
        stats = {
            'total_documents': total_docs,
            'collection_name': self.collection.name,
            'persist_directory': self.persist_directory
        }

        logger.info(f"📊 Statistiche RAG: {total_docs} documenti totali")

        return stats

    def delete_email_documents(self, email_id: int) -> int:
        """
        Elimina tutti i documenti associati a un'email.

        Args:
            email_id: ID email

        Returns:
            int: Numero documenti eliminati
        """
        logger.info(f"🗑️ Eliminazione documenti email {email_id} dal RAG...")

        # Trova tutti i documenti dell'email
        try:
            results = self.collection.get(
                where={"email_id": str(email_id)}
            )

            if results and results['ids']:
                ids_to_delete = results['ids']
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"✅ Eliminati {len(ids_to_delete)} documenti dall'email {email_id}")
                return len(ids_to_delete)
            else:
                logger.info(f"Nessun documento trovato per email {email_id}")
                return 0

        except Exception as e:
            logger.error(f"Errore eliminazione documenti email {email_id}: {e}")
            return 0

    def reset_collection(self) -> bool:
        """
        Reset completo della collection (ATTENZIONE: elimina tutti i dati).

        Returns:
            bool: True se reset completato
        """
        logger.warning("⚠️ RESET RAG collection...")

        try:
            self.client.delete_collection(name="snals_documents")
            self.collection = self.client.get_or_create_collection(
                name="snals_documents",
                embedding_function=self.embedding_function,
                metadata={"description": "Documenti SNALS da info@snals.it e USR/USP"}
            )
            logger.info("✅ RAG collection resettata")
            return True
        except Exception as e:
            logger.error(f"Errore reset collection: {e}")
            return False

    def chat(
        self,
        query_text: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None,
        use_openai: bool = False,
        max_context_docs: int = 4,
        max_doc_length: int = 1500
    ) -> Dict[str, Any]:
        """
        Esegue una query conversazionale con generazione risposta usando LLM + RAG.

        Args:
            query_text: Domanda dell'utente
            n_results: Numero documenti da recuperare
            filter_metadata: Filtri sui metadati
            use_openai: Se True, usa OpenAI invece di Ollama
            max_context_docs: Numero massimo documenti nel contesto
            max_doc_length: Lunghezza massima per documento

        Returns:
            Dict con risposta generata e fonti
        """
        logger.info(f"💬 Chat RAG query: {query_text[:100]} (OpenAI={use_openai})")

        # Check cache first
        cache_key = f"{query_text}_{n_results}_{filter_metadata}_{use_openai}"
        if hasattr(self, '_chat_cache') and cache_key in self._chat_cache:
            cached = self._chat_cache[cache_key]
            # Cache valid for 5 minutes
            if (datetime.now() - cached['timestamp']).seconds < 300:
                logger.info("📦 Risposta dalla cache")
                cached['result']['cached'] = True
                return cached['result']

        # Recupera documenti rilevanti
        search_result = self.query(
            query_text=query_text,
            n_results=n_results,
            filter_metadata=filter_metadata
        )

        documents = search_result.get('documents', [])

        if not documents:
            return {
                'query': query_text,
                'answer': "Non ho trovato documenti rilevanti per rispondere alla tua domanda. Prova a riformulare la domanda o verifica che i documenti siano stati indicizzati nel sistema.",
                'sources': [],
                'sources_count': 0,
                'llm_model': None,
                'cached': False
            }

        # Costruisci contesto dai documenti
        context_parts = []
        docs_used = min(max_context_docs, len(documents))
        for i, doc in enumerate(documents[:docs_used]):
            metadata = doc.get('metadata', {})
            text = doc.get('full_text', doc.get('document', ''))

            # Limita testo
            if len(text) > max_doc_length:
                text = text[:max_doc_length] + "..."

            # Informazioni fonte
            source_info = []
            if metadata.get('filename'):
                source_info.append(f"File: {metadata['filename']}")
            if metadata.get('oggetto'):
                source_info.append(f"Oggetto: {metadata['oggetto']}")
            if metadata.get('mittente'):
                source_info.append(f"Mittente: {metadata['mittente']}")
            if metadata.get('data_ricezione') or metadata.get('data'):
                source_info.append(f"Data: {metadata.get('data_ricezione') or metadata.get('data')}")
            if metadata.get('categoria'):
                source_info.append(f"Categoria: {metadata['categoria']}")

            source_label = f"[DOCUMENTO {i+1}]"
            if source_info:
                source_label += f"\n{chr(10).join(source_info)}"
            context_parts.append(f"{source_label}\nContenuto:\n{text}\n")

        context = "\n" + "="*50 + "\n".join(context_parts)

        # Genera risposta con LLM
        llm_model = None
        try:
            prompt = f"""Sei un assistente esperto del sindacato SNALS (Sindacato Nazionale Autonomo Lavoratori Scuola).
Rispondi alle domande basandoti ESCLUSIVAMENTE sui documenti forniti.

REGOLE IMPORTANTI:
1. Usa SOLO le informazioni presenti nei documenti
2. Se l'informazione non è nei documenti, dillo chiaramente
3. Cita sempre la fonte (es: "Dal Documento 1...")
4. Riporta date, numeri e riferimenti normativi esattamente
5. Rispondi in italiano, in modo chiaro e professionale
6. Se ci sono più documenti rilevanti, integra le informazioni

DOCUMENTI DISPONIBILI:
{context}

DOMANDA:
{query_text}

RISPOSTA DETTAGLIATA:"""

            if use_openai:
                # Use OpenAI
                answer, llm_model = self._generate_with_openai(prompt)
            else:
                # Use Ollama
                answer, llm_model = self._generate_with_ollama(prompt)

            logger.info(f"✅ Risposta generata con {llm_model}: {len(answer)} caratteri")

            result = {
                'query': query_text,
                'answer': answer,
                'sources': documents,
                'sources_count': len(documents),
                'llm_model': llm_model,
                'cached': False
            }

            # Cache the result
            if not hasattr(self, '_chat_cache'):
                self._chat_cache = {}
            self._chat_cache[cache_key] = {
                'result': result.copy(),
                'timestamp': datetime.now()
            }
            # Limit cache size
            if len(self._chat_cache) > 100:
                oldest = min(self._chat_cache.keys(), key=lambda k: self._chat_cache[k]['timestamp'])
                del self._chat_cache[oldest]

            return result

        except Exception as e:
            logger.error(f"Errore generazione risposta LLM: {e}", exc_info=True)
            return {
                'query': query_text,
                'answer': f"Si è verificato un errore nella generazione della risposta: {str(e)}. I documenti rilevanti sono stati trovati ma non è stato possibile elaborare una risposta.",
                'sources': documents,
                'sources_count': len(documents),
                'llm_model': llm_model,
                'cached': False
            }

    def _generate_with_ollama(self, prompt: str) -> tuple:
        """Genera risposta usando Ollama locale."""
        from app.integrations.llm_client import LLMClient
        llm_client = LLMClient()

        response = llm_client.generate(
            prompt=prompt,
            model_type="generation",  # Usa modello di generazione
            temperature=0.3,
            max_tokens=600,
            timeout=60.0
        )

        answer = response.strip() if response else "Errore nella generazione della risposta."
        model_used = f"Ollama ({llm_client.models.get('generation', 'unknown')})"
        return answer, model_used

    def _generate_with_openai(self, prompt: str) -> tuple:
        """Genera risposta usando OpenAI API."""
        import os
        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            logger.warning("OpenAI API key non configurata, fallback a Ollama")
            return self._generate_with_ollama(prompt)

        try:
            import openai
            client = openai.OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sei un assistente esperto del sindacato SNALS. Rispondi in italiano."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )

            answer = response.choices[0].message.content.strip()
            model_used = f"OpenAI ({response.model})"
            return answer, model_used

        except Exception as e:
            logger.error(f"Errore OpenAI, fallback a Ollama: {e}")
            return self._generate_with_ollama(prompt)


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Ottiene istanza singleton del servizio RAG."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
