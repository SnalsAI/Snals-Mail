"""
Smart Draft Generator - Genera bozze di risposta intelligenti usando RAG.

Questo servizio arricchisce le bozze di risposta recuperando automaticamente
documenti rilevanti dal knowledge base (normativa, FAQ, risposte precedenti).
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from app.integrations.llm_client import LLMClient
from app.models.email import Email, EmailCategory

logger = logging.getLogger(__name__)


def _get_categoria_value(categoria) -> str:
    """Restituisce il valore stringa della categoria, sia che sia enum o stringa."""
    if categoria is None:
        return None
    if hasattr(categoria, 'value'):
        return categoria.value
    return str(categoria)


class SmartDraftGenerator:
    """Generatore intelligente di bozze email con contesto RAG"""

    def __init__(self, llm_client: LLMClient = None, rag_service=None):
        """
        Inizializza il generatore.

        Args:
            llm_client: Client LLM (opzionale, ne crea uno se non fornito)
            rag_service: Servizio RAG (opzionale, lo importa se non fornito)
        """
        self.llm_client = llm_client or LLMClient()

        if rag_service:
            self.rag_service = rag_service
        else:
            # Import lazy per evitare circular dependencies
            from app.services.rag_service import get_rag_service
            self.rag_service = get_rag_service()

    def generate_draft_with_context(
        self,
        email: Email,
        categoria: EmailCategory,
        timeout: float = 180.0
    ) -> Dict:
        """
        Genera bozza di risposta con contesto RAG.

        Args:
            email: Email da cui generare risposta
            categoria: Categoria email
            timeout: Timeout per LLM (default 3 minuti)

        Returns:
            Dict con:
                - draft: Testo bozza generata
                - referenced_documents: Lista ID documenti RAG usati
                - context_summary: Riepilogo contesto usato
                - metadata: Metadati generazione
        """
        logger.info(f"📝 Generazione draft intelligente per email {email.id} (categoria: {_get_categoria_value(categoria)})")

        # 1. Recupera contesto rilevante da RAG
        relevant_docs, context_summary = self._retrieve_relevant_context(
            email=email,
            categoria=categoria,
            limit=5
        )

        logger.info(f"📚 Trovati {len(relevant_docs)} documenti rilevanti nel RAG")

        # 2. Costruisci prompt arricchito
        prompt = self._build_enriched_prompt(
            email=email,
            categoria=categoria,
            relevant_docs=relevant_docs
        )

        # 3. Genera draft con LLM (timeout lungo)
        try:
            draft_text = self.llm_client.generate(
                prompt=prompt,
                model_type="generation",
                max_tokens=1500,
                temperature=0.4,
                timeout=timeout
            )

            logger.info(f"✅ Draft generata ({len(draft_text)} caratteri)")

            return {
                'draft': draft_text,
                'referenced_documents': [doc['id'] for doc in relevant_docs],
                'context_summary': context_summary,
                'metadata': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'categoria': _get_categoria_value(categoria),
                    'rag_docs_count': len(relevant_docs),
                    'timeout_used': timeout
                }
            }

        except Exception as e:
            logger.error(f"❌ Errore generazione draft: {e}")
            raise

    def _retrieve_relevant_context(
        self,
        email: Email,
        categoria: EmailCategory,
        limit: int = 5
    ) -> Tuple[List[Dict], str]:
        """
        Recupera documenti rilevanti dal RAG.

        Args:
            email: Email di riferimento
            categoria: Categoria email
            limit: Numero massimo documenti da recuperare

        Returns:
            Tuple[List[Dict], str]: (documenti, summary)
        """
        # Costruisci query per RAG
        query_parts = []

        if email.oggetto:
            query_parts.append(email.oggetto)

        if email.corpo:
            # Prendi primi 500 caratteri del corpo
            corpo_snippet = email.corpo[:500] if email.corpo else ""
            query_parts.append(corpo_snippet)

        query = " ".join(query_parts)

        if not query.strip():
            logger.warning("Query vuota per RAG, skip retrieval")
            return [], "Nessun contesto disponibile"

        try:
            # Query RAG con filtro categoria opzionale
            # FIX: Usa query() invece di search() (che non esiste)
            filter_metadata = None
            categoria_value = _get_categoria_value(categoria) if categoria else None
            if categoria_value:
                filter_metadata = {"categoria": categoria_value}

            results = self.rag_service.query(
                query_text=query,
                n_results=limit,
                filter_metadata=filter_metadata
            )

            if not results or 'documents' not in results:
                logger.info("Nessun documento rilevante trovato in RAG")
                return [], "Nessun documento rilevante nel knowledge base"

            # Filtra per min_relevance_score (0.5)
            min_relevance_score = 0.5
            documents = [
                doc for doc in results['documents']
                if doc.get('similarity_score') is None or doc.get('similarity_score', 0) >= min_relevance_score
            ]

            if not documents:
                logger.info("Nessun documento con score >= 0.5 trovato")
                return [], "Nessun documento sufficientemente rilevante"

            # Costruisci summary
            summary_parts = []
            for i, doc in enumerate(documents[:3], 1):  # Max 3 per summary
                metadata = doc.get('metadata', {})
                source_type = metadata.get('source', 'unknown')

                if source_type == 'knowledge_base':
                    tipo = metadata.get('tipo', 'documento')
                    summary_parts.append(f"{i}. {tipo.title()}")
                elif source_type == 'email':
                    summary_parts.append(f"{i}. Email precedente simile")
                else:
                    summary_parts.append(f"{i}. Documento")

            summary = f"{len(documents)} documenti trovati: " + ", ".join(summary_parts) if summary_parts else f"{len(documents)} documenti trovati"

            return documents, summary

        except Exception as e:
            logger.error(f"Errore retrieval RAG: {e}")
            return [], f"Errore retrieval: {str(e)}"

    def _build_enriched_prompt(
        self,
        email: Email,
        categoria: EmailCategory,
        relevant_docs: List[Dict]
    ) -> str:
        """
        Costruisce prompt arricchito con contesto RAG.

        Args:
            email: Email originale
            categoria: Categoria email
            relevant_docs: Documenti rilevanti da RAG

        Returns:
            str: Prompt completo per LLM
        """
        # Base info email
        mittente = email.mittente or "N/D"
        oggetto = email.oggetto or "N/D"
        corpo = email.corpo[:1000] if email.corpo else "N/D"  # Limita a 1000 caratteri

        # Formatta contesto RAG
        context_sections = []

        if relevant_docs:
            for i, doc in enumerate(relevant_docs[:5], 1):  # Max 5 documenti
                metadata = doc.get('metadata', {})
                doc_text = doc.get('document', '')[:500]  # Max 500 caratteri per doc

                source_type = metadata.get('source', 'documento')

                # Header documento
                if source_type == 'knowledge_base':
                    tipo = metadata.get('tipo', 'documento')
                    ente = metadata.get('ente', '')
                    header = f"📄 {tipo.title()}"
                    if ente:
                        header += f" ({ente})"
                else:
                    header = "📧 Email precedente simile"

                context_sections.append(f"""
