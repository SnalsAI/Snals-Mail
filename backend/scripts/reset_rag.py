"""
Script per cancellare tutti i documenti nel RAG
"""
import sys
import os

# Aggiungi il path dell'app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rag_service import RAGService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Cancella tutti i documenti dal RAG"""
    try:
        logger.info("🗑️ Inizializzazione RAG Service...")
        rag = RAGService()

        logger.info(f"📊 Documenti attuali: {rag.collection.count()}")

        # Conferma
        risposta = input("\n⚠️ SEI SICURO di voler cancellare TUTTI i documenti dal RAG? (scrivi 'SI' per confermare): ")

        if risposta.strip().upper() != 'SI':
            logger.info("❌ Operazione annullata")
            return

        logger.info("🗑️ Cancellazione in corso...")
        success = rag.reset_collection()

        if success:
            logger.info("✅ TUTTI i documenti sono stati cancellati dal RAG")
            logger.info(f"📊 Documenti rimanenti: {rag.collection.count()}")
        else:
            logger.error("❌ Errore durante la cancellazione")

    except Exception as e:
        logger.error(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
