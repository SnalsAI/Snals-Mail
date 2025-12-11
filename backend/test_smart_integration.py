#!/usr/bin/env python3
"""
Test script per verificare l'integrazione di SmartInterpelloExtractor e SmartResponseGenerator
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import logging
from app.services.smart_extractor import SmartInterpelloExtractor
from app.services.smart_generator import SmartResponseGenerator, TaskType
from app.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_smart_extractor():
    """Test SmartInterpelloExtractor con testo interpello di esempio"""
    print("\n" + "=" * 80)
    print("TEST 1: SmartInterpelloExtractor")
    print("=" * 80)

    settings = get_settings()

    # Inizializza estrattore
    extractor = SmartInterpelloExtractor(
        openai_api_key=settings.OPENAI_API_KEY,
        openai_model=settings.OPENAI_MODEL
    )

    # Testo interpello di test
    testo_interpello = """
    INTERPELLO INTERNO PER SUPPLENZA

    Si rende noto che questo istituto ha la necessità di coprire una supplenza per la
    classe di concorso A-42 (Scienze e tecnologie meccaniche) per 12 ore settimanali.

    La supplenza avrà inizio dal 15/01/2025 e terminerà il 30/06/2025.

    Gli interessati possono presentare domanda entro il 20/12/2024.

    Provincia: Taranto
    Istituto: ITIS "Pacinotti"
    """

    print(f"\n📄 Testo interpello:\n{testo_interpello[:200]}...\n")

    # Estrai dati
    risultato = extractor.extract(testo_interpello)

    if risultato:
        print("\n✅ ESTRAZIONE COMPLETATA")
        print(f"\nDati estratti:")
        for key, value in risultato.items():
            if key != 'metadata_estrazione':
                print(f"  - {key}: {value}")

        # Mostra metadata
        if 'metadata_estrazione' in risultato:
            metadata = risultato['metadata_estrazione']
            print(f"\n📊 Metadata:")
            print(f"  - Strategia finale: {metadata.get('strategy_final')}")
            print(f"  - Strategie tentate: {', '.join(metadata.get('strategies_used', []))}")
            print(f"  - Tempo totale: {metadata.get('total_time_ms', 0):.0f}ms")

            if 'completeness_scores' in metadata:
                print(f"  - Completeness scores:")
                for strategy, score in metadata['completeness_scores'].items():
                    print(f"    * {strategy}: {score:.0%}")

        # Mostra statistiche
        print(f"\n📈 Statistiche estrattore:")
        stats = extractor.get_stats()
        for key, value in stats.items():
            print(f"  - {key}: {value}")

        return True
    else:
        print("\n❌ ESTRAZIONE FALLITA")
        return False


def test_smart_generator():
    """Test SmartResponseGenerator con diverse complessità"""
    print("\n" + "=" * 80)
    print("TEST 2: SmartResponseGenerator")
    print("=" * 80)

    settings = get_settings()

    # Inizializza generatore
    generator = SmartResponseGenerator(
        openai_api_key=settings.OPENAI_API_KEY,
        openai_model=settings.OPENAI_MODEL,
        daily_limit_eur=settings.OPENAI_DAILY_LIMIT_EUR
    )

    # Test 1: Risposta semplice (sintesi)
    print("\n📝 TEST 2.1: Sintesi semplice")
    prompt_sintesi = """
    Sintetizza questa email in 2-3 frasi:

    Da: mario.rossi@scuola.it
    Oggetto: Richiesta informazioni supplenza

    Buongiorno, vorrei sapere se ci sono posti disponibili per supplenze di matematica.
    Sono disponibile da subito.
    """

    result = generator.generate(
        prompt=prompt_sintesi,
        task_type=TaskType.SINTESI,
        max_tokens=200,
        use_cache=True
    )

    if result.get('risposta'):
        print(f"\n✅ Risposta generata:")
        print(f"{result['risposta'][:200]}...")
        print(f"\n📊 Strategia usata: {result['metadata'].get('strategy_final')}")
        print(f"⏱️  Tempo: {result['metadata'].get('total_time_ms', 0):.0f}ms")
    else:
        print(f"\n❌ Generazione fallita")
        if 'error' in result:
            print(f"Errore: {result['error']}")

    # Test 2: Risposta standard (FAQ)
    print("\n📝 TEST 2.2: Risposta standard FAQ")
    prompt_faq = """
    Rispondi a questa domanda frequente:

    Domanda: Come posso iscrivermi al sindacato SNALS?

    Fornisci una risposta chiara e professionale con i passi da seguire.
    """

    result = generator.generate(
        prompt=prompt_faq,
        task_type=TaskType.FAQ,
        max_tokens=300,
        use_cache=True
    )

    if result.get('risposta'):
        print(f"\n✅ Risposta generata:")
        print(f"{result['risposta'][:200]}...")
        print(f"\n📊 Strategia usata: {result['metadata'].get('strategy_final')}")
        print(f"⏱️  Tempo: {result['metadata'].get('total_time_ms', 0):.0f}ms")

        # Verifica validazione
        if 'validation' in result['metadata']:
            print(f"✓ Validazione: {result['metadata']['validation']}")
    else:
        print(f"\n❌ Generazione fallita")

    # Test 3: Risposta complessa (consulenza)
    print("\n📝 TEST 2.3: Risposta complessa (consulenza)")
    prompt_consulenza = """
    Fornisci consulenza dettagliata su questa domanda legale:

    Un docente a tempo determinato chiede: "Ho un contratto al 30 giugno 2025.
    Se mi viene proposta una supplenza più lunga in altra scuola, posso interrompere
    il contratto attuale? Quali sono i diritti e doveri secondo il CCNL?"

    Fornisci risposta dettagliata con riferimenti normativi.
    """

    result = generator.generate(
        prompt=prompt_consulenza,
        task_type=TaskType.CONSULENZA,
        max_tokens=500,
        use_cache=False
    )

    if result.get('risposta'):
        print(f"\n✅ Risposta generata:")
        print(f"{result['risposta'][:300]}...")
        print(f"\n📊 Strategia usata: {result['metadata'].get('strategy_final')}")
        print(f"⏱️  Tempo: {result['metadata'].get('total_time_ms', 0):.0f}ms")

        # Mostra info budget OpenAI
        if 'openai_budget' in result['metadata']:
            budget = result['metadata']['openai_budget']
            print(f"\n💰 Budget OpenAI:")
            print(f"  - Speso oggi: €{budget['today_total_eur']:.6f}")
            print(f"  - Rimanente: €{budget['remaining_eur']:.6f}")
            print(f"  - Usato: {budget['used_pct']:.1f}%")
    else:
        print(f"\n❌ Generazione fallita")
        if 'error' in result:
            print(f"Errore: {result['error']}")

    # Mostra statistiche
    print(f"\n📈 Statistiche generatore:")
    stats = generator.get_stats()
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            if key.endswith('_pct'):
                print(f"  - {key}: {value:.1f}%")
            else:
                print(f"  - {key}: {value}")


def main():
    """Esegue tutti i test"""
    print("\n" + "=" * 80)
    print("VERIFICA INTEGRAZIONE SMART EXTRACTOR & GENERATOR")
    print("=" * 80)

    try:
        # Test 1: Smart Extractor
        test_smart_extractor()

        # Test 2: Smart Generator
        test_smart_generator()

        print("\n" + "=" * 80)
        print("✅ TUTTI I TEST COMPLETATI")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"❌ Errore durante i test: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