### DOCUMENTO {i}: {header}
{doc_text}
""")

        context_text = "\n".join(context_sections) if context_sections else "Nessun documento di riferimento disponibile."

        # Costruisci prompt finale
        prompt = f"""Sei un assistente esperto del sindacato scuola SNALS di Taranto.

Il tuo compito è generare una bozza di risposta professionale, cortese e accurata.

## EMAIL RICEVUTA

**Da:** {mittente}
**Oggetto:** {oggetto}
**Testo:**
{corpo}

**Categoria:** {_get_categoria_value(categoria) or 'N/D'}

## DOCUMENTI DI RIFERIMENTO

{context_text}

## ISTRUZIONI

1. Analizza attentamente l'email ricevuta e i documenti di riferimento
2. Genera una risposta professionale e cortese
3. **Se nei documenti di riferimento c'è normativa o informazioni rilevanti, citale nella risposta**
4. Mantieni un tono formale ma cordiale
5. Fornisci informazioni concrete e utili
6. Se necessario, suggerisci passi successivi o documenti da consultare
7. Firma come "Segreteria SNALS Taranto"
8. Usa formato HTML con paragrafi ben formattati (<p>, <br>, <strong>)

## LINEE GUIDA PER TIPO DI RICHIESTA

- **Richiesta informazioni:** Fornisci info dettagliate, cita normativa se disponibile
- **Richiesta appuntamento:** Conferma disponibilità, chiedi preferenze orarie
- **Richiesta tesseramento:** Spiega procedura, documenti necessari, modalità
- **Convocazione:** Conferma partecipazione o delega
- **Comunicazione UST/USR:** Prendi atto, eventualmente inoltra a interessati

Genera SOLO il corpo della risposta (non includere oggetto o intestazioni email).
"""

        return prompt

    def generate_simple_draft(
        self,
        email: Email,
        categoria: EmailCategory,
        timeout: float = 120.0
    ) -> str:
        """
        Genera bozza semplice senza RAG (fallback).

        Args:
            email: Email da cui generare risposta
            categoria: Categoria email
            timeout: Timeout LLM

        Returns:
            str: Testo bozza
        """
        logger.info(f"📝 Generazione draft semplice (senza RAG) per email {email.id}")

        prompt = f"""Sei un assistente del sindacato SNALS.

Genera una risposta cortese e professionale per questa email:

**Da:** {email.mittente}
**Oggetto:** {email.oggetto}
**Corpo:**
{email.corpo[:800] if email.corpo else 'N/D'}

**Categoria:** {_get_categoria_value(categoria) or 'N/D'}

Genera una risposta appropriata, cortese e professionale.
Firma come "Segreteria SNALS Taranto".
Usa formato HTML.
"""

        try:
            draft = self.llm_client.generate(
                prompt=prompt,
                model_type="generation",
                max_tokens=1000,
                temperature=0.5,
                timeout=timeout
            )
            return draft

        except Exception as e:
            logger.error(f"Errore generazione draft semplice: {e}")
            raise
